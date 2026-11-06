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
        origins = [f"http://{host}:8080" for host in hosts] + ["http://127.0.0.1:9090", "https://127.0.0.1:9090", "http://allowed.test:8082", "https://allowed.test:8443"]
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
        elif host in {"allowed.test", "rebind.test", "fixture-proxy"}: values = [FIXTURE]
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
with Gateway("/egress/gateway.sock", policy, route, audit=audit) as server: server.serve_forever()
