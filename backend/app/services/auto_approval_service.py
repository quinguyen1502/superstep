"""AI review of approvals: the kill switches (TASK-0186, REQ-0081, DEC-0075 decision 7).

- Operator: `STUDIO_AUTO_APPROVAL=off` turns automatic answers off everywhere.
- Organisation: an admin pauses AI review for every workflow (setting `auto_approval_paused`).
- Workflow: its owner or an admin pauses it for that workflow (setting `auto_approval_paused:<workflow id>`, outside the
  workflow's JSON so pausing does not make a new version).
While paused, requests go to people as if AI review were off; the opinion is not asked for either.
"""
from __future__ import annotations
import time
from typing import Optional
from ..core import config, permissions as P
from ..core.errors import AppError
from ..repositories import SettingsRepository

ORG_KEY = "auto_approval_paused"


def _wkey(wid: str) -> str: return f"{ORG_KEY}:{wid}"


class AutoApprovalService:
    def __init__(self, settings: SettingsRepository, access=None, audit=None, reviews=None):
        """reviews: -> AutoReviewService, for the per-workflow counts (TASK-0187)."""
        self.settings, self.access, self.audit, self.reviews = settings, access, audit, reviews

    def org_paused(self) -> bool: return bool(self.settings.get(ORG_KEY, False))
    def workflow_paused(self, wid: Optional[str]) -> bool: return bool(wid) and bool(self.settings.get(_wkey(wid), False))

    def paused(self, wid: Optional[str]) -> bool:
        """True when AI review must not run for this workflow: operator off, organisation or workflow paused."""
        return not config.auto_approval_enabled() or self.org_paused() or self.workflow_paused(wid)

    def _enabled(self) -> None:
        if not config.auto_approval_enabled(): raise AppError("AUTO_APPROVAL_DISABLED")

    def status(self, uid: str) -> dict:
        return {"enabled": config.auto_approval_enabled(), "org_paused": self.org_paused(),
                "can_manage": bool(self.access is None or self.access.can(uid, P.USERS_MANAGE))}

    def set_org_paused(self, uid: str, paused) -> dict:
        if self.access is not None: self.access.require(uid, P.USERS_MANAGE)
        self._enabled()
        before = self.org_paused(); self.settings.set(ORG_KEY, bool(paused), uid, time.time())
        if self.audit: self.audit.record(uid, "policy.auto_approval", "policy", ORG_KEY, ORG_KEY, before=before, after=bool(paused))
        return self.status(uid)

    def workflow_status(self, uid: str, wid: str) -> dict:
        if self.access is not None: self.access.workflow(wid, uid)
        out = {"workflow_id": wid, "paused": self.workflow_paused(wid), "org_paused": self.org_paused(), "enabled": config.auto_approval_enabled()}
        if self.reviews is not None: out["stats"] = self.reviews().stats(wid)
        if self.access is not None:
            w = self.access.workflow(wid, uid); out["can_manage"] = w.owner == uid or self.access.role(uid) == "admin"
        return out

    def set_workflow_paused(self, uid: str, wid: str, paused) -> dict:
        """Owner or admin (owner decision 3): the people who may turn auto on may also pause it."""
        if self.access is not None:
            w = self.access.workflow(wid, uid)
            if w.owner != uid and self.access.role(uid) != "admin": raise AppError("AUTO_APPROVAL_FORBIDDEN")
        self._enabled()
        self.settings.set(_wkey(wid), bool(paused), uid, time.time())
        return self.workflow_status(uid, wid)
