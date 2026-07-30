from __future__ import annotations

import ast
import hashlib
import math
from pathlib import Path

import pytest

from scripts.build_visibility_radiance_response_probe import (
    _decimal_direct_altitude_grid,
    _decimal_vertical_grid,
    _direct_run,
    _point_id,
    _shape_photon_count,
    _trapezoid_response,
    _trilinear_log,
    RunBuilder,
    canonical_json_bytes,
    inspect_spec,
    load_spec,
    radiance_points,
    render_input,
)
from scripts.validate_visibility_radiance_response_probe import (
    ValidationError,
)
from scripts.validate_visibility_radiance_response_probe import (
    _assert_input_equivalent as independent_assert_input_equivalent,
)
from scripts.validate_visibility_radiance_response_probe import (
    _assert_numeric_equal as independent_assert_numeric_equal,
)
from scripts.validate_visibility_radiance_response_probe import (
    _expected_input as independent_expected_input,
)
from scripts.validate_visibility_radiance_response_probe import (
    _direct_altitude_grid as independent_direct_altitude_grid,
)
from scripts.validate_visibility_radiance_response_probe import (
    _response_integral as independent_response_integral,
)
from scripts.validate_visibility_radiance_response_probe import (
    _trilinear as independent_trilinear,
)
from scripts.validate_visibility_radiance_response_probe import (
    _vertical_grid as independent_vertical_grid,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_radiance_response_probe_spec.json"
)
VALIDATOR_PATH = (
    REPO_ROOT
    / "scripts"
    / "validate_visibility_radiance_response_probe.py"
)


def test_spec_is_bounded_and_runtime_inert() -> None:
    inspected = inspect_spec(SPEC_PATH)
    assert inspected["spec_id"] == (
        "physical-heliacal-phase1-radiance-response-v9-2026-07-30"
    )
    assert inspected["training_point_count"] == 64
    assert inspected["monochromatic_holdout_point_count"] == 27
    assert inspected["response_holdout_point_count"] == 9
    assert inspected["direct_run_count"] == 113
    assert inspected["minimum_run_count"] == 605
    spec = load_spec(SPEC_PATH)
    monte_carlo = spec["adaptive_monte_carlo"]
    assert monte_carlo["anchor_maximum_seed_count"] == 16
    assert len(monte_carlo["training_random_seeds"]) == 16
    assert len(monte_carlo["holdout_random_seeds"]) == 16
    assert set(monte_carlo["training_random_seeds"]).isdisjoint(
        monte_carlo["holdout_random_seeds"]
    )
    assert monte_carlo["spectral_shape_maximum_seed_count"] == 8
    assert len(monte_carlo["spectral_shape_training_random_seeds"]) == 8
    assert len(monte_carlo["spectral_shape_holdout_random_seeds"]) == 8
    assert _shape_photon_count(-9.0, spec) == 100000
    assert _shape_photon_count(-7.5, spec) == 100000
    assert _shape_photon_count(-6.0, spec) == 30000
    assert _shape_photon_count(-4.5, spec) == 10000
    assert _shape_photon_count(0.0, spec) == 10000
    assert inspected["runtime_boundary"]["network_allowed"] is False
    assert (
        inspected["runtime_boundary"]["engine_runtime_invocation_allowed"]
        is False
    )
    assert (
        inspected["deep_twilight_law"][
            "solar_altitude_below_table"
        ]
        == "not_evaluable_for_modeled_twilight_background"
    )
    assert (
        inspected["deep_twilight_law"][
            "monte_carlo_non_detection_is_zero"
        ]
        is False
    )


def test_training_and_holdout_inventories_are_disjoint() -> None:
    spec = load_spec(SPEC_PATH)
    training, holdouts, response_holdouts = radiance_points(spec)
    assert len(training) == len(set(training)) == 64
    assert len(holdouts) == len(set(holdouts)) == 27
    assert len(response_holdouts) == len(set(response_holdouts)) == 9
    assert set(training).isdisjoint(holdouts)
    assert set(response_holdouts) < set(holdouts)
    assert len({_point_id(point) for point in training + holdouts}) == 91
    assert response_holdouts == [
        (-7.5, 2.0, 90.0),
        (-7.5, 10.0, 150.0),
        (-7.5, 30.0, 30.0),
        (-4.5, 2.0, 150.0),
        (-4.5, 10.0, 30.0),
        (-4.5, 30.0, 90.0),
        (-1.5, 2.0, 30.0),
        (-1.5, 10.0, 90.0),
        (-1.5, 30.0, 150.0),
    ]


def test_vertical_grid_is_independently_reconstructed() -> None:
    spec = load_spec(SPEC_PATH)
    builder = _decimal_vertical_grid(spec)
    validator = independent_vertical_grid(spec)
    assert builder == validator
    assert len(builder) == 290
    assert builder[0] == 0.0
    assert builder[-1] == 120.0


def test_direct_grid_is_dense_and_independently_reconstructed() -> None:
    spec = load_spec(SPEC_PATH)
    builder_nodes, builder_holdouts = _decimal_direct_altitude_grid(spec)
    validator_nodes, validator_holdouts = independent_direct_altitude_grid(
        spec
    )
    assert builder_nodes == validator_nodes
    assert builder_holdouts == validator_holdouts
    assert len(builder_nodes) == 57
    assert len(builder_holdouts) == 56
    assert builder_nodes[0] == 0.25
    assert builder_nodes[-1] == 45.0
    assert builder_holdouts == [
        (left + right) / 2
        for left, right in zip(builder_nodes, builder_nodes[1:])
    ]
    assert set(builder_nodes).isdisjoint(builder_holdouts)


def test_builder_and_validator_render_identical_inputs() -> None:
    spec = load_spec(SPEC_PATH)
    training, holdouts, _ = radiance_points(spec)
    anchor = {
        "run_id": "training__sample__anchor__r01",
        "kind": "anchor",
        "partition": "training",
        "point_id": "sample",
        "solar_center_altitude_deg": training[0][0],
        "target_true_altitude_deg": training[0][1],
        "relative_solar_azimuth_deg": training[0][2],
        "photon_count": 250000,
        "random_seed": 104729,
    }
    shape = {
        **anchor,
        "run_id": "holdout__sample__shape__r01",
        "kind": "shape",
        "partition": "holdout",
        "solar_center_altitude_deg": holdouts[0][0],
        "target_true_altitude_deg": holdouts[0][1],
        "relative_solar_azimuth_deg": holdouts[0][2],
        "photon_count": 30000,
        "random_seed": 1310731,
    }
    direct = _direct_run(0.5, partition="holdout")

    for run in (anchor, shape, direct):
        rendered = render_input(run, spec)
        assert rendered == independent_expected_input(run, spec)
        assert "mol_abs_param reptran fine" in rendered
        assert "atm_z_grid " in rendered
        assert "altitude " not in rendered
    assert "mc_spectral_is" not in render_input(anchor, spec)
    assert "wavelength 531 531" in render_input(anchor, spec)
    assert "mc_spectral_is 531" in render_input(shape, spec)
    assert "aerosol_modify ssa set 0" in render_input(direct, spec)


def test_response_quadrature_is_independently_reproduced() -> None:
    wavelengths = [500.0, 501.0, 502.0]
    radiances = [1.0, 2.0, 4.0]
    table = {500: 0.0, 501: 0.5, 502: 1.0}
    expected = 3.0
    assert _trapezoid_response(wavelengths, radiances, table) == expected
    assert (
        independent_response_integral(wavelengths, radiances, table)
        == expected
    )


def test_log_trilinear_interpolation_is_exact_for_separable_field() -> None:
    axes = ([0.0, 2.0], [1.0, 5.0], [0.0, 180.0])
    table = {
        (solar, target, azimuth): 10.0
        ** (0.2 * solar + 0.03 * target - 0.001 * azimuth)
        for solar in axes[0]
        for target in axes[1]
        for azimuth in axes[2]
    }
    point = (0.75, 2.5, 45.0)
    expected = 10.0 ** (
        0.2 * point[0] + 0.03 * point[1] - 0.001 * point[2]
    )
    assert math.isclose(
        _trilinear_log(table, axes, point),
        expected,
        rel_tol=1e-14,
    )
    assert math.isclose(
        independent_trilinear(table, axes, point),
        expected,
        rel_tol=1e-14,
    )


def test_cross_platform_comparison_accepts_roundoff_but_not_drift() -> None:
    expected = {"value": [0.712521194033361]}
    rounded = {"value": [0.71252119403336]}
    independent_assert_numeric_equal(rounded, expected, "payload")

    with pytest.raises(ValidationError, match="numeric value differs"):
        independent_assert_numeric_equal(
            {"value": [0.712522194033361]},
            expected,
            "payload",
        )


def test_input_comparison_allows_only_cross_platform_umu_roundoff() -> None:
    expected = "pressure 1013.25\numu -0.707106781186548\nquiet\n"
    independent_assert_input_equivalent(
        b"pressure 1013.25\numu -0.707106781186547\nquiet\n",
        expected,
        "fixture",
    )
    with pytest.raises(ValidationError, match="run input differs"):
        independent_assert_input_equivalent(
            b"pressure 1013.2\numu -0.707106781186547\nquiet\n",
            expected,
            "fixture",
        )
    with pytest.raises(ValidationError, match="run input differs"):
        independent_assert_input_equivalent(
            b"pressure 1013.25\numu -0.70710678118\nquiet\n",
            expected,
            "fixture",
        )


def test_run_cache_reuse_is_byte_verified(tmp_path: Path) -> None:
    spec = load_spec(SPEC_PATH)
    declaration = _direct_run(0.5, partition="holdout")
    source_runs = tmp_path / "source" / "runs"
    source_run = source_runs / declaration["run_id"]
    source_run.mkdir(parents=True)
    kept = {
        "input.inp",
        "stdout.txt",
        "stderr.txt",
        "syntax.stdout.txt",
        "syntax.stderr.txt",
    }
    for name in kept:
        content = (
            render_input(declaration, spec).encode()
            if name == "input.inp"
            else f"{name}\n".encode()
        )
        (source_run / name).write_bytes(content)
    receipts = [
        {
            "path": name,
            "bytes": (source_run / name).stat().st_size,
            "sha256": hashlib.sha256(
                (source_run / name).read_bytes()
            ).hexdigest(),
        }
        for name in sorted(kept)
    ]
    payload = {
        "schema": "moira.visibility-radiance-response-run/v1",
        "run": declaration,
        "result": {"fixture": True},
        "files": receipts,
    }
    (source_run / "result.json").write_bytes(
        canonical_json_bytes(payload)
    )
    output = tmp_path / "output"
    output.mkdir()
    builder = RunBuilder(
        uvspec=tmp_path / "unused-uvspec",
        data_root=tmp_path / "unused-data",
        output_root=output,
        spec=spec,
        cie_tables={},
        max_new_runs=0,
        reuse_runs_root=source_runs,
    )
    assert builder.run(declaration) == payload
    assert builder.reused_run_count == 1
    assert builder.new_run_count == 0
    copied = output / "runs" / declaration["run_id"]
    assert {
        path.name: path.read_bytes() for path in copied.iterdir()
    } == {
        path.name: path.read_bytes() for path in source_run.iterdir()
    }


def test_validator_does_not_import_builder_implementation() -> None:
    tree = ast.parse(VALIDATOR_PATH.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any(
        name.endswith("build_visibility_radiance_response_probe")
        for name in imported
    )
