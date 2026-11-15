"""Result-webhook deliveries with a log and retries.

Each callback becomes a `webhook_deliveries` row. One attempt runs per queue job ({"kind": "delivery"}).
A failed attempt is rescheduled with exponential backoff (base * 2^(n-1), capped) through the queue's delayed
set, until STUDIO_WEBHOOK_MAX_ATTEMPTS. The owner can list deliveries and redeliver one (a fresh round).
"""
import hashlib, json, time, uuid
from typing import Callable, Optional
from ..core import config
from ..core.errors import AppError
from ..models import WebhookDelivery
from ..repositories import WebhookDeliveryRepository, WorkflowRepository
from . import webhooks
from .job_queue import JobQueue

DELIVERY_EVENT = "run.finished"


def backoff(attempt: int) -> float:
    """Delay before attempt `attempt + 1` (attempt = attempts made so far, >= 1)."""
    return min(config.webhook_backoff_max(), config.webhook_backoff_base() * (2 ** (attempt - 1)))


class DeliveryService:
    def __init__(self, repo: WebhookDeliveryRepository, workflows: WorkflowRepository, jobs: JobQueue,
                 secrets: Optional[Callable[[Optional[str]], list[str]]] = None, access=None):
        self.repo, self.workflows, self.jobs, self.secrets = repo, workflows, jobs, secrets  # secrets: token id -> active secrets
        self.access = access  # AccessService

    @staticmethod
    def public(d: WebhookDelivery) -> dict:
        return {"id": d.id, "run_id": d.run_id, "url": d.url, "event": d.event, "status": d.status, "attempts": d.attempts,
                "response_code": d.response_code, "latency_ms": d.latency_ms, "last_error": d.last_error,
                "next_attempt": d.next_attempt, "created": d.created, "updated": d.updated}

    def create(self, wid: str, run_id: str, token_id: Optional[str], url: str, payload: dict) -> str:
        did = uuid.uuid4().hex[:12]; now = time.time()
        self.repo.add(WebhookDelivery(id=did, workflow_id=wid, run_id=run_id, token_id=token_id, url=url, event=DELIVERY_EVENT,
                                      payload=json.dumps(payload, ensure_ascii=False), status="pending", attempts=0, created=now, updated=now))
        self.jobs.enqueue({"kind": "delivery", "delivery_id": did})
        return did

    def for_run(self, run) -> Optional[str]:
        """The callback_url webhook of an API run that just settled (finished, or paused again at a Human node).
        One path for every source - first run, resume from the studio, Slack/Telegram, recovery - and idempotent:
        the key is the run's settled state, so a second caller for the same segment inserts nothing."""
        from .trigger_service import run_result
        if run is None or not run.callback_url or run.status in ("queued", "running"): return None
        key = hashlib.sha256(f"{run.id}|{run.status}|{run.ended}|{len(run.events or '')}".encode()).hexdigest()[:32]
        did = uuid.uuid4().hex[:12]; now = time.time()
        row = WebhookDelivery(id=did, workflow_id=run.workflow_id, run_id=run.id, token_id=run.callback_token_id, url=run.callback_url,
                              event=DELIVERY_EVENT, payload=json.dumps(run_result(run), ensure_ascii=False), status="pending",
                              attempts=0, created=now, updated=now, dedupe_key=key)
        if not self.repo.add_once(row): return None
        self.jobs.enqueue({"kind": "delivery", "delivery_id": did})
        return did

    def attempt(self, did: str) -> Optional[str]:
        """Make one attempt; schedule the next on failure. Returns the new status (None if the row is gone)."""
        d = self.repo.get(did)
        if d is None or d.status in ("ok", "failed"): return d.status if d else None
        res = webhooks.post(d.url, json.loads(d.payload), self.secrets(d.token_id) if self.secrets else None, d.event)
        n = (d.attempts or 0) + 1; now = time.time()
        if res.ok: status, nxt = "ok", None
        elif res.retryable and n < config.webhook_max_attempts(): status, nxt = "retrying", now + backoff(n)
        else: status, nxt = "failed", None
        self.repo.update(did, status=status, attempts=n, response_code=res.code, latency_ms=res.latency_ms,
                         last_error=None if res.ok else res.error, next_attempt=nxt, updated=now)
        if nxt: self.jobs.enqueue_at({"kind": "delivery", "delivery_id": did}, nxt)
        return status

    # ---- owner API ----
    def _owned(self, wid: str, uid: str):
        if self.access is not None: self.access.workflow(wid, uid, "share"); return  # deliveries belong to API tokens
        if self.workflows.get_owned(wid, uid) is None: raise AppError("WORKFLOW_NOT_FOUND")

    def list(self, wid: str, uid: str) -> list[dict]:
        self._owned(wid, uid); return [self.public(d) for d in self.repo.list_for_workflow(wid)]

    def redeliver(self, wid: str, did: str, uid: str) -> dict:
        self._owned(wid, uid); d = self.repo.get(did)
        if d is None or d.workflow_id != wid: raise AppError("DELIVERY_NOT_FOUND")
        self.repo.update(did, status="pending", attempts=0, next_attempt=None, last_error=None, updated=time.time())
        self.jobs.enqueue({"kind": "delivery", "delivery_id": did})
        return self.public(self.repo.get(did))
