from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

import pytest

from scripts.build_visibility_named_spectral_direct_probe import (
    VisibilityLabError,
    bin_comparison,
    expand_runs,
    inspect_spec,
    load_spec,
    parse_spectrum,
    render_input,
    validate_spec,
    vertical_grids,
)
from scripts.validate_visibility_named_spectral_direct_probe import (
    _bin_comparison as independent_bin_comparison,
)
from scripts.validate_visibility_named_spectral_direct_probe import (
    _expected_input as independent_expected_input,
)
from scripts.validate_visibility_named_spectral_direct_probe import (
    _vertical_grids as independent_vertical_grids,
)
from scripts.validate_visibility_named_spectral_direct_probe import (
    expected_runs,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_named_spectral_direct_probe_spec.json"
)
CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase1_named_spectral_direct_checkpoint_2026-07-30.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_probe_spec_is_bounded_and_preserves_checkpoint_three() -> None:
    assert inspect_spec(SPEC_PATH) == {
        "spec_id": (
            "physical-heliacal-phase1-named-spectral-direct-probe-2026-07-30"
        ),
        "status": "research_probe_not_runtime_data_pack",
        "profile_count": 6,
        "vertical_condition_count": 13,
        "vertical_grid_level_counts": {
            "source_native": 50,
            "near_horizon_piecewise_refined_v1": 290,
            "near_horizon_piecewise_reference_v1": 579,
            "near_horizon_piecewise_convergence_v1": 1157,
        },
        "spectral_output_row_count": 8001,
        "run_count": 54,
        "twostr_run_count": 50,
        "DISORT_run_count": 4,
        "repeat_run_count": 1,
        "fine_reference_admitted": True,
        "runtime_data_pack_authorized": False,
        "engine_changes_authorized": False,
    }
    spec = load_spec(SPEC_PATH)
    predecessor = spec["base_labs"]["direct_geometry_checkpoint"]
    for role in ("spec", "builder", "validator", "checkpoint"):
        path = REPO_ROOT / predecessor[f"{role}_path"]
        assert path.stat().st_size == predecessor[f"{role}_bytes"]
        assert _sha256(path) == predecessor[f"{role}_sha256"]


def test_vertical_grids_are_independently_reconstructed() -> None:
    spec = load_spec(SPEC_PATH)
    builder = vertical_grids(spec)
    validator = independent_vertical_grids(spec)

    assert builder == validator
    assert builder["source_native"] is None
    for grid_id, count in (
        ("near_horizon_piecewise_refined_v1", 290),
        ("near_horizon_piecewise_reference_v1", 579),
        ("near_horizon_piecewise_convergence_v1", 1157),
    ):
        levels = builder[grid_id]
        assert levels is not None
        assert len(levels) == count
        assert levels[0] == 0.0
        assert levels[-1] == 120.0
        assert all(left < right for left, right in zip(levels, levels[1:]))


def test_builder_and_validator_expand_the_same_run_contract() -> None:
    spec = load_spec(SPEC_PATH)
    builder_runs = expand_runs(spec)
    validator_runs = expected_runs(spec)

    assert builder_runs == validator_runs
    assert len(builder_runs) == 54
    assert sum(run["rte_solver"] == "disort" for run in builder_runs) == 4
    assert sum("repeat_of" in run for run in builder_runs) == 1
    assert {
        run["profile"]
        for run in builder_runs
        if "vertical_grid_matrix" in run["roles"]
        and run["target_true_altitude_deg"] == 0.25
    } == set(spec["profiles"])


def test_controlled_inputs_are_independently_rendered_and_fail_closed() -> None:
    spec = load_spec(SPEC_PATH)
    grids = vertical_grids(spec)
    run = next(
        item
        for item in expand_runs(spec)
        if item["profile"] == "us_standard"
        and item["target_true_altitude_deg"] == 0.25
        and item["grid_id"] == "near_horizon_piecewise_refined_v1"
        and item["REPTRAN_resolution"] == "fine"
        and item["rte_solver"] == "disort"
    )
    levels = grids[run["grid_id"]]
    rendered = render_input(run, spec, levels)

    assert rendered == independent_expected_input(run, spec, levels)
    assert "mol_abs_param reptran fine\n" in rendered
    assert "rte_solver disort\n" in rendered
    assert "number_of_streams 16\n" in rendered
    assert "atm_z_grid 0 0.025 0.05" in rendered
    for forbidden in (
        "aerosol_",
        "aerosol_default",
        "albedo ",
        "ozone_column",
        "altitude ",
        "mc_spherical",
    ):
        assert forbidden not in rendered


def test_source_native_input_omits_atm_z_grid() -> None:
    spec = load_spec(SPEC_PATH)
    run = next(
        item
        for item in expand_runs(spec)
        if item["grid_id"] == "source_native"
    )
    rendered = render_input(run, spec, None)

    assert "atm_z_grid" not in rendered
    assert "rte_solver twostr\n" in rendered
    assert "number_of_streams" not in rendered


def test_spectrum_parser_applies_horizontal_projection_once() -> None:
    spec = load_spec(SPEC_PATH)
    run = next(
        item
        for item in expand_runs(spec)
        if item["profile"] == "us_standard"
        and item["target_true_altitude_deg"] == 5.0
        and item["grid_id"] == "near_horizon_piecewise_refined_v1"
        and item["REPTRAN_resolution"] == "medium"
        and item["rte_solver"] == "twostr"
    )
    horizontal = 0.01
    text = "".join(
        f"{380.0 + index * 0.05:9.3f} {horizontal:.6e}\n"
        for index in range(8001)
    )
    parsed = parse_spectrum(text, run=run, spec=spec)

    expected = horizontal / math.sin(math.radians(5.0))
    assert parsed["summary"]["row_count"] == 8001
    assert parsed["summary"]["zero_sample_count"] == 0
    assert parsed["direct_spectral_transmission"][0] == pytest.approx(expected)
    assert parsed["direct_spectral_transmission"][-1] == pytest.approx(expected)


def test_bin_comparisons_are_independently_recomputed() -> None:
    spec = load_spec(SPEC_PATH)
    reference = [0.8] * 8001
    candidate = [0.8] * 8001
    candidate[7600:7620] = [0.4] * 20

    builder = bin_comparison(
        candidate,
        reference,
        bin_width_nm=1.0,
        spec=spec,
    )
    validator = independent_bin_comparison(
        candidate,
        reference,
        bin_width_nm=1.0,
        spec=spec,
    )

    assert builder == validator
    assert builder["maximum_bin_start_nm"] == 760.0
    assert builder["maximum_magnitude_difference"] == pytest.approx(
        2.5 * math.log10(2.0)
    )
    assert builder["opacity_classification_mismatch_count"] == 0


def test_runtime_or_api_authorization_is_rejected() -> None:
    spec = copy.deepcopy(load_spec(SPEC_PATH))
    spec["runtime_boundary"]["engine_changes_authorized"] = True

    with pytest.raises(VisibilityLabError, match="runtime boundary"):
        validate_spec(spec)


def test_reptran_module_remains_external_and_fine_is_the_reference() -> None:
    spec = load_spec(SPEC_PATH)
    reptran = spec["source"]["REPTRAN_module"]

    assert reptran["archive_bytes"] == 698709957
    assert reptran["archive_member_count"] == 292
    assert reptran["existing_source_tree_overlap_sha256_mismatch_count"] == 0
    assert reptran["embedded_notice_or_license_file_count"] == 0
    assert (
        reptran["redistribution_policy"]
        == "external_research_input_only_not_redistributed_by_moira"
    )
    assert (
        spec["spectral_design"]["REPTRAN_resolutions"]["fine"]["role"]
        == "admitted_full_spectral_reference"
    )
    assert spec["runtime_boundary"]["runtime_dependency_on_REPTRAN"] is False


def test_compact_checkpoint_binds_the_cross_platform_artifact() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))

    assert checkpoint["phase1_complete"] is False
    assert (
        checkpoint["named_atmosphere_full_spectral_direct_gate"]
        == "passed_for_clear_molecular_AFGL_profiles_and_surface_observer"
    )
    for role in ("specification", "builder", "validator"):
        receipt = checkpoint[role]
        path = REPO_ROOT / receipt["path"]
        assert path.stat().st_size == receipt["bytes"]
        assert _sha256(path) == receipt["sha256"]
    artifact = checkpoint["external_artifact"]
    assert (
        artifact["manifest_sha256"]
        == "b2bac79b30a3458fe17f8446b3da40f61deba1d7320b679724ebd60a65a539e8"
    )
    assert artifact["run_count"] == 54
    assert artifact["DISORT_anchor_run_count"] == 4
    assert artifact["DISORT_parity_byte_identical"] is True
    assert artifact["validated_on_WSL_python"] is True
    assert artifact["validated_on_windows_python_3_14_3"] is True
    assert checkpoint["findings"]["REPTRAN_fine_reference_admitted"] is True
    assert (
        checkpoint["findings"]["REPTRAN_medium_rejected_as_full_spectral_truth"]
        is True
    )
    assert checkpoint["numerical_summary"][
        "combined_candidate_grid_error_bound_by_bin_nm"
    ]["1"] == pytest.approx(0.0027130750801615698)
    assert checkpoint["runtime_boundary"][
        "REPTRAN_archive_redistribution_allowed"
    ] is False
