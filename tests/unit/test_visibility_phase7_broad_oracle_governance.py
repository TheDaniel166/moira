"""Governance for the Phase 7 broad physical-event oracle."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC_PATH = (
    _REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "physical_visibility_phase7_broad_oracle_matrix_v1.json"
)
_GOLDEN_PATH = (
    _REPO_ROOT
    / "tests"
    / "golden"
    / "physical_visibility_phase7_broad_oracle.json"
)
_BUILDER_PATH = (
    _REPO_ROOT / "scripts" / "build_visibility_phase7_broad_oracle.py"
)
_VALIDATOR_PATH = (
    _REPO_ROOT / "scripts" / "validate_visibility_phase7_broad_oracle.py"
)
_ACQUISITION_PATH = (
    _REPO_ROOT / "scripts" / "acquire_visibility_phase7_oracle_sources.py"
)
_DISCOVERY_PATH = (
    _REPO_ROOT / "scripts" / "discover_visibility_phase7_oracle_windows.py"
)
_GOLDEN_SHA256 = (
    "29d96b8eb1187c013357039df8c224e6a41381d83bb81fd961e24057a563ede9"
)
_PACK_MANIFEST_SHA256 = (
    "cf93433a9f66a5ea92832271ce3c4b023fcc8693164803539a9f1be85b17468c"
)
_CERTIFICATE_SHA256 = (
    "eacf8c373606c1628cebdd4caa611ece533d368c32c7f86674a13e04a4c13d3e"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = {
        alias.name.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    result.update(
        node.module.split(".", maxsplit=1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
    )
    return result


def _golden() -> dict[str, object]:
    return json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))


def test_phase7_matrix_is_the_complete_target_phase_product() -> None:
    spec = json.loads(_SPEC_PATH.read_text(encoding="utf-8"))
    policy = spec["selection_policy"]
    targets = tuple(policy["required_targets"])
    phases = tuple(policy["required_phases"])
    cases = tuple(spec["cases"])

    assert len(cases) == policy["required_matrix_cell_count"] == 16
    assert {(case["target"], case["phase"]) for case in cases} == {
        (target, phase) for target in targets for phase in phases
    }
    assert spec["release_gate"] == {
        "timed_event_oracle_case_count": 12,
        "typed_negative_regression_case_count": 4,
        "external_source_grid_step_seconds": 60.0,
        "external_root_interpolation": "linear_visibility_margin",
        "maximum_engine_oracle_difference_seconds": 60.0,
        "oracle_reproduction_tolerance_seconds": 0.01,
        "source_query_half_width_hours": 4.0,
        "source_acquisition_spec_sha256": (
            "ba061013c6e6258475baab4442b072c82c887aabc840cc19f5b0126542eb9323"
        ),
        "negative_cells_are_not_event_time_oracles": True,
    }


def test_phase7_golden_is_immutable_and_bound_to_exact_inputs() -> None:
    golden = _golden()

    assert _sha256(_GOLDEN_PATH) == _GOLDEN_SHA256
    assert golden["matrix_spec"]["sha256"] == _sha256(_SPEC_PATH)
    assert golden["exact_data_pack"]["manifest_sha256"] == (
        _PACK_MANIFEST_SHA256
    )
    assert golden["required_engine_contract"] == {
        "event_time_semantics": "visibility_margin_zero",
        "boundary_source": "visibility_margin",
        "crossing_completeness_state": (
            "certified_lipschitz_zero_enclosure"
        ),
        "crossing_certificate_source_sha256": _CERTIFICATE_SHA256,
        "unresolved_certificate_interval_count": 0,
    }


def test_phase7_offline_oracle_tools_import_no_moira_network_or_numpy() -> None:
    forbidden = {"http", "moira", "numpy", "requests", "socket", "urllib"}
    for path in (_BUILDER_PATH, _VALIDATOR_PATH):
        assert not (_imported_roots(path) & forbidden)

    assert "urllib" in _imported_roots(_ACQUISITION_PATH)
    assert "moira" in _imported_roots(_DISCOVERY_PATH)


def test_phase7_golden_separates_timed_oracles_from_negative_regressions() -> None:
    golden = _golden()
    coverage = golden["coverage"]
    cases = tuple(golden["cases"])
    timed = tuple(
        case for case in cases if case["independent_event_time_claimed"]
    )
    negative = tuple(
        case for case in cases if not case["independent_event_time_claimed"]
    )

    assert coverage["matrix_cell_count"] == len(cases) == 16
    assert coverage["independent_timed_event_oracle_count"] == len(timed) == 12
    assert coverage["typed_engine_negative_regression_count"] == 4
    assert len(negative) == 4
    assert {case["target"] for case in timed} == {
        "Mars",
        "Jupiter",
        "Saturn",
        "Sirius",
    }
    assert {case["phase"] for case in timed} == {
        "morning_first_rising",
        "morning_first_setting",
        "evening_last_rising",
        "evening_last_setting",
    }
    for case in timed:
        assert case["validation_class"] == "independent_timed_event_oracle"
        assert case["independent_oracle"]["guard_day_status"] == (
            "does_not_qualify"
        )
        assert case["absolute_engine_oracle_difference_seconds"] <= 60.0
    for case in negative:
        assert case["validation_class"] == "typed_engine_negative_regression"
        assert "independent_oracle" not in case
        result = case["captured_engine_result"]
        assert result["status"] in {"not_found", "not_evaluable"}
        assert result["reason"]
        assert result["event_jd_ut"] is None


def test_phase7_external_source_inventory_is_complete_and_checksum_bound() -> None:
    golden = _golden()
    files = golden["external_sources"]["jpl_horizons"]["files"]

    assert golden["coverage"]["external_source_file_count"] == len(files) == 40
    assert len({receipt["sha256"] for receipt in files.values()}) == 40
    assert all(receipt["authority"] == "NASA/JPL Horizons" for receipt in files.values())
    assert all(receipt["row_count"] == 481 for receipt in files.values())
    assert all(receipt["STEP_SIZE"] == "1 min" for receipt in files.values())
    assert all(receipt["APPARENT"] == "AIRLESS" for receipt in files.values())
    assert all(receipt["REF_SYSTEM"] == "ICRF" for receipt in files.values())
    saturn_targets = tuple(
        receipt
        for source_id, receipt in files.items()
        if "saturn" in source_id and source_id.endswith(":target")
    )
    assert len(saturn_targets) == 4
    assert all(
        receipt["QUANTITIES"] == "4,9,14,15,43"
        for receipt in saturn_targets
    )


def test_phase7_worst_observed_residual_is_well_inside_fixed_limit() -> None:
    timed = tuple(
        case
        for case in _golden()["cases"]
        if case["independent_event_time_claimed"]
    )
    residuals = tuple(
        case["absolute_engine_oracle_difference_seconds"] for case in timed
    )

    assert max(residuals) < 6.0
    assert max(residuals) == 5.8789461851119995
