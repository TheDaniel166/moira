"""Worked KP period-lord examples from Bhatt's first birth horoscope."""
import pytest

from moira import kp_period_interpretation


def _angle(sign, degree, minute):
    return sign * 30 + degree + minute / 60


@pytest.fixture
def bhatt_birth():
    # Nakshatra Chintamani, printed p. 11. Signs are zero-based here.
    return {
        "cusp_longitudes": tuple(_angle(*point) for point in (
            (9, 12, 25), (10, 19, 44), (11, 25, 44), (0, 25, 44), (1, 21, 28), (2, 15, 44),
            (3, 12, 25), (4, 19, 44), (5, 25, 44), (6, 25, 44), (7, 21, 28), (8, 15, 44),
        )),
        "planet_longitudes": {name: _angle(*point) for name, point in {
            "Sun": (2, 22, 33), "Moon": (11, 21, 49), "Mercury": (3, 13, 2),
            "Venus": (2, 23, 0), "Mars": (4, 1, 40), "Jupiter": (7, 14, 2),
            "Saturn": (1, 7, 30), "Rahu": (11, 24, 36), "Ketu": (5, 24, 36),
        }.items()},
    }


def test_bhatt_education_venus_moon_and_venus_rahu(bhatt_birth):
    # p. 24 compares an adverse Moon bhukti and a supportive Rahu bhukti
    # under the same Venus Mahadasha. Both bhukti lords use Mercury's star.
    moon_line = kp_period_interpretation(**bhatt_birth, subject="education", period_lords=("Venus", "Moon"))
    rahu_line = kp_period_interpretation(**bhatt_birth, subject="education", period_lords=("Venus", "Rahu"))
    assert (moon_line.supporting_houses, moon_line.opposing_houses) == ((4, 9, 11), (3, 8))
    assert moon_line.readings[0] == rahu_line.readings[0]
    moon, rahu = moon_line.readings[1], rahu_line.readings[1]
    assert moon.level_name == rahu.level_name == "Antardasha"
    assert moon.star_lord == rahu.star_lord
    assert (moon.star_lord.planet, moon.star_lord.occupied_house, moon.star_lord.owned_houses) == (
        "Mercury", 7, (6, 9),
    )
    assert moon.star_matches == rahu.star_matches
    assert moon.star_matches.supporting == (9,)
    assert moon.sub_lord.planet == "Sun" and moon.sub_lord.owned_houses == (8,)
    assert moon.sub_matches.opposing == (3, 8)
    assert [(entry.house, entry.significator.strongest_rank) for entry in moon.sub_evidence] == [(3, 3), (8, 4)]
    assert moon.assessment == "adverse"
    assert rahu.sub_lord.planet == "Rahu" and rahu.sub_lord.owned_houses == ()
    assert rahu.sub_matches.supporting == (9,) and rahu.sub_matches.opposing == ()
    assert rahu.assessment == "supportive"


def test_bhatt_marriage_simultaneous_direct_evidence(bhatt_birth):
    # pp. 25 and 29 select favourable marriage evidence for Venus–Rahu.
    # The pp. 18 and 30 tables also show a direct opposing link via house 6.
    result = kp_period_interpretation(
        **bhatt_birth, subject="marriage", period_lords=("Venus", "Rahu", "Jupiter", "Rahu"),
    )
    assert tuple(reading.period_lord.planet for reading in result.readings) == ("Venus", "Rahu", "Jupiter", "Rahu")
    assert result.readings[3].level_name == "Sookshma"
    bhukti = result.readings[1]
    assert bhukti.star_matches.supporting == (7,) and bhukti.star_matches.opposing == (6,)
    assert bhukti.sub_matches.supporting == (2, 7) and bhukti.sub_matches.opposing == (6,)
    assert bhukti.assessment == result.readings[3].assessment == "mixed"


def test_bhatt_sun_service_keeps_also_opposing_house(bhatt_birth):
    # p. 26 uses Jupiter occupying 10 and Saturn owning 2. The same
    # chart's Saturn owns opposing house 1, as recorded on pp. 22 and 30.
    reading, = kp_period_interpretation(**bhatt_birth, subject="service", period_lords=("Sun",)).readings
    assert reading.star_lord.planet == "Jupiter"
    assert (reading.star_lord.occupied_house, reading.star_lord.owned_houses) == (10, (3, 12))
    assert reading.star_matches.supporting == (10,)
    assert reading.sub_lord.planet == "Saturn" and reading.sub_lord.owned_houses == (1, 2)
    assert reading.sub_matches.supporting == (2, 6) and reading.sub_matches.opposing == (1,)
    assert reading.assessment == "mixed"


@pytest.mark.parametrize(("period_lords", "subject"), [
    ((), "education"), (("Sun",) * 5, "education"), (("Lagna",), "education"), (("Sun",), "health"),
])
def test_unsupported_period_inputs_are_rejected(bhatt_birth, period_lords, subject):
    with pytest.raises(ValueError):
        kp_period_interpretation(**bhatt_birth, subject=subject, period_lords=period_lords)
