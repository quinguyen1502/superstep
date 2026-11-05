"""Egress address/proxy behavior independent of a real browser; Docker proof is separate."""
import io
import socket

import pytest

from app.engine.browser_contract import ProxySettings
from app.engine.browser_network import DestinationPolicy, EgressDenied, Route, Destination
from app.engine.browser_gateway import parse_request


def answers(*addresses):
    return lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, args[1])) for address in addresses]


@pytest.mark.parametrize("address", ["127.0.0.1", "127.1.2.3", "10.0.0.1", "172.16.0.1", "192.168.0.1", "169.254.169.254",
    "100.64.0.1", "0.0.0.0", "224.0.0.1", "192.0.2.1", "::1", "fe80::1", "fc00::1", "::ffff:8.8.8.8",
    "64:ff9b::7f00:1", "2002:7f00:1::", "2001:0:4136:e378:8000:63bf:3fff:fdd2"])
def test_private_special_and_transition_addresses_denied(address):
    with pytest.raises(EgressDenied): DestinationPolicy(resolver=answers(address)).resolve("https", "site.example", 443)


def test_mixed_answers_denied_and_rebinding_reresolved_each_command():
    with pytest.raises(EgressDenied): DestinationPolicy(resolver=answers("8.8.8.8", "127.0.0.1")).resolve("https", "site.example", 443)
    values = iter(["8.8.8.8", "127.0.0.1"])
    def resolve(*args, **kwargs): return answers(next(values))(*args, **kwargs)
    policy = DestinationPolicy(resolver=resolve)
    assert policy.resolve("https", "site.example", 443).address == "8.8.8.8"
    with pytest.raises(EgressDenied): policy.resolve("https", "site.example", 443)


def test_exact_origin_port_rules_and_no_fixture_flag():
    policy = DestinationPolicy(["https://allowed.example", "http://allowed.example:8080"], resolver=answers("8.8.8.8"))
    assert policy.resolve("https", "allowed.example", 443).origin == "https://allowed.example"
    assert policy.resolve("http", "allowed.example", 8080).port == 8080
    for scheme, host, port in [("http", "allowed.example", 80), ("https", "sub.allowed.example", 443),
                               ("https", "allowed.example", 8080), ("https", "allowed.example%zone", 443)]:
        with pytest.raises(EgressDenied): policy.resolve(scheme, host, port)
    with pytest.raises(TypeError): DestinationPolicy(allow_private=True)
    with pytest.raises(EgressDenied): DestinationPolicy(resolver=answers("8.8.8.8")).resolve("http", "allowed.example", 8080)


def test_direct_ignores_host_proxy_environment_and_missing_default_denied(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://untrusted.example")
    policy = DestinationPolicy(resolver=answers("8.8.8.8"))
    assert Route.from_settings(ProxySettings(), {}, policy).proxy is None
    with pytest.raises(EgressDenied): Route.from_settings(ProxySettings(mode="operator_default"), {}, policy)
    custom = ProxySettings(mode="custom", server="http://proxy.example:8080")
    with pytest.raises(EgressDenied): Route.from_settings(custom, {}, policy)  # no operator approval
    route = Route.from_settings(ProxySettings(mode="operator_default"), {}, policy,
        operator_default=(custom, {}), approved_proxies=["http://proxy.example:8080"])
    assert route.proxy.host == "proxy.example" and route.proxy.address == "8.8.8.8"


def test_generic_mcp_private_flag_cannot_relax_browser_policy(monkeypatch):
    monkeypatch.setenv("STUDIO_MCP_ALLOW_PRIVATE", "1")
    with pytest.raises(EgressDenied): DestinationPolicy(resolver=answers("127.0.0.1")).resolve("http", "site.example", 80)


class Connection:
    def __init__(self, response=b"HTTP/1.1 200 Connected\r\n\r\n"):
        self.response, self.sent, self.closed = io.BytesIO(response), b"", False
    def settimeout(self, value): pass
    def recv(self, count): return self.response.read(count)
    def sendall(self, value): self.sent += value
    def close(self): self.closed = True


def test_proxy_connect_pins_numeric_target_auth_redacted_no_dns_or_fallback():
    policy = DestinationPolicy(resolver=answers("8.8.4.4"))
    settings = ProxySettings(mode="custom", server="http://proxy.example:8080", auth="basic")
    route = Route.from_settings(settings, {"proxy_username": "fixture", "proxy_password": "synthetic-secret"}, policy,
        approved_proxies=["http://proxy.example:8080"])
    assert "synthetic" not in repr(route) and "Basic" not in repr(route)
    target = Destination("https", "site.example", 443, "8.8.8.8")
    calls, connection = [], Connection()
    def dial(value): calls.append(value); return connection
    assert route.connect(target, dial=dial) is connection
    assert calls == [route.proxy] and connection.sent.startswith(b"CONNECT 8.8.8.8:443 ")
    assert b"site.example" not in connection.sent and b"Proxy-Authorization: Basic " in connection.sent
    rejected = Connection(b"HTTP/1.1 502 Rejected\r\n\r\n")
    def fail(value): calls.append(value); return rejected
    with pytest.raises(EgressDenied): route.connect(target, dial=fail)
    assert calls == [route.proxy, route.proxy] and rejected.closed  # never dial target directly


def test_proxy_itself_must_be_public_and_credentials_cannot_smuggle_headers():
    proxy = ProxySettings(mode="custom", server="http://proxy.example", auth="basic")
    for secrets in [{}, {"proxy_username": "a:b", "proxy_password": "c"}, {"proxy_username": "a", "proxy_password": "x\r\nInjected:1"}]:
        with pytest.raises(EgressDenied): Route.from_settings(proxy, secrets, DestinationPolicy(resolver=answers("8.8.8.8")), approved_proxies=[proxy.server])
    with pytest.raises(EgressDenied): Route.from_settings(proxy, {"proxy_username": "a", "proxy_password": "b"},
        DestinationPolicy(resolver=answers("127.0.0.1")), approved_proxies=[proxy.server])


@pytest.mark.parametrize("raw", [b"GET /relative HTTP/1.1\r\nHost: site.example\r\n\r\n",
    b"GET http://user:password@site.example/ HTTP/1.1\r\n\r\n",
    b"GET http://site.example/ HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n",
    b"GET http://site.example/ HTTP/1.1\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\n",
    b"GET http://site.example/ HTTP/1.1\r\nUpgrade: websocket\r\n\r\n",
    b"CONNECT site.example/path HTTP/1.1\r\n\r\n"])
def test_malformed_or_unsupported_proxy_requests_fail_closed(raw):
    with pytest.raises(EgressDenied): parse_request(raw, DestinationPolicy(resolver=answers("8.8.8.8")))


def test_http_forwarding_rewrites_host_strips_proxy_secrets_and_bounds_body():
    target, forwarded, body_size = parse_request(b"POST http://site.example/a?q=1 HTTP/1.1\r\nHost: attacker.example\r\n"
        b"Proxy-Authorization: private\r\nContent-Length: 3\r\n\r\n", DestinationPolicy(resolver=answers("8.8.8.8")))
    assert target.address == "8.8.8.8" and body_size == 3
    assert forwarded.startswith(b"POST /a?q=1 HTTP/1.1\r\nHost: site.example\r\nConnection: close\r\n")
    assert b"private" not in forwarded and b"attacker" not in forwarded
