"""Workflow sharing (TASK-0014, teams TASK-0029): the owner (or an admin) shares a workflow with users or teams as viewer or editor."""
from __future__ import annotations
import time
from ..core import config, permissions as P
from ..core.errors import AppError
from ..models import WorkflowShare, WorkflowTeamShare
from ..repositories import UserRepository, WorkflowShareRepository
from . import demo_service
from .access import AccessService
from .auth_service import normalise_email


class ShareService:
    def __init__(self, shares: WorkflowShareRepository, users: UserRepository, access: AccessService, teams=None, audit=None):
        self.shares, self.users, self.access, self.teams, self.audit = shares, users, access, teams, audit

    def _log(self, uid, action, w, **d):
        if self.audit: self.audit.record(uid, action, "workflow", w.id, w.name, **d)

    def list(self, wid: str, uid: str) -> dict:
        w = self.access.workflow(wid, uid, P.VIEW)
        owner = self.users.get_by_id(w.owner)
        shares = self.shares.for_workflow(wid)
        # the public demo: anonymous visitors share the samples, so a visitor sees only the owner and their own row
        if config.demo_mode() and demo_service.is_visitor(uid): shares = [(s, e) for s, e in shares if s.user_id == uid]
        return {"owner": {"id": w.owner, "email": owner.email if owner else None},
                "can_share": self.access.may(wid, uid, P.SHARE), "can_transfer": self.access.may(wid, uid, P.TRANSFER),
                "shares": [{"user_id": s.user_id, "email": e, "role": s.role, "created": s.created} for s, e in shares],
                "teams": [{"team_id": s.team_id, "name": n, "role": s.role, "created": s.created} for s, n in self.teams.shares_for_workflow(wid)]
                         if self.teams is not None else []}

    def put(self, wid: str, uid: str, email: str, role: str) -> dict:
        """Share with (or change the role of) the account with this email."""
        w = self.access.workflow(wid, uid, P.SHARE)
        if role not in P.SHARE_ROLES: raise AppError("SHARE_ROLE_INVALID")
        u = self.users.get_by_email(normalise_email(email or ""))
        if u is None or not u.active: raise AppError("SHARE_USER_NOT_FOUND")
        if u.id == w.owner: raise AppError("SHARE_OWNER")
        before = self.shares.role_of(wid, u.id)
        self.shares.upsert(WorkflowShare(workflow_id=wid, user_id=u.id, role=role, created=time.time(), shared_by=uid))
        if before != role: self._log(uid, "share.add" if before is None else "share.role", w, user=u.email, role=role, before=before)
        return self.list(wid, uid)

    def remove(self, wid: str, uid: str, target: str) -> dict:
        """The owner or an admin removes anyone; a user may also leave a workflow shared with them."""
        w = self.access.workflow(wid, uid, P.VIEW if target == uid else P.SHARE)
        if not self.shares.remove(wid, target): raise AppError("SHARE_NOT_FOUND")
        u = self.users.get_by_id(target); self._log(uid, "share.remove", w, user=u.email if u else target)
        return {"ok": True}

    def put_team(self, wid: str, uid: str, team_id: str, role: str) -> dict:
        w = self.access.workflow(wid, uid, P.SHARE)
        if role not in P.SHARE_ROLES: raise AppError("SHARE_ROLE_INVALID")
        t = self.teams.get(team_id or "")
        if t is None: raise AppError("TEAM_NOT_FOUND")
        if self.teams.upsert_share(WorkflowTeamShare(workflow_id=wid, team_id=t.id, role=role, created=time.time(), shared_by=uid)):
            self._log(uid, "share.team", w, team=t.name, role=role)
        return self.list(wid, uid)

    def remove_team(self, wid: str, uid: str, team_id: str) -> dict:
        w = self.access.workflow(wid, uid, P.SHARE); t = self.teams.get(team_id)
        if not self.teams.remove_share(wid, team_id): raise AppError("SHARE_NOT_FOUND")
        self._log(uid, "share.team_remove", w, team=t.name if t else team_id)
        return {"ok": True}
