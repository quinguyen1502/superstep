"""Runtime: stream a compiled workflow as trace events (node_started / node_finished / error / run_finished)."""
from __future__ import annotations
import json, time
from typing import Any, Dict, List, Optional
from langgraph.checkpoint.memory import InMemorySaver
from .compiler import compile_workflow
from . import agents, foreach, browser_recipes, browser_presentation, dataset_nodes
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
    browser_recipes.validate_input(wf,inputs)
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
    {node, nodes, state, checkpoint} before the next superstep starts. None runs to the end.
    A superstep that is only Start does not count, so the first step still reaches the first working node.
    until: pause after this node has finished. If the run ends without it, yield RUN_NODE_NOT_REACHED.
    resume = {"node" | "nodes", "state", "counts"?, "value"?} continues at that node (or those parallel nodes) with the
    saved state: with "value" a paused Human node gets its response; without it the run continues from a
    progress checkpoint (recovery of queue jobs, ).
    Progress checkpoints come from LangGraph itself: the graph is compiled with an in-memory saver and its
    superstep checkpoints are observed (`stream_mode="checkpoints"`), so a step with several parallel nodes (fan-out)
    is resumable too. Each yields `_checkpoint` {node, nodes, state, counts}; callers must not forward it to clients.
    effects: idempotency keys + node-result ledger + fencing guard for side-effect nodes.
    ports: user-bound services for Retriever / MCP nodes (engine.ports.Ports)."""
    if resume is None and (bad := check_input(wf, inputs)): raise ValidationError(bad)
    wf = agents.expand(wf)  # usually expanded already by the run service (idempotent, )
    if until and any(n["id"] == until and n.get("type") == "agent" for n in wf["nodes"]): until = f"{until}{agents.SEP}{agents.EXIT}"  # the whole agent
    usage: Dict[str, Dict[str, Any]] = {}  # node id -> usage since its last node_finished
    embedding: Dict[str, Dict[str, Any]] = {}  # node id -> embedding usage (Retriever, knowledge tools) since then

    def add_usage(nid: str, u: Dict[str, Any]) -> None:
        into = embedding if u.get("kind") == "embedding" else usage
        into[nid] = merge_usage(into.get(nid), u)
    code_out: Dict[str, Dict[str, Any]] = {}  # node id -> Code node stdout/runtime since its last node_finished
    model_attempts: Dict[str, List[dict]] = {}
    held = None
    if resume and ("value" in resume or resume.get("answers") or resume.get("children")):
        held = {k: resume[k] for k in ("node", "value", "answers", "children") if k in resume}
        if isinstance(held.get("answers"), dict): held["answers"] = dict(held["answers"])
        if isinstance(held.get("children"), dict): held["children"] = dict(held["children"])
    counts: Dict[str, int] = {k: int(v) for k, v in ((resume or {}).get("counts") or {}).items()}
    if effects is not None: effects.counts = counts  # node iterations feed the idempotency keys
    app = compile_workflow(wf, resolve, add_usage,
                           entry=resume_nodes(resume) if resume else None, resume=held, effects=effects, checkpointer=InMemorySaver(), ports=ports)
    nodes = {n["id"]: n for n in wf["nodes"]}
    if until is not None and until not in nodes:
        raise ValidationError([f"Node '{until}' is not in the workflow"])
    if resume: inputs = dict(resume.get("state") or {})
    elif agents.START_INPUT in inputs:  # private from here on, so the state and the trace never show it
        go = inputs[agents.START_INPUT]
        inputs = {k: v for k, v in inputs.items() if k != agents.START_INPUT}
        if isinstance(go, str) and go: inputs[agents.START_KEY] = go
    state = dict(inputs); cp_state, cp_counts = dict(state), dict(counts); first = True

    browser_private = browser_presentation.private_workflow(wf, ports)
    # Dataset tool messages are private to the agent and its recovery checkpoint.
    dataset_agent = any("filter_ops" in binding for binding in dataset_nodes.bindings(wf).values())
    def meta(nid):
        return {"node": nid, "label": nodes[nid]["data"].get("label"), "node_type": nodes[nid]["type"],
                **({'browser_private': True} if browser_private else {})}

    def dataset_summary(nid, delta=None, *, failed=False):
        node = nodes.get(nid)
        if node is None or node["type"] != "dataset":
            return {}
        data = node["data"]
        result = (delta or {}).get(data.get("output_field"), {})
        operation = data["operation"]
        count = 0 if failed else len(result.get("items", [])) if operation == "find_rows" else 1
        outcome = "failed" if failed else "simulated" if result.get("dry_run") else "completed"
        return {"dataset": {"id": data["dataset_id"], "operation": operation, "count": count, "outcome": outcome}}

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
            if mode == "custom":  # live LLM text: sent to the client, never stored (node_finished has the result)
                if isinstance(chunk, dict) and chunk.get("node") in nodes and chunk.get("model_attempt"):
                    model_attempts.setdefault(chunk["node"], []).append(chunk["model_attempt"])
                elif isinstance(chunk, dict) and chunk.get("node") in nodes and chunk.get("code_output"):
                    code_out[chunk["node"]] = chunk["code_output"]  # Code node stdout, stored on node_finished
                elif isinstance(chunk, dict) and chunk.get("node") in nodes and chunk.get("delta"):
                    yield {"type": "node_token", "node": chunk["node"], "iteration": counts.get(chunk["node"], 1), "delta": chunk["delta"],
                           "field": nodes[chunk["node"]]["data"].get("output_field")}  # the state field the text goes to (a chat's reply, )
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
                       "input": cap_payload(agents.visible(before) if dataset_agent else before), "delta": cap_payload(agents.visible(delta)),
                       **({'browser': browser_presentation.detail(nodes[nid]['data'].get('tool'), delta.get(nodes[nid]['data'].get('output_field')) or {})}
                          if nodes[nid]['type'] == 'mcp' and browser_private and ports is not None and ports.browser is not None and ports.browser.is_browser(nodes[nid]['data'].get('server_id')) else {}),  # input: time travel forks from it
                       **dataset_summary(nid, delta),
                       **({"agent": cap_payload(step)} if (step := agents.step_of(delta)) else {}),  # what an agent step did
                       **({"usage": usage.pop(nid)} if nid in usage else {}), **({"embedding_usage": embedding.pop(nid)} if nid in embedding else {}), **({"reused": True} if reused else {}),
                       **({"model_attempts": model_attempts.pop(nid)} if nid in model_attempts else {}),
                       **({"code_output": cap_payload(code_out.pop(nid))} if nid in code_out else {})}
    except Interrupt as i:  # a Human node or an Agent tool approval is waiting: hand back a checkpoint instead of an error
        # parallel siblings finish first (Interrupt is a GraphBubbleUp) and come back from the ledger on resume
        holds = _holds(effects, i)
        primary = next((h for h in holds if h["kind"] == "approval"), holds[0])
        cp = {"node": primary["node"], "nodes": pending or [primary["node"]], "state": cp_state, "counts": cp_counts}
        browser_intents={hold['node']:hold['browser_intent'] for hold in holds if hold.get('browser_intent')}
        if browser_intents:cp['browser_intents']=browser_intents
        if len(holds)==1 and primary.get('browser_intent'):cp['browser_intent']=primary['browser_intent']
        if len(holds) > 1: cp["waits"] = holds  # one resume after every wait of this superstep
        elif holds[0]["kind"] == "child": cp["wait"] = {"kind": "child", "run_id": holds[0]["run_id"]}
        extra = {k: primary[k] for k in ("label", "tool", "arguments", "workflow_id", "browser_intent") if primary.get(k) is not None}
        if len(holds) == 1 and primary["kind"] == "child": extra["wait"] = {"kind": "child", "run_id": primary["run_id"]}
        yield {"type": "run_waiting", **meta(primary["node"]), "prompt": primary.get("prompt") or "",
               **{k: cap_payload(v) for k, v in extra.items()}, "state": cap_payload(agents.visible(state)), "checkpoint": cp,
               **({'browser': browser_presentation.facts({'operation': primary.get('tool'), 'status': 'approval_required'})} if primary.get('browser_intent') else {})}
        return
    except Exception as e:  # attribute runtime failures to the node that was running
        if getattr(e, "fenced", False): raise  # this worker lost the run: the service layer stops without writing
        nid = pending[-1] if pending else None
        yield {"type": "error", **(meta(nid) if nid in nodes else {}), "iteration": counts.get(nid, 1) if nid else None,
               "duration_ms": round((time.perf_counter() - t0) * 1000, 2), "input": cap_payload(dict(state)),
               "code": getattr(e, "code", "NODE_FAILED"), "errors": [safe_error(e)],
               **dataset_summary(nid, failed=True),
               **_provider_of(e, nodes[nid]["data"] if nid in nodes else {}),
               **({"browser": e.browser} if isinstance(getattr(e, "browser", None), dict) else {}),
               **({"model_attempts": model_attempts.pop(nid)} if nid in model_attempts else {}),
               **({"code_output": cap_payload(e.output)} if getattr(e, "output", None) else {})}
        return
    if until and until not in finished_ids:
        msg = f"The run finished without reaching node '{until}'"
        yield {"type": "error", "node": until, "code": "RUN_NODE_NOT_REACHED", "errors": [msg],
               "error": {"code": "RUN_NODE_NOT_REACHED", "message": msg, "details": {"node": until}}}
        return
    try:final=browser_recipes.outputs(wf,agents.visible(foreach.visible(state)))
    except Exception as error:
        yield {'type':'error','code':getattr(error,'code','NODE_FAILED'),'errors':[safe_error(error)]}
        return
    yield {"type": "run_finished", "state": final}


def _holds(effects, i: Interrupt) -> List[dict]:
    """Every pause of the superstep. Slots record theirs before raising; the exception covers a pause that did not."""
    found: Dict[str, dict] = {}
    if effects is not None:
        for h in effects.holds:
            if isinstance(h, dict) and h.get("node"): found[str(h["node"])] = h
    if i.node not in found:
        extra = i.extra or {}
        wait = extra.get("wait") if isinstance(extra.get("wait"), dict) else {}
        if wait.get("kind") == "child":
            found[i.node] = {"node": i.node, "kind": "child", "run_id": wait.get("run_id"), "prompt": i.prompt,
                             **{k: extra[k] for k in ("label", "tool", "arguments", "workflow_id", "browser_intent") if k in extra}}
        else:
            found[i.node] = {"node": i.node, "kind": "approval", "prompt": i.prompt,
                             **{k: extra[k] for k in ("label", "tool", "arguments", "browser_intent") if k in extra}}
    return list(found.values())


def resume_nodes(resume: Dict[str, Any]) -> List[str]:
    """Entry nodes of a resume/recovery checkpoint (older checkpoints only have "node")."""
    return list(resume.get("nodes") or [resume["node"]])


def _provider_of(e: Exception, data: dict) -> dict:
    """Provider and model of a failed model call (a ProviderError), for the run's metrics; nothing for other errors."""
    params = getattr(e, "params", None)
    if not isinstance(params, dict) or not isinstance(params.get("provider"), str): return {}
    return {"provider": params["provider"], "model": params.get("model") or data.get("model") or ""}
