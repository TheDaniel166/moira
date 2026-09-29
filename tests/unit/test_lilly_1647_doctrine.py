"""Lilly 1647 doctrine: planetary years, terms, almuten and alcocoden (kernel-free).

Authority: William Lilly, Christian Astrology (London, 1647). Page citations
are to the 1647 edition; the values were read from the 1647 OCR, the Mithras93
transcription of vol. 1 and the Astrology Classics edition (table p. 104).
"""

from __future__ import annotations

import pytest

from moira.dignities import (
    LILLY_1647_TERMS,
    AlmutenDoctrine,
    almuten_figuris,
    almuten_figuris_determination,
    almuten_of_degree,
    almuten_of_degree_determination,
    lilly_1647_essential_dignities_at,
    lilly_1647_term_ruler,
)
from moira.egyptian_bounds import PTOLEMAIC_BOUNDS
from moira.longevity import (
    PTOLEMAIC_YEARS,
    AlcocodenStatus,
    find_alcocoden_lilly_1647,
)

_ORDER = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
_CUSPS = [30.0 * i for i in range(12)]


# ---------------------------------------------------------------------------
# Planetary years (Book I chs. VIII-XIV, pp. 57-83)
# ---------------------------------------------------------------------------

def test_planetary_years_are_lillys_printed_values() -> None:
    # (least, mean, greater) as printed in each planet's chapter.
    assert PTOLEMAIC_YEARS == {
        "Saturn": (30.0, 43.5, 57.0),
        "Jupiter": (12.0, 45.0, 79.0),
        "Mars": (15.0, 40.0, 66.0),
        "Sun": (19.0, 69.0, 120.0),
        "Venus": (8.0, 45.0, 82.0),
        "Mercury": (20.0, 48.0, 76.0),
        "Moon": (25.0, 66.0, 108.0),
    }


# ---------------------------------------------------------------------------
# Lilly's table (Book I ch. XVIII, p. 104)
# ---------------------------------------------------------------------------

def test_lilly_terms_partition_every_sign_among_the_five_planets() -> None:
    for sign, segments in LILLY_1647_TERMS.items():
        assert segments[0][1] == 0 and segments[-1][2] == 30, sign
        for (_, _, end), (_, start, _) in zip(segments, segments[1:]):
            assert end == start, sign
        assert sorted(ruler for ruler, _, _ in segments) == sorted(
            ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")
        ), sign


@pytest.mark.parametrize(
    ("longitude", "lilly", "robbins"),
    [
        (30.0 + 24.0, "Saturn", "Mars"),       # Taurus 22-26 Saturn in Lilly
        (60.0 + 13.5, "Jupiter", "Venus"),     # Gemini 7-14 Jupiter
        (120.0 + 3.0, "Saturn", "Jupiter"),    # Leo opens with Saturn
        (180.0 + 13.0, "Jupiter", "Mercury"),  # Libra 11-19 Jupiter
        (210.0 + 10.0, "Jupiter", "Venus"),    # Scorpio 6-14 Jupiter
        (270.0 + 20.0, "Mars", "Saturn"),      # Capricorn 19-25 Mars
        (330.0 + 25.5, "Mars", "Saturn"),      # Pisces 20-26 Mars
    ],
)
def test_lilly_terms_differ_from_robbins_ptolemaic_terms(
    longitude: float, lilly: str, robbins: str
) -> None:
    assert lilly_1647_term_ruler(longitude) == lilly
    sign_index = int(longitude // 30)
    degree = longitude - 30 * sign_index
    sign = list(PTOLEMAIC_BOUNDS)[sign_index]
    robbins_ruler = next(r for r, a, b in PTOLEMAIC_BOUNDS[sign] if a <= degree < b)
    assert robbins_ruler == robbins


def test_lilly_triplicity_has_no_participating_ruler_and_mars_rules_water() -> None:
    # 0 Aries by day: Sun exaltation + triplicity; Mars domicile + face;
    # Jupiter term; Saturn nothing (no participating ruler in Lilly's table).
    held = {p: lilly_1647_essential_dignities_at(p, 0.0, True) for p in _ORDER}
    assert held["Sun"] == (("exaltation", 4), ("triplicity", 3))
    assert held["Mars"] == (("domicile", 5), ("face", 1))
    assert held["Jupiter"] == (("term", 2),)
    assert held["Saturn"] == ()
    for is_day in (True, False):
        for water in (95.0, 215.0, 335.0):
            kinds = dict(lilly_1647_essential_dignities_at("Mars", water, is_day))
            assert kinds.get("triplicity") == 3
            for other in ("Venus", "Moon"):
                assert "triplicity" not in dict(
                    lilly_1647_essential_dignities_at(other, water, is_day)
                )


# ---------------------------------------------------------------------------
# Almuten
# ---------------------------------------------------------------------------

def test_almuten_of_degree_defaults_to_lilly_and_reports_ties() -> None:
    day = almuten_of_degree_determination(0.0, True)
    assert day.doctrine == "william_lilly_1647_almuten_of_degree"
    assert day.almuten == "Sun"
    assert {t.planet: t.total for t in day.tallies}["Saturn"] == 0

    night = almuten_of_degree_determination(0.0, False)
    totals = {t.planet: t.total for t in night.tallies}
    assert totals["Jupiter"] == 5  # night triplicity 3 + term 2
    assert night.almuten == "Mars"  # domicile 5 + face 1

    # 21 Aries by day: Mars domicile 5 + term 2 (Lilly 21-26) = 7;
    # Sun exaltation 4 + triplicity 3 = 7. Lilly gives no tie-break.
    tie = almuten_of_degree_determination(21.0, True)
    assert tie.almuten is None
    assert tie.tied_planets == ("Sun", "Mars")
    assert tie.tie_break == "none_lilly_gives_no_tie_break"
    with pytest.raises(ValueError, match="tie"):
        almuten_of_degree(21.0, True, doctrine=AlmutenDoctrine.WILLIAM_LILLY_1647)
    # The string API keeps the legacy count by default.
    assert almuten_of_degree(21.0, True) == almuten_of_degree_determination(
        21.0, True, doctrine="moira_legacy_v1"
    ).almuten


_OTHERS = "william_lilly_1647_others_five_places"


def test_almuten_figuris_others_rule_counts_asc_mc_sun_moon_fortune() -> None:
    positions = {
        "Sun": 10.0, "Moon": 100.0, "Mercury": 20.0, "Venus": 40.0,
        "Mars": 200.0, "Jupiter": 250.0, "Saturn": 300.0,
    }
    for is_day in (True, False):
        det = almuten_figuris_determination(positions, _CUSPS, is_day, doctrine=_OTHERS)
        assert det.doctrine == "william_lilly_1647_asc_mc_sun_moon_fortune"
        names = [p.name for p in det.scored_points]
        assert names == ["Ascendant", "Tenth cusp", "Sun", "Moon", "Part of Fortune"]
        # Lilly's Part of Fortune: Asc + Moon - Sun by day and by night.
        assert det.scored_points[-1].longitude == pytest.approx(90.0)
        for tally in det.tallies:
            assert tally.house_points == 0 and tally.ruler_points == 0
            assert tally.essential_points == sum(
                sum(points for _, points in lilly_1647_essential_dignities_at(
                    tally.planet, point.longitude, is_day
                ))
                for point in det.scored_points
            )

    with_mc = almuten_figuris_determination(
        positions, 0.0, True, midheaven_longitude=275.0, doctrine=_OTHERS,
    )
    assert [p.name for p in with_mc.scored_points][1] == "Midheaven"
    with pytest.raises(ValueError, match="Midheaven"):
        almuten_figuris_determination(positions, 0.0, True, doctrine=_OTHERS)
    with pytest.raises(ValueError, match="not used by the william_lilly_1647"):
        almuten_figuris_determination(positions, _CUSPS, True, day_ruler="Sun")
    with pytest.raises(ValueError, match="figuris rule, not an almuten of a degree"):
        almuten_of_degree_determination(0.0, True, doctrine=_OTHERS)
    with pytest.raises(ValueError, match="doctrine must be one of"):
        almuten_figuris_determination(positions, _CUSPS, True, doctrine="ibn_ezra")
    # The string API keeps the legacy count by default.
    assert almuten_figuris(positions, _CUSPS, True) == almuten_figuris_determination(
        positions, _CUSPS, True, doctrine="moira_legacy_v1"
    ).almuten


_SPEEDS = {
    "Sun": 1.0, "Moon": 13.0, "Mercury": 1.5, "Venus": -0.3,
    "Mars": 0.6, "Jupiter": 0.1, "Saturn": 0.03,
}
_STARS = {"Regulus": 150.0, "Spica": 204.0, "Algol": 56.0}


def test_almuten_figuris_default_is_lillys_own_whole_figure_rule() -> None:
    # Lilly III ch. CV pp. 531-532: most essential and accidental dignities in
    # the whole figure, scored by the ready table of p. 115.
    from moira.dignities import calculate_dignities, DignityHorizonFrame

    positions = {
        "Sun": 280.0, "Moon": 110.0, "Mercury": 20.0, "Venus": 40.0,
        "Mars": 200.0, "Jupiter": 250.0, "Saturn": 300.0,
    }
    det = almuten_figuris_determination(
        positions, _CUSPS, True, speeds=_SPEEDS, north_node_longitude=123.0,
        fixed_star_longitudes=_STARS,
    )
    assert det.doctrine == "william_lilly_1647_whole_figure"
    assert det.reason is None
    # Dual path: the tallies are calculate_dignities' Lilly totals.
    direct = {
        d.planet: d
        for d in calculate_dignities(
            [
                {"name": p, "degree": positions[p], "speed": _SPEEDS[p],
                 "is_retrograde": p not in ("Sun", "Moon") and _SPEEDS[p] < 0}
                for p in _ORDER
            ],
            [{"number": i + 1, "degree": c} for i, c in enumerate(_CUSPS)],
            horizon_frame=DignityHorizonFrame(asc_longitude=0.0, mc_longitude=270.0),
            node_positions={"Mean Node": 123.0},
            fixed_star_positions=_STARS,
        )
    }
    for tally in det.tallies:
        assert tally.essential_points == direct[tally.planet].essential_score
        assert tally.accidental_points == direct[tally.planet].accidental_score
        assert tally.total == direct[tally.planet].total_score
    top = max(t.total for t in det.tallies)
    assert det.almuten == next(t.planet for t in det.tallies if t.total == top)
    assert det.tied_planets == (det.almuten,)

    with pytest.raises(ValueError, match="daily motion"):
        almuten_figuris_determination(positions, _CUSPS, True)
    with pytest.raises(ValueError, match="north_node_longitude"):
        almuten_figuris_determination(positions, _CUSPS, True, speeds=_SPEEDS)
    with pytest.raises(ValueError, match="fixed_star_longitudes"):
        almuten_figuris_determination(
            positions, _CUSPS, True, speeds=_SPEEDS, north_node_longitude=123.0,
        )
    with pytest.raises(ValueError, match="sect"):
        almuten_figuris_determination(
            positions, _CUSPS, False, speeds=_SPEEDS, north_node_longitude=123.0,
            fixed_star_longitudes=_STARS,
        )


def test_whole_figure_almuten_is_undetermined_when_a_testimony_is_not_evaluable() -> None:
    # Moon exactly opposite the Sun: waxing/waning is on its boundary.
    positions = {
        "Sun": 280.0, "Moon": 100.0, "Mercury": 20.0, "Venus": 40.0,
        "Mars": 200.0, "Jupiter": 250.0, "Saturn": 300.0,
    }
    det = almuten_figuris_determination(
        positions, _CUSPS, True, speeds=_SPEEDS, north_node_longitude=123.0,
        fixed_star_longitudes=_STARS,
    )
    assert det.almuten is None
    assert det.reason == "lilly_testimony_not_evaluable:Moon:waxing_waning:phase_boundary"


def test_lilly_terms_are_the_bounds_doctrine_table_with_citation() -> None:
    from moira.egyptian_bounds import (
        BOUNDS_SOURCE_CITATIONS,
        WILLIAM_LILLY_1647_TERMS,
        EgyptianBoundsDoctrine,
    )

    assert {s: tuple(v) for s, v in WILLIAM_LILLY_1647_TERMS.items()} == LILLY_1647_TERMS
    assert "p. 104" in BOUNDS_SOURCE_CITATIONS[EgyptianBoundsDoctrine.WILLIAM_LILLY_1647]


# ---------------------------------------------------------------------------
# Alcocoden (Book III ch. CIV, pp. 530-531)
# ---------------------------------------------------------------------------

def test_alcocoden_must_behold_the_hyleg() -> None:
    # Day chart, Sun hyleg at 10 Capricorn in the 10th (equal cusps from 0 Aries).
    # Saturn (domicile, 5 points) and Mars (exaltation + face, 5) do not
    # behold the Sun's degree within their orbs; Venus (triplicity by day, 3)
    # does, by trine, so Venus is the alcocoden.
    positions = {
        "Sun": 280.0, "Moon": 100.0, "Mercury": 20.0, "Venus": 40.0,
        "Mars": 200.0, "Jupiter": 250.0, "Saturn": 300.0,
    }
    det = find_alcocoden_lilly_1647(positions, _CUSPS, True)
    assert det.status is AlcocodenStatus.SELECTED
    assert det.hyleg.hyleg == "Sun"
    assert det.alcocoden == "Venus"
    assert det.selection_basis == "most_essential_dignity_in_hyleg_place_beholding_it"
    by_planet = {c.planet: c for c in det.candidates}
    assert by_planet["Saturn"].essential_points == 5 and not by_planet["Saturn"].beholds_hyleg
    assert by_planet["Mars"].essential_points == 5 and not by_planet["Mars"].beholds_hyleg
    assert by_planet["Venus"].aspect_to_hyleg == "trine"
    assert (det.years_least, det.years_mean, det.years_greater) == PTOLEMAIC_YEARS["Venus"]
    assert det.sign_ruler_of_hyleg == "Saturn"
    # Every beholding, dignified contender scores no more than the chosen one.
    chosen = by_planet["Venus"].essential_points
    assert all(
        c.essential_points <= chosen
        for c in det.candidates
        if c.beholds_hyleg and c.planet != "Sun"
    )


def test_luminary_hyleg_in_own_exaltation_is_its_own_alcocoden() -> None:
    # Equal cusps from 5 Cancer: the 10th cusp is 5 Aries, and the Sun at
    # 15 Aries stands in the 10th, exalted (Lilly III ch. CIV p. 530).
    cusps = [(95.0 + 30.0 * i) % 360.0 for i in range(12)]
    positions = {
        "Sun": 15.0, "Moon": 200.0, "Mercury": 20.0, "Venus": 40.0,
        "Mars": 200.0, "Jupiter": 250.0, "Saturn": 300.0,
    }
    det = find_alcocoden_lilly_1647(positions, cusps, True)
    assert det.hyleg.hyleg == "Sun"
    assert det.alcocoden == "Sun"
    assert det.selection_basis == "luminary_hyleg_in_own_domicile_or_exaltation"
    assert det.alcocoden_house == 10
    assert det.angular_in_first_or_tenth is True


def test_alcocoden_not_evaluable_when_no_dignified_planet_beholds() -> None:
    # Sun hyleg at 10 Capricorn by day. Dignified there: Saturn 5, Mars 5,
    # Venus 3, Mercury 2. None of them beholds 10 Capricorn within its orb:
    # Saturn 20 deg past it (orb 9), Mars 10 deg off the square (orb 7),
    # Venus at 25 Taurus 15 deg off the trine, Mercury 10 deg off the square.
    positions = {
        "Sun": 280.0, "Moon": 100.0, "Mercury": 20.0, "Venus": 55.0,
        "Mars": 200.0, "Jupiter": 250.0, "Saturn": 300.0,
    }
    det = find_alcocoden_lilly_1647(positions, _CUSPS, True)
    assert det.status is AlcocodenStatus.NOT_EVALUABLE
    assert det.alcocoden is None
    assert det.reason == "no_dignified_planet_beholds_hyleg"


def test_alcocoden_not_evaluable_when_hyleg_is_not() -> None:
    positions = {
        "Sun": 220.0, "Moon": 340.0, "Mercury": 20.0, "Venus": 40.0,
        "Mars": 200.0, "Jupiter": 250.0, "Saturn": 300.0,
    }
    det = find_alcocoden_lilly_1647(positions, _CUSPS, True)
    assert det.status is AlcocodenStatus.NOT_EVALUABLE
    assert det.reason.startswith("hyleg_not_evaluable:")
    assert det.candidates == ()


def test_alcocoden_requires_all_seven_planets() -> None:
    with pytest.raises(ValueError, match="missing"):
        find_alcocoden_lilly_1647({"Sun": 280.0, "Moon": 100.0}, _CUSPS, True)
