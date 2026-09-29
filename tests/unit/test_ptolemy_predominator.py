"""Predominator by Ptolemy, Tetrabiblos III.10 (Robbins, Loeb 435, pp. 271-279).

No worked example is given by Ptolemy; these are invariant tests of each step
of the procedure as the text states it (kernel-free, caller-supplied
longitudes).
"""

from __future__ import annotations

import pytest

from moira.hellenistic_offices import (
    HellenisticOfficeStatus,
    ProrogativePlace,
    find_predominator_ptolemy,
    hunt_hellenistic_offices,
)


def _positions(**overrides: float) -> dict[str, float]:
    base = {
        "Sun": 10.0, "Moon": 100.0, "Mercury": 20.0, "Venus": 40.0,
        "Mars": 80.0, "Jupiter": 200.0, "Saturn": 300.0,
    }
    base.update(overrides)
    return base


def test_prorogative_places_are_thirty_degree_arcs_from_five_above_the_ascendant() -> None:
    asc = 100.0
    expectations = {
        96.0: ProrogativePlace.ORIENT,        # 4 deg above the horizon
        124.0: ProrogativePlace.ORIENT,       # 24 deg below, still coming into the light
        126.0: None,                          # beyond the 25 deg
        94.0: None,                           # more than 5 deg above: Evil Daemon
        50.0: ProrogativePlace.GOOD_DAEMON,   # offset 310
        10.0: ProrogativePlace.MIDHEAVEN,     # offset 270
        340.0: ProrogativePlace.HOUSE_OF_THE_GOD,  # offset 240
        290.0: ProrogativePlace.OCCIDENT,     # offset 190
        220.0: None,                          # below the earth
    }
    for longitude, place in expectations.items():
        det = find_predominator_ptolemy(
            positions=_positions(Mercury=longitude), asc_longitude=asc, is_day_chart=True,
            prenatal_new_moon_longitude=0.0,
        )
        truth = next(p for p in det.places if p.name == "Mercury")
        assert truth.place is place, longitude


def test_day_sun_in_midheaven_is_predominator() -> None:
    # Sun at offset 270 from the Ascendant: mid-heaven, the place of greatest
    # authority, so no planet can outrank it.
    det = find_predominator_ptolemy(
        positions=_positions(Sun=10.0, Moon=200.0), asc_longitude=100.0, is_day_chart=True,
    )
    assert det.status is HellenisticOfficeStatus.SELECTED
    assert det.predominator == "Sun"
    assert det.selection_step == "sect_light_in_prorogative_place"


def test_night_moon_first_and_lot_of_fortune_is_unreversed() -> None:
    det = find_predominator_ptolemy(
        positions=_positions(Sun=250.0, Moon=10.0), asc_longitude=100.0, is_day_chart=False,
    )
    assert det.predominator == "Moon"
    # Ptolemy p. 275: Asc + Moon - Sun "both by night and by day".
    assert det.lot_of_fortune_longitude == pytest.approx((100.0 + 10.0 - 250.0) % 360.0)


def test_both_luminaries_take_the_place_of_greater_authority() -> None:
    # Day chart: Sun in the Good Daemon, Moon in the mid-heaven.
    det = find_predominator_ptolemy(
        positions=_positions(Sun=50.0, Moon=10.0, Mercury=150.0, Venus=150.0, Mars=150.0,
                             Jupiter=150.0, Saturn=150.0),
        asc_longitude=100.0, is_day_chart=True,
    )
    assert det.predominator == "Moon"
    assert det.selection_step == "luminary_in_place_of_greater_authority"


def test_ruler_step_needs_the_preceding_new_moon_by_day() -> None:
    # Neither luminary in a prorogative place.
    positions = _positions(Sun=180.0, Moon=160.0)
    det = find_predominator_ptolemy(positions=positions, asc_longitude=100.0, is_day_chart=True)
    assert det.status is HellenisticOfficeStatus.NOT_EVALUABLE
    assert det.reason == "prenatal_new_moon_longitude_required"


def test_ruler_needs_three_forms_to_one_place_and_a_prorogative_place() -> None:
    positions = _positions(Sun=180.0, Moon=160.0)
    det = find_predominator_ptolemy(
        positions=positions, asc_longitude=100.0, is_day_chart=True,
        prenatal_new_moon_longitude=175.0,
    )
    places = {p.name: p.place for p in det.places}
    by_planet: dict[str, list[int]] = {}
    for count in det.ruler_counts:
        by_planet.setdefault(count.planet, []).append(count.count)
    qualified = {
        planet for planet, counts in by_planet.items()
        if max(counts) >= 3 and places[planet] is not None
    }
    assert set(det.ruler_candidates) <= qualified
    if det.status is HellenisticOfficeStatus.SELECTED:
        if det.selection_step == "ruler_by_domination":
            top = max(sum(by_planet[p]) for p in qualified)
            assert sum(by_planet[det.predominator]) == top
        else:
            assert not qualified
            assert det.predominator == "Ascendant"
            assert det.selection_step == "horoscope_final"


def test_day_final_resort_is_the_horoscope() -> None:
    # No luminary in place and no planet in any prorogative place.
    positions = _positions(Sun=180.0, Moon=160.0, Mercury=150.0, Venus=150.0,
                           Mars=150.0, Jupiter=150.0, Saturn=150.0)
    det = find_predominator_ptolemy(
        positions=positions, asc_longitude=100.0, is_day_chart=True,
        prenatal_new_moon_longitude=175.0,
    )
    assert det.predominator == "Ascendant"
    assert det.selection_step == "horoscope_final"


def test_night_final_resort_follows_the_last_syzygy() -> None:
    positions = _positions(Sun=180.0, Moon=160.0, Mercury=150.0, Venus=150.0,
                           Mars=150.0, Jupiter=150.0, Saturn=150.0)
    common = dict(positions=positions, asc_longitude=100.0, is_day_chart=False,
                  prenatal_full_moon_longitude=340.0)
    missing = find_predominator_ptolemy(**common)
    assert missing.reason == "latest_prenatal_syzygy_required"
    new = find_predominator_ptolemy(**common, latest_prenatal_syzygy="new_moon")
    assert new.predominator == "Ascendant"
    full = find_predominator_ptolemy(**common, latest_prenatal_syzygy="full_moon")
    assert full.predominator == "Lot of Fortune"
    assert full.predominator_longitude == pytest.approx(full.lot_of_fortune_longitude)


def test_ruler_in_a_place_of_greater_authority_with_relation_to_both_luminaries() -> None:
    # Day: Moon in the House of the God (offset 260); Venus in the Occident
    # (offset 200) with triangle + exaltation + aspect to the preceding new
    # moon at 25 Pisces, and a relation to both the Sun and the Moon.
    det = find_predominator_ptolemy(
        positions=_positions(), asc_longitude=200.0, is_day_chart=True,
        prenatal_new_moon_longitude=355.0,
    )
    assert det.predominator == "Venus"
    assert det.selection_step == "ruler_preferred_over_luminary"


def test_office_hunt_carries_the_predominator_and_never_a_house_master() -> None:
    hunt = hunt_hellenistic_offices(
        positions=_positions(Sun=10.0), is_day_chart=True, asc_longitude=100.0,
    )
    assert hunt.predominator == "Sun"
    assert hunt.status is HellenisticOfficeStatus.SELECTED
    assert hunt.house_master is None
    assert hunt.house_master_reason == "doctrine_not_admitted"

    partial = hunt_hellenistic_offices(positions={"Sun": 10.0}, is_day_chart=True, asc_longitude=100.0)
    assert partial.status is HellenisticOfficeStatus.NOT_EVALUABLE
    assert partial.reason == "positions_required_for_all_seven_planets"
    no_asc = hunt_hellenistic_offices(positions=_positions(), is_day_chart=True)
    assert no_asc.reason == "asc_longitude_required"
