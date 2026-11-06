"""Browser egress policy and pinned TCP routes for the isolated gateway.

This module does not grant browser access. Only a network-isolated worker using
the gateway for *all* page traffic can enforce this policy (see browser-egress.md).
Page destinations require a non-empty origin whitelist (Accepted DEC-0085);
empty allowlists deny every non-infrastructure resolve.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import ipaddress
import socket
import time
from urllib.parse import urlsplit

from ..core.browser_urls import http_url


class EgressDenied(Exception):
    def __init__(self): super().__init__("Browser egress denied")


def origin(scheme, host, port):
    host = host.lower().rstrip(".")
    bracketed = f"[{host}]" if ":" in host else host
    suffix = "" if (scheme, port) in (("http", 80), ("https", 443)) else f":{port}"
    return f"{scheme}://{bracketed}{suffix}"


@dataclass(frozen=True)
class Destination:
    scheme: str
    host: str
    port: int
    address: str

    @property
    def origin(self): return origin(self.scheme, self.host, self.port)

    @property
    def authority(self):
        return f"[{self.address}]:{self.port}" if ":" in self.address else f"{self.address}:{self.port}"


class DestinationPolicy:
    """Resolve once, reject any non-global answer, then connect only to the pinned IP.

    There is deliberately no `allow_private` or fixture field. The fixture-only
    subclass lives outside app/ and cannot be enabled by connection/model data.
    """
    def __init__(self, allowed_origins=(), *, resolver=socket.getaddrinfo, require_whitelist=True):
        try:
            self.allowed_origins = frozenset(self._origin(value) for value in allowed_origins)
        except (ValueError, TypeError): raise EgressDenied() from None
        if require_whitelist and not self.allowed_origins: raise EgressDenied()
        self.resolver = resolver

    @staticmethod
    def _origin(value):
        parsed = urlsplit(http_url(value, origin=True))
        return origin(parsed.scheme, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))

    @staticmethod
    def address_allowed(value):
        ip = ipaddress.ip_address(value)
        if isinstance(ip, ipaddress.IPv6Address):
            if ip.ipv4_mapped or ip.sixtofour or ip.teredo or ip in ipaddress.ip_network("64:ff9b::/96"):
                return False
        return ip.is_global and not ip.is_multicast

    def resolve(self, scheme, host, port, *, infrastructure=False):
        try:
            if scheme not in {"http", "https"} or type(port) is not int or not 1 <= port <= 65535:
                raise ValueError()
            if not host or any(ord(c) <= 32 or c in "\\/%@?#" or ord(c) == 127 for c in host): raise ValueError()
            host = host.lower().rstrip(".").encode("idna").decode("ascii")
            target_origin = origin(scheme, host, port)
            if not infrastructure and target_origin not in self.allowed_origins: raise ValueError()
            # Nonstandard ports must be explicitly named in the destination allowlist.
            if not infrastructure and port not in {80, 443} and target_origin not in self.allowed_origins: raise ValueError()
            answers = self.resolver(host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
            addresses = tuple(dict.fromkeys(item[4][0] for item in answers))
            if not addresses or any(not self.address_allowed(value) for value in addresses): raise ValueError()
            return Destination(scheme, host, port, addresses[0])
        except (ValueError, TypeError, OSError, UnicodeError): raise EgressDenied() from None


def pinned_socket(destination, timeout=15):
    """Numeric connect avoids a second DNS lookup (including at a configured proxy)."""
    family = socket.AF_INET6 if ":" in destination.address else socket.AF_INET
    connection = socket.socket(family, socket.SOCK_STREAM)
    connection.settimeout(timeout)
    try:
        target = (destination.address, destination.port, 0, 0) if family == socket.AF_INET6 else (destination.address, destination.port)
        connection.connect(target)
        return connection
    except BaseException:
        connection.close()
        raise


def read_header(connection, limit=16384):
    """No over-read: following tunnel/body bytes belong to the relay."""
    value, deadline = bytearray(), time.monotonic() + 15
    while not value.endswith(b"\r\n\r\n"):
        remaining = deadline - time.monotonic()
        if len(value) >= limit or remaining <= 0: raise EgressDenied()
        connection.settimeout(remaining)
        chunk = connection.recv(1)
        if not chunk: raise EgressDenied()
        value.extend(chunk)
    return bytes(value)


@dataclass(frozen=True)
class Route:
    proxy: Destination | None = None
    authorization: bytes | None = field(default=None, repr=False)

    @classmethod
    def from_settings(cls, proxy, secrets, policy, *, operator_default=None, approved_proxies=()):
        """Operator-approved proxy origins only; environment proxy inheritance is forbidden.

        operator_default is an explicit (settings, secrets) pair from deployment
        config. An absent default, unapproved proxy or unsupported protocol fails.
        """
        mode = proxy.mode
        if mode == "direct": return cls()
        if mode == "operator_default":
            if operator_default is None: raise EgressDenied()
            proxy, secrets = operator_default
            if proxy.mode != "custom": raise EgressDenied()
        try:
            server = http_url(proxy.server, proxy=True)
            if DestinationPolicy._origin(server) not in {DestinationPolicy._origin(value) for value in approved_proxies}:
                raise EgressDenied()
            parsed = urlsplit(server)
            destination = policy.resolve("http", parsed.hostname, parsed.port or 80, infrastructure=True)
            auth = None
            if proxy.auth == "basic":
                username, password = secrets["proxy_username"], secrets["proxy_password"]
                if not username or not password or ":" in username or any(ord(c) < 32 or ord(c) == 127 for c in username + password):
                    raise ValueError()
                auth = b"Basic " + base64.b64encode((username + ":" + password).encode("utf-8"))
            return cls(destination, auth)
        except (ValueError, TypeError, KeyError, AttributeError): raise EgressDenied() from None

    def connect(self, destination, *, dial=pinned_socket):
        if self.proxy is None: return dial(destination)
        connection = dial(self.proxy)
        try:
            authority = destination.authority.encode("ascii")
            headers = b"CONNECT " + authority + b" HTTP/1.1\r\nHost: " + authority + b"\r\n"
            if self.authorization: headers += b"Proxy-Authorization: " + self.authorization + b"\r\n"
            connection.sendall(headers + b"\r\n")
            response = read_header(connection, 8192)
            status = response.split(b"\r\n", 1)[0].split(b" ")
            if len(status) < 2 or status[0] not in {b"HTTP/1.0", b"HTTP/1.1"} or status[1] != b"200": raise EgressDenied()
            return connection
        except BaseException:
            connection.close()
            raise
