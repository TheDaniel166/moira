"""
Shared helper for integration tests that cross-check a custom Type-13
kernel against a live JPL Horizons OBSERVER product (geocentric ecliptic
lon/lat). Used by test_custom_type13_kaepaokaawela_kernel.py and
test_custom_type13_aylochaxnim_kernel.py.
"""

from __future__ import annotations

import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from moira.julian import calendar_datetime_from_jd

_HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"


def observer_ecliptic_horizons(command: str, jd_ut: float) -> tuple[float, float]:
    """Return (ecliptic_longitude_deg, ecliptic_latitude_deg) from a live Horizons OBSERVER query."""
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
        f"Could not parse Horizons observer ecliptic response for command={command!r}.\n"
        f"--- raw response (first 40 lines) ---\n{preview}"
    )


def angle_diff_arcsec(a: float, b: float) -> float:
    """Signed shortest angular distance between two degree values, in arcseconds."""
    return ((a - b + 180.0) % 360.0 - 180.0) * 3600.0
