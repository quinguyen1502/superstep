"""STUDIO_TRUSTED_PROXIES: X-Forwarded-For walked right to left, skipping trusted hops."""
import pytest
from app.core.client_ip import client_ip, parse_networks, resolve

NETS = parse_networks("10.0.0.0/8, 172.16.0.0/12, ::1/128, not-a-cidr")


@pytest.mark.parametrize("peer, xff, want", [
    ("10.0.0.2", "6.6.6.6, 203.0.113.7", "203.0.113.7"),             # spoofed first hop ignored
    ("10.0.0.2", "6.6.6.6, 203.0.113.7, 172.16.4.4", "203.0.113.7"),  # two proxies skipped
    ("10.0.0.2", "10.1.1.1, 10.2.2.2", "10.1.1.1"),                    # all trusted: the farthest
    ("10.0.0.2", None, "10.0.0.2"),
    ("198.51.100.9", "203.0.113.7", "198.51.100.9"),                   # untrusted peer cannot forward for anyone
    ("10.0.0.2", "203.0.113.7:4711", "203.0.113.7"),                   # ports stripped
    ("::1", "2001:db8::5", "2001:db8::5"),
    ("10.0.0.2", "6.6.6.6, junk", "junk"),                             # garbage stops the walk
])
def test_resolve(peer, xff, want): assert resolve(peer, xff, NETS) == want


def test_invalid_cidrs_are_skipped(): assert len(NETS) == 3


def test_env_and_backward_compatible_alias(monkeypatch):
    monkeypatch.delenv("STUDIO_TRUSTED_PROXIES", raising=False); monkeypatch.delenv("STUDIO_TRUST_PROXY", raising=False)
    assert client_ip("10.0.0.2", "6.6.6.6") == "10.0.0.2"                         # default: no proxy trusted
    monkeypatch.setenv("STUDIO_TRUST_PROXY", "1")
    assert client_ip("198.51.100.9", "6.6.6.6, 203.0.113.7") == "203.0.113.7"     # alias: exactly one hop
    monkeypatch.setenv("STUDIO_TRUSTED_PROXIES", "10.0.0.0/8")                    # the list wins over the alias
    assert client_ip("198.51.100.9", "6.6.6.6, 203.0.113.7") == "198.51.100.9"
    assert client_ip("10.9.9.9", "6.6.6.6, 203.0.113.7, 10.3.3.3") == "203.0.113.7"
