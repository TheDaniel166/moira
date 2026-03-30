from __future__ import annotations

"""
Moira — nine_parts.py
The Nine Parts Engine: governs computation of Abu Ma'shar's Nine Hermetic Lots
(the seven externally evidenced planetary parts plus the admitted extension of
the Part of the Sword and the Part of the Node), collectively known in Moira as
the Nine Parts.

Boundary declaration
--------------------
Owns: the Nine Parts catalogue, formula resolution, day/night reversal logic,
      dependency ordering (Fortune and Spirit before derived lots), result
      vessels, condition profiling, and aggregate intelligence.
Delegates: sign name lookup to moira.constants. Does NOT own chart construction,
           house calculation, or night-determination logic (caller supplies
           is_night_chart).

Doctrine basis
--------------
Abu Ma'shar, Kitāb taḥāwil sinī al-mawālīd. Confirmed formulas and full-
reversal rule from: Benjamin N. Dykes, Introductions to Traditional Astrology
(Cazimi Press, 2010) and Persian Nativities Vol. II (Cazimi Press, 2010).

Historical scope note
---------------------
The seven planetary parts (Fortune, Spirit, Love, Necessity, Courage, Victory,
Nemesis) are treated as the externally evidenced Abu Ma'shar core. The Part of
the Sword and the Part of the Node are retained as admitted Moira extensions
within the same computational family, but not claimed at the same confidence
level as the seven-part core.

Night = Sun in houses 1–6 (below the horizon). Full reversal: all nine parts
use the night formula when the chart is nocturnal. No per-lot exceptions in
the Abu Ma'shar core.

Dependency order: Fortune and Spirit are computed first; Love, Necessity, and
Victory depend on them. Sword and Node are independent.

Import-time side effects: None

External dependency assumptions
--------------------------------
- moira.constants.sign_of(longitude) returns the sign name as a string.
- moira.constants.SIGNS is an ordered list of 12 sign name strings.
- moira.constants.SIGN_SYMBOLS is a parallel list of 12 sign symbol strings.
- Caller is responsible for determining is_night_chart (Sun in H1–H6).

Public surface
--------------
NinePartName            — canonical Abu Ma'shar part names
NinePartFormulaVariant  — DAY or NIGHT formula used
NinePartDependencyKind  — DIRECT (raw planets) or DERIVED (other lots)
NinePartHistoricalStatus — CORE_SEVEN or ADMITTED_EXTENSION
NinePartsReversalRule   — FULL_REVERSAL (only admitted rule)
NinePartsHistoricalScope — current doctrinal provenance scope
NinePartsPolicy         — doctrinal configuration surface
DEFAULT_NINE_PARTS_POLICY
NinePartComputationTruth — preserved computational truth per part
NinePart                — primary result vessel
NinePartsDependencyRelation — inter-lot dependency relation
NinePartsSet            — the nine parts as a related group
NinePartConditionProfile — integrated per-part condition profile
NinePartsAggregate      — chart-wide aggregate intelligence
nine_parts_abu_mashar() — main computation engine
validate_nine_parts_output() — validation entry point
"""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from .constants import sign_of


# ---------------------------------------------------------------------------
# Phase 12 — Public API Curation (declared first for orientation)
# ---------------------------------------------------------------------------

__all__ = [
    # Classification namespaces
    "NinePartName",
    "NinePartFormulaVariant",
    "NinePartDependencyKind",
    "NinePartHistoricalStatus",
    # Policy surface
    "NinePartsReversalRule",
    "NinePartsHistoricalScope",
    "NinePartsPolicy",
    "DEFAULT_NINE_PARTS_POLICY",
    # Truth-preservation vessels
    "NinePartComputationTruth",
    "NinePart",
    # Relational vessels
    "NinePartsDependencyRelation",
    "NinePartsSet",
    # Condition vessel
    "NinePartConditionProfile",
    # Aggregate vessel
    "NinePartsAggregate",
    # Computation functions
    "nine_parts_abu_mashar",
    # Validation
    "validate_nine_parts_output",
]


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# Traditional domicile rulers (Abu Ma'shar tradition — no outer planets)
_SIGN_RULER: dict[str, str] = {
    "Aries":       "Mars",
    "Taurus":      "Venus",
    "Gemini":      "Mercury",
    "Cancer":      "Moon",
    "Leo":         "Sun",
    "Virgo":       "Mercury",
    "Libra":       "Venus",
    "Scorpio":     "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn":   "Saturn",
    "Aquarius":    "Saturn",
    "Pisces":      "Jupiter",
}

# Canonical Abu Ma'shar Nine Parts catalogue.
# Each entry: (name, planet_association, meaning, day_add_key, day_sub_key)
# All nine parts use full reversal at night (swap day_add and day_sub).
# Dependency order: Fortune and Spirit must be resolved before
# Love, Necessity, and Victory.
_NINE_PARTS_CATALOGUE: list[tuple[str, str | None, str, str, str]] = [
    ("Fortune",   "Moon",    "Body/Success",   "Moon",        "Sun"),
    ("Spirit",    "Sun",     "Soul/Intellect",  "Sun",         "Moon"),
    ("Love",      "Venus",   "Desire",          "Spirit",      "Fortune"),
    ("Necessity", "Mercury", "Constraint",      "Fortune",     "Spirit"),
    ("Courage",   "Mars",    "Boldness",        "Fortune",     "Mars"),
    ("Victory",   "Jupiter", "Ease",            "Jupiter",     "Spirit"),
    ("Nemesis",   "Saturn",  "Weight",          "Fortune",     "Saturn"),
    ("Sword",     None,      "Conflict",        "Mars",        "Saturn"),
    ("Node",      None,      "Fate/Hidden",     "North Node",  "Moon"),
]

# Parts whose formulas use other computed lots as ingredients.
_DERIVED_PARTS: frozenset[str] = frozenset({"Love", "Necessity", "Victory"})

# Inter-lot dependencies: which lots each derived part depends on.
_DEPENDENCIES: dict[str, list[str]] = {
    "Love":      ["Spirit", "Fortune"],
    "Necessity": ["Fortune", "Spirit"],
    "Victory":   ["Jupiter", "Spirit"],   # Jupiter is a planet, Spirit is a lot
}
# Strictly lot-to-lot (non-planet) dependencies:
_LOT_DEPENDENCIES: dict[str, list[str]] = {
    "Love":      ["Spirit", "Fortune"],
    "Necessity": ["Fortune", "Spirit"],
    "Victory":   ["Spirit"],
}

_ADMITTED_EXTENSION_PARTS: frozenset[str] = frozenset({"Sword", "Node"})


# ---------------------------------------------------------------------------
# Phase 2 — Classification namespaces
# ---------------------------------------------------------------------------

class NinePartName(StrEnum):
    """
    Canonical Abu Ma'shar names for the Nine Parts, in doctrinal order.

    Order follows Dykes, Introductions to Traditional Astrology:
    Fortune → Spirit → Love → Necessity → Courage → Victory → Nemesis →
    Sword → Node.

    Fortune and Spirit are always computed first; Love, Necessity, and Victory
    depend on them.
    """
    FORTUNE   = "Fortune"
    SPIRIT    = "Spirit"
    LOVE      = "Love"
    NECESSITY = "Necessity"
    COURAGE   = "Courage"
    VICTORY   = "Victory"
    NEMESIS   = "Nemesis"
    SWORD     = "Sword"
    NODE      = "Node"


class NinePartFormulaVariant(StrEnum):
    """
    Which formula column was applied when computing a part.

    DAY   — day formula: Asc + day_add − day_sub
    NIGHT — night formula: Asc + day_sub − day_add (operands swapped)

    Abu Ma'shar: full reversal applies to all nine parts for night charts.
    """
    DAY   = "day"
    NIGHT = "night"


class NinePartDependencyKind(StrEnum):
    """
    Whether a part's formula ingredients are raw planet longitudes or include
    other computed lots.

    DIRECT  — both add and sub keys are raw planet positions (Fortune, Spirit,
              Courage, Nemesis, Sword, Node).
    DERIVED — at least one key is a previously computed lot (Love, Necessity,
              Victory).
    """
    DIRECT  = "direct"
    DERIVED = "derived"


class NinePartHistoricalStatus(StrEnum):
    """
    Historical confidence status for one part within the current subsystem.

    CORE_SEVEN
        One of the seven externally evidenced planetary lots in the Abu Ma'shar
        transmission path presently secured by Moira's doctrine.
    ADMITTED_EXTENSION
        A Moira-admitted extension preserved in the same computational family,
        but not claimed at the same evidentiary level as the seven-part core.
    """
    CORE_SEVEN = "core_seven"
    ADMITTED_EXTENSION = "admitted_extension"


# ---------------------------------------------------------------------------
# Phase 4 — Doctrine / Policy Surface
# ---------------------------------------------------------------------------

class NinePartsReversalRule(StrEnum):
    """
    Governs which reversal logic applies to the nine parts at night.

    FULL_REVERSAL — all nine parts reverse their add/sub operands for night
                    charts; no per-lot exceptions. This is the Abu Ma'shar
                    standard confirmed by Dykes.

    This is the only admitted reversal rule. A per-lot rule table is not
    supported because no historical source authorises a partial exception
    within the Abu Ma'shar Nine Parts system.
    """
    FULL_REVERSAL = "full_reversal"


class NinePartsHistoricalScope(StrEnum):
    """
    Governs the provenance stance of the subsystem's admitted lot set.

    EVIDENCED_CORE_PLUS_ADMITTED_EXTENSION
        Preserve the seven externally evidenced planetary lots plus the admitted
        extension of Sword and Node, while exposing the difference in status
        explicitly.
    """
    EVIDENCED_CORE_PLUS_ADMITTED_EXTENSION = "evidenced_core_plus_admitted_extension"


@dataclass(frozen=True, slots=True)
class NinePartsPolicy:
    """
    Doctrinal configuration surface for the Nine Parts engine.

    All fields are immutable once constructed. Pass a custom instance to
    nine_parts_abu_mashar() to override defaults.

    reversal_rule
        Which reversal rule to apply. Default: FULL_REVERSAL (the only
        historically supported option in the Abu Ma'shar tradition).
    historical_scope
        Provenance stance for the subsystem. Default preserves Moira's current
        runtime surface: seven evidenced planetary lots plus two admitted
        extension lots (Sword and Node).
    """
    reversal_rule: NinePartsReversalRule = NinePartsReversalRule.FULL_REVERSAL
    historical_scope: NinePartsHistoricalScope = (
        NinePartsHistoricalScope.EVIDENCED_CORE_PLUS_ADMITTED_EXTENSION
    )


DEFAULT_NINE_PARTS_POLICY: NinePartsPolicy = NinePartsPolicy()


# ---------------------------------------------------------------------------
# Phase 1 — Truth Preservation
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class NinePartComputationTruth:
    """
    Preserved computational path for one computed Nine Part.

    Records every operand and decision made during formula evaluation so
    that callers and higher SCP layers do not need to reconstruct hidden
    logic from the flattened longitude alone.

    asc_longitude
        The Ascendant longitude used as the projection point.
    add_key
        The ingredient key used as the 'add' operand (after night reversal
        if applicable).
    sub_key
        The ingredient key used as the 'sub' operand (after night reversal
        if applicable).
    add_longitude
        Resolved longitude of add_key.
    sub_longitude
        Resolved longitude of sub_key.
    is_night_chart
        True when the chart is nocturnal (Sun in houses 1–6).
    formula_reversed
        True when the night reversal was applied (is_night_chart and
        reversal_rule == FULL_REVERSAL).
    formula_variant
        DAY or NIGHT — which formula column was used.
    formula
        Human-readable formula string, e.g. "Asc + Moon − Sun".
    """
    asc_longitude:    float
    add_key:          str
    sub_key:          str
    add_longitude:    float
    sub_longitude:    float
    is_night_chart:   bool
    formula_reversed: bool
    formula_variant:  NinePartFormulaVariant
    formula:          str

    def __post_init__(self) -> None:
        expected = f"Asc + {self.add_key} − {self.sub_key}"
        if self.formula != expected:
            raise ValueError(
                f"NinePartComputationTruth invariant: formula must be "
                f"'Asc + {self.add_key} − {self.sub_key}', got {self.formula!r}"
            )
        if self.formula_reversed and not self.is_night_chart:
            raise ValueError(
                "NinePartComputationTruth invariant: formula_reversed requires "
                "is_night_chart to be True"
            )
        expected_variant = (
            NinePartFormulaVariant.NIGHT if self.formula_reversed
            else NinePartFormulaVariant.DAY
        )
        if self.formula_variant is not expected_variant:
            raise ValueError(
                f"NinePartComputationTruth invariant: formula_variant must be "
                f"{expected_variant!r} when formula_reversed={self.formula_reversed}"
            )


@dataclass(slots=True, frozen=True)
class NinePart:
    """
    RITE: The Sacred Arc — the computed longitude where Abu Ma'shar's formula
    for a single Hermetic Lot lands in the zodiac, carrying its name, planet
    association, meaning, sign position, and full computational truth.

    THEOREM: Primary result vessel for the Nine Parts engine. Preserves all
    computational truth (Phase 1), provides typed classification (Phase 2),
    and exposes inspectability properties (Phase 3).

    RITE OF PURPOSE:
        NinePart is the atomic output unit of nine_parts_abu_mashar(). Without
        it, callers would receive raw longitudes with no sign context, no
        formula audit trail, and no typed name. The computation truth field
        allows every derived layer to verify and classify results without
        re-running the engine.

    LAW OF OPERATION:
        Responsibilities:
            - Store name, planet_association, meaning, longitude, sign,
              sign_degree, sign_symbol, dependency_kind, and computation.
        Non-responsibilities:
            - Does not compute the longitude (delegated to the engine).
            - Does not determine the lord of the part (delegated to
              NinePartConditionProfile).
            - Does not perform any I/O or ephemeris access.
        Dependencies:
            - Populated by nine_parts_abu_mashar().
        Structural invariants:
            - longitude is in [0, 360).
            - sign_degree is in [0, 30).
            - sign is the sign name corresponding to longitude.

    Canon: Abu Ma'shar, Kitāb taḥāwil sinī al-mawālīd; Dykes (trans.),
           Introductions to Traditional Astrology (Cazimi Press, 2010).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.nine_parts.NinePart",
        "risk": "low",
        "api": {
            "frozen": [
                "name", "planet_association", "meaning", "longitude",
                "sign", "sign_degree", "sign_symbol", "dependency_kind",
                "computation"
            ],
            "internal": []
        },
        "state": {"mutable": false},
        "effects": {"io": [], "signals_emitted": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "caller ensures finite longitudes before construction"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    name:             NinePartName
    planet_association: str | None  # None for Sword and Node (nodal/gap calculations)
    meaning:          str
    longitude:        float
    sign:             str
    sign_degree:      float
    sign_symbol:      str
    dependency_kind:  NinePartDependencyKind
    computation:      NinePartComputationTruth

    def __post_init__(self) -> None:
        if not isfinite(self.longitude):
            raise ValueError(f"NinePart invariant: longitude must be finite, got {self.longitude}")
        if not (0.0 <= self.longitude < 360.0):
            raise ValueError(f"NinePart invariant: longitude must be in [0, 360), got {self.longitude}")
        if not (0.0 <= self.sign_degree < 30.0):
            raise ValueError(f"NinePart invariant: sign_degree must be in [0, 30), got {self.sign_degree}")
        computed_sign, _, _ = sign_of(self.longitude)
        if computed_sign != self.sign:
            raise ValueError(
                f"NinePart invariant: sign {self.sign!r} does not match "
                f"longitude {self.longitude}"
            )

    # -----------------------------------------------------------------------
    # Phase 3 — Inspectability
    # -----------------------------------------------------------------------

    @property
    def is_derived(self) -> bool:
        """True when the formula uses another computed lot as an ingredient."""
        return self.dependency_kind is NinePartDependencyKind.DERIVED

    @property
    def historical_status(self) -> NinePartHistoricalStatus:
        """Historical confidence status for this part."""
        if self.name.value in _ADMITTED_EXTENSION_PARTS:
            return NinePartHistoricalStatus.ADMITTED_EXTENSION
        return NinePartHistoricalStatus.CORE_SEVEN

    @property
    def is_historically_evidenced_core(self) -> bool:
        """True for the seven historically evidenced planetary lots."""
        return self.historical_status is NinePartHistoricalStatus.CORE_SEVEN

    @property
    def is_nocturnal_formula(self) -> bool:
        """True when the night formula was applied to compute this part."""
        return self.computation.formula_reversed

    @property
    def has_planet_association(self) -> bool:
        """True for the seven planetary parts (False for Sword and Node)."""
        return self.planet_association is not None

    @property
    def degrees_in_sign(self) -> int:
        """Whole degrees within the sign (truncated)."""
        return int(self.sign_degree)

    @property
    def minutes_in_sign(self) -> int:
        """Arc minutes within the current whole degree."""
        return int((self.sign_degree - self.degrees_in_sign) * 60)

    def __repr__(self) -> str:
        assoc = self.planet_association or "—"
        return (
            f"NinePart({self.name}: {self.degrees_in_sign}°{self.minutes_in_sign:02d}′ "
            f"{self.sign} {self.sign_symbol} | assoc={assoc} | "
            f"{'night' if self.is_nocturnal_formula else 'day'})"
        )


# ---------------------------------------------------------------------------
# Phase 5 — Relational Formalization
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class NinePartsDependencyRelation:
    """
    Inter-lot dependency relation for a single derived Nine Part.

    Captures which other computed lots a derived part's formula uses as
    ingredients, making the dependency graph explicit rather than implicit
    in the computation order.

    part
        The derived part whose formula depends on other lots.
    lot_dependencies
        Names of the lots (not raw planets) this part's formula depends on.
        For Love: [SPIRIT, FORTUNE]. For Necessity: [FORTUNE, SPIRIT].
        For Victory: [SPIRIT]. Empty for direct parts.
    """
    part:             NinePartName
    lot_dependencies: tuple[NinePartName, ...]

    def __post_init__(self) -> None:
        expected = _LOT_DEPENDENCIES.get(self.part.value, [])
        expected_names = tuple(NinePartName(n) for n in expected)
        if set(self.lot_dependencies) != set(expected_names):
            raise ValueError(
                f"NinePartsDependencyRelation invariant: lot_dependencies for "
                f"{self.part!r} must be {expected_names!r}, got {self.lot_dependencies!r}"
            )

    @property
    def is_direct(self) -> bool:
        """True when this part has no inter-lot dependencies."""
        return len(self.lot_dependencies) == 0

    @property
    def dependency_count(self) -> int:
        """Number of lot dependencies."""
        return len(self.lot_dependencies)


# Precomputed dependency relations for all nine parts
_ALL_DEPENDENCY_RELATIONS: tuple[NinePartsDependencyRelation, ...] = (
    NinePartsDependencyRelation(NinePartName.FORTUNE,   ()),
    NinePartsDependencyRelation(NinePartName.SPIRIT,    ()),
    NinePartsDependencyRelation(NinePartName.LOVE,      (NinePartName.SPIRIT, NinePartName.FORTUNE)),
    NinePartsDependencyRelation(NinePartName.NECESSITY, (NinePartName.FORTUNE, NinePartName.SPIRIT)),
    NinePartsDependencyRelation(NinePartName.COURAGE,   ()),
    NinePartsDependencyRelation(NinePartName.VICTORY,   (NinePartName.SPIRIT,)),
    NinePartsDependencyRelation(NinePartName.NEMESIS,   ()),
    NinePartsDependencyRelation(NinePartName.SWORD,     ()),
    NinePartsDependencyRelation(NinePartName.NODE,      ()),
)

_DEPENDENCY_RELATION_BY_NAME: dict[NinePartName, NinePartsDependencyRelation] = {
    r.part: r for r in _ALL_DEPENDENCY_RELATIONS
}


@dataclass(slots=True)
class NinePartsSet:
    """
    RITE: The Sacred Ninefold — the complete set of Abu Ma'shar's Nine Parts
    computed from a single natal chart, carrying the ordered parts, the
    night-chart flag, the policy used, and the full dependency graph.

    THEOREM: Relational vessel that groups nine NinePart results with their
    inter-lot dependency relations. Provides inspectability over the set as
    a whole.

    Structural invariants:
        - parts contains exactly 9 NinePart instances.
        - parts are in canonical Abu Ma'shar order (Fortune → Node).
        - all parts share the same is_night_chart value.
        - dependency_relations contains exactly 9 entries.
    """
    parts:                list[NinePart]
    is_night_chart:       bool
    policy:               NinePartsPolicy
    dependency_relations: list[NinePartsDependencyRelation]

    def __post_init__(self) -> None:
        if len(self.parts) != 9:
            raise ValueError(
                f"NinePartsSet invariant: must contain exactly 9 parts, "
                f"got {len(self.parts)}"
            )
        if len(self.dependency_relations) != 9:
            raise ValueError(
                f"NinePartsSet invariant: must contain exactly 9 dependency "
                f"relations, got {len(self.dependency_relations)}"
            )
        expected_order = list(NinePartName)
        actual_order = [part.name for part in self.parts]
        if actual_order != expected_order:
            raise ValueError(
                "NinePartsSet invariant: parts must be in canonical Abu Ma'shar order"
            )
        expected_relation_order = list(NinePartName)
        actual_relation_order = [relation.part for relation in self.dependency_relations]
        if actual_relation_order != expected_relation_order:
            raise ValueError(
                "NinePartsSet invariant: dependency_relations must be in canonical Abu Ma'shar order"
            )
        for part in self.parts:
            if part.computation.is_night_chart != self.is_night_chart:
                raise ValueError(
                    f"NinePartsSet invariant: all parts must share the same "
                    f"is_night_chart value"
                )

    # -----------------------------------------------------------------------
    # Phase 6 — Relational Hardening / Inspectability
    # -----------------------------------------------------------------------

    def get(self, name: NinePartName) -> NinePart:
        """Return the part by canonical name. Raises KeyError if not found."""
        for part in self.parts:
            if part.name is name:
                return part
        raise KeyError(f"Nine Part {name!r} not found in set")

    def get_dependency_relation(self, name: NinePartName) -> NinePartsDependencyRelation:
        """Return the dependency relation for the named part."""
        for rel in self.dependency_relations:
            if rel.part is name:
                return rel
        raise KeyError(f"Dependency relation for {name!r} not found")

    @property
    def direct_parts(self) -> list[NinePart]:
        """Parts whose formulas use only raw planet longitudes."""
        return [p for p in self.parts if not p.is_derived]

    @property
    def derived_parts(self) -> list[NinePart]:
        """Parts whose formulas use other computed lots as ingredients."""
        return [p for p in self.parts if p.is_derived]

    @property
    def nocturnal_formula_count(self) -> int:
        """Number of parts computed with the night formula."""
        return sum(1 for p in self.parts if p.is_nocturnal_formula)

    @property
    def planetary_parts(self) -> list[NinePart]:
        """The seven parts that have a planet association (excludes Sword and Node)."""
        return [p for p in self.parts if p.has_planet_association]

    @property
    def nodal_parts(self) -> list[NinePart]:
        """The two parts without a planet association: Sword and Node."""
        return [p for p in self.parts if not p.has_planet_association]

    @property
    def historical_core_parts(self) -> list[NinePart]:
        """The seven historically evidenced planetary lots."""
        return [p for p in self.parts if p.is_historically_evidenced_core]

    @property
    def admitted_extension_parts(self) -> list[NinePart]:
        """The admitted extension lots preserved beyond the evidenced core."""
        return [p for p in self.parts if not p.is_historically_evidenced_core]

    def __repr__(self) -> str:
        mode = "nocturnal" if self.is_night_chart else "diurnal"
        return (
            f"NinePartsSet({mode}, "
            f"{len(self.derived_parts)} derived, "
            f"{len(self.nodal_parts)} nodal)"
        )


# ---------------------------------------------------------------------------
# Phase 7 — Integrated Local Condition
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class NinePartConditionProfile:
    """
    Integrated per-part condition profile.

    Combines the computed part position, its dependency relation, and the
    sign ruler (lord of the part) into a single coherent unit per part.

    part
        The NinePart result vessel.
    dependency_relation
        The inter-lot dependency relation for this part.
    lord
        The traditional domicile ruler of the sign the part falls in.
        Always one of the seven classical planets.
    lord_is_part_planet
        True when the lord of the part is the same planet as the part's
        own planet association (e.g. Fortune in Cancer → lord is Moon,
        which is Fortune's planet association).
    """
    part:               NinePart
    dependency_relation: NinePartsDependencyRelation
    lord:               str
    lord_is_part_planet: bool

    def __post_init__(self) -> None:
        if self.dependency_relation.part is not self.part.name:
            raise ValueError(
                "NinePartConditionProfile invariant: dependency_relation.part must match part.name"
            )
        expected_lord = _SIGN_RULER.get(self.part.sign)
        if expected_lord is None:
            raise ValueError(
                f"NinePartConditionProfile invariant: unrecognised sign "
                f"{self.part.sign!r}"
            )
        if self.lord != expected_lord:
            raise ValueError(
                f"NinePartConditionProfile invariant: lord must be "
                f"{expected_lord!r} for sign {self.part.sign!r}, got {self.lord!r}"
            )
        expected_match = (self.part.planet_association == self.lord)
        if self.lord_is_part_planet != expected_match:
            raise ValueError(
                "NinePartConditionProfile invariant: lord_is_part_planet "
                "must match (part.planet_association == lord)"
            )

    @property
    def is_in_own_sign(self) -> bool:
        """
        True when the part falls in the sign whose ruler is the part's own
        planet (i.e. the lord of the part is the part's associated planet).
        """
        return self.lord_is_part_planet

    @property
    def is_derived(self) -> bool:
        """Convenience delegation to part.is_derived."""
        return self.part.is_derived


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate Intelligence
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class NinePartsAggregate:
    """
    Chart-wide aggregate intelligence built from the Nine Parts set and its
    per-part condition profiles.

    parts_set
        The complete NinePartsSet for the chart.
    condition_profiles
        Per-part condition profiles in canonical order (Fortune → Node).
    policy
        The doctrinal policy used for this computation.
    parts_in_own_sign
        Parts where the lord of the part is the part's own planet association.
    unique_lords
        Distinct lords across all nine parts (how many planets govern the set).
    dominant_lord
        The planet that lords over the most parts. None if there is a tie.
    """
    parts_set:          NinePartsSet
    condition_profiles: list[NinePartConditionProfile]
    policy:             NinePartsPolicy

    def __post_init__(self) -> None:
        if len(self.condition_profiles) != 9:
            raise ValueError(
                f"NinePartsAggregate invariant: must have exactly 9 condition "
                f"profiles, got {len(self.condition_profiles)}"
            )
        expected_profile_order = list(NinePartName)
        actual_profile_order = [profile.part.name for profile in self.condition_profiles]
        if actual_profile_order != expected_profile_order:
            raise ValueError(
                "NinePartsAggregate invariant: condition_profiles must be in canonical Abu Ma'shar order"
            )
        if any(profile.part is not part for profile, part in zip(self.condition_profiles, self.parts_set.parts)):
            raise ValueError(
                "NinePartsAggregate invariant: condition_profiles must align one-to-one with parts_set.parts"
            )
        if self.policy is not self.parts_set.policy:
            raise ValueError(
                "NinePartsAggregate invariant: aggregate policy must match parts_set policy"
            )

    @property
    def parts_in_own_sign(self) -> list[NinePart]:
        """Parts whose lord is the part's own planet association."""
        return [cp.part for cp in self.condition_profiles if cp.is_in_own_sign]

    @property
    def unique_lords(self) -> list[str]:
        """Distinct lord planets across all nine parts, in Chaldean order."""
        chaldean = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
        seen = {cp.lord for cp in self.condition_profiles}
        return [p for p in chaldean if p in seen]

    @property
    def dominant_lord(self) -> str | None:
        """
        The planet that lords over the most parts. None if two or more planets
        tie for the highest count.
        """
        from collections import Counter
        counts = Counter(cp.lord for cp in self.condition_profiles)
        if not counts:
            return None
        top = counts.most_common(2)
        if len(top) == 1 or top[0][1] > top[1][1]:
            return top[0][0]
        return None  # tie

    def get_profile(self, name: NinePartName) -> NinePartConditionProfile:
        """Return the condition profile for the named part."""
        for cp in self.condition_profiles:
            if cp.part.name is name:
                return cp
        raise KeyError(f"Condition profile for {name!r} not found")

    def __repr__(self) -> str:
        mode = "nocturnal" if self.parts_set.is_night_chart else "diurnal"
        dom = self.dominant_lord or "tied"
        return (
            f"NinePartsAggregate({mode}, dominant_lord={dom}, "
            f"in_own_sign={len(self.parts_in_own_sign)})"
        )


# ---------------------------------------------------------------------------
# Phase 1 / Engine — Core Computation
# ---------------------------------------------------------------------------

def nine_parts_abu_mashar(
    asc: float,
    planets: dict[str, float],
    is_night_chart: bool,
    policy: NinePartsPolicy = DEFAULT_NINE_PARTS_POLICY,
) -> NinePartsAggregate:
    """
    Compute Abu Ma'shar's Nine Hermetic Lots for a chart.

    Parameters
    ----------
    asc : float
        Ascendant longitude in degrees [0, 360).
    planets : dict[str, float]
        Mapping of planet names to ecliptic longitudes. Must include at
        minimum: 'Sun', 'Moon', 'Mars', 'Jupiter', 'Saturn', 'North Node'.
        All longitudes must be finite. Values are normalized modulo 360
        before formula evaluation.
    is_night_chart : bool
        True when the chart is nocturnal (Sun in houses 1–6, i.e. below
        the horizon). The caller is responsible for this determination.
        Moira's house calculation functions can be used to derive it.
    policy : NinePartsPolicy
        Doctrinal configuration. Defaults to DEFAULT_NINE_PARTS_POLICY
        (FULL_REVERSAL).

    Returns
    -------
    NinePartsAggregate
        Complete nine-parts result including all parts, dependency relations,
        per-part condition profiles, and aggregate intelligence.

    Raises
    ------
    KeyError
        If a required planet key is missing from the planets dict.
    ValueError
        If any longitude is not finite, or if `is_night_chart` / `policy`
        are malformed.

    Notes
    -----
    Dependency order: Fortune and Spirit are resolved first. Love, Necessity,
    and Victory depend on them. The engine enforces this internally.

    Night reversal (FULL_REVERSAL): for night charts, the add and sub
    operands are swapped for all nine parts. There are no per-lot exceptions
    in the Abu Ma'shar system.
    """
    _validate_inputs(asc, planets)
    _validate_runtime_inputs(is_night_chart, policy)

    full_reversal = (
        is_night_chart
        and policy.reversal_rule is NinePartsReversalRule.FULL_REVERSAL
    )

    # Resolve raw planet longitudes
    refs: dict[str, float] = {}
    for key, lon in planets.items():
        refs[key] = lon % 360.0

    # Computed parts accumulate here for inter-lot dependency resolution
    computed_lons: dict[str, float] = {}

    parts: list[NinePart] = []

    for name_str, planet_assoc, meaning, day_add_key, day_sub_key in _NINE_PARTS_CATALOGUE:
        part_name = NinePartName(name_str)

        # Determine effective operands after reversal
        if full_reversal:
            add_key = day_sub_key
            sub_key = day_add_key
            formula_variant = NinePartFormulaVariant.NIGHT
        else:
            add_key = day_add_key
            sub_key = day_sub_key
            formula_variant = NinePartFormulaVariant.DAY

        # Resolve operand longitudes — check computed lots before raw planets
        add_lon = _resolve_key(add_key, refs, computed_lons)
        sub_lon = _resolve_key(sub_key, refs, computed_lons)

        # Compute the part longitude
        lon = (asc + add_lon - sub_lon) % 360.0
        computed_lons[name_str] = lon

        # Determine dependency kind
        dep_kind = (
            NinePartDependencyKind.DERIVED
            if name_str in _DERIVED_PARTS
            else NinePartDependencyKind.DIRECT
        )

        sign_name, sign_sym, sign_deg = sign_of(lon)

        computation = NinePartComputationTruth(
            asc_longitude    = asc % 360.0,
            add_key          = add_key,
            sub_key          = sub_key,
            add_longitude    = add_lon,
            sub_longitude    = sub_lon,
            is_night_chart   = is_night_chart,
            formula_reversed = full_reversal,
            formula_variant  = formula_variant,
            formula          = f"Asc + {add_key} − {sub_key}",
        )

        parts.append(NinePart(
            name               = part_name,
            planet_association = planet_assoc,
            meaning            = meaning,
            longitude          = lon,
            sign               = sign_name,
            sign_degree        = sign_deg,
            sign_symbol        = sign_sym,
            dependency_kind    = dep_kind,
            computation        = computation,
        ))

    # Build dependency relations
    dep_relations = [_DEPENDENCY_RELATION_BY_NAME[p.name] for p in parts]

    parts_set = NinePartsSet(
        parts                = parts,
        is_night_chart       = is_night_chart,
        policy               = policy,
        dependency_relations = dep_relations,
    )

    # Build condition profiles
    profiles: list[NinePartConditionProfile] = []
    for part in parts:
        lord = _SIGN_RULER[part.sign]
        profiles.append(NinePartConditionProfile(
            part                = part,
            dependency_relation = _DEPENDENCY_RELATION_BY_NAME[part.name],
            lord                = lord,
            lord_is_part_planet = (part.planet_association == lord),
        ))

    return NinePartsAggregate(
        parts_set          = parts_set,
        condition_profiles = profiles,
        policy             = policy,
    )


# ---------------------------------------------------------------------------
# Phase 10 — Full-Subsystem Hardening
# ---------------------------------------------------------------------------

def validate_nine_parts_output(aggregate: NinePartsAggregate) -> list[str]:
    """
    Validate the internal consistency of a NinePartsAggregate result.

    Returns a list of failure strings. An empty list means the output is
    fully consistent.

    Checks:
    1. Exactly 9 parts present in canonical order.
    2. All parts share the same is_night_chart value.
    3. All nocturnal-formula flags match the aggregate night flag.
    4. Fortune and Spirit are always computed before derived parts.
    5. Derived parts (Love, Necessity, Victory) report DERIVED dependency kind.
    6. Direct parts report DIRECT dependency kind.
    7. All longitudes are finite and in [0, 360).
    8. All sign_degree values are in [0, 30).
    9. All sign names match their longitudes.
    10. Lord assignments match sign rulers.
    11. Condition profile count matches part count.
    12. Dependency relation count matches part count.
    """
    failures: list[str] = []
    parts = aggregate.parts_set.parts

    # Check 1 — count and order
    canonical_order = list(NinePartName)
    if len(parts) != 9:
        failures.append(f"Expected 9 parts, found {len(parts)}")
    else:
        for i, (part, expected_name) in enumerate(zip(parts, canonical_order)):
            if part.name is not expected_name:
                failures.append(
                    f"Part {i}: expected {expected_name!r}, got {part.name!r}"
                )

    # Check 2 & 3 — night consistency
    expected_night = aggregate.parts_set.is_night_chart
    for part in parts:
        if part.computation.is_night_chart != expected_night:
            failures.append(
                f"{part.name}: is_night_chart mismatch "
                f"(set={expected_night}, part={part.computation.is_night_chart})"
            )
        if part.computation.formula_reversed != expected_night:
            failures.append(
                f"{part.name}: formula_reversed={part.computation.formula_reversed} "
                f"but is_night_chart={expected_night} (FULL_REVERSAL requires they match)"
            )

    # Check 4 — Fortune and Spirit appear before derived parts
    names_so_far: list[str] = []
    for part in parts:
        if part.name in (NinePartName.LOVE, NinePartName.NECESSITY, NinePartName.VICTORY):
            required = _LOT_DEPENDENCIES[part.name.value]
            for req in required:
                if req not in names_so_far:
                    failures.append(
                        f"{part.name} appears before its dependency {req!r}"
                    )
        names_so_far.append(part.name.value)

    # Checks 5 & 6 — dependency kind classification
    for part in parts:
        expected_kind = (
            NinePartDependencyKind.DERIVED
            if part.name.value in _DERIVED_PARTS
            else NinePartDependencyKind.DIRECT
        )
        if part.dependency_kind is not expected_kind:
            failures.append(
                f"{part.name}: dependency_kind should be {expected_kind!r}, "
                f"got {part.dependency_kind!r}"
            )

    # Checks 7, 8, 9 — longitude and sign geometry
    for part in parts:
        if not isfinite(part.longitude):
            failures.append(f"{part.name}: longitude is not finite")
        elif not (0.0 <= part.longitude < 360.0):
            failures.append(f"{part.name}: longitude {part.longitude} not in [0, 360)")
        if not (0.0 <= part.sign_degree < 30.0):
            failures.append(
                f"{part.name}: sign_degree {part.sign_degree} not in [0, 30)"
            )
        computed_sign, _, _ = sign_of(part.longitude)
        if part.sign != computed_sign:
            failures.append(
                f"{part.name}: sign {part.sign!r} does not match "
                f"sign_of({part.longitude}) = {computed_sign!r}"
            )

    # Check 10 — lord assignments
    for cp in aggregate.condition_profiles:
        expected_lord = _SIGN_RULER.get(cp.part.sign)
        if cp.lord != expected_lord:
            failures.append(
                f"{cp.part.name}: lord {cp.lord!r} does not match "
                f"sign ruler for {cp.part.sign!r} ({expected_lord!r})"
            )

    # Check 11 — profile count
    if len(aggregate.condition_profiles) != 9:
        failures.append(
            f"Expected 9 condition profiles, found {len(aggregate.condition_profiles)}"
        )

    # Check 12 — dependency relation count
    if len(aggregate.parts_set.dependency_relations) != 9:
        failures.append(
            f"Expected 9 dependency relations, found "
            f"{len(aggregate.parts_set.dependency_relations)}"
        )

    return failures


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_inputs(asc: float, planets: dict[str, float]) -> None:
    """Raise ValueError for malformed inputs at the system boundary."""
    if not isfinite(asc):
        raise ValueError(f"asc must be finite, got {asc}")
    required = {"Sun", "Moon", "Mars", "Jupiter", "Saturn", "North Node"}
    missing = required - planets.keys()
    if missing:
        raise KeyError(f"planets dict missing required keys: {missing!r}")
    for key, lon in planets.items():
        if not isfinite(lon):
            raise ValueError(f"planets[{key!r}] longitude must be finite, got {lon}")


def _validate_runtime_inputs(
    is_night_chart: bool,
    policy: NinePartsPolicy,
) -> None:
    """Raise ValueError for malformed non-coordinate runtime inputs."""
    if not isinstance(is_night_chart, bool):
        raise ValueError("is_night_chart must be a bool")
    if not isinstance(policy, NinePartsPolicy):
        raise ValueError("policy must be a NinePartsPolicy")


def _resolve_key(
    key: str,
    refs: dict[str, float],
    computed_lons: dict[str, float],
) -> float:
    """
    Resolve a formula key to a longitude.

    Checks computed lots first (Fortune, Spirit) then raw planet refs.
    Raises KeyError if the key cannot be resolved.
    """
    if key in computed_lons:
        return computed_lons[key]
    if key in refs:
        return refs[key]
    raise KeyError(
        f"Cannot resolve formula key {key!r}: not in computed lots or planet refs"
    )
