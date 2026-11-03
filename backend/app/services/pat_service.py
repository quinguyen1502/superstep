"""Personal access tokens and the browser sign-in `superstep login` polls (TASK-0167, DEC-0071)."""
import asyncio, hashlib, secrets, time, uuid
from typing import Optional
from ..core import config
from ..core.errors import AppError
from ..models import CliDevice, PersonalAccessToken
from ..repositories import CliDeviceRepository, PersonalAccessTokenRepository, UserRepository
from ..repositories.personal_access_tokens import PatNameTaken

PAT_PREFIX = "pat_"
DEVICE_TTL = 600
POLL_INTERVAL = 1
NAME_MAX = 80
DEFAULT_NAME = "CLI"
DEVICE_STARTS, DEVICE_WINDOW = 10, 600  # sign-ins started per client IP per 10 minutes (TASK-0205)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class PatService:
    def __init__(self, pats: PersonalAccessTokenRepository, devices: CliDeviceRepository, users: UserRepository, limiter=None):
        self.pats, self.devices, self.users, self.limiter = pats, devices, users, limiter

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
        try: return self.pats.add(row), secret
        except PatNameTaken: raise AppError("PAT_NAME_TAKEN", name=name) from None  # lost a race to a create with the same name (TASK-0213)

    def _free_name(self, user_id: str, name: str) -> str:
        """`name`, or `name (2)`, `name (3)`... when a token with that name was created after approval (TASK-0208, DEC-0076)."""
        chosen, n = name, 1
        while self.pats.active_by_name(user_id, chosen):
            n += 1; suffix = f" ({n})"
            chosen = name[:NAME_MAX - len(suffix)] + suffix
        return chosen

    def _issue_free(self, user_id: str, name: str, attempts: int = 20) -> tuple[PersonalAccessToken, str]:
        """_issue with a free name; a create that takes the chosen name at the same moment moves on to the next (TASK-0213)."""
        for _ in range(attempts - 1):
            try: return self._issue(user_id, self._free_name(user_id, name))
            except AppError as exc:
                if exc.code != "PAT_NAME_TAKEN": raise
        return self._issue(user_id, self._free_name(user_id, name))

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

    async def start_device_from(self, ip: str, name: Optional[str] = None) -> dict:
        """start_device for an unauthenticated caller: limited per client IP, so the table cannot be flooded (TASK-0205)."""
        if self.limiter is not None:
            ok, retry = await self.limiter.hit(f"cli-device:{ip}", DEVICE_STARTS, DEVICE_WINDOW)
            if not ok: raise AppError("RATE_LIMITED", headers={"Retry-After": str(retry)}, retry_after=retry)
        return await asyncio.to_thread(self.start_device, name)

    def start_device(self, name: Optional[str] = None) -> dict:
        cleaned = self._name(name, required=False)
        device_code, user_code = secrets.token_urlsafe(32), secrets.token_hex(4)
        now = time.time()
        for old in self.devices.expired_secrets(now): self._drop_secret(old)  # a token never collected is revoked (TASK-0207)
        self.devices.delete_expired(now - DEVICE_TTL)  # sign-ins that ended long ago are kept no longer (TASK-0205)
        self.devices.add(CliDevice(id=uuid.uuid4().hex[:12], device_hash=digest(device_code), user_code_hash=digest(user_code),
                                    name=cleaned or None, user_id=None, token_id=None, status="pending", secret=None,
                                    expires=now + DEVICE_TTL, created=now))
        path = "/cli/authorize"  # without the code: the person types the code their own terminal shows (TASK-0205, DEC-0076)
        base = config.public_url()
        return {"device_code": device_code, "user_code": user_code, "verification_uri": f"{base}{path}" if base else path,
                "expires_in": DEVICE_TTL, "interval": POLL_INTERVAL}

    def _device_by_user_code(self, user_code: str) -> CliDevice:
        row = self.devices.by_user_code_hash(digest(user_code or ""))
        if row is None: raise AppError("CLI_DEVICE_INVALID")
        return row

    def _drop_secret(self, row: CliDevice) -> None:
        if row.token_id: self.pats.set_fields(row.token_id, revoked=time.time())
        self.devices.set_fields(row.id, secret=None)

    @staticmethod
    def _collected(row: CliDevice) -> bool:
        """The CLI already has its token: delivered, or (before TASK-0207) approved with the secret already taken."""
        return row.status == "delivered" or (row.status == "approved" and bool(row.token_id) and not row.secret)

    def _fresh(self, row: CliDevice) -> CliDevice:
        """Refuse a device that is still waiting, or approved and not yet collected, after its deadline."""
        if row.expires >= time.time() or self._collected(row) or row.status == "denied": return row
        if row.secret: self._drop_secret(row)
        raise AppError("CLI_DEVICE_EXPIRED")

    def poll(self, device_code: str) -> dict:
        row = self.devices.by_device_hash(digest(device_code or ""))
        if row is None: raise AppError("CLI_DEVICE_INVALID")
        if row.status == "denied": raise AppError("CLI_DEVICE_DENIED")
        row = self._fresh(row)
        if row.status == "pending": return {"status": "pending", "interval": POLL_INTERVAL}
        if row.secret:  # approved before TASK-0207: the secret was stored
            secret = self.devices.take_secret(row.id)
            if not secret: raise AppError("CLI_DEVICE_INVALID")
            return {"status": "approved", "token": secret, "interval": POLL_INTERVAL}
        if self._collected(row) or not self.devices.claim(row.id, "approved", "delivered"): raise AppError("CLI_DEVICE_INVALID")
        token, secret = self._issue_free(row.user_id, row.name or DEFAULT_NAME)  # minted now: no token waits in the table (TASK-0207)
        self.devices.set_fields(row.id, token_id=token.id)
        return {"status": "approved", "token": secret, "interval": POLL_INTERVAL}

    def approve(self, user_id: str, user_code: str, name: Optional[str]) -> dict:
        row = self._fresh(self._device_by_user_code(user_code))
        if row.status != "pending": raise AppError("CLI_DEVICE_INVALID")
        chosen = self._name(name, required=False) or row.name or DEFAULT_NAME
        if self.users.get_by_id(user_id) is None: raise AppError("AUTH_TOKEN_INVALID")
        if self.pats.active_by_name(user_id, chosen): raise AppError("PAT_NAME_TAKEN", name=chosen)
        if not self.devices.claim(row.id, "pending", "approved", user_id=user_id, name=chosen): raise AppError("CLI_DEVICE_INVALID")
        # the token is minted when the CLI collects it, so none waits in the table (TASK-0207)
        return {"ok": True, "name": chosen}

    def deny(self, user_code: str) -> dict:
        row = self._fresh(self._device_by_user_code(user_code))
        if row.status != "pending": raise AppError("CLI_DEVICE_INVALID")
        self.devices.set_fields(row.id, status="denied", secret=None)
        return {"ok": True}
