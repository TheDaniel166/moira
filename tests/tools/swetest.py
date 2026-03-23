from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from urllib.parse import urlencode
from urllib.request import urlopen


_SWETEST_URL = "https://www.astro.com/cgi/swetest.cgi"

_SIGN_BASE = {
    "ar": 0.0,
    "ta": 30.0,
    "ge": 60.0,
    "cn": 90.0,
    "le": 120.0,
    "vi": 150.0,
    "li": 180.0,
    "sc": 210.0,
    "sa": 240.0,
    "cp": 270.0,
    "aq": 300.0,
    "pi": 330.0,
}

_PLANET_CODES = "0123456789"
_PLANET_LINE = re.compile(
    r"^\d{6}\s+"
    r"(Sun|Moon|Mercury|Venus|Mars|Jupiter|Saturn|Uranus|Neptune|Pluto)\s+"
    r"(\d+)\s+([a-z]{2})\s+(\d+)'\s*([0-9.]+)\s+"
    r"([+\-]?[0-9.]+)"
)
_UT_LINE = re.compile(r"UT:\s+([0-9.]+)")
_TT_LINE = re.compile(r"TT:\s+([0-9.]+)")


@dataclass(frozen=True, slots=True)
class SwetestPlanetPosition:
    body: str
    longitude_deg: float
    speed_deg_per_day: float


@dataclass(frozen=True, slots=True)
class SwetestSnapshot:
    source_url: str
    datetime_utc: datetime
    jd_ut: float
    jd_tt: float
    positions: dict[str, SwetestPlanetPosition]


def swetest_url(dt_utc: datetime, planet_codes: str = _PLANET_CODES) -> str:
    dt_utc = dt_utc.astimezone(timezone.utc)
    params = {
        "arg": f"-ut{dt_utc:%H:%M:%S}",
        "b": f"{dt_utc.day}.{dt_utc.month}.{dt_utc.year}",
        "e": "-eswe",
        "f": "tPZsD",
        "n": "1",
        "p": planet_codes,
        "s": "1",
    }
    return f"{_SWETEST_URL}?{urlencode(params)}"


def fetch_swetest_snapshot(
    dt_utc: datetime,
    planet_codes: str = _PLANET_CODES,
) -> SwetestSnapshot:
    dt_utc = dt_utc.astimezone(timezone.utc)
    url = swetest_url(dt_utc, planet_codes=planet_codes)
    text = urlopen(url, timeout=30).read().decode("utf-8", errors="replace")
    return parse_swetest_snapshot(text, url=url, dt_utc=dt_utc)


def parse_swetest_snapshot(text: str, *, url: str, dt_utc: datetime) -> SwetestSnapshot:
    jd_ut: float | None = None
    jd_tt: float | None = None
    positions: dict[str, SwetestPlanetPosition] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        ut_match = _UT_LINE.search(line)
        if ut_match:
            jd_ut = float(ut_match.group(1))
            continue

        tt_match = _TT_LINE.search(line)
        if tt_match:
            jd_tt = float(tt_match.group(1))
            continue

        match = _PLANET_LINE.match(line)
        if not match:
            continue

        body = match.group(1)
        deg = int(match.group(2))
        sign = match.group(3)
        minutes = int(match.group(4))
        seconds = float(match.group(5))
        speed = float(match.group(6))

        longitude = _SIGN_BASE[sign] + deg + (minutes / 60.0) + (seconds / 3600.0)
        positions[body] = SwetestPlanetPosition(
            body=body,
            longitude_deg=longitude % 360.0,
            speed_deg_per_day=speed,
        )

    if jd_ut is None or jd_tt is None:
        raise ValueError("Failed to parse JD metadata from swetest output")
    if not positions:
        raise ValueError("Failed to parse any planet positions from swetest output")

    return SwetestSnapshot(
        source_url=url,
        datetime_utc=dt_utc,
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        positions=positions,
    )
