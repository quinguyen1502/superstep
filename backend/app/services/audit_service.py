"""Administrative audit log: who changed roles, shares, teams, ownership, accounts and policy."""
from __future__ import annotations
import json, time, uuid
from typing import Optional
from ..core import permissions as P
from ..models import AuditEvent
from ..repositories import AuditRepository, UserRepository

CATEGORIES = ("user", "share", "team", "workflow", "policy")
SINCE = {"24h": 86400, "7d": 7 * 86400, "30d": 30 * 86400}
PAGE_MAX = 200


class AuditService:
    def __init__(self, repo: AuditRepository, users: UserRepository, access=None):
        self.repo, self.users, self.access = repo, users, access

    def record(self, actor: Optional[str], action: str, target_type: str, target_id: Optional[str] = None,
               label: Optional[str] = None, **details) -> None:
        a = self.users.get_by_id(actor) if actor else None
        self.repo.add(AuditEvent(id=uuid.uuid4().hex[:12], ts=time.time(), actor_id=actor, actor_email=a.email if a else None, action=action,
                                 target_type=target_type, target_id=target_id, target_label=label,
                                 details=json.dumps(details, ensure_ascii=False) if details else None))

    def list(self, uid: str, category: Optional[str] = None, q: Optional[str] = None, since: Optional[str] = None,
             limit: int = 50, offset: int = 0) -> dict:
        self.access.require(uid, P.USERS_MANAGE)
        limit, offset = max(1, min(PAGE_MAX, int(limit))), max(0, int(offset))
        rows, total = self.repo.query(category=category if category in CATEGORIES else None, q=(q or "").strip()[:100] or None,
                                      since=time.time() - SINCE[since] if since in SINCE else None, limit=limit, offset=offset)
        return {"items": [{"id": e.id, "at": e.ts, "actor": e.actor_email, "action": e.action, "target_type": e.target_type,
                           "target_id": e.target_id, "target": e.target_label, "details": json.loads(e.details) if e.details else {}} for e in rows],
                "total": total, "limit": limit, "offset": offset, "categories": list(CATEGORIES)}
