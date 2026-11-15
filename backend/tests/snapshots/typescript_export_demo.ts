/**
 * TypeScript demo (version 3): a LangGraph.js graph exported from Superstep.
 *
 * The graph on the canvas, written as TypeScript: the state, one function per node, and buildGraph(),
 * which connects them. Run it with Deno (the npm: packages are fetched on the first run):
 *
 *     deno run --allow-env --allow-read --allow-sys=homedir typescript_demo.ts
 *
 * For Node, drop the "npm:" prefixes and versions, `npm i @langchain/langgraph @langchain/core`, then
 * `npx tsx typescript_demo.ts`.
 *
 * TypeScript Code nodes run here as written on the canvas, without the studio's sandbox: read them
 * first. Python Code nodes and Python tool functions are stubs that throw: port them to TypeScript.
 *
 * Credentials, knowledge bases, MCP servers and approval channels are not exported; keys are read from
 * environment variables.
 */
import { Annotation, END, interrupt, MemorySaver, START, StateGraph } from "npm:@langchain/langgraph@^1.5";
// imports of the TypeScript Code nodes
import { z } from "npm:zod@^3"


// --- Environment --------------------------------------------------------------------------------------------------
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

// --- Reducers -----------------------------------------------------------------------------------------------------
// A reducer says how a node's output combines with the field's current value. Without one, the new
// value replaces the old one, and two parallel branches writing the same field in one step is an error.

/** Reducer "append": a list that collects every value written to it, from parallel branches too. */
function appendItems(current: unknown, next: unknown): unknown[] {
  const list = current === null || current === undefined ? [] : Array.isArray(current) ? current : [current];
  return list.concat(Array.isArray(next) ? next : next === null || next === undefined ? [] : [next]);
}

// ==================================================================================================================
// Graph
// ==================================================================================================================

// The state is an object shared by every node. A node returns only the fields it changes, and LangGraph
// merges them into the state (through the field's reducer, if it has one).
const State = Annotation.Root({
  "message": Annotation<string>(),
  "count": Annotation<number>(),
  "out": Annotation<Record<string, unknown>>(),
  "py": Annotation<string>(),
  "tags": Annotation<unknown[], unknown>({ reducer: appendItems, default: () => [] }),
});
type State = typeof State.State;
type Update = typeof State.Update;
/** A node's result: the fields it changes (their values come from the canvas, typed at run time). */
const asUpdate = (fields: Record<string, unknown>) => fields as Update;

// Tool node "c" (id: c): the node's TypeScript as written on the canvas (its imports are at the top of the
// file). In the studio it runs in a sandbox without network access; here it runs in this process.
const CCode = (() => {
  function main(state: State) {
    console.log("got", state.message)
    const msg = z.string().parse(state.message ?? "")
    return { shout: msg.toUpperCase(), count: (state.count ?? 0) + 1 }
  }
  return main;
})();

/** Tool node "c" (id: c): main(state) gives the result. */
async function c(state: State): Promise<Update> {
  return asUpdate({ "out": await CCode(structuredClone(state)) });
}

/** Tool node "p" (id: p): written in python on the canvas, which this TypeScript file cannot run.
 * TODO: port the node's code to TypeScript. */
async function p(state: State): Promise<Update> {
  void state;
  throw new Error("Tool node \"p\" (id: p) is python code: not implemented in TS export (port it to TypeScript)");
}

/** The graph: nodes, then edges. compile() checks it and returns a runnable graph. */
export function buildGraph(checkpointer?: MemorySaver) {
  return new StateGraph(State)
    .addNode("c", c)
    // p() is not connected to Start; LangGraph.js rejects unreachable nodes, so it is left out.
    .addEdge(START, "c")
    .addEdge("c", END)
    // The checkpointer saves the state after every step, so a run paused by interrupt() can resume.
    .compile({ checkpointer });
}

// ==================================================================================================================
// Run it
// ==================================================================================================================

const EXAMPLE_INPUT = {"message": "héllo wörld", "count": 1} as Update;

async function main(): Promise<void> {
  const graph = buildGraph(new MemorySaver());
  // thread_id names this run in the checkpointer.
  const config = { configurable: { thread_id: "example" } };
  const print = (node: string, delta: unknown) => console.log(`[${node}] ${JSON.stringify(delta)}`);
  // streamMode "updates": what each node returned, step by step (subgraphs: inside subgraphs too).
  for await (const [, update] of await graph.stream(EXAMPLE_INPUT, { ...config, streamMode: "updates", subgraphs: true })) {
    for (const [node, delta] of Object.entries(update as Record<string, unknown>)) print(node, delta);
  }
  console.log("Final state:", JSON.stringify((await graph.getState(config)).values, null, 2));
}

if ((import.meta as { main?: boolean }).main !== false) await main();
