"""Staleness gates for generated Hellenistic runtime documentation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


_REPO_ROOT = Path(__file__).parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "generate_hellenistic_inventory.py"


def _generator_module():
    spec = importlib.util.spec_from_file_location(
        "generate_hellenistic_inventory",
        _SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_generated_hellenistic_inventories_match_runtime_truth() -> None:
    generator = _generator_module()
    assert generator.CAPABILITY_PATH.read_text(
        encoding="utf-8"
    ) == generator.render_capability_matrix()
    assert generator.API_PATH.read_text(
        encoding="utf-8"
    ) == generator.render_api_inventory()
