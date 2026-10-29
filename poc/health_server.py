import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_error(404)
            return

        ready = False
        try:
            with socket.create_connection(("127.0.0.1", 5555), timeout=1):
                ready = True
        except OSError:
            pass

        payload = {
            "service": "harvey-render-free-poc",
            "dashboard": "loopback-only",
            "dashboard_ready": ready,
            "note": "Disposable build/boot test; model authentication and persistent storage are not configured."
        }
        body = json.dumps(payload).encode()
        self.send_response(200 if ready else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


port = int(os.environ.get("PORT", "10000"))
ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
