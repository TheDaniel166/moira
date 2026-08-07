"""Fail-closed registration for Moira's required pytest policy plugins."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

import pytest


PLUGIN_DIR = Path(__file__).resolve().parent

# Keep this tuple in runtime initialization order. Dynamic registration invokes
# historic configure hooks immediately.
REQUIRED_PLUGIN_MODULES = (
    "_pytest_plugins.classification",
    "_pytest_plugins.configuration",
    "_pytest_plugins.determinism",
    "_pytest_plugins.network_policy",
    "_pytest_plugins.known_issues",
    "_pytest_plugins.xdist_coordination",
    "_pytest_plugins.resources",
    "_pytest_plugins.lifecycle",
    "_pytest_plugins.artifacts",
    "_pytest_plugins.evidence",
)


def _local_plugin_module(module_name: str):
    module = importlib.import_module(module_name)
    module_file = getattr(module, "__file__", None)
    if module_file is None:
        raise pytest.UsageError(
            f"Required Moira pytest plugin has no file identity: {module_name}"
        )
    try:
        local = Path(module_file).resolve().is_relative_to(PLUGIN_DIR)
    except (OSError, RuntimeError):
        local = False
    if not local:
        raise pytest.UsageError(
            "Required Moira pytest plugin resolved outside the local "
            f"tests/_pytest_plugins directory: {module_name} -> {module_file}"
        )
    alias_name = f"tests.{module_name}"
    alias = sys.modules.get(alias_name)
    if alias is not None and alias is not module:
        raise pytest.UsageError(
            "Moira pytest plugin was loaded under two import identities: "
            f"{module_name} and {alias_name}"
        )
    return module


def register_required_plugins(config) -> None:
    """Register every required local plugin or fail if one was suppressed."""

    manager = config.pluginmanager
    for module_name in REQUIRED_PLUGIN_MODULES:
        if manager.is_blocked(module_name):
            raise pytest.UsageError(
                f"Required Moira pytest plugin was blocked: {module_name}"
            )
        module = _local_plugin_module(module_name)
        registered = manager.get_plugin(module_name)
        if registered is None:
            existing_name = manager.get_name(module)
            if existing_name is not None and existing_name != module_name:
                raise pytest.UsageError(
                    "Required Moira pytest plugin was registered under an "
                    f"unexpected name: {module_name} -> {existing_name}"
                )
            manager.register(module, name=module_name)
        elif registered is not module:
            raise pytest.UsageError(
                "Required Moira pytest plugin name is owned by a different "
                f"object: {module_name}"
            )


def verify_required_plugins(config) -> None:
    """Recheck identity so late unregistration cannot create a false green."""

    manager = config.pluginmanager
    errors: list[str] = []
    for module_name in REQUIRED_PLUGIN_MODULES:
        try:
            module = _local_plugin_module(module_name)
        except pytest.UsageError as exc:
            errors.append(str(exc))
            continue
        if manager.get_plugin(module_name) is not module:
            errors.append(f"{module_name} is not registered by canonical name")
    if errors:
        raise pytest.UsageError(
            "Required Moira pytest plugin manifest is incomplete:\n- "
            + "\n- ".join(errors)
        )
