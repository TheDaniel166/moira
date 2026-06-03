"""
Experimental high-latitude solver for Campanus houses.

This module is intentionally separate from moira.houses (following the established
pattern from experimental_placidus.py) so that research-grade or experimental
high-latitude prime-vertical / local-horizon resolution logic for Campanus
can be developed and opted into explicitly via PolarFallbackPolicy.EXPERIMENTAL_SEARCH
without altering the main house doctrine or computation paths for normal latitudes.

The main houses engine will delegate to this only under explicit experimental
policy for this system when |lat| >= critical and the system is still guarded.

See HOUSES_SOVEREIGNTY_REMEDIATION_ROADMAP.md for the required geometric
object-first remediation for Campanus (local-horizon sector objects, branch
doctrine, visible-MC handling).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ._house_quality import strictly_ordered_cusp_cycle


__all__ = [
    "ExperimentalCampanusStatus",
    "ExperimentalCampanusResult",
    "ExperimentalCampanusWindow",
    "ExperimentalCampanusAdmissibilityMap",
    "search_experimental_campanus",
    "scan_experimental_campanus_admissibility",
]


class ExperimentalCampanusStatus(str, Enum):
    """Structured outcome for a high-latitude Campanus experimental computation."""

    UNIQUE_ORDERED_SOLUTION = "unique_ordered_solution"
    HORIZON_BRANCH_SELECTION_FAILED = "horizon_branch_selection_failed"
    ASSEMBLY_FAILED = "assembly_failed"
    UNORDERED_CUSP_CYCLE = "unordered_cusp_cycle"


@dataclass(frozen=True, slots=True)
class ExperimentalCampanusResult:
    """Result of an explicit high-latitude Campanus experimental computation."""

    armc: float
    obliquity: float
    latitude: float
    asc: float
    mc: float
    status: ExperimentalCampanusStatus
    cusps: tuple[float, ...] | None = None
    diagnostic_summary: str = ""

    @property
    def has_solution(self) -> bool:
        return self.cusps is not None


@dataclass(frozen=True, slots=True)
class ExperimentalCampanusWindow:
    """Contiguous ARMC interval where one unique ordered Campanus solution exists."""

    start_armc: float
    end_armc: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class ExperimentalCampanusAdmissibilityMap:
    """Scanned admissibility windows for the explicit Campanus search mode."""

    latitude: float
    obliquity: float
    armc_start: float
    armc_end: float
    armc_step: float
    valid_armcs: tuple[float, ...]
    windows: tuple[ExperimentalCampanusWindow, ...]
    total_samples: int

    @property
    def valid_fraction(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return len(self.valid_armcs) / self.total_samples

    @property
    def has_any_window(self) -> bool:
        return bool(self.windows)


def search_experimental_campanus(
    armc: float,
    obliquity: float,
    latitude: float,
    asc: float,
    mc: float,
    *,
    ordering_tolerance: float = 1e-7,
    **kwargs,
) -> ExperimentalCampanusResult:
    """
    Experimental high-latitude Campanus cusp computation.

    Campanus is governed by local-horizon prime-vertical sectors. This
    experimental surface makes that doctrine explicit: build the local east and
    zenith basis, construct the sector planes for the Campanus quadrant
    primaries, select their ecliptic intersections by horizon hemisphere, then
    assemble the quadrant family against the visible MC rather than performing
    retroactive flips.
    """
    from .houses import (
        _assemble_antipodal_quadrant_cusps,
        _ecliptic_intersection_candidates,
        _local_horizon_basis,
        _mc_above_horizon,
        _normalize3,
        _select_horizon_branch,
    )

    mc_visible = _mc_above_horizon(mc, obliquity, latitude)
    ic_visible = (mc_visible + 180.0) % 360.0
    east, _north, zenith = _local_horizon_basis(armc, latitude)

    def _campanus_cusp(
        alpha_deg: float,
        *,
        prefer_above_horizon: bool,
        tie_arc_start: float,
        tie_arc_end: float,
    ) -> float:
        alpha = math.radians(alpha_deg)
        plane_normal = _normalize3((
            math.cos(alpha) * east[0] + math.sin(alpha) * zenith[0],
            math.cos(alpha) * east[1] + math.sin(alpha) * zenith[1],
            math.cos(alpha) * east[2] + math.sin(alpha) * zenith[2],
        ))
        primary, secondary = _ecliptic_intersection_candidates(plane_normal, obliquity)
        return _select_horizon_branch(
            primary,
            secondary,
            zenith=zenith,
            prefer_above_horizon=prefer_above_horizon,
            obliquity_deg=obliquity,
            tie_arc_start=tie_arc_start,
            tie_arc_end=tie_arc_end,
        )

    try:
        h2 = _campanus_cusp(60.0, prefer_above_horizon=False, tie_arc_start=asc, tie_arc_end=ic_visible)
        h3 = _campanus_cusp(30.0, prefer_above_horizon=False, tie_arc_start=asc, tie_arc_end=ic_visible)
        h11 = _campanus_cusp(150.0, prefer_above_horizon=True, tie_arc_start=mc_visible, tie_arc_end=asc)
        h12 = _campanus_cusp(120.0, prefer_above_horizon=True, tie_arc_start=mc_visible, tie_arc_end=asc)
    except Exception as exc:
        return ExperimentalCampanusResult(
            armc=armc,
            obliquity=obliquity,
            latitude=latitude,
            asc=asc,
            mc=mc,
            status=ExperimentalCampanusStatus.HORIZON_BRANCH_SELECTION_FAILED,
            cusps=None,
            diagnostic_summary=f"horizon branch selection failed: {exc}",
        )

    try:
        cusp_list = _assemble_antipodal_quadrant_cusps(
            asc=asc,
            mc=mc_visible,
            h2=h2,
            h3=h3,
            h11=h11,
            h12=h12,
            context="experimental_campanus",
        )
    except Exception as exc:
        return ExperimentalCampanusResult(
            armc=armc,
            obliquity=obliquity,
            latitude=latitude,
            asc=asc,
            mc=mc,
            status=ExperimentalCampanusStatus.ASSEMBLY_FAILED,
            cusps=None,
            diagnostic_summary=f"assembly failed: {exc}",
        )

    cusps = tuple(cusp_list)
    is_ordered = strictly_ordered_cusp_cycle(
        cusps,
        ordering_tolerance=ordering_tolerance,
    )

    if is_ordered:
        status = ExperimentalCampanusStatus.UNIQUE_ORDERED_SOLUTION
        diag = "local-horizon prime-vertical construction yielded ordered Campanus cusps"
    else:
        status = ExperimentalCampanusStatus.UNORDERED_CUSP_CYCLE
        cusps = None
        diag = "assembled cusps not strictly ordered"

    return ExperimentalCampanusResult(
        armc=armc,
        obliquity=obliquity,
        latitude=latitude,
        asc=asc,
        mc=mc,
        status=status,
        cusps=cusps,
        diagnostic_summary=diag,
    )


def scan_experimental_campanus_admissibility(
    latitude: float,
    obliquity: float,
    *,
    armc_start: float = 0.0,
    armc_end: float = 360.0,
    armc_step: float = 0.5,
    ordering_tolerance: float = 1e-7,
) -> ExperimentalCampanusAdmissibilityMap:
    """Scan ARMC space for unique ordered experimental Campanus solutions."""
    from .houses import _asc_from_armc, _mc_from_armc

    if armc_step <= 0.0:
        raise ValueError("armc_step must be > 0")
    if armc_end < armc_start:
        raise ValueError("armc_end must be >= armc_start")

    valid_armcs: list[float] = []
    armc = armc_start
    while armc <= armc_end + 1e-12:
        asc = _asc_from_armc(armc, obliquity, latitude)
        mc = _mc_from_armc(armc, obliquity, latitude)
        result = search_experimental_campanus(
            armc,
            obliquity,
            latitude,
            asc,
            mc,
            ordering_tolerance=ordering_tolerance,
        )
        if result.status == ExperimentalCampanusStatus.UNIQUE_ORDERED_SOLUTION:
            valid_armcs.append(round(armc, 10))
        armc += armc_step

    windows: list[ExperimentalCampanusWindow] = []
    if valid_armcs:
        start = prev = valid_armcs[0]
        for armc_value in valid_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                windows.append(
                    ExperimentalCampanusWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        windows.append(
            ExperimentalCampanusWindow(
                start_armc=start,
                end_armc=prev,
                sample_count=int(round((prev - start) / armc_step)) + 1,
            )
        )

    total_samples = int(round((armc_end - armc_start) / armc_step)) + 1
    return ExperimentalCampanusAdmissibilityMap(
        latitude=latitude,
        obliquity=obliquity,
        armc_start=armc_start,
        armc_end=armc_end,
        armc_step=armc_step,
        valid_armcs=tuple(valid_armcs),
        windows=tuple(windows),
        total_samples=total_samples,
    )
