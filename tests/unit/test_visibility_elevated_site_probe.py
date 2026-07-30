from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path

import pytest

from scripts.build_visibility_elevated_site_probe import (
    VisibilityLabError,
    _parse_atmosphere_profile,
    _resume_case,
    base_lab,
    construct_truncated_atmosphere,
    construct_truncated_o4_profile,
    expand_direct_cases,
    expand_mystic_cases,
    inspect_spec,
    load_spec,
    render_direct_input,
    render_mystic_input,
)
from scripts.validate_visibility_elevated_site_probe import (
    ValidationError,
    _validate_file_receipt,
    _verify_byte_identity,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase1_elevated_site_probe_spec.json"
)
CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase1_elevated_site_checkpoint_2026-07-29.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _float32(value: float) -> float:
    return struct.unpack("!f", struct.pack("!f", float(value)))[0]


def _synthetic_atmosphere() -> str:
    return """\
# z p T air O3 O2 H2O CO2 NO2
3 700 270 1e19 1e13 2e18 1e16 4e15 1e10
1 900 280 2e19 2e13 4e18 2e16 8e15 2e10
0 1000 290 3e19 3e13 6e18 3e16 1.2e16 3e10
"""


def test_probe_spec_is_bounded_and_preserves_checkpoint_one_identity() -> None:
    summary = inspect_spec(SPEC_PATH)

    assert summary == {
        "spec_id": "physical-heliacal-phase1-elevated-site-probe-2026-07-29",
        "status": "research_probe_not_runtime_data_pack",
        "site_profile_count": 5,
        "direct_comparison_case_count": 45,
        "direct_uvspec_run_count": 90,
        "mystic_case_count": 7,
        "total_uvspec_run_count": 97,
        "checkpoint1_identity_preserved": True,
        "runtime_data_pack_authorized": False,
    }

    spec = load_spec(SPEC_PATH)
    for role in ("spec", "builder", "validator"):
        declaration = spec["base_lab"][f"{role}_path"]
        path = REPO_ROOT / declaration
        assert path.stat().st_size == spec["base_lab"][f"{role}_bytes"]
        assert _sha256(path) == spec["base_lab"][f"{role}_sha256"]


def test_truncated_atmosphere_uses_source_interpolation_law() -> None:
    payload, metadata = construct_truncated_atmosphere(
        _synthetic_atmosphere(),
        1500.0,
    )
    rows = _parse_atmosphere_profile(payload.decode("utf-8"))
    bottom = rows[-1]

    expected_pressure = _float32(
        math.exp(math.log(_float32(900.0)) + 0.25 * (
            math.log(_float32(700.0)) - math.log(_float32(900.0))
        ))
    )
    expected_air = _float32(
        math.exp(math.log(_float32(2e19)) + 0.25 * (
            math.log(_float32(1e19)) - math.log(_float32(2e19))
        ))
    )

    assert len(rows) == 2
    assert bottom[0] == 1.5
    assert bottom[1] == expected_pressure
    assert bottom[2] == _float32(277.5)
    assert bottom[3] == expected_air
    assert bottom[4] == pytest.approx(_float32(1e-6 * expected_air), rel=2e-7)
    assert bottom[5] == pytest.approx(_float32(0.2 * expected_air), rel=2e-7)
    assert metadata["interpolated_bottom_level"] is True
    assert metadata["bracketing_altitude_km"] == [1.0, 3.0]
    assert metadata["level_count"] == 2


def test_exact_source_level_is_copied_without_interpolation() -> None:
    source = _synthetic_atmosphere()
    payload, metadata = construct_truncated_atmosphere(source, 1000.0)
    rows = _parse_atmosphere_profile(payload.decode("utf-8"))
    source_rows = _parse_atmosphere_profile(source)

    assert rows == source_rows[:2]
    assert metadata["interpolated_bottom_level"] is False
    assert metadata["bracketing_altitude_km"] == [1.0, 1.0]


def test_o4_companion_preserves_preinterpolation_derived_profile() -> None:
    payload, metadata = construct_truncated_o4_profile(
        _synthetic_atmosphere(),
        1500.0,
    )
    rows = [
        [float(field) for field in line.split()]
        for line in payload.decode("utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    expected_air = _float32(
        math.exp(math.log(_float32(2e19)) + 0.25 * (
            math.log(_float32(1e19)) - math.log(_float32(2e19))
        ))
    )
    low_o4 = _float32((_float32(4e18) * 1e-23) ** 2)
    high_o4 = _float32((_float32(2e18) * 1e-23) ** 2)
    low_mix = _float32(low_o4 / _float32(2e19))
    high_mix = _float32(high_o4 / _float32(1e19))
    interpolated_mix = _float32(low_mix + 0.25 * (high_mix - low_mix))
    expected_o4 = _float32(interpolated_mix * expected_air)

    assert len(rows) == 2
    assert rows[-1][0] == 1.5
    assert _float32(rows[-1][1]) == expected_o4
    assert metadata["bottom_scaled_o4_density_cm-3"] == expected_o4
    assert rows[-1][1] != _float32(
        (_float32(0.2 * expected_air) * 1e-23) ** 2
    )


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("3 700 270 1e19 1e13 2e18 1e16 4e15\n", "nine columns"),
        (
            "1 900 280 2e19 2e13 4e18 2e16 8e15 2e10\n"
            "3 700 270 1e19 1e13 2e18 1e16 4e15 1e10\n",
            "strictly descending",
        ),
        (
            "3 700 270 1e19 1e13 2e18 1e16 4e15 1e10\n"
            "0 0 290 3e19 3e13 6e18 3e16 1.2e16 3e10\n",
            "must remain positive",
        ),
    ],
)
def test_malformed_source_profiles_fail_closed(source: str, message: str) -> None:
    with pytest.raises(VisibilityLabError, match=message):
        _parse_atmosphere_profile(source)


def test_site_outside_source_profile_fails_closed() -> None:
    with pytest.raises(VisibilityLabError, match="outside"):
        construct_truncated_atmosphere(_synthetic_atmosphere(), 5000.0)


def test_direct_oracle_and_cut_profile_inputs_are_distinct_and_explicit() -> None:
    spec = load_spec(SPEC_PATH)
    base_spec = base_lab.load_spec(REPO_ROOT / spec["base_lab"]["spec_path"])
    case = next(
        item
        for item in expand_direct_cases(spec)
        if item["site_altitude_m"] == 1500.0
        and item["target_true_altitude_deg"] == 5.0
        and item["wavelength_nm"] == 550.0
    )

    oracle = render_direct_input(
        case,
        spec,
        base_spec,
        method="altitude_option",
    )
    truncated = render_direct_input(
        case,
        spec,
        base_spec,
        method="truncated_profile",
    )

    assert "atmosphere_file libradtran_data/atmmod/afglus.dat\n" in oracle
    assert "altitude 1.5\n" in oracle
    assert "atmosphere_file atmosphere.dat\n" in truncated
    assert "mol_file O4 o4.dat cm_3\n" in truncated
    assert not any(line.startswith("altitude ") for line in truncated.splitlines())
    assert "mc_elevation_file" not in truncated
    for rendered in (oracle, truncated):
        assert "rte_solver disort\n" in rendered
        assert "pseudospherical\n" in rendered
        assert "number_of_streams 16\n" in rendered
        assert "zout 0\n" in rendered


def test_spherical_mystic_uses_only_a_cut_atmosphere_for_elevation() -> None:
    spec = load_spec(SPEC_PATH)
    base_spec = base_lab.load_spec(REPO_ROOT / spec["base_lab"]["spec_path"])
    case = next(
        item
        for item in expand_mystic_cases(spec)
        if item["site_altitude_m"] == 3000.0
        and item["profile_method"] == "truncated_profile"
    )

    rendered = render_mystic_input(case, spec, base_spec)

    assert "atmosphere_file atmosphere.dat\n" in rendered
    assert "mol_file O4 o4.dat cm_3\n" in rendered
    assert "rte_solver mystic\n" in rendered
    assert "mc_spherical 1D\n" in rendered
    assert "mc_randomseed 32452843\n" in rendered
    assert not any(line.startswith("altitude ") for line in rendered.splitlines())
    assert "mc_elevation_file" not in rendered


def test_independent_receipt_validator_rejects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "evidence.txt"
    path.write_bytes(b"bound evidence\n")
    receipt = {
        "path": "evidence.txt",
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }

    assert _validate_file_receipt(tmp_path, receipt, label="test") == "evidence.txt"
    path.write_bytes(b"tampered evidence\n")
    with pytest.raises(ValidationError, match="receipt mismatch"):
        _validate_file_receipt(tmp_path, receipt, label="test")


def test_case_resume_rejects_a_stale_generation_identity(
    tmp_path: Path,
) -> None:
    case = {"case_id": "bound-case"}
    case_dir = tmp_path / case["case_id"]
    case_dir.mkdir()
    (case_dir / "case-result.json").write_text(
        json.dumps(
            {
                "schema": "moira.visibility-elevated-site-probe-case/v1",
                "case": case,
                "generation_identity": {"builder": "old"},
                "files": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(VisibilityLabError, match="generation identity"):
        _resume_case(
            case_dir,
            case,
            {"builder": "current"},
        )


def test_independent_repeat_validator_rejects_nonidentical_science(
    tmp_path: Path,
) -> None:
    original = tmp_path / "original" / "mystic"
    comparison = tmp_path / "comparison" / "mystic"
    original.mkdir(parents=True)
    comparison.mkdir(parents=True)
    scientific_files = (
        "mc.flx.spc",
        "mc.flx.std.spc",
        "mc.rad.spc",
        "mc.rad.std.spc",
        "mc0.rad",
        "mc0.rad.std",
        "randomseed",
    )
    for filename in scientific_files:
        (original / filename).write_bytes(b"same\n")
        (comparison / filename).write_bytes(b"same\n")
    receipt = {
        "original_case_id": "original",
        "comparison_case_id": "comparison",
        "byte_identical_files": list(scientific_files),
    }
    _verify_byte_identity(
        tmp_path,
        receipt,
        expected_original="original",
        expected_comparison="comparison",
        label="repeat",
    )

    (comparison / "mc0.rad").write_bytes(b"different\n")
    with pytest.raises(ValidationError, match="not byte-identical"):
        _verify_byte_identity(
            tmp_path,
            receipt,
            expected_original="original",
            expected_comparison="comparison",
            label="repeat",
        )


def test_spec_runtime_boundary_remains_research_only() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

    assert spec["status"] == "research_probe_not_runtime_data_pack"
    assert spec["runtime_boundary"] == {
        "network_allowed": False,
        "automatic_download_allowed": False,
        "engine_dependency_allowed": False,
        "engine_runtime_invocation_allowed": False,
        "generated_numerical_products_only": True,
    }
    assert (
        spec["atmosphere_construction"]["pressure_policy"]
        == "named_profile_derived_no_explicit_override_in_probe"
    )


def test_elevated_site_checkpoint_is_bound_and_not_runtime_admission() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))

    assert checkpoint["schema"] == "moira.visibility-elevated-site-checkpoint/v1"
    assert checkpoint["status"] == "research_checkpoint_not_runtime_data_pack"
    assert checkpoint["phase1_complete"] is False
    assert checkpoint["elevated_site_construction_gate"] == (
        "passed_for_named_profile_derived_pressure"
    )
    assert checkpoint["specification"]["sha256"] == _sha256(SPEC_PATH)
    for role in ("builder", "validator"):
        receipt = checkpoint["tooling"][role]
        path = REPO_ROOT / receipt["path"]
        assert receipt["bytes"] == path.stat().st_size
        assert receipt["sha256"] == _sha256(path)
    assert checkpoint["external_artifact"]["manifest_sha256"] == (
        "823ac54a3a6a52a5ab709bffb80693ffc945f800c6957f9024053c52289557ff"
    )
    assert checkpoint["direct_oracle"]["maximum_absolute_differences"] == {
        "normalized_direct_irradiance_edir_over_e0": 0.0,
        "direct_spectral_transmission": 0.0,
        "extinction_magnitude": 0.0,
    }
    assert checkpoint["diagnostic_closed"]["tolerance_relaxed"] is False
    assert checkpoint["findings"]["explicit_pressure_override_validated"] is False
    assert checkpoint["findings"]["elevated_site_runtime_table_admitted"] is False
    assert checkpoint["findings"]["phase2_authorized"] is False
