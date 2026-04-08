# image_manager/image_manager.py

import os
import json
import shutil
import tarfile
from datetime import datetime
from urllib import request


class ImageManager:
    def __init__(self, fs_manager, image_state_file="images.json"):
        self.fs_manager = fs_manager
        self.image_state_file = image_state_file
        self.images = {}

        self._load_images()

    # ----------------------------
    # State Persistence
    # ----------------------------
    def _load_images(self):
        if os.path.exists(self.image_state_file):
            with open(self.image_state_file, "r") as f:
                self.images = json.load(f)
        else:
            self.images = {}

    def _save_images(self):
        with open(self.image_state_file, "w") as f:
            json.dump(self.images, f, indent=2)

    # ----------------------------
    # Validation
    # ----------------------------
    def _validate_layers(self, layers):
        for snap in layers:
            meta = self.fs_manager.inspect_snapshot(snap)
            if not meta:
                raise RuntimeError(f"Invalid snapshot layer: {snap}")

    # ----------------------------
    # Register Image
    # ----------------------------
    def register_image_layers(self, image_name, layers, tag="latest"):
        if not layers:
            raise ValueError("Cannot register image with no layers")

        self._validate_layers(layers)

        self.images.setdefault(image_name, {})

        self.images[image_name][tag] = {
            "name": image_name,
            "tag": tag,
            "layers": layers,
            "top_layer": layers[-1],
            "created_at": datetime.now().isoformat(),
            "layer_count": len(layers)
        }

        self._save_images()

    # ----------------------------
    # Build Image (Legacy)
    # ----------------------------
    def build_image(self, image_name, container_id, tag="latest"):
        snapshot_id = self.fs_manager.snapshot_container(container_id)

        layers = []
        current = snapshot_id

        while current:
            layers.append(current)
            meta = self.fs_manager.inspect_snapshot(current)
            current = meta.get("parent")

        layers.reverse()

        self.register_image_layers(image_name, layers, tag)

        return snapshot_id

    # ----------------------------
    # Get Layers
    # ----------------------------
    def get_image_layers(self, image_name, tag="latest"):
        if image_name not in self.images:
            raise ValueError(f"Image '{image_name}' not found")

        if tag not in self.images[image_name]:
            raise ValueError(f"Tag '{tag}' not found")

        return self.images[image_name][tag]["layers"]

    # ----------------------------
    # Create Container from Image
    # ----------------------------
    def create_container_from_image(self, image_name, container_id, tag="latest"):
        layers = self.get_image_layers(image_name, tag)

        container_path = os.path.join(self.fs_manager.base_path, container_id)

        if os.path.exists(container_path):
            raise RuntimeError(f"Container '{container_id}' already exists")

        self.fs_manager.create_container_root(container_id)

        for snap in layers:
            self.fs_manager.restore_snapshot(container_id, snap)

        return container_id

    # ----------------------------
    # Export Image → TAR
    # ----------------------------
    def export_image(self, image_name, tag="latest", output_file=None):
        if image_name not in self.images:
            raise ValueError("Image not found")

        if tag not in self.images[image_name]:
            raise ValueError("Tag not found")

        image = self.images[image_name][tag]
        layers = image["layers"]

        output_file = output_file or f"{image_name}_{tag}.tar"

        with tarfile.open(output_file, "w") as tar:
            meta_path = "metadata.json"

            with open(meta_path, "w") as f:
                json.dump(image, f, indent=2)

            tar.add(meta_path, arcname="metadata.json")
            os.remove(meta_path)

            for layer in layers:
                layer_path = os.path.join(self.fs_manager.snapshots_path, layer)
                if os.path.exists(layer_path):
                    tar.add(layer_path, arcname=f"layers/{layer}")

        return output_file

    # ----------------------------
    # Import Image from TAR
    # ----------------------------
    def import_image(self, tar_file):
        if not os.path.exists(tar_file):
            raise FileNotFoundError(tar_file)

        temp_dir = "tmp_import"

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        os.makedirs(temp_dir, exist_ok=True)

        with tarfile.open(tar_file, "r") as tar:
            tar.extractall(temp_dir)

        meta_file = os.path.join(temp_dir, "metadata.json")

        if not os.path.exists(meta_file):
            raise RuntimeError("Invalid image archive")

        with open(meta_file, "r") as f:
            image = json.load(f)

        image_name = image["name"]
        tag = image["tag"]

        layers_dir = os.path.join(temp_dir, "layers")

        if os.path.exists(layers_dir):
            for layer in os.listdir(layers_dir):
                src = os.path.join(layers_dir, layer)
                dest = os.path.join(self.fs_manager.snapshots_path, layer)

                if not os.path.exists(dest):
                    shutil.copytree(src, dest)

        self.images.setdefault(image_name, {})
        self.images[image_name][tag] = image

        self._save_images()
        shutil.rmtree(temp_dir)

        return image_name

    # ----------------------------
    # Registry Push (NO requests lib)
    # ----------------------------
    def push_image(self, image_name, registry_url, tag="latest"):
        tar_file = self.export_image(image_name, tag)

        with open(tar_file, "rb") as f:
            data = f.read()

        req = request.Request(
            f"{registry_url}/push",
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/octet-stream",
                "X-Filename": os.path.basename(tar_file)
            }
        )

        try:
            request.urlopen(req)
        except Exception as e:
            raise RuntimeError(f"Push failed: {e}")

        return tar_file

    # ----------------------------
    # Registry Pull
    # ----------------------------
    def pull_remote(self, tar_name, registry_url):
        url = f"{registry_url}/pull?name={tar_name}"

        local_file = tar_name

        try:
            with request.urlopen(url) as response, open(local_file, "wb") as out:
                shutil.copyfileobj(response, out)
        except Exception as e:
            raise RuntimeError(f"Pull failed: {e}")

        return self.import_image(local_file)

    # ----------------------------
    # List / Inspect
    # ----------------------------
    def list_images(self):
        return self.images

    def list_tags(self, image_name):
        if image_name not in self.images:
            raise ValueError("Image not found")
        return list(self.images[image_name].keys())

    def inspect_image(self, image_name, tag="latest"):
        if image_name not in self.images:
            raise ValueError("Image not found")

        if tag not in self.images[image_name]:
            raise ValueError("Tag not found")

        return self.images[image_name][tag]

    # ----------------------------
    # Remove Image
    # ----------------------------
    def remove_image(self, image_name, tag=None, force=False):
        if image_name not in self.images:
            raise ValueError(f"Image '{image_name}' does not exist")

        if tag:
            if tag not in self.images[image_name]:
                raise ValueError("Tag not found")

            del self.images[image_name][tag]

            if not self.images[image_name]:
                del self.images[image_name]

        else:
            if not force and len(self.images[image_name]) > 1:
                raise RuntimeError(
                    f"Image '{image_name}' has multiple tags. Use force=True."
                )

            del self.images[image_name]

        self._save_images()