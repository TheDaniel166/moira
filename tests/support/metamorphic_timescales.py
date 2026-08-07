"""Reviewed observations and predicates for hybrid UT1/TT relations."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real

from moira.julian import DeltaTPolicy, tt_to_ut, ut_to_tt
from support.metamorphic import require_relation


HYBRID_TIMESCALE_RELATION_ID = "MOIRA-TIMESCALE-HYBRID-UT1-TT-INVERSE-V1"
BASELINE_MUTANT_ID = "unmutated-production-observation"
REVIEWED_MIN_JD_UT1 = 1_355_817.5
REVIEWED_MAX_JD_UT1 = 3_547_272.5


@dataclass(frozen=True, slots=True)
class HybridInverseObservation:
    """One omitted-policy and named-hybrid clock-graph observation."""

    jd_ut1: float
    default_jd_tt: float
    named_jd_tt: float
    default_recovered_jd_ut1: float
    named_recovered_jd_ut1: float
    coordinate_ulp_days: float

    @property
    def maximum_round_trip_residual_ulps(self) -> float:
        residual_days = max(
            abs(self.default_recovered_jd_ut1 - self.jd_ut1),
            abs(self.named_recovered_jd_ut1 - self.jd_ut1),
        )
        return residual_days / self.coordinate_ulp_days


def _finite_real(value: object, *, role: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{role} must be a non-boolean real number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{role} must be finite")
    return converted


def _reviewed_jd_ut1(value: object) -> float:
    jd_ut1 = _finite_real(value, role="JD UT1")
    if not REVIEWED_MIN_JD_UT1 <= jd_ut1 <= REVIEWED_MAX_JD_UT1:
        raise ValueError(
            "JD UT1 lies outside the reviewed proleptic-year "
            "[-1000, 5000] relation domain"
        )
    return jd_ut1


def observe_hybrid_inverse(
    jd_ut1: float,
    *,
    recovered_ut1_bias_seconds: float = 0.0,
) -> HybridInverseObservation:
    """Observe ``u -> u + DeltaT(u) -> u`` under both default spellings.

    The optional bias is applied to both recovered coordinates only after the
    production calls return. It exists solely for a predicate-sensitivity
    canary and cannot change Moira's time-scale policy or source selection.
    """

    reviewed_jd_ut1 = _reviewed_jd_ut1(jd_ut1)
    bias_seconds = _finite_real(
        recovered_ut1_bias_seconds,
        role="recovered UT1 bias seconds",
    )
    named_hybrid = DeltaTPolicy(model="hybrid")

    default_jd_tt = ut_to_tt(reviewed_jd_ut1)
    named_jd_tt = ut_to_tt(
        reviewed_jd_ut1,
        delta_t_policy=named_hybrid,
    )
    default_recovered = tt_to_ut(default_jd_tt)
    named_recovered = tt_to_ut(
        named_jd_tt,
        delta_t_policy=named_hybrid,
    )
    bias_days = bias_seconds / 86_400.0
    default_recovered += bias_days
    named_recovered += bias_days
    coordinate_ulp_days = max(
        math.ulp(reviewed_jd_ut1),
        math.ulp(default_jd_tt),
        math.ulp(named_jd_tt),
        math.ulp(default_recovered),
        math.ulp(named_recovered),
    )
    return HybridInverseObservation(
        jd_ut1=reviewed_jd_ut1,
        default_jd_tt=default_jd_tt,
        named_jd_tt=named_jd_tt,
        default_recovered_jd_ut1=default_recovered,
        named_recovered_jd_ut1=named_recovered,
        coordinate_ulp_days=coordinate_ulp_days,
    )


def assert_hybrid_inverse(
    observation: HybridInverseObservation,
    *,
    limit_ulps: float,
    mutant_id: str = BASELINE_MUTANT_ID,
) -> None:
    """Apply the same exact/default and ULP predicates to base and canary."""

    limit = _finite_real(limit_ulps, role="hybrid inverse ULP limit")
    if limit < 0.0:
        raise ValueError("hybrid inverse ULP limit must be nonnegative")
    require_relation(
        observation.default_jd_tt == observation.named_jd_tt,
        relation_id=HYBRID_TIMESCALE_RELATION_ID,
        mutant_id=mutant_id,
        metric="default versus named hybrid TT mismatch indicator",
        observed=(
            0.0
            if observation.default_jd_tt == observation.named_jd_tt
            else 1.0
        ),
        limit=0.0,
    )
    require_relation(
        (
            observation.default_recovered_jd_ut1
            == observation.named_recovered_jd_ut1
        ),
        relation_id=HYBRID_TIMESCALE_RELATION_ID,
        mutant_id=mutant_id,
        metric="default versus named hybrid recovered UT1 mismatch indicator",
        observed=(
            0.0
            if (
                observation.default_recovered_jd_ut1
                == observation.named_recovered_jd_ut1
            )
            else 1.0
        ),
        limit=0.0,
    )
    require_relation(
        observation.maximum_round_trip_residual_ulps <= limit,
        relation_id=HYBRID_TIMESCALE_RELATION_ID,
        mutant_id=mutant_id,
        metric="maximum hybrid UT1 round-trip residual",
        observed=observation.maximum_round_trip_residual_ulps,
        limit=limit,
    )


__all__ = [
    "BASELINE_MUTANT_ID",
    "HYBRID_TIMESCALE_RELATION_ID",
    "HybridInverseObservation",
    "REVIEWED_MAX_JD_UT1",
    "REVIEWED_MIN_JD_UT1",
    "assert_hybrid_inverse",
    "observe_hybrid_inverse",
]
