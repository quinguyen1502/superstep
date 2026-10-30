"""Startup bootstrap: migrate the schema, seed the demo user (not in production, TASK-0045) and the shared example workflow."""
import os, secrets, time, uuid
from ..core import config, security
from ..core.logging import get_logger
from ..models.database import Database
from ..repositories import UserRepository, WorkflowRepository, RunRepository, WorkflowVersionRepository
from . import demo_service
from .workflow_service import WorkflowService

log = get_logger("seed")


def _admin_password() -> tuple[str, bool]:
    """(password, generated). STUDIO_ADMIN_PASSWORD when set (it must pass the password policy), else a random one."""
    if pw := os.environ.get("STUDIO_ADMIN_PASSWORD"):
        if (err := security.password_problem(pw)): raise RuntimeError(f"STUDIO_ADMIN_PASSWORD is rejected: {err.code}")
        return pw, False
    while security.password_problem(pw := secrets.token_urlsafe(15)): pass  # needs a letter and a digit
    return pw, True


def create_admin(users: UserRepository, email: str) -> None:
    """PaaS bootstrap (no demo user in production): create the first STUDIO_ADMIN_EMAILS account at start-up, so
    nobody can claim the address by signing up first. A generated password is logged once, never stored in clear."""
    pw, generated = _admin_password()
    uid = uuid.uuid4().hex[:10]
    users.add(uid, email, security.hash_password(pw), time.time()); users.set_admin(uid)
    if generated: log.warning("Created the admin account %s with this one-time password (sign in and change it now): %s", email, pw)
    else: log.warning("Created the admin account %s with the password from STUDIO_ADMIN_PASSWORD.", email)


def bootstrap(db: Database, jobs=None) -> None:
    db.migrate()
    users, wfs = UserRepository(db), WorkflowRepository(db)
    u = users.get_by_email(config.DEMO_EMAIL)
    uid = u.id if u else "admin"
    if not u and config.demo_user():  # TASK-0045: no account with a published password in production
        users.add(uid, config.DEMO_EMAIL, security.hash_password(config.DEMO_PASSWORD), time.time())
        users.set_admin(uid)  # the first account administers the studio
    elif u and not config.demo_user() and u.active and security.verify_password(config.DEMO_PASSWORD, u.password or ""):
        users.set_active(u.id, False)
        log.error("%s still has the demo password; it is deactivated in production. Set STUDIO_ADMIN_EMAILS to bootstrap an admin.", config.DEMO_EMAIL)
    if users.count_active_admins() == 0:  # bootstrap / lockout recovery only (TASK-0014): roles are managed in Settings → Users
        for email in config.admin_emails():  # STUDIO_ADMIN_EMAILS
            if (a := users.get_by_email(email)) is not None: users.set_admin(a.id); users.set_active(a.id, True)
        if users.count_active_admins() == 0 and (emails := sorted(config.admin_emails())): create_admin(users, emails[0])
        if users.count_active_admins() == 0 and not config.IS_PROD: users.set_admin(uid); users.set_active(uid, True)  # dev: the demo user
    if not users.get_by_id(uid):  # production without the demo user: the oldest active admin owns legacy rows and the example
        uid = next((x.id for x, _ in users.list_all() if x.role == "admin" and x.active), None)
        if uid is None: return
    wfs.adopt_unowned(uid)  # legacy rows created before multi-user support
    if not wfs.exists("example"):
        WorkflowService(wfs, RunRepository(db), WorkflowVersionRepository(db)).seed_example(uid, "example")
    if config.demo_mode(): demo_service.seed(db, uid, jobs=jobs)  # every boot: the free plan wipes SQLite when it sleeps
