# engine_core/engine_core.py

import os
import json
from datetime import datetime
from typing import List, Dict, Optional


class Container:
    """Manual Python class to represent container state."""

    def __init__(
        self,
        container_id: str,
        path: str,
        status: str = "stopped",
        created_at: Optional[str] = None,
        last_started: Optional[str] = None,
        last_stopped: Optional[str] = None,
        last_snapshot: Optional[str] = None,
        snapshots: Optional[List[str]] = None,
    ):
        if snapshots is None:
            snapshots = []

        # Type checks
        if not isinstance(container_id, str):
            raise TypeError("container_id must be str")
        if not isinstance(path, str):
            raise TypeError("path must be str")
        if not isinstance(status, str):
            raise TypeError("status must be str")
        if not isinstance(snapshots, list):
            raise TypeError("snapshots must be a list of strings")

        self.id = container_id
        self.path = path
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.last_started = last_started
        self.last_stopped = last_stopped
        self.last_snapshot = last_snapshot
        self.snapshots = snapshots

    def to_dict(self) -> Dict:
        """Serialize container to dictionary."""
        return {
            "id": self.id,
            "path": self.path,
            "status": self.status,
            "created_at": self.created_at,
            "last_started": self.last_started,
            "last_stopped": self.last_stopped,
            "last_snapshot": self.last_snapshot,
            "snapshots": self.snapshots,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Deserialize container from dictionary."""
        return cls(
            container_id=data["id"],
            path=data["path"],
            status=data.get("status", "stopped"),
            created_at=data.get("created_at"),
            last_started=data.get("last_started"),
            last_stopped=data.get("last_stopped"),
            last_snapshot=data.get("last_snapshot"),
            snapshots=data.get("snapshots", []),
        )


class EngineCore:
    """EngineCore manages containers and snapshots manually."""

    def __init__(self, fs_manager, state_file="engine_state.json"):
        self.fs_manager = fs_manager
        self.state_file = state_file
        self.containers: Dict[str, Container] = {}

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
                data = json.load(f)
                for cid, cont_data in data.items():
                    self.containers[cid] = Container.from_dict(cont_data)
        else:
            self.containers = {}

    def _save_state(self):
        data = {cid: cont.to_dict() for cid, cont in self.containers.items()}
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    # ----------------------------
    # Container Lifecycle
    # ----------------------------
    def create_container(self, container_id):
        if container_id in self.containers:
            raise ValueError(f"Container '{container_id}' already exists")

        path = self.fs_manager.create_container_root(container_id)

        container = Container(container_id, path)
        self.containers[container_id] = container
        self._save_state()
        return path

    def start_container(self, container_id, runtime_manager=None, command="bash"):
        container = self._get_container(container_id)

        if container.status == "running":
            raise RuntimeError(f"Container '{container_id}' is already running")

        if runtime_manager:
            runtime_manager.run_container(container_id, command)

        container.status = "running"
        container.last_started = datetime.now().isoformat()
        self._save_state()

    def stop_container(self, container_id, runtime_manager=None):
        container = self._get_container(container_id)

        if container.status == "stopped":
            raise RuntimeError(f"Container '{container_id}' is already stopped")

        if runtime_manager:
            runtime_manager.stop_container(container_id)

        container.status = "stopped"
        container.last_stopped = datetime.now().isoformat()

        if self.auto_snapshot_on_stop:
            snapshot_id = self.fs_manager.snapshot_container(container_id)
            container.last_snapshot = snapshot_id
            container.snapshots.append(snapshot_id)
            try:
                self.fs_manager.prune_snapshots(container_id, keep_last=self.snapshot_retention)
                container.snapshots = self.fs_manager.list_snapshots(container_id)
            except Exception:
                pass

        self._save_state()

    def remove_container(self, container_id, force=False):
        container = self._get_container(container_id)
        if container.status == "running" and not force:
            raise RuntimeError(f"Container '{container_id}' is running. Stop it first or use force=True.")

        self.fs_manager.remove_container(container_id, remove_snapshots=True)
        del self.containers[container_id]
        self._save_state()

    # ----------------------------
    # Snapshot Management
    # ----------------------------
    def snapshot_container(self, container_id):
        container = self._get_container(container_id)
        snapshot_id = self.fs_manager.snapshot_container(container_id)
        container.last_snapshot = snapshot_id
        container.snapshots.append(snapshot_id)
        self._save_state()
        return snapshot_id

    def restore_container(self, container_id, snapshot_id):
        container = self._get_container(container_id)
        if container.status == "running":
            raise RuntimeError("Stop container before restoring snapshot")
        self.fs_manager.restore_snapshot(container_id, snapshot_id)

    def list_snapshots(self, container_id):
        return self._get_container(container_id).snapshots

    # ----------------------------
    # Image Integration
    # ----------------------------
    def create_container_from_image(self, image_name, container_id, image_manager):
        if container_id in self.containers:
            raise ValueError(f"Container '{container_id}' already exists")

        self.fs_manager.create_container_root(container_id)
        layers = image_manager.get_image_layers(image_name)
        for snap in layers:
            self.fs_manager.restore_snapshot(container_id, snap)

        container = Container(container_id, os.path.join(self.fs_manager.base_path, container_id))
        self.containers[container_id] = container
        self._save_state()

    # ----------------------------
    # Query / Info
    # ----------------------------
    def list_containers(self):
        return {cid: cont.to_dict() for cid, cont in self.containers.items()}

    def inspect_container(self, container_id):
        return self._get_container(container_id).to_dict()

    # ----------------------------
    # Internal Helper
    # ----------------------------
    def _get_container(self, container_id):
        if container_id not in self.containers:
            raise ValueError(f"Container '{container_id}' does not exist")
        return self.containers[container_id]
