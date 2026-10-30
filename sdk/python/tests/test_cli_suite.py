"""`test` writes JUnit and exits non-zero when a suite fails (TASK-0170)."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx
import pytest

from superstep.cli import run

TOKEN = "pat_secret-token"
REASON = "because & <tag>"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("SUPERSTEP_URL", raising=False)
    monkeypatch.delenv("SUPERSTEP_TOKEN", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".superstep"
    config.mkdir()
    (config / "cli.json").write_text(json.dumps({
        "url": "http://studio.example",
        "token": TOKEN,
        "account": "ada@example.com",
    }), encoding="utf-8")
    return tmp_path


def invoke(argv, client=None):
    from contextlib import redirect_stderr, redirect_stdout
    import io
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv, client=client)
    return code, out.getvalue(), err.getvalue()


def envelope(data, status=200):
    if status >= 400:
        error = data if isinstance(data, dict) else {"code": "BAD", "message": "no"}
        return httpx.Response(status, json={"success": False, "data": None, "error": error})
    return httpx.Response(status, json={"success": True, "data": data, "error": None})


def result(name, status, reason=None, checks=None):
    return {
        "id": "r-" + name, "test_id": "t-" + name, "name": name, "status": status, "run_id": "run",
        "version": 1, "reason": reason, "detail": None, "ended": 2, "change": None,
        "checks": [] if checks is None else checks,
    }


def suite(sid, wid, status, results, failed=None):
    if failed is None:
        failed = sum(1 for row in results if row["status"] == "failed")
    return {
        "id": sid, "workflow_id": wid, "version": 1, "status": status, "mock": False, "total": len(results),
        "passed": sum(1 for row in results if row["status"] == "passed"), "failed": failed, "started": 1,
        "ended": None if status == "running" else 2, "by": "ada@example.com", "langsmith_url": None, "results": results,
    }


class Script:
    """POST returns a running suite. The following GET returns the finished one."""

    def __init__(self, rows, cases, finish, stay_running=False):
        self.rows = rows
        self.cases = cases
        self.finish = finish
        self.stay_running = stay_running
        self.bodies = []
        self.posts = []
        self.gets = []
        self.client = httpx.Client(transport=httpx.MockTransport(self))

    def __call__(self, request: httpx.Request):
        if request.headers.get("authorization") != "Bearer " + TOKEN:
            return envelope({"code": "AUTH_TOKEN_INVALID", "message": "no"}, status=401)
        path = request.url.path
        bits = path.strip("/").split("/")
        if path == "/api/workflows" and request.method == "GET":
            return envelope(self.rows)
        if len(bits) == 4 and bits[0:2] == ["api", "workflows"] and bits[3] == "tests" and request.method == "GET":
            return envelope({"items": self.cases.get(bits[2], [])})
        if bits[-2:] == ["tests", "run"] and request.method == "POST":
            wid = bits[2]
            self.bodies.append(json.loads(request.content.decode() or "{}"))
            self.posts.append(wid)
            done = self.finish[wid]
            return envelope(suite(done["id"], wid, "running", []))
        if "runs" in bits and request.method == "GET":
            wid = bits[2]
            self.gets.append(wid)
            if self.stay_running:
                return envelope(suite(self.finish[wid]["id"], wid, "running", []))
            return envelope(self.finish[wid])
        if path == "/api/health":
            return envelope({"version": "0.9.0"})
        return envelope({"code": "NOT_FOUND", "message": "no"}, status=404)


def open_xml(path: Path):
    root = ET.parse(path).getroot()
    assert root.tag == "testsuites"
    return root


def test_done_with_no_failures_exits_zero(isolated):
    script = Script(
        [{"id": "w1", "name": "Support"}],
        {"w1": [{"id": "t1", "name": "greets"}]},
        {"w1": suite("s1", "w1", "done", [result("greets", "passed")])},
    )
    code, out, err = invoke(["test", "Support"], client=script.client)
    assert code == 0 and out == ""
    assert script.gets == ["w1"] and script.bodies == [{}]
    assert TOKEN not in err
    root = open_xml(isolated / "superstep-junit.xml")
    cases = list(root.iter("testcase"))
    assert len(list(root.iter("testsuite"))) == 1
    assert len(cases) == 1 and cases[0].get("name") == "greets" and cases[0].find("failure") is None
    assert "Case greets on Support is passed." in err


def test_failed_case_exits_one_and_junit_includes_the_reason(isolated):
    script = Script(
        [{"id": "w1", "name": "Support"}],
        {"w1": [{"id": "t1", "name": "greets"}]},
        {"w1": suite("s1", "w1", "done", [result("greets", "failed", reason=REASON, checks=[])])},
    )
    code, out, err = invoke(["test", "Support"], client=script.client)
    assert code == 1 and out == ""
    path = isolated / "superstep-junit.xml"
    raw = path.read_text(encoding="utf-8")
    failure = open_xml(path).find(".//failure")
    assert failure is not None and REASON in (failure.text or "")
    assert failure.get("message") == "failed"
    assert "&amp;" in raw and "&lt;" in raw and "&gt;" in raw and "<tag>" not in raw
    assert TOKEN not in raw and TOKEN not in err


def test_cancelled_suite_exits_one(isolated):
    script = Script(
        [{"id": "w1", "name": "Support"}],
        {"w1": [{"id": "t1", "name": "greets"}]},
        {"w1": suite("s1", "w1", "cancelled", [result("greets", "cancelled")], failed=0)},
    )
    code, _out, _err = invoke(["test", "Support"], client=script.client)
    assert code == 1
    case = open_xml(isolated / "superstep-junit.xml").find(".//testcase")
    assert case is not None and case.get("name") == "greets"


def test_junit_flag_writes_that_path_only(isolated):
    script = Script(
        [{"id": "w1", "name": "Support"}],
        {"w1": [{"id": "t1", "name": "greets"}]},
        {"w1": suite("s1", "w1", "done", [result("greets", "passed")])},
    )
    code, _out, _err = invoke(["test", "w1", "--junit", "out.xml"], client=script.client)
    assert code == 0
    assert (isolated / "out.xml").is_file()
    assert not (isolated / "superstep-junit.xml").exists()
    assert open_xml(isolated / "out.xml").find(".//testcase").get("name") == "greets"


def test_mock_is_the_only_request_that_sends_mock_true(isolated):
    def make():
        return Script(
            [{"id": "w1", "name": "Support"}],
            {"w1": [{"id": "t1", "name": "greets"}]},
            {"w1": suite("s1", "w1", "done", [result("greets", "passed")])},
        )
    plain, mocked = make(), make()
    assert invoke(["test", "Support"], client=plain.client)[0] == 0
    assert invoke(["test", "Support", "--mock"], client=mocked.client)[0] == 0
    assert plain.bodies == [{}]
    assert mocked.bodies == [{"mock": True}]
    assert all(body.get("mock") is not True for body in plain.bodies)


def test_all_runs_suites_with_tests_skips_empty_and_does_not_stop(isolated):
    script = Script(
        [{"id": "a", "name": "Alpha"}, {"id": "b", "name": "Beta"}, {"id": "c", "name": "Gamma"}],
        {"a": [{"id": "t1"}], "b": [], "c": [{"id": "t2"}]},
        {
            "a": suite("sa", "a", "done", [result("one", "failed", reason=REASON)], failed=1),
            "c": suite("sc", "c", "done", [result("two", "passed")], failed=0),
        },
    )
    code, out, err = invoke(["test", "--all"], client=script.client)
    assert code == 1 and out == ""
    assert script.posts == ["a", "c"]
    assert "Skipping Beta: no tests." in err
    root = open_xml(isolated / "superstep-junit.xml")
    suites = list(root.iter("testsuite"))
    assert [item.get("name") for item in suites] == ["Alpha", "Gamma"]
    failure = root.find(".//failure")
    assert failure is not None and REASON in (failure.text or "")
    passed = [item for item in root.iter("testcase") if item.get("name") == "two"]
    assert passed and passed[0].find("failure") is None


def test_all_with_no_tests_is_no_tests_and_writes_no_file(isolated):
    script = Script(
        [{"id": "a", "name": "Alpha"}, {"id": "b", "name": "Beta"}],
        {"a": [], "b": []},
        {},
    )
    code, out, err = invoke(["test", "--all", "--json"], client=script.client)
    body = json.loads(out)
    assert code != 0 and body["ok"] is False and body["error"]["code"] == "NO_TESTS"
    assert "Skipping Alpha: no tests." in err and "Skipping Beta: no tests." in err
    assert not (isolated / "superstep-junit.xml").exists()
    assert script.posts == []


def test_help_includes_an_example():
    code, out, err = invoke(["test", "--help"])
    assert code == 0 and out == ""
    assert "Example: superstep test Support --junit out.xml" in err
    code, out, err = invoke(["--lang", "vi", "test", "--help"])
    assert code == 0 and out == ""
    assert "Ví dụ: superstep test Support --junit out.xml" in err


def test_json_stdout_is_one_object_and_file_is_written(isolated):
    script = Script(
        [{"id": "w1", "name": "Support"}],
        {"w1": [{"id": "t1", "name": "greets"}]},
        {"w1": suite("s1", "w1", "done", [result("greets", "failed", reason=REASON)], failed=1)},
    )
    code, out, err = invoke(["test", "Support", "--json"], client=script.client)
    body = json.loads(out)
    assert code == 1 and set(body) == {"ok", "suites"} and body["ok"] is False
    assert body["suites"][0]["status"] == "done" and body["suites"][0]["failed"] == 1
    assert "<?xml" not in out and "<testsuite" not in out and "<testcase" not in out
    raw = (isolated / "superstep-junit.xml").read_text(encoding="utf-8")
    assert "<testsuite" in raw and REASON in (open_xml(isolated / "superstep-junit.xml").find(".//failure").text or "")
    assert TOKEN not in out and TOKEN not in err and TOKEN not in raw


def test_summary_lines_follow_the_selected_language(isolated):
    def script():
        return Script(
            [{"id": "w1", "name": "Support"}, {"id": "w2", "name": "Empty"}],
            {"w1": [{"id": "t1"}], "w2": []},
            {"w1": suite("s1", "w1", "done", [result("greets", "passed")])},
        )
    code, _out, err = invoke(["test", "--all"], client=script().client)
    assert code == 0
    assert "Case greets on Support is passed." in err
    assert "Skipping Empty: no tests." in err
    code, _out, err = invoke(["--lang", "vi", "test", "--all"], client=script().client)
    assert code == 0
    assert "Ca greets của Support là passed." in err
    assert "Bỏ qua Empty: không có bài kiểm tra." in err
    assert "Case greets on Support is passed." not in err
    assert "Skipping Empty: no tests." not in err


def test_two_names_are_ambiguous_and_a_missing_name_is_not_found(isolated):
    ambiguous = Script(
        [{"id": "a", "name": "Support"}, {"id": "b", "name": "Support"}],
        {},
        {},
    )
    code, out, _err = invoke(["test", "Support", "--json"], client=ambiguous.client)
    body = json.loads(out)
    assert code != 0 and body["error"]["code"] == "AMBIGUOUS" and "Pass the id" in body["error"]["message"]
    assert not (isolated / "superstep-junit.xml").exists()
    assert ambiguous.posts == []
    missing = Script([{"id": "a", "name": "Other"}], {}, {})
    code, out, _err = invoke(["test", "Missing", "--json"], client=missing.client)
    assert code != 0 and json.loads(out)["error"]["code"] == "WORKFLOW_NOT_FOUND"
    assert missing.posts == []


def test_still_running_at_timeout_exits_one(isolated):
    script = Script(
        [{"id": "w1", "name": "Support"}],
        {"w1": [{"id": "t1"}]},
        {"w1": suite("s1", "w1", "running", [])},
        stay_running=True,
    )
    code, _out, err = invoke(["test", "Support", "--timeout", "0"], client=script.client)
    assert code == 1 and script.gets == []
    assert "Suite Support was still running after 0 seconds." in err
    assert (isolated / "superstep-junit.xml").is_file()
    open_xml(isolated / "superstep-junit.xml")


def test_missing_route_is_server_too_old(isolated):
    def handler(request: httpx.Request):
        if request.url.path == "/api/health":
            return envelope({"version": "0.9.0"})
        if request.url.path == "/api/workflows":
            return envelope([{"id": "w1", "name": "Support"}])
        return envelope({"code": "NOT_FOUND", "message": "no"}, status=404)

    code, out, _err = invoke(["test", "Support", "--json"], client=httpx.Client(transport=httpx.MockTransport(handler)))
    body = json.loads(out)
    assert code == 1 and body["error"]["code"] == "SERVER_TOO_OLD" and "0.9.0" in body["error"]["message"]
    assert not (isolated / "superstep-junit.xml").exists()
