from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_visibility_environment_contract_probe import (
    VisibilityEnvironmentProbeError,
    expand_runs,
    inspect_spec,
    load_spec,
    parse_output,
    render_input,
    validate_spec,
)
from scripts.validate_visibility_environment_contract_probe import (
    expected_input as independent_expected_input,
)
from scripts.validate_visibility_environment_contract_probe import (
    expected_runs as independent_expected_runs,
)
from scripts.validate_visibility_environment_contract_probe import (
    parse_output as independent_parse_output,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_environment_contract_probe_spec.json"
)
CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase1_environment_contract_checkpoint_2026-07-30.json"
)
VALIDATOR_PATH = (
    REPO_ROOT / "scripts" / "validate_visibility_environment_contract_probe.py"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_environment_probe_spec_is_bounded_and_complete() -> None:
    assert inspect_spec(SPEC_PATH) == {
        "spec_id": (
            "physical-heliacal-phase1-environment-contract-probe-2026-07-30"
        ),
        "status": "research_probe_not_runtime_data_pack",
        "run_count": 73,
        "run_kind_counts": {
            "albedo_direct_invariance": 7,
            "angstrom_sweep": 18,
            "aod_sweep": 24,
            "exact_repeat": 1,
            "named_aerosol_direct_invariance": 8,
            "ozone_sweep": 6,
            "pressure_sweep": 5,
            "raw_delta_m_haze_diagnostic": 4,
        },
        "named_aerosol_profile_count": 8,
        "pressure_coordinate": (
            "ratio_to_named_profile_surface_pressure_at_observer_altitude"
        ),
        "temperature_override_admitted": False,
        "relative_humidity_override_admitted": False,
        "production_data_pack_authorized": False,
        "engine_changes_authorized": False,
    }


def test_checkpoint_four_predecessor_receipts_are_exact() -> None:
    spec = load_spec(SPEC_PATH)
    predecessor = spec["predecessor"]
    for role in ("spec", "builder", "validator", "checkpoint"):
        path = REPO_ROOT / predecessor[f"{role}_path"]
        assert path.stat().st_size == predecessor[f"{role}_bytes"]
        assert _sha256(path) == predecessor[f"{role}_sha256"]


def test_all_eight_shettle_haze_season_combinations_are_named() -> None:
    profiles = load_spec(SPEC_PATH)["environment_contract"]["aerosol"][
        "named_profiles"
    ]
    assert profiles == {
        "rural_summer": {"haze": 1, "season": 1},
        "rural_winter": {"haze": 1, "season": 2},
        "maritime_summer": {"haze": 4, "season": 1},
        "maritime_winter": {"haze": 4, "season": 2},
        "urban_summer": {"haze": 5, "season": 1},
        "urban_winter": {"haze": 5, "season": 2},
        "tropospheric_summer": {"haze": 6, "season": 1},
        "tropospheric_winter": {"haze": 6, "season": 2},
    }


def test_environment_roles_do_not_create_false_independent_dimensions() -> None:
    contract = load_spec(SPEC_PATH)["environment_contract"]
    pressure = contract["surface_pressure"]
    assert pressure["table_coordinate"] == (
        "ratio_to_named_profile_surface_pressure_at_observer_altitude"
    )
    assert pressure["admission_law"] == (
        "absolute_and_ratio_bounds_must_both_pass"
    )
    assert pressure["absolute_hard_bounds_hpa"] == [500.0, 1100.0]
    assert pressure["ratio_hard_bounds"] == [0.85, 1.08]

    molecular = contract["molecular_atmosphere"]
    assert molecular["temperature_policy"].startswith("profile_derived")
    assert molecular["water_vapor_and_relative_humidity_policy"].startswith(
        "profile_derived"
    )

    aerosol = contract["aerosol"]
    assert aerosol["visibility_input_policy"] == (
        "not_exposed_because_aod550_is_authoritative"
    )
    assert aerosol["direct_table_dimensions"] == [
        "season",
        "aod550",
        "angstrom_exponent",
    ]
    assert "haze" in aerosol["radiance_table_dimensions"]
    assert contract["ground_albedo"]["direct_table_role"] == "excluded"
    assert contract["ground_albedo"]["radiance_table_role"] == "included"


def test_builder_and_independent_validator_expand_identical_runs() -> None:
    spec = load_spec(SPEC_PATH)
    builder = expand_runs(spec)
    validator = independent_expected_runs(spec)
    assert builder == validator
    assert len(builder) == 73
    assert len({run["run_id"] for run in builder}) == 73
    assert next(run for run in builder if run["kind"] == "exact_repeat")[
        "repeat_of"
    ] == "aod_alt_20p00_aod_0p100"


def test_builder_and_independent_validator_render_every_input_identically() -> None:
    spec = load_spec(SPEC_PATH)
    for run in expand_runs(spec):
        assert render_input(run, spec) == independent_expected_input(run, spec)


def test_admitted_direct_oracle_removes_aerosol_delta_m_phase_term() -> None:
    spec = load_spec(SPEC_PATH)
    runs = expand_runs(spec)
    admitted = next(
        run for run in runs if run["kind"] == "named_aerosol_direct_invariance"
    )
    diagnostic = next(
        run for run in runs if run["kind"] == "raw_delta_m_haze_diagnostic"
    )
    admitted_input = render_input(admitted, spec)
    diagnostic_input = render_input(diagnostic, spec)

    assert "aerosol_modify ssa set 0\n" in admitted_input
    assert "deltam off\n" in admitted_input
    assert "aerosol_modify ssa set 0\n" not in diagnostic_input
    assert "deltam on\n" in diagnostic_input
    assert "aerosol_visibility" not in admitted_input


def test_angstrom_beta_is_bound_to_aod550_at_550_nm() -> None:
    spec = load_spec(SPEC_PATH)
    run = next(
        run
        for run in expand_runs(spec)
        if run["kind"] == "angstrom_sweep"
        and run["angstrom_exponent"] == 2.5
        and run["wavelength_nm"] == 550.0
    )
    expected_beta = run["aod550"] * (0.55 ** run["angstrom_exponent"])
    assert (
        f"aerosol_angstrom 2.5 {format(expected_beta, '.15g')}\n"
        in render_input(run, spec)
    )


def test_output_derivations_are_independently_reconstructed() -> None:
    spec = load_spec(SPEC_PATH)
    run = next(
        run
        for run in expand_runs(spec)
        if run["run_id"] == "aerosol_maritime_winter"
    )
    text = "  550.000  1.792000e-01 \n"
    assert parse_output(text, run, spec) == independent_parse_output(
        text,
        run,
        spec,
    )
    assert parse_output(text, run, spec)["extinction_magnitude"] == (
        0.701784198298527
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
        name.endswith("build_visibility_environment_contract_probe")
        for name in imported
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda spec: spec["runtime_boundary"].__setitem__(
                "engine_changes_authorized",
                True,
            ),
            "runtime boundary",
        ),
        (
            lambda spec: spec["environment_contract"]["aerosol"][
                "named_profiles"
            ].pop("urban_summer"),
            "named aerosol inventory",
        ),
        (
            lambda spec: spec["environment_contract"]["surface_pressure"].__setitem__(
                "ratio_hard_bounds",
                [0.5, 2.0],
            ),
            "pressure admission law",
        ),
        (
            lambda spec: spec["direct_extinction_oracle"].__setitem__(
                "aerosol_scattering_override",
                None,
            ),
            "direct extinction oracle",
        ),
    ],
)
def test_spec_mutations_fail_closed(mutation: object, message: str) -> None:
    spec = copy.deepcopy(load_spec(SPEC_PATH))
    mutation(spec)
    with pytest.raises(VisibilityEnvironmentProbeError, match=message):
        validate_spec(spec)


def test_compact_checkpoint_binds_final_artifact_and_tooling() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    assert checkpoint["schema"] == (
        "moira.visibility-environment-contract-checkpoint/v1"
    )
    assert checkpoint["status"] == (
        "phase1_environment_contract_gate_passed_not_runtime_data_pack"
    )
    assert checkpoint["artifact"]["run_count"] == 73
    for role, path in (
        ("spec", SPEC_PATH),
        (
            "builder",
            REPO_ROOT / "scripts" / "build_visibility_environment_contract_probe.py",
        ),
        ("validator", VALIDATOR_PATH),
    ):
        assert checkpoint["tooling"][role] == {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
    assert checkpoint["decisions"]["production_data_pack_authorized"] is False
    assert checkpoint["decisions"]["engine_changes_authorized"] is False
