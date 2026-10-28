from typing import Optional
from sqlalchemy import func, select, update
from ..models import User, Workflow
from ..models.database import Database


class UserRepository:
    def __init__(self, db: Database): self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        with self.db.session() as s:
            return s.scalars(select(User).where(User.email == email)).first()

    def get_by_id(self, uid: str) -> Optional[User]:
        with self.db.session() as s:
            return s.get(User, uid)

    def add(self, uid: str, email: str, password_hash: str, created: float) -> User:
        with self.db.session() as s:
            u = User(id=uid, email=email, password=password_hash, created=created); s.add(u); s.commit(); return u

    def ids_created_before(self, prefix: str, before: float) -> list[str]:
        """Ids starting with `prefix` of accounts created before `before` (demo visitors past their TTL)."""
        with self.db.session() as s:
            return list(s.scalars(select(User.id).where(User.id.startswith(prefix, autoescape=True), User.created < before)))

    def set_prefs(self, uid: str, **prefs) -> Optional[User]:
        """Preferences: notify_in_app / notify_email (TASK-0021, booleans), lang (TASK-0022 follow-up, en | vi)."""
        with self.db.session() as s:
            u = s.get(User, uid)
            if u is None: return None
            for k, v in prefs.items(): setattr(u, k, v if k == "lang" else bool(v))
            s.commit(); s.refresh(u); return u

    def set_admin(self, uid: str, admin: bool = True) -> None:
        """Shortcut kept for seeds and tests: admin role, or back to the default role."""
        self.set_role(uid, "admin" if admin else "editor")

    def set_role(self, uid: str, role: str) -> None:
        with self.db.session() as s: s.execute(update(User).where(User.id == uid).values(role=role)); s.commit()

    def set_password(self, uid: str, password_hash: str, changed: float) -> None:
        """Replace the hash. Tokens issued before `changed` stop working."""
        with self.db.session() as s:
            s.execute(update(User).where(User.id == uid).values(password=password_hash, password_changed=changed))
            s.commit()

    def set_active(self, uid: str, active: bool) -> None:
        with self.db.session() as s: s.execute(update(User).where(User.id == uid).values(active=active)); s.commit()

    def list_all(self) -> list[tuple[User, int]]:
        """(user, owned workflow count), oldest account first."""
        counts = select(Workflow.owner, func.count(Workflow.id).label("n")).group_by(Workflow.owner).subquery()
        with self.db.session() as s:
            return [(u, int(n or 0)) for u, n in s.execute(select(User, counts.c.n).outerjoin(counts, counts.c.owner == User.id).order_by(User.created))]

    def count_active_admins(self) -> int:
        with self.db.session() as s:
            return int(s.scalar(select(func.count(User.id)).where(User.role == "admin", User.active.is_(True))) or 0)

    def by_ids(self, ids: list[str]) -> dict[str, User]:
        if not ids: return {}
        with self.db.session() as s: return {u.id: u for u in s.scalars(select(User).where(User.id.in_(ids)))}
