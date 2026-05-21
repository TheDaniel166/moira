"""
Second-wave oracle-hostile semantic audit for Moira.

This layer widens the authority surfaces beyond the first hostile pass. It
targets public fixed-star and twilight routes where an answer could remain
stable and well-formed while still becoming semantically false.

The forbidden outcome is silent semantic drift.
"""
from __future__ import annotations

import json
import importlib
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest

from moira.julian import datetime_from_jd, jd_from_datetime, tt_to_ut
from moira.rise_set import _altitude
from moira.stars import star_at


_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_STARS_SWISS_FIXTURE = _FIXTURES / "stars_swetest_reference.json"
_MAX_STAR_SWISS_LONGITUDE_ERROR_DEG = 0.01
_MAX_STAR_SWISS_LATITUDE_ERROR_DEG = 0.0025
_MAX_PUBLIC_STAR_ROUTE_DELTA_DEG = 2e-6
_MAX_TWILIGHT_USNO_ERROR_SECONDS = 120.0
_MAX_TWILIGHT_ALTITUDE_RESIDUAL_DEG = 0.05
_ONE_MINUTE_JD = 1.0 / 1440.0


def _angular_diff(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


def _load_star_reference_cases() -> list[tuple[str, str, dict[str, float]]]:
    data = json.loads(_STARS_SWISS_FIXTURE.read_text(encoding="utf-8"))
    params: list[tuple[str, str, dict[str, float]]] = []
    for case in data["cases"]:
        for star_name, ref in case["stars"].items():
            params.append((str(case["id"]), str(star_name), dict(ref)))
    assert params, "Expected fixed-star Swiss reference cases for hostile audit"
    return params


_USNO_TWILIGHT_CASES = [
    {
        "label": "Boston civil dawn",
        "lat": 42.32,
        "lon": -71.09,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "civil_dawn",
        "target_altitude": -6.0,
        "expected": datetime(2024, 6, 21, 8, 33, tzinfo=timezone.utc),
    },
    {
        "label": "Boston civil dusk",
        "lat": 42.32,
        "lon": -71.09,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "civil_dusk",
        "target_altitude": -6.0,
        "expected": datetime(2024, 6, 22, 0, 59, tzinfo=timezone.utc),
    },
    {
        "label": "Hartford nautical dawn",
        "lat": 41.76,
        "lon": -72.69,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "nautical_dawn",
        "target_altitude": -12.0,
        "expected": datetime(2024, 6, 21, 7, 58, tzinfo=timezone.utc),
    },
    {
        "label": "Hartford nautical dusk",
        "lat": 41.76,
        "lon": -72.69,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "nautical_dusk",
        "target_altitude": -12.0,
        "expected": datetime(2024, 6, 22, 1, 48, tzinfo=timezone.utc),
    },
    {
        "label": "Hartford astronomical dawn",
        "lat": 41.76,
        "lon": -72.69,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "astronomical_dawn",
        "target_altitude": -18.0,
        "expected": datetime(2024, 6, 21, 7, 5, tzinfo=timezone.utc),
    },
    {
        "label": "Hartford astronomical dusk",
        "lat": 41.76,
        "lon": -72.69,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "astronomical_dusk",
        "target_altitude": -18.0,
        "expected": datetime(2024, 6, 22, 2, 41, tzinfo=timezone.utc),
    },
]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("case_id", "star_name", "ref"),
    _load_star_reference_cases(),
    ids=[
        f"{case_id}::{star_name}"
        for case_id, star_name, _ in _load_star_reference_cases()
    ],
)
def test_oracle_hostile_public_fixed_star_path_matches_cached_swiss_reference(
    case_id: str,
    star_name: str,
    ref: dict[str, float],
    moira_engine,
) -> None:
    """
    Cached Swiss fixed-star audit through the public datetime facade path.

    Governing boundaries:
      - UTC datetime -> public fixed_star() -> TT conversion route
      - cached Swiss star authority
      - direct TT substrate route equivalence

    Expected invariant:
      - public fixed-star output matches the Swiss cached reference
      - public datetime route agrees with direct TT substrate access
      - no plausible longitude/latitude lie appears in the wrapper path

    The public wrapper is UTC-datetime based and converts through the core
    timescale helpers before calling the TT-native star engine. Route
    equivalence is therefore checked with a dedicated micro-budget rather than
    exact identity.
    """
    jd_ut = float(ref["jd_ut"])
    public = moira_engine.fixed_star(star_name, datetime_from_jd(jd_ut).astimezone(timezone.utc))
    direct = star_at(star_name, float(ref["jd_tt"]))

    lon_err = _angular_diff(public.longitude, float(ref["longitude_deg"]))
    lat_err = abs(public.latitude - float(ref["latitude_deg"]))

    assert lon_err <= _MAX_STAR_SWISS_LONGITUDE_ERROR_DEG, (
        f"{case_id} {star_name}: public longitude delta {lon_err:.10f} deg exceeds "
        f"{_MAX_STAR_SWISS_LONGITUDE_ERROR_DEG:.10f} deg"
    )
    assert lat_err <= _MAX_STAR_SWISS_LATITUDE_ERROR_DEG, (
        f"{case_id} {star_name}: public latitude delta {lat_err:.10f} deg exceeds "
        f"{_MAX_STAR_SWISS_LATITUDE_ERROR_DEG:.10f} deg"
    )
    assert _angular_diff(public.longitude, direct.longitude) <= _MAX_PUBLIC_STAR_ROUTE_DELTA_DEG
    assert abs(public.latitude - direct.latitude) <= _MAX_PUBLIC_STAR_ROUTE_DELTA_DEG


@pytest.mark.integration
def test_oracle_hostile_public_fixed_star_path_matches_erfa_anchor_cases(
    moira_engine,
) -> None:
    """
    ERFA anchor audit through the public fixed-star datetime path.

    Governing boundaries:
      - UTC datetime -> public fixed_star() path
      - ERFA fixed-star propagation authority

    Expected invariant:
      - public fixed-star answers remain aligned with the ERFA anchor corpus
      - no public-wrapper semantic drift appears across centuries
    """
    test_stars_erfa_reference = importlib.import_module("tests.integration.test_stars_erfa_reference")
    threshold = float(test_stars_erfa_reference.ERFA_ANCHOR_THRESHOLD_DEG)

    failures: list[str] = []
    for name, jd_tt in test_stars_erfa_reference.ANCHOR_CASES:
        erfa_lon, erfa_lat = test_stars_erfa_reference._erfa_fixed_star_position(
            test_stars_erfa_reference._registry_by_name()[name],
            jd_tt,
        )
        public = moira_engine.fixed_star(name, datetime_from_jd(tt_to_ut(jd_tt)).astimezone(timezone.utc))
        lon_err = _angular_diff(public.longitude, erfa_lon)
        lat_err = abs(public.latitude - erfa_lat)
        if lon_err > threshold or lat_err > threshold:
            failures.append(
                f"{name} jd_tt={jd_tt:.6f}: lon_err={lon_err:.9f} lat_err={lat_err:.9f}"
            )

    assert not failures, "Public ERFA star anchor mismatches:\n" + "\n".join(failures)


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize("case", _USNO_TWILIGHT_CASES, ids=[case["label"] for case in _USNO_TWILIGHT_CASES])
def test_oracle_hostile_public_twilight_path_preserves_usno_boundary_semantics(
    case: dict[str, object],
    moira_engine,
) -> None:
    """
    Published USNO twilight audit through the public facade path.

    Governing boundaries:
      - UTC datetime -> public twilight() path
      - published USNO twilight table authority
      - semantic identity of the returned solar-altitude crossing

    Expected invariant:
      - returned twilight time matches the published table
      - the solved epoch actually sits on the requested solar altitude boundary
      - dawn/dusk direction of crossing is preserved
    """
    dt = datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)
    twilight = moira_engine.twilight(dt, float(case["lat"]), float(case["lon"]))
    actual_jd = getattr(twilight, str(case["attr"]))
    assert actual_jd is not None

    expected_jd = jd_from_datetime(case["expected"])
    error_seconds = abs(actual_jd - expected_jd) * 86400.0
    assert error_seconds <= _MAX_TWILIGHT_USNO_ERROR_SECONDS

    target_altitude = float(case["target_altitude"])
    lat = float(case["lat"])
    lon = float(case["lon"])
    before = _altitude(actual_jd - _ONE_MINUTE_JD, lat, lon, "Sun")
    exact = _altitude(actual_jd, lat, lon, "Sun")
    after = _altitude(actual_jd + _ONE_MINUTE_JD, lat, lon, "Sun")

    assert math.isfinite(exact)
    assert abs(exact - target_altitude) <= _MAX_TWILIGHT_ALTITUDE_RESIDUAL_DEG, (
        f"{case['label']}: altitude {exact:.5f} not near threshold {target_altitude:.5f}"
    )

    attr = str(case["attr"])
    if attr.endswith("dawn"):
        assert before < target_altitude < after, f"{case['label']}: dawn lost crossing direction"
    else:
        assert before > target_altitude > after, f"{case['label']}: dusk lost crossing direction"
