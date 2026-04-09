# fs_snapshots/build_system.py

import os
import shutil
import json
import hashlib


class BuildSystem:
    def __init__(self, fs_manager, image_manager, cache_file="build_cache.json"):
        self.fs = fs_manager
        self.images = image_manager
        self.cache_file = cache_file

        self.cache = self._load_cache()

    # ----------------------------
    # Cache System
    # ----------------------------
    def _load_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r") as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=2)

    def _hash_step(self, step, parent_layer):
        """
        Deterministic hash for caching:
        depends on step + previous layer
        """
        data = json.dumps(step, sort_keys=True) + str(parent_layer)
        return hashlib.sha256(data.encode()).hexdigest()

    # ----------------------------
    # Build Image
    # ----------------------------
    def build(self, image_name, instructions):
        container_id = f"build_{image_name}"

        # Clean previous build container if exists
        if os.path.exists(os.path.join(self.fs.base_path, container_id)):
            self.fs.remove_container(container_id, remove_snapshots=False)

        self.fs.create_container_root(container_id)

        layers = []
        parent = None

        for step in instructions:
            step_type = step["type"]
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
                self._apply_base_image(container_id, step["image"])

            elif step_type == "COPY":
                self._copy_into_container(container_id, step["src"], step["dest"])

            elif step_type == "RUN":
                self._run_command(container_id, step["cmd"])

            else:
                raise ValueError(f"Unknown step: {step_type}")

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
        import subprocess

        container_path = os.path.join(self.fs.base_path, container_id)

        result = subprocess.run(
            cmd,
            cwd=container_path,
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            raise RuntimeError(f"RUN failed: {cmd}")