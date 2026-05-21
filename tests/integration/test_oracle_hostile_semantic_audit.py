"""
Oracle-hostile semantic audit for Moira.

These tests are not ordinary seam checks. They target public paths that could
remain finite, normalized, and internally coherent while still returning a
plausible lie against stronger cached authority.

The forbidden outcome is silent semantic drift.
"""
from __future__ import annotations

import json
from datetime import timezone
from pathlib import Path

import pytest

from moira.constants import Body
from moira.gauquelin import gauquelin_sector
from moira.houses import assign_house
from moira.julian import datetime_from_jd, local_sidereal_time, ut_to_tt
from moira.obliquity import nutation, true_obliquity
from moira.planets import sky_position_at
from moira.rise_set import find_phenomena, get_transit
from scripts.compare_swetest import (
    PASS_THRESHOLD,
    _angular_diff,
    _parse_gauquelin_iterations,
    _parse_iterations,
)


_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
_SWISS_FIXTURE = _FIXTURES / "swe_t.exp"
_HORIZONS_RISE_SET_FIXTURE = _FIXTURES / "horizons_rise_set_reference.json"
_JD_SECONDS = 86400.0
_ONE_MINUTE_JD = 1.0 / 1440.0
_TEN_MINUTES_JD = 10.0 / 1440.0
_PUBLIC_HOUSES_THRESHOLD_DEG = 0.0012
_ALTITUDE_THRESHOLD_DEG = 0.05
_HOUR_ANGLE_THRESHOLD_DEG = 0.05


def _fixture_text() -> str:
    return _SWISS_FIXTURE.read_text(encoding="utf-8", errors="replace")


def _datetime_safe(jd_ut: float) -> bool:
    try:
        datetime_from_jd(jd_ut)
    except Exception:
        return False
    return True


def _selected_house_cases() -> list[dict[str, object]]:
    preferred_systems = ("P", "K", "C", "R", "O", "E", "W", "B", "M", "T")
    selected: list[dict[str, object]] = []
    iterations = _parse_iterations(_fixture_text())

    for system in preferred_systems:
        for it in iterations:
            if it["hsys"] != system:
                continue
            if not _datetime_safe(float(it["jd_ut"])):
                continue
            jd_tt = ut_to_tt(float(it["jd_ut"]))
            critical_lat = 90.0 - true_obliquity(jd_tt)
            if abs(float(it["lat"])) >= critical_lat:
                continue
            selected.append(it)
            break

    assert selected, "Expected datetime-safe Swiss house cases for oracle audit"
    return selected


def _selected_gauquelin_cases(limit: int = 8) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    for it in _parse_gauquelin_iterations(_fixture_text(), imeth=0):
        if not _datetime_safe(float(it["jd_ut"])):
            continue
        selected.append(it)
        if len(selected) >= limit:
            break
    assert selected, "Expected datetime-safe Swiss Gauquelin cases for oracle audit"
    return selected


def _rise_set_cases() -> list[dict[str, object]]:
    data = json.loads(_HORIZONS_RISE_SET_FIXTURE.read_text(encoding="utf-8"))
    cases = list(data.get("cases", []))
    assert cases, "Expected offline Horizons rise/set cases for oracle audit"
    return cases


def _event_error_seconds(actual_jd: float, expected_jd: float) -> float:
    return abs(actual_jd - expected_jd) * _JD_SECONDS


def _signed_angle_diff(value: float, target: float) -> float:
    return ((value - target + 180.0) % 360.0) - 180.0


def _hour_angle_at(jd_ut: float, body: str, lat: float, lon: float, reader) -> float:
    jd_tt = ut_to_tt(jd_ut)
    dpsi, _ = nutation(jd_tt)
    obliquity = true_obliquity(jd_tt)
    lst = local_sidereal_time(jd_ut, lon, dpsi, obliquity)
    sky = sky_position_at(
        body,
        jd_ut,
        observer_lat=lat,
        observer_lon=lon,
        reader=reader,
        refraction=False,
    )
    return (lst - sky.right_ascension) % 360.0


def _sector_oracle_value(sector: int, degree_in_sector: float, sectors: int) -> float:
    value = sector + degree_in_sector / (360.0 / sectors)
    return value - sectors if value >= sectors + 1 else value


def _sector_diff(a: float, b: float, sectors: int = 36) -> float:
    diff = abs(a - b) % sectors
    return diff if diff <= sectors / 2 else sectors - diff


@pytest.mark.integration
def test_oracle_hostile_public_houses_datetime_path_matches_selected_swiss_cases(
    moira_engine,
) -> None:
    """
    Cached Swiss oracle through the public datetime facade path.

    Governing boundaries:
      - JD -> datetime -> facade.houses() public path
      - cached Swiss cusp authority
      - exact cusp ownership doctrine

    Expected invariant:
      - public house figures match the selected Swiss oracle rows
      - no unexpected fallback on non-polar supported rows
      - exact cusp equality belongs to the owning house index

    The public facade accepts UTC datetimes and explicitly converts through
    ``utc_to_ut1()`` before house computation. The cached Swiss rows are keyed
    directly by UT. This route therefore carries a slightly wider tolerance
    budget than the raw Swiss direct-JD audit.
    """
    failures: list[str] = []

    for it in _selected_house_cases():
        jd_ut = float(it["jd_ut"])
        lat = float(it["lat"])
        lon = float(it["lon"])
        system = str(it["hsys"])
        dt = datetime_from_jd(jd_ut).astimezone(timezone.utc)
        result = moira_engine.houses(dt, lat, lon, system)

        diffs = [_angular_diff(result.cusps[i], float(it["cusps"][i])) for i in range(12)]
        max_diff = max(diffs)
        if max_diff > _PUBLIC_HOUSES_THRESHOLD_DEG:
            failures.append(
                f"jd={jd_ut:.6f} sys={system} lat={lat:.2f} lon={lon:.2f} "
                f"max_diff={max_diff:.6f}"
            )
            continue

        assert result.effective_system == system
        assert result.fallback is False

        for house_index, cusp in enumerate(result.cusps, start=1):
            placement = assign_house(cusp, result)
            assert placement.exact_on_cusp is True, f"sys={system} cusp {house_index} lost exactness"
            assert placement.house == house_index, f"sys={system} cusp {house_index} changed owner"

    assert not failures, "Public Swiss house oracle mismatches:\n" + "\n".join(failures)


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_oracle_hostile_public_gauquelin_pipeline_matches_selected_swiss_cases(
    moira_engine,
) -> None:
    """
    Cached Swiss Gauquelin oracle through the public sky-position path.

    Governing boundaries:
      - public apparent topocentric RA/Dec path
      - local sidereal time path
      - downstream sector semantics

    Expected invariant:
      - the public route reaches the same sector truth as the cached Swiss row
      - no finite but semantically false sector drift
    """
    failures: list[str] = []

    for it in _selected_gauquelin_cases():
        jd_ut = float(it["jd_ut"])
        lat = float(it["lat"])
        lon = float(it["lon"])
        dt = datetime_from_jd(jd_ut).astimezone(timezone.utc)
        sky = moira_engine.sky_position(dt, Body.SUN, lat, lon)

        jd_tt = ut_to_tt(jd_ut)
        dpsi, _ = nutation(jd_tt)
        obliquity = true_obliquity(jd_tt)
        lst = local_sidereal_time(jd_ut, lon, dpsi, obliquity)

        position = gauquelin_sector(
            sky.right_ascension,
            sky.declination,
            lat,
            lst,
            horizon_altitude=0.0,
        )
        moira_gp = _sector_oracle_value(
            position.sector,
            position.degree_in_sector,
            position.sectors,
        )
        diff = _sector_diff(moira_gp, float(it["gp"]))
        if diff > PASS_THRESHOLD:
            failures.append(
                f"jd={jd_ut:.6f} lat={lat:.2f} lon={lon:.2f} "
                f"swiss_gp={float(it['gp']):.9f} moira_gp={moira_gp:.9f} diff={diff:.9f}"
            )

    assert not failures, "Public Gauquelin oracle mismatches:\n" + "\n".join(failures)


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.skipif(
    not _HORIZONS_RISE_SET_FIXTURE.exists(),
    reason="horizons_rise_set_reference.json not found",
)
@pytest.mark.parametrize("case", _rise_set_cases(), ids=lambda case: str(case["id"]))
def test_oracle_hostile_rise_set_public_path_preserves_horizons_event_semantics(
    case: dict[str, object],
    moira_engine,
) -> None:
    """
    Offline Horizons rise/set oracle with semantic event identity checks.

    Governing boundaries:
      - public rise/set search path
      - public transit search path
      - cached Horizons event authority
      - event semantics at the solved epoch

    Expected invariant:
      - event times match the oracle window
      - rise/set epochs actually sit on the configured altitude threshold
      - transit / anti-transit epochs actually sit on the requested meridian
    """
    body = str(case["body"])
    location = dict(case["location"])
    window = dict(case["window"])
    expected = dict(case["expected_events"])
    altitude = float(case["altitude_deg"])
    threshold = float(case["threshold_seconds"])
    jd_start = float(window["jd_start"])
    lat = float(location["latitude_deg"])
    lon = float(location["longitude_deg"])

    phenomena = find_phenomena(body, jd_start, lat, lon, altitude=altitude)

    for event_name in ("Rise", "Set"):
        expected_jd = expected.get(event_name)
        actual_jd = phenomena.get(event_name)
        if expected_jd is None:
            assert actual_jd is None, f"{case['id']} unexpectedly returned {event_name}"
            continue

        assert actual_jd is not None, f"{case['id']} missing {event_name}"
        error_seconds = _event_error_seconds(float(actual_jd), float(expected_jd))
        assert error_seconds <= threshold, (
            f"{case['id']} {event_name} error {error_seconds:.2f}s exceeds {threshold:.2f}s"
        )

        before = sky_position_at(
            body,
            float(actual_jd) - _ONE_MINUTE_JD,
            observer_lat=lat,
            observer_lon=lon,
            reader=moira_engine._reader,
            refraction=False,
        ).altitude
        exact = sky_position_at(
            body,
            float(actual_jd),
            observer_lat=lat,
            observer_lon=lon,
            reader=moira_engine._reader,
            refraction=False,
        ).altitude
        after = sky_position_at(
            body,
            float(actual_jd) + _ONE_MINUTE_JD,
            observer_lat=lat,
            observer_lon=lon,
            reader=moira_engine._reader,
            refraction=False,
        ).altitude

        assert abs(exact - altitude) <= _ALTITUDE_THRESHOLD_DEG, (
            f"{case['id']} {event_name} altitude {exact:.5f} not near threshold {altitude:.5f}"
        )
        if event_name == "Rise":
            assert before < altitude < after, f"{case['id']} Rise lost crossing identity"
        else:
            assert before > altitude > after, f"{case['id']} Set lost crossing identity"

    for event_name, target_hour_angle in (("Transit", 0.0), ("AntiTransit", 180.0)):
        actual_jd = get_transit(body, jd_start, lat, lon, upper=(event_name == "Transit"))
        expected_jd = float(expected[event_name])
        error_seconds = _event_error_seconds(actual_jd, expected_jd)
        assert error_seconds <= threshold, (
            f"{case['id']} {event_name} error {error_seconds:.2f}s exceeds {threshold:.2f}s"
        )

        target_alt = sky_position_at(
            body,
            actual_jd,
            observer_lat=lat,
            observer_lon=lon,
            reader=moira_engine._reader,
            refraction=False,
        ).altitude
        before_alt = sky_position_at(
            body,
            actual_jd - _TEN_MINUTES_JD,
            observer_lat=lat,
            observer_lon=lon,
            reader=moira_engine._reader,
            refraction=False,
        ).altitude
        after_alt = sky_position_at(
            body,
            actual_jd + _TEN_MINUTES_JD,
            observer_lat=lat,
            observer_lon=lon,
            reader=moira_engine._reader,
            refraction=False,
        ).altitude
        hour_angle = _hour_angle_at(actual_jd, body, lat, lon, moira_engine._reader)

        assert abs(_signed_angle_diff(hour_angle, target_hour_angle)) <= _HOUR_ANGLE_THRESHOLD_DEG, (
            f"{case['id']} {event_name} lost meridian identity: HA={hour_angle:.6f}"
        )
        if event_name == "Transit":
            assert target_alt >= before_alt and target_alt >= after_alt, (
                f"{case['id']} Transit is not a local altitude maximum"
            )
        else:
            assert target_alt <= before_alt and target_alt <= after_alt, (
                f"{case['id']} AntiTransit is not a local altitude minimum"
            )
