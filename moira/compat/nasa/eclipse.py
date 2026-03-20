"""
NASA Eclipse Compatibility Gate — moira/compat/nasa/eclipse.py

Archetype: Gate
Purpose: Translates Moira's native lunar eclipse outputs into the contact-time
         and geometry parameterization used by NASA's eclipse canon, enabling
         direct comparison against NASA published tables.

Boundary declaration
--------------------
Owns:
    - NasaLunarEclipseContacts frozen dataclass (NASA-parameterized contacts).
    - NasaLunarEclipseEvent frozen dataclass (full NASA-style event record).
    - translate_lunar_eclipse_event() — single-event translation entry point.
    - next_nasa_lunar_eclipse() / previous_nasa_lunar_eclipse() — search API.
    - _translate_contacts() — internal contact struct adapter.
Delegates:
    - Eclipse search and EclipseEvent production to moira.eclipse.EclipseCalculator.
    - Canon geometry (gamma, magnitudes) to moira.eclipse_canon.lunar_canon_geometry.
    - Contact timing to moira.eclipse_canon.find_lunar_contacts_canon.
    - TT conversion to moira.julian.ut_to_tt_nasa_canon.

Import-time side effects: None.

External dependency assumptions:
    - de441.bsp must be loadable before any search function is called.
    - No Qt, no database, no OS threads.

Public surface / exports:
    NasaLunarEclipseContacts
    NasaLunarEclipseEvent
    translate_lunar_eclipse_event()
    next_nasa_lunar_eclipse()
    previous_nasa_lunar_eclipse()
"""

from dataclasses import dataclass

from ...eclipse import EclipseCalculator, EclipseEvent
from ...eclipse_canon import (
    DEFAULT_LUNAR_CANON_METHOD,
    LunarCanonContacts,
    LunarCanonGeometry,
    find_lunar_contacts_canon,
    lunar_canon_source_model,
    lunar_canon_geometry,
    refine_lunar_greatest_eclipse_canon_tt,
)
from ...julian import ut_to_tt_nasa_canon


@dataclass(frozen=True, slots=True)
class NasaLunarEclipseContacts:
    """
    RITE: Gate of Contact Times

    THEOREM: Frozen dataclass holding the seven NASA-parameterized contact
             timestamps (UT) for a single lunar eclipse event.

    RITE OF PURPOSE:
        NASA eclipse tables express lunar eclipse timing through a canonical
        set of seven contact moments: penumbral ingress (P1), umbral ingress
        (U1), total ingress (U2), greatest eclipse, total egress (U3), umbral
        egress (U4), and penumbral egress (P4). This dataclass carries exactly
        that parameterization so Moira outputs can be compared against NASA
        published tables without ambiguity. Without it, callers would have to
        manually map Moira's native contact model to NASA's naming convention.

    LAW OF OPERATION:
        Responsibilities:
            - Hold the seven NASA contact timestamps as UT Julian Day floats.
            - Represent partial and penumbral eclipses correctly via None for
              contacts that do not occur (e.g. U2/U3 absent for partial events).
        Non-responsibilities:
            - Does not compute contact times; all values are injected at
              construction by translate_lunar_eclipse_event() or the search API.
            - Does not validate physical consistency of the contact sequence.
        Dependencies:
            - None; pure frozen data vessel.
        Structural invariants:
            - greatest_ut is always non-None (every eclipse has a greatest moment).
            - p1_ut and p4_ut are None only for umbral-only events (rare edge case).
        Failure behavior:
            - dataclass(frozen=True) raises FrozenInstanceError on mutation attempt.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.compat.nasa.eclipse.NasaLunarEclipseContacts",
        "risk": "high",
        "api": {
            "inputs": ["p1_ut", "u1_ut", "u2_ut", "greatest_ut", "u3_ut", "u4_ut", "p4_ut"],
            "outputs": ["frozen dataclass instance"]
        },
        "state": "stateless",
        "effects": {
            "io": [],
            "signals_emitted": [],
            "mutations": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": ["FrozenInstanceError on mutation attempt"],
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    p1_ut: float | None
    u1_ut: float | None
    u2_ut: float | None
    greatest_ut: float
    u3_ut: float | None
    u4_ut: float | None
    p4_ut: float | None


@dataclass(frozen=True, slots=True)
class NasaLunarEclipseEvent:
    """
    RITE: Gate of the Eclipse Record

    THEOREM: Frozen dataclass holding the complete NASA-parameterized record
             for a single lunar eclipse, including geometry, magnitudes, contact
             times, the originating Moira event, and the canon method used.

    RITE OF PURPOSE:
        NASA eclipse publications report each lunar eclipse through a fixed set
        of parameters: UT and TT epochs, gamma (shadow axis distance in Earth
        radii), umbral and penumbral magnitudes, and the seven contact times.
        This dataclass packages all of those fields alongside the native Moira
        EclipseEvent so callers retain full traceability back to the source
        computation. Without it, the compatibility layer would have no stable
        output contract and callers could not reliably compare Moira results
        against NASA tables.

    LAW OF OPERATION:
        Responsibilities:
            - Hold jd_ut, jd_tt, gamma, umbral magnitude, penumbral magnitude,
              NasaLunarEclipseContacts, the originating EclipseEvent, source
              model string, and canon method string.
            - Serve as the stable output type of next_nasa_lunar_eclipse(),
              previous_nasa_lunar_eclipse(), and translate_lunar_eclipse_event().
        Non-responsibilities:
            - Does not compute any values; all fields are injected at construction.
            - Does not validate physical consistency of geometry or magnitudes.
            - Does not expose Moira's internal eclipse classification directly
              (use moira_event.eclipse_type for that).
        Dependencies:
            - moira.eclipse.EclipseEvent (stored in moira_event field).
            - moira.compat.nasa.eclipse.NasaLunarEclipseContacts (contacts field).
        Failure behavior:
            - dataclass(frozen=True) raises FrozenInstanceError on mutation attempt.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.compat.nasa.eclipse.NasaLunarEclipseEvent",
        "risk": "high",
        "api": {
            "inputs": [
                "jd_ut", "jd_tt", "gamma_earth_radii", "umbral_magnitude",
                "penumbral_magnitude", "contacts", "moira_event",
                "source_model", "canon_method"
            ],
            "outputs": ["frozen dataclass instance"]
        },
        "state": "stateless",
        "effects": {
            "io": [],
            "signals_emitted": [],
            "mutations": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": ["FrozenInstanceError on mutation attempt"],
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    jd_ut: float
    jd_tt: float
    gamma_earth_radii: float
    umbral_magnitude: float
    penumbral_magnitude: float
    contacts: NasaLunarEclipseContacts
    moira_event: EclipseEvent
    source_model: str = lunar_canon_source_model(DEFAULT_LUNAR_CANON_METHOD)
    canon_method: str = DEFAULT_LUNAR_CANON_METHOD


def _translate_contacts(contacts: LunarCanonContacts) -> NasaLunarEclipseContacts:
    return NasaLunarEclipseContacts(
        p1_ut=contacts.p1_ut,
        u1_ut=contacts.u1_ut,
        u2_ut=contacts.u2_ut,
        greatest_ut=contacts.greatest_ut,
        u3_ut=contacts.u3_ut,
        u4_ut=contacts.u4_ut,
        p4_ut=contacts.p4_ut,
    )


def translate_lunar_eclipse_event(
    calculator: EclipseCalculator,
    event: EclipseEvent,
) -> NasaLunarEclipseEvent:
    """
    Translate a Moira lunar eclipse event into NASA-style canon parameters.
    """
    jd_tt = ut_to_tt_nasa_canon(event.jd_ut)
    geom: LunarCanonGeometry = lunar_canon_geometry(
        calculator,
        jd_tt,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    contacts = find_lunar_contacts_canon(
        calculator,
        event.jd_ut,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    return NasaLunarEclipseEvent(
        jd_ut=event.jd_ut,
        jd_tt=jd_tt,
        gamma_earth_radii=geom.gamma_earth_radii,
        umbral_magnitude=geom.umbral_magnitude,
        penumbral_magnitude=geom.penumbral_magnitude,
        contacts=_translate_contacts(contacts),
        moira_event=event,
        source_model=lunar_canon_source_model(DEFAULT_LUNAR_CANON_METHOD),
        canon_method=DEFAULT_LUNAR_CANON_METHOD,
    )


def next_nasa_lunar_eclipse(
    jd_start: float,
    *,
    kind: str = "any",
    calculator: EclipseCalculator | None = None,
) -> NasaLunarEclipseEvent:
    calc = calculator or EclipseCalculator()
    event = calc.next_lunar_eclipse_canon(jd_start, kind=kind)
    jd_tt = refine_lunar_greatest_eclipse_canon_tt(
        calc,
        event.jd_ut,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    geom: LunarCanonGeometry = lunar_canon_geometry(
        calc,
        jd_tt,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    contacts = find_lunar_contacts_canon(
        calc,
        event.jd_ut,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    return NasaLunarEclipseEvent(
        jd_ut=event.jd_ut,
        jd_tt=jd_tt,
        gamma_earth_radii=geom.gamma_earth_radii,
        umbral_magnitude=geom.umbral_magnitude,
        penumbral_magnitude=geom.penumbral_magnitude,
        contacts=_translate_contacts(contacts),
        moira_event=event,
        source_model=lunar_canon_source_model(DEFAULT_LUNAR_CANON_METHOD),
        canon_method=DEFAULT_LUNAR_CANON_METHOD,
    )


def previous_nasa_lunar_eclipse(
    jd_start: float,
    *,
    kind: str = "any",
    calculator: EclipseCalculator | None = None,
) -> NasaLunarEclipseEvent:
    calc = calculator or EclipseCalculator()
    event = calc.previous_lunar_eclipse_canon(jd_start, kind=kind)
    jd_tt = refine_lunar_greatest_eclipse_canon_tt(
        calc,
        event.jd_ut,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    geom: LunarCanonGeometry = lunar_canon_geometry(
        calc,
        jd_tt,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    contacts = find_lunar_contacts_canon(
        calc,
        event.jd_ut,
        method=DEFAULT_LUNAR_CANON_METHOD,
    )
    return NasaLunarEclipseEvent(
        jd_ut=event.jd_ut,
        jd_tt=jd_tt,
        gamma_earth_radii=geom.gamma_earth_radii,
        umbral_magnitude=geom.umbral_magnitude,
        penumbral_magnitude=geom.penumbral_magnitude,
        contacts=_translate_contacts(contacts),
        moira_event=event,
        source_model=lunar_canon_source_model(DEFAULT_LUNAR_CANON_METHOD),
        canon_method=DEFAULT_LUNAR_CANON_METHOD,
    )
