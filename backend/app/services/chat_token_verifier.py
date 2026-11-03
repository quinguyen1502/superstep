"""Third-party chat JWTs (DEC-0077): pinned HS256, bounded claims, audience and origin; no key cache."""
from __future__ import annotations
import base64, binascii, hashlib, hmac, json, math, re, time
from dataclasses import dataclass
from typing import Protocol
from ..core import crypto
from ..core.errors import AppError
from .chat_session_service import origin_of


@dataclass(frozen=True)
class ChatAppUser:
    id: str
    name: str
    meta: dict
    app_key_id: str

    def input(self) -> dict:
        return {"user": {"id": self.id, "name": self.name, "kind": "app"}, "meta": self.meta}


class ChatTokenVerifier(Protocol):
    def verify(self, token: str, slug: str, trigger_id: str, origin: str | None) -> ChatAppUser: ...


def _decode(segment: str) -> bytes:
    if not segment or not re.fullmatch(r"[A-Za-z0-9_-]+", segment): raise ValueError("base64url")
    return base64.b64decode(segment + "=" * (-len(segment) % 4), altchars=b"-_", validate=True)


def _object(pairs):
    out = {}
    for k, v in pairs:
        if k in out: raise ValueError("duplicate claim")
        out[k] = v
    return out


def _json(segment: str) -> dict:
    def bad_constant(_): raise ValueError("non-finite JSON")
    out = json.loads(_decode(segment), object_pairs_hook=_object, parse_constant=bad_constant)
    if not isinstance(out, dict): raise ValueError("object")
    return out


def _number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


class Hs256ChatTokenVerifier:
    def __init__(self, keys, clock=time.time): self.keys, self.clock = keys, clock

    def verify(self, token: str, slug: str, trigger_id: str, origin: str | None) -> ChatAppUser:
        invalid = AppError("CHAT_TOKEN_INVALID")
        try:
            if not isinstance(token, str) or len(token) > 8192: raise invalid
            head, body, sig = token.split(".")
            header, claims = _json(head), _json(body)
            if header.get("alg") != "HS256" or header.get("typ", "JWT") != "JWT" or "crit" in header or "b64" in header: raise invalid
            kid = header.get("kid")
            if not isinstance(kid, str) or not kid or len(kid) > 128: raise invalid
            kid.encode("ascii")
            key = self.keys.get(kid)
            if key is None or key.trigger_id != trigger_id: raise invalid
            expected = hmac.new(crypto.decrypt(key.secret_enc).encode(), f"{head}.{body}".encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(_decode(sig), expected): raise invalid
            if claims.get("iss") != kid or claims.get("aud") != f"superstep-chat:{slug}": raise invalid
            sub, name, meta = claims.get("sub"), claims.get("name", ""), claims.get("meta", {})
            if not isinstance(sub, str) or not 1 <= len(sub) <= 128 or not isinstance(name, str) or len(name) > 80: raise invalid
            sub.encode("utf-8"); name.encode("utf-8")
            if not isinstance(meta, dict) or len(json.dumps(meta, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()) > 1024: raise invalid
            iat, exp, now = claims.get("iat"), claims.get("exp"), self.clock()
            if not _number(iat) or not _number(exp) or not 0 < exp - iat <= 3600 or iat > now + 60: raise invalid
            if "nbf" in claims and (not _number(claims["nbf"]) or claims["nbf"] > now + 60): raise invalid
            origins = json.loads(key.origins)
            if origins and origin_of(origin) not in origins: raise AppError("CHAT_ORIGIN_FORBIDDEN")
            if key.revoked_at is not None: raise AppError("CHAT_APP_KEY_REVOKED")
            if exp <= now - 60: raise AppError("CHAT_TOKEN_EXPIRED")
            # The conditional write also observes a revoke racing the initial read.
            if not self.keys.used(kid, now): raise AppError("CHAT_APP_KEY_REVOKED")
            return ChatAppUser(sub, name, meta, key.id)
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError, binascii.Error, UnicodeError):
            raise invalid from None
