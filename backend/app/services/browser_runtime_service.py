"""Trusted runtime boundary: persist captures before returning any artifact reference.

The run service binds owner, worker and command; there is no public launch/call API.
Session registry/fencing and durable human approval integration are separate tasks.
"""
from ..engine.browser_worker import BrowserWorkerError


class BrowserRuntimeService:
    def __init__(self, artifacts): self.artifacts = artifacts

    def execute(self, owner, worker, command):
        result = worker.call(command)
        if result.status != "confirmed" or result.artifact_id is None: return result
        try:
            png = worker.artifact(result.artifact_id)
            artifact_id = self.artifacts.save(owner, command.context, png)
        except BrowserWorkerError:
            worker.close()
            return result.model_copy(update={"status": "session_lost", "artifact_id": None})
        except Exception:
            worker.close()
            raise
        return result.model_copy(update={"artifact_id": artifact_id})
