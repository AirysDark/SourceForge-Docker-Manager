# network_manager/__init__.py

"""
Network Manager Module Initialization

This module handles:
- Networking for containers
- Port mapping and inter-container communication
- Overlay or bridged network simulation within Termux

Compatible with Termux Python 3.10+.
"""

from .network_core import NetworkManager
from .compose_system import ComposeSystem

__all__ = [
    "NetworkManager",
    "ComposeSystem",
]
