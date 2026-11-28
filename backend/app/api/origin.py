"""Validate a browser origin against the request or the configured external URL."""
from urllib.parse import urlsplit

from starlette.requests import HTTPConnection

from ..core import config


def matches_origin(connection: HTTPConnection, origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        if (parsed.scheme not in ("http", "https") or parsed.username or parsed.password
                or parsed.path or parsed.query or parsed.fragment):
            return False
        scheme = {"ws": "http", "wss": "https"}.get(connection.url.scheme, connection.url.scheme)
        expected = urlsplit(f"{scheme}://{connection.headers.get('host', '')}")
        origin_port = parsed.port or (443 if parsed.scheme == "https" else 80)
        expected_port = expected.port or (443 if scheme == "https" else 80)
        own = parsed.scheme == expected.scheme and parsed.hostname == expected.hostname and origin_port == expected_port
        # The configured public URL describes a trusted reverse proxy's external origin.
        return own or bool(config.public_url() and origin.rstrip("/") == config.public_url())
    except ValueError:
        return False


def same_origin(connection: HTTPConnection) -> bool:
    origin = connection.headers.get("origin")
    # Non-browser clients can supply credentials without an Origin header.
    return not origin or matches_origin(connection, origin)
