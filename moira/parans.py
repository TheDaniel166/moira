"""
Moira — Paran Engine
=====================

Archetype: Engine

Purpose
-------
Governs detection of paranatellonta (parans) — simultaneous horizon and
meridian circle crossings between two celestial bodies as seen from a
geographic location on a given day.

Boundary declaration
--------------------
Owns: paran detection logic, crossing-time collection, time-orb comparison,
      ``ParanCrossing`` and ``Paran`` result vessels.
Delegates: rise/set time computation to ``moira.rise_set``,
           transit time computation to ``moira.rise_set.get_transit``,
           Julian Day conversion to ``moira.julian``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Requires caller to supply
body names resolvable by ``moira.rise_set`` and a valid geographic location.

Public surface
--------------
``ParanCrossing``  — vessel for a single mundane circle crossing event.
``Paran``          — vessel for a paran aspect between two bodies.
``CIRCLE_TYPES``   — tuple of the four mundane circle names.
``find_parans``    — find all parans for a list of bodies on a given day.
``natal_parans``   — convenience wrapper for natal-day parans.
"""


import math
import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .constants import DEG2RAD, RAD2DEG


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CIRCLE_TYPES = ("Rising", "Setting", "Culminating", "AntiCulminating")

# Minutes → fractional JD conversion factor
_MINUTES_TO_JD = 1.0 / (24.0 * 60.0)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ParanCrossing:
    """
    RITE: The Crossing Witness — a single moment of mundane circle passage.

    THEOREM: Holds the body name, circle type, and Julian Day of a single
    instance where a celestial body crosses one of the four mundane circles
    (Rising, Setting, Culminating, AntiCulminating).

    RITE OF PURPOSE:
        Serves the Paran Engine as the atomic unit of paran detection. Every
        paran is formed by pairing two ``ParanCrossing`` instances whose times
        fall within the orb. Without this vessel, the crossing-time collection
        step would have no structured representation, making paran matching
        impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store the body name, circle type string, and crossing JD.
            - Expose ``datetime_utc`` and ``calendar_utc`` computed properties
              for human-readable time access.
        Non-responsibilities:
            - Does not compute crossing times (delegated to ``_crossing_times``).
            - Does not validate that ``circle`` is one of ``CIRCLE_TYPES``.
        Dependencies:
            - ``datetime_utc`` delegates to ``moira.julian.datetime_from_jd``.
            - ``calendar_utc`` delegates to ``moira.julian.calendar_datetime_from_jd``.
        Structural invariants:
            - ``circle`` is always one of "Rising", "Setting", "Culminating",
              "AntiCulminating".
        Succession stance: terminal — not designed for subclassing.

    Canon: Brady, "Brady's Book of Fixed Stars" (1998); Ptolemy, Tetrabiblos I.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.parans.ParanCrossing",
        "risk": "low",
        "api": {
            "public_methods": ["datetime_utc", "calendar_utc", "__repr__"],
            "public_attributes": ["body", "circle", "jd"]
        },
        "state": {
            "mutable": false,
            "fields": ["body", "circle", "jd"]
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller ensures valid JD before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]

    Attributes
    ----------
    body   : name of the celestial body.
    circle : one of ``"Rising"``, ``"Setting"``, ``"Culminating"``,
             ``"AntiCulminating"``.
    jd     : Julian Day (UT) of the crossing.
    """

    body:   str
    circle: str    # "Rising", "Setting", "Culminating", "AntiCulminating"
    jd:     float  # JD of the crossing (UT)

    @property
    def datetime_utc(self) -> datetime:
        """Return the crossing time as a timezone-aware UTC datetime."""
        from .julian import datetime_from_jd
        return datetime_from_jd(self.jd)

    @property
    def calendar_utc(self):
        """Return the crossing time as a BCE-safe UTC calendar object."""
        from .julian import calendar_datetime_from_jd
        return calendar_datetime_from_jd(self.jd)

    def __repr__(self) -> str:
        return (
            f"ParanCrossing({self.body!r}, {self.circle!r}, "
            f"jd={self.jd:.6f})"
        )


@dataclass(slots=True)
class Paran:
    """
    RITE: The Paran Vessel — a simultaneous mundane circle crossing between two bodies.

    THEOREM: Holds the two body names, their respective circle types, the
    average Julian Day of the crossing pair, and the time orb in minutes.

    RITE OF PURPOSE:
        Serves the Paran Engine as the canonical result vessel for detected
        paran aspects. A paran is the astrological event formed when two bodies
        cross any two mundane circles within a time orb. Without this vessel,
        ``find_parans`` would have no structured output, and callers could not
        filter, sort, or display paran results.

    LAW OF OPERATION:
        Responsibilities:
            - Store both body names, their circle types, the average JD, and
              the time orb in minutes.
        Non-responsibilities:
            - Does not detect parans (delegated to ``find_parans``).
            - Does not validate that circle types are members of ``CIRCLE_TYPES``.
        Dependencies:
            - Populated exclusively by ``find_parans()``.
        Structural invariants:
            - ``orb_min`` is always non-negative.
            - ``jd`` is the arithmetic mean of the two crossing JDs.
        Succession stance: terminal — not designed for subclassing.

    Canon: Brady, "Brady's Book of Fixed Stars" (1998); Ptolemy, Tetrabiblos I.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.parans.Paran",
        "risk": "medium",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": ["body1", "body2", "circle1", "circle2", "jd", "orb_min"]
        },
        "state": {
            "mutable": false,
            "fields": ["body1", "body2", "circle1", "circle2", "jd", "orb_min"]
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller ensures valid crossing data before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]

    Attributes
    ----------
    body1    : name of the first body.
    body2    : name of the second body.
    circle1  : mundane circle for *body1* (one of :data:`CIRCLE_TYPES`).
    circle2  : mundane circle for *body2* (one of :data:`CIRCLE_TYPES`).
    jd       : average JD (UT) of the two crossings.
    orb_min  : time separation of the two crossings in minutes.
    """

    body1:   str
    body2:   str
    circle1: str    # mundane circle for body1
    circle2: str    # mundane circle for body2
    jd:      float  # average JD of the two crossings (UT)
    orb_min: float  # time orb in minutes (always positive)

    def __repr__(self) -> str:
        return (
            f"Paran({self.body1!r} {self.circle1} ∥ "
            f"{self.body2!r} {self.circle2}, "
            f"orb={self.orb_min:.1f}′)"
        )


# ---------------------------------------------------------------------------
# Internal: find all four crossings for a single body on a given day
# ---------------------------------------------------------------------------

def _crossing_times(
    body: str,
    jd_day: float,
    lat: float,
    lon: float,
) -> list[ParanCrossing]:
    """
    Find all four mundane circle crossings for *body* on the day starting
    at *jd_day*, as seen from the observer at (``lat``, ``lon``).

    The four crossings are:

    - **Rising** — body crosses the eastern horizon (altitude = 0°,
      ascending);
    - **Setting** — body crosses the western horizon (altitude = 0°,
      descending);
    - **Culminating** — body crosses the upper meridian (LST = RA);
    - **AntiCulminating** — body crosses the lower meridian
      (approximately Culminating + 0.5 day).

    Parameters
    ----------
    body    : body name (one of the ``Body.*`` constants).
    jd_day  : Julian Day (UT) at the start of the search window (i.e. the
              integer JD at 00:00 UT or the natal JD floored to the day).
    lat     : observer geographic latitude (degrees, signed).
    lon     : observer geographic longitude (degrees, east positive).

    Returns
    -------
    list[ParanCrossing] — up to four entries (fewer if the body is
    circumpolar or never rises at the given latitude).
    """
    from .rise_set import find_phenomena, get_transit

    crossings: list[ParanCrossing] = []

    # Rise and Set via find_phenomena().
    # Use the standard stellar refraction altitude (-0.5667°).
    phenomena = find_phenomena(body, jd_day, lat, lon, altitude=-0.5667)

    if "Rise" in phenomena:
        crossings.append(
            ParanCrossing(body=body, circle="Rising", jd=phenomena["Rise"])
        )
    if "Set" in phenomena:
        crossings.append(
            ParanCrossing(body=body, circle="Setting", jd=phenomena["Set"])
        )

    # Upper transit (Culminating) via get_transit().
    try:
        jd_transit = get_transit(body, jd_day, lat, lon)
        crossings.append(
            ParanCrossing(body=body, circle="Culminating", jd=jd_transit)
        )
        # Anti-culmination (lower transit) should be solved explicitly on the
        # same search day. Re-seeding get_transit() with jd_transit + 0.49 and
        # leaving upper=True can wrap the answer into the next sidereal day.
        try:
            jd_anti = get_transit(body, jd_day, lat, lon, upper=False)
            crossings.append(
                ParanCrossing(body=body, circle="AntiCulminating", jd=jd_anti)
            )
        except Exception:
            pass
    except Exception:
        # get_transit() can fail for bodies near the pole; skip gracefully.
        pass

    return crossings


# ---------------------------------------------------------------------------
# Main paran-finding function
# ---------------------------------------------------------------------------

def find_parans(
    bodies: list[str],
    jd_day: float,
    lat: float,
    lon: float,
    orb_minutes: float = 4.0,
) -> list[Paran]:
    """
    Find all parans between the given bodies for a given day and location.

    A paran is detected whenever two crossing times (one for each body) fall
    within *orb_minutes* of each other, regardless of which circles are
    involved.  Both "same circle" parans (e.g. both Rising) and "mixed
    circle" parans (e.g. one Rising while the other Culminates) are returned.

    Parameters
    ----------
    bodies      : list of body names to check (e.g. ``Body.ALL_PLANETS``).
    jd_day      : Julian Day (UT) of the day to search.  The function looks
                  over the full 24-hour window starting at this JD.
    lat         : observer geographic latitude (degrees, signed).
    lon         : observer geographic longitude (degrees, east positive).
    orb_minutes : maximum time separation (in minutes) for two crossings to
                  qualify as a paran.  Default 4 minutes (traditional orb).

    Returns
    -------
    list[Paran] sorted by ``orb_min`` (tightest paran first).

    Notes
    -----
    The function does *not* deduplicate symmetric pairs — i.e., the paran
    "Sun Rising ∥ Moon Culminating" and "Moon Culminating ∥ Sun Rising" are
    the same event and will appear only once (body order follows the input
    *bodies* list via :func:`itertools.combinations`).
    """
    orb_jd = orb_minutes * _MINUTES_TO_JD

    # Gather all crossings for every body.
    all_crossings: list[ParanCrossing] = []
    for body in bodies:
        all_crossings.extend(_crossing_times(body, jd_day, lat, lon))

    parans: list[Paran] = []

    # Compare every crossing of body A against every crossing of body B
    # (each unordered pair of distinct bodies).
    body_crossings: dict[str, list[ParanCrossing]] = {}
    for c in all_crossings:
        body_crossings.setdefault(c.body, []).append(c)

    for body_a, body_b in itertools.combinations(bodies, 2):
        crossings_a = body_crossings.get(body_a, [])
        crossings_b = body_crossings.get(body_b, [])

        for ca in crossings_a:
            for cb in crossings_b:
                dt_jd = abs(ca.jd - cb.jd)
                if dt_jd <= orb_jd:
                    orb_min = dt_jd / _MINUTES_TO_JD
                    avg_jd  = (ca.jd + cb.jd) / 2.0
                    parans.append(
                        Paran(
                            body1=body_a,
                            body2=body_b,
                            circle1=ca.circle,
                            circle2=cb.circle,
                            jd=avg_jd,
                            orb_min=orb_min,
                        )
                    )

    parans.sort(key=lambda p: p.orb_min)
    return parans


# ---------------------------------------------------------------------------
# Natal parans convenience function
# ---------------------------------------------------------------------------

def natal_parans(
    bodies: list[str],
    natal_jd: float,
    lat: float,
    lon: float,
    orb_minutes: float = 4.0,
) -> list[Paran]:
    """
    Find natal parans — the parans active on the birth day.

    This is a thin wrapper around :func:`find_parans` that floors the natal
    Julian Day to the start of the birth day (00:00 UT) before searching,
    ensuring the full 24-hour window of the birth date is examined.

    Parameters
    ----------
    bodies      : list of body names to check.
    natal_jd    : Julian Day (UT) of the birth moment.
    lat         : birth location geographic latitude (degrees, signed).
    lon         : birth location geographic longitude (degrees, east positive).
    orb_minutes : time orb in minutes.  Default 4 minutes.

    Returns
    -------
    list[Paran] sorted by ``orb_min`` (tightest paran first).
    """
    # Floor to the start of the UT day (JD noon convention: subtract 0.5,
    # floor, add 0.5 back so the window begins at 00:00 UT).
    jd_day = math.floor(natal_jd - 0.5) + 0.5
    return find_parans(bodies, jd_day, lat, lon, orb_minutes=orb_minutes)
