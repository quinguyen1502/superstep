"""Managed tool transport and outcome boundaries. All targets go through the shared SSRF guard."""
import httpx
from ...core import config
from ...core.net import public_address, pinned_request


class ToolFailure(Exception):
    def __init__(self, outcome="failed"):
        super().__init__("External operation outcome is " + outcome)
        self.outcome = outcome


def http_client(): return httpx.Client(timeout=20, follow_redirects=False)


def request(method, url, max_bytes=None, **kwargs):
    target, ip = public_address(url, config.mcp_allow_private(), "MCP_URL_INVALID")
    pinned, headers, extensions = pinned_request(target, ip)
    with http_client() as client:
        provided = kwargs.pop("headers", {})
        options = {**kwargs, "headers": {**provided, **headers}, "extensions": extensions}
        if max_bytes is None: return client.request(method, pinned, **options)
        with client.stream(method, pinned, **options) as response:
            body = bytearray()
            for chunk in response.iter_bytes():
                if len(body) + len(chunk) > max_bytes: raise httpx.DecodingError("Managed response byte limit exceeded")
                body.extend(chunk)
            return httpx.Response(response.status_code, content=bytes(body), headers={"content-type": response.headers.get("content-type", "")})


def redact_values(value, secrets):
    sensitive = sorted({item for item in secrets if isinstance(item, str) and item}, key=len, reverse=True)
    def clean(item):
        if isinstance(item, str):
            for secret in sensitive: item = item.replace(secret, "[redacted]")
            return item
        if isinstance(item, dict): return {clean(key): clean(value) for key, value in item.items()}
        if isinstance(item, list): return [clean(value) for value in item]
        return item
    return clean(value)
