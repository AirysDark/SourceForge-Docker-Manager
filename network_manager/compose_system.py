# network_manager/compose_system.py

import json
import os

try:
    import yaml
except ImportError:
    yaml = None  # YAML support requires PyYAML


class ComposeSystem:
    def __init__(self, engine, image_mgr, runtime_mgr, network_mgr, fs_manager):
        self.engine = engine
        self.image_mgr = image_mgr
        self.runtime_mgr = runtime_mgr
        self.network_mgr = network_mgr
        self.fs_manager = fs_manager

    # ----------------------------
    # Load Compose File (JSON or YAML)
    # ----------------------------
    def load(self, filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Compose file not found: {filepath}")

        if filepath.endswith((".yml", ".yaml")):
            if yaml is None:
                raise ImportError("PyYAML is required to load YAML files. Install with `pip install pyyaml`")
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
        else:
            with open(filepath, "r") as f:
                data = json.load(f)

        return data

    # ----------------------------
    # Resolve Dependency Order
    # ----------------------------
    def resolve_order(self, services):
        resolved = []
        visited = set()

        def visit(name):
            if name in visited:
                return
            visited.add(name)
            service = services[name]
            deps = service.get("depends_on", [])
            for dep in deps:
                visit(dep)
            resolved.append(name)

        for name in services:
            visit(name)

        return resolved

    # ----------------------------
    # Start Stack
    # ----------------------------
    def up(self, config):
        services = config["services"]
        order = self.resolve_order(services)

        print("[Compose] Startup order:", order)

        for name in order:
            svc = services[name]
            image = svc["image"]
            cid = svc["container_name"]

            print(f"[Compose] Starting {name} ({cid})")

            # Create container
            self.engine.create_container_from_image(image, cid, self.image_mgr)

            # Start runtime
            self.engine.start_container(cid, self.runtime_mgr)

            # Start networking
            for port in svc.get("ports", []):
                self.network_mgr.start_container_network(cid, port)

        # Connect all containers
        self._connect_all(services)

    # ----------------------------
    # Stop Stack
    # ----------------------------
    def down(self, config):
        services = config["services"]
        for name, svc in services.items():
            cid = svc["container_name"]
            print(f"[Compose] Stopping {cid}")
            try:
                self.engine.stop_container(cid, self.runtime_mgr)
            except Exception:
                pass

    # ----------------------------
    # Connect All Services
    # ----------------------------
    def _connect_all(self, services):
        names = list(services.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a = services[names[i]]["container_name"]
                b = services[names[j]]["container_name"]
                self.network_mgr.connect_containers(a, b)
        print("[Compose] Network mesh connected")

    # ----------------------------
    # Status
    # ----------------------------
    def status(self, config):
        services = config["services"]
        status = {}
        for name, svc in services.items():
            cid = svc["container_name"]
            running = self.runtime_mgr.is_running(cid)
            status[name] = {
                "container": cid,
                "running": running
            }
        return status