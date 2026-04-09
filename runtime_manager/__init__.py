# runtime_manager/__init__.py

"""
Runtime Manager Module Initialization

Provides the RuntimeManager class to handle:
- Container lifecycle (start, stop, exec)
- Live log streaming for multiple containers
- Container environment setup and management

Designed for Termux Python 3.10+.
"""

from .runtime_manager import RuntimeManager

__all__ = [
    "RuntimeManager",
]
