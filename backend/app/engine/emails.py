"""Send email nodes (TASK-0051, DEC-0040): send one e-mail through the owner's SMTP credential.

Node data: `credential_id` (an SMTP credential), `to`, `cc`, `bcc`, `reply_to` (templates; addresses separated by
`,` `;` or new lines, or one `{{state.x}}` holding a list), `subject` and `body` (templates), `format` ("text" or
"html": values inserted into HTML are escaped and a plain text part is added), optional `output_field` (object).
Without a credential the node is a dry run: nothing is sent and the output shows the message it would have sent.
Sending is a side effect (engine/effects.py): a recovered run reuses the recorded result instead of sending again,
and the Message-ID comes from the node's idempotency key. `ports.email_quota(n)` caps recipients per owner per hour.
"""
from __future__ import annotations
import html as htmlmod, re, uuid
from typing import Any, Callable, Dict, List, Optional
from ..core import smtp
from ..core.errors import AppError
from . import providers
from .issues import Issue
from .ports import Ports
from .templating import VAR_RE, render, render_args

FORMATS = ("text", "html")
ADDRESS_FIELDS = ("to", "cc", "bcc", "reply_to")
MAX_RECIPIENTS, MAX_SUBJECT, MAX_BODY, PREVIEW = 50, 998, 512 * 1024, 2000


def templates(d: Dict[str, Any]) -> List[str]:
    return [d.get(k) or "" for k in (*ADDRESS_FIELDS, "subject", "body") if isinstance(d.get(k) or "", str)]


def fields(d: Dict[str, Any]) -> List[str]:
    return [d["output_field"]] if d.get("output_field") else []


def to_text(markup: str) -> str:
    """A readable plain text part for an HTML body."""
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", markup)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|h[1-6]|li|tr)>", "\n", t)
    t = re.sub(r"(?i)<li\b[^>]*>", "- ", t)
    t = htmlmod.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line.strip() for line in t.splitlines())).strip()


def _addresses(nid: str, raw: Any, state: Dict[str, Any]) -> List[str]:
    out = smtp.addresses(render_args(raw, state) if isinstance(raw, str) else raw)
    if (bad := smtp.invalid(out)): raise AppError("EMAIL_RECIPIENT_INVALID", node=nid, address=bad[0][:100])
    return out


def build(nid: str, d: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """Rendered and checked message parts."""
    to, cc, bcc, reply = (_addresses(nid, d.get(k) or "", state) for k in ADDRESS_FIELDS)
    rcpt = list(dict.fromkeys(to + cc + bcc))
    if not rcpt: raise AppError("EMAIL_RECIPIENTS_MISSING", node=nid)
    if len(rcpt) > MAX_RECIPIENTS: raise AppError("EMAIL_TOO_MANY_RECIPIENTS", node=nid, max=MAX_RECIPIENTS)
    subject = " ".join(render(d.get("subject") or "", state).split())[:MAX_SUBJECT]
    is_html = d.get("format") == "html"
    body = render(d.get("body") or "", state, htmlmod.escape if is_html else None)
    if len(body.encode()) > MAX_BODY: raise AppError("EMAIL_SEND_FAILED", reason=f"the message is larger than {MAX_BODY // 1024} KB")
    return {"to": to, "cc": cc, "bcc": bcc, "reply_to": reply, "recipients": rcpt, "subject": subject,
            "text": to_text(body) if is_html else body, "html": body if is_html else None}


def message_id(key: Optional[str], sender: str) -> str:
    domain = sender.rsplit("@", 1)[-1] if "@" in sender else "studio.local"
    return f"<{key or 'studio-' + uuid.uuid4().hex}@{domain}>"


def node_fn(node: Dict[str, Any], resolve=None, key: Callable[[], Optional[str]] = lambda: None,
            ports: Optional[Ports] = None) -> Callable[[dict], dict]:
    nid, d = node["id"], node.get("data") or {}
    ports = ports or Ports()

    def fn(state):
        m = build(nid, d, state)
        cred = None
        if d.get("credential_id") and not ports.test:  # a test run never sends (DEC-0044)
            if resolve is None: raise AppError("EMAIL_CREDENTIAL_INVALID", node=nid)
            cred = resolve(d["credential_id"])
        head = {"to": m["to"], "cc": m["cc"], "bcc": m["bcc"], "subject": m["subject"]}
        if cred is None:  # dry run (no credential, or a test run): show what would have been sent
            res = {"sent": False, "dry_run": True, **head, "message_id": None,
                   "preview": m["text"][:PREVIEW] + ("…" if len(m["text"]) > PREVIEW else "")}
        else:
            p = providers.get(cred.get("provider") or "")
            if not isinstance(p, providers.Smtp): raise AppError("EMAIL_CREDENTIAL_INVALID", node=nid)
            s = p.smtp_settings(cred)
            if ports.email_quota is not None: ports.email_quota(len(m["recipients"]))
            mid = message_id(key(), s["sender"] or "")
            msg = smtp.message(s, m["to"], m["subject"], m["text"], m["html"], m["cc"], m["reply_to"], mid)
            refused = smtp.deliver(s, msg, m["recipients"])
            res = {"sent": True, "dry_run": False, **head, "message_id": mid, "refused": refused}
        return {d["output_field"]: res} if d.get("output_field") else {}
    return fn


def errors(nid: str, d: Dict[str, Any], schema: List[dict]) -> List[str]:
    errs: List[str] = []
    static: List[str] = []
    for k in ADDRESS_FIELDS:
        v = d.get(k) or ""
        if not isinstance(v, str): errs.append(Issue("EMAIL_FIELD_TEXT", node=nid, key=k)); continue
        if not VAR_RE.search(v):  # fixed addresses are checked now, templated ones when the node runs
            got = smtp.addresses(v)
            if (bad := smtp.invalid(got)): errs.append(Issue("EMAIL_ADDRESS_INVALID", node=nid, address=bad[0][:100], key=k))
            if k != "reply_to": static += got
    if not any((d.get(k) or "").strip() for k in ("to", "cc", "bcc") if isinstance(d.get(k) or "", str)): errs.append(Issue("EMAIL_RECIPIENT_MISSING", node=nid))
    if len(set(static)) > MAX_RECIPIENTS: errs.append(Issue("EMAIL_RECIPIENTS_MANY", node=nid, max=MAX_RECIPIENTS))
    if not str(d.get("subject") or "").strip(): errs.append(Issue("EMAIL_SUBJECT_EMPTY", node=nid))
    if not str(d.get("body") or "").strip(): errs.append(Issue("EMAIL_BODY_EMPTY", node=nid))
    if d.get("format", "text") not in FORMATS: errs.append(Issue("EMAIL_FORMAT", node=nid))
    if d.get("retry") or d.get("cache_ttl") is not None:  # a retry after the server took the message, or a cache hit, would be wrong
        errs.append(Issue("EMAIL_NO_RETRY", node=nid))
    of = d.get("output_field")
    if of and schema:
        f = {x["name"]: x for x in schema}.get(of)
        if f is None: errs.append(Issue("EMAIL_OUTPUT_UNKNOWN", node=nid, field=of))
        elif f.get("type", "string") != "object": errs.append(Issue("EMAIL_OUTPUT_TYPE", node=nid, field=of))
    return errs
