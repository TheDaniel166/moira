"""
Standard heliacal nomenclature (6.9.9) — Venus and Saturn regression cases.

Nomenclature authority: Ptolemy, *Phaseis*; C. Schoch (1924), MNRAS 84, 731,
and Schoch's tables in Langdon & Fotheringham (1928); J. Evans (1998), *The
History and Practice of Ancient Astronomy*.  Swiss Ephemeris ``swe_heliacal_ut``
uses the same names (1 morning first = heliacal rising, 2 evening last =
heliacal setting, 3 evening first, 4 morning last, 5 acronychal rising,
6 cosmical setting) and is cited for naming parity only.

Evidence class: regression parity (values pinned from the 6.9.9 Moira
implementation, DE441, observer 35N 35E, default HeliacalPolicy) plus
physical/geometric invariants that follow from each definition.  They are not
authority validation.
"""
from __future__ import annotations

import pytest

import moira.heliacal as heliacal_module
from moira.constants import Body
from moira.heliacal import (
    STANDARD_HELIACAL_EVENT_KINDS,
    HeliacalEventKind,
    heliacal_event_kind_applies,
    phasis_events_near,
    visibility_event,
)
from moira.spk_reader import use_reader_override


_LAT, _LON = 35.0, 35.0
_SATURN_OPPOSITION_2023 = 2460183.5  # 2023-08-27
_VENUS_INFERIOR_CONJ_2022 = 2459588.5  # 2022-01-09
_VENUS_SUPERIOR_CONJ_2021 = 2459299.5  # 2021-03-26

K = HeliacalEventKind

# (body, kind, jd_start, pinned jd_ut or None)
_CASES = [
    (Body.VENUS, K.HELIACAL_RISING, 2458994.5, 2459008.5848),
    (Body.VENUS, K.HELIACAL_SETTING, 2459400.5, 2459585.1284),
    (Body.VENUS, K.EVENING_FIRST, 2459299.5, 2459324.1977),
    (Body.VENUS, K.MORNING_LAST, 2459050.5, 2459255.6683),
    (Body.VENUS, K.ACRONYCHAL_RISING, 2459299.5, None),
    (Body.VENUS, K.COSMICAL_SETTING, 2459299.5, None),
    (Body.SATURN, K.HELIACAL_RISING, 2459992.5, 2460013.6343),
    (Body.SATURN, K.HELIACAL_SETTING, 2460200.5, 2460358.1733),
    (Body.SATURN, K.EVENING_FIRST, 2460100.5, None),
    (Body.SATURN, K.MORNING_LAST, 2460000.5, None),
    (Body.SATURN, K.ACRONYCHAL_RISING, 2460100.5, 2460166.2270),
    (Body.SATURN, K.COSMICAL_SETTING, 2460100.5, 2460194.6030),
]


def test_enum_values_follow_standard_names() -> None:
    assert [kind.value for kind in STANDARD_HELIACAL_EVENT_KINDS] == [
        "heliacal_rising",
        "heliacal_setting",
        "evening_first",
        "morning_last",
        "acronychal_rising",
        "cosmical_setting",
    ]
    # Compatibility members keep their wire values.
    assert K("acronychal_setting") is K.ACRONYCHAL_SETTING
    assert K("cosmic_rising") is K.COSMIC_RISING
    assert K("cosmic_setting") is K.COSMIC_SETTING


@pytest.mark.parametrize(
    ("body", "applicable"),
    [
        (Body.VENUS, {K.HELIACAL_RISING, K.HELIACAL_SETTING, K.EVENING_FIRST, K.MORNING_LAST}),
        (Body.MERCURY, {K.HELIACAL_RISING, K.HELIACAL_SETTING, K.EVENING_FIRST, K.MORNING_LAST}),
        (Body.SATURN, {K.HELIACAL_RISING, K.HELIACAL_SETTING, K.ACRONYCHAL_RISING, K.COSMICAL_SETTING}),
        (Body.MARS, {K.HELIACAL_RISING, K.HELIACAL_SETTING, K.ACRONYCHAL_RISING, K.COSMICAL_SETTING}),
        ("Sirius", {K.HELIACAL_RISING, K.HELIACAL_SETTING, K.ACRONYCHAL_RISING, K.COSMICAL_SETTING}),
        (Body.MOON, {K.EVENING_FIRST, K.MORNING_LAST}),
    ],
)
def test_standard_kind_applicability(body: str, applicable: set) -> None:
    got = {kind for kind in STANDARD_HELIACAL_EVENT_KINDS if heliacal_event_kind_applies(body, kind)}
    assert got == applicable


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("body", "kind", "jd_start", "expected_jd"),
    _CASES,
    ids=[f"{body}-{kind.value}" for body, kind, _, _ in _CASES],
)
def test_venus_and_saturn_standard_kind_regression(
    planetary_reader, body, kind, jd_start, expected_jd
) -> None:
    with use_reader_override(planetary_reader):
        event = visibility_event(body, kind, jd_start, _LAT, _LON)
    if expected_jd is None:
        assert event is None
        return
    assert event is not None
    assert event.kind is kind
    assert event.jd_ut == pytest.approx(expected_jd, abs=0.01)
    assert event.sun_altitude_deg < 0.0

    # Definitional invariants.
    if kind in (K.HELIACAL_RISING, K.MORNING_LAST):
        assert event.elongation_deg < 0.0  # morning sky, west of the Sun
    if kind in (K.HELIACAL_SETTING, K.EVENING_FIRST):
        assert event.elongation_deg > 0.0  # evening sky, east of the Sun
    if kind is K.ACRONYCHAL_RISING:
        # Evening rising, before opposition: west of the Sun by more than 90 deg,
        # the body at the horizon while the Sun is below -arcus visionis.
        assert event.elongation_deg < -90.0
        assert event.jd_ut < _SATURN_OPPOSITION_2023
        assert abs(event.target_altitude_deg) < 0.05
        assert event.sun_altitude_deg <= -10.0
    if kind is K.COSMICAL_SETTING:
        assert event.elongation_deg > 90.0
        assert event.jd_ut > _SATURN_OPPOSITION_2023
        assert abs(event.target_altitude_deg) < 0.05
        assert event.sun_altitude_deg <= -10.0


@pytest.mark.requires_ephemeris
def test_venus_heliacal_setting_is_evening_last_before_inferior_conjunction(planetary_reader) -> None:
    with use_reader_override(planetary_reader):
        event = visibility_event(Body.VENUS, K.HELIACAL_SETTING, 2459400.5, _LAT, _LON)
    assert event is not None
    assert event.jd_ut < _VENUS_INFERIOR_CONJ_2022
    # Evening event: local mean solar time after noon at 35E.
    local_fraction = (event.jd_ut + 0.5 + _LON / 360.0) % 1.0
    assert local_fraction > 0.5


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(("body", "jd_start"), [(Body.VENUS, 2459400.5), (Body.SATURN, 2460200.5)])
def test_deprecated_acronychal_setting_equals_heliacal_setting(planetary_reader, body, jd_start) -> None:
    with use_reader_override(planetary_reader):
        standard = visibility_event(body, K.HELIACAL_SETTING, jd_start, _LAT, _LON)
        legacy = visibility_event(body, K.ACRONYCHAL_SETTING, jd_start, _LAT, _LON)
    assert standard is not None and legacy is not None
    assert legacy.kind is K.ACRONYCHAL_SETTING
    assert legacy.jd_ut == standard.jd_ut


@pytest.mark.requires_ephemeris
def test_evening_first_search_rejects_opposition_side_change_for_saturn(planetary_reader) -> None:
    """The physics guard, independent of the applicability gate: Saturn enters
    the evening side at opposition, not out of the Sun's glare."""
    model = heliacal_module._effective_visibility_model(heliacal_module.HeliacalPolicy.default())
    with use_reader_override(planetary_reader):
        result = heliacal_module._search_visibility_event(
            Body.SATURN,
            K.EVENING_FIRST,
            2460150.5,
            _LAT,
            _LON,
            model=model,
            search_days=120,
        )
    assert result is None


@pytest.mark.requires_ephemeris
def test_phasis_events_near_saturn_acronychal_rising(planetary_reader) -> None:
    with use_reader_override(planetary_reader):
        result = phasis_events_near(Body.SATURN, 2460170.0, _LAT, _LON)
    assert result.window_days == 7.0
    assert [entry.kind for entry in result.results] == list(STANDARD_HELIACAL_EVENT_KINDS)
    by_kind = {entry.kind: entry for entry in result.results}
    assert by_kind[K.EVENING_FIRST].applicable is False
    assert by_kind[K.MORNING_LAST].applicable is False
    ar = by_kind[K.ACRONYCHAL_RISING]
    assert ar.applicable is True
    assert ar.event is not None
    assert ar.event.jd_ut == pytest.approx(2460166.2270, abs=0.01)
    assert ar.offset_days == pytest.approx(ar.event.jd_ut - 2460170.0)
    for kind in (K.HELIACAL_RISING, K.HELIACAL_SETTING, K.COSMICAL_SETTING):
        assert by_kind[kind].applicable is True
        assert by_kind[kind].event is None


@pytest.mark.requires_ephemeris
def test_phasis_events_near_venus_around_inferior_conjunction(planetary_reader) -> None:
    with use_reader_override(planetary_reader):
        result = phasis_events_near(Body.VENUS, 2459586.0, _LAT, _LON)
    by_kind = {entry.kind: entry for entry in result.results}
    assert by_kind[K.HELIACAL_SETTING].event is not None
    assert by_kind[K.HELIACAL_SETTING].event.jd_ut == pytest.approx(2459585.1284, abs=0.01)
    assert by_kind[K.HELIACAL_RISING].event is not None
    assert abs(by_kind[K.HELIACAL_RISING].offset_days) <= 7.0
    assert by_kind[K.ACRONYCHAL_RISING].applicable is False
    assert by_kind[K.COSMICAL_SETTING].applicable is False


@pytest.mark.parametrize("window", [0.0, -1.0, 30.5, float("nan")])
def test_phasis_rejects_out_of_range_windows(window: float) -> None:
    with pytest.raises(ValueError, match="window_days"):
        phasis_events_near(Body.VENUS, 2459586.0, _LAT, _LON, window_days=window)


# ---------------------------------------------------------------------------
# Moon under the Yallop crescent criterion: morning last (old crescent)
# ---------------------------------------------------------------------------
#
# Yallop (1997, NAO TN 69) states the best time for sunset/moonset (eq. 4.1),
# but his Table 4 calibration set includes morning (M) observations evaluated
# at the mirrored best time (moonrise-to-sunrise lag); Odeh (2006, Exp. Astron.
# 18, p. 41) defines the lag for moonrise and sunrise likewise.  Values below
# are regression pins from Moira 6.9.9 (DE441, 35N 35E, naked eye) plus the
# definitional invariants; they are not authority validation.

_NEW_MOON_2024_04_08 = 2460409.264  # 2024-04-08 18:21 UT


def _yallop_policy():
    from moira.heliacal import VisibilityCriterionFamily, VisibilityPolicy

    return VisibilityPolicy(criterion_family=VisibilityCriterionFamily.YALLOP_LUNAR_CRESCENT)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd_start", [2460381.5, 2460397.5])  # waxing / waning start
def test_moon_morning_last_under_yallop_is_last_old_crescent(planetary_reader, jd_start) -> None:
    from moira.heliacal import _lunar_crescent_details_for_morning, _local_mean_solar_midnight

    with use_reader_override(planetary_reader):
        event = visibility_event(
            Body.MOON, K.MORNING_LAST, jd_start, _LAT, _LON, visibility_policy=_yallop_policy()
        )
        assert event is not None
        next_morning = _lunar_crescent_details_for_morning(
            _local_mean_solar_midnight(event.jd_ut, _LON) + 1.0, _LAT, _LON
        )
    assert event.kind is K.MORNING_LAST
    assert event.jd_ut == pytest.approx(2460407.6232, abs=0.01)  # 2024-04-07 dawn
    assert event.jd_ut < _NEW_MOON_2024_04_08
    assert event.elongation_deg < 0.0  # waning, west of the Sun
    details = event.lunar_crescent_details
    assert details is not None
    assert details.observation_window == "morning"
    assert details.best_time_jd_ut < details.sunset_jd_ut  # morning field holds sunrise
    assert details.visibility_class.value in ("A", "B")
    # The following morning is not a naked-eye crescent.
    assert next_morning is None or next_morning.visibility_class.value not in ("A", "B")


@pytest.mark.requires_ephemeris
def test_moon_evening_first_under_yallop_skips_waning_moon(planetary_reader) -> None:
    with use_reader_override(planetary_reader):
        event = visibility_event(
            Body.MOON, K.EVENING_FIRST, 2460397.5, _LAT, _LON, visibility_policy=_yallop_policy()
        )
    assert event is not None
    assert event.elongation_deg > 0.0
    assert event.jd_ut > _NEW_MOON_2024_04_08
    assert event.jd_ut == pytest.approx(2460410.1911, abs=0.01)  # 2024-04-09 dusk
    assert event.lunar_crescent_details.observation_window == "evening"


@pytest.mark.requires_ephemeris
def test_moon_evening_first_under_yallop_started_mid_crescent_waits_for_next_new_crescent(
    planetary_reader,
) -> None:
    from moira.heliacal import (
        _lunar_crescent_details_for_evening,
        _local_mean_solar_midnight,
        _yallop_class_observable,
    )

    new_moon_2024_05_08 = 2460438.64  # 2024-05-08 03:22 UT
    with use_reader_override(planetary_reader):
        # 2024-04-11: the April crescent is already visible, so its first
        # sighting (2024-04-09) lies before the search start.
        event = visibility_event(
            Body.MOON, K.EVENING_FIRST, 2460411.5, _LAT, _LON, visibility_policy=_yallop_policy()
        )
        assert event is not None
        evening_before = _lunar_crescent_details_for_evening(
            _local_mean_solar_midnight(event.jd_ut, _LON) - 1.0, _LAT, _LON
        )
    assert event.jd_ut > new_moon_2024_05_08
    assert event.elongation_deg > 0.0
    # First visibility is a transition: the evening before was not observable.
    assert evening_before is None or not _yallop_class_observable(
        evening_before.visibility_class, _yallop_policy().environment.observing_aid
    )
