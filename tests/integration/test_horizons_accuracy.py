from __future__ import annotations

import pytest

from moira.asteroids import asteroid_at
from moira.planets import planet_at
from tools.benchmark_matrix import (
    STRICT_POSITION_ASTEROID_CASES,
    STRICT_POSITION_PLANET_CASES,
    PositionCase,
)
from tools.horizons import observer_ecliptic_position, signed_arcminutes


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(
    ("body", "case"),
    [(body, case) for body, cases in STRICT_POSITION_PLANET_CASES.items() for case in cases],
    ids=[f"{body}-{case.label}" for body, cases in STRICT_POSITION_PLANET_CASES.items() for case in cases],
)
def test_planet_positions_match_horizons(body: str, case: PositionCase) -> None:
    moira = planet_at(body, case.jd_ut)
    ref = observer_ecliptic_position(case.command, case.jd_ut)

    lon_error = signed_arcminutes(moira.longitude, ref.longitude)
    lat_error = (moira.latitude - ref.latitude) * 60.0

    assert abs(lon_error) <= case.lon_tolerance_arcmin, (
        f"{body} {case.label}: longitude error {lon_error:+.4f} arcmin "
        f"exceeds {case.lon_tolerance_arcmin:.4f}"
    )
    assert abs(lat_error) <= case.lat_tolerance_arcmin, (
        f"{body} {case.label}: latitude error {lat_error:+.4f} arcmin "
        f"exceeds {case.lat_tolerance_arcmin:.4f}"
    )


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(
    ("name", "case"),
    [(name, case) for name, cases in STRICT_POSITION_ASTEROID_CASES.items() for case in cases],
    ids=[f"{name}-{case.label}" for name, cases in STRICT_POSITION_ASTEROID_CASES.items() for case in cases],
)
def test_asteroid_positions_match_horizons(name: str, case: PositionCase) -> None:
    moira = asteroid_at(name, case.jd_ut)
    ref = observer_ecliptic_position(case.command, case.jd_ut)

    lon_error = signed_arcminutes(moira.longitude, ref.longitude)
    lat_error = (moira.latitude - ref.latitude) * 60.0

    assert abs(lon_error) <= case.lon_tolerance_arcmin, (
        f"{name} {case.label}: longitude error {lon_error:+.4f} arcmin "
        f"exceeds {case.lon_tolerance_arcmin:.4f}"
    )
    assert abs(lat_error) <= case.lat_tolerance_arcmin, (
        f"{name} {case.label}: latitude error {lat_error:+.4f} arcmin "
        f"exceeds {case.lat_tolerance_arcmin:.4f}"
    )
