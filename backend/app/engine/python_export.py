"""Export a workflow as one readable, runnable LangGraph Python file (TASK-0070, REQ-0043, DEC-0045).

`to_python` writes the plain LangGraph equivalent of the canvas, for people learning how a graph is written in code:
the state as a `TypedDict`, one function per node, `build_graph()` with `add_node` / `add_edge` /
`add_conditional_edges`, and a `main()` that runs an example. The file imports nothing from Superstep; it runs with
`pip install langgraph`, offline with a mock model unless `LLM_PROVIDER` is set (owner, REQ-0043 Q1).

The graph is read through `templates.sanitize`, so no credential, knowledge base, server, channel, approver or
secret-like value reaches the file. Retriever, MCP and Send email nodes call stubs (they need studio services).
A Subgraph node becomes its child workflow's own compiled graph, added as a node (Q3). Comments are English (Q2).
The output is a pure function of its input: the same graph gives the same bytes.
"""
from __future__ import annotations
import ast, builtins, inspect, io, json, keyword, re, tokenize
from typing import Any, Dict, List, Optional
from . import foreach
from .export_common import (TITLES, RECURSION, Export, Graph as _Graph, GraphWriter, camel as _camel, number as _number,
                            one_line as _one_line, slug)
from .templating import VAR_RE, _ONE_FILTER
from .tools import TOOLS

PY_TYPES = {"string": "str", "number": "float", "integer": "int", "boolean": "bool", "object": "dict", "list": "list"}
REDUCERS = {"append": "append_items", "merge": "merge_objects", "add": "add_numbers"}

# names the file defines or imports: node functions never take them
RESERVED = set(dir(builtins)) | set(keyword.kwlist) | set(keyword.softkwlist) | {
    "annotations", "json", "os", "re", "string", "httpx", "Annotated", "Any", "Optional", "TypedDict", "StateGraph",
    "START", "END", "Command", "interrupt", "MemorySaver", "RetryPolicy", "CachePolicy", "InMemoryCache", "State",
    "VAR_RE", "FILTER_RE", "FILTERS", "render", "render_args", "LLM_PROVIDER", "DECISION_MODEL", "mock_llm",
    "call_llm", "pick_branch", "decide", "retrieve", "call_mcp_tool", "send_email", "addresses", "build_graph",
    "EXAMPLE_INPUT", "EXAMPLE_ANSWERS", "main", "graph", "builder", *REDUCERS.values()}


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
        if "model" in self.uses:
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
        rows = [(f["name"], self.ann(f)) for f in fields] + [(c, "int") for c in g.cursors.values()]
        if rows and all(n.isidentifier() and not keyword.iskeyword(n) for n, _ in rows):
            self.add(f"class {cls}(TypedDict, total=False):")
            for n, a in rows:
                why = "  # loop position of a For each node" if n in g.cursors.values() else ""
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
            self.add(ret(f"call_llm(prompt, {lit(d.get('model') or 'gpt-4o-mini')})"))
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

    def build(self, g: _Graph, cls: str, build: str, is_main: bool) -> None:
        name = lambda i: "END" if g.nodes[i]["type"] == "end" else lit(g.names[i])  # noqa: E731
        cache = any(_number((n.get("data") or {}).get("cache_ttl"), int) is not None for n in g.nodes.values())
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
            src = "START" if n["type"] == "start" else lit(g.names[nid])
            s = len(self.lines) + 1
            if n["type"] in ("condition", "foreach") and out:
                if first_edge and n["type"] == "condition":
                    self.add("    # A conditional edge: the router returns a label, and the map says which node it leads to.")
                    first_edge = False
                mapping = ", ".join(f"{lit(e.get('label'))}: {name(e['target'])}" for e in out)
                self.add(f"    builder.add_conditional_edges({src}, route_{g.names[nid]}, {{{mapping}}})")
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
            srcs = [("START" if g.nodes[e["source"]]["type"] == "start" else lit(g.names[e["source"]]))
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
