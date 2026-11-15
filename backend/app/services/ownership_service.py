"""Ownership transfer of workflows. The owner or an admin hands a workflow to another editor/admin.

Runs use the owner's credentials, knowledge bases and personal MCP servers, so a transfer checks every
reference against the new owner: each one the new owner cannot use is either re-bound to one of their own resources
(`rebind: {node_id: resource_id}`) or reported back as a flagged issue (the node then fails clearly until fixed)."""
from __future__ import annotations
import json, time
from typing import Optional
from ..core import permissions as P
from ..core.errors import AppError
from ..engine import subgraphs
from ..models import WorkflowShare
from .auth_service import normalise_email
from .naming import unique_name

# node data field -> resource kind
FIELDS = (("credential_id", "credential"), ("knowledge_base_id", "knowledge_base"), ("server_id", "mcp_server"))


class OwnershipService:
    def __init__(self, workflows, users, access, shares, credentials, knowledge, mcp, audit, writer):
        """writer: WorkflowService (versioned writes, one code path for every save)."""
        self.workflows, self.users, self.access, self.shares = workflows, users, access, shares
        self.credentials, self.knowledge, self.mcp, self.audit, self.writer = credentials, knowledge, mcp, audit, writer

    # ---- what a user may use ----
    def _usable(self, kind: str, rid: str, uid: str) -> bool:
        if kind == "credential": return self.credentials.get_owned(rid, uid) is not None
        if kind == "knowledge_base": return self.knowledge.get_owned(rid, uid) is not None
        if kind == "mcp_server": s = self.mcp.get(rid); return s is not None and (s.scope == "org" or s.owner == uid)
        if kind == "subgraph": return self.access.may(rid, uid)
        return False

    def _name(self, kind: str, rid: str, owner: str) -> Optional[str]:
        row = (self.credentials.get_owned(rid, owner) if kind == "credential" else self.knowledge.get_owned(rid, owner) if kind == "knowledge_base"
               else self.mcp.get(rid) if kind == "mcp_server" else self.workflows.get(rid))
        return getattr(row, "name", None)

    def options(self, uid: str) -> dict:
        return {"credential": [{"id": c.id, "name": c.name} for c in self.credentials.list_for_owner(uid)],
                "knowledge_base": [{"id": k.id, "name": k.name} for k, _, _ in self.knowledge.list_for_owner(uid)],
                "mcp_server": [{"id": m.id, "name": m.name} for m in self.mcp.visible(uid)]}

    def issues(self, wf: dict, owner: str, new: str) -> list[dict]:
        out = []
        for n in wf.get("nodes", []):
            d = n.get("data") or {}; label = d.get("label") or n.get("id")
            refs = [(f, k, d.get(f)) for f, k in FIELDS if d.get(f)]
            if n.get("type") == "subgraph" and d.get("workflow_id"): refs.append(("workflow_id", "subgraph", d["workflow_id"]))
            for field, kind, rid in refs:
                if not self._usable(kind, str(rid), new):
                    out.append({"node_id": n["id"], "node": label, "field": field, "kind": kind, "id": rid, "name": self._name(kind, str(rid), owner),
                                "rebindable": kind != "subgraph"})
        return out

    def _target(self, w, email: str):
        u = self.users.get_by_email(normalise_email(email or ""))
        if u is None or not u.active: raise AppError("SHARE_USER_NOT_FOUND")
        if u.id == w.owner: raise AppError("TRANSFER_SAME_OWNER")
        if not P.can(u.role, P.WORKFLOWS_CREATE): raise AppError("TRANSFER_TARGET_ROLE")
        return u

    def preview(self, wid: str, uid: str, email: str) -> dict:
        w = self.access.workflow(wid, uid, P.TRANSFER); u = self._target(w, email)
        return {"new_owner": u.email, "issues": self.issues(json.loads(w.data or "{}"), w.owner, u.id), "options": self.options(u.id)}

    def transfer(self, wid: str, uid: str, email: str, rebind: Optional[dict] = None, keep_access: bool = True) -> dict:
        w = self.access.workflow(wid, uid, P.TRANSFER); u = self._target(w, email)
        return self.reassign(w, u, uid, rebind or {}, keep_access)

    def reassign(self, w, u, uid: str, rebind: dict, keep_access: bool) -> dict:
        """Move `w` to user `u` (checks done by the caller). Used by transfer and by account deletion."""
        wf = json.loads(w.data or "{}"); old = w.owner; before = self.users.get_by_id(old)
        pending = {i["node_id"]: i for i in self.issues(wf, old, u.id)}
        for nid, rid in (rebind or {}).items():
            i = pending.get(nid)
            if i is None or not i["rebindable"] or not rid or not self._usable(i["kind"], str(rid), u.id): raise AppError("TRANSFER_REBIND_INVALID", node=nid)
            node = next(n for n in wf["nodes"] if n["id"] == nid); node["data"][i["field"]] = rid; pending.pop(nid)
        name = unique_name(self.workflows.names_for_owner(u.id), w.name or "Untitled")
        wf["name"] = name
        self.workflows.set_owner(w.id, u.id, name)
        self.writer.write_as(w.id, name, wf, uid, note=f"Ownership transferred to {u.email}")
        self.shares.remove(w.id, u.id)
        if keep_access and before is not None and before.active:
            self.shares.upsert(WorkflowShare(workflow_id=w.id, user_id=old, role="editor", created=time.time(), shared_by=uid))
        flagged = list(pending.values())
        self.audit.record(uid, "workflow.transfer", "workflow", w.id, name, **{"from": before.email if before else old, "to": u.email},
                          rebound=len(rebind or {}), flagged=[f"{i['node']}: {i['kind']}" for i in flagged])
        return {"id": w.id, "name": name, "owner_email": u.email, "flagged": flagged}
