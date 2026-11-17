"""Conditional serving sidereal-time bounds from a supplied nutation box.

This private composition bounds Moira's Python and native GMST/GAST schedules
only under explicit floating-point and libm premises. One entry point requires
the caller to enclose represented nutation-in-longitude values; a second derives
an amplitude enclosure from loaded nutation coefficients under explicit table
and cache premises. Neither attests its source, UT1/TT conversion, polar motion,
an Earth-fixed shadow or an eclipse.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded
from ._eclipse_nutation_amplitudes import (
    ConditionalNutationAmplitudeBounds,
    bound_conditional_nutation_amplitudes,
)
from ._eclipse_wgs84_orientation import bound_conditional_earth_rotation_angle
from ._eclipse_polar_motion_bounds import _trig_rounded


class EclipseSiderealBoundsUnavailable(EnclosureUnavailable):
    """The conditional sidereal enclosure cannot cover the requested box."""


@dataclass(frozen=True, slots=True)
class ConditionalSiderealBounds:
    """Serving sidereal angles conditional on supplied represented dpsi values."""

    ut1_anchor_jd: float
    ut1_offset_days: I
    tt_anchor_jd: float
    tt_offset_days: I
    nutation_longitude_degrees: I
    era_degrees: I
    gmst_degrees: I
    gast_degrees: I
    caller_supplied_nutation_enclosure_required: bool = True
    rounded_integer_powers_required: bool = True
    finite_unit_trig_required: bool = True
    source_and_arithmetic_attested: bool = False
    nutation_enclosure_attested: bool = False
    earth_fixed_orientation_certified: bool = False
    physical_accuracy_certified: bool = False


@dataclass(frozen=True, slots=True)
class ConditionalModelSiderealBounds:
    """Sidereal bounds with dpsi derived from loaded nutation amplitudes."""

    nutation: ConditionalNutationAmplitudeBounds
    sidereal: ConditionalSiderealBounds
    registered_nutation_tables_match_required: bool = True
    source_and_arithmetic_attested: bool = False
    earth_fixed_orientation_certified: bool = False
    physical_accuracy_certified: bool = False


def _hull(*values: I) -> I:
    return I(min(value.lo for value in values), max(value.hi for value in values))


def _sum_product(accumulator: I, product: I) -> I:
    """Include separate multiply-add and one fused multiply-add."""
    return _hull(_rounded(accumulator + _rounded(product)), _rounded(accumulator + product))


def _mod_360(value: I) -> I:
    """Enclose Python modulo and native mod_floor when quotient is unique."""
    quotient = _hull(value / 360, _rounded(value / 360))
    first, last = quotient.lo // 1, quotient.hi // 1
    if first != last or abs(first) >= 2**40:
        raise EclipseSiderealBoundsUnavailable("sidereal modulo branch requires subdivision")
    # 360*first is an exact binary64 integer in the admitted quotient range.
    return _rounded(value - I.point(first * 360))


def _gmst_polynomial(T: I) -> I:
    """Enclose the two source polynomial schedules, including native FMA."""
    coefficients = (0.014506, 4612.156534, 1.3915817,
                    -0.00000044, -0.000029956, -0.0000000368)
    # Python evaluates T**n separately; correctly rounded binary64 integer
    # powers are an explicit, unattested premise of this bound.
    python = I.point(coefficients[0])
    for exponent, coefficient in enumerate(coefficients[1:], 1):
        power = T if exponent == 1 else _rounded(T ** exponent)
        python = _rounded(python + _rounded(I.point(coefficient) * power))

    # Native uses coefficient*T*T...; each multiply may round or contract
    # with the immediately following sum, but no unsafe reassociation.
    native = I.point(coefficients[0])
    for exponent, coefficient in enumerate(coefficients[1:], 1):
        partial = I.point(coefficient)
        for _ in range(exponent - 1):
            partial = _rounded(partial * T)
        native = _sum_product(native, partial * T)
    return _hull(python, native)


def _complementary_terms(T: I) -> I:
    """Bound all source complementary terms using finite sine in [-1, 1]."""
    trig = I(-1, 1)
    coefficients = (0.00264096, 0.00006352, 0.00001175, 0.00001121,
                    -0.00000455, 0.00000202, 0.00000198, -0.00000172)
    total = _rounded(I.point(coefficients[0]) * trig)
    for coefficient in coefficients[1:]:
        total = _sum_product(total, I.point(coefficient) * trig)
    last_prefix = _rounded(I.point(-0.00000087) * T)
    total = _sum_product(total, last_prefix * trig)
    return _rounded(total / 3600)


def _mean_obliquity_cosine(T: I) -> I:
    """Enclose both serving polynomial schedules and the one-ulp cosine."""
    coefficients = (84381.406,-46.836769,-0.0001831,
                    0.00200340,-0.000000576,-0.0000000434)
    native,python = I.point(coefficients[0]),I.point(coefficients[0])
    for exponent,coefficient in enumerate(coefficients[1:],1):
        partial = I.point(coefficient)
        for _ in range(exponent-1):
            partial = _rounded(partial*T)
        native = _sum_product(native,partial*T)
        python = _rounded(python+_rounded(I.point(coefficient)*_rounded(T**exponent)))
    degrees = _rounded(_hull(native,python)/3600)
    return _trig_rounded(_rounded(degrees*I.point(math.pi/180)))[1]


def _periodic_argument(value: I) -> I:
    """Include Python remainder and native floored subtraction/FMA."""
    tau = I.point(math.tau)
    quotient = _hull(value/tau,_rounded(value/tau))
    first,last = quotient.lo//1,quotient.hi//1
    if first!=last or abs(first)>=2**40:
        return I(-math.tau,2*math.tau)
    product = I.point(first)*tau
    return _hull(_rounded(value-_rounded(product)),_rounded(value-product))


def _tight_complementary_terms(T: I) -> I:
    """Bound the actual IERS-term arguments, including both source orders."""
    arcsec = I.point(math.pi/648000)
    om = _sum_product(I.point(7.4722),T*I.point(0.007702))
    om = _sum_product(I.point(-6962890.5431),T*om)
    om = _periodic_argument(_rounded(_sum_product(I.point(450160.398036),T*om)*arcsec))
    f = _periodic_argument(_rounded(_sum_product(I.point(335779.526232),T*I.point(1739527262.8478))*arcsec))
    d = _periodic_argument(_rounded(_sum_product(I.point(1072260.703692),T*I.point(1602961601.2090))*arcsec))
    base = _rounded(_rounded(2*f)-_rounded(2*d))
    args = (om,_rounded(2*om),_sum_product(base,3*om),
            _rounded(base+om),_sum_product(base,2*om),
            _sum_product(_rounded(2*f),3*om),_rounded(_rounded(2*f)+om),_rounded(3*om))
    coefficients = (0.00264096,0.00006352,0.00001175,0.00001121,
                    -0.00000455,0.00000202,0.00000198,-0.00000172)
    sine = tuple(_trig_rounded(argument)[0] for argument in args)
    total = _rounded(I.point(coefficients[0])*sine[0])
    for coefficient,trig in zip(coefficients[1:],sine[1:]):
        total = _sum_product(total,I.point(coefficient)*trig)
    prefix = _rounded(I.point(-0.00000087)*T)
    return _rounded(_sum_product(total,prefix*sine[0])/3600)


def bound_conditional_sidereal_time(
    ut1_anchor_jd: float, ut1_offset_days: I,
    tt_anchor_jd: float, tt_offset_days: I,
    nutation_longitude_degrees: I, *, assume_ieee_arithmetic: bool = False,
    assume_correctly_rounded_integer_powers: bool = False,
    assume_finite_unit_trig: bool = False,
    tight_equation_of_equinoxes: bool = False,
) -> ConditionalSiderealBounds:
    """Enclose successful serving GAST values with a supplied dpsi enclosure.

    The caller must bound all represented dpsi values from the exact nutation
    route it uses. Every sin/cos call must return a finite value in [-1,1],
    Python float integer powers must be correctly rounded, and IEEE binary64
    nearest/gradual arithmetic and native no-unsafe-reassociation must hold.
    ERA's fmod premise is inherited. These claims are not runtime attestation.
    TT and UT1 are separate represented inputs; neither conversion nor their
    physical correspondence is proved. Modulo/day seams fail closed.
    """
    if type(tight_equation_of_equinoxes) is not bool:
        raise TypeError('tight equation-of-equinoxes option must be bool')
    flags = (assume_ieee_arithmetic, assume_correctly_rounded_integer_powers, assume_finite_unit_trig)
    if not all(type(flag) is bool for flag in flags):
        raise TypeError("sidereal arithmetic premises must be booleans")
    if not all(flags):
        raise EclipseSiderealBoundsUnavailable("sidereal arithmetic premises are required")
    if (isinstance(tt_anchor_jd, bool) or not isinstance(tt_anchor_jd, (float, int))
            or not isinstance(tt_offset_days, I) or not isinstance(nutation_longitude_degrees, I)):
        raise TypeError("finite TT anchor and rational TT/dpsi intervals are required")
    try:
        tt_anchor = float(tt_anchor_jd)
        if not math.isfinite(tt_anchor):
            raise ValueError("TT anchor must be finite")
        tt = I.point(tt_anchor) + tt_offset_days
        if tt.lo < -40_000_000 or tt.hi > 40_000_000:
            raise EclipseSiderealBoundsUnavailable("TT outside supported sidereal proof domain")
        era = bound_conditional_earth_rotation_angle(
            ut1_anchor_jd, ut1_offset_days, assume_ieee_arithmetic=True,
        )
        T = _rounded(_rounded(tt - 2451545) / 36525)
        polynomial = _gmst_polynomial(T)
        gmst = _mod_360(_rounded(era.angle_degrees + _rounded(polynomial / 3600)))
        complement = _tight_complementary_terms(T) if tight_equation_of_equinoxes else _complementary_terms(T)
        cosine = _mean_obliquity_cosine(T) if tight_equation_of_equinoxes else I(-1,1)
        product = nutation_longitude_degrees * cosine
        equation = _sum_product(complement, product)
        gast = _mod_360(_rounded(gmst + equation))
        return ConditionalSiderealBounds(float(ut1_anchor_jd), ut1_offset_days, tt_anchor,
                                         tt_offset_days, nutation_longitude_degrees,
                                         era.angle_degrees, gmst, gast)
    except (IntervalBudgetError, IntervalDomainError, OverflowError, ZeroDivisionError) as exc:
        raise EclipseSiderealBoundsUnavailable("sidereal enclosure unavailable") from exc


def bound_conditional_sidereal_from_nutation_tables(
    ut1_anchor_jd: float, ut1_offset_days: I,
    tt_anchor_jd: float, tt_offset_days: I, *,
    assume_ieee_arithmetic: bool = False,
    assume_correctly_rounded_integer_powers: bool = False,
    assume_finite_unit_trig: bool = False,
    assume_registered_tables_and_caches_match: bool = False,
) -> ConditionalModelSiderealBounds:
    """Compose serving GAST with actual loaded nutation coefficient bounds.

    The registration/cache, source, native-build and arithmetic premises are
    inherited from both component bounds and are not attested. This proves
    neither UT1/TT correspondence, ITRF orientation, nor physical accuracy.
    """
    nutation = bound_conditional_nutation_amplitudes(
        tt_anchor_jd, tt_offset_days,
        assume_ieee_arithmetic=assume_ieee_arithmetic,
        assume_finite_unit_trig=assume_finite_unit_trig,
        assume_registered_tables_and_caches_match=assume_registered_tables_and_caches_match,
    )
    sidereal = bound_conditional_sidereal_time(
        ut1_anchor_jd, ut1_offset_days, tt_anchor_jd, tt_offset_days,
        nutation.longitude_degrees,
        assume_ieee_arithmetic=assume_ieee_arithmetic,
        assume_correctly_rounded_integer_powers=assume_correctly_rounded_integer_powers,
        assume_finite_unit_trig=assume_finite_unit_trig,
    )
    return ConditionalModelSiderealBounds(nutation, sidereal)
