"""
Moira — dispatch.py
The Substrate Dispatcher: governs the routing of astronomical computations
between the Python reference (Truth) and the C++ accelerated (Forge) backends.
"""

from __future__ import annotations

import os
import functools
from enum import Enum
from collections.abc import Callable
from typing import Any

class MoiraBackend(Enum):
    PYTHON = "python"
    NATIVE = "native"

class DispatchSettings:
    def __init__(self):
        # Default to Python (The Truth) unless acceleration is explicitly requested.
        self._default_backend = MoiraBackend.PYTHON
        if os.environ.get("MOIRA_ACCELERATE") == "1":
            self._default_backend = MoiraBackend.NATIVE

    def current_backend(self) -> MoiraBackend:
        return self._default_backend

    def set_backend(self, backend: MoiraBackend):
        self._default_backend = backend

settings = DispatchSettings()

def accelerate(pillar_name: str):
    """
    RITE: The Accelerator — a decorator that attempts to delegate a function
    to the moira_native substrate if enabled.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if settings.current_backend() == MoiraBackend.NATIVE:
                try:
                    # Attempt to import and delegate to the native extension
                    from . import moira_native
                    if hasattr(moira_native, pillar_name):
                        native_func = getattr(moira_native, pillar_name)
                        return native_func(*args, **kwargs)
                except (ImportError, AttributeError):
                    # Fallback to Python if native is unavailable or incomplete
                    pass
            return func(*args, **kwargs)
        return wrapper
    return decorator
