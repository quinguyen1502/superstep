"""SMTP delivery shared by system e-mail (services/mailer.py) and Send email nodes (engine/emails.py; ).

Settings: {host, port, security, username, password, sender, allow_private, tls_optional}.
- `security`: "starttls" (upgrade before login, required unless `tls_optional`), "ssl" (TLS from the first byte) or "none".
- SSRF guard: the host is resolved once and every address is checked (core/net.blocked) unless `allow_private`; the
  connection goes to that pinned IP while TLS still verifies the certificate against the host name.
Errors raise AppError: EMAIL_HOST_BLOCKED, EMAIL_AUTH_FAILED, EMAIL_SEND_FAILED (with a short reason, never the password).
"""
from __future__ import annotations
import ipaddress, re, smtplib, socket, ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from typing import Any, Dict, Iterable, List, Optional
from .errors import AppError
from .net import blocked

SECURITY = ("starttls", "ssl", "none")
TIMEOUT = 20
ADDRESS_RE = re.compile(r"^[^@\s<>,;\"]+@[^@\s<>,;\"]+\.[^@\s<>,;\"]+$")


def addresses(value: Any) -> List[str]:
    """`a@x.io, B <b@y.io>; c@z.io` or a list of them -> bare addresses (empty parts dropped). A part that is not an
    address is kept as it is so `invalid()` can name it."""
    items = value if isinstance(value, list) else [value]
    parts = [p.strip() for x in items if x not in (None, "") for p in re.split(r"[,;\n]", str(x)) if p.strip()]
    return [a.strip() if ADDRESS_RE.match((a := parseaddr(p)[1]).strip()) else p for p in parts]


def invalid(addrs: Iterable[str]) -> List[str]:
    return [a for a in addrs if not ADDRESS_RE.match(a)]


def sender(s: Dict[str, Any]) -> str:
    return formataddr((s.get("from_name") or "", s["sender"])) if s.get("from_name") else s["sender"]


def message(s: Dict[str, Any], to: List[str], subject: str, text: str, html: Optional[str] = None, cc: Iterable[str] = (),
            reply_to: Iterable[str] = (), message_id: Optional[str] = None) -> EmailMessage:
    """Plain text, or multipart/alternative (text + HTML). Bcc never goes into the headers."""
    msg = EmailMessage(); msg["From"] = sender(s); msg["To"] = ", ".join(to)
    if cc: msg["Cc"] = ", ".join(cc)
    if reply_to: msg["Reply-To"] = ", ".join(reply_to)
    msg["Subject"] = " ".join(subject.split())  # no CR/LF: a header can never be injected
    if message_id: msg["Message-ID"] = message_id
    msg.set_content(text)
    if html: msg.add_alternative(html, subtype="html")
    return msg


def _pin(host: str, port: int, allow_private: bool) -> str:
    try: addrs = [ai[4][0].split("%")[0] for ai in socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)]
    except (OSError, UnicodeError, ValueError): raise AppError("EMAIL_SEND_FAILED", reason=f"cannot resolve {host}") from None
    if not addrs: raise AppError("EMAIL_SEND_FAILED", reason=f"cannot resolve {host}")
    if not allow_private and any(blocked(ipaddress.ip_address(a)) for a in addrs): raise AppError("EMAIL_HOST_BLOCKED", host=host)
    return addrs[0]


class _Pinned(smtplib.SMTP):
    """Connects to the checked IP; `_host` stays the name, so STARTTLS verifies the certificate for it."""
    def __init__(self, ip: str, **kw):
        self._ip = ip; super().__init__(**kw)

    def _get_socket(self, host, port, timeout):
        return socket.create_connection((self._ip, port), timeout, self.source_address)


class _PinnedSSL(smtplib.SMTP_SSL):
    def __init__(self, ip: str, **kw):
        self._ip = ip; super().__init__(**kw)

    def _get_socket(self, host, port, timeout):
        sock = socket.create_connection((self._ip, port), timeout, self.source_address)
        return self.context.wrap_socket(sock, server_hostname=host)


def _reason(e: Exception) -> str:
    if isinstance(e, smtplib.SMTPResponseException):
        text = e.smtp_error.decode(errors="replace") if isinstance(e.smtp_error, bytes) else str(e.smtp_error)
        return f"{e.smtp_code} {' '.join(text.split())}"[:200]
    if isinstance(e, smtplib.SMTPRecipientsRefused): return "every recipient was refused"
    return type(e).__name__ if not str(e) else f"{type(e).__name__}: {e}"[:200]


def _login(conn: smtplib.SMTP, user: str, password: str) -> None:
    """One mechanism (PLAIN, else LOGIN, else CRAM-MD5): smtplib's login() tries the next one after a refusal,
    which some servers answer by hanging until the timeout."""
    conn.ehlo_or_helo_if_needed()
    offered = (conn.esmtp_features.get("auth") or "").upper().split()
    mech = next((m for m in ("PLAIN", "LOGIN", "CRAM-MD5") if m in offered), None)
    if mech is None: return conn.login(user, password)  # raises SMTPNotSupportedError when AUTH is not offered
    conn.user, conn.password = user, password
    conn.auth(mech, getattr(conn, "auth_" + mech.lower().replace("-", "_")))


def _session(s: Dict[str, Any]) -> smtplib.SMTP:
    host, port, sec = s["host"], int(s["port"]), s.get("security") or "starttls"
    ip = _pin(host, port, bool(s.get("allow_private")))
    try:
        conn = _PinnedSSL(ip, timeout=TIMEOUT, context=ssl.create_default_context()) if sec == "ssl" else _Pinned(ip, timeout=TIMEOUT)
        conn.connect(host, port)
        if sec == "starttls":
            conn.ehlo()
            if conn.has_extn("starttls"): conn.starttls(context=ssl.create_default_context()); conn.ehlo()
            elif not s.get("tls_optional"): conn.close(); raise AppError("EMAIL_SEND_FAILED", reason="the server does not offer STARTTLS")
        if s.get("username"):
            try: _login(conn, s["username"], s.get("password") or "")
            except smtplib.SMTPAuthenticationError as e: conn.close(); raise AppError("EMAIL_AUTH_FAILED", reason=_reason(e)) from None
        return conn
    except AppError: raise
    except (OSError, smtplib.SMTPException) as e: raise AppError("EMAIL_SEND_FAILED", reason=_reason(e)) from None


def check(s: Dict[str, Any]) -> None:
    """Connect, upgrade to TLS and sign in, then quit: proves the settings work without sending anything."""
    conn = _session(s)
    try: conn.quit()
    except (OSError, smtplib.SMTPException): pass


def deliver(s: Dict[str, Any], msg: EmailMessage, recipients: List[str]) -> List[str]:
    """Send to every recipient (To + Cc + Bcc); returns the refused ones. Raises when nobody accepted it."""
    conn = _session(s)
    try:
        refused = conn.send_message(msg, from_addr=s["sender"], to_addrs=recipients)
    except (OSError, smtplib.SMTPException) as e: raise AppError("EMAIL_SEND_FAILED", reason=_reason(e)) from None
    finally:
        try: conn.quit()
        except (OSError, smtplib.SMTPException): pass
    return sorted(refused)
