"""Packaging boundary checks for optional lunar dependencies."""

from __future__ import annotations

import importlib
import sys

import pytest


def test_lunar_module_imports_without_optional_deps(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"spiceypy", "laspy"} or name.startswith("laspy."):
            raise ImportError(f"missing optional dependency: {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)
    sys.modules.pop("moira.lunar_limb", None)
    import moira.lunar_limb as lunar_limb

    try:
        with pytest.raises(ImportError, match=r"moira-astro\[lunar\]"):
            lunar_limb.official_lunar_limb_profile_adjustment(
                2451545.0,
                0.0,
                0.0,
                0.0,
                0.0,
                400000.0,
            )
    finally:
        sys.modules.pop("moira.lunar_limb", None)
        monkeypatch.undo()
        importlib.import_module("moira.lunar_limb")
