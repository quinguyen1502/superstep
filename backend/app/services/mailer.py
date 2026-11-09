"""System e-mail (notifications, approval links, password reset; ) through the studio's SMTP settings
(`config.smtp`). Delivery itself is core/smtp.py, shared with Send email nodes."""
from typing import Optional
from ..core import smtp as mail
from ..core.errors import AppError
from ..core.logging import get_logger

log = get_logger("mail")


def send(smtp: dict, to: str, subject: str, text: str, html: Optional[str] = None) -> bool:
    """Send one message; False (logged, no exception) when the server refuses or is unreachable."""
    try:
        mail.deliver(smtp, mail.message(smtp, [to], subject, text, html), [to]); return True
    except AppError as e:
        log.warning("e-mail failed: %s", e.code); return False
