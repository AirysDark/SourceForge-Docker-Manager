# root/__init__.py

"""
SourceForge-Docker-Manager Core Package Initialization

This module initializes the root package and exposes core components.
It provides access to:
- RuntimeManager: manages container lifecycle and logging
- Any other utilities or submodules added in the future

Designed to be fully compatible with Termux Python 3.10+.
"""

# Import core runtime manager
from .runtime_manager import RuntimeManager
from .docker_support import DockerSupport
from .fs_snapshots import FsSnapshots
from .image_manager import imagemanager
from .network_manager import NetworkManager
from .registry import Registry
from .engine_core import EngineCore


# Explicitly define public API
__all__ = [
    "RuntimeManager",
    "DockerSupport",
    "FsSnapshots",
    "EngineCore",
    "imagemanager",
    "NetworkManager",
    "Registry",
]
