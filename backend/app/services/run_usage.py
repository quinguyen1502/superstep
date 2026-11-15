"""Per-run model usage rows from a run's events: one row per node, kind (llm, embedding, review), model and provider.

The same events give the run's `tokens_in`, `tokens_out` and `cost_usd` (telemetry.summarize), so the rows of a run
add up to its totals. A workflow tool's child run writes its own rows; the parent's `workflow` usage is skipped."""
from __future__ import annotations
import json, logging, time
from typing import Any, Optional
from .telemetry import is_llm_code

log = logging.getLogger("studio.usage")
KINDS = ("llm", "embedding", "review")


def usage_rows(events: list[dict]) -> list[dict]:
    rows: dict[tuple, dict] = {}

    def add(node: Optional[str], kind: str, u: dict, errors: int = 0) -> None:
        key = (node or "", kind, str(u.get("model") or "unknown"), str(u.get("provider") or "unknown"))
        r = rows.setdefault(key, {"node_id": key[0], "kind": kind, "model": key[2], "provider": key[3], "tokens_in": 0, "tokens_out": 0,
                                  "cost_usd": 0.0, "calls": 0, "errors": 0, "duration_ms": 0.0})
        r["tokens_in"] += int(u.get("tokens_in") or 0); r["tokens_out"] += int(u.get("tokens_out") or 0)
        if errors: r["errors"] += errors
        else:
            r["calls"] += 1
            r["cost_usd"] = None if r["cost_usd"] is None or u.get("cost_usd") is None else round(r["cost_usd"] + u["cost_usd"], 8)
        r["duration_ms"] = round(r["duration_ms"] + float(u.get("duration_ms") or 0), 2)

    for ev in events:
        t, u = ev.get("type"), ev.get("usage")
        if t == "node_finished":
            if u and u.get("provider") != "workflow": add(ev.get("node"), "llm", u)
            if (e := ev.get("embedding_usage")): add(ev.get("node"), "embedding", e)
            for a in ev.get("model_attempts") or []:
                if isinstance(a, dict) and a.get("status") == "error": add(ev.get("node"), "llm", a, errors=1)
        elif t == "approval_review" and u and u.get("provider") != "workflow": add(ev.get("node"), "review", u)
        elif t == "error" and not ev.get("model_attempts") and is_llm_code(ev.get("code")): add(ev.get("node"), "llm", ev, errors=1)
    return list(rows.values())


def write(repo, run_id: str, workflow_id: Optional[str], owner: Optional[str], events: list[dict], ended: Optional[float] = None) -> int:
    """Replace the run's rows; never raises (usage rows must not fail a run)."""
    try: return repo.replace(run_id, workflow_id or "adhoc", owner or None, ended or time.time(), usage_rows(events))
    except Exception:
        log.exception("writing usage rows for run %s failed", run_id); return 0


def backfill(repo, days: int, batch: int = 200) -> dict:
    """Rows for finished runs of the last `days` days that have none, from `runs.events` (admin command). Walks the runs
    by end time, so a run with no model usage is read once and left without rows."""
    after = time.time() - days * 86400; runs = rows = 0; strict = False
    while True:
        todo = repo.runs_without_rows(after, batch, strict)
        for rid, wid, owner, events, ended in todo:
            try: evs: Any = json.loads(events or "[]")
            except ValueError: evs = []
            rows += write(repo, rid, wid, owner, evs if isinstance(evs, list) else [], ended); runs += 1
        if len(todo) < batch: break
        after, strict = todo[-1][4], True
    return {"runs": runs, "rows": rows}
