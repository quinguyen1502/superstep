"""Notifications for runs that need a human (TASK-0020, DEC-0017).

Always: an in-app row (bell in the header, mark read).
Optional channels, each a no-op unless configured:
- E-mail via SMTP (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_STARTTLS / SMTP_SSL).
- A generic notify webhook (STUDIO_NOTIFY_WEBHOOK_URL, signed with STUDIO_NOTIFY_WEBHOOK_SECRET when set; same
  SSRF guard, DNS pinning and signature format as result webhooks).
External channels run in a background thread so recording a run never waits on SMTP/HTTP.
TASK-0021: new in-app notifications are pushed live (NotificationHub -> WebSocket /ws/notifications); e-mail is
multipart (plain text + HTML template); per-user preferences switch the in-app and e-mail channels off/on.
"""
import html, json, threading, time, uuid
from typing import Optional
from ..core import config
from ..core.errors import AppError
from ..core.logging import get_logger
from ..models import Notification
from ..repositories import NotificationRepository, UserRepository, WorkflowRepository
from . import mailer, webhooks
from .approval_channels.messages import LANGS, lang_of

log = get_logger("notify")
KINDS = {"run_waiting": "A run is waiting for your response", "run_expired": "A waiting run expired",
         "run_reminder": "A run is still waiting for your response", "run_escalated": "A run was handed to you for approval",  # TASK-0066
         "run_auto_answered": "AI review answered an approval for you"}  # TASK-0187


class NotificationService:
    def __init__(self, repo: NotificationRepository, users: Optional[UserRepository] = None,
                 workflows: Optional[WorkflowRepository] = None, background: bool = True, hub=None):
        self.repo, self.users, self.workflows, self.background, self.hub = repo, users, workflows, background, hub

    @staticmethod
    def public(n: Notification) -> dict:
        return {"id": n.id, "kind": n.kind, "run_id": n.run_id, "workflow_id": n.workflow_id, "title": n.title,
                "params": json.loads(n.params or "{}"), "link": n.link, "created": n.created, "read": n.read_at is not None}

    # ---- producer ----
    def run_event(self, kind: str, uid: str, run_id: str, workflow_id: Optional[str], node_event: Optional[dict] = None,
                  link: Optional[str] = None, extra: Optional[dict] = None) -> Notification:
        """link: where the notification opens (default: the run in the editor; deadline reminders open /approvals)."""
        w = self.workflows.get(workflow_id) if self.workflows and workflow_id and workflow_id != "adhoc" else None
        ev = node_event or {}
        params = {"workflow_name": w.name if w else None, "label": ev.get("label"), "prompt": ev.get("prompt"), **(extra or {})}
        link = link or (f"/workflows/{workflow_id}?run={run_id}" if workflow_id and workflow_id != "adhoc" else None)
        prefs = self.preferences(uid)
        n = Notification(id=uuid.uuid4().hex[:12], user_id=uid, kind=kind, run_id=run_id, workflow_id=workflow_id,
                         title=KINDS[kind], params=json.dumps(params, ensure_ascii=False), link=link, created=time.time())
        if prefs["in_app"]:
            n = self.repo.add(n)
            if self.hub is not None:
                try: self.hub.publish(uid, {"type": "notification", "notification": self.public(n), "unread": self.repo.unread_count(uid)})
                except Exception: log.warning("live push of notification %s failed (the bell polls as a fallback)", n.id)
        if (config.smtp() and prefs["email"]) or config.notify_webhook():
            job = lambda: self.dispatch(n, email=prefs["email"])  # noqa: E731
            threading.Thread(target=job, daemon=True).start() if self.background else job()
        return n

    def dispatch(self, n: Notification, email: bool = True) -> dict:
        """Send to the configured external channels. Never raises. Returns {channel: ok} (for tests/logs)."""
        out = {}
        if email and (smtp := config.smtp()):
            u = self.users.get_by_id(n.user_id) if self.users else None
            if u: out["email"] = self._email(smtp, u.email, n)
        if (hook := config.notify_webhook()):
            url, secret = hook
            out["webhook"] = webhooks.post(url, {"event": "notification.created", "user_id": n.user_id, **self.public(n)},
                                           [secret] if secret else None, "notification.created").ok
        return out

    @staticmethod
    def _email(smtp: dict, to: str, n: Notification) -> bool:
        p = json.loads(n.params or "{}")
        subject = f"[Superstep] {n.title}" + (f": {p['workflow_name']}" if p.get("workflow_name") else "")
        return mailer.send(smtp, to, subject, email_text(n, p), email_html(n, p))

    # ---- owner API ----
    def list(self, uid: str, unread_only: bool = False) -> dict:
        return {"items": [self.public(n) for n in self.repo.list_for_user(uid, unread_only=unread_only)], "unread": self.repo.unread_count(uid)}

    def mark_read(self, uid: str, nid: str) -> dict:
        n = self.repo.get(nid)
        if n is None or n.user_id != uid: raise AppError("NOTIFICATION_NOT_FOUND")
        self.repo.mark_read(uid, nid); return {"ok": True, "unread": self.repo.unread_count(uid)}

    def mark_all_read(self, uid: str) -> dict:
        self.repo.mark_read(uid); return {"ok": True, "unread": 0}

    # ---- preferences (TASK-0021) ----
    def preferences(self, uid: str) -> dict:
        u = self.users.get_by_id(uid) if self.users else None
        return {"in_app": True if u is None or u.notify_in_app is None else bool(u.notify_in_app),
                "email": True if u is None or u.notify_email is None else bool(u.notify_email),
                "email_configured": bool(config.smtp()), "lang": lang_of(u)}

    def set_preferences(self, uid: str, body) -> dict:
        """{in_app?: bool, email?: bool, lang?: "en" | "vi"} (lang: chat messages, from the studio's language switcher)."""
        ok = lambda k, v: (k in ("in_app", "email") and isinstance(v, bool)) or (k == "lang" and v in LANGS)  # noqa: E731
        if not isinstance(body, dict) or not body or not all(ok(k, v) for k, v in body.items()): raise AppError("NOTIFICATION_PREFS_INVALID")
        self.users.set_prefs(uid, **{(k if k == "lang" else f"notify_{k}"): v for k, v in body.items()})
        return self.preferences(uid)


LABELS = {"workflow_name": "Workflow", "label": "Step", "prompt": "Question", "ai_decision": "AI review", "ai_confidence": "Confidence", "ai_reason": "Reason"}


def email_text(n: Notification, p: dict) -> str:
    lines = [n.title + "."] + [f"{LABELS[k]}: {p[k]}" for k in LABELS if p.get(k)]
    if n.link: lines.append(f"Open: {config.public_url()}{n.link}")
    return "\n".join(lines)


def email_html(n: Notification, p: dict) -> str:
    """Small inline-styled HTML e-mail (no external assets); every value is HTML-escaped."""
    e = html.escape
    rows = "".join(f'<tr><td style="padding:4px 12px 4px 0;color:#71717a">{LABELS[k]}</td><td style="padding:4px 0">{e(str(p[k]))}</td></tr>'
                   for k in LABELS if p.get(k))
    button = (f'<p style="margin:24px 0 0"><a href="{e(config.public_url() + n.link, quote=True)}" '
              'style="background:#18181b;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none;display:inline-block">Open the run</a></p>') if n.link else ""
    return ('<!doctype html><html><body style="margin:0;padding:24px;background:#f4f4f5;font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#18181b">'
            '<table role="presentation" style="max-width:560px;margin:0 auto;background:#fff;border:1px solid #e4e4e7;border-radius:12px;padding:24px;width:100%">'
            f'<tr><td><p style="margin:0 0 4px;font-size:12px;color:#71717a">Superstep</p><h1 style="margin:0 0 16px;font-size:18px">{e(n.title)}</h1>'
            f'<table role="presentation" style="font-size:14px;border-collapse:collapse">{rows}</table>{button}'
            '<p style="margin:24px 0 0;font-size:12px;color:#a1a1aa">You can turn these e-mails off in Notification settings.</p></td></tr></table></body></html>')
