"""
Moira — eclipse_contacts.py
The Contact Engine: governs lunar eclipse contact time solving for all seven
phase boundaries of a single lunar eclipse event.

Boundary: owns bisection root-finding and contact-time assembly. Delegates
shadow geometry to EclipseCalculator, and eclipse maximum refinement to
eclipse_search. Does not own shadow geometry computation, eclipse detection,
or any display formatting.

Public surface:
    LunarEclipseContacts, find_lunar_contacts

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._eclipse_contact_solver import (
    _CONTACT_COALESCENCE_TOLERANCE_KM,
    _find_contact_pair,
)
from .eclipse_search import refine_minimum

__all__ = ["LunarEclipseContacts", "find_lunar_contacts"]


@dataclass(frozen=True, slots=True)
class LunarEclipseContacts:
    """
    RITE: The Lunar Eclipse Contacts Vessel

    THEOREM: Governs the storage of the seven contact Julian Days for a single
    lunar eclipse.

    RITE OF PURPOSE:
        LunarEclipseContacts is the authoritative data vessel for all seven
        phase-boundary contact times of a lunar eclipse: penumbral ingress (P1),
        partial umbral ingress (U1), totality ingress (U2), greatest eclipse,
        totality egress (U3), partial umbral egress (U4), and penumbral egress
        (P4). Without it, callers would receive unstructured tuples with no
        field-level guarantees. It exists to give every higher-level consumer a
        single, named, immutable record of the eclipse timeline.

    LAW OF OPERATION:
        Responsibilities:
            - Store the seven contact Julian Days as named, typed fields
            - Permit None for contacts that do not occur (e.g. U2/U3 for a
              partial eclipse)
            - Serve as a read-only vessel passed between all higher-level
              consumers
        Non-responsibilities:
            - Computing contact times (delegates to find_lunar_contacts)
            - Performing shadow geometry (delegates to EclipseCalculator)
            - Converting Julian Days to calendar dates or display strings
        Dependencies:
            - Populated exclusively by find_lunar_contacts()
        Structural invariants:
            - greatest is always a finite float (the eclipse maximum is always
              defined)
            - p1, u1, u2, u3, u4, p4 are float | None depending on eclipse type
        Behavioral invariants:
            - All consumers treat LunarEclipseContacts as read-only after
              construction

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse_contacts.LunarEclipseContacts",
      "risk": "high",
      "api": {
        "frozen": ["p1", "u1", "u2", "greatest", "u3", "u4", "p4"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["find_lunar_contacts"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    p1: float | None
    u1: float | None
    u2: float | None
    greatest: float
    u3: float | None
    u4: float | None
    p4: float | None


def _bisect_root(func, a: float, b: float, iterations: int = 60) -> float:
    """Bisect to find a root of func in [a, b] to the given iteration depth."""
    fa = func(a)
    fb = func(b)
    for _ in range(iterations):
        m = (a + b) / 2.0
        fm = func(m)
        if fa == 0.0:
            return a
        if fb == 0.0:
            return b
        if fa * fm <= 0.0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    return (a + b) / 2.0


def _find_roots(func, start: float, end: float, step_days: float) -> list[float]:
    """Scan a finite ordered window and collect its distinct bracketed roots."""
    if not all(math.isfinite(value) for value in (start, end, step_days)):
        raise ValueError("root scan bounds and step_days must be finite")
    if end <= start:
        raise ValueError("root scan end must be greater than start")
    if step_days <= 0.0:
        raise ValueError("step_days must be greater than zero")

    roots: list[float] = []

    def evaluate(jd: float) -> float:
        value = func(jd)
        if not math.isfinite(value):
            raise ValueError("root scan function returned a non-finite value")
        return value

    x = start
    fx = evaluate(x)
    if fx == 0.0:
        roots.append(start)

    while x < end:
        nx = min(x + step_days, end)
        if nx <= x:
            raise ValueError("step_days is too small to advance within the root scan window")
        fn = evaluate(nx)

        root: float | None = None
        if fn == 0.0:
            root = nx
        elif fx != 0.0 and fx * fn < 0.0:
            root = _bisect_root(evaluate, x, nx)

        if root is not None:
            bounded_root = min(end, max(start, root))
            if not roots or bounded_root != roots[-1]:
                roots.append(bounded_root)
        x, fx = nx, fn
    return roots


def find_lunar_contacts(
    calculator,
    center_jd: float,
    *,
    window_days: float = 0.2,
    coarse_step_seconds: float = 60.0,
) -> LunarEclipseContacts:
    """
    Solve the lunar eclipse contact times around a candidate event maximum.

    Contacts are derived from the current Moira lunar geometry:
    - P1/P4: penumbral contacts
    - U1/U4: partial umbral contacts
    - U2/U3: totality contacts
    """
    if not math.isfinite(center_jd):
        raise ValueError("center_jd must be finite")
    if not math.isfinite(window_days) or window_days <= 0.0:
        raise ValueError("window_days must be finite and greater than zero")
    if not math.isfinite(coarse_step_seconds) or coarse_step_seconds <= 0.0:
        raise ValueError("coarse_step_seconds must be finite and greater than zero")

    initial_start = center_jd - window_days
    initial_end = center_jd + window_days
    if (
        not math.isfinite(initial_start)
        or not math.isfinite(initial_end)
        or initial_end <= initial_start
    ):
        raise ValueError("contact search window must have finite ordered bounds")

    center_data = calculator.calculate_jd(center_jd)
    # Astronomical event identity includes penumbral eclipses, but the native
    # contact vector policy remains family-specific: retarded Moon for umbral
    # partial/total events and geometric Moon for penumbral-only events.
    use_retarded_moon = (
        center_data.eclipse_type.is_partial
        or center_data.eclipse_type.is_total
    )

    greatest = refine_minimum(
        lambda jd: calculator._lunar_shadow_axis_distance_km(
            jd,
            retarded_moon=use_retarded_moon,
        ),
        center_jd,
        window_days=window_days,
        tol_days=1e-7,
        max_iter=100,
    )
    if not math.isfinite(greatest):
        raise ValueError("refined greatest eclipse must be finite")

    def p_contact(jd: float) -> float:
        axis, moon_r, _umb_r, pen_r, _moon_dist = calculator._lunar_event_geometry_ut(
            jd,
            retarded_moon=use_retarded_moon,
        )
        return axis - (pen_r + moon_r)

    def u_contact(jd: float) -> float:
        axis, moon_r, umb_r, _pen_r, _moon_dist = calculator._lunar_event_geometry_ut(
            jd,
            retarded_moon=use_retarded_moon,
        )
        return axis - (umb_r + moon_r)

    def total_contact(jd: float) -> float:
        axis, moon_r, umb_r, _pen_r, _moon_dist = calculator._lunar_event_geometry_ut(
            jd,
            retarded_moon=use_retarded_moon,
        )
        return axis - (umb_r - moon_r)

    step_days = coarse_step_seconds / 86400.0
    if step_days <= 0.0:
        raise ValueError("coarse_step_seconds is too small to form a positive day step")
    start = greatest - window_days
    end = greatest + window_days
    if not math.isfinite(start) or not math.isfinite(end) or end <= start:
        raise ValueError("refined contact search window must have finite ordered bounds")

    p1, p4 = _find_contact_pair(
        p_contact,
        start,
        end,
        step_days,
        greatest_jd=greatest,
        clearance_tolerance=_CONTACT_COALESCENCE_TOLERANCE_KM,
    )
    u1, u4 = _find_contact_pair(
        u_contact,
        start,
        end,
        step_days,
        greatest_jd=greatest,
        clearance_tolerance=_CONTACT_COALESCENCE_TOLERANCE_KM,
    )
    u2, u3 = _find_contact_pair(
        total_contact,
        start,
        end,
        step_days,
        greatest_jd=greatest,
        clearance_tolerance=_CONTACT_COALESCENCE_TOLERANCE_KM,
    )

    return LunarEclipseContacts(
        p1=p1,
        u1=u1,
        u2=u2,
        greatest=greatest,
        u3=u3,
        u4=u4,
        p4=p4,
    )
