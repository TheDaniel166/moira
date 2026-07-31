from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_visibility_phase4_jones_source import (
    EXPECTED_ARCHIVE_BYTES,
    EXPECTED_ARCHIVE_SHA256,
    JonesSourceAuditError,
    _parse_fits_scalar,
    audit_archive,
    inspect_spec,
    load_spec,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / "scripts"
    / "visibility_reference_lab"
    / "phase4_jones_source_audit_spec.json"
)
CHECKPOINT_PATH = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "visibility_reference_lab"
    / "phase4_jones_source_audit_checkpoint_2026-07-31.json"
)


def test_fits_string_parser_preserves_slashes_and_escaped_quotes() -> None:
    assert _parse_fits_scalar(
        "'ph/s/m2/micron/arcsec2' / physical unit"
    ) == "ph/s/m2/micron/arcsec2"
    assert _parse_fits_scalar("'Jones'' model'") == "Jones' model"


def test_jones_source_audit_spec_is_bounded_and_nonruntime() -> None:
    assert inspect_spec(SPEC_PATH) == {
        "spec_id": (
            "physical-heliacal-phase4-jones-source-audit-2026-07-31"
        ),
        "status": "source_audit_and_artifact_contract_not_runtime_model",
        "candidate_model_id": (
            "jones_paranal_scattered_moonlight_2013_v1"
        ),
        "admission_status": "not_admitted",
        "required_source_member_count": 17,
        "first_admission_site_id": "cerro_paranal_jones_2013",
        "first_admission_phase_domain_deg": [1.55, 97.0],
        "source_fixture_inside_admission_domain": False,
        "artifact_status": "required_not_yet_generated",
        "atmospheric_sensitivity_available": False,
        "runtime_dependency": False,
    }


def test_committed_checkpoint_binds_auditor_spec_and_source_receipts() -> None:
    checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    spec = load_spec(SPEC_PATH)
    assert checkpoint["status"] == (
        "source_audit_complete_runtime_model_not_admitted"
    )
    assert checkpoint["admission_decision"]["admitted"] is False
    assert checkpoint["runtime_dependency"] is False
    assert checkpoint["network_dependency"] is False
    assert checkpoint["external_source_bytes_redistributed"] is False
    assert checkpoint["required_members"] == spec["eso_source_package"][
        "required_members"
    ]
    assert checkpoint["archive"] == {
        "url": spec["eso_source_package"]["url"],
        "release": spec["eso_source_package"]["release"],
        "bytes": spec["eso_source_package"]["archive_bytes"],
        "sha256": spec["eso_source_package"]["archive_sha256"],
        "license": spec["eso_source_package"]["license"],
    }
    source_fixture = checkpoint["source_owned_regression_fixture"]
    expected_fixture = spec["source_owned_regression_fixture"]
    assert source_fixture["derived_lunar_phase_angle_deg"] == (
        expected_fixture["derived_lunar_phase_angle_deg"]
    )
    assert source_fixture["inside_first_admission_domain"] is False
    assert source_fixture["fits_row_count"] == expected_fixture[
        "fits_row_count"
    ]
    assert source_fixture["fits_row_bytes"] == expected_fixture[
        "fits_row_bytes"
    ]
    assert source_fixture["optical_signature_row_count"] == (
        expected_fixture["optical_signature_row_count"]
    )
    assert source_fixture["optical_signature_sha256"] == (
        expected_fixture["optical_signature_sha256"]
    )
    operational = checkpoint["operational_comparison_capture"]
    expected_operational = spec["operational_comparison_capture"]
    for checkpoint_key, spec_key in (
        ("bytes", "fits_bytes"),
        ("sha256", "fits_sha256"),
        ("skycalc_version", "skycalc_version"),
        ("capture_date", "capture_date"),
        (
            "derived_lunar_phase_angle_deg",
            "derived_lunar_phase_angle_deg",
        ),
        ("row_count", "row_count"),
        ("component_signature_sha256", "component_signature_sha256"),
        ("role", "role"),
    ):
        assert operational[checkpoint_key] == expected_operational[spec_key]
    assert operational["component_isolated"] is True

    for receipt_name in ("auditor", "spec"):
        receipt = checkpoint[receipt_name]
        payload = (REPO_ROOT / receipt["path"]).read_bytes()
        assert receipt["bytes"] == len(payload)
        assert receipt["sha256"] == hashlib.sha256(payload).hexdigest()


def test_official_archive_and_governing_members_are_checksum_locked() -> None:
    spec = load_spec(SPEC_PATH)
    package = spec["eso_source_package"]
    assert package["archive_bytes"] == EXPECTED_ARCHIVE_BYTES
    assert package["archive_sha256"] == EXPECTED_ARCHIVE_SHA256
    assert package["license"] == "GPL-2.0-or-later"
    assert package["role"] == (
        "external_lineage_inspection_and_source_owned_regression_only"
    )
    receipts = {
        item["path"]: item["sha256"]
        for item in package["required_members"]
    }
    assert receipts["SM-01/sm-01_mod2/src/sm_scatmoonlight.c"] == (
        "686dcce3e4aadf41785b9b26bdeeee858"
        "c730030969c7dd4045748527985a5ea"
    )
    assert receipts["SM-01/sm-01_mod2/src/sm_skyemcomp.c"] == (
        "eaa20b583c24f81cf15f7f63ac561240"
        "3fbfb939cbe933f43df24bb56573adc6"
    )
    assert receipts["SM-01/sm-01_mod2/data/moonalbedo.dat"] == (
        "86b9f9860fabb283de6659aabee895918"
        "6dc03e9d081aaa7c2761c2869ff16cc"
    )


def test_source_owned_regression_is_not_an_admission_golden() -> None:
    spec = load_spec(SPEC_PATH)
    fixture = spec["source_owned_regression_fixture"]
    phase_angle = abs(
        180.0 - fixture["expected_parameters"]["alpha"]
    )
    assert phase_angle == pytest.approx(102.1, abs=1e-12)
    assert phase_angle > spec["first_admission_domain"][
        "lunar_phase_angle_deg"
    ][1]
    assert fixture["inside_first_moira_admission_domain"] is False
    assert fixture["regression_role"] == (
        "official_implementation_lineage_only_not_admission_golden"
    )


def test_first_admission_rejects_rolo_and_site_extrapolation() -> None:
    domain = load_spec(SPEC_PATH)["first_admission_domain"]
    assert domain["site_id"] == "cerro_paranal_jones_2013"
    assert domain["site_transfer_allowed"] is False
    assert domain["phase_extrapolation_policy"] == "rejected"
    assert domain["site_substitution_policy"] == "rejected"
    assert domain["subhorizon_moon_policy"] == (
        "not_evaluable_until_separately_admitted"
    )
    assert domain["outside_domain_policy"] == "not_evaluable"


def test_independent_artifact_contract_exposes_every_geometry_axis() -> None:
    contract = load_spec(SPEC_PATH)["independent_artifact_contract"]
    assert set(contract["required_coordinate_axes"]) == {
        "target_true_altitude_deg",
        "moon_true_altitude_deg",
        "relative_moon_azimuth_deg",
        "lunar_phase_angle_deg",
        "waxing_state",
        "moon_earth_distance_ratio",
    }
    assert contract["external_generator"] == {
        "name": "libRadtran",
        "version": "2.0.6",
        "solver": "MYSTIC",
        "geometry": "spherical_one_dimensional_atmosphere",
        "archive_sha256": (
            "64930cc40b6e4a37aa220520974d330fc"
            "1563796f466a649b2238131f2d69840"
        ),
        "runtime_dependency": False,
    }
    assert contract["official_eso_code_used_as_generator"] is False
    assert contract["official_eso_code_used_as_independent_oracle"] is False
    assert contract["acceptance_thresholds_status"] == (
        "pilot_results_required_before_freeze"
    )
    assert contract["production_admission_allowed"] is False


def test_atmospheric_sensitivity_requires_distinct_scenario_packs() -> None:
    contract = load_spec(SPEC_PATH)["atmospheric_sensitivity_contract"]
    assert contract["current_runtime_pack_atmosphere_axes"] == []
    assert (
        contract[
            "current_pack_can_produce_atmospheric_sensitivity_envelope"
        ]
        is False
    )
    assert contract["required_method"] == (
        "separate_immutable_admitted_scenario_packs"
    )
    assert contract["scenario_event_evaluation"] == (
        "rerun_complete_event_search_per_pack"
    )
    assert contract["missing_or_noncomparable_scenario_policy"] == (
        "typed_not_bounded"
    )
    assert contract["interpolation_between_scenario_packs_allowed"] is False
    assert contract["probabilistic_confidence_claimed"] is False


def test_operational_capture_is_comparison_only_and_component_isolated() -> None:
    capture = load_spec(SPEC_PATH)["operational_comparison_capture"]
    assert capture["skycalc_version"] == "2.0.9"
    assert capture["derived_lunar_phase_angle_deg"] == 50.0
    assert capture["component_column"] == "flux_sml"
    assert capture["component_signature_sha256"] == (
        "8e15e62b5aa5cab32961f3be7ba300f4"
        "6217d20614e91bdc131aa8ee8b2e1c29"
    )
    assert capture["all_other_emission_components_zero"] is True
    assert capture["total_flux_equals_scattered_moonlight"] is True
    assert capture["role"] == (
        "versioned_source_owned_operational_comparison_not_independent_oracle"
    )


def test_validator_rejects_relaxed_phase_extrapolation(
    tmp_path: Path,
) -> None:
    payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    payload["first_admission_domain"][
        "phase_extrapolation_policy"
    ] = "allowed"
    mutated = tmp_path / "mutated.json"
    mutated.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        JonesSourceAuditError,
        match="first admission domain differs",
    ):
        load_spec(mutated)


def test_archive_audit_rejects_wrong_file_before_tar_processing(
    tmp_path: Path,
) -> None:
    wrong = tmp_path / "SM-01.tar.gz"
    wrong.write_bytes(b"not the official archive")
    with pytest.raises(
        JonesSourceAuditError,
        match="archive byte count differs",
    ):
        audit_archive(wrong, spec_path=SPEC_PATH)
