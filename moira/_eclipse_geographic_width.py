"""Bounded geographic cross-track widths with a differentiated track.

The metric is arc length on the central plane section of WGS84 whose tangent
at the near-axis reference is perpendicular to the instantaneous axis motion.
This is a named Moira metric, not a geodesic, swept-union width, same-row limit
distance, support span, tangent-plane extrapolation or NASA-compatible width.
All section cells between finite hemisphere endpoints are enclosed. A value
requires one certified interior component and two bounded limit bands with
excluded complements. Requested precision is reported separately from a valid
coarser interval. Missing references or unproved complements return no number.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F

from . import _eclipse_interval_jets as j
from ._eclipse_interval import RationalInterval as I,IntervalBudgetError
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_inverse_trig import atan_enclosure
from ._eclipse_interval_elementary import sin_cos_enclosure
from ._eclipse_central_region_bounds import central_region_bounds,norm,unit,cross
from .constants import EARTH_RADIUS_KM,MOON_RADIUS_KM
from .eclipse import _WGS84_POLAR_RADIUS_KM


@dataclass(frozen=True, slots=True)
class GeographicSection:
    """Orthonormal scaled-sphere basis bounds and a validated track reference.

    Caller invariant: first/second enclose the SAME underlying orthonormal
    pair. axis_normal_section proves it from QP cross V; arbitrary boxes
    do not independently establish that geometric invariant.
    """

    sun: tuple
    moon: tuple
    first: tuple
    second: tuple
    reference_itrf_km: tuple
    track_velocity_km_per_day: tuple
    track_speed_km_per_day: I
    axis_half_chord_sq_km2: I
    radii: tuple = (F.from_float(EARTH_RADIUS_KM),F.from_float(EARTH_RADIUS_KM),
                   F.from_float(_WGS84_POLAR_RADIUS_KM))


def axis_normal_section(frame):
    """Differentiate the lawful near axis intersection; no time-step estimate."""
    if not frame.continuous:
        raise EnclosureUnavailable('source_seam_track_derivative_unproved')
    sun,moon = (j.matrix_vector(frame.rotation,v) for v in (frame.sun,frame.moon))
    delta = j.vector_sub(moon,sun)
    distance = j.norm(delta)
    axis = tuple(j.div(v,distance) for v in delta)
    radii = (F.from_float(EARTH_RADIUS_KM),)*2+(F.from_float(_WGS84_POLAR_RADIUS_KM),)

    def metric(a,b):
        value = j.constant(0)
        for x,y,r in zip(a,b,radii):
            value = j.add(value,j.scale(j.mul(x,y),1/(r*r)))
        return value

    a,b = metric(axis,axis),metric(moon,axis)
    c = j.sub(metric(moon,moon),j.constant(1))
    discriminant = j.div(j.sub(j.square(b),j.mul(a,c)),j.square(a))
    if discriminant[0].lo <= 0:
        raise EnclosureUnavailable('no_strict_near_axis_reference')
    distance_from_moon = j.sub(j.neg(j.div(b,a)),j.sqrt(discriminant))
    if distance_from_moon[0].lo <= F.from_float(MOON_RADIUS_KM):
        raise EnclosureUnavailable('forward_axis_reference_unproved')
    position = tuple(j.add(m,j.mul(t,distance_from_moon)) for m,t in zip(moon,axis))
    point = tuple(v[0] for v in position)
    velocity = tuple(v[1] for v in position)
    normal = tuple(p/(r*r) for p,r in zip(point,radii))
    transverse = cross(normal,velocity)
    if norm(transverse).lo <= 0:
        raise EnclosureUnavailable('stationary_or_unconditioned_track')
    first = unit(tuple(p/r for p,r in zip(point,radii)))
    second = unit(tuple(v/r for v,r in zip(transverse,radii)))
    # The exact underlying axis lies on the ellipsoid; its derivative is
    # tangent. QP cross V is perpendicular to both the normal and track.
    return GeographicSection(tuple(v[0] for v in sun),tuple(v[0] for v in moon),
        first,second,point,velocity,norm(velocity),discriminant[0],radii)


def section_point(section,x):
    """Projective parameter on the reference hemisphere, x in [-1,1]."""
    d = 1+x.square()
    cosine,sine = (1-x.square())/d,2*x/d
    return tuple((r*(a*cosine+b*sine)).quantize_outward(128)
                 for r,a,b in zip(section.radii,section.first,section.second))


def section_bounds(section,x):
    point = section_point(section,x)
    normal = tuple(p/(r*r) for p,r in zip(point,section.radii))
    return central_region_bounds(section.sun,section.moon,point,normal)


def _speed(section,x):
    # Derivatives of cos= (1-x²)/(1+x²), sin=2x/(1+x²).
    den = (1+x.square()).square()
    dc,ds = -4*x/den,2*(1-x.square())/den
    return norm(tuple(r*(a*dc+b*ds) for r,a,b in zip(section.radii,section.first,section.second)))


def _arc_length(section,lo,hi,tolerance,max_panels):
    if lo > hi:
        raise ValueError('ordered section endpoints required')
    angle_lo,angle_hi = 2*atan_enclosure(I.point(lo)),2*atan_enclosure(I.point(hi))
    domain = I(angle_lo.lo,angle_hi.hi)
    # Separate a fixed coefficient uncertainty from quadrature truncation.
    # Refining panels cannot reduce an uncertain track direction. The norm
    # is 1-Lipschitz, so E times angular length bounds this effect rigorously.
    coefficient_error = sum((norm(tuple(r*(v-v.midpoint) for r,v in zip(section.radii,basis)))
                             for basis in (section.first,section.second)),I.point(0)).hi
    original = section
    section = replace(section,first=tuple(I.point(v.midpoint) for v in section.first),
                      second=tuple(I.point(v.midpoint) for v in section.second))

    def panel(box):
        # Midpoint-rule remainder |error| <= sup|speed''|*width³/24.
        # v=P', v'=-P, v''=-v for this fixed plane ellipse (angle coordinate).
        trig = sin_cos_enclosure(box,precision_bits=160)
        velocity = tuple(r*(-a*trig.sine+b*trig.cosine)
                         for r,a,b in zip(section.radii,section.first,section.second))
        acceleration = tuple(r*(-a*trig.cosine-b*trig.sine)
                             for r,a,b in zip(section.radii,section.first,section.second))
        speed,acc = norm(velocity),norm(acceleration)
        if speed.lo <= 0:
            return None
        curvature = acc.hi**2/speed.lo+speed.hi+speed.hi**2*acc.hi**2/speed.lo**3
        mid = sin_cos_enclosure(I.point(box.midpoint),precision_bits=160)
        value = norm(tuple(r*(-a*mid.sine+b*mid.cosine)
                           for r,a,b in zip(section.radii,section.first,section.second)))
        error = curvature*box.width**3/24
        return (value*box.width+I(-error,error)).quantize_outward(128)

    pieces,pending = [],[domain]
    while pending:
        box = pending.pop()
        value = panel(box)
        if value is None:
            if len(pending)+len(pieces) >= max_panels:
                raise EnclosureUnavailable('arc_length_conditioning_budget')
            pending.extend((I(box.lo,box.midpoint),I(box.midpoint,box.hi)))
        else:
            pieces.append((box,value))
    while sum(v.width for _,v in pieces) > tolerance:
        if len(pieces) >= max_panels:
            raise EnclosureUnavailable('arc_length_quadrature_budget')
        index = max(range(len(pieces)),key=lambda k:pieces[k][1].width)
        box,_ = pieces.pop(index)
        mid = box.midpoint
        for child in (I(box.lo,mid),I(mid,box.hi)):
            value = panel(child)
            if value is None:
                raise EnclosureUnavailable('arc_length_speed_conditioning')
            pieces.append((child,value))
    result = sum((v for _,v in pieces),I.point(0))
    # Outer angle endpoints enclose the true atan endpoints. Bound the two
    # tiny extra tails without claiming a rounded atan value is exact.
    speed_bound = max(original.radii)*(norm(original.first).hi+norm(original.second).hi)
    tails = speed_bound*(angle_lo.width+angle_hi.width)
    model_error = coefficient_error*domain.width
    return I(max(F(0),result.lo-tails-model_error),result.hi+model_error).quantize_outward(128)


@dataclass(frozen=True, slots=True)
class GeographicLimit:
    """Time-stamped Moira section edge; sign names cross-track orientation."""

    side: str
    parameter: I
    xyz_itrf_km: tuple
    epoch_ut1: float | None
    unique_root_proved: bool = False


@dataclass(frozen=True, slots=True)
class GeographicWidth:
    """A certified interval in a declared geographic metric, or no value."""

    status: str
    width_km: I | None
    left_limit: I | None
    right_limit: I | None
    cells: tuple
    evaluations: int
    reason: str
    section: GeographicSection | None
    epoch_ut1: float | None
    metric: str = 'WGS84_central_plane_cross_track_arc_length'
    limit_policy: str = 'instantaneous_visible_central_component_containing_near_axis'
    horizon_policy: str = 'geometric_Sun_centre_no_refraction_or_terrain'
    nasa_compatible: bool = False
    swept_union_boundary_claimed: bool = False
    requested_tolerance_km: F | None = None
    model_profile: str = 'conditional_supplied_section_and_ray_bounds'
    event_domain_offset_days: I | None = None
    track_policy: str = 'implicit_local_derivative_or_enclosed_one_sided_tangent_family'

    @property
    def limits(self):
        if self.width_km is None:
            return ()
        return tuple(GeographicLimit(side,parameter,section_point(self.section,parameter),self.epoch_ut1)
                     for side,parameter in (('negative_cross_track',self.left_limit),
                                            ('positive_cross_track',self.right_limit)))


def bound_geographic_width(section, *, epoch_ut1=None,tolerance_km=F(1,10),
                            max_evaluations=4096,max_quadrature_panels=4096,
                            model_profile='conditional_supplied_section_and_ray_bounds',event_domain=None):
    """Bound both limits and their arc separation; never fabricate zero.

    The entire reference hemisphere is retained. Multiple components,
    tangencies or unproved complements fail with no numeric width. A valid
    coarse interval explicitly reports unmet precision. Root uniqueness inside a band is not asserted; the
    component's edge is enclosed by the strict inside/outside complements.
    """
    tolerance = I.point(tolerance_km)
    if tolerance.width or tolerance.lo <= 0 or type(max_evaluations) is not int or max_evaluations < 0:
        raise ValueError('positive tolerance and finite nonnegative budget required')
    if type(max_quadrature_panels) is not int or max_quadrature_panels < 1:
        raise ValueError('positive finite quadrature panel budget required')
    calls,cells,pending = 0,[],[I(-1,1)]
    parameter_tolerance = F(tolerance_km)/(32*max(section.radii))

    def partition(resolution):
        nonlocal calls
        while pending:
            box = pending[-1]
            if calls >= max_evaluations:
                pending.pop()
                cells.append((box,'unresolved','evaluation_budget'))
                continue
            calls += 1
            bound = section_bounds(section,box)
            pending.pop()
            if bound.inside:
                cells.append((box,'inside',bound))
            elif bound.outside:
                cells.append((box,'outside',bound))
            elif box.width <= resolution:
                cells.append((box,'unresolved',bound))
            else:
                mid = box.midpoint
                pending.extend((I(mid,box.hi),I(box.lo,mid)))
        cells.sort(key=lambda row:row[0].lo)

    def measure():
        groups = []
        for box,status,_ in cells:
            if groups and groups[-1][1] == status:
                groups[-1] = I(groups[-1][0].lo,box.hi),status
            else:
                groups.append((box,status))
        if ([status for _,status in groups] != ['outside','unresolved','inside','unresolved','outside'] or
                not groups[2][0].contains(0)):
            raise EnclosureUnavailable('unproved_two_limits_or_multiple_components')
        left,right = groups[1][0],groups[3][0]
        inner = _arc_length(section,left.hi,right.lo,F(tolerance_km)/4,max_quadrature_panels)
        outer = _arc_length(section,left.lo,right.hi,F(tolerance_km)/4,max_quadrature_panels)
        width = I(inner.lo,outer.hi)
        if width.lo <= 0:
            raise EnclosureUnavailable('geographic_width_error_budget')
        return width,left,right

    try:
        partition(parameter_tolerance)
        width,left,right = measure()
        if width.width > tolerance_km and calls < max_evaluations:
            # Refine only the two previously bounded limit bands. Their
            # sensitivity can exceed the nominal parameter-to-arc scaling
            # near a grazing horizon. Preserve a valid coarse interval if
            # the extra work reaches the shared evaluation budget.
            coarse_cells = cells
            pending = [box for box,status,_ in cells if status == 'unresolved']
            cells = [row for row in cells if row[1] != 'unresolved']
            partition(parameter_tolerance/16)
            if calls >= max_evaluations:
                cells = coarse_cells
            else:
                refined,left,right = measure()
                width = width.intersect(refined)
                if width is None:
                    raise ArithmeticError('independent geographic arc enclosures disagree')
        status = 'bounded_width' if width.width <= tolerance_km else 'bounded_precision_limited'
        if status == 'bounded_width':
            reason = 'strict component interior, excluded complements and bounded arc integral'
        elif calls >= max_evaluations:
            reason = 'valid interval with requested precision limited by the section evaluation budget'
        else:
            reason = 'valid interval with requested precision limited by track or limit conditioning'
        return GeographicWidth(status,width,left,right,tuple(cells),calls,reason,section,epoch_ut1,
                               requested_tolerance_km=F(tolerance_km),model_profile=model_profile,
                               event_domain_offset_days=event_domain)
    except (EnclosureUnavailable,IntervalBudgetError) as exc:
        cells.extend((box,'unresolved','retained_after_failure') for box in pending)
        return GeographicWidth('unresolved',None,None,None,tuple(cells),calls,str(exc),section,epoch_ut1)


def geographic_width_from_frame(frame, *, epoch_ut1=None,**kwargs):
    """Withhold the result when its reference, track or source is unproved."""
    try:
        section = axis_normal_section(frame)
    except (EnclosureUnavailable,IntervalBudgetError) as exc:
        return GeographicWidth('unresolved',None,None,None,(),0,str(exc),None,epoch_ut1)
    return bound_geographic_width(section,epoch_ut1=epoch_ut1,**kwargs)
