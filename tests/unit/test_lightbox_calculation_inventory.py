"""Completeness and drift gates for the Light Box calculation inventory."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "generate_lightbox_calculation_inventory.py"


def _generator_module():
    spec = importlib.util.spec_from_file_location(
        "generate_lightbox_calculation_inventory",
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
    return generator.build_inventory()


def test_generated_inventory_matches_runtime_and_source_truth(
    generator, inventory
) -> None:
    assert generator.JSON_PATH.read_text(encoding="utf-8") == generator.render_json(
        inventory
    )
    assert generator.MARKDOWN_PATH.read_text(
        encoding="utf-8"
    ) == generator.render_markdown(inventory)


def test_every_facade_export_is_inventoried_exactly_once(inventory) -> None:
    import moira.facade as facade

    rows = inventory["python_exports"]
    names = [row["public_name"] for row in rows]
    assert len(names) == len(set(names))
    assert set(names) == set(facade.__all__)
    assert len(rows) == len(facade.__all__)


def test_every_openapi_operation_is_inventoried_exactly_once(inventory) -> None:
    from moira_server.app import create_app

    schema = create_app().openapi()
    expected = {
        f"rest:{method.upper()}:{path}"
        for path, path_item in schema["paths"].items()
        for method, operation in path_item.items()
        if method.upper()
        in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD", "TRACE"}
        and isinstance(operation, dict)
    }
    actual = [row["surface_id"] for row in inventory["rest_operations"]]
    assert len(actual) == len(set(actual))
    assert set(actual) == expected


def test_every_row_has_a_stable_classification_and_source_owner(inventory) -> None:
    allowed = {
        "calculation",
        "composition_profile",
        "transport_adapter",
        "reference_query",
        "validation_helper",
        "operational_meta",
        "excluded_type",
        "excluded_value",
    }
    for collection in ("python_exports", "rest_operations"):
        for row in inventory[collection]:
            assert row["surface_kind"] in allowed
            assert row["classification_basis"]
            assert row["classification_rationale"]
            assert row["source_path"]
            assert (REPO_ROOT / row["source_path"]).is_file()
            assert isinstance(row["source_line"], int) and row["source_line"] > 0
            if row["in_lightbox_calculation_scope"]:
                assert row["exclusion_reason"] is None
            else:
                assert row["exclusion_reason"]


def test_aliases_point_to_present_canonical_surfaces(inventory) -> None:
    for collection in ("python_exports", "rest_operations"):
        rows = inventory[collection]
        ids = {row["surface_id"] for row in rows}
        for row in rows:
            assert row["canonical_id"] in ids
            if row["alias_of"] is not None:
                assert row["alias_of"] == row["canonical_id"]
                assert row["alias_of"] != row["surface_id"]


def test_only_explicit_non_calculation_classes_are_excluded(inventory) -> None:
    excluded_kinds = {
        "reference_query",
        "validation_helper",
        "operational_meta",
        "excluded_type",
        "excluded_value",
    }
    for collection in ("python_exports", "rest_operations"):
        for row in inventory[collection]:
            assert row["in_lightbox_calculation_scope"] is (
                row["surface_kind"] not in excluded_kinds
            )


def test_reference_links_are_repository_relative_and_existing(inventory) -> None:
    for collection in ("python_exports", "rest_operations"):
        for row in inventory[collection]:
            for key in ("documentation_paths", "test_paths"):
                assert row[key] == sorted(set(row[key]))
                for relative in row[key]:
                    assert not Path(relative).is_absolute()
                    assert (REPO_ROOT / relative).is_file()


def test_derived_lightbox_reports_cannot_self_credit_documentation(generator) -> None:
    documentation_paths = set(generator._documentation_paths())
    assert generator.MARKDOWN_PATH not in documentation_paths
    assert generator.CONFORMANCE_MARKDOWN_PATH not in documentation_paths
    assert all(
        not (path.name.startswith("LIGHT_BOX_") and path.name.endswith(".generated.md"))
        for path in documentation_paths
    )


def test_lightbox_governance_tests_cannot_self_credit_evidence(generator) -> None:
    assert all(
        not path.name.startswith("test_lightbox_") for path in generator._test_paths()
    )


def test_fingerprint_and_serialization_are_deterministic(generator, inventory) -> None:
    rebuilt = generator.build_inventory()
    assert rebuilt == inventory
    fingerprint = inventory["surface_fingerprint_sha256"]
    without_fingerprint = dict(inventory)
    del without_fingerprint["surface_fingerprint_sha256"]
    assert fingerprint == generator._canonical_sha256(without_fingerprint)
    assert inventory["structural_fingerprint_sha256"] == generator._canonical_sha256(
        generator.structural_payload(inventory)
    )
    loaded = json.loads(generator.render_json(inventory))
    assert loaded == inventory
