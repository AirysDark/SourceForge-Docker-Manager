# root/__init__.py

"""
SourceForge-Docker-Manager Core Package Initialization

This module initializes the root package and exposes core components:
- RuntimeManager: manages container lifecycle and logging
- DockerSupport: Docker-related utilities
- FsSnapshots: filesystem snapshot management
- ImageManager (imagemanager): container image management
- NetworkManager: container networking management
- Registry: registry server handling
- EngineCore: core engine logic

Designed to be fully compatible with Termux Python 3.10+.
"""

# Import core modules
from .runtime_manager import RuntimeManager
from .docker_support import DockerSupport
from .fs_snapshots import FsSnapshots
from .image_manager import ImageManager
from .network_manager import NetworkManager
from .registry import Registry
from .engine_core import EngineCore

# Explicitly define public API
__all__ = [
    "RuntimeManager",
    "DockerSupport",
    "FsSnapshots",
    "EngineCore",
    "ImageManager",
    "NetworkManager",
    "Registry",
]
