# engine_core/__init__.py

"""
EngineCore Module Initialization

This module provides the core engine functionalities for container management, including:
- Container lifecycle orchestration
- Command execution and logging
- Integration with runtime managers and networking

Designed to be fully compatible with Termux Python 3.10+.
"""

from .engine import Engine
from .hooks import HooksManager
from .events import EventDispatcher

__all__ = [
    "Engine",
    "HooksManager",
    "EventDispatcher",
]
