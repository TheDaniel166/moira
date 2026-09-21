"""
Moira -- primary_directions/keys.py
Standalone time-key doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, family classification, and arc-to-time conversion
rules for currently admitted primary-direction keys. This module is intentionally
orthogonal to primary-direction geometry and direction space.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from .._strenum import StrEnum
from numbers import Real

__all__ = [
    "PrimaryDirectionKey",
    "PrimaryDirectionKeyFamily",
    "PrimaryDirectionKeyPolicy",
    "PrimaryDirectionKeyTruth",
    "convert_arc_to_time",
    "invert_solar_arc_lon",
    "invert_solar_arc_ra",
    "primary_direction_key_truth",
]


_NAIBOD_RATE = 360.0 / 365.25
_PTOLEMY_RATE = 1.0
_CARDAN_RATE = 59.0 / 60.0 + 12.0 / 3600.0


class PrimaryDirectionKey(StrEnum):
    """Vessel: Enumeration of specific time-keys used for arc-to-year conversion."""
    PTOLEMY = "ptolemy"
    NAIBOD = "naibod"
    CARDAN = "cardan"
    SOLAR = "solar"
    SOLAR_RA_DYNAMIC = "solar_ra_dynamic"
    SOLAR_LON_DYNAMIC = "solar_lon_dynamic"


class PrimaryDirectionKeyFamily(StrEnum):
    """Vessel: Classification of time-keys as static or dynamic (solar-arc dependent)."""
    STATIC = "static"
    DYNAMIC = "dynamic"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionKeyPolicy:
    """Vessel: Governance policy for time-key selection and family derivation."""
    key: PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD

    def __post_init__(self) -> None:
        if not isinstance(self.key, PrimaryDirectionKey):
            raise ValueError(f"Unsupported primary direction key: {self.key}")

    @property
    def family(self) -> PrimaryDirectionKeyFamily:
        if self.key in (
            PrimaryDirectionKey.SOLAR_RA_DYNAMIC,
            PrimaryDirectionKey.SOLAR_LON_DYNAMIC,
        ):
            return PrimaryDirectionKeyFamily.DYNAMIC
        return PrimaryDirectionKeyFamily.STATIC


@dataclass(frozen=True, slots=True)
class PrimaryDirectionKeyTruth:
    """Vessel: Record of the exact mathematical rate and family for a specific time-key."""
    key: PrimaryDirectionKey
    family: PrimaryDirectionKeyFamily
    rate_degrees_per_year: float
    requested_key: str = ""
    fallback_applied: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.key, PrimaryDirectionKey):
            raise ValueError("PrimaryDirectionKeyTruth key must be PrimaryDirectionKey")
        if not isinstance(self.family, PrimaryDirectionKeyFamily):
            raise ValueError("PrimaryDirectionKeyTruth family must be PrimaryDirectionKeyFamily")
        expected_family = PrimaryDirectionKeyPolicy(self.key).family
        if self.family is not expected_family:
            raise ValueError(
                "PrimaryDirectionKeyTruth invariant failed: family does not match key"
            )
        if (
            not isinstance(self.rate_degrees_per_year, Real)
            or isinstance(self.rate_degrees_per_year, bool)
            or not math.isfinite(self.rate_degrees_per_year)
            or self.rate_degrees_per_year <= 0.0
        ):
            raise ValueError(
                "PrimaryDirectionKeyTruth invariant failed: rate_degrees_per_year must be positive"
            )
        if not isinstance(self.requested_key, str):
            raise ValueError("PrimaryDirectionKeyTruth requested_key must be str")
        if not isinstance(self.fallback_applied, bool):
            raise ValueError("PrimaryDirectionKeyTruth fallback_applied must be bool")
        if self.fallback_applied and self.key is not PrimaryDirectionKey.NAIBOD:
            raise ValueError(
                "PrimaryDirectionKeyTruth invariant failed: fallback must resolve to Naibod"
            )


def _resolve_key(key: str | PrimaryDirectionKey) -> tuple[PrimaryDirectionKey, bool]:
    if isinstance(key, PrimaryDirectionKey):
        return key, False
    if not isinstance(key, str):
        raise ValueError("Primary direction key must be a string or PrimaryDirectionKey")
    try:
        return PrimaryDirectionKey(str(key).lower()), False
    except ValueError:
        return PrimaryDirectionKey.NAIBOD, True


def primary_direction_key_truth(
    key: str | PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD,
    *,
    solar_rate: float | None = None,
) -> PrimaryDirectionKeyTruth:
    resolved_key, fallback_applied = _resolve_key(key)
    if resolved_key is PrimaryDirectionKey.SOLAR:
        if (
            not isinstance(solar_rate, Real)
            or isinstance(solar_rate, bool)
            or not math.isfinite(solar_rate)
            or solar_rate <= 0.0
        ):
            raise ValueError(
                "The solar primary-direction key requires an explicit positive finite natal solar rate"
            )
        resolved_rate = float(solar_rate)
    elif resolved_key is PrimaryDirectionKey.PTOLEMY:
        resolved_rate = _PTOLEMY_RATE
    elif resolved_key is PrimaryDirectionKey.CARDAN:
        resolved_rate = _CARDAN_RATE
    elif resolved_key in (
        PrimaryDirectionKey.SOLAR_RA_DYNAMIC,
        PrimaryDirectionKey.SOLAR_LON_DYNAMIC,
    ):
        if (
            isinstance(solar_rate, Real)
            and not isinstance(solar_rate, bool)
            and math.isfinite(solar_rate)
            and solar_rate > 0.0
        ):
            resolved_rate = float(solar_rate)
        else:
            resolved_rate = _NAIBOD_RATE
    else:
        resolved_rate = _NAIBOD_RATE
    policy = PrimaryDirectionKeyPolicy(resolved_key)
    # Key resolution is case-insensitive (see _resolve_key), but the recorded
    # requested_key preserves the caller's original token verbatim so that a
    # fallback remains diagnosable exactly as it was requested.
    requested = key.value if isinstance(key, PrimaryDirectionKey) else str(key)
    return PrimaryDirectionKeyTruth(
        key=resolved_key,
        family=policy.family,
        rate_degrees_per_year=resolved_rate,
        requested_key=requested,
        fallback_applied=fallback_applied,
    )


def _get_reader(reader: object = None) -> object:
    if reader is not None:
        return reader
    try:
        from ..planets import get_active_reader
        active = get_active_reader()
        if active is not None:
            return active
    except Exception:
        pass
    try:
        from .._kernel_paths import find_planetary_kernel
        from ..spk_reader import SpkReader
        kpath = find_planetary_kernel()
        if kpath is not None:
            return SpkReader(str(kpath))
    except Exception:
        pass
    return None


def invert_solar_arc_ra(
    natal_jd_ut: float,
    arc_deg: float,
    *,
    reader: object = None,
    tol_days: float = 1e-6,
) -> tuple[float, float]:
    """Invert true solar arc in Right Ascension via ephemeris bisection.

    Finds the elapsed time Y (in tropical years / ephemeris days) such that
    the Sun's equatorial progress in Right Ascension from natal_jd_ut equals arc_deg:
        (RA_sun(natal_jd_ut + Y) - RA_sun(natal_jd_ut)) = arc_deg

    Returns:
        (years, perfection_jd_ut):
            years: elapsed age in tropical years (ephemeris days of solar motion)
            perfection_jd_ut: Julian Date of perfection (natal_jd_ut + years * TROPICAL_YEAR)
    """
    if (
        not isinstance(natal_jd_ut, Real)
        or isinstance(natal_jd_ut, bool)
        or not math.isfinite(natal_jd_ut)
    ):
        raise ValueError("natal_jd_ut must be a finite real")
    if (
        not isinstance(arc_deg, Real)
        or isinstance(arc_deg, bool)
        or not math.isfinite(arc_deg)
        or arc_deg <= 0.0
    ):
        raise ValueError("arc_deg must be a positive finite real")
    if (
        not isinstance(tol_days, Real)
        or isinstance(tol_days, bool)
        or not math.isfinite(tol_days)
        or tol_days <= 0.0
    ):
        raise ValueError("tol_days must be a positive finite real")

    active_reader = _get_reader(reader)
    if active_reader is None:
        raise RuntimeError(
            "A planetary kernel reader or active kernel context is required for dynamic ephemeris inversion"
        )

    from .._solar import _solar_declination_ra
    from ..constants import TROPICAL_YEAR

    t0 = float(natal_jd_ut)
    arc = float(arc_deg)
    _, ra0 = _solar_declination_ra(t0, active_reader)

    def _delta_ra(y: float) -> float:
        _, ra_y = _solar_declination_ra(t0 + y, active_reader)
        approx = y * (360.0 / TROPICAL_YEAR)
        raw = (ra_y - ra0) % 360.0
        k = round((approx - raw) / 360.0)
        return raw + 360.0 * k

    y_low = 0.0
    y_high = arc / 0.8 + 5.0

    while _delta_ra(y_high) < arc:
        y_high *= 2.0

    while (y_high - y_low) > tol_days:
        y_mid = 0.5 * (y_low + y_high)
        f_mid = _delta_ra(y_mid) - arc
        if abs(f_mid) < 1e-12:
            y_low = y_mid
            y_high = y_mid
            break
        if f_mid < 0.0:
            y_low = y_mid
        else:
            y_high = y_mid

    y_res = 0.5 * (y_low + y_high)
    perfection_jd = t0 + y_res * TROPICAL_YEAR
    return y_res, perfection_jd


def invert_solar_arc_lon(
    natal_jd_ut: float,
    arc_deg: float,
    *,
    reader: object = None,
    tol_days: float = 1e-6,
) -> tuple[float, float]:
    """Invert true solar arc in Ecliptic Longitude via ephemeris bisection.

    Finds the elapsed time Y (in tropical years / ephemeris days) such that
    the Sun's progress in Ecliptic Longitude from natal_jd_ut equals arc_deg:
        (Lon_sun(natal_jd_ut + Y) - Lon_sun(natal_jd_ut)) = arc_deg

    Returns:
        (years, perfection_jd_ut):
            years: elapsed age in tropical years (ephemeris days of solar motion)
            perfection_jd_ut: Julian Date of perfection (natal_jd_ut + years * TROPICAL_YEAR)
    """
    if (
        not isinstance(natal_jd_ut, Real)
        or isinstance(natal_jd_ut, bool)
        or not math.isfinite(natal_jd_ut)
    ):
        raise ValueError("natal_jd_ut must be a finite real")
    if (
        not isinstance(arc_deg, Real)
        or isinstance(arc_deg, bool)
        or not math.isfinite(arc_deg)
        or arc_deg <= 0.0
    ):
        raise ValueError("arc_deg must be a positive finite real")
    if (
        not isinstance(tol_days, Real)
        or isinstance(tol_days, bool)
        or not math.isfinite(tol_days)
        or tol_days <= 0.0
    ):
        raise ValueError("tol_days must be a positive finite real")

    active_reader = _get_reader(reader)
    if active_reader is None:
        raise RuntimeError(
            "A planetary kernel reader or active kernel context is required for dynamic ephemeris inversion"
        )

    from .._solar import _solar_longitude
    from ..constants import TROPICAL_YEAR

    t0 = float(natal_jd_ut)
    arc = float(arc_deg)
    lon0 = _solar_longitude(t0, active_reader)

    def _delta_lon(y: float) -> float:
        lon_y = _solar_longitude(t0 + y, active_reader)
        approx = y * (360.0 / TROPICAL_YEAR)
        raw = (lon_y - lon0) % 360.0
        k = round((approx - raw) / 360.0)
        return raw + 360.0 * k

    y_low = 0.0
    y_high = arc / 0.8 + 5.0

    while _delta_lon(y_high) < arc:
        y_high *= 2.0

    while (y_high - y_low) > tol_days:
        y_mid = 0.5 * (y_low + y_high)
        f_mid = _delta_lon(y_mid) - arc
        if abs(f_mid) < 1e-12:
            y_low = y_mid
            y_high = y_mid
            break
        if f_mid < 0.0:
            y_low = y_mid
        else:
            y_high = y_mid

    y_res = 0.5 * (y_low + y_high)
    perfection_jd = t0 + y_res * TROPICAL_YEAR
    return y_res, perfection_jd


def convert_arc_to_time(
    arc: float,
    key: str | PrimaryDirectionKey = PrimaryDirectionKey.NAIBOD,
    *,
    solar_rate: float | None = None,
    natal_jd_ut: float | None = None,
    reader: object = None,
    tol_days: float = 1e-6,
) -> float:
    if (
        not isinstance(arc, Real)
        or isinstance(arc, bool)
        or not math.isfinite(arc)
        or arc <= 0.0
    ):
        raise ValueError("convert_arc_to_time requires a positive arc")

    resolved_key, fallback_applied = _resolve_key(key)
    if resolved_key is PrimaryDirectionKey.SOLAR_RA_DYNAMIC:
        if natal_jd_ut is not None:
            try:
                years, _ = invert_solar_arc_ra(
                    natal_jd_ut=natal_jd_ut,
                    arc_deg=arc,
                    reader=reader,
                    tol_days=tol_days,
                )
                return years
            except Exception:
                pass
        rate = (
            float(solar_rate)
            if (
                isinstance(solar_rate, Real)
                and not isinstance(solar_rate, bool)
                and math.isfinite(solar_rate)
                and solar_rate > 0.0
            )
            else _NAIBOD_RATE
        )
        return arc / rate

    if resolved_key is PrimaryDirectionKey.SOLAR_LON_DYNAMIC:
        if natal_jd_ut is not None:
            try:
                years, _ = invert_solar_arc_lon(
                    natal_jd_ut=natal_jd_ut,
                    arc_deg=arc,
                    reader=reader,
                    tol_days=tol_days,
                )
                return years
            except Exception:
                pass
        rate = (
            float(solar_rate)
            if (
                isinstance(solar_rate, Real)
                and not isinstance(solar_rate, bool)
                and math.isfinite(solar_rate)
                and solar_rate > 0.0
            )
            else _NAIBOD_RATE
        )
        return arc / rate

    truth = primary_direction_key_truth(resolved_key, solar_rate=solar_rate)
    return arc / truth.rate_degrees_per_year
