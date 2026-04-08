# rootfs_builder/rootfs_builder.py

import os
import shutil


class RootFSBuilder:
    def __init__(self, busybox_path=None):
        """
        busybox_path:
        Optional explicit path to busybox binary.
        If not provided, auto-detect.
        """
        self.busybox_path = busybox_path or self._find_busybox()

    # ----------------------------
    # BusyBox Detection
    # ----------------------------
    def _find_busybox(self):
        candidates = [
            "/data/data/com.termux/files/usr/bin/busybox",  # Termux
            "/usr/bin/busybox",
            "/bin/busybox",
            "/Busybox/system/bin"
        ]

        for path in candidates:
            if os.path.exists(path):
                return path

        return None

    # ----------------------------
    # RootFS Builder
    # ----------------------------
    def build_rootfs(self, container_path):
        dirs = [
            "bin",
            "usr/bin",
            "lib",
            "tmp",
            "etc",
            "var",
            "home"
        ]

        # Create directory structure
        for d in dirs:
            os.makedirs(os.path.join(container_path, d), exist_ok=True)

        # Ensure tmp exists (important for many tools)
        os.makedirs(os.path.join(container_path, "tmp"), exist_ok=True)

        # Install BusyBox if available
        if self.busybox_path:
            self._install_busybox(container_path)
        else:
            # Fallback minimal shell if busybox not found
            self._create_fallback_shell(container_path)

    # ----------------------------
    # BusyBox Installation
    # ----------------------------
    def _install_busybox(self, container_path):
        bin_dir = os.path.join(container_path, "bin")
        busybox_dest = os.path.join(bin_dir, "busybox")

        # Copy busybox binary
        shutil.copy2(self.busybox_path, busybox_dest)
        os.chmod(busybox_dest, 0o755)

        # Common tools to expose
        tools = [
            "sh", "ls", "cp", "mv", "rm", "mkdir",
            "cat", "echo", "pwd", "touch", "chmod",
            "uname", "whoami", "date"
        ]

        # Create symlinks
        for tool in tools:
            link_path = os.path.join(bin_dir, tool)

            if not os.path.exists(link_path):
                try:
                    os.symlink("busybox", link_path)
                except Exception:
                    # Some filesystems may not support symlinks
                    shutil.copy2(busybox_dest, link_path)

    # ----------------------------
    # Fallback Shell (No BusyBox)
    # ----------------------------
    def _create_fallback_shell(self, container_path):
        shell_path = os.path.join(container_path, "bin/sh")

        script = f"""#!/bin/sh
# Fallback shell (no busybox found)
cd "{container_path}"
exec /bin/sh "$@"
"""

        with open(shell_path, "w") as f:
            f.write(script)

        os.chmod(shell_path, 0o755)