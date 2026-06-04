"""
Experimental high-latitude solver for Regiomontanus houses.

This module is intentionally separate from moira.houses (following the established
pattern from experimental_placidus.py) so that research-grade or experimental
high-latitude pole-height / polar-projection resolution logic for Regiomontanus
can be developed and opted into explicitly via PolarFallbackPolicy.EXPERIMENTAL_SEARCH
without altering the main house doctrine or computation paths for normal latitudes.

The main houses engine will delegate to this only under explicit experimental
policy for this system when |lat| >= critical and the system is still guarded.

See HOUSES_SOVEREIGNTY_REMEDIATION_ROADMAP.md for the required geometric
object-first remediation for Regiomontanus (pole heights, branch selection
not driven by mc_swapped repair).
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
    "ExperimentalRegiomontanusStatus",
    "ExperimentalRegiomontanusResult",
    "ExperimentalRegiomontanusWindow",
    "ExperimentalRegiomontanusAdmissibilityMap",
    "search_experimental_regiomontanus",
    "scan_experimental_regiomontanus_admissibility",
]


class ExperimentalRegiomontanusStatus(str, Enum):
    """Structured outcome for a high-latitude Regiomontanus experimental computation."""

    NOT_IMPLEMENTED = "not_implemented"
    UNIQUE_ORDERED_SOLUTION = "unique_ordered_solution"
    NO_VALID_SOLUTION = "no_valid_solution"


@dataclass(frozen=True, slots=True)
class ExperimentalRegiomontanusResult:
    """Result of an explicit high-latitude Regiomontanus experimental computation."""

    armc: float
    obliquity: float
    latitude: float
    asc: float
    mc: float
    status: ExperimentalRegiomontanusStatus
    cusps: tuple[float, ...] | None = None
    diagnostic_summary: str = ""
    quality_verdict: HouseCycleVerdict | None = None
    distortion_profile: HouseDistortionProfile | None = None
    practical_rho_max: float | None = None

    @property
    def has_solution(self) -> bool:
        return self.cusps is not None


@dataclass(frozen=True, slots=True)
class ExperimentalRegiomontanusWindow:
    """Contiguous ARMC interval where one unique ordered Regiomontanus solution exists."""

    start_armc: float
    end_armc: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class ExperimentalRegiomontanusAdmissibilityMap:
    """Scanned admissibility windows for the explicit Regiomontanus search mode."""

    latitude: float
    obliquity: float
    armc_start: float
    armc_end: float
    armc_step: float
    sample_count: int
    valid_armcs: tuple[float, ...]
    windows: tuple[ExperimentalRegiomontanusWindow, ...]
    total_samples: int
    practical_rho_max: float | None = None
    practically_valid_armcs: tuple[float, ...] = ()
    practical_windows: tuple[ExperimentalRegiomontanusWindow, ...] = ()
    stability_radius: int = 0
    stable_practical_armcs: tuple[float, ...] = ()
    stable_practical_windows: tuple[ExperimentalRegiomontanusWindow, ...] = ()

    @property
    def valid_fraction(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return len(self.valid_armcs) / self.total_samples

    @property
    def has_any_window(self) -> bool:
        return bool(self.windows)


def search_experimental_regiomontanus(
    armc: float,
    obliquity: float,
    latitude: float,
    asc: float,
    mc: float,
    *,
    rho_max: float | None = None,
    **kwargs,
) -> ExperimentalRegiomontanusResult:
    """
    Experimental high-latitude Regiomontanus cusp computation.

    Uses the standard Regiomontanus pole-height specs, but projects each
    RA+pole cusp plane using a tan-free cleared-denominator plane normal to
    avoid overflow near the poles. Branches are selected by horizon hemisphere
    and the final figure is accepted only if the cusp cycle is strictly ordered.
    """
    from .houses import (
        _assemble_antipodal_quadrant_cusps,
        _ecliptic_intersection_candidates,
        _local_horizon_basis,
        _normalize3,
        _select_horizon_branch,
    )

    phi = math.radians(latitude)

    def _safe_ra_pole_plane_normal(ra_deg: float, pole_height_deg: float) -> tuple[float, float, float]:
        ra_r = math.radians(ra_deg)
        p_r = math.radians(pole_height_deg)
        cp = math.cos(p_r)
        sp = math.sin(p_r)
        return _normalize3((
            -math.sin(ra_r) * cp,
            math.cos(ra_r) * cp,
            -sp,
        ))

    phi_h1 = math.degrees(math.atan(math.tan(phi) * math.sin(math.radians(30.0))))
    phi_h2 = math.degrees(math.atan(math.tan(phi) * math.sin(math.radians(60.0))))
    specs = {
        2: (armc + 120.0, phi_h2),
        3: (armc + 150.0, phi_h1),
        11: (armc + 30.0, phi_h1),
        12: (armc + 60.0, phi_h2),
    }

    _, _, zenith = _local_horizon_basis(armc, latitude)

    primaries: dict[int, float] = {}
    for house in (2, 3, 11, 12):
        ra, pole = specs[house]
        plane = _safe_ra_pole_plane_normal(ra, pole)
        primary, secondary = _ecliptic_intersection_candidates(plane, obliquity)
        prefer_above = house in (11, 12)
        tie_start = mc if prefer_above else asc
        tie_end = asc if prefer_above else mc
        try:
            lam = _select_horizon_branch(
                primary,
                secondary,
                zenith=zenith,
                prefer_above_horizon=prefer_above,
                obliquity_deg=obliquity,
                tie_arc_start=tie_start,
                tie_arc_end=tie_end,
            )
            primaries[house] = lam
        except Exception:
            return ExperimentalRegiomontanusResult(
                armc=armc,
                obliquity=obliquity,
                latitude=latitude,
                asc=asc,
                mc=mc,
                status=ExperimentalRegiomontanusStatus.NO_VALID_SOLUTION,
                cusps=None,
                diagnostic_summary="horizon branch selection failed for safe pole projection",
            )

    try:
        cusps_list = _assemble_antipodal_quadrant_cusps(
            asc=asc,
            mc=mc,
            h2=primaries[2],
            h3=primaries[3],
            h11=primaries[11],
            h12=primaries[12],
            context="experimental_regiomontanus",
        )
    except Exception as e:
        return ExperimentalRegiomontanusResult(
            armc=armc,
            obliquity=obliquity,
            latitude=latitude,
            asc=asc,
            mc=mc,
            status=ExperimentalRegiomontanusStatus.NO_VALID_SOLUTION,
            cusps=None,
            diagnostic_summary=f"assembly failed: {e}",
        )

    cusps = tuple(cusps_list)
    is_ordered = strictly_ordered_cusp_cycle(
        cusps,
        ordering_tolerance=kwargs.get("ordering_tolerance", 1e-7),
    )

    if is_ordered:
        status = ExperimentalRegiomontanusStatus.UNIQUE_ORDERED_SOLUTION
        diag = "safe pole projection yielded ordered Regiomontanus cusps"
        quality_verdict: HouseCycleVerdict | None = None
        distortion_profile: HouseDistortionProfile | None = None
        if rho_max is not None:
            quality_verdict, distortion_profile = house_cycle_verdict(
                cusps,
                rho_max=rho_max,
                ordering_tolerance=kwargs.get("ordering_tolerance", 1e-7),
            )
    else:
        status = ExperimentalRegiomontanusStatus.NO_VALID_SOLUTION
        cusps = None
        diag = "assembled cusps not strictly ordered"
        quality_verdict = None
        distortion_profile = None

    return ExperimentalRegiomontanusResult(
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


def scan_experimental_regiomontanus_admissibility(
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
) -> ExperimentalRegiomontanusAdmissibilityMap:
    """
    Scan ARMC space for unique ordered experimental Regiomontanus solutions.
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
        result = search_experimental_regiomontanus(
            armc,
            obliquity,
            latitude,
            asc,
            mc,
            sample_count=sample_count,
            ordering_tolerance=ordering_tolerance,
            rho_max=rho_max,
        )
        if result.status == ExperimentalRegiomontanusStatus.UNIQUE_ORDERED_SOLUTION:
            valid_armcs.append(round(armc, 10))
        is_practical = result.quality_verdict == "practically_admissible"
        practical_flags.append(is_practical)
        if is_practical:
            practical_armcs.append(round(armc, 10))
        armc += armc_step

    windows: list[ExperimentalRegiomontanusWindow] = []
    if valid_armcs:
        start = prev = valid_armcs[0]
        for armc_value in valid_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                windows.append(
                    ExperimentalRegiomontanusWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        windows.append(
            ExperimentalRegiomontanusWindow(
                start_armc=start,
                end_armc=prev,
                sample_count=int(round((prev - start) / armc_step)) + 1,
            )
        )

    practical_windows: list[ExperimentalRegiomontanusWindow] = []
    if practical_armcs:
        start = prev = practical_armcs[0]
        for armc_value in practical_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                practical_windows.append(
                    ExperimentalRegiomontanusWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        practical_windows.append(
            ExperimentalRegiomontanusWindow(
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
    stable_practical_windows: list[ExperimentalRegiomontanusWindow] = []
    if stable_practical_armcs:
        start = prev = stable_practical_armcs[0]
        for armc_value in stable_practical_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                stable_practical_windows.append(
                    ExperimentalRegiomontanusWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        stable_practical_windows.append(
            ExperimentalRegiomontanusWindow(
                start_armc=start,
                end_armc=prev,
                sample_count=int(round((prev - start) / armc_step)) + 1,
            )
        )

    total_samples = int(round((armc_end - armc_start) / armc_step)) + 1
    return ExperimentalRegiomontanusAdmissibilityMap(
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
