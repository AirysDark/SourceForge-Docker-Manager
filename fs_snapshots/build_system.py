# fs_snapshots/build_system.py

import os
import shutil
import json
import hashlib
import subprocess


class BuildSystem:
    """
    BuildSystem manages image builds using filesystem snapshots.
    Fully manual Python class; no pydantic or external validation.
    """

    def __init__(self, fs_manager, image_manager, cache_file="build_cache.json"):
        if fs_manager is None or image_manager is None:
            raise ValueError("fs_manager and image_manager are required")

        self.fs = fs_manager
        self.images = image_manager
        self.cache_file = cache_file
        self.cache = self._load_cache()

    # ----------------------------
    # Cache System
    # ----------------------------
    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load cache: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to save cache: {e}")

    def _hash_step(self, step, parent_layer):
        """
        Deterministic hash for caching: depends on step + previous layer.
        """
        data = json.dumps(step, sort_keys=True) + str(parent_layer)
        return hashlib.sha256(data.encode()).hexdigest()

    # ----------------------------
    # Build Image
    # ----------------------------
    def build(self, image_name, instructions):
        if not isinstance(image_name, str):
            raise TypeError("image_name must be a string")
        if not isinstance(instructions, list):
            raise TypeError("instructions must be a list of dicts")

        container_id = f"build_{image_name}"

        # Clean previous build container if exists
        if os.path.exists(os.path.join(self.fs.base_path, container_id)):
            self.fs.remove_container(container_id, remove_snapshots=False)

        self.fs.create_container_root(container_id)

        layers = []
        parent = None

        for step in instructions:
            step_type = step.get("type")
            step_hash = self._hash_step(step, parent)

            # ----------------------------
            # CACHE HIT
            # ----------------------------
            if step_hash in self.cache:
                snap = self.cache[step_hash]
                print(f"[CACHE HIT] {step_type} → {snap}")
                self.fs.restore_snapshot(container_id, snap)
                layers.append(snap)
                parent = snap
                continue

            # ----------------------------
            # EXECUTE STEP
            # ----------------------------
            print(f"[BUILD] {step_type}")

            if step_type == "FROM":
                self._apply_base_image(container_id, step.get("image"))
            elif step_type == "COPY":
                self._copy_into_container(
                    container_id, step.get("src"), step.get("dest")
                )
            elif step_type == "RUN":
                self._run_command(container_id, step.get("cmd"))
            else:
                raise ValueError(f"Unknown step type: {step_type}")

            # Snapshot = layer
            snap = self.fs.snapshot_container(container_id)

            # Save cache
            self.cache[step_hash] = snap
            self._save_cache()

            layers.append(snap)
            parent = snap

        # Save image
        self.images.register_image_layers(image_name, layers)

        # Cleanup build container (keep snapshots)
        self.fs.remove_container(container_id, remove_snapshots=False)

        return layers

    # ----------------------------
    # Apply Base Image
    # ----------------------------
    def _apply_base_image(self, container_id, image_name):
        if not image_name:
            raise ValueError("Base image name required")
        layers = self.images.get_image_layers(image_name)
        for snap in layers:
            self.fs.restore_snapshot(container_id, snap)

    # ----------------------------
    # COPY
    # ----------------------------
    def _copy_into_container(self, container_id, src, dest):
        container_path = os.path.join(self.fs.base_path, container_id)
        dest_path = os.path.join(container_path, dest)

        if not os.path.exists(src):
            raise FileNotFoundError(f"COPY source not found: {src}")

        if os.path.isdir(src):
            shutil.copytree(src, dest_path, dirs_exist_ok=True)
        else:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src, dest_path)

    # ----------------------------
    # RUN
    # ----------------------------
    def _run_command(self, container_id, cmd):
        container_path = os.path.join(self.fs.base_path, container_id)

        if not isinstance(cmd, str):
            raise TypeError("Command must be a string")

        result = subprocess.run(
            cmd,
            cwd=container_path,
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            raise RuntimeError(f"RUN failed: {cmd}")
