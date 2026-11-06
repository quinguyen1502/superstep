"""Disposable destination and authenticated numeric-CONNECT proxy; synthetic data only."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import socket
import ssl
import threading
from urllib.parse import urlsplit

from app.engine.browser_gateway import relay

LOCK, STATS = threading.Lock(), {"requests": [], "connects": [], "auth_rejections": 0, "effects": []}
AUTH = "Basic " + base64.b64encode(b"synthetic-user:synthetic-password").decode()


def record(key, value):
    with LOCK:
        STATS[key].append(value)
        with open("/tmp/fixture-stats.json", "w") as stream: json.dump(STATS, stream)


class Destination(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_POST(self):
        size=int(self.headers.get('Content-Length','0'))
        if self.path!='/effect' or size>1024:self.send_error(400);return
        self.rfile.read(size)
        record('effects',{'path':'/effect'})
        self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'{}')

    def do_GET(self):
        record("requests", {"path": self.path.split("?", 1)[0], "leaked_proxy_auth": "Proxy-Authorization" in self.headers, "host": self.headers.get("Host", ""), "profile_cookie": self.headers.get("Cookie", "") == "login=synthetic-cookie"})
        if self.path.startswith("/redirect"):
            self.send_response(302); self.send_header("Location", "http://127.0.0.1:9090/private"); self.end_headers(); return
        if self.path.startswith("/hostile"):
            body = b'''<html><h1>fixture</h1><img src="http://127.0.0.1:9090/image">
            <script>fetch('http://metadata.test:8080/secret').catch(()=>{});
            new WebSocket('wss://127.0.0.1:9090/socket');
            navigator.serviceWorker.register('/sw.js').catch(()=>{});</script></html>'''
        elif self.path.startswith("/sw.js"):
            body = b"self.addEventListener('activate',()=>fetch('http://127.0.0.1:9090/service-worker'))"
        elif self.path.startswith("/effect-form"):
            body = b'''<html><h1>Effect fixture</h1><button onclick="fetch('/effect',{method:'POST'}).then(()=>document.getElementById('status').textContent='Submitted')">Submit effect</button><p id="status">Ready</p></html>'''
        elif self.path.startswith("/profile"):
            body = b'''<html><h1>Profile fixture</h1><p id="status">Anonymous</p><p>synthetic-cookie</p>
            <script>if(localStorage.getItem('login')==='synthetic-storage')document.getElementById('status').textContent='Stored login';
            document.body.insertAdjacentHTML('beforeend','<p>'+localStorage.getItem('login')+'</p>')</script></html>'''
        elif self.path.startswith("/form"):
            body = b'''<html><h1>Form fixture</h1><input aria-label="Name" value="sensitive-prefilled-value">
            <button onclick="document.getElementById('status').textContent='Submitted'">Submit fixture</button>
            <p id="status">Ready</p></html>'''
        elif self.path.startswith("/hang"):
            body = b'<html><button onclick="while(true){}">Hang fixture</button></html>'
        else: body = b"<html><h1>allowed fixture</h1></html>"
        self.send_response(200); self.send_header("Content-Type", "application/javascript" if self.path.startswith("/sw.js") else "text/html"); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)


class Proxy(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_CONNECT(self):
        if self.headers.get("Proxy-Authorization") != AUTH:
            self.send_response(407); self.end_headers(); return
        parsed = urlsplit("http://" + self.path)
        try: ipaddress.ip_address(parsed.hostname)
        except ValueError:
            self.send_response(403); self.end_headers(); return
        record("connects", {"address": parsed.hostname, "port": parsed.port})
        if parsed.port == 8082:  # controlled upstream failure: no direct route fallback permitted
            self.send_response(502); self.end_headers(); return
        try:
            with socket.create_connection((parsed.hostname, parsed.port), timeout=5) as upstream:
                self.send_response(200); self.end_headers()
                relay(self.connection, upstream, lifetime_s=15)
        except OSError: pass


threading.Thread(target=ThreadingHTTPServer(("0.0.0.0", 8081), Proxy).serve_forever, daemon=True).start()
threading.Thread(target=ThreadingHTTPServer(("0.0.0.0", 8082), Destination).serve_forever, daemon=True).start()
secure = ThreadingHTTPServer(("0.0.0.0", 8443), Destination)
tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
tls.load_cert_chain("/fixture/fixture-cert.pem", "/fixture/fixture-key.pem")
secure.socket = tls.wrap_socket(secure.socket, server_side=True)
threading.Thread(target=secure.serve_forever, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 8080), Destination).serve_forever()
