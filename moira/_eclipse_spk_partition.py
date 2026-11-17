"""Disjoint binary64 input ledger for conditional SPK snapshot bounds.

Each cell owns a Cartesian set of representable finite input floats, not all
real points between the endpoints. Adjacent cells use consecutive floats;
the two signed zeros belong to the same numeric cell. Every admitted input is
owned by one resolved or explicitly unresolved cell, even on budget exhaustion.
The ledger does not certify live kernel immutability or the legacy evaluator.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from fractions import Fraction
import math

from ._eclipse_interval import IntervalDomainError, RationalInterval as I
from ._eclipse_spk_bounds import EclipseSpkBoundsUnavailable
from ._eclipse_variable_spk_bounds import (
    ConditionalVariableAnchorBounds, StrictScalarVariableAnchorBounds, strict_variable_anchor_type2_bounds,
)
from .spk_reader import SpkReader


@dataclass(frozen=True, slots=True)
class SpkSnapshotCell:
    """One disjoint float rectangle and its bound or reason for uncertainty."""

    anchor_days: I
    offset_days: I
    bounds: ConditionalVariableAnchorBounds | StrictScalarVariableAnchorBounds | None
    unresolved_reason: str | None


@dataclass(frozen=True, slots=True)
class SpkSnapshotLedger:
    """Complete ownership ledger; resolved cells remain conditional bounds."""

    anchor_days: I
    offset_days: I
    cells: tuple[SpkSnapshotCell, ...]
    evaluations: int
    binary64_input_coverage_complete: bool = True
    same_live_source_certified: bool = False
    legacy_evaluator_certified: bool = False

    @property
    def all_resolved(self) -> bool:
        """Whether every binary64 cell has a conditional snapshot bound."""
        return all(cell.bounds is not None for cell in self.cells)

    def owner(self, anchor_days: float, offset_days: float) -> SpkSnapshotCell:
        """Return the unique owner of an admitted finite binary64 pair."""
        if (type(anchor_days) is not float or type(offset_days) is not float
                or not math.isfinite(anchor_days) or not math.isfinite(offset_days)):
            raise ValueError("ownership requires finite binary64 float inputs")
        if not self.anchor_days.contains(anchor_days) or not self.offset_days.contains(offset_days):
            raise ValueError("input lies outside ledger domain")
        matches = [cell for cell in self.cells
                   if cell.anchor_days.contains(anchor_days) and cell.offset_days.contains(offset_days)]
        if len(matches) != 1:
            raise ArithmeticError("ledger ownership is missing or ambiguous")
        return matches[0]


def _binary64_domain(interval: I) -> I:
    """Round endpoints inward so no float outside the requested set is owned."""
    if not isinstance(interval, I):
        raise TypeError("TDB domains must be rational intervals")
    try:
        lo, hi = interval.to_float_bounds()
    except (IntervalDomainError, OverflowError) as exc:
        raise EclipseSpkBoundsUnavailable("finite binary64 domain unavailable") from exc
    if not math.isfinite(lo) or not math.isfinite(hi):
        raise EclipseSpkBoundsUnavailable("finite binary64 domain unavailable")
    if Fraction.from_float(lo) < interval.lo:
        lo = math.nextafter(lo, math.inf)
    if Fraction.from_float(hi) > interval.hi:
        hi = math.nextafter(hi, -math.inf)
    if not math.isfinite(lo) or not math.isfinite(hi) or lo > hi:
        raise EclipseSpkBoundsUnavailable("input domain contains no finite binary64 value")
    return I(lo, hi)


def _split_float_domain(domain: I) -> tuple[I, I] | None:
    lo, hi = float(domain.lo), float(domain.hi)
    if lo == hi:
        return None
    # Native floor has a whole-day branch at zero. A numeric bisection
    # across zero can otherwise need over a thousand subdivisions to reach
    # adjacent subnormal floats, exhausting a useful budget first.
    mid = math.nextafter(0.0, -math.inf) if lo < 0.0 <= hi else float((domain.lo + domain.hi) / 2)
    if mid < lo:
        mid = lo
    if mid >= hi:
        mid = math.nextafter(hi, -math.inf)
    right = math.nextafter(mid, math.inf)
    if not lo <= mid < right <= hi:
        raise ArithmeticError("could not partition binary64 inputs")
    return I(lo, mid), I(right, hi)


_SPLITTABLE_REASONS = (
    "requires subdivision", "requires split", "record interval exceeds budget",
    "native and exact-model record selection differ", "mathematical and native descriptor routes differ",
    "requested interval lies outside type-2 records",
)


def partition_variable_type2_snapshots(
    reader: SpkReader, center: int, target: int, anchor_days: I, offset_days: I,
    *, max_cells: int = 256, max_evaluations: int = 512, max_depth: int = 64,
) -> SpkSnapshotLedger:
    """Partition until each original-split branch resolves or reports a limit.

    Endpoints are restricted to finite binary64 values within the caller's
    rational domains. Unresolved point cells are retained, including cases
    where outward interval arithmetic cannot decide an exact descriptor seam.
    Each resolved cell carries its own copied-record/metadata digest. The
    returned ledger makes no assertion that the mapped kernel remained fixed
    between copies. Budgets count all attempted cells and bound result size.
    """
    if type(reader) is not SpkReader:
        raise EclipseSpkBoundsUnavailable("concrete SpkReader required")
    if (type(max_cells) is not int or not 1 <= max_cells <= 4096
            or type(max_evaluations) is not int or not 1 <= max_evaluations <= 8191
            or type(max_depth) is not int or not 0 <= max_depth <= 256):
        raise ValueError("invalid SPK partition resource budget")
    domain_anchor, domain_offset = _binary64_domain(anchor_days), _binary64_domain(offset_days)
    queue = deque([(domain_anchor, domain_offset, 0)])
    leaves: list[SpkSnapshotCell] = []
    evaluations = 0
    while queue:
        anchor, offset, depth = queue.popleft()
        if evaluations >= max_evaluations:
            leaves.append(SpkSnapshotCell(anchor, offset, None, "evaluation budget exhausted"))
            continue
        evaluations += 1
        try:
            result = strict_variable_anchor_type2_bounds(reader, center, target, anchor, offset)
        except EclipseSpkBoundsUnavailable as exc:
            reason = str(exc)
            if not any(text in reason for text in _SPLITTABLE_REASONS):
                leaves.append(SpkSnapshotCell(anchor, offset, None, reason))
                continue
            if depth >= max_depth or len(leaves) + len(queue) + 2 > max_cells:
                leaves.append(SpkSnapshotCell(anchor, offset, None, "partition budget exhausted: " + reason))
                continue
            axes = ((anchor, True), (offset, False)) if anchor.width >= offset.width else ((offset, False), (anchor, True))
            for domain, is_anchor in axes:
                parts = _split_float_domain(domain)
                if parts is not None:
                    for part in parts:
                        queue.append((part if is_anchor else anchor, offset if is_anchor else part, depth + 1))
                    break
            else:
                leaves.append(SpkSnapshotCell(anchor, offset, None, "singleton branch unresolved: " + reason))
        else:
            leaves.append(SpkSnapshotCell(anchor, offset, result, None))
    return SpkSnapshotLedger(domain_anchor, domain_offset, tuple(leaves), evaluations)
