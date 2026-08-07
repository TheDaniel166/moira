"""Contracts for root-conftest ownership of test-support imports."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


pytestmark = pytest.mark.parallel(reason="worker_isolated")


_ROOT_CONFTEST = Path(__file__).resolve().parents[2] / "conftest.py"


@pytest.mark.parametrize(
    ("module_name", "is_package"),
    (
        ("support", True),
        ("_pytest_plugins", True),
        ("_pytest_plugins.configuration", False),
    ),
)
def test_root_sanitizer_evicts_foreign_repo_owned_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    is_package: bool,
) -> None:
    foreign_module = ModuleType(module_name)
    foreign_path = tmp_path.joinpath(*module_name.split("."))
    foreign_module.__file__ = str(
        foreign_path / "__init__.py"
        if is_package
        else foreign_path.with_suffix(".py")
    )
    if is_package:
        foreign_module.__path__ = [str(foreign_path)]
    monkeypatch.setitem(sys.modules, module_name, foreign_module)
    if "." in module_name:
        package_name = module_name.split(".", 1)[0]
        foreign_package = ModuleType(package_name)
        foreign_package.__file__ = str(
            tmp_path / package_name / "__init__.py"
        )
        foreign_package.__path__ = [str(tmp_path / package_name)]
        monkeypatch.setitem(sys.modules, package_name, foreign_package)
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

    assert sys.modules.get(module_name) is not foreign_module
