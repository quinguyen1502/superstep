"""What every workflow-to-code exporter shares (TASK-0082, DEC-0051): the sanitised graph, node names, reading order,
subgraph children, the state fields, the helpers a graph needs, and the example input of `main()`.

`python_export` (TASK-0070) and `typescript_export` subclass `GraphWriter` and only write their own language;
`exporters.EXPORTERS` is the registry the service picks from. Nothing here knows a language's syntax.
"""
from __future__ import annotations
import re, unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple
from . import agents, foreach
from .templates import sanitize

SKIP = ("start", "end", "note")  # canvas nodes that are not LangGraph nodes
TITLES = {"agent": "Agent", "llm": "LLM", "foreach": "For each", "mcp": "MCP", "email": "Send email", "subgraph_exit": "Subgraph exit"}
RECURSION = 25  # LangGraph's default step limit (Python and JS)
EMPTY = {"string": "", "number": 0, "integer": 0, "boolean": False, "list": [], "object": {}}


@dataclass
class Export:
    code: str
    nodes: Dict[str, List[List[int]]] = field(default_factory=dict)  # top-level node id -> 1-based [first, last] line ranges
    names: Dict[str, str] = field(default_factory=dict)  # node id ("sub/inner" inside subgraphs) -> LangGraph node name
    filename: str = "workflow.py"


def slug(text: str, fallback: str = "node") -> str:
    s = unicodedata.normalize("NFKD", str(text or "").replace("đ", "d").replace("Đ", "D"))
    s = re.sub(r"[^a-z0-9]+", "_", "".join(c for c in s if not unicodedata.combining(c)).lower()).strip("_")
    if not s: s = fallback
    return f"{fallback}_{s}" if s[0].isdigit() else s


def number(v: Any, kind: type = float) -> Any:
    """`v` when it is a number (an int for `kind=int`), else None. Graph values never reach the code unchecked."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or (kind is int and not isinstance(v, int)): return None
    return v if v == v and abs(v) != float("inf") else None


def one_line(text: Any) -> str:
    return " ".join(str(text or "").split())


def camel(name: str) -> str:
    return "".join(p[:1].upper() + p[1:] for p in name.split("_") if p) or "Node"


class Names:
    """Unique identifiers: never a reserved word of the file's language, never one already taken."""

    def __init__(self, reserved: Iterable[str], taken: Iterable[str] = ()):
        self.used = set(reserved) | set(taken)

    def take(self, base: str) -> str:
        name = base if base not in self.used else f"{base}_node"
        i = 2
        while name in self.used: name, i = f"{base}_{i}", i + 1
        self.used.add(name)
        return name


class Graph:
    """One workflow (the exported one or a subgraph child), after `sanitize`, with its LangGraph names."""

    def __init__(self, raw: dict, title: str, wid: Optional[str]):
        self.raw, self.title, self.wid = raw, title, wid
        self.wf = sanitize(raw)
        self.refs = {n["id"]: (n.get("data") or {}).get("workflow_id") or "" for n in raw.get("nodes") or []
                     if isinstance(n, dict) and n.get("type") == "subgraph"}
        self.nodes = {n["id"]: n for n in self.wf["nodes"]}
        self.edges = [e for e in self.wf["edges"] if e["source"] in self.nodes and e["target"] in self.nodes]
        self.names: Dict[str, str] = {}
        self.cursors: Dict[str, str] = {}
        self.agents: Dict[str, Dict[str, str]] = {}  # Agent node id -> its LangGraph names: model, tool, exit, chat (state field)
        self.fields: List[dict] = list(self.wf["state"])

    def order(self) -> List[str]:
        """Node ids in reading order: breadth first from Start along the edges, then the rest as stored."""
        out: List[str] = []
        queue = [i for i, n in self.nodes.items() if n["type"] == "start"]
        while queue:
            i = queue.pop(0)
            if i in out: continue
            out.append(i); queue += [e["target"] for e in self.edges if e["source"] == i]
        return out + [i for i in self.nodes if i not in out]

    def out(self, nid: str) -> List[dict]:
        return [e for e in self.edges if e["source"] == nid and self.nodes[e["target"]]["type"] != "note"]


class GraphWriter:
    """The language-neutral half of an exporter. Subclasses set RESERVED and write the file."""
    RESERVED: frozenset = frozenset()

    def __init__(self, name: str, version: Optional[int], children: Dict[str, dict], example: Optional[dict]):
        self.title, self.version = one_line(name) or "Workflow", version
        self.children, self.example = children, example or {}
        self.lines: List[str] = []
        self.spans: Dict[str, List[List[int]]] = {}
        self.uses: set = set()
        self.built: Dict[str, Tuple[Graph, str, str]] = {}  # child workflow id -> (graph, build function, state name)

    # -- output --
    def add(self, text: str = "") -> None:
        self.lines.extend(text.split("\n"))

    def span(self, nid: Optional[str], start: int) -> None:
        if nid is not None and len(self.lines) >= start: self.spans.setdefault(nid, []).append([start, len(self.lines)])

    # -- names --
    def build_name(self, base: str) -> str: return f"build_{base}"
    def state_name(self, base: str) -> str: return f"{camel(base)}State"
    def cursor_name(self, name: str) -> str: return f"loop_{name}"

    def name_graphs(self, g: Graph, names: Names) -> None:
        for nid in g.order():
            n = g.nodes[nid]
            if n["type"] in SKIP: continue
            g.names[nid] = names.take(slug((n.get("data") or {}).get("label") or nid, n["type"]))
            if n["type"] == "foreach":
                g.cursors[nid] = names.take(self.cursor_name(g.names[nid]))
            if n["type"] == "agent":  # one node per step, as the studio expands it (DEC-0063)
                base = g.names[nid]
                g.agents[nid] = {"model": names.take(f"{base}_model"), "tool": names.take(f"{base}_tool"), "exit": names.take(f"{base}_end"),
                                 "chat": names.take(f"agent_{base}")}
            if n["type"] == "subgraph":
                ref = g.refs.get(nid) or ""
                if ref in self.children and ref not in self.built:  # each child once, even when used twice
                    child = Graph(self.children[ref], one_line(self.children[ref].get("name")) or ref, ref)
                    self.built[ref] = (child, "", "")
                    self.name_graphs(child, names)
                    base = slug(child.title, "subgraph")
                    self.built[ref] = (child, names.take(self.build_name(base)), names.take(self.state_name(base)))

    def all_fields(self, g: Graph, seen: Tuple[str, ...] = ()) -> List[dict]:
        """The graph's state fields and those of its subgraphs (shared by name, as the studio expands them)."""
        out = list(g.fields); known = {f["name"] for f in out}
        for nid, ref in g.refs.items():
            if ref in self.built and ref not in seen:
                for f in self.all_fields(self.built[ref][0], seen + (ref,)):
                    if f["name"] not in known: out.append(f); known.add(f["name"])
        return out

    def expanded_names(self, g: Graph, prefix: str = "", seen: Tuple[str, ...] = ()) -> Dict[str, str]:
        out = {prefix + nid: name for nid, name in g.names.items()}
        steps = {"model": agents.MODEL, "tool": agents.TOOL, "exit": agents.EXIT}
        out.update({f"{prefix}{nid}{agents.SEP}{steps[k]}": v for nid, a in g.agents.items() for k, v in a.items() if k in steps})
        for nid, ref in g.refs.items():
            if ref in self.built and ref not in seen:
                out.update(self.expanded_names(self.built[ref][0], f"{prefix}{nid}/", seen + (ref,)))
        return out

    def every_field(self, g: Graph) -> List[dict]:
        out = list(g.fields)
        for c in self.children.values(): out += list(sanitize(c)["state"])
        return out

    def children_first(self, g: Graph, seen: Optional[List[str]] = None) -> List[Graph]:
        """Subgraphs, deepest first, each once."""
        seen = [] if seen is None else seen
        for ref in g.refs.values():
            if ref in self.built and ref not in seen:
                seen.append(ref)
                self.children_first(self.built[ref][0], seen)
                seen.remove(ref); seen.append(ref)  # after its own children
        return [self.built[r][0] for r in seen]

    def prepare(self, raw: dict, taken: Iterable[str] = ()) -> Tuple[Graph, List[Graph]]:
        """Name everything and find what the file needs; (main graph, graphs children first then main)."""
        main = Graph(raw, self.title, None)
        self.name_graphs(main, Names(self.RESERVED, {f.get("name") for f in self.every_field(main)} | set(taken)))
        graphs = self.children_first(main) + [main]
        for g in graphs: self.scan(g)
        return main, graphs

    def scan(self, g: Graph) -> None:
        """What the file needs: helpers, stubs, reducers."""
        for f in self.all_fields(g):
            if (f.get("reducer") or "replace") in ("append", "merge", "add"): self.uses.add(f["reducer"])
        for n in g.nodes.values():
            t, d = n["type"], n.get("data") or {}
            if t in ("llm", "human", "retriever", "decision", "email", "mcp") or (t == "tool" and d.get("mode") == "http"):
                self.uses.add("templates")
            if t in ("llm", "decision"): self.uses.add("model")
            if t in ("condition", "decision"): self.uses.add("routing")
            if t == "decision": self.uses.add("decide")
            if t == "human": self.uses.add("human")
            if t == "tool" and d.get("mode") == "code": self.uses.add("code")
            if t == "retriever": self.uses.add("retrieve")
            if t == "mcp": self.uses.add("call_mcp_tool")
            if t == "email": self.uses.add("send_email")
            if t == "agent":
                self.uses.update({"templates", "model", "agent"})
                sources = {x.get("source") for x in d.get("tools") or [] if isinstance(x, dict)}
                if "knowledge" in sources: self.uses.add("retrieve")
                if "mcp" in sources: self.uses.add("call_mcp_tool")
                if agents.needs_approval(d): self.uses.add("human")

    def inputs(self, g: Graph, nid: str) -> List[str]:
        """The node's input fields when they are all state fields (as `node_policy.input_schema`), else none."""
        n = g.nodes[nid]; names = (n.get("data") or {}).get("input_fields")
        known = {f["name"] for f in self.all_fields(g)}
        ok = n["type"] != "subgraph" and isinstance(names, list) and names and all(x in known for x in names)
        return list(names) if ok else []

    @staticmethod
    def http_key(const: str, t: dict) -> str:
        """The constant prefix of an Agent node's HTTP tool (its URL and body templates)."""
        return f"{const}_{re.sub(r'[^A-Za-z0-9]', '_', t.get('name') or '').upper()}"

    @staticmethod
    def rounds(d: dict) -> int:
        """An Agent node's round limit, as the studio reads it."""
        r = d.get("max_rounds", agents.DEFAULT_ROUNDS)
        return r if isinstance(r, int) and not isinstance(r, bool) and 1 <= r <= agents.MAX_ROUNDS else agents.DEFAULT_ROUNDS

    def questions(self, d: dict) -> List[dict]:
        """A Decision node's questions, reduced to what the exported decide() needs."""
        qs = []
        for q in d.get("questions") or []:
            if not isinstance(q, dict): continue
            item: Dict[str, Any] = {"id": q.get("id"), "type": q.get("type"), "instructions": q.get("instructions") or ""}
            if q.get("type") == "choice": item["options"] = [o.get("label") for o in q.get("options") or [] if isinstance(o, dict)]
            if q.get("type") == "score": item["levels"] = list(q.get("levels") or [])
            if q.get("field"): item["field"] = q["field"]
            qs.append(item)
        return qs

    def example_run(self, main: Graph) -> Tuple[dict, Dict[str, list], int]:
        """(example input, Human answers by LangGraph node name, extra steps For each loops need)."""
        fields = {f["name"]: f for f in self.all_fields(main)}
        names = self.expanded_names(main)
        inp = self.example.get("input")
        if not isinstance(inp, dict):
            written = set()
            from .validator import written as writes
            for g in [main] + [c for c, _, _ in self.built.values()]:
                for n in g.nodes.values(): written.update(writes(n))
            inp = {k: EMPTY.get(f.get("type", "string"), "") for k, f in fields.items() if k not in written}
        answers = {names[k]: list(v) for k, v in (self.example.get("answers") or {}).items() if k in names and v}
        budget = max([foreach.step_budget(main.wf) + agents.step_budget(main.wf)] +
                     [foreach.step_budget(c.wf) + agents.step_budget(c.wf) for c, _, _ in self.built.values()])
        return inp, answers, budget
