"""Bounded HTTP CONNECT gateway on a private Unix socket; not a public proxy.

The browser worker must have network=none and only the private socket volume.
Do not expose this listener through a host TCP port or put it on a shared volume.
"""
from __future__ import annotations

import os
import re
import selectors
import socketserver
import threading
import time
from urllib.parse import urlsplit

from .browser_network import DestinationPolicy, EgressDenied, Route, read_header


def relay(client, upstream, *, max_bytes=32 * 1024 * 1024, lifetime_s=60):
    deadline, transferred = time.monotonic() + lifetime_s, 0
    with selectors.DefaultSelector() as ready:
        ready.register(client, selectors.EVENT_READ, upstream)
        ready.register(upstream, selectors.EVENT_READ, client)
        while time.monotonic() < deadline:
            for key, _ in ready.select(min(1, max(0, deadline - time.monotonic()))):
                key.fileobj.settimeout(max(0.001, deadline - time.monotonic()))
                chunk = key.fileobj.recv(65536)
                if not chunk: return
                transferred += len(chunk)
                if transferred > max_bytes: return
                key.data.settimeout(max(0.001, deadline - time.monotonic()))
                key.data.sendall(chunk)


def parse_request(header, policy):
    try:
        lines = header.decode("iso-8859-1").split("\r\n")
        method, target, version = lines[0].split(" ")
        if version != "HTTP/1.1" or not re.fullmatch(r"[A-Z]{1,20}", method): raise ValueError()
        if method == "CONNECT":
            parsed = urlsplit("https://" + target)
            if parsed.path or parsed.query or parsed.fragment: raise ValueError()
            scheme, host, port = "https", parsed.hostname, parsed.port or 443
            if parsed.username is not None or parsed.password is not None: raise ValueError()
        else:
            parsed = urlsplit(target)
            if parsed.scheme != "http" or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.fragment:
                raise ValueError()
            scheme, host, port = "http", parsed.hostname, parsed.port or 80
        destination = policy.resolve(scheme, host, port)
        if method == "CONNECT": return destination, None, 0
        # One absolute-form HTTP request per TCP connection. Direct HTTP traffic
        # cannot smuggle a second request to an unvalidated destination.
        authority = parsed.netloc.encode("ascii")
        path = (parsed.path or "/") + (("?" + parsed.query) if parsed.query else "")
        headers, seen, body_size = [], set(), 0
        for line in lines[1:]:
            if not line: continue
            key, value = line.split(":", 1)
            lower = key.lower()
            if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]{1,100}", key) or lower in seen: raise ValueError()
            seen.add(lower)
            if lower in {"transfer-encoding", "upgrade", "expect", "trailer"}: raise ValueError()
            if any(ord(c) < 32 or ord(c) == 127 for c in value.replace("\t", "")): raise ValueError()
            if lower == "content-length" and (not value.strip().isdigit() or int(value.strip()) > 1024 * 1024): raise ValueError()
            if lower == "content-length": body_size = int(value.strip())
            if lower in {"host", "connection", "proxy-connection", "proxy-authorization", "keep-alive"}: continue
            headers.append(line.encode("iso-8859-1"))
        forwarded = (method + " " + path + " HTTP/1.1\r\n").encode("ascii")
        forwarded += b"Host: " + authority + b"\r\nConnection: close\r\n"
        return destination, forwarded + b"\r\n".join(headers) + (b"\r\n" if headers else b"") + b"\r\n", body_size
    except (ValueError, TypeError, UnicodeError): raise EgressDenied() from None


class Gateway(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    request_queue_size = 16

    def __init__(self, path, policy: DestinationPolicy, route: Route, *, max_connections=16, audit=None):
        self.policy, self.route = policy, route
        self.audit = audit or (lambda event, target: None)
        self.slots = threading.BoundedSemaphore(max_connections)
        super().__init__(path, GatewayHandler)
        os.chmod(path, 0o600)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try: super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try: super().process_request_thread(request, client_address)
        finally: self.slots.release()

    def handle_error(self, request, client_address):
        pass  # Never log headers, query strings, body values or proxy credentials.


class GatewayHandler(socketserver.BaseRequestHandler):
    def handle(self):
        client = self.request
        client.settimeout(15)
        upstream, connected = None, False
        try:
            destination, forwarded, body_size = parse_request(read_header(client), self.server.policy)
            upstream = self.server.route.connect(destination)
            self.server.audit("connected", destination.origin)
            if forwarded is None: client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            else: upstream.sendall(forwarded)
            connected = True
            if forwarded is None:
                relay(client, upstream)
            else:
                deadline = time.monotonic() + 60
                while body_size:
                    client.settimeout(max(0.001, deadline - time.monotonic()))
                    if time.monotonic() >= deadline: raise EgressDenied()
                    chunk = client.recv(min(65536, body_size))
                    if not chunk: raise EgressDenied()
                    upstream.settimeout(max(0.001, deadline - time.monotonic()))
                    upstream.sendall(chunk)
                    body_size -= len(chunk)
                transferred = 0
                while time.monotonic() < deadline:
                    upstream.settimeout(max(0.001, deadline - time.monotonic()))
                    chunk = upstream.recv(65536)
                    if not chunk: break
                    transferred += len(chunk)
                    if transferred > 32 * 1024 * 1024: break
                    client.settimeout(max(0.001, deadline - time.monotonic()))
                    client.sendall(chunk)
        except (EgressDenied, OSError):
            self.server.audit("denied", None)
            if not connected:
                try: client.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                except OSError: pass
        finally:
            if upstream is not None: upstream.close()
