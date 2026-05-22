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
    """Vessel: Enumerates the supported execution backends for Moira dispatch."""
    PYTHON = "python"
    NATIVE = "native"

class DispatchSettings:
    """
    RITE: The Dispatch Settings Keeper.

    THEOREM: Governs the repository-global backend preference that decides
    whether accelerated entry points should attempt native delegation.

    RITE OF PURPOSE:
        DispatchSettings centralizes the ambient backend policy for the
        dispatcher layer. It records the selected backend once, exposes a
        stable query surface to decorators, and honors the acceleration
        environment flag without forcing computational modules to read process
        state directly.

    LAW OF OPERATION:
        Responsibilities:
            - Initialize the default backend from process configuration.
            - Expose the current backend to the dispatch decorator layer.
            - Allow tests and callers to override the backend explicitly.
        Non-responsibilities:
            - Does not perform any astronomical computation.
            - Does not import or validate the native extension itself.
            - Does not persist backend choices beyond process memory.
        Dependencies:
            - stdlib ``os`` for environment inspection.
            - ``MoiraBackend`` for the backend identity contract.
        Structural invariants:
            - ``_default_backend`` is always a ``MoiraBackend`` member.
            - Backend selection is process-local and deterministic.
        Failure behavior:
            - No custom exceptions; invalid caller inputs propagate naturally.

    Canon: None (repository dispatch policy).

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.dispatch.DispatchSettings",
      "risk": "medium",
      "api": {
        "frozen": ["current_backend", "set_backend"],
        "internal": ["_default_backend"]
      },
      "state": {
        "mutable": true,
        "owners": ["DispatchSettings"]
      },
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {
        "thread": "pure_computation",
        "cross_thread_calls": "safe_read_only"
      },
      "failures": {
        "policy": "raise"
      },
      "succession": {
        "stance": "terminal"
      },
      "agent": {
        "autofix": "allowed",
        "requires_human_for": ["api_change"]
      }
    }
    [/MACHINE_CONTRACT]
    """
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
