"""Executes queued jobs (TASK-0007; leases, recovery from checkpoints and webhook deliveries in TASK-0020, DEC-0017).

Runs inside the API process (STUDIO_WORKER=1, default) and/or as a dedicated process (`python -m app.worker`).
- Run jobs use the same RunService.execute as the WebSocket, with progress checkpoints after every node, so a
  job recovered from a dead worker continues from its last finished node instead of starting over.
- Delivery jobs make one webhook attempt (DeliveryService) and reschedule themselves with backoff on failure.
- `maintain` (every worker): promotes due delayed jobs every second and reaps expired leases every
  STUDIO_JOB_REAP_EVERY seconds. The lease of a running job is renewed every visibility/3 seconds.
"""
import asyncio, json, time
from typing import Callable, Optional
from ..core import config
from ..core.errors import AppError
from ..core.logging import get_logger
from ..repositories import StaleLease
from .job_queue import JobQueue
from .run_service import RunService, error_event

log = get_logger("worker")
CHAT_CLEANUP_EVERY = 3600  # seconds between chat retention sweeps
_recovered = False  # start-up recovery runs once per process: later lifespans (tests) share the same in-memory queue


class RunWorker:
    def __init__(self, jobs: JobQueue, services: Callable[[], RunService], deliveries: Optional[Callable[[], object]] = None,
                 schedules: Optional[Callable[[], object]] = None, approvals: Optional[Callable[[], object]] = None,
                 chat: Optional[Callable[[], object]] = None, langsmith: Optional[Callable[[], object]] = None):
        self.jobs, self.services, self.deliveries = jobs, services, deliveries  # deliveries: -> DeliveryService
        self.schedules = schedules  # -> ScheduleService (TASK-0046): due cron schedules start runs from maintain()
        self.approvals = approvals  # -> ApprovalService (TASK-0066): Human node reminders and deadlines from maintain()
        self.chat = chat  # -> ChatRunService (TASK-0075): chat_message jobs check a message and start its run
        self.langsmith = langsmith  # -> LangSmithService: langsmith_suite jobs send a finished test suite as an experiment
        self._tasks: list[asyncio.Task] = []; self._stop = False

    async def run_job(self, job: dict) -> Optional[str]:
        if job.get("kind") == "delivery":
            return await asyncio.to_thread(self.deliveries().attempt, job["delivery_id"]) if self.deliveries else None
        if job.get("kind") == "langsmith_suite":
            return await asyncio.to_thread(self.langsmith().on_suite_done, job["suite_id"]) if self.langsmith else None
        if job.get("kind") == "chat_message":
            return await self.chat().handle(job["message_id"]) if self.chat else None
        svc = self.services(); rid = job["run_id"]; row = svc.runs.get(rid); attempt = int(job.get("attempt") or 1)
        if job.get("kind") == "resume" and (not job.get("recovered") or (row is not None and row.status == "waiting")):
            return await self.resume_job(svc, job)  # a recovered resume job of a run that already started continues below
        # Claim = compare-and-set to `running` + a new fencing token (TASK-0021). Cancelled/finished jobs are skipped;
        # a recovered job (its worker died or lost the lease) may take over a `running` run, which fences the old worker out.
        gen = svc.runs.claim(rid, ("queued", "running") if job.get("recovered") else ("queued",)) if row is not None else None
        if gen is None: return None
        try:
            if row.status == "running":  # recovered: continue from the last checkpoint (or restart without one)
                plan = svc.plan_recover(row, gen, attempt)
            else:
                plan = svc.plan(job["owner"], {"workflow_id": job["workflow_id"], "input": job.get("input") or {},
                                               **({"version": job["version"]} if job.get("version") else {})})  # a test suite on a stored version
                plan.run_id, plan.source, plan.checkpointing, plan.fence, plan.attempt = rid, job.get("source", "api"), True, gen, attempt
            svc.apply_test(plan, job.get("test"))  # a workflow test run (TASK-0067)
            async def send(ev): return True                       # nobody streams; history + webhook carry the result
            async def listen(): await asyncio.Event().wait()      # cancel arrives through the RunBus
            status = await svc.execute(plan, send, listen, job["owner"])
        except AppError as e:  # e.g. the workflow was deleted or is too large
            try: svc.record(rid, job["workflow_id"], job.get("input") or {}, [error_event(e.to_dict())], None, "error", row.started, job["owner"],
                            source=job.get("source", "api"), fence=gen)
            except StaleLease: return "fenced"
            status = "error"
            await svc.settled(rid, job.get("source"))  # execute() did not run: the error result still goes to the callback
        return status  # execute() queued the callback_url webhook (RunService.settled); a fenced worker leaves it to the new owner

    async def resume_job(self, svc: RunService, job: dict) -> Optional[str]:
        """Continue a waiting run with a decision from an approval channel (TASK-0022). The claim (waiting -> running,
        compare-and-set) makes sure only one resume happens, however many jobs or clicks there were."""
        rid, owner = job["run_id"], job["owner"]
        try: plan = svc.plan_resume(owner, rid, job["response"], via_channel=True)
        except AppError as e:
            log.info("approval resume of run %s skipped: %s", rid, e.code); return None
        gen = svc.runs.claim(rid, ("waiting",))
        if gen is None: return None
        plan.fence, plan.checkpointing, plan.resumed_by = gen, True, job.get("by")
        svc.apply_test(plan, job.get("test"))
        async def send(ev): return True
        async def listen(): await asyncio.Event().wait()
        return await svc.execute(plan, send, listen, owner)  # settles -> callback_url (RunService.settled)

    async def _with_lease(self, job: dict) -> None:
        """Run the job while renewing its lease so the reaper leaves it alone."""
        async def renew():
            while True:
                await asyncio.sleep(max(1.0, config.job_visibility() / 3))
                try: await asyncio.to_thread(self.jobs.touch, job)
                except Exception: log.warning("renewing job lease failed")
        keeper = asyncio.create_task(renew())
        try: await self.run_job(job)
        finally:
            keeper.cancel()
            await asyncio.to_thread(self.jobs.ack, job)  # recorded (or skipped): drop from processing list

    async def loop(self) -> None:
        while not self._stop:
            try:
                job = await asyncio.to_thread(self.jobs.dequeue, 1.0)
                if job: await self._with_lease(job)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("job failed"); await asyncio.sleep(1)

    async def reap(self) -> int:
        try:
            n = await asyncio.to_thread(self.jobs.reap)
            if n: log.warning("requeued %s job(s) whose lease expired", n)
            return n
        except Exception:
            log.exception("reaping expired jobs failed"); return 0

    async def maintain(self) -> None:
        last_reap = last_cleanup = 0.0
        while not self._stop:
            try: await asyncio.to_thread(self.jobs.promote_due)
            except Exception: log.warning("promoting delayed jobs failed")
            if self.schedules is not None:
                try: await asyncio.to_thread(self.schedules().fire_due)
                except Exception: log.exception("firing schedules failed")
            if self.approvals is not None:
                try: await asyncio.to_thread(self.approvals().fire_deadlines)
                except Exception: log.exception("firing approval deadlines failed")
            if self.chat is not None and time.time() - last_cleanup >= CHAT_CLEANUP_EVERY:  # chat history retention (TASK-0084)
                last_cleanup = time.time()
                try:
                    if (web := self.chat().web) is not None: await asyncio.to_thread(web.cleanup)
                except Exception: log.exception("cleaning up old chats failed")
            if time.time() - last_reap >= config.job_reap_every():
                last_reap = time.time(); await self.reap()
            await asyncio.sleep(min(1.0, config.job_reap_every()))

    async def recover_unfinished(self) -> int:
        """Start-up recovery for the in-memory queue (TASK-0115, DEC-0062): jobs held in memory are gone after a restart,
        so every queued or running queue-job run is queued again as a recovered job. The worker continues it from its
        last progress checkpoint (or from the start when no node had finished), exactly as for a lost Redis lease. A
        run cut off STUDIO_RECOVER_MAX_ATTEMPTS times (it keeps stopping the server, or keeps being interrupted) ends
        as `error` RUN_INTERRUPTED instead; resumes after a Human node or an Agent tool approval do not count
        (RunService.interruptions). A waiting run needs nothing (its checkpoint is in the database), unless it was
        answered and the answer's resume job was lost (TASK-0127): the answer kept on the run is queued again, also
        for a run claimed by that resume and cut off before it recorded anything, which goes back to waiting first.
        Returns the number of runs requeued."""
        global _recovered
        if self.jobs.kind != "memory" or not config.recover_on_start() or _recovered: return 0  # Redis: the reaper requeues lost jobs
        _recovered = True
        svc = self.services(); n = 0; most = config.recover_max_attempts()
        kept = await asyncio.to_thread(svc.runs.list_resumes)
        for r in kept:
            try:
                if r.status == "running":  # claimed by the resume, then cut off: its checkpoint is still the waiting one
                    if (cut := svc.interruptions(r)) >= most:
                        await asyncio.to_thread(svc.interrupted, r, cut); await svc.settled(r.id, r.source); continue
                    await asyncio.to_thread(svc.runs.set_status, r.id, "waiting")
                self.jobs.enqueue(json.loads(r.resume_job)); n += 1
            except Exception: log.exception("recovering the answer to run %s failed", r.id)
        answered = {r.id for r in kept}
        for r in await asyncio.to_thread(svc.runs.list_unfinished):
            if r.id in answered: continue
            try:
                if (cut := svc.interruptions(r)) >= most:
                    await asyncio.to_thread(svc.interrupted, r, cut); await svc.settled(r.id, r.source); continue
                self.jobs.enqueue(await asyncio.to_thread(svc.recovery_job, r)); n += 1
            except Exception: log.exception("recovering run %s failed", r.id)
        if n: log.warning("requeued %s unfinished run(s) after a restart", n)
        return n

    def start(self, n: int) -> None:
        self._stop = False
        self._tasks = [asyncio.create_task(self.maintain())] + [asyncio.create_task(self.loop()) for _ in range(n)]

    async def stop(self) -> None:
        self._stop = True
        for t in self._tasks: t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
