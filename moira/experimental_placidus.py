"""
Experimental branch-aware Placidus solver for high latitudes.

This module is intentionally separate from moira.houses so callers can opt into
research-grade experimentation explicitly. It does not alter Moira's default
house doctrine. The owning house engine may call into this module only when the
user selects an explicit experimental policy.
"""

import math
from dataclasses import dataclass
from enum import Enum
from itertools import product


__all__ = [
    "ExperimentalPlacidusStatus",
    "ExperimentalPlacidusResult",
    "ExperimentalPlacidusWindow",
    "ExperimentalPlacidusAdmissibilityMap",
    "search_experimental_placidus",
    "scan_experimental_placidus_admissibility",
]


class ExperimentalPlacidusStatus(str, Enum):
    """Structured outcome for a high-latitude Placidus branch search."""

    UNIQUE_ORDERED_SOLUTION = "unique_ordered_solution"
    NO_REQUIRED_ROOTS = "no_required_roots"
    NO_ORDERED_SOLUTION = "no_ordered_solution"
    AMBIGUOUS_ORDERED_SOLUTION = "ambiguous_ordered_solution"


@dataclass(frozen=True, slots=True)
class ExperimentalPlacidusResult:
    """Result of an explicit high-latitude Placidus branch search."""

    armc: float
    obliquity: float
    latitude: float
    asc: float
    mc: float
    status: ExperimentalPlacidusStatus
    cusps: tuple[float, ...] | None
    ordered_solution_count: int
    ordered_solutions: tuple[tuple[float, ...], ...]
    h11_roots: tuple[float, ...]
    h12_roots: tuple[float, ...]
    h3_roots: tuple[float, ...]
    h2_roots: tuple[float, ...]

    @property
    def has_solution(self) -> bool:
        return self.cusps is not None

    @property
    def all_required_roots_present(self) -> bool:
        return all((self.h11_roots, self.h12_roots, self.h3_roots, self.h2_roots))

    @property
    def root_counts(self) -> tuple[int, int, int, int]:
        return (
            len(self.h11_roots),
            len(self.h12_roots),
            len(self.h3_roots),
            len(self.h2_roots),
        )

    @property
    def diagnostic_summary(self) -> str:
        return (
            f"status={self.status.value}; armc={self.armc:.4f}°; latitude={self.latitude:.4f}°; "
            f"ordered_solutions={self.ordered_solution_count}; "
            f"root_counts=(H11={len(self.h11_roots)}, H12={len(self.h12_roots)}, "
            f"H3={len(self.h3_roots)}, H2={len(self.h2_roots)})"
        )


@dataclass(frozen=True, slots=True)
class ExperimentalPlacidusWindow:
    """Contiguous ARMC interval where one unique ordered solution exists."""

    start_armc: float
    end_armc: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class ExperimentalPlacidusAdmissibilityMap:
    """Scanned admissibility windows for the explicit Placidus search mode."""

    latitude: float
    obliquity: float
    armc_start: float
    armc_end: float
    armc_step: float
    sample_count: int
    valid_armcs: tuple[float, ...]
    windows: tuple[ExperimentalPlacidusWindow, ...]
    total_samples: int

    @property
    def valid_fraction(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return len(self.valid_armcs) / self.total_samples

    @property
    def has_any_window(self) -> bool:
        return bool(self.windows)


def search_experimental_placidus(
    armc: float,
    obliquity: float,
    latitude: float,
    asc: float,
    mc: float,
    *,
    sample_count: int = 12000,
    ordering_tolerance: float = 1e-7,
) -> ExperimentalPlacidusResult:
    """
    Search for a unique ordered Placidus cusp cycle at a high latitude.

    The search solves the underlying semi-arc equations directly rather than
    relying on the fixed-point iteration used by the standard private Placidus
    implementation. If exactly one ordered cusp cycle is found, it is returned.
    If none or more than one are found, ``cusps`` is ``None`` and the caller is
    expected to decide what policy should apply.
    """
    eps = math.radians(obliquity)
    phi = math.radians(latitude)
    tau = 2.0 * math.pi

    def ra_to_lam(ra: float) -> float:
        return math.atan2(math.sin(ra), math.cos(eps) * math.cos(ra)) % tau

    def dsa_from_ra(ra: float) -> float | None:
        lam = ra_to_lam(ra)
        dec = math.asin(max(-1.0, min(1.0, math.sin(eps) * math.sin(lam))))
        arg = -math.tan(phi) * math.tan(dec)
        if arg < -1.0 or arg > 1.0:
            return None
        return math.acos(arg)

    def residual(ra: float, frac: float, *, lower: bool) -> float | None:
        armc_r = math.radians(armc)
        ic_r = armc_r + math.pi
        dsa = dsa_from_ra(ra)
        if dsa is None:
            return None
        if lower:
            return (ra - ic_r) + frac * (math.pi - dsa)
        return (ra - armc_r) - frac * dsa

    def bisect_root(a: float, b: float, frac: float, *, lower: bool) -> float:
        fa = residual(a, frac, lower=lower)
        if fa is None:
            return 0.5 * (a + b)
        for _ in range(80):
            m = 0.5 * (a + b)
            fm = residual(m, frac, lower=lower)
            if fm is None:
                break
            if abs(fm) < 1e-13:
                return m
            if (fa > 0) != (fm > 0):
                b = m
            else:
                a, fa = m, fm
        return 0.5 * (a + b)

    def roots_for(frac: float, *, lower: bool) -> tuple[float, ...]:
        armc_r = math.radians(armc)
        roots: list[float] = []
        prev_x: float | None = None
        prev_y: float | None = None
        for i in range(sample_count + 1):
            x = armc_r + tau * i / sample_count
            y = residual(x, frac, lower=lower)
            if y is None:
                prev_x = None
                prev_y = None
                continue
            if prev_y is not None and (y == 0.0 or prev_y == 0.0 or (y > 0) != (prev_y > 0)):
                root = bisect_root(prev_x, x, frac, lower=lower)
                lon = math.degrees(ra_to_lam(root)) % 360.0
                if not roots or min(abs((lon - item + 180.0) % 360.0 - 180.0) for item in roots) > 1e-5:
                    roots.append(lon)
            prev_x = x
            prev_y = y
        return tuple(sorted(roots))

    def ordered_cycle(cusps: tuple[float, ...]) -> bool:
        unwrapped = [0.0] + [((cusp - asc) % 360.0) for cusp in cusps[1:]]
        return all(unwrapped[i + 1] - unwrapped[i] > ordering_tolerance for i in range(11))

    h11_roots = roots_for(1.0 / 3.0, lower=False)
    h12_roots = roots_for(2.0 / 3.0, lower=False)
    h3_roots = roots_for(1.0 / 3.0, lower=True)
    h2_roots = roots_for(2.0 / 3.0, lower=True)

    ordered: list[tuple[float, ...]] = []
    if h11_roots and h12_roots and h3_roots and h2_roots:
        for h11, h12, h3, h2 in product(h11_roots, h12_roots, h3_roots, h2_roots):
            cusps = (
                asc,
                h2,
                h3,
                (mc + 180.0) % 360.0,
                (h11 + 180.0) % 360.0,
                (h12 + 180.0) % 360.0,
                (asc + 180.0) % 360.0,
                (h2 + 180.0) % 360.0,
                (h3 + 180.0) % 360.0,
                mc,
                h11,
                h12,
            )
            if ordered_cycle(cusps):
                ordered.append(cusps)

    if len(ordered) == 1:
        status = ExperimentalPlacidusStatus.UNIQUE_ORDERED_SOLUTION
    elif not (h11_roots and h12_roots and h3_roots and h2_roots):
        status = ExperimentalPlacidusStatus.NO_REQUIRED_ROOTS
    elif len(ordered) == 0:
        status = ExperimentalPlacidusStatus.NO_ORDERED_SOLUTION
    else:
        status = ExperimentalPlacidusStatus.AMBIGUOUS_ORDERED_SOLUTION

    unique_cusps = ordered[0] if len(ordered) == 1 else None
    return ExperimentalPlacidusResult(
        armc=armc,
        obliquity=obliquity,
        latitude=latitude,
        asc=asc,
        mc=mc,
        status=status,
        cusps=unique_cusps,
        ordered_solution_count=len(ordered),
        ordered_solutions=tuple(ordered),
        h11_roots=h11_roots,
        h12_roots=h12_roots,
        h3_roots=h3_roots,
        h2_roots=h2_roots,
    )


def scan_experimental_placidus_admissibility(
    latitude: float,
    obliquity: float,
    *,
    armc_start: float = 0.0,
    armc_end: float = 360.0,
    armc_step: float = 0.5,
    sample_count: int = 12000,
    ordering_tolerance: float = 1e-7,
) -> ExperimentalPlacidusAdmissibilityMap:
    """
    Scan ARMC space for unique ordered experimental Placidus solutions.

    This is an inspection tool for users who want to see where the explicit
    high-latitude Placidus search is admissible. A sample is considered valid
    only when ``search_experimental_placidus`` returns exactly one ordered
    solution.
    """
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
        result = search_experimental_placidus(
            armc,
            obliquity,
            latitude,
            asc,
            mc,
            sample_count=sample_count,
            ordering_tolerance=ordering_tolerance,
        )
        if result.status == ExperimentalPlacidusStatus.UNIQUE_ORDERED_SOLUTION:
            valid_armcs.append(round(armc, 10))
        armc += armc_step

    windows: list[ExperimentalPlacidusWindow] = []
    if valid_armcs:
        start = prev = valid_armcs[0]
        for armc_value in valid_armcs[1:]:
            if abs(armc_value - prev - armc_step) < 1e-9:
                prev = armc_value
            else:
                windows.append(
                    ExperimentalPlacidusWindow(
                        start_armc=start,
                        end_armc=prev,
                        sample_count=int(round((prev - start) / armc_step)) + 1,
                    )
                )
                start = prev = armc_value
        windows.append(
            ExperimentalPlacidusWindow(
                start_armc=start,
                end_armc=prev,
                sample_count=int(round((prev - start) / armc_step)) + 1,
            )
        )

    total_samples = int(round((armc_end - armc_start) / armc_step)) + 1
    return ExperimentalPlacidusAdmissibilityMap(
        latitude=latitude,
        obliquity=obliquity,
        armc_start=armc_start,
        armc_end=armc_end,
        armc_step=armc_step,
        sample_count=sample_count,
        valid_armcs=tuple(valid_armcs),
        windows=tuple(windows),
        total_samples=total_samples,
    )