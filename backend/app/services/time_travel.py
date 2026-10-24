"""Time travel (fork from a checkpoint): the checkpoints of a finished run, read back from its event log.

Every `node_finished` event carries the state the node started from (`input`). Nodes that started from the same
state in a row ran in the same superstep, so they form one checkpoint: {nodes that ran next, state before them,
iteration counts}. Forking a checkpoint starts a new run at those nodes with that state (optionally edited), the
same way a recovered or resumed run continues (engine.runtime.run_stream `resume`). The last entry is the run's
final state, for inspection only. Pure functions: no I/O.
"""
from __future__ import annotations
from typing import Any, Optional

SKIP = ("start", "end")


def _truncated(state: Any) -> bool:
    return isinstance(state, dict) and bool(state.get("_truncated"))


def checkpoints(events: list, final_state: Optional[dict] = None) -> list[dict]:
    out: list[dict] = []; cur: Optional[dict] = None; counts: dict[str, int] = {}
    for ev in events or []:
        t = ev.get("type")
        if t in ("run_resumed", "run_recovered"): cur = None  # a new segment starts a new superstep
        if t != "node_finished" or ev.get("node_type") in SKIP: continue
        node, state = ev.get("node"), ev.get("input")
        if cur is not None and cur["state"] == state and node not in cur["nodes"]:
            cur["nodes"].append(node); cur["labels"].append(ev.get("label") or node)
        else:
            cur = {"index": len(out), "nodes": [node], "labels": [ev.get("label") or node], "state": state, "counts": dict(counts),
                   "ts": ev.get("ts"), "forkable": isinstance(state, dict) and not _truncated(state)}
            out.append(cur)
        counts[node] = int(ev.get("iteration") or counts.get(node, 0) + 1)
    if final_state is not None:
        out.append({"index": len(out), "nodes": [], "labels": [], "state": final_state, "counts": dict(counts), "ts": None, "forkable": False, "final": True})
    return out
