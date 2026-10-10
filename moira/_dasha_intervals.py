"""Full-axis subdivision and visible interval validation shared by Dashas."""

from __future__ import annotations

import math
from collections.abc import Iterator


def validate_interval(
    start: float, end: float, full_start: float | None, full_end: float | None
) -> None:
    """Unknown provenance is allowed only as a pair of absent full endpoints."""
    for index, value in enumerate((start, end, full_start, full_end)):
        if value is None and index >= 2:
            continue
        try:
            finite = math.isfinite(value)
        except (TypeError, OverflowError):
            finite = False
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not finite:
            raise ValueError("Dasha endpoints must be finite numbers without coercion")
    if not all(math.isfinite(x) for x in (start, end, end - start)) or start >= end:
        raise ValueError(
            "Dasha end_jd must be greater than start_jd with finite duration"
        )
    if (full_start is None) != (full_end is None):
        raise ValueError("full_start_jd and full_end_jd must be supplied together")
    if full_start is not None and full_end is not None:
        if (
            not all(
                math.isfinite(x) for x in (full_start, full_end, full_end - full_start)
            )
            or not full_start <= start < end <= full_end
        ):
            raise ValueError(
                "Full Dasha interval must be finite and contain the visible interval"
            )


def validate_child_interval(parent, child, *, tolerance: float) -> None:
    """Validate declared full provenance and the visible intersection.

    Absent full endpoints remain unknown legacy provenance. A known child
    still must clip to the visible parent; full containment can be checked
    only when both full intervals are declared.
    """
    validate_interval(child.start_jd, child.end_jd, child.full_start_jd, child.full_end_jd)
    if child.full_start_jd is None:
        return
    if parent.full_start_jd is not None and (
        child.full_start_jd < parent.full_start_jd - tolerance
        or child.full_end_jd > parent.full_end_jd + tolerance
    ):
        raise ValueError("Full Dasha child interval must be contained by its full parent")
    start = max(parent.start_jd, child.full_start_jd)
    end = min(parent.end_jd, child.full_end_jd)
    if (start >= end or abs(child.start_jd - start) > tolerance
            or abs(child.end_jd - end) > tolerance):
        raise ValueError("Dasha child visible interval must equal its full interval clipped to parent")


def subdivisions(
    start: float,
    end: float,
    full_start: float | None,
    full_end: float | None,
    weights: list[int],
) -> Iterator[tuple[int, float, float, float, float]]:
    """Partition the full parent first; intersect each child with visible time."""
    origin = start if full_start is None else full_start
    limit = end if full_end is None else full_end
    total = sum(weights)
    elapsed = 0
    left = origin
    for i, weight in enumerate(weights):
        elapsed += weight
        right = (
            limit
            if i == len(weights) - 1
            else origin + (limit - origin) * elapsed / total
        )
        if right <= left:
            raise ValueError("Dasha subdivision is below representable JD precision")
        lo, hi = max(start, left), min(end, right)
        if lo < hi:
            yield i, lo, hi, left, right
        left = right
