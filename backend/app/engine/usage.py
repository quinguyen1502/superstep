"""LLM token usage and cost. One place for the price table and the usage record shape."""
from __future__ import annotations
import functools, json, logging, os
from typing import Any, Callable, Dict, Optional

# USD per 1M tokens (input, output). Unknown models get cost None (shown as "-").
PRICES: Dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60), "gpt-4o": (2.50, 10.00), "gpt-4.1-mini": (0.40, 1.60), "gpt-4.1": (2.00, 8.00),
    "claude-3-5-haiku": (0.80, 4.00), "claude-3-5-sonnet": (3.00, 15.00), "claude-3-7-sonnet": (3.00, 15.00),
    "jev": (0.042, 0.0),  # TypeSafe Jev: output tokens are free
    # embedding models: input tokens only
    "text-embedding-3-small": (0.02, 0.0), "text-embedding-3-large": (0.13, 0.0), "text-embedding-ada-002": (0.10, 0.0),
}

UsageSink = Callable[[str, Dict[str, Any]], None]  # (node_id, usage) -> None


def _parse(raw: str, source: str) -> Dict[str, tuple[float, float]]:
    """{"model-prefix": [input_per_1M, output_per_1M], ...}; invalid entries are skipped with a warning."""
    out: Dict[str, tuple[float, float]] = {}
    try: data = json.loads(raw)
    except ValueError:
        logging.getLogger("studio.usage").warning("ignoring invalid price table in %s (not JSON)", source); return out
    for k, v in (data.items() if isinstance(data, dict) else []):
        try: out[str(k).lower()] = (float(v[0]), float(v[1]))
        except (TypeError, ValueError, IndexError, KeyError):
            logging.getLogger("studio.usage").warning("ignoring price entry %r in %s", k, source)
    return out


@functools.lru_cache(maxsize=8)
def _prices(env_json: str, path: str, mtime: float) -> Dict[str, tuple[float, float]]:
    table = dict(PRICES)
    if path:
        try:
            with open(path, encoding="utf-8") as f: table.update(_parse(f.read(), path))
        except OSError: logging.getLogger("studio.usage").warning("price file %s not readable", path)
    if env_json: table.update(_parse(env_json, "STUDIO_PRICES"))  # env wins over the file
    return table


def prices() -> Dict[str, tuple[float, float]]:
    """Built-in table overridden/extended by STUDIO_PRICES_FILE (JSON file) and STUDIO_PRICES (JSON string).
    Re-read when the env or the file's mtime changes."""
    path = os.environ.get("STUDIO_PRICES_FILE", "").strip()
    try: mtime = os.path.getmtime(path) if path else 0.0
    except OSError: mtime = -1.0
    return _prices(os.environ.get("STUDIO_PRICES", "").strip(), path, mtime)


def price_for(model: str) -> Optional[tuple[float, float]]:
    m = (model or "").lower(); table = prices()
    for k in sorted(table, key=len, reverse=True):  # longest prefix wins (gpt-4o-mini before gpt-4o)
        if m.startswith(k): return table[k]
    return None


def make_usage(provider: str, model: str, tokens_in: int, tokens_out: int, estimated: bool = False) -> Dict[str, Any]:
    """Usage record attached to `node_finished` events. Mock runs are estimated and always cost 0."""
    p = None if provider == "mock" else price_for(model)
    cost = 0.0 if provider == "mock" else (round((tokens_in * p[0] + tokens_out * p[1]) / 1e6, 8) if p else None)
    return {"provider": provider, "model": model, "tokens_in": int(tokens_in), "tokens_out": int(tokens_out),
            "tokens": int(tokens_in) + int(tokens_out), "cost_usd": cost, "estimated": estimated}


def estimate_tokens(text: str) -> int:
    return max(1, (len(text or "") + 3) // 4)  # ~4 chars per token; good enough for offline mock runs


def merge(a: Optional[Dict[str, Any]], b: Dict[str, Any]) -> Dict[str, Any]:
    """Sum two usage records (a node may call the LLM more than once in future node types)."""
    if not a: return dict(b)
    out = dict(a)
    for k in ("tokens_in", "tokens_out", "tokens"): out[k] = a[k] + b[k]
    out["cost_usd"] = None if a["cost_usd"] is None or b["cost_usd"] is None else round(a["cost_usd"] + b["cost_usd"], 8)
    out["estimated"] = a["estimated"] or b["estimated"]
    if "duration_ms" in a or "duration_ms" in b: out["duration_ms"] = round((a.get("duration_ms") or 0) + (b.get("duration_ms") or 0), 2)
    if "ttft_ms" not in a and "ttft_ms" in b: out["ttft_ms"] = b["ttft_ms"]  # the node's first streamed call
    return out
