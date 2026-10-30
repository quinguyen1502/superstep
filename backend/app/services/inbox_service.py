"""The Approvals inbox (TASK-0065, DEC-0043): every waiting step a user may answer, as run owner or listed approver,
across workflows, answered in place. An approver sees only the request, never the workflow, trace or state."""
from typing import Optional
from ..core.errors import AppError
from ..models import ApprovalWait
from .approval_service import ApprovalService
from .run_service import RunService, human_response


class InboxService:
    def __init__(self, approvals: ApprovalService, runs: RunService, access=None):
        self.approvals, self.runs, self.access = approvals, runs, access
        self.repo, self.users, self.workflows = approvals.repo, approvals.users, runs.workflows

    def list(self, uid: str) -> list[dict]:
        self.runs.expire_waiting()
        names, emails = {}, {}
        def name(wid):
            if wid and wid not in names: w = self.workflows.get(wid); names[wid] = w.name if w else None
            return names.get(wid)
        def email(u):
            if u not in emails: x = self.users.get_by_id(u); emails[u] = x.email if x else None
            return emails[u]
        chain = lambda w: self.approvals.workflow_name(w.run_id, w.workflow_id) if self.runs.runs.get(w.run_id) and self.runs.runs.get(w.run_id).parent_run_id else name(w.workflow_id)  # noqa: E731
        return [{"run_id": w.run_id, "workflow_id": w.workflow_id, "workflow_name": chain(w), "node": w.node_id, "label": w.label,
                 "prompt": w.prompt, "channel": w.channel, "mine": w.owner == uid, "owner_email": None if w.owner == uid else email(w.owner),
                 "waiting_since": w.created, "due_at": w.due_at, "can_open": self._can_open(w, uid)} for w in self.repo.inbox(uid)]

    def _can_open(self, w: ApprovalWait, uid: str) -> bool:
        """Only users who may already read the run: its owner, and the workflow's owner or an admin (run history rule)."""
        if w.owner == uid: return True
        if self.access is None or not w.workflow_id: return False
        row = self.workflows.get(w.workflow_id)
        return row is not None and self.access.access_of(row, uid) == "owner"

    def answer(self, uid: str, rid: str, response) -> dict:
        response = human_response(response)
        w: Optional[ApprovalWait] = self.repo.latest_wait(rid)
        if w is None or not self.approvals.may_answer(uid, w): raise AppError("RUN_NOT_FOUND")  # ids are not disclosed
        if w.status != "waiting": raise AppError("APPROVAL_ALREADY_DECIDED")
        run = self.runs.runs.get(rid)
        if run is None or run.status != "waiting": raise AppError("RUN_NOT_WAITING")
        if self.runs.expire_if_stale(run): raise AppError("RUN_EXPIRED")
        if self.approvals.decided_elsewhere(rid) or not self.repo.close_wait(rid, "answered"): raise AppError("APPROVAL_ALREADY_DECIDED")
        self.approvals.answered_in_studio(w, uid, response)
        return {"run_id": rid, "response": response}
