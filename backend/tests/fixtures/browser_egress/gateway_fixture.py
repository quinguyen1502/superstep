"""TEST ONLY: synthetic DNS and one exact private fixture IP; never copied into production images."""
import json
import os
import socket
import threading
from types import SimpleNamespace

from app.engine.browser_gateway import Gateway
from app.engine.browser_network import DestinationPolicy, Route

FIXTURE = socket.gethostbyname("fixture")
LOCK, EVENTS, DNS = threading.Lock(), [], {}


class FixturePolicy(DestinationPolicy):
    def __init__(self):
        hosts = ["allowed.test", "rebind.test", "mixed.test", "private.test", "metadata.test", "localhost", "127.0.0.1", "[::1]", "169.254.169.254"]
        origins = [f"http://{host}:8080" for host in hosts] + ["http://127.0.0.1:9090", "https://127.0.0.1:9090", "http://allowed.test:8082", "https://allowed.test:8443", "https://other.test:8443", "https://sub.allowed.test:8443"]
        super().__init__(origins, resolver=self.synthetic_dns)

    @staticmethod
    def address_allowed(value): return value == FIXTURE  # narrower than production; no internet destinations

    @staticmethod
    def synthetic_dns(host, port, **kwargs):
        with LOCK:
            DNS[host] = DNS.get(host, 0) + 1
            count = DNS[host]
        if host == "rebind.test" and count > 1: values = ["127.0.0.1"]
        elif host == "mixed.test": values = [FIXTURE, "127.0.0.1"]
        elif host in {"private.test", "localhost"}: values = ["127.0.0.1"]
        elif host == "metadata.test": values = ["169.254.169.254"]
        elif host in {"allowed.test", "rebind.test", "fixture-proxy", "other.test", "sub.allowed.test"}: values = [FIXTURE]
        else: values = [host]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (value, port)) for value in values]


def audit(event, target):
    with LOCK:
        EVENTS.append({"event": event, "origin": target})
        with open("/tmp/gateway-stats.json", "w") as stream: json.dump({"events": EVENTS, "dns": DNS}, stream)


policy = FixturePolicy()
mode = os.environ.get("FIXTURE_ROUTE", "direct")
custom = SimpleNamespace(mode="custom", server="http://fixture-proxy:8081", auth="basic")
secrets = {"proxy_username": "synthetic-user", "proxy_password": "synthetic-password"}
if mode == "direct": route = Route()
elif mode == "operator_default":
    route = Route.from_settings(SimpleNamespace(mode="operator_default"), {}, policy,
        operator_default=(custom, secrets), approved_proxies=[custom.server])
else:
    route = Route.from_settings(custom, secrets, policy, approved_proxies=[custom.server])
# Product-worker fixtures use the exact trusted supervisor config shape; standalone
# egress proof retains FIXTURE_ROUTE. Only synthetic DNS/IP acceptance differs from production.
raw = os.environ.get("STUDIO_BROWSER_GATEWAY_CONFIG")
if raw:
    value = json.loads(raw)
    if value["allowed_origins"]:
        policy.allowed_origins = frozenset(policy._origin(item) for item in value["allowed_origins"])
    default = value.get("operator_default")
    configured_default = (SimpleNamespace(**default["proxy"]), default["secrets"]) if default else None
    route = Route.from_settings(SimpleNamespace(**value["proxy"]), value["secrets"], policy,
        operator_default=configured_default, approved_proxies=value["approved_proxies"])
with Gateway("/egress/gateway.sock", policy, route, audit=audit) as server: server.serve_forever()
