from __future__ import annotations

import pytest

from moira.babylonian import (
    BABYLONIAN_MERCURY_REFERENCES,
    BABYLONIAN_VENUS_AMMISADUQA_PHENOMENA,
    BABYLONIAN_VENUS_REFERENCES,
    BabylonianAdmissionStrength,
    BabylonianCalendarDate,
    BabylonianChronologyAuthority,
    BabylonianHoldoutReason,
    BabylonianObservationClass,
    BabylonianSourceQuality,
    BabylonianValidationStatus,
    admitted_babylonian_mercury_references,
    admitted_babylonian_venus_references,
    babylonian_calendar_to_civil_day,
    babylonian_month_length,
    babylonian_month_start,
    babylonian_planetary_reference,
    babylonian_venus_ammisaduqa_phenomena,
    holdout_babylonian_mercury_references,
    holdout_babylonian_venus_references,
    julian_calendar_day_from_jd,
    julian_calendar_day_to_jd,
)
from moira.heliacal import HeliacalEventKind
from moira.julian import calendar_datetime_from_jd


def test_julian_calendar_day_to_jd_round_trips_historical_source_dates() -> None:
    jd = julian_calendar_day_to_jd(-388, 10, 30, 0.0)
    calendar = julian_calendar_day_from_jd(jd)

    assert (calendar.year, calendar.month, calendar.day) == (-388, 10, 30)


def test_babylonian_month_start_uses_parker_dubberstein_table() -> None:
    civil_day = babylonian_month_start(79, 8)

    assert (civil_day.year, civil_day.month, civil_day.day) == (-232, 11, 3)


def test_babylonian_calendar_to_civil_day_converts_se79_mercury_diary_pair() -> None:
    first_appearance = babylonian_calendar_to_civil_day(79, 8, 9)
    last_appearance = babylonian_calendar_to_civil_day(79, 8, 14)

    assert (first_appearance.year, first_appearance.month, first_appearance.day) == (-232, 11, 11)
    assert (last_appearance.year, last_appearance.month, last_appearance.day) == (-232, 11, 16)


def test_babylonian_month_length_for_se79_month_viii_is_29_days() -> None:
    assert babylonian_month_length(79, 8) == 29


def test_babylonian_calendar_date_uses_same_conversion_surface() -> None:
    date = BabylonianCalendarDate(79, 8, 9)

    assert (date.civil_day.year, date.civil_day.month, date.civil_day.day) == (-232, 11, 11)


def test_babylonian_mercury_reference_set_separates_admitted_from_candidates() -> None:
    admitted = [
        reference
        for reference in BABYLONIAN_MERCURY_REFERENCES
        if reference.validation_status is BabylonianValidationStatus.ADMITTED
    ]
    candidates = [
        reference
        for reference in BABYLONIAN_MERCURY_REFERENCES
        if reference.validation_status is BabylonianValidationStatus.CANDIDATE
    ]

    assert [reference.id for reference in admitted] == ["mercury_artaxerxes_ii_y16_mf"]
    assert {reference.id for reference in candidates} == {
        "mercury_artaxerxes_ii_y16_ml",
        "mercury_se79_viii_9_mf",
        "mercury_se79_viii_14_el",
        "mercury_text_m_el_403_bce",
    }


def test_babylonian_mercury_admission_policy_is_encoded_explicitly() -> None:
    references = {reference.id: reference for reference in BABYLONIAN_MERCURY_REFERENCES}

    assert references["mercury_artaxerxes_ii_y16_mf"].observation_class is BabylonianObservationClass.OBSERVED_AND_IDEAL
    assert references["mercury_artaxerxes_ii_y16_mf"].admission_strength is BabylonianAdmissionStrength.BOUNDED
    assert references["mercury_artaxerxes_ii_y16_ml"].observation_class is BabylonianObservationClass.EXPECTED
    assert references["mercury_se79_viii_9_mf"].observation_class is BabylonianObservationClass.OMITTED
    assert references["mercury_se79_viii_14_el"].observation_class is BabylonianObservationClass.OMITTED
    assert references["mercury_text_m_el_403_bce"].observation_class is BabylonianObservationClass.TERMINUS_SUPPORT
    assert all(
        references[row_id].admission_strength is BabylonianAdmissionStrength.HOLDOUT
        for row_id in (
            "mercury_artaxerxes_ii_y16_ml",
            "mercury_se79_viii_9_mf",
            "mercury_se79_viii_14_el",
            "mercury_text_m_el_403_bce",
        )
    )


def test_admitted_babylonian_mercury_registry_exposes_only_admitted_rows() -> None:
    assert [reference.id for reference in admitted_babylonian_mercury_references()] == [
        "mercury_artaxerxes_ii_y16_mf"
    ]


def test_holdout_babylonian_mercury_registry_exposes_only_candidates() -> None:
    assert {reference.id for reference in holdout_babylonian_mercury_references()} == {
        "mercury_artaxerxes_ii_y16_ml",
        "mercury_se79_viii_9_mf",
        "mercury_se79_viii_14_el",
        "mercury_text_m_el_403_bce",
    }


def test_all_holdout_mercury_rows_have_explicit_holdout_reasons() -> None:
    references = {reference.id: reference for reference in holdout_babylonian_mercury_references()}

    assert references["mercury_artaxerxes_ii_y16_ml"].holdout_reason is BabylonianHoldoutReason.MIXED
    assert references["mercury_se79_viii_9_mf"].holdout_reason is BabylonianHoldoutReason.MIXED
    assert references["mercury_se79_viii_14_el"].holdout_reason is BabylonianHoldoutReason.MIXED
    assert references["mercury_text_m_el_403_bce"].holdout_reason is BabylonianHoldoutReason.MIXED


def test_babylonian_admitted_mercury_window_contains_moira_solved_date() -> None:
    reference = babylonian_planetary_reference("mercury_artaxerxes_ii_y16_mf")
    solved_calendar = calendar_datetime_from_jd(1579640.6018365026)

    assert reference.comparison_window.contains_calendar_date(solved_calendar)


def test_se79_candidate_windows_match_parker_conversion() -> None:
    first_reference = babylonian_planetary_reference("mercury_se79_viii_9_mf")
    last_reference = babylonian_planetary_reference("mercury_se79_viii_14_el")

    assert first_reference.source_window.start.date_tuple == (-232, 11, 11)
    assert last_reference.source_window.start.date_tuple == (-232, 11, 16)


def test_unknown_babylonian_reference_id_raises_key_error() -> None:
    with pytest.raises(KeyError, match="Unknown Babylonian planetary reference id"):
        babylonian_planetary_reference("does_not_exist")


def test_venus_ammisaduqa_source_corpus_exposes_reliable_event_typed_rows() -> None:
    rows = babylonian_venus_ammisaduqa_phenomena()

    assert rows == BABYLONIAN_VENUS_AMMISADUQA_PHENOMENA
    assert len(rows) == 11
    assert all(row.source_quality is BabylonianSourceQuality.RELIABLE for row in rows)


def test_venus_ammisaduqa_source_corpus_covers_all_four_visibility_event_families() -> None:
    event_kinds = {row.event_kind for row in BABYLONIAN_VENUS_AMMISADUQA_PHENOMENA}

    assert event_kinds == {
        HeliacalEventKind.HELIACAL_RISING,
        HeliacalEventKind.HELIACAL_SETTING,
        HeliacalEventKind.ACRONYCHAL_RISING,
        HeliacalEventKind.ACRONYCHAL_SETTING,
    }


def test_venus_ammisaduqa_source_rows_preserve_year_month_day_labels() -> None:
    rows = {row.id: row for row in BABYLONIAN_VENUS_AMMISADUQA_PHENOMENA}

    assert (rows["venus_ammisaduqa_y1_el"].source_year, rows["venus_ammisaduqa_y1_el"].babylonian_month, rows["venus_ammisaduqa_y1_el"].babylonian_day) == (1, "XI", "14")
    assert (rows["venus_ammisaduqa_y2_ml"].source_year, rows["venus_ammisaduqa_y2_ml"].babylonian_month, rows["venus_ammisaduqa_y2_ml"].babylonian_day) == (2, "VIII", "10")
    assert (rows["venus_ammisaduqa_y3_mf"].source_year, rows["venus_ammisaduqa_y3_mf"].babylonian_month, rows["venus_ammisaduqa_y3_mf"].babylonian_day) == (3, "VII", "13")
    assert (rows["venus_ammisaduqa_y10_ef"].source_year, rows["venus_ammisaduqa_y10_ef"].babylonian_month, rows["venus_ammisaduqa_y10_ef"].babylonian_day) == (10, "X", "16")
    assert (rows["venus_ammisaduqa_y14_mf"].source_year, rows["venus_ammisaduqa_y14_mf"].babylonian_month, rows["venus_ammisaduqa_y14_mf"].babylonian_day) == (14, "VIII", "7")


def test_babylonian_venus_registry_does_not_claim_legacy_solver_admission() -> None:
    assert admitted_babylonian_venus_references() == ()


def test_babylonian_venus_registry_preserves_physical_model_rows_as_candidates() -> None:
    assert holdout_babylonian_venus_references() == BABYLONIAN_VENUS_REFERENCES
    assert all(
        reference.holdout_reason
        is BabylonianHoldoutReason.VISIBILITY_DOCTRINE_NOT_IMPLEMENTED
        for reference in BABYLONIAN_VENUS_REFERENCES
    )
    assert all(
        reference.source_window.authority
        is BabylonianChronologyAuthority.DE_JONG_FOERTMEYER_2010
        for reference in BABYLONIAN_VENUS_REFERENCES
    )


def test_babylonian_venus_registry_transcribes_de_jong_foertmeyer_table_1_evidence() -> None:
    expected = {
        "venus_ammisaduqa_y1_el_long": (0.25, 5.0, 7.3, 0, False),
        "venus_ammisaduqa_y1_mf_long": (0.19, 3.6, 5.9, -1, False),
        "venus_ammisaduqa_y2_ml_long": (0.31, 4.1, 7.7, -4, False),
        "venus_ammisaduqa_y2_ef_long": (0.29, 3.6, 7.4, 2, False),
        "venus_ammisaduqa_y3_el_long": (0.52, 5.6, 9.6, -6, True),
        "venus_ammisaduqa_y3_mf_long": (0.13, 3.8, 4.4, -2, False),
        "venus_ammisaduqa_y4_ml_long": (0.29, 3.1, 7.3, -4, False),
        "venus_ammisaduqa_y4_ef_long": (0.18, 3.0, 5.3, -11, False),
        "venus_ammisaduqa_y10_ml_long": (0.28, 2.8, 7.1, -2, False),
        "venus_ammisaduqa_y10_ef_long": (0.29, 3.7, 7.4, 3, False),
        "venus_ammisaduqa_y14_mf_long": (0.23, 4.6, 6.7, 0, False),
    }

    actual = {}
    for reference in BABYLONIAN_VENUS_REFERENCES:
        evidence = reference.visibility_evidence
        assert evidence is not None
        actual[reference.id] = (
            evidence.extinction_coefficient_mag_per_airmass,
            evidence.refracted_elevation_deg,
            evidence.geometric_arcus_visionis_deg,
            evidence.nominal_date_delta_days,
            evidence.source_fit_bracketed,
        )

    assert actual == expected
