from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest

from scripts.build_visibility_radiance_lut import (
    ARTIFACT_SCHEMA,
    CASE_SCHEMA,
    DIRECT_TRANSMISSION_CASE_FILES,
    MYSTIC_CASE_FILES,
    _completed_case,
    _parse_direct_transmission_output,
    canonical_json_bytes,
    expand_profile,
    file_receipt,
    inspect_spec,
    load_spec,
    render_direct_transmission_input,
    render_mystic_input,
    sha256_file,
    validate_case,
)
from scripts.validate_visibility_radiance_lut import (
    VisibilityLabError,
    _verify_case,
    validate_artifact,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT / "scripts" / "visibility_reference_lab" / "phase1_lab_spec.json"
)
CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase1_reference_lab_checkpoint_2026-07-29.json"
)


def test_phase1_lab_spec_forbids_a_full_cartesian_build() -> None:
    summary = inspect_spec(SPEC_PATH)

    assert summary == {
        "spec_id": "physical-heliacal-phase1-pilot-2026-07-29",
        "status": "research_pilot_not_runtime_data_pack",
        "convergence_case_count": 21,
        "geometry_smoke_case_count": 6,
        "direct_transmission_smoke_case_count": 13,
        "reserved_holdout_case_count": 2,
        "candidate_axis_product_before_spectral_grid": 653_184_000,
        "build_spectral_sample_count": 81,
        "prohibited_full_cartesian_case_count": 52_907_904_000,
        "sampling_law": (
            "adaptive_sparse_design_required_no_cartesian_product_authorized"
        ),
    }


def test_mystic_input_is_deterministic_explicit_and_path_neutral() -> None:
    spec = load_spec(SPEC_PATH)
    case = expand_profile(spec, "convergence")[0]

    first = render_mystic_input(case, spec)
    second = render_mystic_input(copy.deepcopy(case), spec)

    assert first == second
    assert "data_files_path libradtran_data\n" in first
    assert "mol_abs_param crs\n" in first
    assert "crs_model rayleigh Bodhaine\n" in first
    assert "crs_model O3 Molina\n" in first
    assert "mc_spherical 1D\n" in first
    assert "mc_randomseed 104729\n" in first
    assert "mc_vroom on\n" in first
    assert "mc_escape\n" in first
    assert "mc_seed" not in first
    assert "day_of_year" not in first
    assert "C:\\" not in first
    assert "/home/" not in first
    assert "aerosol_angstrom 1.3 0.0459696816675\n" in first


def test_direct_transmission_input_and_normalization_are_explicit(
    tmp_path: Path,
) -> None:
    spec = load_spec(SPEC_PATH)
    case = expand_profile(spec, "direct_transmission_smoke")[4]

    rendered = render_direct_transmission_input(case, spec)

    assert "sza 85\n" in rendered
    assert "rte_solver disort\n" in rendered
    assert "pseudospherical\n" in rendered
    assert "number_of_streams 16\n" in rendered
    assert "output_quantity transmittance\n" in rendered
    assert "output_user lambda edir\n" in rendered
    assert "mc_randomseed 49979687\n" in rendered
    assert "mc_spherical" not in rendered
    output_path = tmp_path / "stdout.txt"
    output_path.write_text("550.000 8.995140e-03\n", encoding="utf-8")
    result = _parse_direct_transmission_output(output_path, case)
    assert result["direct_spectral_transmission"] == pytest.approx(
        0.103207656964655,
    )
    assert result["extinction_magnitude"] == pytest.approx(2.46572020313491)


def test_direct_transmission_case_receipt_is_fully_bound(tmp_path: Path) -> None:
    spec = load_spec(SPEC_PATH)
    case = expand_profile(spec, "direct_transmission_smoke")[0]
    case_dir = tmp_path / case["case_id"]
    case_dir.mkdir()
    projection = math.sin(math.radians(case["target_true_altitude_deg"]))
    payloads = {
        "input.inp": render_direct_transmission_input(case, spec).encode(),
        "randomseed": f"{case['random_seed']}\n".encode(),
        "stderr.txt": b"",
        "stdout.txt": f"{case['wavelength_nm']:.3f} {0.5 * projection:.16g}\n".encode(),
        "syntax.stderr.txt": b"",
        "syntax.stdout.txt": b"",
    }
    assert payloads.keys() == DIRECT_TRANSMISSION_CASE_FILES
    for filename, payload in payloads.items():
        (case_dir / filename).write_bytes(payload)
    summary = _parse_direct_transmission_output(case_dir / "stdout.txt", case)
    result = {
        "schema": CASE_SCHEMA,
        "case": case,
        "result": summary,
        "files": [
            file_receipt(path, relative_to=case_dir)
            for path in sorted(case_dir.iterdir())
        ],
    }
    result_path = case_dir / "case-result.json"
    result_path.write_bytes(canonical_json_bytes(result))
    receipt = {
        "case_id": case["case_id"],
        "case_result": file_receipt(result_path, relative_to=tmp_path),
        "result": summary,
    }

    verified, bound_paths = _verify_case(tmp_path, receipt)

    assert verified == result
    assert bound_paths == {
        f"{case['case_id']}/{name}"
        for name in DIRECT_TRANSMISSION_CASE_FILES | {"case-result.json"}
    }


def test_target_at_exact_geometric_horizon_is_rejected() -> None:
    spec = load_spec(SPEC_PATH)
    case = expand_profile(spec, "convergence")[0]
    case["target_true_altitude_deg"] = 0.0

    with pytest.raises(VisibilityLabError, match="umu=0"):
        validate_case(case, spec)


def test_phase1_checkpoint_is_bound_to_current_tooling_and_remains_non_admitted() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))

    assert checkpoint["schema"] == "moira.visibility-reference-lab-checkpoint/v1"
    assert checkpoint["status"] == "research_checkpoint_not_runtime_data_pack"
    assert checkpoint["phase1_complete"] is False
    assert checkpoint["specification"]["sha256"] == sha256_file(SPEC_PATH)
    for role in ("builder", "validator"):
        receipt = checkpoint["tooling"][role]
        assert receipt["sha256"] == sha256_file(REPO_ROOT / receipt["path"])
    assert checkpoint["artifacts"]["convergence"]["case_count"] == 21
    assert checkpoint["artifacts"]["convergence"][
        "fixed_seed_repeat_byte_identical"
    ]
    assert checkpoint["artifacts"]["geometry_smoke"]["case_count"] == 6
    assert checkpoint["findings"]["fixed_photon_budget_admissible_for_production"] is (
        False
    )
    assert checkpoint["package_boundary_audit"][
        "forbidden_visibility_or_cie_or_libradtran_entry_count"
    ] == 0


def _case_file_payloads(case: dict, spec: dict) -> dict[str, bytes]:
    wavelength = float(case["wavelength_nm"])
    viewing_zenith = 90.0 + float(case["target_true_altitude_deg"])
    viewing_azimuth = float(case["relative_solar_azimuth_deg"])
    spectral_row = f"{wavelength:.5f} 0 0 0 1\n".encode()
    spectral_std_row = f"{wavelength:.5f} 0 0 0 0.1\n".encode()
    payloads = {
        "input.inp": render_mystic_input(case, spec).encode(),
        "mc.flx.spc": spectral_row,
        "mc.flx.std.spc": spectral_std_row,
        "mc.rad.spc": spectral_row,
        "mc.rad.std.spc": spectral_std_row,
        "mc0.rad": (
            f"0 0 {viewing_zenith:.8f} {viewing_azimuth:.8f} 0 0 0 1\n"
        ).encode(),
        "mc0.rad.std": b"0 0 95 360 0 0 0 0.1\n",
        "randomseed": f"{case['random_seed']}\n".encode(),
        "stderr.txt": b"",
        "stdout.txt": b"reference fixture\n",
        "syntax.stderr.txt": b"",
        "syntax.stdout.txt": b"",
    }
    assert payloads.keys() == MYSTIC_CASE_FILES
    return payloads


def _write_fake_geometry_artifact(root: Path) -> None:
    spec = load_spec(SPEC_PATH)
    case_receipts = []
    for case in expand_profile(spec, "geometry_smoke"):
        case_dir = root / case["case_id"]
        case_dir.mkdir(parents=True)
        for filename, payload in _case_file_payloads(case, spec).items():
            (case_dir / filename).write_bytes(payload)
        files = [
            file_receipt(path, relative_to=case_dir)
            for path in sorted(case_dir.iterdir())
        ]
        result = {
            "schema": CASE_SCHEMA,
            "case": case,
            "result": {
                "wavelength_nm": float(case["wavelength_nm"]),
                "viewing_zenith_deg": 90.0
                + float(case["target_true_altitude_deg"]),
                "viewing_azimuth_deg": float(
                    case["relative_solar_azimuth_deg"]
                ),
                "escape_spectral_radiance_mw_m2_nm_sr": 1.0,
                "reported_standard_deviation_mw_m2_nm_sr": 0.1,
                "reported_relative_standard_deviation": 0.1,
            },
            "files": files,
        }
        result_path = case_dir / "case-result.json"
        result_path.write_bytes(canonical_json_bytes(result))
        case_receipts.append(
            {
                "case_id": case["case_id"],
                "case_result": file_receipt(result_path, relative_to=root),
                "result": result["result"],
            }
        )

    source_paths = {spec["source_datasets"]["solar_spectrum"]}
    source_paths.update(spec["source_datasets"]["atmosphere_files"].values())
    manifest = {
        "schema": ARTIFACT_SCHEMA,
        "artifact_status": "phase1_reference_lab_evidence_not_runtime_data_pack",
        "tooling": {
            "builder": file_receipt(
                REPO_ROOT / "scripts" / "build_visibility_radiance_lut.py",
                relative_to=REPO_ROOT,
            ),
            "validator": file_receipt(
                REPO_ROOT / "scripts" / "validate_visibility_radiance_lut.py",
                relative_to=REPO_ROOT,
            ),
        },
        "spec": {
            "path": SPEC_PATH.name,
            "sha256": sha256_file(SPEC_PATH),
            "spec_id": spec["spec_id"],
        },
        "model_id": spec["model_id"],
        "composite_model_id": spec["composite_model_id"],
        "profile": "geometry_smoke",
        "generator": {
            "source_archive": {
                "path": "libRadtran-2.0.6.tar.gz",
                "bytes": spec["source"]["archive_bytes"],
                "sha256": spec["source"]["archive_sha256"],
            },
            "source_archive_expected_url": spec["source"]["archive_url"],
            "uvspec_version": "uvspec, version 2.0.6-MYSTIC",
            "uvspec_sha256": "a" * 64,
            "configure_options": (
                "CC=gcc CFLAGS=-O2 CXX=g++ CXXFLAGS=-O2 "
                "F77=gfortran FFLAGS=-O2"
            ),
            "build_capabilities": {
                "mystic": True,
                "mystic_3d": False,
                "gsl": True,
                "netcdf4": True,
                "vroom_exercised_by_cases": True,
            },
            "build_files": [
                {
                    "path": path,
                    "bytes": 1,
                    "sha256": "d" * 64,
                }
                for path in ("Makeconf", "config.log", "config.status")
            ],
            "source_datasets": [
                {
                    "path": path,
                    "bytes": 1,
                    "sha256": "b" * 64,
                }
                for path in sorted(source_paths)
            ],
            "source_data_trees": [
                {
                    "path": path,
                    "file_count": 1,
                    "bytes": 1,
                    "tree_sha256": "c" * 64,
                    "tree_hash_law": (
                        "sha256(relative_path_nul_bytes_nul_file_sha256_lf)"
                    ),
                    "excluded_names": ["._*", "Makefile", "Makefile.in"],
                }
                for path in sorted(spec["source_datasets"]["data_trees"].values())
            ],
        },
        "environment": {
            "platform": "test-platform",
            "python": "test-python",
            "tools": {
                "gcc": "test-gcc",
                "g++": "test-g++",
                "gfortran": "test-gfortran",
                "make": "test-make",
                "flex": "test-flex",
                "netcdf": "test-netcdf",
                "gsl": "test-gsl",
            },
        },
        "runtime_boundary": spec["runtime_boundary"],
        "case_count": len(case_receipts),
        "cases": case_receipts,
        "fixed_seed_repeat_check": None,
    }
    (root / "artifact-manifest.json").write_bytes(canonical_json_bytes(manifest))


def test_artifact_validator_binds_every_file_and_rejects_tampering(
    tmp_path: Path,
) -> None:
    _write_fake_geometry_artifact(tmp_path)

    valid = validate_artifact(tmp_path, spec_path=SPEC_PATH)

    assert valid["case_count"] == 6
    assert valid["all_files_bound"] is True
    assert valid["runtime_dependency"] is False
    assert valid["network_dependency"] is False

    input_path = tmp_path / "geometry_civil_near_sun" / "input.inp"
    input_path.write_text(
        input_path.read_text(encoding="utf-8") + "# tampered\n",
        encoding="utf-8",
    )
    with pytest.raises(VisibilityLabError, match="byte count mismatch"):
        validate_artifact(tmp_path, spec_path=SPEC_PATH)


def test_resume_rejects_an_unbound_case_file(tmp_path: Path) -> None:
    _write_fake_geometry_artifact(tmp_path)
    spec = load_spec(SPEC_PATH)
    case = expand_profile(spec, "geometry_smoke")[0]
    case_dir = tmp_path / case["case_id"]
    (case_dir / "unbound.txt").write_text("not receipted\n", encoding="utf-8")

    with pytest.raises(VisibilityLabError, match="unbound file"):
        _completed_case(case_dir, case)
