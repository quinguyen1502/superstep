"""Registration, login and token → user resolution (with the user's role, TASK-0014).

TASK-0045: failed sign-ins lock an e-mail for a while, password reset links (admin-made, or e-mailed when SMTP is set),
and tokens issued before the last password change stop working."""
import hashlib, html, math, re, secrets, threading, time, uuid
from typing import Callable, Optional
from ..core import config, security
from ..core import permissions as P
from ..core.errors import AppError
from ..core.logging import get_logger
from ..models import PasswordReset
from ..repositories import AuthSecurityRepository, UserRepository
from . import demo_service
from . import mailer

log = get_logger("auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalise_email(email: str) -> str:
    return email.strip().lower()


def public_user(u) -> dict:
    return {"id": u.id, "email": u.email, "role": u.role, "permissions": sorted(P.PERMISSIONS.get(u.role, ())),
            "is_admin": u.role == "admin", "created": u.created}


def _digest(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, users: UserRepository, workflows=None, sec: Optional[AuthSecurityRepository] = None, background: bool = True, audit=None,
                 visit: Optional[Callable[[], str]] = None):
        # workflows: WorkflowService (seeds the example for new users); sec: lockout + reset links (None: neither)
        # visit: demo mode, a fresh visitor account for each "Try the demo" sign-in (demo_service.start_visit)
        self.users, self.workflows, self.sec, self.background, self.audit, self.visit = users, workflows, sec, background, audit, visit

    def _session(self, uid: str) -> dict:
        u = self.users.get_by_id(uid); token = security.make_token(uid, u.email)
        return {"token": token, "expires_at": security.decode_token(token)["exp"], "user": public_user(u)}

    def register(self, email: str, password: str) -> dict:
        email = normalise_email(email)
        if not EMAIL_RE.match(email) or len(email) > 254: raise AppError("AUTH_EMAIL_INVALID")
        if (err := security.password_problem(password)): raise err
        if self.users.get_by_email(email): raise AppError("AUTH_EMAIL_TAKEN")
        uid = uuid.uuid4().hex[:10]
        self.users.add(uid, email, security.hash_password(password), time.time())
        # STUDIO_ADMIN_EMAILS bootstraps admins at sign-up; everyone else gets STUDIO_DEFAULT_ROLE (editor)
        self.users.set_role(uid, "admin" if email in config.admin_emails() else config.default_role())
        if self.workflows is not None and P.can(self.users.get_by_id(uid).role, P.WORKFLOWS_CREATE):
            self.workflows.seed_example(uid)  # new users get a copy of the example workflow
        return self._session(uid)

    def _check_password(self, email: str, password: str, wrong: str):
        """The user if `password` is right. A lock refuses even the right password; a wrong one counts toward it
        (sign-in and password change share the counter, TASK-0045/0052) and raises `wrong`."""
        now = time.time()
        if self.sec and (t := self.sec.throttle(email)) and t.locked_until and t.locked_until > now:
            raise AppError("AUTH_LOCKED", minutes=math.ceil((t.locked_until - now) / 60))
        u = self.users.get_by_email(email)
        if not u or not security.verify_password(password, u.password or ""):
            if self.sec:
                t = self.sec.record_failure(email, now, config.login_window(), config.login_max_failures(), config.login_lock())
                self.sec.prune_throttle(now - config.login_window() - config.login_lock())
                if t.locked_until and t.locked_until > now: raise AppError("AUTH_LOCKED", minutes=math.ceil(config.login_lock() / 60))
            raise AppError(wrong)
        if self.sec: self.sec.clear_throttle(email)
        return u

    def login(self, email: str, password: str) -> dict:
        u = self._check_password(normalise_email(email), password, "AUTH_INVALID_CREDENTIALS")  # generic: no user enumeration
        if not u.active: raise AppError("AUTH_ACCOUNT_DISABLED")
        if u.id == demo_service.VISITOR_ID and self.visit is not None and config.demo_mode(): return self._session(self.visit())  # per-visitor history
        return self._session(u.id)

    def change_password(self, uid: str, current: str, new: str) -> dict:
        """TASK-0052: needs the current password. Other sessions stop working; the caller gets a fresh one."""
        me = self.users.get_by_id(uid)
        if me is None: raise AppError("AUTH_TOKEN_INVALID")
        u = self._check_password(me.email, current, "AUTH_PASSWORD_WRONG")
        if (err := security.password_problem(new)): raise err
        if security.verify_password(new, u.password or ""): raise AppError("AUTH_PASSWORD_SAME")
        self.sec.set_password(uid, security.hash_password(new), time.time())
        log.info("password changed by user %s", uid)
        if self.audit: self.audit.record(uid, "user.password_changed", "user", uid, u.email)
        return self._session(uid)

    # ---- password reset (TASK-0045) ----
    def options(self) -> dict:
        """What the sign-in page offers: the demo hint, and whether "forgot password" sends e-mail or says to ask an admin."""
        return {"demo": config.demo_user(), "reset": "email" if config.smtp() and config.public_url() else "admin",
                **({"demo_mode": demo_service.options()} if config.demo_mode() else {})}

    def _new_reset(self, uid: str, by: str) -> str:
        token = secrets.token_urlsafe(32); now = time.time()
        self.sec.prune_resets(now)
        self.sec.add_reset(PasswordReset(id=_digest(token), user_id=uid, created=now, expires=now + config.password_reset_ttl(), created_by=by))
        return token

    def admin_reset_link(self, admin_id: str, uid: str) -> dict:
        """`path` for the UI to put on its own origin; `url` too when STUDIO_PUBLIC_URL is set (behind a proxy the API cannot tell the page's origin)."""
        u = self.users.get_by_id(uid)
        if u is None: raise AppError("USER_NOT_FOUND")
        token = self._new_reset(uid, admin_id)
        if self.audit: self.audit.record(admin_id, "user.password_reset_link", "user", uid, u.email)
        path = f"/reset-password?token={token}"
        return {"path": path, "url": f"{config.public_url()}{path}" if config.public_url() else None, "expires_in": config.password_reset_ttl()}

    def request_reset(self, email: str) -> dict:
        """Always the same answer, so it cannot tell who has an account. Sends the link only when SMTP is configured."""
        opts = self.options()
        u = self.users.get_by_email(normalise_email(email))
        if opts["reset"] == "email" and u is not None and u.active:
            url = f"{config.public_url()}/reset-password?token={self._new_reset(u.id, 'self')}"
            minutes = config.password_reset_ttl() // 60
            text = f"Someone asked to reset the password of {u.email} on Superstep.\n\nOpen this link within {minutes} minutes to choose a new one:\n{url}\n\nIf it was not you, ignore this e-mail."
            body = f"<p>Someone asked to reset the password of {html.escape(u.email)} on Superstep.</p><p><a href=\"{html.escape(url)}\">Choose a new password</a> (valid for {minutes} minutes).</p><p>If it was not you, ignore this e-mail.</p>"
            send = lambda: mailer.send(config.smtp(), u.email, "[Superstep] Reset your password", text, body)
            threading.Thread(target=send, daemon=True).start() if self.background else send()
        return {"reset": opts["reset"]}

    def confirm_reset(self, token: str, password: str) -> dict:
        r = self.sec.reset(_digest(token or ""))
        if r is None or r.used is not None or r.expires < time.time(): raise AppError("PASSWORD_RESET_INVALID")
        if (err := security.password_problem(password)): raise err
        u = self.users.get_by_id(r.user_id)
        if u is None or not u.active: raise AppError("PASSWORD_RESET_INVALID")
        if not self.sec.use_reset(r.id, u.id, security.hash_password(password), time.time()): raise AppError("PASSWORD_RESET_INVALID")
        self.sec.clear_throttle(u.email)
        log.info("password reset for user %s (link by %s)", u.id, r.created_by)
        if self.audit: self.audit.record(u.id, "user.password_reset", "user", u.id, u.email, link_by=r.created_by)
        return {"email": u.email}

    @staticmethod
    def user_from_token(token: str | None) -> dict:
        """Signature check only (no database): {id, email}. Use `current` for requests."""
        if not token: raise AppError("AUTH_REQUIRED")
        p = security.decode_token(token)
        return {"id": p["sub"], "email": p["email"]}

    def current(self, token: str | None) -> dict:
        """The signed-in user, checked against the database: deleted or deactivated accounts lose access at once."""
        uid = self.user_from_token(token)["id"]
        u = self.users.get_by_id(uid)
        if u is None: raise AppError("AUTH_TOKEN_INVALID")
        if not u.active: raise AppError("AUTH_ACCOUNT_DISABLED")
        changed = getattr(u, "password_changed", None)
        if changed and security.decode_token(token).get("iat", 0) < int(changed): raise AppError("AUTH_TOKEN_EXPIRED", headers={"X-Auth-Error": "expired"})
        return public_user(u)
