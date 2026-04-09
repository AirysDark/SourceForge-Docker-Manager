# network_manager/kube.py

import threading
import time
import os
import json
from datetime import datetime

# ----------------------------
# Manual Python Data Classes
# ----------------------------
class DeploymentSpec:
    def __init__(self, name: str, image: str, replicas: int = 1, port: int = 8000):
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        if not isinstance(image, str):
            raise TypeError("image must be a string")
        if not isinstance(replicas, int) or replicas < 0:
            raise TypeError("replicas must be a non-negative integer")
        if not isinstance(port, int):
            raise TypeError("port must be an integer")
        self.name = name
        self.image = image
        self.replicas = replicas
        self.port = port

    def to_dict(self):
        return {"name": self.name, "image": self.image, "replicas": self.replicas, "port": self.port}

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            image=data["image"],
            replicas=data.get("replicas", 1),
            port=data.get("port", 8000)
        )

# ----------------------------
# KubeLite Orchestrator
# ----------------------------
class KubeLite:
    """
    Lightweight orchestrator with:
    - Multi-replica deployments
    - Self-healing & restart
    - Persistent service state
    - Auto-snapshot integration
    - Health checks & service status
    - Interactive CLI
    """

    def __init__(self, engine, runtime_mgr, network_mgr, image_mgr, state_file="kube_state.json"):
        self.engine = engine
        self.runtime_mgr = runtime_mgr
        self.network_mgr = network_mgr
        self.image_mgr = image_mgr

        self.state_file = state_file
        self.running = False
        self.state = {}  # service_name -> {"pods": [...], "index": 0, "last_snapshot": ...}
        self.lock = threading.Lock()

        self._load_state()

    # ----------------------------
    # Load / Save State
    # ----------------------------
    def _load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                self.state = json.load(f)
        else:
            self.state = {}

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    # ----------------------------
    # Load Deployment Spec
    # ----------------------------
    def load(self, filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
        deployments = {}
        for name, spec in data.get("deployments", {}).items():
            deployments[name] = DeploymentSpec.from_dict(spec)
        return deployments

    # ----------------------------
    # Start / Stop
    # ----------------------------
    def start(self, config):
        if self.running:
            raise RuntimeError("KubeLite already running")
        self.running = True
        thread = threading.Thread(target=self._controller_loop, args=(config,), daemon=True)
        thread.start()
        print("[KubeLite] Controller started")

    def stop(self):
        self.running = False
        self._save_state()
        print("[KubeLite] Controller stopped")

    # ----------------------------
    # Main Controller Loop
    # ----------------------------
    def _controller_loop(self, config):
        while self.running:
            try:
                self._reconcile(config)
            except Exception as e:
                print("[KubeLite] Error:", e)
            time.sleep(3)

    # ----------------------------
    # Reconciliation Logic
    # ----------------------------
    def _reconcile(self, deployments):
        for name, spec in deployments.items():
            desired = spec.replicas
            existing = self._get_existing(name)

            # Scale UP
            for i in range(len(existing), desired):
                cid = f"{name}-{i}"
                print(f"[KubeLite] Creating {cid}")
                self.engine.create_container_from_image(spec.image, cid, self.image_mgr)
                self.engine.start_container(cid, self.runtime_mgr)
                self.network_mgr.start_container_network(cid, spec.port + i)

            # Scale DOWN
            for cid in existing[desired:]:
                print(f"[KubeLite] Removing {cid}")
                try:
                    self.engine.stop_container(cid, self.runtime_mgr)
                    self.engine.remove_container(cid)
                except Exception:
                    pass

            # Self-Healing
            for cid in self._get_existing(name):
                if not self.runtime_mgr.is_running(cid):
                    print(f"[KubeLite] Restarting {cid}")
                    self.engine.start_container(cid, self.runtime_mgr)

        # Auto-Snapshot
        self._auto_snapshot()
        # Update state
        self._update_services(deployments)

    # ----------------------------
    # Auto Snapshot
    # ----------------------------
    def _auto_snapshot(self):
        with self.lock:
            for svc_name, data in self.state.items():
                for cid in data.get("pods", []):
                    try:
                        snap = self.engine.snapshot_container(cid)
                        data["last_snapshot"] = snap
                        print(f"[KubeLite] Auto-snapshot {cid} → {snap}")
                    except Exception:
                        pass
            self._save_state()

    # ----------------------------
    # Existing Containers for a Service
    # ----------------------------
    def _get_existing(self, prefix):
        return [cid for cid in self.engine.list_containers() if cid.startswith(prefix + "-")]

    # ----------------------------
    # Update Load Balancer State
    # ----------------------------
    def _update_services(self, deployments):
        with self.lock:
            for name in deployments:
                pods = self._get_existing(name)
                if pods:
                    if name not in self.state:
                        self.state[name] = {"pods": [], "index": 0, "last_snapshot": None}
                    self.state[name]["pods"] = pods
            self._save_state()

    # ----------------------------
    # Round-Robin Request Routing
    # ----------------------------
    def request(self, service_name, message):
        with self.lock:
            if service_name not in self.state or not self.state[service_name]["pods"]:
                raise RuntimeError(f"Service '{service_name}' not available")
            svc = self.state[service_name]
            pod = svc["pods"][svc["index"]]
            svc["index"] = (svc["index"] + 1) % len(svc["pods"])
        return {"target": pod, "message": message}

    # ----------------------------
    # Health Check Utility
    # ----------------------------
    def health_check(self, service_name):
        pods = self._get_existing(service_name)
        return {cid: self.runtime_mgr.is_running(cid) for cid in pods}

    # ----------------------------
    # Full Service Status
    # ----------------------------
    def status(self):
        report = {}
        for svc, data in self.state.items():
            report[svc] = {
                "pods": data["pods"],
                "running": {cid: self.runtime_mgr.is_running(cid) for cid in data["pods"]},
                "last_snapshot": data.get("last_snapshot")
            }
        return report

    # ----------------------------
    # Interactive CLI
    # ----------------------------
    def cli(self):
        print("KubeLite CLI (type 'help' for commands)")
        while True:
            try:
                cmd = input("kube-lite> ").strip()
                if not cmd:
                    continue
                if cmd.lower() in ["exit", "quit"]:
                    print("Exiting KubeLite CLI...")
                    break
                self._parse_cli(cmd)
            except KeyboardInterrupt:
                print("\nExiting KubeLite CLI...")
                break
            except Exception as e:
                print("Error:", e)

    def _parse_cli(self, cmd):
        parts = cmd.split()
        action = parts[0].lower()

        if action == "help":
            print("Commands:\n"
                  "  status                - Show all services & pods\n"
                  "  health <service>      - Show pod health\n"
                  "  snapshot              - Trigger auto-snapshot\n"
                  "  scale <service> <n>   - Scale a service\n"
                  "  exit / quit           - Exit CLI")
        elif action == "status":
            print(json.dumps(self.status(), indent=2))
        elif action == "health" and len(parts) >= 2:
            print(json.dumps(self.health_check(parts[1]), indent=2))
        elif action == "snapshot":
            self._auto_snapshot()
            print("Snapshots triggered.")
        elif action == "scale" and len(parts) >= 3:
            svc, n = parts[1], int(parts[2])
            self._scale_service(svc, n)
        else:
            print("Unknown command. Type 'help' for available commands.")

    # ----------------------------
    # Scale a Service
    # ----------------------------
    def _scale_service(self, service_name, replicas):
        with self.lock:
            existing = self._get_existing(service_name)
            current = len(existing)
            print(f"[KubeLite] Scaling {service_name}: {current} → {replicas}")

            if replicas > current:
                for i in range(current, replicas):
                    cid = f"{service_name}-{i}"
                    spec = DeploymentSpec(service_name, service_name)  # simple default image mapping
                    self.engine.create_container_from_image(spec.image, cid, self.image_mgr)
                    self.engine.start_container(cid, self.runtime_mgr)
                    self.network_mgr.start_container_network(cid, 8000 + i)
            elif replicas < current:
                for cid in existing[replicas:]:
                    self.engine.stop_container(cid, self.runtime_mgr)
                    self.engine.remove_container(cid)

            # Update state
            self._update_services({service_name: DeploymentSpec(service_name, service_name, replicas)})
            print(f"[KubeLite] Scaling complete for {service_name}")
