"""Whole-Earth penumbral exclusion on the real solar frame.

A shared tangent plane has Earth and the Sun beyond the Moon's support.
This supplies an exclusion bound without sampling surface patches or the
geometric horizon. All closed time cells retain their proof or uncertainty.
"""

from fractions import Fraction
import time

from . import _eclipse_interval_jets as j
from ._eclipse_interval import IntervalBudgetError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_solar_time_surface import SolarTimeSurfaceCover, TimeSurfaceCell
from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM
from .eclipse import _WGS84_POLAR_RADIUS_KM


def _cross(a, b):
    return tuple(j.sub(j.mul(a[i], b[k]), j.mul(a[k], b[i]))
                 for i, k in ((1, 2), (2, 0), (0, 1)))


def penumbral_plane_gap(
    frame, *, equatorial=EARTH_RADIUS_KM, polar=_WGS84_POLAR_RADIUS_KM,
    sun_radius=SUN_RADIUS_KM, moon_radius=MOON_RADIUS_KM,
):
    """Enclose the Earth-to-plane separation in km and its UT1 derivatives.

    With e directed from Sun to Moon and w the unit transverse vector from
    Earth's centre toward the shadow axis, n = -cos(f)w - sin(f)e is unit.
    Here sin(f) = (Rs+Rm)/|M-S|, so n·M+Rm = n·S-Rs. A strictly positive
    gap between that level and Earth's minimum support along n rules out
    every ordered Earth-Moon-Sun line by convexity of the half-space.

    The frame supplies matched Sun/Moon jets and one orthogonal rotation.
    Only its celestial polar axis enters the oblate ellipsoid support.
    A nonpositive result has no occurrence implication.
    """
    a, b, rs, rm = map(Fraction, (equatorial, polar, sun_radius, moon_radius))
    if not 0 < b <= a or not 0 < rm < rs:
        raise ValueError("positive ordered ellipsoid and source radii required")
    sun, moon = frame.sun, frame.moon
    ds, dm = j.norm(sun)[0], j.norm(moon)[0]
    if dm.lo <= a + rm or ds.lo - a - rs <= dm.hi + a + rm:
        raise EnclosureUnavailable("Earth, Moon and solar ray depths are not ordered")
    delta = j.vector_sub(moon, sun)
    distance = j.norm(delta)
    axis = tuple(j.div(component, distance) for component in delta)
    sine = j.div(j.constant(rs + rm), distance)
    cosine = j.sqrt(j.sub(j.constant(1), j.square(sine)))
    transverse = _cross(moon, axis)
    distance_to_axis = j.norm(transverse)
    axis_foot = _cross(axis, transverse)
    normal = tuple(j.neg(j.add(j.div(j.mul(cosine, foot), distance_to_axis), j.mul(sine, direction)))
                   for foot, direction in zip(axis_foot, axis))
    pole_projection = j.dot(normal, frame.rotation[2])
    support = j.sqrt(j.sub(j.constant(a * a), j.scale(j.square(pole_projection), a * a - b * b)))
    plane = j.sub(j.constant(rm),
                  j.add(j.mul(cosine, distance_to_axis), j.mul(sine, j.dot(moon, axis))))
    return j.neg(j.add(plane, support))


def cover_penumbra_exclusion(domain, frame_provider, *, max_evaluations=256, minimum_width=Fraction(1, 86400)):
    """Cover a closed UT1 time interval using whole-Earth plane exclusions.

    Each frame query for a box or midpoint counts toward the budget. The
    mean-value bound only uses source-continuous boxes, with the hull of
    one-sided rates at the clock or polar interpolation knots.
    """
    if not isinstance(domain, I) or type(max_evaluations) is not int or max_evaluations < 0:
        raise ValueError("exact time domain and nonnegative evaluation budget required")
    if minimum_width <= 0:
        raise ValueError("positive minimum time width required")
    started = time.monotonic()
    count, cells, pending = 0, [], [domain]
    while pending:
        box = pending.pop()
        if count >= max_evaluations:
            cells.append(TimeSurfaceCell(box, None, "unresolved", "penumbral_plane_evaluation_budget"))
            continue
        count += 1
        gap = None
        reason = "penumbral_plane_gap_not_strict"
        try:
            frame = frame_provider(box)
            gap, rate, _ = penumbral_plane_gap(frame)
            if gap.lo <= 0 < gap.hi and frame.continuous and box.width and count < max_evaluations:
                count += 1
                center = penumbral_plane_gap(frame_provider(I.point(box.midpoint)))[0]
                narrower = gap.intersect(center + rate * (box - box.midpoint))
                if narrower is None:
                    raise ArithmeticError("independent penumbral plane bounds disagree")
                gap = narrower
        except (EnclosureUnavailable, IntervalBudgetError) as exc:
            reason = str(exc)
        if gap is not None and gap.lo > 0:
            cells.append(TimeSurfaceCell(box, None, "excluded", "earth_sun_moon_separating_plane", gap))
        elif box.width <= minimum_width or (gap is not None and gap.hi <= 0):
            cells.append(TimeSurfaceCell(box, None, "unresolved", reason, gap))
        else:
            mid = box.midpoint
            pending.extend((I(mid, box.hi), I(box.lo, mid)))
    return SolarTimeSurfaceCover(domain, tuple(cells), None, count, time.monotonic() - started,
                                 max_evaluations, None, scope="conditional_whole_earth_penumbra_separation")
