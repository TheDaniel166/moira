"""Independent geometry checks for Makransky's published solar-arc method."""

import math
from datetime import datetime, timezone

import pytest

from moira.constants import HOUSE_SYSTEM_NAMES, HouseSystem
from moira.houses import calculate_houses, houses_from_armc


@pytest.mark.parametrize(
    ("armc", "latitude", "declination"),
    [
        pytest.param(0.0, 45.0, 20.0, id="ordinary-north"),
        pytest.param(37.0, 65.0, 23.44, id="northern-long-day"),
        pytest.param(37.0, 65.0, -23.44, id="northern-long-night"),
        pytest.param(37.0, -65.0, -23.44, id="southern-long-day"),
        pytest.param(37.0, -65.0, 23.44, id="southern-long-night"),
        pytest.param(37.0, 80.0, 5.0, id="arctic-sun-crosses-horizon"),
        pytest.param(12.37, -51.5, 18.38, id="southern-signed-declination"),
        pytest.param(30.0, -45.0, 0.0, id="southern-cardinal"),
        pytest.param(150.0, 45.0, 0.0, id="appendix-w-equals-180"),
    ],
)
def test_solar_subdivisions_lie_in_the_returned_house_planes(armc, latitude, declination):
    obliquity = 23.45
    result = houses_from_armc(
        armc, obliquity, latitude, HouseSystem.MAKRANSKY_SUNSHINE,
        sun_declination=declination, include_boundary_geometry=True,
    )
    assert result.effective_system == HouseSystem.MAKRANSKY_SUNSHINE
    assert not result.fallback
    assert result.cusps[::3] == pytest.approx((result.asc, result.ic, result.dsc, result.mc))
    widths = [(result.cusps[(i + 1) % 12] - cusp) % 360
              for i, cusp in enumerate(result.cusps)]
    assert all(width > 0 for width in widths)
    assert sum(widths) == pytest.approx(360, abs=1e-9)
    if declination:
        assert result.cusps[11] != pytest.approx((result.cusps[5] + 180) % 360)
    # Solve the altitude equation independently by bisection. At 65° the
    # longer arc includes subdivisions outside the appendix's MD branches.
    theta, phi, delta, epsilon = map(math.radians, (armc, latitude, declination, obliquity))
    north = (-math.sin(phi) * math.cos(theta), -math.sin(phi) * math.sin(theta), math.cos(phi))
    east = (-math.sin(theta), math.cos(theta), 0.0)
    zenith = (math.cos(phi) * math.cos(theta), math.cos(phi) * math.sin(theta), math.sin(phi))

    def dot(left, right):
        return sum(a * b for a, b in zip(left, right, strict=True))

    lower, upper = 0.0, math.pi
    for _ in range(60):
        midpoint = (lower + upper) / 2
        altitude_sine = (math.cos(phi) * math.cos(delta) * math.cos(midpoint)
                         + math.sin(phi) * math.sin(delta))
        if altitude_sine > 0:
            lower = midpoint
        else:
            upper = midpoint
    sunset = (lower + upper) / 2
    for i, boundary in enumerate(result.boundary_geometry.boundaries):
        if i < 6:
            hour_angle = -sunset - i * (2 * math.pi - 2 * sunset) / 6
        else:
            hour_angle = sunset - (i - 6) * 2 * sunset / 6
        solar_ra = theta - hour_angle
        sun = (math.cos(delta) * math.cos(solar_ra),
               math.cos(delta) * math.sin(solar_ra), math.sin(delta))
        longitude = math.radians(result.cusps[i])
        cusp = (math.cos(longitude), math.sin(longitude) * math.cos(epsilon),
                math.sin(longitude) * math.sin(epsilon))
        assert dot(boundary.plane_normal, north) == pytest.approx(0.0, abs=1e-12)
        assert dot(boundary.plane_normal, sun) == pytest.approx(0.0, abs=1e-12)
        assert dot(boundary.plane_normal, cusp) == pytest.approx(0.0, abs=1e-12)
        if i in (0, 6):
            assert dot(cusp, zenith) == pytest.approx(0.0, abs=1e-12)
            assert dot(cusp, east) * (1 if i == 0 else -1) > 0
        else:
            assert dot(cusp, zenith) * (1 if i > 6 else -1) > 0


@pytest.mark.parametrize(("latitude", "declination"), [
    (70.0, -23.0), (70.0, 23.0), (70.0, 20.0),
    (-70.0, -23.0), (-70.0, 23.0), (-70.0, -20.0),
])
def test_absent_or_tangent_solar_arc_is_an_error(latitude, declination):
    with pytest.raises(ValueError, match="distinct solar rise and set"):
        houses_from_armc(35, 23.44, latitude, HouseSystem.MAKRANSKY_SUNSHINE,
                         sun_declination=declination)


def test_southern_cardinal_cusps_are_continuous_through_exact_branch():
    exact = houses_from_armc(30, 23.45, -45, HouseSystem.MAKRANSKY_SUNSHINE,
                            sun_declination=0)
    for armc in (29.9999, 30.0001):
        nearby = houses_from_armc(armc, 23.45, -45, HouseSystem.MAKRANSKY_SUNSHINE,
                                 sun_declination=0)
        for cusp, neighbor in zip(exact.cusps, nearby.cusps, strict=True):
            assert abs((neighbor - cusp + 180) % 360 - 180) < 0.001


def test_solar_crossings_do_not_override_incompatible_chart_angles():
    with pytest.raises(ValueError, match="ordered cycle with the chart angles"):
        houses_from_armc(270, 23.45, 80, HouseSystem.MAKRANSKY_SUNSHINE,
                         sun_declination=5)


def test_explicit_declination_and_legacy_solar_longitude_have_distinct_contracts():
    with pytest.raises(ValueError, match="sun_declination"):
        houses_from_armc(0, 23.44, 45, HouseSystem.MAKRANSKY_SUNSHINE, sun_longitude=60)
    legacy = houses_from_armc(0, 23.44, 45, HouseSystem.SUNSHINE, sun_longitude=60)
    assert legacy.cusps == (90, 120, 150, 180, 210, 240, 270, 300, 330, 0, 30, 60)
    assert HOUSE_SYSTEM_NAMES[HouseSystem.SUNSHINE] == "Sun-Anchored Equal"


def test_chart_backed_path_derives_solar_declination(planetary_reader):
    from moira.planets import planet_at
    from moira.spk_reader import use_reader_override

    jd = 2451545.0
    sun = planet_at("Sun", jd, reader=planetary_reader, frame="cartesian")
    declination = math.degrees(math.atan2(sun.z, math.hypot(sun.x, sun.y)))
    with use_reader_override(planetary_reader):
        computed = calculate_houses(jd, 45, 0, HouseSystem.MAKRANSKY_SUNSHINE)
    explicit = calculate_houses(jd, 45, 0, HouseSystem.MAKRANSKY_SUNSHINE,
                                sun_declination=declination)
    assert computed.cusps == explicit.cusps


def test_equal_solar_arcs_recover_regiomontanus():
    result = houses_from_armc(123, 23.44, -42, HouseSystem.MAKRANSKY_SUNSHINE,
                              sun_declination=0)
    reference = houses_from_armc(123, 23.44, -42, HouseSystem.REGIOMONTANUS)
    assert result.cusps == pytest.approx(reference.cusps, abs=1e-9)


def test_makransky_article_tables_distinguish_the_revised_sixth_cusp(planetary_reader):
    from moira.julian import jd_from_datetime
    from moira.spk_reader import use_reader_override

    # The article's rectified 18:03:27 is interpreted on the reported
    # GDT clock (GMT+1), consistent with the printed meridian.
    jd_ut = jd_from_datetime(datetime(1889, 4, 20, 17, 3, 27, tzinfo=timezone.utc))
    with use_reader_override(planetary_reader):
        result = calculate_houses(jd_ut, 48.25, 13 + 2 / 60, HouseSystem.MAKRANSKY_SUNSHINE)
    printed = {
        1: 200 + 23 / 60, 2: 221 + 28 / 60, 3: 252 + 13 / 60,
        4: 295 + 52 / 60, 5: 334 + 45 / 60, 6: 359 + 20 / 60,
        7: 20 + 23 / 60, 8: 46 + 12 / 60, 9: 77 + 50 / 60,
        10: 115 + 52 / 60, 11: 150 + 5 / 60, 12: 176 + 31 / 60,
    }
    for house, expected in printed.items():
        residual_arcmin = ((result.cusps[house - 1] - expected + 180) % 360 - 180) * 60
        if house == 6:
            # The printed row rounds to the reflection across 0° Aries.
            # The inverse solar-arc check establishes which side is lawful.
            assert 79 < residual_arcmin < 80
            reflected = (-result.cusps[house - 1]) % 360
            assert abs(reflected - expected) * 60 < 0.5
        else:
            assert abs(residual_arcmin) < 1.1

    # The Astrological Journal, June/July 2021, revises three rows.
    revised = printed | {5: 334 + 44 / 60, 6: 38 / 60, 12: 176 + 30 / 60}
    for house, expected in revised.items():
        assert result.cusps[house - 1] == pytest.approx(expected, abs=1.6 / 60)


def test_makransky_book_test_data_matches_eight_intermediate_cusps():
    # Primary Directions: A Primer of Calculation, "Solar House Cusp
    # Algorithm", pp. 147–148. The block leaves obliquity implicit.
    result = houses_from_armc(12.37, 23.45, 51.50, HouseSystem.MAKRANSKY_SUNSHINE,
                              sun_declination=-18.38)
    printed = {
        2: 147 + 18 / 60, 3: 167 + 4 / 60, 5: 233 + 6 / 60, 6: 274 + 53 / 60,
        8: 321 + 12 / 60, 9: 340 + 33 / 60, 11: 67 + 4 / 60, 12: 105 + 29 / 60,
    }
    for house, expected in printed.items():
        assert result.cusps[house - 1] == pytest.approx(expected, abs=1 / 60)
