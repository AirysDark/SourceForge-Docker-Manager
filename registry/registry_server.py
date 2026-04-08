# registry/registry_server.py

import http.server
import socketserver
import os
import json
from urllib.parse import urlparse, parse_qs


REGISTRY_DIR = "registry_storage"
PORT = 5000

os.makedirs(REGISTRY_DIR, exist_ok=True)


class RegistryHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/list":
            self._handle_list()

        elif parsed.path == "/pull":
            self._handle_pull(parsed)

        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/push":
            self._handle_push()
        else:
            self.send_error(404)

    # ----------------------------
    # LIST IMAGES
    # ----------------------------
    def _handle_list(self):
        files = os.listdir(REGISTRY_DIR)

        images = [f for f in files if f.endswith(".tar")]

        self._send_json({"images": images})

    # ----------------------------
    # PUSH IMAGE
    # ----------------------------
    def _handle_push(self):
        filename = self.headers.get("X-Filename")

        if not filename:
            self.send_error(400, "Missing filename header")
            return

        filepath = os.path.join(REGISTRY_DIR, filename)

        length = int(self.headers.get("Content-Length", 0))

        with open(filepath, "wb") as f:
            f.write(self.rfile.read(length))

        print(f"[Registry] Uploaded: {filename}")

        self._send_json({"status": "ok"})

    # ----------------------------
    # PULL IMAGE
    # ----------------------------
    def _handle_pull(self, parsed):
        params = parse_qs(parsed.query)

        name = params.get("name", [None])[0]

        if not name:
            self.send_error(400, "Missing name")
            return

        filepath = os.path.join(REGISTRY_DIR, name)

        if not os.path.exists(filepath):
            self.send_error(404, "Image not found")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()

        with open(filepath, "rb") as f:
            self.wfile.write(f.read())

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def run_registry():
    with socketserver.TCPServer(("", PORT), RegistryHandler) as httpd:
        print(f"[Registry] Running on port {PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    run_registry()