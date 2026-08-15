from __future__ import annotations

import pytest

from moira.nodes import true_node
from moira.planets import planet_at


def _angular_difference_arcsec(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0 - 180.0) * 3600.0


def _moon_geometric_ecliptic(reader, jd_tt: float) -> tuple[float, float]:
    moon = planet_at(
        "Moon",
        jd_tt,
        reader=reader,
        jd_tt=jd_tt,
        apparent=False,
        aberration=False,
        grav_deflection=False,
        nutation=True,
    )
    return moon.longitude, moon.latitude


def _ascending_crossing_tt(reader, seed_tt: float) -> float:
    step_days = 0.25
    previous_tt = seed_tt - 20.0
    previous_latitude = _moon_geometric_ecliptic(reader, previous_tt)[1]
    jd_tt = previous_tt + step_days

    while jd_tt < seed_tt + 20.0:
        latitude = _moon_geometric_ecliptic(reader, jd_tt)[1]
        if previous_latitude < 0.0 <= latitude:
            lower = jd_tt - step_days
            upper = jd_tt
            for _ in range(60):
                midpoint = (lower + upper) / 2.0
                if _moon_geometric_ecliptic(reader, midpoint)[1] < 0.0:
                    lower = midpoint
                else:
                    upper = midpoint
            return (lower + upper) / 2.0
        previous_latitude = latitude
        jd_tt += step_days

    raise AssertionError(f"no ascending lunar crossing near TT {seed_tt}")


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("seed_tt", [2439528.1944444445, 2461199.9375])
def test_true_node_equals_moon_longitude_at_ascending_crossing(
    reader,
    seed_tt: float,
) -> None:
    """First-principles invariant: at β=0 ascending, the Moon is the node line."""
    crossing_tt = _ascending_crossing_tt(reader, seed_tt)
    moon_longitude, moon_latitude = _moon_geometric_ecliptic(reader, crossing_tt)
    node_longitude = true_node(
        crossing_tt,
        reader=reader,
        jd_tt=crossing_tt,
    ).longitude

    assert abs(moon_latitude * 3600.0) < 0.00001
    assert abs(_angular_difference_arcsec(node_longitude, moon_longitude)) < 0.001


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("jd_tt", "swiss_true_node"),
    [
        pytest.param(
            2314654.0,
            173.83721162074826,
            id="swe_calc-ipl11-1625",
        ),
        pytest.param(
            2450333.25,
            188.27945684618007,
            id="swe_nod_aps-method2-1996",
        ),
    ],
)
def test_true_node_is_corroborated_by_shipped_swiss_fixture(
    reader,
    jd_tt: float,
    swiss_true_node: float,
) -> None:
    """Secondary corroboration, not primary proof.

    Provenance: ``tests/fixtures/swe_t.exp``, Swiss Ephemeris 2.10.02a.
    The 1625 value is ``swe_calc`` body 11 with ``SEFLG_SPEED``; the 1996
    value is the Moon's ascending node from ``swe_nod_aps`` method 2.
    Both are true-ecliptic-of-date longitudes in degrees. The 0.5 arcsecond
    tolerance admits the independent DE441-versus-Swiss product difference.
    """
    actual = true_node(jd_tt, reader=reader, jd_tt=jd_tt).longitude

    assert abs(_angular_difference_arcsec(actual, swiss_true_node)) < 0.5


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "jd_tt",
    [
        pytest.param(2451545.0, id="j2000"),
        pytest.param(2461199.9375, id="2026"),
    ],
)
def test_true_node_speed_matches_longitude_finite_difference(reader, jd_tt: float) -> None:
    step = 0.002
    before = true_node(jd_tt, reader=reader, jd_tt=jd_tt - step).longitude
    after = true_node(jd_tt, reader=reader, jd_tt=jd_tt + step).longitude
    expected = ((after - before + 180.0) % 360.0 - 180.0) / (2.0 * step)
    actual = true_node(jd_tt, reader=reader, jd_tt=jd_tt)
    assert actual.speed == pytest.approx(expected, abs=2.0e-9)


@pytest.mark.requires_ephemeris
def test_true_node_speed_is_not_the_mean_node_constant(reader) -> None:
    actual = true_node(2461199.9375, reader=reader, jd_tt=2461199.9375).speed
    assert actual != pytest.approx(-1934.136261 / 36525.0, abs=1.0e-6)
