"""Validation tests for replayable Light Box evidence contracts."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "replay_lightbox_receipts.py"


def _module():
    spec = importlib.util.spec_from_file_location("replay_lightbox_receipts", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_contracts_are_unique_and_cover_every_structural_admission() -> None:
    replay = _module()
    contracts, inventory = replay.load_contracts()
    contract_surfaces = {
        surface_id
        for contract in contracts["contracts"]
        for surface_id in contract["surface_ids"]
    }
    admissions = replay._load(
        REPO_ROOT / "wiki" / "03_validation" / "LIGHT_BOX_CONFORMANCE_ADMISSIONS.json"
    )
    admitted = {row["surface_id"] for row in admissions["entries"]}
    assert contract_surfaces == admitted
    assert inventory["surface_fingerprint_sha256"]


def test_passed_count_uses_terminal_pytest_summary() -> None:
    replay = _module()
    assert replay._passed_count(".... 4 passed in 1.00s") == 4
    assert replay._passed_count("1 passed\nthen 7 passed in 2.00s") == 7
    assert replay._passed_count("............... [100%]\npolicy receipt") == 15
    assert replay._passed_count("2 failed") == 0


def test_contract_hash_is_order_stable() -> None:
    replay = _module()
    assert replay._sha({"b": 2, "a": 1}) == replay._sha({"a": 1, "b": 2})
