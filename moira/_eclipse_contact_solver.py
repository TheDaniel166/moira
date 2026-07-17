"""
Private numerical solver for one eclipse phase-contact pair.

The governing object is a signed mean-limb clearance around a known eclipse
maximum.  Negative clearance means overlap, positive clearance means
separation, and zero is contact.  The solver keeps ingress and egress as
independent sides so that a truncated search window cannot be mistaken for a
tangent contact.

This module owns numerical coalescence only.  It does not model lunar limb
topography, Baily's Beads, or observational uncertainty.
"""

from __future__ import annotations

import math
from collections.abc import Callable

_CONTACT_COALESCENCE_TOLERANCE_KM = 1.0e-6
_CONTACT_TIME_TOLERANCE_DAYS = 1.0e-7


def _bisect_contact_root(
    evaluate: Callable[[float], float],
    left: float,
    right: float,
    *,
    time_tolerance_days: float,
) -> float:
    """Refine one sign-bracketed contact without leaving its bounded side."""
    f_left = evaluate(left)
    f_right = evaluate(right)
    if f_left == 0.0:
        return left
    if f_right == 0.0:
        return right
    if (f_left < 0.0) == (f_right < 0.0):
        raise ValueError("contact root refinement requires a sign-changing bracket")

    for _ in range(100):
        if right - left <= time_tolerance_days:
            break
        midpoint = (left + right) / 2.0
        if midpoint <= left or midpoint >= right:
            break
        f_midpoint = evaluate(midpoint)
        if f_midpoint == 0.0:
            return midpoint
        if (f_left < 0.0) == (f_midpoint < 0.0):
            left, f_left = midpoint, f_midpoint
        else:
            right, f_right = midpoint, f_midpoint
    return (left + right) / 2.0


def _refine_bounded_minimum(
    evaluate: Callable[[float], float],
    left: float,
    right: float,
    *,
    seed: float,
    time_tolerance_days: float,
) -> tuple[float, float]:
    """Refine a sampled local minimum inside a finite, ordered bracket."""
    if left == right:
        return left, evaluate(left)

    inverse_phi = (math.sqrt(5.0) - 1.0) / 2.0
    a = left
    b = right
    c = b - inverse_phi * (b - a)
    d = a + inverse_phi * (b - a)
    f_c = evaluate(c)
    f_d = evaluate(d)

    for _ in range(100):
        if b - a <= time_tolerance_days:
            break
        if c <= a or d >= b or c >= d:
            break
        if f_c <= f_d:
            b = d
            d, f_d = c, f_c
            c = b - inverse_phi * (b - a)
            if c <= a or c >= d:
                break
            f_c = evaluate(c)
        else:
            a = c
            c, f_c = d, f_d
            d = a + inverse_phi * (b - a)
            if d <= c or d >= b:
                break
            f_d = evaluate(d)

    candidates = (left, right, seed, a, b, c, d, (a + b) / 2.0)
    bounded_candidates = tuple(
        candidate for candidate in candidates if left <= candidate <= right
    )
    minimum_jd = min(bounded_candidates, key=evaluate)
    return minimum_jd, evaluate(minimum_jd)


def _find_contact_pair(
    func: Callable[[float], float],
    start: float,
    end: float,
    step_days: float,
    *,
    greatest_jd: float,
    clearance_tolerance: float,
    time_tolerance_days: float = _CONTACT_TIME_TOLERANCE_DAYS,
) -> tuple[float | None, float | None]:
    """
    Solve ingress and egress for one signed eclipse phase clearance.

    A clearance minimum within ``clearance_tolerance`` of zero is a numerical
    mean-limb tangency and therefore returns the same instant for both sides.
    A meaningfully negative minimum is searched independently toward the two
    window boundaries; either side may remain ``None`` when the window is
    truncated.  A positive minimum beyond tolerance has no contacts.
    """
    values = (
        start,
        end,
        step_days,
        greatest_jd,
        clearance_tolerance,
        time_tolerance_days,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("contact-pair bounds, seed, and tolerances must be finite")
    if end <= start:
        raise ValueError("contact-pair end must be greater than start")
    if step_days <= 0.0:
        raise ValueError("contact-pair step_days must be greater than zero")
    if start + step_days <= start:
        raise ValueError("contact-pair step_days is too small to advance the scan")
    if not start <= greatest_jd <= end:
        raise ValueError("contact-pair greatest_jd must lie within the search window")
    if clearance_tolerance <= 0.0:
        raise ValueError("contact-pair clearance_tolerance must be greater than zero")
    if time_tolerance_days <= 0.0:
        raise ValueError("contact-pair time_tolerance_days must be greater than zero")

    effective_time_tolerance = max(
        time_tolerance_days,
        8.0 * max(math.ulp(start), math.ulp(end), math.ulp(greatest_jd)),
    )
    cache: dict[float, float] = {}

    def evaluate(jd: float) -> float:
        if jd not in cache:
            value = func(jd)
            if not math.isfinite(value):
                raise ValueError("contact-pair function returned a non-finite value")
            cache[jd] = value
        return cache[jd]

    scan_points = [start]
    x = start
    while x < end:
        next_x = min(end, x + step_days)
        if next_x <= x:
            raise ValueError("contact-pair step_days is too small to advance the scan")
        scan_points.append(next_x)
        x = next_x
    scan_points.append(greatest_jd)
    scan_points = sorted(set(scan_points))
    scan_values = [evaluate(point) for point in scan_points]
    if scan_values and all(value == 0.0 for value in scan_values):
        raise ValueError("contact-pair function is a constant zero plateau")

    sampled_minimum_index = min(
        range(len(scan_points)),
        key=lambda index: scan_values[index],
    )
    sampled_minimum = scan_points[sampled_minimum_index]
    minimum_left = scan_points[max(0, sampled_minimum_index - 1)]
    minimum_right = scan_points[
        min(len(scan_points) - 1, sampled_minimum_index + 1)
    ]
    minimum_jd, minimum_clearance = _refine_bounded_minimum(
        evaluate,
        minimum_left,
        minimum_right,
        seed=sampled_minimum,
        time_tolerance_days=effective_time_tolerance,
    )

    if minimum_clearance > clearance_tolerance:
        return None, None
    if abs(minimum_clearance) <= clearance_tolerance:
        if minimum_jd == start:
            return start, None
        if minimum_jd == end:
            return None, end
        return minimum_jd, minimum_jd

    augmented_points = sorted(set((*scan_points, minimum_jd)))
    minimum_index = augmented_points.index(minimum_jd)

    ingress: float | None = None
    inner = minimum_jd
    inner_clearance = minimum_clearance
    for outer in reversed(augmented_points[:minimum_index]):
        outer_clearance = evaluate(outer)
        if outer_clearance == 0.0:
            ingress = outer
            break
        if outer_clearance > 0.0 and inner_clearance < 0.0:
            ingress = _bisect_contact_root(
                evaluate,
                outer,
                inner,
                time_tolerance_days=effective_time_tolerance,
            )
            break
        inner = outer
        inner_clearance = outer_clearance

    egress: float | None = None
    inner = minimum_jd
    inner_clearance = minimum_clearance
    for outer in augmented_points[minimum_index + 1 :]:
        outer_clearance = evaluate(outer)
        if outer_clearance == 0.0:
            egress = outer
            break
        if outer_clearance > 0.0 and inner_clearance < 0.0:
            egress = _bisect_contact_root(
                evaluate,
                inner,
                outer,
                time_tolerance_days=effective_time_tolerance,
            )
            break
        inner = outer
        inner_clearance = outer_clearance

    return ingress, egress
