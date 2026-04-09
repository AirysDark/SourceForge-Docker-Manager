# registry/__init__.py

"""
Registry Module Initialization

This module provides a simple local registry server for storing and retrieving container images.
It exposes the RegistryServer class to start the HTTP registry and perform image operations.

Compatible with Termux Python 3.10+.
"""

from .registry_server import RegistryHandler, run_registry

__all__ = [
    "RegistryHandler",
    "run_registry",
]
