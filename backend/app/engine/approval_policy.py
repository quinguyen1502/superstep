"""AI review of approvals (TASK-0186, REQ-0081, DEC-0075): the `approval.auto` policy of a Human node or of an Agent
node's tool approval. Pure: parsing, validation, rule matching and the policy hash. The review itself runs in
services/auto_review_service.py before people are asked.

`approval.auto`:
- `mode`: "off" | "suggest" | "auto" (off when missing). Suggest shows the AI's opinion and never answers.
- `rules`: [{field, op, value, effect}] checked first. `field` is a dot path in the request: `tool`, `args.<name>`
  (an Agent tool call), `prompt` or `state.<field>` (a Human node). `effect` is "human" (ask people) or "reject".
  A rule never approves.
- `max_per_day`: automatic answers per workflow per day (default 50).
- `judge`: {credential_id, model, instructions}: a separate model call (any chat credential).
- `min_confidence`: 0..1 (default 0.8); `notify`: tell the run owner about automatic answers (default true).
"""
from __future__ import annotations
import hashlib, json, re
from typing import Any, Dict, List, Optional
from .issues import Issue

MODES = ("off", "suggest", "auto")
OPS = ("equals", "not_equals", "contains", "not_contains", "matches", "gt", "lt", "empty")
EFFECTS = ("human", "reject")
ROOTS = ("tool", "args", "prompt", "state")
DEFAULT_CAP, MAX_CAP, DEFAULT_MIN, MAX_RULES = 50, 10000, 0.8, 20
_PATH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*$")


def raw(d: Dict[str, Any]) -> Optional[dict]:
    a = (d.get("approval") or {}) if isinstance(d.get("approval"), dict) else {}
    x = a.get("auto")
    return x if isinstance(x, dict) else None


def mode(d: Dict[str, Any]) -> str:
    x = raw(d)
    return x.get("mode") if x and x.get("mode") in MODES else "off"


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool): return None
    if isinstance(v, (int, float)): return float(v)
    try: return float(str(v).strip())
    except (TypeError, ValueError): return None


def _rule_ok(r: Any) -> bool:
    if not isinstance(r, dict) or r.get("op") not in OPS or r.get("effect") not in EFFECTS: return False
    f = r.get("field")
    if not isinstance(f, str) or not _PATH.match(f) or f.split(".")[0] not in ROOTS: return False
    if r["op"] == "empty": return True
    if r["op"] in ("gt", "lt"): return _num(r.get("value")) is not None
    if r["op"] == "matches":
        try: re.compile(str(r.get("value") or ""))
        except re.error: return False
    return isinstance(r.get("value"), (str, int, float)) and str(r.get("value")) != ""


def errors(nid: str, d: Dict[str, Any]) -> List[Issue]:
    x = raw(d)
    if x is None: return []
    errs: List[Issue] = []
    m = x.get("mode", "off")
    if m not in MODES: return [Issue("AUTO_APPROVAL_MODE", node=nid, modes=", ".join(MODES))]
    if m == "off": return []
    rules = x.get("rules") or []
    if not isinstance(rules, list) or len(rules) > MAX_RULES: errs.append(Issue("AUTO_APPROVAL_RULE_INVALID", node=nid, index=0))
    else: errs += [Issue("AUTO_APPROVAL_RULE_INVALID", node=nid, index=i) for i, r in enumerate(rules, 1) if not _rule_ok(r)]
    j = x.get("judge") if isinstance(x.get("judge"), dict) else {}
    if not j.get("credential_id"): errs.append(Issue("AUTO_APPROVAL_JUDGE_REQUIRED", node=nid))
    c = x.get("min_confidence", DEFAULT_MIN); c = _num(c) if c is not None else DEFAULT_MIN
    if c is None or not 0 <= c <= 1: errs.append(Issue("AUTO_APPROVAL_CONFIDENCE", node=nid))
    cap = x.get("max_per_day", DEFAULT_CAP)
    if not isinstance(cap, int) or isinstance(cap, bool) or not 1 <= cap <= MAX_CAP: errs.append(Issue("AUTO_APPROVAL_CAP", node=nid, max=MAX_CAP))
    return errs


def parse(d: Dict[str, Any]) -> Optional[dict]:
    """The node's policy with defaults, or None when it is off or invalid (invalid never reviews: people are asked)."""
    x = raw(d)
    if x is None or mode(d) == "off" or errors("", d): return None
    j = x.get("judge") or {}
    return {"mode": x["mode"], "rules": [dict(r) for r in x.get("rules") or []], "max_per_day": x.get("max_per_day", DEFAULT_CAP),
            "judge": {"credential_id": j.get("credential_id"), "model": j.get("model") or "", "instructions": str(j.get("instructions") or "")},
            "min_confidence": float(x.get("min_confidence", DEFAULT_MIN)), "notify": x.get("notify", True) is not False}


def policy_hash(p: Optional[dict]) -> Optional[str]:
    return hashlib.sha256(json.dumps(p, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16] if p else None


def lookup(data: Dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur: cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur): cur = cur[int(part)]
        else: return None
    return cur


def _text(v: Any) -> str:
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, sort_keys=True) if v is not None else ""


def matches(rule: dict, data: Dict[str, Any]) -> bool:
    v, op, want = lookup(data, rule["field"]), rule["op"], rule.get("value")
    if op == "empty": return v is None or v == "" or v == [] or v == {}
    if op in ("gt", "lt"):
        a, b = _num(v), _num(want)
        return a is not None and b is not None and (a > b if op == "gt" else a < b)
    s, w = _text(v).casefold(), str(want).casefold()
    if op == "equals": return s == w
    if op == "not_equals": return s != w
    if op == "contains": return w in s
    if op == "not_contains": return w not in s
    try: return re.search(str(want), _text(v)) is not None  # matches
    except re.error: return False


def check(rules: List[dict], data: Dict[str, Any]) -> tuple[Optional[str], List[int]]:
    """-> (effect, matched rule numbers): "reject" when any reject rule matches, else "human" when any human rule
    matches, else None (the judge decides)."""
    hit = [i for i, r in enumerate(rules, 1) if matches(r, data)]
    effects = {rules[i - 1]["effect"] for i in hit}
    return ("reject" if "reject" in effects else "human" if hit else None), hit


def auto_policies(wf: Optional[dict]) -> Dict[str, str]:
    """{node id: policy hash} of every node whose policy answers on its own (mode auto). Saving a change to this
    needs the workflow owner or an admin (owner decision 3)."""
    out = {}
    for n in (wf or {}).get("nodes") or []:
        d = n.get("data") or {} if isinstance(n, dict) else {}
        if mode(d) == "auto": out[str(n.get("id"))] = policy_hash(raw(d))
    return out
