# network_manager/network_manager.py

import socket
import threading
import json
import os
import http.server
import socketserver


class NetworkManager:
    """
    Manual Python class version of NetworkManager.
    Handles container networking, message passing, and simple web serving.
    Compatible with Termux and Python 3.10+ without external dependencies.
    """

    def __init__(self):
        self.connections = {}   # dict[(container_a, container_b)] = True
        self.servers = {}       # dict[container_id] = Thread
        self.ports = {}         # dict[container_id] = port
        self.running = True

    # ----------------------------
    # Container Socket Server
    # ----------------------------
    def start_container_network(self, container_id: str, port: int):
        if container_id in self.servers:
            raise RuntimeError(f"Network already running for {container_id}")

        self.ports[container_id] = port

        def server():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", port))
            sock.listen(5)

            print(f"[Network] {container_id} listening on 127.0.0.1:{port}")

            while self.running:
                try:
                    client, _ = sock.accept()
                    threading.Thread(
                        target=self._handle_client,
                        args=(container_id, client),
                        daemon=True
                    ).start()
                except Exception:
                    break

            sock.close()

        t = threading.Thread(target=server, daemon=True)
        t.start()
        self.servers[container_id] = t

    def _handle_client(self, container_id: str, client_socket: socket.socket):
        try:
            data = client_socket.recv(4096)
            if not data:
                return

            message = json.loads(data.decode())
            print(f"[Network:{container_id}] RX:", message)

            response = {
                "status": "ok",
                "container": container_id,
                "echo": message
            }
            client_socket.send(json.dumps(response).encode())
        except Exception as e:
            print(f"[Network:{container_id}] Error:", e)
        finally:
            client_socket.close()

    # ----------------------------
    # Connect / Disconnect Containers
    # ----------------------------
    def connect_containers(self, container_a: str, container_b: str):
        self.connections[(container_a, container_b)] = True
        self.connections[(container_b, container_a)] = True

    def disconnect_containers(self, container_a: str, container_b: str):
        self.connections.pop((container_a, container_b), None)
        self.connections.pop((container_b, container_a), None)

    # ----------------------------
    # Send Message
    # ----------------------------
    def send_message(self, from_container: str, to_container: str, message):
        if (from_container, to_container) not in self.connections:
            raise RuntimeError("Containers are not connected")
        if to_container not in self.ports:
            raise RuntimeError(f"{to_container} has no network port")

        port = self.ports[to_container]

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", port))
            payload = {"from": from_container, "data": message}
            sock.send(json.dumps(payload).encode())
            response = sock.recv(4096)
            sock.close()
            return json.loads(response.decode())
        except Exception as e:
            raise RuntimeError(f"Send failed: {e}")

    # ----------------------------
    # Port Mapping (Host -> Container)
    # ----------------------------
    def map_port(self, container_id: str, host_port: int, container_port: int):
        def forwarder():
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("0.0.0.0", host_port))
            server.listen(5)

            print(f"[PortMap] {container_id}: {host_port} -> {container_port}")

            while self.running:
                try:
                    client, _ = server.accept()
                    forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    forward.connect(("127.0.0.1", container_port))

                    threading.Thread(target=self._pipe, args=(client, forward), daemon=True).start()
                    threading.Thread(target=self._pipe, args=(forward, client), daemon=True).start()
                except Exception:
                    break

            server.close()

        threading.Thread(target=forwarder, daemon=True).start()

    def _pipe(self, src: socket.socket, dst: socket.socket):
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.send(data)
        except Exception:
            pass
        finally:
            src.close()
            dst.close()

    # ----------------------------
    # Container Web Server
    # ----------------------------
    def serve_container_web(self, container_id: str, fs_manager, port: int = 8080):
        container_path = os.path.join(fs_manager.base_path, container_id)
        web_root = os.path.join(container_path, "app")

        if not os.path.exists(web_root):
            raise RuntimeError("No /app directory found")

        handler = http.server.SimpleHTTPRequestHandler

        def server():
            os.chdir(web_root)
            with socketserver.TCPServer(("", port), handler) as httpd:
                print(f"[WEB] {container_id} → http://localhost:{port}")
                httpd.serve_forever()

        thread = threading.Thread(target=server, daemon=True)
        thread.start()
        return port

    # ----------------------------
    # List Active Networks
    # ----------------------------
    def list_networks(self):
        return {
            cid: {"port": self.ports.get(cid), "active": cid in self.servers}
            for cid in self.ports
        }

    # ----------------------------
    # Shutdown
    # ----------------------------
    def shutdown(self):
        self.running = False
        print("[Network] Shutdown complete")
