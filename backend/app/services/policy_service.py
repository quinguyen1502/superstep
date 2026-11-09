"""Studio policy edited by admins: which roles may use org-wide approval channels and MCP servers at run time."""
from __future__ import annotations
import time
from ..core import permissions as P
from ..core.errors import AppError
from ..repositories import SettingsRepository

ORG_KEY = "org_resources_roles"


class PolicyService:
    def __init__(self, settings: SettingsRepository, access, audit=None):
        self.settings, self.access, self.audit = settings, access, audit

    def org_roles(self) -> list[str]:
        roles = self.settings.get(ORG_KEY, list(P.ORG_RESOURCE_DEFAULT))
        return ["admin"] + [r for r in P.ROLES if r != "admin" and r in roles]  # admins can never be locked out

    def org_allowed(self, uid: str | None) -> bool:
        return bool(uid) and self.access.role(uid) in self.org_roles()

    def get(self, uid: str) -> dict:
        return {"org_resources_roles": self.org_roles(), "default": list(P.ORG_RESOURCE_DEFAULT)}

    def update(self, uid: str, org_resources_roles) -> dict:
        self.access.require(uid, P.USERS_MANAGE)
        if not isinstance(org_resources_roles, list) or any(r not in P.ROLES for r in org_resources_roles):
            raise AppError("USER_ROLE_INVALID", roles=", ".join(P.ROLES))
        before = self.org_roles()
        self.settings.set(ORG_KEY, sorted(set(org_resources_roles) | {"admin"}, key=P.ROLES.index), uid, time.time())
        if self.audit: self.audit.record(uid, "policy.org_resources", "policy", ORG_KEY, "org_resources_roles", before=before, after=self.org_roles())
        return self.get(uid)
