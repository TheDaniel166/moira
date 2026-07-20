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
_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"


def _canonical_bytes(path: Path) -> bytes:
    text = path.read_bytes().decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _document() -> dict:
    return json.loads(_PROFILE.read_text(encoding="utf-8"))


def test_manifest_hash_and_profile_metadata_match_packaged_data() -> None:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))

    assert set(manifest) == {
        "schema_version",
        "generated_at_utc",
        "hash_algorithm",
        "hash_canonicalization",
        "profiles",
    }
    assert manifest["schema_version"] == 1
    assert manifest["generated_at_utc"] == "2026-07-20T11:03:23Z"
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
        "admission_status": "research_only",
        "product_kind": "aksara_prasna_operating_schedule",
    }


def test_manifest_requires_an_iso_utc_generation_timestamp(tmp_path: Path) -> None:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    manifest["generated_at_utc"] = "2026-07-20"
    invalid_manifest = tmp_path / _MANIFEST.name
    invalid_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(pakshi.PanchaPakshiDataError, match="UTC timestamp"):
        pakshi._read_manifest(invalid_manifest)


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
        if "schedule_grid" in locator["evidence_role"]
    }
    assert grid_roles == {
        "ia_n19_n20": "non_executable_unreconciled_schedule_grids",
        "ia_n22_n25": "non_executable_unreconciled_schedule_grids",
        "ia_n27_n30": "non_executable_unreconciled_schedule_grids",
        "ia_n32_n35": "non_executable_unreconciled_schedule_grids",
    }
    relationship_locator = next(
        locator
        for locator in document["source_locators"]
        if locator["locator_id"] == "ia_n52"
    )
    assert relationship_locator["evidence_role"] == (
        "contested_non_executable_directed_relationship_reading"
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
        pakshi._parse_profile_document(document)


def test_unknown_locator_and_unreduced_fraction_fail_closed() -> None:
    bad_locator = _document()
    bad_locator["duration_vector_nazhigai"][0]["source_locators"] = [
        "ia_unverified"
    ]
    with pytest.raises(pakshi.PanchaPakshiDataError, match="unknown locators"):
        pakshi._parse_profile_document(bad_locator)

    unreduced = _document()
    unreduced["duration_vector_nazhigai"][0]["duration"] = {
        "numerator": 10,
        "denominator": 8,
    }
    with pytest.raises(pakshi.PanchaPakshiDataError, match="reduced exact form"):
        pakshi._parse_profile_document(unreduced)


def test_frozen_source_records_and_reconciliation_preserve_disagreement() -> None:
    review = json.loads(_INDEPENDENT_REVIEW.read_text(encoding="utf-8"))
    blind = json.loads(_BLIND_READING.read_text(encoding="utf-8"))
    grid = json.loads(_GRID_READING.read_text(encoding="utf-8"))
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
        "agreed_machine_readings",
        "partial_cross_record_matches",
        "single_record_profile_matches",
        "unresolved_findings",
        "tamil_review_questions",
        "artifact_distribution_boundary",
    }
    assert review["schema_version"] == 1
    assert review["evidence_class"] == "machine_assisted_reconciliation"
    assert review["status"] == "non_executable_unreconciled"
    assert review["admission_effect"] == "blocks_public_admission"
    assert review["reconciliation_method"]["competent_tamil_signoff"] is False
    assert document["profile"]["admission_status"] == "research_only"

    reviewed_profile = review["reviewed_profile"]
    assert reviewed_profile["path"] == (
        "moira/data/pancha_pakshi_agastya_madras_1879_"
        "akshara_fixed_clock.json"
    )
    assert reviewed_profile["sha256"] == hashlib.sha256(
        _canonical_bytes(_PROFILE)
    ).hexdigest()
    assert reviewed_profile["admission_status"] == "research_only"

    source_paths = {
        _BLIND_READING.name: _BLIND_READING,
        _GRID_READING.name: _GRID_READING,
    }
    source_records = {entry["record_id"]: entry for entry in review["source_records"]}
    assert set(source_records) == {blind["record_id"], grid["record_id"]}
    assert set(blind) == {
        "schema_version",
        "record_id",
        "record_kind",
        "created_at_utc",
        "reviewer_identity",
        "protocol",
        "witness",
        "readings",
        "unresolved",
    }
    assert set(grid) == {
        "schema_version",
        "record_id",
        "record_kind",
        "created_at_utc",
        "reviewer_identity",
        "protocol",
        "witness",
        "structural_readings",
        "representative_grid_rows",
        "human_review_questions",
    }
    for record in (blind, grid):
        assert record["schema_version"] == 1
        assert record["record_kind"].startswith("frozen_machine_assisted_")
        assert record["reviewer_identity"]
        assert pakshi._require_utc_timestamp(
            record["created_at_utc"], f"{record['record_id']}.created_at_utc"
        ) == record["created_at_utc"]
    for record in source_records.values():
        path = source_paths[record["path"]]
        assert record["sha256"] == hashlib.sha256(
            _canonical_bytes(path)
        ).hexdigest()

    assert blind["protocol"]["protocol_id"] == "blind_source_transcription_v1"
    assert blind["protocol"]["isolation_observed"] is True
    assert blind["protocol"]["competent_tamil_signoff"] is False
    assert grid["protocol"]["protocol_id"] == "representative_grid_reading_v1"
    assert grid["protocol"]["pairing_policy"].startswith(
        "Bird and activity rows are preserved separately"
    )
    assert grid["protocol"]["competent_tamil_signoff"] is False
    for reading in grid["representative_grid_rows"]:
        assert set(reading) == {
            "reading_id",
            "locators",
            "printed_bird_order",
            "printed_activity_row",
            "pairing_status",
        }
        assert reading["locators"]
        assert reading["pairing_status"] == "unresolved_table_axes"

    source = document["source"]
    for record in (blind, grid):
        witness = record["witness"]
        assert witness["archive_item_id"] == source["witness_id"]
        assert witness["archive_pdf_md5"] == source["archive_pdf_md5"]
        assert witness["archive_pdf_sha1"] == source["archive_pdf_sha1"]
        assert witness["locally_verified_pdf_sha256"] == (
            source["locally_verified_pdf_sha256"]
        )

    agreed = review["agreed_machine_readings"]
    assert set(agreed) == {"duration_vector_nazhigai"}
    blind_readings = blind["readings"]
    grid_structural_readings = {
        reading["reading_id"]: reading
        for reading in grid["structural_readings"]
    }
    assert agreed["duration_vector_nazhigai"] == (
        blind_readings["duration_vector_nazhigai"]["values"]
    )
    assert agreed["duration_vector_nazhigai"] == (
        grid_structural_readings["duration_vector"]["values"]
    )

    partial_matches = review["partial_cross_record_matches"]
    assert set(partial_matches) == {"displayed_half_structure"}
    displayed_half = partial_matches["displayed_half_structure"]
    assert set(displayed_half) == {
        "evidence_status",
        "source_scope",
        "values",
    }
    assert displayed_half["evidence_status"] == (
        "both_records_match_values_scope_not_generalized"
    )
    assert displayed_half["source_scope"] == (
        "displayed_purva_day_construction_only"
    )
    assert displayed_half["values"] == (
        grid_structural_readings["fixed_half_and_samam_structure"]["values"]
    )
    blind_temporal = blind_readings["temporal_model"]["values"]
    assert displayed_half["values"] == {
        "half_span_nazhigai": blind_temporal["day_span_nazhigai"],
        "samam_count": blind_temporal["samam_count_per_half"],
        "samam_span_nazhigai": blind_temporal["samam_span_nazhigai"],
    }
    scope_question = (
        "Does the fixed thirty-nazhigai statement govern both day and night "
        "or only the displayed Purva-day construction?"
    )
    assert scope_question in grid["human_review_questions"]

    single_record_matches = review["single_record_profile_matches"]
    assert set(single_record_matches) == {
        "source_record_id",
        "evidence_status",
        "temporal_model",
        "initial_vowels",
        "first_eat_by_weekday",
    }
    assert single_record_matches["source_record_id"] == blind["record_id"]
    assert single_record_matches["evidence_status"] == (
        "one_source_reading_matches_profile_not_independent_consensus"
    )
    tamil_vowels = {
        symbol: entry["bird"]
        for entry in document["initial_vowel_identity"]["entries"]
        for symbol in entry["symbols"]
        if not symbol.isascii()
    }
    assert tamil_vowels == single_record_matches["initial_vowels"]

    temporal = document["temporal_model"]
    profile_temporal = {
        "day_span_nazhigai": temporal["day_span_nazhigai"]["numerator"],
        "night_span_nazhigai": temporal["night_span_nazhigai"]["numerator"],
        "samam_count_per_half": temporal["samam_count_per_half"],
        "samam_span_nazhigai": temporal["samam_span_nazhigai"]["numerator"],
    }
    assert single_record_matches["temporal_model"] == blind_temporal
    assert single_record_matches["temporal_model"] == profile_temporal
    assert all(
        temporal[field]["denominator"] == 1
        for field in (
            "day_span_nazhigai",
            "night_span_nazhigai",
            "samam_span_nazhigai",
        )
    )
    profile_durations = {
        rule["activity"]: [
            rule["duration"]["numerator"],
            rule["duration"]["denominator"],
        ]
        for rule in document["duration_vector_nazhigai"]
    }
    assert profile_durations == agreed["duration_vector_nazhigai"]

    generators = {
        generator["generator_id"]: [
            entry["bird"] for entry in generator["first_eat_by_weekday"]
        ]
        for generator in document["schedule_generators"]
    }
    for generator_id, expected in single_record_matches[
        "first_eat_by_weekday"
    ].items():
        assert generators[generator_id] == expected

    findings = {
        finding["finding_id"]: finding
        for finding in review["unresolved_findings"]
    }
    assert set(findings) == {
        "temporal_model_scope",
        "purva_night_grid_assembly",
        "amara_night_weekday_seeds",
        "amara_night_grid_assembly",
        "directed_relationship_matrix",
        "printed_grid_semantics",
    }
    source_record_ids = set(source_records)
    for finding in findings.values():
        assert set(finding) == {
            "finding_id",
            "surface",
            "status",
            "profile_snapshot",
            "source_readings",
            "required_resolution",
        }
        assert finding["status"] == "unresolved"
        assert finding["surface"]
        assert finding["required_resolution"]
        assert finding["source_readings"]
        for reading in finding["source_readings"]:
            assert set(reading) == {
                "record_id",
                "reading_status",
                "locator_ids",
                "reading",
            }
            assert reading["record_id"] in source_record_ids
            assert reading["reading_status"]
            assert reading["locator_ids"]

    assert findings["temporal_model_scope"]["source_readings"][1]["reading"][
        "scope_question"
    ] == scope_question

    profile = pakshi.load_pancha_pakshi_profile(_PROFILE_ID)
    assert profile_temporal == findings["temporal_model_scope"][
        "profile_snapshot"
    ]
    purva_night = pakshi.generate_pancha_pakshi_schedule(
        profile,
        paksha=pakshi.PanchaPakshiPaksha.PURVA,
        half=pakshi.PanchaPakshiHalf.NIGHT,
        weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
    )
    assert [
        [cell.bird.value, cell.activity.value] for cell in purva_night.cells[:5]
    ] == findings["purva_night_grid_assembly"]["profile_snapshot"]
    assert generators["amara_night"] == findings["amara_night_weekday_seeds"][
        "profile_snapshot"
    ]

    amara_night = pakshi.generate_pancha_pakshi_schedule(
        profile,
        paksha=pakshi.PanchaPakshiPaksha.AMARA,
        half=pakshi.PanchaPakshiHalf.NIGHT,
        weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
    )
    assert {
        cell.bird.value: cell.activity.value for cell in amara_night.cells[:5]
    } == dict(findings["amara_night_grid_assembly"]["profile_snapshot"])

    friend_edges = [
        [cell["subject"], cell["target"]]
        for cell in document["directed_relationships"]["cells"]
        if cell["relation"] == "friend"
    ]
    assert friend_edges == findings["directed_relationship_matrix"][
        "profile_snapshot"
    ]["friend_edges"]
    assert document["profile"]["assembly_policy"] == findings[
        "printed_grid_semantics"
    ]["profile_snapshot"]
    artifact_boundary = review["artifact_distribution_boundary"]
    assert set(artifact_boundary) == {
        "policy_status",
        "excluded_artifacts",
        "license_scope",
        "admission_effect",
    }
    assert artifact_boundary["policy_status"] == source[
        "artifact_distribution_status"
    ]
    assert artifact_boundary["excluded_artifacts"] == [
        "scan",
        "pdf",
        "ocr",
        "page_images",
        "table_layout",
        "source_prose",
        "third_party_translation",
    ]
    assert artifact_boundary["license_scope"] == (
        "MIT covers Moira-authored code, schema, prose, and profile representation."
    )
    assert artifact_boundary["admission_effect"] == (
        "outside_public_admission_under_standing_non_bundling_policy"
    )
