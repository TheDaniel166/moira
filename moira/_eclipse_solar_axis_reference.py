"""Real-arithmetic WGS84 central-axis predicates from bounded Sun/Moon vectors.

This derives the line/ellipsoid discriminant, near-side ray and signed
spherical-cone radius from their geometric objects. The interval result
describes this exact-real reference, not every rounded operation in
``_earth_fixed_solar_shadow``. Input vector/model continuity is explicit.
"""
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_solar_coverage import SolarAxisFunctionBounds
from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM
from .eclipse import _WGS84_POLAR_RADIUS_KM


def bound_solar_axis_reference(
    domain: I, sun: tuple[I, I, I], moon: tuple[I, I, I], *,
    sun_rate=None, moon_rate=None, earth_major_km=EARTH_RADIUS_KM,
    earth_minor_km=_WGS84_POLAR_RADIUS_KM, sun_radius_km=SUN_RADIUS_KM,
    moon_radius_km=MOON_RADIUS_KM, precision_bits: int = 128,
    continuous_model: bool = False,
) -> SolarAxisFunctionBounds:
    """Enclose axis/ellipsoid and near-side cone functions and optional rates.

    A=sum(a_i^2/e_i^2), B=sum(p_i*a_i/e_i^2), C=sum(p_i^2/e_i^2)-1
    for the exact unit Sun-to-Moon axis a and fundamental-plane point p.
    The signed half-chord squared is (B^2-A*C)/A^2; the near parameter
    is -B/A-sqrt(half_chord_squared). The signed radius there is
    (Rm-(t-proj)*sin(f))/cos(f), sin(f)=(Rs-Rm)/|Moon-Sun|.

    For a strictly interior near intersection, the ellipsoid normal dotted
    with the sunward ray is positive: B+A*t=-sqrt(B^2-A*C), and the Sun
    is earlier on that exact line. Thus a proved forward distance also proves
    geometric Sun-centre daylight on the strict interior. Exact endpoints
    are horizon limits. This algebraic proof is not applied to independently
    rounded axis/plane vectors, which need their own residual treatment.
    """
    if not isinstance(domain, I) or type(continuous_model) is not bool:
        raise TypeError('rational domain and explicit continuity flag required')
    if type(precision_bits) is not int or not 64 <= precision_bits <= 256:
        raise ValueError('invalid solar reference precision')
    for vector in (sun, moon):
        if not isinstance(vector, tuple) or len(vector) != 3 or not all(isinstance(x, I) for x in vector):
            raise TypeError('three interval vector components required')
    radii = tuple(I.point(x) for x in (earth_major_km, earth_minor_km, sun_radius_km, moon_radius_km))
    if any(x.lo != x.hi or x.lo <= 0 for x in radii):
        raise ValueError('positive exact radii required')
    ea, eb, rs, rm = (x.lo for x in radii)
    if eb > ea or rs <= rm:
        raise ValueError('invalid ellipsoid or solar/lunar radii')
    rates = sun_rate is not None or moon_rate is not None
    if rates and any(not isinstance(v, tuple) or len(v) != 3 or not all(isinstance(x, I) for x in v)
                     for v in (sun_rate, moon_rate)):
        raise TypeError('both vector rates must contain three intervals')

    def q(value):
        return value.quantize_outward(precision_bits)

    def dot(a, b):
        return q(sum((x*y for x, y in zip(a, b)), I.point(0)))

    def norm(a):
        return q(sum((x.square() for x in a), I.point(0)).sqrt(precision_bits))

    if norm(sun).lo <= rs + ea or norm(moon).lo <= rm + ea:
        raise EnclosureUnavailable('disjoint source/ellipsoid domains not proved')
    delta = tuple(q(m-s) for m, s in zip(moon, sun))
    distance = norm(delta)
    if distance.lo <= rs + rm:
        raise EnclosureUnavailable('source-separation domain not proved')
    axis = tuple(q(x/distance) for x in delta)
    projection = dot(moon, axis)
    plane = tuple(q(m-projection*a) for m, a in zip(moon, axis))
    weights = (1/(ea*ea), 1/(ea*ea), 1/(eb*eb))
    a = q(sum((w*x.square() for w, x in zip(weights, axis)), I.point(0)))
    b = q(sum((w*x*y for w, x, y in zip(weights, plane, axis)), I.point(0)))
    c = q(sum((w*x.square() for w, x in zip(weights, plane)), I.point(0))-1)
    if a.lo <= 0:
        raise EnclosureUnavailable('ellipsoid direction denominator not proved')
    discriminant = q((b.square()-a*c)/a.square())
    dd = None
    if rates:
        dv = tuple(q(m-s) for m, s in zip(moon_rate, sun_rate))
        distance_rate = q(dot(delta, dv)/distance)
        av = tuple(q((v-x*distance_rate)/distance) for v, x in zip(dv, axis))
        projection_rate = q(dot(moon_rate, axis)+dot(moon, av))
        pv = tuple(q(m-projection_rate*x-projection*v) for m, x, v in zip(moon_rate, axis, av))
        da = q(2*sum((w*x*v for w, x, v in zip(weights, axis, av)), I.point(0)))
        db = q(sum((w*(v*x+p*y) for w, v, x, p, y in zip(weights, pv, axis, plane, av)), I.point(0)))
        dc = q(2*sum((w*x*v for w, x, v in zip(weights, plane, pv)), I.point(0)))
        raw = q(b.square()-a*c)
        raw_rate = q(2*b*db-da*c-a*dc)
        dd = q(raw_rate/a.square()-2*raw*da/(a**3))
    if discriminant.hi < 0:
        return SolarAxisFunctionBounds(domain, discriminant, None, None, None,
                                       axis_derivative=dd, real_continuous_model=continuous_model)
    # Other fields enclose only the subset where the exact axis intersects.
    half = I(max(0, discriminant.lo), discriminant.hi).sqrt(precision_bits)
    center = q(-b/a)
    near = q(center-half)
    forward = q(near-projection-rm)
    sine = q(I.point(rs-rm)/distance)
    if sine.lo <= 0 or sine.hi >= 1:
        raise EnclosureUnavailable('central cone opening not proved')
    cosine = (1-sine.square()).sqrt(precision_bits)
    if cosine.lo <= 0:
        raise EnclosureUnavailable('central cone cosine not proved')
    numerator = q(rm-(near-projection)*sine)
    radius = q(numerator/cosine)
    kr = None
    if rates and discriminant.lo > 0:
        center_rate = q(-db/a+b*da/a.square())
        near_rate = q(center_rate-dd/(2*half))
        sine_rate = q(-I.point(rs-rm)*distance_rate/distance.square())
        cosine_rate = q(-sine*sine_rate/cosine)
        numerator_rate = q(-(near_rate-projection_rate)*sine-(near-projection)*sine_rate)
        kr = q(numerator_rate/cosine-numerator*cosine_rate/cosine.square())
    return SolarAxisFunctionBounds(
        domain, discriminant, radius, forward, None, dd, kr,
        daylight_interior_proved=forward.lo > 0,
        real_continuous_model=continuous_model,
    )
