"""Teams: admins create teams and manage members; anyone who may share a workflow can share it with a team."""
from __future__ import annotations
import time, uuid
from ..core import permissions as P
from ..core.errors import AppError
from ..models import Team, TeamMember
from ..repositories import TeamRepository, UserRepository
from .auth_service import normalise_email

NAME_MAX = 80


class TeamService:
    def __init__(self, teams: TeamRepository, users: UserRepository, access, audit):
        self.teams, self.users, self.access, self.audit = teams, users, access, audit

    def _team(self, tid: str) -> Team:
        t = self.teams.get(tid)
        if t is None: raise AppError("TEAM_NOT_FOUND")
        return t

    def _name(self, name: str, exclude: str | None = None) -> str:
        n = " ".join((name or "").split())[:NAME_MAX]
        if not n: raise AppError("TEAM_NAME_REQUIRED")
        if (o := self.teams.by_name(n)) is not None and o.id != exclude: raise AppError("TEAM_NAME_TAKEN")
        return n

    def list(self, uid: str) -> dict:
        """Every team (name, size, whether I am in it). Members are listed for admins only."""
        if self.access.role(uid) is None: raise AppError("AUTH_REQUIRED")
        admin = self.access.can(uid, P.USERS_MANAGE); mine = set(self.teams.teams_of(uid))
        return {"can_manage": admin, "teams": [{"id": t.id, "name": t.name, "description": t.description, "members": n, "mine": t.id in mine,
                                                **({"member_list": self._members(t.id)} if admin else {})} for t, n in self.teams.all()]}

    def _members(self, tid: str) -> list[dict]:
        return [{"user_id": u.id, "email": u.email, "role": u.role, "active": bool(u.active)} for _, u in self.teams.members(tid)]

    def create(self, uid: str, name: str, description: str | None = None) -> dict:
        self.access.require(uid, P.USERS_MANAGE)
        t = self.teams.save(Team(id=uuid.uuid4().hex[:10], name=self._name(name), description=(description or "").strip()[:200] or None,
                                 created=time.time(), created_by=uid))
        self.audit.record(uid, "team.create", "team", t.id, t.name)
        return {"id": t.id, "name": t.name, "description": t.description, "members": 0, "mine": False, "member_list": []}

    def update(self, uid: str, tid: str, name: str | None = None, description: str | None = None) -> dict:
        self.access.require(uid, P.USERS_MANAGE); t = self._team(tid); old = t.name
        if name is not None: t.name = self._name(name, exclude=tid)
        if description is not None: t.description = description.strip()[:200] or None
        self.teams.save(t)
        if t.name != old: self.audit.record(uid, "team.rename", "team", tid, t.name, before=old)
        return {"id": t.id, "name": t.name, "description": t.description}

    def delete(self, uid: str, tid: str) -> dict:
        self.access.require(uid, P.USERS_MANAGE); t = self._team(tid)
        self.teams.delete(tid); self.audit.record(uid, "team.delete", "team", tid, t.name)
        return {"ok": True}

    def add_member(self, uid: str, tid: str, email: str) -> dict:
        self.access.require(uid, P.USERS_MANAGE); t = self._team(tid)
        u = self.users.get_by_email(normalise_email(email or ""))
        if u is None or not u.active: raise AppError("SHARE_USER_NOT_FOUND")
        if self.teams.add_member(TeamMember(team_id=tid, user_id=u.id, added=time.time())):
            self.audit.record(uid, "team.member_add", "team", tid, t.name, member=u.email)
        return {"members": self._members(tid)}

    def remove_member(self, uid: str, tid: str, member: str) -> dict:
        self.access.require(uid, P.USERS_MANAGE); t = self._team(tid)
        u = self.users.get_by_id(member)
        if not self.teams.remove_member(tid, member): raise AppError("TEAM_MEMBER_NOT_FOUND")
        self.audit.record(uid, "team.member_remove", "team", tid, t.name, member=u.email if u else member)
        return {"members": self._members(tid)}
