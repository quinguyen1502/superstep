"""Job queue (; reliable in ; leases + delayed jobs in ).

Jobs are small JSON dicts. Kinds: run jobs {"run_id", "workflow_id", "owner", "input", "callback_url"?, "token_id"?}
and webhook deliveries {"kind": "delivery", "delivery_id"}.

- InMemoryJobQueue (REDIS_URL unset): **dev/single-process only**. Jobs are lost on restart; start-up recovery queues
  unfinished runs again, and the answers to waiting runs that `enqueue_resume` kept on the run.
- RedisJobQueue (REDIS_URL set): at-least-once.
  - `dequeue`: BLMOVE `studio:run-jobs` → `studio:run-jobs:processing:<worker>`, then take a **lease**
    `studio:job-lease:<id>` with TTL = visibility timeout.
  - The worker renews the lease (`touch`) while the job runs, and `ack` drops the job and its lease.
  - `reap` (every worker, periodically): a job in ANY processing list whose lease is missing on two
    consecutive passes is moved back to the queue head, marked `recovered`. That covers dead workers and
    stuck ones. The two passes cover the instant between BLMOVE and taking the lease.
  - Delayed jobs (webhook retries with backoff): `enqueue_at` adds to the sorted set `studio:run-jobs:delayed`,
    and `promote_due` moves due jobs to the queue.
Blocking calls are made from worker threads (asyncio.to_thread), never on the event loop.

Health (readiness and metrics): `depth()` counts ready, delayed and in-flight jobs; every worker writes a
heartbeat (`heartbeat`) with its busy slots and capacity, and `heartbeats()` lists the live ones.
"""
import hashlib, heapq, json, queue, threading, time, uuid
from typing import Callable, Optional, Protocol
from .telemetry import current_request

QUEUE_KEY = "studio:run-jobs"
PROCESSING_PREFIX = "studio:run-jobs:processing:"
DELAYED_KEY = "studio:run-jobs:delayed"
LEASE_PREFIX = "studio:job-lease:"
HEARTBEAT_PREFIX = "studio:worker-heartbeat:"


def heartbeat_ttl() -> int:
    """Seconds a worker heartbeat stays visible: three reap intervals, at least a minute."""
    from ..core import config
    return int(max(60.0, 3 * config.job_reap_every()))


def _dump(job: dict) -> str: return json.dumps({k: v for k, v in job.items() if not k.startswith("_")}, ensure_ascii=False, sort_keys=True)
def _lease_id(raw: str) -> str: return hashlib.sha1(raw.encode()).hexdigest()


class JobQueue(Protocol):
    kind: str
    worker_id: str
    def enqueue(self, job: dict) -> None: ...
    def enqueue_at(self, job: dict, due: float) -> None: ...
    def promote_due(self, now: Optional[float] = None) -> int: ...
    def dequeue(self, timeout: float) -> Optional[dict]: ...  # blocking, returns None on timeout
    def touch(self, job: dict) -> None: ...
    def ack(self, job: dict) -> None: ...
    def reap(self) -> int: ...
    def depth(self) -> dict: ...  # {"ready", "delayed", "processing"}
    def heartbeat(self, busy: int, capacity: int) -> None: ...
    def heartbeats(self) -> list[dict]: ...  # [{"worker", "ts", "busy", "capacity"}] of live workers


def stamp(job: dict) -> dict:
    """A run job queued inside a traced request remembers that request's span, so the run's trace links to it."""
    req = current_request() if job.get("run_id") and "request_span" not in job else None
    return {**job, "request_span": req} if req else dict(job)


def enqueue_resume(runs, enqueue: Callable[[dict], None], job: dict) -> None:
    """Queue the answer to a waiting run (a resume job), kept on the run first: an in-memory queue loses it
    on a restart, and RunWorker.recover_unfinished queues the kept one again. `runs` is the RunRepository."""
    runs.keep_resume(job); enqueue(job)


class InMemoryJobQueue:
    kind = "memory"
    def __init__(self):
        self._q: "queue.Queue[dict]" = queue.Queue(); self.worker_id = "local"
        self._delayed: list[tuple[float, int, dict]] = []; self._seq = 0; self._lock = threading.Lock()
        self._taken = 0; self._beat: Optional[dict] = None
    def enqueue(self, job): self._q.put(stamp(job))
    def enqueue_at(self, job, due):
        with self._lock: self._seq += 1; heapq.heappush(self._delayed, (due, self._seq, dict(job)))
    def promote_due(self, now=None):
        now = now or time.time(); n = 0
        with self._lock:
            while self._delayed and self._delayed[0][0] <= now:
                self._q.put(heapq.heappop(self._delayed)[2]); n += 1
        return n
    def dequeue(self, timeout):
        try: job = self._q.get(timeout=timeout)
        except queue.Empty: return None
        with self._lock: self._taken += 1
        return job
    def touch(self, job): pass
    def ack(self, job):
        with self._lock: self._taken = max(0, self._taken - 1)
    def reap(self): return 0
    def depth(self):
        with self._lock: return {"ready": self._q.qsize(), "delayed": len(self._delayed), "processing": self._taken}
    def heartbeat(self, busy, capacity): self._beat = {"worker": self.worker_id, "ts": time.time(), "busy": busy, "capacity": capacity}
    def heartbeats(self):
        b = self._beat
        return [dict(b)] if b and time.time() - b["ts"] <= heartbeat_ttl() else []


class RedisJobQueue:
    kind = "redis"
    def __init__(self, url: str, client=None, worker_id: Optional[str] = None, visibility: Optional[int] = None):
        if client is None:
            import redis
            client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=10)
        self.r = client; self.worker_id = worker_id or uuid.uuid4().hex[:12]
        self.processing = PROCESSING_PREFIX + self.worker_id
        self._visibility = visibility; self._suspects: set[tuple[str, str]] = set()

    @property
    def visibility(self) -> int:
        from ..core import config
        return self._visibility or config.job_visibility()

    def enqueue(self, job): self.r.lpush(QUEUE_KEY, _dump(stamp(job)))
    def enqueue_at(self, job, due): self.r.zadd(DELAYED_KEY, {_dump(job) + f"|{uuid.uuid4().hex[:6]}": due})  # suffix: identical jobs stay distinct

    def promote_due(self, now=None):
        n = 0
        for member in self.r.zrangebyscore(DELAYED_KEY, "-inf", now or time.time(), start=0, num=100):
            if self.r.zrem(DELAYED_KEY, member):  # only the worker that removed it promotes it
                self.r.lpush(QUEUE_KEY, member.rsplit("|", 1)[0]); n += 1
        return n

    def dequeue(self, timeout):
        raw = self.r.blmove(QUEUE_KEY, self.processing, max(1, int(timeout)), "RIGHT", "LEFT")
        if raw is None: return None
        self.r.set(LEASE_PREFIX + _lease_id(raw), self.worker_id, ex=self.visibility)
        job = json.loads(raw); job["_raw"] = raw  # exact payload, needed for LREM on ack
        return job

    def touch(self, job):
        if job.get("_raw"): self.r.set(LEASE_PREFIX + _lease_id(job["_raw"]), self.worker_id, ex=self.visibility)

    def ack(self, job):
        raw = job.get("_raw")
        if raw:
            self.r.lrem(self.processing, 1, raw); self.r.delete(LEASE_PREFIX + _lease_id(raw))

    def reap(self) -> int:
        """Requeue jobs whose lease expired (seen expired on two consecutive passes). Safe on every worker."""
        n = 0; seen: set[tuple[str, str]] = set()
        for key in self.r.scan_iter(match=PROCESSING_PREFIX + "*"):
            for raw in self.r.lrange(key, 0, -1):
                if self.r.exists(LEASE_PREFIX + _lease_id(raw)): continue
                if (key, raw) not in self._suspects: seen.add((key, raw)); continue
                if self.r.lrem(key, 1, raw):  # only the reaper that removed it requeues it
                    job = json.loads(raw); job["recovered"] = True; job["attempt"] = int(job.get("attempt") or 1) + 1  # unique payload -> own lease key
                    self.r.rpush(QUEUE_KEY, _dump(job)); n += 1  # RPUSH: served next (BLMOVE takes from the right)
        self._suspects = seen
        return n

    def depth(self):
        processing = sum(int(self.r.llen(k)) for k in self.r.scan_iter(match=PROCESSING_PREFIX + "*", count=100))
        return {"ready": int(self.r.llen(QUEUE_KEY)), "delayed": int(self.r.zcard(DELAYED_KEY)), "processing": processing}

    def heartbeat(self, busy, capacity):
        beat = {"worker": self.worker_id, "ts": time.time(), "busy": busy, "capacity": capacity}
        self.r.set(HEARTBEAT_PREFIX + self.worker_id, json.dumps(beat), ex=heartbeat_ttl())

    def heartbeats(self):
        keys = list(self.r.scan_iter(match=HEARTBEAT_PREFIX + "*", count=100))
        out = []
        for raw in (self.r.mget(keys) if keys else []):
            if not raw: continue
            try: out.append(json.loads(raw))
            except ValueError: continue
        return out


def make_job_queue(url: Optional[str]) -> JobQueue:
    return RedisJobQueue(url) if url else InMemoryJobQueue()
