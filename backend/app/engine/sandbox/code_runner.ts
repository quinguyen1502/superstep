// Runs one TypeScript Tool node Code call. Executed INSIDE the sandbox by Deno with no
// permission at all: `deno run --no-prompt --no-remote --cached-only data:application/typescript;base64,<this file>`.
// Never imported by the server. It uses no import, so any Deno 2 can run it.
//
// stdin: one JSON object {"source", "state", "stdout_max"}.
// stdout: the last line is one JSON object, either {"ok": true, "value", "stdout"} or
// {"ok": false, "kind": "invalid" | "failed" | "not_json", "error", "traceback", "stdout", "type"} (same as code_runner.py).

const FILE = "<code>";
const enc = new TextEncoder();
const out: string[] = [];
const write = Deno.stdout.writeSync.bind(Deno.stdout);

function result(obj: Record<string, unknown>): void {
  write(enc.encode("\n" + JSON.stringify(obj) + "\n"));
}

function clip(text: string, limit: number): string {
  const data = enc.encode(text);
  if (data.length <= limit) return text;
  return new TextDecoder().decode(data.slice(0, limit)).replace(/\uFFFD+$/, "") +
    `\n…[${data.length - limit} more bytes]`;
}

function b64(text: string): string {
  const bytes = enc.encode(text);
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

const fmt = (args: unknown[]) =>
  args.map((a) => typeof a === "string" ? a : Deno.inspect(a, { colors: false, depth: 6 })).join(" ");
for (const k of ["log", "info", "debug", "warn", "error", "trace"] as const) {
  (console as unknown as Record<string, unknown>)[k] = (...a: unknown[]) => {
    out.push(fmt(a) + "\n");
  };
}

function frames(err: unknown, url: string): string {
  const stack = err instanceof Error && err.stack ? err.stack : String(err);
  const lines = stack.split(url).join(FILE).split("\n");
  const head = lines[0];
  const own = lines.slice(1).filter((l) => l.includes(FILE));
  return [head, ...own].join("\n").trim();
}

const describe = (err: unknown) => err instanceof Error ? `${err.name}: ${err.message}` : `Uncaught ${String(err)}`;

const req = JSON.parse(await new Response(Deno.stdin.readable).text());
const limit = Number(req.stdout_max) || 65536;
const url = "data:application/typescript;base64," + b64(String(req.source));
try {
  Object.defineProperty(Deno, "exit", {
    value: (code?: number) => {
      throw new Error(`Deno.exit(${code ?? 0}) is not allowed in a Code node`);
    },
  });
} catch { /* a Deno without a configurable exit: the host then reports the missing result line */ }

async function run(): Promise<void> {
  let mod: Record<string, unknown>;
  try {
    mod = await import(url);
  } catch (err) {
    const text = String(err);
    const kind = err instanceof SyntaxError ||
        /SyntaxError|Failed loading|not found in cache|Module not found|Relative import/i.test(text)
      ? "invalid"
      : "failed";
    const error =
      (text.includes("SyntaxError:") ? text.slice(text.indexOf("SyntaxError:")) : describe(err)).split("\n")[0];
    result({
      ok: false,
      kind,
      error: error.split(url).join(FILE),
      traceback: frames(err, url),
      stdout: clip(out.join(""), limit),
    });
    return;
  }
  const fn = mod.main;
  if (typeof fn !== "function") {
    result({
      ok: false,
      kind: "invalid",
      error: "export a function main(state)",
      traceback: "",
      stdout: clip(out.join(""), limit),
    });
  } else {
    let value: unknown, failed = false;
    try {
      value = await (fn as (s: unknown) => unknown)(req.state);
    } catch (err) {
      failed = true;
      result({
        ok: false,
        kind: "failed",
        error: describe(err).slice(0, 1000),
        traceback: frames(err, url),
        stdout: clip(out.join(""), limit),
      });
    }
    if (!failed) {
      const stdout = clip(out.join(""), limit);
      let line: string | undefined;
      try {
        line = value === undefined ? undefined : JSON.stringify({ ok: true, value, stdout });
      } catch {
        line = undefined;
      }
      if (line === undefined || !("value" in JSON.parse(line))) {
        const type = value === null
          ? "null"
          : typeof value === "object"
          ? (value as object).constructor?.name ?? "object"
          : typeof value;
        result({ ok: false, kind: "not_json", type, error: "", traceback: "", stdout });
      } else write(enc.encode("\n" + line + "\n"));
    }
  }
}

await run();
