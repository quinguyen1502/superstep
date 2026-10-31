"""Export a workflow as one readable, runnable LangGraph Python file (TASK-0070, REQ-0043, DEC-0045).

`to_python` writes the plain LangGraph equivalent of the canvas, for people learning how a graph is written in code:
the state as a `TypedDict`, one function per node, `build_graph()` with `add_node` / `add_edge` /
`add_conditional_edges`, and a `main()` that runs an example. The file imports nothing from Superstep; it runs with
`pip install langgraph`, offline with a mock model unless `LLM_PROVIDER` is set (owner, REQ-0043 Q1).

The graph is read through `templates.sanitize`, so no credential, knowledge base, server, channel, approver or
secret-like value reaches the file. Retriever, MCP and Send email nodes call stubs (they need studio services).
A Subgraph node becomes its child workflow's own compiled graph, added as a node (Q3). An Agent node becomes the
studio's own expansion (TASK-0119, DEC-0063): an entry node, a model node and a tool node in a loop with two routers,
and an end node; approval is `interrupt()`, and its knowledge base and MCP tools use the same stubs. Comments are
English (Q2).
The output is a pure function of its input: the same graph gives the same bytes.
"""
from __future__ import annotations
import ast, builtins, inspect, io, json, keyword, re, tokenize
from typing import Any, Dict, List, Optional
from . import agents, approval_policy, attachments, foreach
from .export_common import (TITLES, RECURSION, Export, Graph as _Graph, GraphWriter, camel as _camel, number as _number,
                            one_line as _one_line, slug)
from .templating import VAR_RE, _ONE_FILTER, refs
from .tools import TOOLS

PY_TYPES = {"string": "str", "number": "float", "integer": "int", "boolean": "bool", "object": "dict", "list": "list"}
REDUCERS = {"append": "append_items", "merge": "merge_objects", "add": "add_numbers"}

# names the file defines or imports: node functions never take them
RESERVED = set(dir(builtins)) | set(keyword.kwlist) | set(keyword.softkwlist) | {
    "annotations", "json", "os", "re", "string", "httpx", "Annotated", "Any", "Optional", "TypedDict", "StateGraph",
    "START", "END", "Command", "interrupt", "MemorySaver", "RetryPolicy", "CachePolicy", "InMemoryCache", "State",
    "VAR_RE", "FILTER_RE", "FILTERS", "render", "render_args", "LLM_PROVIDER", "DECISION_MODEL", "mock_llm",
    "call_llm", "pick_branch", "decide", "retrieve", "call_mcp_tool", "send_email", "addresses", "build_graph",
    "EXAMPLE_INPUT", "EXAMPLE_ANSWERS", "main", "graph", "builder", "time", "MAX_CALLS_PER_ROUND", "RESULT_CHARS", "STEP_CHARS",
    "JSON_TYPES", "agent_task", "mock_agent", "call_agent", "is_image", "with_files", "files_note", "call_llm_files", "call_agent_files", "check_arguments", "tool_text", "shorten", *REDUCERS.values()}


RULE = re.compile(r"# --- (.+?) -+")
WIDTH = 117


def _rule(title: str) -> str:
    """A section heading comment as wide as the code."""
    return f"# --- {title} ".ljust(WIDTH, "-")


def _doc(text: Any) -> str:
    """Text safe inside a docstring or a comment."""
    return _one_line(text).replace("\\", "\\\\").replace('"""', "'''")


def lit(v: Any, indent: str = "") -> str:
    """A Python literal for `v` in double quotes; multi-line text as a triple-quoted string when that keeps it exact.
    Objects and lists that do not fit on one line get one item per line."""
    if isinstance(v, str):
        if ("\n" in v and '"""' not in v and "\\" not in v and not v.endswith('"')
                and all(c.isprintable() or c == "\n" for c in v)):
            return '"""' + v + '"""'
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool) or v is None or isinstance(v, (int, float)): return repr(v)
    if isinstance(v, dict):
        items = [f"{lit(str(k))}: {lit(x, indent + '    ')}" for k, x in v.items()]
        one = "{" + ", ".join(items) + "}"
        if len(one) + len(indent) <= 100 and "\n" not in one: return one
        return "{\n" + "".join(f"{indent}    {i},\n" for i in items) + indent + "}"
    if isinstance(v, (list, tuple)):
        items = [lit(x, indent + "    ") for x in v]
        one = "[" + ", ".join(items) + "]"
        if len(one) + len(indent) <= 100 and "\n" not in one: return one
        return "[\n" + "".join(f"{indent}    {i},\n" for i in items) + indent + "]"
    return lit(str(v), indent)


def _indent_code(source: str, pad: str = "    ") -> List[str]:
    """`source` indented by `pad`, except the inner lines of multi-line strings (their text must not change)."""
    lines = source.rstrip("\n").split("\n")
    inside: set = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.STRING and tok.end[0] > tok.start[0]:
                inside.update(range(tok.start[0] + 1, tok.end[0] + 1))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return [ln if i in inside or not ln.strip() else pad + ln for i, ln in enumerate(lines, 1)]


# ---- fixed parts of the file ------------------------------------------------------------------------------------

TEMPLATES = '''
# --- Templates -----------------------------------------------------------------------------------------------
# Prompts use {{ state.field }} references, as on the canvas. render() fills them in from the state: a path walks
# into objects and lists ({{ state.order.items.0 }}) and filters change the value ({{ state.name | upper }}).

VAR_RE = re.compile(r"%(var)s")
FILTER_RE = re.compile(r"%(filter)s")


def _text(value: Any) -> str:
    return "" if value is None else value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _truncate(value: Any, n: int) -> str:
    s = _text(value)
    return s if len(s) <= n else s[:max(n - 1, 0)] + "…"


FILTERS = {
    "upper": lambda v, _: _text(v).upper(),
    "lower": lambda v, _: _text(v).lower(),
    "trim": lambda v, _: _text(v).strip(),
    "json": lambda v, _: json.dumps(v, ensure_ascii=False),
    "length": lambda v, _: len(v) if isinstance(v, (str, list, dict)) else 0,
    "first": lambda v, _: v[0] if isinstance(v, (str, list)) and v else None,
    "last": lambda v, _: v[-1] if isinstance(v, (str, list)) and v else None,
    "default": lambda v, a: a if v is None or v == "" else v,
    "join": lambda v, a: a.join(_text(x) for x in v) if isinstance(v, list) else _text(v),
    "truncate": _truncate,
}


def _value(match: re.Match, state: dict) -> Any:
    value = state.get(match.group(1))
    for key in [p for p in match.group(2).split(".") if p]:
        if isinstance(value, dict):
            value = value.get(key)
        elif isinstance(value, list) and key.isdigit() and int(key) < len(value):
            value = value[int(key)]
        else:
            value = None
            break
    for f in FILTER_RE.finditer(match.group(3) or ""):
        raw = f.group(2)
        arg = None if raw is None else raw[1:-1] if raw[0] in "\\"'" else int(raw)
        value = FILTERS[f.group(1)](value, arg)
    return value


def render(template: str, state: dict) -> str:
    """The template with each {{ state.x }} replaced by its value."""
    return VAR_RE.sub(lambda m: _text(_value(m, state)), template or "")


def render_args(args: Any, state: dict) -> Any:
    """render() inside objects and lists; a string that is exactly one reference keeps the value's type."""
    if isinstance(args, dict):
        return {k: render_args(v, state) for k, v in args.items()}
    if isinstance(args, list):
        return [render_args(v, state) for v in args]
    if isinstance(args, str):
        m = VAR_RE.fullmatch(args.strip())
        return _value(m, state) if m else render(args, state)
    return args
''' % {"var": VAR_RE.pattern, "filter": _ONE_FILTER.pattern}
assert all(re.fullmatch(r'(?:[^"\\]|\\.)*', p) for p in (VAR_RE.pattern, _ONE_FILTER.pattern))  # fits in r"..."

MODEL = '''
# --- Model ---------------------------------------------------------------------------------------------------
# LLM nodes call call_llm(). Without configuration it is an offline mock: the file runs anywhere, for free, with the
# same answers every time (the studio's mock model). To call a real model, install LangChain and a provider package,
# then name the provider (any provider init_chat_model knows) and set its API key:
#     pip install langchain langchain-openai
#     export LLM_PROVIDER=openai OPENAI_API_KEY=sk-...
LLM_PROVIDER = os.environ.get("LLM_PROVIDER")


def mock_llm(prompt: str, model: str) -> str:
    """Offline answers: a category for classification prompts, else the last line of the prompt echoed back."""
    p = prompt.lower()
    if "classify" in p or "phân loại" in p:
        msg = p.split("message:")[-1] if "message:" in p else p
        if any(k in msg for k in ["order", "đơn", "giao hàng", "ship", "a100", "b200", "c300"]):
            return "order_status"
        if any(k in msg for k in ["refund", "hoàn tiền", "return"]):
            return "refund"
        return "general"
    tail = prompt.strip().splitlines()[-1] if prompt.strip() else ""
    return f"[mock:{model}] Answer: {tail[:200]}"


def call_llm(prompt: str, model: str) -> str:
    if not LLM_PROVIDER:
        return mock_llm(prompt, model)
    from langchain.chat_models import init_chat_model

    reply = init_chat_model(model, model_provider=LLM_PROVIDER).invoke(prompt)
    if isinstance(reply.content, str):
        return reply.content
    return "".join(b.get("text", "") for b in reply.content if isinstance(b, dict))
'''

FILES = '''
# --- Attachments ---------------------------------------------------------------------------------------------
# Files a chat sent with the message, for nodes with "Include attachments": a list of {name, type, text?, text_cut?,
# data_url?}. A document reaches the model as text after the prompt. An image reaches it only when its record carries
# a data_url ("data:image/png;base64,...") that you supply; otherwise the model gets a note.


def is_image(f: dict) -> bool:
    return str(f.get("type") or "").startswith("image/")


def with_files(prompt: str, files: Any) -> tuple:
    """(text, image parts) of one user message with its files."""
    text, images = [prompt], []
    for f in files if isinstance(files, list) else []:
        if not isinstance(f, dict):
            continue
        name = f.get("name")
        if is_image(f):
            url = f.get("data_url")
            if isinstance(url, str) and url.startswith("data:"):
                images.append({"type": "image_url", "image_url": {"url": url}})
            else:
                text.append(f"An image named {name} was attached, but no image data was given.")
        else:
            body, cut = f.get("text") or "", " (cut)" if f.get("text_cut") else ""
            text.append(f'Attached document "{name}"{cut}:\\n{body}' if body else f'Attached document "{name}" has no text.')
    return "\\n\\n".join(t for t in text if t), images


def files_note(files: Any) -> str:
    """What the offline mock says it received: each file's kind and name."""
    return "Attachments: " + ", ".join(f"{'image' if is_image(f) else 'document'} {f.get('name')}" for f in files if isinstance(f, dict))


def call_llm_files(prompt: str, model: str, files: Any) -> str:
    """call_llm() with the files sent with the message."""
    files = files if isinstance(files, list) else []
    if not LLM_PROVIDER:
        return mock_llm(prompt, model) + (f"\\n{files_note(files)}" if files else "")
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import HumanMessage

    text, images = with_files(prompt, files)
    reply = init_chat_model(model, model_provider=LLM_PROVIDER).invoke([HumanMessage([{"type": "text", "text": text}] + images)] if images else text)
    if isinstance(reply.content, str):
        return reply.content
    return "".join(b.get("text", "") for b in reply.content if isinstance(b, dict))
'''

AGENT_FILES = '''

def call_agent_files(messages: list, tools: Optional[list], model: str) -> tuple:
    """call_agent() for a conversation whose user message carries `files`."""
    files = [f for m in messages if m["role"] == "user" for f in m.get("files") or []]
    if not LLM_PROVIDER:
        text, calls = mock_agent(messages, tools, model)
        return (f"{text}\\n{files_note(files)}" if text and files else text), calls
    out = []
    for m in messages:
        if m.get("files"):
            text, images = with_files(m["content"], m["files"])
            m = {"role": "user", "content": text, "images": images}
        out.append(m)
    return call_agent(out, tools, model)
'''

ROUTING = '''
# --- Routing -------------------------------------------------------------------------------------------------


def pick_branch(value: str, labels: list) -> Optional[str]:
    """The label `value` names: an exact match, then a match ignoring case, spaces and punctuation, then the longest
    label found in it as a whole word. None when no label (or two equally long ones) matches."""
    if value in labels:
        return value
    norm = lambda x: x.strip().strip(string.punctuation + " ").casefold()  # noqa: E731
    for label in labels:
        if norm(label) and norm(label) == norm(value):
            return label
    hits = [k for k in labels if norm(k) and re.search(rf"(?<!\\w){re.escape(norm(k))}(?!\\w)", value.casefold())]
    if not hits:
        return None
    best = max(len(norm(k)) for k in hits)
    top = [k for k in hits if len(norm(k)) == best]
    return top[0] if len(top) == 1 else None
'''

DECIDE = '''
# --- Decisions -----------------------------------------------------------------------------------------------
# In Superstep a Decision node asks TypeSafe's Jev model typed questions. Here the mock answers offline (the first
# option named in the text, the lowest score, 0.5 for yes/no); with LLM_PROVIDER set, call_llm() answers instead.
DECISION_MODEL = os.environ.get("DECISION_MODEL", "gpt-4o-mini")


def decide(text: str, question: dict) -> Any:
    """The answer to one question: an option label ("choice"), a level index ("score") or 0 to 1 ("noul")."""
    kind, instructions = question["type"], question["instructions"]
    if kind == "choice":
        labels = question["options"]
        if not LLM_PROVIDER:
            low = text.casefold()
            return next((x for x in labels if re.search(rf"(?<!\\w){re.escape(x.casefold())}(?!\\w)", low)), labels[0])
        reply = call_llm(f"{instructions}\\n\\nText:\\n{text}\\n\\nAnswer with one of: {', '.join(labels)}", DECISION_MODEL)
        return pick_branch(reply.strip(), labels) or labels[0]
    if not LLM_PROVIDER:
        return 0.0 if kind == "score" else 0.5
    if kind == "score":
        levels = "\\n".join(f"{i}: {level}" for i, level in enumerate(question["levels"]))
        reply = call_llm(f"{instructions}\\n\\nText:\\n{text}\\n\\nLevels:\\n{levels}\\n\\nAnswer with the level number.", DECISION_MODEL)
    else:
        reply = call_llm(f"{instructions}\\n\\nText:\\n{text}\\n\\nHow likely is it true, from 0 to 1? Answer with a number.", DECISION_MODEL)
    found = re.search(r"\\d+(?:\\.\\d+)?", reply)
    return float(found.group()) if found else 0.0
'''

HANDOFF = r'''
# --- Hand-offs -----------------------------------------------------------------------------------------------
# An Agent node with hand-off targets offers the model one transfer_to_<agent> tool per target. Calling one ends the
# agent: its hand-off node records who takes over, and a conditional edge goes to that agent, which continues the
# conversation. MAX_HANDOFFS bounds a run; past it the tools are gone and the agent answers itself.
HANDOFF_NOTE = "The conversation was handed off to you by {source}.{reason} Continue it and answer the person yourself."
NOT_RUN = "Not run: the conversation was handed off"
NO_MORE = "You cannot hand the conversation off again in this run: answer the person yourself."


def carried(messages: list) -> list:
    """What the next agent sees: the person's messages and the agents' replies, without tool calls and results."""
    return [{"role": m["role"], "content": m["content"]} for m in messages
            if m.get("role") == "user" or (m.get("role") == "assistant" and not m.get("tool_calls") and m.get("content"))]
'''

AGENT = r'''
# --- Agents --------------------------------------------------------------------------------------------------
# An Agent node is a loop of two nodes: the model node asks the model, which answers or asks for tool calls, and the
# tool node runs that round's calls. They run together unless the node turns that off. Without LLM_PROVIDER,
# call_agent() is an offline mock: it calls the tools the task names, then answers with the last result.
MAX_CALLS_PER_ROUND = 8
RESULT_CHARS = 8000  # a tool result goes back to the model shortened to this
STEP_CHARS = 2000  # ... and into the steps field shortened to this


def wave_cap(enabled: bool) -> int:
    """Calls of one round that run together. Off is one. Otherwise 4, or STUDIO_AGENT_PARALLEL_TOOLS when it is 1..8."""
    if not enabled:
        return 1
    raw = os.environ.get("STUDIO_AGENT_PARALLEL_TOOLS")
    if raw is None or not str(raw).strip():
        return 4
    try:
        n = int(str(raw).strip())
    except ValueError:
        return 4
    return n if 1 <= n <= 8 else 4
JSON_TYPES = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict}


def agent_task(messages: list) -> tuple:
    """The last user message and the tool results after it."""
    last = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=-1)
    return (messages[last].get("content") or "") if last >= 0 else "", [m for m in messages[last + 1:] if m.get("role") == "tool"]


def mock_agent(messages: list, tools: Optional[list], model: str) -> tuple:
    """Offline agent: with no tool result yet it calls every tool the task names (or the best match), then answers."""
    task, results = agent_task(messages)
    if tools and not results:
        words = set(re.findall(r"\w+", task.lower()))
        score = lambda t: len(words & set(re.findall(r"\w+", f"{t['name'].replace('_', ' ')} {t.get('description') or ''}".lower())))  # noqa: E731
        named = [t for t in tools if re.search(r"(?<!\w)" + re.escape(str(t.get("name") or "").lower()) + r"(?!\w)", task.lower())]
        picked = named if len(named) >= 2 else [max(tools, key=score)]
        calls = []
        for i, best in enumerate(picked, 1):
            params = best.get("parameters") or {}
            props, required = params.get("properties") or {}, set(params.get("required") or [])
            empty = {"number": 0, "integer": 0, "boolean": False, "array": [], "object": {}}
            args = {k: task if (v or {}).get("type", "string") == "string" else empty.get((v or {}).get("type"))
                    for k, v in props.items() if k in required or (v or {}).get("type", "string") == "string"}
            calls.append({"id": f"mock_call_{i}", "name": best["name"], "args": args})
        return "", calls
    said = (results[-1].get("content") or "") if results else (task.strip().splitlines() or [""])[-1]
    return f"[mock:{model}] Answer: {said[:200]}", []


def call_agent(messages: list, tools: Optional[list], model: str) -> tuple:
    """One model call: (text, tool calls [{id, name, args}]). With tools None the model has to answer."""
    if not LLM_PROVIDER:
        return mock_agent(messages, tools, model)
    from langchain.chat_models import init_chat_model
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

    history = []
    for m in messages:
        if m["role"] == "assistant":
            calls = [{"id": c["id"], "name": c["name"], "args": c["args"] or {}} for c in m.get("tool_calls") or []]
            history.append(AIMessage(m["content"], tool_calls=calls))
        elif m["role"] == "tool":
            history.append(ToolMessage(m["content"], tool_call_id=m["tool_call_id"]))
        else:
            images = m.get("images") or []
            content = [{"type": "text", "text": m["content"]}] + images if images else m["content"]
            history.append(SystemMessage(m["content"]) if m["role"] == "system" else HumanMessage(content))
    llm = init_chat_model(model, model_provider=LLM_PROVIDER)
    if tools:
        llm = llm.bind_tools([{"type": "function", "function": t} for t in tools])
    reply = llm.invoke(history)
    text = reply.content if isinstance(reply.content, str) else "".join(b.get("text", "") for b in reply.content if isinstance(b, dict))
    return text.strip(), [{"id": c.get("id") or f"call_{i}", "name": c["name"], "args": c.get("args") or {}} for i, c in enumerate(reply.tool_calls)]


def check_arguments(schema: dict, args: Any) -> Optional[str]:
    """Why the model's arguments do not fit the tool's parameters: required names and top-level JSON types."""
    if not isinstance(args, dict):
        return "arguments must be a JSON object"
    props = schema.get("properties") or {}
    missing = [k for k in schema.get("required") or [] if k not in args]
    if missing:
        return f"missing argument(s): {', '.join(missing)}"
    for k, v in args.items():
        want = (props.get(k) or {}).get("type") if isinstance(props.get(k), dict) else None
        if not isinstance(want, str) or want not in JSON_TYPES or v is None:
            continue
        if not isinstance(v, JSON_TYPES[want]) or (want in ("number", "integer") and isinstance(v, bool)):
            return f"argument {k} must be of type {want}"
    return None


def tool_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)


def shorten(text: str, n: int) -> str:
    return text if len(text) <= n else text[:n] + f"… (shortened from {len(text)} characters)"
'''

STUBS = {
    "retrieve": '''

def retrieve(query: str, top_k: int) -> list:
    """Retriever nodes search a Superstep knowledge base, which this file cannot reach.
    TODO: search your own index for `query`, for example with a LangChain vector store retriever."""
    return []
''',
    "call_mcp_tool": '''

def call_mcp_tool(tool: str, arguments: dict) -> Any:
    """MCP nodes call a tool on an MCP server connected in Superstep, which this file does not include.
    TODO: call the tool with an MCP client, for example the `mcp` package or langchain-mcp-adapters."""
    return None
''',
    "send_email": '''

def addresses(value: Any) -> list:
    items = value if isinstance(value, list) else [value]
    return [p.strip() for x in items if x not in (None, "") for p in re.split(r"[,;\\n]", str(x)) if p.strip()]


def send_email(message: dict) -> dict:
    """Send email nodes send through an SMTP credential in Superstep. This file never sends: like a studio dry run,
    it prints the message and returns what it would have sent.
    TODO: send it with smtplib and your own SMTP settings."""
    print(f"(e-mail not sent) to {', '.join(message['to'])}: {message['subject']}")
    return {"sent": False, "dry_run": True, "to": message["to"], "cc": message["cc"], "bcc": message["bcc"],
            "subject": message["subject"], "message_id": None, "preview": message["body"][:2000]}
''',
}

REDUCER_CODE = {
    "append": '''

def append_items(current: Any, new: Any) -> list:
    """Reducer "append": a list that collects every value written to it, from parallel branches too."""
    current = [] if current is None else (current if isinstance(current, list) else [current])
    return current + (new if isinstance(new, list) else [] if new is None else [new])
''',
    "merge": '''

def merge_objects(current: Any, new: Any) -> dict:
    """Reducer "merge": a shallow merge of objects; later keys win."""
    return {**(current if isinstance(current, dict) else {}), **(new if isinstance(new, dict) else {})}
''',
    "add": '''

def add_numbers(current: Any, new: Any) -> float:
    """Reducer "add": the sum of every number written to it."""
    num = lambda x: x if isinstance(x, (int, float)) and not isinstance(x, bool) else 0  # noqa: E731
    return num(current) + num(new)
''',
}


# ---- the generator ------------------------------------------------------------------------------------------------


class _Writer(GraphWriter):
    RESERVED = frozenset(RESERVED)

    def __init__(self, name: str, version: Optional[int], children: Dict[str, dict], example: Optional[dict]):
        super().__init__(name, version, children, example)
        self.extra: Dict[str, str] = {}  # tool helpers: name -> source
        self.imports: set = set()  # modules the tool functions use
        self.taken: set = set()  # names the tool functions define

    def write(self, raw: dict) -> Export:
        for g in [raw, *self.children.values()]:  # tool functions are copied in under their own names
            for n in g.get("nodes") or []:
                d = (n.get("data") or {}) if isinstance(n, dict) else {}
                if n.get("type") == "tool" and d.get("mode", "function") == "function": self.tool_source(d.get("function") or "")
                if n.get("type") == "agent":  # an Agent node's built-in tools (TASK-0119); its steps are timed
                    self.imports.add("time")
                    for t in d.get("tools") or []:
                        if isinstance(t, dict) and t.get("source") == "builtin": self.tool_source(t.get("function") or "")
        main, graphs = self.prepare(raw, self.taken)
        self.body(graphs, main)
        self.lines = [_rule(m.group(1)) if (m := RULE.fullmatch(ln)) else ln for ln in self.lines]
        head = self.header()
        self.lines = head + self.lines
        spans = {nid: [[a + len(head), b + len(head)] for a, b in r] for nid, r in self.spans.items()}
        return Export("\n".join(self.lines).rstrip("\n") + "\n", spans, self.expanded_names(main), f"{slug(self.title, 'workflow')}.py")

    def tool_source(self, name: str) -> None:
        fn = TOOLS.get(name)
        if fn is None or name in self.extra: return
        src = "\n".join(ln for ln in inspect.getsource(fn).split("\n") if not ln.startswith("@"))
        module = inspect.getmodule(fn)
        used = {n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name)}
        consts = []
        for ref in sorted(used):
            v = getattr(module, ref, None)
            if v is None or ref in dir(builtins) or ref == name: continue
            if inspect.ismodule(v): self.imports.add(v.__name__)
            elif isinstance(v, (dict, list, tuple, str, int, float)): consts.append(f"{ref} = {lit(v)}"); self.taken.add(ref)
        self.extra[name] = ("\n".join(consts) + "\n\n\n" if consts else "") + src.rstrip()
        self.taken.add(name)

    def header(self) -> List[str]:
        v = f" (version {self.version})" if self.version is not None else ""
        names = {n.id for n in ast.walk(ast.parse("\n".join(self.lines))) if isinstance(n, ast.Name)}
        uses = lambda n: n in names  # noqa: E731
        pip = "pip install langgraph" + (" httpx" if uses("httpx") else "")
        doc = [f'"""{_doc(self.title)}{v}: a LangGraph graph exported from Superstep.', "",
               "The graph on the canvas, written as code: the state, one function per node, and build_graph(), which",
               "connects them. Run it:", "", f"    {pip}", f"    python {slug(self.title, 'workflow')}.py", ""]
        if "agent" in self.uses:
            doc += ["LLM and Agent nodes use an offline mock model unless LLM_PROVIDER is set (see call_llm and call_agent below).", ""]
        elif "model" in self.uses:
            doc += ["LLM nodes use an offline mock model unless LLM_PROVIDER is set (see call_llm below).", ""]
        if "code" in self.uses:
            doc += ["Code nodes run here as written on the canvas, without the studio's sandbox: read them first.", ""]
        doc += ["Credentials, knowledge bases, MCP servers and approval channels are not exported.", '"""',
                "from __future__ import annotations", ""]
        std = sorted(m for m in {"json", "os", "re", "string", *self.imports} if uses(m))
        typing = sorted(n for n in ("Annotated", "Any", "Dict", "List", "Optional", "TypedDict") if uses(n))
        out = [f"import {m}" for m in std] + ([f"from typing import {', '.join(typing)}"] if typing else []) + [""]
        if uses("httpx"): out += ["import httpx", ""]
        lg = [line for name, line in (("InMemoryCache", "from langgraph.cache.memory import InMemoryCache"),
                                      ("MemorySaver", "from langgraph.checkpoint.memory import MemorySaver")) if uses(name)]
        graph = [n for n in ("END", "START", "StateGraph") if uses(n)]
        if graph: lg.append(f"from langgraph.graph import {', '.join(graph)}")
        types = [n for n in ("CachePolicy", "Command", "RetryPolicy", "interrupt") if uses(n)]
        if types: lg.append(f"from langgraph.types import {', '.join(types)}")
        return doc + out + lg + [""]

    def body(self, graphs: List[_Graph], main: _Graph) -> None:
        if "templates" in self.uses: self.add(TEMPLATES.rstrip())
        if "model" in self.uses: self.add("\n" + MODEL.rstrip())
        if "agent" in self.uses: self.add("\n" + AGENT.rstrip())
        if "handoff" in self.uses: self.add("\n" + HANDOFF.rstrip() + f"\nMAX_HANDOFFS = {self.max_handoffs(main.raw)}")
        if "files" in self.uses: self.add("\n" + FILES.rstrip() + (AGENT_FILES.rstrip() if "agent" in self.uses else ""))
        if "routing" in self.uses: self.add("\n" + ROUTING.rstrip())
        if "decide" in self.uses: self.add("\n" + DECIDE.rstrip())
        stubs = [k for k in STUBS if k in self.uses]
        if stubs:
            self.add("\n\n# --- Studio services ------------------------------------------------------------------------------------")
            self.add("# These nodes use services of the Superstep server. The stubs keep the graph running; replace them.")
            for k in stubs: self.add(STUBS[k].rstrip())
        if self.extra:
            self.add("\n\n# --- Tool functions -------------------------------------------------------------------------------------")
            for src in self.extra.values(): self.add("\n\n" + src)
        reducers = [k for k in REDUCERS if k in self.uses]
        if reducers:
            self.add("\n\n# --- Reducers -------------------------------------------------------------------------------------------")
            self.add("# A reducer says how a node's output combines with the field's current value. Without one, the new")
            self.add("# value replaces the old one, and two parallel branches writing the same field in one step is an error.")
            for k in reducers: self.add(REDUCER_CODE[k].rstrip())
        for g in graphs: self.graph(g, g is main)
        self.run(main)

    # -- one graph --
    def graph(self, g: _Graph, is_main: bool) -> None:
        cls = "State" if is_main else self.built[g.wid][2]
        build = "build_graph" if is_main else self.built[g.wid][1]
        what = "Graph" if is_main else f'Subgraph "{_doc(g.title)}"'
        self.add(f"\n\n# {'=' * (WIDTH - 2)}")
        self.add(f"# {what}")
        self.add(f"# {'=' * (WIDTH - 2)}")
        notes = [i for i in g.order() if g.nodes[i]["type"] == "note"]
        for nid in notes:
            s = len(self.lines) + 1
            text = str((g.nodes[nid].get("data") or {}).get("text") or "").strip()
            self.add("\n# Note on the canvas:")
            for ln in text.splitlines() or [""]: self.add(f"#   {ln.rstrip()}" if ln.strip() else "#")  # every kind of line break
            if is_main: self.span(nid, s + 1)
        self.state(g, cls, is_main)
        for nid in g.order():
            if nid in g.names:
                s = len(self.lines) + 1
                self.node(g, nid, cls)
                if is_main: self.span(nid, s + 2)  # skip the two blank lines before the code
        self.build(g, cls, build, is_main)

    def state(self, g: _Graph, cls: str, is_main: bool) -> None:
        fields = self.all_fields(g)
        self.add("")
        self.add("")
        if is_main:
            self.add("# The state is a dict shared by every node. A node returns only the fields it changes, and LangGraph")
            self.add("# merges them into the state. total=False: a field is missing until a node or the input sets it.")
        else:
            self.add("# A subgraph has its own state. It shares fields with the parent graph by name: the parent passes them")
            self.add("# in, and the fields the subgraph changed come back when it ends.")
        chats = [a["chat"] for a in g.agents.values()]
        rows = [(f["name"], self.ann(f)) for f in fields] + [(c, "int") for c in g.cursors.values()] + [(c, "Optional[dict]") for c in chats]
        if self.has_handoffs(g):  # the pending hand-off, the run's count, and the agent a chat continues with (TASK-0183)
            rows += [(self.HANDOFF_FIELD, "Optional[dict]"), (self.COUNT_FIELD, "int"), (self.START_FIELD, "str")]
        if rows and all(n.isidentifier() and not keyword.iskeyword(n) for n, _ in rows):
            self.add(f"class {cls}(TypedDict, total=False):")
            for n, a in rows:
                why = "  # loop position of a For each node" if n in g.cursors.values() else "  # an Agent node's conversation" if n in chats else \
                    {self.HANDOFF_FIELD: "  # a hand-off on its way to the next agent", self.COUNT_FIELD: "  # hand-offs so far in this run",
                     self.START_FIELD: "  # input: start at this agent (a chat continues with the agent that answered last)"}.get(n, "")
                self.add(f"    {n}: {a}{why}")
        else:
            body = ", ".join(f"{lit(n)}: {a}" for n, a in rows)
            self.add(f"{cls} = TypedDict({lit(cls)}, {{{body}}}, total=False)")

    def ann(self, f: dict) -> str:
        typ = PY_TYPES.get(f.get("type", "string"), "Any")
        r = f.get("reducer") or "replace"
        return f"Annotated[{typ}, {REDUCERS[r]}]" if r in REDUCERS else typ

    def node(self, g: _Graph, nid: str, cls: str) -> None:
        n = g.nodes[nid]; t, d = n["type"], n.get("data") or {}
        name, label = g.names[nid], _doc(d.get("label") or nid)
        const = name.upper()
        head = f'{TITLES.get(t, _camel(t))} node "{label}" (id: {_doc(nid)})'
        out = d.get("output_field")
        ret = (lambda expr: f"    return {{{lit(out)}: {expr}}}") if out else (lambda expr: f"    {expr}\n    return {{}}")
        self.add("")
        self.add("")
        if t == "llm":
            self.add(f"{const}_PROMPT = {lit(d.get('prompt') or '')}")
            self.add("")
            self.add("")
            self.add(f"def {name}(state: {cls}) -> dict:")
            self.add(f'    """{head}."""')
            self.add(f"    prompt = render({const}_PROMPT, state)")
            files = attachments.field_of(d)
            self.add(ret(f"call_llm_files(prompt, {lit(d.get('model') or 'gpt-4o-mini')}, state.get({lit(files)}))" if files
                         else f"call_llm(prompt, {lit(d.get('model') or 'gpt-4o-mini')})"))
        elif t == "human":
            self.add(f"{const}_PROMPT = {lit(d.get('prompt') or '')}")
            self.add("")
            self.add("")
            self.add(f"def {name}(state: {cls}) -> dict:")
            self.add(f'    """{head}.')
            self.add("")
            self.add("    interrupt() pauses the run and hands the question to the caller (see main()). The caller resumes it")
            self.add("    with Command(resume=answer): the node then runs again from the top and interrupt() returns the answer.")
            extra = []
            if (d.get("approval") or {}).get("channel"): extra.append(f"also asks on {str(d['approval']['channel']).title()}")
            if d.get("deadline"): extra.append("has a deadline with reminders")
            if approval_policy.mode(d) != "off": extra.append("has AI review of the request (people answer every request here)")
            if extra: self.add(f"    In Superstep this node {' and '.join(extra)}; that is not part of LangGraph.")
            self.add('    """')
            self.add(f"    answer = interrupt({{\"node\": {lit(name)}, \"question\": render({const}_PROMPT, state)}})")
            self.add(ret("answer"))
        elif t == "condition":
            self.add(f"def {name}(state: {cls}) -> dict:")
            self.add(f'    """{head}: changes nothing. The routing is route_{name}(), on the edges after it.')
            self.add("    In hand-written LangGraph the router often sits on the node before, without a node of its own.\"\"\"")
            self.add("    return {}")
            self.router(g, nid, cls)
        elif t == "join":
            self.add(f"def {name}(state: {cls}) -> dict:")
            self.add(f'    """{head}: runs once, after every branch that leads here has finished (see build_graph)."""')
            self.add("    return {}")
        elif t == "foreach":
            self.foreach(g, nid, cls, head)
        elif t == "decision":
            self.decision(g, nid, cls, head)
        elif t == "agent":
            self.agent(g, nid, cls, head)
        elif t == "tool":
            self.tool(g, nid, cls, head, ret)
        elif t == "retriever":
            self.add(f"{const}_QUERY = {lit(d.get('query') or '')}")
            self.add("")
            self.add("")
            self.add(f"def {name}(state: {cls}) -> dict:")
            self.add(f'    """{head}: the chunks of a knowledge base that best match the query (see retrieve)."""')
            self.add(ret(f"retrieve(render({const}_QUERY, state), top_k={_number(d.get('top_k'), int) or 4})"))
        elif t == "mcp":
            self.add(f"{const}_ARGUMENTS = {lit(d.get('arguments') or {})}")
            self.add("")
            self.add("")
            self.add(f"def {name}(state: {cls}) -> dict:")
            self.add(f'    """{head}: calls the MCP tool {lit(_doc(d.get("tool")))} (see call_mcp_tool)."""')
            self.add(ret(f"call_mcp_tool({lit(d.get('tool') or '')}, render_args({const}_ARGUMENTS, state))"))
        elif t == "email":
            self.email(g, nid, cls, head)
        elif t == "subgraph":
            ref = g.refs.get(nid) or ""
            build = self.built[ref][1] if ref in self.built else None
            self.add(f"# {head}: the workflow \"{_doc(self.built[ref][0].title) if build else ref}\" runs as a subgraph.")
            self.add(f"# build_graph() adds {build or 'it'}() as the node: a compiled graph can be a node of another graph.")
        else:  # subgraph_exit or an unknown type: a pass-through
            self.add(f"def {name}(state: {cls}) -> dict:")
            self.add(f'    """{head}."""')
            self.add("    return {}")
        if (names := self.inputs(g, nid)):
            fields = {f["name"]: f for f in self.all_fields(g)}
            self.add("")
            self.add("")
            self.add(f"# {_camel(name)}Input: the only fields {name}() sees (input_schema in build_graph).")
            self.add(f"{_camel(name)}Input = TypedDict({lit(_camel(name) + 'Input')}, "
                     f"{{{', '.join(f'{lit(x)}: {self.ann(fields[x])}' for x in names)}}}, total=False)")

    def router(self, g: _Graph, nid: str, cls: str) -> None:
        d = g.nodes[nid].get("data") or {}; fld = d.get("field") or ""
        labels = [e.get("label") for e in g.out(nid)]
        default = d.get("default") or ("default" if "default" in labels else None)
        self.add("")
        self.add("")
        self.add(f"def route_{g.names[nid]}(state: {cls}) -> str:")
        self.add(f'    """The branch to take after "{_doc(d.get("label") or nid)}": the edge label that state[{lit(fld)}] names."""')
        self.add(f"    value = state.get({lit(fld)})")
        self.add('    value = ("" if value is None else str(value).lower() if isinstance(value, bool) else str(value)).strip()')
        self.add(f"    label = pick_branch(value, {lit(labels)})")
        if default and default in labels:
            self.add(f"    return {lit(default)} if label is None else label")
        else:
            self.add("    if label is None:")
            msg = lit(f"{_one_line(d.get('label') or nid)}: no edge label matches (and no default) ")
            self.add(f"        raise ValueError({msg} + repr(value[:100]))")
            self.add("    return label")

    def foreach(self, g: _Graph, nid: str, cls: str, head: str) -> None:
        d = g.nodes[nid].get("data") or {}; name, cur = g.names[nid], g.cursors[nid]
        src, item, idx = d.get("items_field") or "", d.get("item_field") or "", d.get("index_field")
        cap = foreach.max_items(d)
        self.add(f"def {name}(state: {cls}) -> dict:")
        self.add(f'    """{head}: one item of state[{lit(src)}] per visit, in order.')
        self.add("")
        self.add("    The \"each\" edge leads into the loop body, which comes back here; after the last item the \"done\" edge")
        self.add(f"    leaves the loop. The position is kept in state[{lit(cur)}].\"\"\"")
        self.add(f"    items = state.get({lit(src)}) or []")
        self.add(f"    if not isinstance(items, list) or len(items) > {cap}:")
        msg = lit(f"{_one_line(d.get('label') or nid)}: state[{lit(src)}] must be a list of at most {cap} items")
        self.add(f"        raise ValueError({msg})")
        self.add(f"    position = state.get({lit(cur)}) or 0")
        self.add("    if position >= len(items):")
        self.add(f"        return {{{lit(cur)}: 0}}  # finished: back to 0, so an enclosing loop starts the list again")
        upd = f"{lit(cur)}: position + 1, {lit(item)}: items[position]" + (f", {lit(idx)}: position" if idx else "")
        self.add(f"    return {{{upd}}}")
        self.add("")
        self.add("")
        self.add(f"def route_{name}(state: {cls}) -> str:")
        self.add(f"    return \"each\" if state.get({lit(cur)}) else \"done\"")

    def decision(self, g: _Graph, nid: str, cls: str, head: str) -> None:
        d = g.nodes[nid].get("data") or {}; name, const = g.names[nid], g.names[nid].upper()
        qs = self.questions(d)
        self.add(f"{const}_TEXT = {lit(d.get('text') or '')}")
        self.add(f"{const}_QUESTIONS = {lit(qs)}")
        self.add("")
        self.add("")
        self.add(f"def {name}(state: {cls}) -> dict:")
        self.add(f'    """{head}: answers each question about the text (see decide)."""')
        self.add(f"    text = str(render_args({const}_TEXT, state))")
        self.add("    update = {}")
        self.add("    answers = {}")
        self.add(f"    for question in {const}_QUESTIONS:")
        self.add("        instructions = render(question[\"instructions\"], state)")
        self.add("        answer = decide(text, {**question, \"instructions\": instructions})")
        self.add("        answers[question[\"id\"]] = {\"type\": question[\"type\"], question[\"type\"]: answer}")
        self.add("        if question.get(\"field\"):")
        self.add("            update[question[\"field\"]] = answer")
        if d.get("output_field"): self.add(f"    update[{lit(d['output_field'])}] = answers")
        self.add("    return update")

    def tool(self, g: _Graph, nid: str, cls: str, head: str, ret) -> None:
        d = g.nodes[nid].get("data") or {}; name, const = g.names[nid], g.names[nid].upper()
        mode = d.get("mode") or "function"
        if mode == "http":
            self.add(f"{const}_URL = {lit(d.get('url') or '')}")
            self.add(f"{const}_BODY = {lit(d.get('body') or '')}")
            self.add("")
            self.add("")
            self.add(f"def {name}(state: {cls}) -> dict:")
            self.add(f'    """{head}: an HTTP request; the JSON reply (or the text) is the result.')
            self.add("    The studio only calls public addresses and never follows redirects.\"\"\"")
            self.add(f"    body = render({const}_BODY, state)")
            self.add(f"    response = httpx.request({lit(d.get('method') or 'GET')}, render({const}_URL, state), content=body.encode() or None,")
            self.add("                             headers={\"Content-Type\": \"application/json\"}, timeout=30, follow_redirects=False)")
            self.add("    try:")
            self.add("        result = response.json()")
            self.add("    except ValueError:")
            self.add("        result = response.text")
            self.add(ret("result"))
        elif mode == "code" and (d.get("language") or "python") != "python":
            lang = str(d.get("language"))  # TASK-0079: another language cannot be pasted into a Python file
            self.add(f"def {name}(state: {cls}) -> dict:")
            self.add(f'    """{head}: written in {lang} on the canvas, which this Python file cannot run."""')
            self.add(f"    raise NotImplementedError({lit(f'{head} is {lang} code; port it to Python to run it here')})")
        elif mode == "code":
            self.add(f"def {name}(state: {cls}) -> dict:")
            self.add(f'    """{head}: the node\'s Python code as written on the canvas; main(state) gives the result.')
            self.add("    In the studio it runs in a sandbox without network access; here it runs in this process.\"\"\"")
            for ln in _indent_code(d.get("code") or "def main(state):\n    return None\n"): self.add(ln)
            self.add("")
            self.add(ret("main(dict(state))"))
        else:
            fn = d.get("function") or ""
            self.add(f"def {name}(state: {cls}) -> dict:")
            self.add(f'    """{head}: the Python function {fn}(state)."""')
            if fn in self.extra: self.add(ret(f"{fn}(state)"))
            else:
                self.add(f"    # TODO: the function {lit(fn)} is not registered on this server any more.")
                self.add(ret("None"))

    def email(self, g: _Graph, nid: str, cls: str, head: str) -> None:
        d = g.nodes[nid].get("data") or {}; name, const = g.names[nid], g.names[nid].upper()
        self.add(f"{const}_SUBJECT = {lit(d.get('subject') or '')}")
        self.add(f"{const}_BODY = {lit(d.get('body') or '')}")
        self.add("")
        self.add("")
        self.add(f"def {name}(state: {cls}) -> dict:")
        self.add(f'    """{head}: builds the message from the state (see send_email)."""')
        self.add("    message = {")
        for k in ("to", "cc", "bcc"):
            self.add(f"        {lit(k)}: addresses(render_args({lit(d[k])}, state)),"
                     if d.get(k) else f"        {lit(k)}: [],")
        self.add(f"        \"subject\": \" \".join(render({const}_SUBJECT, state).split()),")
        self.add(f"        \"body\": render({const}_BODY, state),")
        self.add("    }")
        out = d.get("output_field")
        if out: self.add(f"    return {{{lit(out)}: send_email(message)}}")
        else:
            self.add("    send_email(message)")
            self.add("    return {}")

    def agent(self, g: _Graph, nid: str, cls: str, head: str) -> None:
        """An Agent node as the studio runs it (DEC-0063): an entry node, the model node and the tool node in a loop, and
        an end node, with the conversation in its own state field."""
        d = g.nodes[nid].get("data") or {}; name, const, a = g.names[nid], g.names[nid].upper(), g.agents[nid]
        chat, model, tool, end = lit(a["chat"]), a["model"], a["tool"], a["exit"]
        tools = agents.specs(self.tool_spec_data(d))
        approval = [t.get("name") for t in d.get("tools") or [] if isinstance(t, dict) and t.get("approval")]
        who = _one_line(d.get("label") or nid)
        if d.get("system_prompt"): self.add(f"{const}_SYSTEM = {lit(d['system_prompt'])}")
        self.add(f"{const}_PROMPT = {lit(d.get('prompt') or '')}")
        self.add(f"# The tools the model may call: their names, what they do, and the JSON Schema of their arguments.")
        self.add(f"{const}_TOOLS = {lit(tools)}")
        if approval: self.add(f"{const}_NEEDS_APPROVAL = {lit(approval)}  # these ask a person first (interrupt)")
        for t in d.get("tools") or []:
            if isinstance(t, dict) and t.get("source") == "http":
                self.add(f"{self.http_key(const, t)}_URL = {lit(t.get('url') or '')}")
                self.add(f"{self.http_key(const, t)}_BODY = {lit(t.get('body') or '')}")
        hs = self.handoff_tools(g, nid) if "handoff" in a else []
        if hs:
            self.add(f"# Hand-offs: the transfer tools the model may call, and the agent each one leads to.")
            self.add(f"{const}_HANDOFF_TOOLS = {lit(self.handoff_specs(hs))}")
            self.add(f"{const}_HANDOFFS = {lit({h['name']: {'to': h['node'], 'label': h['label']} for h in hs})}")
        self.add(f"{const}_MAX_ROUNDS = {self.rounds(d)}")
        self.add(f"{const}_PARALLEL = {d.get('parallel_tool_calls') is not False}")
        self.add("")
        self.add("")
        self.add(f"def {name}(state: {cls}) -> dict:")
        self.add(f'    """{head}: starts the conversation in state[{chat}].')
        self.add("")
        self.add("    Then the model and the tools take turns, one node each:")
        self.add(f"    - {model}() asks the model, which answers or asks for tool calls;")
        self.add(f"    - {tool}() runs the waiting tool calls (route_{model}() and route_{tool}() pick the next node);")
        self.add(f"    - {end}() writes the answer.\"\"\"")
        receiver = nid in self.receivers(g)
        if receiver:
            self.add(f"    got = state.get({lit(self.HANDOFF_FIELD)}) or {{}}")
            self.add(f"    if got.get(\"to\") == {lit(name)}:  # handed off to this agent: the note, then the conversation so far")
            self.add("        reason = f\" Reason: {got['reason']}.\" if got.get(\"reason\") else \"\"")
            sys_ = f"render({const}_SYSTEM, state), " if d.get("system_prompt") else ""
            self.add(f"        system = \"\\n\\n\".join(x for x in ({sys_}HANDOFF_NOTE.format(source=got[\"from\"], reason=reason)) if x)")
            self.add(f"        messages = [{{\"role\": \"system\", \"content\": system}}] + got[\"messages\"] + [{{\"role\": \"user\", \"content\": render({const}_PROMPT, state)}}]")
            self.add(f"        return {{{chat}: {{\"messages\": messages, \"pending\": [], \"rounds\": 0, \"steps\": [], \"answer\": None}}, {lit(self.HANDOFF_FIELD)}: None}}")
        self.add("    messages = []")
        if d.get("system_prompt"): self.add(f"    messages.append({{\"role\": \"system\", \"content\": render({const}_SYSTEM, state)}})")
        if d.get("history_field"):
            self.add(f"    for m in state.get({lit(d['history_field'])}) or []:  # the earlier turns of a chat")
            self.add("        if isinstance(m, dict) and m.get(\"role\") in (\"user\", \"assistant\") and isinstance(m.get(\"content\"), str):")
            self.add("            messages.append({\"role\": m[\"role\"], \"content\": m[\"content\"]})")
        files = attachments.field_of(d)
        if files: self.add(f"    messages.append({{\"role\": \"user\", \"content\": render({const}_PROMPT, state), \"files\": state.get({lit(files)}) or []}})")
        else: self.add(f"    messages.append({{\"role\": \"user\", \"content\": render({const}_PROMPT, state)}})")
        self.add(f"    return {{{chat}: {{\"messages\": messages, \"pending\": [], \"rounds\": 0, \"steps\": [], \"answer\": None}}}}")
        self.add("")
        self.add("")
        self.add(f"def {model}(state: {cls}) -> dict:")
        self.add(f'    """{_doc(who)}: one model call. After {const}_MAX_ROUNDS rounds the model gets no tools, so it has to answer."""')
        self.add(f"    chat = dict(state[{chat}])")
        self.add(f"    last = chat[\"rounds\"] >= {const}_MAX_ROUNDS")
        call = "call_agent_files" if attachments.field_of(d) else "call_agent"
        if hs:
            self.add(f"    can = state.get({lit(self.COUNT_FIELD)}, 0) < MAX_HANDOFFS")
            self.add("    if not can and not chat.get(\"no_more\"):  # the run's hand-offs are used up: say so once")
            self.add("        chat[\"messages\"] = [{\"role\": \"system\", \"content\": NO_MORE}] + chat[\"messages\"]")
            self.add("        chat[\"no_more\"] = True")
            self.add(f"    tools = {const}_TOOLS + ({const}_HANDOFF_TOOLS if can else [])")
            self.add(f"    text, calls = {call}(chat[\"messages\"], None if last else tools, {lit(d.get('model') or 'gpt-4o-mini')})")
        else:
            self.add(f"    text, calls = {call}(chat[\"messages\"], None if last else {const}_TOOLS, {lit(d.get('model') or 'gpt-4o-mini')})")
        self.add("    calls = [] if last else [{\"id\": str(c.get(\"id\") or f\"call_{i}\"), \"name\": str(c.get(\"name\") or \"\"), \"args\": c.get(\"args\")}")
        self.add("                             for i, c in enumerate(calls)]")
        self.add("    if not last:")
        self.add("        chat[\"rounds\"] += 1")
        self.add("    chat[\"messages\"] = chat[\"messages\"] + [{\"role\": \"assistant\", \"content\": text, **({\"tool_calls\": calls} if calls else {})}]")
        if hs:
            self.add(f"    first = next((c for c in calls if c[\"name\"] in {const}_HANDOFFS), None) if can else None")
            self.add("    if first is not None:  # the hand-off wins: the other calls of the round are answered, not run")
            self.add(f"        h = {const}_HANDOFFS[first[\"name\"]]")
            self.add("        for c in calls:")
            self.add("            said = f\"Handed off to {h['label']}\" if c is first else NOT_RUN")
            self.add("            chat[\"messages\"] = chat[\"messages\"] + [{\"role\": \"tool\", \"tool_call_id\": c[\"id\"], \"name\": c[\"name\"], \"content\": said}]")
            self.add("            if c is not first:")
            self.add("                chat[\"steps\"] = chat[\"steps\"] + [{\"tool\": c[\"name\"], \"args\": c[\"args\"], \"result\": NOT_RUN, \"status\": \"not_run\", \"ms\": 0}]")
            self.add("        reason = str((first[\"args\"] if isinstance(first[\"args\"], dict) else {}).get(\"reason\") or \"\")[:500]")
            self.add("        chat[\"pending\"], chat[\"handoff\"] = [], {\"to\": h[\"to\"], \"reason\": reason}")
            self.add(f"        return {{{chat}: chat}}")
        self.add("    chat[\"pending\"] = calls[:MAX_CALLS_PER_ROUND]")
        self.add("    for c in calls[MAX_CALLS_PER_ROUND:]:  # every call needs an answer, but these never run")
        self.add("        why = f\"Refused: at most {MAX_CALLS_PER_ROUND} tool calls per round\"")
        self.add("        chat[\"messages\"] = chat[\"messages\"] + [{\"role\": \"tool\", \"tool_call_id\": c[\"id\"], \"name\": c[\"name\"], \"content\": why}]")
        self.add("        chat[\"steps\"] = chat[\"steps\"] + [{\"tool\": c[\"name\"], \"args\": c[\"args\"], \"result\": why, \"status\": \"refused\", \"ms\": 0}]")
        self.add("    if not calls:")
        self.add("        chat[\"answer\"] = text")
        self.add(f"    return {{{chat}: chat}}")
        self.add("")
        self.add("")
        self.add(f"def route_{model}(state: {cls}) -> str:")
        if hs:
            self.add("    \"\"\"After a model call: \"handoff\" when it handed off, \"tool\" while tool calls wait, else \"done\".\"\"\"")
            self.add(f"    if state[{chat}].get(\"handoff\"):")
            self.add("        return \"handoff\"")
        else:
            self.add("    \"\"\"After a model call: \"tool\" while tool calls wait, else \"done\".\"\"\"")
        self.add(f"    return \"tool\" if state[{chat}][\"pending\"] else \"done\"")
        if hs:
            hn = a["handoff"]
            self.add("")
            self.add("")
            self.add(f"def {hn}(state: {cls}) -> dict:")
            self.add(f'    """{_doc(who)} hands off: the conversation so far goes to the next agent, and this one ends without answering."""')
            self.add(f"    chat = state[{chat}]")
            self.add(f"    handoff = {{\"from\": {lit(who)}, \"to\": chat[\"handoff\"][\"to\"], \"reason\": chat[\"handoff\"][\"reason\"], \"messages\": carried(chat[\"messages\"])}}")
            self.add(f"    return {{{chat}: None, {lit(self.HANDOFF_FIELD)}: handoff, {lit(self.COUNT_FIELD)}: state.get({lit(self.COUNT_FIELD)}, 0) + 1}}")
            self.add("")
            self.add("")
            self.add(f"def route_{hn}(state: {cls}) -> str:")
            self.add("    \"\"\"The agent the hand-off goes to.\"\"\"")
            self.add(f"    return state[{lit(self.HANDOFF_FIELD)}][\"to\"]")
        self.agent_calls(d, name, const, cls)
        self.add("")
        self.add("")
        self.add(f"def {tool}(state: {cls}) -> dict:")
        self.add(f'    """{_doc(who)}: runs the tool calls waiting from the model and gives the results back, in the model\'s order.')
        self.add(f"    With {const}_PARALLEL on, up to wave_cap() calls run together. A failure becomes that call's result;")
        self.add("    the others still finish.")
        if approval:
            self.add(f"    A tool in {const}_NEEDS_APPROVAL runs on its own and asks first with interrupt(): \"approved\" runs the call;")
            self.add("    any other answer rejects it, and the model is told why. On resume the node runs again from the top.")
        if (d.get("approval") or {}).get("channel") or d.get("deadline"):
            self.add("    In Superstep the approval can also go to a channel and have a deadline; that is not part of LangGraph.")
        if approval_policy.mode(d) != "off":
            self.add("    In Superstep a model can review the request first (AI review); here people answer every request.")
        self.add('    """')
        self.add(f"    chat = dict(state[{chat}])")
        self.add("    pending = list(chat[\"pending\"])")
        self.add(f"    n = min(wave_cap({const}_PARALLEL), len(pending))")
        if approval:
            self.add("    for i, call in enumerate(pending[:n]):")
            self.add(f"        if call[\"name\"] in {const}_NEEDS_APPROVAL:")
            self.add("            n = 1 if i == 0 else i")
            self.add("            break")
        self.add("    batch, chat[\"pending\"] = pending[:n], pending[n:]")
        self.add("    def one(call: dict) -> tuple:")
        self.add(f"        spec = next((t for t in {const}_TOOLS if t[\"name\"] == call[\"name\"]), None)")
        self.add("        problem = None if spec is None else check_arguments(spec[\"parameters\"], call[\"args\"])")
        if approval:
            self.add("        answer = None")
            self.add(f"        if spec is not None and problem is None and call[\"name\"] in {const}_NEEDS_APPROVAL:")
            self.add(f"            question = ({lit(who + ' wants to call ')} + call[\"name\"] + \" with these arguments:\\n\"")
            self.add("                        + json.dumps(call[\"args\"], ensure_ascii=False, indent=2)")
            self.add("                        + \"\\nApprove to run it, or reject it. A text reply rejects it and tells the model why.\")")
            self.add(f"            answer = str(interrupt({{\"node\": {lit(name)}, \"question\": question}}))")
        self.add("        started = time.perf_counter()")
        self.add("        if spec is None:")
        self.add(f"            status, result = \"error\", f\"Unknown tool {{call['name']}}: use one of {{', '.join(sorted(t['name'] for t in {const}_TOOLS))}}\"")
        self.add("        elif problem:")
        self.add("            status, result = \"error\", f\"Invalid arguments for {call['name']}: {problem}\"")
        if approval:
            self.add("        elif answer is not None and answer.strip().lower() != \"approved\":")
            self.add("            comment = \"\" if answer.strip().lower() == \"rejected\" else answer.strip()")
            self.add("            status, result = \"rejected\", \"Rejected by a reviewer\" + (f\": {comment}\" if comment else \"\")")
        self.add("        else:")
        self.add("            try:")
        self.add(f"                status, result = \"ok\", tool_text(call_{name}_tool(call[\"name\"], call[\"args\"], state))")
        self.add("            except Exception as error:  # the model hears about the failure and can try something else")
        self.add("                status, result = \"error\", f\"The tool failed: {error}\"")
        self.add("        step = {\"tool\": call[\"name\"], \"args\": call[\"args\"], \"result\": shorten(result, STEP_CHARS), \"status\": status,")
        self.add("                \"ms\": round((time.perf_counter() - started) * 1000, 2)}")
        if approval:
            self.add("        if answer is not None:")
            self.add("            step[\"approval\"] = \"rejected\" if status == \"rejected\" else \"approved\"")
        self.add("        return ({\"role\": \"tool\", \"tool_call_id\": call[\"id\"], \"name\": call[\"name\"], \"content\": shorten(result, RESULT_CHARS)}, step)")
        self.add("    if n <= 1:")
        self.add("        pairs = [one(batch[0])]")
        self.add("    else:")
        self.add("        from concurrent.futures import ThreadPoolExecutor")
        self.add("        with ThreadPoolExecutor(max_workers=n) as pool:")
        self.add("            pairs = list(pool.map(one, batch))  # map keeps the model's order")
        self.add("    for message, step in pairs:")
        self.add("        chat[\"messages\"] = chat[\"messages\"] + [message]")
        self.add("        chat[\"steps\"] = chat[\"steps\"] + [step]")
        self.add(f"    return {{{chat}: chat}}")
        self.add("")
        self.add("")
        self.add(f"def route_{tool}(state: {cls}) -> str:")
        self.add("    \"\"\"After a batch of tool calls: another batch if any remain, else back to the model.\"\"\"")
        self.add(f"    return \"tool\" if state[{chat}][\"pending\"] else \"model\"")
        self.add("")
        self.add("")
        self.add(f"def {end}(state: {cls}) -> dict:")
        self.add(f'    """{_doc(who)}: the model\'s answer into the state, and the conversation cleared."""')
        self.add(f"    chat = state[{chat}]")
        out = [f"{lit(d.get('output_field') or '')}: chat[\"answer\"] or \"\""]
        if d.get("steps_field"): out.append(f"{lit(d['steps_field'])}: chat[\"steps\"]")
        self.add(f"    return {{{', '.join(out)}, {chat}: None}}")

    def agent_calls(self, d: dict, name: str, const: str, cls: str) -> None:
        """call_<agent>_tool(): what each of the Agent node's tools does."""
        self.add("")
        self.add("")
        self.add(f"def call_{name}_tool(name: str, args: dict, state: {cls}) -> Any:")
        self.add("    \"\"\"Runs the tool the model asked for with the model's arguments.\"\"\"")
        for t in d.get("tools") or []:
            if not isinstance(t, dict): continue
            src, tname = t.get("source"), t.get("name") or ""
            self.add(f"    if name == {lit(tname)}:")
            if src == "builtin":
                fn = t.get("function") or ""
                if fn in self.extra: self.add(f"        return {fn}({{**state, **args}})  # the arguments over the state, as in the studio")
                else:
                    self.add(f"        # TODO: the function {lit(fn)} is not registered on this server any more.")
                    self.add("        return None")
            elif src == "knowledge":
                self.add(f"        return retrieve(str(args.get(\"query\") or \"\"), top_k={_number(t.get('top_k'), int) or 4})")
            elif src == "mcp":
                self.add(f"        return call_mcp_tool({lit(t.get('tool') or '')}, args)")
            elif src == "workflow":
                ref = t.get("workflow_id") or ""; inputs, outputs = agents.field_list(t.get("inputs")), agents.field_list(t.get("outputs"))
                if ref in self.built:
                    child, build = self.built[ref][0], self.built[ref][1]
                    self.add(f"        # the workflow \"{_doc(child.title)}\" as its own graph (in the studio: a child run). Inside this graph's run,")
                    self.add("        # a question for a person in it pauses this graph too.")
                    self.add(f"        final = {build}().invoke({{k: args[k] for k in {lit(inputs)} if k in args}})")
                    self.add(f"        return {{k: final.get(k) for k in {lit(outputs)}}}")
                else:
                    self.add(f"        # TODO: the workflow {lit(ref)} was not found (deleted, or not shared with you).")
                    self.add("        return None")
            elif src == "http":
                method, url, body = (t.get("method") or "GET").upper(), t.get("url") or "", t.get("body") or ""
                key = self.http_key(const, t)
                self.add(f"        values = {{**state, \"args\": args}}  # the templates read the arguments as {{{{state.args.<name>}}}}")
                self.add(f"        url, body = render({key}_URL, values), render({key}_BODY, values)")
                uses_args = "args" in {r.field for r in refs(url) + refs(body)}
                query = method == "GET" and not uses_args
                if not body and method in ("POST", "PUT", "PATCH"):
                    self.add("        body = json.dumps(args, ensure_ascii=False)  # no body template: the arguments as JSON")
                if query: self.add("        query = {k: tool_text(v) for k, v in args.items()}  # the URL does not use the arguments")
                self.add(f"        response = httpx.request({lit(method)}, url, {'params=query or None, ' if query else ''}content=body.encode() or None,")
                self.add("                                 headers={\"Content-Type\": \"application/json\"}, timeout=30, follow_redirects=False)")
                self.add("        try:")
                self.add("            return response.json()")
                self.add("        except ValueError:")
                self.add("            return response.text")
            else:
                self.add(f"        raise ValueError({lit(f'unknown tool source {src!r}')})")
        self.add("    raise ValueError(f\"unknown tool {name}\")")

    @staticmethod
    def start_router(build: str, is_main: bool) -> str: return "route_start" if is_main else f"route_start_{build}"

    def build(self, g: _Graph, cls: str, build: str, is_main: bool) -> None:
        name = lambda i: "END" if g.nodes[i]["type"] == "end" else lit(g.names[i])  # noqa: E731
        leave = lambda i: lit(g.agents[i]["exit"]) if i in g.agents else lit(g.names[i])  # an Agent node's edges leave from its end node  # noqa: E731
        cache = any(_number((n.get("data") or {}).get("cache_ttl"), int) is not None for n in g.nodes.values())
        if (rec := self.start_receivers(g)):
            first = [name(e["target"]) for s in g.nodes if g.nodes[s]["type"] == "start" for e in g.out(s) if g.nodes[e["target"]]["type"] != "join"]
            self.add("")
            self.add("")
            self.add(f"{self.start_router(build, is_main).upper()}_AGENTS = {lit([g.names[r] for r in rec])}  # the agents a chat may continue with")
            self.add("")
            self.add("")
            self.add(f"def {self.start_router(build, is_main)}(state: {cls}) -> list:")
            self.add(f"    \"\"\"Where the run starts: the agent named in {self.START_FIELD}, if it is one a hand-off reaches, else the first node.\"\"\"")
            self.add(f"    if state.get({lit(self.START_FIELD)}) in {self.start_router(build, is_main).upper()}_AGENTS:")
            self.add(f"        return [state[{lit(self.START_FIELD)}]]")
            self.add(f"    return [{', '.join(first)}]")
        self.add("")
        self.add("")
        if is_main:
            self.add("def build_graph(checkpointer=None):")
            self.add('    """The graph: nodes, then edges. compile() checks it and returns a runnable graph."""')
        else:
            self.add(f"def {build}():")
            self.add(f'    """The subgraph "{_doc(g.title)}". It has no checkpointer of its own: it uses the parent\'s."""')
        self.add(f"    builder = StateGraph({cls})")
        for nid in g.order():
            if nid not in g.names: continue
            n = g.nodes[nid]; d = n.get("data") or {}; s = len(self.lines) + 1
            fn = g.names[nid]
            if n["type"] == "subgraph":
                ref = g.refs.get(nid) or ""
                fn = f"{self.built[ref][1]}()" if ref in self.built else "StateGraph(dict).compile()  # TODO: the subgraph was not found"
            kw = []
            retry = d.get("retry") if isinstance(d.get("retry"), dict) else {}
            if (attempts := _number(retry.get("max_attempts"), int)) is not None:
                wait = _number(retry.get("initial_interval"))
                kw.append(f"retry_policy=RetryPolicy(max_attempts={attempts}, "
                          f"initial_interval={0.5 if wait is None else wait}, backoff_factor=1.0, jitter=False)")
            if (ttl := _number(d.get("cache_ttl"), int)) is not None:
                kw.append(f"cache_policy=CachePolicy(ttl={ttl})")
            if self.inputs(g, nid):
                kw.append(f"input_schema={_camel(g.names[nid])}Input")
            self.add(f"    builder.add_node({lit(g.names[nid])}, {fn}{''.join(', ' + k for k in kw)})")
            if n["type"] == "agent":
                for step in ("model", "tool", "exit", "handoff"):
                    if step in g.agents[nid]: self.add(f"    builder.add_node({lit(g.agents[nid][step])}, {g.agents[nid][step]})")
            if (timeout := _number(d.get("timeout"))) is not None:
                self.add(f"    # The studio stops {g.names[nid]} after {timeout} s; LangGraph has no timeout for a node that blocks.")
            if is_main: self.span(nid, s)
        self.add("")
        joins = [i for i in g.order() if g.nodes[i]["type"] == "join"]
        first_edge = True
        for nid in g.order():
            n = g.nodes[nid]
            if n["type"] in ("end", "note"): continue
            out = g.out(nid)
            src = "START" if n["type"] == "start" else leave(nid)
            s = len(self.lines) + 1
            if n["type"] == "agent":
                a = {k: lit(v) for k, v in g.agents[nid].items()}
                self.add("    # The Agent node's loop: the model, then each tool call it asks for, then back to the model.")
                self.add(f"    builder.add_edge({lit(g.names[nid])}, {a['model']})")
                more = f", \"handoff\": {a['handoff']}" if "handoff" in a else ""
                self.add(f"    builder.add_conditional_edges({a['model']}, route_{g.agents[nid]['model']}, {{\"tool\": {a['tool']}, \"done\": {a['exit']}{more}}})")
                self.add(f"    builder.add_conditional_edges({a['tool']}, route_{g.agents[nid]['tool']}, {{\"tool\": {a['tool']}, \"model\": {a['model']}}})")
                if "handoff" in a:
                    to = ", ".join(f"{lit(h['node'])}: {lit(h['node'])}" for h in self.handoff_tools(g, nid))
                    self.add(f"    builder.add_conditional_edges({a['handoff']}, route_{g.agents[nid]['handoff']}, {{{to}}})  # hand-offs")
            if n["type"] in ("condition", "foreach") and out:
                if first_edge and n["type"] == "condition":
                    self.add("    # A conditional edge: the router returns a label, and the map says which node it leads to.")
                    first_edge = False
                mapping = ", ".join(f"{lit(e.get('label'))}: {name(e['target'])}" for e in out)
                self.add(f"    builder.add_conditional_edges({src}, route_{g.names[nid]}, {{{mapping}}})")
            elif n["type"] == "start" and self.start_receivers(g):
                targets = [e["target"] for e in out if g.nodes[e["target"]]["type"] != "join"]
                every = ", ".join(dict.fromkeys([name(t) for t in targets] + [lit(g.names[r]) for r in self.start_receivers(g)]))
                self.add(f"    # A chat continues with the agent that answered last: {self.START_FIELD} in the input starts there.")
                self.add(f"    builder.add_conditional_edges(START, {self.start_router(build, is_main)}, [{every}])")
            else:
                targets = [e["target"] for e in out if g.nodes[e["target"]]["type"] != "join"]
                if len(targets) > 1:
                    self.add("    # Several edges from one node: the targets run in parallel, in the same step.")
                for tgt in targets: self.add(f"    builder.add_edge({src}, {name(tgt)})")
            if is_main:
                self.span(nid, s)
                for e in out:
                    if g.nodes[e["target"]]["type"] == "end": self.span(e["target"], len(self.lines))
        for j in joins:
            srcs = [("START" if g.nodes[e["source"]]["type"] == "start" else leave(e["source"]))
                    for e in g.edges if e["target"] == j and e["source"] in g.nodes]
            s = len(self.lines) + 1
            self.add(f"    # Fan-in: {g.names[j]} waits for all of {', '.join(x.strip(chr(34)) for x in srcs)}.")
            self.add(f"    builder.add_edge([{', '.join(srcs)}], {lit(g.names[j])})")
            if is_main: self.span(j, s)
        if is_main:
            extra = ", cache=InMemoryCache()" if cache else ""
            self.add("    # The checkpointer saves the state after every step, so a run paused by interrupt() can resume.")
            self.add(f"    return builder.compile(checkpointer=checkpointer{extra})")
        else:
            self.add(f"    return builder.compile({'cache=InMemoryCache()' if cache else ''})")

    def run(self, main: _Graph) -> None:
        inp, answers, budget = self.example_run(main)
        has_human = "human" in self.uses
        self.add("")
        self.add("")
        self.add(f"# {'=' * (WIDTH - 2)}")
        self.add("# Run it")
        self.add(f"# {'=' * (WIDTH - 2)}")
        self.add("")
        self.add(f"EXAMPLE_INPUT = {lit(inp)}")
        if has_human:
            self.add("# Answers for the Human nodes, in order. When a node has none left, main() asks on the terminal.")
            self.add(f"EXAMPLE_ANSWERS = {lit(answers)}")
        self.add("")
        self.add("")
        self.add("def main() -> None:")
        self.add("    graph = build_graph(MemorySaver())")
        cfg = '{"configurable": {"thread_id": "example"}' + (f', "recursion_limit": {RECURSION + budget}' if budget else "") + "}"
        self.add("    # thread_id names this run in the checkpointer" + ("; For each loops need more steps than the default 25." if budget else "."))
        self.add(f"    config = {cfg}")
        if has_human:
            self.add("    answers = {node: list(values) for node, values in EXAMPLE_ANSWERS.items()}")
            self.add("")
            self.add("    def answer_for(request: dict) -> str:")
            self.add("        queue = answers.get(request[\"node\"]) or []")
            self.add("        value = queue.pop(0) if queue else input(f\"{request['question']}\\n> \")")
            self.add("        print(f\">> {request['node']}: {value}\")")
            self.add("        return value")
            self.add("")
            self.add("    payload = EXAMPLE_INPUT")
            self.add("    while True:")
            self.add("        waiting = []")
            self.add("        # stream_mode=\"updates\": what each node returned, step by step (subgraphs=True: inside subgraphs too).")
            self.add("        for _, update in graph.stream(payload, config, stream_mode=\"updates\", subgraphs=True):")
            self.add("            for node, delta in update.items():")
            self.add("                if node == \"__interrupt__\":")
            self.add("                    waiting += [i for i in delta if i.id not in {w.id for w in waiting}]")
            self.add("                else:")
            self.add("                    print(f\"[{node}] {json.dumps(delta, ensure_ascii=False, default=str)}\")")
            self.add("        if not waiting:")
            self.add("            break")
            self.add("        if len(waiting) == 1:")
            self.add("            payload = Command(resume=answer_for(waiting[0].value))")
            self.add("        else:  # several Human nodes wait at once (parallel branches): answer each by its interrupt id")
            self.add("            payload = Command(resume={i.id: answer_for(i.value) for i in waiting})")
        else:
            self.add("    # stream_mode=\"updates\": what each node returned, step by step (subgraphs=True: inside subgraphs too).")
            self.add("    for _, update in graph.stream(EXAMPLE_INPUT, config, stream_mode=\"updates\", subgraphs=True):")
            self.add("        for node, delta in update.items():")
            self.add("            print(f\"[{node}] {json.dumps(delta, ensure_ascii=False, default=str)}\")")
        self.add("    print(\"Final state:\", json.dumps(graph.get_state(config).values, ensure_ascii=False, default=str, indent=2))")
        self.add("")
        self.add("")
        self.add('if __name__ == "__main__":')
        self.add("    main()")


def to_python(wf: dict, name: str, version: Optional[int] = None, children: Optional[Dict[str, dict]] = None,
              example: Optional[dict] = None) -> Export:
    """The LangGraph Python file for workflow `wf`. `children`: subgraph workflow id -> graph (every level, already
    loaded with the viewer's access). `example`: {"input": {...}, "answers": {node id: [answers]}} for main()."""
    return _Writer(name, version, children or {}, example).write(wf)
