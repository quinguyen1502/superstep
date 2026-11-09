"""Executed INSIDE the imported repo's own venv, in a subprocess. Never imported by the server.
Usage: python runner.py inspect <repo_dir> <file.py:var>
       python runner.py run <repo_dir> <file.py:var>   (input JSON on stdin)
Writes one JSON object per line to stdout."""
import asyncio, importlib.util, inspect, json, os, sys, time, traceback

def emit(o):
    sys.stdout.write(json.dumps(o, default=_ser, ensure_ascii=False) + "\n"); sys.stdout.flush()

def _ser(o):
    for m in ("model_dump", "dict"):
        f = getattr(o, m, None)
        if callable(f):
            try: return f()
            except Exception: pass
    if hasattr(o, "__dataclass_fields__"):
        import dataclasses; return dataclasses.asdict(o)
    return str(o)

def load_graph(repo, ref):
    path, _, var = ref.rpartition(":")
    path = os.path.normpath(os.path.join(repo, path))
    for p in (repo, os.path.join(repo, "src"), os.path.dirname(path)):
        if p not in sys.path: sys.path.insert(0, p)
    try:
        from dotenv import load_dotenv; load_dotenv(os.path.join(repo, ".env"))
    except Exception: pass
    rel = os.path.relpath(path, repo)
    modname = rel[:-3].replace(os.sep, ".")
    if modname.startswith("src."): modname = modname[4:]
    try:
        mod = importlib.import_module(modname)
    except Exception:
        spec = importlib.util.spec_from_file_location("_imported_graph", path)
        mod = importlib.util.module_from_spec(spec); sys.modules["_imported_graph"] = mod; spec.loader.exec_module(mod)
    g = getattr(mod, var)
    if not hasattr(g, "get_graph") and callable(g):
        g = g({}) if len(inspect.signature(g).parameters) else g()
        if inspect.isawaitable(g): g = asyncio.run(g)
    return g

LLM_HINTS = ("ChatOpenAI", "ChatAnthropic", "init_chat_model", "load_chat_model", "bind_tools", "llm.invoke", "model.invoke", "ainvoke(")

def node_info(g, name):
    info = {"ref": None, "source": None, "is_llm": False, "kind": None}
    try:
        spec = g.builder.nodes[name]
        r = spec.runnable
        info["kind"] = type(r).__name__
        fn = getattr(r, "func", None) or getattr(r, "afunc", None) or r
        if type(r).__name__ == "ToolNode":
            info["source"] = "ToolNode(tools=[" + ", ".join(getattr(r, "tools_by_name", {}) or []) + "])"
            info["ref"] = "langgraph.prebuilt.ToolNode"; info["kind"] = "ToolNode"
        else:
            target = inspect.unwrap(fn)
            info["ref"] = f"{getattr(target, '__module__', '?')}:{getattr(target, '__qualname__', type(target).__name__)}"
            try: info["source"] = inspect.getsource(target)
            except Exception: info["source"] = repr(target)
        info["is_llm"] = any(h in (info["source"] or "") for h in LLM_HINTS)
    except Exception as e:
        info["source"] = f"(source unavailable: {e})"
    return info

def schema_fields(g):
    out = []
    for getter in ("get_input_jsonschema", "get_output_jsonschema"):
        try:
            props = getattr(g, getter)().get("properties", {})
            for k, v in props.items():
                if k not in [f["name"] for f in out]:
                    out.append({"name": k, "type": {"string": "string", "number": "number", "integer": "integer", "boolean": "boolean", "array": "list", "object": "object"}.get(v.get("type"), "object")})
        except Exception: pass
    return out

def inspect_graph(repo, ref):
    g = load_graph(repo, ref)
    try: dg = g.get_graph(xray=True); xray = True
    except Exception: dg = g.get_graph(); xray = False
    nodes = []
    for nid, n in dg.nodes.items():
        base = nid.split(":")[-1]
        info = node_info(g, nid) if nid not in ("__start__", "__end__") else {}
        nodes.append({"id": nid, "name": getattr(n, "name", nid), "subgraph": ":" in nid, **info})
    edges = [{"source": e.source, "target": e.target, "conditional": bool(e.conditional), "label": (str(e.data) if e.data is not None else None)} for e in dg.edges]
    emit({"type": "graph", "name": getattr(g, "name", None), "xray": xray, "nodes": nodes, "edges": edges,
          "state": schema_fields(g), "input_schema": _safe(lambda: g.get_input_jsonschema())})

def _safe(f):
    try: return f()
    except Exception: return None

KEY_HINTS = ("API_KEY", "api_key", "API key", "credentials")

CHECKPOINT_MAX = 2_000_000  # bytes of a serialized checkpoint; larger ones are skipped (recovery restarts instead)


def attach_saver(g):
    """Progress checkpoints: give a graph WITHOUT its own checkpointer an in-memory LangGraph saver, so its
    superstep checkpoints can be serialized to the server and restored in a fresh subprocess. None when not possible."""
    if getattr(g, "checkpointer", None) is not None: return None  # the repo manages its own persistence
    try:
        try: from langgraph.checkpoint.memory import InMemorySaver as Saver
        except ImportError: from langgraph.checkpoint.memory import MemorySaver as Saver
        saver = Saver(); g.checkpointer = saver; return saver
    except Exception: return None


def dump_checkpoint(saver, cfg):
    import base64
    t = saver.get_tuple(cfg)
    if t is None: return None
    typ, data = saver.serde.dumps_typed((t.checkpoint, t.metadata))
    return None if len(data) > CHECKPOINT_MAX else {"type": typ, "data": base64.b64encode(data).decode()}


def load_checkpoint(saver, blob):
    import base64
    cp, md = saver.serde.loads_typed((blob["type"], base64.b64decode(blob["data"])))
    saver.put({"configurable": {"thread_id": "studio", "checkpoint_ns": ""}}, cp, md, cp.get("channel_versions") or {})


async def run_graph(repo, ref, inp):
    g = load_graph(repo, ref)
    ctx = inp.pop("__context__", None)
    resume = inp.pop("__resume__", None); saver = attach_saver(g) if (inp.pop("__checkpointing__", False) or resume) else None
    cfg = {"configurable": {"thread_id": "studio"}} if saver else None
    if resume and saver: load_checkpoint(saver, resume); inp = None  # continue the stored checkpoint
    elif resume: emit({"type": "_restart"})  # cannot restore here: the server notes it and the graph starts over
    if inp is not None:
        emit({"type": "node_started", "node": "__start__"}); emit({"type": "node_finished", "node": "__start__", "duration_ms": 0, "delta": inp})
    starts = {}; final = None
    kw = {"stream_mode": ["debug", "values"], **({"config": cfg} if cfg else {})}
    if saver is not None and "durability" in inspect.signature(g.astream).parameters:
        kw["durability"] = "sync"  # each checkpoint is saved before the next step starts, so it can be read right away
    cs = getattr(g, "context_schema", None) or getattr(getattr(g, "builder", None), "context_schema", None)
    if cs is not None and hasattr(cs, "__dataclass_fields__"):
        try: ctx = cs(**(ctx or {}))  # dataclass context with defaults (e.g. react-agent)
        except Exception: pass
    if ctx is not None: kw["context"] = ctx
    async for mode, chunk in g.astream(inp, **kw):
        if mode == "values": final = chunk; continue
        t, p = chunk.get("type"), chunk.get("payload", {})
        if t == "checkpoint" and saver is not None:
            nxt = [n for n in (p.get("next") or []) if n != "__start__"]
            if nxt:
                try: blob = dump_checkpoint(saver, cfg)
                except Exception: blob = None  # unserializable state: no checkpoint for this step
                if blob: emit({"type": "_checkpoint", "node": nxt[0], "nodes": nxt, "blob": blob})
            continue
        if t == "task":
            starts[p.get("id")] = time.perf_counter(); emit({"type": "node_started", "node": p.get("name")})
        elif t == "task_result":
            t0 = starts.pop(p.get("id"), time.perf_counter())
            res = p.get("result")
            delta = dict(res) if isinstance(res, list) else (res or {})
            if p.get("error"): emit({"type": "error", "node": p.get("name"), "errors": [str(p.get("error"))]}); continue
            emit({"type": "node_finished", "node": p.get("name"), "duration_ms": round((time.perf_counter() - t0) * 1000, 2), "delta": delta})
    emit({"type": "node_started", "node": "__end__"}); emit({"type": "node_finished", "node": "__end__", "duration_ms": 0, "delta": {}})
    emit({"type": "run_finished", "state": final})

def main():
    mode, repo, ref = sys.argv[1:4]
    try:
        if mode == "inspect": inspect_graph(repo, ref)
        else: asyncio.run(run_graph(repo, ref, json.loads(sys.stdin.read() or "{}")))
    except BaseException as e:
        msg = f"{type(e).__name__}: {e}"
        if any(h in msg for h in KEY_HINTS) or "environment variable" in msg.lower():
            msg = "Missing environment variable / API key for the imported repo: " + msg
        emit({"type": "error", "errors": [msg], "trace": traceback.format_exc()[-3000:]}); sys.exit(1)

if __name__ == "__main__":
    main()
