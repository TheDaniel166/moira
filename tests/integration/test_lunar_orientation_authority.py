from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira._lunar_apparent import lunar_apparent_context
from moira._lunar_orientation_resources import lunar_me_rotation
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.lunar_orientation import LunarObserver, lunar_orientation_at
from moira.spk_reader import SpkReader


_FIXTURES = Path(__file__).parents[1] / "fixtures"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def _circular_residual(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def test_authority_fixture_receipts_are_disjoint_and_convention_explicit() -> None:
    calibration = _load("lunar_orientation_horizons_calibration.json")
    holdout = _load("lunar_orientation_horizons_holdout.json")
    svs = _load("lunar_orientation_svs_2026_holdout.json")
    assert calibration["quantities"] == [14, 15, 16, 17]
    assert holdout["quantities"] == [14, 15, 16, 17]
    assert calibration["position_angle_convention"] == (
        "counter-clockwise from true-of-date north"
    )
    assert svs["position_angle_convention"] == (
        "counter-clockwise from J2000 celestial north"
    )
    calibration_epochs = {case["utc"] for case in calibration["cases"]}
    holdout_epochs = {case["utc"] for case in holdout["cases"]}
    assert calibration_epochs.isdisjoint(holdout_epochs)
    for fixture in (calibration, holdout):
        for case in fixture["cases"]:
            assert "QUANTITIES=%2714%2C15%2C16%2C17%27" in case["query_url"]
            assert case["response_byte_length"] > 0
            assert len(case["response_sha256"]) == 64
    assert svs["source_byte_length"] > 0
    assert len(svs["source_sha256"]) == 64


def _j2000_axis_pa(jd_ut1: float, reader: SpkReader) -> float:
    context = lunar_apparent_context(jd_ut1, observer=None, reader=reader)
    matrix = lunar_me_rotation(context.jd_tdb_lunar_emission)
    lunar_north = tuple(matrix[2][column] for column in range(3))
    los = context.observer_to_moon_icrf

    def dot(left, right):
        return sum(left[index] * right[index] for index in range(3))

    north = tuple((0.0, 0.0, 1.0)[index] - dot((0.0, 0.0, 1.0), los) * los[index] for index in range(3))
    magnitude = math.sqrt(dot(north, north))
    north = tuple(value / magnitude for value in north)
    east = (
        north[1] * los[2] - north[2] * los[1],
        north[2] * los[0] - north[0] * los[2],
        north[0] * los[1] - north[1] * los[0],
    )
    return math.degrees(math.atan2(dot(lunar_north, east), dot(lunar_north, north))) % 360.0


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "fixture_name",
    [
        "lunar_orientation_horizons_calibration.json",
        "lunar_orientation_horizons_holdout.json",
    ],
)
def test_orientation_matches_horizons_calibration_and_holdout(
    fixture_name: str,
) -> None:
    fixture = _load(fixture_name)
    path = find_planetary_kernel()
    if path is None or path.name.lower() != "de441.bsp":
        pytest.skip("DE441 is required for the lunar orientation authority test")
    with SpkReader(path) as reader:
        for case in fixture["cases"]:
            dt = datetime.fromisoformat(case["utc"].replace("Z", "+00:00"))
            observer_data = case.get("observer")
            observer = (
                None if observer_data is None else LunarObserver(**observer_data)
            )
            result = lunar_orientation_at(
                utc_to_ut1(jd_from_datetime(dt)), observer=observer, reader=reader
            )
            assert _circular_residual(
                result.sub_observer_longitude_east_deg,
                case["sub_observer_longitude_east_deg"],
            ) <= 0.001
            assert abs(result.sub_observer_latitude_deg - case["sub_observer_latitude_deg"]) <= 0.001
            assert _circular_residual(result.sub_solar_longitude_east_deg, case["sub_solar_longitude_east_deg"]) <= 0.001
            assert abs(result.sub_solar_latitude_deg - case["sub_solar_latitude_deg"]) <= 0.001
            assert _circular_residual(
                result.axis_position_angle_deg, case["axis_position_angle_deg"]
            ) <= 0.002
            assert _circular_residual(result.bright_limb_position_angle_deg, case["bright_limb_position_angle_deg"]) <= 0.02


@pytest.mark.requires_ephemeris
def test_geocentric_orientation_matches_nasa_svs_holdout() -> None:
    fixture = _load("lunar_orientation_svs_2026_holdout.json")
    assert fixture["position_angle_convention"] == "counter-clockwise from J2000 celestial north"
    path = find_planetary_kernel()
    if path is None or path.name.lower() != "de441.bsp":
        pytest.skip("DE441 is required for the lunar orientation authority test")
    with SpkReader(path) as reader:
        for case in fixture["cases"]:
            dt = datetime.fromisoformat(case["utc"].replace("Z", "+00:00"))
            jd_ut1 = utc_to_ut1(jd_from_datetime(dt))
            result = lunar_orientation_at(jd_ut1, reader=reader)
            assert _circular_residual(result.sub_observer_longitude_east_deg, case["sub_observer_longitude_east_deg"]) <= 0.01
            assert abs(result.sub_observer_latitude_deg - case["sub_observer_latitude_deg"]) <= 0.01
            assert _circular_residual(result.sub_solar_longitude_east_deg, case["sub_solar_longitude_east_deg"]) <= 0.01
            assert abs(result.sub_solar_latitude_deg - case["sub_solar_latitude_deg"]) <= 0.01
            assert _circular_residual(_j2000_axis_pa(jd_ut1, reader), case["axis_position_angle_j2000_deg"]) <= 0.01
