from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from moira._kernel_paths import find_planetary_kernel
from moira._spk_body_kernel import SmallBodyKernel
from moira.asteroids import ASTEROID_NAIF, asteroid_at
from moira.julian import calendar_datetime_from_jd, julian_day
from moira.spk_reader import KernelPool, SpkReader, use_reader_override

_ROOT = Path(__file__).resolve().parents[2]
_META = _ROOT / "tests" / "artifacts" / "kernels" / "toutatis_type13_test.metadata.json"
_HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"


def _observer_ecliptic_horizons(command: str, jd_ut: float) -> tuple[float, float]:
    cdt = calendar_datetime_from_jd(jd_ut)
    start_dt = datetime(cdt.year, cdt.month, cdt.day, 0, 0, tzinfo=timezone.utc)
    stop_dt = start_dt + timedelta(days=1)
    fmt = "%Y-%b-%d %H:%M"

    params = {
        "format": "text",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'500@399'",
        "START_TIME": f"'{start_dt.strftime(fmt)}'",
        "STOP_TIME": f"'{stop_dt.strftime(fmt)}'",
        "STEP_SIZE": "'1 d'",
        "QUANTITIES": "'31'",
        "ANG_FORMAT": "DEG",
    }
    url = _HORIZONS_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode("utf-8")

    in_data = False
    for line in text.splitlines():
        s = line.strip()
        if s == "$$SOE":
            in_data = True
            continue
        if s == "$$EOE":
            break
        if not in_data or not s:
            continue
        parts = s.split()
        if len(parts) >= 4:
            try:
                return float(parts[2]), float(parts[3])
            except ValueError:
                pass

    preview = "\n".join(text.splitlines()[:40])
    raise RuntimeError(
        "Could not parse Horizons observer ecliptic response for Toutatis.\n"
        f"--- raw response (first 40 lines) ---\n{preview}"
    )


def _angle_diff_arcsec(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0 - 180.0) * 3600.0


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_custom_toutatis_type13_kernel_round_trips_through_public_asteroid_api() -> None:
    if not _META.exists():
        pytest.skip("toutatis type13 metadata artifact is missing")

    payload = json.loads(_META.read_text(encoding="utf-8"))
    kernel_path = _ROOT / payload["output_bsp"]
    if not kernel_path.exists():
        pytest.skip("toutatis type13 BSP artifact is missing")

    planetary_path = find_planetary_kernel()
    if planetary_path is None:
        pytest.skip("no planetary kernel is installed")

    assert ASTEROID_NAIF["Toutatis"] == payload["target"]["naif_id"]

    readers = [SpkReader(planetary_path), SmallBodyKernel(kernel_path)]
    try:
        pool = KernelPool(readers)
        with use_reader_override(pool):
            coverage = payload["coverage"]
            start_jd = float(coverage["start_jd"])
            end_jd = float(coverage["end_jd"])
            midpoint_jd = float(payload["verification"]["midpoint_jd"])
            sample_jds = (start_jd + 120.0, midpoint_jd, end_jd - 120.0)

            longitudes: list[float] = []
            for jd_ut in sample_jds:
                result = asteroid_at("Toutatis", jd_ut, reader=pool)
                assert result.naif_id == 2004179
                assert math.isfinite(result.longitude)
                assert math.isfinite(result.latitude)
                assert math.isfinite(result.distance)
                assert math.isfinite(result.speed)
                longitudes.append(result.longitude)

            for earlier, later in zip(longitudes, longitudes[1:]):
                delta = ((later - earlier + 180.0) % 360.0) - 180.0
                assert abs(delta) < 180.0
    finally:
        for reader in reversed(readers):
            reader.close()


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.network
def test_custom_toutatis_type13_kernel_matches_live_horizons_observer_product() -> None:
    if not _META.exists():
        pytest.skip("toutatis type13 metadata artifact is missing")

    payload = json.loads(_META.read_text(encoding="utf-8"))
    kernel_path = _ROOT / payload["output_bsp"]
    if not kernel_path.exists():
        pytest.skip("toutatis type13 BSP artifact is missing")

    planetary_path = find_planetary_kernel()
    if planetary_path is None:
        pytest.skip("no planetary kernel is installed")

    jd_ut = julian_day(2026, 5, 9, 0.0)
    ref_lon, ref_lat = _observer_ecliptic_horizons(payload["target"]["command"], jd_ut)

    readers = [SpkReader(planetary_path), SmallBodyKernel(kernel_path)]
    try:
        pool = KernelPool(readers)
        with use_reader_override(pool):
            result = asteroid_at("Toutatis", jd_ut, reader=pool)
    finally:
        for reader in reversed(readers):
            reader.close()

    lon_err_arcsec = _angle_diff_arcsec(result.longitude, ref_lon)
    lat_err_arcsec = (result.latitude - ref_lat) * 3600.0

    assert abs(lon_err_arcsec) < 0.1, lon_err_arcsec
    assert abs(lat_err_arcsec) < 0.01, lat_err_arcsec
