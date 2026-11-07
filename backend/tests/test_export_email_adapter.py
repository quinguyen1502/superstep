"""TASK-0271 (REQ-0089, DEC-0088): the exported Send email adapter, executed in Python (smtplib) and TypeScript (Deno,
nodemailer) against a local SMTP server (no external call). A node with an SMTP credential in the studio sends with
SMTP_* settings from the environment; one without makes a dry run, as in the studio."""
import base64, os, re, socketserver, subprocess, sys, threading, uuid
import pytest
from app.engine import python_export as X, typescript_export as T
from test_python_export import KEYS, N, E, F
from test_typescript_export import DENO, DENO_ARGS, deno_env  # noqa: F401

MAIL: list = []


class Smtp(socketserver.StreamRequestHandler):
    def handle(self):
        w = lambda s: (self.wfile.write((s + "\r\n").encode()), self.wfile.flush())  # noqa: E731
        w("220 test ESMTP")
        frm, rcpt, auth = None, [], None
        while True:
            line = self.rfile.readline()
            if not line: return
            cmd = line.decode().strip(); up = cmd.upper()
            if up.startswith("EHLO"): w("250-test"); w("250-AUTH PLAIN LOGIN"); w("250 8BITMIME")
            elif up.startswith("HELO"): w("250 test")
            elif up.startswith("AUTH PLAIN"):
                arg = cmd.split(" ", 2)[2] if cmd.count(" ") >= 2 else None
                if arg is None: w("334 "); arg = self.rfile.readline().decode().strip()
                auth = base64.b64decode(arg).split(b"\0")[1:]; w("235 ok")
            elif up.startswith("MAIL FROM"): frm = re.search(r"<(.*?)>", cmd).group(1); rcpt = []; w("250 ok")
            elif up.startswith("RCPT TO"): rcpt.append(re.search(r"<(.*?)>", cmd).group(1)); w("250 ok")
            elif up == "DATA":
                w("354 go"); data = []
                while (l := self.rfile.readline()) not in (b".\r\n", b".\n", b""): data.append(l)
                MAIL.append({"from": frm, "rcpt": rcpt, "auth": auth, "data": b"".join(data).decode()}); w("250 queued")
            elif up == "QUIT": w("221 bye"); return
            else: w("250 ok")


@pytest.fixture(scope="module")
def smtp():
    s = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Smtp); s.daemon_threads = True
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield s.server_address[1]
    s.shutdown()


def wf(sends=True, to="a@example.com"):
    data = dict(to=to, cc="c@example.com", bcc="hidden@example.com", subject="Hi {{state.message}}", body="Body {{state.message}}", output_field="mail")
    if sends: data["credential_id"] = "smtp-cred-secret-id"
    return {"name": "Mail", "state": [F("message"), F("mail", "object")],
            "nodes": [N("start", "start"), N("mail", "email", **data), N("end", "end")], "edges": [E("start", "mail"), E("mail", "end")]}


def base_env(env):
    return {k: v for k, v in env.items() if k not in KEYS and k != "PYTHONPATH" and not k.startswith(("SMTP_", "STUDIO_SMTP"))}


def run_py(tmp_path, graph, extra):
    code = X.to_python(graph, "Mail", 1, {}, {"input": {"message": "there"}}).code
    assert "smtp-cred-secret-id" not in code
    f = tmp_path / f"e_{uuid.uuid4().hex[:6]}.py"; f.write_text(code)
    return subprocess.run([sys.executable, "-I", str(f)], cwd=tmp_path, env={**base_env(os.environ), **extra}, capture_output=True, text=True,
                          timeout=120, stdin=subprocess.DEVNULL)


def run_ts(tmp_path, base, graph, extra):
    code = T.to_typescript(graph, "Mail", 1, {}, {"input": {"message": "there"}}).code
    assert "smtp-cred-secret-id" not in code
    f = tmp_path / f"e_{uuid.uuid4().hex[:6]}.ts"; f.write_text(code)
    return subprocess.run([DENO, "run", "-q", *DENO_ARGS, "--allow-env", "--allow-read", "--allow-sys", "--allow-net", str(f)], cwd=tmp_path,
                          env={**base_env(base), **extra}, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)


@pytest.fixture(params=["python", "typescript"])
def run(request):
    if request.param == "typescript":
        base = request.getfixturevalue("deno_env")
        return lambda tp, g, **e: run_ts(tp, base, g, e)
    return lambda tp, g, **e: run_py(tp, g, e)


def cfg(port, **more):
    return {"SMTP_HOST": "127.0.0.1", "SMTP_PORT": str(port), "SMTP_FROM": "bot@example.org", "SMTP_SECURITY": "none",
            "STUDIO_SMTP_ALLOW_PRIVATE": "1", "SMTP_USERNAME": "user", "SMTP_PASSWORD": "pw", "SUPERSTEP_RUN_ID": "r1", **more}


def test_configured_node_sends_once_with_bcc_only_in_the_envelope(tmp_path, smtp, run):
    MAIL.clear()
    for _ in range(2):
        p = run(tmp_path, wf(), **cfg(smtp))
        assert p.returncode == 0, p.stderr
        assert '"sent": true' in p.stdout.replace('"sent":true', '"sent": true')
    assert len(MAIL) == 2
    m = MAIL[0]
    assert m["from"] == "bot@example.org" and m["rcpt"] == ["a@example.com", "c@example.com", "hidden@example.com"]
    assert m["auth"] == [b"user", b"pw"] and "Subject: Hi there" in m["data"] and "Body there" in m["data"]
    assert "hidden@example.com" not in m["data"] and "Cc: c@example.com" in m["data"]
    ids = [re.search(r"Message-ID: (<[0-9a-f]{32}@example.org>)", x["data"], re.I).group(1) for x in MAIL]
    assert ids[0] == ids[1]  # same run and message: the same Message-ID, so a retried send is recognisable


def test_private_smtp_host_is_refused_by_default(tmp_path, smtp, run):
    MAIL.clear()
    p = run(tmp_path, wf(), **cfg(smtp, STUDIO_SMTP_ALLOW_PRIVATE=""))
    assert p.returncode != 0 and "STUDIO_SMTP_ALLOW_PRIVATE" in p.stderr and MAIL == []


def test_starttls_is_required_by_default(tmp_path, smtp, run):
    MAIL.clear()
    p = run(tmp_path, wf(), **cfg(smtp, SMTP_SECURITY=""))
    assert p.returncode != 0 and MAIL == [] and re.search(r"STARTTLS", p.stderr, re.I)


def test_unconfigured_offline_is_a_dry_run_and_live_is_refused(tmp_path, run):
    p = run(tmp_path, wf())
    assert p.returncode == 0 and "(offline mock) Send email" in p.stderr and "SMTP_HOST, SMTP_FROM not set" in p.stderr
    assert "(e-mail not sent)" in p.stdout
    p = run(tmp_path, wf(), LLM_PROVIDER="openai")
    assert p.returncode != 0 and "set SMTP_HOST, SMTP_FROM" in p.stderr


def test_a_node_without_a_studio_credential_never_sends(tmp_path, smtp, run):
    MAIL.clear()
    p = run(tmp_path, wf(sends=False), LLM_PROVIDER="openai", **cfg(smtp))
    assert p.returncode == 0 and MAIL == [] and "no SMTP credential on this node" in p.stderr


def test_an_invalid_recipient_stops_the_run(tmp_path, smtp, run):
    MAIL.clear()
    p = run(tmp_path, wf(to="not-an-address"), **cfg(smtp))
    assert p.returncode != 0 and "not an e-mail address" in p.stderr and MAIL == []
