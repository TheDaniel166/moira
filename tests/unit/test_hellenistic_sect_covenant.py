"""Hellenistic composition uses horizon-frame sect, not house numbers."""

from __future__ import annotations

from datetime import datetime, timezone

from moira.dignities import DignityHorizonFrame, calculate_dignities
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
