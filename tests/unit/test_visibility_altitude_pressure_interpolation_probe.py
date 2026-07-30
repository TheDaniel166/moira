from __future__ import annotations

import ast
import copy
import hashlib
import math
from pathlib import Path

import pytest

import scripts.build_visibility_elevated_site_probe as elevated_dependency
from scripts.build_visibility_altitude_pressure_interpolation_probe import (
    VisibilityAltitudePressureProbeError,
    _scale_o4_payload,
    expand_runs,
    inspect_spec,
    load_spec,
    render_input,
    site_relative_vertical_grid,
    summarize,
    validate_spec,
)
from scripts.validate_visibility_altitude_pressure_interpolation_probe import (
    ValidationError,
)
from scripts.validate_visibility_altitude_pressure_interpolation_probe import (
    _assert_cross_platform_equal as independent_assert_cross_platform_equal,
)
from scripts.validate_visibility_altitude_pressure_interpolation_probe import (
    _expected_input as independent_expected_input,
)
from scripts.validate_visibility_altitude_pressure_interpolation_probe import (
    _expected_runs as independent_expected_runs,
)
from scripts.validate_visibility_altitude_pressure_interpolation_probe import (
    _float32 as independent_float32,
)
from scripts.validate_visibility_altitude_pressure_interpolation_probe import (
    _site_relative_vertical_grid as independent_site_relative_vertical_grid,
)
from scripts.validate_visibility_altitude_pressure_interpolation_probe import (
    _validate_receipt_shape as independent_validate_receipt_shape,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_altitude_pressure_interpolation_probe_spec.json"
)
VALIDATOR_PATH = (
    REPO_ROOT
    / "scripts"
    / "validate_visibility_altitude_pressure_interpolation_probe.py"
)


def _synthetic_profiles(
    spec: dict[str, object],
) -> tuple[
    dict[tuple[str, float], dict[str, object]],
    dict[tuple[str, float], dict[str, object]],
]:
    builder: dict[tuple[str, float], dict[str, object]] = {}
    validator: dict[tuple[str, float], dict[str, object]] = {}
    altitude_axis = spec["axes"]["observer_altitude_m"]  # type: ignore[index]
    altitudes = sorted(
        {
            *altitude_axis["training_nodes"],  # type: ignore[index]
            *altitude_axis["reserved_holdouts"],  # type: ignore[index]
        }
    )
    for profile in spec["atmosphere_profiles"]:  # type: ignore[union-attr]
        for altitude in altitudes:
            pressure = float(format(1013.0 - 0.092 * altitude, ".15g"))
            builder[(profile, altitude)] = {
                "metadata": {"profile_surface_pressure_hpa": pressure}
            }
            validator[(profile, altitude)] = {
                "profile_surface_pressure_hpa": pressure
            }
    return builder, validator


def _result_from_extinction(
    wavelength_nm: float,
    extinction_magnitude: float,
) -> dict[str, float]:
    transmission = 10.0 ** (-extinction_magnitude / 2.5)
    return {
        "wavelength_nm": wavelength_nm,
        "horizontal_direct_transmittance": transmission,
        "geometric_projection_sin_altitude": 1.0,
        "direct_spectral_transmission": transmission,
        "optical_depth": -math.log(transmission),
        "extinction_magnitude": extinction_magnitude,
    }


def test_spec_is_bounded_and_runtime_inert() -> None:
    assert inspect_spec(SPEC_PATH) == {
        "spec_id": (
            "physical-heliacal-phase1-altitude-pressure-interpolation-v5-2026-07-30"
        ),
        "profile_count": 6,
        "maximum_unfiltered_run_count": 5148,
        "wavelength_count_per_run": 3,
        "hard_pressure_filter_applied_during_expansion": True,
        "runtime_boundary": {
            "network_allowed": False,
            "automatic_download_allowed": False,
            "engine_dependency_allowed": False,
            "engine_runtime_invocation_allowed": False,
            "generated_numerical_products_only": True,
            "production_data_pack_authorized": False,
            "engine_changes_authorized": False,
        },
    }


def test_builder_and_validator_expand_the_same_hard_bound_filtered_runs() -> None:
    spec = load_spec(SPEC_PATH)
    builder_profiles, validator_profiles = _synthetic_profiles(spec)
    builder_runs = expand_runs(spec, builder_profiles)
    validator_runs = independent_expected_runs(spec, validator_profiles)

    assert builder_runs == validator_runs
    assert len(builder_runs) < 5148
    assert len({run["run_id"] for run in builder_runs}) == len(builder_runs)
    assert {
        run["partition"] for run in builder_runs
    } == {
        "training",
        "altitude_holdout",
        "pressure_holdout",
        "joint_holdout",
    }
    assert all(
        500.0 <= run["requested_surface_pressure_hpa"] <= 1100.0
        for run in builder_runs
    )


def test_builder_and_validator_render_identical_inputs() -> None:
    spec = load_spec(SPEC_PATH)
    builder_profiles, _ = _synthetic_profiles(spec)
    runs = expand_runs(spec, builder_profiles)
    for run in (runs[0], runs[len(runs) // 2], runs[-1]):
        assert render_input(run, spec) == independent_expected_input(run, spec)
        assert "aerosol_modify ssa set 0\n" in render_input(run, spec)
        assert "mol_file O4 o4.dat cm_3\n" in render_input(run, spec)
        assert "wavelength_grid_file wavelength_grid.dat\n" in render_input(
            run,
            spec,
        )
        assert "\natm_z_grid " in render_input(run, spec)


def test_site_relative_vertical_grid_is_independently_reconstructed() -> None:
    spec = load_spec(SPEC_PATH)
    for altitude in (0.0, 125.0, 1688.0, 5000.0):
        builder = site_relative_vertical_grid(altitude, spec)
        validator = independent_site_relative_vertical_grid(altitude, spec)
        assert builder == validator
        assert builder[0] == altitude / 1000.0
        assert builder[-1] == 120.0
        assert all(a < b for a, b in zip(builder, builder[1:]))
    assert len(site_relative_vertical_grid(0.0, spec)) == 290


def test_pressure_o4_scaling_is_ratio_squared_and_ratio_one_is_byte_exact() -> None:
    source = b"# z O4\n2 4e-8\n0 9e-8\n"
    assert _scale_o4_payload(
        source,
        1.0,
        elevated_dependency,
    ) == source
    scaled = _scale_o4_payload(
        source,
        0.925,
        elevated_dependency,
    ).decode("utf-8")
    values = [
        float(line.split()[1])
        for line in scaled.splitlines()
        if line and not line.startswith("#")
    ]
    assert values[0] == pytest.approx(4e-8 * 0.925**2, rel=3e-7)
    assert values[1] == pytest.approx(9e-8 * 0.925**2, rel=3e-7)


def test_validator_compares_serialized_profile_values_as_binary32() -> None:
    assert independent_float32(1002.06641) == 1002.06640625
    assert independent_float32(1002.06641) == independent_float32(
        1002.06640625
    )


def test_validator_admits_checksum_bound_empty_diagnostic_files() -> None:
    assert independent_validate_receipt_shape(
        {
            "path": "runs/example/stderr.txt",
            "bytes": 0,
            "sha256": hashlib.sha256(b"").hexdigest(),
        },
        "empty diagnostic",
    )["bytes"] == 0


def test_extinction_interpolation_reproduces_a_bilinear_surface() -> None:
    spec = load_spec(SPEC_PATH)
    runs = []
    results = {}
    for altitude in (0.0, 500.0):
        for pressure in (0.85, 0.925):
            run_id = f"node_{altitude}_{pressure}"
            run = {
                "run_id": run_id,
                "partition": "training",
                "profile": "us_standard",
                "observer_altitude_m": altitude,
                "pressure_ratio": pressure,
                "target_true_altitude_deg": 5.0,
            }
            extinction = 1.0 + altitude * 0.0002 + pressure * 0.5
            runs.append(run)
            results[run_id] = [_result_from_extinction(550.0, extinction)]
    holdout = {
        "run_id": "joint_holdout",
        "partition": "joint_holdout",
        "profile": "us_standard",
        "observer_altitude_m": 125.0,
        "pressure_ratio": 0.8688,
        "target_true_altitude_deg": 5.0,
    }
    runs.append(holdout)
    truth = 1.0 + 125.0 * 0.0002 + 0.8688 * 0.5
    results["joint_holdout"] = [_result_from_extinction(550.0, truth)]

    summary = summarize(runs=runs, results=results, spec=spec)
    required = summary["interpolation_methods"][
        "bilinear_extinction_magnitude"
    ]
    assert required["evaluated_holdout_value_count"] == 1
    assert required["maximum_absolute_extinction_error_mag"] < 1e-14
    assert required["maximum_relative_transmission_error"] < 1e-14


def test_missing_training_corner_is_explicitly_excluded() -> None:
    spec = load_spec(SPEC_PATH)
    runs = []
    results = {}
    for altitude, pressure in (
        (0.0, 0.85),
        (0.0, 0.925),
        (500.0, 0.925),
    ):
        run_id = f"node_{altitude}_{pressure}"
        runs.append(
            {
                "run_id": run_id,
                "partition": "training",
                "profile": "us_standard",
                "observer_altitude_m": altitude,
                "pressure_ratio": pressure,
                "target_true_altitude_deg": 5.0,
            }
        )
        results[run_id] = [_result_from_extinction(550.0, 1.0)]
    runs.append(
        {
            "run_id": "excluded",
            "partition": "joint_holdout",
            "profile": "us_standard",
            "observer_altitude_m": 125.0,
            "pressure_ratio": 0.8688,
            "target_true_altitude_deg": 5.0,
        }
    )
    results["excluded"] = [_result_from_extinction(550.0, 1.0)]

    with pytest.raises(
        VisibilityAltitudePressureProbeError,
        match="no holdout values",
    ):
        summarize(runs=runs, results=results, spec=spec)


def test_spec_mutations_fail_closed() -> None:
    spec = copy.deepcopy(load_spec(SPEC_PATH))
    spec["runtime_boundary"]["engine_changes_authorized"] = True
    with pytest.raises(
        VisibilityAltitudePressureProbeError,
        match="runtime boundary",
    ):
        validate_spec(spec)

    spec = copy.deepcopy(load_spec(SPEC_PATH))
    spec["pressure_o4_closure"]["physical_override"] = "unscaled"
    with pytest.raises(
        VisibilityAltitudePressureProbeError,
        match="O4 closure",
    ):
        validate_spec(spec)


def test_failed_design_receipts_are_bound_without_relaxing_thresholds() -> None:
    spec = load_spec(SPEC_PATH)
    refinements = spec["refinement_from_failed_designs"]
    assert len(refinements) == 4
    for refinement in refinements:
        path = REPO_ROOT / refinement["receipt_path"]
        assert path.stat().st_size == refinement["receipt_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == refinement[
            "receipt_sha256"
        ]
        assert refinement["thresholds_relaxed"] is False
    assert spec["interpolation_admission"][
        "maximum_absolute_extinction_error_mag"
    ] == 0.025


def test_cross_platform_validator_accepts_roundoff_but_rejects_drift() -> None:
    expected = {
        "result": [
            {
                "extinction_magnitude": 0.010000000000001,
                "run_id": "case",
            }
        ]
    }
    one_ulp_different = copy.deepcopy(expected)
    one_ulp_different["result"][0]["extinction_magnitude"] = math.nextafter(
        expected["result"][0]["extinction_magnitude"],
        math.inf,
    )
    independent_assert_cross_platform_equal(
        one_ulp_different,
        expected,
        "result",
    )

    materially_different = copy.deepcopy(expected)
    materially_different["result"][0]["extinction_magnitude"] += 1e-9
    with pytest.raises(ValidationError, match="numeric value differs"):
        independent_assert_cross_platform_equal(
            materially_different,
            expected,
            "result",
        )


def test_validator_does_not_import_builder_implementation() -> None:
    tree = ast.parse(VALIDATOR_PATH.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any(
        name.endswith(
            "build_visibility_altitude_pressure_interpolation_probe"
        )
        for name in imported
    )
