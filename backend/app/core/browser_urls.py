"""Browser HTTP target syntax shared by metadata contracts and the isolated egress gateway."""
from urllib.parse import urlsplit


def http_url(value: str, *, origin=False, proxy=False) -> str:
    """Syntax only. The egress boundary must resolve/pin every actual connection."""
    parsed = urlsplit(value)
    if (parsed.scheme not in ({"http"} if proxy else {"https", "http"}) or not parsed.hostname
            or parsed.username is not None or parsed.password is not None or "\\" in value
            or any(ord(c) <= 32 or ord(c) == 127 for c in value)
            or (parsed.port is not None and not 1 <= parsed.port <= 65535)):
        raise ValueError("Invalid HTTP target")
    if (origin or proxy) and (parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ValueError("Expected an origin without a path, query or fragment")
    return value.rstrip("/") if origin or proxy else value

