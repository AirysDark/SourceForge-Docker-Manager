# network_manager/compose_system.py

import json
import os

try:
    import yaml
except ImportError:
    yaml = None  # YAML support requires PyYAML


class ServiceConfig:
    """
    Manual replacement for Pydantic model.
    Represents one service in a compose configuration.
    """

    def __init__(self, name: str, image: str, container_name: str, ports=None, depends_on=None):
        if not isinstance(name, str):
            raise TypeError(f"name must be str, got {type(name)}")
        if not isinstance(image, str):
            raise TypeError(f"image must be str, got {type(image)}")
        if not isinstance(container_name, str):
            raise TypeError(f"container_name must be str, got {type(container_name)}")
        if ports is None:
            ports = []
        if depends_on is None:
            depends_on = []
        if not isinstance(ports, list) or not all(isinstance(p, int) for p in ports):
            raise TypeError("ports must be a list of integers")
        if not isinstance(depends_on, list) or not all(isinstance(d, str) for d in depends_on):
            raise TypeError("depends_on must be a list of strings")

        self.name = name
        self.image = image
        self.container_name = container_name
        self.ports = ports
        self.depends_on = depends_on

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            image=data["image"],
            container_name=data["container_name"],
            ports=data.get("ports", []),
            depends_on=data.get("depends_on", [])
        )


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

        # Convert dicts to ServiceConfig objects
        services = {}
        for name, svc in data.get("services", {}).items():
            services[name] = ServiceConfig.from_dict({
                "name": name,
                "image": svc.get("image"),
                "container_name": svc.get("container_name", name),
                "ports": svc.get("ports", []),
                "depends_on": svc.get("depends_on", [])
            })
        return services

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
            for dep in getattr(service, "depends_on", []):
                visit(dep)
            resolved.append(name)

        for name in services:
            visit(name)

        return resolved

    # ----------------------------
    # Start Stack
    # ----------------------------
    def up(self, services):
        order = self.resolve_order(services)
        print("[Compose] Startup order:", order)

        for name in order:
            svc = services[name]
            print(f"[Compose] Starting {name} ({svc.container_name})")
            self.engine.create_container_from_image(svc.image, svc.container_name, self.image_mgr)
            self.engine.start_container(svc.container_name, self.runtime_mgr)
            for port in svc.ports:
                self.network_mgr.start_container_network(svc.container_name, port)

        self._connect_all(services)

    # ----------------------------
    # Stop Stack
    # ----------------------------
    def down(self, services):
        for name, svc in services.items():
            print(f"[Compose] Stopping {svc.container_name}")
            try:
                self.engine.stop_container(svc.container_name, self.runtime_mgr)
            except Exception:
                pass

    # ----------------------------
    # Connect All Services
    # ----------------------------
    def _connect_all(self, services):
        names = list(services.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a = services[names[i]].container_name
                b = services[names[j]].container_name
                self.network_mgr.connect_containers(a, b)
        print("[Compose] Network mesh connected")

    # ----------------------------
    # Status
    # ----------------------------
    def status(self, services):
        status = {}
        for name, svc in services.items():
            running = self.runtime_mgr.is_running(svc.container_name)
            status[name] = {
                "container": svc.container_name,
                "running": running
            }
        return status
