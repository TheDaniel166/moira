"""
Experimental high-latitude solver for Topocentric houses.

This module is intentionally separate from moira.houses (following the established
pattern from experimental_placidus.py) so that research-grade or experimental
high-latitude pole-height / polar-projection resolution logic for Topocentric
can be developed and opted into explicitly via PolarFallbackPolicy.EXPERIMENTAL_SEARCH
without altering the main house doctrine or computation paths for normal latitudes.

The main houses engine will delegate to this only under explicit experimental
policy for this system when |lat| >= critical and the system is still guarded.

See HOUSES_SOVEREIGNTY_REMEDIATION_ROADMAP.md for the required geometric
object-first remediation for Topocentric (similar pole-height issues to Regio).
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
    "ExperimentalTopocentricStatus",
    "ExperimentalTopocentricResult",
    "ExperimentalTopocentricWindow",
    "ExperimentalTopocentricAdmissibilityMap",
    "search_experimental_topocentric",
    "scan_experimental_topocentric_admissibility",
]


class ExperimentalTopocentricStatus(str, Enum):
    """Structured outcome for a high-latitude Topocentric experimental computation."""

    UNIQUE_ORDERED_SOLUTION = "unique_ordered_solution"
    ASSEMBLY_FAILED = "assembly_failed"
    UNORDERED_CUSP_CYCLE = "unordered_cusp_cycle"


@dataclass(frozen=True, slots=True)
class ExperimentalTopocentricResult:
    """Result of an explicit high-latitude Topocentric experimental computation."""

    armc: float
    obliquity: float
    latitude: float
    asc: float
    mc: float
    status: ExperimentalTopocentricStatus
    cusps: tuple[float, ...] | None = None
    diagnostic_summary: str = ""
    quality_verdict: HouseCycleVerdict | None = None
    distortion_profile: HouseDistortionProfile | None = None
    practical_rho_max: float | None = None

    @property
    def has_solution(self) -> bool:
        return self.cusps is not None


@dataclass(frozen=True, slots=True)
class ExperimentalTopocentricWindow:
    """Contiguous ARMC interval where one unique ordered Topocentric solution exists."""

    start_armc: float
    end_armc: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class ExperimentalTopocentricAdmissibilityMap:
    """Scanned admissibility windows for the explicit Topocentric search mode."""

    latitude: float
    obliquity: float
    armc_start: float
    armc_end: float
    armc_step: float
    valid_armcs: tuple[float, ...]
    windows: tuple[ExperimentalTopocentricWindow, ...]
    total_samples: int
    practical_rho_max: float | None = None
    practically_valid_armcs: tuple[float, ...] = ()
    practical_windows: tuple[ExperimentalTopocentricWindow, ...] = ()
    stability_radius: int = 0
    stable_practical_armcs: tuple[float, ...] = ()
    stable_practical_windows: tuple[ExperimentalTopocentricWindow, ...] = ()

    @property
    def valid_fraction(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return len(self.valid_armcs) / self.total_samples

    @property
    def has_any_window(self) -> bool:
        return bool(self.windows)


def search_experimental_topocentric(
    armc: float,
    obliquity: float,
    latitude: float,
    asc: float,
    mc: float,
    *,
    ordering_tolerance: float = 1e-7,
    rho_max: float | None = None,
    **kwargs,
) -> ExperimentalTopocentricResult:
    """
    Experimental high-latitude Topocentric cusp computation.

    Topocentric belongs to the shared pole-height family. The experimental
    surface makes that doctrine explicit: derive the Polich-Page graduated pole
    heights ``phi_1`` and ``phi_2``, express houses 2/3/11/12 as equatorial
    right ascension plus pole-height specifications, then feed those named
    objects through the shared horizon-branch pole-height assembler.

    The resulting quadrant figure is admitted only when the cusp cycle remains
    strictly ordered from the actual Ascendant.
    """
    from .houses import _assemble_pole_height_quadrant_family, _mc_above_horizon

    phi = math.radians(latitude)
    phi_1 = math.degrees(math.atan((1.0 / 3.0) * math.tan(phi)))
    phi_2 = math.degrees(math.atan((2.0 / 3.0) * math.tan(phi)))
    mc_visible = _mc_above_horizon(mc, obliquity, latitude)

    try:
        cusp_list = _assemble_pole_height_quadrant_family(
            armc_deg=armc,
            asc=asc,
            mc=mc_visible,
            obliquity_deg=obliquity,
            latitude_deg=latitude,
            cusp_specs={
                2: (armc + 120.0, phi_2),
                3: (armc + 150.0, phi_1),
                11: (armc + 30.0, phi_1),
                12: (armc + 60.0, phi_2),
            },
            context="experimental_topocentric",
        )
    except Exception as exc:
        return ExperimentalTopocentricResult(
            armc=armc,
            obliquity=obliquity,
            latitude=latitude,
            asc=asc,
            mc=mc,
            status=ExperimentalTopocentricStatus.ASSEMBLY_FAILED,
            cusps=None,
            diagnostic_summary=f"assembly failed: {exc}",
        )

    cusps = tuple(cusp_list)
    is_ordered = strictly_ordered_cusp_cycle(
        cusps,
        ordering_tolerance=ordering_tolerance,
    )

    if is_ordered:
        status = ExperimentalTopocentricStatus.UNIQUE_ORDERED_SOLUTION
        diag = "pole-height projection yielded ordered Topocentric cusps"
        quality_verdict: HouseCycleVerdict | None = None
        distortion_profile: HouseDistortionProfile | None = None
        if rho_max is not None:
            quality_verdict, distortion_profile = house_cycle_verdict(
                cusps,
                rho_max=rho_max,
                ordering_tolerance=ordering_tolerance,
            )
    else:
        status = ExperimentalTopocentricStatus.UNORDERED_CUSP_CYCLE
        cusps = None
        diag = "assembled cusps not strictly ordered"
        quality_verdict = None
        distortion_profile = None

    return ExperimentalTopocentricResult(
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


def scan_experimental_topocentric_admissibility(
    latitude: float,
    obliquity: float,
    *,
    armc_start: float = 0.0,
    armc_end: float = 360.0,
    armc_step: float = 0.5,
    ordering_tolerance: float = 1e-7,
    rho_max: float | None = None,
    stability_radius: int = 0,
) -> ExperimentalTopocentricAdmissibilityMap:
    """Scan ARMC space for unique ordered experimental Topocentric solutions."""
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
        result = search_experimental_topocentric(
            armc,
            obliquity,
            latitude,
            asc,
            mc,
            ordering_tolerance=ordering_tolerance,
            rho_max=rho_max,
        )
        if result.status == ExperimentalTopocentricStatus.UNIQUE_ORDERED_SOLUTION:
            valid_armcs.append(round(armc, 10))
        is_practical = result.quality_verdict == "practically_admissible"
        practical_flags.append(is_practical)
        if is_practical:
            practical_armcs.append(round(armc, 10))
        armc += armc_step

    windows: list[ExperimentalTopocentricWindow] = []
    if valid_armcs:
        start = prev = valid_armcs[0]
        for armc_value in valid_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                windows.append(
                    ExperimentalTopocentricWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        windows.append(
            ExperimentalTopocentricWindow(
                start_armc=start,
                end_armc=prev,
                sample_count=int(round((prev - start) / armc_step)) + 1,
            )
        )

    practical_windows: list[ExperimentalTopocentricWindow] = []
    if practical_armcs:
        start = prev = practical_armcs[0]
        for armc_value in practical_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                practical_windows.append(
                    ExperimentalTopocentricWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        practical_windows.append(
            ExperimentalTopocentricWindow(
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
    stable_practical_windows: list[ExperimentalTopocentricWindow] = []
    if stable_practical_armcs:
        start = prev = stable_practical_armcs[0]
        for armc_value in stable_practical_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                stable_practical_windows.append(
                    ExperimentalTopocentricWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        stable_practical_windows.append(
            ExperimentalTopocentricWindow(
                start_armc=start,
                end_armc=prev,
                sample_count=int(round((prev - start) / armc_step)) + 1,
            )
        )

    total_samples = int(round((armc_end - armc_start) / armc_step)) + 1
    return ExperimentalTopocentricAdmissibilityMap(
        latitude=latitude,
        obliquity=obliquity,
        armc_start=armc_start,
        armc_end=armc_end,
        armc_step=armc_step,
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
