"""Runtime: stream a compiled workflow as trace events (node_started / node_finished / error / run_finished)."""
from __future__ import annotations
import json, time
from typing import Any, Dict, List, Optional
from langgraph.checkpoint.memory import InMemorySaver
from .compiler import compile_workflow
from . import agents, foreach
from .effects import Effects
from .errors import Interrupt, ValidationError
from .issues import Issue
from .limits import safe_error
from .reducers import apply as apply_delta
from .usage import merge as merge_usage
from ..core.config import recursion_limit

TRACE_CAP = 16_000  # max JSON chars per traced payload (input/delta) in an event


def cap_payload(obj: Any, limit: int = TRACE_CAP) -> Any:
    """Return obj unchanged if its JSON is small, else a truncated preview marker."""
    try:
        txt = json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        txt = str(obj)
    if len(txt) <= limit: return obj
    return {"_truncated": True, "size": len(txt), "preview": txt[:limit]}


PY_TYPES = {"number": (int, float), "integer": (int,), "boolean": (bool,), "list": (list,), "object": (dict,), "string": (str,)}


def check_input(wf: Dict[str, Any], inputs: Any) -> List[str]:
    """Run input must be a JSON object whose known fields match the state schema types."""
    if not isinstance(inputs, dict): return [Issue("INPUT_NOT_OBJECT")]
    errs = []
    for f in wf.get("state", []) or []:
        name, typ = f.get("name"), f.get("type", "string")
        if name in inputs and inputs[name] is not None and typ in PY_TYPES:
            v = inputs[name]; ok = isinstance(v, PY_TYPES[typ]) and not (typ in ("number", "integer") and isinstance(v, bool))
            if not ok: errs.append(Issue("INPUT_TYPE", field=name, type=typ, got=type(v).__name__))
    return errs


def run_stream(wf: Dict[str, Any], inputs: Dict[str, Any], resolve=None, resume: Dict[str, Any] | None = None,
               effects: Optional[Effects] = None, ports=None, steps: Optional[int] = None, until: Optional[str] = None):
    """Yield per-node events: started / finished(duration, input=state before, delta=output) / error. Sync generator.
    A Human node without a response yields `run_waiting` {node, prompt, checkpoint} and stops.
    steps: stop after this many supersteps that contain a node other than Start or End, yielding `run_paused`
    {node, nodes, state, checkpoint} before the next superstep starts (TASK-0036). None runs to the end.
    A superstep that is only Start does not count, so the first step still reaches the first working node.
    until: pause after this node has finished. If the run ends without it, yield RUN_NODE_NOT_REACHED.
    resume = {"node" | "nodes", "state", "counts"?, "value"?} continues at that node (or those parallel nodes) with the
    saved state: with "value" a paused Human node gets its response (TASK-0006); without it the run continues from a
    progress checkpoint (recovery of queue jobs, TASK-0020).
    Progress checkpoints come from LangGraph itself (TASK-0021): the graph is compiled with an in-memory saver and its
    superstep checkpoints are observed (`stream_mode="checkpoints"`), so a step with several parallel nodes (fan-out)
    is resumable too. Each yields `_checkpoint` {node, nodes, state, counts}; callers must not forward it to clients.
    effects: idempotency keys + node-result ledger + fencing guard for side-effect nodes (TASK-0021).
    ports: user-bound services for Retriever / MCP nodes (engine.ports.Ports)."""
    if resume is None and (bad := check_input(wf, inputs)): raise ValidationError(bad)
    wf = agents.expand(wf)  # usually expanded already by the run service (idempotent, TASK-0116)
    if until and any(n["id"] == until and n.get("type") == "agent" for n in wf["nodes"]): until = f"{until}{agents.SEP}{agents.EXIT}"  # the whole agent
    usage: Dict[str, Dict[str, Any]] = {}  # node id -> usage since its last node_finished (TASK-0010)
    code_out: Dict[str, Dict[str, Any]] = {}  # node id -> Code node stdout/runtime since its last node_finished (TASK-0053)
    held = {"node": resume["node"], "value": resume["value"]} if resume and "value" in resume else None
    counts: Dict[str, int] = {k: int(v) for k, v in ((resume or {}).get("counts") or {}).items()}
    if effects is not None: effects.counts = counts  # node iterations feed the idempotency keys
    app = compile_workflow(wf, resolve, lambda nid, u: usage.__setitem__(nid, merge_usage(usage.get(nid), u)),
                           entry=resume_nodes(resume) if resume else None, resume=held, effects=effects, checkpointer=InMemorySaver(), ports=ports)
    nodes = {n["id"]: n for n in wf["nodes"]}
    if until is not None and until not in nodes:
        raise ValidationError([f"Node '{until}' is not in the workflow"])
    if resume: inputs = dict(resume.get("state") or {})
    state = dict(inputs); cp_state, cp_counts = dict(state), dict(counts); first = True

    def meta(nid):
        return {"node": nid, "label": nodes[nid]["data"].get("label"), "node_type": nodes[nid]["type"]}

    def started(nid):
        counts[nid] = counts.get(nid, 0) + 1
        return {"type": "node_started", **meta(nid), "iteration": counts[nid]}

    t0 = time.perf_counter(); pending: List[str] = []; done_steps = 0; finished_ids: set[str] = set()
    superstep = 0  # numbers this segment's supersteps on node_finished: nodes with the same number ran in parallel (time travel)
    cfg = {"recursion_limit": recursion_limit() + foreach.step_budget(wf) + agents.step_budget(wf),  # For each loops and agents add steps
           "configurable": {"thread_id": "run"}}

    def counts_as_step(ids: List[str]) -> bool:
        return any(nodes[n]["type"] not in ("start", "end") for n in ids)

    try:
        for mode, chunk in app.stream(inputs, cfg, stream_mode=["updates", "checkpoints", "custom"]):
            if mode == "custom":  # live LLM text (TASK-0030): sent to the client, never stored (node_finished has the result)
                if isinstance(chunk, dict) and chunk.get("node") in nodes and chunk.get("code_output"):
                    code_out[chunk["node"]] = chunk["code_output"]  # Code node stdout (TASK-0053), stored on node_finished
                elif isinstance(chunk, dict) and chunk.get("node") in nodes and chunk.get("delta"):
                    yield {"type": "node_token", "node": chunk["node"], "iteration": counts.get(chunk["node"], 1), "delta": chunk["delta"],
                           "field": nodes[chunk["node"]]["data"].get("output_field")}  # the state field the text goes to (a chat's reply, TASK-0084)
                continue
            if mode == "checkpoints":  # superstep boundary: the nodes that run next, all inputs settled
                nxt = [n for n in (chunk.get("next") or []) if n in nodes]
                if not nxt: continue
                if counts_as_step(pending): done_steps += 1  # the superstep that just finished
                # pause before this superstep starts: step budget spent, or the chosen node just finished
                if (steps is not None and done_steps >= steps) or (until is not None and until in pending):
                    yield {"type": "run_paused", "node": nxt[0], "nodes": nxt, "state": cap_payload(agents.visible(state)),
                           "checkpoint": {"node": nxt[0], "nodes": nxt, "state": dict(state), "counts": dict(counts)}}
                    return
                cp_state, cp_counts = dict(state), dict(counts)
                if not first and any(nodes[n]["type"] not in ("start", "end") for n in nxt):
                    yield {"type": "_checkpoint", "node": nxt[0], "nodes": nxt, "state": dict(state), "counts": dict(counts)}
                first = False; pending = nxt; t0 = time.perf_counter(); superstep += 1
                for n2 in nxt: yield started(n2)
                continue
            before = dict(state)
            for nid, delta in chunk.items():
                if nid not in nodes: continue
                delta = delta or {}
                state = apply_delta(state, delta, wf.get("state") or [])
                reused = effects is not None and nid in effects.reused
                if reused: effects.reused.discard(nid)
                finished_ids.add(nid)
                yield {"type": "node_finished", **meta(nid), "iteration": counts.get(nid, 1), "superstep": superstep,
                       "duration_ms": round((time.perf_counter() - t0) * 1000, 2),
                       "input": cap_payload(before), "delta": cap_payload(agents.visible(delta)),  # input: time travel forks from it
                       **({"agent": cap_payload(step)} if (step := agents.step_of(delta)) else {}),  # what an agent step did (TASK-0116)
                       **({"usage": usage.pop(nid)} if nid in usage else {}), **({"reused": True} if reused else {}),
                       **({"code_output": cap_payload(code_out.pop(nid))} if nid in code_out else {})}
    except Interrupt as i:  # a Human node or an Agent tool approval is waiting: hand back a checkpoint instead of an error
        # parallel siblings of the Human node resume with it (their results come from the ledger when recorded)
        yield {"type": "run_waiting", **meta(i.node), "prompt": i.prompt, **{k: cap_payload(v) for k, v in i.extra.items()}, "state": cap_payload(agents.visible(state)),
               "checkpoint": {"node": i.node, "nodes": pending or [i.node], "state": cp_state, "counts": cp_counts}}
        return
    except Exception as e:  # attribute runtime failures to the node that was running
        if getattr(e, "fenced", False): raise  # this worker lost the run: the service layer stops without writing
        nid = pending[-1] if pending else None
        yield {"type": "error", **(meta(nid) if nid in nodes else {}), "iteration": counts.get(nid, 1) if nid else None,
               "duration_ms": round((time.perf_counter() - t0) * 1000, 2), "input": cap_payload(dict(state)),
               "code": getattr(e, "code", "NODE_FAILED"), "errors": [safe_error(e)],
               **({"code_output": cap_payload(e.output)} if getattr(e, "output", None) else {})}
        return
    if until and until not in finished_ids:
        msg = f"The run finished without reaching node '{until}'"
        yield {"type": "error", "node": until, "code": "RUN_NODE_NOT_REACHED", "errors": [msg],
               "error": {"code": "RUN_NODE_NOT_REACHED", "message": msg, "details": {"node": until}}}
        return
    yield {"type": "run_finished", "state": agents.visible(foreach.visible(state))}


def resume_nodes(resume: Dict[str, Any]) -> List[str]:
    """Entry nodes of a resume/recovery checkpoint (older checkpoints only have "node")."""
    return list(resume.get("nodes") or [resume["node"]])
