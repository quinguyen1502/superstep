from typing import Optional
from sqlalchemy import delete, update
from ..models import LoginThrottle, PasswordReset, User
from ..models.database import Database


class AuthSecurityRepository:
    """Sign-in throttling and password reset links."""
    def __init__(self, db: Database): self.db = db

    def throttle(self, email: str) -> Optional[LoginThrottle]:
        with self.db.session() as s: return s.get(LoginThrottle, email)

    def record_failure(self, email: str, now: float, window: float, max_failures: int, lock: float) -> LoginThrottle:
        """Count one failure in the current window; at `max_failures`, lock until now + lock."""
        with self.db.session() as s:
            t = s.get(LoginThrottle, email)
            if t is None or now - t.first_at > window: t = s.merge(LoginThrottle(email=email, failures=0, first_at=now, locked_until=None))
            t.failures += 1
            if t.failures >= max_failures: t.locked_until = now + lock; t.failures = 0; t.first_at = now
            s.commit(); s.refresh(t); return t

    def clear_throttle(self, email: str) -> None:
        with self.db.session() as s: s.execute(delete(LoginThrottle).where(LoginThrottle.email == email)); s.commit()

    def prune_throttle(self, before: float) -> None:
        """Drop rows whose window and lock both ended before `before`."""
        with self.db.session() as s:
            s.execute(delete(LoginThrottle).where(LoginThrottle.first_at < before, (LoginThrottle.locked_until.is_(None)) | (LoginThrottle.locked_until < before)))
            s.commit()

    def add_reset(self, r: PasswordReset) -> None:
        with self.db.session() as s: s.add(r); s.commit()

    def reset(self, rid: str) -> Optional[PasswordReset]:
        with self.db.session() as s: return s.get(PasswordReset, rid)

    def use_reset(self, rid: str, uid: str, password_hash: str, now: float) -> bool:
        """Mark the link used and set the password in one transaction; False if it was already used."""
        with self.db.session() as s:
            n = s.execute(update(PasswordReset).where(PasswordReset.id == rid, PasswordReset.used.is_(None)).values(used=now)).rowcount
            if not n: s.rollback(); return False
            s.execute(update(User).where(User.id == uid).values(password=password_hash, password_changed=now))
            s.execute(delete(PasswordReset).where(PasswordReset.user_id == uid, PasswordReset.used.is_(None)))  # other open links die too
            s.commit(); return True

    def set_password(self, uid: str, password_hash: str, now: float) -> None:
        """A self-service change: older sessions stop working and open reset links die."""
        with self.db.session() as s:
            s.execute(update(User).where(User.id == uid).values(password=password_hash, password_changed=now))
            s.execute(delete(PasswordReset).where(PasswordReset.user_id == uid, PasswordReset.used.is_(None)))
            s.commit()

    def prune_resets(self, before: float) -> None:
        with self.db.session() as s: s.execute(delete(PasswordReset).where(PasswordReset.expires < before)); s.commit()
