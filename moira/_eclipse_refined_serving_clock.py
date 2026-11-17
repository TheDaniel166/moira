"""Refined successful-output enclosure for the reduced split LSK clock.

This bounds the represented converter relative to the continuous implicit
NAIF reference. All arithmetic/libm/source premises remain explicit; this
value enclosure does not itself prove convergence or authenticate a build.
The derivation includes each normalization, the represented tau's difference
from mathematical 2*pi, phase operations, the finite iteration, and final
normalization. The two-part decomposition may vary throughout the input box.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import math

from . import julian as source
from ._eclipse_interval import RationalInterval as I
from ._eclipse_inverse_trig import atan_enclosure
from ._eclipse_reference_clock import bound_continuous_reference_tdb
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_time_convergence import (_ulp_upper, ConditionalSplitTimeConvergence,
                                       _modeled_clock_source_unchanged)
from ._eclipse_time_bounds import ServingTdbEnvelope


@dataclass(frozen=True, slots=True)
class RefinedServingClockError:
    """A derived error bound and its distinct arithmetic/source premises."""

    total_error_seconds: F
    periodic_evaluation_error_seconds: F
    normalization_error_seconds: F
    finite_iteration_error_seconds: F
    contraction_ratio: F
    source_and_arithmetic_attested: bool = False
    converter_totality_proved: bool = False


def refined_split_clock_error(anchor: float, offsets: I):
    """Derive the bound using exact inequalities, with no chosen timing slack.

    Each fsum is allowed one extra ulp. At most 2**-40 day encloses the
    normalization schedule already bounded in _eclipse_time_bounds. The
    implicit map has q=|K*M1|*(1+|EB|). A returned correction has at least
    two evaluations; q**2*|K|/(1-q)+E/(1-q) bounds its fixed-point error.
    Sine/remainder accuracy and unit-range, RN/gradual arithmetic and matching
    source are premises. Failed execution is not an enclosed negative event.
    """
    if (isinstance(anchor,bool) or not isinstance(anchor,(int,float))
            or not isinstance(offsets,I) or not math.isfinite(anchor)
            or source._TT_TDB_FIXED_POINT_MAX_ITERATIONS<2):
        raise EnclosureUnavailable('supported source and finite split input required')
    if not _modeled_clock_source_unchanged():
        raise EnclosureUnavailable('modeled split clock source or math callable changed')
    absolute = I.point(anchor)+offsets
    if absolute.lo < -40_000_000 or absolute.hi>40_000_000:
        raise EnclosureUnavailable('clock proof outside source domain')
    k,eb,m0,m1,tau = map(lambda x:abs(F.from_float(x)),(
        source._NAIF_DELTET_K_SECONDS,source._NAIF_DELTET_EB,
        source._NAIF_DELTET_M0_RADIANS,source._NAIF_DELTET_M1_RADIANS_PER_SECOND,math.tau))
    q = k*m1*(1+eb)
    if q>=1:
        raise EnclosureUnavailable('clock contraction not proved')
    seconds = ((absolute-2451545).magnitude+2)*86400
    large_phase = m0+m1*(seconds+_ulp_upper(seconds))
    # Product and two-argument fsum errors for the large fixed term; smaller
    # products, additions and remainders are enclosed separately below.
    phase_error = m1*_ulp_upper(seconds)+4*_ulp_upper(large_phase)
    phase_error += m1*_ulp_upper(F(86400))+4*_ulp_upper(tau+m1*86400)
    real_tau = 8*atan_enclosure(I.point(1),precision_bits=160)
    tau_error = (I.point(math.tau)-real_tau).magnitude
    quotients = large_phase/tau+4
    phase_error += quotients*tau_error
    sine_error = F(1,2**52)
    anomaly_error = (1+eb)*phase_error+eb*sine_error+_ulp_upper(eb)+_ulp_upper(tau+eb)
    normalization = F(86400,2**40)
    evaluation = k*(anomaly_error+sine_error)+_ulp_upper(k)+q*normalization
    finite = q*q*k/(1-q)
    total = normalization+finite+evaluation/(1-q)
    return RefinedServingClockError(total,evaluation,normalization,finite,q)


def bound_refined_serving_split_tdb(anchor: float, offsets: I):
    """Enclose successful split outputs in a tighter exact-reference tube."""
    error = refined_split_clock_error(anchor,offsets)
    # One inclusion step already encloses the exact fixed point. Its small
    # contraction remainder remains inside the returned interval; the serving
    # roundoff tube dominates that remainder. Additional steps are unnecessary
    # for this successful-output enclosure and do not change its model.
    real = bound_continuous_reference_tdb(anchor,offsets,steps=1)
    radius = error.total_error_seconds/86400
    tdb = I(real.tdb_offset_days.lo-radius,real.tdb_offset_days.hi+radius).quantize_outward(128)
    return ServingTdbEnvelope(float(anchor),offsets,tdb)


def prove_reduced_split_clock_convergence(anchor: float, offsets: I, *, first_part_offsets=None):
    """Prove convergence of the compensated, reduced serving iteration.

    The whole-day product's high/low pair is exact in the admitted normal
    range (FMA residual, or the rational fallback). IEEE remainder subtracts
    an exact integral multiple of represented tau. Relative to the exact
    modulo-tau periodic map, each evaluation therefore has only small-angle
    rounding error. The map's possible seam jump is bounded by
    |K|*(1+|EB|)*|tau-2*pi|. Incorporating that jump in the difference
    recurrence also covers day carries and periodic quotient changes.
    The result retains RN/fma/fsum/sine/remainder and unchanged-source
    premises; it is not an authenticated environment or physical-time proof.
    """
    first = I.point(0) if first_part_offsets is None else first_part_offsets
    if not isinstance(first,I) or not isinstance(offsets,I):
        raise TypeError('exact split input intervals required')
    combined = first+offsets
    if ((I.point(anchor)+first).magnitude>40_000_000 or offsets.magnitude>40_000_000):
        raise EnclosureUnavailable('original split input part outside source domain')
    bound = refined_split_clock_error(anchor,combined)
    k,eb,m1 = map(lambda x:abs(F.from_float(x)),(source._NAIF_DELTET_K_SECONDS,
        source._NAIF_DELTET_EB,source._NAIF_DELTET_M1_RADIANS_PER_SECOND))
    tau = F.from_float(math.tau)
    real_tau = 8*atan_enclosure(I.point(1),precision_bits=160)
    seam_jump = k*(1+eb)*(I.point(math.tau)-real_tau).magnitude
    sine_error = F(1,2**52)
    small_phase_error = (16*_ulp_upper(2*tau+abs(F.from_float(source._NAIF_DELTET_M0_RADIANS)))
                         +m1*_ulp_upper(F(86400))+_ulp_upper(m1*86400))
    evaluation = (k*((1+eb)*small_phase_error+eb*sine_error+_ulp_upper(eb)
                        +_ulp_upper(tau+eb)+sine_error)
                  +_ulp_upper(k)+bound.contraction_ratio*bound.normalization_error_seconds)
    difference = bound.contraction_ratio*k+2*evaluation+seam_jump
    threshold = F.from_float(source._TT_TDB_FIXED_POINT_RESIDUAL_SECONDS)
    subtraction = _ulp_upper(2*k)
    maximum = source._TT_TDB_FIXED_POINT_MAX_ITERATIONS
    for count in range(2,maximum+1):
        if difference+subtraction<=threshold:
            return ConditionalSplitTimeConvergence('proved',
                'compensated reduced-phase recurrence, including possible tau seam jump',
                count,evaluation,bound.contraction_ratio,difference+subtraction,
                float(anchor),offsets,first,combined)
        difference = bound.contraction_ratio*difference+2*evaluation+seam_jump
    return ConditionalSplitTimeConvergence('unresolved','reduced-phase residual bound too wide',
        maximum,evaluation,bound.contraction_ratio,difference+subtraction,float(anchor),offsets,first,combined)
