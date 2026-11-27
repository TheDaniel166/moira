"""Primary fixtures and exact boundary regressions for Kuta and KP."""
from fractions import Fraction
from math import nextafter

import pytest

from moira import kp_longitude, kuta_match


def _charak(bride, groom):
    return kuta_match(profile_id="charak_ashtakoota", bride_moon=bride, groom_moon=groom)


def _iyer(bride, groom):
    return kuta_match(profile_id="iyer_porutham_1917", bride_moon=bride, groom_moon=groom)


def _factors(match):
    return {factor.name: factor for factor in match.factors}


def test_charak_published_pair():
    # Charts XXVII-1 and XXVII-2, pp. 461–462. The printed Moons are Pisces
    # 5°33′ (Uttara Bhadrapada) and Sagittarius 7°54′ (Mula).
    match = _charak(335 + 33 / 60, 247 + 54 / 60)
    assert match.bride.nakshatra_index == 25
    assert match.groom.nakshatra_index == 18
    assert (match.profile.maximum_points, match.total_points) == (36, 24)
    assert tuple(f.applied_points for f in match.factors) == (0, 0.5, 1.5, 2, 5, 0, 7, 8)
    forward = _factors(match)
    assert (forward["tara"].bride_category, forward["tara"].groom_category) == ("21", "8")
    reverse = _factors(_charak(match.groom.longitude, match.bride.longitude))
    assert reverse["varna"].raw_points == 1
    assert reverse["tara"].raw_points == 1.5


def test_charak_directional_cells_and_boundaries():
    # XXVII-2, row quadruped / column wild and its transpose.
    assert _factors(_charak(1, 121))["vashya"].raw_points == 0.5
    assert _factors(_charak(121, 1))["vashya"].raw_points == 0
    # XXVII-6, row Deva / column Rakshasa and its transpose.
    assert _factors(_charak(1, 27))["gana"].raw_points == 1
    assert _factors(_charak(27, 1))["gana"].raw_points == 0
    assert _factors(_charak(nextafter(255.0, 0), 121))["vashya"].bride_category == "Manava"
    assert _factors(_charak(255, 121))["vashya"].bride_category == "Chatushpada"
    assert _factors(_charak(nextafter(285.0, 0), 31))["vashya"].bride_category == "Chatushpada"
    assert _factors(_charak(285, 31))["vashya"].bride_category == "Jalachara"
    # XXVII-4: Abhijit overlaps Shravana in Capricorn and changes only Yoni.
    end = float(Fraction(1011200, 3600))
    just_inside = _charak(nextafter(end, 0), 1)
    outside = _charak(end, 1)
    assert just_inside.bride.nakshatra == outside.bride.nakshatra == "Shravana"
    assert _factors(just_inside)["yoni"].bride_category == "Mongoose"
    assert _factors(outside)["yoni"].bride_category == "Monkey"


def test_charak_blemish_cancellations_keep_printed_nadi_points():
    # Adya in the same sign but different stars, then one Madhya star across signs.
    for bride, groom, clause in [(150, 162, "(a)"), (177, 182, "(b)")]:
        nadi = _factors(_charak(bride, groom))["nadi"]
        assert nadi.raw_points == nadi.applied_points == 0
        assert nadi.applied_status == "cancelled"
        assert clause in nadi.exception


def test_iyer_printed_directional_exception_and_checklist():
    # Iyer p. 70 names Punarvasu (bride) to Hasta (groom) as a favourable
    # seventh-star case. Gemini 24° and Virgo 12° instantiate that pair.
    match = _iyer(84, 162)
    assert match.profile.minimum_agreements == 5
    assert match.total_points is None
    assert len(match.factors) == 10
    assert match.confirmed_agreements == 7
    forward = _factors(match)
    assert forward["dina"].bride_category == "7"
    assert forward["dina"].raw_status == "disagreement"
    assert forward["dina"].applied_status == "agreement"
    assert forward["mahendra"].applied_status == "agreement"
    assert forward["stree_deergha"].applied_status == "disagreement"
    assert forward["gana"].raw_status == "agreement"
    assert forward["rajju"].applied_status == forward["vedha"].applied_status == "agreement"
    reverse = _factors(_iyer(162, 84))
    assert reverse["dina"].bride_category == "22"
    assert reverse["dina"].applied_status == "disagreement"
    assert reverse["stree_deergha"].applied_status == "agreement"


def test_iyer_explicit_rasi_exception_and_unresolved_source_cases():
    even_second = _factors(_iyer(1, 31))["rasi"]
    assert (even_second.raw_status, even_second.applied_status) == ("disagreement", "agreement")
    assert _factors(_iyer(61, 153))["gana"].applied_status == "unresolved"
    assert _factors(_iyer(157, 149))["dina"].applied_status == "unresolved"
    dina = _factors(_iyer(181, 100))["dina"]
    assert (dina.bride_category, dina.groom_category) == ("22", "7")
    assert dina.applied_status == "unresolved"
    # A shared lord can trigger a possible p. 76 cancellation. The
    # edition joins it to other conditions that cannot all hold together.
    rajju = _factors(_iyer(10, 231))["rajju"]
    assert (rajju.raw_status, rajju.applied_status) == ("disagreement", "unresolved")
    assert "p. 76" in rajju.exception


def test_kuta_all_canonical_pada_endpoints():
    for quarter in range(108):
        boundary = float(Fraction(quarter * 10, 3))
        at = _iyer(boundary, 1).bride
        assert (at.nakshatra_index, at.pada) == (quarter // 4, quarter % 4 + 1)
        if quarter:
            previous = _iyer(nextafter(boundary, 0), 1).bride
            assert (previous.nakshatra_index, previous.pada) == ((quarter - 1) // 4, (quarter - 1) % 4 + 1)


def test_kp_sign_boundary_inside_one_sub():
    aries = kp_longitude(nextafter(30, 0))
    taurus = kp_longitude(30)
    assert (aries.sign.lord, taurus.sign.lord) == ("Mars", "Venus")
    assert aries.star == taurus.star
    assert aries.sub == taurus.sub
    assert aries.sub_sub == taurus.sub_sub
    assert (taurus.star.lord, taurus.sub.lord, taurus.sub_sub.lord) == ("Sun", "Rahu", "Saturn")


def test_kp_readers_and_part_v_printed_chains():
    # Reader III, pp. 503–504. Mrigashira and the adjoining Saturn and
    # Mercury subs cross Taurus to Gemini at exactly 60 degrees.
    taurus = kp_longitude(nextafter(60, 0))
    gemini = kp_longitude(60)
    assert taurus.star == gemini.star
    assert (taurus.sign.lord, taurus.star.lord, taurus.sub.lord) == ("Venus", "Mars", "Saturn")
    assert (gemini.sign.lord, gemini.star.lord, gemini.sub.lord) == ("Mercury", "Mars", "Mercury")
    assert taurus.sub.start_ticks == 625200
    assert taurus.sub.end_ticks == gemini.sub.start_ticks == 648000
    assert gemini.sub.end_ticks == 668400

    # Reader VI's rotation examples, and Astro Secrets Part V pp. 171–172.
    moon = kp_longitude(9 + 14 / 60)
    mars = kp_longitude(60 + 2 + 53 / 60)
    assert (moon.sign.lord, moon.star.lord, moon.sub.lord, moon.sub_sub.lord) == (
        "Mars", "Ketu", "Jupiter", "Rahu",
    )
    assert (mars.sign.lord, mars.star.lord, mars.sub.lord, mars.sub_sub.lord) == (
        "Mercury", "Mars", "Venus", "Venus",
    )


    # The same source gives the Cancer Ascendant and Capricorn descendant.
    for longitude, expected in [
        (111 + 38 / 60, ("Moon", "Mercury", "Sun", "Moon")),
        (291 + 38 / 60, ("Saturn", "Moon", "Venus", "Jupiter")),
    ]:
        point = kp_longitude(longitude)
        assert (point.sign.lord, point.star.lord, point.sub.lord, point.sub_sub.lord) == expected


def test_kp_all_sub_sub_boundaries_against_fractional_partition():
    # Reconstruct the primary rotation using rational degrees independently
    # of the production unit (thirds of an arcsecond).
    lords = ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury")
    weights = (7, 20, 6, 10, 7, 18, 16, 19, 17)
    position = Fraction(0)
    previous = None
    for star in range(27):
        for si in range(9):
            sub = (star + si) % 9
            for ci in range(9):
                child = (sub + ci) % 9
                width = Fraction(40, 3) * Fraction(weights[sub], 120) * Fraction(weights[child], 120)
                endpoint = float(position)
                result = kp_longitude(endpoint)
                assert (result.nakshatra_index, result.sub.lord, result.sub_sub.lord) == (
                    star, lords[sub], lords[child],
                )
                assert result.sub_sub.start_ticks == position * 10800
                assert result.sub_sub.end_ticks == (position + width) * 10800
                assert result.star.start_ticks <= result.sub.start_ticks <= result.sub_sub.start_ticks
                assert result.sub_sub.end_ticks <= result.sub.end_ticks <= result.star.end_ticks
                if previous is not None:
                    assert kp_longitude(nextafter(endpoint, 0)).sub_sub == previous
                assert kp_longitude(nextafter(endpoint, 360)).sub_sub == result.sub_sub
                previous = result.sub_sub
                position += width
    assert position == 360
    assert kp_longitude(nextafter(360, 0)).sub_sub == previous


@pytest.mark.parametrize("value", [True, "12", float("inf"), -1, 360])
def test_wave4_strict_canonical_longitudes(value):
    with pytest.raises((ValueError, TypeError)):
        kp_longitude(value)
    with pytest.raises((ValueError, TypeError)):
        _charak(value, 12)
