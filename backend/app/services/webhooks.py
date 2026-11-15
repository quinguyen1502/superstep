"""Result webhooks.

- SSRF guard and DNS-rebinding-safe pinned IP from `core/net.py` (shared with MCP and HTTP Tool nodes);
  private targets are refused unless STUDIO_ALLOW_PRIVATE_CALLBACKS=1. The host is resolved at delivery time.
- Signed: `X-Studio-Signature: t=<unix ts>,v1=<hex HMAC-SHA256(secret, "<ts>.<raw body>")>` with the token's
  signing secret (shown once when the token is created). `verify_signature` is the reference check.
"""
import hashlib, hmac, json, time
from dataclasses import dataclass
from typing import Optional
import httpx
from ..core import config
from ..core.errors import AppError
from ..core.net import pinned_request, public_address  # noqa: F401  (re-exported for MCP and tests)
from ..core.logging import get_logger

log = get_logger("webhooks")
SIGNATURE_HEADER = "X-Studio-Signature"
TOLERANCE_S = 300  # receivers should reject signatures older than this (replay protection)


def http_client() -> httpx.Client:
    """Factory for webhook calls (tests replace it with a MockTransport client)."""
    return httpx.Client(timeout=10, follow_redirects=False)  # a redirect could point anywhere: never follow


def resolve(url: Optional[str]) -> tuple[str, str]:
    """Validate a callback `url` and resolve its host once. Returns (url, pinned_ip). Raises CALLBACK_URL_INVALID."""
    return public_address(url, config.allow_private_callbacks())


def check_callback_url(url: Optional[str]) -> Optional[str]:
    """Early validation when the run is queued (the address is resolved and checked again at delivery)."""
    return resolve(url)[0] if url else None


def _mac(secret: str, body: bytes, ts: int) -> str:
    return hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()


def sign(secrets: "str | list[str]", body: bytes, ts: Optional[int] = None) -> str:
    """`t=<ts>,v1=<mac>[,v1=<mac>…]`, one v1 per active secret (during a rotation grace period both the new
    and the previous secret sign, so receivers can switch over without dropping callbacks; )."""
    ts = int(ts if ts is not None else time.time())
    secrets = [secrets] if isinstance(secrets, str) else secrets
    return ",".join([f"t={ts}"] + [f"v1={_mac(s, body, ts)}" for s in secrets])


def verify_signature(secret: str, header: str, body: bytes, tolerance: int = TOLERANCE_S, now: Optional[float] = None) -> bool:
    """Reference receiver-side check (documented in the README): any v1 may match."""
    try:
        parts = [p.split("=", 1) for p in (header or "").split(",")]
        ts = int(next(v for k, v in parts if k == "t"))
    except (ValueError, StopIteration):
        return False
    if abs((now or time.time()) - ts) > tolerance: return False
    expected = _mac(secret, body, ts)
    return any(k == "v1" and hmac.compare_digest(expected, v) for k, v in parts)


@dataclass
class Attempt:
    ok: bool
    code: Optional[int] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    retryable: bool = True  # False when the address itself is refused (SSRF guard): retrying cannot help


def post(url: str, payload: dict, secrets: "list[str] | None" = None, event: str = "run.finished") -> Attempt:
    """ONE signed POST to the pinned, validated IP. Never raises. Retries are scheduled by the caller
    (DeliveryService, exponential backoff through the job queue)."""
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    t0 = time.perf_counter()
    try:
        _, ip = resolve(url)
        target, headers, ext = pinned_request(url, ip)
        headers.update({"Content-Type": "application/json", "X-Studio-Event": event})
        if secrets: headers[SIGNATURE_HEADER] = sign(secrets, body)
        with http_client() as c:
            r = c.send(c.build_request("POST", target, content=body, headers=headers, extensions=ext))
        ms = round((time.perf_counter() - t0) * 1000, 2)
        if r.status_code < 400: return Attempt(True, r.status_code, ms)
        log.warning("webhook %s returned HTTP %s", url, r.status_code)
        return Attempt(False, r.status_code, ms, f"HTTP {r.status_code}")
    except AppError:
        log.warning("webhook %s refused (address not allowed or unresolvable)", url)
        return Attempt(False, None, None, "address not allowed or unresolvable", retryable=False)
    except httpx.HTTPError as e:
        log.warning("webhook %s failed: %s", url, type(e).__name__)
        return Attempt(False, None, round((time.perf_counter() - t0) * 1000, 2), type(e).__name__)


def deliver(url: str, payload: dict, secret: "str | list[str] | None" = None) -> bool:
    """Single synchronous delivery (kept for callers without a delivery log)."""
    return post(url, payload, [secret] if isinstance(secret, str) else secret).ok
