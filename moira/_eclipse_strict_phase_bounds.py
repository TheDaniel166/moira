"""Whole-interval bounds for the opt-in strict mean-ecliptic phase policy.

The domain is a closed interval of represented TT inputs. Successful samples
use one fixed ordered set of immutable SPK record copies. The strict evaluator
checks each native snapshot result against its own interval and rejects any
record, epoch, digest or output mismatch. This policy is separate from the
legacy apparent-phase evaluator and gives no continuity or physical proof.

Proof composition: the one-second TT/TDB box follows from the strict
correctly rounded sine and the guarded NAIF amplitude, regardless of libm;
the body route and its ten possible light-time iterations are covered by the
conditional native boxes and checked snapshot results; exact checked-RN norm
and division obey the vector guard's broad bounds, with its lower bound used
only above 2**-500. Strict aberration follows the same outward operation
schedule and exact sqrt enclosures. Strict FW/Vondrak/P03 polynomials, matrices and
correctly rounded mathematical sine/cosine lie inside the independently
computed pole matrix boxes: the latter's 2**-52 allowance contains strict RN
trig without assuming anything about platform sin/cos. Finally each strict
projection multiply and addition is outward-rounded in the exact source
order; the determinant and dot are exact rational operations.

All intervals cover successful strict evaluations only. Python integer and
Fraction arithmetic, binary64 encoding/checked conversion, unchanged model
constants/source and the per-call native snapshot guards remain premises;
the present module does not verify an already-loaded binary or external
kernel provenance. Unresolved branches, negative/zero-delay layouts, resource
budgets, unresolved branch transitions and |T|>200 centuries fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded
from ._eclipse_phase_aberration import bound_phase_aberration
from ._eclipse_phase_astro import ConditionalPhasePlanetaryBounds, bound_phase_planetary_vectors
from ._eclipse_phase_frame import bound_mean_ecliptic_frame
from ._eclipse_phase_pole import ConditionalMeanEclipticPole
from ._eclipse_strict_phase import StrictMeanPhaseSample, evaluate_strict_mean_phase


class EclipseStrictDomainUnavailable(EnclosureUnavailable):
    """The strict phase schedule cannot be enclosed for the requested box."""


@dataclass(frozen=True, slots=True)
class ConditionalStrictMeanDomain:
    """Whole-interval strict phase enclosure under explicitly retained premises."""

    tt_anchor_jd: float
    tt_offset_days: I
    vector_bounds: ConditionalPhasePlanetaryBounds
    frame_bounds: ConditionalMeanEclipticPole
    sun_xy: tuple[I, I]
    moon_xy: tuple[I, I]
    cross_km2: I
    dot_km2: I
    new_direction_sign: int | None
    full_direction_sign: int | None
    checked_rn_and_snapshot_guards_required: bool = True
    unchanged_strict_source_and_constants_required: bool = True
    platform_sin_cos_or_atan2_required: bool = False
    source_and_loaded_native_image_attested: bool = False
    legacy_phase_evaluator_attested: bool = False
    successful_outputs_only: bool = True
    ut1_enclosed: bool = False
    continuous_root_proved: bool = False
    complete_search_certified: bool = False
    physical_accuracy_certified: bool = False


def bound_strict_mean_phase_interval(reader, tt_anchor_jd: float, tt_offset_days: I) -> ConditionalStrictMeanDomain:
    """Bound strict phase dot, determinant and any provable branch sign."""
    vectors = bound_phase_planetary_vectors(reader, tt_anchor_jd, tt_offset_days)
    if len(vectors.spk_usages) != 34:
        raise EclipseStrictDomainUnavailable("strict phase needs one proven positive-delay route per iteration")
    frame = bound_mean_ecliptic_frame(tt_anchor_jd, tt_offset_days)
    sun = bound_phase_aberration(vectors.sun_retarded_km, vectors.earth_velocity_km_per_day).position_km
    moon = bound_phase_aberration(vectors.moon_retarded_km, vectors.earth_velocity_km_per_day).position_km

    def project(vector):
        result = []
        for row in frame.mean_matrix[:2]:
            terms = tuple(_rounded(a * b) for a, b in zip(row, vector))
            result.append(_rounded(_rounded(terms[0] + terms[1]) + terms[2]))
        return tuple(result)

    s, m = project(sun), project(moon)
    cross = (s[0] * m[1] - s[1] * m[0]).quantize_outward(128)
    dot = (s[0] * m[0] + s[1] * m[1]).quantize_outward(128)
    cross_sign = 1 if cross.lo > 0 else -1 if cross.hi < 0 else None
    dot_sign = 1 if dot.lo > 0 else -1 if dot.hi < 0 else None
    new_sign = cross_sign if dot_sign == 1 else None
    full_sign = -cross_sign if dot_sign == -1 and cross_sign is not None else None
    return ConditionalStrictMeanDomain(
        float(tt_anchor_jd), tt_offset_days, vectors, frame, s, m, cross, dot, new_sign, full_sign,
    )


def evaluate_bounded_strict_mean_phase(bounds: ConditionalStrictMeanDomain, tt_jd: float) -> StrictMeanPhaseSample:
    """Evaluate and independently check one sample against its domain boxes."""
    if not isinstance(bounds, ConditionalStrictMeanDomain):
        raise TypeError("conditional strict mean-phase domain required")
    sample = evaluate_strict_mean_phase(bounds.vector_bounds, tt_jd)
    if (not all(box.contains(value) for box, value in zip(bounds.sun_xy, sample.sun_ecliptic_xy))
            or not all(box.contains(value) for box, value in zip(bounds.moon_xy, sample.moon_ecliptic_xy))
            or not bounds.cross_km2.contains(sample.cross_km2)
            or not bounds.dot_km2.contains(sample.dot_km2)):
        raise ArithmeticError("strict sample escaped its strict-schedule interval")
    return sample
