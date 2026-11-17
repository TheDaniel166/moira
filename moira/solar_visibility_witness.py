"""Fixed-site common-ray solar eclipse visibility under native WGS-84.

This is an opt-in, geometric witness product. It does not change existing
solar eclipse search/classification or establish the absence of an event.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from numbers import Real
from typing import Iterable, Literal

from ._ephemeris_time import _ut1_to_ephemeris_tt
from .constants import MOON_RADIUS_KM, SUN_RADIUS_KM
from .solar_disc_visibility import SolarDiscVisibility, solar_disc_visibility

__all__ = ["SolarVisibilityDomainError", "SolarVisibilitySite", "SolarVisibilitySearch",
           "SolarVisibilityRefinement", "solar_visibility_at_site", "inspect_solar_visibility_candidates",
           "refine_solar_visibility_candidate"]


class SolarVisibilityDomainError(ValueError):
    """Native site or foreground geometry is outside the supported domain."""


@dataclass(frozen=True, slots=True)
class SolarVisibilitySite:
    """One geometric site/epoch result; directions are in terrestrial ITRF."""
    jd_ut1: float
    jd_tt: float
    latitude_deg: float
    longitude_deg: float
    lunation: int | None
    ephemeris: str
    surface_policy: str
    vector_policy: str
    horizon_policy: str
    sun_distance_km: float
    moon_distance_km: float
    geometry: SolarDiscVisibility


@dataclass(frozen=True, slots=True)
class SolarVisibilitySearch:
    """A witness from supplied samples or an unresolved numerical search."""
    status: Literal["witness_found", "unresolved"]
    witness: SolarVisibilitySite | None
    tested_count: int
    status_counts: tuple[tuple[str, int], ...]
    complete: Literal[False] = False


@dataclass(frozen=True, slots=True)
class SolarVisibilityRefinement:
    """A bounded local search result, never a global exclusion certificate."""
    status: Literal["witness_found", "unresolved"]
    witness: SolarVisibilitySite | None
    best_candidate: SolarVisibilitySite
    domain: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    iterations: int
    evaluations: int
    converged: bool
    final_step_seconds: float
    final_step_latitude_deg: float
    final_step_longitude_deg: float
    complete: Literal[False] = False


def _real(value, label):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{label} must be a real number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


def solar_visibility_at_site(
    calculator,
    jd_ut1: float,
    latitude_deg: float,
    longitude_deg: float,
    *,
    lunation: int | None = None,
    tolerance_rad: float = 1e-12,
) -> SolarVisibilitySite:
    """Evaluate one native instantaneous observer-sky common-lens geometry.

    The site is zero-elevation WGS-84; the horizon is the local ellipsoid
    tangent plane without refraction or terrain. Sun and Moon follow Moira's
    native Earth-reception retarded vectors transformed into ITRF, not a
    separate observer-reception light-time or apparent-place reduction.
    ``lunation`` is caller-supplied provenance, not inferred or verified.
    """
    from .eclipse import (
        _earth_fixed_solar_shadow, _reader_identity_at, _shadow_add,
        _shadow_scale, _shadow_subtract, _wgs84_surface_normal_unit,
        _wgs84_surface_xyz_km,
    )
    jd_ut1 = _real(jd_ut1, "jd_ut1")
    latitude_deg = _real(latitude_deg, "latitude_deg")
    longitude_deg = _real(longitude_deg, "longitude_deg")
    tolerance_rad = _real(tolerance_rad, "tolerance_rad")
    if not -90 <= latitude_deg <= 90 or not -180 <= longitude_deg <= 180:
        raise ValueError("site latitude/longitude must be within [-90,90] / [-180,180]")
    if lunation is not None and (isinstance(lunation, bool) or not isinstance(lunation, int)):
        raise TypeError("lunation must be an integer or None")
    jd_tt = _ut1_to_ephemeris_tt(jd_ut1, calculator._reader)
    shadow = _earth_fixed_solar_shadow(calculator, jd_ut1, jd_tt=jd_tt)
    if shadow is None:
        raise SolarVisibilityDomainError("native Earth-reception shadow direction is unavailable")
    site = _wgs84_surface_xyz_km(latitude_deg, longitude_deg)
    zenith = _wgs84_surface_normal_unit(site)
    moon_position = _shadow_add(shadow.fundamental_plane_point_xyz_km,
                                _shadow_scale(shadow.axis_unit_away_from_sun, shadow.axis_projection_km))
    moon = _shadow_subtract(moon_position, site)
    sun = _shadow_subtract(shadow.sun_xyz_from_earth_itrf_km, site)
    moon_dist, sun_dist = math.hypot(*moon), math.hypot(*sun)
    if (not math.isfinite(moon_dist) or not math.isfinite(sun_dist)
            or moon_dist <= MOON_RADIUS_KM or sun_dist <= SUN_RADIUS_KM
            or moon_dist + MOON_RADIUS_KM >= sun_dist - SUN_RADIUS_KM):
        raise SolarVisibilityDomainError("Moon and Sun must have nonoverlapping foreground depth intervals")
    sun_radius = math.asin(SUN_RADIUS_KM / sun_dist)
    moon_radius = math.asin(MOON_RADIUS_KM / moon_dist)
    geometry = solar_disc_visibility(sun, moon, zenith, sun_radius, moon_radius, tolerance_rad=tolerance_rad)
    identity = _reader_identity_at(calculator._reader, jd_tt)
    return SolarVisibilitySite(
        jd_ut1=jd_ut1, jd_tt=jd_tt, latitude_deg=latitude_deg, longitude_deg=longitude_deg,
        lunation=lunation, ephemeris=identity.summary_label if identity else "unidentified",
        surface_policy="zero-elevation WGS-84 ellipsoid; ITRF geodetic coordinates",
        vector_policy="Earth-reception retarded Sun and Moon; native ICRF-to-ITRF transform",
        horizon_policy="geometric local ellipsoid tangent plane; no refraction or terrain",
        sun_distance_km=sun_dist, moon_distance_km=moon_dist, geometry=geometry,
    )


def inspect_solar_visibility_candidates(
    calculator,
    candidates: Iterable[tuple[float, float, float]],
    *,
    lunation: int | None = None,
    tolerance_rad: float = 1e-12,
) -> SolarVisibilitySearch:
    """Test caller-supplied (UT1 JD, latitude, longitude) tuples in order.

    A positive result carries one strictly visible fixed-site witness. An
    exhausted set is always ``unresolved``: no time interval or geographic
    region is certified by sampling. Model and ephemeris errors propagate.
    """
    counts = Counter()
    count = 0
    for candidate in candidates:
        try:
            jd_ut1, latitude, longitude = candidate
        except (TypeError, ValueError) as exc:
            raise ValueError("each candidate must contain JD UT1, latitude, longitude") from exc
        result = solar_visibility_at_site(calculator, jd_ut1, latitude, longitude,
                                          lunation=lunation, tolerance_rad=tolerance_rad)
        count += 1
        counts[result.geometry.status] += 1
        if result.geometry.status == "visible":
            if result.geometry.witness_direction is None:
                raise ArithmeticError("visible site lacks a strict common-ray witness")
            return SolarVisibilitySearch("witness_found", result, count, tuple(sorted(counts.items())))
    if not count:
        raise ValueError("at least one candidate must be provided")
    return SolarVisibilitySearch("unresolved", None, count, tuple(sorted(counts.items())))


def refine_solar_visibility_candidate(
    calculator,
    seed: tuple[float, float, float],
    *,
    time_bounds_ut1: tuple[float, float],
    latitude_bounds_deg: tuple[float, float],
    longitude_bounds_deg: tuple[float, float],
    max_iterations: int = 80,
    time_tolerance_seconds: float = 1.0,
    angular_tolerance_deg: float = 0.001,
    tolerance_rad: float = 1e-12,
    lunation: int | None = None,
) -> SolarVisibilityRefinement:
    """Refine a supplied time/site seed inside explicit finite coordinate bounds.

    A derivative-free bounded coordinate-pattern search maximizes a heuristic:
    the smaller of angular disc overlap and common-lens maximum altitude.
    When the latter is unavailable the nonpositive overlap is used. The
    heuristic need not be continuous at degenerate/disjoint boundaries and its
    local minimum/maximum is not a certificate. Only a result whose exact
    fixed-site predicate reports ``visible`` is a positive witness. Otherwise
    the result is unresolved regardless of local convergence.

    ``converged`` describes step sizes only, not global coverage, uniqueness,
    physical model accuracy, or absence of other visible time/site components.
    Provider and unsupported-geometry exceptions propagate without conversion.
    """
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or max_iterations <= 0:
        raise ValueError("max_iterations must be a positive integer")
    time_tol = _real(time_tolerance_seconds, "time_tolerance_seconds")
    angle_tol = _real(angular_tolerance_deg, "angular_tolerance_deg")
    if time_tol <= 0 or angle_tol <= 0:
        raise ValueError("time and angular tolerances must be positive")

    def pair(raw, label):
        try:
            lo, hi = raw
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{label} must contain exactly two bounds") from exc
        lo, hi = _real(lo, label), _real(hi, label)
        if hi < lo or not math.isfinite(hi-lo):
            raise ValueError(f"{label} must be finite and ordered")
        return lo, hi

    domain = (pair(time_bounds_ut1, "time_bounds_ut1"),
              pair(latitude_bounds_deg, "latitude_bounds_deg"),
              pair(longitude_bounds_deg, "longitude_bounds_deg"))
    if domain[1][0] < -90 or domain[1][1] > 90 or domain[2][0] < -180 or domain[2][1] > 180:
        raise ValueError("latitude/longitude bounds exceed the WGS-84 coordinate domain")
    try:
        t, lat, lon = seed
    except (TypeError, ValueError) as exc:
        raise ValueError("seed must contain JD UT1, latitude, longitude") from exc
    origin = tuple(_real(x, "seed component") for x in (t, lat, lon))
    if any(not lo <= value <= hi for value, (lo, hi) in zip(origin, domain)):
        raise ValueError("seed must lie within every supplied bound")
    if (domain[0][1] > domain[0][0]
            and time_tol < 8 * max(math.ulp(domain[0][0]), math.ulp(domain[0][1])) * 86400):
        raise ValueError("time_tolerance_seconds is below the representable JD resolution")
    span = tuple(hi-lo for lo, hi in domain)
    x = tuple((value-lo)/width if width else 0. for value, (lo, _), width in zip(origin, domain, span))
    cache = {}
    witness = None
    witness_score = -math.inf

    def evaluate(coordinates):
        nonlocal witness, witness_score
        physical = tuple(lo + width*u if width else lo for u, (lo, _), width in zip(coordinates, domain, span))
        if physical not in cache:
            site = solar_visibility_at_site(calculator, *physical, lunation=lunation, tolerance_rad=tolerance_rad)
            geometry = site.geometry
            overlap = geometry.separation_margin_rad
            altitude = geometry.maximum_altitude_rad
            if not math.isfinite(overlap) or (altitude is not None and not math.isfinite(altitude)):
                raise ArithmeticError("site model returned a non-finite angular margin")
            score = min(overlap, altitude) if altitude is not None else min(overlap, 0.0)
            if geometry.status == "visible":
                if geometry.witness_direction is None:
                    raise ArithmeticError("visible site lacks a strict common-ray witness")
                if score > witness_score:
                    witness, witness_score = site, score
            cache[physical] = site, score
        return cache[physical]

    best, score = evaluate(x)
    step = 0.25
    iterations = 0
    converged = False
    for iterations in range(1, max_iterations + 1):
        steps = (step*span[0]*86400, step*span[1], step*span[2])
        if steps[0] <= time_tol and steps[1] <= angle_tol and steps[2] <= angle_tol:
            converged = True
            break
        best_trial, best_score, next_x = best, score, x
        for axis in range(3):
            if not span[axis]:
                continue
            for direction in (-1., 1.):
                trial = list(x)
                trial[axis] = min(1., max(0., trial[axis] + direction*step))
                trial = tuple(trial)
                site, candidate_score = evaluate(trial)
                if candidate_score > best_score:
                    best_trial, best_score, next_x = site, candidate_score, trial
        if best_score > score:
            best, score, x = best_trial, best_score, next_x
        else:
            step /= 2
    final_steps = (step*span[0]*86400, step*span[1], step*span[2])
    if final_steps[0] <= time_tol and final_steps[1] <= angle_tol and final_steps[2] <= angle_tol:
        converged = True
    return SolarVisibilityRefinement(
        status="witness_found" if witness is not None else "unresolved", witness=witness,
        best_candidate=best, domain=domain, iterations=iterations, evaluations=len(cache),
        converged=converged, final_step_seconds=final_steps[0],
        final_step_latitude_deg=final_steps[1], final_step_longitude_deg=final_steps[2],
    )
