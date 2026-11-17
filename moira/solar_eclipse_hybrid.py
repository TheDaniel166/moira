"""Opt-in evidence for hybrid solar eclipses along the visible central axis.

The legacy :class:`~moira.eclipse.EclipseData` describes one instant; it is
not modified by this module.  Two lawful, daylight axis points with opposite
central-cone signs establish a hybrid under the native geometry.  A search
that finds only one sign does *not* establish its absence: sampled brackets
are not an exhaustive isolation of the continuous path.  In that case the
result is explicitly unresolved, including for apparent tangencies.

Coordinates are zero-elevation WGS-84, using the unrefracted geometric Sun
center horizon.  Epochs are UT1 binary64 Julian days; a narrow numerical
bracket is not a bound on the physical accuracy of an eclipse prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Literal

from .eclipse import (
    EclipseCalculator,
    EclipseEvent,
    _SearchLimitReached,
    _axis_surface_point_from_shadow,
    _earth_fixed_solar_shadow,
    _shadow_dot,
    _shadow_subtract,
    _solar_shadow_discs,
    _solve_solar_central_interval,
    _wgs84_surface_normal_unit,
)


@dataclass(frozen=True, slots=True)
class SolarCentralAxisWitness:
    """A directly evaluated lawful axis point, with two independent signs."""

    jd_ut: float
    latitude_deg: float
    longitude_deg: float
    signed_radius_km: float
    sun_altitude_deg: float
    angular_radius_ratio_minus_one: float


@dataclass(frozen=True, slots=True)
class SolarCentralAxisTransition:
    """A sampled sign-change bracket, not an exhaustive path root list."""

    start_jd_ut: float
    end_jd_ut: float
    direction: Literal["annular_to_total", "total_to_annular"]

    @property
    def width_seconds(self) -> float:
        return (self.end_jd_ut - self.start_jd_ut) * 86400.0


@dataclass(frozen=True, slots=True)
class SolarCentralPathClassification:
    """Native evidence for a hybrid or an explicitly unresolved path.

    ``transitions`` are only those found among sampled sign changes. They need
    not contain every transition.  Consequently ``subtype`` is unavailable:
    H2/H3 require path-end and completeness guarantees not supplied here.
    ``evaluation_count`` counts the diagnostic's shadow evaluations; the
    existing axis-interval solve has its own independent evaluation limit.
    """

    status: Literal["hybrid", "unresolved"]
    subtype: None
    reason: str
    axis_interval: tuple[float, float] | None
    annular_witness: SolarCentralAxisWitness | None
    total_witness: SolarCentralAxisWitness | None
    transitions: tuple[SolarCentralAxisTransition, ...]
    evaluation_count: int
    budget_exhausted: bool


class _EvaluationBudgetExhausted(Exception):
    """Signal exhaustion of the hybrid investigation's evaluation budget."""


def _bisect_sign_change(
    func: Callable[[float], float | None],
    left: float,
    right: float,
    max_iterations: int = 80,
) -> tuple[float, float] | None:
    """Refine a witnessed strict sign change without rounding past an endpoint.

    Invalid interior geometry yields no bracket; exceptions from ``func``
    propagate to the caller.  Sampling or bisection does not prove uniqueness.
    """

    if not math.isfinite(left) or not math.isfinite(right) or left >= right:
        return None
    fl, fr = func(left), func(right)
    if fl is None or fr is None or not math.isfinite(fl) or not math.isfinite(fr):
        return None
    if fl == 0.0 or fr == 0.0 or (fl > 0.0) == (fr > 0.0):
        return None
    for _ in range(max_iterations):
        mid = left + (right - left) / 2.0
        if mid == left or mid == right:
            break
        fm = func(mid)
        if fm is None or not math.isfinite(fm):
            return None
        if fm == 0.0:
            before, after = math.nextafter(mid, left), math.nextafter(mid, right)
            if before == left and after == right:
                break
            fb, fa = func(before), func(after)
            if (fb is not None and fa is not None and math.isfinite(fb)
                    and math.isfinite(fa) and fb != 0.0 and fa != 0.0
                    and (fb > 0.0) != (fa > 0.0)):
                return before, after
            # A rounded zero or unresolved tangent is not a strict bracket.
            return None
        if (fm > 0.0) == (fl > 0.0):
            left, fl = mid, fm
        else:
            right, fr = mid, fm
    return left, right


def _sample_epochs(left: float, right: float, greatest: float) -> tuple[float, ...]:
    """Generate candidate epochs including a sub-second endpoint ladder."""

    duration = (right - left) * 86400.0
    offsets = (0.001, 0.003, 0.01, 0.02, 0.04, 0.06, 0.08, 0.1, 0.2,
               0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
    times = {left + (right - left) * i / 64.0 for i in range(1, 64)}
    if left < greatest < right:
        times.add(greatest)
    for offset in offsets:
        if offset < duration:
            times.add(left + offset / 86400.0)
            times.add(right - offset / 86400.0)
    return tuple(sorted(time for time in times if left < time < right))


def classify_solar_central_path(
    calc: EclipseCalculator,
    event: EclipseEvent,
    *,
    max_evaluations: int = 512,
) -> SolarCentralPathClassification:
    """Find constructive evidence of an event-wide hybrid central axis.

    The result only establishes that both phases occur at visible central-axis
    points. It does not establish a non-hybrid event, an exhaustive list of
    transitions, or NASA subtype. If the greatest-eclipse epoch has no axis
    point, that does not establish that the entire event lacks one.
    """

    if not isinstance(event, EclipseEvent) or not event.data.is_solar_eclipse:
        raise ValueError("event must be a solar EclipseEvent")
    if isinstance(max_evaluations, bool) or not isinstance(max_evaluations, int) or max_evaluations < 1:
        raise ValueError("max_evaluations must be a positive integer")
    if not math.isfinite(event.jd_ut):
        raise ValueError("event epoch must be finite")
    # Check for the ordinary no-axis case explicitly. Do not catch generic
    # ValueError/ArithmeticError here: SPK and time-data failures must reach
    # the caller, not be mistaken for missing geometric evidence.
    seed_shadow = _earth_fixed_solar_shadow(calc, event.jd_ut)
    seed_axis = _axis_surface_point_from_shadow(seed_shadow) if seed_shadow is not None else None
    if seed_axis is None:
        return SolarCentralPathClassification(
            "unresolved", None, "central-axis interval unavailable at the event seed",
            None, None, None, (), 1, False,
        )
    try:
        start, end = _solve_solar_central_interval(calc, event.jd_ut)
        left, right = start.jd_ut, end.jd_ut
        if not math.isfinite(left) or not math.isfinite(right) or left >= right:
            raise ArithmeticError("invalid central-axis interval")
    except _SearchLimitReached:
        return SolarCentralPathClassification(
            "unresolved", None, "central-axis interval search limit reached",
            None, None, None, (), 1, False,
        )

    count = 1
    exhausted = False
    cache: dict[float, SolarCentralAxisWitness | None] = {}

    def evaluate(jd: float) -> SolarCentralAxisWitness | None:
        nonlocal count
        if jd in cache:
            return cache[jd]
        if count >= max_evaluations:
            raise _EvaluationBudgetExhausted
        count += 1
        shadow = _earth_fixed_solar_shadow(calc, jd)
        axis = _axis_surface_point_from_shadow(shadow) if shadow is not None else None
        if shadow is None or axis is None:
            cache[jd] = None
            return None
        xyz = axis.xyz_itrf_km
        radius = shadow.central_radius_km - shadow.central_cone_slope * _shadow_dot(
            _shadow_subtract(xyz, shadow.fundamental_plane_point_xyz_km),
            shadow.axis_unit_away_from_sun,
        )
        sun_vector = _shadow_subtract(shadow.sun_xyz_from_earth_itrf_km, xyz)
        sun_distance = math.sqrt(_shadow_dot(sun_vector, sun_vector))
        altitude_sine = _shadow_dot(_wgs84_surface_normal_unit(xyz), sun_vector) / sun_distance
        if not math.isfinite(altitude_sine):
            raise ArithmeticError("solar altitude is not finite")
        if abs(altitude_sine) > 1.0 + 1.0e-12:
            raise ArithmeticError("solar altitude sine is outside its physical range")
        if altitude_sine <= 0.0:
            cache[jd] = None
            return None
        _, sun_radius, moon_radius = _solar_shadow_discs(shadow, xyz)
        ratio = moon_radius / sun_radius - 1.0
        values = (radius, ratio, axis.latitude_deg, axis.longitude_deg)
        if not all(math.isfinite(value) for value in values):
            raise ArithmeticError("central-axis geometry is not finite")
        point = SolarCentralAxisWitness(
            jd, axis.latitude_deg, axis.longitude_deg, radius,
            math.degrees(math.asin(min(1.0, altitude_sine))), ratio,
        )
        cache[jd] = point
        return point

    points: list[SolarCentralAxisWitness] = []
    try:
        for epoch in _sample_epochs(left, right, event.jd_ut):
            point = evaluate(epoch)
            if point is not None:
                points.append(point)
    except _EvaluationBudgetExhausted:
        exhausted = True

    # Keep comfortably nonzero witnesses and verify the independent disc-size
    # ordering. Near zero, binary64 cancellation cannot establish a phase.
    annular = [p for p in points if p.signed_radius_km < -1.0e-6 and p.angular_radius_ratio_minus_one < -1.0e-12]
    total = [p for p in points if p.signed_radius_km > 1.0e-6 and p.angular_radius_ratio_minus_one > 1.0e-12]
    annular_witness = min(annular, key=lambda p: p.signed_radius_km, default=None)
    total_witness = max(total, key=lambda p: p.signed_radius_km, default=None)
    transitions: list[SolarCentralAxisTransition] = []
    if not exhausted:
        for a, b in zip(points, points[1:]):
            if a.signed_radius_km == 0.0 or b.signed_radius_km == 0.0 or (a.signed_radius_km > 0.0) == (b.signed_radius_km > 0.0):
                continue
            def radius_at(jd: float) -> float | None:
                point = evaluate(jd)
                return point.signed_radius_km if point is not None else None
            try:
                bracket = _bisect_sign_change(radius_at, a.jd_ut, b.jd_ut)
            except _EvaluationBudgetExhausted:
                exhausted = True
                break
            if bracket is not None:
                direction = "annular_to_total" if a.signed_radius_km < 0.0 else "total_to_annular"
                transitions.append(SolarCentralAxisTransition(*bracket, direction))

    hybrid = annular_witness is not None and total_witness is not None
    if hybrid:
        reason = "opposite-sign daylight central-axis witnesses found; transition coverage is incomplete"
    elif exhausted:
        reason = "evaluation budget exhausted before two phases were witnessed"
    else:
        reason = "one or both phases were not witnessed; absence is unproved"
    return SolarCentralPathClassification(
        "hybrid" if hybrid else "unresolved", None, reason, (left, right),
        annular_witness, total_witness, tuple(transitions), count, exhausted,
    )
