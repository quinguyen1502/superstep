"""What every workflow-to-code exporter shares: the sanitised graph, node names, reading order,
subgraph children, the state fields, the helpers a graph needs, and the example input of `main()`.

`python_export` and `typescript_export` subclass `GraphWriter` and only write their own language;
`exporters.EXPORTERS` is the registry the service picks from. Nothing here knows a language's syntax.
"""
from __future__ import annotations
import re, unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple
from . import agents, approval_policy, deadlines, foreach
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


# NFKD does not decompose the stroked d (U+0111, U+0110), so map it to a plain d before dropping combining marks.
_STROKED_D = str.maketrans({0x0111: "d", 0x0110: "D"})


def slug(text: str, fallback: str = "node") -> str:
    s = unicodedata.normalize("NFKD", str(text or "").translate(_STROKED_D))
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
        # sanitize blanks resource ids, but a workflow tool's workflow is a graph of this same file: keep it
        kept = {(n.get("id"), t.get("name")): t.get("workflow_id") for n in raw.get("nodes") or [] if isinstance(n, dict) and n.get("type") == "agent"
                for t in (n.get("data") or {}).get("tools") or [] if isinstance(t, dict) and t.get("source") == "workflow"}
        def kept_managed(value):
            """True stays the placeholder. A real adapter id is kept. A browser row is never this flag."""
            if value is True: return True
            if isinstance(value, str) and value and value != "browser": return value
            return None

        managed_nodes, managed_tools = {}, {}
        for n in raw.get("nodes") or []:
            if not isinstance(n, dict): continue
            data = n.get("data") or {}
            if n.get("type") == "mcp" and (flag := kept_managed(data.get("_managed_export"))) is not None:
                managed_nodes[n.get("id")] = flag
            if n.get("type") == "agent":
                for tool in data.get("tools") or []:
                    if isinstance(tool, dict) and (flag := kept_managed(tool.get("_managed_export"))) is not None:
                        managed_tools[(n.get("id"), tool.get("name"))] = flag
        # credentials, the judge and the deadline are read from the raw node: sanitize blanks the ids and drops
        # escalation addresses, and a judge with no credential does not parse
        raw_llm, raw_fallback, raw_policy, raw_deadline = {}, {}, {}, {}
        for n in raw.get("nodes") or []:
            if not isinstance(n, dict): continue
            data, kind = n.get("data") or {}, n.get("type")
            if kind in ("llm", "agent", "decision"): raw_llm[n.get("id")] = str(data.get("credential_id") or "")
            if kind == "llm" and isinstance(data.get("fallback"), dict):
                raw_fallback[n.get("id")] = str(data["fallback"].get("credential_id") or "")
            if kind in ("human", "agent"):
                policy = approval_policy.parse(data)
                if policy:
                    judge = policy.get("judge") or {}
                    # the file may name the mode, rules and model, never the judge credential or instructions
                    raw_policy[n.get("id")] = ({"mode": policy["mode"], "max_per_day": policy.get("max_per_day"),
                        "min_confidence": policy.get("min_confidence"),
                        "rules": [{k: rule.get(k) for k in ("field", "op", "value", "effect")} for rule in policy.get("rules") or []],
                        "judge": {"model": judge.get("model") or ""}},
                        str(judge.get("credential_id") or ""))
                parsed = deadlines.parse(data)
                if parsed:
                    kept = {"after": parsed["after"], "on_timeout": parsed.get("on_timeout") or "reject"}
                    if parsed.get("remind_every"): kept["remind_every"] = parsed["remind_every"]
                    raw_deadline[n.get("id")] = kept
        browser_nodes = {n.get("id"): (n.get("data") or {}).get("_browser_export") for n in raw.get("nodes") or []
                         if isinstance(n, dict) and n.get("type") == "mcp" and isinstance((n.get("data") or {}).get("_browser_export"), dict)}
        browser_tools = {(n.get("id"), tool.get("name")): tool.get("_browser_export") for n in raw.get("nodes") or []
                         if isinstance(n, dict) and n.get("type") == "agent"
                         for tool in (n.get("data") or {}).get("tools") or []
                         if isinstance(tool, dict) and isinstance(tool.get("_browser_export"), dict)}
        # sanitize blanks MCP server ids too; keep which nodes share a server, by an internal key that is never written
        # out: the exporters turn it into an environment variable prefix
        raw_server = {n.get("id"): (n.get("data") or {}).get("server_id") for n in raw.get("nodes") or [] if isinstance(n, dict) and n.get("type") == "mcp"}
        raw_tool_server = {(n.get("id"), t.get("name")): t.get("server_id") for n in raw.get("nodes") or [] if isinstance(n, dict) and n.get("type") == "agent"
                           for t in (n.get("data") or {}).get("tools") or [] if isinstance(t, dict) and t.get("source") == "mcp"}
        # the same for knowledge bases: Retriever nodes and Agent knowledge tools
        raw_kb = {n.get("id"): (n.get("data") or {}).get("knowledge_base_id") for n in raw.get("nodes") or [] if isinstance(n, dict) and n.get("type") == "retriever"}
        raw_tool_kb = {(n.get("id"), t.get("name")): t.get("knowledge_base_id") for n in raw.get("nodes") or [] if isinstance(n, dict) and n.get("type") == "agent"
                       for t in (n.get("data") or {}).get("tools") or [] if isinstance(t, dict) and t.get("source") == "knowledge"}
        # a Send email node sends only when it has an SMTP credential in the studio (else a dry run): keep that fact,
        # never the credential
        raw_mail = {n.get("id"): bool((n.get("data") or {}).get("credential_id")) for n in raw.get("nodes") or [] if isinstance(n, dict) and n.get("type") == "email"}
        for n in self.wf["nodes"]:
            if n["id"] in raw_mail: n["data"]["_email_sends"] = raw_mail[n["id"]]
        for n in self.wf["nodes"]:
            if n["id"] in raw_kb: n["data"]["_knowledge_base"] = str(raw_kb[n["id"]] or "")
            for t in (n.get("data") or {}).get("tools") or [] if n.get("type") == "agent" else []:
                if isinstance(t, dict) and (n["id"], t.get("name")) in raw_tool_kb: t["_knowledge_base"] = str(raw_tool_kb[(n["id"], t.get("name"))] or "")
        for n in self.wf["nodes"]:
            if n["id"] in raw_server: n["data"]["_mcp_server"] = str(raw_server[n["id"]] or "")
            for t in (n.get("data") or {}).get("tools") or [] if n.get("type") == "agent" else []:
                if isinstance(t, dict) and (n["id"], t.get("name")) in raw_tool_server: t["_mcp_server"] = str(raw_tool_server[(n["id"], t.get("name"))] or "")
        for n in self.wf["nodes"]:
            if n["id"] in managed_nodes: n["data"]["_managed_export"] = managed_nodes[n["id"]]
            if n["id"] in browser_nodes: n["data"]["_browser_export"] = browser_nodes[n["id"]]
            if raw_llm.get(n["id"]): n["data"]["_llm_credential"] = raw_llm[n["id"]]
            if raw_fallback.get(n["id"]): n["data"]["_fallback_credential"] = raw_fallback[n["id"]]
            if n["id"] in raw_policy:
                n["data"]["_approval_policy"], n["data"]["_judge_credential"] = raw_policy[n["id"]]
            if n["id"] in raw_deadline: n["data"]["_deadline"] = raw_deadline[n["id"]]
            for t in (n.get("data") or {}).get("tools") or [] if n.get("type") == "agent" else []:
                if isinstance(t, dict) and t.get("source") == "workflow": t["workflow_id"] = kept.get((n["id"], t.get("name"))) or ""
                if isinstance(t, dict) and (n["id"], t.get("name")) in managed_tools: t["_managed_export"] = managed_tools[(n["id"], t.get("name"))]
                if isinstance(t, dict) and (n["id"], t.get("name")) in browser_tools: t["_browser_export"] = browser_tools[(n["id"], t.get("name"))]
        self.refs = {n["id"]: (n.get("data") or {}).get("workflow_id") or "" for n in raw.get("nodes") or []
                     if isinstance(n, dict) and n.get("type") == "subgraph"}
        # workflow tools of Agent nodes: their own graphs, with their own state, called by the tool
        self.tool_refs = [t.get("workflow_id") or "" for n in raw.get("nodes") or [] if isinstance(n, dict) and n.get("type") == "agent"
                          for t in (n.get("data") or {}).get("tools") or [] if isinstance(t, dict) and t.get("source") == "workflow"]
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
        self.browser_policies: Dict[str, dict] = {}
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
            if n["type"] == "agent":  # one node per step, as the studio expands it
                base = g.names[nid]
                g.agents[nid] = {"model": names.take(f"{base}_model"), "tool": names.take(f"{base}_tool"), "exit": names.take(f"{base}_end"),
                                 "chat": names.take(f"agent_{base}")}
                if self.handoff_raw(g, nid): g.agents[nid]["handoff"] = names.take(f"{base}_handoff")
            if n["type"] == "subgraph": self.build_child(g.refs.get(nid) or "", names)
            if n["type"] == "agent":
                for t in (n.get("data") or {}).get("tools") or []:
                    if isinstance(t, dict) and t.get("source") == "workflow": self.build_child(t.get("workflow_id") or "", names)

    def build_child(self, ref: str, names: Names) -> None:
        """Name a subgraph's or workflow tool's workflow and its own nodes, each child once even when used twice."""
        if ref in self.children and ref not in self.built:
            child = Graph(self.children[ref], one_line(self.children[ref].get("name")) or ref, ref)
            self.built[ref] = (child, "", "")
            self.name_graphs(child, names)
            base = slug(child.title, "subgraph")
            self.built[ref] = (child, names.take(self.build_name(base)), names.take(self.state_name(base)))

    def tool_spec_data(self, d: dict) -> dict:
        """An Agent node's data with each workflow tool's child state attached, so the exported tool schemas have the
        child's field types, as `agents.parameters` gives them in a run."""
        tools = [{**t, "snapshot": {"state": (self.children.get(t.get("workflow_id") or "") or {}).get("state") or []}}
                 if isinstance(t, dict) and t.get("source") == "workflow" else t for t in d.get("tools") or []]
        return {**d, "tools": tools}

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
        steps = {"model": agents.MODEL, "tool": agents.TOOL, "exit": agents.EXIT, "handoff": agents.HANDOFF}
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
        """Subgraphs and workflow tools' workflows, deepest first, each once."""
        seen = [] if seen is None else seen
        for ref in [*g.refs.values(), *g.tool_refs]:
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
            if t in ("llm", "agent", "decision"): self.llm_slot(str(d.get("_llm_credential") or ""))
            if t == "llm": self.llm_slot(str(d.get("_fallback_credential") or ""))
            if t == "llm" and isinstance(d.get("fallback"), dict): self.uses.add("fallback")
            if t in ("llm", "agent") and d.get("include_attachments"): self.uses.add("files")
            if t == "llm" and isinstance(d.get("fallback"), dict) and d.get("include_attachments"): self.uses.add("fallback_files")
            if t in ("condition", "decision"): self.uses.add("routing")
            if t == "decision": self.uses.add("decide")
            if t == "human": self.uses.add("human")
            if t == "tool" and d.get("mode") == "code": self.uses.add("code")
            if t == "tool" and d.get("mode") == "http": self.uses.add("http")
            if t == "retriever": self.uses.add("retrieve"); self.kb_prefix(d)
            if t == "mcp": self.note_mcp(d)
            if t == "email": self.uses.add("send_email")
            if t == "agent":
                self.uses.update({"templates", "model", "agent"})
                if self.handoff_raw(g, n["id"]): self.uses.add("handoff")
                sources = {x.get("source") for x in d.get("tools") or [] if isinstance(x, dict)}
                if "knowledge" in sources: self.uses.add("retrieve")
                for tool in d.get("tools") or []:
                    if isinstance(tool, dict) and tool.get("source") == "knowledge": self.kb_prefix(tool)
                if "http" in sources: self.uses.add("http")
                for tool in d.get("tools") or []:
                    if isinstance(tool, dict) and tool.get("source") == "mcp": self.note_mcp(tool)
                if agents.needs_approval(d): self.uses.add("human")
            if t in ("human", "agent"):
                self.llm_slot(str(d.get("_judge_credential") or ""))
                if self.approval_extra(d):
                    self.uses.add("approval")
                    self.uses.add("model")  # the review helper calls the model even when the graph has no LLM node
                    kind = str(((d.get("approval") or {}).get("channel") if isinstance(d.get("approval"), dict) else "") or "").strip().lower()
                    if kind: self.__dict__.setdefault("approval_channels", set()).add(kind)

    def approval_extra(self, data: dict) -> bool:
        """A channel, a deadline or an AI-review policy: the file then carries the approval helpers."""
        approval = data.get("approval") if isinstance(data.get("approval"), dict) else {}
        return bool(approval.get("channel") or data.get("_deadline") or data.get("_approval_policy"))

    def note_mcp(self, data: dict) -> None:
        """A browser connection emits its helper. A managed adapter gets MANAGED_<n>. Anything else is MCP."""
        info = data.get("_browser_export")
        if isinstance(info, dict) and isinstance(info.get("alias"), str) and isinstance(info.get("policy"), dict):
            self.browser_policies[info["alias"]] = info["policy"]
            self.uses.add("browser")
            self.uses.add("templates")
            return
        managed = data.get("_managed_export")
        if managed:
            self.uses.add("managed_operation")
            if isinstance(managed, str): self.managed_prefix(data)  # True is the placeholder: no prefix, two arguments
            return
        self.uses.add("call_mcp_tool")
        self.mcp_prefix(data)  # each server's environment variable prefix, in order of first use

    def kb_prefix(self, data: dict) -> str:
        """KNOWLEDGE_BASE_<n>: the environment variable prefix of a Retriever node's or Agent tool's knowledge base,
        numbered in order of first use. The Studio knowledge base id is never written to the file."""
        bases = self.__dict__.setdefault("knowledge_bases", {})
        kid = str(data.get("_knowledge_base") or "")
        if kid not in bases: bases[kid] = f"KNOWLEDGE_BASE_{len(bases) + 1}"
        return bases[kid]

    def mcp_prefix(self, data: dict) -> str:
        """MCP_SERVER_<n>: the environment variable prefix of a node's or tool's MCP server, numbered in order of first
        use; nodes on the same server share it. The Studio server id itself is never written to the file."""
        servers = self.__dict__.setdefault("mcp_servers", {})
        sid = str(data.get("_mcp_server") or "")
        if sid not in servers: servers[sid] = f"MCP_SERVER_{len(servers) + 1}"
        return servers[sid]

    def llm_slot(self, credential: str) -> str:
        """LLM_CRED_<n> for one Studio credential, numbered in order of first use. An empty id is not a slot, and the
        id itself is never written. When the slot's provider is unset, the node keeps LLM_PROVIDER."""
        credential = str(credential or "")
        if not credential: return ""
        slots = self.__dict__.setdefault("llm_slots", {})
        if credential not in slots: slots[credential] = f"LLM_CRED_{len(slots) + 1}"
        return slots[credential]

    def managed_prefix(self, data: dict) -> str:
        """MANAGED_<n> for one managed server, in order of first use. A blank server id does not collapse two nodes."""
        servers = self.__dict__.setdefault("managed_servers", {})
        sid = str(data.get("_mcp_server") or "") or f"anon:{id(data)}"
        if sid not in servers: servers[sid] = f"MANAGED_{len(servers) + 1}"
        return servers[sid]

    def export_env_names(self) -> List[str]:
        """Literal environment names this file reads, so a project .env.example can list the numbered ones."""
        names: List[str] = []
        for slot in getattr(self, "llm_slots", {}).values():
            names += [f"{slot}_PROVIDER", f"{slot}_API_KEY", f"{slot}_BASE_URL"]
        for prefix in getattr(self, "managed_servers", {}).values():
            names += [f"{prefix}_SETTINGS", f"{prefix}_SECRETS"]
        for kind in sorted(getattr(self, "approval_channels", ())):
            if kind == "telegram": names += ["APPROVAL_TELEGRAM_BOT_TOKEN", "APPROVAL_TELEGRAM_CHAT_ID"]
            else: names.append(f"APPROVAL_{kind.upper()}_WEBHOOK_URL")
        return names

    def inputs(self, g: Graph, nid: str) -> List[str]:
        """The node's input fields when they are all state fields (as `node_policy.input_schema`), else none."""
        n = g.nodes[nid]; names = (n.get("data") or {}).get("input_fields")
        known = {f["name"] for f in self.all_fields(g)}
        ok = n["type"] != "subgraph" and isinstance(names, list) and names and all(x in known for x in names)
        return list(names) if ok else []

    # ---- hand-offs: the exports mirror the engine's steps and names ----
    HANDOFF_FIELD, COUNT_FIELD, START_FIELD = "agent_handoff", "agent_handoffs", "start_agent"  # state fields of a graph with hand-offs

    @staticmethod
    def handoff_raw(g: Graph, nid: str) -> List[dict]:
        """[{name, target, label, description}] of an Agent node's valid hand-offs, as the engine names its tools."""
        d = g.nodes[nid].get("data") or {}
        labels = {i: str((n.get("data") or {}).get("label") or i) for i, n in g.nodes.items() if n["type"] == "agent"}
        taken = {t.get("name") for t in d.get("tools") or [] if isinstance(t, dict)}
        return agents._handoff_tools(nid, d, labels, taken)

    def handoff_tools(self, g: Graph, nid: str) -> List[dict]:
        """The hand-offs with each target's exported node name (`node`)."""
        return [{**h, "node": g.names[h["target"]]} for h in self.handoff_raw(g, nid) if h["target"] in g.names]

    @staticmethod
    def handoff_specs(hs: List[dict]) -> List[dict]:
        return agents.handoff_specs({"handoff_tools": hs})

    def receivers(self, g: Graph) -> List[str]:
        """Agent node ids some Agent of this graph hands off to, in reading order (where a chat may start)."""
        got = {h["target"] for nid in g.agents for h in self.handoff_raw(g, nid)}
        return [i for i in g.order() if i in got]

    def start_receivers(self, g: Graph) -> List[str]:
        """The receivers a chat may start at: none when nodes sit between Start and the first agent (handoffs.straight_to_agents)."""
        starts = [i for i, n in g.nodes.items() if n["type"] == "start"]
        straight = all(g.nodes[e["target"]]["type"] == "agent" for s in starts for e in g.out(s)) and any(g.out(s) for s in starts)
        return self.receivers(g) if straight else []

    def has_handoffs(self, g: Graph) -> bool: return any("handoff" in a for a in g.agents.values())

    @staticmethod
    def max_handoffs(raw: dict) -> int:
        from . import handoffs
        return handoffs.limit(raw)

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
