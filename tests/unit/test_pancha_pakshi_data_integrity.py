"""Data and fail-closed schema checks for the Pancha Pakshi profile."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from moira import _pancha_pakshi as pakshi


_ROOT = Path(__file__).resolve().parents[2]
_DATA = _ROOT / "moira" / "data"
_MANIFEST = _DATA / "pancha_pakshi_manifest.json"
_PROFILE = _DATA / "pancha_pakshi_agastya_madras_1879_akshara_fixed_clock.json"
_INDEPENDENT_REVIEW = (
    _ROOT / "tests" / "fixtures" / "pancha_pakshi_1879_independent_review.json"
)
_BLIND_READING = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_1879_blind_reading_2026_07_20.json"
)
_GRID_READING = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_1879_grid_reading_2026_07_20.json"
)
_ADJUDICATION = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_1879_adjudication_2026_07_20.json"
)
_PUBLIC_ADMISSION = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_1879_public_admission_2026_07_20.json"
)
_LOCAL_SOLAR_CONTEXT_ADMISSION = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_1879_local_solar_context_2026_07_20.json"
)
_FIXED_CLOCK_MATERIALIZATION_ADMISSION = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_1879_fixed_clock_materialization_2026_07_20.json"
)
_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_PRIOR_PROFILE_SHA256 = "02f1252cbcff10f680148b0213021d30db043c0ecc7387be727ad5d60de04e98"
_PHASE_1_DECISION_ID = "pancha_pakshi_1879_source_scoped_public_2026_07_20"
_LOCAL_SOLAR_CONTEXT_DECISION_ID = (
    "pancha_pakshi_1879_local_solar_context_2026_07_20"
)
_FIXED_CLOCK_MATERIALIZATION_DECISION_ID = (
    "pancha_pakshi_1879_fixed_clock_materialization_2026_07_20"
)


def _canonical_bytes(path: Path) -> bytes:
    text = path.read_bytes().decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _document() -> dict:
    return json.loads(_PROFILE.read_text(encoding="utf-8"))


def _parse_current_document(document: dict) -> pakshi.PanchaPakshiProfile:
    return pakshi._parse_profile_document(
        document,
        admission_status=pakshi.PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC,
        default_selection_allowed=False,
        capabilities=(
            pakshi.PanchaPakshiCapability.AKSARA_IDENTITY,
            pakshi.PanchaPakshiCapability.NOMINAL_SCHEDULE,
            pakshi.PanchaPakshiCapability.DIRECTED_RELATIONSHIPS,
            pakshi.PanchaPakshiCapability.ASTRONOMICAL_CONTEXT,
            pakshi.PanchaPakshiCapability.FIXED_CLOCK_MATERIALIZATION,
        ),
        admission_decision_id=_FIXED_CLOCK_MATERIALIZATION_DECISION_ID,
    )

def test_manifest_hash_and_profile_metadata_match_packaged_data() -> None:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))

    assert set(manifest) == {
        "schema_version",
        "generated_at_utc",
        "hash_algorithm",
        "hash_canonicalization",
        "profiles",
    }
    assert manifest["schema_version"] == 2
    assert manifest["generated_at_utc"] == "2026-07-20T15:50:57Z"
    assert manifest["hash_algorithm"] == "sha256"
    assert manifest["hash_canonicalization"] == (
        "UTF-8 text with CRLF and CR normalized to LF before hashing"
    )
    assert len(manifest["profiles"]) == 1
    entry = manifest["profiles"][0]
    assert entry == {
        "profile_id": _PROFILE_ID,
        "path": _PROFILE.name,
        "sha256": hashlib.sha256(_canonical_bytes(_PROFILE)).hexdigest(),
        "admission_status": "source_scoped_public",
        "product_kind": "aksara_prasna_operating_schedule",
        "default_selection_allowed": False,
        "capabilities": [
            "aksara_identity",
            "nominal_schedule",
            "directed_relationships",
            "astronomical_context",
            "fixed_clock_materialization",
        ],
        "admission_decision_id": _FIXED_CLOCK_MATERIALIZATION_DECISION_ID,
    }


def test_schema_v2_profile_requires_manifest_policy_keywords() -> None:
    document = _document()
    profile = _parse_current_document(document)
    assert profile.admission_status is pakshi.PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC
    assert profile.default_selection_allowed is False
    assert profile.admission_decision_id.startswith("pancha_pakshi_")

    with pytest.raises(pakshi.PanchaPakshiDataError, match="default_selection_allowed"):
        pakshi._parse_profile_document(
            document,
            admission_status=pakshi.PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC,
            default_selection_allowed=True,
            capabilities=(
                pakshi.PanchaPakshiCapability.AKSARA_IDENTITY,
                pakshi.PanchaPakshiCapability.NOMINAL_SCHEDULE,
                pakshi.PanchaPakshiCapability.DIRECTED_RELATIONSHIPS,
                pakshi.PanchaPakshiCapability.ASTRONOMICAL_CONTEXT,
                pakshi.PanchaPakshiCapability.FIXED_CLOCK_MATERIALIZATION,
            ),
            admission_decision_id=_FIXED_CLOCK_MATERIALIZATION_DECISION_ID,
        )


def test_manifest_requires_an_iso_utc_generation_timestamp(tmp_path: Path) -> None:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    manifest["generated_at_utc"] = "2026-07-20"
    invalid_manifest = tmp_path / _MANIFEST.name
    invalid_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(pakshi.PanchaPakshiDataError, match="UTC timestamp"):
        pakshi._read_manifest(invalid_manifest)


@pytest.mark.parametrize(
    ("mutator", "message"),
    (
        (
            lambda entry: entry.__setitem__(
                "admission_status", "universal_default"
            ),
            "unknown value",
        ),
        (
            lambda entry: entry.__setitem__(
                "default_selection_allowed", True
            ),
            "must remain false",
        ),
        (
            lambda entry: entry["capabilities"].append("invented_scoring"),
            "unknown value",
        ),
        (
            lambda entry: entry["capabilities"].pop(),
            "disagree with product_kind",
        ),
        (
            lambda entry: entry["capabilities"].reverse(),
            "canonical capability order",
        ),
    ),
)
def test_manifest_admission_policy_fails_closed(
    tmp_path: Path, mutator, message: str
) -> None:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    mutator(manifest["profiles"][0])
    invalid_manifest = tmp_path / _MANIFEST.name
    invalid_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(pakshi.PanchaPakshiDataError, match=message):
        pakshi._read_manifest(invalid_manifest)


def test_public_admission_migrates_metadata_without_rewriting_frozen_evidence() -> None:
    decision = json.loads(_PUBLIC_ADMISSION.read_text(encoding="utf-8"))
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))

    assert set(decision) == {
        "schema_version",
        "decision_id",
        "decided_at_utc",
        "decision_kind",
        "profile_id",
        "profile_migration",
        "semantic_projection",
        "admission",
        "evidence_records",
        "evidence_limits",
        "public_nonclaims",
        "artifact_distribution_boundary",
    }
    assert decision["schema_version"] == 1
    assert decision["decision_kind"] == "source_scoped_public_admission"
    assert decision["profile_id"] == _PROFILE_ID
    assert pakshi._require_utc_timestamp(
        decision["decided_at_utc"], "admission.decided_at_utc"
    ) == decision["decided_at_utc"]

    migration = decision["profile_migration"]
    assert migration["prior_schema_version"] == 1
    assert migration["current_schema_version"] == 2
    assert migration["prior_profile_sha256"] == _PRIOR_PROFILE_SHA256
    assert migration["current_profile_sha256"] == hashlib.sha256(
        _canonical_bytes(_PROFILE)
    ).hexdigest()
    assert migration["metadata_changes_only"] == [
        "profile schema version 1 to 2",
        "admission state moved from profile facts to manifest policy",
        "title changed from research profile to source-scoped profile",
        (
            "omission reasons changed from research-profile to "
            "source-scoped-profile wording"
        ),
        "authority-bird nonclaim added to runtime omissions",
    ]

    projection = decision["semantic_projection"]
    assert projection["algorithm_id"] == (
        "pancha_pakshi_computational_semantics_v1"
    )
    assert projection["scope"] == (
        "identity mapping, temporal model, exact durations, generated "
        "schedule cells, and directed relationship values; intentionally "
        "excludes admission and provenance metadata changed by this migration"
    )
    assert projection["canonicalization"] == (
        "UTF-8 JSON with sorted object keys, no insignificant whitespace, and "
        "exact fractions represented as numerator-denominator integer pairs"
    )
    assert projection["sha256"] == (
        "7ac6da0aa5a556d1e510f87b73fff767be56749bf263e0722c925eeed01bafec"
    )
    assert {
        key: projection[key]
        for key in (
            "identity_symbol_count",
            "schedule_count",
            "schedule_cell_count",
            "directed_relationship_count",
        )
    } == {
        "identity_symbol_count": 10,
        "schedule_count": 28,
        "schedule_cell_count": 700,
        "directed_relationship_count": 20,
    }

    admission = decision["admission"]
    entry = manifest["profiles"][0]
    assert decision["decision_id"] == _PHASE_1_DECISION_ID
    assert entry["admission_decision_id"] == (
        _FIXED_CLOCK_MATERIALIZATION_DECISION_ID
    )
    assert admission["admission_status"] == entry["admission_status"]
    assert admission["product_kind"] == entry["product_kind"]
    assert admission["default_selection_allowed"] is False
    assert admission["capabilities"] == [
        "aksara_identity",
        "nominal_schedule",
        "directed_relationships",
    ]
    assert entry["capabilities"] == [
        *admission["capabilities"],
        "astronomical_context",
        "fixed_clock_materialization",
    ]
    assert admission["governing_witness_id"] == _document()["source"]["witness_id"]
    assert admission["astronomical_routing_status"] == "not_performed"
    assert admission["exact_public_claim"] == (
        "Agastya-attributed Madras 1879 aksara/query-or-name-initial "
        "fixed-clock Pancha Pakshi operating schedule and directed "
        "relationship matrix"
    )
    assert "universal Pancha Pakshi canon" in decision["public_nonclaims"]
    assert decision["evidence_limits"] == {
        "competent_tamil_signoff": False,
        "independent_witness_collation": "not_completed",
        "external_oracle_status": "none",
        "effect": (
            "limits the claim to this named machine-reconciled witness and "
            "prevents any universal or default canon claim"
        ),
    }
    assert decision["artifact_distribution_boundary"]["policy_effect"] == (
        "This is the standing non-bundling architecture, not a "
        "rights-clearance gate."
    )

    fixture_paths = {
        _BLIND_READING.name: _BLIND_READING,
        _GRID_READING.name: _GRID_READING,
        _ADJUDICATION.name: _ADJUDICATION,
        _INDEPENDENT_REVIEW.name: _INDEPENDENT_REVIEW,
    }
    assert {record["path"] for record in decision["evidence_records"]} == set(
        fixture_paths
    )
    for record in decision["evidence_records"]:
        assert record["sha256"] == hashlib.sha256(
            _canonical_bytes(fixture_paths[record["path"]])
        ).hexdigest()


def test_local_solar_context_admission_is_additive_and_hash_bound() -> None:
    decision = json.loads(
        _LOCAL_SOLAR_CONTEXT_ADMISSION.read_text(encoding="utf-8")
    )
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    phase_1 = json.loads(_PUBLIC_ADMISSION.read_text(encoding="utf-8"))
    entry = manifest["profiles"][0]

    assert set(decision) == {
        "schema_version",
        "decision_id",
        "decided_at_utc",
        "decision_kind",
        "profile_id",
        "prior_admission",
        "profile_binding",
        "manifest_transition",
        "computational_object",
        "assembly_doctrine",
        "authority_and_provenance",
        "validation_evidence",
        "public_claim",
        "public_nonclaims",
        "artifact_distribution_boundary",
    }
    assert decision["schema_version"] == 1
    assert decision["decision_id"] == _LOCAL_SOLAR_CONTEXT_DECISION_ID
    assert decision["decision_kind"] == (
        "additive_modern_local_solar_context_admission"
    )
    assert decision["profile_id"] == _PROFILE_ID
    assert pakshi._require_utc_timestamp(
        decision["decided_at_utc"], "local_solar_context.decided_at_utc"
    ) == decision["decided_at_utc"]

    prior = decision["prior_admission"]
    assert prior["decision_id"] == phase_1["decision_id"] == _PHASE_1_DECISION_ID
    assert prior["fixture_path"] == _PUBLIC_ADMISSION.name
    assert prior["fixture_sha256"] == hashlib.sha256(
        _canonical_bytes(_PUBLIC_ADMISSION)
    ).hexdigest()

    profile_binding = decision["profile_binding"]
    assert profile_binding["path"] == (
        "moira/data/"
        "pancha_pakshi_agastya_madras_1879_akshara_fixed_clock.json"
    )
    assert profile_binding["sha256"] == hashlib.sha256(
        _canonical_bytes(_PROFILE)
    ).hexdigest()
    assert profile_binding["profile_content_changed"] is False
    assert profile_binding["admission_status"] == "source_scoped_public"
    assert profile_binding["default_selection_allowed"] is False

    transition = decision["manifest_transition"]
    reconstructed_phase_1_manifest = copy.deepcopy(manifest)
    reconstructed_phase_1_manifest["generated_at_utc"] = (
        phase_1["decided_at_utc"]
    )
    reconstructed_phase_1_entry = reconstructed_phase_1_manifest["profiles"][0]
    reconstructed_phase_1_entry["capabilities"] = phase_1["admission"][
        "capabilities"
    ]
    reconstructed_phase_1_entry["admission_decision_id"] = phase_1[
        "decision_id"
    ]
    reconstructed_phase_1_bytes = (
        json.dumps(
            reconstructed_phase_1_manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    assert transition["prior_manifest_sha256"] == hashlib.sha256(
        reconstructed_phase_1_bytes
    ).hexdigest()
    reconstructed_stage_2a_manifest = copy.deepcopy(manifest)
    reconstructed_stage_2a_manifest["generated_at_utc"] = decision["decided_at_utc"]
    reconstructed_stage_2a_entry = reconstructed_stage_2a_manifest["profiles"][0]
    reconstructed_stage_2a_entry["capabilities"] = transition[
        "current_capabilities"
    ]
    reconstructed_stage_2a_entry["admission_decision_id"] = decision[
        "decision_id"
    ]
    reconstructed_stage_2a_bytes = (
        json.dumps(
            reconstructed_stage_2a_manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    assert transition["current_manifest_sha256"] == hashlib.sha256(
        reconstructed_stage_2a_bytes
    ).hexdigest()
    assert transition["prior_capabilities"] == phase_1["admission"]["capabilities"]
    assert transition["current_capabilities"] == [
        *transition["prior_capabilities"],
        "astronomical_context",
    ]
    assert transition["added_capability"] == "astronomical_context"
    assert transition["profile_product_kind_changed"] is False
    assert transition["profile_admission_status_changed"] is False
    assert entry["capabilities"] == [
        *transition["current_capabilities"],
        "fixed_clock_materialization",
    ]
    assert entry["admission_decision_id"] == (
        _FIXED_CLOCK_MATERIALIZATION_DECISION_ID
    )

    computation = decision["computational_object"]
    assert computation["engine_function"] == (
        "pancha_pakshi_local_solar_context_at"
    )
    assert computation["facade_method"] == (
        "Moira.pancha_pakshi_local_solar_context"
    )
    assert computation["rest_route"] == (
        "POST /v1/pancha-pakshi/context/local-solar"
    )
    assert computation["policy"] == {
        "policy_id": "local_solar_day_explicit_paksha_v1",
        "paksha_basis": "caller_supplied_source_label",
        "solar_day_basis": "topocentric_sunrise_to_next_sunrise",
        "solar_event_altitude_deg": -0.833,
        "observer_elevation_m": 0.0,
        "solar_altitude_refraction_mode": (
            "unrefracted_signal_standard_refraction_and_semidiameter_in_threshold"
        ),
        "half_basis": "topocentric_sunrise_sunset",
        "weekday_basis": "local_mean_solar_time_at_governing_sunrise",
        "offset_materialization_status": "not_performed",
    }
    assert decision["assembly_doctrine"]["boundary_rule"] == (
        "Day is sunrise inclusive to sunset exclusive; night is sunset "
        "inclusive to next sunrise exclusive."
    )
    assert decision["authority_and_provenance"]["policy_origin"] == (
        "modern_moira_composition_policy"
    )
    validation = decision["validation_evidence"]
    horizons_fixture = _ROOT / validation["fixture_path"]
    assert validation["evidence_class"] == "authority_validation"
    assert pakshi._require_utc_timestamp(
        validation["validated_at_utc"],
        "local_solar_context.validation_evidence.validated_at_utc",
    ) == validation["validated_at_utc"]
    assert validation["authority"] == "JPL Horizons observer tables"
    assert validation["case_id"] == "sun-new-york-equinox"
    assert validation["fixture_sha256"] == hashlib.sha256(
        _canonical_bytes(horizons_fixture)
    ).hexdigest()
    assert validation["fixture_hash_canonicalization"] == (
        "UTF-8 text with CRLF and CR normalized to LF before hashing"
    )
    assert validation["content_identified_kernel"] == "DE-0441LE-0441"
    assert validation["moira_solar_event_altitude_deg"] == -0.833
    assert validation["authority_fixture_altitude_deg"] == -0.8333
    assert validation["tolerance_seconds"] == 2.0
    assert validation["observed_sunrise_error_seconds"] <= 2.0
    assert validation["observed_sunset_error_seconds"] <= 2.0
    assert "does not validate" in validation["scope"]
    assert {
        "astronomical or lunar inference of Purva or Amara paksha",
        "conversion of nominal nazhigai offsets to Julian Days or datetimes",
        "a current Pancha Pakshi activity or schedule cell",
        "cross-witness normalization or corroborated public status",
        "a universal or default Pancha Pakshi canon",
    } <= set(decision["public_nonclaims"])


def test_fixed_clock_materialization_admission_is_additive_and_hash_bound() -> None:
    decision = json.loads(
        _FIXED_CLOCK_MATERIALIZATION_ADMISSION.read_text(encoding="utf-8")
    )
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    stage_2a = json.loads(
        _LOCAL_SOLAR_CONTEXT_ADMISSION.read_text(encoding="utf-8")
    )
    entry = manifest["profiles"][0]

    assert set(decision) == {
        "schema_version",
        "decision_id",
        "decided_at_utc",
        "decision_kind",
        "profile_id",
        "prior_admission",
        "profile_binding",
        "manifest_transition",
        "computational_object",
        "assembly_doctrine",
        "authority_and_provenance",
        "validation_evidence",
        "public_claim",
        "public_nonclaims",
        "artifact_distribution_boundary",
    }
    assert decision["schema_version"] == 1
    assert decision["decision_id"] == _FIXED_CLOCK_MATERIALIZATION_DECISION_ID
    assert decision["decision_kind"] == (
        "additive_modern_fixed_clock_materialization_admission"
    )
    assert decision["profile_id"] == _PROFILE_ID
    assert pakshi._require_utc_timestamp(
        decision["decided_at_utc"],
        "fixed_clock_materialization.decided_at_utc",
    ) == decision["decided_at_utc"]

    prior = decision["prior_admission"]
    assert prior["decision_id"] == stage_2a["decision_id"]
    assert prior["decision_id"] == _LOCAL_SOLAR_CONTEXT_DECISION_ID
    assert prior["fixture_path"] == _LOCAL_SOLAR_CONTEXT_ADMISSION.name
    assert prior["fixture_sha256"] == hashlib.sha256(
        _canonical_bytes(_LOCAL_SOLAR_CONTEXT_ADMISSION)
    ).hexdigest()
    assert prior["fixture_sha256"] == (
        "de8e40c161a327695702b9b152f89da8e848f32aafb4d0b155176d28381c9fd2"
    )

    profile_binding = decision["profile_binding"]
    assert profile_binding["path"] == (
        "moira/data/"
        "pancha_pakshi_agastya_madras_1879_akshara_fixed_clock.json"
    )
    assert profile_binding["sha256"] == hashlib.sha256(
        _canonical_bytes(_PROFILE)
    ).hexdigest()
    assert profile_binding["sha256"] == (
        "876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4"
    )
    assert profile_binding["profile_content_changed"] is False
    assert profile_binding["admission_status"] == "source_scoped_public"
    assert profile_binding["default_selection_allowed"] is False

    transition = decision["manifest_transition"]
    reconstructed_stage_2a_manifest = copy.deepcopy(manifest)
    reconstructed_stage_2a_manifest["generated_at_utc"] = stage_2a[
        "decided_at_utc"
    ]
    reconstructed_stage_2a_entry = reconstructed_stage_2a_manifest["profiles"][0]
    reconstructed_stage_2a_entry["capabilities"] = stage_2a[
        "manifest_transition"
    ]["current_capabilities"]
    reconstructed_stage_2a_entry["admission_decision_id"] = stage_2a[
        "decision_id"
    ]
    reconstructed_stage_2a_bytes = (
        json.dumps(
            reconstructed_stage_2a_manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    assert transition["prior_manifest_sha256"] == hashlib.sha256(
        reconstructed_stage_2a_bytes
    ).hexdigest()
    assert transition["prior_manifest_sha256"] == (
        "4587306ded9b5760940e7f80c45b6c40132590473e910ea9350c9d7fa141a2ee"
    )
    assert transition["current_manifest_sha256"] == hashlib.sha256(
        _canonical_bytes(_MANIFEST)
    ).hexdigest()
    assert transition["prior_capabilities"] == stage_2a[
        "manifest_transition"
    ]["current_capabilities"]
    assert transition["current_capabilities"] == entry["capabilities"]
    assert transition["current_capabilities"] == [
        *transition["prior_capabilities"],
        "fixed_clock_materialization",
    ]
    assert transition["added_capability"] == "fixed_clock_materialization"
    assert transition["profile_product_kind_changed"] is False
    assert transition["profile_admission_status_changed"] is False
    assert entry["admission_decision_id"] == decision["decision_id"]

    computation = decision["computational_object"]
    assert computation["engine_function"] == (
        "pancha_pakshi_fixed_clock_materialization_at"
    )
    assert computation["facade_method"] == (
        "Moira.pancha_pakshi_fixed_clock_materialization"
    )
    assert computation["rest_route"] == (
        "POST /v1/pancha-pakshi/schedule/fixed-clock"
    )
    assert computation["result_vessel"] == (
        "PanchaPakshiFixedClockMaterialization"
    )
    assert computation["policy_vessel"] == (
        "PanchaPakshiFixedClockMaterializationPolicy"
    )
    assert computation["provenance_routing_status"] == (
        "fixed_clock_materialization_performed_paksha_caller_supplied_"
        "no_current_cell"
    )
    assert computation["policy"] == {
        "policy_id": (
            "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
        ),
        "paksha_basis": "caller_supplied_source_label",
        "solar_context_basis": "topocentric_sunrise_to_next_sunrise",
        "day_anchor": "governing_topocentric_sunrise",
        "night_anchor": "governing_topocentric_sunset",
        "nazhigai_seconds": 1440,
        "half_span_nazhigai": 30,
        "half_span_seconds": 43200,
        "offset_arithmetic_time_scale": "reader_bound_tt",
        "published_endpoint_time_scale": "ut1",
        "interval_ownership": "half_open",
        "solar_end_clipping": "none",
        "topology_metric": "fixed_end_jd_tt_minus_solar_end_jd_tt",
        "topology_coalescence_seconds": 0.0001,
        "current_cell_status": "not_performed",
        "solar_proportional_scaling_status": "not_performed",
    }

    assembly = decision["assembly_doctrine"]
    assert "reader-bound TT" in assembly["clock_layer"]
    assert "never clipped or stretched" in assembly["solar_end_rule"]
    assert "Do not select or claim" in assembly["current_cell_rule"]

    authority = decision["authority_and_provenance"]
    assert authority["policy_origin"] == "modern_moira_composition_policy"
    historical = authority["historical_source_binding"]
    assert historical["profile_sha256"] == profile_binding["sha256"]
    assert historical["temporal_locator_ids"] == ["ia_n6"]
    assert historical["duration_locator_ids"] == [
        "ia_n6",
        "ia_n23",
        "ia_n28",
        "ia_n33",
    ]
    unit = authority["nazhigai_unit_authority"]
    assert unit["authority"] == "University of Madras, Tamil Lexicon"
    assert unit["page"] == 2231
    assert unit["assertion"] == (
        "one nazhigai is an Indian hour of 60 vinadi or 24 minutes"
    )
    assert unit["url"].startswith(
        "https://dsal.uchicago.edu/cgi-bin/app/tamil-lex_query.py?"
    )
    tt = authority["tt_authority"]
    assert tt["authority"] == (
        "International Earth Rotation and Reference Systems Service"
    )
    assert tt["technical_note"] == "IERS Technical Note No. 29"
    assert "SI second" in tt["assertion"]
    solar = authority["solar_anchor_authority"]
    horizons_fixture = _ROOT / solar["fixture_path"]
    assert solar["prior_decision_sha256"] == prior["fixture_sha256"]
    assert solar["fixture_sha256"] == hashlib.sha256(
        _canonical_bytes(horizons_fixture)
    ).hexdigest()
    assert solar["evidence_role"].endswith("anchor validation only")
    assert authority["external_pancha_pakshi_current_cell_oracle_status"] == (
        "none"
    )

    validation = decision["validation_evidence"]
    assert validation["topology_coalescence_seconds"] == 0.0001
    assert validation["topology_coalescence_evidence_class"] == (
        "numerical policy, not astronomical or historical accuracy"
    )
    assert validation["external_current_cell_validation"] == (
        "not_applicable_because_no_current_cell_is_claimed"
    )
    assert {
        "a current Pancha Pakshi activity or schedule cell",
        "clipping or stretching the fixed schedule to the astronomical half",
        "solar-proportional or seasonal scaling of nominal durations",
        "cross-witness normalization or corroborated public status",
        "a universal or default Pancha Pakshi canon",
    } <= set(decision["public_nonclaims"])


def test_schema_v2_metadata_migration_reconstructs_frozen_profile_hash() -> None:
    current = _PROFILE.read_text(encoding="utf-8")
    prior = current.replace('"schema_version": 2', '"schema_version": 1', 1)
    prior = prior.replace(
        '    {"feature": "authority_birds", "status": "omitted", '
        '"reason": "No source-owned Padu, Bharana, or Adhikara bird product '
        'is admitted; instantaneous Rule activity is not reinterpreted as a '
        'day ruler."},\n',
        "",
        1,
    )
    prior = prior.replace(
        f'    "profile_id": "{_PROFILE_ID}",\n',
        f'    "profile_id": "{_PROFILE_ID}",\n'
        '    "admission_status": "research_only",\n',
        1,
    )
    prior = prior.replace(
        "Pancha Pakshi source-scoped profile",
        "Pancha Pakshi research profile",
        1,
    )
    prior = prior.replace(
        "No scoring doctrine is admitted for this source-scoped profile.",
        "No scoring doctrine is admitted for this research profile.",
        1,
    )
    prior = prior.replace(
        "No vinadi-level subdivision doctrine is admitted for this "
        "source-scoped profile.",
        "No vinadi-level subdivision doctrine is admitted for this "
        "research profile.",
        1,
    )
    canonical = (
        prior.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    )

    assert hashlib.sha256(canonical).hexdigest() == _PRIOR_PROFILE_SHA256


def test_source_identity_and_locator_ledger_are_hash_bound() -> None:
    document = _document()
    source = document["source"]

    assert source["witness_id"] == "dli.rmrl.000451_images"
    assert source["publication_year"] == 1879
    assert source["authorship_status"] == (
        "traditional_attribution_not_asserted_authorship"
    )
    assert source["archive_pdf_md5"] == "0736b952fb587132c2181a383ff10cfb"
    assert source["archive_pdf_sha1"] == (
        "d41ff5c2d569de6422435b20135b58be82a68560"
    )
    assert source["archive_original_image_zip_name"] == (
        "dli.rmrl.000451_images.zip"
    )
    assert source["archive_original_image_zip_source_status"] == (
        "internet_archive_original"
    )
    assert source["archive_original_image_zip_md5"] == (
        "823f14099d376ac86a358349de292e1f"
    )
    assert source["archive_original_image_zip_sha1"] == (
        "5e3dcda52dcd87f9d5a91d23f22de605cfbd01ce"
    )
    assert source["archive_pdf_name"] == "dli.rmrl.000451.pdf"
    assert source["archive_pdf_source_status"] == "internet_archive_derivative"
    assert source["locally_verified_pdf_sha256"] == (
        "ed52945ee141faa3f6967b8f043077b95abef9ff674ffb83eaba633417c669c9"
    )
    assert source["artifact_distribution_status"] == (
        "reference_only_source_artifacts_not_packaged"
    )
    assert source["redistribution_policy"] == (
        "normalized_rules_only_no_scan_ocr_page_images_layout_source_prose_or_"
        "third_party_translation"
    )
    assert source["license_scope"] == (
        "mit_covers_moira_authored_code_schema_prose_and_profile_representation"
    )
    assert "Kandasami Pillai" in source["catalogued_contributor_note"]
    assert "research inputs, not package assets" in source[
        "artifact_distribution_note"
    ]
    assert "never redistributes" in source["artifact_distribution_note"]
    assert "do not govern public admission" in source[
        "artifact_distribution_note"
    ]

    locator_ids = {
        locator["locator_id"] for locator in document["source_locators"]
    }
    assert locator_ids == {
        "ia_n5",
        "ia_n6",
        "ia_n10",
        "ia_n16",
        "ia_n19_n20",
        "ia_n21",
        "ia_n22",
        "ia_n22_n25",
        "ia_n23",
        "ia_n26",
        "ia_n27_n30",
        "ia_n28",
        "ia_n31",
        "ia_n32",
        "ia_n32_n35",
        "ia_n33",
        "ia_n52",
    }
    grid_roles = {
        locator["locator_id"]: locator["evidence_role"]
        for locator in document["source_locators"]
        if locator["locator_id"]
        in {"ia_n19_n20", "ia_n22_n25", "ia_n27_n30", "ia_n32_n35"}
    }
    assert grid_roles == {
        "ia_n19_n20": (
            "machine_reconciled_assignment_grid_not_chronological_authority"
        ),
        "ia_n22_n25": (
            "machine_reconciled_assignment_grid_not_chronological_authority"
        ),
        "ia_n27_n30": (
            "machine_reconciled_assignment_grid_not_chronological_authority"
        ),
        "ia_n32_n35": (
            "machine_reconciled_assignment_grid_not_chronological_authority"
        ),
    }
    relationship_locator = next(
        locator
        for locator in document["source_locators"]
        if locator["locator_id"] == "ia_n52"
    )
    assert relationship_locator["evidence_role"] == (
        "machine_reviewed_directed_relationship_prose"
    )


def test_loader_detects_profile_hash_tampering(tmp_path: Path) -> None:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    copied_profile = tmp_path / _PROFILE.name
    copied_manifest = tmp_path / _MANIFEST.name
    copied_profile.write_bytes(_PROFILE.read_bytes() + b"\n")
    copied_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )

    pakshi._load_profile_cached.cache_clear()
    with pytest.raises(pakshi.PanchaPakshiDataError, match="hash mismatch"):
        pakshi._load_profile_cached(_PROFILE_ID, str(copied_manifest.resolve()))
    pakshi._load_profile_cached.cache_clear()


@pytest.mark.parametrize(
    "mutator",
    (
        lambda document: document.update({"unknown_policy": True}),
        lambda document: document["birds"].__setitem__(0, "eagle"),
        lambda document: document["schedule_generators"].pop(),
        lambda document: document["schedule_generators"][0][
            "first_eat_by_weekday"
        ].pop(),
        lambda document: document["directed_relationships"]["cells"].pop(),
        lambda document: document["explicit_omissions"].pop(),
        lambda document: document["source"].__setitem__(
            "artifact_distribution_status", "bundled"
        ),
    ),
)
def test_schema_unknown_values_and_incomplete_tables_fail_closed(mutator) -> None:
    document = copy.deepcopy(_document())
    mutator(document)

    with pytest.raises(pakshi.PanchaPakshiDataError):
        _parse_current_document(document)


def test_unknown_locator_and_unreduced_fraction_fail_closed() -> None:
    bad_locator = _document()
    bad_locator["duration_vector_nazhigai"][0]["source_locators"] = [
        "ia_unverified"
    ]
    with pytest.raises(pakshi.PanchaPakshiDataError, match="unknown locators"):
        _parse_current_document(bad_locator)

    unreduced = _document()
    unreduced["duration_vector_nazhigai"][0]["duration"] = {
        "numerator": 10,
        "denominator": 8,
    }
    with pytest.raises(pakshi.PanchaPakshiDataError, match="reduced exact form"):
        _parse_current_document(unreduced)


def test_frozen_source_records_and_machine_reconciliation_are_hash_bound() -> None:
    review = json.loads(_INDEPENDENT_REVIEW.read_text(encoding="utf-8"))
    blind = json.loads(_BLIND_READING.read_text(encoding="utf-8"))
    grid = json.loads(_GRID_READING.read_text(encoding="utf-8"))
    adjudication = json.loads(_ADJUDICATION.read_text(encoding="utf-8"))
    document = _document()

    assert set(review) == {
        "schema_version",
        "fixture_id",
        "evidence_class",
        "created_at_utc",
        "status",
        "admission_effect",
        "reviewed_profile",
        "source_records",
        "reconciliation_method",
        "historical_disagreements",
        "adjudicated_machine_readings",
        "resolved_findings",
        "remaining_admission_gaps",
        "artifact_distribution_boundary",
    }
    assert review["schema_version"] == 2
    assert review["evidence_class"] == "machine_assisted_reconciliation"
    assert review["status"] == "private_executable_machine_reconciled"
    assert review["admission_effect"] == "blocks_public_admission"
    assert pakshi._require_utc_timestamp(
        review["created_at_utc"], "reconciliation.created_at_utc"
    ) == review["created_at_utc"]

    reviewed_profile = review["reviewed_profile"]
    assert reviewed_profile == {
        "path": (
            "moira/data/pancha_pakshi_agastya_madras_1879_"
            "akshara_fixed_clock.json"
        ),
        "sha256": _PRIOR_PROFILE_SHA256,
        "hash_canonicalization": (
            "UTF-8 text with CRLF and CR normalized to LF before hashing"
        ),
        "admission_status": "research_only",
    }
    assert reviewed_profile["sha256"] != hashlib.sha256(
        _canonical_bytes(_PROFILE)
    ).hexdigest()

    source_paths = {
        _BLIND_READING.name: _BLIND_READING,
        _GRID_READING.name: _GRID_READING,
        _ADJUDICATION.name: _ADJUDICATION,
    }
    source_records = {entry["record_id"]: entry for entry in review["source_records"]}
    assert set(source_records) == {
        blind["record_id"],
        grid["record_id"],
        adjudication["record_id"],
    }
    for record in source_records.values():
        path = source_paths[record["path"]]
        assert record["sha256"] == hashlib.sha256(
            _canonical_bytes(path)
        ).hexdigest()

    assert blind["record_kind"] == "frozen_machine_assisted_source_reading"
    assert blind["protocol"]["protocol_id"] == "blind_source_transcription_v1"
    assert blind["protocol"]["isolation_observed"] is True
    assert blind["protocol"]["competent_tamil_signoff"] is False
    assert grid["record_kind"].startswith("frozen_machine_assisted_")
    assert grid["protocol"]["protocol_id"] == "representative_grid_reading_v1"
    assert grid["protocol"]["competent_tamil_signoff"] is False
    assert all(
        reading["pairing_status"] == "unresolved_table_axes"
        for reading in grid["representative_grid_rows"]
    )

    assert set(adjudication) == {
        "schema_version",
        "record_id",
        "record_kind",
        "created_at_utc",
        "reviewer_identity",
        "protocol",
        "witness",
        "findings",
        "limitations",
    }
    assert adjudication["schema_version"] == 1
    assert adjudication["record_kind"] == (
        "frozen_machine_assisted_image_adjudication"
    )
    assert adjudication["protocol"]["protocol_id"] == (
        "independent_page_image_adjudication_v1"
    )
    assert adjudication["protocol"]["governing_evidence"] == "page_images"
    assert adjudication["protocol"]["ocr_role"] == "locator_only"
    assert adjudication["protocol"]["competent_tamil_signoff"] is False
    assert adjudication["limitations"] == {
        "competent_tamil_signoff": False,
        "independent_witness_collation": "not_completed",
        "universal_doctrine_claim": False,
        "public_api_admission": False,
    }

    for record in (blind, grid, adjudication):
        assert pakshi._require_utc_timestamp(
            record["created_at_utc"], f"{record['record_id']}.created_at_utc"
        ) == record["created_at_utc"]
        witness = record["witness"]
        source = document["source"]
        assert witness["archive_item_id"] == source["witness_id"]
        assert witness["archive_pdf_md5"] == source["archive_pdf_md5"]
        assert witness["archive_pdf_sha1"] == source["archive_pdf_sha1"]
        assert witness["locally_verified_pdf_sha256"] == (
            source["locally_verified_pdf_sha256"]
        )

    method = review["reconciliation_method"]
    assert method["protocol_id"] == "multi_pass_page_image_reconciliation_v2"
    assert method["frozen_source_records_preserved"] is True
    assert method["competent_tamil_signoff"] is False
    assert method["external_oracle_status"] == "none"

    historical = review["historical_disagreements"]
    finding_ids = {
        "temporal_model_scope",
        "purva_night_grid_assembly",
        "amara_night_weekday_seeds",
        "amara_night_grid_assembly",
        "directed_relationship_matrix",
        "printed_grid_semantics",
    }
    assert historical["prior_status"] == "non_executable_unreconciled"
    assert set(historical["finding_ids"]) == finding_ids
    assert "without rewriting either record" in historical["preservation_policy"]

    adjudicated = review["adjudicated_machine_readings"]
    temporal = document["temporal_model"]
    assert adjudicated["temporal_model"] == {
        "day_span_nazhigai": temporal["day_span_nazhigai"]["numerator"],
        "night_span_nazhigai": temporal["night_span_nazhigai"]["numerator"],
        "samam_count_per_half": temporal["samam_count_per_half"],
        "samam_span_nazhigai": temporal["samam_span_nazhigai"]["numerator"],
    }
    assert all(
        temporal[field]["denominator"] == 1
        for field in (
            "day_span_nazhigai",
            "night_span_nazhigai",
            "samam_span_nazhigai",
        )
    )
    assert adjudicated["duration_vector_nazhigai"] == {
        rule["activity"]: [
            rule["duration"]["numerator"],
            rule["duration"]["denominator"],
        ]
        for rule in document["duration_vector_nazhigai"]
    }
    assert adjudication["findings"]["duration_vector_nazhigai"]["values"] == (
        adjudicated["duration_vector_nazhigai"]
    )

    generators = {
        generator["generator_id"]: generator
        for generator in document["schedule_generators"]
    }
    purva_night = generators["purva_night"]
    assert {
        "first_eat_by_weekday": [
            entry["bird"] for entry in purva_night["first_eat_by_weekday"]
        ],
        "eat_step_per_samam": purva_night["eat_step_per_samam"],
        "activity_offsets": purva_night["activity_offsets"],
        "chronological_activities": purva_night["chronological_activities"],
    } == {
        key: adjudicated["purva_night"][key]
        for key in (
            "first_eat_by_weekday",
            "eat_step_per_samam",
            "activity_offsets",
            "chronological_activities",
        )
    }
    profile = pakshi.load_pancha_pakshi_profile(_PROFILE_ID)
    purva_sunday = pakshi.generate_pancha_pakshi_schedule(
        profile,
        paksha=pakshi.PanchaPakshiPaksha.PURVA,
        half=pakshi.PanchaPakshiHalf.NIGHT,
        weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
    )
    assert [
        [cell.bird.value, cell.activity.value] for cell in purva_sunday.cells[:5]
    ] == adjudicated["purva_night"]["sunday_first_samam"]

    amara_night = generators["amara_night"]
    assert {
        "first_eat_by_weekday": [
            entry["bird"] for entry in amara_night["first_eat_by_weekday"]
        ],
        "eat_step_per_samam": amara_night["eat_step_per_samam"],
        "activity_offsets": amara_night["activity_offsets"],
        "chronological_activities": amara_night["chronological_activities"],
    } == adjudicated["amara_night"]

    friend_edges = [
        [cell["subject"], cell["target"]]
        for cell in document["directed_relationships"]["cells"]
        if cell["relation"] == "friend"
    ]
    assert friend_edges == adjudicated["directed_relationships"]["friend_edges"]
    assert document["directed_relationships"]["model_kind"] == (
        "source_scoped_directed_1879_machine_reviewed"
    )
    assert adjudicated["directed_relationships"]["all_other_nonself_edges"] == (
        "enemy"
    )

    table_semantics = adjudicated["table_semantics"]
    assert table_semantics["grid_role"].startswith(
        "bird/activity assignment evidence"
    )
    assert table_semantics["chronology_role"].startswith(
        "explicit prose and verse"
    )
    assert document["profile"]["assembly_policy"] == (
        "resolved_grid_axes_assign_birds_explicit_prose_and_verse_govern_"
        "chronology"
    )

    resolved = {
        finding["finding_id"]: finding for finding in review["resolved_findings"]
    }
    assert set(resolved) == finding_ids
    assert all(
        finding["status"] == "machine_resolved_for_private_profile"
        for finding in resolved.values()
    )
    assert all(finding["governing_locator_ids"] for finding in resolved.values())
    assert all(finding["resolution"] for finding in resolved.values())

    gaps = {
        gap["gap_id"]: gap for gap in review["remaining_admission_gaps"]
    }
    assert gaps == {
        "competent_tamil_review": {
            "gap_id": "competent_tamil_review",
            "status": "not_completed",
            "effect": "blocks_public_admission",
        },
        "independent_witness_collation": {
            "gap_id": "independent_witness_collation",
            "status": "not_completed",
            "effect": "blocks_public_admission",
        },
        "public_vessel_and_transport_design": {
            "gap_id": "public_vessel_and_transport_design",
            "status": "intentionally_deferred",
            "effect": "no_public_surface",
        },
    }

    source = document["source"]
    artifact_boundary = review["artifact_distribution_boundary"]
    assert artifact_boundary == {
        "policy_status": source["artifact_distribution_status"],
        "excluded_artifacts": [
            "scan",
            "pdf",
            "ocr",
            "page_images",
            "table_layout",
            "source_prose",
            "third_party_translation",
        ],
        "license_scope": (
            "MIT covers Moira-authored code, schema, prose, and profile "
            "representation."
        ),
        "admission_effect": (
            "outside_public_admission_under_standing_non_bundling_policy"
        ),
    }
