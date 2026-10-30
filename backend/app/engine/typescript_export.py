"""Export a workflow as one readable, runnable LangGraph.js TypeScript file (TASK-0082, REQ-0047, DEC-0051).

The TypeScript twin of `python_export` (TASK-0070): the state as an `Annotation.Root` with the same reducers, one
function per node, `buildGraph()` with `addNode` / `addEdge` / `addConditionalEdges`, and a `main()` that runs an
example. It imports only `@langchain/langgraph` (and LangChain.js when `LLM_PROVIDER` is set), as `npm:` specifiers,
so `deno run` / `deno check` work as is; for Node, drop the `npm:` prefixes.

The graph is read through `templates.sanitize` (`export_common`), so no credential reaches the file: keys come from
environment variables at run time. TypeScript Code nodes are inlined as written; Python Code nodes and registered
Python tool functions become stubs that throw. Retriever, MCP and Send email nodes call stubs, as in the Python file.
An Agent node is its model and tool steps in a loop, as in the Python file (TASK-0125, DEC-0063); its built-in tools are
Python functions, so they throw too, and the model is told the tool failed.
The output is a pure function of its input: the same graph gives the same bytes.
"""
from __future__ import annotations
import json, re
from typing import Any, List, Optional, Tuple
from . import agents, attachments, foreach
from .export_common import TITLES, RECURSION, Export, Graph, GraphWriter, camel, number, one_line, slug
from .templating import VAR_RE, _ONE_FILTER, refs

LANGGRAPH = "npm:@langchain/langgraph@^1.5"
CHECKPOINT = "npm:@langchain/langgraph-checkpoint@^1"
LANGCHAIN = "npm:langchain@^1"
TS_TYPES = {"string": "string", "number": "number", "integer": "number", "boolean": "boolean",
            "object": "Record<string, unknown>", "list": "unknown[]"}
REDUCERS = {"append": ("appendItems", "unknown[]", "[]"), "merge": ("mergeObjects", "Record<string, unknown>", "{}"),
            "add": ("addNumbers", "number", "0")}
WIDTH = 117
RULE = re.compile(r"// --- (.+?) -+")

KEYWORDS = {
    "break", "case", "catch", "class", "const", "continue", "debugger", "default", "delete", "do", "else", "enum", "export",
    "extends", "false", "finally", "for", "function", "if", "import", "in", "instanceof", "new", "null", "return", "super",
    "switch", "this", "throw", "true", "try", "typeof", "var", "void", "while", "with", "as", "implements", "interface",
    "let", "package", "private", "protected", "public", "static", "yield", "await", "async", "any", "boolean", "number",
    "string", "symbol", "type", "from", "of", "get", "set", "declare", "module", "namespace", "require", "never", "unknown",
    "object", "undefined", "arguments", "eval", "constructor", "keyof", "readonly", "infer", "is", "satisfies", "accessor"}
GLOBALS = {
    "console", "fetch", "JSON", "Math", "Object", "Array", "String", "Number", "Boolean", "Promise", "Error", "Date",
    "RegExp", "Map", "Set", "Symbol", "globalThis", "structuredClone", "AbortSignal", "prompt", "process", "Deno",
    "NaN", "Infinity", "parseInt", "parseFloat", "setTimeout", "Record", "Partial", "Response", "Request", "URL",
    "URLSearchParams", "performance"}
HELPERS = {
    "Annotation", "StateGraph", "START", "END", "Command", "interrupt", "MemorySaver", "InMemoryCache", "State", "Update",
    "env", "VAR_RE", "FILTER_RE", "ONE_VAR_RE", "FILTERS", "text", "value", "render", "renderArgs", "LLM_PROVIDER",
    "DECISION_MODEL", "mockLlm", "callLlm", "norm", "escapeRe", "pickBranch", "decide", "retrieve", "callMcpTool",
    "sendEmail", "addresses", "asUpdate", "buildGraph", "EXAMPLE_INPUT", "EXAMPLE_ANSWERS", "main", "graph", "pyJson",
    "MAX_CALLS_PER_ROUND", "RESULT_CHARS", "STEP_CHARS", "JSON_TYPES", "WORDS", "Schema", "ToolSpec", "ToolCall", "ChatMessage",
    "AgentStep", "AgentChat", "agentTask", "mockAgent", "callAgent", "FileRecord", "isImage", "fileList", "withFiles", "filesNote", "callLlmFiles", "callAgentFiles", "checkArguments", "toolText", "shorten", "Question", "Message",
    *(r[0] for r in REDUCERS.values())}


def lit(v: Any, indent: str = "") -> str:
    """A TypeScript literal for `v` (JSON); objects and lists that do not fit on one line get one item per line."""
    if isinstance(v, str): return json.dumps(v, ensure_ascii=False)
    if v is None: return "null"
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, (int, float)): return json.dumps(v) if v == v and abs(v) != float("inf") else "null"
    if isinstance(v, dict):
        items = [f"{lit(str(k))}: {lit(x, indent + '  ')}" for k, x in v.items()]
        one = "{" + ", ".join(items) + "}"
        if len(one) + len(indent) <= 100 and "\n" not in one: return one
        return "{\n" + "".join(f"{indent}  {i},\n" for i in items) + indent + "}"
    if isinstance(v, (list, tuple)):
        items = [lit(x, indent + "  ") for x in v]
        one = "[" + ", ".join(items) + "]"
        if len(one) + len(indent) <= 100 and "\n" not in one: return one
        return "[\n" + "".join(f"{indent}  {i},\n" for i in items) + indent + "]"
    return lit(str(v), indent)


def _doc(text: Any) -> str:
    """Text safe inside a // or /** */ comment."""
    return one_line(text).replace("*/", "* /")


def _rule(title: str) -> str:
    return f"// --- {title} ".ljust(WIDTH, "-")


def _js_regex(pattern: str) -> str:
    return pattern.replace("/", "\\/")


IMPORT_END = re.compile(r"""(?:\bfrom\s*["'][^"']+["']|^import\s*["'][^"']+["'])\s*;?\s*$""", re.S)


def split_imports(source: str) -> Tuple[List[str], List[str]]:
    """(top-level import statements, the rest) of a TypeScript Code node; `export` is dropped from the rest, since
    the code is inlined into a function body."""
    imports: List[str] = []; rest: List[str] = []; cur: List[str] = []
    for ln in source.rstrip("\n").split("\n"):
        if cur or re.match(r"import[\s{*\"']", ln):
            cur.append(ln)
            if IMPORT_END.search("\n".join(cur)): imports.append("\n".join(cur)); cur = []
            continue
        rest.append(re.sub(r"^export\s+(?:default\s+)?(?=(?:async\s+)?function|const|let|var|class|type|interface|enum)", "", ln))
    rest += cur
    while rest and not rest[0].strip(): rest.pop(0)
    return imports, rest


# ---- fixed parts of the file ------------------------------------------------------------------------------------

ENV = r'''
// --- Environment ---------------------------------------------------------------------------------------------
// Settings and credentials (LLM_PROVIDER, OPENAI_API_KEY, ...) are read from environment variables, never written in
// this file. Without --allow-env, Deno gives nothing, and the defaults apply. (--allow-read lets LangGraph.js
// look for its optional LangSmith config.)
function env(name: string): string | undefined {
  try {
    const g = globalThis as { process?: { env: Record<string, string | undefined> }; Deno?: { env: { get(n: string): string | undefined } } };
    return g.Deno ? g.Deno.env.get(name) : g.process?.env[name];
  } catch {
    return undefined;
  }
}
'''

TEMPLATES = r'''
// --- Templates -----------------------------------------------------------------------------------------------
// Prompts use {{ state.field }} references, as on the canvas. render() fills them in from the state: a path walks
// into objects and lists ({{ state.order.items.0 }}) and filters change the value ({{ state.name | upper }}).

const VAR_RE = /%(var)s/g;
const ONE_VAR_RE = /^%(var)s$/;
const FILTER_RE = /%(filter)s/g;

/** JSON as Python writes it (", " and ": "), so text matches the studio's. */
function pyJson(v: unknown): string {
  if (Array.isArray(v)) return "[" + v.map(pyJson).join(", ") + "]";
  if (v !== null && typeof v === "object") {
    return "{" + Object.entries(v).map(([k, x]) => JSON.stringify(k) + ": " + pyJson(x)).join(", ") + "}";
  }
  return JSON.stringify(v ?? null);
}

function text(v: unknown): string {
  return v === null || v === undefined ? "" : typeof v === "string" ? v : pyJson(v);
}

const FILTERS: Record<string, (v: unknown, arg: unknown) => unknown> = {
  upper: (v) => text(v).toUpperCase(),
  lower: (v) => text(v).toLowerCase(),
  trim: (v) => text(v).trim(),
  json: (v) => pyJson(v),
  length: (v) => typeof v === "string" || Array.isArray(v) ? v.length : v && typeof v === "object" ? Object.keys(v).length : 0,
  first: (v) => (typeof v === "string" || Array.isArray(v)) && v.length ? v[0] : null,
  last: (v) => (typeof v === "string" || Array.isArray(v)) && v.length ? v[v.length - 1] : null,
  default: (v, arg) => v === null || v === undefined || v === "" ? arg : v,
  join: (v, arg) => Array.isArray(v) ? v.map(text).join(String(arg ?? "")) : text(v),
  truncate: (v, arg) => {
    const s = text(v), n = Number(arg);
    return s.length <= n ? s : s.slice(0, Math.max(n - 1, 0)) + "…";
  },
};

function value(m: string[], state: object): unknown {
  let v: unknown = (state as Record<string, unknown>)[m[1]];
  for (const key of (m[2] || "").split(".").filter(Boolean)) {
    if (v !== null && typeof v === "object" && !Array.isArray(v)) {
      v = (v as Record<string, unknown>)[key];
    } else if (Array.isArray(v) && /^\d+$/.test(key) && Number(key) < v.length) {
      v = v[Number(key)];
    } else {
      v = null;
      break;
    }
  }
  for (const f of (m[3] || "").matchAll(FILTER_RE)) {
    const raw = f[2];
    const arg = raw === undefined ? null : /^["']/.test(raw) ? raw.slice(1, -1) : parseInt(raw, 10);
    v = FILTERS[f[1]](v, arg);
  }
  return v ?? null;
}

/** The template with each {{ state.x }} replaced by its value. */
function render(template: string, state: object): string {
  return (template || "").replace(VAR_RE, (...m: string[]) => text(value(m, state)));
}

/** render() inside objects and lists; a string that is exactly one reference keeps the value's type. */
function renderArgs(args: unknown, state: object): unknown {
  if (Array.isArray(args)) return args.map((v) => renderArgs(v, state));
  if (args !== null && typeof args === "object") {
    return Object.fromEntries(Object.entries(args).map(([k, v]) => [k, renderArgs(v, state)]));
  }
  if (typeof args === "string") {
    const m = ONE_VAR_RE.exec(args.trim());
    return m ? value(m, state) : render(args, state);
  }
  return args;
}
''' % {"var": _js_regex(VAR_RE.pattern), "filter": _js_regex(_ONE_FILTER.pattern)}

MODEL = r'''
// --- Model ---------------------------------------------------------------------------------------------------
// LLM nodes call callLlm(). Without configuration it is an offline mock: the file runs anywhere, for free, with the
// same answers every time (the studio's mock model). To call a real model, name the provider (any provider
// initChatModel knows) and set its API key; LangChain.js and the provider package are fetched on first use:
//     LLM_PROVIDER=openai OPENAI_API_KEY=sk-... deno run --allow-env --allow-read --allow-net workflow.ts
const LLM_PROVIDER = env("LLM_PROVIDER");

/** Offline answers: a category for classification prompts, else the last line of the prompt echoed back. */
function mockLlm(prompt: string, model: string): string {
  const p = prompt.toLowerCase();
  if (p.includes("classify") || p.includes("phân loại")) {
    const msg = p.includes("message:") ? p.split("message:").at(-1)! : p;
    if (["order", "đơn", "giao hàng", "ship", "a100", "b200", "c300"].some((k) => msg.includes(k))) return "order_status";
    if (["refund", "hoàn tiền", "return"].some((k) => msg.includes(k))) return "refund";
    return "general";
  }
  const tail = prompt.trim() ? prompt.trim().split(/\r?\n/).at(-1)! : "";
  return `[mock:${model}] Answer: ${[...tail].slice(0, 200).join("")}`;
}

async function callLlm(prompt: string, model: string): Promise<string> {
  if (!LLM_PROVIDER) return mockLlm(prompt, model);
  const { initChatModel } = await import("%(langchain)s");
  const reply = await (await initChatModel(model, { modelProvider: LLM_PROVIDER })).invoke(prompt);
  if (typeof reply.content === "string") return reply.content;
  return reply.content.map((b) => ("text" in b && typeof b.text === "string" ? b.text : "")).join("");
}
''' % {"langchain": LANGCHAIN}

FILES = r'''
// --- Attachments ---------------------------------------------------------------------------------------------
// Files a chat sent with the message, for nodes with "Include attachments": a list of { name, type, text?, text_cut?,
// data_url? }. A document reaches the model as text after the prompt. An image reaches it only when its record carries
// a data_url ("data:image/png;base64,...") that you supply; otherwise the model gets a note.
type FileRecord = { name?: string; type?: string; text?: string; text_cut?: boolean; data_url?: string };

function isImage(f: FileRecord): boolean {
  return String(f.type ?? "").startsWith("image/");
}

function fileList(files: unknown): FileRecord[] {
  return Array.isArray(files) ? files.filter((f) => f !== null && typeof f === "object") : [];
}

/** [text, image parts] of one user message with its files. */
function withFiles(prompt: string, files: unknown): [string, unknown[]] {
  const text = [prompt];
  const images: unknown[] = [];
  for (const f of fileList(files)) {
    if (isImage(f)) {
      if (typeof f.data_url === "string" && f.data_url.startsWith("data:")) images.push({ type: "image_url", image_url: { url: f.data_url } });
      else text.push(`An image named ${f.name} was attached, but no image data was given.`);
    } else {
      const cut = f.text_cut ? " (cut)" : "";
      text.push(f.text ? `Attached document "${f.name}"${cut}:\n${f.text}` : `Attached document "${f.name}" has no text.`);
    }
  }
  return [text.filter((t) => t).join("\n\n"), images];
}

/** What the offline mock says it received: each file's kind and name. */
function filesNote(files: unknown): string {
  return "Attachments: " + fileList(files).map((f) => `${isImage(f) ? "image" : "document"} ${f.name}`).join(", ");
}

/** callLlm() with the files sent with the message. */
async function callLlmFiles(prompt: string, model: string, files: unknown): Promise<string> {
  const list = fileList(files);
  if (!LLM_PROVIDER) return mockLlm(prompt, model) + (list.length ? `\n${filesNote(list)}` : "");
  const [text, images] = withFiles(prompt, list);
  const { initChatModel } = await import("%(langchain)s");
  const ask = images.length ? [{ role: "user", content: [{ type: "text", text }, ...images] }] : text;
  // deno-lint-ignore no-explicit-any
  const reply = await (await initChatModel(model, { modelProvider: LLM_PROVIDER })).invoke(ask as any);
  if (typeof reply.content === "string") return reply.content;
  return reply.content.map((b) => ("text" in b && typeof b.text === "string" ? b.text : "")).join("");
}
''' % {"langchain": LANGCHAIN}

AGENT_FILES = r'''

/** callAgent() for a conversation whose user message carries `files`. */
async function callAgentFiles(messages: ChatMessage[], tools: ToolSpec[] | null, model: string): Promise<[string, ToolCall[]]> {
  const files = messages.filter((m) => m.role === "user").flatMap((m) => fileList(m.files));
  if (!LLM_PROVIDER) {
    const [text, calls] = mockAgent(messages, tools, model);
    return [text && files.length ? `${text}\n${filesNote(files)}` : text, calls];
  }
  return callAgent(messages.map((m) => {
    if (!m.files) return m;
    const [content, images] = withFiles(m.content, m.files);
    return { role: "user", content, images };
  }), tools, model);
}
'''

ROUTING = r'''
// --- Routing -------------------------------------------------------------------------------------------------
const PUNCTUATION = /^[\s!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~]+|[\s!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~]+$/g;

function norm(x: string): string {
  return x.trim().replace(PUNCTUATION, "").toLowerCase();
}

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** The label `value` names: an exact match, then a match ignoring case, spaces and punctuation, then the longest
 * label found in it as a whole word. null when no label (or two equally long ones) matches. */
function pickBranch(value: string, labels: string[]): string | null {
  if (labels.includes(value)) return value;
  for (const label of labels) if (norm(label) && norm(label) === norm(value)) return label;
  const word = (k: string) => new RegExp(`(?<![\\p{L}\\p{N}_])${escapeRe(norm(k))}(?![\\p{L}\\p{N}_])`, "u");
  const hits = labels.filter((k) => norm(k) && word(k).test(value.toLowerCase()));
  if (!hits.length) return null;
  const best = Math.max(...hits.map((k) => norm(k).length));
  const top = hits.filter((k) => norm(k).length === best);
  return top.length === 1 ? top[0] : null;
}
'''

DECIDE = r'''
// --- Decisions -----------------------------------------------------------------------------------------------
// In Superstep a Decision node asks TypeSafe's Jev model typed questions. Here the mock answers offline (the first
// option named in the text, the lowest score, 0.5 for yes/no); with LLM_PROVIDER set, callLlm() answers instead.
const DECISION_MODEL = env("DECISION_MODEL") ?? "gpt-4o-mini";

type Question = { id: string; type: string; instructions: string; options?: string[]; levels?: string[]; field?: string };

/** The answer to one question: an option label ("choice"), a level index ("score") or 0 to 1 ("noul"). */
async function decide(text: string, question: Question): Promise<unknown> {
  const { type: kind, instructions } = question;
  if (kind === "choice") {
    const labels = question.options ?? [];
    if (!LLM_PROVIDER) {
      const low = text.toLowerCase();
      return labels.find((x) => new RegExp(`(?<![\\p{L}\\p{N}_])${escapeRe(x.toLowerCase())}(?![\\p{L}\\p{N}_])`, "u").test(low)) ?? labels[0];
    }
    const reply = await callLlm(`${instructions}\n\nText:\n${text}\n\nAnswer with one of: ${labels.join(", ")}`, DECISION_MODEL);
    return pickBranch(reply.trim(), labels) ?? labels[0];
  }
  if (!LLM_PROVIDER) return kind === "score" ? 0.0 : 0.5;
  const reply = kind === "score"
    ? await callLlm(`${instructions}\n\nText:\n${text}\n\nLevels:\n${(question.levels ?? []).map((l, i) => `${i}: ${l}`).join("\n")}\n\nAnswer with the level number.`, DECISION_MODEL)
    : await callLlm(`${instructions}\n\nText:\n${text}\n\nHow likely is it true, from 0 to 1? Answer with a number.`, DECISION_MODEL);
  const found = /\d+(?:\.\d+)?/.exec(reply);
  return found ? parseFloat(found[0]) : 0.0;
}
'''

AGENT = r'''
// --- Agents --------------------------------------------------------------------------------------------------
// An Agent node is a loop of two nodes: the model node asks the model, which answers or asks for tool calls, and the
// tool node runs that round's calls. They run together unless the node turns that off. Without LLM_PROVIDER,
// callAgent() is an offline mock: it calls the tools the task names, then answers with the last result.
const MAX_CALLS_PER_ROUND = 8;
const RESULT_CHARS = 8000;  // a tool result goes back to the model shortened to this
const STEP_CHARS = 2000;  // ... and into the steps field shortened to this

/** Calls of one round that run together. Off is one. Otherwise 4, or STUDIO_AGENT_PARALLEL_TOOLS when it is 1..8.
 * env() is the reader above: Node has no Deno, and Deno without --allow-env must stay at the default. */
function waveCap(enabled: boolean): number {
  if (!enabled) return 1;
  const raw = env("STUDIO_AGENT_PARALLEL_TOOLS");
  if (raw == null || !raw.trim()) return 4;
  const n = Number(raw);
  return Number.isInteger(n) && n >= 1 && n <= 8 ? n : 4;
}

type Schema = { type?: string; properties?: Record<string, unknown>; required?: string[] };
type ToolSpec = { name: string; description: string; parameters: Schema };
type ToolCall = { id: string; name: string; args: unknown };
type ChatMessage = { role: string; content: string; tool_calls?: ToolCall[]; tool_call_id?: string; name?: string; files?: unknown; images?: unknown[] };
type AgentStep = { tool: string; args: unknown; result: string; status: string; ms: number; approval?: string };
/** An Agent node's conversation, in its own state field while the loop runs. */
type AgentChat = { messages: ChatMessage[]; pending: ToolCall[]; rounds: number; steps: AgentStep[]; answer: string | null };

const WORDS = /[\p{L}\p{N}_]+/gu;

/** The last user message and the tool results after it. */
function agentTask(messages: ChatMessage[]): [string, ChatMessage[]] {
  const last = messages.map((m) => m.role).lastIndexOf("user");
  return [last >= 0 ? messages[last].content || "" : "", messages.slice(last + 1).filter((m) => m.role === "tool")];
}

/** Offline agent: with no tool result yet it calls every tool the task names (or the best match), then answers. */
function mockAgent(messages: ChatMessage[], tools: ToolSpec[] | null, model: string): [string, ToolCall[]] {
  const [task, results] = agentTask(messages);
  if (tools?.length && !results.length) {
    const words = new Set(task.toLowerCase().match(WORDS));
    const score = (t: ToolSpec) =>
      [...new Set(`${t.name.replaceAll("_", " ")} ${t.description || ""}`.toLowerCase().match(WORDS))].filter((w) => words.has(w)).length;
    const named = tools.filter((t) => new RegExp("(^|[^a-z0-9_])" + t.name.toLowerCase() + "([^a-z0-9_]|$)").test(task.toLowerCase()));
    const picked = named.length >= 2 ? named : [tools.reduce((a, t) => (score(t) > score(a) ? t : a))];
    const calls: ToolCall[] = picked.map((best, i) => {
      const required = best.parameters?.required ?? [];
      const empty: Record<string, unknown> = { number: 0, integer: 0, boolean: false, array: [], object: {} };
      const args: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(best.parameters?.properties ?? {})) {
        const type = v !== null && typeof v === "object" && "type" in v ? v.type : "string";
        if (type === "string") args[k] = task;
        else if (required.includes(k)) args[k] = empty[String(type)] ?? null;
      }
      return { id: `mock_call_${i + 1}`, name: best.name, args };
    });
    return ["", calls];
  }
  const said = results.length ? results.at(-1)!.content || "" : task.trim() ? task.trim().split(/\r?\n/).at(-1)! : "";
  return [`[mock:${model}] Answer: ${[...said].slice(0, 200).join("")}`, []];
}

/** One model call: [text, tool calls]. With tools null the model has to answer. */
async function callAgent(messages: ChatMessage[], tools: ToolSpec[] | null, model: string): Promise<[string, ToolCall[]]> {
  if (!LLM_PROVIDER) return mockAgent(messages, tools, model);
  const { initChatModel } = await import("%(langchain)s");
  const llm = await initChatModel(model, { modelProvider: LLM_PROVIDER });
  // LangChain.js turns { role, content, tool_calls, tool_call_id } objects into its message classes.
  // deno-lint-ignore no-explicit-any
  const history: any[] = messages.map((m) =>
    m.tool_calls ? { ...m, tool_calls: m.tool_calls.map((c) => ({ ...c, args: c.args ?? {} })) }
    : m.images?.length ? { role: m.role, content: [{ type: "text", text: m.content }, ...m.images] } : m
  );
  const reply = tools?.length
    ? await llm.bindTools(tools.map((t) => ({ type: "function" as const, function: t }))).invoke(history)
    : await llm.invoke(history);
  const text = typeof reply.content === "string"
    ? reply.content
    : reply.content.map((b) => ("text" in b && typeof b.text === "string" ? b.text : "")).join("");
  return [text.trim(), (reply.tool_calls ?? []).map((c, i) => ({ id: c.id || `call_${i}`, name: c.name, args: c.args ?? {} }))];
}

const JSON_TYPES: Record<string, (v: unknown) => boolean> = {
  string: (v) => typeof v === "string",
  number: (v) => typeof v === "number",
  integer: (v) => Number.isInteger(v),
  boolean: (v) => typeof v === "boolean",
  array: (v) => Array.isArray(v),
  object: (v) => v !== null && typeof v === "object" && !Array.isArray(v),
};

/** Why the model's arguments do not fit the tool's parameters: required names and top-level JSON types. */
function checkArguments(schema: Schema, args: unknown): string | null {
  if (!JSON_TYPES.object(args)) return "arguments must be a JSON object";
  const given = args as Record<string, unknown>;
  const missing = (schema.required ?? []).filter((k) => !Object.hasOwn(given, k));
  if (missing.length) return `missing argument(s): ${missing.join(", ")}`;
  for (const [k, v] of Object.entries(given)) {
    const prop = Object.hasOwn(schema.properties ?? {}, k) ? schema.properties![k] : null;
    const want = prop !== null && typeof prop === "object" && "type" in prop ? prop.type : null;
    if (typeof want !== "string" || !Object.hasOwn(JSON_TYPES, want) || v === null) continue;
    if (!JSON_TYPES[want](v)) return `argument ${k} must be of type ${want}`;
  }
  return null;
}

function toolText(value: unknown): string {
  return typeof value === "string" ? value : pyJson(value);
}

function shorten(s: string, n: number): string {
  const chars = [...s];
  return chars.length <= n ? s : chars.slice(0, n).join("") + `… (shortened from ${chars.length} characters)`;
}
''' % {"langchain": LANGCHAIN}

STUBS = {
    "retrieve": r'''
/** Retriever nodes search a Superstep knowledge base, which this file cannot reach.
 * TODO: search your own index for `query`, for example with a LangChain.js vector store retriever
 * (`vectorStore.asRetriever(topK).invoke(query)`). */
async function retrieve(query: string, topK: number): Promise<unknown[]> {
  void query, topK;
  return [];
}
''',
    "call_mcp_tool": r'''
/** MCP nodes call a tool on an MCP server connected in Superstep, which this file does not include.
 * TODO: call the tool with an MCP client, for example @langchain/mcp-adapters (MultiServerMCPClient). */
async function callMcpTool(tool: string, args: unknown): Promise<unknown> {
  void tool, args;
  return null;
}
''',
    "send_email": r'''
function addresses(value: unknown): string[] {
  const items = Array.isArray(value) ? value : [value];
  return items.filter((x) => x !== null && x !== undefined && x !== "")
    .flatMap((x) => String(x).split(/[,;\n]/)).map((p) => p.trim()).filter(Boolean);
}

type Message = { to: string[]; cc: string[]; bcc: string[]; subject: string; body: string };

/** Send email nodes send through an SMTP credential in Superstep. This file never sends: like a studio dry run,
 * it prints the message and returns what it would have sent.
 * TODO: send it with your own mail library and SMTP settings from environment variables. */
async function sendEmail(message: Message): Promise<Record<string, unknown>> {
  console.log(`(e-mail not sent) to ${message.to.join(", ")}: ${message.subject}`);
  return { sent: false, dry_run: true, to: message.to, cc: message.cc, bcc: message.bcc, subject: message.subject,
    message_id: null, preview: message.body.slice(0, 2000) };
}
''',
}

REDUCER_CODE = {
    "append": r'''
/** Reducer "append": a list that collects every value written to it, from parallel branches too. */
function appendItems(current: unknown, next: unknown): unknown[] {
  const list = current === null || current === undefined ? [] : Array.isArray(current) ? current : [current];
  return list.concat(Array.isArray(next) ? next : next === null || next === undefined ? [] : [next]);
}
''',
    "merge": r'''
/** Reducer "merge": a shallow merge of objects; later keys win. */
function mergeObjects(current: unknown, next: unknown): Record<string, unknown> {
  const obj = (x: unknown) => (x !== null && typeof x === "object" && !Array.isArray(x) ? x : {});
  return { ...obj(current), ...obj(next) };
}
''',
    "add": r'''
/** Reducer "add": the sum of every number written to it. */
function addNumbers(current: unknown, next: unknown): number {
  const num = (x: unknown) => (typeof x === "number" ? x : 0);
  return num(current) + num(next);
}
''',
}


class _Writer(GraphWriter):
    RESERVED = frozenset(KEYWORDS | GLOBALS | HELPERS)

    def __init__(self, *a):
        super().__init__(*a)
        self.imports: List[str] = []  # import statements of TypeScript Code nodes, hoisted to the top

    def write(self, raw: dict) -> Export:
        main, graphs = self.prepare(raw)
        self.body(graphs, main)
        self.lines = [_rule(m.group(1)) if (m := RULE.fullmatch(ln)) else ln for ln in self.lines]
        head = self.header()
        self.lines = head + self.lines
        spans = {nid: [[a + len(head), b + len(head)] for a, b in r] for nid, r in self.spans.items()}
        return Export("\n".join(self.lines).rstrip("\n") + "\n", spans, self.expanded_names(main),
                      f"{slug(self.title, 'workflow')}.ts")

    def state_name(self, base: str) -> str: return f"{camel(base)}State"

    def header(self) -> List[str]:
        body = "\n".join(self.lines)
        uses = lambda n: re.search(rf"(?<![\w.\"]){n}\b", body) is not None  # noqa: E731
        v = f" (version {self.version})" if self.version is not None else ""
        file = f"{slug(self.title, 'workflow')}.ts"
        net = " --allow-net" if "fetch(" in body else ""
        doc = ["/**", f" * {_doc(self.title)}{v}: a LangGraph.js graph exported from Superstep.", " *",
               " * The graph on the canvas, written as TypeScript: the state, one function per node, and buildGraph(),",
               " * which connects them. Run it with Deno (the npm: packages are fetched on the first run):", " *",
               f" *     deno run --allow-env --allow-read{net} {file}", " *",
               " * For Node, drop the \"npm:\" prefixes and versions, `npm i @langchain/langgraph @langchain/core`, then",
               f" * `npx tsx {file}`.", " *"]
        if "agent" in self.uses:
            doc += [" * LLM and Agent nodes use an offline mock model unless LLM_PROVIDER is set (see callLlm and callAgent",
                    " * below).", " *"]
        elif "model" in self.uses:
            doc += [" * LLM nodes use an offline mock model unless LLM_PROVIDER is set (see callLlm below).", " *"]
        if "agent_builtin" in self.uses:
            doc += [" * An Agent node's built-in tools are Python functions of the Superstep server: here they throw, and the",
                    " * model is told the tool failed. Port them to TypeScript.", " *"]
        if "code" in self.uses:
            doc += [" * TypeScript Code nodes run here as written on the canvas, without the studio's sandbox: read them",
                    " * first. Python Code nodes and Python tool functions are stubs that throw: port them to TypeScript.", " *"]
        doc += [" * Credentials, knowledge bases, MCP servers and approval channels are not exported; keys are read from",
                " * environment variables.", " */"]
        lg = sorted((n for n in ("Annotation", "Command", "END", "MemorySaver", "START", "StateGraph", "interrupt") if uses(n)),
                    key=lambda n: n.lower())
        out = [f"import {{ {', '.join(lg)} }} from \"{LANGGRAPH}\";"]
        if uses("InMemoryCache"): out.append(f"import {{ InMemoryCache }} from \"{CHECKPOINT}\";")
        if self.imports:
            out += ["// imports of the TypeScript Code nodes"] + self.imports
        return doc + out + [""]

    def body(self, graphs: List[Graph], main: Graph) -> None:
        self.add(ENV.rstrip())
        if "templates" in self.uses: self.add(TEMPLATES.rstrip())
        if "model" in self.uses: self.add(MODEL.rstrip())
        if "agent" in self.uses: self.add(AGENT.rstrip())
        if "files" in self.uses: self.add(FILES.rstrip() + (AGENT_FILES.rstrip() if "agent" in self.uses else ""))
        if "routing" in self.uses or "decide" in self.uses: self.add(ROUTING.rstrip())
        if "decide" in self.uses: self.add(DECIDE.rstrip())
        stubs = [k for k in STUBS if k in self.uses]
        if stubs:
            self.add("\n// --- Studio services ------------------------------------------------------------------------------------")
            self.add("// These nodes use services of the Superstep server. The stubs keep the graph running; replace them.")
            for k in stubs: self.add(STUBS[k].rstrip())
        reducers = [k for k in REDUCERS if k in self.uses]
        if reducers:
            self.add("\n// --- Reducers -------------------------------------------------------------------------------------------")
            self.add("// A reducer says how a node's output combines with the field's current value. Without one, the new")
            self.add("// value replaces the old one, and two parallel branches writing the same field in one step is an error.")
            for k in reducers: self.add(REDUCER_CODE[k].rstrip())
        for g in graphs: self.graph(g, g is main)
        self.run(main)

    # -- one graph --
    def graph(self, g: Graph, is_main: bool) -> None:
        cls = "State" if is_main else self.built[g.wid][2]
        build = "buildGraph" if is_main else self.built[g.wid][1]
        what = "Graph" if is_main else f'Subgraph "{_doc(g.title)}"'
        self.add(f"\n// {'=' * (WIDTH - 3)}")
        self.add(f"// {what}")
        self.add(f"// {'=' * (WIDTH - 3)}")
        for nid in [i for i in g.order() if g.nodes[i]["type"] == "note"]:
            s = len(self.lines) + 1
            text = str((g.nodes[nid].get("data") or {}).get("text") or "").strip()
            self.add("\n// Note on the canvas:")
            for ln in text.splitlines() or [""]: self.add(f"//   {ln.rstrip()}" if ln.strip() else "//")
            if is_main: self.span(nid, s + 1)
        self.state(g, cls, is_main)
        for nid in g.order():
            if nid in g.names:
                s = len(self.lines) + 1
                self.node(g, nid, cls)
                if is_main: self.span(nid, s + 1)  # skip the blank line before the code
        self.build(g, cls, build, is_main)

    def ann(self, f: dict) -> str:
        r = f.get("reducer") or "replace"
        if r in REDUCERS:
            fn, typ, default = REDUCERS[r]
            return f"Annotation<{typ}, unknown>({{ reducer: {fn}, default: () => {default} }})"
        return f"Annotation<{TS_TYPES.get(f.get('type', 'string'), 'unknown')}>()"

    def state(self, g: Graph, cls: str, is_main: bool) -> None:
        self.add("")
        if is_main:
            self.add("// The state is an object shared by every node. A node returns only the fields it changes, and LangGraph")
            self.add("// merges them into the state (through the field's reducer, if it has one).")
        else:
            self.add("// A subgraph has its own state. It shares fields with the parent graph by name: the parent passes them")
            self.add("// in, and the fields the subgraph changed come back when it ends.")
        self.add(f"const {cls} = Annotation.Root({{")
        for f in self.all_fields(g): self.add(f"  {lit(f['name'])}: {self.ann(f)},")
        for c in g.cursors.values(): self.add(f"  {lit(c)}: Annotation<number>(),  // loop position of a For each node")
        for a in g.agents.values(): self.add(f"  {lit(a['chat'])}: Annotation<AgentChat | null>(),  // an Agent node's conversation")
        self.add("});")
        self.add(f"type {cls} = typeof {cls}.State;")
        if is_main:
            self.add("type Update = typeof State.Update;")
            self.add("/** A node's result: the fields it changes (their values come from the canvas, typed at run time). */")
            self.add("const asUpdate = (fields: Record<string, unknown>) => fields as Update;")

    def node(self, g: Graph, nid: str, cls: str) -> None:
        n = g.nodes[nid]; t, d = n["type"], n.get("data") or {}
        name, label = g.names[nid], _doc(d.get("label") or nid)
        const = name.upper()
        head = f'{TITLES.get(t, camel(t))} node "{label}" (id: {_doc(nid)})'
        out = d.get("output_field")
        ret = (lambda expr: f"  return asUpdate({{ {lit(out)}: {expr} }});") if out else (lambda expr: f"  {expr};\n  return {{}};")
        sig = f"async function {name}(state: {cls}): Promise<Update> {{"
        self.add("")
        if t == "llm":
            self.add(f"const {const}_PROMPT = {lit(d.get('prompt') or '')};")
            self.add("")
            self.add(f"/** {head}. */")
            self.add(sig)
            self.add(f"  const prompt = render({const}_PROMPT, state);")
            files = attachments.field_of(d)
            self.add(ret(f"await callLlmFiles(prompt, {lit(d.get('model') or 'gpt-4o-mini')}, (state as Record<string, unknown>)[{lit(files)}])" if files
                         else f"await callLlm(prompt, {lit(d.get('model') or 'gpt-4o-mini')})"))
            self.add("}")
        elif t == "human":
            self.add(f"const {const}_PROMPT = {lit(d.get('prompt') or '')};")
            self.add("")
            self.add(f"/** {head}.")
            self.add(" *")
            self.add(" * interrupt() pauses the run and hands the question to the caller (see main()). The caller resumes it")
            self.add(" * with new Command({ resume: answer }): the node then runs again from the top and interrupt() returns it.")
            extra = []
            if (d.get("approval") or {}).get("channel"): extra.append(f"also asks on {_doc(str(d['approval']['channel']).title())}")
            if d.get("deadline"): extra.append("has a deadline with reminders")
            if extra: self.add(f" * In Superstep this node {' and '.join(extra)}; that is not part of LangGraph.")
            self.add(" */")
            self.add(sig)
            self.add(f"  const answer = interrupt({{ node: {lit(name)}, question: render({const}_PROMPT, state) }});")
            self.add(ret("answer"))
            self.add("}")
        elif t == "condition":
            self.add(f"/** {head}: changes nothing. The routing is route_{name}(), on the edges after it. */")
            self.add(sig)
            self.add("  void state;")
            self.add("  return {};")
            self.add("}")
            self.router(g, nid, cls)
        elif t == "join":
            self.add(f"/** {head}: runs once, after every branch that leads here has finished (see buildGraph). */")
            self.add(sig)
            self.add("  void state;")
            self.add("  return {};")
            self.add("}")
        elif t == "foreach":
            self.foreach(g, nid, cls, head)
        elif t == "decision":
            self.decision(g, nid, cls, head, sig)
        elif t == "tool":
            self.tool(g, nid, cls, head, ret, sig)
        elif t == "retriever":
            self.add(f"const {const}_QUERY = {lit(d.get('query') or '')};")
            self.add("")
            self.add(f"/** {head}: the chunks of a knowledge base that best match the query (see retrieve). */")
            self.add(sig)
            self.add(ret(f"await retrieve(render({const}_QUERY, state), {number(d.get('top_k'), int) or 4})"))
            self.add("}")
        elif t == "mcp":
            self.add(f"const {const}_ARGUMENTS = {lit(d.get('arguments') or {})};")
            self.add("")
            self.add(f"/** {head}: calls the MCP tool {lit(_doc(d.get('tool')))} (see callMcpTool). */")
            self.add(sig)
            self.add(ret(f"await callMcpTool({lit(d.get('tool') or '')}, renderArgs({const}_ARGUMENTS, state))"))
            self.add("}")
        elif t == "email":
            self.email(g, nid, cls, head, sig)
        elif t == "agent":
            self.agent(g, nid, cls, head, sig)
        elif t == "subgraph":
            ref = g.refs.get(nid) or ""
            build = self.built[ref][1] if ref in self.built else None
            self.add(f"// {head}: the workflow \"{_doc(self.built[ref][0].title) if build else _doc(ref)}\" runs as a subgraph.")
            self.add(f"// buildGraph() adds {build or 'it'}() as the node: a compiled graph can be a node of another graph.")
        else:  # subgraph_exit or an unknown type: a pass-through
            self.add(f"/** {head}. */")
            self.add(sig)
            self.add("  void state;")
            self.add("  return {};")
            self.add("}")
        if (names := self.inputs(g, nid)):
            fields = {f["name"]: f for f in self.all_fields(g)}
            self.add("")
            self.add(f"// {camel(name)}Input: the only fields {name}() sees (input in buildGraph).")
            self.add(f"const {camel(name)}Input = Annotation.Root({{ {', '.join(f'{lit(x)}: {self.ann(fields[x])}' for x in names)} }});")

    def router(self, g: Graph, nid: str, cls: str) -> None:
        d = g.nodes[nid].get("data") or {}; fld = d.get("field") or ""
        labels = [e.get("label") for e in g.out(nid)]
        default = d.get("default") or ("default" if "default" in labels else None)
        self.add("")
        self.add(f"/** The branch to take after \"{_doc(d.get('label') or nid)}\": the edge label that state[{_doc(lit(fld))}] names. */")
        self.add(f"function route_{g.names[nid]}(state: {cls}): string {{")
        self.add(f"  const raw: unknown = (state as Record<string, unknown>)[{lit(fld)}];")
        self.add("  const value = (raw === null || raw === undefined ? \"\" : String(raw)).trim();")
        self.add(f"  const label = pickBranch(value, {lit(labels)});")
        if default and default in labels:
            self.add(f"  return label ?? {lit(default)};")
        else:
            msg = lit(f"{one_line(d.get('label') or nid)}: no edge label matches (and no default) ")
            self.add(f"  if (label === null) throw new Error({msg} + JSON.stringify(value.slice(0, 100)));")
            self.add("  return label;")
        self.add("}")

    def foreach(self, g: Graph, nid: str, cls: str, head: str) -> None:
        d = g.nodes[nid].get("data") or {}; name, cur = g.names[nid], g.cursors[nid]
        src, item, idx = d.get("items_field") or "", d.get("item_field") or "", d.get("index_field")
        cap = foreach.max_items(d)
        self.add(f"/** {head}: one item of state[{_doc(lit(src))}] per visit, in order.")
        self.add(" *")
        self.add(" * The \"each\" edge leads into the loop body, which comes back here; after the last item the \"done\" edge")
        self.add(f" * leaves the loop. The position is kept in state[{_doc(lit(cur))}]. */")
        self.add(f"async function {name}(state: {cls}): Promise<Update> {{")
        self.add(f"  const items: unknown = (state as Record<string, unknown>)[{lit(src)}] ?? [];")
        self.add(f"  if (!Array.isArray(items) || items.length > {cap}) {{")
        self.add(f"    throw new Error({lit(f'{one_line(d.get('label') or nid)}: state[{lit(src)}] must be a list of at most {cap} items')});")
        self.add("  }")
        self.add(f"  const position = (state as Record<string, unknown>)[{lit(cur)}] as number | undefined ?? 0;")
        self.add(f"  if (position >= items.length) return asUpdate({{ {lit(cur)}: 0 }});  // finished: back to 0 for an enclosing loop")
        upd = f"{lit(cur)}: position + 1, {lit(item)}: items[position]" + (f", {lit(idx)}: position" if idx else "")
        self.add(f"  return asUpdate({{ {upd} }});")
        self.add("}")
        self.add("")
        self.add(f"function route_{name}(state: {cls}): string {{")
        self.add(f"  return (state as Record<string, unknown>)[{lit(cur)}] ? \"each\" : \"done\";")
        self.add("}")

    def decision(self, g: Graph, nid: str, cls: str, head: str, sig: str) -> None:
        d = g.nodes[nid].get("data") or {}; const = g.names[nid].upper()
        self.add(f"const {const}_TEXT = {lit(d.get('text') or '')};")
        self.add(f"const {const}_QUESTIONS: Question[] = {lit(self.questions(d))};")
        self.add("")
        self.add(f"/** {head}: answers each question about the text (see decide). */")
        self.add(sig)
        self.add(f"  const text = String(renderArgs({const}_TEXT, state));")
        self.add("  const update: Record<string, unknown> = {};")
        self.add("  const answers: Record<string, unknown> = {};")
        self.add(f"  for (const question of {const}_QUESTIONS) {{")
        self.add("    const answer = await decide(text, { ...question, instructions: render(question.instructions, state) });")
        self.add("    answers[question.id] = { type: question.type, [question.type]: answer };")
        self.add("    if (question.field) update[question.field] = answer;")
        self.add("  }")
        if d.get("output_field"): self.add(f"  update[{lit(d['output_field'])}] = answers;")
        self.add("  return asUpdate(update);")
        self.add("}")

    def tool(self, g: Graph, nid: str, cls: str, head: str, ret, sig: str) -> None:
        d = g.nodes[nid].get("data") or {}; name, const = g.names[nid], g.names[nid].upper()
        mode = d.get("mode") or "function"
        lang = str(d.get("language") or "python")
        if mode == "http":
            method = str(d.get("method") or "GET")
            self.add(f"const {const}_URL = {lit(d.get('url') or '')};")
            self.add(f"const {const}_BODY = {lit(d.get('body') or '')};")
            self.add("")
            self.add(f"/** {head}: an HTTP request; the JSON reply (or the text) is the result.")
            self.add(" * The studio only calls public addresses and never follows redirects. */")
            self.add(sig)
            self.add(f"  const body = render({const}_BODY, state);")
            self.add(f"  const response = await fetch(render({const}_URL, state), {{")
            self.add(f"    method: {lit(method)}, body: {'undefined' if method in ('GET', 'HEAD') else 'body || undefined'},")
            self.add("    headers: { \"Content-Type\": \"application/json\" }, redirect: \"manual\", signal: AbortSignal.timeout(30_000),")
            self.add("  });")
            self.add("  const raw = await response.text();")
            self.add("  let result: unknown;")
            self.add("  try {")
            self.add("    result = JSON.parse(raw);")
            self.add("  } catch {")
            self.add("    result = raw;")
            self.add("  }")
            self.add(ret("result"))
            self.add("}")
        elif mode == "code" and lang == "typescript":
            imports, rest = split_imports(d.get("code") or "export function main(state: State) {\n  return null\n}\n")
            for imp in imports:
                if imp not in self.imports: self.imports.append(imp)
            code = f"{camel(name)}Code"
            self.add(f"// {head}: the node's TypeScript as written on the canvas (its imports are at the top of the")
            self.add("// file). In the studio it runs in a sandbox without network access; here it runs in this process.")
            self.add(f"const {code} = (() => {{")
            for ln in rest: self.add(f"  {ln}" if ln.strip() else "")
            self.add("  return main;")
            self.add("})();")
            self.add("")
            self.add(f"/** {head}: main(state) gives the result. */")
            self.add(sig)
            self.add(ret(f"await {code}(structuredClone(state))"))
            self.add("}")
        elif mode == "code":
            msg = f"{head} is {lang} code: not implemented in TS export (port it to TypeScript)"
            self.add(f"/** {head}: written in {_doc(lang)} on the canvas, which this TypeScript file cannot run.")
            self.add(" * TODO: port the node's code to TypeScript. */")
            self.add(sig)
            self.add("  void state;")
            self.add(f"  throw new Error({lit(msg)});")
            self.add("}")
        else:
            fn = d.get("function") or ""
            msg = f"{head} calls the Python function {fn}: not implemented in TS export (port it to TypeScript)"
            self.add(f"/** {head}: the server's Python function {_doc(fn)}(state), which this file cannot call.")
            self.add(" * TODO: port the function to TypeScript (the Python export has its source). */")
            self.add(sig)
            self.add("  void state;")
            self.add(f"  throw new Error({lit(msg)});")
            self.add("}")

    def email(self, g: Graph, nid: str, cls: str, head: str, sig: str) -> None:
        d = g.nodes[nid].get("data") or {}; const = g.names[nid].upper()
        self.add(f"const {const}_SUBJECT = {lit(d.get('subject') or '')};")
        self.add(f"const {const}_BODY = {lit(d.get('body') or '')};")
        self.add("")
        self.add(f"/** {head}: builds the message from the state (see sendEmail). */")
        self.add(sig)
        self.add("  const message: Message = {")
        for k in ("to", "cc", "bcc"):
            self.add(f"    {k}: addresses(renderArgs({lit(d[k])}, state))," if d.get(k) else f"    {k}: [],")
        self.add(f"    subject: render({const}_SUBJECT, state).split(/\\s+/).filter(Boolean).join(\" \"),")
        self.add(f"    body: render({const}_BODY, state),")
        self.add("  };")
        out = d.get("output_field")
        if out: self.add(f"  return asUpdate({{ {lit(out)}: await sendEmail(message) }});")
        else:
            self.add("  await sendEmail(message);")
            self.add("  return {};")
        self.add("}")

    def agent(self, g: Graph, nid: str, cls: str, head: str, sig: str) -> None:
        """An Agent node as the studio runs it (DEC-0063), as in the Python file: an entry node, the model node and the
        tool node in a loop, and an end node, with the conversation in its own state field."""
        d = g.nodes[nid].get("data") or {}; name, const, a = g.names[nid], g.names[nid].upper(), g.agents[nid]
        chat, model, tool, end = lit(a["chat"]), a["model"], a["tool"], a["exit"]
        approval = [t.get("name") for t in d.get("tools") or [] if isinstance(t, dict) and t.get("approval")]
        who = one_line(d.get("label") or nid)
        if d.get("system_prompt"): self.add(f"const {const}_SYSTEM = {lit(d['system_prompt'])};")
        self.add(f"const {const}_PROMPT = {lit(d.get('prompt') or '')};")
        self.add("// The tools the model may call: their names, what they do, and the JSON Schema of their arguments.")
        self.add(f"const {const}_TOOLS: ToolSpec[] = {lit(agents.specs(self.tool_spec_data(d)))};")
        self.add(f"const {const}_PARALLEL = {str(d.get('parallel_tool_calls') is not False).lower()};")
        if approval: self.add(f"const {const}_NEEDS_APPROVAL = {lit(approval)};  // these ask a person first (interrupt)")
        for t in d.get("tools") or []:
            if isinstance(t, dict) and t.get("source") == "http":
                self.add(f"const {self.http_key(const, t)}_URL = {lit(t.get('url') or '')};")
                self.add(f"const {self.http_key(const, t)}_BODY = {lit(t.get('body') or '')};")
        self.add(f"const {const}_MAX_ROUNDS = {self.rounds(d)};")
        self.add("")
        self.add(f"/** {head}: starts the conversation in state[{_doc(chat)}].")
        self.add(" *")
        self.add(" * Then the model and the tools take turns, one node each:")
        self.add(f" * - {model}() asks the model, which answers or asks for tool calls;")
        self.add(f" * - {tool}() runs one tool call (route_{model}() and route_{tool}() pick the next node);")
        self.add(f" * - {end}() writes the answer. */")
        self.add(sig)
        self.add("  const messages: ChatMessage[] = [];")
        if d.get("system_prompt"): self.add(f"  messages.push({{ role: \"system\", content: render({const}_SYSTEM, state) }});")
        if d.get("history_field"):
            self.add(f"  const history: unknown = (state as Record<string, unknown>)[{lit(d['history_field'])}];")
            self.add("  for (const m of Array.isArray(history) ? history : []) {  // the earlier turns of a chat")
            self.add("    if (m && (m.role === \"user\" || m.role === \"assistant\") && typeof m.content === \"string\") {")
            self.add("      messages.push({ role: m.role, content: m.content });")
            self.add("    }")
            self.add("  }")
        files = attachments.field_of(d)
        if files: self.add(f"  messages.push({{ role: \"user\", content: render({const}_PROMPT, state), files: fileList((state as Record<string, unknown>)[{lit(files)}]) }});")
        else: self.add(f"  messages.push({{ role: \"user\", content: render({const}_PROMPT, state) }});")
        self.add(f"  return asUpdate({{ {chat}: {{ messages, pending: [], rounds: 0, steps: [], answer: null }} }});")
        self.add("}")
        self.add("")
        self.add(f"/** {_doc(who)}: one model call. After {const}_MAX_ROUNDS rounds the model gets no tools, so it has to answer. */")
        self.add(f"async function {model}(state: {cls}): Promise<Update> {{")
        self.add(f"  const chat: AgentChat = {{ ...state[{chat}]! }};")
        self.add(f"  const last = chat.rounds >= {const}_MAX_ROUNDS;")
        call = "callAgentFiles" if attachments.field_of(d) else "callAgent"
        self.add(f"  const [text, asked] = await {call}(chat.messages, last ? null : {const}_TOOLS, {lit(d.get('model') or 'gpt-4o-mini')});")
        self.add("  const calls: ToolCall[] = last ? [] : asked.map((c, i) => ({ id: String(c.id || `call_${i}`), name: String(c.name || \"\"), args: c.args }));")
        self.add("  if (!last) chat.rounds += 1;")
        self.add("  chat.messages = [...chat.messages, { role: \"assistant\", content: text, ...(calls.length ? { tool_calls: calls } : {}) }];")
        self.add("  chat.pending = calls.slice(0, MAX_CALLS_PER_ROUND);")
        self.add("  for (const c of calls.slice(MAX_CALLS_PER_ROUND)) {  // every call needs an answer, but these never run")
        self.add("    const why = `Refused: at most ${MAX_CALLS_PER_ROUND} tool calls per round`;")
        self.add("    chat.messages = [...chat.messages, { role: \"tool\", tool_call_id: c.id, name: c.name, content: why }];")
        self.add("    chat.steps = [...chat.steps, { tool: c.name, args: c.args, result: why, status: \"refused\", ms: 0 }];")
        self.add("  }")
        self.add("  if (!calls.length) chat.answer = text;")
        self.add(f"  return asUpdate({{ {chat}: chat }});")
        self.add("}")
        self.add("")
        self.add("/** After a model call: \"tool\" while tool calls wait, else \"done\". */")
        self.add(f"function route_{model}(state: {cls}): string {{")
        self.add(f"  return state[{chat}]?.pending.length ? \"tool\" : \"done\";")
        self.add("}")
        self.agent_calls(d, name, const, cls)
        self.add("")
        self.add(f"/** {_doc(who)}: runs the tool calls waiting from the model and gives the results back, in the model's order.")
        self.add(f" * With {const}_PARALLEL on, up to waveCap() calls run together. A failure becomes that call's result;")
        self.add(" * the others still finish.")
        if approval:
            self.add(f" * A tool in {const}_NEEDS_APPROVAL runs on its own and asks first with interrupt(): \"approved\" runs the call;")
            self.add(" * any other answer rejects it, and the model is told why. On resume the node runs again from the top.")
        if (d.get("approval") or {}).get("channel") or d.get("deadline"):
            self.add(" * In Superstep the approval can also go to a channel and have a deadline; that is not part of LangGraph.")
        self.add(" */")
        self.add(f"async function {tool}(state: {cls}): Promise<Update> {{")
        self.add(f"  const chat: AgentChat = {{ ...state[{chat}]! }};")
        self.add("  const pending = [...chat.pending];")
        self.add(f"  let n = Math.min(waveCap({const}_PARALLEL), pending.length);")
        if approval:
            self.add("  for (let i = 0; i < n; i++) {")
            self.add(f"    if ({const}_NEEDS_APPROVAL.includes(pending[i].name)) {{ n = i === 0 ? 1 : i; break; }}")
            self.add("  }")
        self.add("  const batch = pending.slice(0, n);")
        self.add("  chat.pending = pending.slice(n);")
        self.add("  async function one(call: ToolCall): Promise<[ChatMessage, AgentStep]> {")
        self.add(f"    const spec = {const}_TOOLS.find((t) => t.name === call.name);")
        self.add("    const problem = spec ? checkArguments(spec.parameters, call.args) : null;")
        if approval:
            self.add("    let answer: string | null = null;")
            self.add(f"    if (spec && problem === null && {const}_NEEDS_APPROVAL.includes(call.name)) {{")
            self.add(f"      const question = {lit(who + ' wants to call ')} + call.name + \" with these arguments:\\n\"")
            self.add("        + JSON.stringify(call.args, null, 2)")
            self.add("        + \"\\nApprove to run it, or reject it. A text reply rejects it and tells the model why.\";")
            self.add(f"      answer = String(interrupt({{ node: {lit(name)}, question }}));")
            self.add("    }")
        self.add("    const started = performance.now();")
        self.add("    let status: string, result: string;")
        self.add("    if (!spec) {")
        self.add(f"      [status, result] = [\"error\", `Unknown tool ${{call.name}}: use one of ${{{const}_TOOLS.map((t) => t.name).sort().join(\", \")}}`];")
        self.add("    } else if (problem) {")
        self.add("      [status, result] = [\"error\", `Invalid arguments for ${call.name}: ${problem}`];")
        if approval:
            self.add("    } else if (answer !== null && answer.trim().toLowerCase() !== \"approved\") {")
            self.add("      const comment = answer.trim().toLowerCase() === \"rejected\" ? \"\" : answer.trim();")
            self.add("      [status, result] = [\"rejected\", \"Rejected by a reviewer\" + (comment ? `: ${comment}` : \"\")];")
        self.add("    } else {")
        self.add("      try {")
        self.add(f"        [status, result] = [\"ok\", toolText(await call_{name}_tool(call.name, call.args as Record<string, unknown>, state))];")
        self.add("      } catch (error) {  // the model hears about the failure and can try something else")
        self.add("        [status, result] = [\"error\", `The tool failed: ${error instanceof Error ? error.message : error}`];")
        self.add("      }")
        self.add("    }")
        self.add("    const step: AgentStep = { tool: call.name, args: call.args, result: shorten(result, STEP_CHARS), status,")
        self.add("      ms: Math.round((performance.now() - started) * 100) / 100 };")
        if approval: self.add("    if (answer !== null) step.approval = status === \"rejected\" ? \"rejected\" : \"approved\";")
        self.add("    const message: ChatMessage = { role: \"tool\", tool_call_id: call.id, name: call.name, content: shorten(result, RESULT_CHARS) };")
        self.add("    return [message, step];")
        self.add("  }")
        self.add("  const pairs = n <= 1 ? [await one(batch[0])] : await Promise.all(batch.map((call) => one(call)));")
        self.add("  for (const [message, step] of pairs) {")
        self.add("    chat.messages = [...chat.messages, message];")
        self.add("    chat.steps = [...chat.steps, step];")
        self.add("  }")
        self.add(f"  return asUpdate({{ {chat}: chat }});")
        self.add("}")
        self.add("")
        self.add("/** After a batch of tool calls: another batch if any remain, else back to the model. */")
        self.add(f"function route_{tool}(state: {cls}): string {{")
        self.add(f"  return state[{chat}]?.pending.length ? \"tool\" : \"model\";")
        self.add("}")
        self.add("")
        self.add(f"/** {_doc(who)}: the model's answer into the state, and the conversation cleared. */")
        self.add(f"async function {end}(state: {cls}): Promise<Update> {{")
        self.add(f"  const chat = state[{chat}]!;")
        out = [f"{lit(d.get('output_field') or '')}: chat.answer || \"\""]
        if d.get("steps_field"): out.append(f"{lit(d['steps_field'])}: chat.steps")
        self.add(f"  return asUpdate({{ {', '.join(out)}, {chat}: null }});")
        self.add("}")

    def agent_calls(self, d: dict, name: str, const: str, cls: str) -> None:
        """call_<agent>_tool(): what each of the Agent node's tools does."""
        self.add("")
        self.add("/** Runs the tool the model asked for with the model's arguments. */")
        self.add(f"async function call_{name}_tool(name: string, args: Record<string, unknown>, state: {cls}): Promise<unknown> {{")
        for t in d.get("tools") or []:
            if not isinstance(t, dict): continue
            src, tname = t.get("source"), t.get("name") or ""
            self.add(f"  if (name === {lit(tname)}) {{")
            if src == "builtin":
                fn = t.get("function") or ""
                self.uses.add("agent_builtin")
                self.add(f"    // TODO: port the server's Python function {_doc(fn)} to TypeScript (the Python export has its source).")
                self.add(f"    throw new Error({lit(f'{fn} is a Python function of the Superstep server: not implemented in TS export')});")
            elif src == "knowledge":
                self.add(f"    return await retrieve(String(args.query || \"\"), {number(t.get('top_k'), int) or 4});")
            elif src == "mcp":
                self.add(f"    return await callMcpTool({lit(t.get('tool') or '')}, args);")
            elif src == "workflow":
                ref = t.get("workflow_id") or ""; inputs, outputs = agents.field_list(t.get("inputs")), agents.field_list(t.get("outputs"))
                if ref in self.built:
                    child, build = self.built[ref][0], self.built[ref][1]
                    self.add(f"    // the workflow \"{_doc(child.title)}\" as its own graph (in the studio: a child run). Inside this graph's run,")
                    self.add("    // a question for a person in it pauses this graph too.")
                    self.add(f"    const graph = {build}();")
                    self.add(f"    const input = Object.fromEntries(Object.entries(args).filter(([k]) => {lit(inputs)}.includes(k)));")
                    self.add("    const final = (await graph.invoke(input as Parameters<typeof graph.invoke>[0])) as Record<string, unknown>;")
                    self.add(f"    return Object.fromEntries({lit(outputs)}.map((k) => [k, final[k]]));")
                else:
                    self.add(f"    // TODO: the workflow {lit(ref)} was not found (deleted, or not shared with you).")
                    self.add("    return null;")
            elif src == "http":
                method, url, body = (t.get("method") or "GET").upper(), t.get("url") or "", t.get("body") or ""
                key = self.http_key(const, t)
                query = method == "GET" and "args" not in {r.field for r in refs(url) + refs(body)}
                self.add("    const values = { ...state, args };  // the templates read the arguments as {{state.args.<name>}}")
                self.add(f"    {'let' if query else 'const'} url = render({key}_URL, values);")
                if query:
                    self.add("    // the URL does not use the arguments: they go in the query string")
                    self.add("    const query = new URLSearchParams(Object.entries(args).map(([k, v]) => [k, toolText(v)])).toString();")
                    self.add("    if (query) url += (url.includes(\"?\") ? \"&\" : \"?\") + query;")
                send = "undefined"
                if not body and method in ("POST", "PUT", "PATCH"): send = "JSON.stringify(args)"  # no body template: the arguments
                elif method != "GET":
                    self.add(f"    const body = render({key}_BODY, values);")
                    send = "body || undefined"
                self.add("    const response = await fetch(url, {")
                self.add(f"      method: {lit(method)}, body: {send},")
                self.add("      headers: { \"Content-Type\": \"application/json\" }, redirect: \"manual\", signal: AbortSignal.timeout(30_000),")
                self.add("    });")
                self.add("    const raw = await response.text();")
                self.add("    try {")
                self.add("      return JSON.parse(raw);")
                self.add("    } catch {")
                self.add("      return raw;")
                self.add("    }")
            else:
                self.add(f"    throw new Error({lit(f'unknown tool source {src!r}')});")
            self.add("  }")
        self.add("  throw new Error(`unknown tool ${name}`);")
        self.add("}")

    def build(self, g: Graph, cls: str, build: str, is_main: bool) -> None:
        name = lambda i: "END" if g.nodes[i]["type"] == "end" else lit(g.names[i])  # noqa: E731
        leave = lambda i: lit(g.agents[i]["exit"]) if i in g.agents else lit(g.names[i])  # an Agent node's edges leave from its end node  # noqa: E731
        cache = any(number((n.get("data") or {}).get("cache_ttl"), int) is not None for n in g.nodes.values())
        self.add("")
        if is_main:
            self.add("/** The graph: nodes, then edges. compile() checks it and returns a runnable graph. */")
            self.add("export function buildGraph(checkpointer?: MemorySaver) {")
        else:
            self.add(f"/** The subgraph \"{_doc(g.title)}\". It has no checkpointer of its own: it uses the parent's. */")
            self.add(f"function {build}() {{")
        reach = self.reachable(g)
        self.add(f"  return new StateGraph({cls})")
        for nid in g.order():
            if nid not in g.names: continue
            if nid not in reach:
                self.add(f"    // {g.names[nid]}() is not connected to Start; LangGraph.js rejects unreachable nodes, so it is left out.")
                if is_main: self.span(nid, len(self.lines))
                continue
            n = g.nodes[nid]; d = n.get("data") or {}; s = len(self.lines) + 1
            fn = g.names[nid]
            if n["type"] == "subgraph":
                ref = g.refs.get(nid) or ""
                fn = f"{self.built[ref][1]}()" if ref in self.built else f"new StateGraph({cls}).compile() /* TODO: the subgraph was not found */"
            opts = []
            retry = d.get("retry") if isinstance(d.get("retry"), dict) else {}
            if (attempts := number(retry.get("max_attempts"), int)) is not None:
                wait = number(retry.get("initial_interval"))
                ms = round((0.5 if wait is None else wait) * 1000)
                opts.append(f"retryPolicy: {{ maxAttempts: {attempts}, initialInterval: {ms}, backoffFactor: 1, jitter: false }}")
            if (ttl := number(d.get("cache_ttl"), int)) is not None: opts.append(f"cachePolicy: {{ ttl: {ttl} }}")
            if (timeout := number(d.get("timeout"))) is not None: opts.append(f"timeout: {round(timeout * 1000)}")
            if self.inputs(g, nid): opts.append(f"input: {camel(g.names[nid])}Input")
            self.add(f"    .addNode({lit(g.names[nid])}, {fn}{', { ' + ', '.join(opts) + ' }' if opts else ''})")
            if n["type"] == "agent":
                for step in ("model", "tool", "exit"): self.add(f"    .addNode({lit(g.agents[nid][step])}, {g.agents[nid][step]})")
            if is_main: self.span(nid, s)
        joins = [i for i in g.order() if g.nodes[i]["type"] == "join" and i in reach]
        first_edge = True
        for nid in g.order():
            n = g.nodes[nid]
            if n["type"] in ("end", "note") or nid not in reach: continue
            out = g.out(nid)
            src = "START" if n["type"] == "start" else leave(nid)
            s = len(self.lines) + 1
            if n["type"] == "agent":
                a = {k: lit(v) for k, v in g.agents[nid].items()}
                self.add("    // The Agent node's loop: the model, then each tool call it asks for, then back to the model.")
                self.add(f"    .addEdge({lit(g.names[nid])}, {a['model']})")
                self.add(f"    .addConditionalEdges({a['model']}, route_{g.agents[nid]['model']}, {{ tool: {a['tool']}, done: {a['exit']} }})")
                self.add(f"    .addConditionalEdges({a['tool']}, route_{g.agents[nid]['tool']}, {{ tool: {a['tool']}, model: {a['model']} }})")
            if n["type"] in ("condition", "foreach") and out:
                if first_edge and n["type"] == "condition":
                    self.add("    // A conditional edge: the router returns a label, and the map says which node it leads to.")
                    first_edge = False
                mapping = ", ".join(f"{lit(e.get('label'))}: {name(e['target'])}" for e in out)
                self.add(f"    .addConditionalEdges({src}, route_{g.names[nid]}, {{ {mapping} }})")
            else:
                targets = [e["target"] for e in out if g.nodes[e["target"]]["type"] != "join"]
                if len(targets) > 1:
                    self.add("    // Several edges from one node: the targets run in parallel, in the same step.")
                for tgt in targets: self.add(f"    .addEdge({src}, {name(tgt)})")
            if is_main:
                self.span(nid, s)
                for e in out:
                    if g.nodes[e["target"]]["type"] == "end": self.span(e["target"], len(self.lines))
        for j in joins:
            srcs = [("START" if g.nodes[e["source"]]["type"] == "start" else leave(e["source"]))
                    for e in g.edges if e["target"] == j and e["source"] in reach]
            s = len(self.lines) + 1
            self.add(f"    // Fan-in: {g.names[j]} waits for all of {', '.join(x.strip(chr(34)) for x in srcs)}.")
            self.add(f"    .addEdge([{', '.join(srcs)}], {lit(g.names[j])})")
            if is_main: self.span(j, s)
        if is_main:
            self.add("    // The checkpointer saves the state after every step, so a run paused by interrupt() can resume.")
            self.add(f"    .compile({{ checkpointer{', cache: new InMemoryCache()' if cache else ''} }});")
        else:
            self.add(f"    .compile({'{ cache: new InMemoryCache() }' if cache else ''});")
        self.add("}")

    def reachable(self, g: Graph) -> set:
        """Node ids reachable from Start along the edges (LangGraph.js's compile() refuses the others)."""
        seen: set = set()
        queue = [i for i, n in g.nodes.items() if n["type"] == "start"]
        while queue:
            i = queue.pop()
            if i in seen: continue
            seen.add(i); queue += [e["target"] for e in g.edges if e["source"] == i]
        return seen

    def run(self, main: Graph) -> None:
        inp, answers, budget = self.example_run(main)
        has_human = "human" in self.uses
        self.add("")
        self.add(f"// {'=' * (WIDTH - 3)}")
        self.add("// Run it")
        self.add(f"// {'=' * (WIDTH - 3)}")
        self.add("")
        self.add(f"const EXAMPLE_INPUT = {lit(inp)} as Update;")
        if has_human:
            self.add("// Answers for the Human nodes, in order. When a node has none left, main() asks on the terminal.")
            self.add(f"const EXAMPLE_ANSWERS: Record<string, string[]> = {lit(answers)};")
        self.add("")
        self.add("async function main(): Promise<void> {")
        self.add("  const graph = buildGraph(new MemorySaver());")
        cfg = '{ configurable: { thread_id: "example" }' + (f", recursionLimit: {RECURSION + budget}" if budget else "") + " }"
        self.add("  // thread_id names this run in the checkpointer" + ("; For each loops need more steps than the default 25." if budget else "."))
        self.add(f"  const config = {cfg};")
        self.add("  const print = (node: string, delta: unknown) => console.log(`[${node}] ${JSON.stringify(delta)}`);")
        if has_human:
            self.add("  const answers = Object.fromEntries(Object.entries(EXAMPLE_ANSWERS).map(([k, v]) => [k, [...v]]));")
            self.add("  type Ask = { node: string; question: string };")
            self.add("  const answerFor = (request: Ask): string => {")
            self.add("    const value = (answers[request.node]?.shift() ?? globalThis.prompt?.(`${request.question}\\n>`)) || \"(no answer)\";")
            self.add("    console.log(`>> ${request.node}: ${value}`);")
            self.add("    return value;")
            self.add("  };")
            self.add("")
            self.add("  type Input = Parameters<typeof graph.stream>[0];")
            self.add("  const resume = (value: unknown) => new Command({ resume: value }) as unknown as Input;")
            self.add("  let payload: Input = EXAMPLE_INPUT;")
            self.add("  while (true) {")
            self.add("    const waiting: { id: string; value: Ask }[] = [];")
            self.add("    // streamMode \"updates\": what each node returned, step by step (subgraphs: inside subgraphs too).")
            self.add("    for await (const [, update] of await graph.stream(payload, { ...config, streamMode: \"updates\", subgraphs: true })) {")
            self.add("      for (const [node, delta] of Object.entries(update as Record<string, unknown>)) {")
            self.add("        if (node !== \"__interrupt__\") print(node, delta);")
            self.add("        else for (const i of delta as { id: string; value: Ask }[]) if (!waiting.some((w) => w.id === i.id)) waiting.push(i);")
            self.add("      }")
            self.add("    }")
            self.add("    if (!waiting.length) break;")
            self.add("    payload = waiting.length === 1")
            self.add("      ? resume(answerFor(waiting[0].value))")
            self.add("      // several Human nodes wait at once (parallel branches): answer each by its interrupt id")
            self.add("      : resume(Object.fromEntries(waiting.map((i) => [i.id, answerFor(i.value)])));")
            self.add("  }")
        else:
            self.add("  // streamMode \"updates\": what each node returned, step by step (subgraphs: inside subgraphs too).")
            self.add("  for await (const [, update] of await graph.stream(EXAMPLE_INPUT, { ...config, streamMode: \"updates\", subgraphs: true })) {")
            self.add("    for (const [node, delta] of Object.entries(update as Record<string, unknown>)) print(node, delta);")
            self.add("  }")
        self.add("  console.log(\"Final state:\", JSON.stringify((await graph.getState(config)).values, null, 2));")
        self.add("}")
        self.add("")
        self.add("if ((import.meta as { main?: boolean }).main !== false) await main();")


def to_typescript(wf: dict, name: str, version: Optional[int] = None, children: Optional[dict] = None,
                  example: Optional[dict] = None) -> Export:
    """The LangGraph.js TypeScript file for workflow `wf` (same arguments as `python_export.to_python`)."""
    return _Writer(name, version, children or {}, example).write(wf)
