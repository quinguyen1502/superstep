"""Tiny MCP server for tests and the e2e/demo stack (TASK-0013): stdio (default) or Streamable HTTP (`http PORT`).

Tools: add(a, b) -> structured {"sum"}, echo(text), env(name) -> value of an environment variable (sandbox checks),
fail() -> isError, slow(seconds). HTTP mode answers tools/call as an SSE stream to exercise that path."""
import json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOOLS = [
    {"name": "add", "description": "Add two integers", "inputSchema": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}, "required": ["a", "b"]}},
    {"name": "echo", "description": "Echo the text back", "inputSchema": {"type": "object", "properties": {"text": {"type": "string", "description": "Text to echo"}}, "required": ["text"]}},
    {"name": "env", "description": "Read an environment variable of the server process", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "fail", "description": "Always fails", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "slow", "description": "Sleep for some seconds", "inputSchema": {"type": "object", "properties": {"seconds": {"type": "number"}}}},
]


def handle(msg):
    m, p, rid = msg.get("method"), msg.get("params") or {}, msg.get("id")
    if rid is None: return None  # notification
    if m == "initialize":
        res = {"protocolVersion": p.get("protocolVersion"), "capabilities": {"tools": {}}, "serverInfo": {"name": "demo", "version": "1"}}
    elif m == "tools/list":
        res = {"tools": TOOLS}
    elif m == "tools/call":
        a, name = p.get("arguments") or {}, p.get("name")
        if name == "add": res = {"content": [{"type": "text", "text": str(a["a"] + a["b"])}], "structuredContent": {"sum": a["a"] + a["b"]}}
        elif name == "echo": res = {"content": [{"type": "text", "text": str(a.get("text"))}]}
        elif name == "env": res = {"content": [{"type": "text", "text": json.dumps(os.environ.get(a.get("name", "")))}]}
        elif name == "fail": res = {"content": [{"type": "text", "text": "boom"}], "isError": True}
        elif name == "slow": time.sleep(float(a.get("seconds", 1))); res = {"content": [{"type": "text", "text": "done"}]}
        else: return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": f"unknown tool {name}"}}
    else:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found"}}
    return {"jsonrpc": "2.0", "id": rid, "result": res}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):  # health for the e2e web server
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")

    def do_DELETE(self):
        self.send_response(200); self.end_headers()

    def do_POST(self):
        # read the body first, also for a 401: closing with it unread resets the connection, and the client may then
        # see a ReadError instead of the 401 (TASK-0130)
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if os.environ.get("MCP_REQUIRE_TOKEN") and self.headers.get("Authorization") != f"Bearer {os.environ['MCP_REQUIRE_TOKEN']}":
            self.send_response(401); self.end_headers(); return
        msg = json.loads(raw)
        out = handle(msg)
        if out is None:
            self.send_response(202); self.end_headers(); return
        sse = msg.get("method") == "tools/call"
        body = (f"event: message\ndata: {json.dumps(out)}\n\n" if sse else json.dumps(out)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream" if sse else "application/json")
        self.send_header("Mcp-Session-Id", "s-1"); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "http":
        ThreadingHTTPServer((os.environ.get("MCP_BIND", "127.0.0.1"), int(sys.argv[2])), H).serve_forever()
    else:
        for line in sys.stdin:
            if not line.strip(): continue
            out = handle(json.loads(line))
            if out is not None: sys.stdout.write(json.dumps(out) + "\n"); sys.stdout.flush()
