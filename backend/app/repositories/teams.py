from typing import Optional
from sqlalchemy import delete, func, select
from ..models import Team, TeamMember, User, WorkflowTeamShare
from ..models.database import Database
from ..models.usage_budget import UsageBudget
from ..models.dataset import Dataset
from .datasets import delete_dataset_definitions
from .usage_budgets import delete_budget_rows


class TeamRepository:
    def __init__(self, db: Database): self.db = db

    def all(self) -> list[tuple[Team, int]]:
        """(team, member count), by name."""
        n = select(TeamMember.team_id, func.count(TeamMember.user_id).label("n")).group_by(TeamMember.team_id).subquery()
        with self.db.session() as s:
            return [(t, int(c or 0)) for t, c in s.execute(select(Team, n.c.n).outerjoin(n, n.c.team_id == Team.id).order_by(Team.name))]

    def get(self, tid: str) -> Optional[Team]:
        with self.db.session() as s: return s.get(Team, tid)

    def by_name(self, name: str) -> Optional[Team]:
        with self.db.session() as s: return s.scalar(select(Team).where(func.lower(Team.name) == name.lower()))

    def save(self, t: Team) -> Team:
        with self.db.session() as s: t = s.merge(t); s.commit(); s.refresh(t); return t

    def delete(self, tid: str) -> None:
        with self.db.session() as s:
            delete_dataset_definitions(s, Dataset.team_id == tid)
            delete_budget_rows(s, UsageBudget.team_id == tid)
            for m in (TeamMember, WorkflowTeamShare): s.execute(delete(m).where(m.team_id == tid))
            s.execute(delete(Team).where(Team.id == tid)); s.commit()

    # ---- members ----
    def members(self, tid: str) -> list[tuple[TeamMember, User]]:
        with self.db.session() as s:
            return list(s.execute(select(TeamMember, User).join(User, User.id == TeamMember.user_id).where(TeamMember.team_id == tid).order_by(User.email)))

    def add_member(self, m: TeamMember) -> bool:
        """True when the user was not a member yet."""
        with self.db.session() as s:
            if s.get(TeamMember, (m.team_id, m.user_id)) is not None: return False
            s.add(m); s.commit(); return True

    def remove_member(self, tid: str, uid: str) -> bool:
        with self.db.session() as s:
            n = s.execute(delete(TeamMember).where(TeamMember.team_id == tid, TeamMember.user_id == uid)).rowcount; s.commit(); return bool(n)

    def teams_of(self, uid: str) -> list[str]:
        with self.db.session() as s: return list(s.scalars(select(TeamMember.team_id).where(TeamMember.user_id == uid)))

    # ---- workflow team shares ----
    def shares_for_workflow(self, wid: str) -> list[tuple[WorkflowTeamShare, str]]:
        with self.db.session() as s:
            return list(s.execute(select(WorkflowTeamShare, Team.name).join(Team, Team.id == WorkflowTeamShare.team_id)
                                  .where(WorkflowTeamShare.workflow_id == wid).order_by(Team.name)))

    def roles_for_user(self, uid: str, wid: Optional[str] = None) -> dict[str, list[str]]:
        """workflow id -> share roles granted through this user's teams (optionally for one workflow)."""
        q = (select(WorkflowTeamShare.workflow_id, WorkflowTeamShare.role)
             .join(TeamMember, TeamMember.team_id == WorkflowTeamShare.team_id).where(TeamMember.user_id == uid))
        if wid is not None: q = q.where(WorkflowTeamShare.workflow_id == wid)
        out: dict[str, list[str]] = {}
        with self.db.session() as s:
            for w, r in s.execute(q): out.setdefault(w, []).append(r)
        return out

    def upsert_share(self, row: WorkflowTeamShare) -> bool:
        """True when the share is new or its role changed."""
        with self.db.session() as s:
            old = s.get(WorkflowTeamShare, (row.workflow_id, row.team_id))
            if old is not None and old.role == row.role: return False
            s.merge(row); s.commit(); return True

    def remove_share(self, wid: str, tid: str) -> bool:
        with self.db.session() as s:
            n = s.execute(delete(WorkflowTeamShare).where(WorkflowTeamShare.workflow_id == wid, WorkflowTeamShare.team_id == tid)).rowcount
            s.commit(); return bool(n)

    def delete_shares_for_workflow(self, wid: str) -> None:
        with self.db.session() as s: s.execute(delete(WorkflowTeamShare).where(WorkflowTeamShare.workflow_id == wid)); s.commit()
