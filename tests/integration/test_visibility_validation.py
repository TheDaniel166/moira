from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pytest

from moira.constants import Body
from moira.heliacal import (
    HeliacalEventKind,
    LunarCrescentVisibilityClass,
    MoonlightPolicy,
    VisibilityPolicy,
    VisibilitySearchPolicy,
    VisibilityTargetKind,
    _lunar_crescent_details_for_morning,
    _lunar_crescent_details_for_evening,
    visibility_event,
)
from moira.julian import julian_day
from moira.sothic import sothic_rising
from moira.stars import heliacal_rising_event


_YALLOP_REFERENCE_ROWS = tuple(
    json.loads(
        (Path(__file__).resolve().parent.parent / "fixtures" / "yallop_table4_reference.json")
        .read_text(encoding="utf-8")
    )
)
_YALLOP_Q_OUTLIER_ENTRY_NUMBERS = frozenset()
_YALLOP_NON_BOUNDARY_ROWS = tuple(
    row
    for row in _YALLOP_REFERENCE_ROWS
    if not bool(row["boundary_sensitive"])
)
_YALLOP_NON_BOUNDARY_EXACT_ROWS = tuple(
    row
    for row in _YALLOP_NON_BOUNDARY_ROWS
    if int(row["entry_number"]) not in _YALLOP_Q_OUTLIER_ENTRY_NUMBERS
)
_YALLOP_Q_OUTLIER_ROWS = tuple(
    row
    for row in _YALLOP_NON_BOUNDARY_ROWS
    if int(row["entry_number"]) in _YALLOP_Q_OUTLIER_ENTRY_NUMBERS
)
_YALLOP_BOUNDARY_ROWS = tuple(
    row for row in _YALLOP_REFERENCE_ROWS if bool(row["boundary_sensitive"])
)
_YALLOP_ADJACENT_CLASS_ALLOWANCES = {
    LunarCrescentVisibilityClass.A: {
        LunarCrescentVisibilityClass.A,
        LunarCrescentVisibilityClass.B,
    },
    LunarCrescentVisibilityClass.B: {
        LunarCrescentVisibilityClass.A,
        LunarCrescentVisibilityClass.B,
        LunarCrescentVisibilityClass.C,
    },
    LunarCrescentVisibilityClass.C: {
        LunarCrescentVisibilityClass.B,
        LunarCrescentVisibilityClass.C,
        LunarCrescentVisibilityClass.D,
    },
    LunarCrescentVisibilityClass.D: {
        LunarCrescentVisibilityClass.C,
        LunarCrescentVisibilityClass.D,
        LunarCrescentVisibilityClass.E,
    },
    LunarCrescentVisibilityClass.E: {
        LunarCrescentVisibilityClass.D,
        LunarCrescentVisibilityClass.E,
        LunarCrescentVisibilityClass.F,
    },
    LunarCrescentVisibilityClass.F: {
        LunarCrescentVisibilityClass.E,
        LunarCrescentVisibilityClass.F,
    },
}


@lru_cache(maxsize=None)
def _yallop_details_for_reference_row(
    date_text: str,
    latitude_deg: float,
    longitude_deg: float,
    time_of_day: str,
):
    year, month, day = (int(part) for part in date_text.split("-"))
    jd_midnight = julian_day(year, month, day, 0.0)
    if time_of_day == "evening":
        return _lunar_crescent_details_for_evening(jd_midnight, latitude_deg, longitude_deg)
    return _lunar_crescent_details_for_morning(jd_midnight, latitude_deg, longitude_deg)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("body", "event_kind", "jd_start", "search_days", "jd_lo", "jd_hi"),
    [
        (
            Body.MERCURY,
            HeliacalEventKind.HELIACAL_RISING,
            2459950.5,
            90,
            2459956.5,
            2459983.5,
        ),
        (
            Body.VENUS,
            HeliacalEventKind.HELIACAL_RISING,
            2458994.5,
            120,
            2459004.0,
            2459044.0,
        ),
        (
            Body.JUPITER,
            HeliacalEventKind.HELIACAL_RISING,
            2460045.5,
            120,
            2460050.0,
            2460110.0,
        ),
        (
            Body.VENUS,
            HeliacalEventKind.ACRONYCHAL_RISING,
            2459299.5,
            120,
            2459310.0,
            2459360.0,
        ),
        (
            Body.VENUS,
            HeliacalEventKind.HELIACAL_SETTING,
            2459050.5,
            300,
            2459220.0,
            2459290.0,
        ),
    ],
)
def test_generalized_planetary_visibility_event_matches_published_windows(
    body: str,
    event_kind: HeliacalEventKind,
    jd_start: float,
    search_days: int,
    jd_lo: float,
    jd_hi: float,
) -> None:
    """
    Validate the generalized event surface against the admitted modern
    apparition windows already used by the planetary heliacal corpus.

    Mercury's Berlin row is admitted against the explicit 12 Jan 2023 to
    08 Feb 2023 morning-apparition table published by In-The-Sky.org.
    """
    latitude_deg = 52.52 if body is Body.MERCURY else 35.0
    longitude_deg = 13.41 if body is Body.MERCURY else 35.0
    event = visibility_event(
        body,
        event_kind,
        jd_start,
        latitude_deg,
        longitude_deg,
        search_policy=VisibilitySearchPolicy(search_window_days=search_days),
    )

    assert event is not None
    assert event.target_kind is VisibilityTargetKind.PLANET
    assert event.kind is event_kind
    assert event.assessment.observable is True
    assert jd_lo < event.jd_ut < jd_hi


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("body", "event_kind", "jd_start", "search_days", "jd_lo", "jd_hi"),
    [
        (
            Body.VENUS,
            HeliacalEventKind.HELIACAL_RISING,
            2458994.5,
            120,
            2459004.0,
            2459044.0,
        ),
        (
            Body.VENUS,
            HeliacalEventKind.ACRONYCHAL_RISING,
            2459299.5,
            120,
            2459310.0,
            2459360.0,
        ),
        (
            Body.VENUS,
            HeliacalEventKind.HELIACAL_SETTING,
            2459050.5,
            300,
            2459220.0,
            2459290.0,
        ),
    ],
)
def test_generalized_planetary_visibility_event_ks1991_slice_stays_within_admitted_windows(
    body: str,
    event_kind: HeliacalEventKind,
    jd_start: float,
    search_days: int,
    jd_lo: float,
    jd_hi: float,
) -> None:
    """
    Validate that the admitted K&S 1991 moonlight path remains inside the
    same published Venus visibility windows already used by the non-moonlight
    generalized planetary slice.
    """
    event = visibility_event(
        body,
        event_kind,
        jd_start,
        35.0,
        35.0,
        visibility_policy=VisibilityPolicy(
            moonlight_policy=MoonlightPolicy.KRISCIUNAS_SCHAEFER_1991,
        ),
        search_policy=VisibilitySearchPolicy(search_window_days=search_days),
    )

    assert event is not None
    assert event.target_kind is VisibilityTargetKind.PLANET
    assert event.kind is event_kind
    assert event.assessment.observable is True
    assert event.assessment.moonlight_sky_nanolamberts is not None
    assert event.assessment.moonlight_sky_nanolamberts > 0.0
    assert jd_lo < event.jd_ut < jd_hi


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_generalized_stellar_visibility_event_matches_sothic_anchor_slice() -> None:
    """
    The generalized stellar branch currently delegates to the default
    star-heliacal doctrine. Measure that delegation explicitly against the
    Sirius/Sothic anchor slice and preserve the doctrine split.
    """
    sothic_entry = sothic_rising(31.2, 29.9, 139, 139, arcus_visionis=10.0)[0]
    direct_default = heliacal_rising_event(
        "Sirius",
        julian_day(139, 1, 1, 0.0),
        31.2,
        29.9,
    )
    event = visibility_event(
        "Sirius",
        HeliacalEventKind.HELIACAL_RISING,
        julian_day(139, 1, 1, 0.0),
        31.2,
        29.9,
    )

    assert event is not None
    assert event.target_kind is VisibilityTargetKind.STAR
    assert event.kind is HeliacalEventKind.HELIACAL_RISING
    assert event.assessment.observable is True
    assert direct_default.is_found is True
    assert direct_default.jd_ut is not None
    assert event.jd_ut == pytest.approx(direct_default.jd_ut, abs=1.0 / 1440.0)
    assert event.jd_ut < sothic_entry.jd_rising
    assert (sothic_entry.jd_rising - event.jd_ut) < 5.0


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "row",
    _YALLOP_NON_BOUNDARY_EXACT_ROWS,
    ids=lambda row: f"{row['entry_number']}-{row['date']}-{row['expected_class']}",
)
def test_yallop_lunar_corpus_slice_matches_published_table4_cases(
    row: dict[str, object],
) -> None:
    """
    Validate a published slice of Yallop Table 4 against Moira's admitted
    evening lunar-crescent implementation.

    These cases are intentionally chosen away from the class boundaries so the
    validation measures doctrinal fidelity rather than boundary sensitivity.
    """
    assert row["source"] == "Yallop 1997 Table 4"
    assert row["boundary_sensitive"] is False

    details = _yallop_details_for_reference_row(
        str(row["date"]),
        float(row["latitude_deg"]),
        float(row["longitude_deg"]),
        str(row["time_of_day"]),
    )

    assert details is not None
    assert details.q == pytest.approx(float(row["published_q"]), abs=0.035)
    assert details.visibility_class is LunarCrescentVisibilityClass(str(row["expected_class"]))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "row",
    _YALLOP_Q_OUTLIER_ROWS,
    ids=lambda row: f"outlier-{row['entry_number']}-{row['date']}-{row['expected_class']}",
)
def test_yallop_full_corpus_outlier_family_still_lands_in_same_broad_class(
    row: dict[str, object],
) -> None:
    """
    A small published subset currently shows large q residuals under Moira's
    reconstructed best-time path while still remaining inside Yallop class A.
    Keep these explicit rather than mixing them into the exact-tolerance family.
    """
    details = _yallop_details_for_reference_row(
        str(row["date"]),
        float(row["latitude_deg"]),
        float(row["longitude_deg"]),
        str(row["time_of_day"]),
    )

    assert details is not None
    assert float(row["published_q"]) > 0.216
    assert details.q > 0.216
    assert details.visibility_class is LunarCrescentVisibilityClass.A


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "row",
    _YALLOP_BOUNDARY_ROWS,
    ids=lambda row: f"boundary-{row['entry_number']}-{row['date']}-{row['expected_class']}",
)
def test_yallop_boundary_cases_preserve_near_threshold_behavior(
    row: dict[str, object],
) -> None:
    """
    Boundary-sensitive rows are validated under a separate doctrine:
    the computed q must stay close to the published value, but exact class
    agreement is not forced when the published row lies very near a threshold.
    """
    assert row["source"] == "Yallop 1997 Table 4"
    assert row["boundary_sensitive"] is True

    details = _yallop_details_for_reference_row(
        str(row["date"]),
        float(row["latitude_deg"]),
        float(row["longitude_deg"]),
        str(row["time_of_day"]),
    )

    assert details is not None
    published_q = float(row["published_q"])
    expected_class = LunarCrescentVisibilityClass(str(row["expected_class"]))
    assert details.q == pytest.approx(published_q, abs=0.03)
    assert abs(details.q - published_q) < 0.03
    assert details.visibility_class in _YALLOP_ADJACENT_CLASS_ALLOWANCES[expected_class]


@pytest.mark.requires_ephemeris
def test_yallop_full_table4_corpus_audit_envelope() -> None:
    residuals: list[float] = []
    class_matches = 0
    outlier_entries: list[int] = []

    for row in _YALLOP_REFERENCE_ROWS:
        details = _yallop_details_for_reference_row(
            str(row["date"]),
            float(row["latitude_deg"]),
            float(row["longitude_deg"]),
            str(row["time_of_day"]),
        )
        assert details is not None
        residual = abs(details.q - float(row["published_q"]))
        residuals.append(residual)
        if details.visibility_class.value == str(row["expected_class"]):
            class_matches += 1
        if residual > 0.2:
            outlier_entries.append(int(row["entry_number"]))

    assert len(_YALLOP_REFERENCE_ROWS) == 295
    assert sum(res <= 0.03 for res in residuals) >= 293
    assert sum(res <= 0.05 for res in residuals) >= 295
    assert class_matches >= 289
    assert set(outlier_entries) == set()
