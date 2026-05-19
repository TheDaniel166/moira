"""
Moira — light_cone.py: Received-Light Chart Engine
====================================================

Archetype: Engine

Purpose
-------
Governs computation of "received-light" positions — the ecliptic
coordinates of celestial bodies as they were when the light that reached
Earth at the birth moment was actually emitted.

Standard astrological positions already incorporate light-time correction
(the body's position is computed for the moment t − τ, where τ is the
one-way light travel time).  This engine makes the light-cone geometry
*explicit* by surfacing:

  - The *apparent* ecliptic position (Moira's standard observed position:
    light-time emission geometry plus the admitted apparent-sky corrections).
  - The *geometric* ecliptic position (where the body physically is at the
    birth moment, without any light-time correction).
  - The *light travel time* τ in days and minutes.
  - The *emission Julian Day* (jd_ut − τ): the instant when the photons
    now arriving at Earth were released.
  - The *longitude displacement*: the angular shift between Moira's apparent
    observed longitude and the same-time geometric longitude.  This is a
    received-light displacement measure, not a pure light-time-only term.

Physical context
----------------
Light travel times at J2000.0 are approximately:

    Moon       ~1.3 s   (< 0.0001°  displacement)
    Sun        ~8.3 min (~0.004° displacement — fast-moving luminaries
                         can show up to ~0.02° in extreme cases)
    Mars       ~4–20 min
    Jupiter    ~35–52 min (~0.04–0.06° displacement)
    Saturn     ~68–84 min
    Uranus     ~2.7 h
    Neptune    ~4.1 h
    Pluto      ~5.3 h   (~0.25–0.35° displacement — detectable in
                         precise work)

For inner planets, the displacement is sub-degree; for the outer solar
system it can reach a third of a degree or more, comparable in magnitude
to a tight orb.

Boundary declaration
--------------------
Owns: ``ReceivedLightPosition`` vessel, ``RECEIVED_LIGHT_BODIES``,
      ``received_light_at``, ``all_received_light_at``.
Delegates: apparent and geometric position computation to
           ``moira.planets.planet_at``, constants to ``moira.constants``.

Import-time side effects: None

External dependency assumptions
--------------------------------
Requires the DE441 kernel to be initialised (same requirement as
``moira.planets.planet_at``).

Public surface
--------------
``ReceivedLightPosition``   — vessel for a single received-light position.
``RECEIVED_LIGHT_BODIES``   — frozenset of body names for which
                              received-light positions can be computed.
``received_light_at``       — received-light position for one body.
``all_received_light_at``   — received-light positions for all supported bodies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .constants import Body, C_KM_PER_DAY, KM_PER_AU, sign_of

__all__ = [
    "ReceivedLightPosition",
    "RECEIVED_LIGHT_BODIES",
    "received_light_at",
    "all_received_light_at",
]

# ---------------------------------------------------------------------------
# Valid body set
# ---------------------------------------------------------------------------

#: Physical bodies for which light-time corrections are meaningful.
#: Excludes computed points (True Node, Mean Node, Lilith) because those
#: have no physical surface emitting light.
RECEIVED_LIGHT_BODIES: frozenset[str] = frozenset(Body.ALL_PLANETS)


# ---------------------------------------------------------------------------
# Data vessel
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ReceivedLightPosition:
    """
    RITE: The Received-Light Position Vessel.

    THEOREM: Holds both Moira's apparent observed ecliptic position of a body
    (including light-time and apparent-sky corrections) and the geometric
    position (where the body physically is at the birth instant), along with
    the light-cone parameters that connect them.

    The ``sign``, ``sign_symbol``, and ``sign_degree`` fields reflect the
    *apparent* longitude — the position an astrologer would use.

    Structural invariants
    ---------------------
    - ``apparent_longitude`` and ``geometric_longitude`` are both in
      [0°, 360°).
    - ``sign``, ``sign_symbol``, ``sign_degree`` are always consistent with
      ``apparent_longitude`` after ``__post_init__`` completes.
    - ``retrograde`` is consistent with the apparent (light-time corrected)
      longitudinal speed.
    - ``light_travel_days`` is always ≥ 0.
    - ``emission_jd < jd_ut`` for all physical bodies with finite distance.
    """

    name:                str    # Body name (Body.* constant)
    apparent_longitude:  float  # Where body was when light emitted, [0°, 360°)
    apparent_latitude:   float  # Ecliptic latitude at emission instant
    geometric_longitude: float  # Where body actually is at birth moment, [0°, 360°)
    geometric_latitude:  float  # Ecliptic latitude at birth moment
    distance_km:         float  # Earth–body distance at emission instant (km)
    light_travel_days:   float  # One-way light travel time in days (τ)
    emission_jd:         float  # Julian Date when photons were emitted (jd_ut − τ)
    speed:               float  # Apparent longitudinal speed (degrees/day)
    retrograde:          bool   # True when apparent speed < 0

    # Derived zodiac fields — populated by __post_init__, based on apparent longitude
    sign:        str   = field(init=False)
    sign_symbol: str   = field(init=False)
    sign_degree: float = field(init=False)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.apparent_longitude)

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def light_travel_minutes(self) -> float:
        """One-way light travel time in minutes."""
        return self.light_travel_days * 1440.0

    @property
    def longitude_displacement(self) -> float:
        """
        Angular displacement between apparent and geometric longitude, in degrees.

        Returns a value in (−180°, +180°], positive when the body has moved
        forward (direct motion) in the time the light was in transit.
        """
        d = (self.apparent_longitude - self.geometric_longitude + 180.0) % 360.0 - 180.0
        return d

    @property
    def distance_au(self) -> float:
        """Earth–body distance at emission instant in Astronomical Units."""
        return self.distance_km / KM_PER_AU

    def __repr__(self) -> str:
        disp = self.longitude_displacement
        return (
            f"ReceivedLightPosition("
            f"name={self.name!r}, "
            f"apparent={self.apparent_longitude:.4f}°, "
            f"geometric={self.geometric_longitude:.4f}°, "
            f"displacement={disp:+.4f}°, "
            f"lt={self.light_travel_minutes:.2f} min)"
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def received_light_at(
    body:   str,
    jd_ut:  float,
    reader=None,
) -> ReceivedLightPosition:
    """
    Compute the received-light position of ``body`` at the given Julian Date.

    The apparent position is derived from ``planet_at(apparent=True)``,
    which applies Moira's full apparent-position pipeline.  The geometric
    position is derived from ``planet_at(apparent=False)``.  The light travel
    time is inferred from the apparent pipeline's light-time-corrected
    distance:

        τ (days) = distance_km / C_KM_PER_DAY

    Parameters
    ----------
    body   : Body name (``Body.*`` constant).  Must be in
             ``RECEIVED_LIGHT_BODIES``.
    jd_ut  : Julian Day Number in Universal Time (UT1).
    reader : An open ``SpkReader`` instance.  If ``None``, the module-level
             singleton from ``moira.planets.get_reader()`` is used.

    Returns
    -------
    ReceivedLightPosition — apparent and geometric positions, light-cone
    parameters, and zodiac data.

    Raises
    ------
    ValueError
        If ``body`` is not in ``RECEIVED_LIGHT_BODIES``.

    Notes
    -----
    The light travel time is computed from the iteratively-converged
    light-time corrected distance already embedded in the ``planet_at``
    apparent pipeline.  No additional iteration is performed here.

    The ``speed`` and ``retrograde`` fields reflect the apparent longitudinal
    rate returned by ``planet_at(apparent=True)``, consistent with all other
    standard Moira position products.
    """
    if body not in RECEIVED_LIGHT_BODIES:
        raise ValueError(
            f"received_light_at: {body!r} is not in RECEIVED_LIGHT_BODIES. "
            f"Choose from: {sorted(RECEIVED_LIGHT_BODIES)}"
        )

    from .planets import planet_at, get_reader

    if reader is None:
        reader = get_reader()

    # Apparent position — light-time corrected, with full pipeline.
    apparent  = planet_at(body, jd_ut, reader=reader, apparent=True)
    # Geometric position — no corrections; where the body actually is now.
    geometric = planet_at(body, jd_ut, reader=reader, apparent=False)

    # Light travel time from the already-converged apparent distance.
    lt_days    = apparent.distance / C_KM_PER_DAY
    emission   = jd_ut - lt_days

    return ReceivedLightPosition(
        name                = body,
        apparent_longitude  = apparent.longitude,
        apparent_latitude   = apparent.latitude,
        geometric_longitude = geometric.longitude,
        geometric_latitude  = geometric.latitude,
        distance_km         = apparent.distance,
        light_travel_days   = lt_days,
        emission_jd         = emission,
        speed               = apparent.speed,
        retrograde          = apparent.retrograde,
    )


def all_received_light_at(
    jd_ut:  float,
    bodies: list[str] | None = None,
    reader=None,
) -> dict[str, ReceivedLightPosition]:
    """
    Compute received-light positions for multiple bodies at once.

    Parameters
    ----------
    jd_ut  : Julian Day Number in Universal Time (UT1).
    bodies : List of body names to compute.  Defaults to all members of
             ``RECEIVED_LIGHT_BODIES``.
    reader : An open ``SpkReader`` instance.  If ``None``, the module-level
             singleton is used.

    Returns
    -------
    dict mapping body name (``str``) to ``ReceivedLightPosition``.

    Raises
    ------
    ValueError
        If any entry in ``bodies`` is not in ``RECEIVED_LIGHT_BODIES``.
    """
    if bodies is None:
        bodies = sorted(RECEIVED_LIGHT_BODIES)

    from .planets import get_reader
    if reader is None:
        reader = get_reader()

    return {
        body: received_light_at(body, jd_ut, reader=reader)
        for body in bodies
    }
