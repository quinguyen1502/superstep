"""HTTP Tool SSRF guard, deterministic Condition matching, CORS origins, log redaction."""
import logging, socket
import httpx, pytest, respx
from app.core import config
from app.core.logging import RedactTokens
from app.engine.compiler import pick_branch
from app.engine.runtime import run_stream


def N(i, t, **d): return {"id": i, "type": t, "data": {"label": i, **d}}
def E(i, s, t, label=None): return {"id": i, "source": s, "target": t, **({"label": label} if label else {})}
def http_wf(url): return {"name": "t", "state": [{"name": "out", "type": "object"}],
                          "nodes": [N("s", "start"), N("h", "tool", mode="http", method="GET", url=url, output_field="out"), N("e", "end")],
                          "edges": [E("1", "s", "h"), E("2", "h", "e")]}
def resolve_to(monkeypatch, ip): monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))])


# ---------- HTTP Tool SSRF guard ----------
@pytest.mark.parametrize("url,ip", [("http://127.0.0.1:9/x", "127.0.0.1"), ("http://169.254.169.254/latest/meta-data", "169.254.169.254"),
                                    ("http://intranet.example/x", "10.0.0.5"), ("file:///etc/passwd", None), ("", None)])
def test_http_tool_refuses_non_public_targets(monkeypatch, url, ip):
    if ip: resolve_to(monkeypatch, ip)
    monkeypatch.setattr(httpx.Client, "send", lambda *a, **k: pytest.fail("no request may be sent"))
    w = http_wf(url)
    if not url: w["nodes"][1]["data"]["url"] = "{{state.out}}"  # renders empty at run time
    err = list(run_stream(w, {}))[-1]
    assert err["type"] == "error" and err["node"] == "h" and err["code"] == "HTTP_TOOL_URL_BLOCKED"
    assert "HTTP Tool node h" in err["errors"][0]


@respx.mock
def test_http_tool_calls_a_public_host_on_the_checked_ip(monkeypatch):
    resolve_to(monkeypatch, "93.184.216.34")
    route = respx.get("http://93.184.216.34/v1/status").mock(return_value=httpx.Response(200, json={"ok": True}))
    evs = list(run_stream(http_wf("http://api.example.com/v1/status"), {}))
    assert evs[-1]["type"] == "run_finished" and evs[-1]["state"]["out"] == {"ok": True}
    assert route.calls.last.request.headers["Host"] == "api.example.com"


@respx.mock
def test_http_tool_keeps_basic_auth_from_the_url(monkeypatch):
    resolve_to(monkeypatch, "93.184.216.34")
    route = respx.get("http://93.184.216.34/p").mock(return_value=httpx.Response(200, json=[]))
    list(run_stream(http_wf("http://bot:s%40cret@api.example.com/p"), {}))
    req = route.calls.last.request
    assert req.headers["Authorization"] == httpx.BasicAuth("bot", "s@cret")._auth_header and req.headers["Host"] == "api.example.com"


@respx.mock
def test_http_tool_does_not_follow_redirects(monkeypatch):
    resolve_to(monkeypatch, "93.184.216.34")
    respx.get("http://93.184.216.34/r").mock(return_value=httpx.Response(302, headers={"Location": "http://127.0.0.1/admin"}, text="moved"))
    inner = respx.get("http://127.0.0.1/admin").mock(return_value=httpx.Response(200, text="secret"))
    evs = list(run_stream(http_wf("http://api.example.com/r"), {}))
    assert evs[-1]["state"]["out"] == "moved" and not inner.called


@respx.mock
def test_http_tool_private_addresses_with_opt_in(monkeypatch):
    monkeypatch.setenv("STUDIO_HTTP_TOOL_ALLOW_PRIVATE", "1")
    respx.get("http://127.0.0.1:8080/x").mock(return_value=httpx.Response(200, text="local"))
    assert list(run_stream(http_wf("http://127.0.0.1:8080/x"), {}))[-1]["state"]["out"] == "local"


# ---------- Condition matching ----------
@pytest.mark.parametrize("labels", [["approve", "disapprove"], ["disapprove", "approve"]])
@pytest.mark.parametrize("value,expected", [("Disapprove.", "disapprove"), ("I approve", "approve"), ("APPROVE!", "approve"),
                                            ("I disapprove of this", "disapprove"), ("approved", None), ("", None)])
def test_condition_match_does_not_depend_on_label_order(labels, value, expected):
    assert pick_branch(value, labels) == expected


def test_condition_match_rules():
    assert pick_branch("order_status", ["general", "order_status"]) == "order_status"
    assert pick_branch("The intent is: order_status.", ["general", "order_status"]) == "order_status"
    assert pick_branch("generally fine", ["general", "order_status"]) is None   # not a whole word any more
    assert pick_branch("yes and no", ["yes", "no"]) == "yes"                     # the longest whole-word label wins
    assert pick_branch("ok or no", ["ok", "no"]) is None                         # two labels of the same length: ambiguous


def test_ambiguous_condition_value_uses_the_default():
    w = {"name": "t", "state": [{"name": "intent", "type": "string"}],
         "nodes": [N("s", "start"), N("c", "condition", field="intent", default="ok"), N("x", "end"), N("y", "end")],
         "edges": [E("1", "s", "c"), E("2", "c", "x", "ok"), E("3", "c", "y", "no")]}
    reached = [e["node"] for e in run_stream(w, {"intent": "ok or no"}) if e["type"] == "node_finished" and e["node"] in ("x", "y")]
    assert reached == ["x"]


# ---------- CORS origins and log redaction ----------
def test_cors_origins(monkeypatch):
    monkeypatch.delenv("STUDIO_CORS_ORIGINS", raising=False)
    monkeypatch.setattr(config, "IS_PROD", False); assert config.cors_origins() == ["*"]
    monkeypatch.setattr(config, "IS_PROD", True); assert config.cors_origins() == []
    monkeypatch.setenv("STUDIO_CORS_ORIGINS", "https://studio.example.com/, http://localhost:5173")
    assert config.cors_origins() == ["https://studio.example.com", "http://localhost:5173"]


def test_access_log_hides_websocket_tokens():
    rec = logging.LogRecord("uvicorn.error", logging.INFO, __file__, 1, '%s - "WebSocket %s" [accepted]',
                            ("127.0.0.1:5", "/ws/run?token=eyJhbGciOi.x.y&lang=vi"), None)
    RedactTokens().filter(rec)
    assert rec.getMessage() == '127.0.0.1:5 - "WebSocket /ws/run?token=***&lang=vi" [accepted]'
