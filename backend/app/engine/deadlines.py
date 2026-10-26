"""Human node deadlines (TASK-0066, REQ-0041): how long a Human node waits, reminders while it waits, and what happens
when time runs out. The worker's maintenance loop fires them (ApprovalService.fire_deadlines).

Node data `deadline` (optional): `after` ("30m", "4h", "2d"), `remind_every` (same format, optional, shorter than
`after`), `on_timeout` ("reject" | "approve" | "escalate"), `escalate_to` (e-mails, required for "escalate").
Escalation happens once: the listed people become approvers and the step waits `after` again, then it is rejected.
Durations are wall-clock time.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from .issues import Issue

UNITS = {"m": 60, "h": 3600, "d": 86400}
ACTIONS = ("reject", "approve", "escalate")
RESPONSES = {"reject": "rejected", "approve": "approved"}
MAX_REMINDERS = 5
_DURATION = re.compile(r"^\s*(\d{1,5})\s*([mhd])\s*$")


def seconds(v: Any) -> Optional[float]:
    """"4h" -> 14400.0; None for anything that is not a positive duration."""
    m = _DURATION.match(v) if isinstance(v, str) else None
    n = int(m.group(1)) * UNITS[m.group(2)] if m else 0
    return float(n) if n > 0 else None


def emails(v: Any) -> List[str]:
    return [e.strip().lower() for e in v if isinstance(e, str) and e.strip()] if isinstance(v, list) else []


def parse(d: Dict[str, Any]) -> Optional[dict]:
    """The node's deadline as {after, remind_every, on_timeout, escalate_to} in seconds, or None when it has none or
    it is not valid (the validator reports why)."""
    raw = d.get("deadline")
    if not isinstance(raw, dict) or not raw.get("after") or errors("", d, 0): return None
    every = seconds(raw.get("remind_every"))
    return {"after": seconds(raw["after"]), "remind_every": every, "on_timeout": raw.get("on_timeout") or "reject",
            "escalate_to": emails(raw.get("escalate_to"))}


def errors(nid: str, d: Dict[str, Any], wait_ttl: float) -> List[str]:
    raw = d.get("deadline")
    if raw is None or raw == {} or (isinstance(raw, dict) and not raw.get("after") and not raw.get("remind_every")): return []
    if not isinstance(raw, dict): return [Issue("DEADLINE_NOT_OBJECT", node=nid)]
    errs, after = [], seconds(raw.get("after"))
    if after is None: errs.append(Issue("DEADLINE_DURATION", node=nid))
    if raw.get("remind_every"):
        every = seconds(raw["remind_every"])
        if every is None: errs.append(Issue("DEADLINE_REMINDER_DURATION", node=nid))
        elif after is not None and every >= after: errs.append(Issue("DEADLINE_REMINDER_OFTEN", node=nid))
    action = raw.get("on_timeout") or "reject"
    if action not in ACTIONS: errs.append(Issue("DEADLINE_ACTION", node=nid, actions=", ".join(ACTIONS)))
    if action == "escalate":
        to = emails(raw.get("escalate_to"))
        if not to: errs.append(Issue("DEADLINE_ESCALATE_MISSING", node=nid))
        elif any("@" not in e for e in to): errs.append(Issue("DEADLINE_ESCALATE_EMAILS", node=nid))
    if after is not None and wait_ttl and after * (2 if action == "escalate" else 1) > wait_ttl:
        errs.append(Issue("DEADLINE_TOO_LONG", node=nid, hours=int(wait_ttl // 3600)))
    return errs
