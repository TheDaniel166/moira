"""Hellenistic composition uses horizon-frame sect, not house numbers."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from moira.constants import HouseSystem
from moira.dignities import (
    DignitiesService,
    DignityHorizonFrame,
    HorizonHemisphere,
    calculate_dignities,
)
from moira.houses import houses_from_armc
from moira.hellenistic import HELLENISTIC_CLASSICAL_PLANETS, hellenistic_chart_profile


NATAL_DT = datetime(2000, 1, 1, tzinfo=timezone.utc)
CURRENT_DT = datetime(2024, 6, 1, tzinfo=timezone.utc)
POSITIONS = {
    "Sun": 10.0,
    "Moon": 45.0,
    "Mercury": 80.0,
    "Venus": 125.0,
    "Mars": 170.0,
    "Jupiter": 230.0,
    "Saturn": 300.0,
}
SPEEDS = {
    "Sun": 1.0,
    "Moon": 13.0,
    "Mercury": 1.2,
    "Venus": 1.0,
    "Mars": 0.5,
    "Jupiter": -0.1,
    "Saturn": 0.05,
}


def test_profile_sect_matches_horizon_frame() -> None:
    profile = hellenistic_chart_profile(
        POSITIONS,
        SPEEDS,
        {number: (number - 1) * 30.0 for number in range(1, 13)},
        15.0,
        280.0,
        NATAL_DT,
        CURRENT_DT,
    )
    dignities = calculate_dignities(
        [
            {"name": planet, "degree": POSITIONS[planet]}
            for planet in HELLENISTIC_CLASSICAL_PLANETS
        ],
        [{"number": number, "degree": (number - 1) * 30.0} for number in range(1, 13)],
        horizon_frame=DignityHorizonFrame(
            asc_longitude=15.0,
            mc_longitude=280.0,
        ),
    )
    sun = next(item for item in dignities if item.planet == "Sun")
    assert sun.sect_truth is not None
    assert profile.is_day_chart is sun.sect_truth.is_day_chart
    for planet in profile.planets:
        assert planet.sect_truth.is_day_chart is profile.is_day_chart


# ---------------------------------------------------------------------------
# Polar horizon covenant
#
# Authority: spherical astronomy. An ecliptic point (lambda, beta = 0) has
# right ascension alpha and declination delta with
#   sin(delta) = sin(eps) sin(lambda),  tan(alpha) = cos(eps) tan(lambda),
# hour angle H = ARMC - alpha, and altitude h with
#   sin(h) = sin(phi) sin(delta) + cos(phi) cos(delta) cos(H).
# The hemisphere evaluated from the Asc/MC frame must agree with the sign of
# h. Sample: ARMC every 1.25 deg (288 frames) x ecliptic longitude every 5 deg
# (72 points), skipping points within 1e-6 deg of the horizon.
# ---------------------------------------------------------------------------

OBLIQUITY = 23.4392911


def _ecliptic_altitude(longitude: float, armc: float, lat: float, eps: float) -> float:
    lam = math.radians(longitude)
    e = math.radians(eps)
    delta = math.asin(math.sin(e) * math.sin(lam))
    alpha = math.atan2(math.cos(e) * math.sin(lam), math.cos(lam))
    hour = math.radians(armc) - alpha
    phi = math.radians(lat)
    sin_h = (
        math.sin(phi) * math.sin(delta)
        + math.cos(phi) * math.cos(delta) * math.cos(hour)
    )
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_h))))


def _hemisphere_disagreements(lat: float, *, supply_latitude: bool) -> int:
    disagreements = 0
    for step in range(288):
        armc = step * 1.25
        houses = houses_from_armc(armc, OBLIQUITY, lat, HouseSystem.WHOLE_SIGN)
        frame = DignityHorizonFrame(
            asc_longitude=houses.asc,
            mc_longitude=houses.mc,
            geographic_latitude=lat if supply_latitude else None,
            obliquity=OBLIQUITY if supply_latitude else None,
        )
        for index in range(72):
            longitude = index * 5.0 + 0.5
            altitude = _ecliptic_altitude(longitude, armc, lat, OBLIQUITY)
            if abs(altitude) < 1e-6:
                continue
            truth = DignitiesService._build_horizon_truth(longitude, frame)
            if truth.hemisphere is None:
                continue
            expected = (
                HorizonHemisphere.ABOVE if altitude > 0.0 else HorizonHemisphere.BELOW
            )
            if truth.hemisphere is not expected:
                disagreements += 1
    return disagreements


@pytest.mark.parametrize("lat", [80.0, 70.0, -75.0, 51.5, -33.9, 0.0])
def test_meridian_altitude_frame_matches_true_altitude_at_all_latitudes(lat: float) -> None:
    assert _hemisphere_disagreements(lat, supply_latitude=True) == 0


def test_unsupplied_frame_is_exact_below_polar_circles_and_wrong_above() -> None:
    # The documented non-polar assumption holds below 90 - eps ...
    assert _hemisphere_disagreements(51.5, supply_latitude=False) == 0
    assert _hemisphere_disagreements(-60.0, supply_latitude=False) == 0
    # ... and is the polar inversion the meridian altitude repairs.
    assert _hemisphere_disagreements(80.0, supply_latitude=False) > 0


def test_horizon_frame_requires_latitude_and_obliquity_together() -> None:
    with pytest.raises(ValueError, match="supplied together"):
        DignityHorizonFrame(asc_longitude=10.0, mc_longitude=280.0, geographic_latitude=80.0)
    with pytest.raises(ValueError, match="obliquity must be finite"):
        DignityHorizonFrame(
            asc_longitude=10.0,
            mc_longitude=280.0,
            geographic_latitude=80.0,
            obliquity=95.0,
        )


def test_polar_profile_sect_follows_true_solar_altitude() -> None:
    # Find a polar frame where the Midheaven is below the horizon and the Sun
    # is above it, so the unsupplied frame would call this a night chart.
    lat = 80.0
    for step in range(288):
        armc = step * 1.25
        houses = houses_from_armc(armc, OBLIQUITY, lat, HouseSystem.WHOLE_SIGN)
        frame = DignityHorizonFrame(
            asc_longitude=houses.asc,
            mc_longitude=houses.mc,
            geographic_latitude=lat,
            obliquity=OBLIQUITY,
        )
        if frame.mc_altitude_deg >= 0.0:
            continue
        sun = next(
            (
                index * 5.0 + 0.5
                for index in range(72)
                if _ecliptic_altitude(index * 5.0 + 0.5, armc, lat, OBLIQUITY) > 1.0
            ),
            None,
        )
        if sun is not None:
            break
    else:
        pytest.fail("no polar frame with a below-horizon Midheaven and a risen Sun")

    positions = {**POSITIONS, "Sun": sun}
    cusps = {number: cusp for number, cusp in enumerate(houses.cusps, start=1)}
    common = dict(
        natal_positions=positions,
        natal_speeds=SPEEDS,
        house_cusps=cusps,
        asc_longitude=houses.asc,
        mc_longitude=houses.mc,
        natal_dt=NATAL_DT,
        current_dt=CURRENT_DT,
    )
    exact = hellenistic_chart_profile(
        **common,
        observer_latitude=lat,
        observer_longitude=0.0,
        obliquity=OBLIQUITY,
    )
    assumed = hellenistic_chart_profile(**common)

    assert exact.is_day_chart is True
    assert assumed.is_day_chart is False
