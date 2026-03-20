from __future__ import annotations

import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache

from moira.julian import datetime_from_jd
from moira.julian import ut_to_tt

_HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"


def _horizons_time_string(dt) -> str:
    return dt.strftime("%Y-%b-%d %H:%M:%S")


@dataclass(frozen=True)
class ObserverEclipticPosition:
    longitude: float
    latitude: float


@dataclass(frozen=True)
class VectorState:
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float


@dataclass(frozen=True)
class ObserverSkyPosition:
    right_ascension: float
    declination: float
    azimuth: float
    altitude: float


@dataclass(frozen=True)
class ObserverApparentPosition:
    right_ascension: float
    declination: float
    distance_au: float


def _request_text(params: dict[str, str]) -> str:
    url = _HORIZONS_URL + "?" + urllib.parse.urlencode(params)
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                return resp.read().decode("utf-8")
        except HTTPError as exc:
            last_error = exc
            if exc.code != 503 or attempt == 3:
                raise
        except URLError as exc:
            last_error = exc
            if attempt == 3:
                raise
        time.sleep(1.5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def _extract_error(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if "ERROR" in stripped.upper():
            return stripped
    return None


@lru_cache(maxsize=256)
def observer_ecliptic_position(command: str, jd_ut: float) -> ObserverEclipticPosition:
    dt = datetime_from_jd(jd_ut)
    dt_next = dt + timedelta(days=1)
    params = {
        "format": "text",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'500@399'",
        "START_TIME": f"'{_horizons_time_string(dt)}'",
        "STOP_TIME": f"'{_horizons_time_string(dt_next)}'",
        "STEP_SIZE": "'1 d'",
        "QUANTITIES": "'31'",
        "ANG_FORMAT": "DEG",
    }
    text = _request_text(params)

    in_data = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "$$SOE":
            in_data = True
            continue
        if stripped == "$$EOE":
            break
        if not in_data or not stripped:
            continue

        numeric_tokens: list[float] = []
        for token in stripped.split():
            try:
                numeric_tokens.append(float(token))
            except ValueError:
                continue

        if len(numeric_tokens) >= 2:
            return ObserverEclipticPosition(
                longitude=numeric_tokens[0],
                latitude=numeric_tokens[1],
            )

    if error := _extract_error(text):
        raise RuntimeError(f"Horizons error for {command!r}: {error}")
    raise RuntimeError(f"Could not parse Horizons observer ephemeris for {command!r}")


def signed_arcminutes(a_deg: float, b_deg: float) -> float:
    return ((a_deg - b_deg + 180.0) % 360.0 - 180.0) * 60.0


@lru_cache(maxsize=256)
def observer_apparent_position(command: str, start_utc: str, stop_utc: str) -> ObserverApparentPosition:
    """
    Fetch apparent geocentric RA/Dec and distance from Horizons.

    With ``ANG_FORMAT=DEG`` and ``QUANTITIES='2,20'`` the first data row has:
      date, time, RA_deg, Dec_deg, delta_AU, deldot
    """
    params = {
        "format": "json",
        "COMMAND": f"'{command}'",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'500@399'",
        "START_TIME": f"'{start_utc}'",
        "STOP_TIME": f"'{stop_utc}'",
        "STEP_SIZE": "'1h'",
        "QUANTITIES": "'2,20'",
        "MAKE_EPHEM": "YES",
        "OBJ_DATA": "NO",
        "ANG_FORMAT": "DEG",
        "EXTRA_PREC": "YES",
    }
    text = _request_text(params)

    try:
        import json
        payload = json.loads(text)
        raw = payload.get("result", "")
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Could not decode Horizons JSON apparent-position response") from exc

    if "$$SOE" not in raw or "$$EOE" not in raw:
        if error := _extract_error(raw):
            raise RuntimeError(f"Horizons error for {command!r}: {error}")
        raise RuntimeError(f"Could not parse Horizons apparent position for {command!r}")

    line = raw[raw.index("$$SOE") + 5:raw.index("$$EOE")].strip().splitlines()[0]
    parts = line.split()
    try:
        return ObserverApparentPosition(
            right_ascension=float(parts[2]),
            declination=float(parts[3]),
            distance_au=float(parts[4]),
        )
    except (IndexError, ValueError) as exc:
        raise RuntimeError(f"Could not parse Horizons apparent position for {command!r}: {line!r}") from exc


@lru_cache(maxsize=256)
def vector_state(command: str, jd_ut: float, center: str = "500@399") -> VectorState:
    # Horizons VECTORS uses TDB-tagged epochs. Our internal state pipeline is
    # evaluated at TT from the supplied UT Julian day, and TT-TDB is negligible
    # at the current accuracy envelope, while UT-TT is not.
    jd_tt = ut_to_tt(jd_ut)
    dt = datetime_from_jd(jd_tt)
    dt_next = dt + timedelta(days=1)
    params = {
        "format": "text",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "CENTER": f"'{center}'",
        "START_TIME": f"'{_horizons_time_string(dt)}'",
        "STOP_TIME": f"'{_horizons_time_string(dt_next)}'",
        "STEP_SIZE": "'1 d'",
        "OUT_UNITS": "KM-S",
        "VEC_TABLE": "2",
        "VEC_LABELS": "NO",
        "CSV_FORMAT": "YES",
        "REF_SYSTEM": "ICRF",
        "REF_PLANE": "FRAME",
    }
    text = _request_text(params)

    in_data = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "$$SOE":
            in_data = True
            continue
        if stripped == "$$EOE":
            break
        if not in_data or not stripped:
            continue

        parts = [part.strip() for part in stripped.split(",")]
        if len(parts) < 8:
            continue
        try:
            return VectorState(
                x=float(parts[2]),
                y=float(parts[3]),
                z=float(parts[4]),
                vx=float(parts[5]),
                vy=float(parts[6]),
                vz=float(parts[7]),
            )
        except ValueError:
            continue

    if error := _extract_error(text):
        raise RuntimeError(f"Horizons error for {command!r}: {error}")
    raise RuntimeError(f"Could not parse Horizons vector state for {command!r}")


@lru_cache(maxsize=256)
def observer_sky_position(
    command: str,
    jd_ut: float,
    longitude_deg: float,
    latitude_deg: float,
    elevation_km: float = 0.0,
) -> ObserverSkyPosition:
    dt = datetime_from_jd(jd_ut)
    dt_next = dt + timedelta(days=1)
    params = {
        "format": "text",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'coord@399'",
        "COORD_TYPE": "GEODETIC",
        "SITE_COORD": f"'{longitude_deg},{latitude_deg},{elevation_km}'",
        "START_TIME": f"'{_horizons_time_string(dt)}'",
        "STOP_TIME": f"'{_horizons_time_string(dt_next)}'",
        "STEP_SIZE": "'1 d'",
        # Request apparent topocentric RA/Dec so the reference frame matches
        # sky_position_at(), which returns apparent topocentric coordinates
        # after precession and nutation. Quantity 1 returns ICRF RA/Dec and is
        # not comparable here.
        "QUANTITIES": "'2,4'",
        "ANG_FORMAT": "DEG",
    }
    text = _request_text(params)

    in_data = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "$$SOE":
            in_data = True
            continue
        if stripped == "$$EOE":
            break
        if not in_data or not stripped:
            continue

        numeric_tokens: list[float] = []
        for token in stripped.split():
            try:
                numeric_tokens.append(float(token))
            except ValueError:
                continue

        if len(numeric_tokens) >= 4:
            return ObserverSkyPosition(
                right_ascension=numeric_tokens[0],
                declination=numeric_tokens[1],
                azimuth=numeric_tokens[2],
                altitude=numeric_tokens[3],
            )

    if error := _extract_error(text):
        raise RuntimeError(f"Horizons error for {command!r}: {error}")
    raise RuntimeError(f"Could not parse Horizons sky position for {command!r}")
