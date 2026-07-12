"""
Canonical Python import surface for the native Moira backend.

The compiled extension lives under the private module name ``_moira_native``.
Keeping the public import as a Python shim prevents stale extension binaries
from winning import resolution when multiple `.pyd` files are present.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import EXTENSION_SUFFIXES
import sys
from importlib import import_module
from pathlib import Path


def _load_backend():
    try:
        return import_module("._moira_native", __package__)
    except ImportError:
        package_dir = Path(__file__).resolve().parent
        candidates = []
        for suffix in EXTENSION_SUFFIXES:
            candidates.append(package_dir / f"_moira_native{suffix}")
            candidates.extend(sorted((package_dir / "Release").glob(f"_moira_native*{suffix}")))
            candidates.extend(sorted((package_dir / "Debug").glob(f"_moira_native*{suffix}")))
        for path in candidates:
            if not path.exists():
                continue
            spec = importlib.util.spec_from_file_location(f"{__package__}._moira_native", path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"{__package__}._moira_native"] = module
            spec.loader.exec_module(module)
            return module
        raise


_backend = _load_backend()

__backend_file__ = getattr(_backend, "__file__", None)

for _name in dir(_backend):
    if _name.startswith("__") and _name not in {"__doc__", "__name__"}:
        continue
    globals()[_name] = getattr(_backend, _name)


def _ensure_native_nutation_ready() -> None:
    """Register the packaged IERS tables before a native R06 evaluation."""

    if _backend.nutation_2000r06_series_ready():
        return
    from .nutation_2000a import _ensure_tables_loaded

    _ensure_tables_loaded()


def _nutation_ready_wrapper(name: str):
    raw = getattr(_backend, name)

    def call(*args, **kwargs):
        _ensure_native_nutation_ready()
        return raw(*args, **kwargs)

    call.__name__ = name
    call.__qualname__ = name
    call.__doc__ = getattr(raw, "__doc__", None)
    return call


# These entry points release the GIL or call the shared native series directly.
# Table readiness therefore belongs in this Python-governed boundary, before
# native execution begins, rather than in hidden import-time I/O.
for _name in (
    "nutation_2000a",
    "target_topocentric_altitude",
    "find_sun_at_alt",
    "search_heliacal_rising",
    "search_heliacal_setting",
    "heliacal_signed_elongation",
):
    if hasattr(_backend, _name):
        globals()[_name] = _nutation_ready_wrapper(_name)

__doc__ = getattr(_backend, "__doc__", __doc__)
__all__ = [name for name in dir(_backend) if not name.startswith("_")]
