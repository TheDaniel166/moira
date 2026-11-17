"""One-sided witnesses for the interior of a swept central-eclipse footprint.

An instantaneous WGS-84 interior witness also belongs to the interior of any
time union containing that instant, relative to the ellipsoid's surface
topology. Failure to find one says nothing about whether a site lies on the
union boundary. This module never draws or claims a complete swept footprint.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from typing import Iterable, Literal, Sequence

from ._ephemeris_time import _ut1_to_ephemeris_tt
from .constants import MOON_RADIUS_KM, SUN_RADIUS_KM

__all__ = ["CentralShadowInterior", "CentralShadowSnapshot", "SweptCentralInterior",
           "SolarSweptDomainError", "central_shadow_interior", "inspect_swept_central_interior"]


class SolarSweptDomainError(ValueError):
    """The vector geometry is invalid or outside the foreground domain."""


@dataclass(frozen=True, slots=True)
class CentralShadowInterior:
    """Instantaneous local predicate; all margins are angular radians."""
    status: Literal["interior_witness", "unresolved"]
    phase: Literal["total", "annular"] | None
    central_margin_rad: float
    sun_altitude_rad: float
    separation_rad: float
    sun_radius_rad: float
    moon_radius_rad: float
    tolerance_rad: float


@dataclass(frozen=True, slots=True)
class CentralShadowSnapshot:
    """Hold a central-shadow interior at its stated UT1 and TT epochs."""

    jd_ut1: float
    jd_tt: float
    ephemeris: str
    geometry: CentralShadowInterior


@dataclass(frozen=True, slots=True)
class SweptCentralInterior:
    """One positive interior witness, or an inconclusive finite sample."""
    status: Literal["interior_witness", "unresolved"]
    witness: CentralShadowSnapshot | None
    samples: tuple[CentralShadowSnapshot, ...]
    interval_ut1: tuple[float, float]
    latitude_deg: float
    longitude_deg: float
    lunation: int | None
    surface_policy: str
    vector_policy: str
    horizon_policy: str
    complete: Literal[False] = False


def _number(x, name):
    if isinstance(x, bool) or not isinstance(x, Real):
        raise TypeError(f"{name} must be a real number")
    x = float(x)
    if not math.isfinite(x):
        raise ValueError(f"{name} must be finite")
    return x


def _vector(raw: Sequence[float], name: str) -> tuple[float, float, float]:
    try:
        if len(raw) != 3:
            raise ValueError
        value = tuple(float(x) for x in raw)
        length = math.hypot(*value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise SolarSweptDomainError(f"{name} must be a finite nonzero three-vector") from exc
    if not math.isfinite(length) or length == 0:
        raise SolarSweptDomainError(f"{name} must be a finite nonzero three-vector")
    return value  # type: ignore[return-value]


def central_shadow_interior(
    sun_vector_km: Sequence[float],
    moon_vector_km: Sequence[float],
    zenith_direction: Sequence[float],
    *,
    sun_radius_km: float = SUN_RADIUS_KM,
    moon_radius_km: float = MOON_RADIUS_KM,
    tolerance_rad: float = 1e-12,
) -> CentralShadowInterior:
    """Test strict central containment and Sun-center daylight at one site.

    Inputs are topocentric body vectors in a common frame and local zenith.
    Strictly positive margins beyond the numerical guard imply an open local
    neighborhood inside the instantaneous visible central footprint, under
    the spherical-limb/geometric-horizon model. The guard is not a certified
    bound on all floating-point or physical-model errors.
    """
    sun = _vector(sun_vector_km, "sun_vector_km")
    moon = _vector(moon_vector_km, "moon_vector_km")
    zenith = _vector(zenith_direction, "zenith_direction")
    sr = _number(sun_radius_km, "sun_radius_km")
    mr = _number(moon_radius_km, "moon_radius_km")
    tol = _number(tolerance_rad, "tolerance_rad")
    if sr <= 0 or mr <= 0 or not 1e-12 <= tol < .1:
        raise ValueError("radii must be positive and tolerance_rad in [1e-12, 0.1)")
    ds, dm, dz = math.hypot(*sun), math.hypot(*moon), math.hypot(*zenith)
    if ds <= sr or dm <= mr or dm + mr >= ds - sr:
        raise SolarSweptDomainError("Sun and Moon foreground depth intervals must not overlap")
    s = tuple(x / ds for x in sun)
    m = tuple(x / dm for x in moon)
    z = tuple(x / dz for x in zenith)
    cross = (s[1]*m[2]-s[2]*m[1], s[2]*m[0]-s[0]*m[2], s[0]*m[1]-s[1]*m[0])
    sep = math.atan2(math.hypot(*cross), math.fsum(a*b for a,b in zip(s,m)))
    alpha, beta = math.asin(sr/ds), math.asin(mr/dm)
    sine_alt = math.fsum(a*b for a,b in zip(s,z))
    # Only bound the last-bit normalization overshoot; no sign is fabricated.
    altitude = math.asin(max(-1., min(1., sine_alt)))
    central = abs(beta-alpha)-sep
    admitted = central > tol and altitude > tol
    return CentralShadowInterior(
        status="interior_witness" if admitted else "unresolved",
        phase=("total" if beta > alpha else "annular") if admitted else None,
        central_margin_rad=central, sun_altitude_rad=altitude, separation_rad=sep,
        sun_radius_rad=alpha, moon_radius_rad=beta, tolerance_rad=tol,
    )


def inspect_swept_central_interior(
    calculator,
    latitude_deg: float,
    longitude_deg: float,
    times_ut1: Iterable[float],
    *,
    interval_ut1: tuple[float, float],
    lunation: int | None = None,
    tolerance_rad: float = 1e-12,
) -> SweptCentralInterior:
    """Check a site at supplied times in one explicitly closed UT1 interval.

    A positive witness excludes the site from the boundary of the spatial
    union over that same interval, relative to the WGS-84 surface topology
    and conditional on the declared model. Missing
    witnesses are unresolved, never evidence of absence or boundary status.
    A caller-provided lunation is metadata and is not independently verified.
    """
    from .eclipse import (
        _earth_fixed_solar_shadow, _reader_identity_at, _shadow_add, _shadow_scale,
        _shadow_subtract, _wgs84_surface_normal_unit, _wgs84_surface_xyz_km,
    )
    lat, lon = _number(latitude_deg, "latitude_deg"), _number(longitude_deg, "longitude_deg")
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("latitude/longitude must be within [-90,90] / [-180,180]")
    if lunation is not None and (isinstance(lunation, bool) or not isinstance(lunation, int)):
        raise TypeError("lunation must be an integer or None")
    try:
        start, end = interval_ut1
    except (TypeError, ValueError) as exc:
        raise ValueError("interval_ut1 must contain two bounds") from exc
    start, end = _number(start, "interval start"), _number(end, "interval end")
    if end < start:
        raise ValueError("interval_ut1 must be ordered")
    tol = _number(tolerance_rad, "tolerance_rad")
    if not 1e-12 <= tol < .1:
        raise ValueError("tolerance_rad must be in [1e-12, 0.1)")
    times = tuple(_number(value, "sample time") for value in times_ut1)
    if not times:
        raise ValueError("at least one sample time is required")
    if any(not start <= value <= end for value in times):
        raise ValueError("all sample times must lie in the supplied closed interval")
    site = _wgs84_surface_xyz_km(lat, lon)
    zenith = _wgs84_surface_normal_unit(site)
    snapshots = []
    witness = None
    for jd_ut1 in times:
        jd_tt = _ut1_to_ephemeris_tt(jd_ut1, calculator._reader)
        shadow = _earth_fixed_solar_shadow(calculator, jd_ut1, jd_tt=jd_tt)
        if shadow is None:
            raise SolarSweptDomainError("native Earth-reception shadow direction is unavailable")
        moon_xyz = _shadow_add(shadow.fundamental_plane_point_xyz_km,
                               _shadow_scale(shadow.axis_unit_away_from_sun, shadow.axis_projection_km))
        geometry = central_shadow_interior(
            _shadow_subtract(shadow.sun_xyz_from_earth_itrf_km, site),
            _shadow_subtract(moon_xyz, site), zenith, tolerance_rad=tol,
        )
        identity = _reader_identity_at(calculator._reader, jd_tt)
        snapshot = CentralShadowSnapshot(jd_ut1=jd_ut1, jd_tt=jd_tt,
                                         ephemeris=identity.summary_label if identity else "unidentified",
                                         geometry=geometry)
        snapshots.append(snapshot)
        if geometry.status == "interior_witness":
            witness = snapshot
            break
    return SweptCentralInterior(
        status="interior_witness" if witness else "unresolved", witness=witness,
        samples=tuple(snapshots), interval_ut1=(start, end), latitude_deg=lat,
        longitude_deg=lon, lunation=lunation,
        surface_policy="zero-elevation WGS-84 geodetic ellipsoid; ITRF",
        vector_policy="Earth-reception retarded Sun and Moon; native ICRF-to-ITRF transform",
        horizon_policy="geometric Sun-center altitude; no refraction or terrain",
    )
