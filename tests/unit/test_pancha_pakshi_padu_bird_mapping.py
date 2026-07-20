"""Stage 2H source-scoped Padu-bird mapping contracts."""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import moira._pancha_pakshi as internal
import moira.pancha_pakshi as pakshi


_ROOT = Path(__file__).resolve().parents[2]
_PROFILE_PATH = (
    _ROOT
    / "moira"
    / "data"
    / "pancha_pakshi_bogamuni_chennai_2024_padu_bird_mapping.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_ADMISSION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_bogamuni_2024_padu_bird_mapping_2026_07_20.json"
)
_PRIOR_ADMISSION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_bogamuni_2024_natal_moon_identity_2026_07_20.json"
)
_PROFILE_ID = "bogamuni_chennai_2024_padu_bird_mapping"
_DECISION_ID = "pancha_pakshi_bogamuni_2024_padu_bird_mapping_2026_07_20"
_CAPABILITIES = (pakshi.PanchaPakshiCapability.PADU_BIRD_MAPPING,)
_PROFILE_SHA256 = (
    "5de0d1e28d47fad8be6a2a1ab648f2ed71eaf742be2775d166ea44981e96ff10"
)
_MANIFEST_SHA256 = (
    "eae9fc471da08eccf24515ef12cdaf59330aa1b7ad7f9d43432c7a1482704a03"
)
_ADMISSION_SHA256 = (
    "9ea7c871643bb8fc68d420223d0090ca91699154c761c67ccaf9201f401906cd"
)
_PRIOR_ADMISSION_SHA256 = (
    "3da998bc78c6c1fc4ec1c71629dc6b3872725ef25f73965474d5e894deec1575"
)


def _canonical_bytes(path: Path) -> bytes:
    text = path.read_bytes().decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _digest(path: Path) -> str:
    return hashlib.sha256(_canonical_bytes(path)).hexdigest()


def _stage2h_manifest_bytes() -> bytes:
    """Project the append-only live manifest back to Stage 2H exactly."""

    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["generated_at_utc"] = "2026-07-20T22:42:10Z"
    schedule_entry = next(
        entry
        for entry in manifest["profiles"]
        if entry["profile_id"]
        == "agastya_madras_1879_akshara_fixed_clock"
    )
    schedule_entry["capabilities"].remove("first_eat_bird_mapping")
    schedule_entry["admission_decision_id"] = (
        "pancha_pakshi_1879_astronomical_paksha_inference_2026_07_20"
    )
    return (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def _document() -> dict:
    return json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))


def _parse(document: dict, *, capabilities=_CAPABILITIES):
    return internal._parse_padu_bird_profile_document(
        document,
        admission_status=pakshi.PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC,
        default_selection_allowed=False,
        capabilities=capabilities,
        admission_decision_id=_DECISION_ID,
    )


def test_stage2h_profile_is_separate_hash_verified_and_source_scoped() -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)

    assert isinstance(profile, internal.PanchaPakshiPaduBirdProfile)
    assert profile.product_kind == "padu_bird_mapping"
    assert profile.capabilities == _CAPABILITIES
    assert profile.default_selection_allowed is False
    assert profile.assembly_policy == (
        "paksha_stanzas_govern_repeated_combined_table_confirms"
    )
    assert profile.source.archive_pdf_source_status == "internet_archive_original"
    assert profile.source.archive_pdf_md5 == "abe489a832ac38a0270335b7429776f3"
    assert profile.source.locally_verified_pdf_sha256 == (
        "035eab41f62cf078180c03e99ec9eacf8edf2d2dc6d3dc31b37e6a6dfdb09990"
    )
    assert len(profile.padu_bird_rules) == 14
    assert len(profile.source_locators) == 4
    assert profile.research_conflict_ledger == ()


def test_stage2h_admission_fixture_chains_stage2g_and_binds_exact_hashes() -> None:
    decision = json.loads(_ADMISSION_PATH.read_text(encoding="utf-8"))

    assert _digest(_PROFILE_PATH) == _PROFILE_SHA256
    assert hashlib.sha256(_stage2h_manifest_bytes()).hexdigest() == (
        _MANIFEST_SHA256
    )
    assert _digest(_ADMISSION_PATH) == _ADMISSION_SHA256
    assert _digest(_PRIOR_ADMISSION_PATH) == _PRIOR_ADMISSION_SHA256
    assert decision["decision_id"] == _DECISION_ID
    assert decision["prior_admission"] == {
        "decision_id": (
            "pancha_pakshi_bogamuni_2024_natal_moon_identity_2026_07_20"
        ),
        "fixture_path": (
            "tests/fixtures/"
            "pancha_pakshi_bogamuni_2024_natal_moon_identity_2026_07_20.json"
        ),
        "fixture_sha256": _PRIOR_ADMISSION_SHA256,
        "relationship": "append_only_new_profile_no_mutation_or_implicit_composition",
    }
    assert decision["profile_binding"] == {
        "path": (
            "moira/data/"
            "pancha_pakshi_bogamuni_chennai_2024_padu_bird_mapping.json"
        ),
        "sha256": _PROFILE_SHA256,
        "admission_status": "source_scoped_public",
        "product_kind": "padu_bird_mapping",
        "default_selection_allowed": False,
        "capabilities": ["padu_bird_mapping"],
    }
    assert decision["manifest_binding"] == {
        "path": "moira/data/pancha_pakshi_manifest.json",
        "sha256": _MANIFEST_SHA256,
        "hash_canonicalization": (
            "UTF-8 text with CRLF and CR normalized to LF"
        ),
        "profile_entry_decision_id": _DECISION_ID,
    }
    assert decision["validation_evidence"]["exact_source_cells"] == 14


def test_all_14_padu_cells_are_exact_complete_and_bind_repeated_evidence() -> None:
    purva = (
        pakshi.PanchaPakshiBird.OWL,
        pakshi.PanchaPakshiBird.CROW,
        pakshi.PanchaPakshiBird.COCK,
        pakshi.PanchaPakshiBird.PEACOCK,
        pakshi.PanchaPakshiBird.VULTURE,
        pakshi.PanchaPakshiBird.OWL,
        pakshi.PanchaPakshiBird.VULTURE,
    )
    amara = (
        pakshi.PanchaPakshiBird.CROW,
        pakshi.PanchaPakshiBird.OWL,
        pakshi.PanchaPakshiBird.VULTURE,
        pakshi.PanchaPakshiBird.PEACOCK,
        pakshi.PanchaPakshiBird.COCK,
        pakshi.PanchaPakshiBird.PEACOCK,
        pakshi.PanchaPakshiBird.COCK,
    )

    results = []
    for profile_paksha, expected_birds, governing_locator_id in (
        (
            pakshi.PanchaPakshiPaksha.PURVA,
            purva,
            "bogar_n52_purva_padu",
        ),
        (
            pakshi.PanchaPakshiPaksha.AMARA,
            amara,
            "bogar_n60_amara_padu",
        ),
    ):
        for weekday, expected_bird in zip(
            pakshi.PanchaPakshiWeekday,
            expected_birds,
            strict=True,
        ):
            mapping = pakshi.pancha_pakshi_padu_bird_mapping(
                _PROFILE_ID,
                profile_paksha=profile_paksha,
                weekday=weekday,
            )
            results.append(mapping)
            assert mapping.bird is expected_bird
            assert tuple(x.locator_id for x in mapping.source_locators) == (
                governing_locator_id,
                "bogar_n157_combined_padu_table",
                "bogar_n158_combined_padu_commentary",
            )
            assert mapping.mapping_status == "direct_source_attested"
            assert mapping.source_table_semantics == (
                "profile_paksha_weekday_death_or_inoperative_bird_not_"
                "schedule_rule_activity"
            )
            assert mapping.provenance.astronomical_routing_status == "not_performed"
            assert mapping.provenance.capabilities == _CAPABILITIES

    assert len(results) == 14
    assert len({(x.profile_paksha, x.weekday) for x in results}) == 14


def test_padu_lookup_has_only_explicit_profile_paksha_and_weekday_axes() -> None:
    signature = inspect.signature(pakshi.pancha_pakshi_padu_bird_mapping)

    assert tuple(signature.parameters) == (
        "profile_id",
        "profile_paksha",
        "weekday",
    )
    assert signature.parameters["profile_paksha"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["weekday"].kind is inspect.Parameter.KEYWORD_ONLY
    assert not {
        "half",
        "jd_ut1",
        "jd_utc",
        "latitude",
        "longitude",
        "natal_bird",
        "activity",
        "score",
    } & set(signature.parameters)


def test_padu_vessel_is_immutable_and_validates_against_canonical_table() -> None:
    mapping = pakshi.pancha_pakshi_padu_bird_mapping(
        _PROFILE_ID,
        profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
        weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
    )

    with pytest.raises(FrozenInstanceError):
        mapping.bird = pakshi.PanchaPakshiBird.CROW  # type: ignore[misc]
    with pytest.raises(ValueError, match="canonical source table"):
        replace(mapping, bird=pakshi.PanchaPakshiBird.CROW)
    with pytest.raises(ValueError, match="not canonical"):
        replace(mapping, source_locators=tuple(reversed(mapping.source_locators)))
    with pytest.raises(ValueError, match="source_table_semantics"):
        replace(mapping, source_table_semantics="schedule_rule_activity")
    with pytest.raises(ValueError, match="provenance is not canonical"):
        replace(
            mapping,
            provenance=replace(
                mapping.provenance,
                product_kind="forged_product_kind",
            ),
        )


@pytest.mark.parametrize(
    "mutator",
    (
        lambda d: d["padu_bird_mapping"]["entries"].pop(),
        lambda d: d["padu_bird_mapping"]["entries"][0].__setitem__(
            "bird", "crow"
        ),
        lambda d: d["padu_bird_mapping"]["entries"][0].__setitem__(
            "half", "day"
        ),
        lambda d: d["padu_bird_mapping"].__setitem__(
            "source_table_semantics", "generic_authority_bird"
        ),
        lambda d: d["source"].__setitem__(
            "locally_verified_pdf_sha256", "0" * 64
        ),
        lambda d: d["source_locators"][0].__setitem__(
            "label", "an imprecise page reference"
        ),
        lambda d: d["explicit_omissions"].pop(8),
        lambda d: d["research_conflict_ledger"].append({"invented": True}),
    ),
)
def test_strict_padu_parser_rejects_table_provenance_or_scope_drift(mutator) -> None:
    document = copy.deepcopy(_document())
    mutator(document)

    with pytest.raises(pakshi.PanchaPakshiDataError):
        _parse(document)


def test_padu_parser_rejects_generic_authority_capability() -> None:
    with pytest.raises(pakshi.PanchaPakshiDataError, match="capabilities"):
        _parse(
            _document(),
            capabilities=(pakshi.PanchaPakshiCapability.AUTHORITY_BIRDS,),
        )


@pytest.mark.parametrize(
    ("profile_paksha", "weekday", "error"),
    (
        ("purva", pakshi.PanchaPakshiWeekday.SUNDAY, TypeError),
        (pakshi.PanchaPakshiPaksha.PURVA, "sunday", TypeError),
        (True, pakshi.PanchaPakshiWeekday.SUNDAY, TypeError),
    ),
)
def test_padu_lookup_rejects_untyped_axes(profile_paksha, weekday, error) -> None:
    with pytest.raises(error):
        pakshi.pancha_pakshi_padu_bird_mapping(
            _PROFILE_ID,
            profile_paksha=profile_paksha,
            weekday=weekday,
        )


def test_padu_profile_cannot_enter_other_profile_products() -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)

    with pytest.raises(TypeError, match="PanchaPakshiProfile"):
        internal.generate_pancha_pakshi_schedule(
            profile,
            paksha=pakshi.PanchaPakshiPaksha.PURVA,
            half=pakshi.PanchaPakshiHalf.DAY,
            weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
        )
    with pytest.raises(ValueError, match="does not admit 'nominal_schedule'"):
        pakshi.pancha_pakshi_schedule(
            _PROFILE_ID,
            paksha=pakshi.PanchaPakshiPaksha.PURVA,
            half=pakshi.PanchaPakshiHalf.DAY,
            weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
        )
    with pytest.raises(ValueError, match="does not admit 'nakshatra_bird_mapping'"):
        pakshi.pancha_pakshi_nakshatra_bird_mapping(
            _PROFILE_ID,
            profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
            nakshatra_index=0,
        )
    with pytest.raises(ValueError, match="does not admit 'padu_bird_mapping'"):
        pakshi.pancha_pakshi_padu_bird_mapping(
            "bogamuni_chennai_2024_nakshatra_natal_identity",
            profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
            weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
        )


def test_prior_profile_capabilities_and_authority_omissions_remain_unchanged() -> None:
    schedule = internal.load_pancha_pakshi_profile(
        "agastya_madras_1879_akshara_fixed_clock"
    )
    natal = internal.load_pancha_pakshi_profile(
        "bogamuni_chennai_2024_nakshatra_natal_identity"
    )

    assert pakshi.PanchaPakshiCapability.PADU_BIRD_MAPPING not in schedule.capabilities
    assert pakshi.PanchaPakshiCapability.PADU_BIRD_MAPPING not in natal.capabilities
    assert "authority_birds" in {x.feature for x in schedule.explicit_omissions}
    assert "authority_birds" in {x.feature for x in natal.explicit_omissions}
    assert schedule.product_kind == "aksara_prasna_operating_schedule"
    assert natal.product_kind == "natal_moon_bird_identity"
