"""User administration. Callers need users.manage."""
from __future__ import annotations
from ..core import permissions as P
from ..core.errors import AppError
from ..repositories import UserRepository
from .access import AccessService
from .auth_service import normalise_email

DELETE_MODES = ("anonymize", "delete")


class UserService:
    def __init__(self, users: UserRepository, access: AccessService, audit=None, data=None, ownership=None, workflows=None, browser=None):
        """data: UserDataRepository; ownership: OwnershipService; workflows: WorkflowRepository (account deletion)."""
        self.browser=browser
        self.users, self.access, self.audit, self.data, self.ownership, self.workflows = users, access, audit, data, ownership, workflows

    @staticmethod
    def public(u, workflows: int = 0) -> dict:
        return {"id": u.id, "email": u.email, "role": u.role, "active": bool(u.active), "created": u.created, "workflows": workflows}

    def _log(self, uid, action, u, **d):
        if self.audit: self.audit.record(uid, action, "user", u.id, u.email, **d)

    def list(self, uid: str) -> dict:
        self.access.require(uid, P.USERS_MANAGE)
        return {"users": [self.public(u, n) for u, n in self.users.list_all() if not (u.email or "").endswith("@deleted.invalid")], **P.matrix()}

    def _guard(self, uid: str, u, demotes: bool) -> None:
        if u.id == uid and demotes: raise AppError("USER_SELF_CHANGE")  # no self-lockout
        if demotes and u.role == "admin" and u.active and self.users.count_active_admins() <= 1: raise AppError("USER_LAST_ADMIN")

    def _get(self, target: str):
        u = self.users.get_by_id(target)
        if u is None: raise AppError("USER_NOT_FOUND")
        return u

    def update(self, uid: str, target: str, role: str | None = None, active: bool | None = None) -> dict:
        self.access.require(uid, P.USERS_MANAGE); u = self._get(target)
        if role is not None and role not in P.ROLES: raise AppError("USER_ROLE_INVALID", roles=", ".join(P.ROLES))
        changes_role = role is not None and role != u.role
        deactivates = active is False and u.active
        self._guard(uid, u, changes_role or deactivates)
        if changes_role: self.users.set_role(target, role); self._log(uid, "user.role", u, before=u.role, after=role)
        if active is not None and active != bool(u.active):
            self.users.set_active(target, active); self._log(uid, "user.activate" if active else "user.deactivate", u)
        if self.browser and (changes_role or deactivates):self.browser().close_owner(target)
        return self.public(self.users.get_by_id(target))

    def delete(self, uid: str, target: str, mode: str = "anonymize", reassign_to: str | None = None) -> dict:
        """Delete or anonymise an account. Owned workflows must first move to `reassign_to` (an editor or admin);
        references the new owner cannot use are flagged per workflow. Personal resources (keys, knowledge bases,
        personal MCP servers and channels, tokens) are removed in both modes; `delete` also removes the runs they started
        and the account row, `anonymize` keeps a deactivated tombstone so run history stays attributable."""
        self.access.require(uid, P.USERS_MANAGE); u = self._get(target)
        if mode not in DELETE_MODES: raise AppError("USER_DELETE_MODE_INVALID")
        self._guard(uid, u, True)
        owned = self.workflows.list_for_owner(target)
        moved, flagged = [], []
        if owned:
            if not reassign_to: raise AppError("USER_HAS_WORKFLOWS", count=len(owned))
            new = self.users.get_by_email(normalise_email(reassign_to))
            if new is None or not new.active or new.id == target: raise AppError("SHARE_USER_NOT_FOUND")
            if not P.can(new.role, P.WORKFLOWS_CREATE): raise AppError("TRANSFER_TARGET_ROLE")
            for w in owned:
                r = self.ownership.reassign(w, new, uid, {}, keep_access=False); moved.append(r["id"])
                flagged += [{"workflow_id": w.id, "workflow": r["name"], **i} for i in r["flagged"]]
        email = u.email
        if self.browser:self.browser().close_owner(target)
        self.data.purge(target, runs=mode == "delete")
        if mode == "delete": self.data.delete_user(target)
        else: self.data.anonymise(target)
        if self.audit: self.audit.record(uid, f"user.{mode}", "user", target, email, reassigned_to=reassign_to, workflows=len(moved))
        return {"ok": True, "mode": mode, "reassigned": moved, "flagged": flagged}
