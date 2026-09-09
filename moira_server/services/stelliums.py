"""Thin conversion of supplied snapshots; never performs chart calculation."""

from __future__ import annotations

import math

from moira.houses import (
    HouseBoundaryCurvePoint,
    HouseBoundaryGeometry,
    HouseBoundaryGeometryAvailability,
    HouseBoundaryGeometryKind,
    HouseBoundaryGeometrySet,
    HouseCusps,
    HousePolicy,
    classify_house_system,
)
from moira.stelliums import (
    StelliumAnalysis,
    StelliumAnalysisPolicy,
    StelliumContext,
    StelliumHouseContext,
    StelliumSelection,
    analyze_stelliums,
)
from ..models.stelliums import StelliumAnalysisRequest, StelliumHouseSnapshot


def _house_context(snapshot: StelliumHouseSnapshot) -> StelliumHouseContext:
    classification = classify_house_system(snapshot.effective_system)
    for field, expected in (
        ("classification_family", classification.family.value),
        ("classification_cusp_basis", classification.cusp_basis.value),
        ("classification_latitude_sensitive", classification.latitude_sensitive),
        ("classification_polar_capable", classification.polar_capable),
    ):
        received = getattr(snapshot, field)
        if received is not None and received != expected:
            raise ValueError(f"house {field} disagrees with effective system")
    geometry = None
    if snapshot.boundary_geometry is not None:
        raw = snapshot.boundary_geometry
        geometry = HouseBoundaryGeometrySet(
            **raw.model_dump(exclude={"availability", "boundaries"}),
            availability=HouseBoundaryGeometryAvailability(raw.availability),
            boundaries=tuple(
                HouseBoundaryGeometry(
                    **b.model_dump(exclude={"kind", "curve_points"}),
                    kind=HouseBoundaryGeometryKind(b.kind),
                    curve_points=tuple(
                        HouseBoundaryCurvePoint(**p.model_dump())
                        for p in b.curve_points
                    ),
                )
                for b in raw.boundaries
            ),
        )
    houses = HouseCusps(
        system=snapshot.system,
        effective_system=snapshot.effective_system,
        fallback=snapshot.fallback,
        fallback_reason=snapshot.fallback_reason,
        classification=classification,
        policy=HousePolicy(**snapshot.policy.model_dump()),
        cusps=tuple(snapshot.cusps),
        asc=snapshot.asc,
        mc=snapshot.mc,
        armc=snapshot.armc,
        east_point=snapshot.east_point,
        vertex=snapshot.vertex,
        anti_vertex=snapshot.anti_vertex,
        boundary_geometry=geometry,
    )
    # Derived opposite angles are evidence, not independently configurable inputs.
    for name in ("dsc", "ic"):
        residual = (getattr(houses, name) - getattr(snapshot, name) + 180) % 360 - 180
        if not math.isclose(residual, 0, rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"house {name} disagrees with its source angle")
    return StelliumHouseContext(houses, snapshot.longitude_frame)


def compute_stellium_analysis(request: StelliumAnalysisRequest) -> StelliumAnalysis:
    """Admit house evidence and delegate all detection to the engine owner."""
    return analyze_stelliums(
        request.positions,
        policy=StelliumAnalysisPolicy(
            request.policy.preset,
            request.policy.max_span_degrees,
            tuple(request.policy.criteria),
        ),
        selection=StelliumSelection(
            tuple(request.selection.core), tuple(request.selection.associated)
        ),
        context=StelliumContext(**request.context.model_dump()),
        houses=_house_context(request.houses) if request.houses is not None else None,
        house_unavailable_reason=request.house_unavailable_reason,
    )


__all__ = ["compute_stellium_analysis"]
