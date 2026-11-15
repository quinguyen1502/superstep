"""Outbound-address guard shared by webhooks, MCP servers and HTTP Tool nodes.

- SSRF guard: http(s) only; private / loopback / link-local / reserved / multicast / unspecified targets are refused
  unless the caller allows private addresses.
- DNS-rebinding safe: the host is resolved ONCE, every address is validated, and the request connects to that pinned
  IP (Host header + TLS SNI/certificate check still use the original hostname).
"""
import ipaddress, socket
from typing import Optional
from urllib.parse import urlparse, urlunparse
from .errors import AppError


def blocked(ip: ipaddress._BaseAddress) -> bool:
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified


def public_address(url: Optional[str], allow_private: bool, code: str = "CALLBACK_URL_INVALID", **params) -> tuple[str, str]:
    """Validate an outbound http(s) `url` and resolve its host once. Returns (url, pinned_ip); raises AppError(code, **params)."""
    u = urlparse(url or "")
    if u.scheme not in ("http", "https") or not u.hostname: raise AppError(code, **params)
    try: addrs = [ai[4][0].split("%")[0] for ai in socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80), proto=socket.IPPROTO_TCP)]
    except (OSError, UnicodeError, ValueError): raise AppError(code, **params) from None
    if not addrs: raise AppError(code, **params)
    if not allow_private and any(blocked(ipaddress.ip_address(a)) for a in addrs): raise AppError(code, **params)
    return url or "", addrs[0]


def pinned_request(url: str, ip: str) -> tuple[str, dict, dict]:
    """(url with the IP as host, headers, httpx extensions) so the connection goes to the validated IP."""
    u = urlparse(url); host = u.hostname or ""
    ip_host = f"[{ip}]" if ":" in ip else ip
    netloc = ip_host + (f":{u.port}" if u.port else "")
    headers = {"Host": u.netloc.rsplit("@", 1)[-1]}
    ext = {"sni_hostname": host} if u.scheme == "https" else {}
    return urlunparse(u._replace(netloc=netloc)), headers, ext
