"""TASK-0267 (REQ-0089, DEC-0088): exported HTTP Tool requests connect to the address they checked, as the studio does
(core/net.py). Executed in Python and in TypeScript (Deno) against local servers, with the name resolver replaced in
the generated program's own process: a DNS rebind after the check cannot move the request, the Host header keeps
the name, and HTTPS keeps SNI and the certificate check on the name (not the IP)."""
import json, os, subprocess, sys, threading, uuid, ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from app.engine import python_export as X, typescript_export as T
from test_python_export import KEYS, N, E, F
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401


def make_server(label, ip="127.0.0.1", context=None):
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append({"host": self.headers.get("Host"), "sni": getattr(self.connection, "sni", None)})
            body = json.dumps({"server": label}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self, *a): pass

    s = ThreadingHTTPServer((ip, 0), Handler)
    if context is not None:
        s.socket = context.wrap_socket(s.socket, server_side=True)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, seen


@pytest.fixture(scope="module")
def certs(tmp_path_factory):
    d = tmp_path_factory.mktemp("tls")
    run = lambda *a: subprocess.run(["openssl", *a], cwd=d, check=True, capture_output=True)
    run("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2", "-subj", "/CN=Test CA", "-keyout", "ca.key", "-out", "ca.pem",
        "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign")
    run("req", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=pinned.test", "-keyout", "srv.key", "-out", "srv.csr")
    (d / "ext.cnf").write_text("subjectAltName=DNS:pinned.test\n")
    run("x509", "-req", "-in", "srv.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-CAcreateserial", "-days", "2", "-out", "srv.pem",
        "-extfile", "ext.cnf")
    return d


def wf(url):
    return {"name": "Http", "state": [F("message"), F("res", "object")],
            "nodes": [N("start", "start"), N("call", "tool", mode="http", method="GET", url=url, body="", output_field="res"), N("end", "end")],
            "edges": [E("start", "call"), E("call", "end")]}


# The resolver answers 127.0.0.1 the first time and 127.0.0.2 afterwards (a rebind); the log records each lookup.
PY_RESOLVER = '''
import socket, sys, runpy
real, calls = socket.getaddrinfo, []
def fake(host, *a, **k):
    if host == "pinned.test":
        calls.append(host)
        ip = "127.0.0.1" if len(calls) == 1 else "127.0.0.2"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, a[0] if a else 0))]
    return real(host, *a, **k)
socket.getaddrinfo = fake
try:
    runpy.run_path(sys.argv[1], run_name="__main__")
finally:
    print(f"lookups={len(calls)}", file=sys.stderr)
'''

TS_RESOLVER = '''
import dns from "node:dns";
let calls = 0;
const answer = () => { console.error(`lookups=${++calls}`); return calls === 1 ? "127.0.0.1" : "127.0.0.2"; };
const real = dns.promises.lookup.bind(dns.promises);
(dns.promises as unknown as Record<string, unknown>).lookup = (host: string, options?: { all?: boolean }) => {
  if (host !== "pinned.test") return real(host, options as never);
  const ip = answer();
  return Promise.resolve(options?.all ? [{ address: ip, family: 4 }] : { address: ip, family: 4 });
};
const realCb = dns.lookup;
(dns as unknown as Record<string, unknown>).lookup = (host: string, options: unknown, done?: unknown) => {
  if (host !== "pinned.test") return (realCb as (...a: unknown[]) => void)(host, options, done);
  const cb = (typeof options === "function" ? options : done) as (...a: unknown[]) => void;
  const ip = answer();
  (options as { all?: boolean })?.all ? cb(null, [{ address: ip, family: 4 }]) : cb(null, ip, 4);
};
'''


def run_py(tmp_path, graph, extra_env, allow):
    f = tmp_path / f"h_{uuid.uuid4().hex[:6]}.py"; f.write_text(X.to_python(graph, "Http", 1, {}, {"input": {"message": "x"}}).code)
    w = tmp_path / "resolver.py"; w.write_text(PY_RESOLVER)
    env = {k: v for k, v in os.environ.items() if k not in KEYS and k not in ("PYTHONPATH", "STUDIO_HTTP_TOOL_ALLOW_PRIVATE")}
    env.update(SUPERSTEP_RUN_ID="r1", **({"STUDIO_HTTP_TOOL_ALLOW_PRIVATE": "1"} if allow else {}), **extra_env)
    return subprocess.run([sys.executable, "-I", str(w), str(f)], cwd=tmp_path, env=env, capture_output=True, text=True,
                          timeout=120, stdin=subprocess.DEVNULL)


def run_ts(tmp_path, base, graph, extra_env, allow):
    f = tmp_path / f"h_{uuid.uuid4().hex[:6]}.ts"; f.write_text(T.to_typescript(graph, "Http", 1, {}, {"input": {"message": "x"}}).code)
    w = tmp_path / "resolver.ts"; w.write_text(TS_RESOLVER)
    env = {k: v for k, v in base.items() if k not in ("LLM_PROVIDER", "STUDIO_HTTP_TOOL_ALLOW_PRIVATE")}
    env.update(SUPERSTEP_RUN_ID="r1", **({"STUDIO_HTTP_TOOL_ALLOW_PRIVATE": "1"} if allow else {}), **extra_env)
    return subprocess.run([DENO, "run", "-q", *DENO_ARGS, "--allow-env", "--allow-read", "--allow-sys", "--allow-net",
                           "--preload", str(w), str(f)], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=180,
                          stdin=subprocess.DEVNULL)


@pytest.fixture(params=["python", "typescript"])
def runner(request):
    if request.param == "typescript":
        base = request.getfixturevalue("deno_env")
        return lambda tp, g, ca=None, allow=True: run_ts(tp, base, g, {"DENO_CERT": str(ca)} if ca else {}, allow)
    return lambda tp, g, ca=None, allow=True: run_py(tp, g, {"SSL_CERT_FILE": str(ca)} if ca else {}, allow)


def test_a_rebind_after_the_check_cannot_move_the_request(tmp_path, runner):
    good, seen_good = make_server("checked")
    port = good.server_address[1]
    seen_evil = []
    try:  # the rebound address listens on the same port: a second lookup would reach it
        evil = ThreadingHTTPServer(("127.0.0.2", port), type("H", (BaseHTTPRequestHandler,), {
            "do_GET": lambda self: (seen_evil.append(self.path), self.send_response(500), self.end_headers()),
            "log_message": lambda self, *a: None}))
    except OSError:
        good.shutdown(); pytest.skip("127.0.0.2 is not available here")
    threading.Thread(target=evil.serve_forever, daemon=True).start()
    try:
        p = runner(tmp_path, wf(f"http://pinned.test:{port}/ok"))
        assert p.returncode == 0, p.stderr
        assert '"checked"' in p.stdout and seen_evil == []
        assert seen_good == [{"host": f"pinned.test:{port}", "sni": None}]
        assert "lookups=1" in p.stderr and "lookups=2" not in p.stderr  # resolved once: the request reused the checked address
    finally:
        good.shutdown(); evil.shutdown()


def tls_context(certs):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certs / "srv.pem", certs / "srv.key")
    names = []
    ctx.sni_callback = lambda sock, name, c: (names.append(name), setattr(sock, "sni", name)) and None
    return ctx, names


def test_https_keeps_sni_and_the_certificate_name(tmp_path, runner, certs):
    ctx, names = tls_context(certs)
    s, seen = make_server("tls", context=ctx)
    try:
        port = s.server_address[1]
        p = runner(tmp_path, wf(f"https://pinned.test:{port}/ok"), ca=certs / "ca.pem")
        assert p.returncode == 0, p.stderr
        assert '"tls"' in p.stdout and set(names) == {"pinned.test"} and seen[0]["host"] == f"pinned.test:{port}"
    finally:
        s.shutdown()


def test_https_refuses_a_certificate_for_another_name(tmp_path, runner, certs):
    ctx, _ = tls_context(certs)
    s, seen = make_server("tls", context=ctx)
    try:
        p = runner(tmp_path, wf(f"https://127.0.0.1:{s.server_address[1]}/ok"), ca=certs / "ca.pem")
        assert p.returncode != 0 and seen == []
    finally:
        s.shutdown()


def test_a_private_answer_is_refused_without_the_opt_in(tmp_path, runner):
    p = runner(tmp_path, wf("http://pinned.test:9/ok"), allow=False)
    assert p.returncode != 0 and "STUDIO_HTTP_TOOL_ALLOW_PRIVATE" in p.stderr and "lookups=1" in p.stderr and "lookups=2" not in p.stderr
