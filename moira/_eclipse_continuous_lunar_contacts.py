"""Continuous finite-cone reference contact enclosures and root coverage.

The mathematical object is the signed sphere/cone clearance used by
``spherical_cone_shadow``, interpreted in real arithmetic on an explicitly
continuous vector model. It is distinct from the rounded serving calculation,
the angular/Danjon policy and a physical eclipse. A complete root partition
concerns only the supplied closed TT domain and those model premises.

The three margins are kept separate. No full-moon neighbourhood, sample grid,
negative sample or contact bracket is promoted to a complete event search.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable

from ._eclipse_continuous_lunar import (
    ContinuousLunarReference,
    ContinuousLunarVectorBounds,
    enclose_continuous_lunar_reference,
)
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable, RootPartition, isolate_roots
from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM


@dataclass(frozen=True, slots=True)
class ContinuousLunarContactBounds:
    """Real finite-cone margins in km and optional TT derivatives in km/day.

    A missing derivative denotes an unproved differentiability domain; the
    value enclosure can still exclude a root. Positive margins mean overlap
    or, for ``total``, containment. These are infinite positive-nappe distances
    on the supported downstream domain, with the same signs as the truncated
    physical cone predicates. They carry no serving or physical attestation.
    """

    tt_offset_days: I
    penumbral_margin_km: I
    umbral_margin_km: I
    total_margin_km: I
    penumbral_derivative_km_per_day: I | None
    umbral_derivative_km_per_day: I | None
    total_derivative_km_per_day: I | None
    axis_distance_km: I
    effective_earth_radius_km: Fraction
    sun_radius_km: Fraction
    moon_radius_km: Fraction
    exact_reference_model_only: bool = True
    serving_evaluator_enclosed: bool = False
    physical_accuracy_certified: bool = False


@dataclass(frozen=True, slots=True)
class ContinuousLunarContactPartition:
    """Three separate covering partitions with a shared callback budget.

    Root cells on opposite sides of a shared endpoint may describe the same
    contact; they are not deduplicated P1/U1/U2/U3/U4/P4 identities. The result
    does not establish local/global extrema, exclude other TT intervals, or
    classify a live or physical eclipse. Unknown cells remain in each cover.
    """

    domain: I
    penumbral: RootPartition
    umbral: RootPartition
    total: RootPartition
    evaluations: int
    max_evaluations: int
    vector_evaluations: int
    exact_reference_model_only: bool = True
    serving_evaluator_enclosed: bool = False
    eclipse_absence_certified: bool = False
    physical_accuracy_certified: bool = False
    margin_unit: str = "km"
    model_policy: str = "static_finite_cone_reference"


@dataclass(frozen=True, slots=True)
class LunarMarginTriplet:
    """One named geometry's three margins and derivatives on the same domain."""

    domain: I
    margins: tuple[I, I, I]
    derivatives: tuple[I | None, I | None, I | None]


def _radii(earth, sun, moon) -> tuple[Fraction, Fraction, Fraction]:
    """Retain exact represented radii and reject invalid cone definitions."""
    values = tuple(I.point(value) for value in (earth, sun, moon))
    if any(value.lo != value.hi or value.lo <= 0 for value in values):
        raise ValueError("radii must be finite positive exact points")
    re, rs, rm = (value.lo for value in values)
    if re >= rs:
        raise ValueError("effective Earth radius must be smaller than Sun radius")
    return re, rs, rm


def bound_continuous_lunar_contacts(
    vectors: ContinuousLunarVectorBounds, *,
    effective_earth_radius_km=EARTH_RADIUS_KM,
    sun_radius_km=SUN_RADIUS_KM,
    moon_radius_km=MOON_RADIUS_KM,
    precision_bits: int = 128,
) -> ContinuousLunarContactBounds:
    """Enclose exact-real margins and their signed first TT derivatives.

    Derivation: let ``s`` be Sun distance, ``z`` the Moon's antisolar-axis
    coordinate, and ``r`` its perpendicular distance. For effective Earth,
    Sun and Moon radii E, S and M, put p=(S+E)/s, u=(S-E)/s,
    cp=sqrt(1-p*p), cu=sqrt(1-u*u). Penumbral overlap is
    E+p*z-cp*r+M. The forward umbral plane clearance is E-u*z-cu*r;
    behind its apex/nappe it is -hypot(E/u-z, r). Add M for overlap and
    subtract M for total containment. This is the selected static spherical
    sensitivity model, not NASA's atmospheric angular shadow prescription.

    All arithmetic is rational interval arithmetic with outward dyadic
    quantization and integer-certified square roots. First derivatives use
    product, quotient and chain rules on the same real vector model. At an
    axis/apex singularity the derivative can be unavailable; neither a
    derivative nor a domain obligation is inferred from finite samples.
    """
    if not isinstance(vectors, ContinuousLunarVectorBounds):
        raise TypeError("continuous lunar vector bounds required")
    if type(precision_bits) is not int or not 64 <= precision_bits <= 256:
        raise ValueError("precision_bits must be an integer from 64 to 256")
    re, rs, rm = _radii(effective_earth_radius_km, sun_radius_km, moon_radius_km)

    def q(value):
        return value.quantize_outward(precision_bits)

    def scalar(value):
        return I.point(value), I.point(0)

    def add(a, b):
        rate = None if a[1] is None or b[1] is None else q(a[1] + b[1])
        return q(a[0] + b[0]), rate

    def neg(a):
        return -a[0], None if a[1] is None else -a[1]

    def sub(a, b):
        return add(a, neg(b))

    def mul(a, b):
        rate = None if a[1] is None or b[1] is None else q(a[1] * b[0] + a[0] * b[1])
        return q(a[0] * b[0]), rate

    def square(a):
        rate = None if a[1] is None else q(2 * a[0] * a[1])
        return q(a[0].square()), rate

    def div(a, b):
        if b[0].contains_zero:
            raise EnclosureUnavailable("reference cone denominator may vanish")
        rate = None if a[1] is None or b[1] is None else q(
            (a[1] * b[0] - a[0] * b[1]) / b[0].square())
        return q(a[0] / b[0]), rate

    def sqrt(a):
        if a[0].lo < 0:
            raise EnclosureUnavailable("reference cone square-root domain not proved")
        value = a[0].sqrt(precision_bits)
        rate = None if a[1] is None or value.lo == 0 else q(a[1] / (2 * value))
        return value, rate

    def dot(a, b):
        result = scalar(0)
        for left, right in zip(a, b):
            result = add(result, mul(left, right))
        return result

    def norm_squared(a):
        result = scalar(0)
        for component in a:
            result = add(result, square(component))
        return result

    def checked_vector(values, rates):
        if (not isinstance(values, tuple) or len(values) != 3
                or not isinstance(rates, tuple) or len(rates) != 3
                or not all(isinstance(value, I) for value in values + rates)):
            raise TypeError("three interval components and derivatives required")
        return tuple((value, rate if vectors.continuous_on_domain and vectors.differentiable_on_domain else None)
                     for value, rate in zip(values, rates))

    sun = checked_vector(vectors.sun_geocentric_km, vectors.sun_derivative_km_per_tt_day)
    moon = checked_vector(vectors.moon_geocentric_km, vectors.moon_derivative_km_per_tt_day)
    distance = sqrt(norm_squared(sun))
    moon_distance = sqrt(norm_squared(moon))
    if distance[0].lo <= rs + re or moon_distance[0].lo <= re + rm:
        raise EnclosureUnavailable("disjoint spherical source domains not proved")
    axis = tuple(neg(div(component, distance)) for component in sun)
    z = dot(moon, axis)
    if z[0].lo - rm < re:
        raise EnclosureUnavailable("whole Moon downstream domain not proved")
    cross = (
        sub(mul(moon[1], axis[2]), mul(moon[2], axis[1])),
        sub(mul(moon[2], axis[0]), mul(moon[0], axis[2])),
        sub(mul(moon[0], axis[1]), mul(moon[1], axis[0])),
    )
    radial_squared = norm_squared(cross)
    radial = sqrt(radial_squared)
    p, u = div(scalar(rs + re), distance), div(scalar(rs - re), distance)
    if not (0 < u[0].lo <= u[0].hi < 1 and 0 < p[0].lo <= p[0].hi < 1):
        raise EnclosureUnavailable("reference cone angles not proved")
    cp, cu = sqrt(sub(scalar(1), square(p))), sqrt(sub(scalar(1), square(u)))
    pen = add(sub(add(scalar(re), mul(p, z)), mul(cp, radial)), scalar(rm))
    plane = sub(sub(scalar(re), mul(u, z)), mul(cu, radial))
    apex_t = sub(div(scalar(re), u), z)
    nappe = add(apex_t, mul(div(u, cu), radial))[0]
    if nappe.lo > 0:
        clearance = plane
    else:
        behind = neg(sqrt(add(square(apex_t), radial_squared)))
        if nappe.hi <= 0:
            clearance = behind
        else:
            # Both branches meet continuously. Hull their derivatives only
            # when both are defined; the apex itself remains unproved.
            rate = None if plane[1] is None or behind[1] is None else I(
                min(plane[1].lo, behind[1].lo), max(plane[1].hi, behind[1].hi))
            clearance = I(min(plane[0].lo, behind[0].lo), max(plane[0].hi, behind[0].hi)), rate
    umb, total = add(clearance, scalar(rm)), sub(clearance, scalar(rm))
    return ContinuousLunarContactBounds(
        vectors.tt_offset_days, pen[0], umb[0], total[0], pen[1], umb[1], total[1],
        radial[0], re, rs, rm,
    )


def isolate_lunar_margin_triplet(
    domain: I,
    contact_enclosure: Callable[[I], LunarMarginTriplet], *,
    tolerance: int | float | Fraction | I,
    continuity_assumed: bool,
    margin_unit: str,
    model_policy: str,
    max_evaluations: int = 10000,
    max_depth: int = 80,
) -> ContinuousLunarContactPartition:
    """Share one root-callback budget across three model-specific predicates.

    The provider must enclose the same continuous vector functions throughout
    the domain, including shared endpoints. Frozen records, seams, radii and
    source identity remain the provider/caller's obligations. The single
    callback budget is shared in penumbral, umbral, total order. Immutable
    vector/margin bounds are reused within this invocation only. Derivative
    callbacks count toward the budget even when their value is cached.

    A rejected geometry, unsupported seam, tangent or exhausted budget remains
    unresolved. Complete partitions would establish all reference contact
    roots in this domain, subject to their retained continuity assumptions;
    they do not certify an entire lunation or a serving eclipse search.
    """
    if not isinstance(domain, I):
        raise TypeError("TT domain must be a RationalInterval")
    if type(continuity_assumed) is not bool:
        raise TypeError("continuity_assumed must be a bool")
    if type(max_evaluations) is not int or max_evaluations < 0:
        raise ValueError("max_evaluations must be a nonnegative integer")
    if margin_unit not in ("km", "rad") or not isinstance(model_policy, str) or not model_policy:
        raise ValueError("explicit margin unit and model policy required")
    cache: dict[tuple[Fraction, Fraction], LunarMarginTriplet] = {}
    vector_evaluations = 0

    def observe(box):
        nonlocal vector_evaluations
        key = box.lo, box.hi
        if key not in cache:
            vector_evaluations += 1
            value = contact_enclosure(box)
            if not isinstance(value, LunarMarginTriplet) or value.domain != box:
                raise TypeError("provider must retain exactly the requested TT offset domain")
            if (len(value.margins) != 3 or len(value.derivatives) != 3
                    or not all(isinstance(item, I) for item in value.margins)
                    or not all(item is None or isinstance(item, I) for item in value.derivatives)):
                raise TypeError("three margin intervals and optional derivative intervals required")
            cache[key] = value
        return cache[key]

    partitions = []
    evaluations = 0
    for index in range(3):
        def margin(box):
            return observe(box).margins[index]

        def derivative(box):
            value = observe(box).derivatives[index]
            if value is None:
                raise EnclosureUnavailable("reference margin differentiability not proved")
            return value

        roots = isolate_roots(
            domain, margin, tolerance=tolerance, unit="day offset from TT anchor",
            time_scale="TT", derivative=derivative, continuous=continuity_assumed,
            max_evaluations=max_evaluations - evaluations, max_depth=max_depth,
        )
        partitions.append(roots)
        evaluations += roots.evaluations
    return ContinuousLunarContactPartition(
        domain, *partitions, evaluations, max_evaluations, vector_evaluations,
        margin_unit=margin_unit, model_policy=model_policy,
    )


def isolate_lunar_reference_contacts(
    domain: I,
    vector_enclosure: Callable[[I], ContinuousLunarVectorBounds], *,
    tolerance: int | float | Fraction | I,
    continuity_assumed: bool,
    effective_earth_radius_km=EARTH_RADIUS_KM,
    sun_radius_km=SUN_RADIUS_KM,
    moon_radius_km=MOON_RADIUS_KM,
    precision_bits: int = 128,
    max_evaluations: int = 10000,
    max_depth: int = 80,
) -> ContinuousLunarContactPartition:
    """Partition all three finite-cone margins on the full requested domain.

    Input radii and source/reference premises retain the contract of
    ``bound_continuous_lunar_contacts``. Root callback accounting, unresolved
    cells and shared endpoints follow ``isolate_lunar_margin_triplet``.
    """
    _radii(effective_earth_radius_km, sun_radius_km, moon_radius_km)
    if type(precision_bits) is not int or not 64 <= precision_bits <= 256:
        raise ValueError("precision_bits must be an integer from 64 to 256")

    def enclosure(box):
        vectors = vector_enclosure(box)
        if not isinstance(vectors, ContinuousLunarVectorBounds) or vectors.tt_offset_days != box:
            raise TypeError("provider must retain exactly the requested TT offset domain")
        if continuity_assumed and not vectors.continuous_on_domain:
            raise EnclosureUnavailable("continuous vector model not established")
        value = bound_continuous_lunar_contacts(
            vectors, effective_earth_radius_km=effective_earth_radius_km,
            sun_radius_km=sun_radius_km, moon_radius_km=moon_radius_km,
            precision_bits=precision_bits,
        )
        return LunarMarginTriplet(box,
            (value.penumbral_margin_km, value.umbral_margin_km, value.total_margin_km),
            (value.penumbral_derivative_km_per_day, value.umbral_derivative_km_per_day,
             value.total_derivative_km_per_day))

    return isolate_lunar_margin_triplet(
        domain, enclosure, tolerance=tolerance, continuity_assumed=continuity_assumed,
        margin_unit="km", model_policy="static_finite_cone_reference",
        max_evaluations=max_evaluations, max_depth=max_depth,
    )


def isolate_continuous_lunar_contacts(
    model: ContinuousLunarReference,
    domain: I, *,
    tolerance: int | float | Fraction | I,
    effective_earth_radius_km=EARTH_RADIUS_KM,
    sun_radius_km=SUN_RADIUS_KM,
    moon_radius_km=MOON_RADIUS_KM,
    max_evaluations: int = 10000,
    max_depth: int = 80,
) -> ContinuousLunarContactPartition:
    """Use one frozen continuous reference on a contained closed TT domain.

    The existing reference's uniform INIT/INTLEN normalization, real TT/TDB
    relation, ten real Sun-delay updates and unsupported-seam policy remain
    explicit. This function neither reads another kernel nor changes the
    serving finite-cone, angular, native or NASA-compatible policies.
    """
    if not isinstance(model, ContinuousLunarReference):
        raise TypeError("continuous lunar reference model required")
    if not isinstance(domain, I):
        raise TypeError("TT domain must be a RationalInterval")
    if domain.lo < model.tt_offset_days.lo or domain.hi > model.tt_offset_days.hi:
        raise ValueError("contact domain lies outside the frozen reference")
    return isolate_lunar_reference_contacts(
        domain, lambda box: enclose_continuous_lunar_reference(model, box),
        tolerance=tolerance, continuity_assumed=True,
        effective_earth_radius_km=effective_earth_radius_km,
        sun_radius_km=sun_radius_km, moon_radius_km=moon_radius_km,
        precision_bits=model.precision_bits,
        max_evaluations=max_evaluations, max_depth=max_depth,
    )
