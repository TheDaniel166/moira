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

from dataclasses import dataclass

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
    """Scan [start, end] in steps of step_days and collect all sign-change roots of func."""
    roots: list[float] = []
    x = start
    fx = func(x)
    while x < end:
        nx = x + step_days
        fn = func(nx)
        if fx == 0.0 or fn == 0.0 or fx * fn < 0.0:
            roots.append(_bisect_root(func, x, nx))
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
    center_data = calculator.calculate_jd(center_jd)
    use_retarded_moon = center_data.is_lunar_eclipse

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
    start = greatest - window_days
    end = greatest + window_days

    p_roots = _find_roots(p_contact, start, end, step_days)
    u_roots = _find_roots(u_contact, start, end, step_days)
    t_roots = _find_roots(total_contact, start, end, step_days)

    return LunarEclipseContacts(
        p1=p_roots[0] if len(p_roots) >= 1 else None,
        u1=u_roots[0] if len(u_roots) >= 1 else None,
        u2=t_roots[0] if len(t_roots) >= 1 else None,
        greatest=greatest,
        u3=t_roots[1] if len(t_roots) >= 2 else None,
        u4=u_roots[1] if len(u_roots) >= 2 else None,
        p4=p_roots[1] if len(p_roots) >= 2 else None,
    )
