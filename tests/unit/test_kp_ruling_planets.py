"""Reader-owned examples and boundary tests for KP ruling planets."""
from datetime import date
from math import nextafter

import pytest

from moira import kp_ruling_planets


def _rulers(moon, ascendant, weekday=6, **kwargs):
    return kp_ruling_planets(
        moon_sidereal_longitude=moon, ascendant_sidereal_longitude=ascendant, weekday=weekday, **kwargs,
    )


def _roles(result):
    return tuple((role.role, role.planet) for role in result.roles)


def test_reader_vi_kandy_telephone_worked_example():
    # Reader VI pp. 125–126, at booking. Moon Capricorn 1°52′,
    # Ascendant Libra 20°22′, Sunday 21 September 1969.
    result = _rulers(271 + 52 / 60, 200 + 22 / 60, date(1969, 9, 21).weekday())
    assert _roles(result) == (
        ("day_lord", "Sun"), ("moon_star_lord", "Sun"), ("moon_sign_lord", "Saturn"),
        ("ascendant_sign_lord", "Venus"), ("ascendant_star_lord", "Jupiter"),
    )
    assert result.ruling_planets == ("Sun", "Saturn", "Venus", "Jupiter")
    assert result.node_policy == "none" and result.node_agents == ()


def test_reader_vi_friends_arrival_and_reader_iii_analysis_example():
    # Reader VI p. 127 states the signs/stars, not precise longitudes.
    # Libra 14° is in Swathi, and Taurus 15° is in Rohini.
    friends = _rulers(194, 45, date(1969, 2, 9).weekday())
    assert tuple(planet for _, planet in _roles(friends)) == ("Sun", "Rahu", "Venus", "Venus", "Moon")
    assert friends.ruling_planets == ("Sun", "Rahu", "Venus", "Moon")

    # Reader III p. 506, 7 April 1966. The instant being judged gives
    # Aries/Bharani rising. Rahu is in Taurus/Krittika in the source.
    analysis = _rulers(194, 18, date(1966, 4, 7).weekday(), node_longitudes={"Rahu": 33, "Ketu": 213})
    assert tuple(planet for _, planet in _roles(analysis)) == ("Jupiter", "Rahu", "Venus", "Mars", "Venus")
    assert tuple(dict.fromkeys(role.planet for role in analysis.roles)) == ("Jupiter", "Rahu", "Venus", "Mars")
    assert analysis.ruling_planets.count("Rahu") == 1
    assert analysis.node_agents[0].node == "Rahu"
    assert analysis.node_agents[0].represented_roles == ("moon_sign_lord",)


def test_reader_vi_sign_agents_with_counterpart_sign():
    # Reader VI p. 123 says Ketu in Gemini also represents Mercury
    # where Virgo is rising. Both Mercury-ruled signs qualify.
    result = _rulers(83, 165, weekday=2, node_longitudes={"Rahu": 247, "Ketu": 67})
    assert result.node_policy == "reader_vi_sign_agents"
    assert [(agent.node, agent.represented_planet, agent.represented_roles) for agent in result.node_agents] == [
        ("Ketu", "Mercury", ("day_lord", "moon_sign_lord", "ascendant_sign_lord")),
    ]
    assert result.ruling_planets[-1] == "Ketu"

    # Reader VI pp. 223–224 uses Ketu in Virgo to represent Mercury,
    # the lord of Wednesday. The direct test places Moon in the
    # printed Cancer/Mercury sector without reconstructing the chart.
    loan = _rulers(112 + 18 / 60, 275, weekday=2, node_longitudes={"Rahu": 330 + 52 / 60, "Ketu": 150 + 52 / 60})
    assert loan.node_agents[0].represented_planet == "Mercury"
    assert loan.node_agents[0].represented_roles == ("day_lord",)


@pytest.mark.parametrize(("weekday", "planet"), enumerate(("Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun")))
def test_reader_vi_weekday_table(weekday, planet):
    assert _rulers(1, 1, weekday).roles[0].planet == planet


def test_exact_stellar_and_sign_boundaries():
    before = _rulers(nextafter(200.0, 0.0), nextafter(30.0, 0.0))
    at = _rulers(200, 30)
    assert dict(_roles(before))["moon_star_lord"] == "Rahu"
    assert dict(_roles(at))["moon_star_lord"] == "Jupiter"
    assert dict(_roles(before))["ascendant_sign_lord"] == "Mars"
    assert dict(_roles(at))["ascendant_sign_lord"] == "Venus"
    assert dict(_roles(before))["ascendant_star_lord"] == dict(_roles(at))["ascendant_star_lord"] == "Sun"


@pytest.mark.parametrize("weekday", [-1, 7, True, "6", 6.0])
def test_invalid_weekday(weekday):
    with pytest.raises(ValueError, match="weekday"):
        _rulers(1, 1, weekday)


def test_incomplete_node_inputs():
    with pytest.raises(ValueError, match="Rahu and Ketu"):
        _rulers(1, 1, node_longitudes={"Rahu": 30})
