"""Completeness and drift gates for the Light Box family register."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "generate_lightbox_family_register.py"


def _generator_module():
    spec = importlib.util.spec_from_file_location(
        "generate_lightbox_family_register", SCRIPT
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generator():
    return _generator_module()


@pytest.fixture(scope="module")
def inventory(generator):
    return generator.load_current_inventory()


@pytest.fixture(scope="module")
def register(generator, inventory):
    return generator.build_register(inventory)


def test_generated_register_matches_inventory(generator, inventory, register) -> None:
    assert generator.validate_register(register, inventory) == []
    assert generator.JSON_PATH.read_text(encoding="utf-8") == generator.render_json(
        register
    )
    assert generator.MARKDOWN_PATH.read_text(
        encoding="utf-8"
    ) == generator.render_markdown(register)


def test_every_in_scope_surface_has_one_family(inventory, register) -> None:
    expected = {
        row["surface_id"]
        for collection in ("python_exports", "rest_operations")
        for row in inventory[collection]
        if row["in_lightbox_calculation_scope"]
    }
    ids = [row["surface_id"] for row in register["entries"]]
    assert len(ids) == len(set(ids))
    assert set(ids) == expected
    for row in register["entries"]:
        assert row["family_id"]
        assert row["family_label"]
        assert row["domain_group"]
        assert row["assignment_basis"]


def test_aliases_remain_visible_without_inflating_family_denominator(register) -> None:
    canonical = {
        row["surface_id"]
        for row in register["entries"]
        if row["entry_role"] == "canonical"
    }
    aliases = [row for row in register["entries"] if row["entry_role"] == "alias"]
    assert aliases
    assert register["summary"]["canonical_entries"] == len(canonical)
    assert register["summary"]["alias_entries"] == len(aliases)
    for row in aliases:
        assert row["canonical_surface_id"] in canonical


def test_product_use_is_promoted_only_from_revision_bound_snapshot(
    generator,
    inventory,
    register,
) -> None:
    usage = generator.load_product_usage(inventory)
    expected = {row["canonical_surface_id"] for row in usage["entries"]}
    p0 = {
        row["surface_id"]
        for row in register["entries"]
        if row["entry_role"] == "canonical" and row["priority"] == "P0"
    }
    assert p0 == expected
    assert register["summary"]["canonical_by_priority"]["P0"] == len(expected)
    assert register["summary"]["canonical_by_review_state"] == {
        "seeded": 0,
        "reviewed": register["summary"]["canonical_entries"],
        "blocked": 0,
    }
    for row in register["entries"]:
        assert row["exposure"] in {"production_user", "public_api", "source_only"}
        assert row["review_state"] == "reviewed"
        assert row["review_stage"] in {
            "stage_2_exemplars",
            "stage_3_product_use",
            "stage_4_phenomena_relationships",
            "stage_5_remaining_tail",
        }
        assert row["assessment_status"] in {
            "strong_exemplar",
            "partial",
            "mixed",
            "major_gap",
            "unresolved",
        }


def test_cross_transport_family_mapping_has_known_core_examples(register) -> None:
    by_family = {}
    for row in register["entries"]:
        if row["entry_role"] == "canonical":
            by_family.setdefault(row["family_id"], set()).add(row["transport"])
    assert by_family["houses"] == {"python", "rest"}
    assert by_family["progressions"] == {"python", "rest"}
    assert by_family["relationship"] == {"python", "rest"}


def test_register_serialization_is_deterministic(
    generator, inventory, register
) -> None:
    rebuilt = generator.build_register(inventory)
    assert rebuilt == register
    assert json.loads(generator.render_json(rebuilt)) == register
