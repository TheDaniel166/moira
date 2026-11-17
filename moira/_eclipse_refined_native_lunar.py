"""Native lunar phase covers transported through derived error tubes.

Scalar reference Taylor bounds preserve time correlation at shallow overlap
maxima. The independent uniform error theorem inflates those bounds to the
literal serving margins. Only narrow residual binary64 cells are enumerated.
Source joins are bounded directly and never assigned fictitious continuity.
"""
from dataclasses import dataclass
from fractions import Fraction as F

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_lunar_serving_error import derive_lunar_serving_error_tube
from ._eclipse_piecewise_vectors import enclose_piecewise_eclipse_vectors
from ._eclipse_lunar_piecewise_extrema import bound_piecewise_lunar_observables
from ._eclipse_solar_float_coverage import cover_native_solar_float_path
from ._eclipse_solar_coverage import SolarAxisFunctionBounds
from .constants import EARTH_RADIUS_KM
from .eclipse import _eclipse_body_pair
from .lunar_shadow_models import danjon_angular_shadow,spherical_cone_shadow


@dataclass(frozen=True, slots=True)
class RefinedLunarPanel:
    """A smooth scalar Taylor panel or an explicit source-join panel."""

    domain: I
    continuous: bool
    whole: object
    midpoint: F
    point: object


@dataclass(frozen=True, slots=True)
class RefinedNativeLunarCoverage:
    """Native phase coverage with the independent source error derivation."""

    tt_anchor_jd: float
    domain: I
    policy: str
    earth_radius_scale: float
    error_tube: object
    phases: tuple
    all_represented_inputs_covered: bool
    taylor_panels: int
    scalar_enclosures: int
    reference_point_enclosures: int
    literal_native_points: int
    native_continuity_claimed: bool = False
    physical_accuracy_certified: bool = False


def cover_refined_native_lunar(scope,reader, *, policy,earth_radius_scale=1.,
                               tolerance=F(1,86400000),max_evaluations=4096,
                               max_point_evaluations=32768,progress=None):
    """Prove every native phase sign or retain its bounded unresolved cell.

    The geometry-specific tube is derived once over the complete request.
    Reference scalar curvature on a closed smooth panel proves each Taylor
    value box. Direct piecewise values cover source joins. No measured native
    residual supplies an error budget or justifies a discarded time cell.
    """
    if policy not in ('danjon_angular','static_finite_cone'):
        raise ValueError('unknown selected lunar policy')
    if policy=='danjon_angular' and earth_radius_scale!=1.:
        raise ValueError('Danjon atmospheric convention is fixed')
    tube = derive_lunar_serving_error_tube(scope,
        earth_radius_scale=earth_radius_scale if policy=='static_finite_cone' else 1.01)
    errors = tube.danjon_margin_errors_rad if policy=='danjon_angular' else tube.cone_margin_errors_km
    radius = EARTH_RADIUS_KM*earth_radius_scale
    domain = scope.requested_domain
    anchor = scope.model.tt_anchor_jd
    panels,point_count = [],0

    def observe(box):
        vectors = enclose_piecewise_eclipse_vectors(scope.model,box)
        return vectors,bound_piecewise_lunar_observables(vectors,policy=policy,earth_radius_km=radius)

    stack = [(I(domain.lo+domain.width*n/32,domain.lo+domain.width*(n+1)/32),0) for n in range(32)]
    while stack:
        box,depth = stack.pop()
        try:
            vectors,whole = observe(box)
        except EnclosureUnavailable:
            if depth>=24:
                raise
            mid = box.midpoint
            stack.extend(((I(box.lo,mid),depth+1),(I(mid,box.hi),depth+1)))
            continue
        _,point = observe(I.point(box.midpoint))
        point_count += 1
        panels.append(RefinedLunarPanel(box,vectors.continuous_on_domain,whole,box.midpoint,point))
    panels.sort(key=lambda panel:panel.domain.lo)
    points = {index:{panel.midpoint:panel.point} for index,panel in enumerate(panels)}
    cache,native_points = {},{}

    def margins(box):
        nonlocal point_count
        if box in cache:
            return cache[box]
        if progress is not None and len(cache)%64==0:
            progress(dict(scalar_enclosures=len(cache),reference_points=point_count,
                          width_seconds=float(box.width*86400)))
        values = []
        for index,panel in enumerate(panels):
            owned = box.intersect(panel.domain)
            if owned is None:
                continue
            if not panel.continuous:
                values.append(observe(owned)[1].values[2:])
                continue
            local_points = points[index]
            near = min(local_points,key=lambda value:abs(value-owned.midpoint))
            h = owned-near
            estimated = max(curvature.magnitude*h.magnitude**2/2
                            for curvature in panel.whole.curvatures[2:])
            if owned.width<F(2,86400) and estimated>min(errors)/4:
                near = owned.midpoint
                local_points[near] = observe(I.point(near))[1]
                point_count += 1
                h = owned-near
            point = local_points[near]
            values.append(tuple((value+rate*h+curvature*h.square()/2).quantize_outward(128)
                for value,rate,curvature in zip(point.values[2:],point.rates[2:],panel.whole.curvatures[2:])))
        if not values:
            raise EnclosureUnavailable('reference Taylor panels do not cover requested time')
        result = tuple(I(min(value[k].lo for value in values)-errors[k],
                         max(value[k].hi for value in values)+errors[k]) for k in range(3))
        cache[box] = result
        return result

    def at(jd):
        if jd not in native_points:
            sun,moon = _eclipse_body_pair(jd,reader,sun_retarded=True,moon_retarded=False)
            geometry = (danjon_angular_shadow(sun,moon) if policy=='danjon_angular' else
                        spherical_cone_shadow(sun,moon,earth_radius_scale=earth_radius_scale))
            native_points[jd] = geometry.penumbral_margin,geometry.umbral_margin,geometry.total_margin
        return native_points[jd]

    phases = []
    for phase in range(3):
        def enclosure(box):
            return SolarAxisFunctionBounds(box,margins(box)[phase],I.point(1),I.point(1),I.point(1))

        phases.append(cover_native_solar_float_path(anchor,domain,enclosure,
            lambda jd:'total' if at(jd)[phase]>=0 else 'none',tolerance=tolerance,
            max_interval_evaluations=max_evaluations,max_point_evaluations=max_point_evaluations))
    return RefinedNativeLunarCoverage(anchor,domain,policy,float(earth_radius_scale),tube,tuple(phases),
        all(phase.all_represented_inputs_covered for phase in phases),len(panels),len(cache),
        point_count,len(native_points))
