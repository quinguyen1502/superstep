"""Break-glass admin accounts for `python -m app.admin_cmd`. No HTTP."""
import secrets
import time
import uuid

from ..core import security
from ..core.errors import AppError
from ..repositories import UserRepository
from .auth_service import EMAIL_RE, normalise_email


class AdminAccountService:
    def __init__(self, users: UserRepository):
        self.users = users

    def create(self, email: str, password: str | None = None) -> str:
        """Insert an admin, or promote and reset an existing address. Returns the password."""
        address = _email(email)
        pw = _password(password)
        existing = self.users.get_by_email(address)
        hashed = security.hash_password(pw)
        if existing is None:
            uid = uuid.uuid4().hex[:10]
            self.users.add(uid, address, hashed, time.time())
            self.users.set_admin(uid)
            return pw
        self.users.set_password(existing.id, hashed, time.time())
        self.users.set_admin(existing.id)
        self.users.set_active(existing.id, True)
        return pw

    def reset_password(self, email: str, password: str | None = None) -> str:
        address = _email(email)
        user = self.users.get_by_email(address)
        if user is None:
            raise AppError("USER_NOT_FOUND")
        pw = _password(password)
        self.users.set_password(user.id, security.hash_password(pw), time.time())
        return pw

    def list_admins(self) -> list[tuple[str, str]]:
        """(email, role) for admins. No hash."""
        rows = []
        for user, _count in self.users.list_all():
            email = user.email or ""
            if user.role != "admin" or not email or email.endswith("@deleted.invalid"):
                continue
            rows.append((email, user.role))
        return rows


def _email(email: str) -> str:
    address = normalise_email(email or "")
    if not EMAIL_RE.match(address):
        raise AppError("AUTH_EMAIL_INVALID")
    return address


def _password(given: str | None) -> str:
    if given is not None:
        if (err := security.password_problem(given)):
            raise err
        return given
    while security.password_problem(pw := secrets.token_urlsafe(15)):
        pass
    return pw
