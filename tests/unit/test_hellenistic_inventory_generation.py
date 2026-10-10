"""Staleness gates for generated Hellenistic runtime documentation."""

from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


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


@pytest.fixture(scope="module")
def runtime_app():
    from moira_server.app import create_app

    app = create_app()
    app.openapi()
    return app


def _app_with_schema(app, schema):
    return SimpleNamespace(title=app.title, version=app.version, openapi=lambda: schema)


def test_unrelated_routes_leave_family_inventory_stable_but_change_global_inventory(runtime_app):
    """New Vedic routes must not stale a Hellenistic-only generated artifact."""
    from scripts.sync_rest_api_reference import _surface

    generator = _generator_module()
    schema = deepcopy(runtime_app.openapi())
    schema["paths"]["/v1/muhurta/inventory-regression-probe"] = {
        "post": {"operationId": "unrelated_muhurta_probe", "responses": {"200": {"description": "OK"}}}
    }
    changed = _app_with_schema(runtime_app, schema)
    assert generator.render_api_inventory(changed) == generator.render_api_inventory(runtime_app)
    assert generator.render_capability_matrix(changed) == generator.render_capability_matrix(runtime_app)
    # The general REST gate continues to detect the changed server-wide surface.
    assert _surface(changed) != _surface(runtime_app)


@pytest.mark.parametrize("change", ["operation_id", "response_schema"])
def test_admitted_route_contract_changes_still_invalidate_inventory(runtime_app, change):
    generator = _generator_module()
    schema = deepcopy(runtime_app.openapi())
    selected = generator._operations(runtime_app)[0]
    operation = schema["paths"][selected["path"]][selected["method"].lower()]
    if change == "operation_id":
        operation["operationId"] = "changed_admitted_operation"
    else:
        operation["responses"]["200"] = {
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ChangedResponse"}}}
        }
    changed = _app_with_schema(runtime_app, schema)
    assert generator.render_api_inventory(changed) != generator.render_api_inventory(runtime_app)


def test_closed_exclusions_remain_rejected(runtime_app):
    generator = _generator_module()
    schema = deepcopy(runtime_app.openapi())
    schema["paths"]["/v1/hermetic/reintroduced"] = {"post": {"responses": {"200": {"description": "OK"}}}}
    with pytest.raises(ValueError, match="Closed-exclusion"):
        generator.render_api_inventory(_app_with_schema(runtime_app, schema))


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
