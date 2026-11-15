"""Client IP behind reverse proxies ( follow-up).

STUDIO_TRUSTED_PROXIES is a comma-separated CIDR list (e.g. "10.0.0.0/8,172.16.0.0/12"). X-Forwarded-For is only
honoured when the direct peer is trusted; the chain (XFF hops + peer) is then walked right to left, skipping trusted
hops, and the first untrusted address is the client. Hops left of it are client-controlled and never used.
STUDIO_TRUST_PROXY=1 (older setting) is an alias for "trust exactly one hop": the last XFF entry, whatever the peer.
"""
import ipaddress
import os
from functools import lru_cache
from typing import Optional

Net = ipaddress.IPv4Network | ipaddress.IPv6Network


@lru_cache(maxsize=16)
def parse_networks(raw: str) -> tuple[Net, ...]:
    """CIDRs (or bare IPs); invalid entries are skipped rather than trusting too much."""
    out = []
    for part in raw.split(","):
        try: out.append(ipaddress.ip_network(part.strip(), strict=False)) if part.strip() else None
        except ValueError: continue
    return tuple(out)


def _ip(s: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    s = s.strip().strip('"')
    if s.startswith("[") and "]" in s: s = s[1:s.index("]")]              # [v6]:port
    elif s.count(":") == 1: s = s.split(":")[0]                            # v4:port
    try: return ipaddress.ip_address(s)
    except ValueError: return None


def resolve(peer: Optional[str], forwarded_for: Optional[str], trusted: tuple[Net, ...] = (), one_hop: bool = False) -> str:
    peer = peer or "unknown"
    hops = [h.strip() for h in (forwarded_for or "").split(",") if h.strip()]
    if one_hop: return hops[-1] if hops else peer                          # STUDIO_TRUST_PROXY=1 compatibility
    def is_trusted(h: str) -> bool:
        a = _ip(h); return a is not None and any(a in n for n in trusted)
    if not trusted or not is_trusted(peer): return peer                    # only a trusted proxy may speak for the client
    for h in reversed(hops):
        if _ip(h) is None: return h                                         # garbage: stop, it is not one of ours
        if not is_trusted(h): return str(_ip(h))
    return str(_ip(hops[0])) if hops else peer                              # everything is a proxy: the farthest one


def client_ip(peer: Optional[str], forwarded_for: Optional[str]) -> str:
    """Resolve with the configured trust (env read per call, parsed once per value)."""
    nets = parse_networks(os.environ.get("STUDIO_TRUSTED_PROXIES", ""))
    return resolve(peer, forwarded_for, nets, one_hop=not nets and os.environ.get("STUDIO_TRUST_PROXY") == "1")
