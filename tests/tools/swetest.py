from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
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
_FIXED_STAR_LINE = re.compile(
    r"^(.+?)\s+([+\-]?\d+(?:\.\d+)?)\s+([+\-]?\d+(?:\.\d+)?)\s+([+\-]?\d+(?:\.\d+)?)$"
)


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


@dataclass(frozen=True, slots=True)
class SwetestFixedStarPosition:
    query: str
    designation: str
    longitude_deg: float
    latitude_deg: float
    distance_au: float


@dataclass(frozen=True, slots=True)
class SwetestFixedStarSnapshot:
    source_url: str
    datetime_utc: datetime
    jd_ut: float
    jd_tt: float
    position: SwetestFixedStarPosition


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


def swetest_fixed_star_url(dt_utc: datetime, star_name: str) -> str:
    dt_utc = dt_utc.astimezone(timezone.utc)
    params = {
        "arg": f"-ut{dt_utc:%H:%M:%S} -xf{star_name}",
        "b": f"{dt_utc.day}.{dt_utc.month}.{dt_utc.year}",
        "e": "-eswe",
        "f": "PlbR",
        "n": "1",
        "p": "f",
        "s": "1",
    }
    return f"{_SWETEST_URL}?{urlencode(params)}"


def _extract_swetest_text(payload: str) -> str:
    match = re.search(r"<pre[^>]*>(.*?)</pre>", payload, re.S | re.I)
    if match:
        return unescape(match.group(1))
    return payload


def fetch_swetest_snapshot(
    dt_utc: datetime,
    planet_codes: str = _PLANET_CODES,
) -> SwetestSnapshot:
    dt_utc = dt_utc.astimezone(timezone.utc)
    url = swetest_url(dt_utc, planet_codes=planet_codes)
    text = _extract_swetest_text(urlopen(url, timeout=30).read().decode("utf-8", errors="replace"))
    return parse_swetest_snapshot(text, url=url, dt_utc=dt_utc)


def fetch_swetest_fixed_star_snapshot(
    dt_utc: datetime,
    star_name: str,
) -> SwetestFixedStarSnapshot:
    dt_utc = dt_utc.astimezone(timezone.utc)
    url = swetest_fixed_star_url(dt_utc, star_name)
    text = _extract_swetest_text(urlopen(url, timeout=30).read().decode("utf-8", errors="replace"))
    return parse_swetest_fixed_star_snapshot(text, url=url, dt_utc=dt_utc, star_name=star_name)


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


def parse_swetest_fixed_star_snapshot(
    text: str,
    *,
    url: str,
    dt_utc: datetime,
    star_name: str,
) -> SwetestFixedStarSnapshot:
    jd_ut: float | None = None
    jd_tt: float | None = None
    position: SwetestFixedStarPosition | None = None

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

        match = _FIXED_STAR_LINE.match(line)
        if not match:
            continue

        designation = match.group(1).strip()
        position = SwetestFixedStarPosition(
            query=star_name,
            designation=designation,
            longitude_deg=float(match.group(2)) % 360.0,
            latitude_deg=float(match.group(3)),
            distance_au=float(match.group(4)),
        )

    if jd_ut is None or jd_tt is None:
        raise ValueError("Failed to parse JD metadata from swetest fixed-star output")
    if position is None:
        raise ValueError(f"Failed to parse fixed-star position for {star_name!r}")

    return SwetestFixedStarSnapshot(
        source_url=url,
        datetime_utc=dt_utc,
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        position=position,
    )
