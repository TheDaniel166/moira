"""Complete represented-TT phase coverage of the selected lunar policies.

Frozen native record recurrences enclose the actual retarded-Sun/geometric-
Moon route. Rounded geometry is bounded separately from real-reference
contact/critical-point proofs. Exhaustive boundary cells close the binary64
input set without claiming continuity of floating-point evaluation. Caller
resource, binary and source lifetime premises remain explicit.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import math

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded as r,_fsum
from ._eclipse_frozen_native_vectors import bound_frozen_native_vectors
from ._eclipse_inverse_trig import asin_enclosure,atan_enclosure
from ._eclipse_lunar_cone_bounds import _hypot_box,bound_lunar_cone_penumbral_margin
from ._eclipse_solar_coverage import SolarAxisFunctionBounds
from ._eclipse_solar_float_coverage import cover_native_solar_float_path,SolarFloatPathCoverage
from .constants import EARTH_RADIUS_KM,MOON_RADIUS_KM,SUN_RADIUS_KM
from .eclipse import _eclipse_body_pair
from .lunar_shadow_models import danjon_angular_shadow,spherical_cone_shadow


def _libm_one_ulp(box):
    lower,upper = box.to_float_bounds()
    for _ in range(2):
        lower,upper = math.nextafter(lower,-math.inf),math.nextafter(upper,math.inf)
    return I(lower,upper)


def bound_native_danjon_margins(sun,moon):
    """Enclose the source's geometry, including all rejection guards.

    Hypot/fsum and inverse trig require their declared one-ulp premises;
    binary64 nearest/gradual arithmetic and stable source/constants are
    required. Inverse-trig reference values have rational remainder proofs.
    This is a whole-vector-box inclusion, not a sampled serving comparison.
    """
    re,rs,rm = map(I.point,(EARTH_RADIUS_KM,SUN_RADIUS_KM,MOON_RADIUS_KM))
    s,d = _hypot_box(sun),_hypot_box(moon)
    if s.lo<=r(rs+re).hi or d.lo<=r(re+rm).hi:
        raise EnclosureUnavailable('Danjon disjoint-source guard unproved')
    axis = tuple(r(-value/s) for value in sun)
    z = _fsum(tuple(r(m*a) for m,a in zip(moon,axis)))
    if z.lo<=0:
        raise EnclosureUnavailable('Danjon antisolar domain unproved')
    cross = tuple(r(r(moon[a]*axis[b])-r(moon[b]*axis[a])) for a,b in ((1,2),(2,0),(0,1)))
    radial = _hypot_box(cross)
    theta = _libm_one_ulp(atan_enclosure(radial/z))
    angles = tuple(_libm_one_ulp(asin_enclosure(r(radius/distance)))
                   for radius,distance in ((re,d),(re,s),(rs,s),(rm,d)))
    pm,ps,ss,alpha = angles
    common = r(I.point(1.01)*pm)
    pen = r(r(common+ss)+ps)
    umb = r(r(common-ss)+ps)
    if alpha.lo<=0 or umb.lo<=0 or r(pen+alpha).hi>=F.from_float(math.pi):
        raise EnclosureUnavailable('Danjon angular guard unproved')
    margins = r(r(pen+alpha)-theta),r(r(umb+alpha)-theta),r(r(umb-alpha)-theta)
    # The full source also computes magnitudes; prove their finite positive
    # divisor rather than considering only a successful-return subset.
    denominator = r(2*alpha)
    for margin in margins[:2]:
        r(margin/denominator)
    return margins


def bound_native_lunar_objectives(sun,moon, *, policy,earth_radius_scale=1.):
    """Enclose independent native axis/angle/overlap objectives on one box."""
    norm = _hypot_box(sun)
    axis = tuple(r(-value/norm) for value in sun)
    z = _fsum(tuple(r(m*a) for m,a in zip(moon,axis)))
    if z.lo<=0:
        raise EnclosureUnavailable('native objective antisolar domain unproved')
    cross = tuple(r(r(moon[a]*axis[b])-r(moon[b]*axis[a])) for a,b in ((1,2),(2,0),(0,1)))
    radial = _hypot_box(cross)
    theta = _libm_one_ulp(atan_enclosure(radial/z))
    if policy=='danjon_angular':
        if earth_radius_scale!=1.:
            raise ValueError('Danjon scaling is fixed by its own convention')
        margins = bound_native_danjon_margins(sun,moon)
    elif policy=='static_finite_cone':
        cone = bound_lunar_cone_penumbral_margin(sun,moon,earth_radius_scale=earth_radius_scale)
        margins = cone.penumbral_margin_km,cone.umbral_margin_km,cone.total_margin_km
    else:
        raise ValueError('unknown selected lunar policy')
    return radial,theta,*margins


@dataclass(frozen=True, slots=True)
class NativeLunarStage3Coverage:
    """Three complete or explicitly unresolved phase partitions."""

    tt_anchor_jd: float
    domain: I
    policy: str
    earth_radius_scale: float
    phases: tuple[SolarFloatPathCoverage,...]
    distinct_vector_boxes: int
    literal_native_points: int
    all_represented_inputs_covered: bool
    real_continuity_claimed: bool = False
    physical_accuracy_certified: bool = False


def cover_native_lunar_stage3(scope,reader,domain: I, *, policy,earth_radius_scale=1.,
                              tolerance=F(1,86400000),max_interval_evaluations=4096,
                              max_point_evaluations=8192,progress=None):
    """Cover every represented TT input of each phase on the entire domain.

    A native compiler/libm contract and stable reader/source lifetime must be
    established independently. Unsupported branches, missing data and budget
    limits remain bounded unresolved cells. The native TT partitions join
    the separate real-reference contact/critical sets; no IVT is asserted for
    rounded execution. UT1/canon conversion is a separate, explicit mapping.
    """
    if policy not in ('danjon_angular','static_finite_cone'):
        raise ValueError('unknown selected lunar policy')
    if policy=='danjon_angular' and earth_radius_scale!=1.:
        raise ValueError('Danjon has its own fixed atmospheric convention')
    anchor = scope.model.tt_anchor_jd
    boxes,points = {},{}

    def margins(box):
        if box not in boxes:
            if progress is not None and len(boxes)%64==0:
                progress(dict(vector_boxes=len(boxes),current_width_seconds=float(box.width*86400)))
            vectors = bound_frozen_native_vectors(scope,box,moon_retarded=False)
            if policy=='danjon_angular':
                value = bound_native_danjon_margins(vectors.sun_retarded_km,vectors.moon_retarded_km)
            else:
                cone = bound_lunar_cone_penumbral_margin(vectors.sun_retarded_km,vectors.moon_retarded_km,
                                                        earth_radius_scale=earth_radius_scale)
                value = cone.penumbral_margin_km,cone.umbral_margin_km,cone.total_margin_km
            boxes[box] = value
        return boxes[box]

    def at(jd):
        if jd not in points:
            sun,moon = _eclipse_body_pair(jd,reader,sun_retarded=True,moon_retarded=False)
            state = (danjon_angular_shadow(sun,moon) if policy=='danjon_angular' else
                     spherical_cone_shadow(sun,moon,earth_radius_scale=earth_radius_scale))
            points[jd] = state.penumbral_margin,state.umbral_margin,state.total_margin
        return points[jd]

    phases = []
    for phase in range(3):
        def enclosure(box):
            return SolarAxisFunctionBounds(box,margins(box)[phase],I.point(1),I.point(1),I.point(1))

        def evaluate(jd):
            return 'total' if at(jd)[phase]>=0 else 'none'

        phases.append(cover_native_solar_float_path(anchor,domain,enclosure,evaluate,tolerance=tolerance,
            max_interval_evaluations=max_interval_evaluations,max_point_evaluations=max_point_evaluations))
    return NativeLunarStage3Coverage(anchor,domain,policy,float(earth_radius_scale),tuple(phases),
        len(boxes),len(points),all(phase.all_represented_inputs_covered for phase in phases))
