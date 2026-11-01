"""Managed tool transport and outcome boundaries. All targets go through the shared SSRF guard."""
import httpx
from ...core import config
from ...core.net import public_address, pinned_request


class ToolFailure(Exception):
    def __init__(self, outcome="failed"):
        super().__init__("External operation outcome is " + outcome)
        self.outcome = outcome


def http_client(): return httpx.Client(timeout=20, follow_redirects=False)


def request(method, url, **kwargs):
    target, ip = public_address(url, config.mcp_allow_private(), "MCP_URL_INVALID")
    pinned, headers, extensions = pinned_request(target, ip)
    with http_client() as client:
        return client.request(method, pinned, headers={**kwargs.pop("headers", {}), **headers}, extensions=extensions, **kwargs)
