"""Kernel-free tests for the private Pancha Pakshi research foundation."""

from __future__ import annotations

from fractions import Fraction

import pytest

import moira
from moira import Moira
from moira._pancha_pakshi import (
    PanchaPakshiActivity,
    PanchaPakshiAdmissionStatus,
    PanchaPakshiBird,
    PanchaPakshiCapability,
    PanchaPakshiHalf,
    PanchaPakshiPaksha,
    PanchaPakshiRelation,
    PanchaPakshiWeekday,
    available_pancha_pakshi_profiles,
    generate_amara_day_schedule,
    generate_amara_night_schedule,
    generate_pancha_pakshi_schedule,
    generate_purva_day_schedule,
    generate_purva_night_schedule,
    load_pancha_pakshi_profile,
    pancha_pakshi_directed_relationship,
    pancha_pakshi_identity_from_initial_vowel,
)


PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"


@pytest.fixture(scope="module")
def profile():
    return load_pancha_pakshi_profile(PROFILE_ID)


def test_profile_is_explicitly_named_source_scoped_and_never_default(profile) -> None:
    assert available_pancha_pakshi_profiles() == (
        type(available_pancha_pakshi_profiles()[0])(
            profile_id=PROFILE_ID,
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
        type(available_pancha_pakshi_profiles()[0])(
            profile_id="bogamuni_chennai_2024_sookshma_temporal_selector",
            admission_status=PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC,
            product_kind="sookshma_temporal_selector",
            default_selection_allowed=False,
            capabilities=(
                PanchaPakshiCapability.SOOKSHMA_TEMPORAL_SELECTION,
            ),
            admission_decision_id=(
                "pancha_pakshi_bogamuni_2024_sookshma_temporal_selector_"
                "2026_07_21"
            ),
        ),
    )
    assert profile.profile_id == PROFILE_ID
    assert profile.admission_status is PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC
    assert profile.product_kind == "aksara_prasna_operating_schedule"
    assert profile.default_selection_allowed is False
    assert profile.capabilities == (
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
    assert profile.derivation_status == (
        "machine_reconciled_source_assignment_with_declared_uncertainty"
    )
    assert profile.assembly_policy == (
        "resolved_grid_axes_assign_birds_explicit_prose_and_verse_govern_"
        "chronology"
    )

    with pytest.raises(ValueError, match="no default canon"):
        load_pancha_pakshi_profile("")
    with pytest.raises(ValueError, match="no default canon"):
        load_pancha_pakshi_profile("unidentified_blended_canon")


def test_private_loader_remains_out_of_the_public_engine() -> None:
    assert not hasattr(moira, "load_pancha_pakshi_profile")
    assert not hasattr(moira, "PanchaPakshiProfile")
    assert hasattr(moira, "pancha_pakshi_schedule")
    assert hasattr(Moira, "pancha_pakshi_schedule")


def test_akshara_identity_is_not_a_natal_moon_mapping(profile) -> None:
    expected = {
        "A": PanchaPakshiBird.VULTURE,
        "அ": PanchaPakshiBird.VULTURE,
        "I": PanchaPakshiBird.OWL,
        "இ": PanchaPakshiBird.OWL,
        "U": PanchaPakshiBird.CROW,
        "உ": PanchaPakshiBird.CROW,
        "E": PanchaPakshiBird.COCK,
        "எ": PanchaPakshiBird.COCK,
        "O": PanchaPakshiBird.PEACOCK,
        "ஒ": PanchaPakshiBird.PEACOCK,
    }
    for symbol, bird in expected.items():
        identity = pancha_pakshi_identity_from_initial_vowel(profile, symbol)
        assert identity.identity_kind == "aksara_query_or_name_initial_vowel"
        assert identity.bird is bird
        assert identity.is_natal_moon_identity is False
        assert {locator.locator_id for locator in identity.source_locators} == {
            "ia_n5",
            "ia_n10",
        }

    assert pancha_pakshi_identity_from_initial_vowel(profile, "a").bird is (
        PanchaPakshiBird.VULTURE
    )
    with pytest.raises(ValueError, match="not explicitly mapped"):
        pancha_pakshi_identity_from_initial_vowel(profile, "ஆ")
    with pytest.raises(ValueError, match="one explicitly listed vowel"):
        pancha_pakshi_identity_from_initial_vowel(profile, "Arun")


def test_uniform_durations_are_exact_fractions(profile) -> None:
    assert {
        rule.activity: rule.duration_nazhigai for rule in profile.duration_rules
    } == {
        PanchaPakshiActivity.EAT: Fraction(5, 4),
        PanchaPakshiActivity.WALK: Fraction(3, 2),
        PanchaPakshiActivity.RULE: Fraction(2, 1),
        PanchaPakshiActivity.SLEEP: Fraction(3, 4),
        PanchaPakshiActivity.DIE: Fraction(1, 2),
    }
    assert sum(
        (rule.duration_nazhigai for rule in profile.duration_rules), Fraction()
    ) == Fraction(6)
    assert profile.temporal_model.day_span_nazhigai == Fraction(30)
    assert profile.temporal_model.night_span_nazhigai == Fraction(30)
    assert profile.temporal_model.samam_span_nazhigai == Fraction(6)


@pytest.mark.parametrize(
    ("builder", "expected_first_samam"),
    (
        (
            generate_purva_day_schedule,
            (
                (PanchaPakshiBird.VULTURE, PanchaPakshiActivity.EAT),
                (PanchaPakshiBird.OWL, PanchaPakshiActivity.WALK),
                (PanchaPakshiBird.CROW, PanchaPakshiActivity.RULE),
                (PanchaPakshiBird.COCK, PanchaPakshiActivity.SLEEP),
                (PanchaPakshiBird.PEACOCK, PanchaPakshiActivity.DIE),
            ),
        ),
        (
            generate_purva_night_schedule,
            (
                (PanchaPakshiBird.CROW, PanchaPakshiActivity.EAT),
                (PanchaPakshiBird.OWL, PanchaPakshiActivity.RULE),
                (PanchaPakshiBird.VULTURE, PanchaPakshiActivity.DIE),
                (PanchaPakshiBird.PEACOCK, PanchaPakshiActivity.WALK),
                (PanchaPakshiBird.COCK, PanchaPakshiActivity.SLEEP),
            ),
        ),
        (
            generate_amara_day_schedule,
            (
                (PanchaPakshiBird.COCK, PanchaPakshiActivity.EAT),
                (PanchaPakshiBird.OWL, PanchaPakshiActivity.DIE),
                (PanchaPakshiBird.PEACOCK, PanchaPakshiActivity.SLEEP),
                (PanchaPakshiBird.CROW, PanchaPakshiActivity.RULE),
                (PanchaPakshiBird.VULTURE, PanchaPakshiActivity.WALK),
            ),
        ),
        (
            generate_amara_night_schedule,
            (
                (PanchaPakshiBird.VULTURE, PanchaPakshiActivity.EAT),
                (PanchaPakshiBird.PEACOCK, PanchaPakshiActivity.SLEEP),
                (PanchaPakshiBird.COCK, PanchaPakshiActivity.WALK),
                (PanchaPakshiBird.CROW, PanchaPakshiActivity.DIE),
                (PanchaPakshiBird.OWL, PanchaPakshiActivity.RULE),
            ),
        ),
    ),
)
def test_four_source_generators_materialize_current_profile_sunday_rows(
    profile, builder, expected_first_samam
) -> None:
    schedule = builder(profile, PanchaPakshiWeekday.SUNDAY)

    assert tuple((cell.bird, cell.activity) for cell in schedule.cells[:5]) == (
        expected_first_samam
    )
    assert len(schedule.cells) == 25
    assert schedule.cells[0].start_nazhigai == 0
    assert schedule.cells[-1].end_nazhigai == 30
    assert schedule.span_nazhigai == 30
    assert all(cell.source_locators for cell in schedule.cells)
    assert all(
        cell.assembly_policy
        == (
            "resolved_grid_axes_assign_birds_explicit_prose_and_verse_govern_"
            "chronology"
        )
        for cell in schedule.cells
    )
    assert all(
        "ia_n6" in {locator.locator_id for locator in cell.source_locators}
        for cell in schedule.cells
    )


def test_purva_night_matches_source_owned_weekday_and_samam_oracle(profile) -> None:
    chronology = (
        PanchaPakshiActivity.EAT,
        PanchaPakshiActivity.RULE,
        PanchaPakshiActivity.DIE,
        PanchaPakshiActivity.WALK,
        PanchaPakshiActivity.SLEEP,
    )
    assignment_rows = {
        "A": (
            PanchaPakshiBird.CROW,
            PanchaPakshiBird.OWL,
            PanchaPakshiBird.VULTURE,
            PanchaPakshiBird.PEACOCK,
            PanchaPakshiBird.COCK,
        ),
        "B": (
            PanchaPakshiBird.COCK,
            PanchaPakshiBird.CROW,
            PanchaPakshiBird.OWL,
            PanchaPakshiBird.VULTURE,
            PanchaPakshiBird.PEACOCK,
        ),
        "C": (
            PanchaPakshiBird.PEACOCK,
            PanchaPakshiBird.COCK,
            PanchaPakshiBird.CROW,
            PanchaPakshiBird.OWL,
            PanchaPakshiBird.VULTURE,
        ),
        "D": (
            PanchaPakshiBird.VULTURE,
            PanchaPakshiBird.PEACOCK,
            PanchaPakshiBird.COCK,
            PanchaPakshiBird.CROW,
            PanchaPakshiBird.OWL,
        ),
        "E": (
            PanchaPakshiBird.OWL,
            PanchaPakshiBird.VULTURE,
            PanchaPakshiBird.PEACOCK,
            PanchaPakshiBird.COCK,
            PanchaPakshiBird.CROW,
        ),
    }
    weekday_rows = {
        PanchaPakshiWeekday.SUNDAY: ("A", "B", "C", "D", "E"),
        PanchaPakshiWeekday.MONDAY: ("B", "C", "D", "E", "A"),
        PanchaPakshiWeekday.TUESDAY: ("A", "B", "C", "D", "E"),
        PanchaPakshiWeekday.WEDNESDAY: ("B", "C", "D", "E", "A"),
        PanchaPakshiWeekday.THURSDAY: ("C", "D", "E", "A", "B"),
        PanchaPakshiWeekday.FRIDAY: ("D", "E", "A", "B", "C"),
        PanchaPakshiWeekday.SATURDAY: ("E", "A", "B", "C", "D"),
    }

    generator = profile.generator(
        PanchaPakshiPaksha.PURVA, PanchaPakshiHalf.NIGHT
    )
    assert generator.eat_step_per_samam == 1
    assert {
        activity: generator.offset_for(activity)
        for activity in PanchaPakshiActivity
    } == {
        PanchaPakshiActivity.EAT: 0,
        PanchaPakshiActivity.WALK: 2,
        PanchaPakshiActivity.RULE: -1,
        PanchaPakshiActivity.SLEEP: 1,
        PanchaPakshiActivity.DIE: -2,
    }
    assert generator.chronological_activities == chronology

    for weekday, expected_rows in weekday_rows.items():
        schedule = generate_purva_night_schedule(profile, weekday)
        for samam_index, row_id in enumerate(expected_rows, start=1):
            samam = tuple(
                cell for cell in schedule.cells if cell.samam_index == samam_index
            )
            assert tuple(cell.activity for cell in samam) == chronology
            assert tuple(cell.bird for cell in samam) == assignment_rows[row_id]


def test_all_context_weekday_schedules_are_complete_and_contiguous(profile) -> None:
    expected_pairs = {
        (bird, activity)
        for bird in PanchaPakshiBird
        for activity in PanchaPakshiActivity
    }
    for paksha in PanchaPakshiPaksha:
        for half in PanchaPakshiHalf:
            for weekday in PanchaPakshiWeekday:
                schedule = generate_pancha_pakshi_schedule(
                    profile, paksha=paksha, half=half, weekday=weekday
                )
                assert len(schedule.cells) == 25
                assert {
                    (cell.bird, cell.activity) for cell in schedule.cells
                } == expected_pairs
                assert all(
                    left.end_nazhigai == right.start_nazhigai
                    for left, right in zip(schedule.cells, schedule.cells[1:])
                )
                for samam_index in range(1, 6):
                    samam = tuple(
                        cell
                        for cell in schedule.cells
                        if cell.samam_index == samam_index
                    )
                    assert len(samam) == 5
                    assert {cell.bird for cell in samam} == set(PanchaPakshiBird)
                    assert {cell.activity for cell in samam} == set(
                        PanchaPakshiActivity
                    )
                    assert sum(
                        (cell.duration_nazhigai for cell in samam), Fraction()
                    ) == 6


def test_nominal_lookup_uses_half_open_exact_boundaries(profile) -> None:
    schedule = generate_purva_day_schedule(profile, PanchaPakshiWeekday.SUNDAY)

    assert schedule.cell_at_nazhigai(0) is schedule.cells[0]
    assert schedule.cell_at_nazhigai(Fraction(5, 4)) is schedule.cells[1]
    assert schedule.cell_at_nazhigai(Fraction(59, 2)) is schedule.cells[-1]
    with pytest.raises(ValueError, match="half-open"):
        schedule.cell_at_nazhigai(30)
    with pytest.raises(TypeError, match="int or Fraction"):
        schedule.cell_at_nazhigai(0.5)


def test_relationships_are_complete_directed_source_cells(profile) -> None:
    owl_to_peacock = pancha_pakshi_directed_relationship(
        profile, PanchaPakshiBird.OWL, PanchaPakshiBird.PEACOCK
    )
    peacock_to_owl = pancha_pakshi_directed_relationship(
        profile, PanchaPakshiBird.PEACOCK, PanchaPakshiBird.OWL
    )

    assert len(profile.relationship_rules) == 20
    assert owl_to_peacock.model_kind == (
        "source_scoped_directed_1879_machine_reviewed"
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
            profile, PanchaPakshiBird.CROW, PanchaPakshiBird.CROW
        )


def test_omissions_and_conflict_witnesses_remain_explicit(profile) -> None:
    assert {omission.feature for omission in profile.explicit_omissions} == {
        "authority_birds",
        "natal_mapping",
        "scoring",
        "cross_witness_normalized_relationship_policy",
        "vinadi",
        "seasonal_scaling",
    }
    assert all(
        omission.status == "omitted" for omission in profile.explicit_omissions
    )
    assert all(
        conflict.runtime_status == "not_imported"
        for conflict in profile.research_conflict_ledger
    )
    sarasvati = next(
        conflict
        for conflict in profile.research_conflict_ledger
        if conflict.witness_id == "TVA_BOK_0022647"
    )
    assert "sixth edition and 2014" in sarasvati.bibliographic_label
    assert "fifth edition and September 2011" in sarasvati.bibliographic_label
    assert "discrepancy unresolved" in sarasvati.record_identity
