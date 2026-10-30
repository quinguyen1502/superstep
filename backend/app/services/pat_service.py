"""Personal access tokens and the browser sign-in `superstep login` polls (TASK-0167, DEC-0071)."""
import hashlib, secrets, time, uuid
from typing import Optional
from ..core import config
from ..core.errors import AppError
from ..models import CliDevice, PersonalAccessToken
from ..repositories import CliDeviceRepository, PersonalAccessTokenRepository, UserRepository

PAT_PREFIX = "pat_"
DEVICE_TTL = 600
POLL_INTERVAL = 1
NAME_MAX = 80
DEFAULT_NAME = "CLI"


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class PatService:
    def __init__(self, pats: PersonalAccessTokenRepository, devices: CliDeviceRepository, users: UserRepository):
        self.pats, self.devices, self.users = pats, devices, users

    def _name(self, name: Optional[str], *, required: bool) -> str:
        cleaned = (name or "").strip()
        if not cleaned:
            if required: raise AppError("BAD_REQUEST")
            return ""
        if len(cleaned) > NAME_MAX: raise AppError("BAD_REQUEST")
        return cleaned

    def _issue(self, user_id: str, name: str) -> tuple[PersonalAccessToken, str]:
        if self.users.get_by_id(user_id) is None: raise AppError("AUTH_TOKEN_INVALID")
        if self.pats.active_by_name(user_id, name): raise AppError("PAT_NAME_TAKEN", name=name)
        secret = PAT_PREFIX + secrets.token_urlsafe(24)
        row = PersonalAccessToken(id=uuid.uuid4().hex[:12], user_id=user_id, name=name, token_hash=digest(secret),
                                   prefix=secret[:10], created=time.time(), last_used=None, revoked=None)
        return self.pats.add(row), secret

    def create(self, user_id: str, name: str) -> dict:
        row, secret = self._issue(user_id, self._name(name, required=True))
        return {"id": row.id, "name": row.name, "prefix": row.prefix, "token": secret}

    def list(self, user_id: str) -> dict:
        return {"items": [{"id": row.id, "name": row.name, "prefix": row.prefix, "created": row.created, "last_used": row.last_used}
                          for row in self.pats.list_active(user_id)]}

    def revoke(self, user_id: str, tid: str) -> dict:
        row = self.pats.get(tid)
        if row is None or row.user_id != user_id: raise AppError("PAT_NOT_FOUND")
        if row.revoked is None: self.pats.set_fields(tid, revoked=time.time())
        return {"ok": True}

    def user_for_token(self, token: str):
        """The active user for a `pat_` secret, or None when it is not one. Raises when it is a PAT and is not usable.
        Touches last_used. Does not apply password-change expiry."""
        if not token or not token.startswith(PAT_PREFIX): return None
        row = self.pats.by_hash(digest(token))
        if row is None or row.revoked is not None: raise AppError("AUTH_TOKEN_INVALID")
        user = self.users.get_by_id(row.user_id)
        if user is None: raise AppError("AUTH_TOKEN_INVALID")
        if not user.active: raise AppError("AUTH_ACCOUNT_DISABLED")
        self.pats.set_fields(row.id, last_used=time.time())
        return user

    def start_device(self, name: Optional[str] = None) -> dict:
        cleaned = self._name(name, required=False)
        device_code, user_code = secrets.token_urlsafe(32), secrets.token_hex(4)
        now = time.time()
        self.devices.add(CliDevice(id=uuid.uuid4().hex[:12], device_hash=digest(device_code), user_code_hash=digest(user_code),
                                    name=cleaned or None, user_id=None, token_id=None, status="pending", secret=None,
                                    expires=now + DEVICE_TTL, created=now))
        path = f"/cli/authorize?code={user_code}"
        base = config.public_url()
        return {"device_code": device_code, "user_code": user_code, "verification_uri": f"{base}{path}" if base else path,
                "expires_in": DEVICE_TTL, "interval": POLL_INTERVAL}

    def _device_by_user_code(self, user_code: str) -> CliDevice:
        row = self.devices.by_user_code_hash(digest(user_code or ""))
        if row is None: raise AppError("CLI_DEVICE_INVALID")
        return row

    def _fresh(self, row: CliDevice) -> CliDevice:
        """Refuse a device that is still waiting, or that holds an undelivered secret, after its deadline."""
        if row.expires >= time.time() or (row.status != "pending" and not row.secret): return row
        if row.token_id and row.secret: self.pats.set_fields(row.token_id, revoked=time.time())
        if row.secret: self.devices.set_fields(row.id, secret=None)
        raise AppError("CLI_DEVICE_EXPIRED")

    def poll(self, device_code: str) -> dict:
        row = self.devices.by_device_hash(digest(device_code or ""))
        if row is None: raise AppError("CLI_DEVICE_INVALID")
        if row.status == "denied": raise AppError("CLI_DEVICE_DENIED")
        row = self._fresh(row)
        if row.status == "pending": return {"status": "pending", "interval": POLL_INTERVAL}
        secret = self.devices.take_secret(row.id)
        if not secret: raise AppError("CLI_DEVICE_INVALID")
        return {"status": "approved", "token": secret, "interval": POLL_INTERVAL}

    def approve(self, user_id: str, user_code: str, name: Optional[str]) -> dict:
        row = self._fresh(self._device_by_user_code(user_code))
        if row.status != "pending": raise AppError("CLI_DEVICE_INVALID")
        chosen = self._name(name, required=False) or row.name or DEFAULT_NAME
        token, secret = self._issue(user_id, chosen)
        self.devices.set_fields(row.id, status="approved", user_id=user_id, token_id=token.id, secret=secret, name=chosen)
        return {"ok": True, "name": chosen}

    def deny(self, user_code: str) -> dict:
        row = self._fresh(self._device_by_user_code(user_code))
        if row.status != "pending": raise AppError("CLI_DEVICE_INVALID")
        self.devices.set_fields(row.id, status="denied", secret=None)
        return {"ok": True}
