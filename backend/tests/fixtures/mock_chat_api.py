"""Fake Slack + Telegram Web APIs and a Teams webhook (/teams/…, TASK-0047) for the e2e suite (TASK-0022). Records every call; GET /_messages lists them.

Run: python mock_chat_api.py [port]  (default 8111). Point SLACK_API_URL=http://127.0.0.1:8111/slack and
TELEGRAM_API_URL=http://127.0.0.1:8111/telegram at it. A bot token xoxb-<n>-<TEAM>-... answers auth.test with team <TEAM>.
Also fakes LLM providers (TASK-0030): /ollama (Ollama API: tags, streamed chat, embed), /lmstudio/v1 (OpenAI-compatible), /openrouter/api/v1 (key sk-or-good).
"""
import json, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CALLS: list[dict] = []
OLLAMA_MODELS = ["llama3.2:latest", "qwen2.5:7b"]
STREAM_DELAY = 0.4


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, data, status=200):
        b = json.dumps(data).encode(); self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if self.path.startswith("/_messages"): return self._send(CALLS)
        if self.path.startswith("/health"): return self._send({"ok": True})
        if self.path == "/ollama/api/tags": return self._send({"models": [{"name": m, "model": m} for m in OLLAMA_MODELS]})
        if self.path == "/lmstudio/v1/models": return self._send({"object": "list", "data": [{"id": "qwen2.5-7b-instruct", "object": "model"}]})
        if self.path == "/openrouter/api/v1/models":
            if self.headers.get("Authorization") != "Bearer sk-or-good": return self._send({"error": {"message": "No auth credentials found", "code": 401}}, 401)
            return self._send({"data": [{"id": "openrouter/auto"}, {"id": "meta-llama/llama-3.1-8b-instruct"}]})
        self._send({"ok": False}, 404)

    def do_DELETE(self):
        CALLS.clear(); self._send({"ok": True})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); raw = self.rfile.read(n) if n else b"{}"
        try: body = json.loads(raw or b"{}")
        except ValueError: body = {}
        method = self.path.rstrip("/").rsplit("/", 1)[-1]; auth = self.headers.get("Authorization", "")
        CALLS.append({"path": self.path, "method": method, "body": body, "at": time.time()})
        if self.path == "/ollama/api/chat":
            if body.get("model") not in OLLAMA_MODELS: return self._send({"error": f"model '{body.get('model')}' not found"}, 404)
            classify = "classify" in json.dumps(body).lower()
            judge = "<request>" in json.dumps(body)  # the AI review judge of an approval (TASK-0189): a fixed, confident verdict
            if judge: classify = True
            parts = [json.dumps({"decision": "approve", "confidence": 0.92, "reason": "A small refund for an existing order.", "flags": []})] if judge \
                else ["order_status"] if classify else [f"[ollama:{body['model']}] ", "xin ", "chào, ", "đây ", "là ", "câu ", "trả ", "lời ", "từng ", "phần."]
            self.send_response(200); self.send_header("Content-Type", "application/x-ndjson"); self.end_headers()  # HTTP/1.0: body ends at close
            for p in parts + [""]:
                last = p == ""
                row = {"model": body["model"], "created_at": "2026-01-01T00:00:00Z", "message": {"role": "assistant", "content": p}, "done": last,
                       **({"done_reason": "stop", "prompt_eval_count": 5, "eval_count": 3} if last else {})}
                self.wfile.write(json.dumps(row).encode() + b"\n"); self.wfile.flush()
                if not classify and not last: time.sleep(STREAM_DELAY)  # slow enough for the e2e to see the live trace
            return
        if self.path == "/ollama/api/embed":  # deterministic 8-dim vectors (letter histogram) for any *embed* model
            if "embed" not in str(body.get("model")): return self._send({"error": f"model '{body.get('model')}' not found"}, 404)
            vec = lambda t: [sum(t.lower().count(ch) for ch in g) + 0.01 for g in ("ae", "io", "u", "nm", "rs", "tl", "cdg", "hy")]
            return self._send({"model": body["model"], "embeddings": [vec(t) for t in body.get("input") or []]})
        if self.path.startswith("/slack/"):
            if method == "auth.test":
                parts = auth.removeprefix("Bearer ").split("-")
                team = parts[2] if len(parts) > 3 else "T0E2E"
                return self._send({"ok": True, "team": f"Workspace {team}", "team_id": team, "user_id": "UBOT", "bot_id": "BBOT"})
            if method == "chat.postMessage": return self._send({"ok": True, "channel": body.get("channel"), "ts": f"{time.time():.6f}"})
            return self._send({"ok": True})
        if self.path.startswith("/teams/"): return self._send({"ok": True}, 202)  # a Teams Workflows webhook (TASK-0047)
        if self.path.startswith("/telegram/"):
            if method == "getMe": return self._send({"ok": True, "result": {"id": 1, "is_bot": True, "username": "studio_e2e_bot", "first_name": "Studio"}})
            if method == "sendMessage": return self._send({"ok": True, "result": {"message_id": len(CALLS), "chat": {"id": body.get("chat_id")}}})
            return self._send({"ok": True, "result": True})
        self._send({"ok": False, "error": "unknown"}, 404)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8111
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
