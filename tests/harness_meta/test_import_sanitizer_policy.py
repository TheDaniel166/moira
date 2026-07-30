"""Contracts for root-conftest ownership of test-support imports."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


_ROOT_CONFTEST = Path(__file__).resolve().parents[2] / "conftest.py"


def test_root_sanitizer_evicts_foreign_support_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    foreign_support = ModuleType("support")
    foreign_support.__file__ = str(tmp_path / "support" / "__init__.py")
    monkeypatch.setitem(sys.modules, "support", foreign_support)
    original_path = list(sys.path)

    spec = importlib.util.spec_from_file_location(
        "_moira_root_conftest_sanitizer_probe",
        _ROOT_CONFTEST,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_path

    assert sys.modules.get("support") is not foreign_support
