# main.py

import os
import sys
import json
import traceback
from datetime import datetime

from engine_core.engine_core import EngineCore
from image_manager.image_manager import ImageManager
from network_manager.network_manager import NetworkManager
from runtime_manager.runtime_manager import RuntimeManager
from fs_snapshots.fs_snapshots import FileSystemManager
from fs_snapshots.build_system import BuildSystem
from docker_support.dockerfile_parser import DockerfileParser
from network_manager.compose_system import ComposeSystem
from network_manager.kube import Kube
from registry.registry_server import run_registry


class ContainerEngineApp:
    def __init__(self):
        # Core managers
        self.fs_manager = FileSystemManager()
        self.engine = EngineCore(self.fs_manager)
        self.image_mgr = ImageManager(self.fs_manager)
        self.network_mgr = NetworkManager()
        self.runtime_mgr = RuntimeManager(self.fs_manager)

        # Build system
        self.builder = BuildSystem(self.fs_manager, self.image_mgr)

        # Compose system
        self.compose = ComposeSystem(
            self.engine,
            self.image_mgr,
            self.runtime_mgr,
            self.network_mgr,
            self.fs_manager
        )

        # Kubernetes orchestration
        self.kube = Kube(
            self.engine,
            self.runtime_mgr,
            self.network_mgr,
            self.image_mgr
        )

        # Load default docker config if exists
        docker_config_path = "docker.json"
        if os.path.exists(docker_config_path):
            with open(docker_config_path, "r") as f:
                self.docker_config = json.load(f)
        else:
            self.docker_config = {"default_registry": "http://localhost:5000", "registries": []}

    # ----------------------------
    # Logging
    # ----------------------------
    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def error(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {msg}")

    # ----------------------------
    # Container commands
    # ----------------------------
    def cmd_create(self, cid):
        self.engine.create_container(cid)
        self.log(f"Container created: {cid}")

    def cmd_start(self, cid):
        self.engine.start_container(cid, self.runtime_mgr)
        self.log(f"Container started: {cid}")

    def cmd_stop(self, cid):
        self.engine.stop_container(cid, self.runtime_mgr)
        self.log(f"Container stopped: {cid}")

    def cmd_remove(self, cid):
        self.engine.remove_container(cid)
        self.log(f"Container removed: {cid}")

    def cmd_exec(self, cid, command):
        result = self.runtime_mgr.exec_in_container(cid, command)
        print(result)

    def cmd_shell(self, cid):
        self.runtime_mgr.exec_interactive(cid, "/bin/sh")

    # ----------------------------
    # Snapshot commands
    # ----------------------------
    def cmd_snapshot(self, cid):
        snap = self.fs_manager.snapshot_container(cid)
        self.log(f"Snapshot created: {snap}")

    def cmd_restore(self, cid, snap):
        self.engine.restore_container(cid, snap)
        self.log(f"Restored {cid} → {snap}")

    def cmd_snapshots(self, cid):
        for s in self.fs_manager.list_snapshots(cid):
            print(s)

    def cmd_diff(self, snap1, snap2):
        diff = self.fs_manager.diff_snapshots(snap1, snap2)
        print(json.dumps(diff, indent=2))

    def cmd_prune(self, cid):
        self.fs_manager.prune_snapshots(cid)
        self.log(f"Pruned snapshots for {cid}")

    # ----------------------------
    # Image / build commands
    # ----------------------------
    def cmd_build(self, image, source=None):
        if source is None:
            source = "Dockerfile"

        if os.path.isfile(source) and not source.endswith(".json"):
            self.log(f"Parsing Dockerfile: {source}")
            parser = DockerfileParser(source)
            instructions = parser.parse()
        elif source.endswith(".json"):
            if not os.path.exists(source):
                raise FileNotFoundError(source)
            self.log(f"Using JSON instructions: {source}")
            with open(source, "r") as f:
                instructions = json.load(f)
        else:
            raise ValueError("Invalid build source")

        layers = self.builder.build(image, instructions)
        self.log(f"Image built: {image}")
        for l in layers:
            print("  ", l)

    def cmd_images(self):
        print(json.dumps(self.image_mgr.list_images(), indent=2))

    def cmd_run(self, image, cid):
        self.engine.create_container_from_image(image, cid, self.image_mgr)
        self.engine.start_container(cid, self.runtime_mgr)
        self.log(f"Container {cid} started from image {image}")

    def cmd_export(self, image, tag="latest"):
        path = self.image_mgr.export_image(image, tag)
        self.log(f"Exported image → {path}")

    def cmd_import(self, tarfile):
        name = self.image_mgr.import_image(tarfile)
        self.log(f"Imported image → {name}")

    # ----------------------------
    # Registry commands
    # ----------------------------
    def cmd_registry_start(self):
        self.log("Starting registry server on port 5000...")
        run_registry()

    def cmd_push(self, image, url=None):
        if url is None:
            url = self.docker_config.get("default_registry")
        self.image_mgr.push_image(image, url)
        self.log(f"Pushed {image} → {url}")

    def cmd_pull(self, tar_name, url=None):
        if url is None:
            url = self.docker_config.get("default_registry")
        self.image_mgr.pull_remote(tar_name, url)
        self.log(f"Pulled {tar_name} from {url}")

    def cmd_registry_list(self, url=None):
        from urllib import request
        if url is None:
            url = self.docker_config.get("default_registry")
        with request.urlopen(f"{url}/list") as response:
            print(json.dumps(json.load(response), indent=2))

    # ----------------------------
    # Compose commands
    # ----------------------------
    def cmd_compose_up(self, file):
        config = self.compose.load(file)
        self.compose.up(config)

    def cmd_compose_down(self, file):
        config = self.compose.load(file)
        self.compose.down(config)

    def cmd_compose_status(self, file):
        config = self.compose.load(file)
        status = self.compose.status(config)
        print(json.dumps(status, indent=2))

    # ----------------------------
    # Kubernetes / Kube commands
    # ----------------------------
    def cmd_kube_start(self, file):
        config = self.kube.load(file)
        self.kube.start(config)

    def cmd_kube_stop(self):
        self.kube.stop()

    def cmd_kube_status(self):
        print(json.dumps(self.kube.status(), indent=2))

    # ----------------------------
    # Network / web commands
    # ----------------------------
    def cmd_web(self, cid, port):
        self.network_mgr.serve_container_web(cid, self.fs_manager, int(port))
        self.log(f"Web server running: http://localhost:{port}")

    def cmd_connect(self, a, b):
        self.network_mgr.connect_containers(a, b)
        self.log(f"Connected {a} → {b}")

    def cmd_send(self, a, b, msg):
        response = self.network_mgr.send_message(a, b, json.loads(msg))
        print(json.dumps(response, indent=2))

    # ----------------------------
    # Demo
    # ----------------------------
    def demo(self):
        try:
            self.log("Running demo...")
            self.cmd_create("c1")
            path = os.path.join(self.fs_manager.base_path, "c1/app")
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path, "index.html"), "w") as f:
                f.write("<h1>Hello Container</h1>")
            self.cmd_snapshot("c1")
            self.cmd_web("c1", 8080)
            self.log("Demo complete → open http://localhost:8080")
        except Exception:
            traceback.print_exc()

    # ----------------------------
    # CLI Router
    # ----------------------------
    def run_cli(self):
        if len(sys.argv) < 2:
            print("Usage:")
            print("  compose-up <file>")
            print("  compose-down <file>")
            print("  compose-status <file>")
            print("  kube-start <file>")
            print("  kube-stop")
            print("  kube-status")
            print("  registry / push / pull")
            print("  (all previous commands still supported)")
            return

        cmd = sys.argv[1]

        try:
            if cmd == "compose-up":
                self.cmd_compose_up(sys.argv[2])
            elif cmd == "compose-down":
                self.cmd_compose_down(sys.argv[2])
            elif cmd == "compose-status":
                self.cmd_compose_status(sys.argv[2])
            elif cmd == "kube-start":
                self.cmd_kube_start(sys.argv[2])
            elif cmd == "kube-stop":
                self.cmd_kube_stop()
            elif cmd == "kube-status":
                self.cmd_kube_status()
            elif cmd == "registry":
                self.cmd_registry_start()
            elif cmd == "push":
                self.cmd_push(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
            elif cmd == "pull":
                self.cmd_pull(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
            elif cmd == "registry-list":
                self.cmd_registry_list(sys.argv[2] if len(sys.argv) > 2 else None)
            else:
                self._legacy_router(cmd)

        except Exception:
            self.error("Command failed")
            traceback.print_exc()

    # ----------------------------
    # Legacy router
    # ----------------------------
    def _legacy_router(self, cmd):
        args = sys.argv
        if cmd == "demo":
            self.demo()
        elif cmd == "create":
            self.cmd_create(args[2])
        elif cmd == "start":
            self.cmd_start(args[2])
        elif cmd == "stop":
            self.cmd_stop(args[2])
        elif cmd == "remove":
            self.cmd_remove(args[2])
        elif cmd == "exec":
            self.cmd_exec(args[2], " ".join(args[3:]))
        elif cmd == "shell":
            self.cmd_shell(args[2])
        elif cmd == "snapshot":
            self.cmd_snapshot(args[2])
        elif cmd == "restore":
            self.cmd_restore(args[2], args[3])
        elif cmd == "snapshots":
            self.cmd_snapshots(args[2])
        elif cmd == "diff":
            self.cmd_diff(args[2], args[3])
        elif cmd == "prune":
            self.cmd_prune(args[2])
        elif cmd == "build":
            self.cmd_build(args[2], args[3] if len(args) > 3 else None)
        elif cmd == "images":
            self.cmd_images()
        elif cmd == "run":
            self.cmd_run(args[2], args[3])
        elif cmd == "export":
            self.cmd_export(args[2])
        elif cmd == "import":
            self.cmd_import(args[2])
        elif cmd == "web":
            self.cmd_web(args[2], args[3])
        elif cmd == "connect":
            self.cmd_connect(args[2], args[3])
        elif cmd == "send":
            self.cmd_send(args[2], args[3], args[4])
        else:
            self.error("Unknown command")

# ----------------------------
# CLI Entry function
# ----------------------------
def main_cli():
    app = ContainerEngineApp()
    app.run_cli()

# ----------------------------
# Entry point
# ----------------------------
if __name__ == "__main__":
    main_cli()