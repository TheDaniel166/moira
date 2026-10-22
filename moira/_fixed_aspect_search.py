"""Private bounded search of one admitted mover against fixed longitudes.

The caller owns body admission, time/frame provenance, and coverage. One
canonical longitude memo and stationary-point scan serve every target.
Completeness means completion of the declared finite scan, not an enclosure
proof that an arbitrary function has no additional roots between samples.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _FixedScanPolicy:
    """Explicit finite scan, root, angular and work controls."""

    step_days: float
    time_tolerance_days: float
    angular_tolerance_deg: float
    curvature_tolerance_deg: float
    max_evaluations: int
    max_subdivisions: int
    max_depth: int
    velocity_step_days: float
    stationary_rate_tolerance: float


@dataclass(frozen=True, slots=True)
class _FixedPass:
    """One isolated exact root and its directed branch and motion witness."""

    target_index: int
    jd_ut1: float
    directed_angle_deg: float
    motion: str
    residual_deg: float


@dataclass(frozen=True, slots=True)
class _FixedWindow:
    """Connected directed-branch orb interval, including clipped boundaries."""

    target_index: int
    start: float
    end: float
    entry_status: str
    exit_status: str


@dataclass(frozen=True, slots=True)
class _FixedScanResult:
    """Finite scan result, immutable evidence and explicit incompleteness."""

    passes: tuple[_FixedPass, ...]
    windows: tuple[_FixedWindow, ...]
    evaluations: int
    subdivisions: int
    complete: bool
    reasons: tuple[str, ...]
    scanned_intervals: tuple[tuple[float, float], ...]


class _ScanBudgetExhausted(RuntimeError):
    """Private control signal; never converted into a successful empty scan."""


def _delta(a, b):
    return (a - b + 180.0) % 360.0 - 180.0


def _bisect_scalar(function, low, high, time_tolerance, value_tolerance):
    """Refine a bracket without crossing a circular discontinuity."""
    flo, fhi = function(low), function(high)
    if flo == 0:
        return low
    if fhi == 0:
        return high
    if flo * fhi > 0:
        raise ValueError("root is not bracketed")
    for _ in range(90):
        middle = low / 2 + high / 2
        fm = function(middle)
        if abs(fm) <= value_tolerance and high - low <= time_tolerance:
            return middle
        if middle in (low, high):
            if abs(fm) <= value_tolerance:
                return middle
            raise ValueError("root below time representation or angular tolerance")
        if flo * fm <= 0:
            high, fhi = middle, fm
        else:
            low, flo = middle, fm
    raise ValueError("root refinement did not converge")


def _scan_fixed_aspects(evaluator, targets, intervals, policy):
    """Search directed ``(longitude, angle, orb)`` targets on covered intervals.

    Each interval is ``(start, end, start_clip_status, end_clip_status)``.
    Root and orb searches never leave it. Stationary touches are accepted
    only after refining a zero of the finite-difference angular velocity and
    verifying the exact residual. Unresolved extrema are reported explicitly.
    """
    cache = {}
    subdivisions = 0
    reasons = set()
    passes, windows, scanned = [], [], []

    def longitude(jd):
        if jd not in cache:
            if len(cache) >= policy.max_evaluations:
                raise _ScanBudgetExhausted
            value = float(evaluator(jd))
            if not math.isfinite(value):
                raise ValueError("canonical mover returned nonfinite longitude")
            cache[jd] = value % 360.0
        return cache[jd]

    for low, high, start_clip, end_clip in intervals:
        interval_passes, interval_windows = [], []
        try:
            ratio = (high - low) / policy.step_days
            if not math.isfinite(ratio) or ratio > policy.max_evaluations:
                raise _ScanBudgetExhausted
            count = max(1, math.ceil(ratio))
            if count * 2 + 1 > policy.max_evaluations - len(cache):
                raise _ScanBudgetExhausted
            knots = {low, high}
            pending = [(low + (high - low) * i / count, low + (high - low) * (i + 1) / count, 0) for i in range(count)]
            while pending:
                a, b, depth = pending.pop()
                m = a / 2 + b / 2
                va, vm, vb = longitude(a), longitude(m), longitude(b)
                knots.update((a, m, b))
                first, second = _delta(vm, va), _delta(vb, vm)
                ambiguous = max(abs(first), abs(second)) >= 45 or abs(second - first) > policy.curvature_tolerance_deg
                if ambiguous:
                    if depth >= policy.max_depth or m in (a, b):
                        reasons.add("subdivision_depth_exhausted")
                    elif subdivisions >= policy.max_subdivisions:
                        raise _ScanBudgetExhausted
                    else:
                        subdivisions += 1
                        pending.extend(((a, m, depth + 1), (m, b, depth + 1)))
            times = sorted(knots)

            def velocity(t):
                h = min(policy.velocity_step_days, (high - low) / 4)
                if t + h == t or t - h == t:
                    raise ValueError("interval too small for motion witness")
                if t - h < low:
                    return (4 * _delta(longitude(t + h), longitude(t)) - _delta(longitude(t + 2 * h), longitude(t))) / (2 * h)
                if t + h > high:
                    return (-4 * _delta(longitude(t - h), longitude(t)) + _delta(longitude(t - 2 * h), longitude(t))) / (2 * h)
                return _delta(longitude(t + h), longitude(t - h)) / (2 * h)

            # Secant slopes can have the same sign even when an extremum
            # lies near a cell edge and two roots occur before its midpoint.
            # Bracket the velocity itself at every knot, including endpoints.
            rates = {t: velocity(t) for t in times}
            brackets = [(a, b) for a, b in zip(times, times[1:])
                        if rates[a] * rates[b] <= 0 and rates[a] != rates[b]
                        and max(abs(rates[a]), abs(rates[b])) > policy.stationary_rate_tolerance]
            for a, m, b in zip(times, times[1:], times[2:]):
                left = _delta(longitude(m), longitude(a)) / (m - a)
                right = _delta(longitude(b), longitude(m)) / (b - m)
                if left * right <= 0 and left != right and max(abs(left), abs(right)) > policy.stationary_rate_tolerance:
                    if any(a <= low and high <= b for low, high in brackets):
                        continue
                    if rates[a] * rates[b] <= 0:
                        brackets.append((a, b))
                    else:
                        reasons.add("unresolved_extremum")
            stationary = []
            for a, b in brackets:
                try:
                    root = _bisect_scalar(velocity, a, b, policy.time_tolerance_days, policy.stationary_rate_tolerance)
                except ValueError:
                    reasons.add("unresolved_extremum")
                    continue
                if not any(abs(root - t) <= 4 * policy.time_tolerance_days for t in stationary):
                    stationary.append(root)
                    knots.add(root)
            times = sorted(knots)

            for target_index, (target, angle, orb) in enumerate(targets):
                anchor = (target + angle) % 360

                def residual(t):
                    return _delta(longitude(t), anchor)

                roots = []
                near_continuous = set()
                for a, b in zip(times, times[1:]):
                    if abs(residual(a)) <= policy.angular_tolerance_deg and abs(residual(b)) <= policy.angular_tolerance_deg:
                        near_continuous.update((a, b))
                if near_continuous:
                    reasons.add("unresolved_near_continuous_contact")
                for index, t in enumerate(times):
                    value = residual(t)
                    if t in near_continuous or abs(value) > policy.angular_tolerance_deg:
                        continue
                    if value == 0:
                        roots.append(t)
                        continue
                    is_extremum = any(abs(t - s) <= 4 * policy.time_tolerance_days for s in stationary)
                    adjacent_crossing = ((index > 0 and residual(times[index - 1]) * value < 0)
                                         or (index + 1 < len(times) and residual(times[index + 1]) * value < 0))
                    if is_extremum and not adjacent_crossing:
                        roots.append(t)
                    elif t in (low, high):
                        # An endpoint is accepted only within both declared
                        # angular and local timing tolerances. Ordinary near-
                        # zero interior samples are refined by their bracket,
                        # not emitted as extra exact passes.
                        rate = abs(velocity(t))
                        if abs(value) <= rate * policy.time_tolerance_days or rate <= policy.stationary_rate_tolerance:
                            roots.append(t)
                for a, b in zip(times, times[1:]):
                    fa, fb = residual(a), residual(b)
                    if fa * fb < 0 and abs(fb - fa) < 180:
                        try:
                            roots.append(_bisect_scalar(residual, a, b, policy.time_tolerance_days, policy.angular_tolerance_deg))
                        except ValueError:
                            reasons.add("unresolved_exact_root")
                roots.sort()
                unique = []
                for root in roots:
                    if not unique or root - unique[-1] > 4 * policy.time_tolerance_days:
                        unique.append(root)
                for root in unique:
                    rate = velocity(root)
                    motion = "stationary" if abs(rate) <= policy.stationary_rate_tolerance else "direct" if rate > 0 else "retrograde"
                    interval_passes.append(_FixedPass(target_index, root, angle, motion, abs(residual(root))))

                if orb == 0:
                    interval_windows.extend(_FixedWindow(target_index, t, t, "found", "found") for t in unique)
                    continue

                def orb_residual(t):
                    return abs(residual(t)) - orb

                boundaries = {low, high}
                verified_boundaries = set()
                for index, t in enumerate(times):
                    value = orb_residual(t)
                    if abs(value) > policy.angular_tolerance_deg:
                        continue
                    adjacent_crossing = ((index > 0 and orb_residual(times[index - 1]) * value < 0)
                                         or (index + 1 < len(times) and orb_residual(times[index + 1]) * value < 0))
                    is_extremum = any(abs(t - s) <= 4 * policy.time_tolerance_days for s in stationary)
                    endpoint_close = t in (low, high) and (abs(value) <= abs(velocity(t)) * policy.time_tolerance_days or abs(velocity(t)) <= policy.stationary_rate_tolerance)
                    if value == 0 or (is_extremum and not adjacent_crossing) or endpoint_close:
                        boundaries.add(t)
                        verified_boundaries.add(t)
                for a, b in zip(times, times[1:]):
                    fa, fb = orb_residual(a), orb_residual(b)
                    if fa * fb < 0:
                        try:
                            root = _bisect_scalar(orb_residual, a, b, policy.time_tolerance_days, policy.angular_tolerance_deg)
                            boundaries.add(root)
                            verified_boundaries.add(root)
                        except ValueError:
                            reasons.add("unresolved_orb_boundary")
                ordered = sorted(boundaries)
                pieces = [(a, b) for a, b in zip(ordered, ordered[1:]) if orb_residual(a / 2 + b / 2) <= 0]
                # Retain isolated tangent contacts with the orb boundary too.
                pieces.extend((t, t) for t in verified_boundaries)
                merged = []
                for a, b in sorted(pieces):
                    if merged and a <= merged[-1][1] + policy.time_tolerance_days:
                        merged[-1] = (merged[-1][0], max(merged[-1][1], b))
                    else:
                        merged.append((a, b))
                for a, b in merged:
                    entry = start_clip if a == low and a not in verified_boundaries else "found"
                    exit_ = end_clip if b == high and b not in verified_boundaries else "found"
                    interval_windows.append(_FixedWindow(target_index, a, b, entry, exit_))
            passes.extend(interval_passes)
            windows.extend(interval_windows)
            scanned.append((low, high))
        except _ScanBudgetExhausted:
            reasons.add("search_budget_exhausted")
            break
    passes.sort(key=lambda p: (p.jd_ut1, p.target_index))
    windows.sort(key=lambda w: (w.start, w.target_index))
    return _FixedScanResult(tuple(passes), tuple(windows), len(cache), subdivisions,
                            not reasons, tuple(sorted(reasons)), tuple(scanned))
