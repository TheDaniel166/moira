"""Public source-scoped Pancha Pakshi engine contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

import moira
import moira.facade as facade
import moira.pancha_pakshi as pancha_pakshi
import moira.vedic as vedic
from moira.pancha_pakshi import (
    PanchaPakshiActivity,
    PanchaPakshiAdmissionStatus,
    PanchaPakshiBird,
    PanchaPakshiCapability,
    PanchaPakshiHalf,
    PanchaPakshiPaksha,
    PanchaPakshiRelation,
    PanchaPakshiWeekday,
    available_pancha_pakshi_profiles,
    pancha_pakshi_directed_relationship,
    pancha_pakshi_identity_from_initial_vowel,
    pancha_pakshi_profile_info,
    pancha_pakshi_schedule,
)


_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_ADMISSION = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "pancha_pakshi_1879_public_admission_2026_07_20.json"
)
_IDENTITY_SYMBOLS = (
    "A",
    "\u0b85",
    "I",
    "\u0b87",
    "U",
    "\u0b89",
    "E",
    "\u0b8e",
    "O",
    "\u0b92",
)


def _fraction_pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _runtime_semantic_projection() -> dict[str, object]:
    sample = pancha_pakshi_schedule(
        _PROFILE_ID,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )
    night = pancha_pakshi_schedule(
        _PROFILE_ID,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.NIGHT,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )
    projection: dict[str, object] = {
        "identity": [
            [
                symbol,
                pancha_pakshi_identity_from_initial_vowel(
                    _PROFILE_ID, symbol
                ).bird.value,
            ]
            for symbol in _IDENTITY_SYMBOLS
        ],
        "temporal_model": {
            "model_kind": sample.temporal_model_kind,
            "day_span_nazhigai": _fraction_pair(sample.span_nazhigai),
            "night_span_nazhigai": _fraction_pair(night.span_nazhigai),
            "samam_count_per_half": len(
                {cell.samam_index for cell in sample.cells}
            ),
            "samam_span_nazhigai": _fraction_pair(
                sample.samam_span_nazhigai
            ),
        },
        "durations": [
            [
                activity.value,
                _fraction_pair(
                    next(
                        cell.duration_nazhigai
                        for cell in sample.cells
                        if cell.activity is activity
                    )
                ),
            ]
            for activity in PanchaPakshiActivity
        ],
        "schedules": [],
        "relationships": [
            [
                subject.value,
                target.value,
                pancha_pakshi_directed_relationship(
                    _PROFILE_ID, subject, target
                ).relation.value,
            ]
            for subject in PanchaPakshiBird
            for target in PanchaPakshiBird
            if subject is not target
        ],
    }
    schedules: list[object] = []
    for paksha in PanchaPakshiPaksha:
        for half in PanchaPakshiHalf:
            for weekday in PanchaPakshiWeekday:
                schedule = pancha_pakshi_schedule(
                    _PROFILE_ID,
                    paksha=paksha,
                    half=half,
                    weekday=weekday,
                )
                schedules.append(
                    [
                        paksha.value,
                        half.value,
                        weekday.value,
                        schedule.generator_id,
                        schedule.first_eat_bird.value,
                        [
                            [
                                cell.samam_index,
                                cell.sequence_index,
                                cell.bird.value,
                                cell.activity.value,
                                _fraction_pair(cell.start_nazhigai),
                                _fraction_pair(cell.end_nazhigai),
                                _fraction_pair(cell.duration_nazhigai),
                            ]
                            for cell in schedule.cells
                        ],
                    ]
                )
    projection["schedules"] = schedules
    return projection


def test_public_registry_is_source_scoped_and_has_no_default() -> None:
    assert available_pancha_pakshi_profiles() == (
        type(available_pancha_pakshi_profiles()[0])(
            profile_id=_PROFILE_ID,
            admission_status=PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC,
            product_kind="aksara_prasna_operating_schedule",
            default_selection_allowed=False,
            capabilities=(
                PanchaPakshiCapability.AKSARA_IDENTITY,
                PanchaPakshiCapability.NOMINAL_SCHEDULE,
                PanchaPakshiCapability.FIRST_EAT_BIRD_MAPPING,
                PanchaPakshiCapability.DIRECTED_RELATIONSHIPS,
                PanchaPakshiCapability.ASTRONOMICAL_CONTEXT,
                PanchaPakshiCapability.ASTRONOMICAL_PAKSHA_INFERENCE,
                PanchaPakshiCapability.FIXED_CLOCK_MATERIALIZATION,
                PanchaPakshiCapability.FIXED_CLOCK_CURRENT_CELL_SELECTION,
                PanchaPakshiCapability.SOLAR_PROPORTIONAL_MATERIALIZATION,
                (
                    PanchaPakshiCapability
                    .SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION
                ),
            ),
            admission_decision_id=(
                "pancha_pakshi_1879_first_eat_bird_mapping_2026_07_20"
            ),
        ),
        type(available_pancha_pakshi_profiles()[0])(
            profile_id="bogamuni_chennai_2024_nakshatra_natal_identity",
            admission_status=PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC,
            product_kind="natal_moon_bird_identity",
            default_selection_allowed=False,
            capabilities=(
                PanchaPakshiCapability.NAKSHATRA_BIRD_MAPPING,
                PanchaPakshiCapability.NATAL_IDENTITY,
            ),
            admission_decision_id=(
                "pancha_pakshi_bogamuni_2024_natal_moon_identity_2026_07_20"
            ),
        ),
        type(available_pancha_pakshi_profiles()[0])(
            profile_id="bogamuni_chennai_2024_padu_bird_mapping",
            admission_status=PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC,
            product_kind="padu_bird_mapping",
            default_selection_allowed=False,
            capabilities=(PanchaPakshiCapability.PADU_BIRD_MAPPING,),
            admission_decision_id=(
                "pancha_pakshi_bogamuni_2024_padu_bird_mapping_2026_07_20"
            ),
        ),
    )

    with pytest.raises(TypeError):
        pancha_pakshi_profile_info()  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="no default canon"):
        pancha_pakshi_profile_info("")


def test_stage2e_public_exports_share_identity_and_facade_is_bound() -> None:
    names = (
        "PanchaPakshiSolarProportionalCurrentCellSelection",
        "PanchaPakshiSolarProportionalCurrentCellSelectionPolicy",
        "pancha_pakshi_solar_proportional_current_cell_at",
    )
    for name in names:
        expected = getattr(pancha_pakshi, name)
        assert getattr(moira, name) is expected
        assert getattr(facade, name) is expected
        assert getattr(vedic, name) is expected

    assert hasattr(
        moira.Moira,
        "pancha_pakshi_solar_proportional_current_cell",
    )


def test_public_gate_rejects_a_research_only_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import moira._pancha_pakshi as internal

    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    research_profile = replace(
        profile,
        admission_status=PanchaPakshiAdmissionStatus.RESEARCH_ONLY,
    )
    monkeypatch.setattr(
        internal,
        "load_pancha_pakshi_profile",
        lambda profile_id: research_profile,
    )

    with pytest.raises(ValueError, match="is not publicly admitted"):
        pancha_pakshi_profile_info(_PROFILE_ID)


def test_public_gate_rejects_an_unavailable_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import moira._pancha_pakshi as internal

    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    identity_only_profile = replace(
        profile,
        capabilities=(PanchaPakshiCapability.AKSARA_IDENTITY,),
    )
    monkeypatch.setattr(
        internal,
        "load_pancha_pakshi_profile",
        lambda profile_id: identity_only_profile,
    )

    with pytest.raises(ValueError, match="does not admit 'nominal_schedule'"):
        pancha_pakshi_schedule(
            _PROFILE_ID,
            paksha=PanchaPakshiPaksha.PURVA,
            half=PanchaPakshiHalf.DAY,
            weekday=PanchaPakshiWeekday.SUNDAY,
        )


def test_public_vessels_are_immutable_and_carry_scope_and_omissions() -> None:
    info = pancha_pakshi_profile_info(_PROFILE_ID)
    provenance = info.provenance

    assert provenance.profile_id == _PROFILE_ID
    assert provenance.admission_status is PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC
    assert provenance.default_selection_allowed is False
    assert provenance.astronomical_routing_status == "not_performed"
    assert provenance.source.witness_id == "dli.rmrl.000451_images"
    assert provenance.capabilities == (
        PanchaPakshiCapability.AKSARA_IDENTITY,
        PanchaPakshiCapability.NOMINAL_SCHEDULE,
        PanchaPakshiCapability.FIRST_EAT_BIRD_MAPPING,
        PanchaPakshiCapability.DIRECTED_RELATIONSHIPS,
        PanchaPakshiCapability.ASTRONOMICAL_CONTEXT,
        PanchaPakshiCapability.ASTRONOMICAL_PAKSHA_INFERENCE,
        PanchaPakshiCapability.FIXED_CLOCK_MATERIALIZATION,
        PanchaPakshiCapability.FIXED_CLOCK_CURRENT_CELL_SELECTION,
        PanchaPakshiCapability.SOLAR_PROPORTIONAL_MATERIALIZATION,
        PanchaPakshiCapability.SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION,
    )
    assert {omission.feature for omission in provenance.declared_omissions} == {
        "authority_birds",
        "natal_mapping",
        "scoring",
        "cross_witness_normalized_relationship_policy",
        "vinadi",
        "seasonal_scaling",
    }
    assert all(omission.status == "omitted" for omission in provenance.declared_omissions)
    assert all(
        "research profile" not in omission.reason
        for omission in provenance.declared_omissions
    )
    assert all(locator.witness_id == provenance.source.witness_id for locator in info.source_locators)

    with pytest.raises(FrozenInstanceError):
        provenance.product_kind = "invented"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        info.title = "invented"  # type: ignore[misc]


def test_public_identity_and_relationship_are_source_located_and_directed() -> None:
    identity = pancha_pakshi_identity_from_initial_vowel(_PROFILE_ID, "A")
    assert identity.bird is PanchaPakshiBird.VULTURE
    assert identity.is_natal_moon_identity is False
    assert {locator.locator_id for locator in identity.source_locators} == {
        "ia_n5",
        "ia_n10",
    }
    assert identity.provenance.default_selection_allowed is False

    owl_to_peacock = pancha_pakshi_directed_relationship(
        _PROFILE_ID, PanchaPakshiBird.OWL, PanchaPakshiBird.PEACOCK
    )
    peacock_to_owl = pancha_pakshi_directed_relationship(
        _PROFILE_ID, PanchaPakshiBird.PEACOCK, PanchaPakshiBird.OWL
    )
    assert owl_to_peacock.relation is PanchaPakshiRelation.FRIEND
    assert peacock_to_owl.relation is PanchaPakshiRelation.ENEMY
    assert owl_to_peacock.is_reciprocal_inference is False
    assert peacock_to_owl.is_reciprocal_inference is False
    assert {locator.locator_id for locator in owl_to_peacock.source_locators} == {
        "ia_n52"
    }

    with pytest.raises(ValueError, match="self-relation undefined"):
        pancha_pakshi_directed_relationship(
            _PROFILE_ID, PanchaPakshiBird.CROW, PanchaPakshiBird.CROW
        )


def test_all_public_nominal_schedules_are_exact_complete_and_contiguous() -> None:
    pair_product = {
        (bird, activity)
        for bird in PanchaPakshiBird
        for activity in PanchaPakshiActivity
    }
    schedules = []
    for paksha in PanchaPakshiPaksha:
        for half in PanchaPakshiHalf:
            for weekday in PanchaPakshiWeekday:
                schedule = pancha_pakshi_schedule(
                    _PROFILE_ID,
                    paksha=paksha,
                    half=half,
                    weekday=weekday,
                )
                schedules.append(schedule)
                assert schedule.span_nazhigai == Fraction(30)
                assert schedule.samam_span_nazhigai == Fraction(6)
                assert len(schedule.cells) == 25
                assert {(cell.bird, cell.activity) for cell in schedule.cells} == pair_product
                assert schedule.cells[0].start_nazhigai == Fraction()
                assert schedule.cells[-1].end_nazhigai == Fraction(30)
                assert all(
                    left.end_nazhigai == right.start_nazhigai
                    for left, right in zip(schedule.cells, schedule.cells[1:])
                )
                assert all(cell.source_locators for cell in schedule.cells)

    assert len(schedules) == 28
    assert sum(len(schedule.cells) for schedule in schedules) == 700


def test_admission_fixture_names_the_semantic_projection_digest_algorithm() -> None:
    decision = json.loads(_ADMISSION.read_text(encoding="utf-8"))
    projection = decision["semantic_projection"]

    assert projection["algorithm_id"] == (
        "pancha_pakshi_computational_semantics_v1"
    )
    assert projection["sha256"] == (
        "7ac6da0aa5a556d1e510f87b73fff767be56749bf263e0722c925eeed01bafec"
    )
    assert len(projection["sha256"]) == hashlib.sha256().digest_size * 2
    assert projection["identity_symbol_count"] == 10
    assert projection["schedule_count"] == 28
    assert projection["schedule_cell_count"] == 700
    assert projection["directed_relationship_count"] == 20

    payload = json.dumps(
        _runtime_semantic_projection(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert hashlib.sha256(payload).hexdigest() == projection["sha256"]
