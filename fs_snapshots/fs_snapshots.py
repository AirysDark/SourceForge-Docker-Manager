# fs_snapshots/fs_snapshots.py

import os
import shutil
import hashlib
import json
from datetime import datetime

from rootfs_builder.rootfs_builder import RootFSBuilder


class FileSystemManager:
    def __init__(self, base_path="containers", snapshots_path="snapshots"):
        self.base_path = base_path
        self.snapshots_path = snapshots_path

        self.index_file = os.path.join(self.snapshots_path, "index.json")
        self.hash_cache_file = os.path.join(self.base_path, ".hash_cache.json")

        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(self.snapshots_path, exist_ok=True)

    # ----------------------------
    # Safety Guard
    # ----------------------------
    def _safe_path(self, path):
        base = os.path.abspath(self.base_path)
        target = os.path.abspath(path)
        if not target.startswith(base):
            raise RuntimeError(f"Unsafe path detected: {target}")

    # ----------------------------
    # Hash Cache
    # ----------------------------
    def _load_hash_cache(self):
        if os.path.exists(self.hash_cache_file):
            return json.load(open(self.hash_cache_file))
        return {}

    def _save_hash_cache(self, cache):
        json.dump(cache, open(self.hash_cache_file, "w"), indent=2)

    def _file_hash(self, filepath, cache):
        stat = os.stat(filepath)
        key = filepath

        entry = cache.get(key)

        if entry and entry["mtime"] == stat.st_mtime and entry["size"] == stat.st_size:
            return entry["hash"]

        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)

        h = sha.hexdigest()

        cache[key] = {
            "mtime": stat.st_mtime,
            "size": stat.st_size,
            "hash": h
        }

        return h

    # ----------------------------
    # Container Root
    # ----------------------------
    def create_container_root(self, container_id):
        path = os.path.join(self.base_path, container_id)

        if os.path.exists(path):
            return path

        os.makedirs(path, exist_ok=True)

        # Build fake rootfs (BusyBox + dirs)
        RootFSBuilder().build_rootfs(path)

        for sub in ["app", "data", "logs"]:
            os.makedirs(os.path.join(path, sub), exist_ok=True)

        return path

    # ----------------------------
    # Snapshot Index
    # ----------------------------
    def _load_index(self):
        if os.path.exists(self.index_file):
            return json.load(open(self.index_file))
        return {}

    def _save_index(self, index):
        json.dump(index, open(self.index_file, "w"), indent=2)

    def _update_index(self, container_id, snapshot_id):
        index = self._load_index()
        index.setdefault(container_id, []).append(snapshot_id)
        self._save_index(index)

    def _get_snapshots(self, container_id):
        index = self._load_index()
        return sorted(index.get(container_id, []))

    def _remove_from_index(self, container_id, snapshot_id):
        index = self._load_index()
        if container_id in index:
            index[container_id] = [s for s in index[container_id] if s != snapshot_id]
            self._save_index(index)

    # ----------------------------
    # Metadata
    # ----------------------------
    def _load_metadata(self, snapshot_id):
        meta_path = os.path.join(self.snapshots_path, snapshot_id, "metadata.json")
        if os.path.exists(meta_path):
            return json.load(open(meta_path))
        return {}

    # ----------------------------
    # Snapshot Creation
    # ----------------------------
    def snapshot_container(self, container_id):
        src = os.path.join(self.base_path, container_id)

        if not os.path.exists(src):
            raise FileNotFoundError(f"Container not found: {container_id}")

        cache = self._load_hash_cache()

        snapshots = self._get_snapshots(container_id)
        prev_meta = {}

        if snapshots:
            prev_meta = self._load_metadata(snapshots[-1]).get("files", {})

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"{container_id}_{ts}"
        dest = os.path.join(self.snapshots_path, snapshot_id)

        os.makedirs(dest, exist_ok=True)

        new_meta = {}
        changed_files = []
        deleted_files = []
        current_files = {}

        for root, _, files in os.walk(src):
            rel_root = os.path.relpath(root, src)

            for file in files:
                src_file = os.path.join(root, file)
                rel_file = os.path.normpath(os.path.join(rel_root, file))

                h = self._file_hash(src_file, cache)

                new_meta[rel_file] = h
                current_files[rel_file] = True

                if rel_file not in prev_meta or prev_meta[rel_file] != h:
                    changed_files.append(rel_file)

                    dest_file = os.path.join(dest, rel_file)
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(src_file, dest_file)

        for old_file in prev_meta:
            if old_file not in current_files:
                deleted_files.append(old_file)

        metadata = {
            "container_id": container_id,
            "snapshot_id": snapshot_id,
            "created_at": datetime.now().isoformat(),
            "parent": snapshots[-1] if snapshots else None,
            "files": new_meta,
            "changed": changed_files,
            "deleted": deleted_files
        }

        with open(os.path.join(dest, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

        self._update_index(container_id, snapshot_id)
        self._save_hash_cache(cache)

        return snapshot_id

    # ----------------------------
    # Restore (FIXED)
    # ----------------------------
    def restore_snapshot(self, container_id, snapshot_id):
        container_path = os.path.join(self.base_path, container_id)
        self._safe_path(container_path)

        if not os.path.exists(container_path):
            self.create_container_root(container_id)

        # Build snapshot chain
        chain = []
        current = snapshot_id

        while current:
            chain.append(current)
            meta = self._load_metadata(current)
            current = meta.get("parent")

        chain.reverse()

        # Clean tracked files ONLY (preserve rootfs)
        for root, _, files in os.walk(container_path):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, container_path)

                if not rel.startswith(("bin", "usr", "lib")):
                    os.remove(full)

        # Apply snapshots
        for snap in chain:
            snap_path = os.path.join(self.snapshots_path, snap)
            meta = self._load_metadata(snap)

            for rel_file in meta.get("changed", []):
                src_file = os.path.join(snap_path, rel_file)
                dest_file = os.path.join(container_path, rel_file)

                if os.path.exists(src_file):
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(src_file, dest_file)

            for rel_file in meta.get("deleted", []):
                target = os.path.join(container_path, rel_file)
                if os.path.exists(target):
                    os.remove(target)

    # ----------------------------
    # Remove Container
    # ----------------------------
    def remove_container(self, container_id, remove_snapshots=False):
        container_path = os.path.join(self.base_path, container_id)
        self._safe_path(container_path)

        if os.path.exists(container_path):
            shutil.rmtree(container_path)

        if remove_snapshots:
            for snap in self._get_snapshots(container_id):
                shutil.rmtree(os.path.join(self.snapshots_path, snap), ignore_errors=True)
                self._remove_from_index(container_id, snap)

    # ----------------------------
    # Snapshot Tools
    # ----------------------------
    def list_snapshots(self, container_id):
        return self._get_snapshots(container_id)

    def inspect_snapshot(self, snapshot_id):
        return self._load_metadata(snapshot_id)

    def diff_snapshots(self, snap_a, snap_b):
        a = self._load_metadata(snap_a).get("files", {})
        b = self._load_metadata(snap_b).get("files", {})

        return {
            "added": [f for f in b if f not in a],
            "removed": [f for f in a if f not in b],
            "changed": [f for f in a if f in b and a[f] != b[f]]
        }

    def prune_snapshots(self, container_id, keep_last=3):
        snaps = self._get_snapshots(container_id)

        if len(snaps) <= keep_last:
            return

        for snap in snaps[:-keep_last]:
            shutil.rmtree(os.path.join(self.snapshots_path, snap), ignore_errors=True)
            self._remove_from_index(container_id, snap)