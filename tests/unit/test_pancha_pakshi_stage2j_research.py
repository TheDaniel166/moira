"""Stage 2J research-only vinadi recovery and non-admission guards."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path

import moira
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.vedic as vedic
from moira_server.routers import pancha_pakshi as router_module


_ROOT = Path(__file__).resolve().parents[2]
_DECISION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_vinadi_stage2j_research_2026_07_21.json"
)
_PRIOR_DECISION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_1879_first_eat_bird_mapping_2026_07_20.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "d04ed0f3716fe605dc5d8172114dc759b30c4e87be968eebc36e35a23d789243"
)
_PRIOR_DECISION_SHA256 = (
    "83c9bc0a423c09ccc113007625fee4a7d6b9ee1e890827f71595c96c3f826807"
)
_MANIFEST_SHA256 = (
    "d1aba3757910ded019cb6a2a5d6fb92c2e1ebbea755c26953dff1347834bf0e8"
)


def _digest(path: Path) -> str:
    text = path.read_bytes().decode("utf-8")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _stage2i_manifest_bytes() -> bytes:
    """Project the append-only live manifest back to the Stage 2J baseline."""

    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["generated_at_utc"] = "2026-07-20T23:28:13Z"
    manifest["profiles"] = [
        entry
        for entry in manifest["profiles"]
        if entry["profile_id"]
        != "bogamuni_chennai_2024_sookshma_temporal_selector"
    ]
    manifest["profiles"][0]["sha256"] = (
        "4fe769b6f13c4a719c9d31446dd3fef413eca5d3ce1f56340aada9f99b0dce64"
    )
    return (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def test_stage2j_decision_is_hash_exact_and_preserves_stage2i() -> None:
    decision = json.loads(_DECISION_PATH.read_text(encoding="utf-8"))

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PRIOR_DECISION_PATH) == _PRIOR_DECISION_SHA256
    assert hashlib.sha256(_stage2i_manifest_bytes()).hexdigest() == (
        _MANIFEST_SHA256
    )
    assert decision["admission_status"] == "research_only"
    assert decision["prior_public_state"] == {
        "stage": "2I",
        "manifest_path": "moira/data/pancha_pakshi_manifest.json",
        "manifest_sha256": _MANIFEST_SHA256,
        "decision_path": (
            "tests/fixtures/"
            "pancha_pakshi_1879_first_eat_bird_mapping_2026_07_20.json"
        ),
        "decision_sha256": _PRIOR_DECISION_SHA256,
        "manifest_changed": False,
    }
    assert set(decision["admission_decision"].values()) == {False}


def test_recovered_axis_is_explicit_and_not_temporally_inferred() -> None:
    decision = json.loads(_DECISION_PATH.read_text(encoding="utf-8"))
    recovered = decision["recovered_computational_object"]
    ambiguity = decision["ambiguity_policy"]

    assert recovered["source_owned_object"] == (
        "five_position_vinadi_ordinal_axis_under_each_activity"
    )
    assert recovered["parent_activities"] == [
        "eat",
        "walk",
        "rule",
        "sleep",
        "die",
    ]
    assert recovered["ordinal_values"] == [1, 2, 3, 4, 5]
    assert recovered["routing_status"] == (
        "unbound_between_uromarisi_ordinals_and_separate_selector_doctrines"
    )
    assert recovered["timing_formula_status"] == (
        "not_stated_in_inspected_uromarisi_governing_pages_but_two_separate_"
        "comparator_formulas_are_attested"
    )
    assert recovered["equal_subdivision_status"] == (
        "attested_only_as_separate_eka_sookshma_editorial_policy"
    )
    assert ambiguity["permitted_research_input"] == "explicit_ordinal_label_only"
    assert ambiguity["automatic_clock_to_uromarisi_ordinal_routing"] == "forbidden"
    assert ambiguity["implicit_selector_or_default"] == "forbidden"
    assert ambiguity["human_language_reviewer_dependency"] == "none"

    witnesses = decision["witnesses"]
    assert [witness["pdf_sha256"] for witness in witnesses] == [
        "dbd12d7e26f39ca7f9650a17311b5483eb478844144544a2cbb11aac7c3d6243",
        "51b4b34890412fd57011aebe0c1ab22ab1800e5035a84bbbb9330ea0f6597741",
        "e2ab7a64d4d4e540c30bc464c12923e6f14e93fbbe15d73e459e9c62a5815da0",
        "035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990",
    ]
    assert {locator["pdf_page"] for locator in witnesses[0]["locators"]} == {
        5,
        88,
        89,
    }
    assert {locator["pdf_page"] for locator in witnesses[1]["locators"]} == {
        115,
        116,
    }
    assert {locator["pdf_page"] for locator in witnesses[2]["locators"]} == {
        115,
        116,
        117,
    }
    assert {locator["pdf_page"] for locator in witnesses[3]["locators"]} == {
        157,
        158,
        169,
    }
    assert decision["cross_edition_finding"]["textual_lineage_independence"] == (
        "not_established"
    )


def test_temporal_selector_candidates_are_exact_distinct_and_unbound() -> None:
    decision = json.loads(_DECISION_PATH.read_text(encoding="utf-8"))
    findings = decision["temporal_selector_findings"]
    candidates = {
        candidate["provisional_policy_id"]: candidate
        for candidate in findings["separate_source_attested_candidates"]
    }

    weighted = candidates["bogamuni_2024_weighted_sookshma_samam_v1"]
    assert weighted["activity_duration_nazhigai"] == {
        "eat": "3/2",
        "walk": "5/4",
        "rule": "2",
        "sleep": "3/4",
        "die": "1/2",
    }
    assert sum(
        Fraction(value) for value in weighted["activity_duration_nazhigai"].values()
    ) == Fraction(6)
    assert weighted["duration_sum_nazhigai"] == "6"

    equal = candidates["bogamuni_2024_eka_sookshma_equal_fifths_v1"]
    assert equal["partition_rule"] == "five_equal_half_open_parts"
    assert equal["exact_boundary_formula"] == (
        "start_plus_k_times_span_over_5_for_k_0_through_5"
    )
    assert "not interchangeable" in findings["conflict"]
    assert findings["uromarisi_composition_status"] == (
        "forbidden_without_a_separate_explicit_cross_witness_or_modern_"
        "composition_decision"
    )
    assert findings["recommended_next_surface"] == (
        "two_explicit_policy_selectors_without_default_and_without_outcome_"
        "interpretation"
    )


def test_vinadi_remains_absent_from_runtime_and_public_surfaces() -> None:
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_tokens = json.dumps(manifest, sort_keys=True).lower()

    assert "vinadi" not in manifest_tokens
    for surface in (moira, pakshi, vedic, facade.Moira):
        assert not [name for name in dir(surface) if "vinadi" in name.lower()]
    assert all("vinadi" not in route.path.lower() for route in router_module.router.routes)
