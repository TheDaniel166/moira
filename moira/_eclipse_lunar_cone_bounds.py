"""Conditional binary64 enclosure of the finite-cone penumbral margin.

This private adapter models the successful split-vector and downstream cone
branches. Its source/build/rounding and library-function assumptions remain
unattested. It neither covers legacy single-part fallback nor proves UT1,
contact completeness, eclipse classification, or physical accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _fsum, _rounded
from ._eclipse_serving_astro import ConditionalLunarServingBounds, bound_conditional_lunar_serving_vectors
from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM


class EclipseLunarConeUnavailable(EnclosureUnavailable):
    """The conditional finite-cone margin could not be enclosed."""


def _hypot_box(values: tuple[I, ...]) -> I:
    """Enclose a hypot result under the stated one-ulp error premise.

    Two representable steps are needed because spacing changes at powers of
    two; one ulp on the coarser side may span two numbers on the finer side.
    """
    exact = sum((x.square() for x in values), I.point(0)).sqrt(128)
    lo, hi = exact.to_float_bounds()
    for _ in range(2):
        lo = max(0.0, math.nextafter(lo, -math.inf))
        hi = math.nextafter(hi, math.inf)
    if not math.isfinite(hi):
        raise EclipseLunarConeUnavailable("hypot may not return finite values")
    return I(lo, hi)


@dataclass(frozen=True, slots=True)
class ConditionalLunarConeMargin:
    """A signed-kilometre margin for one conditional vector-box domain."""

    penumbral_margin_km: I
    antisolar_axis_projection_km: I
    axis_distance_km: I
    effective_earth_radius_km: I
    umbral_margin_km: I
    total_margin_km: I
    umbral_nappe_branch: Literal["positive", "apex"]
    source_and_constants_unchanged_required: bool = True
    arithmetic_model: str = (
        "binary64 RN; gradual underflow; sqrt correctly rounded; "
        "hypot <=1 ulp; fsum <=1 ulp; atan2 finite on finite inputs"
    )
    represented_finite_float_vectors_required: bool = True
    geometry_total_for_vector_box_under_premises: bool = True
    successful_full_cone_evaluation_required: bool = False
    arithmetic_environment_attested: bool = False
    source_and_kernel_attested: bool = False
    physical_accuracy_certified: bool = False
    eclipse_classification_certified: bool = False
    event_search_complete: bool = False


@dataclass(frozen=True, slots=True)
class ConditionalLunarConeServingBounds:
    """Split-TT vector receipt and its conditional finite-cone margin."""

    vectors: ConditionalLunarServingBounds
    cone: ConditionalLunarConeMargin
    split_body_pair_route_required: bool = True
    legacy_fallback_enclosed: bool = False
    ut1_enclosed: bool = False
    source_and_kernel_attested: bool = False
    eclipse_classification_certified: bool = False
    event_search_complete: bool = False


def bound_lunar_cone_penumbral_margin(
    sun_km: tuple[I, I, I], moon_km: tuple[I, I, I], *, earth_radius_scale: float = 1.0,
) -> ConditionalLunarConeMargin:
    """Bound the successful binary64 penumbral margin on vector boxes.

    The input vectors must enclose the represented floats supplied to the
    unchanged ``spherical_cone_shadow`` implementation. The downstream cone
    domain, the positive penumbral nappe, and one umbral branch must be proved
    for all supplied inputs. Every arithmetic operation that could reject or
    overflow in the full cone evaluation is bounded; atan2 is assumed finite
    on finite inputs. This proves only conditional geometry totality, not
    success of an ephemeris, clock or fallback route.
    Hypot is assumed within one binary64 ulp of the exact real norm, sqrt is
    assumed correctly rounded, and fsum is assumed within one ulp. These are
    platform premises, not an attestation. A zero-containing resulting margin
    is not an absence or event witness.
    """
    if (not isinstance(sun_km, tuple) or len(sun_km) != 3
            or not isinstance(moon_km, tuple) or len(moon_km) != 3
            or not all(isinstance(x, I) for x in (*sun_km, *moon_km))):
        raise TypeError("Sun and Moon must be three RationalInterval components")
    if isinstance(earth_radius_scale, bool) or not isinstance(earth_radius_scale, (int, float)):
        raise ValueError("Earth radius scale must be a positive finite float")
    try:
        scale = float(earth_radius_scale)
    except OverflowError as exc:
        raise ValueError("Earth radius scale must be a positive finite float") from exc
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("Earth radius scale must be a positive finite float")

    def mul(a, b):
        return _rounded(a * b)

    def div(a, b):
        if b.contains_zero:
            raise EclipseLunarConeUnavailable("cone denominator may vanish")
        return _rounded(a / b)

    def root(x):
        if x.lo < 0:
            raise EclipseLunarConeUnavailable("cone square-root domain is ambiguous")
        return _rounded(x.sqrt(128))

    try:
        re, rs, rm = map(I.point, (EARTH_RADIUS_KM, SUN_RADIUS_KM, MOON_RADIUS_KM))
        s, d = _hypot_box(sun_km), _hypot_box(moon_km)
        if s.lo <= _rounded(rs + re).hi or d.lo <= _rounded(re + rm).hi:
            raise EclipseLunarConeUnavailable("Sun or Moon input domain requires subdivision")
        axis = tuple(div(-v, s) for v in sun_km)
        z = _fsum(tuple(mul(m, a) for m, a in zip(moon_km, axis)))
        cross = (
            _rounded(mul(moon_km[1], axis[2]) - mul(moon_km[2], axis[1])),
            _rounded(mul(moon_km[2], axis[0]) - mul(moon_km[0], axis[2])),
            _rounded(mul(moon_km[0], axis[1]) - mul(moon_km[1], axis[0])),
        )
        r = _hypot_box(cross)
        # _input checks finiteness of theta=atan2(r,z) and r/re. The former
        # uses the declared atan2 premise; this division refuses overflow.
        div(r, re)
        effective = mul(re, I.point(scale))
        if (effective.lo <= 0 or effective.hi >= rs.lo or
                s.lo <= _rounded(rs + effective).hi or _rounded(z - rm).lo < effective.hi):
            raise EclipseLunarConeUnavailable("downstream cone domain requires subdivision")
        sp = div(_rounded(rs + effective), s)
        su = div(_rounded(rs - effective), s)
        if sp.lo <= 0 or sp.hi >= 1 or su.lo <= 0 or su.hi >= 1:
            raise EclipseLunarConeUnavailable("cone angle is ambiguous")
        cp = root(mul(_rounded(I.point(1) - sp), _rounded(I.point(1) + sp)))
        cu = root(mul(_rounded(I.point(1) - su), _rounded(I.point(1) + su)))
        pen_t = _rounded(z + div(effective, sp))
        nappe_check = _rounded(pen_t + mul(div(sp, cp), r))
        if nappe_check.lo <= 0:
            raise EclipseLunarConeUnavailable("penumbral cone nappe is ambiguous")
        clearance = _rounded(mul(sp, pen_t) - mul(cp, r))
        penumbral = _rounded(clearance + rm)
        umb_t = _rounded(div(effective, su) - z)
        umb_check = _rounded(umb_t + mul(div(su, cu), r))
        if umb_check.lo > 0:
            umbral_clearance = _rounded(mul(su, umb_t) - mul(cu, r))
            branch = "positive"
        elif umb_check.hi <= 0:
            umbral_clearance = -_hypot_box((umb_t, r))
            branch = "apex"
        else:
            raise EclipseLunarConeUnavailable("umbral cone nappe is ambiguous")
        umbral = _rounded(umbral_clearance + rm)
        total = _rounded(umbral_clearance - rm)
        return ConditionalLunarConeMargin(penumbral, z, r, effective, umbral, total, branch)
    except (IntervalBudgetError, IntervalDomainError, OverflowError, ZeroDivisionError) as exc:
        raise EclipseLunarConeUnavailable("cone arithmetic or resource budget unavailable") from exc


def bound_conditional_lunar_cone_serving_margin(
    reader, tt_anchor_jd: float, tt_offset_days: I, *, earth_radius_scale: float = 1.0,
    max_route_calls: int = 32, max_records: int = 256, tight_norm: bool = False,
) -> ConditionalLunarConeServingBounds:
    """Compose the guarded split-TT lunar vectors and finite-cone margin.

    ``tight_norm`` is opt-in and introduces the additional, unattested
    floating square and square-root premises on the nested vector receipt.
    """
    vectors = bound_conditional_lunar_serving_vectors(
        reader, tt_anchor_jd, tt_offset_days, max_route_calls=max_route_calls,
        max_records=max_records, tight_norm=tight_norm,
    )
    cone = bound_lunar_cone_penumbral_margin(
        vectors.sun_retarded_km, vectors.moon_geometric_km, earth_radius_scale=earth_radius_scale,
    )
    return ConditionalLunarConeServingBounds(vectors, cone)
