"""Instantaneous geometric horizon clipping for a central-shadow candidate.

This experimental internal module is separate from the swept path products. It
supports one bounded generator interval and two transverse horizon crossings.
The inspection API also samples a limited periodic daylight loop. Degenerate or
numerically unresolved topologies fail closed. The native generator-interval
solver is assumed; this module does not independently certify that its interval
is the only component. Coordinates
are WGS84, the cone is Moira's native physical central cone, and the horizon is
the unrefracted, topocentric geometric horizon of the Sun's centre.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Literal

from .constants import SUN_RADIUS_KM
from .eclipse import (
    EARTH_RADIUS_KM, MOON_RADIUS_KM, _WGS84_POLAR_RADIUS_KM,
    _central_shadow_clearance_km, _earth_fixed_solar_shadow,
    _noncentral_shadow_branch, _penumbral_generator_line,
    _penumbral_lawful_azimuth_interval, _shadow_add, _shadow_dot,
    _shadow_scale, _shadow_subtract, _wgs84_geodetic_from_xyz_km,
    _wgs84_line_intersection_parameters, _wgs84_line_quadratic_coefficients,
)


class ClippedBoundaryIndeterminate(ArithmeticError):
    """The geometry is outside this solver's supported or resolved topology."""


@dataclass(frozen=True, slots=True)
class ClippedBoundaryPoint:
    """One sampled zero-elevation WGS84 point, including terrestrial XYZ."""

    latitude_deg: float
    longitude_deg: float
    xyz_itrf_km: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class InstantaneousClippedCentralBoundary:
    """Sampled cone and, when present, horizon arcs on the WGS84 ellipsoid.

    Both curves are sampled for presentation. Their endpoints and each sampled
    point are solved numerically; connecting samples by straight segments is
    an approximation. Bounded cone samples allow a horizon-plane residual
    down to -1e-6 and horizon samples allow cone clearance down to -1e-5 km.
    The horizon-plane residual is the unnormalized dimensionless ellipsoid
    normal dot Sun-minus-site vector. Neither arc is an event-wide limit.
    """
    jd_ut: float
    cone_arc: tuple[ClippedBoundaryPoint, ...]
    horizon_arc: tuple[ClippedBoundaryPoint, ...]
    horizon_model: str = "GEOMETRIC_SUN_CENTER_NO_REFRACTION"
    surface_model: str = "WGS84_ZERO_ELEVATION"
    scope: str = "INSTANTANEOUS"
    cone_model: str = "NATIVE_PHYSICAL_CENTRAL_CONE"
    topology: str = "NUMERICALLY_RESOLVED_BOUNDED_TWO_CROSSINGS"


@dataclass(frozen=True, slots=True)
class InstantaneousClippedBoundaryCandidate:
    """Numerical candidate for one instantaneous boundary, or unresolved.

    ``complete`` is always false: neither the native generator interval nor
    the finite arc sampling proves that every surface component was found.
    Missing resources and unexpected calculation failures propagate to the
    caller instead of being represented as an unresolved topology. The
    ephemeris filename, when present, is descriptive only: it is not a content
    hash or proof that the file supplied every routed state.
    """

    status: Literal["candidate", "unresolved"]
    boundary: InstantaneousClippedCentralBoundary | None
    reason: str | None
    complete: Literal[False] = False
    jd_ut1: float | None = None
    time_scale: Literal["UT1"] = "UT1"
    engine_version: str | None = None
    ephemeris_filename: str | None = None
    earth_equatorial_radius_km: float = EARTH_RADIUS_KM
    earth_polar_radius_km: float = _WGS84_POLAR_RADIUS_KM
    sun_radius_km: float = SUN_RADIUS_KM
    moon_radius_km: float = MOON_RADIUS_KM


def _polyval(coeff: list[float], x: float) -> float:
    y = 0.0
    for value in reversed(coeff):
        y = y * x + value
    return y


def _roots_in_unit_interval(coeff: list[float]) -> list[float]:
    """Isolate simple polynomial roots between -1 and 1 via derivative roots.

    Near tangencies are intentionally rejected: binary64 cannot establish their
    topology reliably. The two angular charts avoid unbounded tan-half-angle.
    """
    scale = max(map(abs, coeff), default=0.0)
    if not math.isfinite(scale) or scale == 0.0:
        raise ClippedBoundaryIndeterminate("degenerate horizon/cone polynomial")
    while len(coeff) > 1 and abs(coeff[-1]) <= scale * 1e-15:
        coeff = coeff[:-1]
    if len(coeff) == 1:
        return []
    if len(coeff) == 2:
        root = -coeff[0] / coeff[1]
        return [root] if -1.0 <= root <= 1.0 else []
    critical = _roots_in_unit_interval([i * coeff[i] for i in range(1, len(coeff))])
    knots = [-1.0] + [x for x in critical if -1.0 < x < 1.0] + [1.0]
    values = [_polyval(coeff, x) for x in knots]
    tolerance = scale * 2e-12
    if any(abs(v) <= tolerance for v in values):
        raise ClippedBoundaryIndeterminate("tangent or unresolved horizon/cone intersection")
    roots = []
    for lo, hi, flo, fhi in zip(knots, knots[1:], values, values[1:]):
        if (flo > 0) == (fhi > 0):
            continue
        for _ in range(65):
            mid = (lo + hi) / 2.0
            fm = _polyval(coeff, mid)
            if (fm > 0) == (flo > 0):
                lo, flo = mid, fm
            else:
                hi = mid
        roots.append((lo + hi) / 2.0)
    return roots


def _horizon_circle(shadow):
    a, b = EARTH_RADIUS_KM, _WGS84_POLAR_RADIUS_KM
    sun = shadow.sun_xyz_from_earth_itrf_km
    v = (sun[0] / a, sun[1] / a, sun[2] / b)
    length = math.sqrt(_shadow_dot(v, v))
    if not math.isfinite(length) or length <= 1.0:
        raise ClippedBoundaryIndeterminate("Sun is not outside the ellipsoid")
    n = _shadow_scale(v, 1.0 / length)
    # Cross with a nonparallel coordinate axis for a well-conditioned basis.
    ref = (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0)
    p0 = (n[1]*ref[2]-n[2]*ref[1], n[2]*ref[0]-n[0]*ref[2], n[0]*ref[1]-n[1]*ref[0])
    p = _shadow_scale(p0, 1.0 / math.sqrt(_shadow_dot(p0, p0)))
    q = (n[1]*p[2]-n[2]*p[1], n[2]*p[0]-n[0]*p[2], n[0]*p[1]-n[1]*p[0])
    radius = math.sqrt(1.0 - 1.0 / (length * length))
    def unscale(u):
        return (a*u[0], a*u[1], b*u[2])
    return unscale(_shadow_scale(n, 1.0/length)), unscale(_shadow_scale(p, radius)), unscale(_shadow_scale(q, radius))


def _circle_point(circle, angle):
    center, cosine, sine = circle
    return _shadow_add(center, _shadow_add(_shadow_scale(cosine, math.cos(angle)), _shadow_scale(sine, math.sin(angle))))


def _horizon_crossings(shadow, circle):
    center, c, s = circle
    d = _shadow_subtract(center, shadow.fundamental_plane_point_xyz_km)
    axis, k, r = shadow.axis_unit_away_from_sun, shadow.central_cone_slope, shadow.central_radius_km
    def bilinear(u, v):
        return _shadow_dot(u, v) - (1.0+k*k)*_shadow_dot(axis, u)*_shadow_dot(axis, v)
    constant = bilinear(d,d) + (bilinear(c,c)+bilinear(s,s))/2 + 2*r*k*_shadow_dot(axis,d)-r*r
    co = 2*bilinear(d,c)+2*r*k*_shadow_dot(axis,c)
    si = 2*bilinear(d,s)+2*r*k*_shadow_dot(axis,s)
    co2 = (bilinear(c,c)-bilinear(s,s))/2
    si2 = bilinear(c,s)
    angles = []
    for base, sign in ((0.0, 1.0), (math.pi, -1.0)):
        x, y = sign*co, sign*si
        polynomial = [constant+x+co2, 2*y+4*si2, 2*constant-6*co2, 2*y-4*si2, constant-x+co2]
        angles.extend((base+2*math.atan(t)) % math.tau for t in _roots_in_unit_interval(polynomial))
    angles.sort()
    unique = []
    for angle in angles:
        if unique and angle - unique[-1] <= 1e-8:
            raise ClippedBoundaryIndeterminate("closely spaced horizon crossings are ambiguous")
        unique.append(angle)
    if len(unique)>1 and unique[0]+math.tau-unique[-1] < 1e-8:
        raise ClippedBoundaryIndeterminate("closely spaced horizon crossings are ambiguous")
    return unique


def _point(xyz):
    lat, lon = _wgs84_geodetic_from_xyz_km(xyz)
    return ClippedBoundaryPoint(lat, lon, xyz)


def _generator_interval(branch):
    """Normalize documented topology failures; propagate other failures."""
    try:
        return _penumbral_lawful_azimuth_interval(branch)
    except ArithmeticError as exc:
        if str(exc) not in {
            "penumbral cone has no strict WGS-84 intersection",
            "partial penumbral cone arc has no limb endpoint",
            "lawful penumbral arc does not contain its maximum",
        }:
            raise
        raise ClippedBoundaryIndeterminate("unresolved generator interval") from exc


def instantaneous_clipped_central_boundary(
    calc, jd_ut: float, *, arc_samples: int = 65
) -> InstantaneousClippedCentralBoundary:
    """Solve one bounded cap with two transverse geometric-horizon crossings.

    Unsupported/full-cone/empty/grazing/apex-crossing cases raise
    ClippedBoundaryIndeterminate; they must not be interpreted as no eclipse.
    """
    if not math.isfinite(jd_ut) or isinstance(arc_samples, bool) or not isinstance(arc_samples, int) or arc_samples < 3:
        raise ValueError("finite jd_ut and integer arc_samples >= 3 required")
    shadow = _earth_fixed_solar_shadow(calc, jd_ut)
    if shadow is None:
        raise ClippedBoundaryIndeterminate("no native shadow at this epoch")
    branch = _noncentral_shadow_branch(shadow)
    left, right, periodic = _generator_interval(branch)
    if periodic or not left < right:
        raise ClippedBoundaryIndeterminate("only bounded generator intervals are supported")
    circle = _horizon_circle(shadow)
    angles = _horizon_crossings(shadow, circle)
    if len(angles) != 2:
        raise ClippedBoundaryIndeterminate("expected exactly two transverse horizon crossings")
    junctions = [_circle_point(circle, a) for a in angles]
    ts = []
    for xyz in junctions:
        offset = _shadow_subtract(xyz, shadow.fundamental_plane_point_xyz_km)
        axial = _shadow_dot(offset, shadow.axis_unit_away_from_sun)
        radial = _shadow_subtract(offset, _shadow_scale(shadow.axis_unit_away_from_sun, axial))
        radius = branch.penumbral_radius_km + branch.penumbral_cone_slope * axial
        if axial-shadow.axis_projection_km <= MOON_RADIUS_KM or radius <= 1e-8:
            raise ClippedBoundaryIndeterminate("crossing is outside the forward cone or at its apex")
        phi = math.atan2(_shadow_dot(radial, branch.fundamental_north_unit_itrf), _shadow_dot(radial, branch.fundamental_east_unit_itrf))
        phi = left + (phi-left) % math.tau
        if not left-1e-8 <= phi <= right+1e-8:
            raise ClippedBoundaryIndeterminate("crossing lies outside the bounded generator interval")
        origin, direction = _penumbral_generator_line(branch, phi)
        _, roots = _wgs84_line_intersection_parameters(origin, direction)
        if roots is None or abs(roots[1]-roots[0]) < 1e-5:
            raise ClippedBoundaryIndeterminate("crossing at a generator tangency")
        index = 0 if abs(axial-roots[0]) < abs(axial-roots[1]) else 1
        if abs(axial-roots[index]) > 1e-3:
            raise ClippedBoundaryIndeterminate("crossing fails generator residual check")
        fraction = (phi-left)/(right-left)
        ts.append(fraction if index == 0 else 2.0-fraction)
    def cone(t):
        t %= 2.0
        frac = t if t <= 1.0 else 2.0-t
        phi = left+(right-left)*frac
        origin, direction = _penumbral_generator_line(branch, phi)
        _, roots = _wgs84_line_intersection_parameters(origin, direction)
        if roots is None:
            # At the bounded endpoints, evaluate the exact tangent vertex.
            if min(abs(frac), abs(frac-1.0)) > 1e-9:
                raise ClippedBoundaryIndeterminate("generator lost surface roots")
            qa, qb, _ = _wgs84_line_quadratic_coefficients(origin, direction)
            roots = (-qb/qa, -qb/qa)
        axial = roots[0 if t <= 1.0 else 1]
        if axial-shadow.axis_projection_km <= MOON_RADIUS_KM or branch.penumbral_radius_km+branch.penumbral_cone_slope*axial <= 0:
            raise ClippedBoundaryIndeterminate("cone arc crosses its physical branch")
        return _shadow_add(origin, _shadow_scale(direction, axial))
    def horizon_value(xyz):
        sun = shadow.sun_xyz_from_earth_itrf_km
        return xyz[0]*(sun[0]-xyz[0])/EARTH_RADIUS_KM**2 + xyz[1]*(sun[1]-xyz[1])/EARTH_RADIUS_KM**2 + xyz[2]*(sun[2]-xyz[2])/_WGS84_POLAR_RADIUS_KM**2
    t0,t1 = sorted(ts)
    mids = [horizon_value(cone((t0+t1)/2)), horizon_value(cone((t1+t0+2)/2))]
    if mids[0]*mids[1] >= 0 or min(map(abs,mids)) < 1e-9:
        raise ClippedBoundaryIndeterminate("cone daylight arc is ambiguous")
    ca, cb = (t0,t1) if mids[0]>0 else (t1,t0+2)
    a0,a1 = angles
    hmid = [_central_shadow_clearance_km(shadow, _circle_point(circle, (a0+a1)/2)), _central_shadow_clearance_km(shadow, _circle_point(circle, (a1+a0+math.tau)/2))]
    if hmid[0]*hmid[1] >= 0 or min(map(abs,hmid)) < 1e-7:
        raise ClippedBoundaryIndeterminate("horizon shadow arc is ambiguous")
    ha,hb = (a0,a1) if hmid[0]>0 else (a1,a0+math.tau)
    cone_arc = tuple(_point(cone(ca+(cb-ca)*i/(arc_samples-1))) for i in range(arc_samples))
    horizon_arc = tuple(_point(_circle_point(circle,ha+(hb-ha)*i/(arc_samples-1))) for i in range(arc_samples))
    # Check the forward and single-nappe conditions along the horizon too.
    for point in horizon_arc:
        offset = _shadow_subtract(point.xyz_itrf_km, shadow.fundamental_plane_point_xyz_km)
        axial = _shadow_dot(offset, shadow.axis_unit_away_from_sun)
        if axial-shadow.axis_projection_km <= MOON_RADIUS_KM or branch.penumbral_radius_km+branch.penumbral_cone_slope*axial <= 0:
            raise ClippedBoundaryIndeterminate("horizon arc crosses its physical cone branch")
    # Ensure arcs share endpoints and form a consistently oriented closed contour.
    def distance(a,b):
        return math.sqrt(sum((x-y)**2 for x,y in zip(a.xyz_itrf_km,b.xyz_itrf_km)))
    if distance(cone_arc[-1], horizon_arc[0]) > distance(cone_arc[-1], horizon_arc[-1]):
        horizon_arc = tuple(reversed(horizon_arc))
    if distance(cone_arc[-1],horizon_arc[0]) > 1e-3 or distance(horizon_arc[-1],cone_arc[0]) > 1e-3:
        raise ClippedBoundaryIndeterminate("arc junctions do not agree")
    # Keep one solved point at each shared junction.  Independently generated
    # cone and horizon coordinates can differ despite representing the same
    # intersection; using a common point prevents a false daylight sliver.
    # Check the actual shared points before using them, not merely their
    # distance from a separately reconstructed generator endpoint.
    for point in (horizon_arc[0], horizon_arc[-1]):
        x, y, z = point.xyz_itrf_km
        surface = (x*x + y*y) / EARTH_RADIUS_KM**2 + z*z / _WGS84_POLAR_RADIUS_KM**2 - 1.0
        horizon = horizon_value(point.xyz_itrf_km)
        clearance = _central_shadow_clearance_km(shadow, point.xyz_itrf_km)
        if (not all(math.isfinite(v) for v in (surface, horizon, clearance))
                or abs(surface) >= 2e-12 or abs(horizon) >= 2e-10
                or abs(clearance) >= 1e-6):
            raise ClippedBoundaryIndeterminate("shared junction fails surface residual checks")
    cone_arc = (horizon_arc[-1],) + cone_arc[1:-1] + (horizon_arc[0],)
    for arc, is_cone in ((cone_arc, True), (horizon_arc, False)):
        for point in arc:
            x, y, z = point.xyz_itrf_km
            surface = (x*x + y*y) / EARTH_RADIUS_KM**2 + z*z / _WGS84_POLAR_RADIUS_KM**2 - 1.0
            h = horizon_value(point.xyz_itrf_km)
            clearance = _central_shadow_clearance_km(shadow, point.xyz_itrf_km)
            if not all(math.isfinite(v) for v in (surface, h, clearance)) or abs(surface) >= 2e-12:
                raise ClippedBoundaryIndeterminate("sample fails ellipsoid residual")
            if is_cone and (abs(clearance) >= 1e-6 or h < -1e-6):
                raise ClippedBoundaryIndeterminate("cone sample fails boundary or daylight residual")
            if not is_cone and (abs(h) >= 2e-10 or clearance < -1e-5):
                raise ClippedBoundaryIndeterminate("horizon sample fails boundary or cone residual")
    return InstantaneousClippedCentralBoundary(jd_ut, cone_arc, horizon_arc)


def _periodic_daylight_candidate(calc, jd_ut, arc_samples):
    """Construct a sampled daylight loop; this does not prove completeness."""
    shadow = _earth_fixed_solar_shadow(calc, jd_ut)
    if shadow is None:
        raise ClippedBoundaryIndeterminate("no native shadow at this epoch")
    branch = _noncentral_shadow_branch(shadow)
    left, right, periodic = _generator_interval(branch)
    if not periodic:
        raise ClippedBoundaryIndeterminate("bounded candidate could not be resolved")
    crossings = _horizon_crossings(shadow, _horizon_circle(shadow))
    if crossings:
        raise ClippedBoundaryIndeterminate("periodic cone intersects the geometric horizon")
    accepted = []
    sun = shadow.sun_xyz_from_earth_itrf_km
    for index in (0, 1):
        samples = []
        for i in range(arc_samples - 1):
            phi = left + (right - left) * i / (arc_samples - 1)
            origin, direction = _penumbral_generator_line(branch, phi)
            _, roots = _wgs84_line_intersection_parameters(origin, direction)
            if roots is None:
                break
            axial = roots[index]
            radius = branch.penumbral_radius_km + branch.penumbral_cone_slope * axial
            if axial - shadow.axis_projection_km <= MOON_RADIUS_KM or radius <= 1e-8:
                break
            xyz = _shadow_add(origin, _shadow_scale(direction, axial))
            x, y, z = xyz
            surface = (x*x + y*y) / EARTH_RADIUS_KM**2 + z*z / _WGS84_POLAR_RADIUS_KM**2 - 1.0
            horizon = (x*(sun[0]-x) + y*(sun[1]-y)) / EARTH_RADIUS_KM**2 + z*(sun[2]-z) / _WGS84_POLAR_RADIUS_KM**2
            clearance = _central_shadow_clearance_km(shadow, xyz)
            if (not all(math.isfinite(v) for v in (surface, horizon, clearance))
                    or abs(surface) >= 2e-12 or horizon <= 0.0
                    or abs(clearance) >= 1e-6):
                break
            samples.append(_point(xyz))
        else:
            accepted.append(tuple(samples) + (samples[0],))
    if len(accepted) != 1:
        raise ClippedBoundaryIndeterminate("periodic daylight branch is absent or ambiguous in numerical samples")
    return InstantaneousClippedCentralBoundary(
        jd_ut, accepted[0], (), topology="NUMERICAL_PERIODIC_DAYLIGHT_CANDIDATE"
    )


def inspect_instantaneous_clipped_central_boundary(
    calc, jd_ut: float, *, arc_samples: int = 65
) -> InstantaneousClippedBoundaryCandidate:
    """Inspect a bounded or periodic central-shadow snapshot provisionally.

    A candidate reports a sampled curve using one native state.  The native
    generator interval, physical branch membership and horizon topology have
    not been independently certified over their entire domains.  An unresolved
    result does not mean no eclipse or no boundary.  These products are not
    published-table limits, event-wide swept boundaries, or path widths.
    """
    from . import __version__

    reader = getattr(calc, "_reader", None)
    source_path = getattr(reader, "path", None)
    filename = Path(source_path).name if isinstance(source_path, (str, Path)) else None

    def result(status, boundary, reason):
        return InstantaneousClippedBoundaryCandidate(
            status, boundary, reason, jd_ut1=float(jd_ut), engine_version=__version__,
            ephemeris_filename=filename,
        )

    try:
        try:
            boundary = instantaneous_clipped_central_boundary(calc, jd_ut, arc_samples=arc_samples)
        except ClippedBoundaryIndeterminate as bounded_error:
            try:
                boundary = _periodic_daylight_candidate(calc, jd_ut, arc_samples)
            except ClippedBoundaryIndeterminate as periodic_error:
                return result("unresolved", None, f"{bounded_error}; {periodic_error}")
    except ClippedBoundaryIndeterminate as exc:
        return result("unresolved", None, str(exc))
    return result("candidate", boundary, None)
