from __future__ import annotations

import math
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from moira.julian import datetime_from_jd
from moira.julian import jd_from_datetime
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


@dataclass(frozen=True)
class ObserverSkySample:
    jd_ut: float
    date_utc: str
    solar_marker: str
    event_marker: str
    azimuth: float
    altitude: float
    local_apparent_hour_angle_hours: float


@dataclass(frozen=True)
class ObserverEvent:
    event: str
    jd_ut: float


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
def vector_state_corrected(
    command: str,
    jd_ut: float,
    center: str = "500@399",
    vec_corr: str = "LT",
) -> VectorState:
    """
    Fetch Horizons VECTORS output with an explicit correction mode.

    Common ``vec_corr`` values:
      - ``NONE`` : geometric state
      - ``LT``   : Newtonian down-leg light-time corrected state
    """
    jd_tt = ut_to_tt(jd_ut)
    params = {
        "format": "text",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "CENTER": f"'{center}'",
        "TLIST": f"'{jd_tt}'",
        "TLIST_TYPE": "JD",
        "OUT_UNITS": "KM-S",
        "VEC_TABLE": "2",
        "VEC_LABELS": "NO",
        "CSV_FORMAT": "YES",
        "REF_SYSTEM": "ICRF",
        "REF_PLANE": "FRAME",
        "VEC_CORR": vec_corr,
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
    raise RuntimeError(
        f"Could not parse Horizons vector state for {command!r} with VEC_CORR={vec_corr!r}"
    )


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


def _parse_horizons_calendar_utc(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y-%b-%d %H:%M:%S").replace(tzinfo=timezone.utc)


@lru_cache(maxsize=128)
def observer_sky_samples(
    command: str,
    start_utc: str,
    stop_utc: str,
    longitude_deg: float,
    latitude_deg: float,
    elevation_km: float = 0.0,
    step_size: str = "1 m",
) -> tuple[ObserverSkySample, ...]:
    """
    Fetch topocentric azimuth/elevation and local apparent hour angle samples.

    Horizons observer tables with ``QUANTITIES='4,42'`` return apparent azimuth,
    apparent elevation, and local apparent hour angle.  These samples are used
    to derive rise/set/transit events externally without relying on Moira's own
    event solver.
    """
    params = {
        "format": "text",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "'coord@399'",
        "COORD_TYPE": "GEODETIC",
        "SITE_COORD": f"'{longitude_deg},{latitude_deg},{elevation_km}'",
        "START_TIME": f"'{start_utc}'",
        "STOP_TIME": f"'{stop_utc}'",
        "STEP_SIZE": f"'{step_size}'",
        "TIME_TYPE": "UT",
        "TIME_DIGITS": "SECONDS",
        "QUANTITIES": "'4,42'",
        "CSV_FORMAT": "YES",
        "ANG_FORMAT": "DEG",
    }
    text = _request_text(params)

    in_data = False
    rows: list[ObserverSkySample] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "$$SOE":
            in_data = True
            continue
        if stripped == "$$EOE":
            break
        if not in_data or not stripped:
            continue

        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 6:
            continue
        try:
            dt = _parse_horizons_calendar_utc(parts[0])
            rows.append(
                ObserverSkySample(
                    jd_ut=jd_from_datetime(dt),
                    date_utc=parts[0].strip(),
                    solar_marker=parts[1],
                    event_marker=parts[2],
                    azimuth=float(parts[3]),
                    altitude=float(parts[4]),
                    local_apparent_hour_angle_hours=float(parts[5]),
                )
            )
        except ValueError:
            continue

    if rows:
        return tuple(rows)
    if error := _extract_error(text):
        raise RuntimeError(f"Horizons error for {command!r}: {error}")
    raise RuntimeError(f"Could not parse Horizons observer sky samples for {command!r}")


def _linear_root(x0: float, y0: float, x1: float, y1: float) -> float:
    if y1 == y0:
        return (x0 + x1) / 2.0
    return x0 + (-y0) * (x1 - x0) / (y1 - y0)


def _wrapped_hour_angle_diff(lha_hours: float, target_hours: float) -> float:
    value = lha_hours % 24.0
    return ((value - target_hours + 12.0) % 24.0) - 12.0


def observer_event_times(
    command: str,
    jd_start: float,
    latitude_deg: float,
    longitude_deg: float,
    *,
    altitude_deg: float,
    elevation_km: float = 0.0,
    step_size: str = "1 m",
) -> dict[str, float | None]:
    """
    Derive rise/set/transit/anti-transit times from Horizons sky samples.

    The search window is the next 24 hours from ``jd_start``.  Rise and set use
    the supplied altitude cut-off.  Upper transit is derived from the local
    apparent hour-angle zero crossing; lower transit is derived from the
    12-hour crossing.
    """
    start_dt = datetime_from_jd(jd_start).replace(tzinfo=timezone.utc)
    stop_dt = start_dt + timedelta(days=1)
    samples = observer_sky_samples(
        command,
        start_dt.strftime("%Y-%b-%d %H:%M:%S"),
        stop_dt.strftime("%Y-%b-%d %H:%M:%S"),
        longitude_deg,
        latitude_deg,
        elevation_km=elevation_km,
        step_size=step_size,
    )

    results: dict[str, float | None] = {
        "Rise": None,
        "Set": None,
        "Transit": None,
        "AntiTransit": None,
    }

    for left, right in zip(samples, samples[1:]):
        left_alt = left.altitude - altitude_deg
        right_alt = right.altitude - altitude_deg
        if results["Rise"] is None and left_alt <= 0.0 < right_alt:
            results["Rise"] = _linear_root(left.jd_ut, left_alt, right.jd_ut, right_alt)
        if results["Set"] is None and left_alt >= 0.0 > right_alt:
            results["Set"] = _linear_root(left.jd_ut, left_alt, right.jd_ut, right_alt)

        left_transit = _wrapped_hour_angle_diff(left.local_apparent_hour_angle_hours, 0.0)
        right_transit = _wrapped_hour_angle_diff(right.local_apparent_hour_angle_hours, 0.0)
        if (
            results["Transit"] is None
            and left_transit != right_transit
            and left_transit * right_transit <= 0.0
            and max(abs(left_transit), abs(right_transit)) < 1.0
        ):
            results["Transit"] = _linear_root(left.jd_ut, left_transit, right.jd_ut, right_transit)

        left_anti = _wrapped_hour_angle_diff(left.local_apparent_hour_angle_hours, 12.0)
        right_anti = _wrapped_hour_angle_diff(right.local_apparent_hour_angle_hours, 12.0)
        if (
            results["AntiTransit"] is None
            and left_anti != right_anti
            and left_anti * right_anti <= 0.0
            and max(abs(left_anti), abs(right_anti)) < 1.0
        ):
            results["AntiTransit"] = _linear_root(left.jd_ut, left_anti, right.jd_ut, right_anti)

    return results
