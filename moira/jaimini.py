"""
Moira — Jaimini Karaka Engine
===============================

Archetype: Engine

Purpose
-------
Computes the Chara Karakas (variable significators) of Jaimini astrology
by sorting the seven classical planets (and optionally Rahu) by their
degree within their respective sidereal signs.

Two schemes are supported:

  7-karaka scheme  — the seven classical planets (Sun through Saturn) are
                     ranked and assigned significator roles.  This is the
                     mainstream Parashari-compatible Jaimini system and the
                     default.

  8-karaka scheme  — Rahu is added as the eighth candidate.  Rahu's degree
                     within its sign is inverted (``30 - degree``) because
                     Rahu moves retrograde.  This scheme is associated with
                     Sanjay Rath's reading of the Jaimini Sutras.

In both schemes Ketu is always excluded.

Karaka assignment (7-karaka)
----------------------------
  Rank 1 — Atmakaraka   (AK)  — soul significator
  Rank 2 — Amatyakaraka (AmK) — career / minister
  Rank 3 — Bhratrikaraka (BK) — siblings
  Rank 4 — Matrikaraka  (MaK) — mother
  Rank 5 — Pitrikaraka  (PiK) — father
  Rank 6 — Gnatikaraka  (GK)  — community / disputes
  Rank 7 — Darakaraka   (DK)  — spouse

Karaka assignment (8-karaka)
----------------------------
  Ranks 1–5 same as 7-karaka, then:
  Rank 6 — Putrakaraka  (PuK) — children
  Rank 7 — Gnatikaraka  (GK)
  Rank 8 — Darakaraka   (DK)

Tradition and sources
---------------------
Jaimini, "Jaimini Sutras" (Jaimini Sutramritam), Adhyaya 1, Pada 1,
Sutras 1–14.  Commentary: Sanjay Rath, "Jaimini Maharishi's Upadesa
Sutras" (2002).  P.V.R. Narasimha Rao's Jaimini notes (on the 7/8-karaka
debate).

Boundary declaration
--------------------
Owns: Jaimini Chara Karaka computation, Rahu degree inversion, the
      ``KarakaAssignment`` and ``JaiminiKarakaResult`` result vessels.
Delegates: nothing.  All inputs must already be converted to sidereal
           longitude by the caller (see ``moira.sidereal``).

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required.  No database access.  The computation is a
single sort over at most 8 values.

Constitutional phase
--------------------
Phase 12 — Public API Curation.  All twelve phases complete.

Public surface
--------------
``KarakaRole``               — string constants for the eight karaka role names.
``KarakaPlanetType``         — structural category constants for karaka pool planets.
``JaiminiPolicy``            — policy dataclass for Jaimini computation.
``KARAKA_NAMES_7``           — ordered list of karaka names for the 7-scheme.
``KARAKA_NAMES_8``           — ordered list of karaka names for the 8-scheme.
``KarakaAssignment``         — immutable truth-preservation vessel for one planet's role.
``JaiminiKarakaResult``      — immutable truth-preservation vessel for the full result.
``KarakaConditionProfile``   — integrated condition profile for one Chara Karaka.
``JaiminiChartProfile``      — aggregate intelligence profile for a full computation.
``KarakaPair``               — network pair connecting two Chara Karaka roles.
``jaimini_karakas``          — compute all Chara Karakas from sidereal longitudes.
``atmakaraka``               — convenience accessor returning the AK planet name.
``karaka_condition_profile`` — build a KarakaConditionProfile from a KarakaAssignment.
``jaimini_chart_profile``    — build a JaiminiChartProfile from a JaiminiKarakaResult.
``karaka_pair``              — build a KarakaPair connecting two named roles.
``validate_jaimini_output``  — validate structural invariants of a JaiminiKarakaResult.
"""

from dataclasses import dataclass

__all__ = [
    # Phase 2 — Classification
    "KarakaRole",
    "KarakaPlanetType",
    # Phase 4 — Policy
    "JaiminiPolicy",
    # Name tables
    "KARAKA_NAMES_7",
    "KARAKA_NAMES_8",
    # Phase 1 — Truth Preservation
    "KarakaAssignment",
    "JaiminiKarakaResult",
    # Phase 7 — Integrated Local Condition
    "KarakaConditionProfile",
    # Phase 8 — Aggregate Intelligence
    "JaiminiChartProfile",
    # Phase 9 — Network Intelligence
    "KarakaPair",
    # Functions
    "jaimini_karakas",
    "atmakaraka",
    "karaka_condition_profile",
    "jaimini_chart_profile",
    "karaka_pair",
    "validate_jaimini_output",
]

# ---------------------------------------------------------------------------
# Karaka name sequences
# ---------------------------------------------------------------------------

KARAKA_NAMES_7: list[str] = [
    'Atmakaraka',    # AK  — rank 1
    'Amatyakaraka',  # AmK — rank 2
    'Bhratrikaraka', # BK  — rank 3
    'Matrikaraka',   # MaK — rank 4
    'Pitrikaraka',   # PiK — rank 5
    'Gnatikaraka',   # GK  — rank 6
    'Darakaraka',    # DK  — rank 7
]

KARAKA_NAMES_8: list[str] = [
    'Atmakaraka',    # AK  — rank 1
    'Amatyakaraka',  # AmK — rank 2
    'Bhratrikaraka', # BK  — rank 3
    'Matrikaraka',   # MaK — rank 4
    'Pitrikaraka',   # PiK — rank 5
    'Putrakaraka',   # PuK — rank 6
    'Gnatikaraka',   # GK  — rank 7
    'Darakaraka',    # DK  — rank 8
]

# Planet pool for each scheme (Ketu is never included)
_POOL_7: tuple[str, ...] = ('Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn')
_POOL_8: tuple[str, ...] = _POOL_7 + ('Rahu',)


# ---------------------------------------------------------------------------
# Phase 2 — Classification constants
# ---------------------------------------------------------------------------

class KarakaRole:
    """String constants for Jaimini Chara Karaka role names.

    Use these instead of bare string literals to reference a karaka role.
    The values are identical to those in ``KARAKA_NAMES_7`` and
    ``KARAKA_NAMES_8``.
    """
    ATMAKARAKA    = 'Atmakaraka'
    AMATYAKARAKA  = 'Amatyakaraka'
    BHRATRIKARAKA = 'Bhratrikaraka'
    MATRIKARAKA   = 'Matrikaraka'
    PITRIKARAKA   = 'Pitrikaraka'
    PUTRAKARAKA   = 'Putrakaraka'   # 8-scheme only
    GNATIKARAKA   = 'Gnatikaraka'
    DARAKARAKA    = 'Darakaraka'


class KarakaPlanetType:
    """Structural category constants for planets in the Jaimini karaka pool.

    Mirrors ``DashaLordType`` in ``moira.dasha`` for cross-subsystem
    consistency.
    """
    LUMINARY = 'luminary'   # Sun, Moon
    INNER    = 'inner'      # Mercury, Venus, Mars
    OUTER    = 'outer'      # Jupiter, Saturn
    NODE     = 'node'       # Rahu (8-scheme only)


# Phase 4 — Policy

@dataclass(frozen=True, slots=True)
class JaiminiPolicy:
    """Policy surface for Jaimini Chara Karaka computation.

    Attributes
    ----------
    scheme : int
        7 (default) or 8.  Selects the 7-karaka (Parashari-compatible)
        or 8-karaka (Sanjay Rath / Jaimini Sutras) assignment scheme.
    ayanamsa_system : str
        Ayanamsa system used by the caller for sidereal conversion.
        Informational only; this module operates on pre-converted
        sidereal longitudes.
    """
    scheme: int = 7
    ayanamsa_system: str = 'Lahiri'

    def __post_init__(self) -> None:
        if self.scheme not in (7, 8):
            raise ValueError(f"JaiminiPolicy.scheme must be 7 or 8, got {self.scheme!r}")


# ---------------------------------------------------------------------------
# Internal planet-type lookup
# ---------------------------------------------------------------------------

_PLANET_TYPE: dict[str, str] = {
    'Sun':     KarakaPlanetType.LUMINARY,
    'Moon':    KarakaPlanetType.LUMINARY,
    'Mars':    KarakaPlanetType.INNER,
    'Mercury': KarakaPlanetType.INNER,
    'Venus':   KarakaPlanetType.INNER,
    'Jupiter': KarakaPlanetType.OUTER,
    'Saturn':  KarakaPlanetType.OUTER,
    'Rahu':    KarakaPlanetType.NODE,
}


# ---------------------------------------------------------------------------
# Result vessels
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class KarakaAssignment:
    """
    Immutable vessel for one planet's Jaimini Chara Karaka role.

    Attributes
    ----------
    karaka_name : str
        The karaka role, e.g. ``'Atmakaraka'``.
    karaka_rank : int
        1-based rank (1 = highest degree = Atmakaraka).
    planet : str
        The planet assigned to this role.
    degree_in_sign : float
        The effective degree used for sorting, in [0, 30).
        For Rahu this is the inverted value (``30 - actual_degree``).
    sidereal_longitude : float
        Original sidereal longitude of the planet (before any inversion),
        normalised to [0, 360).
    is_rahu_inverted : bool
        ``True`` only when ``planet == 'Rahu'`` and degree inversion was
        applied.
    """

    karaka_name: str
    karaka_rank: int
    planet: str
    degree_in_sign: float
    sidereal_longitude: float
    is_rahu_inverted: bool

    def __post_init__(self) -> None:
        if not (1 <= self.karaka_rank <= 8):
            raise ValueError(
                f"karaka_rank must be in [1, 8], got {self.karaka_rank}"
            )
        if not self.planet:
            raise ValueError("planet must be a non-empty string")
        if not (0.0 <= self.degree_in_sign <= 30.0):
            raise ValueError(
                f"degree_in_sign must be in [0, 30], got {self.degree_in_sign}"
            )
        if not (0.0 <= self.sidereal_longitude < 360.0):
            raise ValueError(
                f"sidereal_longitude must be in [0, 360), got {self.sidereal_longitude}"
            )


@dataclass(frozen=True, slots=True)
class JaiminiKarakaResult:
    """
    Immutable vessel for a complete Jaimini Chara Karaka computation.

    Attributes
    ----------
    assignments : list[KarakaAssignment]
        Full ordered list from AK (rank 1) through DK (rank 7 or 8).
    scheme : int
        7 or 8 — the karaka scheme used.
    atmakaraka : str
        Planet name of the Atmakaraka (convenience field;
        always equals ``assignments[0].planet``).
    tie_warnings : list[tuple[str, str]]
        Each entry is an (planet_A, planet_B) pair whose effective degrees
        within their respective signs are exactly equal.  Ties are
        astronomically very rare.  When they occur, a deterministic
        tiebreaker is applied (lower index in the planet pool sequence) but
        the result is flagged here as indeterminate.
    """

    assignments: list[KarakaAssignment]
    scheme: int
    atmakaraka: str
    tie_warnings: list[tuple[str, str]]

    def __post_init__(self) -> None:
        if self.scheme not in (7, 8):
            raise ValueError(f"scheme must be 7 or 8, got {self.scheme}")
        if len(self.assignments) != self.scheme:
            raise ValueError(
                f"assignments must have {self.scheme} entries, "
                f"got {len(self.assignments)}"
            )
        planets_seen: set[str] = set()
        for i, a in enumerate(self.assignments):
            if a.karaka_rank != i + 1:
                raise ValueError(
                    f"assignments[{i}].karaka_rank = {a.karaka_rank}, "
                    f"expected {i + 1}"
                )
            if a.planet in planets_seen:
                raise ValueError(
                    f"Duplicate planet {a.planet!r} in assignments"
                )
            planets_seen.add(a.planet)
        if self.atmakaraka != self.assignments[0].planet:
            raise ValueError(
                f"atmakaraka {self.atmakaraka!r} != "
                f"assignments[0].planet {self.assignments[0].planet!r}"
            )

    # --- Phase 3 — Inspectability ------------------------------------------

    def by_planet(self, planet: str) -> KarakaAssignment | None:
        """Return the KarakaAssignment for the given planet, or ``None``."""
        for a in self.assignments:
            if a.planet == planet:
                return a
        return None

    def by_karaka(self, name: str) -> KarakaAssignment | None:
        """Return the KarakaAssignment for the given karaka name, or ``None``."""
        for a in self.assignments:
            if a.karaka_name == name:
                return a
        return None

    @property
    def darakaraka(self) -> KarakaAssignment:
        """The Darakaraka (DK) — the last planet in the ranked sequence."""
        return self.assignments[-1]

    @property
    def has_ties(self) -> bool:
        """``True`` if any tie warnings are present in this result."""
        return len(self.tie_warnings) > 0


# ---------------------------------------------------------------------------
# Phase 7 — Integrated Local Condition
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class KarakaConditionProfile:
    """Integrated condition profile for one Jaimini Chara Karaka.

    Combines the raw assignment truth with typed classification.  Built
    from a ``KarakaAssignment`` via :func:`karaka_condition_profile`.

    Attributes
    ----------
    karaka_name : str
        The karaka role name (e.g. ``'Atmakaraka'``).
    karaka_rank : int
        1-based rank within the scheme.
    planet : str
        The planet holding this karaka role.
    planet_type : str
        Structural category from ``KarakaPlanetType``: ``'luminary'``,
        ``'inner'``, ``'outer'``, or ``'node'``.
    degree_in_sign : float
        Effective degree within sign used for sorting, in [0, 30).
    sidereal_longitude : float
        Original sidereal longitude, normalised to [0, 360).
    is_rahu_inverted : bool
        ``True`` only when planet is Rahu and degree inversion was applied.
    is_atmakaraka : bool
        ``True`` when ``karaka_rank == 1``.
    is_darakaraka : bool
        ``True`` when this is the last rank in the scheme (DK).
    """

    karaka_name: str
    karaka_rank: int
    planet: str
    planet_type: str
    degree_in_sign: float
    sidereal_longitude: float
    is_rahu_inverted: bool
    is_atmakaraka: bool
    is_darakaraka: bool


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate Intelligence
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class JaiminiChartProfile:
    """Aggregate intelligence profile for a complete Jaimini Chara Karaka
    computation.

    Derived from a ``JaiminiKarakaResult`` via :func:`jaimini_chart_profile`.
    Summarises chart-wide doctrinal facts about the karaka structure.

    Attributes
    ----------
    scheme : int
        7 or 8.
    atmakaraka_planet : str
        Planet holding the Atmakaraka role.
    darakaraka_planet : str
        Planet holding the Darakaraka role.
    has_node_atmakaraka : bool
        ``True`` when Rahu holds the Atmakaraka role (8-scheme only).
    has_node_darakaraka : bool
        ``True`` when Rahu holds the Darakaraka role (8-scheme only).
    has_ties : bool
        ``True`` if any degree tie was detected.
    tie_count : int
        Number of (planet_A, planet_B) tie pairs detected.
    profiles : list[KarakaConditionProfile]
        One profile per karaka in ranked order.
    """

    scheme: int
    atmakaraka_planet: str
    darakaraka_planet: str
    has_node_atmakaraka: bool
    has_node_darakaraka: bool
    has_ties: bool
    tie_count: int
    profiles: list[KarakaConditionProfile]

    def __post_init__(self) -> None:
        if self.scheme not in (7, 8):
            raise ValueError(f"scheme must be 7 or 8, got {self.scheme}")
        if len(self.profiles) != self.scheme:
            raise ValueError(
                f"profiles must have {self.scheme} entries, "
                f"got {len(self.profiles)}"
            )
        if self.tie_count != (1 if self.has_ties and self.tie_count >= 1 else self.tie_count):
            pass  # tie_count just mirrors len(tie_warnings); no further constraint
        if self.has_ties and self.tie_count == 0:
            raise ValueError(
                "has_ties is True but tie_count is 0"
            )
        if not self.has_ties and self.tie_count != 0:
            raise ValueError(
                f"has_ties is False but tie_count is {self.tie_count}"
            )


# ---------------------------------------------------------------------------
# Phase 9 — Network Intelligence
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class KarakaPair:
    """Network pair connecting two Jaimini Chara Karaka roles.

    Built from a ``JaiminiKarakaResult`` via :func:`karaka_pair`.
    Represents a structural edge between any two karakas (e.g. AK–DK,
    AK–AmK).

    Attributes
    ----------
    role_a : str
        ``KarakaRole`` constant for the first role.
    role_b : str
        ``KarakaRole`` constant for the second role.
    planet_a : str
        Planet holding ``role_a``.
    planet_b : str
        Planet holding ``role_b``.
    type_a : str
        ``KarakaPlanetType`` of ``planet_a``.
    type_b : str
        ``KarakaPlanetType`` of ``planet_b``.
    involves_node : bool
        ``True`` when either planet is Rahu (a node).
    both_are_nodes : bool
        ``True`` when both planets are nodes (only possible in the
        8-scheme if two node assignments exist, which cannot happen in
        practice; guarded here for completeness).
    """

    role_a: str
    role_b: str
    planet_a: str
    planet_b: str
    type_a: str
    type_b: str
    involves_node: bool
    both_are_nodes: bool

    def __post_init__(self) -> None:
        if self.planet_a == self.planet_b:
            raise ValueError(
                f"KarakaPair cannot have the same planet in both roles: "
                f"{self.planet_a!r}"
            )
        expected_involves = (
            self.type_a == KarakaPlanetType.NODE
            or self.type_b == KarakaPlanetType.NODE
        )
        if self.involves_node != expected_involves:
            raise ValueError(
                f"involves_node={self.involves_node} is inconsistent with "
                f"type_a={self.type_a!r}, type_b={self.type_b!r}"
            )
        expected_both = (
            self.type_a == KarakaPlanetType.NODE
            and self.type_b == KarakaPlanetType.NODE
        )
        if self.both_are_nodes != expected_both:
            raise ValueError(
                f"both_are_nodes={self.both_are_nodes} is inconsistent with "
                f"type_a={self.type_a!r}, type_b={self.type_b!r}"
            )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _effective_degree(planet: str, sidereal_lon: float) -> float:
    """
    Return the degree within sign used for Jaimini karaka sorting.

    For all planets except Rahu: ``sidereal_lon % 30``.
    For Rahu: ``30 - (sidereal_lon % 30)``, because Rahu moves retrograde
    and its progress within a sign is measured backward from the sign end.
    """
    deg = sidereal_lon % 30.0
    if planet == 'Rahu':
        return 30.0 - deg
    return deg


def _find_ties(
    planets: list[str],
    degrees: dict[str, float],
) -> list[tuple[str, str]]:
    """Return all (planet_A, planet_B) pairs with equal effective degrees."""
    ties: list[tuple[str, str]] = []
    n = len(planets)
    for i in range(n):
        for j in range(i + 1, n):
            if degrees[planets[i]] == degrees[planets[j]]:
                ties.append((planets[i], planets[j]))
    return ties


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def jaimini_karakas(
    sidereal_longitudes: dict[str, float],
    scheme: int = 7,
    policy: JaiminiPolicy | None = None,
) -> JaiminiKarakaResult:
    """
    Compute all Jaimini Chara Karakas from a set of sidereal longitudes.

    Planets are ranked in descending order of their effective degree within
    their sidereal sign.  The highest-degree planet becomes the Atmakaraka.

    Rahu's effective degree is inverted (``30 - degree``) in the 8-karaka
    scheme.  Ketu is never included in either scheme.

    Parameters
    ----------
    sidereal_longitudes : dict[str, float]
        Mapping of planet name → sidereal longitude.  Must contain at least
        all planets in the requested scheme's pool.  Extra keys (e.g. Ketu,
        Uranus) are silently ignored.
    scheme : int
        7 (default) or 8.  Raises ``ValueError`` for any other value.
        Ignored when ``policy`` is supplied.
    policy : JaiminiPolicy or None
        Optional policy vessel.  When provided, ``policy.scheme`` overrides
        the ``scheme`` argument.

    Returns
    -------
    JaiminiKarakaResult

    Raises
    ------
    ValueError
        If the resolved scheme is not 7 or 8.
    KeyError
        If a required planet is absent from ``sidereal_longitudes``.

    Examples
    --------
    >>> lons = {
    ...     'Sun': 10.0, 'Moon': 45.0, 'Mars': 80.0,
    ...     'Mercury': 115.0, 'Jupiter': 150.0, 'Venus': 185.0,
    ...     'Saturn': 220.0,
    ... }
    >>> result = jaimini_karakas(lons)
    >>> result.scheme
    7
    >>> len(result.assignments)
    7
    """
    if policy is not None:
        scheme = policy.scheme
    if scheme not in (7, 8):
        raise ValueError(f"scheme must be 7 or 8, got {scheme!r}")

    pool = _POOL_7 if scheme == 7 else _POOL_8
    karaka_names = KARAKA_NAMES_7 if scheme == 7 else KARAKA_NAMES_8

    # Compute effective degrees for each planet in the pool
    degrees: dict[str, float] = {
        p: _effective_degree(p, sidereal_longitudes[p])
        for p in pool
    }

    # Detect ties before sorting (deterministic tiebreaker: pool order)
    tie_warnings = _find_ties(list(pool), degrees)

    # Sort descending by effective degree; tiebreaker = pool index (stable)
    ranked: list[str] = sorted(
        pool,
        key=lambda p: (-degrees[p], pool.index(p)),
    )

    assignments: list[KarakaAssignment] = [
        KarakaAssignment(
            karaka_name=karaka_names[i],
            karaka_rank=i + 1,
            planet=ranked[i],
            degree_in_sign=degrees[ranked[i]],
            sidereal_longitude=sidereal_longitudes[ranked[i]] % 360.0,
            is_rahu_inverted=(ranked[i] == 'Rahu'),
        )
        for i in range(len(pool))
    ]

    return JaiminiKarakaResult(
        assignments=assignments,
        scheme=scheme,
        atmakaraka=ranked[0],
        tie_warnings=tie_warnings,
    )


def atmakaraka(
    sidereal_longitudes: dict[str, float],
    scheme: int = 7,
) -> str:
    """
    Return the name of the Atmakaraka planet.

    This is a convenience wrapper around ``jaimini_karakas`` that returns
    only the planet with the highest effective degree within its sign.

    Parameters
    ----------
    sidereal_longitudes : dict[str, float]
        Mapping of planet name → sidereal longitude.
    scheme : int
        7 (default) or 8.

    Returns
    -------
    str
        Planet name of the Atmakaraka.
    """
    return jaimini_karakas(sidereal_longitudes, scheme=scheme).atmakaraka


# ---------------------------------------------------------------------------
# Phase 7 — Condition profile
# ---------------------------------------------------------------------------

def karaka_condition_profile(
    assignment: KarakaAssignment,
    scheme: int,
) -> KarakaConditionProfile:
    """Build a :class:`KarakaConditionProfile` from a :class:`KarakaAssignment`.

    Parameters
    ----------
    assignment : KarakaAssignment
        The raw truth-preservation vessel.
    scheme : int
        7 or 8.  Used to determine whether this assignment is the Darakaraka.

    Returns
    -------
    KarakaConditionProfile
    """
    return KarakaConditionProfile(
        karaka_name=assignment.karaka_name,
        karaka_rank=assignment.karaka_rank,
        planet=assignment.planet,
        planet_type=_PLANET_TYPE[assignment.planet],
        degree_in_sign=assignment.degree_in_sign,
        sidereal_longitude=assignment.sidereal_longitude,
        is_rahu_inverted=assignment.is_rahu_inverted,
        is_atmakaraka=(assignment.karaka_rank == 1),
        is_darakaraka=(assignment.karaka_rank == scheme),
    )


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate function
# ---------------------------------------------------------------------------

def jaimini_chart_profile(result: JaiminiKarakaResult) -> JaiminiChartProfile:
    """Build a :class:`JaiminiChartProfile` from a :class:`JaiminiKarakaResult`.

    Parameters
    ----------
    result : JaiminiKarakaResult

    Returns
    -------
    JaiminiChartProfile
    """
    profiles = [
        karaka_condition_profile(a, result.scheme)
        for a in result.assignments
    ]
    ak_type = _PLANET_TYPE[result.atmakaraka]
    dk_type = _PLANET_TYPE[result.darakaraka.planet]
    return JaiminiChartProfile(
        scheme=result.scheme,
        atmakaraka_planet=result.atmakaraka,
        darakaraka_planet=result.darakaraka.planet,
        has_node_atmakaraka=(ak_type == KarakaPlanetType.NODE),
        has_node_darakaraka=(dk_type == KarakaPlanetType.NODE),
        has_ties=result.has_ties,
        tie_count=len(result.tie_warnings),
        profiles=profiles,
    )


# ---------------------------------------------------------------------------
# Phase 9 — Network function
# ---------------------------------------------------------------------------

def karaka_pair(
    result: JaiminiKarakaResult,
    role_a: str,
    role_b: str,
) -> KarakaPair:
    """Build a :class:`KarakaPair` connecting two named Chara Karaka roles.

    Parameters
    ----------
    result : JaiminiKarakaResult
        The computed karaka assignment to draw from.
    role_a : str
        A ``KarakaRole`` constant for the first role (e.g.
        ``KarakaRole.ATMAKARAKA``).
    role_b : str
        A ``KarakaRole`` constant for the second role (e.g.
        ``KarakaRole.DARAKARAKA``).

    Returns
    -------
    KarakaPair

    Raises
    ------
    ValueError
        If either role name is not found in the result.
    """
    a = result.by_karaka(role_a)
    b = result.by_karaka(role_b)
    if a is None:
        raise ValueError(
            f"Role {role_a!r} not found in result (scheme={result.scheme})"
        )
    if b is None:
        raise ValueError(
            f"Role {role_b!r} not found in result (scheme={result.scheme})"
        )
    type_a = _PLANET_TYPE[a.planet]
    type_b = _PLANET_TYPE[b.planet]
    return KarakaPair(
        role_a=role_a,
        role_b=role_b,
        planet_a=a.planet,
        planet_b=b.planet,
        type_a=type_a,
        type_b=type_b,
        involves_node=(
            type_a == KarakaPlanetType.NODE
            or type_b == KarakaPlanetType.NODE
        ),
        both_are_nodes=(
            type_a == KarakaPlanetType.NODE
            and type_b == KarakaPlanetType.NODE
        ),
    )


# ---------------------------------------------------------------------------
# Phase 10 — Full-subsystem hardening
# ---------------------------------------------------------------------------

def validate_jaimini_output(result: JaiminiKarakaResult) -> None:
    """Validate the structural invariants of a :class:`JaiminiKarakaResult`.

    Raises ``ValueError`` with a descriptive message if any invariant is
    violated.  Intended as a test harness and post-computation guard.

    Invariants checked
    ------------------
    - ``scheme`` is 7 or 8.
    - ``len(assignments) == scheme``.
    - ``assignments[i].karaka_rank == i + 1`` for all i.
    - ``assignments[i].karaka_name`` matches the canonical name list.
    - All planet names are distinct.
    - All planet names are within the pool for the scheme.
    - ``atmakaraka == assignments[0].planet``.
    - No tie_warnings entry is a self-pair or references a planet outside
      the pool.

    Parameters
    ----------
    result : JaiminiKarakaResult

    Raises
    ------
    ValueError
        On any invariant violation.
    """
    if result.scheme not in (7, 8):
        raise ValueError(f"scheme must be 7 or 8, got {result.scheme}")
    expected_len = result.scheme
    if len(result.assignments) != expected_len:
        raise ValueError(
            f"Expected {expected_len} assignments, got {len(result.assignments)}"
        )
    pool = _POOL_7 if result.scheme == 7 else _POOL_8
    names = KARAKA_NAMES_7 if result.scheme == 7 else KARAKA_NAMES_8
    planets_seen: set[str] = set()
    for i, a in enumerate(result.assignments):
        if a.karaka_rank != i + 1:
            raise ValueError(
                f"assignments[{i}].karaka_rank = {a.karaka_rank}, "
                f"expected {i + 1}"
            )
        if a.karaka_name != names[i]:
            raise ValueError(
                f"assignments[{i}].karaka_name = {a.karaka_name!r}, "
                f"expected {names[i]!r}"
            )
        if a.planet not in pool:
            raise ValueError(
                f"assignments[{i}].planet = {a.planet!r} is not in the "
                f"{result.scheme}-karaka pool"
            )
        if a.planet in planets_seen:
            raise ValueError(
                f"Duplicate planet {a.planet!r} in assignments"
            )
        planets_seen.add(a.planet)
    if result.atmakaraka != result.assignments[0].planet:
        raise ValueError(
            f"atmakaraka {result.atmakaraka!r} != "
            f"assignments[0].planet {result.assignments[0].planet!r}"
        )
    for planet_p, planet_q in result.tie_warnings:
        if planet_p not in pool or planet_q not in pool:
            raise ValueError(
                f"tie_warnings references planet(s) outside the pool: "
                f"({planet_p!r}, {planet_q!r})"
            )
        if planet_p == planet_q:
            raise ValueError(
                f"tie_warnings contains a self-pair: ({planet_p!r}, {planet_q!r})"
            )
