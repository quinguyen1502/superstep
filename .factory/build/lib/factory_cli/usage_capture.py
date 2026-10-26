"""Extract token/cost usage from the JSON output of coding tools.

Codex (`codex exec --json`), Claude Code (`claude -p --output-format json`), and
Cursor (`cursor-agent -p --output-format json`) all emit JSON (or JSON lines)
that include token counts and, for some, a cost. Rather than hard-code each
tool's exact schema (which differs and changes), this scans the document for the
well-known usage keys and takes the last values seen, which for streaming output
is the final cumulative total.
"""
from __future__ import annotations

import json
from typing import List, Tuple

from .project import FactoryError

_INPUT_KEYS = {"input_tokens", "inputtokens", "prompt_tokens", "prompttokens"}
_OUTPUT_KEYS = {"output_tokens", "outputtokens", "completion_tokens", "completiontokens"}
_COST_KEYS = {"total_cost_usd", "cost_usd", "costusd", "cost"}

# Friendly tool names mapped to the canonical ids used elsewhere.
TOOL_ALIASES = {
    "claude": "claude-code",
    "claude-code": "claude-code",
    "codex": "codex",
    "cursor": "cursor",
    "cursor-agent": "cursor",
    "grok": "grok",
}


def normalize_tool_id(tool_id: str) -> str:
    return TOOL_ALIASES.get(tool_id.strip().lower(), tool_id.strip())


def _iter_json_objects(text: str) -> List[object]:
    text = text.strip()
    if not text:
        return []
    try:
        return [json.loads(text)]
    except json.JSONDecodeError:
        pass
    objects: List[object] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            objects.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return objects


def _scan(node: object, found: dict) -> None:
    if isinstance(node, dict):
        lowered = {str(k).lower(): v for k, v in node.items()}
        for key in _INPUT_KEYS:
            if isinstance(lowered.get(key), (int, float)):
                found["input"] = int(lowered[key])
        for key in _OUTPUT_KEYS:
            if isinstance(lowered.get(key), (int, float)):
                found["output"] = int(lowered[key])
        for key in _COST_KEYS:
            if isinstance(lowered.get(key), (int, float)):
                found["cost"] = float(lowered[key])
        for value in node.values():
            _scan(value, found)
    elif isinstance(node, list):
        for value in node:
            _scan(value, found)


def parse_tool_usage(text: str) -> Tuple[int, int, float]:
    """Return (input_tokens, output_tokens, cost_usd) parsed from tool output."""
    found: dict = {}
    for obj in _iter_json_objects(text):
        _scan(obj, found)
    if not found:
        raise FactoryError(
            "Could not find token usage or cost in the tool output. Run the tool "
            "with its JSON output format (e.g. --output-format json / --json)."
        )
    return found.get("input", 0), found.get("output", 0), found.get("cost", 0.0)
