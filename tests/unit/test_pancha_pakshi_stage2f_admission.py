"""Append-only Stage 2F Pancha Pakshi admission and source-data integrity."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[2]
_PROFILE = (
    _ROOT
    / "moira"
    / "data"
    / "pancha_pakshi_agastya_madras_1879_akshara_fixed_clock.json"
)
_MANIFEST = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_FIXTURES = _ROOT / "tests" / "fixtures"
_PRIOR_DECISION = (
    _FIXTURES
    / "pancha_pakshi_1879_solar_proportional_current_cell_2026_07_20.json"
)
_MAPPING_EVIDENCE = (
    _FIXTURES
    / "pancha_pakshi_1879_lunar_paksha_mapping_reading_2026_07_20.json"
)
_DECISION = (
    _FIXTURES
    / "pancha_pakshi_1879_astronomical_paksha_inference_2026_07_20.json"
)

_PRIOR_PROFILE_SHA256 = (
    "876e4cc7cc5d894f5e558ac733913e84a8b779f72c77661e89d448fd1e05ced4"
)
_CURRENT_PROFILE_SHA256 = (
    "4fe769b6f13c4a719c9d31446dd3fef413eca5d3ce1f56340aada9f99b0dce64"
)
_PRIOR_MANIFEST_SHA256 = (
    "d2b5f8f1ae7e067d257eeb24b533be1d33349446d56d361ea59f4a71472eca70"
)
_STAGE2F_MANIFEST_SHA256 = (
    "a4fdceee4089c2812d9d77be763c1738152a63231b3f06847ea93383e4a3b327"
)
_PRIOR_DECISION_SHA256 = (
    "4ddf0a5fa5b680fa83a7bb3052ecbc5d1a9c2f685c466290f22121dd02724d18"
)
_MAPPING_EVIDENCE_SHA256 = (
    "9ce3686a90a41af916a370b8d4ec04637f22a1d32f872180c6d8a1b790e25a0e"
)
_DECISION_SHA256 = (
    "1020b28d5da8d0e823cadd352ea2236c69cbb636660a573eb5d74b8c131bc5d8"
)


def _canonical_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _digest(path: Path) -> str:
    return hashlib.sha256(_canonical_text(path).encode("utf-8")).hexdigest()


def _stage2f_profile_text() -> str:
    """Project the live profile back to its Stage 2F derivation label."""

    return _canonical_text(_PROFILE).replace(
        "machine_reconciled_source_assignment_with_declared_uncertainty",
        "machine_reconciled_source_assignment_pending_competent_tamil_review",
        1,
    )


def _stage2f_manifest_text() -> str:
    """Project the append-only manifest back to its Stage 2F state."""

    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    manifest["generated_at_utc"] = "2026-07-20T20:06:19Z"
    manifest["profiles"] = [
        entry
        for entry in manifest["profiles"]
        if entry["profile_id"] == "agastya_madras_1879_akshara_fixed_clock"
    ]
    entry = manifest["profiles"][0]
    entry["sha256"] = _CURRENT_PROFILE_SHA256
    entry["capabilities"].remove("first_eat_bird_mapping")
    entry["admission_decision_id"] = (
        "pancha_pakshi_1879_astronomical_paksha_inference_2026_07_20"
    )
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def test_stage2f_artifacts_and_reconstructed_bindings_are_hash_exact() -> None:
    manifest = json.loads(_stage2f_manifest_text())
    decision = json.loads(_DECISION.read_text(encoding="utf-8"))
    evidence = json.loads(_MAPPING_EVIDENCE.read_text(encoding="utf-8"))
    entry = next(
        candidate
        for candidate in manifest["profiles"]
        if candidate["profile_id"] == decision["profile_id"]
    )

    assert hashlib.sha256(_stage2f_profile_text().encode("utf-8")).hexdigest() == (
        _CURRENT_PROFILE_SHA256
    )
    assert hashlib.sha256(_stage2f_manifest_text().encode("utf-8")).hexdigest() == (
        _STAGE2F_MANIFEST_SHA256
    )
    assert _digest(_PRIOR_DECISION) == _PRIOR_DECISION_SHA256
    assert _digest(_MAPPING_EVIDENCE) == _MAPPING_EVIDENCE_SHA256
    assert _digest(_DECISION) == _DECISION_SHA256

    assert entry["sha256"] == _CURRENT_PROFILE_SHA256
    assert entry["admission_decision_id"] == decision["decision_id"]
    assert entry["capabilities"] == decision["manifest_transition"][
        "current_capabilities"
    ]
    assert decision["prior_admission"]["fixture_sha256"] == (
        _PRIOR_DECISION_SHA256
    )
    assert decision["source_reading_evidence"]["fixture_sha256"] == (
        _MAPPING_EVIDENCE_SHA256
    )
    assert decision["profile_transition"]["current_sha256"] == (
        _CURRENT_PROFILE_SHA256
    )
    assert decision["manifest_transition"]["current_manifest_sha256"] == (
        _STAGE2F_MANIFEST_SHA256
    )
    assert evidence["evidence_id"] == decision["source_reading_evidence"][
        "evidence_id"
    ]


def test_schema3_profile_carries_exact_two_direct_source_mappings() -> None:
    profile = json.loads(_PROFILE.read_text(encoding="utf-8"))
    mapping = profile["lunar_paksha_mapping"]

    assert profile["schema_version"] == 3
    assert mapping["mapping_kind"] == (
        "source_attested_lunar_phase_half_to_profile_paksha"
    )
    assert mapping["entries"] == [
        {
            "lunar_phase_half": "waxing",
            "profile_paksha": "purva",
            "source_locators": ["ia_n16"],
        },
        {
            "lunar_phase_half": "waning",
            "profile_paksha": "amara",
            "source_locators": ["ia_n26"],
        },
    ]
    locators = {
        locator["locator_id"]: locator for locator in profile["source_locators"]
    }
    assert "waxing/Purva" in locators["ia_n16"]["label"]
    assert "waning/Amara" in locators["ia_n26"]["label"]
    assert all(
        "explicit_lunar_phase_half_mapping" in locators[locator_id]["evidence_role"]
        for locator_id in ("ia_n16", "ia_n26")
    )


def test_prior_profile_and_manifest_are_reconstructible_exactly() -> None:
    current_profile = _stage2f_profile_text()
    mapping_block = (
        '  "lunar_paksha_mapping": {\n'
        '    "mapping_kind": "source_attested_lunar_phase_half_to_profile_paksha",\n'
        '    "entries": [\n'
        '      {"lunar_phase_half": "waxing", "profile_paksha": "purva", '
        '"source_locators": ["ia_n16"]},\n'
        '      {"lunar_phase_half": "waning", "profile_paksha": "amara", '
        '"source_locators": ["ia_n26"]}\n'
        '    ]\n'
        '  },\n'
    )
    prior_profile = current_profile.replace(
        '"schema_version": 3', '"schema_version": 2', 1
    ).replace(mapping_block, "", 1)
    prior_profile = prior_profile.replace(
        "IA leaf n16: explicit waxing/Purva mapping, Purva-day weekday "
        "first-EAT verse, and representative prose",
        "IA leaf n16: Purva-day weekday first-EAT verse and representative prose",
        1,
    ).replace(
        "explicit_lunar_phase_half_mapping_and_current_schedule_rule_reading",
        "current_schedule_rule_reading",
        1,
    )
    prior_profile = prior_profile.replace(
        "IA leaf n26: explicit waning/Amara mapping, Amara-day weekday "
        "first-EAT verse, and progression rule",
        "IA leaf n26: Amara-day weekday first-EAT verse and progression rule",
        1,
    ).replace(
        "explicit_lunar_phase_half_mapping_and_current_schedule_rule_reading",
        "current_schedule_rule_reading",
        1,
    )
    assert mapping_block in current_profile
    assert hashlib.sha256(prior_profile.encode("utf-8")).hexdigest() == (
        _PRIOR_PROFILE_SHA256
    )

    current_manifest = _stage2f_manifest_text()
    prior_manifest = current_manifest.replace(
        "2026-07-20T20:06:19Z", "2026-07-20T18:50:02Z", 1
    ).replace(
        _CURRENT_PROFILE_SHA256, _PRIOR_PROFILE_SHA256, 1
    ).replace(
        '        "astronomical_paksha_inference",\n', "", 1
    ).replace(
        "pancha_pakshi_1879_astronomical_paksha_inference_2026_07_20",
        "pancha_pakshi_1879_solar_proportional_current_cell_2026_07_20",
        1,
    )
    assert hashlib.sha256(prior_manifest.encode("utf-8")).hexdigest() == (
        _PRIOR_MANIFEST_SHA256
    )


def test_decision_freezes_source_mapping_and_modern_boundary_roles() -> None:
    decision = json.loads(_DECISION.read_text(encoding="utf-8"))
    computation = decision["computational_object"]
    policy = computation["policy"]

    assert decision["decision_kind"] == (
        "source_mapping_and_modern_astronomical_paksha_inference_admission"
    )
    assert decision["manifest_transition"]["added_capability"] == (
        "astronomical_paksha_inference"
    )
    assert policy["shukla_interval"] == "0_inclusive_180_exclusive"
    assert policy["krishna_interval"] == "180_inclusive_360_exclusive"
    assert policy["boundary_tolerance_degrees"] == 0.0
    assert policy["purva_source_locator_id"] == "ia_n16"
    assert policy["amara_source_locator_id"] == "ia_n26"
    assert decision["boundary_doctrine"]["exact_new_moon_owner"] == (
        "shukla_and_purva"
    )
    assert decision["boundary_doctrine"]["exact_full_moon_owner"] == (
        "krishna_and_amara"
    )
    assert decision["authority_and_provenance"]["numeric_boundary_policy_origin"] == (
        "modern_moira_half_open_policy"
    )
    assert decision["authority_and_provenance"]["source_mapping_scope"] == (
        "named_source_scoped_profile_only"
    )
    assert {
        "schedule selection, materialization, or current-cell selection",
        "automatic insertion of inferred paksha into existing schedule routes",
        "natal Moon, nakshatra, or birth-bird identity",
        "a universal or default Pancha Pakshi canon",
    } <= set(decision["public_nonclaims"])
