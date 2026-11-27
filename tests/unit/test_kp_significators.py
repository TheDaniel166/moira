"""Printed KP significator tables and exact cusp-ownership checks."""
from math import nextafter

import pytest

from moira import kp_significators


def _longitude(sign, degree, minute):
    return sign * 30 + degree + minute / 60


def _longitudes(cusps, planets):
    return dict(
        cusp_longitudes=tuple(_longitude(*cusp) for cusp in cusps),
        planet_longitudes={name: _longitude(*position) for name, position in planets.items()},
    )


def _tiers(house):
    return tuple(
        {entry.planet for entry in house.significators if any(link.rank == rank for link in entry.evidence)}
        for rank in (1, 2, 3, 4)
    )


def test_bhatt_example_birth_horoscope_all_direct_ranks():
    # Nakshatra Chintamani, printed pp. 11 and 18. Read all four
    # columns from p.18, which makes one occupation assignment per point.
    chart = _longitudes(
        [(9, 12, 25), (10, 19, 44), (11, 25, 44), (0, 25, 44), (1, 21, 28), (2, 15, 44),
         (3, 12, 25), (4, 19, 44), (5, 25, 44), (6, 25, 44), (7, 21, 28), (8, 15, 44)],
        {
            "Sun": (2, 22, 33), "Moon": (11, 21, 49), "Mercury": (3, 13, 2),
            "Venus": (2, 23, 0), "Mars": (4, 1, 40), "Jupiter": (7, 14, 2),
            "Saturn": (1, 7, 30), "Rahu": (11, 24, 36), "Ketu": (5, 24, 36),
        },
    )
    hp = kp_significators(**chart)
    printed = (
        ("", "", "Mercury Jupiter", "Saturn"),
        ("", "Moon Rahu", "Mercury Jupiter", "Saturn"),
        ("", "", "Sun Venus", "Jupiter"),
        ("Mercury Jupiter", "Saturn", "Ketu", "Mars"),
        ("", "", "", "Venus"),
        ("Saturn", "Sun Venus", "Moon Rahu", "Mercury"),
        ("Moon Rahu Ketu", "Mercury Mars", "", "Moon"),
        ("Mars", "Ketu", "Saturn", "Sun"),
        ("", "", "Moon Rahu", "Mercury"),
        ("Sun Venus", "Jupiter", "", "Venus"),
        ("", "", "Ketu", "Mars"),
        ("", "", "Sun Venus", "Jupiter"),
    )
    for number, (house, row) in enumerate(zip(hp.houses, printed, strict=True), 1):
        assert house.house == number
        assert _tiers(house) == tuple(set(cell.split()) for cell in row)
        assert len({entry.planet for entry in house.significators}) == len(house.significators)
        ranks = [entry.strongest_rank for entry in house.significators]
        assert ranks == sorted(ranks)
    venus = next(entry for entry in hp.houses[9].significators if entry.planet == "Venus")
    assert venus.strongest_rank == 1
    assert [(link.rank, link.via) for link in venus.evidence] == [(1, "Jupiter"), (4, "Venus")]
    assert next(p for p in hp.placements if p.planet == "Ketu").occupied_house == 8

    reordered = dict(reversed(tuple(chart["planet_longitudes"].items())))
    assert kp_significators(planet_longitudes=reordered, cusp_longitudes=chart["cusp_longitudes"]) == hp


def test_reader_iii_overseas_rows_and_moon_discrepancy():
    # Reader III, pp. 314–315. A damaged digit in Venus's printed minute
    # has no effect on the verified star or house for 25°10′ to 25°19′.
    cusps = [
        (6, 11, 14), (7, 9, 51), (8, 10, 51), (9, 12, 51), (10, 14, 51), (11, 14, 51),
        (0, 11, 14), (1, 9, 51), (2, 10, 51), (3, 12, 51), (4, 14, 51), (5, 14, 51),
    ]
    planets = {
        "Sun": (8, 15, 0), "Moon": (6, 26, 21), "Mercury": (7, 29, 27), "Venus": (8, 25, 10),
        "Mars": (0, 15, 11), "Jupiter": (10, 3, 21), "Saturn": (7, 10, 24),
        "Rahu": (2, 14, 18), "Ketu": (8, 14, 18),
    }
    for venus_minute in range(10, 20):
        planets["Venus"] = (8, 25, venus_minute)
        hp = kp_significators(**_longitudes(cusps, planets))
        assert _tiers(hp.houses[8]) == ({"Rahu"}, {"Rahu"}, {"Mercury"}, {"Mercury"})
        assert _tiers(hp.houses[11]) == (set(), set(), {"Mercury"}, {"Mercury"})
        # The printed Moon is in Vishakha. Its rank-three contribution
        # follows the rule and exposes a contradiction in the p.315 prose.
        assert _tiers(hp.houses[2]) == ({"Ketu", "Sun", "Venus", "Mars"}, {"Ketu", "Sun", "Venus"},
                                       {"Moon"}, {"Jupiter"})


@pytest.mark.parametrize("second", [0.0, 20.0])
def test_cusp_occupancy_owns_exact_boundary_and_adjacent_floats(second):
    cusps = tuple((second + 30 * i) % 360 for i in range(-1, 11))
    planets = dict.fromkeys(("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"), 10)
    planets.update(
        Sun=second,
        Moon=nextafter(second, 0) if second else nextafter(360.0, 0),
        Mercury=nextafter(second, 360),
    )
    result = kp_significators(planet_longitudes=planets, cusp_longitudes=cusps)
    occupied = {p.planet: p.occupied_house for p in result.placements}
    assert (occupied["Sun"], occupied["Moon"], occupied["Mercury"]) == (2, 1, 2)
    expected_lord = "Mars"
    assert result.houses[1].cusp_lord == expected_lord


@pytest.mark.parametrize("case", ["missing", "extra", "duplicate", "unordered", "short", "nonfinite", "text"])
def test_reject_incomplete_or_invalid_geometry(case):
    planets = dict.fromkeys(("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu"), 1)
    cusps = list(range(0, 360, 30))
    if case == "missing":
        del planets["Ketu"]
    elif case == "extra":
        planets["Uranus"] = 40
    elif case == "duplicate":
        cusps[1] = cusps[0]
    elif case == "unordered":
        cusps[1], cusps[2] = cusps[2], cusps[1]
    elif case == "short":
        cusps.pop()
    elif case == "nonfinite":
        cusps[0] = float("inf")
    else:
        planets["Rahu"] = "30"
    with pytest.raises((TypeError, ValueError)):
        kp_significators(planet_longitudes=planets, cusp_longitudes=cusps)
