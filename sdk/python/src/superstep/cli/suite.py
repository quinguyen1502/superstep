"""`test` runs workflow suites and writes JUnit XML (TASK-0170, DEC-0071)."""
from __future__ import annotations

import argparse
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import httpx

from superstep.cli.i18n import Catalog
from superstep.cli.session import SessionError, call, resolve_target

_DEFAULT_JUNIT = "superstep-junit.xml"
_DEFAULT_TIMEOUT = 300.0
_POLL_SECONDS = 0.05
# Non-404 codes from the suite routes. A 404 is SERVER_TOO_OLD when phase2 is set, before this map is consulted.
_ERRORS = {
    "WORKFLOW_NOT_FOUND": "error.workflow_not_found",
    "WORKFLOW_FORBIDDEN": "error.workflow_forbidden",
    "TEST_NOT_FOUND": "error.test_not_found",
    "TEST_SUITE_NOT_FOUND": "error.suite_not_found",
    "TEST_SUITE_RUNNING": "error.suite_running",
}


def add_commands(commands, common, catalog: Catalog) -> None:
    test = _parser(commands, common, catalog, "test", "help.test", "example.test")
    test.add_argument("workflow", nargs="?", help=catalog.format("help.test_workflow"))
    test.add_argument("--all", action="store_true", help=catalog.format("help.all"))
    test.add_argument("--mock", action="store_true", help=catalog.format("help.mock"))
    test.add_argument("--junit", help=catalog.format("help.junit"))
    test.add_argument("--timeout", type=float, default=_DEFAULT_TIMEOUT, help=catalog.format("help.suite_timeout"))
    test.add_argument("--url", help=catalog.format("help.url"))
    test.set_defaults(run=cmd_test)


def cmd_test(args, catalog: Catalog, json_mode: bool, client: Optional[httpx.Client], _parser, _docker) -> int:
    try:
        if bool(args.workflow) == bool(args.all):
            raise SessionError("USAGE", "error.test_target")
        url, token = resolve_target(getattr(args, "url", None))
        if not url:
            raise SessionError("URL_REQUIRED", "error.url_required")
        if not token:
            raise SessionError("AUTH_REQUIRED", "error.login_required")
        rows = _api("GET", url, "/api/workflows", client, token)
        selected = _select(rows, args.workflow, bool(args.all), url)
        ran: list[tuple[dict, dict]] = []
        timed_out = False
        for workflow in selected:
            cases = _cases(url, client, token, str(workflow["id"]))
            # An empty suite POST is 404 TEST_NOT_FOUND, which phase2 would report as SERVER_TOO_OLD.
            if not cases:
                if args.all:
                    _say(catalog, "test.skip", name=str(workflow.get("name") or workflow["id"]))
                continue
            suite, hit = _run(url, client, token, str(workflow["id"]), bool(args.mock), float(args.timeout))
            timed_out = timed_out or hit
            for result in _results(suite):
                _say(catalog, "test.summary", workflow=str(workflow.get("name") or workflow["id"]),
                     name=str(result.get("name") or ""), status=str(result.get("status") or ""))
            if hit:
                _say(catalog, "test.timeout", name=str(workflow.get("name") or workflow["id"]), seconds=_seconds(float(args.timeout)))
            ran.append((workflow, suite))
        if not ran:
            raise SessionError("NO_TESTS", "error.no_tests")
        _write_junit(_junit_path(args), ran)
    except SessionError as exc:
        return _fail(json_mode, catalog, exc.code, exc.key, **exc.fmt)
    ok = _ok(ran, timed_out)
    if json_mode:
        _write_json({"ok": ok, "suites": [suite for _workflow, suite in ran]})
    return 0 if ok else 1


def _select(rows, workflow: Optional[str], all_: bool, url: str) -> list[dict]:
    if not isinstance(rows, list):
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
    found = [row for row in rows if isinstance(row, dict) and row.get("id")]
    if all_:
        return found
    return [_lookup(found, workflow or "")]


def _lookup(rows: list[dict], query: str) -> dict:
    """An id, or an exact name. Two exact names is AMBIGUOUS. Zero matches is the server not-found code."""
    by_id = [row for row in rows if row.get("id") == query]
    if len(by_id) > 1:
        raise SessionError("AMBIGUOUS", "error.ambiguous", name=query)
    if len(by_id) == 1:
        return by_id[0]
    by_name = [row for row in rows if row.get("name") == query]
    if len(by_name) > 1:
        raise SessionError("AMBIGUOUS", "error.ambiguous", name=query)
    if len(by_name) == 1:
        return by_name[0]
    raise SessionError("WORKFLOW_NOT_FOUND", "error.workflow_not_found")


def _cases(url: str, client: Optional[httpx.Client], token: str, wid: str) -> list:
    data = _api("GET", url, _workflow(wid, "/tests"), client, token, phase2=True)
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
    return data["items"]


def _run(url: str, client: Optional[httpx.Client], token: str, wid: str, mock: bool, timeout: float) -> tuple[dict, bool]:
    body = {"mock": True} if mock else {}
    suite = _suite(_api("POST", url, _workflow(wid, "/tests/run"), client, token, body=body, phase2=True), url)
    deadline = time.monotonic() + max(0.0, timeout)
    while suite.get("status") == "running":
        if time.monotonic() >= deadline:
            return suite, True
        time.sleep(min(_POLL_SECONDS, max(0.0, deadline - time.monotonic())))
        suite = _suite(_api("GET", url, _workflow(wid, "/tests/runs/" + quote(str(suite["id"]), safe="")), client, token, phase2=True), url)
    return suite, False


def _suite(data, url: str) -> dict:
    if not isinstance(data, dict) or not data.get("id") or "status" not in data:
        raise SessionError("BAD_RESPONSE", "error.bad_response", url=url)
    return data


def _results(suite: dict) -> list[dict]:
    rows = suite.get("results") or []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _ok(ran: list[tuple[dict, dict]], timed_out: bool) -> bool:
    if timed_out:
        return False
    return all(suite.get("status") == "done" and suite.get("failed") == 0 for _workflow, suite in ran)


def _write_junit(path: Path, ran: list[tuple[dict, dict]]) -> None:
    root = ET.Element("testsuites")
    for workflow, suite in ran:
        results = _results(suite)
        name = str(workflow.get("name") or workflow.get("id") or "")
        failures = sum(1 for result in results if result.get("status") == "failed")
        testsuite = ET.SubElement(root, "testsuite", {
            "name": name,
            "tests": str(len(results)),
            "failures": str(failures),
            "id": str(suite.get("workflow_id") or workflow.get("id") or ""),
        })
        for result in results:
            case = ET.SubElement(testsuite, "testcase", {"name": str(result.get("name") or ""), "classname": name})
            if result.get("status") != "failed":
                continue
            checks = result.get("checks") if isinstance(result.get("checks"), list) else []
            status = str(result.get("status") or "")
            # No check rows: the failure message is the case status, not a missing check reason.
            failure = ET.SubElement(case, "failure", {"message": status})
            reason = result.get("reason")
            if reason:
                failure.text = str(reason)
            elif not checks:
                failure.text = status
    ET.ElementTree(root).write(path, encoding="unicode", xml_declaration=True)


def _junit_path(args) -> Path:
    return Path(args.junit) if args.junit else Path(_DEFAULT_JUNIT)


def _workflow(wid: str, suffix: str) -> str:
    return "/api/workflows/" + quote(str(wid), safe="") + suffix


def _api(method: str, url: str, path: str, client: Optional[httpx.Client], token: str, body: Optional[dict] = None, phase2: bool = False):
    return call(method, url, path, client=client, token=token, body=body, phase2=phase2, errors=_ERRORS)


def _seconds(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return str(value)


def _say(catalog: Catalog, key: str, **fmt: str) -> None:
    sys.stderr.write(catalog.format(key, **fmt) + "\n")


def _fail(json_mode: bool, catalog: Catalog, code: str, key: str, **fmt: str) -> int:
    from superstep.cli.install import _fail as fail
    return fail(json_mode, catalog, code, key, **fmt)


def _write_json(payload: dict) -> None:
    from superstep.cli import _write_json as write
    write(payload)


def _parser(commands, common, catalog: Catalog, name: str, help_key: str, example_key: str):
    return commands.add_parser(
        name,
        parents=[common],
        help=catalog.format(help_key),
        description=catalog.format(help_key),
        epilog=catalog.format(example_key),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
