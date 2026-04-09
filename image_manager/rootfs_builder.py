# rootfs_builder/rootfs_builder.py

import os
import shutil
import stat


class RootFSBuilder:
    """
    Manual Python class for building minimal root filesystem
    Compatible with Termux Python 3.10, no pydantic required.
    """

    def __init__(self, busybox_path=None):
        """
        Initialize RootFSBuilder.

        Parameters:
        - busybox_path (str or None): Optional explicit path to busybox binary.
                                       If not provided, will auto-detect common locations.
        """
        if busybox_path is not None and not isinstance(busybox_path, str):
            raise TypeError(f"busybox_path must be str or None, got {type(busybox_path)}")
        self.busybox_path = busybox_path or self._find_busybox()

    # ----------------------------
    # BusyBox Detection
    # ----------------------------
    def _find_busybox(self):
        """
        Auto-detect BusyBox binary in common locations.
        Returns the path if found, else None.
        """
        candidates = [
            "/data/data/com.termux/files/usr/bin/busybox",  # Termux
            "/usr/bin/busybox",
            "/bin/busybox",
            "/Busybox/system/bin"
        ]

        for path in candidates:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path

        return None

    # ----------------------------
    # RootFS Builder
    # ----------------------------
    def build_rootfs(self, container_path):
        """
        Build root filesystem directory structure and install BusyBox if available.

        Parameters:
        - container_path (str): Path to the root of the container filesystem
        """
        if not isinstance(container_path, str):
            raise TypeError(f"container_path must be str, got {type(container_path)}")

        dirs = ["bin", "usr/bin", "lib", "tmp", "etc", "var", "home"]

        # Create directory structure
        for d in dirs:
            path = os.path.join(container_path, d)
            os.makedirs(path, exist_ok=True)

        # Ensure tmp exists (important for many tools)
        tmp_path = os.path.join(container_path, "tmp")
        os.makedirs(tmp_path, exist_ok=True)

        # Install BusyBox or fallback shell
        if self.busybox_path:
            self._install_busybox(container_path)
        else:
            self._create_fallback_shell(container_path)

    # ----------------------------
    # BusyBox Installation
    # ----------------------------
    def _install_busybox(self, container_path):
        """
        Copy BusyBox binary and create symlinks for common utilities.
        """
        bin_dir = os.path.join(container_path, "bin")
        busybox_dest = os.path.join(bin_dir, "busybox")

        # Copy binary and make executable
        shutil.copy2(self.busybox_path, busybox_dest)
        os.chmod(busybox_dest, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

        # Common BusyBox tools
        tools = [
            "sh", "ls", "cp", "mv", "rm", "mkdir",
            "cat", "echo", "pwd", "touch", "chmod",
            "uname", "whoami", "date"
        ]

        # Create symlinks; fallback to copy if symlink fails
        for tool in tools:
            link_path = os.path.join(bin_dir, tool)
            if not os.path.exists(link_path):
                try:
                    os.symlink("busybox", link_path)
                except OSError:
                    shutil.copy2(busybox_dest, link_path)
                    os.chmod(link_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    # ----------------------------
    # Fallback Shell (No BusyBox)
    # ----------------------------
    def _create_fallback_shell(self, container_path):
        """
        Create a minimal fallback shell if BusyBox is not found.
        """
        shell_path = os.path.join(container_path, "bin/sh")

        script = f"""#!/bin/sh
# Fallback shell (no BusyBox found)
cd "{container_path}"
exec /bin/sh "$@"
"""
        with open(shell_path, "w") as f:
            f.write(script)

        os.chmod(shell_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
