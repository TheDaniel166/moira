"""
Experimental high-latitude solver for Alcabitius houses.

This module is intentionally separate from moira.houses (following the established
pattern from experimental_placidus.py) so that research-grade or experimental
high-latitude direct zero-pole / semi-arc resolution logic for Alcabitius can
be developed and opted into explicitly via PolarFallbackPolicy.EXPERIMENTAL_SEARCH
without altering the main house doctrine or computation paths for normal latitudes.

The main houses engine will delegate to this only under explicit experimental
policy for this system when |lat| >= critical and the system is still guarded.

See HOUSES_SOVEREIGNTY_REMEDIATION_ROADMAP.md for the required geometric
object-first remediation for Alcabitius (direct zero-pole equatorial sector
projection rather than inherited OA/AD/DSA staging).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


__all__ = [
    "ExperimentalAlcabitiusStatus",
    "ExperimentalAlcabitiusResult",
    "ExperimentalAlcabitiusWindow",
    "ExperimentalAlcabitiusAdmissibilityMap",
    "search_experimental_alcabitius",
    "scan_experimental_alcabitius_admissibility",
]


class ExperimentalAlcabitiusStatus(str, Enum):
    """Structured outcome for a high-latitude Alcabitius experimental computation."""

    UNIQUE_ORDERED_SOLUTION = "unique_ordered_solution"
    ASSEMBLY_FAILED = "assembly_failed"
    UNORDERED_CUSP_CYCLE = "unordered_cusp_cycle"


@dataclass(frozen=True, slots=True)
class ExperimentalAlcabitiusResult:
    """Result of an explicit high-latitude Alcabitius experimental computation."""

    armc: float
    obliquity: float
    latitude: float
    asc: float
    mc: float
    status: ExperimentalAlcabitiusStatus
    cusps: tuple[float, ...] | None = None
    diagnostic_summary: str = ""

    @property
    def has_solution(self) -> bool:
        return self.cusps is not None


@dataclass(frozen=True, slots=True)
class ExperimentalAlcabitiusWindow:
    """Contiguous ARMC interval where one unique ordered Alcabitius solution exists."""

    start_armc: float
    end_armc: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class ExperimentalAlcabitiusAdmissibilityMap:
    """Scanned admissibility windows for the explicit Alcabitius search mode."""

    latitude: float
    obliquity: float
    armc_start: float
    armc_end: float
    armc_step: float
    valid_armcs: tuple[float, ...]
    windows: tuple[ExperimentalAlcabitiusWindow, ...]
    total_samples: int

    @property
    def valid_fraction(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return len(self.valid_armcs) / self.total_samples

    @property
    def has_any_window(self) -> bool:
        return bool(self.windows)


def search_experimental_alcabitius(
    armc: float,
    obliquity: float,
    latitude: float,
    asc: float,
    mc: float,
    *,
    ordering_tolerance: float = 1e-7,
    **kwargs,
) -> ExperimentalAlcabitiusResult:
    """
    Experimental high-latitude Alcabitius cusp computation.

    Alcabitius already has a direct zero-pole governing object in the main
    engine: derive the Ascendant declination from the Ascendant vector, derive
    the semi-diurnal arc from the zenith/Ascendant horizon relation, express
    the quadrant primaries as equatorial right ascensions, then project them
    directly back to the ecliptic with zero pole height.

    The experimental surface exposes that doctrine explicitly with structured
    status reporting so the public experimental policy can admit real high-
    latitude Alcabitius figures without fallback when the direct family remains
    ordered.
    """
    from .houses import (
        _alcabitius_zero_pole_specs,
        _assemble_direct_zero_pole_quadrant_family,
    )

    try:
        cusp_list = _assemble_direct_zero_pole_quadrant_family(
            asc=asc,
            mc=mc,
            obliquity_deg=obliquity,
            cusp_ras=_alcabitius_zero_pole_specs(armc, asc, obliquity, latitude),
            context="experimental_alcabitius",
        )
    except Exception as exc:
        return ExperimentalAlcabitiusResult(
            armc=armc,
            obliquity=obliquity,
            latitude=latitude,
            asc=asc,
            mc=mc,
            status=ExperimentalAlcabitiusStatus.ASSEMBLY_FAILED,
            cusps=None,
            diagnostic_summary=f"assembly failed: {exc}",
        )

    cusps = tuple(cusp_list)
    unwrapped = [0.0] + [((c - asc) % 360.0) for c in cusps[1:]]
    is_ordered = all(
        unwrapped[i + 1] - unwrapped[i] > ordering_tolerance
        for i in range(11)
    )

    if is_ordered:
        status = ExperimentalAlcabitiusStatus.UNIQUE_ORDERED_SOLUTION
        diag = "direct zero-pole projection yielded ordered Alcabitius cusps"
    else:
        status = ExperimentalAlcabitiusStatus.UNORDERED_CUSP_CYCLE
        cusps = None
        diag = "assembled cusps not strictly ordered"

    return ExperimentalAlcabitiusResult(
        armc=armc,
        obliquity=obliquity,
        latitude=latitude,
        asc=asc,
        mc=mc,
        status=status,
        cusps=cusps,
        diagnostic_summary=diag,
    )


def scan_experimental_alcabitius_admissibility(
    latitude: float,
    obliquity: float,
    *,
    armc_start: float = 0.0,
    armc_end: float = 360.0,
    armc_step: float = 0.5,
    ordering_tolerance: float = 1e-7,
) -> ExperimentalAlcabitiusAdmissibilityMap:
    """Scan ARMC space for unique ordered experimental Alcabitius solutions."""
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
        result = search_experimental_alcabitius(
            armc,
            obliquity,
            latitude,
            asc,
            mc,
            ordering_tolerance=ordering_tolerance,
        )
        if result.status == ExperimentalAlcabitiusStatus.UNIQUE_ORDERED_SOLUTION:
            valid_armcs.append(round(armc, 10))
        armc += armc_step

    windows: list[ExperimentalAlcabitiusWindow] = []
    if valid_armcs:
        start = prev = valid_armcs[0]
        for armc_value in valid_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                windows.append(
                    ExperimentalAlcabitiusWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        windows.append(
            ExperimentalAlcabitiusWindow(
                start_armc=start,
                end_armc=prev,
                sample_count=int(round((prev - start) / armc_step)) + 1,
            )
        )

    total_samples = int(round((armc_end - armc_start) / armc_step)) + 1
    return ExperimentalAlcabitiusAdmissibilityMap(
        latitude=latitude,
        obliquity=obliquity,
        armc_start=armc_start,
        armc_end=armc_end,
        armc_step=armc_step,
        valid_armcs=tuple(valid_armcs),
        windows=tuple(windows),
        total_samples=total_samples,
    )
