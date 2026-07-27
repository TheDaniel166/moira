"""Staleness gates for generated Hellenistic runtime documentation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


_REPO_ROOT = Path(__file__).parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "generate_hellenistic_inventory.py"
_AUTHORITATIVE_STATUS_PATHS = (
    "moira/timelords.py",
    "moira/hermetic_decans.py",
    "tests/unit/test_timelords_public_api.py",
    "wiki/01_doctrines/timelords/decennials_admission_doctrine.md",
    "wiki/02_services/REST_API_REFERENCE.md",
    "wiki/02_standards/DECANS_BACKEND_STANDARD.md",
    "wiki/02_standards/TIMELORDS_BACKEND_STANDARD.md",
    "wiki/03_validation/VALIDATION_ASTROLOGY.md",
    "wiki/06_roadmap/HELLENISTIC_FREE_ENHANCED_WORKSPACE_PRODUCT_PLAN.md",
    (
        "wiki/06_roadmap/hellenistic_completion/"
        "HELLENISTIC_ENGINE_GATES_2026-07.md"
    ),
    (
        "wiki/06_roadmap/hellenistic_completion/"
        "WESTERN_HELLENISTIC_GAP_TRACKER.md"
    ),
    "wiki/07_audit/FEATURE_AUDIT_2026.md",
    "wiki/07_audit/WESTERN_SYSTEMS_AUDIT.md",
)
_SUPERSEDED_STATUS_FRAGMENTS = (
    "research quarantine",
    "source-quarantined",
    "l3/l4 quarantined",
    "l3/l4 are quarantined",
    "levels 3–4 remain quarantined",
    "deep methods remain deferred",
    "valens distribution scoring is quarantined",
    "valens distributions/delineations quarantined",
    "hephaistio l4 remains explicitly deferred",
    "testvalensinterpretivelayerisquarantined",
)


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


def test_closed_exclusions_cannot_regress_to_stale_status_language() -> None:
    """Keep settled exclusions from being rediscovered as roadmap work."""

    corpus = "\n".join(
        (_REPO_ROOT / relative_path).read_text(encoding="utf-8").lower()
        for relative_path in _AUTHORITATIVE_STATUS_PATHS
    )
    for fragment in _SUPERSEDED_STATUS_FRAGMENTS:
        assert fragment not in corpus
