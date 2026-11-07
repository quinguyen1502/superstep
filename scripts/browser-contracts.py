#!/usr/bin/env python3
"""Generate worker JSON schemas from the same Python contract used by services."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.engine.browser_contract import WorkerCommand, WorkerOpen, WorkerControl, WorkerArtifact, WorkerResult, WorkerRenew, WorkerTarget, WorkerApproval, WorkerSupervisor


def schemas():
    return {model.__name__: model.model_json_schema() for model in
            (WorkerCommand, WorkerOpen, WorkerControl, WorkerArtifact, WorkerResult, WorkerRenew, WorkerTarget, WorkerApproval, WorkerSupervisor)}


if __name__ == "__main__":
    target = ROOT / "docker/browser-worker/contracts.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(schemas(), indent=2, ensure_ascii=False) + "\n")
