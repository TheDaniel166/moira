"""WGS84 ray evidence and conditional Earth-rotation angle bounds.

An orthogonally oriented WGS84 ellipsoid contains its polar-radius sphere and
is contained in its equatorial-radius sphere. Thus a forward ray proved to
hit the inner sphere hits every possible oriented ellipsoid; a ray proved to
miss the outer sphere misses every possible orientation. These are strict
mathematical set statements, with unresolved results at tangency and in the
intermediate annulus. They do not establish the actual rounded ITRF transform,
source vector enclosures, physical eclipse occurrence or event-wide paths. A
separate helper encloses Earth Rotation Angle only, not GAST or full ITRF.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math

from ._eclipse_interval import IntervalBudgetError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded
from ._eclipse_solar_serving import ConditionalSolarServingBounds, bound_conditional_solar_serving_vectors
from .constants import EARTH_RADIUS_KM


class EclipseWgs84OrientationUnavailable(EnclosureUnavailable):
    """A ray vector or arithmetic budget is not sufficient for a proof."""


@dataclass(frozen=True, slots=True)
class Wgs84RayOrientationEvidence:
    """Exact orientation-independent evidence for an ideal forward ray."""

    result: str
    direction_norm_sq_km2: I
    approach_dot_km2: I
    moon_norm_sq_km2: I
    inner_clearance_scaled_km4: I
    outer_clearance_scaled_km4: I
    equatorial_radius_km: Fraction
    polar_radius_km: Fraction
    polar_radius_model: str = "pinned binary64 0x1.8d4c097aa975cp+12 km"
    orthogonal_orientation_required: bool = True
    source_vectors_attested: bool = False
    rounded_legacy_orientation_enclosed: bool = False
    solar_eclipse_occurrence_certified: bool = False
    event_wide_path_certified: bool = False
    physical_accuracy_certified: bool = False


@dataclass(frozen=True, slots=True)
class ConditionalSolarRayOrientationEvidence:
    """Split-TT solar vector boxes and their ideal WGS84 ray evidence."""

    vectors: ConditionalSolarServingBounds
    ray: Wgs84RayOrientationEvidence
    source_and_arithmetic_attested: bool = False
    rounded_legacy_axis_or_orientation_enclosed: bool = False
    solar_eclipse_occurrence_certified: bool = False
    event_wide_path_certified: bool = False


@dataclass(frozen=True, slots=True)
class ConditionalEarthRotationAngleBounds:
    """Conditional IAU Earth Rotation Angle enclosure in degrees at UT1.

    The input interval describes represented binary64 UT1 Julian days. The
    output encloses the current Python and native serving operation schedules,
    under the stated arithmetic and unchanged-source premises. Uncertain day
    and modulo branches raise instead of pretending to be a continuous angle.
    """

    ut1_anchor_jd: float
    ut1_offset_days: I
    angle_degrees: I
    ieee_rounding_and_fmod_required: bool = True
    native_no_unsafe_reassociation_required: bool = True
    source_and_arithmetic_attested: bool = False
    gast_enclosed: bool = False
    nutation_precession_or_polar_motion_enclosed: bool = False
    earth_fixed_shadow_certified: bool = False
    physical_ut1_accuracy_certified: bool = False


def bound_conditional_earth_rotation_angle(
    ut1_anchor_jd: float, ut1_offset_days: I, *, assume_ieee_arithmetic: bool = False,
) -> ConditionalEarthRotationAngleBounds:
    """Bound serving ERA on one branch under explicit IEEE/native premises.

    Values in ``anchor + offsets`` are represented UT1 inputs to Moira's
    ``earth_rotation_angle``. The bound models the Python expression and both
    separate and fused multiply/add forms admitted by the native expression.
    It assumes binary64 round-to-nearest, gradual underflow, exact ``fmod(x,1)``
    for binary64 input, and unchanged matching source/native code without unsafe
    reassociation. These premises are not tested or attested by this function.
    Integer-day and modulo-turn boundaries require subdivision. The result is
    ERA only: it excludes precession, nutation, GAST, polar motion and UT1 or
    ephemeris accuracy, and cannot by itself certify any eclipse geometry.
    """
    if type(assume_ieee_arithmetic) is not bool:
        raise TypeError("ERA arithmetic premise must be a boolean")
    if not assume_ieee_arithmetic:
        raise EclipseWgs84OrientationUnavailable("ERA arithmetic premise is required")
    if isinstance(ut1_anchor_jd, bool) or not isinstance(ut1_anchor_jd, (int, float)):
        raise ValueError("UT1 anchor must be a finite represented Julian day")
    try:
        anchor = float(ut1_anchor_jd)
    except OverflowError as exc:
        raise ValueError("UT1 anchor must be a finite represented Julian day") from exc
    if not math.isfinite(anchor) or not isinstance(ut1_offset_days, I):
        raise ValueError("finite UT1 anchor and rational offsets are required")
    try:
        epoch = I.point(anchor) + ut1_offset_days
        # Restrict to Moira's finite time-transform domain and to an exactly
        # representable integer quotient for fmod by one.
        if epoch.lo < -40_000_000 or epoch.hi > 40_000_000:
            raise EclipseWgs84OrientationUnavailable("UT1 outside supported ERA proof domain")
        first_day, last_day = int(epoch.lo), int(epoch.hi)
        if first_day != last_day:
            raise EclipseWgs84OrientationUnavailable("ERA integer-day branch requires subdivision")
        frac_day = epoch - first_day
        days = _rounded(epoch - I.point(2451545.0))
        first = _rounded(frac_day + I.point(0.7790572732640))
        product = I.point(0.00273781191135448) * days
        separate = _rounded(first + _rounded(product))
        fused = _rounded(first + product)
        turns = I(min(separate.lo, fused.lo), max(separate.hi, fused.hi))
        first_turn, last_turn = turns.lo // 1, turns.hi // 1
        if first_turn != last_turn:
            raise EclipseWgs84OrientationUnavailable("ERA modulo branch requires subdivision")
        fractional_turn = _rounded(turns - first_turn)
        angle = _rounded(fractional_turn * I.point(360.0))
        return ConditionalEarthRotationAngleBounds(anchor, ut1_offset_days, angle)
    except IntervalBudgetError as exc:
        raise EclipseWgs84OrientationUnavailable("ERA interval budget exhausted") from exc


def bound_wgs84_solar_axis_any_orientation(
    sun_xyz_km: tuple[I, I, I], moon_xyz_km: tuple[I, I, I],
) -> Wgs84RayOrientationEvidence:
    """Bound the ideal ray ``moon + t*(moon - sun)``, ``t >= 0``.

    Both Sun and Moon must be enclosed in the same Earth-centered Cartesian
    frame and at the same policy-selected epoch. The polar radius is pinned
    to the represented model constant identified in the result; its equality
    with any later version of Moira is not dynamically attested. This does not
    establish that the supplied boxes correspond to Moira's shadow model.
    """
    if (not isinstance(sun_xyz_km, tuple) or len(sun_xyz_km) != 3
            or not isinstance(moon_xyz_km, tuple) or len(moon_xyz_km) != 3
            or not all(isinstance(x, I) for x in (*sun_xyz_km, *moon_xyz_km))):
        raise TypeError("Sun and Moon must be three RationalInterval components")
    try:
        a = Fraction.from_float(EARTH_RADIUS_KM)
        # Pinned model constant, currently equal to eclipse.py's expression.
        b = Fraction.from_float(float.fromhex("0x1.8d4c097aa975cp+12"))
        if not 0 < b <= a:
            raise EclipseWgs84OrientationUnavailable("WGS84 radii are outside the proved domain")
        direction = tuple(m - s for s, m in zip(sun_xyz_km, moon_xyz_km))
        length2 = sum((component.square() for component in direction), I.point(0))
        if length2.lo <= 0:
            raise EclipseWgs84OrientationUnavailable("Sun and Moon may not define a ray direction")
        moon2 = sum((component.square() for component in moon_xyz_km), I.point(0))
        approach = sum((m * d for m, d in zip(moon_xyz_km, direction)), I.point(0))
        cross = (moon_xyz_km[1] * direction[2] - moon_xyz_km[2] * direction[1],
                 moon_xyz_km[2] * direction[0] - moon_xyz_km[0] * direction[2],
                 moon_xyz_km[0] * direction[1] - moon_xyz_km[1] * direction[0])
        cross2 = sum((component.square() for component in cross), I.point(0))
        inner = cross2 - b * b * length2
        outer = cross2 - a * a * length2
        if outer.lo > 0 or (moon2.lo > a * a and approach.lo >= 0):
            result = "misses_every_orientation"
        elif moon2.lo > a * a and approach.hi < 0 and inner.hi < 0:
            result = "intersects_every_orientation"
        else:
            result = "unresolved"
        return Wgs84RayOrientationEvidence(
            result, length2.quantize_outward(128), approach.quantize_outward(128),
            moon2.quantize_outward(128), inner.quantize_outward(128), outer.quantize_outward(128), a, b,
        )
    except IntervalBudgetError as exc:
        raise EclipseWgs84OrientationUnavailable("WGS84 ray interval budget exhausted") from exc


def bound_conditional_solar_ray_any_orientation(
    reader, tt_anchor_jd: float, tt_offset_days: I,
) -> ConditionalSolarRayOrientationEvidence:
    """Compose the split solar vector route with the ideal orientation bound.

    The ray conclusion is conditional on the nested vector source/roundoff
    premises and orthogonal Earth orientation. It does not enclose the rounded
    implementation of the shadow axis or assert a visible solar eclipse.
    """
    vectors = bound_conditional_solar_serving_vectors(reader, tt_anchor_jd, tt_offset_days)
    ray = bound_wgs84_solar_axis_any_orientation(vectors.sun_retarded_km, vectors.moon_retarded_km)
    return ConditionalSolarRayOrientationEvidence(vectors, ray)
