"""Export a workflow as one readable, runnable LangGraph.js TypeScript file.

The TypeScript twin of `python_export`: the state as an `Annotation.Root` with the same reducers, one
function per node, `buildGraph()` with `addNode` / `addEdge` / `addConditionalEdges`, and a `main()` that runs an
example. It imports only `@langchain/langgraph` (and LangChain.js when `LLM_PROVIDER` is set), as `npm:` specifiers,
so `deno run` / `deno check` work as is; for Node, drop the `npm:` prefixes.

The graph is read through `templates.sanitize` (`export_common`), so no credential reaches the file: keys come from
environment variables at run time. TypeScript Code nodes are inlined as written; Python Code nodes and registered
Python tool functions become stubs that throw. Retriever, MCP and Send email nodes call the studio's services through
environment variables, as in the Python file. A node credential is an LLM_CRED_<n> slot. Approval extras and managed
connections are included when a node has them.
An Agent node is its model and tool steps in a loop, as in the Python file; its built-in tools are
Python functions, so they throw too, and the model is told the tool failed.
The output is a pure function of its input: the same graph gives the same bytes.
"""
from __future__ import annotations
import json, re
from typing import Any, List, Optional, Tuple
from . import agents, approval_policy, attachments, dataset_nodes, foreach
from .browser_export import export_binding
from .browser_export_ts import TS_RUNTIME
from .dataset_export import DatasetExport
from .dataset_export_runtime import TS_DATASET
from .dataset_typescript_standalone import typescript_standalone
from .export_common import TITLES, RECURSION, Export, Graph, GraphWriter, camel, number, one_line, slug
from .export_runtime import TS_APPROVAL, TS_MANAGED
from .llm import CLASSIFY
from .templating import VAR_RE, _ONE_FILTER, refs

LANGGRAPH = "npm:@langchain/langgraph@^1.5"
CHECKPOINT = "npm:@langchain/langgraph-checkpoint@^1"
LANGCHAIN = "npm:langchain@^1"
NODEMAILER = "npm:nodemailer@^6"  # Send email nodes with SMTP configured
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
    "datasetCall", "datasetAgent", "datasetOperationId", "setupDatasets", "datasetStandalone", "datasetBackend",
    "datasetCliArgs", "DATASET_BINDINGS",
    "Annotation", "StateGraph", "START", "END", "Command", "interrupt", "MemorySaver", "InMemoryCache", "State", "Update",
    "env", "VAR_RE", "FILTER_RE", "ONE_VAR_RE", "FILTERS", "text", "value", "render", "renderArgs", "LLM_PROVIDER", "callLlmFallback", "failsOver", "offlineService", "httpRequest", "blockedAddress", "concatBytes", "HTTP_RUN_ID",
    "DECISION_MODEL", "mockLlm", "callLlm", "resolveModel", "norm", "escapeRe", "pickBranch", "decide", "retrieve", "callMcpTool", "MCP_PROTOCOL", "managedOperation",
    "reviewApproval", "waitApproval", "notifyApproval", "approvalPost", "managedHttp", "managedBlocked", "ManagedUnknown",
    "sendEmail", "addresses", "EMAIL_RE", "EMAIL_RUN_ID", "nodemailer", "asUpdate", "buildGraph", "EXAMPLE_INPUT", "EXAMPLE_ANSWERS", "main", "graph", "pyJson",
    "browserCall", "bindBrowserUrl", "browserPrepare", "browserInterrupt", "browserDecide", "BROWSER_POLICY",
    "BrowserError", "SessionLost", "UnknownEffect", "sessions",
    "MAX_CALLS_PER_ROUND", "RESULT_CHARS", "STEP_CHARS", "JSON_TYPES", "WORDS", "Schema", "ToolSpec", "ToolCall", "ChatMessage",
    "AgentStep", "AgentChat", "agentTask", "mockAgent", "callAgent", "FileRecord", "isImage", "fileList", "withFiles", "filesNote", "callLlmFiles", "callLlmFilesFallback", "callAgentFiles", "checkArguments", "toolText", "shorten", "Question", "Message",
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
// this file. Without --allow-env, Deno gives nothing, and the defaults apply. (--allow-read and --allow-sys=homedir
// let LangGraph.js locate and read its optional LangSmith config.)
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
//     LLM_PROVIDER=openai OPENAI_API_KEY=sk-... deno run --allow-env --allow-read --allow-sys=homedir --allow-net workflow.ts
const LLM_PROVIDER = env("LLM_PROVIDER");

/** Offline answers: a category for classification prompts, else the last line of the prompt echoed back. */
function mockLlm(prompt: string, model: string): string {
  const p = prompt.toLowerCase();
  if (%(markers)s.some((k) => p.includes(k))) {
    const msg = p.includes("message:") ? p.split("message:").at(-1)! : p;
    if (%(order)s.some((k) => msg.includes(k))) return "order_status";
    if (%(refund)s.some((k) => msg.includes(k))) return "refund";
    return "general";
  }
  const tail = prompt.trim() ? prompt.trim().split(/\r?\n/).at(-1)! : "";
  return `[mock:${model}] Answer: ${[...tail].slice(0, 200).join("")}`;
}

/** [provider, initChatModel extras]. A set LLM_CRED_<n>_PROVIDER wins, even when LLM_PROVIDER is unset. */
function resolveModel(provider: string | undefined, slot?: string): [string | null, Record<string, string>] {
  if (slot) {
    const named = env(`${slot}_PROVIDER`);
    if (named) {
      const key = env(`${slot}_API_KEY`);
      if (!key) throw new Error(`LLM credential ${slot}: set ${slot}_API_KEY`);
      const kwargs: Record<string, string> = { apiKey: key };
      const base = env(`${slot}_BASE_URL`);
      if (base) kwargs.baseUrl = base;
      return [named, kwargs];
    }
  }
  if (!LLM_PROVIDER) return [null, {}];
  return [provider || LLM_PROVIDER, {}];
}

async function callLlm(prompt: string, model: string, provider?: string, slot?: string): Promise<string> {
  const [chosen, kwargs] = resolveModel(provider, slot);
  if (!chosen) return mockLlm(prompt, model);
  const { initChatModel } = await import("%(langchain)s");
  // deno-lint-ignore no-explicit-any
  const reply = await (await initChatModel(model, { modelProvider: chosen, ...kwargs } as any)).invoke(prompt);
  if (typeof reply.content === "string") return reply.content;
  return reply.content.map((b) => ("text" in b && typeof b.text === "string" ? b.text : "")).join("");
}
''' % {"langchain": LANGCHAIN, **{part: json.dumps(words, ensure_ascii=False) for part, words in CLASSIFY.items()}}  # mock words: app/locales


FALLBACK = r'''
// --- Model fallback ------------------------------------------------------------------------------------------
// An LLM node with a fallback model, as in the studio: the primary model first; only when it is unreachable, answers
// badly (HTTP 5xx) or is not found (HTTP 404) the fallback model, once. Other errors (a bad key, a refused request)
// stop the node. The fallback uses LLM_FALLBACK_PROVIDER, or LLM_PROVIDER; its key comes from the environment too.
// Offline (no LLM_PROVIDER and no slot provider) only the primary mock answers, as in a studio dry run.
// A set slot provider is used even when LLM_PROVIDER is unset; an unset slot keeps LLM_PROVIDER.
function failsOver(error: unknown): boolean {
  const e = error as { status?: unknown; statusCode?: unknown; response?: { status?: unknown }; name?: unknown; code?: unknown };
  const status = [e?.status, e?.statusCode, e?.response?.status].find((s) => typeof s === "number") as number | undefined;
  if (status !== undefined) return status === 404 || status >= 500;
  return ["APIConnectionError", "APIConnectionTimeoutError", "TimeoutError", "FetchError"].includes(String(e?.name)) ||
    ["ECONNREFUSED", "ECONNRESET", "ETIMEDOUT", "ENOTFOUND"].includes(String(e?.code));
}

async function callLlmFallback(prompt: string, model: string, fallback: string, slot?: string, fallbackSlot?: string): Promise<string> {
  if (!resolveModel(undefined, slot)[0]) return await callLlm(prompt, model, undefined, slot);
  try {
    return await callLlm(prompt, model, undefined, slot);
  } catch (error) {
    if (!failsOver(error)) throw error;
    console.error(`(model fallback) ${model} failed (${String((error as { name?: unknown })?.name ?? "Error")}); trying ${fallback}`);
  }
  return await callLlm(prompt, fallback, env("LLM_FALLBACK_PROVIDER") || LLM_PROVIDER, fallbackSlot);
}
'''

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
async function callLlmFiles(prompt: string, model: string, files: unknown, provider?: string, slot?: string): Promise<string> {
  const list = fileList(files);
  const [chosen, kwargs] = resolveModel(provider, slot);
  if (!chosen) return mockLlm(prompt, model) + (list.length ? `\n${filesNote(list)}` : "");
  const [text, images] = withFiles(prompt, list);
  const { initChatModel } = await import("%(langchain)s");
  const ask = images.length ? [{ role: "user", content: [{ type: "text", text }, ...images] }] : text;
  // deno-lint-ignore no-explicit-any
  const reply = await (await initChatModel(model, { modelProvider: chosen, ...kwargs } as any)).invoke(ask as any);
  if (typeof reply.content === "string") return reply.content;
  return reply.content.map((b) => ("text" in b && typeof b.text === "string" ? b.text : "")).join("");
}
''' % {"langchain": LANGCHAIN}

FALLBACK_FILES = r'''

/** callLlmFallback() for a message with files: the fallback model gets the same prompt and files, once. */
async function callLlmFilesFallback(prompt: string, model: string, fallback: string, files: unknown, slot?: string, fallbackSlot?: string): Promise<string> {
  if (!resolveModel(undefined, slot)[0]) return await callLlmFiles(prompt, model, files, undefined, slot);
  try {
    return await callLlmFiles(prompt, model, files, undefined, slot);
  } catch (error) {
    if (!failsOver(error)) throw error;
    console.error(`(model fallback) ${model} failed (${String((error as { name?: unknown })?.name ?? "Error")}); trying ${fallback}`);
  }
  return await callLlmFiles(prompt, fallback, files, env("LLM_FALLBACK_PROVIDER") || LLM_PROVIDER, fallbackSlot);
}
'''

AGENT_FILES = r'''

/** callAgent() for a conversation whose user message carries `files`. */
async function callAgentFiles(messages: ChatMessage[], tools: ToolSpec[] | null, model: string, slot?: string): Promise<[string, ToolCall[]]> {
  const files = messages.filter((m) => m.role === "user").flatMap((m) => fileList(m.files));
  if (!resolveModel(undefined, slot)[0]) {
    const [text, calls] = mockAgent(messages, tools, model);
    return [text && files.length ? `${text}\n${filesNote(files)}` : text, calls];
  }
  return callAgent(messages.map((m) => {
    if (!m.files) return m;
    const [content, images] = withFiles(m.content, m.files);
    return { role: "user", content, images };
  }), tools, model, slot);
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
async function decide(text: string, question: Question, slot?: string): Promise<unknown> {
  const { type: kind, instructions } = question;
  const offline = !resolveModel(undefined, slot)[0];
  if (kind === "choice") {
    const labels = question.options ?? [];
    if (offline) {
      const low = text.toLowerCase();
      return labels.find((x) => new RegExp(`(?<![\\p{L}\\p{N}_])${escapeRe(x.toLowerCase())}(?![\\p{L}\\p{N}_])`, "u").test(low)) ?? labels[0];
    }
    const reply = await callLlm(`${instructions}\n\nText:\n${text}\n\nAnswer with one of: ${labels.join(", ")}`, DECISION_MODEL, undefined, slot);
    return pickBranch(reply.trim(), labels) ?? labels[0];
  }
  if (offline) return kind === "score" ? 0.0 : 0.5;
  const reply = kind === "score"
    ? await callLlm(`${instructions}\n\nText:\n${text}\n\nLevels:\n${(question.levels ?? []).map((l, i) => `${i}: ${l}`).join("\n")}\n\nAnswer with the level number.`, DECISION_MODEL, undefined, slot)
    : await callLlm(`${instructions}\n\nText:\n${text}\n\nHow likely is it true, from 0 to 1? Answer with a number.`, DECISION_MODEL, undefined, slot);
  const found = /\d+(?:\.\d+)?/.exec(reply);
  return found ? parseFloat(found[0]) : 0.0;
}
'''

HANDOFF = r'''
// --- Hand-offs -----------------------------------------------------------------------------------------------
// An Agent node with hand-off targets offers the model one transfer_to_<agent> tool per target. Calling one ends the
// agent: its hand-off node records who takes over, and a conditional edge goes to that agent, which continues the
// conversation. MAX_HANDOFFS bounds a run; past it the tools are gone and the agent answers itself.
const HANDOFF_NOTE = "The conversation was handed off to you by {source}.{reason} Continue it and answer the person yourself.";
const NOT_RUN = "Not run: the conversation was handed off";
const NO_MORE = "You cannot hand the conversation off again in this run: answer the person yourself.";
/** A hand-off on its way to the next agent. */
type Handoff = { from: string; to: string; reason: string; messages: ChatMessage[] };

/** What the next agent sees: the person's messages and the agents' replies, without tool calls and results. */
function carried(messages: ChatMessage[]): ChatMessage[] {
  return messages.filter(m => m.role === "user" || (m.role === "assistant" && !m.tool_calls?.length && m.content))
    .map(m => ({ role: m.role, content: m.content }));
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

type Schema = { type?: string; properties?: Record<string, unknown>; required?: string[]; additionalProperties?: boolean };
type ToolSpec = { name: string; description: string; parameters: Schema };
type ToolCall = { id: string; name: string; args: unknown };
type ChatMessage = { role: string; content: string; tool_calls?: ToolCall[]; tool_call_id?: string; name?: string; files?: unknown; images?: unknown[] };
type AgentStep = { tool: string; args: unknown; result: string; status: string; ms: number; approval?: string };
/** An Agent node's conversation, in its own state field while the loop runs. */
type AgentChat = { messages: ChatMessage[]; pending: ToolCall[]; rounds: number; steps: AgentStep[]; answer: string | null
  handoff?: { to: string; reason: string } | null; no_more?: boolean };

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
      type Schema = { type?: unknown; enum?: unknown[]; properties?: Record<string, Schema> };
      const text = (v: Schema) => (v.type ?? "string") === "string" || (Array.isArray(v.type) && v.type.includes("string"));
      // the task text, the first enum value, or an object of text properties
      const value = (v: Schema): unknown => {
        if (v.enum?.length) return v.enum[0];
        if (text(v)) return task;
        if (v.type === "object" && v.properties) {
          return Object.fromEntries(Object.entries(v.properties).filter(([, p]) => text(p ?? {})).map(([k, p]) => [k, value(p ?? {})]));
        }
        return empty[String(v.type)] ?? null;
      };
      const props = (best.parameters?.properties ?? {}) as Record<string, Schema>;
      const args: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(props)) {
        const schema = v !== null && typeof v === "object" ? v : {};
        if (required.includes(k) || (schema.type ?? "string") === "string") args[k] = value(schema);
      }
      if ((args.operation === "insert_row" || args.operation === "upsert_row") && props.values) {
        args.values = value(props.values);  // a Dataset write tool: the mock writes the task text
      }
      return { id: `mock_call_${i + 1}`, name: best.name, args };
    });
    return ["", calls];
  }
  const said = results.length ? results.at(-1)!.content || "" : task.trim() ? task.trim().split(/\r?\n/).at(-1)! : "";
  return [`[mock:${model}] Answer: ${[...said].slice(0, 200).join("")}`, []];
}

/** One model call: [text, tool calls]. With tools null the model has to answer. */
async function callAgent(messages: ChatMessage[], tools: ToolSpec[] | null, model: string, slot?: string): Promise<[string, ToolCall[]]> {
  const [chosen, kwargs] = resolveModel(undefined, slot);
  if (!chosen) return mockAgent(messages, tools, model);
  const { initChatModel } = await import("%(langchain)s");
  // deno-lint-ignore no-explicit-any
  const llm = await initChatModel(model, { modelProvider: chosen, ...kwargs } as any);
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


HTTP = r'''
// --- HTTP ------------------------------------------------------------------------------------------------------
// HTTP Tool requests keep the studio's safeguards: http(s) only; private, loopback, link-local, reserved, multicast
// and unspecified addresses are refused unless STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1; redirects are never followed;
// user:password@ in the URL is sent as Basic auth, not in the URL. Each request carries an Idempotency-Key from
// SUPERSTEP_RUN_ID (random per process when unset), the node and the request, so a retried request repeats its key.
// As in the studio, the host is resolved once, every address is checked, and the connection goes to that checked
// address (no second lookup a DNS rebind could change); the Host header, TLS SNI and certificate check keep the name.
// Node's http(s) modules make the request (Deno supports them too); Deno needs --allow-net.
const HTTP_RUN_ID = env("SUPERSTEP_RUN_ID") || crypto.randomUUID();

async function httpRequest(node: string, method: string, url: string, body?: string): Promise<unknown> {
  let target: URL;
  try {
    target = new URL(url);
  } catch {
    throw new Error(`${node}: only http(s) URLs can be called, not ${JSON.stringify(url.slice(0, 100))}`);
  }
  if (!["http:", "https:"].includes(target.protocol) || !target.hostname) {
    throw new Error(`${node}: only http(s) URLs can be called, not ${JSON.stringify(url.slice(0, 100))}`);
  }
  const host = target.hostname.replace(/^\[|\]$/g, "");
  const dns = (await import("node:dns")).default;
  const found = await dns.promises.lookup(host, { all: true, verbatim: true }).catch(() => []);
  const addresses = found.map((a) => ({ address: a.address, family: a.family }));
  if (!addresses.length) throw new Error(`${node}: cannot resolve ${JSON.stringify(host)}`);
  if (addresses.some((a) => blockedAddress(a.address)) && env("STUDIO_HTTP_TOOL_ALLOW_PRIVATE") !== "1") {
    throw new Error(`${node}: ${host} is a private address; set STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1 to allow it`);
  }
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (target.username) {
    headers.Authorization = "Basic " + btoa(`${decodeURIComponent(target.username)}:${decodeURIComponent(target.password)}`);
    target.username = ""; target.password = "";
  }
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify([HTTP_RUN_ID, node, method, target.href, body ?? null])));
  headers["Idempotency-Key"] = [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
  const pin = addresses[0];  // the checked address: the request never resolves the name again
  const https = target.protocol === "https:";
  type Res = { on(event: string, listener: (chunk: Uint8Array) => void): void };
  type Req = { on(event: string, listener: (error: Error) => void): void; destroy(error: Error): void; end(data?: Uint8Array): void };
  const lib = (https ? (await import("node:https")).default : (await import("node:http")).default) as unknown as
    { request(options: Record<string, unknown>, onResponse: (res: Res) => void): Req };
  const data = body ? new TextEncoder().encode(body) : undefined;
  if (data) headers["Content-Length"] = String(data.byteLength);
  const raw = await new Promise<string>((resolve, reject) => {
    const req = lib.request({
      protocol: target.protocol, hostname: host, port: target.port || (https ? 443 : 80), path: target.pathname + target.search,
      method, headers, agent: false, timeout: 30_000, ...(https ? { servername: host } : {}),
      lookup: (_name: string, options: { all?: boolean }, done: (...a: unknown[]) => void) =>
        options?.all ? done(null, [pin]) : done(null, pin.address, pin.family),
    }, (res) => {
      const chunks: Uint8Array[] = [];
      res.on("data", (c: Uint8Array) => chunks.push(c));
      res.on("end", () => resolve(new TextDecoder().decode(concatBytes(chunks))));
      res.on("error", reject as unknown as (chunk: Uint8Array) => void);
    });
    req.on("timeout", () => req.destroy(new Error(`${node}: the request timed out after 30 s`)));
    req.on("error", reject);
    req.end(data);
  });
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function concatBytes(chunks: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(chunks.reduce((n, c) => n + c.byteLength, 0));
  let at = 0;
  for (const c of chunks) { out.set(c, at); at += c.byteLength; }
  return out;
}
'''

NET = r'''
/** A private, loopback, link-local, reserved, multicast or unspecified address (as the studio's core/net.blocked). */
function blockedAddress(ip: string): boolean {
  const v4 = ip.startsWith("::ffff:") && ip.includes(".") ? ip.slice(7) : ip;
  if (/^\d+\.\d+\.\d+\.\d+$/.test(v4)) {
    const [a, b, c] = v4.split(".").map(Number);
    return a === 0 || a === 10 || a === 127 || a >= 224 || (a === 100 && b >= 64 && b <= 127) || (a === 169 && b === 254) ||
      (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 192 && b === 0 && (c === 0 || c === 2)) ||
      (a === 198 && (b === 18 || b === 19)) || (a === 198 && b === 51 && c === 100) || (a === 203 && b === 0 && c === 113);
  }
  const x = ip.toLowerCase();
  return x === "::" || x === "::1" || /^f[cd]/.test(x) || /^fe[89ab]/.test(x) || x.startsWith("ff") || x.startsWith("2001:db8") ||
    x.startsWith("::ffff:") || x.startsWith("64:ff9b:") || x.startsWith("100::");
}
'''

OFFLINE_SERVICE = r'''
/** Offline example mode (LLM_PROVIDER unset): like the studio's mock run, a Studio service gives an empty result and
 * says so on stderr. With LLM_PROVIDER set the run is real, so an unimplemented service stops it instead of returning
 * a made-up value. */
function offlineService(kind: string, name: string): void {
  if (env("LLM_PROVIDER")) {
    throw new Error(`${kind} ${JSON.stringify(name)} uses a Superstep service that is not exported: implement it ` +
      "(see the TODO above) before running with LLM_PROVIDER set");
  }
  console.error(`(offline mock) ${kind} ${JSON.stringify(name)} is not implemented: empty result`);
}
'''

STUBS = {
    "retrieve": r'''
/** Retriever nodes (and Agent knowledge tools) search a Superstep knowledge base. This file asks your Superstep
 * server, so the chunks and scores are the studio's own: POST <SUPERSTEP_URL>/api/knowledge-bases/<id>/search.
 * Configure with environment variables (never written here): SUPERSTEP_URL, SUPERSTEP_TOKEN (a Bearer token of a
 * user who can read the knowledge base) and <PREFIX>_ID, the knowledge base id, for each prefix listed above.
 * Not configured: an empty list in offline mock mode (LLM_PROVIDER unset), an error when LLM_PROVIDER is set. */
async function retrieve(prefix: string, query: string, topK: number): Promise<unknown[]> {
  const base = env("SUPERSTEP_URL"), token = env("SUPERSTEP_TOKEN"), kid = env(`${prefix}_ID`);
  const missing = ([["SUPERSTEP_URL", base], ["SUPERSTEP_TOKEN", token], [`${prefix}_ID`, kid]] as const).filter(([, v]) => !v).map(([n]) => n);
  if (missing.length) {
    if (env("LLM_PROVIDER")) throw new Error(`Knowledge base search ${prefix}: set ${missing.join(", ")} to search it`);
    console.error(`(offline mock) Knowledge base search ${JSON.stringify(query.slice(0, 60))}: ${missing.join(", ")} not set: empty result`);
    return [];
  }
  let status = 0;
  let body: { success?: boolean; data?: unknown; error?: { code?: unknown; message?: unknown } | null };
  try {
    const r = await fetch(`${base!.replace(/\/+$/, "")}/api/knowledge-bases/${kid}/search`, { method: "POST", redirect: "manual",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ query, top_k: topK }),
      signal: AbortSignal.timeout(30_000) });
    status = r.status;
    body = await r.json();
  } catch (error) {
    throw new Error(`Knowledge base search ${prefix}: no answer from ${base} (${String((error as { name?: unknown })?.name ?? "Error")})`);
  }
  if (!body?.success) {
    const e = body?.error ?? {};
    throw new Error(`Knowledge base search ${prefix}: ${String(e.code ?? `HTTP ${status}`)} ${String(e.message ?? "").slice(0, 200)}`.trimEnd());
  }
  return Array.isArray(body.data) ? body.data : [];
}
''',
    "managed_operation": r'''
/** Placeholder for a Superstep managed connection. No external action is performed.
 * TODO: implement this tool with your own credentials, operation tracking,
 * idempotency and reconciliation before running the exported workflow.
 * Studio connection settings and secrets are deliberately not exported. */
async function managedOperation(tool: string, args: unknown): Promise<never> {
  void tool, args;
  throw new Error("Managed connection placeholder: implement the tool before running it");
}
''',
    "call_mcp_tool": r'''
/** MCP nodes call a tool on an MCP server, as Superstep does: one short Streamable HTTP session (initialize,
 * tools/call). Each server is configured only by environment variables (never by this file), with its prefix
 * MCP_SERVER_<n> (see MCP servers above): <PREFIX>_URL, the server's Streamable HTTP address, and optionally <PREFIX>_HEADERS, a JSON object of headers such
 * as {"Authorization": "Bearer ..."}. The URL is your own configuration: it is called as given, without redirects.
 * Not configured: null in offline mock mode (LLM_PROVIDER unset), an error when LLM_PROVIDER is set. */
async function callMcpTool(prefix: string, tool: string, args: unknown): Promise<unknown> {
  const url = env(`${prefix}_URL`);
  if (!url) {
    if (env("LLM_PROVIDER")) throw new Error(`MCP tool ${JSON.stringify(tool)}: set ${prefix}_URL to the server's Streamable HTTP address to call it`);
    console.error(`(offline mock) MCP tool ${JSON.stringify(tool)}: ${prefix}_URL is not set: empty result`);
    return null;
  }
  let extra: Record<string, string>;
  try {
    const parsed = JSON.parse(env(`${prefix}_HEADERS`) || "{}");
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error();
    extra = Object.fromEntries(Object.entries(parsed).map(([k, v]) => [k, String(v)]));
  } catch {
    throw new Error(`${prefix}_HEADERS must be a JSON object`);
  }
  let session: string | null = null;
  const rpc = async (message: { id?: number; method: string; [k: string]: unknown }): Promise<Record<string, unknown> | null> => {
    let r: Response;
    try {
      r = await fetch(url, { method: "POST", body: JSON.stringify(message), redirect: "manual", signal: AbortSignal.timeout(30_000),
        headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream", "MCP-Protocol-Version": MCP_PROTOCOL,
          ...extra, ...(session ? { "Mcp-Session-Id": session } : {}) } });
    } catch (error) {
      throw new Error(`MCP server ${prefix}: connection failed (${String((error as { name?: unknown })?.name ?? "Error")})`);
    }
    const raw = await r.text();
    if (r.status >= 300) throw new Error(`MCP server ${prefix}: HTTP ${r.status}`);
    session = r.headers.get("mcp-session-id") ?? session;
    if (message.id === undefined || r.status === 202) return null;
    const found: unknown[] = (r.headers.get("content-type") ?? "").includes("text/event-stream")
      ? raw.split(/\r?\n/).filter((l) => l.startsWith("data:") && l.slice(5).trim()).map((l) => JSON.parse(l.slice(5)))
      : raw ? [JSON.parse(raw)] : [];
    const reply = found.find((m) => m !== null && typeof m === "object" && (m as { id?: unknown }).id === message.id) as
      { result?: Record<string, unknown>; error?: { message?: unknown } } | undefined;
    if (!reply) throw new Error(`MCP server ${prefix}: no response to ${message.method}`);
    if (reply.error !== undefined) throw new Error(`MCP server ${prefix}: ${message.method}: ${String(reply.error?.message ?? JSON.stringify(reply.error)).slice(0, 300)}`);
    return reply.result ?? {};
  };
  let result: Record<string, unknown>;
  try {
    await rpc({ jsonrpc: "2.0", id: 1, method: "initialize",
      params: { protocolVersion: MCP_PROTOCOL, capabilities: {}, clientInfo: { name: "superstep-export", version: "1.0" } } });
    await rpc({ jsonrpc: "2.0", method: "notifications/initialized" });
    result = (await rpc({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: tool, arguments: args } })) ?? {};
  } finally {
    if (session) {
      await fetch(url, { method: "DELETE", redirect: "manual", headers: { ...extra, "Mcp-Session-Id": session } })
        .then((r) => r.body?.cancel()).catch(() => {});
    }
  }
  const content = Array.isArray(result.content) ? result.content as { type?: unknown; text?: unknown }[] : [];
  const texts = content.filter((c) => c?.type === "text").map((c) => String(c.text ?? ""));
  if (result.isError) throw new Error(`MCP tool ${JSON.stringify(tool)} failed: ${(texts.join("\n") || "the tool reported an error").slice(0, 500)}`);
  if (result.structuredContent !== undefined && result.structuredContent !== null) return result.structuredContent;
  if (texts.length && texts.length === content.length) {
    try {
      return JSON.parse(texts.join("\n"));
    } catch {
      return texts.join("\n");
    }
  }
  return content;
}
''',
    "send_email": r'''
function addresses(value: unknown): string[] {
  const items = Array.isArray(value) ? value : [value];
  return items.filter((x) => x !== null && x !== undefined && x !== "")
    .flatMap((x) => String(x).split(/[,;\n]/)).map((p) => p.trim()).filter(Boolean);
}

type Message = { to: string[]; cc: string[]; bcc: string[]; subject: string; body: string; node: string; sends: boolean };
const EMAIL_RE = /^[^@\s<>,;"]+@[^@\s<>,;"]+\.[^@\s<>,;"]+$/;
const EMAIL_RUN_ID = env("SUPERSTEP_RUN_ID") || crypto.randomUUID();

/** Send email nodes, as in the studio: a node with an SMTP credential in Superstep sends; one without makes a dry run
 * (prints the message, returns what would have been sent). Sending uses nodemailer and environment variables only
 * (never this file): SMTP_HOST, SMTP_FROM, and optionally SMTP_PORT (587, or 465 with ssl), SMTP_SECURITY (starttls,
 * the default and required; ssl; or none), SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_NAME. As in the studio the host is
 * resolved once, private addresses are refused unless STUDIO_SMTP_ALLOW_PRIVATE=1, and the connection goes to the
 * checked address (TLS still checks the name). Not configured: a dry run offline (LLM_PROVIDER unset), else an error. */
async function sendEmail(message: Message): Promise<Record<string, unknown>> {
  const rcpt = [...new Set([...message.to, ...message.cc, ...message.bcc])];
  if (!rcpt.length) throw new Error(`Send email ${message.node}: no recipient`);
  const bad = rcpt.filter((a) => !EMAIL_RE.test(a));
  if (bad.length) throw new Error(`Send email ${message.node}: ${JSON.stringify(bad[0].slice(0, 100))} is not an e-mail address`);
  const head = { to: message.to, cc: message.cc, bcc: message.bcc, subject: message.subject.slice(0, 998) };
  const host = env("SMTP_HOST"), sender = env("SMTP_FROM");
  if (!message.sends || !host || !sender) {
    const missing = ([["SMTP_HOST", host], ["SMTP_FROM", sender]] as const).filter(([, v]) => !v).map(([n]) => n).join(", ");
    if (message.sends && env("LLM_PROVIDER")) throw new Error(`Send email ${message.node}: set ${missing} to send it`);
    const why = message.sends ? `${missing} not set` : "no SMTP credential on this node in the studio";
    console.error(`(offline mock) Send email ${JSON.stringify(message.subject.slice(0, 60))}: dry run, ${why}`);
    console.log(`(e-mail not sent) to ${message.to.join(", ")}: ${message.subject}`);
    return { sent: false, dry_run: true, ...head, message_id: null, preview: message.body.slice(0, 2000) };
  }
  const security = (env("SMTP_SECURITY") || "starttls").toLowerCase();
  if (!["starttls", "ssl", "none"].includes(security)) throw new Error("SMTP_SECURITY must be starttls, ssl or none");
  const port = Number(env("SMTP_PORT") || (security === "ssl" ? 465 : 587));
  const dns = (await import("node:dns")).default;
  const found = await dns.promises.lookup(host, { all: true, verbatim: true }).catch(() => []);
  if (!found.length) throw new Error(`Send email ${message.node}: cannot resolve ${host}`);
  if (found.some((a) => blockedAddress(a.address)) && env("STUDIO_SMTP_ALLOW_PRIVATE") !== "1") {
    throw new Error(`Send email ${message.node}: ${host} is a private address; set STUDIO_SMTP_ALLOW_PRIVATE=1 to allow it`);
  }
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify([EMAIL_RUN_ID, message.node, rcpt, message.subject, message.body])));
  const key = [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
  const mid = `<${key}@${sender.split("@").pop()}>`;  // the same run and message keep the same Message-ID
  // deno-lint-ignore no-explicit-any
  const nodemailer: any = (await import("%(nodemailer)s")).default;
  const transport = nodemailer.createTransport({
    host: found[0].address, port, secure: security === "ssl", requireTLS: security === "starttls", ignoreTLS: security === "none",
    tls: { servername: host }, connectionTimeout: 20_000, greetingTimeout: 20_000, socketTimeout: 20_000,
    ...(env("SMTP_USERNAME") ? { auth: { user: env("SMTP_USERNAME"), pass: env("SMTP_PASSWORD") || "" } } : {}),
  });
  const name = env("SMTP_FROM_NAME");
  let info: { rejected?: unknown[] };
  try {
    info = await transport.sendMail({ from: name ? { name, address: sender } : sender, to: message.to, cc: message.cc, bcc: message.bcc,
      subject: message.subject.split(/\s+/).filter(Boolean).join(" ").slice(0, 998), text: message.body, messageId: mid,
      envelope: { from: sender, to: rcpt } });
  } catch (error) {
    throw new Error(`Send email ${message.node}: ${String((error as Error)?.message ?? error).slice(0, 200)}`);
  } finally {
    transport.close();
  }
  return { sent: true, dry_run: false, ...head, message_id: mid, refused: (info.rejected ?? []).map(String).sort() };
}
''' % {"nodemailer": NODEMAILER},
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
                      f"{slug(self.title, 'workflow')}.ts",
                      self.datasets.manifest() if self.datasets.bindings else None)

    def state_name(self, base: str) -> str: return f"{camel(base)}State"

    def header(self) -> List[str]:
        body = "\n".join(self.lines)
        uses = lambda n: re.search(rf"(?<![\w.\"]){n}\b", body) is not None  # noqa: E731
        v = f" (version {self.version})" if self.version is not None else ""
        file = f"{slug(self.title, 'workflow')}.ts"
        net = " --allow-net" if "fetch(" in body else ""
        standalone = "function setupDatasets(" in body
        write = " --allow-write" if standalone else ""
        packages = "@langchain/langgraph @langchain/core" + (" pg" if standalone else "")
        doc = ["/**", f" * {_doc(self.title)}{v}: a LangGraph.js graph exported from Superstep.", " *",
               " * The graph on the canvas, written as TypeScript: the state, one function per node, and buildGraph(),",
               " * which connects them. Run it with Deno (the npm: packages are fetched on the first run):", " *",
               f" *     deno run --allow-env --allow-read --allow-sys=homedir{write}{net} {file}", " *",
               " * For Node, drop the \"npm:\" prefixes and versions, `npm i " + packages + "`, then",
               f" * `npx tsx {file}`.", " *"]
        if standalone:
            doc += [" * Dataset bindings use the Superstep API, SQLite (`node:sqlite`), or PostgreSQL (`pg`).",
                    " * Export the binding variables and run this file with `--setup-datasets` before a standalone workflow.",
                    " * Repeating setup keeps existing rows. SQLite needs Node 22.13 or newer, or `NODE_OPTIONS=--experimental-sqlite`",
                    " * on Node 22.5 through 22.12. Deno 2.2 or newer includes the same SQLite module.", " *"]
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
        if "function setupDatasets(" in body:
            out += [
                'import { createHash } from "node:crypto";',
                'import { existsSync, readFileSync } from "node:fs";',
                'import { homedir } from "node:os";',
                'import { dirname, resolve } from "node:path";',
                'import { fileURLToPath } from "node:url";',
            ]
        if self.imports:
            out += ["// imports of the TypeScript Code nodes"] + self.imports
        return doc + out + [""]

    def body(self, graphs: List[Graph], main: Graph) -> None:
        self.add(ENV.rstrip())
        if "templates" in self.uses: self.add(TEMPLATES.rstrip())
        if "model" in self.uses: self.add(MODEL.rstrip())
        if "fallback" in self.uses: self.add(FALLBACK.rstrip())
        if "http" in self.uses or "send_email" in self.uses: self.add(NET.rstrip())
        if "http" in self.uses: self.add(HTTP.rstrip())
        if "dataset" in self.uses:
            self.add("export const DATASET_BINDINGS: Record<string, { columns: unknown[]; name: string; operations: string[] }> = " + lit(self.datasets.bindings) + ";")
            self.add(TS_DATASET.rstrip())
            self.add(typescript_standalone().rstrip())
        if "agent" in self.uses: self.add(AGENT.rstrip())
        if "handoff" in self.uses: self.add(HANDOFF.rstrip() + f"\nconst MAX_HANDOFFS = {self.max_handoffs(main.raw)};")
        if "files" in self.uses: self.add(FILES.rstrip() + (AGENT_FILES.rstrip() if "agent" in self.uses else ""))
        if "fallback_files" in self.uses: self.add(FALLBACK_FILES.rstrip())
        if "routing" in self.uses or "decide" in self.uses: self.add(ROUTING.rstrip())
        if "decide" in self.uses: self.add(DECIDE.rstrip())
        if "approval" in self.uses: self.add(TS_APPROVAL.rstrip())
        stubs = [k for k in STUBS if k in self.uses and k != "managed_operation"]
        if stubs or "managed_operation" in self.uses:
            self.add("\n// --- Studio services ------------------------------------------------------------------------------------")
            self.add("// These nodes use services of the Superstep server. The stubs keep the graph running; replace them.")
            if stubs: self.add(OFFLINE_SERVICE.rstrip())
            if "retrieve" in stubs:
                self.add("\n// Knowledge bases: before a real run set SUPERSTEP_URL, SUPERSTEP_TOKEN and <PREFIX>_ID for")
                self.add(f"// {', '.join(getattr(self, 'knowledge_bases', {}).values())}. Nodes and tools on the same knowledge base share a prefix.")
            if "call_mcp_tool" in stubs:
                self.add("\n// MCP servers: before a real run set <PREFIX>_URL (and <PREFIX>_HEADERS if the server needs them) for")
                self.add(f"// {', '.join(getattr(self, 'mcp_servers', {}).values())}. MCP nodes and tools on the same Superstep server share a prefix.")
                self.add('const MCP_PROTOCOL = "2025-06-18";')
            for k in stubs: self.add(STUBS[k].rstrip())
        if "managed_operation" in self.uses: self.add(TS_MANAGED.rstrip())
        if names := self.export_env_names():
            self.add("// Environment names for this file: " + " ".join(names))
        if "browser" in self.uses:
            self.add("\n// --- Browser ---------------------------------------------------------------------------------------------")
            self.add("// Secrets are read from the environment at run time. BROWSER_POLICY has no tokens, passwords or cookies.")
            self.add(f"const BROWSER_POLICY = {lit(self.browser_policies)};")
            self.add(TS_RUNTIME.replace("__LANGGRAPH_SPEC__", json.dumps(LANGGRAPH)).rstrip())
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
        if self.has_handoffs(g):
            self.add(f"  {lit(self.HANDOFF_FIELD)}: Annotation<Handoff | null>(),  // a hand-off on its way to the next agent")
            self.add(f"  {lit(self.COUNT_FIELD)}: Annotation<number>(),  // hand-offs so far in this run")
            self.add(f"  {lit(self.START_FIELD)}: Annotation<string>(),  // input: start at this agent (a chat continues with the agent that answered last)")
        self.add("});")
        self.add(f"type {cls} = typeof {cls}.State;")
        if is_main:
            self.add("type Update = typeof State.Update;")
            self.add("/** A node's result: the fields it changes (their values come from the canvas, typed at run time). */")
            self.add("const asUpdate = (fields: Record<string, unknown>) => fields as Update;")

    def ts_slots(self, d: dict, attrs: tuple, holes: int = 0) -> str:
        """Positional slot arguments. A provider hole stays `undefined` so the slot is not read as the provider."""
        values = [self.llm_slot(str(d.get(attr) or "")) for attr in attrs]
        if not any(values): return ""
        parts = ["undefined"] * holes + [lit(value) if value else "undefined" for value in values]
        return ", " + ", ".join(parts)

    def mcp_call(self, data: dict, call: str, tool_expr: str, args_expr: str) -> str:
        managed = data.get("_managed_export")
        if call != "managedOperation":
            return f"callMcpTool({lit(self.mcp_prefix(data))}, {tool_expr}, {args_expr})"
        if not isinstance(managed, str):
            return f"managedOperation({tool_expr}, {args_expr})"
        return f"managedOperation({tool_expr}, {args_expr}, {lit(self.managed_prefix(data))}, {lit(managed)})"

    def approval_answer(self, name: str, d: dict, question_expr: str, prompt_expr: str, pad: str, wrap: bool = False) -> None:
        approval = d.get("approval") if isinstance(d.get("approval"), dict) else {}
        kind = str(approval.get("channel") or "").strip().lower()
        policy = d.get("_approval_policy") if isinstance(d.get("_approval_policy"), dict) else None
        deadline = d.get("_deadline") if isinstance(d.get("_deadline"), dict) else None
        judge = self.llm_slot(str(d.get("_judge_credential") or ""))
        self.add(f"{pad}const request = {{ node: {lit(name)}, question: {question_expr}, prompt: {prompt_expr} }} as Ask;")
        if wrap:
            self.add(f"{pad}request.tool = call.name;")
            self.add(f"{pad}request.args = call.args && typeof call.args === \"object\" ? call.args as Record<string, unknown> : {{}};")
        else:
            self.add(f"{pad}request.state = state as Record<string, unknown>;")
        if kind: self.add(f"{pad}request.channel = {lit(kind)};")
        if deadline: self.add(f"{pad}request.deadline = {lit(deadline)};")
        if policy: self.add(f"{pad}request.policy = {lit(policy)};")
        if judge: self.add(f"{pad}request.judge_slot = {lit(judge)};")
        if policy:
            self.add(f"{pad}const reviewed = await reviewApproval(request);")
            answered = "reviewed !== null && reviewed !== undefined ? reviewed : String(interrupt(request))" if wrap else "reviewed !== null && reviewed !== undefined ? reviewed : interrupt(request)"
            self.add(f"{pad}{'const ' if not wrap else ''}answer = {answered};")
        else:
            self.add(f"{pad}{'const ' if not wrap else ''}answer = {'String(interrupt(request))' if wrap else 'interrupt(request)'};")

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
            fb = d.get("fallback") if isinstance(d.get("fallback"), dict) else None  # only the model name: never its credential
            model = lit(d.get("model") or "gpt-4o-mini")
            if fb and files:
                expr = f"await callLlmFilesFallback(prompt, {model}, {lit(str(fb.get('model') or '').strip())}, (state as Record<string, unknown>)[{lit(files)}]{self.ts_slots(d, ('_llm_credential', '_fallback_credential'))})"
            elif files:
                expr = f"await callLlmFiles(prompt, {model}, (state as Record<string, unknown>)[{lit(files)}]{self.ts_slots(d, ('_llm_credential',), holes=1)})"
            elif fb:
                expr = f"await callLlmFallback(prompt, {model}, {lit(str(fb.get('model') or '').strip())}{self.ts_slots(d, ('_llm_credential', '_fallback_credential'))})"
            else:
                expr = f"await callLlm(prompt, {model}{self.ts_slots(d, ('_llm_credential',), holes=1)})"
            self.add(ret(expr))
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
            if approval_policy.mode(d) != "off": extra.append("has AI review of the request")
            if extra: self.add(f" * In Superstep this node {' and '.join(extra)}; that is not part of LangGraph.")
            self.add(" */")
            self.add(sig)
            if self.approval_extra(d):
                self.approval_answer(name, d, f"render({const}_PROMPT, state)", f"render({const}_PROMPT, state)", "  ")
            else:
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
        elif t == "dataset":
            operation = d.get("operation")
            write = operation in {"insert_row", "upsert_row", "delete_row"}
            config = ", config: unknown" if write else ""
            key = ", await datasetOperationId(config)" if write else ""
            self.add(f"const {const}_ARGUMENTS = {lit(d.get('arguments') or {})};")
            self.add("")
            self.add(f"/** {head}: run a typed operation against the configured dataset. */")
            self.add(f"async function {name}(state: {cls}{config}): Promise<Update> {{")
            self.add(ret(f"await datasetCall({lit(d.get('dataset_id'))}, {lit(operation)}, {lit(d.get('fields') or [])}, renderArgs({const}_ARGUMENTS, state) as Record<string, unknown>{key})"))
            self.add("}")
        elif t == "retriever":
            self.add(f"const {const}_QUERY = {lit(d.get('query') or '')};")
            self.add("")
            self.add(f"/** {head}: the chunks of a knowledge base that best match the query (see retrieve). */")
            self.add(sig)
            self.add(ret(f"await retrieve({lit(self.kb_prefix(d))}, render({const}_QUERY, state), {number(d.get('top_k'), int) or 4})"))
            self.add("}")
        elif t == "mcp":
            info = d.get("_browser_export")
            if isinstance(info, dict):
                self.add(f"const {const}_ARGUMENTS = {lit(d.get('arguments') or {})};")
                self.add("")
                self.add(f"/** {head}: browser tool {lit(_doc(d.get('tool')))}. */")
                self.add(sig)
                self.add(ret(self.browser_expr(info, d, f"renderArgs({const}_ARGUMENTS, state)")))
                self.add("}")
            else:
                call = "managedOperation" if d.get("_managed_export") else "callMcpTool"
                self.add(f"const {const}_ARGUMENTS = {lit(d.get('arguments') or {})};")
                self.add("")
                self.add(f"/** {head}: MCP tool {lit(_doc(d.get('tool')))} (see {call}). */")
                self.add(sig)
                if d.get("_managed_export") is True: self.add("  // TODO: implement this managed step; the placeholder throws until replaced.")
                self.add(ret(f"await {self.mcp_call(d, call, lit(d.get('tool') or ''), f'renderArgs({const}_ARGUMENTS, state)')}"))
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
            if build is None:
                self.add(f"/** {head}: TODO: the workflow {_doc(ref)} was not found when this file was exported. */")
                self.add(sig)
                self.add("  void state;")
                self.add(f"  throw new Error({lit(f'{head}: the subgraph workflow {ref} was not found when this file was exported (deleted, or not shared with you)')});")
                self.add("}")
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
        self.add(f"    const answer = await decide(text, {{ ...question, instructions: render(question.instructions, state) }}{self.ts_slots(d, ('_llm_credential',))});")
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
            body = "undefined" if method in ("GET", "HEAD") else f"render({const}_BODY, state)"
            self.add(f"  const result = await httpRequest({lit(nid)}, {lit(method)}, render({const}_URL, state), {body});")
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
        self.add(f"    node: {lit(g.names[nid])},")
        self.add(f"    sends: {'true' if d.get('_email_sends') else 'false'},  // an SMTP credential in the studio (not exported): a real send")
        self.add("  };")
        out = d.get("output_field")
        if out: self.add(f"  return asUpdate({{ {lit(out)}: await sendEmail(message) }});")
        else:
            self.add("  await sendEmail(message);")
            self.add("  return {};")
        self.add("}")

    def agent(self, g: Graph, nid: str, cls: str, head: str, sig: str) -> None:
        """An Agent node as the studio runs it, as in the Python file: an entry node, the model node and the
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
        hs = self.handoff_tools(g, nid) if "handoff" in a else []
        if hs:
            self.add("// Hand-offs: the transfer tools the model may call, and the agent each one leads to.")
            self.add(f"const {const}_HANDOFF_TOOLS: ToolSpec[] = {lit(self.handoff_specs(hs))};")
            self.add(f"const {const}_HANDOFFS: Record<string, {{ to: string; label: string }}> = {lit({h['name']: {'to': h['node'], 'label': h['label']} for h in hs})};")
        self.add(f"const {const}_MAX_ROUNDS = {self.rounds(d)};")
        self.add("")
        self.add(f"/** {head}: starts the conversation in state[{_doc(chat)}].")
        self.add(" *")
        self.add(" * Then the model and the tools take turns, one node each:")
        self.add(f" * - {model}() asks the model, which answers or asks for tool calls;")
        self.add(f" * - {tool}() runs one tool call (route_{model}() and route_{tool}() pick the next node);")
        self.add(f" * - {end}() writes the answer. */")
        self.add(sig)
        if nid in self.receivers(g):
            self.add(f"  const got = state[{lit(self.HANDOFF_FIELD)}];")
            self.add(f"  if (got && got.to === {lit(name)}) {{  // handed off to this agent: the note, then the conversation so far")
            self.add("    const reason = got.reason ? ` Reason: ${got.reason}.` : \"\";")
            sys_ = f"render({const}_SYSTEM, state), " if d.get("system_prompt") else ""
            self.add(f"    const system = [{sys_}HANDOFF_NOTE.replace(\"{{source}}\", got.from).replace(\"{{reason}}\", reason)].filter(Boolean).join(\"\\n\\n\");")
            self.add(f"    const messages: ChatMessage[] = [{{ role: \"system\", content: system }}, ...got.messages, {{ role: \"user\", content: render({const}_PROMPT, state) }}];")
            self.add(f"    return asUpdate({{ {chat}: {{ messages, pending: [], rounds: 0, steps: [], answer: null }}, {lit(self.HANDOFF_FIELD)}: null }});")
            self.add("  }")
        self.add("  const messages: ChatMessage[] = [];")
        if d.get("system_prompt"): self.add(f"  messages.push({{ role: \"system\", content: render({const}_SYSTEM, state) }});")
        if d.get("history_field"):
            self.add(f"  const history: unknown = (state as Record<string, unknown>)[{lit(d['history_field'])}];")
            self.add("  for (const m of Array.isArray(history) ? history : []) {  // the earlier turns of a chat")
            self.add("    if (m && (m.role === \"user\" || m.role === \"assistant\") && typeof m.content === \"string\") {")
            self.add("      messages.push({ role: m.role, content: m.content });")
            self.add("    }")
            self.add("  }")
            self.add(f"  const prompt = render({const}_PROMPT, state);")
            self.add("  const tail = messages[messages.length - 1];")
            self.add("  if (tail && tail.role === \"user\" && prompt.includes(String(tail.content).trim())) messages.pop();  // the current chat message, already in the prompt")
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
        if hs:
            self.add(f"  const can = (state[{lit(self.COUNT_FIELD)}] ?? 0) < MAX_HANDOFFS;")
            self.add("  if (!can && !chat.no_more) {  // the run's hand-offs are used up: say so once")
            self.add("    chat.messages = [{ role: \"system\", content: NO_MORE }, ...chat.messages];")
            self.add("    chat.no_more = true;")
            self.add("  }")
            self.add(f"  const tools = can ? [...{const}_TOOLS, ...{const}_HANDOFF_TOOLS] : {const}_TOOLS;")
            self.add(f"  const [text, asked] = await {call}(chat.messages, last ? null : tools, {lit(d.get('model') or 'gpt-4o-mini')}{self.ts_slots(d, ('_llm_credential',))});")
        else:
            self.add(f"  const [text, asked] = await {call}(chat.messages, last ? null : {const}_TOOLS, {lit(d.get('model') or 'gpt-4o-mini')}{self.ts_slots(d, ('_llm_credential',))});")
        self.add("  const calls: ToolCall[] = last ? [] : asked.map((c, i) => ({ id: String(c.id || `call_${i}`), name: String(c.name || \"\"), args: c.args }));")
        self.add("  if (!last) chat.rounds += 1;")
        self.add("  chat.messages = [...chat.messages, { role: \"assistant\", content: text, ...(calls.length ? { tool_calls: calls } : {}) }];")
        if hs:
            self.add(f"  const first = can ? calls.find(c => c.name in {const}_HANDOFFS) : undefined;")
            self.add("  if (first) {  // the hand-off wins: the other calls of the round are answered, not run")
            self.add(f"    const h = {const}_HANDOFFS[first.name];")
            self.add("    for (const c of calls) {")
            self.add("      chat.messages = [...chat.messages, { role: \"tool\", tool_call_id: c.id, name: c.name, content: c === first ? `Handed off to ${h.label}` : NOT_RUN }];")
            self.add("      if (c !== first) chat.steps = [...chat.steps, { tool: c.name, args: c.args, result: NOT_RUN, status: \"not_run\", ms: 0 }];")
            self.add("    }")
            self.add("    const args = (first.args && typeof first.args === \"object\" ? first.args : {}) as Record<string, unknown>;")
            self.add("    chat.pending = [];")
            self.add("    chat.handoff = { to: h.to, reason: String(args.reason ?? \"\").slice(0, 500) };")
            self.add(f"    return asUpdate({{ {chat}: chat }});")
            self.add("  }")
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
        if hs:
            self.add("/** After a model call: \"handoff\" when it handed off, \"tool\" while tool calls wait, else \"done\". */")
            self.add(f"function route_{model}(state: {cls}): string {{")
            self.add(f"  if (state[{chat}]?.handoff) return \"handoff\";")
        else:
            self.add("/** After a model call: \"tool\" while tool calls wait, else \"done\". */")
            self.add(f"function route_{model}(state: {cls}): string {{")
        self.add(f"  return state[{chat}]?.pending.length ? \"tool\" : \"done\";")
        self.add("}")
        if hs:
            hn = a["handoff"]
            self.add("")
            self.add(f"/** {_doc(who)} hands off: the conversation so far goes to the next agent, and this one ends without answering. */")
            self.add(f"function {hn}(state: {cls}): Update {{")
            self.add(f"  const chat = state[{chat}]!;")
            self.add(f"  const handoff: Handoff = {{ from: {lit(who)}, to: chat.handoff!.to, reason: chat.handoff!.reason, messages: carried(chat.messages) }};")
            self.add(f"  return asUpdate({{ {chat}: null, {lit(self.HANDOFF_FIELD)}: handoff, {lit(self.COUNT_FIELD)}: (state[{lit(self.COUNT_FIELD)}] ?? 0) + 1 }});")
            self.add("}")
            self.add("")
            self.add("/** The agent the hand-off goes to. */")
            self.add(f"function route_{hn}(state: {cls}): string {{")
            self.add(f"  return state[{lit(self.HANDOFF_FIELD)}]!.to;")
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
        if approval_policy.mode(d) != "off":
            self.add(" * In Superstep a model can review the request first (AI review); suggest mode still asks, and auto mode may answer.")
        self.add(" */")
        self.add(f"async function {tool}(state: {cls}{', config: unknown' if self.dataset_writes(d) else ''}): Promise<Update> {{")
        self.add(f"  const chat: AgentChat = {{ ...state[{chat}]! }};")
        self.add("  const pending = [...chat.pending];")
        self.add(f"  let n = Math.min(waveCap({const}_PARALLEL), pending.length);")
        if approval:
            self.add("  for (let i = 0; i < n; i++) {")
            self.add(f"    if ({const}_NEEDS_APPROVAL.includes(pending[i].name)) {{ n = i === 0 ? 1 : i; break; }}")
            self.add("  }")
        self.add("  const batch = pending.slice(0, n);")
        self.add("  chat.pending = pending.slice(n);")
        dataset_tools = [tool["name"] for tool in d.get("tools") or [] if isinstance(tool, dict) and tool.get("source") == "dataset"]
        writes = self.dataset_writes(d)
        if writes:
            self.add("  const stepId = await datasetOperationId(config);  // one receipt per model call: this step plus the call id")
        self.add("  async function one(call: ToolCall): Promise<[ChatMessage, AgentStep]> {")
        if dataset_tools:
            self.add(f"    const dataset = {lit(dataset_tools)}.includes(call.name);")
            self.add("    let count: number | null = null;")
        self.add(f"    const spec = {const}_TOOLS.find((t) => t.name === call.name);")
        self.add("    const problem = spec ? checkArguments(spec.parameters, call.args) : null;")
        if approval:
            self.add("    let answer: string | null = null;")
            self.add(f"    if (spec && problem === null && {const}_NEEDS_APPROVAL.includes(call.name)) {{")
            self.add(f"      const question = {lit(who + ' wants to call ')} + call.name + \" with these arguments:\\n\"")
            self.add("        + JSON.stringify(call.args, null, 2)")
            self.add("        + \"\\nApprove to run it, or reject it. A text reply rejects it and tells the model why.\";")
            if self.approval_extra(d):
                self.approval_answer(name, d, "question", "question", "      ", wrap=True)
            else:
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
        if dataset_tools:
            if writes:
                self.add("        const operationId = await datasetOperationId({ metadata: { langgraph_checkpoint_ns: stepId + \"#\" + call.id } });")
                self.add(f"        const value = await call_{name}_tool(call.name, call.args as Record<string, unknown>, state, operationId);")
            else:
                self.add(f"        const value = await call_{name}_tool(call.name, call.args as Record<string, unknown>, state);")
            self.add("        if (dataset) count = Array.isArray((value as { rows?: unknown[] }).rows) ? (value as { rows: unknown[] }).rows.length : 1;")
            self.add("        [status, result] = [\"ok\", toolText(value)];")
        else:
            self.add(f"        [status, result] = [\"ok\", toolText(await call_{name}_tool(call.name, call.args as Record<string, unknown>, state))];")
        self.add("      } catch (error) {  // the model hears about the failure and can try something else")
        self.add("        const paused = error instanceof Error ? error.name : \"\";")
        self.add("        if (paused === \"GraphInterrupt\" || paused === \"GraphBubbleUp\") throw error;")
        self.add("        [status, result] = [\"error\", `The tool failed: ${error instanceof Error ? error.message : error}`];")
        self.add("      }")
        self.add("    }")
        self.add("    const step: AgentStep = { tool: call.name, args: call.args, result: shorten(result, STEP_CHARS), status,")
        self.add("      ms: Math.round((performance.now() - started) * 100) / 100 };")
        if dataset_tools:
            if writes:
                self.add("    const operation = (call.args as Record<string, unknown> | null)?.operation;")
                self.add("    if (dataset) Object.assign(step, { args: {}, result: \"\", dataset: { count, ...(operation === \"insert_row\" || operation === \"upsert_row\" ? { operation } : {}) } });")
            else:
                self.add("    if (dataset) Object.assign(step, { args: {}, result: \"\", dataset: { count } });")
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

    def browser_expr(self, info: dict, data: dict, args_expr: str) -> str:
        tool = data.get("tool") or ""
        binding = export_binding(data.get("url_binding"))
        target = data.get("target") if isinstance(data.get("target"), dict) else None
        targets = data.get("targets") if isinstance(data.get("targets"), dict) else None
        prepared = f"browserPrepare({lit(tool)}, {args_expr}, {lit(target)}, {lit(targets)}, state)"
        bound = f"bindBrowserUrl({lit(binding)}, {prepared}, state)"
        return f"await browserCall({lit(info.get('alias') or '')}, {lit(tool)}, {bound}, state)"

    @staticmethod
    def dataset_writes(d: dict) -> bool:
        """Whether an Agent node has a Dataset tool that may insert or upsert rows."""
        return any(isinstance(t, dict) and t.get("source") == "dataset"
                   and dataset_nodes.agent_writes(dataset_nodes.agent_binding(t)) for t in d.get("tools") or [])

    def agent_calls(self, d: dict, name: str, const: str, cls: str) -> None:
        """call_<agent>_tool(): what each of the Agent node's tools does."""
        self.add("")
        self.add("/** Runs the tool the model asked for with the model's arguments. */")
        self.add(f"async function call_{name}_tool(name: string, args: Record<string, unknown>, state: {cls}{', operationId?: string' if self.dataset_writes(d) else ''}): Promise<unknown> {{")
        for t in d.get("tools") or []:
            if not isinstance(t, dict): continue
            src, tname = t.get("source"), t.get("name") or ""
            self.add(f"  if (name === {lit(tname)}) {{")
            if src == "builtin":
                fn = t.get("function") or ""
                self.uses.add("agent_builtin")
                self.add(f"    // TODO: port the server's Python function {_doc(fn)} to TypeScript (the Python export has its source).")
                self.add(f"    throw new Error({lit(f'{fn} is a Python function of the Superstep server: not implemented in TS export')});")
            elif src == "dataset":
                binding = dataset_nodes.agent_binding(t)
                head = f"await datasetAgent({lit(t.get('dataset_id'))}, {lit(t.get('fields') or [])}, {lit(t.get('filter_ops') or {})}, {lit(t.get('limit', 10))}, args"
                if dataset_nodes.agent_writes(binding):
                    writes = {key: binding[key] for key in ("operations", "write_fields", "key") if key in binding}
                    self.add(f"    return {head}, {lit(writes)}, operationId);")
                else:
                    self.add(f"    return {head});")
            elif src == "knowledge":
                self.add(f"    return await retrieve({lit(self.kb_prefix(t))}, String(args.query || \"\"), {number(t.get('top_k'), int) or 4});")
            elif src == "mcp":
                info = t.get("_browser_export")
                if isinstance(info, dict):
                    self.add(f"    return {self.browser_expr(info, t, 'args')};")
                else:
                    call = "managedOperation" if t.get("_managed_export") else "callMcpTool"
                    self.add(f"    return await {self.mcp_call(t, call, lit(t.get('tool') or ''), 'args')};")
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
                    self.add(f"    throw new Error({lit(f'tool {tname}: the workflow {ref} was not found when this file was exported (deleted, or not shared with you)')});")
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
                self.add(f"    return await httpRequest({lit(name + ':' + tname)}, {lit(method)}, url, {send.replace(' || undefined', '')});")
            else:
                self.add(f"    throw new Error({lit(f'unknown tool source {src!r}')});")
            self.add("  }")
        self.add("  throw new Error(`unknown tool ${name}`);")
        self.add("}")

    @staticmethod
    def start_router(build: str, is_main: bool) -> str: return "routeStart" if is_main else f"routeStart_{build}"

    def build(self, g: Graph, cls: str, build: str, is_main: bool) -> None:
        name = lambda i: "END" if g.nodes[i]["type"] == "end" else lit(g.names[i])  # noqa: E731
        leave = lambda i: lit(g.agents[i]["exit"]) if i in g.agents else lit(g.names[i])  # an Agent node's edges leave from its end node  # noqa: E731
        cache = any(number((n.get("data") or {}).get("cache_ttl"), int) is not None for n in g.nodes.values())
        if (rec := self.start_receivers(g)):
            r = self.start_router(build, is_main)
            first = [name(e["target"]) for x in g.nodes if g.nodes[x]["type"] == "start" for e in g.out(x) if g.nodes[e["target"]]["type"] != "join"]
            self.add("")
            self.add(f"const {r.upper()}_AGENTS = {lit([g.names[i] for i in rec])};  // the agents a chat may continue with")
            self.add("")
            self.add(f"/** Where the run starts: the agent named in {self.START_FIELD}, if it is one a hand-off reaches, else the first node. */")
            self.add(f"function {r}(state: {cls}): string[] {{")
            self.add(f"  const at = state[{lit(self.START_FIELD)}];")
            self.add(f"  return at && {r.upper()}_AGENTS.includes(at) ? [at] : [{', '.join(first)}];")
            self.add("}")
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
                fn = f"{self.built[ref][1]}()" if ref in self.built else g.names[nid]  # missing: the node throws
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
                for step in ("model", "tool", "exit", "handoff"):
                    if step in g.agents[nid]: self.add(f"    .addNode({lit(g.agents[nid][step])}, {g.agents[nid][step]})")
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
                more = f", handoff: {a['handoff']}" if "handoff" in a else ""
                self.add(f"    .addConditionalEdges({a['model']}, route_{g.agents[nid]['model']}, {{ tool: {a['tool']}, done: {a['exit']}{more} }})")
                self.add(f"    .addConditionalEdges({a['tool']}, route_{g.agents[nid]['tool']}, {{ tool: {a['tool']}, model: {a['model']} }})")
                if "handoff" in a:
                    to = ", ".join(f"{lit(h['node'])}: {lit(h['node'])}" for h in self.handoff_tools(g, nid))
                    self.add(f"    .addConditionalEdges({a['handoff']}, route_{g.agents[nid]['handoff']}, {{ {to} }})  // hand-offs")
            if n["type"] in ("condition", "foreach") and out:
                if first_edge and n["type"] == "condition":
                    self.add("    // A conditional edge: the router returns a label, and the map says which node it leads to.")
                    first_edge = False
                mapping = ", ".join(f"{lit(e.get('label'))}: {name(e['target'])}" for e in out)
                self.add(f"    .addConditionalEdges({src}, route_{g.names[nid]}, {{ {mapping} }})")
            elif n["type"] == "start" and self.start_receivers(g):
                targets = [e["target"] for e in out if g.nodes[e["target"]]["type"] != "join"]
                every = ", ".join(dict.fromkeys([name(t) for t in targets] + [lit(g.names[r]) for r in self.start_receivers(g)]))
                self.add(f"    // A chat continues with the agent that answered last: {self.START_FIELD} in the input starts there.")
                self.add(f"    .addConditionalEdges(START, {self.start_router(build, is_main)}, [{every}])")
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
            if i in g.agents: queue += [h["target"] for h in self.handoff_raw(g, i)]  # hand-off targets
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
        if "dataset" in self.uses:
            self.add('  if (datasetCliArgs().length === 1 && datasetCliArgs()[0] === "--setup-datasets") {')
            self.add("    await setupDatasets(true);")
            self.add('    console.log("Dataset storage is ready.");')
            self.add("    return;")
            self.add("  }")
            self.add("  await setupDatasets(false);")
        self.add("  const graph = buildGraph(new MemorySaver());")
        cfg = '{ configurable: { thread_id: "example" }' + (f", recursionLimit: {RECURSION + budget}" if budget else "") + " }"
        self.add("  // thread_id names this run in the checkpointer" + ("; For each loops need more steps than the default 25." if budget else "."))
        self.add(f"  const config = {cfg};")
        self.add("  const print = (node: string, delta: unknown) => console.log(`[${node}] ${JSON.stringify(delta)}`);")
        if has_human:
            self.add("  const answers = Object.fromEntries(Object.entries(EXAMPLE_ANSWERS).map(([k, v]) => [k, [...v]]));")
            if "approval" in self.uses:
                self.add("  // Ask is declared with the approval helpers.")
                self.add("  const answerFor = async (request: Ask): Promise<string> => {")
                self.add("    const queued = answers[request.node]?.shift();")
                self.add("    const value = queued !== undefined ? queued : (await notifyApproval(request), await waitApproval(request));")
                self.add("    console.log(`>> ${request.node}: ${value}`);")
                self.add("    return value;")
                self.add("  };")
            else:
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
            if "approval" in self.uses:
                self.add("    payload = waiting.length === 1")
                self.add("      ? resume(await answerFor(waiting[0].value))")
                self.add("      : resume(Object.fromEntries(await Promise.all(waiting.map(async (i) => [i.id, await answerFor(i.value)] as const))));")
            else:
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
                  example: Optional[dict] = None, *, datasets: DatasetExport | None = None) -> Export:
    """The LangGraph.js TypeScript file for workflow `wf` (same arguments as `python_export.to_python`)."""
    return _Writer(name, version, children or {}, example, datasets).write(wf)
