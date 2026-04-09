# image_manager/__init__.py

"""
Image Manager Module Initialization

This module handles:
- Container image management
- Building, storing, and retrieving images
- Import/export of filesystem snapshots as images

Compatible with Termux Python 3.10+.
"""

from .image_manager_core import ImageManager
from .image_utils import ImageUtils

__all__ = [
    "ImageManager",
    "ImageUtils",
]
