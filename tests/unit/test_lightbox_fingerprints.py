"""Separate API identity, discovery freshness, and historical execution evidence."""

from __future__ import annotations

import ast
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


@pytest.fixture(scope="module")
def generator():
    return module("generate_lightbox_calculation_inventory")


@pytest.fixture(scope="module")
def inventory(generator):
    return generator.build_inventory()


def digest(generator, value):
    return generator._canonical_sha256(generator.structural_payload(value))


@pytest.mark.parametrize("field,value", [
    ("source_line", 999999), ("documentation_paths", ["docs/new.md"]),
    ("test_paths", ["tests/new.py"]), ("owner_resolution", "new-resolution"),
    ("classification_rationale", "Clearer explanation."), ("exclusion_reason", "Clearer exclusion."),
])
def test_discovery_changes_do_not_rebind_structural_evidence(generator, inventory, field, value):
    changed = deepcopy(inventory)
    changed["python_exports"][0][field] = value
    changed["rest_operations"][0][field] = value
    assert digest(generator, changed) == inventory["structural_fingerprint_sha256"]
    assert generator.render_json(changed) != generator.render_json(inventory)
    assert generator._canonical_sha256(changed) != generator._canonical_sha256(inventory)


def test_engine_label_and_discovery_counts_do_not_rebind_evidence(generator, inventory):
    changed = deepcopy(inventory)
    changed["engine_version"] = "future"
    changed["summary"]["python_in_scope_without_documentation_mentions"] += 1
    assert digest(generator, changed) == digest(generator, inventory)


@pytest.mark.parametrize("field,value", [
    ("surface_id", "python:moira.facade:new_export"), ("alias_of", "python:moira.facade:other"),
    ("canonical_id", "python:moira.facade:other"), ("surface_kind", "calculation"),
    ("in_lightbox_calculation_scope", True), ("classification_basis", "new-rule"),
    ("owner_module", "moira.other"), ("source_path", "moira/other.py"),
    ("api_contract_sha256", "0" * 64),
])
def test_api_and_classification_changes_require_review(generator, inventory, field, value):
    changed = deepcopy(inventory)
    assert changed["python_exports"][0][field] != value
    changed["python_exports"][0][field] = value
    assert digest(generator, changed) != digest(generator, inventory)


def test_projection_is_order_independent_and_does_not_mutate_input(generator, inventory):
    before = deepcopy(inventory)
    changed = deepcopy(inventory)
    changed["python_exports"].reverse()
    changed["rest_operations"].reverse()
    assert digest(generator, changed) == digest(generator, inventory)
    assert inventory == before


@pytest.mark.parametrize("collection", ["python_exports", "rest_operations"])
def test_export_or_route_membership_changes_bind(generator, inventory, collection):
    changed = deepcopy(inventory)
    changed[collection].pop()
    assert digest(generator, changed) != digest(generator, inventory)


def declaration(generator, source):
    return generator._canonical_sha256(generator._declaration(ast.parse(source).body[0]))


def test_source_lines_comments_docstrings_and_function_body_are_not_api_shape(generator):
    original = 'def calculate(x: float = 1.0) -> float:\n    """Old prose."""\n    return x\n'
    changed = '\n\n# New comment\ndef calculate(x: float = 1.0) -> float:\n    """New prose."""\n    return x * 2\n'
    assert declaration(generator, original) == declaration(generator, changed)
    # Body equivalence is deliberately not claimed. Replay provenance remains source-bound.
    assert original != changed


@pytest.mark.parametrize("changed", [
    "def calculate(x: float = 2.0) -> float: return x",
    "def calculate(x: int = 1.0) -> float: return x",
    "def calculate(x: float = 1.0) -> int: return x",
    "def calculate(*, x: float = 1.0) -> float: return x",
])
def test_python_parameter_default_kind_and_result_annotation_changes_bind(generator, changed):
    assert declaration(generator, "def calculate(x: float = 1.0) -> float: return x") != declaration(generator, changed)


@pytest.mark.parametrize("changed", [
    "class Result:\n    value: int = 1",
    "class Result:\n    value: float = 2",
    "class Result:\n    value: float = 1\n    units: str = 'degrees'",
])
def test_result_fields_and_defaults_bind(generator, changed):
    assert declaration(generator, "class Result:\n    value: float = 1") != declaration(generator, changed)


def api_schema():
    operation = {"operationId": "calculate", "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Input"}}}}}
    schema = {"components": {"schemas": {"Input": {
        "type": "object", "description": "Old prose", "properties": {
            "description": {"type": "number", "minimum": 0, "default": 1},
            "next": {"$ref": "#/components/schemas/Input"},
        }, "required": ["description"],
    }}}}
    return operation, schema


def test_rest_prose_is_excluded_but_named_description_fields_are_retained(generator):
    operation, schema = api_schema()
    changed = deepcopy(schema)
    changed["components"]["schemas"]["Input"]["description"] = "New prose"
    assert generator._openapi_contract(operation, schema) == generator._openapi_contract(operation, changed)
    changed["components"]["schemas"]["Input"]["properties"]["description"]["minimum"] = 2
    assert generator._openapi_contract(operation, schema) != generator._openapi_contract(operation, changed)


@pytest.mark.parametrize("field,value", [("type", "integer"), ("default", 5), ("minimum", -1)])
def test_referenced_rest_schema_changes_bind(generator, field, value):
    operation, schema = api_schema()
    changed = deepcopy(schema)
    changed["components"]["schemas"]["Input"]["properties"]["description"][field] = value
    assert generator._openapi_contract(operation, schema) != generator._openapi_contract(operation, changed)


def test_unreferenced_rest_schemas_do_not_rebind_unrelated_operations(generator):
    operation, schema = api_schema()
    changed = deepcopy(schema)
    changed["components"]["schemas"]["Unrelated"] = {"type": "number"}
    assert generator._openapi_contract(operation, schema) == generator._openapi_contract(operation, changed)


def test_closed_object_constraints_are_api_changes(generator):
    operation, schema = api_schema()
    changed = deepcopy(schema)
    changed["components"]["schemas"]["Input"]["additionalProperties"] = False
    assert generator._openapi_contract(operation, schema) != generator._openapi_contract(operation, changed)


def test_schema_renderer_versions_do_not_rebind_unchanged_api(generator, inventory):
    changed = deepcopy(inventory)
    changed["schema_renderer"] = {"fastapi": "future", "pydantic": "future"}
    assert digest(generator, changed) == digest(generator, inventory)
    assert generator.render_json(changed) != generator.render_json(inventory)


def test_generated_check_still_detects_stale_discovery_without_writing(generator, inventory, tmp_path, monkeypatch):
    changed = deepcopy(inventory)
    changed["python_exports"][0]["source_line"] += 100
    assert digest(generator, changed) == inventory["structural_fingerprint_sha256"]
    json_path, md_path = tmp_path / "inventory.json", tmp_path / "inventory.md"
    json_path.write_text(generator.render_json(inventory), encoding="utf-8")
    md_path.write_text(generator.render_markdown(inventory), encoding="utf-8")
    before = json_path.read_bytes(), md_path.read_bytes()
    monkeypatch.setattr(generator, "JSON_PATH", json_path)
    monkeypatch.setattr(generator, "MARKDOWN_PATH", md_path)
    monkeypatch.setattr(generator, "build_inventory", lambda: changed)
    monkeypatch.setattr(generator, "_relative", lambda path: path.name)
    monkeypatch.setattr(sys, "argv", ["inventory", "--check"])
    assert generator.main() == 1
    assert (json_path.read_bytes(), md_path.read_bytes()) == before


def test_runtime_discovery_line_and_mention_changes_keep_receipt_binding(generator, inventory, monkeypatch):
    original_owner = generator._source_owner
    original_read = generator._read_texts
    monkeypatch.setattr(generator, "_source_owner", lambda *args: {
        **original_owner(*args), "source_line": original_owner(*args)["source_line"] + 10,
    })
    monkeypatch.setattr(generator, "_read_texts", lambda paths: [
        *original_read(paths), ("docs/added-guide.md", "jd_from_datetime"),
    ])
    changed = generator.build_inventory()
    assert changed["structural_fingerprint_sha256"] == inventory["structural_fingerprint_sha256"]
    assert changed["surface_fingerprint_sha256"] != inventory["surface_fingerprint_sha256"]
    manifest_generator = module("generate_lightbox_conformance_manifest")
    manifest = manifest_generator.build_manifest(changed)
    matrix_generator = module("generate_lightbox_assurance_matrix")
    original_receipts = matrix_generator._load(matrix_generator.RECEIPTS_PATH)
    matrix = matrix_generator.build_matrix(
        matrix_generator._load(matrix_generator.CONTRACTS_PATH), original_receipts, manifest,
    )
    assert matrix["receipt_source_revision"] == original_receipts["source_revision"]
    assert matrix["receipt_artifact_status"] == original_receipts["artifact_status"]


@pytest.fixture
def legacy(generator, inventory, monkeypatch):
    replay = module("replay_lightbox_receipts")
    old = deepcopy(inventory)
    old["schema_version"] = "moira.lightbox-calculation-inventory/v1"
    for key in ("structural_fingerprint_sha256", "structural_fingerprint_version", "surface_fingerprint_sha256"):
        old.pop(key)
    for collection in ("python_exports", "rest_operations"):
        for row in old[collection]:
            row.pop("api_contract_sha256")
    old["surface_fingerprint_sha256"] = replay._sha(old)
    contracts = {"contracts": [{"claim_id": "LB-TEST"}]}
    row = {"claim_id": "LB-TEST", "inventory_fingerprint_sha256": old["surface_fingerprint_sha256"],
           "source_revision": "1" * 40, "artifact_status": "local_unreleased_worktree",
           "executed_at_utc": "2026-10-01T00:00:00Z", "output_tail": ["1 passed"], "status": "passed"}
    row = {"receipt_id": replay._sha(row), **row}
    receipts = {"schema_version": "moira.lightbox-evidence-receipts/v1",
                "inventory_fingerprint_sha256": old["surface_fingerprint_sha256"],
                "source_revision": "1" * 40, "artifact_status": "local_unreleased_worktree",
                "contracts_sha256": replay._sha(contracts), "receipts": [row]}
    monkeypatch.setattr(replay, "load_contracts", lambda: (contracts, inventory))
    return replay, old, receipts


def test_legacy_migration_preserves_every_execution_record_and_is_explicit(legacy, inventory):
    replay, old, receipts = legacy
    before = deepcopy(receipts)
    updated = replay.migrate_legacy_binding(receipts, old)
    assert updated["receipts"] == before["receipts"]
    assert receipts == before
    assert updated["source_revision"] == before["source_revision"]
    assert updated["inventory_fingerprint_sha256"] == inventory["structural_fingerprint_sha256"]
    assert updated["binding_migration"]["legacy_receipt_set_sha256"] == replay._sha(before)
    assert replay.reclassify_existing(updated) == updated


@pytest.mark.parametrize("damage", ["inventory", "contracts", "classification", "exact_source", "row"])
def test_legacy_migration_fails_closed(legacy, damage):
    replay, old, receipts = legacy
    if damage == "inventory":
        receipts["inventory_fingerprint_sha256"] = "0" * 64
    elif damage == "contracts":
        receipts["contracts_sha256"] = "0" * 64
    elif damage == "classification":
        old["python_exports"][0]["surface_kind"] = "other"
        old.pop("surface_fingerprint_sha256")
        old["surface_fingerprint_sha256"] = replay._sha(old)
        receipts["inventory_fingerprint_sha256"] = old["surface_fingerprint_sha256"]
    elif damage == "exact_source":
        receipts["artifact_status"] = "exact_source_revision"
    else:
        receipts["receipts"][0]["executed_at_utc"] = "tampered"
    with pytest.raises(replay.ReceiptReplayError):
        replay.migrate_legacy_binding(receipts, old)


def test_reclassification_cannot_silently_migrate_or_rebind(legacy, inventory):
    replay, old, receipts = legacy
    with pytest.raises(replay.ReceiptReplayError, match="explicit migration"):
        replay.reclassify_existing(receipts)
    updated = replay.migrate_legacy_binding(receipts, old)
    updated["inventory_fingerprint_sha256"] = "0" * 64
    with pytest.raises(replay.ReceiptReplayError, match="structural inventory drift"):
        replay.reclassify_existing(updated)


def test_migrated_receipts_cannot_be_promoted_or_rewritten(legacy, inventory):
    replay, old, receipts = legacy
    updated = replay.migrate_legacy_binding(receipts, old)
    updated["receipts"][0]["executed_at_utc"] = "tampered"
    with pytest.raises(replay.ReceiptReplayError, match="records changed"):
        replay.validate_receipt_binding(updated, inventory["structural_fingerprint_sha256"])


def test_current_receipts_retain_a_verifiable_legacy_execution_boundary():
    replay = module("replay_lightbox_receipts")
    current = replay._load(replay.DEFAULT_RECEIPT_PATH)
    replay.validate_receipt_binding(current, current["inventory_fingerprint_sha256"])
    if "binding_migration" in current:
        assert current["binding_migration"]["legacy_header"]["source_revision"] == current["source_revision"]


def test_migration_does_not_establish_exact_release_evidence(legacy):
    replay, old, receipts = legacy
    current = replay.migrate_legacy_binding(receipts, old)
    gate = module("check_lightbox_release_gate")
    assert any("fresh v2 receipts required" in error for error in gate._receipt_errors(current, {}))


def test_python_declaration_hash_is_independent_of_newlines_and_unicode_prose(generator):
    unix = 'def calculate(x: float = 1.0) -> float:\n    """λ"""\n    return x\n'
    assert declaration(generator, unix) == declaration(generator, unix.replace("\n", "\r\n"))


def test_declaration_hash_does_not_use_interpreter_ast_display(generator, monkeypatch):
    source = "def calculate(x: float = 1.0) -> float: return x"
    original = declaration(generator, source)
    monkeypatch.setattr(ast, "dump", lambda *args, **kwargs: "different interpreter presentation")
    assert declaration(generator, source) == original
    shape = generator._ast_shape(ast.parse(source).body[0].args)
    assert shape["fields"]["posonlyargs"] == []
    assert shape["fields"]["kwarg"] is None


def test_legacy_receipt_schema_is_rejected_even_with_a_matching_hash():
    matrix = module("generate_lightbox_assurance_matrix")
    receipts = matrix._load(matrix.RECEIPTS_PATH)
    receipts["schema_version"] = "moira.lightbox-evidence-receipts/v1"
    with pytest.raises(matrix.AssuranceMatrixError, match="unsupported receipts schema"):
        matrix.build_matrix(matrix._load(matrix.CONTRACTS_PATH), receipts, matrix._load(matrix.MANIFEST_PATH))
