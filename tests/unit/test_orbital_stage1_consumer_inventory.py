"""Static release gates for Orbital Core Stage 1 consumer ownership."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "audit_orbital_stage1_consumers.py"
INVENTORY = (
    REPO_ROOT
    / "docs"
    / "architecture"
    / "ORBITAL_CORE_STAGE1_CONSUMER_INVENTORY.md"
)


def _audit_module():
    spec = importlib.util.spec_from_file_location(
        "audit_orbital_stage1_consumers", SCRIPT
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_generated_inventory_matches_source_truth() -> None:
    audit = _audit_module()
    assert INVENTORY.read_text(encoding="utf-8") == audit.render_inventory()


def test_every_discovered_site_has_a_decision() -> None:
    audit = _audit_module()
    sites = audit.discover_sites()
    assert sites
    audit.validate_source_guards(sites)
    for site in sites:
        assert audit.decision_for(site).disposition


def test_governing_spec_starting_paths_remain_covered() -> None:
    audit = _audit_module()
    sites = audit.discover_sites()
    discovered = {(site.category, site.path) for site in sites}
    text = INVENTORY.read_text(encoding="utf-8")
    for category, paths in (
        ("reader", audit.READER_STARTING_FILES),
        ("frame", audit.FRAME_STARTING_FILES),
    ):
        for path in paths:
            assert (REPO_ROOT / path).is_file()
            assert f"| {category} | `{path}` |" in text
            if (category, path) in discovered:
                assert any(
                    site.category == category and site.path == path
                    for site in sites
                )
