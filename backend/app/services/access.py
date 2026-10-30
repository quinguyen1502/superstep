"""Authorisation (TASK-0014, DEC-0023): global permissions and per-workflow access, one place for every service.

`workflow(wid, uid, action)` returns the row when the user may perform `action`, else raises WORKFLOW_NOT_FOUND
(no access at all, so ids are not disclosed) or WORKFLOW_FORBIDDEN (can see it, not do that)."""
from __future__ import annotations
from typing import Optional
from ..core import permissions as P
from ..core.errors import AppError
from ..engine import approval_policy
from ..models import Workflow
from ..repositories import UserRepository, WorkflowRepository, WorkflowShareRepository


class AccessService:
    def __init__(self, users: UserRepository, workflows: WorkflowRepository, shares: WorkflowShareRepository, teams=None):
        self.users, self.workflows, self.shares, self.teams = users, workflows, shares, teams  # teams: TeamRepository (TASK-0029)

    def share_role(self, wid: str, uid: str) -> Optional[str]:
        """Best share role of the user on a workflow: direct share or through any of their teams."""
        roles = [self.shares.role_of(wid, uid)] + ((self.teams.roles_for_user(uid, wid).get(wid) or []) if self.teams else [])
        return P.best_share(roles)

    def shared_map(self, uid: str) -> dict[str, str]:
        out = dict(self.shares.for_user(uid))
        if self.teams is not None:
            for w, roles in self.teams.roles_for_user(uid).items(): out[w] = P.best_share([out.get(w), *roles])
        return out

    def role(self, uid: str) -> Optional[str]:
        u = self.users.get_by_id(uid)
        return u.role if u is not None and u.active else None

    def can(self, uid: str, permission: str) -> bool:
        return P.can(self.role(uid), permission)

    def require(self, uid: str, permission: str) -> None:
        if not self.can(uid, permission): raise AppError("PERMISSION_DENIED", permission=permission)

    def require_code(self, uid: str, before: Optional[dict], after: Optional[dict]) -> None:
        """Adding a Code node or changing its source needs `code.write` (TASK-0054); anything else about it does not."""
        if P.code_written(before, after) and not self.can(uid, P.CODE_WRITE): raise AppError("CODE_WRITE_FORBIDDEN")

    def require_auto(self, uid: str, owner: Optional[str], before: Optional[dict], after: Optional[dict]) -> None:
        """Turning a node's AI review to `auto`, or changing an `auto` policy, needs the workflow owner or an admin
        (TASK-0186, REQ-0081 owner decision 3). Editors may save `suggest`; turning auto off is always allowed."""
        old, new = approval_policy.auto_policies(before), approval_policy.auto_policies(after)
        if any(old.get(n) != h for n, h in new.items()) and uid != owner and self.role(uid) != "admin":
            raise AppError("AUTO_APPROVAL_FORBIDDEN")

    def access_of(self, w: Workflow, uid: str, role: Optional[str] = None) -> Optional[str]:
        role = role if role is not None else self.role(uid)
        if role is None: return None
        return P.workflow_role(role, w.owner == uid, None if w.owner == uid else self.share_role(w.id, uid))

    def workflow(self, wid: str, uid: str, action: str = P.VIEW) -> Workflow:
        w = self.workflows.get(wid)
        acc = self.access_of(w, uid) if w is not None else None
        if acc is None: raise AppError("WORKFLOW_NOT_FOUND")
        if action not in P.WORKFLOW_ACTIONS[acc]: raise AppError("WORKFLOW_FORBIDDEN")
        return w

    def may(self, wid: str, uid: str, action: str = P.VIEW) -> bool:
        try: self.workflow(wid, uid, action); return True
        except AppError: return False

    def visible(self, uid: str, all_: bool = False) -> list[tuple[Workflow, str]]:
        """(workflow, access) the user can open: own + shared; every workflow for admins asking for all."""
        role = self.role(uid)
        if role is None: return []
        shared = self.shared_map(uid)
        if all_ and P.can(role, P.WORKFLOWS_ALL): rows = self.workflows.list_all()
        else: rows = sorted(self.workflows.list_for_owner(uid) + self.workflows.by_ids(shared), key=lambda w: -(w.updated or 0))
        pairs = ((w, P.workflow_role(role, w.owner == uid, shared.get(w.id))) for w in rows)
        return [(w, acc) for w, acc in pairs if acc]
