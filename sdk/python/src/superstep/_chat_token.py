"""Server-side HS256 signing with the standard library."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from typing import Any, Dict, Optional

from ._errors import ConfigError


def _invalid(field: str) -> ConfigError:
    return ConfigError(f"Invalid chat token {field}", code="CONFIG_INVALID")


def _text(value: str, field: str, limit: int, empty: bool = False) -> None:
    if not isinstance(value, str) or not (0 if empty else 1) <= len(value) <= limit: raise _invalid(field)
    try: value.encode("utf-8")
    except UnicodeError: raise _invalid(field) from None


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def mint_chat_token(key_id: str, secret: str, slug: str, user_id: str, name: Optional[str] = None,
                    ttl: int = 600, meta: Optional[Dict[str, Any]] = None) -> str:
    """Authenticate the user in your server first. Never distribute an app-key secret to clients."""
    name = "" if name is None else name
    for value, field, maximum, empty in [(key_id, "key_id", 128, False), (secret, "secret", 8192, False),
        (slug, "slug", 200, False), (user_id, "user_id", 128, False), (name, "name", 80, True)]:
        _text(value, field, maximum, empty)
    if not re.fullmatch(r"[\x21-\x7e]+", key_id) or not re.fullmatch(r"[a-zA-Z0-9_-]+", slug): raise _invalid("key_id/slug")
    if type(ttl) is not int or not 1 <= ttl <= 3600: raise _invalid("ttl")
    now = int(time.time())
    claims = dict(iss=key_id, aud=f"superstep-chat:{slug}", sub=user_id, name=name, iat=now, exp=now + ttl)
    if meta is not None:
        try:
            if not isinstance(meta, dict): raise ValueError()
            encoded = json.dumps(meta, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
            if len(encoded) > 1024: raise ValueError()
            claims["meta"] = json.loads(encoded)
        except (TypeError, ValueError, UnicodeError, RecursionError): raise _invalid("meta") from None
    def part(value): return _b64(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8"))
    unsigned = part(dict(alg="HS256", typ="JWT", kid=key_id)) + "." + part(claims)
    return unsigned + "." + _b64(hmac.new(secret.encode("utf-8"), unsigned.encode("ascii"), hashlib.sha256).digest())
