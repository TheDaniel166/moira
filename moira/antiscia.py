"""
Antiscia Engine — moira/antiscia.py

Archetype: Engine
Purpose: Computes antiscia and contra-antiscia (shadow degrees) for ecliptic
         longitudes, and detects antiscion contacts between chart bodies or
         between a body and a fixed point.

Boundary declaration:
    Owns: the antiscion formula ((180° − lon) mod 360°), the contra-antiscion
          formula ((360° − lon) mod 360°), pair-based and point-based contact
          search, and the AntisciaAspect result type.
    Delegates: sign derivation to moira.constants.sign_of.

Import-time side effects: None

External dependency assumptions:
    - moira.constants.sign_of(longitude) returns (sign_name, symbol, degree).

Public surface / exports:
    AntisciaAspect        — result dataclass for an antiscion contact
    antiscion()           — compute the antiscion of a longitude
    contra_antiscion()    — compute the contra-antiscion of a longitude
    find_antiscia()       — all antiscion/contra-antiscion contacts in a chart
    antiscia_to_point()   — bodies casting a shadow onto a fixed point
"""

from dataclasses import dataclass

from .constants import sign_of

__all__ = [
    "AntisciaAspect",
    "antiscion",
    "contra_antiscion",
    "find_antiscia",
    "antiscia_to_point",
]

# ---------------------------------------------------------------------------
# Core formulae
# ---------------------------------------------------------------------------

def antiscion(longitude: float) -> float:
    """
    Return the antiscion of an ecliptic longitude.

    The antiscion is the mirror image across the 0° Cancer / 0° Capricorn
    (solstice) axis.

    Parameters
    ----------
    longitude : float
        Ecliptic longitude in degrees (0–360).

    Returns
    -------
    float
        Antiscion longitude in degrees (0–360).
    """
    return (180.0 - longitude) % 360.0


def contra_antiscion(longitude: float) -> float:
    """
    Return the contra-antiscion of an ecliptic longitude.

    The contra-antiscion is the mirror image across the 0° Aries / 0° Libra
    (equinox) axis.

    Parameters
    ----------
    longitude : float
        Ecliptic longitude in degrees (0–360).

    Returns
    -------
    float
        Contra-antiscion longitude in degrees (0–360).
    """
    return (360.0 - longitude) % 360.0


# ---------------------------------------------------------------------------
# Helper: minimum angular separation on the circle
# ---------------------------------------------------------------------------

def _angular_distance(a: float, b: float) -> float:
    """Minimum arc between two ecliptic longitudes (0–180°)."""
    diff = abs(a % 360.0 - b % 360.0)
    return min(diff, 360.0 - diff)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AntisciaAspect:
    """
    RITE: The Shadow Contact — the moment a planet's mirror image across
          a solstice or equinox axis falls upon another body, forging a
          hidden bond invisible on the natal wheel.

    THEOREM: Immutable record of a single antiscion or contra-antiscion
             contact between two chart bodies, carrying both original
             longitudes, the shadow longitude, the aspect type, and the
             orb of contact.

    RITE OF PURPOSE:
        AntisciaAspect is the result vessel of find_antiscia() and
        antiscia_to_point().  It labels each shadow contact with the
        names of both bodies, the type of reflection (antiscion or
        contra-antiscion), and the precision of the contact, so that
        callers can filter, sort, and display results without
        reconstructing any of this information.  Without this vessel,
        shadow contacts would be bare tuples with no semantic context.

    LAW OF OPERATION:
        Responsibilities:
            - Store body1, body2, aspect type, lon1, lon2, shadow
              longitude, and orb.
            - Render a compact repr showing both bodies, the shadow
              position, and the orb.
        Non-responsibilities:
            - Does not compute shadow longitudes; that is the Engine's role.
            - Does not validate that aspect is "Antiscion" or
              "Contra-Antiscion".
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.constants.sign_of for repr formatting.
        Structural invariants:
            - orb >= 0.
            - shadow == antiscion(lon1) or contra_antiscion(lon1).

    Canon: Vettius Valens, Anthology II.37 (antiscia);
           William Lilly, Christian Astrology (1647), p. 90

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.antiscia.AntisciaAspect",
        "risk": "low",
        "api": {"frozen": ["body1", "body2", "aspect", "lon1", "lon2", "shadow", "orb"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    body1:  str
    body2:  str
    aspect: str    # "Antiscion" or "Contra-Antiscion"
    lon1:   float  # original longitude of body1
    lon2:   float  # original longitude of body2
    shadow: float  # the shadow longitude (antiscion/contra-antiscion of body1)
    orb:    float  # angular distance between shadow and lon2

    def __repr__(self) -> str:
        sign1, _, deg1 = sign_of(self.lon1)
        sign2, _, deg2 = sign_of(self.lon2)
        shad_sign, _, shad_deg = sign_of(self.shadow)
        return (
            f"AntisciaAspect({self.aspect}: {self.body1} {sign1} {deg1:.2f}° "
            f"→ shadow {shad_sign} {shad_deg:.2f}° "
            f"≈ {self.body2} {sign2} {deg2:.2f}°, orb={self.orb:.3f}°)"
        )


# ---------------------------------------------------------------------------
# Pair-based search
# ---------------------------------------------------------------------------

def find_antiscia(
    positions: dict[str, float],
    orb: float = 1.0,
) -> list[AntisciaAspect]:
    """
    Find all antiscion and contra-antiscion contacts among a set of positions.

    Each unordered pair (A, B) is tested in both directions:
      - antiscion(lon_A) ≈ lon_B
      - antiscion(lon_B) ≈ lon_A
    and similarly for contra-antiscia.  Duplicate (mirrored) entries are
    deduplicated so that each unique contact appears exactly once, with the
    body whose shadow falls closest to the other listed as body1.

    Parameters
    ----------
    positions : dict[str, float]
        Mapping of body name → ecliptic longitude (degrees).
    orb : float
        Maximum allowed orb in degrees (default 1.0°).

    Returns
    -------
    list[AntisciaAspect]
        Contacts found, sorted by orb (tightest first).
    """
    bodies = list(positions.keys())
    seen: set[frozenset[str]] = set()
    results: list[AntisciaAspect] = []

    for i, name_a in enumerate(bodies):
        for name_b in bodies[i + 1:]:
            lon_a = positions[name_a]
            lon_b = positions[name_b]

            # Test antiscion(A) ≈ B  and  antiscion(B) ≈ A
            for shadow_func, aspect_label in (
                (antiscion,         "Antiscion"),
                (contra_antiscion,  "Contra-Antiscion"),
            ):
                key = frozenset({name_a, name_b, aspect_label})
                if key in seen:
                    continue

                shad_a = shadow_func(lon_a)
                dist_a = _angular_distance(shad_a, lon_b)

                shad_b = shadow_func(lon_b)
                dist_b = _angular_distance(shad_b, lon_a)

                # Pick the tighter direction, if either qualifies
                if dist_a <= orb or dist_b <= orb:
                    seen.add(key)
                    if dist_a <= dist_b:
                        results.append(AntisciaAspect(
                            body1=name_a, body2=name_b,
                            aspect=aspect_label,
                            lon1=lon_a, lon2=lon_b,
                            shadow=shad_a, orb=dist_a,
                        ))
                    else:
                        results.append(AntisciaAspect(
                            body1=name_b, body2=name_a,
                            aspect=aspect_label,
                            lon1=lon_b, lon2=lon_a,
                            shadow=shad_b, orb=dist_b,
                        ))

    results.sort(key=lambda a: a.orb)
    return results


# ---------------------------------------------------------------------------
# Point-based search
# ---------------------------------------------------------------------------

def antiscia_to_point(
    point_longitude: float,
    positions: dict[str, float],
    point_name: str = "Point",
    orb: float = 1.0,
) -> list[AntisciaAspect]:
    """
    Find which planets cast an antiscion or contra-antiscion onto a given point.

    Both directions are checked for each planet P:
      - antiscion(lon_P) ≈ point_longitude
      - contra_antiscion(lon_P) ≈ point_longitude

    Parameters
    ----------
    point_longitude : float
        Ecliptic longitude of the fixed point (e.g. an angle or lot).
    positions : dict[str, float]
        Mapping of body name → ecliptic longitude.
    point_name : str
        Display name for the target point (default "Point").
    orb : float
        Maximum allowed orb in degrees (default 1.0°).

    Returns
    -------
    list[AntisciaAspect]
        Contacts found, sorted by orb (tightest first).
    """
    results: list[AntisciaAspect] = []

    for name, lon in positions.items():
        for shadow_func, aspect_label in (
            (antiscion,         "Antiscion"),
            (contra_antiscion,  "Contra-Antiscion"),
        ):
            shadow = shadow_func(lon)
            dist   = _angular_distance(shadow, point_longitude)
            if dist <= orb:
                results.append(AntisciaAspect(
                    body1=name, body2=point_name,
                    aspect=aspect_label,
                    lon1=lon, lon2=point_longitude,
                    shadow=shadow, orb=dist,
                ))

    results.sort(key=lambda a: a.orb)
    return results
