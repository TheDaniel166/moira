"""
Moira — triplicity.py
Standalone triplicity doctrine subsystem.

Archetype: Engine (table-first, doctrine-explicit)

Purpose
-------
Owns the triplicity ruler table and triplicity scoring for the Classic 7
planets under the Dorothean tradition. Provides an explicit
participating-ruler policy so that callers may declare their doctrinal
stance without relying on hidden conventions.

Boundary declaration
--------------------
Owns: triplicity ruler tables, doctrine and policy enumerations,
      TriplicityAssignment result vessel, and the two canonical lookup
      functions (triplicity_assignment_for, triplicity_score).
Delegates: nothing. This module has no runtime dependencies beyond
           moira.constants.SIGNS.

Import-time side effects: None

External dependency assumptions
--------------------------------
moira.constants.SIGNS is an ordered list of 12 sign name strings.

Public surface
--------------
TriplicityDoctrine         — doctrine enum (which scholarly text governs)
ParticipatingRulerPolicy   — policy enum for the participating-ruler ambiguity
TriplicityAssignment       — frozen result vessel for one sign's assignment
triplicity_assignment_for  — canonical assignment lookup by sign
triplicity_score           — compute triplicity score for one planet at one sign

Provenance note — DOROTHEAN_PINGREE_1976
-----------------------------------------
The table _TRIPLICITY_RULERS_DOROTHEAN_PINGREE_1976 is transcribed from
Dorotheus of Sidon "Carmen Astrologicum", as edited and translated by
David Pingree (Teubner, Leipzig, 1976). The water-triplicity assignment
(Cancer / Scorpio / Pisces → Mars [day ruler], Venus [night ruler], Moon
[participating ruler]) follows Pingree's edition, where Mars governs the
water triplicity by day. This is attested in Pingree's critical apparatus
and differs from some later redactions that assign Mars only to mixed-sect
contexts. This module preserves Pingree's edition as the canonical source
for the DOROTHEAN_PINGREE_1976 doctrine value.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .constants import SIGNS

__all__ = [
    "TriplicityDoctrine",
    "TriplicityElement",
    "ParticipatingRulerPolicy",
    "TriplicityAssignment",
    "triplicity_assignment_for",
    "triplicity_score",
]


class TriplicityDoctrine(StrEnum):
    DOROTHEAN_PINGREE_1976 = "dorothean_pingree_1976"


class TriplicityElement(StrEnum):
    FIRE  = "fire"
    EARTH = "earth"
    AIR   = "air"
    WATER = "water"


class ParticipatingRulerPolicy(StrEnum):
    IGNORE        = "ignore"         # participating ruler contributes 0
    AWARD_REDUCED = "award_reduced"  # participating ruler contributes participating_score


@dataclass(frozen=True, slots=True)
class TriplicityAssignment:
    """
    Full triplicity assignment for one sign under one doctrine and sect context.

    Fields
    ------
    sign               : the zodiac sign for which the assignment was looked up
    doctrine           : the doctrinal authority governing the table
    is_day_chart       : sect context supplied at lookup time
    day_ruler          : planet ruling this triplicity in a day chart
    night_ruler        : planet ruling this triplicity in a night chart
    participating_ruler: planet holding the participating (mixed-sect) role
    active_ruler       : day_ruler when is_day_chart, night_ruler otherwise
    signs              : all signs sharing this triplicity group (3-element tuple)
    """

    sign: str
    doctrine: TriplicityDoctrine
    is_day_chart: bool
    day_ruler: str
    night_ruler: str
    participating_ruler: str
    active_ruler: str
    signs: tuple[str, ...]

    # ------------------------------------------------------------------
    # Inspectability properties (Phase 3)
    # ------------------------------------------------------------------

    @property
    def element(self) -> TriplicityElement:
        """Classical element of this triplicity group (fire/earth/air/water).

        Derived from the signs tuple; requires no external data."""
        return _SIGNS_TO_ELEMENT[frozenset(self.signs)]

    @property
    def inactive_ruler(self) -> str:
        """The primary ruler that is NOT active under the current sect context.

        For a day chart this is the night ruler; for a night chart the day ruler.
        Useful when a caller needs to distinguish the dormant from the active
        primary without unpacking both fields manually."""
        return self.night_ruler if self.is_day_chart else self.day_ruler

    @property
    def has_participating_overlap(self) -> bool:
        """True when the participating ruler is identical to the active primary ruler.

        This is False for all assignments in DOROTHEAN_PINGREE_1976 but the
        property makes the invariant testable and guards against future doctrine
        additions that could introduce overlap."""
        return self.participating_ruler == self.active_ruler

    def __post_init__(self) -> None:
        if self.sign not in SIGNS:
            raise ValueError(
                f"sign must be one of the 12 tropical signs, got {self.sign!r}"
            )
        if not isinstance(self.doctrine, TriplicityDoctrine):
            raise ValueError(
                f"doctrine must be a TriplicityDoctrine member, got {self.doctrine!r}"
            )
        if not isinstance(self.is_day_chart, bool):
            raise TypeError(
                f"is_day_chart must be bool, got {type(self.is_day_chart).__name__!r}"
            )
        expected_active = self.day_ruler if self.is_day_chart else self.night_ruler
        if self.active_ruler != expected_active:
            raise ValueError(
                f"active_ruler {self.active_ruler!r} does not match expected "
                f"{expected_active!r} for is_day_chart={self.is_day_chart}"
            )
        if len(self.signs) != 3:
            raise ValueError(
                f"signs must be a 3-element tuple, got {len(self.signs)} elements"
            )
        if self.sign not in self.signs:
            raise ValueError(
                f"sign {self.sign!r} must appear in signs tuple {self.signs!r}"
            )


# ---------------------------------------------------------------------------
# Element classification — maps each triplicity sign-group to its element.
# Keyed by frozenset of signs so lookup is order-independent.
# ---------------------------------------------------------------------------

_SIGNS_TO_ELEMENT: dict[frozenset, TriplicityElement] = {
    frozenset({"Aries", "Leo",     "Sagittarius"}): TriplicityElement.FIRE,
    frozenset({"Taurus", "Virgo",  "Capricorn"}):   TriplicityElement.EARTH,
    frozenset({"Gemini", "Libra",  "Aquarius"}):    TriplicityElement.AIR,
    frozenset({"Cancer", "Scorpio", "Pisces"}):     TriplicityElement.WATER,
}


# ---------------------------------------------------------------------------
# Tables — implementation detail; not part of the public surface.
# ---------------------------------------------------------------------------

# Dorotheus/Pingree 1976: (day_ruler, night_ruler, participating_ruler) per sign.
# Fire: Sun/Jupiter/Saturn   Earth: Venus/Moon/Mars
# Air:  Saturn/Mercury/Jupiter   Water: Mars/Venus/Moon
# See module docstring provenance note for the water-triplicity scholarly commitment.
_TRIPLICITY_RULERS_DOROTHEAN_PINGREE_1976: dict[str, tuple[str, str, str]] = {
    "Aries":       ("Sun",    "Jupiter", "Saturn"),
    "Leo":         ("Sun",    "Jupiter", "Saturn"),
    "Sagittarius": ("Sun",    "Jupiter", "Saturn"),
    "Taurus":      ("Venus",  "Moon",    "Mars"),
    "Virgo":       ("Venus",  "Moon",    "Mars"),
    "Capricorn":   ("Venus",  "Moon",    "Mars"),
    "Gemini":      ("Saturn", "Mercury", "Jupiter"),
    "Libra":       ("Saturn", "Mercury", "Jupiter"),
    "Aquarius":    ("Saturn", "Mercury", "Jupiter"),
    "Cancer":      ("Mars",   "Venus",   "Moon"),   # Pingree: Mars=day, Venus=night
    "Scorpio":     ("Mars",   "Venus",   "Moon"),
    "Pisces":      ("Mars",   "Venus",   "Moon"),
}

# Precomputed: (day_ruler, night_ruler, participating_ruler) → tuple of signs
# sharing that triple.  Used to populate TriplicityAssignment.signs efficiently.
def _build_sign_groups(
    table: dict[str, tuple[str, str, str]],
) -> dict[tuple[str, str, str], tuple[str, ...]]:
    groups: dict[tuple[str, str, str], list[str]] = {}
    for sign, triple in table.items():
        groups.setdefault(triple, []).append(sign)
    return {k: tuple(v) for k, v in groups.items()}


_DOROTHEAN_PINGREE_SIGN_GROUPS: dict[tuple[str, str, str], tuple[str, ...]] = (
    _build_sign_groups(_TRIPLICITY_RULERS_DOROTHEAN_PINGREE_1976)
)

_TABLES: dict[TriplicityDoctrine, dict[str, tuple[str, str, str]]] = {
    TriplicityDoctrine.DOROTHEAN_PINGREE_1976: _TRIPLICITY_RULERS_DOROTHEAN_PINGREE_1976,
}

_SIGN_GROUPS: dict[TriplicityDoctrine, dict[tuple[str, str, str], tuple[str, ...]]] = {
    TriplicityDoctrine.DOROTHEAN_PINGREE_1976: _DOROTHEAN_PINGREE_SIGN_GROUPS,
}


# ---------------------------------------------------------------------------
# Public lookup functions
# ---------------------------------------------------------------------------

def triplicity_assignment_for(
    sign: str,
    *,
    is_day_chart: bool,
    doctrine: TriplicityDoctrine = TriplicityDoctrine.DOROTHEAN_PINGREE_1976,
) -> TriplicityAssignment:
    """
    Return the TriplicityAssignment for *sign* under *doctrine* and sect context.

    Parameters
    ----------
    sign         : one of the 12 tropical zodiac sign names
    is_day_chart : True for a diurnal chart, False for a nocturnal chart
    doctrine     : which doctrinal table to consult

    Returns
    -------
    TriplicityAssignment with day_ruler, night_ruler, participating_ruler,
    active_ruler (= day_ruler or night_ruler per sect), and signs tuple.

    Failure Contract
    ----------------
    ValueError  — sign is not present in the table for the given doctrine.
    KeyError    — doctrine is not a recognised TriplicityDoctrine member
                  (i.e. a raw string is passed where a StrEnum member is needed).
    No partial/mutable output is produced on failure.
    """
    table = _TABLES[doctrine]
    triple = table.get(sign)
    if triple is None:
        raise ValueError(
            f"Sign {sign!r} has no triplicity entry in doctrine {doctrine!r}"
        )
    day_ruler, night_ruler, participating_ruler = triple
    active_ruler = day_ruler if is_day_chart else night_ruler
    sign_groups = _SIGN_GROUPS[doctrine]
    signs = sign_groups[triple]
    return TriplicityAssignment(
        sign=sign,
        doctrine=doctrine,
        is_day_chart=is_day_chart,
        day_ruler=day_ruler,
        night_ruler=night_ruler,
        participating_ruler=participating_ruler,
        active_ruler=active_ruler,
        signs=signs,
    )


def triplicity_score(
    planet: str,
    sign: str,
    *,
    is_day_chart: bool,
    doctrine: TriplicityDoctrine = TriplicityDoctrine.DOROTHEAN_PINGREE_1976,
    participating_policy: ParticipatingRulerPolicy = ParticipatingRulerPolicy.AWARD_REDUCED,
    primary_score: int = 3,
    participating_score: int = 1,
) -> int:
    """
    Compute the triplicity contribution for *planet* in *sign*.

    Parameters
    ----------
    planet               : planet name (Classic 7)
    sign                 : zodiac sign name
    is_day_chart         : True for a diurnal chart
    doctrine             : doctrinal table to use
    participating_policy : how to treat the participating ruler
        IGNORE        → participating ruler contributes 0
        AWARD_REDUCED → participating ruler contributes *participating_score*
    primary_score        : score awarded to the day or night ruler (default 3)
    participating_score  : score awarded to the participating ruler when
                           AWARD_REDUCED policy is in effect (default 1)

    Returns
    -------
    Integer triplicity score: primary_score, participating_score, or 0.

    Failure Contract
    ----------------
    Never raises on an unrecognised sign or planet — returns 0 silently.
    This is intentional: callers may query any string without defensive
    wrapping; the absence of triplicity rulership is the answer.
    KeyError  — doctrine is not a recognised TriplicityDoctrine member.
    Returns exactly one of: primary_score, participating_score, or 0.
    Returns 0 when participating_policy is IGNORE and planet is the
    participating ruler, regardless of primary_score value.
    """
    table = _TABLES[doctrine]
    triple = table.get(sign)
    if triple is None:
        return 0
    day_ruler, night_ruler, participating_ruler = triple
    if is_day_chart and planet == day_ruler:
        return primary_score
    if not is_day_chart and planet == night_ruler:
        return primary_score
    if (
        participating_policy is ParticipatingRulerPolicy.AWARD_REDUCED
        and planet == participating_ruler
    ):
        return participating_score
    return 0
