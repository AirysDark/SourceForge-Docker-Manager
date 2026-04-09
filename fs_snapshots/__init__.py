# fs_snapshots/__init__.py

"""
FileSystem Snapshots Module Initialization

This module handles:
- Container filesystem management
- Snapshot creation, restore, and deletion
- File operations within container roots

Compatible with Termux Python 3.10+.
"""

from .filesystem_manager import FileSystemManager
from .snapshot_utils import SnapshotUtils

__all__ = [
    "FileSystemManager",
    "SnapshotUtils",
]
