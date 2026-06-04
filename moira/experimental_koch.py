"""
Experimental high-latitude solver for Koch houses.

This module is intentionally separate from moira.houses (following the established
pattern from experimental_placidus.py) so that research-grade or experimental
high-latitude branch/pole/ascensional resolution logic for Koch can be developed
and opted into explicitly via PolarFallbackPolicy.EXPERIMENTAL_SEARCH without
altering the main house doctrine or computation paths for normal latitudes.

The main houses engine will delegate to this only under explicit experimental
policy for this system when |lat| >= critical and the system is still guarded.

See HOUSES_SOVEREIGNTY_REMEDIATION_ROADMAP.md for the required geometric
object-first remediation for Koch (equatorial-sector or safe pole projection
to avoid tan(pole) and division issues at high latitude).

Initial real logic implemented: safe (cos(pole)-cleared) plane normal for the
RA+pole construction + reuse of canonical specs/selection/assembly + ordered
check. This allows EXPERIMENTAL_SEARCH for Koch to produce valid cusps at
polar latitudes for at least some ARMC without the main-path overflows.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ._house_quality import (
    HouseCycleVerdict,
    HouseDistortionProfile,
    house_cycle_verdict,
    stable_true_flags,
    strictly_ordered_cusp_cycle,
)


__all__ = [
    "ExperimentalKochStatus",
    "ExperimentalKochResult",
    "ExperimentalKochWindow",
    "ExperimentalKochAdmissibilityMap",
    "search_experimental_koch",
    "scan_experimental_koch_admissibility",
]


class ExperimentalKochStatus(str, Enum):
    """Structured outcome for a high-latitude Koch experimental computation."""

    NOT_IMPLEMENTED = "not_implemented"
    UNIQUE_ORDERED_SOLUTION = "unique_ordered_solution"
    NO_VALID_SOLUTION = "no_valid_solution"
    HORIZON_BRANCH_SELECTION_FAILED = "horizon_branch_selection_failed"
    ASSEMBLY_FAILED = "assembly_failed"
    UNORDERED_CUSP_CYCLE = "unordered_cusp_cycle"


@dataclass(frozen=True, slots=True)
class ExperimentalKochResult:
    """Result of an explicit high-latitude Koch experimental search/computation."""

    armc: float
    obliquity: float
    latitude: float
    asc: float
    mc: float
    status: ExperimentalKochStatus
    cusps: tuple[float, ...] | None = None
    diagnostic_summary: str = ""
    quality_verdict: HouseCycleVerdict | None = None
    distortion_profile: HouseDistortionProfile | None = None
    practical_rho_max: float | None = None

    @property
    def has_solution(self) -> bool:
        return self.cusps is not None


@dataclass(frozen=True, slots=True)
class ExperimentalKochWindow:
    """Contiguous ARMC interval where one unique ordered Koch solution exists."""

    start_armc: float
    end_armc: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class ExperimentalKochAdmissibilityMap:
    """Scanned admissibility windows for the explicit Koch search mode."""

    latitude: float
    obliquity: float
    armc_start: float
    armc_end: float
    armc_step: float
    sample_count: int
    valid_armcs: tuple[float, ...]
    windows: tuple[ExperimentalKochWindow, ...]
    total_samples: int
    practical_rho_max: float | None = None
    practically_valid_armcs: tuple[float, ...] = ()
    practical_windows: tuple[ExperimentalKochWindow, ...] = ()
    stability_radius: int = 0
    stable_practical_armcs: tuple[float, ...] = ()
    stable_practical_windows: tuple[ExperimentalKochWindow, ...] = ()

    @property
    def valid_fraction(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return len(self.valid_armcs) / self.total_samples

    @property
    def has_any_window(self) -> bool:
        return bool(self.windows)


def search_experimental_koch(
    armc: float,
    obliquity: float,
    latitude: float,
    asc: float,
    mc: float,
    *,
    sample_count: int = 12000,
    ordering_tolerance: float = 1e-7,
    rho_max: float | None = None,
    **kwargs,
) -> ExperimentalKochResult:
    """
    Experimental high-latitude Koch cusp computation.

    Uses the standard Koch RA specs (from MC AD/DSA, already clamped in the
    helper) but performs the pole=lat plane projection using a tan-free
    (cleared-denominator) plane normal to avoid overflow at |lat| near 90°.

    This is the "real logic" start: the geometric object (RA + pole plane)
    is constructed safely, intersections selected by horizon branch using
    the passed asc/mc for ties, assembled, and accepted only if the resulting
    cusps form a strictly ordered cycle.

    If a valid ordered set is obtained, it is returned (status UNIQUE_ORDERED_SOLUTION).
    Otherwise cusps=None and the failure is classified by doctrine stage:
    horizon branch selection, assembly, or post-assembly cusp ordering.

    The search is currently "direct" (one candidate from the doctrine) with
    post-check for order; if multiple branches appear in future refinements
    a sampling search (like Placidus) can be added here.

    Signature and Result shape kept compatible with the common experimental
    dispatch.
    """
    # Import the canonical helpers inside the experimental function (like
    # the scan in experimental_placidus) so the research logic stays isolated
    # and can evolve without touching main doctrine.
    from .houses import (
        _koch_pole_height_specs,
        _ecliptic_intersection_candidates,
        _select_horizon_branch,
        _assemble_antipodal_quadrant_cusps,
        _local_horizon_basis,
        _normalize3,
    )

    def _safe_ra_pole_plane_normal(ra_deg: float, pole_deg: float) -> tuple[float, float, float]:
        """Tan-free form of the RA+pole plane normal (multiply equation by cos(pole))."""
        ra_r = math.radians(ra_deg)
        p_r = math.radians(pole_deg)
        cp = math.cos(p_r)
        sp = math.sin(p_r)
        return _normalize3((
            -math.sin(ra_r) * cp,
            math.cos(ra_r) * cp,
            -sp,
        ))

    # Compute the Koch RA specs using the (already safe/clamped) helper.
    # This gives the required RA for houses 2,3,11,12 at pole=latitude.
    specs = _koch_pole_height_specs(armc, mc, obliquity, latitude)

    # Zenith for branch selection (horizon heights).
    _, _, zenith = _local_horizon_basis(armc, latitude)

    primaries = {}
    for house in (2, 3, 11, 12):
        ra, _ = specs[house]  # pole is always latitude for Koch
        plane = _safe_ra_pole_plane_normal(ra, latitude)
        primary, secondary = _ecliptic_intersection_candidates(plane, obliquity)

        prefer_above = house in (11, 12)
        tie_start = mc if prefer_above else asc
        tie_end = asc if prefer_above else mc

        try:
            lam = _select_horizon_branch(
                primary, secondary,
                zenith=zenith,
                prefer_above_horizon=prefer_above,
                obliquity_deg=obliquity,
                tie_arc_start=tie_start,
                tie_arc_end=tie_end,
            )
            primaries[house] = lam
        except Exception:
            # Selection failed (degenerate at this lat/ARMC) -> no valid solution.
            return ExperimentalKochResult(
                armc=armc,
                obliquity=obliquity,
                latitude=latitude,
                asc=asc,
                mc=mc,
                status=ExperimentalKochStatus.HORIZON_BRANCH_SELECTION_FAILED,
                cusps=None,
                diagnostic_summary="horizon branch selection failed for safe pole projection",
            )

    # Assemble using the canonical assembler (antipodal + fixed ASC/MC).
    try:
        cusps_list = _assemble_antipodal_quadrant_cusps(
            asc=asc,
            mc=mc,
            h2=primaries[2],
            h3=primaries[3],
            h11=primaries[11],
            h12=primaries[12],
            context="experimental_koch",
        )
    except Exception as e:
        return ExperimentalKochResult(
            armc=armc,
            obliquity=obliquity,
            latitude=latitude,
            asc=asc,
            mc=mc,
            status=ExperimentalKochStatus.ASSEMBLY_FAILED,
            cusps=None,
            diagnostic_summary=f"assembly failed: {e}",
        )

    cusps = tuple(cusps_list)

    # Check ordered cycle (same doctrine as Placidus experimental for consistency
    # of "valid house figure").
    is_ordered = strictly_ordered_cusp_cycle(
        cusps,
        ordering_tolerance=ordering_tolerance,
    )

    if is_ordered:
        status = ExperimentalKochStatus.UNIQUE_ORDERED_SOLUTION
        diag = "safe pole projection yielded ordered Koch cusps"
        quality_verdict: HouseCycleVerdict | None = None
        distortion_profile: HouseDistortionProfile | None = None
        if rho_max is not None:
            quality_verdict, distortion_profile = house_cycle_verdict(
                cusps,
                rho_max=rho_max,
                ordering_tolerance=ordering_tolerance,
            )
    else:
        status = ExperimentalKochStatus.UNORDERED_CUSP_CYCLE
        cusps = None
        diag = "assembled cusps not strictly ordered"
        quality_verdict = None
        distortion_profile = None

    return ExperimentalKochResult(
        armc=armc,
        obliquity=obliquity,
        latitude=latitude,
        asc=asc,
        mc=mc,
        status=status,
        cusps=cusps,
        diagnostic_summary=diag,
        quality_verdict=quality_verdict,
        distortion_profile=distortion_profile,
        practical_rho_max=rho_max,
    )


def scan_experimental_koch_admissibility(
    latitude: float,
    obliquity: float,
    *,
    armc_start: float = 0.0,
    armc_end: float = 360.0,
    armc_step: float = 0.5,
    sample_count: int = 12000,
    ordering_tolerance: float = 1e-7,
    rho_max: float | None = None,
    stability_radius: int = 0,
) -> ExperimentalKochAdmissibilityMap:
    """
    Scan ARMC space for unique ordered experimental Koch solutions.

    A sample is considered valid only when ``search_experimental_koch`` returns
    exactly one ordered cusp cycle.
    """
    from .houses import _asc_from_armc, _mc_from_armc

    if armc_step <= 0.0:
        raise ValueError("armc_step must be > 0")
    if armc_end < armc_start:
        raise ValueError("armc_end must be >= armc_start")
    if stability_radius < 0:
        raise ValueError("stability_radius must be >= 0")

    valid_armcs: list[float] = []
    practical_armcs: list[float] = []
    practical_flags: list[bool] = []
    armc = armc_start
    while armc <= armc_end + 1e-12:
        asc = _asc_from_armc(armc, obliquity, latitude)
        mc = _mc_from_armc(armc, obliquity, latitude)
        result = search_experimental_koch(
            armc,
            obliquity,
            latitude,
            asc,
            mc,
            sample_count=sample_count,
            ordering_tolerance=ordering_tolerance,
            rho_max=rho_max,
        )
        if result.status == ExperimentalKochStatus.UNIQUE_ORDERED_SOLUTION:
            valid_armcs.append(round(armc, 10))
        is_practical = result.quality_verdict == "practically_admissible"
        practical_flags.append(is_practical)
        if is_practical:
            practical_armcs.append(round(armc, 10))
        armc += armc_step

    windows: list[ExperimentalKochWindow] = []
    if valid_armcs:
        start = prev = valid_armcs[0]
        for armc_value in valid_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                windows.append(
                    ExperimentalKochWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        windows.append(
            ExperimentalKochWindow(
                start_armc=start,
                end_armc=prev,
                sample_count=int(round((prev - start) / armc_step)) + 1,
            )
        )

    practical_windows: list[ExperimentalKochWindow] = []
    if practical_armcs:
        start = prev = practical_armcs[0]
        for armc_value in practical_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                practical_windows.append(
                    ExperimentalKochWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        practical_windows.append(
            ExperimentalKochWindow(
                start_armc=start,
                end_armc=prev,
                sample_count=int(round((prev - start) / armc_step)) + 1,
            )
        )

    stable_practical_flags = stable_true_flags(practical_flags, radius=stability_radius)
    stable_practical_armcs = tuple(
        round(armc_start + index * armc_step, 10)
        for index, is_stable in enumerate(stable_practical_flags)
        if is_stable
    )
    stable_practical_windows: list[ExperimentalKochWindow] = []
    if stable_practical_armcs:
        start = prev = stable_practical_armcs[0]
        for armc_value in stable_practical_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                stable_practical_windows.append(
                    ExperimentalKochWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        stable_practical_windows.append(
            ExperimentalKochWindow(
                start_armc=start,
                end_armc=prev,
                sample_count=int(round((prev - start) / armc_step)) + 1,
            )
        )

    total_samples = int(round((armc_end - armc_start) / armc_step)) + 1
    return ExperimentalKochAdmissibilityMap(
        latitude=latitude,
        obliquity=obliquity,
        armc_start=armc_start,
        armc_end=armc_end,
        armc_step=armc_step,
        sample_count=sample_count,
        valid_armcs=tuple(valid_armcs),
        windows=tuple(windows),
        total_samples=total_samples,
        practical_rho_max=rho_max,
        practically_valid_armcs=tuple(practical_armcs),
        practical_windows=tuple(practical_windows),
        stability_radius=stability_radius,
        stable_practical_armcs=stable_practical_armcs,
        stable_practical_windows=tuple(stable_practical_windows),
    )
