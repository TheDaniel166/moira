"""Exact-real Danjon angular contact bounds on continuous lunar vectors.

This implements the angular prescription already selected by
``danjon_angular_shadow``: 1.01 times lunar parallax, plus/minus the solar
semidiameter and plus solar parallax. It does not substitute a scaled Earth
in a tangent cone and does not attest the native or NASA-compatible search.
"""
from fractions import Fraction

from ._eclipse_continuous_lunar import (
    ContinuousLunarReference, ContinuousLunarVectorBounds, enclose_continuous_lunar_reference,
)
from ._eclipse_continuous_lunar_contacts import (
    LunarMarginTriplet, _radii, isolate_lunar_margin_triplet,
)
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_inverse_trig import asin_enclosure, atan_enclosure
from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM


def bound_angular_lunar_contacts(
    vectors: ContinuousLunarVectorBounds, *,
    earth_radius_km=EARTH_RADIUS_KM, sun_radius_km=SUN_RADIUS_KM,
    moon_radius_km=MOON_RADIUS_KM, precision_bits: int = 128,
) -> LunarMarginTriplet:
    """Enclose three angular margins (rad) and first TT rates (rad/day).

    Norm, dot and cross products use exact rational interval arithmetic.
    theta=atan(r/z) on the explicitly proved antisolar hemisphere.
    d(asin(R/d))/dt=-R*d'/(d*d*sqrt(1-(R/d)**2));
    theta'=(z*r'-r*z')/(z*z+r*r). Axis singularities retain value bounds
    with unavailable derivatives. All vector continuity/route premises and
    the frozen model's ten real Sun iterations remain explicit prerequisites.
    """
    if not isinstance(vectors, ContinuousLunarVectorBounds):
        raise TypeError("continuous lunar vector bounds required")
    if type(precision_bits) is not int or not 64 <= precision_bits <= 256:
        raise ValueError("precision_bits must be an integer from 64 to 256")
    re, rs, rm = _radii(earth_radius_km, sun_radius_km, moon_radius_km)

    def q(value):
        return value.quantize_outward(precision_bits)

    def dot(a, b):
        return q(sum((x*y for x, y in zip(a, b)), I.point(0)))

    def norm(a):
        return q(sum((x.square() for x in a), I.point(0)).sqrt(precision_bits))

    def cross(a, b):
        return (q(a[1]*b[2] - a[2]*b[1]), q(a[2]*b[0] - a[0]*b[2]),
                q(a[0]*b[1] - a[1]*b[0]))

    sun, moon = vectors.sun_geocentric_km, vectors.moon_geocentric_km
    sv, mv = vectors.sun_derivative_km_per_tt_day, vectors.moon_derivative_km_per_tt_day
    if any(not isinstance(v, tuple) or len(v) != 3 or not all(isinstance(x, I) for x in v)
           for v in (sun, moon, sv, mv)):
        raise TypeError("three interval components and derivatives required")
    ds, dm = norm(sun), norm(moon)
    if ds.lo <= rs + re or dm.lo <= re + rm:
        raise EnclosureUnavailable("disjoint angular source domains not proved")
    ds_rate, dm_rate = q(dot(sun, sv)/ds), q(dot(moon, mv)/dm)
    projection = dot(sun, moon)
    z = q(-projection/ds)
    if z.lo <= 0:
        raise EnclosureUnavailable("antisolar angular domain not proved")
    z_rate = q(-(dot(sv, moon) + dot(sun, mv))/ds + projection*ds_rate/ds.square())
    product = cross(moon, sun)
    product_rate = tuple(q(x+y) for x, y in zip(cross(mv, sun), cross(moon, sv)))
    cross_norm = norm(product)
    radial = q(cross_norm/ds)
    theta = atan_enclosure(q(radial/z), precision_bits=precision_bits)
    theta_rate = None
    if cross_norm.lo > 0 and vectors.continuous_on_domain and vectors.differentiable_on_domain:
        radial_rate = q(dot(product, product_rate)/(cross_norm*ds) - cross_norm*ds_rate/ds.square())
        theta_rate = q((z*radial_rate - radial*z_rate)/(z.square() + radial.square()))

    def angle(radius, distance, rate):
        ratio = q(I.point(radius)/distance)
        if ratio.lo <= 0 or ratio.hi >= 1:
            raise EnclosureUnavailable("angular radius domain not proved")
        value = asin_enclosure(ratio, precision_bits=precision_bits)
        cosine = (1 - ratio.square()).sqrt(precision_bits)
        if cosine.lo <= 0:
            raise EnclosureUnavailable("angular radius derivative denominator not proved")
        return value, q(-radius*rate/(distance.square()*cosine))

    pm, pm_rate = angle(re, dm, dm_rate)
    alpha, alpha_rate = angle(rm, dm, dm_rate)
    ss, ss_rate = angle(rs, ds, ds_rate)
    ps, ps_rate = angle(re, ds, ds_rate)
    factor = Fraction.from_float(1.01)
    bp, bu = q(factor*pm + ss + ps), q(factor*pm - ss + ps)
    if bu.lo <= 0 or (bp + alpha).hi >= 3:
        # 3 < pi. This explicitly supported subdomain proves the original
        # angular-circle domain without assuming a libm value of pi.
        raise EnclosureUnavailable("Danjon angular-circle domain not proved")
    margins = q(bp + alpha - theta), q(bu + alpha - theta), q(bu - alpha - theta)
    if theta_rate is None:
        rates = None, None, None
    else:
        bp_rate = q(factor*pm_rate + ss_rate + ps_rate)
        bu_rate = q(factor*pm_rate - ss_rate + ps_rate)
        rates = (q(bp_rate + alpha_rate - theta_rate),
                 q(bu_rate + alpha_rate - theta_rate),
                 q(bu_rate - alpha_rate - theta_rate))
    return LunarMarginTriplet(vectors.tt_offset_days, margins, rates)


def isolate_continuous_angular_contacts(
    model: ContinuousLunarReference, domain: I, *, tolerance,
    earth_radius_km=EARTH_RADIUS_KM, sun_radius_km=SUN_RADIUS_KM,
    moon_radius_km=MOON_RADIUS_KM, max_evaluations: int = 10000, max_depth: int = 80,
):
    """Partition every supplied TT offset for the selected angular reference.

    Units are explicit radians for margins and days for the TT input. This
    uses neither a cone Earth-scale substitute nor the rounded canon solver.
    Unknown domains and exhausted shared budgets remain covering root cells.
    """
    if not isinstance(model, ContinuousLunarReference) or not isinstance(domain, I):
        raise TypeError("continuous reference and rational TT domain required")
    if domain.lo < model.tt_offset_days.lo or domain.hi > model.tt_offset_days.hi:
        raise ValueError("contact domain lies outside the frozen reference")
    _radii(earth_radius_km, sun_radius_km, moon_radius_km)

    def enclosure(box):
        vectors = enclose_continuous_lunar_reference(model, box)
        if not vectors.continuous_on_domain:
            raise EnclosureUnavailable("continuous vector model not established")
        return bound_angular_lunar_contacts(
            vectors, earth_radius_km=earth_radius_km, sun_radius_km=sun_radius_km,
            moon_radius_km=moon_radius_km, precision_bits=model.precision_bits,
        )

    return isolate_lunar_margin_triplet(
        domain, enclosure, tolerance=tolerance, continuity_assumed=True,
        margin_unit="rad", model_policy="danjon_angular_reference",
        max_evaluations=max_evaluations, max_depth=max_depth,
    )
