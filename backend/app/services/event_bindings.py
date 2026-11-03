"""Bounded data-only event admission/mapping, shared by channel adapters and trigger management."""
import json, re
from datetime import datetime, timezone
from ..core import config
from ..core.errors import AppError
from ..engine.limits import size
from ..engine.runtime import check_input

PATH = re.compile(r"(?:id|source|type|time|actor|conversation|data)(?:\.[A-Za-z0-9_-]{1,80}){0,8}")


def settings(trigger):
    values = json.loads(trigger.settings or "{}")
    return values.get("event")


def validate(value, fields):
    def bad(field): raise AppError("CHAT_TRIGGER_CONFIG_INVALID", field=f"event.{field}")
    if not isinstance(value, dict) or set(value) != {"senders", "type", "mapping"}: bad("mapping")
    senders = value["senders"]
    if not isinstance(senders, list) or not 1 <= len(senders) <= 100: bad("senders")
    if any(not isinstance(s, str) or not re.fullmatch(r"[A-Za-z0-9_.*-]{1,80}", s) for s in senders): bad("senders")
    if "*" in senders and senders != ["*"]: bad("senders")
    if not isinstance(value["type"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value["type"]): bad("type")
    mapping = value["mapping"]
    if not isinstance(mapping, dict) or not 1 <= len(mapping) <= 30: bad("mapping")
    for field, path in mapping.items():
        if field not in fields or not isinstance(path, str) or (path != "$" and not PATH.fullmatch(path)): bad("mapping")
    return {"senders": list(dict.fromkeys(senders)), "type": value["type"], "mapping": mapping}


def envelope(kind, message):
    event = {"id": message.key, "source": kind, "type": message.event.get("type", "message.text"),
             "time": message.event.get("time"), "actor": {"id": message.sender, "name": message.event.get("name", "")},
             "conversation": {"id": str(message.ref.get("chat_id", message.place))},
             "data": message.event.get("data", {"text": message.text, "message_id": message.ref.get("message_id")})}
    # Reject absent delivery identity and malformed/oversized metadata before persisting anything.
    if not isinstance(event["id"], str) or not 1 <= len(event["id"]) <= 200 or event["id"] == "None": return None
    try:
        stamp = datetime.fromisoformat(event["time"])
        if stamp.tzinfo is None: return None
        event["time"] = stamp.astimezone(timezone.utc).isoformat()
        json.dumps(event, allow_nan=False)
        if size(event) > config.input_max(): return None
    except (TypeError, ValueError, RecursionError): return None
    return event


def admitted(policy, message, event):
    return event is not None and event["type"] == policy["type"] and (policy["senders"] == ["*"] or message.sender in policy["senders"])


def map_input(policy, event, workflow):
    result = {}
    for field, path in policy["mapping"].items():
        value = event
        if path != "$":
            for key in path.split("."):
                if not isinstance(value, dict) or key not in value: raise AppError("CHAT_TRIGGER_CONFIG_INVALID", field=f"event.mapping.{field}")
                value = value[key]
        result[field] = value
    if check_input(workflow, result): raise AppError("CHAT_TRIGGER_CONFIG_INVALID", field="event.mapping")
    if size(result) > config.input_max(): raise AppError("RUN_INPUT_TOO_LARGE")
    return result
