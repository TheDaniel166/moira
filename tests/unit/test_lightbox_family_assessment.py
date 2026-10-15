"""Completeness gates for the reviewed Light Box family assessment."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "generate_lightbox_family_assessment.py"


def _module():
    spec = importlib.util.spec_from_file_location(
        "generate_lightbox_family_assessment", SCRIPT
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generator():
    return _module()


@pytest.fixture(scope="module")
def inputs(generator):
    return (
        generator._load(generator.INVENTORY_PATH),
        generator._load(generator.REGISTER_PATH),
        generator._load(generator.MANIFEST_PATH),
        generator._load(generator.POLICY_PATH),
    )


@pytest.fixture(scope="module")
def assessment(generator, inputs):
    return generator.build_assessment(*inputs)


def test_generated_assessment_is_complete_and_current(
    generator, inputs, assessment
) -> None:
    _inventory, register, _manifest, _policy = inputs
    assert generator.validate_assessment(assessment, register) == []
    assert generator.JSON_PATH.read_text(encoding="utf-8") == generator.render_json(
        assessment
    )
    assert generator.MARKDOWN_PATH.read_text(
        encoding="utf-8"
    ) == generator.render_markdown(assessment)


def test_every_family_is_reviewed_without_becoming_conformant(assessment) -> None:
    summary = assessment["summary"]
    assert summary["reviewed_families"] == summary["family_count"]
    assert summary["canonical_surface_count"] == 1251
    assert summary["surface_conformance_counts"]["conformant"] == 0
    assert summary["surface_conformance_counts"]["partial"] > 0
    assert summary["surface_conformance_counts"]["unresolved"] > 0


def test_stage_four_and_five_are_not_empty(assessment) -> None:
    stages = assessment["summary"]["families_by_review_stage"]
    assert stages["stage_4_phenomena_relationships"] > 0
    assert stages["stage_5_remaining_tail"] > 0


def test_major_gap_and_mixed_families_remain_explicit(assessment) -> None:
    by_id = {row["family_id"]: row for row in assessment["families"]}
    assert by_id["phenomena"]["assessment_status"] == "major_gap"
    relationship = by_id["relationship"]
    assert relationship["assessment_status"] == "mixed"
    assert relationship["canonical_surface_count"] == 42
    assert relationship["production_user_surface_count"] == 14
    assert relationship["conformance_counts"] == {
        "conformant": 0,
        "not_applicable": 0,
        "partial": 14,
        "unresolved": 28,
    }
    assert by_id["ashtakavarga"]["assessment_status"] == "major_gap"
    assert by_id["positions-frame"]["assessment_status"] == "strong_exemplar"


def test_assessment_serialization_is_deterministic(
    generator, inputs, assessment
) -> None:
    rebuilt = generator.build_assessment(*inputs)
    assert rebuilt == assessment
    assert json.loads(generator.render_json(rebuilt)) == assessment
