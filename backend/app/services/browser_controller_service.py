"""Small dedicated remote-control registry; no Agent/model loop or Studio database access."""
from dataclasses import dataclass, field
import base64
import threading
import time

from ..core.errors import AppError
from ..engine.browser_remote import CAPABILITIES
from ..engine.browser_worker import LocalBrowserWorker, BrowserWorkerError


@dataclass
class Entry:
    context: object
    worker: object
    expires: float
    ready: bool = False
    lock: object = field(default_factory=threading.Lock)


class BrowserControllerService:
    def __init__(self, worker_factory=LocalBrowserWorker, *, approved_proxies=(), operator_default=None, max_sessions=8):
        self.worker_factory, self.approved_proxies, self.operator_default = worker_factory, approved_proxies, operator_default
        self.max_sessions, self.entries, self.lock = max_sessions, {}, threading.Lock()
        self.stopping = threading.Event()
        self.sweeper = threading.Thread(target=self._watch, daemon=True); self.sweeper.start()

    def _watch(self):
        while not self.stopping.wait(1): self.sweep()

    def sweep(self):
        with self.lock: entries = list(self.entries.items())
        for sid, entry in entries:
            if not entry.lock.acquire(blocking=False): continue
            try:
                if entry.worker.closed: entry.worker.close()  # retry pending cleanup, never a command
                if time.monotonic() >= entry.expires and entry.worker.close():
                    with self.lock: self.entries.pop(sid, None)
            finally: entry.lock.release()

    def info(self): return CAPABILITIES.copy()

    def open(self, request):
        if request.settings.provider != 'controlled_remote': raise AppError('BROWSER_CAPABILITY_UNSUPPORTED')
        if set(request.proxy_secrets) - {'proxy_username', 'proxy_password'}: raise AppError('BROWSER_CAPABILITY_UNSUPPORTED')
        # Local supervisor independently validates origin/profile state before launching containers.
        settings = request.settings.model_copy(update={'provider': 'local'})
        with self.lock:
            if request.request_id in self.entries: raise AppError('BROWSER_CONTROL_UNAVAILABLE')
            if len(self.entries) >= 1024 or sum(not e.worker.closed or e.worker.cleanup_pending for e in self.entries.values()) >= self.max_sessions:
                raise AppError('BROWSER_CONTROL_UNAVAILABLE')
            worker = self.worker_factory(request.context, settings)
            entry = Entry(request.context, worker, time.monotonic() + settings.lifetime_s + 60)
            entry.lock.acquire(); self.entries[request.request_id] = entry
        try:
            worker.start(secrets=request.proxy_secrets, profile_seed=request.profile_seed,
                         approved_proxies=self.approved_proxies, operator_default=self.operator_default)
            entry.ready = True
            return {'status': 'ready', 'session_id': request.request_id, 'generation': worker.generation}
        except BrowserWorkerError as error:
            worker.close()
            raise AppError('BROWSER_CAPABILITY_UNSUPPORTED' if error.status == 'unsupported' else 'BROWSER_CONTROL_UNAVAILABLE') from None
        finally: entry.lock.release()

    def invoke(self, method, request):
        with self.lock: entry = self.entries.get(request.session_id)
        if entry is None:
            if method == 'close': return {'status': 'closed'}
            raise AppError('BROWSER_CONTROL_UNAVAILABLE')
        if entry.context != request.context or request.generation != entry.worker.generation:
            raise AppError('BROWSER_PROFILE_DENIED')
        if not entry.lock.acquire(blocking=False): raise AppError('BROWSER_CONTROL_UNAVAILABLE')
        try:
            worker = entry.worker
            mapped = request.model_copy(update={'session_id': worker.session_id})
            if method == 'close':
                if not worker.close(): raise AppError('BROWSER_CONTROL_UNAVAILABLE')
                return {'status': 'closed'}
            if not entry.ready: raise AppError('BROWSER_CONTROL_UNAVAILABLE')
            if method == 'command': return worker.call(mapped).model_dump()
            if method == 'approve': return worker.approve(mapped)
            if method == 'artifact':
                return {'artifact_id': request.artifact_id, 'png': base64.b64encode(worker.artifact(request.artifact_id)).decode()}
            raise AppError('BROWSER_CAPABILITY_UNSUPPORTED')
        except BrowserWorkerError: raise AppError('BROWSER_CONTROL_UNAVAILABLE') from None
        finally: entry.lock.release()

    def close(self):
        self.stopping.set()
        with self.lock: entries = list(self.entries.values())
        for entry in entries:
            with entry.lock: entry.worker.close()
