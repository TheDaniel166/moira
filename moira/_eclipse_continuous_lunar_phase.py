"""Fixed-pole phase roots of a copied-coefficient continuous lunar model.

The root partition concerns the explicit ideal reference function, not the
legacy phase evaluator or a physical eclipse. All source and model assumptions
of the continuous lunar reference remain in force.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ._eclipse_continuous_lunar import enclose_continuous_lunar_reference
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable, RootPartition
from ._eclipse_reference_phase import ReferencePhaseVectors, VectorBox, isolate_reference_phase_roots


@dataclass(frozen=True)
class ContinuousLunarPhasePartition:
    """Root offsets in days from the retained TT anchor, for one reference."""

    phase: Literal["new", "full"]
    pole: VectorBox
    tt_anchor_jd: float
    roots: RootPartition
    ideal_reference_model_only: bool = True
    source_and_kernel_attested: bool = False
    legacy_phase_evaluator_attested: bool = False
    physical_accuracy_certified: bool = False


def isolate_continuous_lunar_phase(
    model,
    tt_offsets: I,
    *,
    pole: VectorBox,
    phase: Literal["new", "full"],
    tolerance: int | float | I,
    max_evaluations: int = 10000,
    max_depth: int = 80,
) -> ContinuousLunarPhasePartition:
    """Isolate roots within one admitted fixed-snapshot reference domain.

    The requested pole is one caller-specified exact vector. It defines a
    fixed projection plane and is not attested to any dynamic ecliptic frame.
    The route must prove its local continuous differentiable model and retain
    the same copied source snapshots for all subintervals. Unknown seams,
    branch signs and exhausted budgets remain unresolved.
    """
    def provider(box: I) -> ReferencePhaseVectors:
        value = enclose_continuous_lunar_reference(model, box)
        if not value.continuous_on_domain or not value.differentiable_on_domain:
            raise EnclosureUnavailable("continuous lunar reference proof unavailable")
        return ReferencePhaseVectors(
            value.sun_geocentric_km,
            value.moon_geocentric_km,
            value.sun_derivative_km_per_tt_day,
            value.moon_derivative_km_per_tt_day,
        )

    roots = isolate_reference_phase_roots(
        tt_offsets, provider, pole=pole, phase=phase, tolerance=tolerance,
        continuity_assumed=True, derivative_enclosed=True, max_evaluations=max_evaluations,
        max_depth=max_depth, time_scale="TT", unit="day offset from TT anchor",
    )
    return ContinuousLunarPhasePartition(phase, pole, model.tt_anchor_jd, roots)
