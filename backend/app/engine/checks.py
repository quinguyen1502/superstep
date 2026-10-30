"""Checks of a workflow test case (TASK-0067, REQ-0042): what a finished test run must show to pass.

A check is a small dict:
- {"kind": "status", "value": "ok" | "error" | "waiting"}
- {"kind": "field", "field": name, "op": equals | contains | not_contains | matches | empty | not_empty, "value": text}
- {"kind": "node", "node": id, "ran": true | false}
- {"kind": "tool", "node": Agent node id, "tool": name, "called": true | false}: whether the Agent node's model called the
  tool and the call ran (its result or its own error went back to the model); a call refused, rejected by an approver
  or with invalid arguments did not run (TASK-0119)
- {"kind": "duration", "max": seconds}  /  {"kind": "cost", "max": US dollars}

`evaluate` returns one result per check: {passed: True | False | None, expected, actual, reason}. `passed` None means
"not evaluated" (the run did not finish, or no model price is known); `reason` is a code the UI translates.
Without a status check, a case also needs the run to end `ok`.
"""
from __future__ import annotations
import json, re
from typing import Any, Dict, List, Optional
from . import agents

KINDS = ("status", "field", "node", "tool", "duration", "cost")
RAN = ("ok", "failed")  # tool call outcomes that count as called
STATUSES = ("ok", "error", "waiting")
OPS = ("equals", "contains", "not_contains", "matches", "empty", "not_empty")
NO_VALUE = ("empty", "not_empty")
MAX_CHECKS = 30
MAX_VALUE = 2000    # characters of an expected value or a pattern
MAX_TEXT = 100_000  # characters of a field value a check reads
SHOWN = 500         # characters of the actual value kept in a result


def errors(checks: Any) -> List[str]:
    """Why these checks cannot be saved (English, shown as TEST_CASE_INVALID)."""
    if not isinstance(checks, list) or not checks: return ["add at least one check"]
    if len(checks) > MAX_CHECKS: return [f"at most {MAX_CHECKS} checks"]
    errs: List[str] = []
    for i, c in enumerate(checks, 1):
        k = c.get("kind") if isinstance(c, dict) else None
        if k not in KINDS: errs.append(f"check {i}: unknown kind"); continue
        if k == "status" and c.get("value") not in STATUSES: errs.append(f"check {i}: status must be one of {', '.join(STATUSES)}")
        if k == "field":
            if not isinstance(c.get("field"), str) or not c["field"].strip(): errs.append(f"check {i}: choose a field")
            if c.get("op") not in OPS: errs.append(f"check {i}: unknown comparison")
            elif c["op"] not in NO_VALUE:
                v = c.get("value")
                if not isinstance(v, str) or len(v) > MAX_VALUE: errs.append(f"check {i}: the value must be text (max {MAX_VALUE} characters)")
                elif c["op"] == "matches":
                    try: re.compile(v)
                    except re.error as e: errs.append(f"check {i}: invalid pattern ({e})")
        if k == "node":
            if not isinstance(c.get("node"), str) or not c["node"].strip(): errs.append(f"check {i}: choose a node")
            if not isinstance(c.get("ran"), bool): errs.append(f"check {i}: ran must be true or false")
        if k == "tool":
            if not isinstance(c.get("node"), str) or not c["node"].strip(): errs.append(f"check {i}: choose an Agent node")
            if not isinstance(c.get("tool"), str) or not c["tool"].strip(): errs.append(f"check {i}: choose a tool")
            if not isinstance(c.get("called"), bool): errs.append(f"check {i}: called must be true or false")
        if k in ("duration", "cost"):
            m = c.get("max")
            if isinstance(m, bool) or not isinstance(m, (int, float)) or m <= 0: errs.append(f"check {i}: the limit must be a positive number")
    return errs


def text(v: Any) -> str:
    """A state value as the text checks compare: strings as they are, anything else as compact JSON."""
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)


def _result(passed: Optional[bool], expected: str, actual: Any = None, reason: Optional[str] = None) -> dict:
    return {"passed": passed, "expected": expected, "actual": None if actual is None else text(actual)[:SHOWN], "reason": reason}


def _field(c: dict, state: Dict[str, Any], schema: set) -> dict:
    name, op, want = c["field"], c["op"], c.get("value") or ""
    expected = op if op in NO_VALUE else want
    if name not in state and name not in schema: return _result(False, expected, reason="field_missing")
    v = state.get(name); t = "" if v is None else text(v)[:MAX_TEXT]
    if op == "empty": ok = v in (None, "", [], {})
    elif op == "not_empty": ok = v not in (None, "", [], {})
    elif op == "equals": ok = t == want
    elif op == "contains": ok = want in t
    elif op == "not_contains": ok = want not in t
    else: ok = re.search(want, t) is not None
    return _result(ok, expected, v)


def evaluate(checks: List[dict], run: Dict[str, Any], workflow: Dict[str, Any]) -> List[dict]:
    """run: {status, final_state, events, duration_ms, cost_usd}; workflow: the graph that ran (nodes, state)."""
    status = run.get("status") or "error"; done = status == "ok"
    state = run.get("final_state") or {}; state = state if isinstance(state, dict) else {}
    schema = {f.get("name") for f in workflow.get("state") or [] if isinstance(f, dict)}
    nodes = {n.get("id") for n in workflow.get("nodes") or [] if isinstance(n, dict)}
    finished = [e for e in run.get("events") or [] if isinstance(e, dict) and e.get("type") == "node_finished"]
    ran = {e.get("node") for e in finished}
    out = []
    for c in checks:
        k = c["kind"]
        if k == "status": out.append(_result(status == c["value"], c["value"], status))
        elif k == "node":
            exp = "ran" if c["ran"] else "not_ran"
            if c["node"] not in nodes: out.append(_result(False, exp, reason="node_missing"))
            else: out.append(_result((c["node"] in ran) == c["ran"], exp, "ran" if c["node"] in ran else "not_ran"))
        elif k == "tool":
            exp = "called" if c["called"] else "not_called"
            if c["node"] not in nodes: out.append(_result(False, exp, reason="node_missing")); continue
            called = any(tool_ran(e, c["node"], c["tool"]) for e in finished)
            out.append(_result(called == c["called"], exp, "called" if called else "not_called"))
        elif not done: out.append(_result(None, text(c.get("value") or c.get("op") or c.get("max")), reason="not_evaluated"))
        elif k == "field": out.append(_field(c, state, schema))
        elif k == "duration":
            secs = (run.get("duration_ms") or 0) / 1000
            out.append(_result(secs <= c["max"], text(c["max"]), round(secs, 3)))
        else:
            cost = run.get("cost_usd")
            out.append(_result(None, text(c["max"]), reason="no_price") if cost is None else _result(cost <= c["max"], text(c["max"]), cost))
    return out


def tool_ran(e: dict, agent: str, tool: str) -> bool:
    """Whether this `node_finished` event is a call of `tool` by Agent node `agent` that ran (engine/agents step summary)."""
    a = e.get("agent") if isinstance(e.get("agent"), dict) else {}
    # a slot is `agent/__tool/1` (DEC-0069); older events used `agent/__tool`
    return agents.agent_of_step(str(e.get("node") or "")) == agent and a.get("kind") == "tool" and a.get("tool") == tool and outcome(a) in RAN


def outcome(a: dict) -> str:
    """ok, failed (the tool raised), or not run: refused, rejected, unknown tool or invalid arguments."""
    if a.get("status") == "ok": return "ok"
    return "failed" if a.get("status") == "error" and str(a.get("result") or "").startswith(agents.FAILED) else "not_run"


def passed(checks: List[dict], results: List[dict], status: str) -> bool:
    """A case passes when no check failed and, unless a status check says otherwise, the run ended ok."""
    if any(r["passed"] is False for r in results): return False
    return any(c["kind"] == "status" for c in checks) or status == "ok"
