"""Contract and drift gates for the Light Box conformance schema."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "generate_lightbox_conformance_manifest.py"


def _generator_module():
    spec = importlib.util.spec_from_file_location(
        "generate_lightbox_conformance_manifest",
        SCRIPT,
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
def schema(generator):
    return generator._load_json(generator.SCHEMA_PATH)


@pytest.fixture(scope="module")
def manifest(generator, inventory):
    return generator.build_manifest(inventory)


def _replace_first_entry(manifest, update):
    changed = dict(manifest)
    entries = list(manifest["entries"])
    first = dict(entries[0])
    update(first)
    entries[0] = first
    changed["entries"] = entries
    return changed


def test_generated_manifest_matches_inventory_and_schema(
    generator,
    inventory,
    schema,
    manifest,
) -> None:
    assert generator.validate_manifest(manifest, inventory, schema) == []
    assert generator.MANIFEST_PATH.read_text(encoding="utf-8") == generator.render_json(
        manifest
    )
    assert generator.MARKDOWN_PATH.read_text(
        encoding="utf-8"
    ) == generator.render_markdown(manifest)


def test_every_in_scope_surface_has_exactly_one_entry(inventory, manifest) -> None:
    expected = {
        row["surface_id"]
        for collection in ("python_exports", "rest_operations")
        for row in inventory[collection]
        if row["in_lightbox_calculation_scope"]
    }
    actual = [row["surface_id"] for row in manifest["entries"]]
    assert len(actual) == len(set(actual))
    assert set(actual) == expected
    assert len(actual) == (
        inventory["summary"]["python_in_scope"] + inventory["summary"]["rest_in_scope"]
    )


def test_aliases_are_visible_but_not_in_the_canonical_denominator(manifest) -> None:
    aliases = [row for row in manifest["entries"] if row["entry_role"] == "alias"]
    canonical_ids = {
        row["surface_id"]
        for row in manifest["entries"]
        if row["entry_role"] == "canonical"
    }
    assert len(aliases) == manifest["summary"]["alias_entries"]
    assert aliases
    for row in aliases:
        assert row["canonical_surface_id"] in canonical_ids
        assert row["canonical_surface_id"] != row["surface_id"]
    assert manifest["summary"]["canonical_entries"] == (
        manifest["summary"]["entries_total"] - len(aliases)
    )


def test_unadmitted_seed_keeps_every_disposition_visibly_unresolved(
    generator,
    inventory,
    manifest,
) -> None:
    admissions = set(generator.load_admissions(inventory))
    summary = manifest["summary"]
    assert summary["canonical_by_status"] == {
        "conformant": 0,
        "partial": len(admissions),
        "not_applicable": 0,
        "unresolved": summary["canonical_entries"] - len(admissions),
    }
    for row in manifest["entries"]:
        if row["surface_id"] in admissions:
            assert row["conformance_status"] == "partial"
            assert row["stage_derivation"]["disposition"] == "documented"
            assert row["evidence"]["disposition"] == "partial"
            assert row["residual"]["disposition"] == "unresolved"
            assert row["release_identity"]["verification_status"] == "not_verified"
            assert row["public_exposure"]["disposition"] == "partial"
            continue
        assert row["conformance_status"] == "unresolved"
        assert row["stage_derivation"]["disposition"] == "unresolved"
        assert row["evidence"]["disposition"] == "unresolved"
        assert row["residual"]["disposition"] == "unresolved"
        assert row["release_identity"]["verification_status"] == "unresolved"
        assert row["public_exposure"]["disposition"] == "unresolved"


def test_structural_admissions_are_bounded_and_not_release_certificates(
    generator,
    inventory,
    manifest,
) -> None:
    admissions = generator.load_admissions(inventory)
    assert len(admissions) == 173
    rows = {row["surface_id"]: row for row in manifest["entries"]}
    for surface_id in admissions:
        row = rows[surface_id]
        assert row["entry_role"] == "canonical"
        assert row["conformance_status"] == "partial"
        assert row["residual"]["disposition"] == "unresolved"
        assert row["release_identity"]["source_revision"] is None
        assert row["release_identity"]["verification_status"] == "not_verified"
        assert not row["evidence"]["receipts"]


@pytest.mark.parametrize(
    ("mutator", "expected_fragment"),
    [
        (
            lambda row: row.pop("stage_derivation"),
            "missing required field 'stage_derivation'",
        ),
        (
            lambda row: row.__setitem__(
                "semantics",
                {
                    name: value
                    for name, value in row["semantics"].items()
                    if name != "timescale"
                },
            ),
            "missing required field 'timescale'",
        ),
        (
            lambda row: row.__setitem__(
                "evidence",
                {
                    name: value
                    for name, value in row["evidence"].items()
                    if name != "tolerance_or_invariant"
                },
            ),
            "missing required field 'tolerance_or_invariant'",
        ),
        (
            lambda row: row.__setitem__(
                "release_identity",
                {
                    name: value
                    for name, value in row["release_identity"].items()
                    if name != "last_verified_on"
                },
            ),
            "missing required field 'last_verified_on'",
        ),
        (
            lambda row: row.__setitem__("unexpected_claim", True),
            "unexpected field 'unexpected_claim'",
        ),
    ],
)
def test_schema_rejects_missing_or_unknown_claim_fields(
    generator,
    schema,
    manifest,
    mutator,
    expected_fragment,
) -> None:
    changed = _replace_first_entry(manifest, mutator)
    errors = generator.validate_json_schema_instance(changed, schema)
    assert any(expected_fragment in error for error in errors), errors[:5]


def test_schema_rejects_unknown_disposition(generator, schema, manifest) -> None:
    def update(row):
        residual = dict(row["residual"])
        residual["disposition"] = "looks_good"
        row["residual"] = residual

    changed = _replace_first_entry(manifest, update)
    errors = generator.validate_json_schema_instance(changed, schema)
    assert any("outside the admitted enum" in error for error in errors)


def test_conformant_status_cannot_hide_unresolved_evidence(
    generator,
    inventory,
    manifest,
) -> None:
    changed = _replace_first_entry(
        manifest,
        lambda row: row.__setitem__("conformance_status", "conformant"),
    )
    changed["summary"] = generator._summary(changed["entries"])
    errors = generator.validate_manifest_semantics(changed, inventory)
    assert any(
        "conformant row contains unresolved evidence" in error for error in errors
    )


def test_resolved_numeric_residual_requires_measurement_unit_and_receipt(
    generator,
    inventory,
    manifest,
) -> None:
    def update(row):
        residual = dict(row["residual"])
        residual["disposition"] = "numeric"
        row["residual"] = residual

    changed = _replace_first_entry(manifest, update)
    changed["summary"] = generator._summary(changed["entries"])
    errors = generator.validate_manifest_semantics(changed, inventory)
    assert any("resolved disposition lacks measurement" in error for error in errors)
    assert any("numeric disposition needs unit" in error for error in errors)
    assert any("resolved disposition needs receipt" in error for error in errors)


def test_manifest_serialization_is_deterministic(
    generator, inventory, manifest
) -> None:
    rebuilt = generator.build_manifest(inventory)
    assert rebuilt == manifest
    assert json.loads(generator.render_json(rebuilt)) == manifest
