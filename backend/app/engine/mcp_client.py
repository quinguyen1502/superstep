"""Minimal MCP client: `initialize`, `tools/list`, `tools/call` over stdio or Streamable HTTP (JSON-RPC 2.0).

Written against the MCP specification instead of the SDK so the process sandbox (environment, working directory,
timeouts, kill) and the outbound HTTP policy stay under our control. One short session per call.
stdio servers get ONLY the variables in `spec["env"]` plus PATH/LANG and a fresh empty HOME/working directory: the
API's own environment (JWT_SECRET, DATABASE_URL, …) is never inherited."""
from __future__ import annotations
import json, os, queue, shutil, signal, subprocess, tempfile, threading, time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional
import httpx

PROTOCOL = "2025-06-18"
CLIENT = {"name": "superstep", "version": "1.0"}
STDERR_KEEP = 2000


class McpError(Exception):
    """code: MCP_CONNECT_FAILED (transport/protocol) or MCP_TOOL_FAILED (the tool reported an error)."""
    def __init__(self, message: str, code: str = "MCP_CONNECT_FAILED"):
        super().__init__(message); self.code = code


def http_client(timeout: float) -> httpx.Client:
    """Factory for Streamable HTTP calls (tests may replace it)."""
    return httpx.Client(timeout=timeout, follow_redirects=False)


class _Stdio:
    def __init__(self, spec: Dict[str, Any], timeout: float):
        self.timeout, self.home = timeout, tempfile.mkdtemp(prefix="lgs-mcp-")
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "HOME": self.home, **(spec.get("env") or {})}
        try:
            self.p = subprocess.Popen([spec["command"], *(spec.get("args") or [])], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, env=env, cwd=self.home, start_new_session=True)
        except OSError as e:
            shutil.rmtree(self.home, ignore_errors=True)
            raise McpError(f"cannot start '{spec['command']}': {e.strerror or type(e).__name__}") from None
        self.lines: "queue.Queue[Optional[bytes]]" = queue.Queue(); self.err = b""
        threading.Thread(target=self._read, daemon=True).start(); threading.Thread(target=self._read_err, daemon=True).start()

    def _read(self):
        for line in self.p.stdout: self.lines.put(line)
        self.lines.put(None)

    def _read_err(self):
        for chunk in iter(lambda: self.p.stderr.read(512), b""): self.err = (self.err + chunk)[-STDERR_KEEP:]

    def send(self, msg: dict) -> None:
        try: self.p.stdin.write((json.dumps(msg) + "\n").encode()); self.p.stdin.flush()
        except (BrokenPipeError, OSError): raise McpError(self._exited()) from None

    def _exited(self) -> str:
        tail = self.err.decode(errors="replace").strip().splitlines()[-1:] or [""]
        return f"server process exited (code {self.p.poll()}){': ' + tail[0][:300] if tail[0] else ''}"

    def receive(self, rid: int) -> dict:
        deadline = time.monotonic() + self.timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0: raise McpError(f"no response within {self.timeout:g}s")
            try: line = self.lines.get(timeout=left)
            except queue.Empty: continue
            if line is None: raise McpError(self._exited())
            try: msg = json.loads(line)
            except ValueError: continue  # stray output on stdout
            if msg.get("id") == rid and ("result" in msg or "error" in msg): return msg
            if "method" in msg and "id" in msg:  # a server request (roots, sampling…): not supported
                self.send({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "not supported"}})

    def close(self) -> None:
        try: self.p.stdin.close()
        except OSError: pass
        try: self.p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try: os.killpg(self.p.pid, signal.SIGKILL)  # the whole process group: servers that spawn children
            except OSError: pass
            self.p.wait()
        shutil.rmtree(self.home, ignore_errors=True)


class _Http:
    def __init__(self, spec: Dict[str, Any], timeout: float):
        self.url, self.headers, self.session = spec["url"], dict(spec.get("headers") or {}), None
        self.pin = spec.get("pin")  # callable(url) -> (url, headers, extensions): connect to the validated IP (SSRF)
        self.c, self.pending = http_client(timeout), {}

    def _post(self, msg: dict) -> httpx.Response:
        url, extra, ext = self.pin(self.url) if self.pin else (self.url, {}, {})
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": PROTOCOL,
             **self.headers, **extra, **({"Mcp-Session-Id": self.session} if self.session else {})}
        try: r = self.c.post(url, content=json.dumps(msg), headers=h, extensions=ext)
        except httpx.HTTPError as e: raise McpError(f"connection failed ({type(e).__name__})") from None
        if r.status_code >= 400: raise McpError(f"HTTP {r.status_code}")
        self.session = r.headers.get("mcp-session-id") or self.session
        return r

    def send(self, msg: dict) -> None:
        r = self._post(msg)
        if "id" not in msg or r.status_code == 202: return
        ctype = r.headers.get("content-type", "")
        msgs = [json.loads(line[5:]) for line in r.text.splitlines() if line.startswith("data:") and line[5:].strip()] \
            if "text/event-stream" in ctype else ([r.json()] if r.content else [])
        for m in (x for x in msgs if isinstance(x, dict)):
            if "id" in m and ("result" in m or "error" in m): self.pending[m["id"]] = m

    def receive(self, rid: int) -> dict:
        if rid not in self.pending: raise McpError("no response from server")
        return self.pending.pop(rid)

    def close(self) -> None:
        if self.session:
            url, extra, ext = self.pin(self.url) if self.pin else (self.url, {}, {})
            try: self.c.delete(url, headers={**self.headers, **extra, "Mcp-Session-Id": self.session}, extensions=ext)
            except httpx.HTTPError: pass
        self.c.close()


class Session:
    def __init__(self, t): self.t, self.n = t, 0

    def request(self, method: str, params: Optional[dict] = None) -> Any:
        self.n += 1; rid = self.n
        self.t.send({"jsonrpc": "2.0", "id": rid, "method": method, **({"params": params} if params is not None else {})})
        msg = self.t.receive(rid)
        if "error" in msg:
            e = msg["error"] or {}
            raise McpError(f"{method}: {str(e.get('message') or e)[:300]}")
        return msg.get("result") or {}


@contextmanager
def session(spec: Dict[str, Any], timeout: float = 30) -> Iterator[Session]:
    """spec: {transport: stdio, command, args, env} | {transport: http, url, headers, pin?}."""
    t = _Stdio(spec, timeout) if spec.get("transport") == "stdio" else _Http(spec, timeout)
    try:
        s = Session(t)
        s.request("initialize", {"protocolVersion": PROTOCOL, "capabilities": {}, "clientInfo": CLIENT})
        t.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        yield s
    finally:
        t.close()


def list_tools(spec: Dict[str, Any], timeout: float = 30) -> List[Dict[str, Any]]:
    out, cursor = [], None
    with session(spec, timeout) as s:
        for _ in range(20):  # pagination, bounded
            res = s.request("tools/list", {"cursor": cursor} if cursor else {})
            out += [{"name": t.get("name"), "description": (t.get("description") or "")[:1000], "input_schema": t.get("inputSchema") or {}}
                    for t in res.get("tools") or [] if isinstance(t, dict) and t.get("name")]
            cursor = res.get("nextCursor")
            if not cursor: break
    return out


def result_value(res: Dict[str, Any]) -> Any:
    """structuredContent when present, else the text content (JSON-decoded when it is JSON), else the raw content list."""
    texts = [c.get("text", "") for c in res.get("content") or [] if isinstance(c, dict) and c.get("type") == "text"]
    if res.get("isError"): raise McpError(("\n".join(texts) or "tool reported an error")[:500], "MCP_TOOL_FAILED")
    if res.get("structuredContent") is not None: return res["structuredContent"]
    if texts and len(texts) == len(res.get("content") or []):
        joined = "\n".join(texts)
        try: return json.loads(joined)
        except ValueError: return joined
    return res.get("content") or []


def call_tool(spec: Dict[str, Any], name: str, arguments: Dict[str, Any], timeout: float = 30) -> Any:
    with session(spec, timeout) as s:
        return result_value(s.request("tools/call", {"name": name, "arguments": arguments}))
