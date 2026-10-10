"""
Hyleg per William Lilly, Christian Astrology (1647), Book III ch. CIV
(pp. 527–529): Sun by day, Moon by night, in houses 1, 10, 11, 7, 9 (with the
5° cusp orb of Book I ch. IV); under the earth only within 25° of the
Ascendant; 8th and 12th rejected; then the dominion step (pp. 528-529) and
the Ascendant or Part of Fortune. Missing inputs and ties return
NOT_EVALUABLE with a named reason.
"""

from __future__ import annotations

import math

import pytest

from moira.longevity import (
    HylegDoctrine,
    HylegStatus,
    find_hyleg_lilly_1647,
)
from moira.longevity import _oblique_ascension


EQUAL_CUSPS = [float(30 * i) for i in range(12)]  # Asc 0°, houses 1..12 in order


def _hyleg(sun: float, moon: float, day: bool, cusps=EQUAL_CUSPS, **kw):
    return find_hyleg_lilly_1647(sun, moon, cusps, day, **kw)


def test_day_sun_in_tenth_is_hyleg() -> None:
    result = _hyleg(280.0, 100.0, True)
    assert result.doctrine is HylegDoctrine.WILLIAM_LILLY_1647
    assert result.status is HylegStatus.SELECTED
    assert result.hyleg == "Sun"
    assert result.candidates[0].orb_house == 10


def test_day_sun_in_eighth_falls_to_moon_in_eleventh() -> None:
    result = _hyleg(220.0, 310.0, True)
    assert result.hyleg == "Moon"
    sun = result.candidates[0]
    assert sun.is_hylegiacal is False
    assert sun.reason == "house_8_not_hylegiacal"


def test_twelfth_house_is_rejected() -> None:
    result = _hyleg(340.0, 225.0, True)
    assert result.status is HylegStatus.NOT_EVALUABLE
    assert result.hyleg is None
    assert result.reason == (
        "planet_positions_required_for_dominion_step:Mercury,Venus,Mars,Jupiter,Saturn"
    )


def test_five_degree_cusp_orb_brings_twelfth_into_first_above_horizon() -> None:
    result = _hyleg(357.0, 100.0, True)
    sun = result.candidates[0]
    assert (sun.strict_house, sun.orb_house, sun.above_horizon) == (12, 1, True)
    assert result.hyleg == "Sun"


def test_sixth_within_orb_of_seventh_is_still_under_the_earth() -> None:
    result = _hyleg(177.0, 100.0, True)
    sun = result.candidates[0]
    assert (sun.strict_house, sun.orb_house) == (6, 7)
    assert sun.is_hylegiacal is False
    assert sun.reason == "under_the_earth"


def test_night_takes_moon_then_sun() -> None:
    selected = _hyleg(280.0, 250.0, False)
    assert selected.hyleg == "Moon"
    assert selected.selection_step == "sect_light_hylegiacal"
    assert selected.both_luminaries_hylegiacal is True

    # Moon in the 8th: the Sun is admitted after her (Lilly's nocturnal
    # example, p. 529; Ptolemy III.10 "by night ... the moon first, next the sun").
    sun = _hyleg(280.0, 220.0, False)
    assert sun.status is HylegStatus.SELECTED
    assert sun.hyleg == "Sun"
    assert sun.selection_step == "other_luminary_hylegiacal"


_FIVE = {"Mercury": 20.0, "Venus": 40.0, "Mars": 200.0, "Jupiter": 250.0, "Saturn": 300.0}


def test_day_dominion_planet_in_hylegiacal_place_is_hyleg() -> None:
    # Sun in the 8th, Moon in the 12th. Places: Sun 10 Scorpio, preceding new
    # Moon 20 Libra, Ascendant 0 Aries. Mars: Scorpio domicile + triplicity
    # (Lilly's water ruler) + Aries domicile + face = 4 dignities, 14 points;
    # Mars stands in the 7th, a hylegiacal house.
    result = _hyleg(220.0, 340.0, True, planet_positions=_FIVE, prenatal_new_moon_longitude=200.0)
    assert result.status is HylegStatus.SELECTED
    assert result.hyleg == "Mars"
    assert result.selection_step == "dominion_planet_in_hylegiacal_place"
    counts = {c.planet: c for c in result.dominion_counts}
    assert (counts["Mars"].dignity_count, counts["Mars"].points) == (4, 14)
    assert all(c.dignity_count >= 3 for c in result.dominion_counts if c.qualifies)
    assert [name for name, _ in result.dominion_places] == [
        "Sun", "preceding_new_moon", "Ascendant",
    ]


def test_day_dominion_planet_out_of_place_gives_ascendant() -> None:
    result = _hyleg(
        220.0, 340.0, True,
        planet_positions={**_FIVE, "Mars": 100.0},  # Mars in the 4th
        prenatal_new_moon_longitude=200.0,
    )
    assert result.dominion_planet == "Mars"
    assert result.hyleg == "Ascendant"
    assert result.selection_step == "ascendant_final"
    assert result.hyleg_longitude == 0.0


def test_night_final_resort_follows_the_preceding_syzygy() -> None:
    # Sun in the 6th, Moon in the 3rd; the dominion planet (Mars) in the 4th.
    # Part of Fortune = Asc + Moon - Sun = 280, in the 10th.
    five = {**_FIVE, "Mercury": 50.0, "Mars": 100.0}
    common = dict(planet_positions=five, prenatal_full_moon_longitude=10.0)
    full = _hyleg(150.0, 70.0, False, latest_prenatal_syzygy="full_moon", **common)
    assert full.hyleg == "Part of Fortune"
    assert full.hyleg_longitude == 280.0
    assert full.selection_step == "part_of_fortune_after_full_moon"
    assert [name for name, _ in full.dominion_places] == [
        "Moon", "preceding_full_moon", "Part of Fortune",
    ]
    new = _hyleg(150.0, 70.0, False, latest_prenatal_syzygy="new_moon", **common)
    assert new.hyleg == "Ascendant"
    missing = _hyleg(150.0, 70.0, False, **common)
    assert missing.status is HylegStatus.NOT_EVALUABLE
    assert missing.reason == "latest_prenatal_syzygy_required"


def test_dominion_step_names_missing_syzygy() -> None:
    result = _hyleg(220.0, 340.0, True, planet_positions=_FIVE)
    assert result.reason == "prenatal_new_moon_longitude_required"


def test_first_house_under_earth_requires_equatorial_inputs() -> None:
    with pytest.raises(ValueError, match="armc, obliquity and geographic_latitude"):
        _hyleg(10.0, 100.0, True)


def _ascendant(armc: float, obliquity: float, latitude: float) -> float:
    a, e, f = map(math.radians, (armc, obliquity, latitude))
    return math.degrees(
        math.atan2(math.cos(a), -(math.sin(a) * math.cos(e) + math.tan(f) * math.sin(e)))
    ) % 360.0


@pytest.mark.parametrize("armc", [0.0, 75.0, 190.0, 300.0])
def test_oblique_ascension_of_ascendant_is_armc_plus_90(armc: float) -> None:
    """Invariant: the rising ecliptic degree has OA = ARMC + 90°."""
    obliquity, latitude = 23.44, 51.5
    asc = _ascendant(armc, obliquity, latitude)
    oa = _oblique_ascension(asc, obliquity, latitude)
    diff = (oa - (armc + 90.0) + 180.0) % 360.0 - 180.0
    assert abs(diff) < 1e-9


def test_first_house_within_and_beyond_25_equatorial_degrees() -> None:
    armc, obliquity, latitude = 100.0, 23.44, 51.5
    asc = _ascendant(armc, obliquity, latitude)
    cusps = [asc] + [(asc + 50.0 + 28.1818 * (i - 1)) % 360.0 for i in range(1, 12)]
    kw = dict(armc=armc, obliquity=obliquity, geographic_latitude=latitude)

    near = _hyleg((asc + 5.0) % 360.0, (asc + 200.0) % 360.0, True, cusps=cusps, **kw)
    sun = near.candidates[0]
    assert sun.strict_house == 1 and sun.above_horizon is False
    assert 0.0 < sun.oblique_ascension_below_ascendant_deg <= 25.0
    assert sun.is_hylegiacal is True

    far = _hyleg((asc + 44.0) % 360.0, (asc + 200.0) % 360.0, True, cusps=cusps, **kw)
    sun = far.candidates[0]
    assert sun.strict_house == 1
    assert sun.oblique_ascension_below_ascendant_deg > 25.0
    assert sun.is_hylegiacal is False
    assert sun.reason == "first_house_beyond_25_equatorial_degrees_of_ascendant"


def test_rejects_malformed_inputs() -> None:
    with pytest.raises(ValueError):
        find_hyleg_lilly_1647(10.0, 20.0, EQUAL_CUSPS[:11], True)
    with pytest.raises(ValueError):
        find_hyleg_lilly_1647(float("nan"), 20.0, EQUAL_CUSPS, True)
    with pytest.raises(TypeError):
        find_hyleg_lilly_1647(10.0, 20.0, EQUAL_CUSPS, 1)  # type: ignore[arg-type]
