"""Refuse to seed a test fixture through a port already owned by another local service."""
import socket
import sys

ports = [int(value) for value in sys.argv[1:]]
if len(ports) != len(set(ports)) or any(not 1024 <= port <= 65535 for port in ports):
    raise SystemExit("Choose distinct local test ports between 1024 and 65535")
reserved = []
try:
    for port in ports:
        probe = socket.socket()
        reserved.append(probe)
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: probe.bind(("127.0.0.1", port))
        except OSError: raise SystemExit(f"Local test port {port} is in use; choose another port") from None
finally:
    for probe in reserved: probe.close()
