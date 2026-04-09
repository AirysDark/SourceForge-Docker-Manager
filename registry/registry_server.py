# registry/registry_server.py

import http.server
import socketserver
import os
import json
from urllib.parse import urlparse, parse_qs
import time

REGISTRY_DIR = "registry_storage"
PORT = 5000

os.makedirs(REGISTRY_DIR, exist_ok=True)


class RegistryHandler(http.server.BaseHTTPRequestHandler):

    # ----------------------------
    # GET Requests
    # ----------------------------
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/list":
            self._handle_list()
        elif parsed.path == "/pull":
            self._handle_pull(parsed)
        elif parsed.path == "/":
            self._handle_webpage()
        else:
            self.send_error(404)

    # ----------------------------
    # POST Requests
    # ----------------------------
    def do_POST(self):
        if self.path == "/push":
            self._handle_push()
        else:
            self.send_error(404)

    # ----------------------------
    # List images (JSON)
    # ----------------------------
    def _handle_list(self):
        files = os.listdir(REGISTRY_DIR)
        images = [f for f in files if f.endswith(".tar")]
        self._send_json({"images": images})

    # ----------------------------
    # Push image
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
    # Pull image
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

    # ----------------------------
    # Web interface for browsing images
    # ----------------------------
    def _handle_webpage(self):
        files = os.listdir(REGISTRY_DIR)
        images = [f for f in files if f.endswith(".tar")]

        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SourceForge Docker Registry</title>
<style>
body { font-family: Arial, sans-serif; background: #f4f4f9; padding: 20px; }
h1 { color: #333; }
table { border-collapse: collapse; width: 100%; margin-top: 20px; }
th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
th { background: #eee; }
tr:nth-child(even) { background: #fafafa; }
a { color: #007bff; text-decoration: none; }
a:hover { text-decoration: underline; }
</style>
</head>
<body>
<h1>Registry Images</h1>
<table>
<tr><th>Image File</th><th>Size (KB)</th><th>Created</th><th>Download</th></tr>
"""

        for img in images:
            path = os.path.join(REGISTRY_DIR, img)
            size = os.path.getsize(path) // 1024
            created_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getctime(path)))
            html += f'<tr><td>{img}</td><td>{size}</td><td>{created_str}</td>'
            html += f'<td><a href="/pull?name={img}">Download</a></td></tr>'

        html += "</table></body></html>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    # ----------------------------
    # Send JSON
    # ----------------------------
    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


# ----------------------------
# Run Registry Server
# ----------------------------
def run_registry():
    with socketserver.TCPServer(("", PORT), RegistryHandler) as httpd:
        print(f"[Registry] Running on port {PORT}")
        httpd.serve_forever()


# ----------------------------
# Entry Point
# ----------------------------
if __name__ == "__main__":
    run_registry()