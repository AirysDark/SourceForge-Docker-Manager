# engine_core/engine_core.py

import os
import json
from datetime import datetime


class EngineCore:
    def __init__(self, fs_manager, state_file="engine_state.json"):
        self.fs_manager = fs_manager
        self.state_file = state_file
        self.containers = {}

        # Config
        self.auto_snapshot_on_stop = True
        self.snapshot_retention = 5

        self._load_state()

    # ----------------------------
    # State Persistence
    # ----------------------------
    def _load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                self.containers = json.load(f)
        else:
            self.containers = {}

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.containers, f, indent=2)

    # ----------------------------
    # Container Lifecycle
    # ----------------------------
    def create_container(self, container_id):
        if container_id in self.containers:
            raise ValueError(f"Container '{container_id}' already exists")

        path = self.fs_manager.create_container_root(container_id)

        self.containers[container_id] = {
            "id": container_id,
            "path": path,
            "status": "stopped",
            "created_at": datetime.now().isoformat(),
            "last_started": None,
            "last_stopped": None,
            "last_snapshot": None,
            "snapshots": []
        }

        self._save_state()
        return path

    def start_container(self, container_id, runtime_manager=None, command="bash"):
        container = self._get_container(container_id)

        if container["status"] == "running":
            raise RuntimeError(f"Container '{container_id}' is already running")

        if runtime_manager:
            runtime_manager.run_container(container_id, command)

        container["status"] = "running"
        container["last_started"] = datetime.now().isoformat()

        self._save_state()

    def stop_container(self, container_id, runtime_manager=None):
        container = self._get_container(container_id)

        if container["status"] == "stopped":
            raise RuntimeError(f"Container '{container_id}' is already stopped")

        if runtime_manager:
            runtime_manager.stop_container(container_id)

        container["status"] = "stopped"
        container["last_stopped"] = datetime.now().isoformat()

        # ----------------------------
        # AUTO SNAPSHOT
        # ----------------------------
        if self.auto_snapshot_on_stop:
            snapshot_id = self.fs_manager.snapshot_container(container_id)

            container["last_snapshot"] = snapshot_id
            container["snapshots"].append(snapshot_id)

            # ----------------------------
            # PROPER SNAPSHOT PRUNING (FIXED)
            # ----------------------------
            try:
                self.fs_manager.prune_snapshots(
                    container_id,
                    keep_last=self.snapshot_retention
                )

                # Keep state in sync
                container["snapshots"] = self.fs_manager.list_snapshots(container_id)

            except Exception:
                pass  # never break lifecycle

        self._save_state()

    def remove_container(self, container_id, force=False):
        container = self._get_container(container_id)

        if container["status"] == "running" and not force:
            raise RuntimeError(
                f"Container '{container_id}' is running. Stop it first or use force=True."
            )

        self.fs_manager.remove_container(container_id, remove_snapshots=True)

        del self.containers[container_id]
        self._save_state()

    # ----------------------------
    # Snapshot Management
    # ----------------------------
    def snapshot_container(self, container_id):
        container = self._get_container(container_id)

        snapshot_id = self.fs_manager.snapshot_container(container_id)

        container["last_snapshot"] = snapshot_id
        container["snapshots"].append(snapshot_id)

        self._save_state()
        return snapshot_id

    def restore_container(self, container_id, snapshot_id):
        container = self._get_container(container_id)

        if container["status"] == "running":
            raise RuntimeError("Stop container before restoring snapshot")

        self.fs_manager.restore_snapshot(container_id, snapshot_id)

    def list_snapshots(self, container_id):
        return self._get_container(container_id).get("snapshots", [])

    # ----------------------------
    # Image Integration (NEW)
    # ----------------------------
    def create_container_from_image(self, image_name, container_id, image_manager):
        if container_id in self.containers:
            raise ValueError(f"Container '{container_id}' already exists")

        self.fs_manager.create_container_root(container_id)

        layers = image_manager.get_image_layers(image_name)

        for snap in layers:
            self.fs_manager.restore_snapshot(container_id, snap)

        self.containers[container_id] = {
            "id": container_id,
            "path": os.path.join(self.fs_manager.base_path, container_id),
            "status": "stopped",
            "created_at": datetime.now().isoformat(),
            "last_started": None,
            "last_stopped": None,
            "last_snapshot": None,
            "snapshots": []
        }

        self._save_state()

    # ----------------------------
    # Query / Info
    # ----------------------------
    def list_containers(self):
        return self.containers

    def inspect_container(self, container_id):
        return self._get_container(container_id)

    # ----------------------------
    # Internal Helpers
    # ----------------------------
    def _get_container(self, container_id):
        if container_id not in self.containers:
            raise ValueError(f"Container '{container_id}' does not exist")
        return self.containers[container_id]