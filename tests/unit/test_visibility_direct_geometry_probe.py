from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from scripts.build_visibility_direct_geometry_probe import (
    VisibilityLabError,
    continuous_slant_optical_depth,
    inspect_spec,
    layer_optical_depths,
    load_spec,
    midpoint_chapman_surface_slant_optical_depth,
    render_input,
    shell_slant_optical_depth,
    validate_spec,
    vertical_grids,
)
from scripts.validate_visibility_direct_geometry_probe import (
    ValidationError,
    _midpoint_chapman_surface_slant_optical_depth,
    _validate_file_receipt,
    independent_continuous_slant_optical_depth,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_direct_geometry_probe_spec.json"
)
CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase1_direct_geometry_checkpoint_2026-07-29.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _continuous_builder(
    spec: dict[str, object],
    scale_height_km: float,
    altitude_deg: float,
) -> float:
    boundary = spec["scientific_boundary"]
    controlled = spec["controlled_exponential_atmospheres"]
    oracle = spec["independent_oracle"]
    assert isinstance(boundary, dict)
    assert isinstance(controlled, dict)
    assert isinstance(oracle, dict)
    value, _ = continuous_slant_optical_depth(
        earth_radius_km=float(boundary["earth_radius_km"]),
        scale_height_km=scale_height_km,
        top_altitude_km=float(boundary["top_altitude_km"]),
        target_true_altitude_deg=altitude_deg,
        vertical_optical_depth=float(controlled["vertical_optical_depth"]),
        relative_tolerance=float(oracle["builder_relative_tolerance"]),
        absolute_tolerance=float(oracle["builder_absolute_tolerance"]),
        initial_panels=int(oracle["builder_initial_equal_root_altitude_panels"]),
        maximum_depth=int(oracle["maximum_recursion_depth"]),
    )
    return value


def _continuous_validator(
    spec: dict[str, object],
    scale_height_km: float,
    altitude_deg: float,
) -> float:
    boundary = spec["scientific_boundary"]
    controlled = spec["controlled_exponential_atmospheres"]
    oracle = spec["independent_oracle"]
    assert isinstance(boundary, dict)
    assert isinstance(controlled, dict)
    assert isinstance(oracle, dict)
    value, _ = independent_continuous_slant_optical_depth(
        earth_radius_km=float(boundary["earth_radius_km"]),
        scale_height_km=scale_height_km,
        top_altitude_km=float(boundary["top_altitude_km"]),
        target_true_altitude_deg=altitude_deg,
        vertical_optical_depth=float(controlled["vertical_optical_depth"]),
        relative_tolerance=float(oracle["validator_relative_tolerance"]),
        absolute_tolerance=float(oracle["validator_absolute_tolerance"]),
        maximum_depth=int(oracle["maximum_recursion_depth"]),
    )
    return value


def test_probe_spec_is_bounded_and_preserves_predecessor_identities() -> None:
    assert inspect_spec(SPEC_PATH) == {
        "spec_id": "physical-heliacal-phase1-direct-geometry-probe-2026-07-29",
        "status": "research_probe_not_runtime_data_pack",
        "vertical_grid_level_counts": {
            "afglus_source_levels_v1": 50,
            "near_horizon_piecewise_refined_v1": 290,
        },
        "controlled_scale_height_count": 6,
        "target_altitude_count": 12,
        "nonrepeat_case_count": 144,
        "uvspec_run_count": 145,
        "exact_horizon_admitted": False,
        "runtime_data_pack_authorized": False,
        "frozen_predecessor_identity_count": 6,
    }
    spec = load_spec(SPEC_PATH)
    for declaration in spec["base_labs"].values():
        for role in ("spec", "builder", "validator"):
            path = REPO_ROOT / declaration[f"{role}_path"]
            assert path.stat().st_size == declaration[f"{role}_bytes"]
            assert _sha256(path) == declaration[f"{role}_sha256"]


def test_refined_grid_is_contiguous_and_resolves_the_lower_atmosphere() -> None:
    spec = load_spec(SPEC_PATH)
    grids = vertical_grids(spec)
    refined = grids["near_horizon_piecewise_refined_v1"]

    assert len(refined) == 290
    assert refined[0] == 120.0
    assert refined[-1] == 0.0
    assert all(a > b for a, b in zip(refined, refined[1:]))
    lower_steps = [
        high - low
        for high, low in zip(refined, refined[1:])
        if high <= 2.0
    ]
    assert lower_steps
    assert all(step == pytest.approx(0.025) for step in lower_steps)


@pytest.mark.parametrize("scale_height_km", [0.25, 1.5, 8.0, 20.0])
@pytest.mark.parametrize("altitude_deg", [0.0, 0.25, 5.0, 90.0])
def test_independent_continuous_oracles_agree(
    scale_height_km: float,
    altitude_deg: float,
) -> None:
    spec = load_spec(SPEC_PATH)
    builder_value = _continuous_builder(
        spec,
        scale_height_km,
        altitude_deg,
    )
    validator_value = _continuous_validator(
        spec,
        scale_height_km,
        altitude_deg,
    )

    assert builder_value == pytest.approx(
        validator_value,
        rel=2e-9,
        abs=2e-12,
    )
    if altitude_deg == 90.0:
        assert builder_value == pytest.approx(0.1, rel=2e-12, abs=2e-13)


def test_refined_grid_meets_declared_admitted_geometry_tolerance() -> None:
    spec = load_spec(SPEC_PATH)
    boundary = spec["scientific_boundary"]
    controlled = spec["controlled_exponential_atmospheres"]
    grids = vertical_grids(spec)
    refined = grids["near_horizon_piecewise_refined_v1"]
    source = grids["afglus_source_levels_v1"]
    maximum_refined = 0.0
    maximum_source = 0.0
    maximum_refined_shell = 0.0

    for scale_height in controlled["scale_height_km"]:
        for altitude in controlled["target_true_altitude_deg"]["admitted_domain"]:
            continuous = _continuous_validator(
                spec,
                float(scale_height),
                float(altitude),
            )
            refined_shell = shell_slant_optical_depth(
                refined,
                earth_radius_km=float(boundary["earth_radius_km"]),
                scale_height_km=float(scale_height),
                target_true_altitude_deg=float(altitude),
                vertical_optical_depth=float(controlled["vertical_optical_depth"]),
            )
            refined_midpoint = midpoint_chapman_surface_slant_optical_depth(
                refined,
                earth_radius_km=float(boundary["earth_radius_km"]),
                scale_height_km=float(scale_height),
                target_true_altitude_deg=float(altitude),
                vertical_optical_depth=float(controlled["vertical_optical_depth"]),
            )
            source_midpoint = midpoint_chapman_surface_slant_optical_depth(
                source,
                earth_radius_km=float(boundary["earth_radius_km"]),
                scale_height_km=float(scale_height),
                target_true_altitude_deg=float(altitude),
                vertical_optical_depth=float(controlled["vertical_optical_depth"]),
            )
            independent_midpoint = (
                _midpoint_chapman_surface_slant_optical_depth(
                    refined,
                    earth_radius_km=float(boundary["earth_radius_km"]),
                    scale_height_km=float(scale_height),
                    target_true_altitude_deg=float(altitude),
                    vertical_optical_depth=float(
                        controlled["vertical_optical_depth"]
                    ),
                )
            )
            assert refined_midpoint == pytest.approx(
                independent_midpoint,
                rel=2e-13,
                abs=2e-13,
            )
            maximum_refined = max(
                maximum_refined,
                abs(refined_midpoint - continuous) / continuous,
            )
            maximum_source = max(
                maximum_source,
                abs(source_midpoint - continuous) / continuous,
            )
            maximum_refined_shell = max(
                maximum_refined_shell,
                abs(refined_shell - continuous) / continuous,
            )

    assert maximum_refined <= 0.001
    assert maximum_refined_shell <= 0.001
    assert maximum_source > 0.001


def test_controlled_layer_optical_depths_close_exactly() -> None:
    spec = load_spec(SPEC_PATH)
    controlled = spec["controlled_exponential_atmospheres"]
    for levels in vertical_grids(spec).values():
        for scale_height in controlled["scale_height_km"]:
            depths = layer_optical_depths(
                levels,
                scale_height_km=float(scale_height),
                vertical_optical_depth=float(controlled["vertical_optical_depth"]),
            )
            assert depths[0] == 0.0
            assert all(value > 0.0 for value in depths[1:])
            assert math.fsum(depths) == pytest.approx(
                controlled["vertical_optical_depth"],
                rel=2e-15,
                abs=2e-15,
            )


def test_controlled_uvspec_input_keeps_horizon_diagnostic_out_of_runtime() -> None:
    spec = load_spec(SPEC_PATH)
    horizon_case = {
        "case_id": "horizon",
        "grid_id": "near_horizon_piecewise_refined_v1",
        "scale_height_km": 1.5,
        "target_true_altitude_deg": 0.0,
        "domain_role": "diagnostic_only",
    }
    admitted_case = {
        **horizon_case,
        "case_id": "admitted",
        "target_true_altitude_deg": 0.25,
        "domain_role": "admitted_domain",
    }

    horizon = render_input(horizon_case, spec)
    admitted = render_input(admitted_case, spec)

    assert "sza 90\n" in horizon
    assert "sza 89.75\n" in admitted
    for rendered in (horizon, admitted):
        assert "rte_solver disort\n" in rendered
        assert "pseudospherical\n" in rendered
        assert "number_of_streams 16\n" in rendered
        assert "mc_randomseed 49979687\n" in rendered
        assert "mol_tau_file abs molecular_tau.dat\n" in rendered
        assert "no_scattering\n" in rendered
        assert "output_user lambda edir uavgdir\n" in rendered
        assert "aerosol_" not in rendered
        assert "mc_spherical" not in rendered
    assert spec["scientific_boundary"]["exact_horizon_status"] == (
        "diagnostic_only_not_admitted"
    )
    assert spec["scientific_boundary"]["uavgdir_production_status"].startswith(
        "forbidden_"
    )


def test_spec_rejects_a_weakened_runtime_boundary() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    spec["runtime_boundary"]["network_allowed"] = True
    with pytest.raises(VisibilityLabError, match="runtime boundary"):
        validate_spec(spec)


def test_independent_receipt_validator_rejects_tampering(
    tmp_path: Path,
) -> None:
    path = tmp_path / "evidence.txt"
    path.write_bytes(b"bound evidence\n")
    receipt = {
        "path": "evidence.txt",
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }
    assert _validate_file_receipt(
        tmp_path,
        receipt,
        label="test",
    ) == "evidence.txt"

    path.write_bytes(b"tampered evidence\n")
    with pytest.raises(ValidationError, match="receipt mismatch"):
        _validate_file_receipt(tmp_path, receipt, label="test")


def test_checkpoint_identity_matches_current_tools_when_present() -> None:
    if not CHECKPOINT_PATH.is_file():
        pytest.skip("external direct-geometry checkpoint has not been emitted")
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    assert checkpoint["schema"] == (
        "moira.visibility-direct-geometry-checkpoint/v1"
    )
    assert checkpoint["artifact_status"] == (
        "phase1_direct_geometry_evidence_not_runtime_data_pack"
    )
    assert checkpoint["specification"]["sha256"] == _sha256(SPEC_PATH)
    assert checkpoint["builder"]["sha256"] == _sha256(
        REPO_ROOT / "scripts" / "build_visibility_direct_geometry_probe.py"
    )
    assert checkpoint["validator"]["sha256"] == _sha256(
        REPO_ROOT / "scripts" / "validate_visibility_direct_geometry_probe.py"
    )
    assert checkpoint["external_artifact"]["manifest_sha256"] == (
        "b69b377bd465b4740ef0dacd802c03d9fb6ee9eaf809a41356d60126dd23cd92"
    )
    assert checkpoint["external_artifact"]["case_count"] == 145
    assert checkpoint["external_artifact"]["all_files_bound"] is True
    refined_error = checkpoint["numerical_summary"][
        "maximum_refined_grid_admitted_midpoint_vs_continuous_relative_error"
    ]
    source_grid_error = checkpoint["numerical_summary"][
        "maximum_source_grid_admitted_midpoint_vs_continuous_relative_error"
    ]
    tolerance = checkpoint["acceptance"][
        "refined_midpoint_vs_continuous_admitted_relative_slant_optical_depth_tolerance"
    ]
    assert refined_error <= tolerance
    assert source_grid_error > tolerance
    assert checkpoint["exact_horizon_admitted"] is False
    assert checkpoint["runtime_data_pack_authorized"] is False
