"""
Moira — Lord of the Turn Engine
Governs computation of the annual Lord of the Turn using Al-Qabisi's succession-hierarchy method and the Egyptian/Al-Sijzi testimony method.

Boundary: owns profection arithmetic, the two Lord of the Turn algorithms, condition assessment in the SR chart, candidate selection logic, result vessels, and aggregate intelligence. Delegates dignity tables to moira.dignities and moira.egyptian_bounds.

Import-time side effects: None

External dependencies:
    - dataclasses for structured data definitions
    - enum for enumeration types
    - math module for mathematical operations
    - moira.constants for sign and body definitions
    - moira.dignities for dignity tables
    - moira.egyptian_bounds for bound calculations
    - moira.triplicity for triplicity rulers

Public surface:
    LordOfTurnMethod, LordOfTurnSelectionReason, LordOfTurnBlockerReason,
    LordOfTurnPolicy, DEFAULT_LORD_OF_TURN_POLICY, LordOfTurnSRChart,
    LordOfTurnProfection, LordOfTurnCandidateAssessment, LordOfTurnResult,
    LordOfTurnConditionProfile, lord_of_turn, lord_of_turn_al_qabisi,
    lord_of_turn_egyptian_al_sijzi, validate_lord_of_turn_output
"""

from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite

from .constants import sign_of, SIGNS
from .dignities import DOMICILE, EXALTATION
from .egyptian_bounds import EGYPTIAN_BOUNDS
from .triplicity import triplicity_assignment_for as _triplicity_assignment_for


# ---------------------------------------------------------------------------
# Phase 12 — Public API Curation
# ---------------------------------------------------------------------------

__all__ = [
    # Classification
    "LordOfTurnMethod",
    "LordOfTurnSelectionReason",
    "LordOfTurnBlockerReason",
    # Policy
    "LordOfTurnPolicy",
    "DEFAULT_LORD_OF_TURN_POLICY",
    # Input vessel
    "LordOfTurnSRChart",
    # Truth-preservation vessels
    "LordOfTurnProfection",
    "LordOfTurnCandidateAssessment",
    "LordOfTurnResult",
    # Condition vessel
    "LordOfTurnConditionProfile",
    # Computation functions
    "lord_of_turn",
    "lord_of_turn_al_qabisi",
    "lord_of_turn_egyptian_al_sijzi",
    # Validation
    "validate_lord_of_turn_output",
]


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_CLASSICAL_PLANETS: frozenset[str] = frozenset(
    {"Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"}
)

# Houses considered "good place" in Al-Qabisi's SR condition check.
# Angular (1,4,7,10) + succedent (2,5,11) — note 8th is excluded as
# a house of death/loss even though technically succedent.
_GOOD_HOUSES: frozenset[int] = frozenset({1, 2, 4, 5, 7, 10, 11})

# Cadent houses — trigger the "blocked" condition for the primary candidate.
_CADENT_HOUSES: frozenset[int] = frozenset({3, 6, 9, 12})

# Major aspect distances in whole signs (Ptolemaic, for witnessing check).
# diff = (planet_sign_idx - target_sign_idx) % 12
_WITNESSING_DIFFS: frozenset[int] = frozenset({0, 2, 3, 4, 6, 8, 9, 10})


# ---------------------------------------------------------------------------
# Phase 2 — Classification namespaces
# ---------------------------------------------------------------------------

class LordOfTurnMethod(StrEnum):
    """
    Which Lord of the Turn algorithm is applied.

    AL_QABISI
        Succession-hierarchy method. The domicile lord of the profected sign
        is the primary candidate. Condition-based blockers (cadent, combust,
        retrograde) cause fallback to exaltation lord, then sect triplicity
        ruler, then bound lord. Tiebreaker via SR sect light aspect.
        Source: Al-Qabisi (Alcabitius), Introduction; Burnett/Yamamoto/Yano
        translation (Warburg Institute, 2004).

    EGYPTIAN_AL_SIJZI
        Testimony-based method. The bound lord of the profected degree is
        primary (Egyptian tradition). Al-Sijzi refinement: requires the
        winning planet to "witness" (be in a sign casting a major aspect to)
        the SR ASC or sect light. If the bound lord does not witness, the
        testimony winner that does witness becomes the Lord of the Turn.
        Source: Al-Sijzi, Introduction to the Book of the Indications of the
        Celestial Signs; Egyptian tradition as transmitted in Arabic sources.
    """
    AL_QABISI        = "al_qabisi"
    EGYPTIAN_AL_SIJZI = "egyptian_al_sijzi"


class LordOfTurnSelectionReason(StrEnum):
    """
    Why a specific planet was selected as Lord of the Turn.

    DOMICILE_WELL_PLACED
        Al-Qabisi: primary candidate (domicile lord of profected sign) was
        well-placed in the SR chart.
    EXALTATION_FALLBACK
        Al-Qabisi: domicile lord was blocked; exaltation lord passed condition.
    TRIPLICITY_FALLBACK
        Al-Qabisi: domicile and exaltation lords blocked; sect triplicity ruler
        was angular in the SR.
    BOUND_FALLBACK
        Al-Qabisi: all above blocked; bound lord is used as last resort.
    BOUND_PRIMARY_WITNESSING
        Egyptian/Al-Sijzi: bound lord of profected degree witnesses SR ASC or
        sect light.
    TESTIMONY_WINNER_WITNESSING
        Egyptian/Al-Sijzi: bound lord does not witness; testimony winner
        (most dignities at degree) that witnesses is selected.
    DOMICILE_ONLY
        No SR chart condition data provided; domicile lord returned without
        condition check (degenerate/minimal mode).
    """
    DOMICILE_WELL_PLACED          = "domicile_well_placed"
    EXALTATION_FALLBACK           = "exaltation_fallback"
    TRIPLICITY_FALLBACK           = "triplicity_fallback"
    BOUND_FALLBACK                = "bound_fallback"
    BOUND_PRIMARY_WITNESSING      = "bound_primary_witnessing"
    TESTIMONY_WINNER_WITNESSING   = "testimony_winner_witnessing"
    DOMICILE_ONLY                 = "domicile_only"


class LordOfTurnBlockerReason(StrEnum):
    """Why a candidate planet was rejected during succession evaluation."""
    CADENT_IN_SR   = "cadent_in_sr"     # in 3rd, 6th, 9th, or 12th SR house
    COMBUST        = "combust"          # within combust_orb of SR Sun
    RETROGRADE     = "retrograde"       # retrograde in SR
    NOT_WITNESSING = "not_witnessing"   # does not aspect SR ASC or sect light
    NO_TESTIMONY   = "no_testimony"     # holds no dignity at the profected degree


# ---------------------------------------------------------------------------
# Phase 4 — Doctrine / Policy Surface
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class LordOfTurnPolicy:
    """
    Doctrinal configuration surface for the Lord of the Turn engine.

    method
        Which algorithm to apply. Default: AL_QABISI.
    combust_orb
        Degree orb within which a planet is considered combust by the Sun.
        Default: 8.5° (traditional standard).
    """
    method:       LordOfTurnMethod = LordOfTurnMethod.AL_QABISI
    combust_orb:  float            = 8.5


DEFAULT_LORD_OF_TURN_POLICY: LordOfTurnPolicy = LordOfTurnPolicy()


# ---------------------------------------------------------------------------
# Input vessel — Solar Return Chart data
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LordOfTurnSRChart:
    """
    Input vessel carrying the Solar Return chart data needed for Lord of the
    Turn computation.

    The caller is responsible for constructing this from the SR chart. The
    Lord of the Turn engine reads from this vessel but does not write to it.

    sr_asc
        SR Ascendant longitude in degrees [0, 360).
    planets
        SR planet longitudes. Required keys depend on the method; at minimum:
        'Sun', 'Moon'. Provide all seven classical planets for full evaluation.
    house_placements
        SR planet → 1-based house number. If omitted, condition checks that
        depend on house placement are skipped (engine falls to DOMICILE_ONLY).
    is_night
        True when the SR is nocturnal (SR Sun below SR horizon).
    retrograde_planets
        Set of planet names that are retrograde in the SR. Default: empty.
    sr_lot_fortune
        Longitude of the Lot of Fortune in the SR chart, computed by the
        caller with sect reversal applied. None if not available.
    """
    sr_asc:             float
    planets:            dict[str, float]
    house_placements:   dict[str, int]   = field(default_factory=dict)
    is_night:           bool             = False
    retrograde_planets: frozenset[str]   = field(default_factory=frozenset)
    sr_lot_fortune:     float | None     = None

    def __post_init__(self) -> None:
        if not isfinite(self.sr_asc):
            raise ValueError(
                f"LordOfTurnSRChart: sr_asc must be finite, got {self.sr_asc}"
            )
        for key, lon in self.planets.items():
            if not isfinite(lon):
                raise ValueError(
                    f"LordOfTurnSRChart: planets[{key!r}] must be finite, got {lon}"
                )

    @property
    def sect_light(self) -> str:
        """Sun for day charts, Moon for night charts."""
        return "Moon" if self.is_night else "Sun"

    @property
    def sect_light_longitude(self) -> float | None:
        """Longitude of the sect light in the SR, or None if not in planets."""
        return self.planets.get(self.sect_light)


# ---------------------------------------------------------------------------
# Phase 1 — Truth Preservation
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class LordOfTurnProfection:
    """
    Result of the natal Ascendant profection step.

    natal_asc
        The natal Ascendant longitude used as the root.
    age
        The native's completed age in years (0 = first year).
    profected_longitude
        The profected longitude: (age * 30 + natal_asc) % 360.
    profected_sign
        The sign the profected longitude falls in (Sign of the Year).
    profected_degree_in_sign
        Degree within the profected sign [0, 30).
    profected_sign_index
        0-based index of the profected sign (0 = Aries).
    """
    natal_asc:                float
    age:                      int
    profected_longitude:      float
    profected_sign:           str
    profected_degree_in_sign: float
    profected_sign_index:     int

    def __post_init__(self) -> None:
        if self.age < 0:
            raise ValueError(
                f"LordOfTurnProfection: age must be >= 0, got {self.age}"
            )
        if not (0.0 <= self.profected_longitude < 360.0):
            raise ValueError(
                f"LordOfTurnProfection: profected_longitude must be in [0, 360), "
                f"got {self.profected_longitude}"
            )
        if not (0.0 <= self.profected_degree_in_sign < 30.0):
            raise ValueError(
                f"LordOfTurnProfection: profected_degree_in_sign must be in [0, 30), "
                f"got {self.profected_degree_in_sign}"
            )


@dataclass(slots=True, frozen=True)
class LordOfTurnCandidateAssessment:
    """
    Condition assessment of one candidate planet evaluated in the SR chart.

    planet
        The candidate planet name.
    role
        Why this planet is a candidate: 'domicile', 'exaltation',
        'triplicity', 'bound', 'testimony'.
    sr_house
        SR house placement (1–12), or None if house_placements not provided.
    is_combust
        True when within combust_orb of the SR Sun.
    is_retrograde
        True when the planet is retrograde in the SR.
    is_well_placed
        True when in a good SR house (1,2,4,5,7,10,11) AND not combust AND
        not retrograde.
    blocker_reasons
        Which blockers fired (empty if well-placed).
    witnesses_target
        True when this planet is in a sign that casts a major whole-sign
        Ptolemaic aspect to the SR Ascendant OR to the SR sect light sign
        (Sun for day charts, Moon for night charts).
        This is the primary witnessing criterion in the Egyptian/Al-Sijzi
        method (directly sourced: Al-Sijzi requires the lord to witness the
        SR ASC or sect light). In Al-Qabisi mode the field is informational
        only — the sequential succession hierarchy never applies a witnessing
        tiebreaker.
    testimony_count
        Number of the five dignity types this planet holds at the profected
        longitude (domicile=1, exaltation=1, triplicity=1, bound=1, face=1).
        Used in the Egyptian/Al-Sijzi testimony ranking.
    """
    planet:           str
    role:             str
    sr_house:         int | None
    is_combust:       bool
    is_retrograde:    bool
    is_well_placed:   bool
    blocker_reasons:  tuple[LordOfTurnBlockerReason, ...]
    witnesses_target: bool
    testimony_count:  int

    def __post_init__(self) -> None:
        if self.sr_house is not None and self.sr_house not in range(1, 13):
            raise ValueError(
                f"LordOfTurnCandidateAssessment: sr_house must be in [1, 12] "
                f"or None, got {self.sr_house}"
            )
        expected_well_placed = (
            (self.sr_house in _GOOD_HOUSES if self.sr_house is not None else True)
            and not self.is_combust
            and not self.is_retrograde
        )
        if self.is_well_placed != expected_well_placed:
            raise ValueError(
                f"LordOfTurnCandidateAssessment: is_well_placed={self.is_well_placed} "
                f"does not match computed value {expected_well_placed}"
            )


@dataclass(slots=True, frozen=True)
class LordOfTurnResult:
    """
    RITE: The Turn Vessel — the planet governing a given solar return year as
    Lord of the Turn, carrying the profection, all candidate assessments, the
    selection reason, and the method used.

    THEOREM: Primary result vessel for the Lord of the Turn engine. Preserves
    the complete decision path so that every selection can be audited.

    RITE OF PURPOSE:
        LordOfTurnResult is the atomic output of lord_of_turn(). Without it,
        callers would receive a bare planet name with no audit trail. The full
        candidate list shows which planets were considered, why each was
        accepted or rejected, and how the final selection was made.

    Structural invariants:
        - lord is one of the seven classical planets.
        - profection.profected_sign is the Sign of the Year.
        - candidates is non-empty.
        - selection_reason is consistent with the method used.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.lord_of_the_turn.LordOfTurnResult",
        "risk": "low",
        "api": {
            "frozen": [
                "lord", "method", "profection", "selection_reason", "candidates"
            ],
            "internal": []
        },
        "state": {"mutable": false},
        "effects": {"io": [], "signals_emitted": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "caller ensures valid inputs before construction"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    lord:             str
    method:           LordOfTurnMethod
    profection:       LordOfTurnProfection
    selection_reason: LordOfTurnSelectionReason
    candidates:       tuple[LordOfTurnCandidateAssessment, ...]

    def __post_init__(self) -> None:
        if self.lord not in _CLASSICAL_PLANETS:
            raise ValueError(
                f"LordOfTurnResult: lord must be a classical planet, got {self.lord!r}"
            )
        if not self.candidates:
            raise ValueError("LordOfTurnResult: candidates must be non-empty")

    # -----------------------------------------------------------------------
    # Phase 3 — Inspectability
    # -----------------------------------------------------------------------

    @property
    def sign_of_year(self) -> str:
        """The Sign of the Year (profected sign)."""
        return self.profection.profected_sign

    @property
    def age(self) -> int:
        """The native's completed age this result was computed for."""
        return self.profection.age

    @property
    def winning_candidate(self) -> LordOfTurnCandidateAssessment | None:
        """The candidate assessment for the selected lord, or None if not found."""
        for c in self.candidates:
            if c.planet == self.lord:
                return c
        return None

    @property
    def blocked_candidates(self) -> list[LordOfTurnCandidateAssessment]:
        """Candidates that were evaluated but rejected (not the winning planet)."""
        return [c for c in self.candidates if c.planet != self.lord]

    @property
    def is_fallback(self) -> bool:
        """True when the lord was not the primary candidate (domicile lord)."""
        return self.selection_reason not in (
            LordOfTurnSelectionReason.DOMICILE_WELL_PLACED,
            LordOfTurnSelectionReason.DOMICILE_ONLY,
            LordOfTurnSelectionReason.BOUND_PRIMARY_WITNESSING,
        )

    def __repr__(self) -> str:
        return (
            f"LordOfTurnResult(lord={self.lord!r}, age={self.age}, "
            f"sign={self.sign_of_year!r}, method={self.method.value}, "
            f"reason={self.selection_reason.value})"
        )


# ---------------------------------------------------------------------------
# Phase 7 — Integrated Local Condition
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LordOfTurnConditionProfile:
    """
    Integrated condition profile for a Lord of the Turn result.

    Combines the result with profection context, the sect light condition in
    the SR, and the lord's witnessing status.

    result
        The primary LordOfTurnResult vessel.
    sr_is_night
        Whether the SR was nocturnal.
    sect_light
        'Sun' for day SR, 'Moon' for night SR.
    lord_witnesses_sr_asc
        True when the lord is in a sign casting a major aspect to the SR ASC.
    lord_sr_house
        SR house of the lord, or None if not provided.
    """
    result:               LordOfTurnResult
    sr_is_night:          bool
    sect_light:           str
    lord_witnesses_sr_asc: bool
    lord_sr_house:        int | None

    @property
    def is_fallback(self) -> bool:
        """Delegation to result.is_fallback."""
        return self.result.is_fallback

    @property
    def lord(self) -> str:
        """The Lord of the Turn."""
        return self.result.lord

    @property
    def sign_of_year(self) -> str:
        """The Sign of the Year."""
        return self.result.sign_of_year


# ---------------------------------------------------------------------------
# Phase 1 / Engine — Core Computation
# ---------------------------------------------------------------------------

def lord_of_turn(
    natal_asc: float,
    age: int,
    sr_chart: LordOfTurnSRChart,
    policy: LordOfTurnPolicy = DEFAULT_LORD_OF_TURN_POLICY,
) -> LordOfTurnConditionProfile:
    """
    Compute the Lord of the Turn for a given solar return year.

    Dispatches to the method-specific engine selected by policy.method.

    Parameters
    ----------
    natal_asc : float
        Natal Ascendant longitude in degrees.
    age : int
        Native's completed age in years (0 = first year of life).
    sr_chart : LordOfTurnSRChart
        Solar return chart data vessel.
    policy : LordOfTurnPolicy
        Doctrinal configuration. Defaults to DEFAULT_LORD_OF_TURN_POLICY
        (AL_QABISI).

    Returns
    -------
    LordOfTurnConditionProfile
        Complete result with condition profile.
    """
    _validate_inputs(natal_asc, age)

    if policy.method is LordOfTurnMethod.AL_QABISI:
        result = lord_of_turn_al_qabisi(natal_asc, age, sr_chart, policy)
    else:
        result = lord_of_turn_egyptian_al_sijzi(natal_asc, age, sr_chart, policy)

    lord_sign_idx = _sign_idx(sr_chart.planets.get(result.lord, 0.0))
    asc_sign_idx  = _sign_idx(sr_chart.sr_asc)
    witnesses_asc = _witnesses(lord_sign_idx, asc_sign_idx)

    lord_sr_house = sr_chart.house_placements.get(result.lord)

    return LordOfTurnConditionProfile(
        result               = result,
        sr_is_night          = sr_chart.is_night,
        sect_light           = sr_chart.sect_light,
        lord_witnesses_sr_asc = witnesses_asc,
        lord_sr_house        = lord_sr_house,
    )


def lord_of_turn_al_qabisi(
    natal_asc: float,
    age: int,
    sr_chart: LordOfTurnSRChart,
    policy: LordOfTurnPolicy = DEFAULT_LORD_OF_TURN_POLICY,
) -> LordOfTurnResult:
    """
    Al-Qabisi succession-hierarchy Lord of the Turn.
    [DIRECTLY SOURCED: Al-Qabisi, Al-Madkhal; Burnett/Yamamoto/Yano 2004]

    Algorithm
    ---------
    Degenerate mode (house_placements empty): skips all condition checks
    and returns the domicile lord with reason DOMICILE_ONLY.
    [MOIRA FORMALIZATION — no historical equivalent for this degenerate mode]

    Full mode:
    1. Profect natal ASC: profected_lon = (age * 30 + natal_asc) % 360
    2. Identify Sign of the Year from profected_lon.
    3. Domicile lord of the Sign of the Year: check SR condition
       (in good house {1,2,4,5,7,10,11}, not combust, not retrograde).
       If passes → DOMICILE_WELL_PLACED.
    4. Exaltation lord (if different from domicile lord): same check.
       If passes → EXALTATION_FALLBACK.
    5. Sect-appropriate triplicity ruler (if not already assessed): must be
       angular in SR (houses 1,4,7,10). If passes → TRIPLICITY_FALLBACK.
       [HISTORICALLY GROUNDED RECONSTRUCTION: Al-Qabisi names triplicity
       rulers but the stricter angular-only test is a Moira reconstruction]
    6. Bound lord of the profected degree: returned as last resort
       regardless of condition → BOUND_FALLBACK.

    On tiebreaking: the succession model is sequential — each step returns
    immediately on the first qualifying candidate, so no two candidates are
    ever simultaneously "well-placed" in this engine. Tiebreaker language
    appearing in some source readings likely reflects a different (almuten-
    scoring) model of the same technique. [MOIRA FORMALIZATION]
    """
    _validate_inputs(natal_asc, age)
    profection = _compute_profection(natal_asc, age)

    # No SR house data → minimal mode
    if not sr_chart.house_placements:
        domicile_lord = _domicile_lord_of_sign(profection.profected_sign)
        tc = _testimony_count(domicile_lord, profection.profected_longitude, not sr_chart.is_night)
        sr_asc_idx_do = _sign_idx(sr_chart.sr_asc)
        dom_lon_do = sr_chart.planets.get(domicile_lord)
        if dom_lon_do is not None:
            dom_sidx = _sign_idx(dom_lon_do)
            sect_lon_do = sr_chart.sect_light_longitude
            sect_sidx_do = _sign_idx(sect_lon_do) if sect_lon_do is not None else sr_asc_idx_do
            wt = _witnesses(dom_sidx, sr_asc_idx_do) or _witnesses(dom_sidx, sect_sidx_do)
        else:
            wt = False
        candidate = LordOfTurnCandidateAssessment(
            planet           = domicile_lord,
            role             = "domicile",
            sr_house         = None,
            is_combust       = False,
            is_retrograde    = False,
            is_well_placed   = True,
            blocker_reasons  = (),
            witnesses_target = wt,
            testimony_count  = tc,
        )
        return LordOfTurnResult(
            lord             = domicile_lord,
            method           = LordOfTurnMethod.AL_QABISI,
            profection       = profection,
            selection_reason = LordOfTurnSelectionReason.DOMICILE_ONLY,
            candidates       = (candidate,),
        )

    all_candidates: list[LordOfTurnCandidateAssessment] = []
    sr_asc_idx = _sign_idx(sr_chart.sr_asc)

    # Helper: build a candidate assessment
    def _assess(planet: str, role: str) -> LordOfTurnCandidateAssessment:
        return _build_candidate(
            planet, role, sr_chart, policy,
            profection.profected_longitude,
            sr_asc_idx,
        )

    # Step 3-5: primary — domicile lord
    dom_lord = _domicile_lord_of_sign(profection.profected_sign)
    dom_assessment = _assess(dom_lord, "domicile")
    all_candidates.append(dom_assessment)
    if dom_assessment.is_well_placed:
        return LordOfTurnResult(
            lord             = dom_lord,
            method           = LordOfTurnMethod.AL_QABISI,
            profection       = profection,
            selection_reason = LordOfTurnSelectionReason.DOMICILE_WELL_PLACED,
            candidates       = tuple(all_candidates),
        )

    # Step 6: exaltation fallback
    exalt_lord = _exaltation_lord_of_sign(profection.profected_sign)
    if exalt_lord and exalt_lord != dom_lord:
        exalt_assessment = _assess(exalt_lord, "exaltation")
        all_candidates.append(exalt_assessment)
        if exalt_assessment.is_well_placed:
            return LordOfTurnResult(
                lord             = exalt_lord,
                method           = LordOfTurnMethod.AL_QABISI,
                profection       = profection,
                selection_reason = LordOfTurnSelectionReason.EXALTATION_FALLBACK,
                candidates       = tuple(all_candidates),
            )

    # Step 7: sect triplicity ruler (angular only — stricter than good place)
    trip_lord = _sect_triplicity_ruler(profection.profected_sign, sr_chart.is_night)
    if trip_lord and trip_lord not in {dom_lord, exalt_lord}:
        trip_assessment = _assess(trip_lord, "triplicity")
        all_candidates.append(trip_assessment)
        if trip_assessment.sr_house in {1, 4, 7, 10}:
            return LordOfTurnResult(
                lord             = trip_lord,
                method           = LordOfTurnMethod.AL_QABISI,
                profection       = profection,
                selection_reason = LordOfTurnSelectionReason.TRIPLICITY_FALLBACK,
                candidates       = tuple(all_candidates),
            )

    # Step 8: bound lord
    bound_lord = _bound_lord(
        profection.profected_sign,
        profection.profected_degree_in_sign,
    )
    if bound_lord not in {c.planet for c in all_candidates}:
        bound_assessment = _assess(bound_lord, "bound")
        all_candidates.append(bound_assessment)
    return LordOfTurnResult(
        lord             = bound_lord,
        method           = LordOfTurnMethod.AL_QABISI,
        profection       = profection,
        selection_reason = LordOfTurnSelectionReason.BOUND_FALLBACK,
        candidates       = tuple(all_candidates),
    )


def lord_of_turn_egyptian_al_sijzi(
    natal_asc: float,
    age: int,
    sr_chart: LordOfTurnSRChart,
    policy: LordOfTurnPolicy = DEFAULT_LORD_OF_TURN_POLICY,
) -> LordOfTurnResult:
    """
    Egyptian/Al-Sijzi testimony Lord of the Turn.
    [DIRECTLY SOURCED: Egyptian bound-lord tradition as transmitted in Al-Sijzi]

    Algorithm
    ---------
    1. Profect natal ASC: profected_lon = (age * 30 + natal_asc) % 360
    2. Identify Sign of the Year and degree within sign.
    3. Primary (Egyptian): bound lord of the profected degree.
    4. Check if the bound lord witnesses the SR ASC or SR sect light
       (is in a sign casting a major whole-sign Ptolemaic aspect to them).
       [DIRECTLY SOURCED: Al-Sijzi's witnessing requirement]
    5. If bound lord witnesses → BOUND_PRIMARY_WITNESSING.
    6. Otherwise: rank all seven classical planets by testimony count at the
       profected longitude (one point per dignity type: domicile, exaltation,
       triplicity, bound, face; maximum 5). [HISTORICALLY GROUNDED
       RECONSTRUCTION: binary counting is a Moira choice — some sources use
       the 5/4/3/2/1 weighting]
    7. Among those with testimony > 0, the one that witnesses SR ASC or sect
       light wins → TESTIMONY_WINNER_WITNESSING. Alphabetical tiebreak for
       determinism. [MOIRA FORMALIZATION for the tiebreak]
    8. If no testimony winner witnesses, return the bound lord anyway
       (BOUND_FALLBACK).
    """
    _validate_inputs(natal_asc, age)
    profection = _compute_profection(natal_asc, age)

    all_candidates: list[LordOfTurnCandidateAssessment] = []
    sr_asc_idx = _sign_idx(sr_chart.sr_asc)

    def _assess(planet: str, role: str) -> LordOfTurnCandidateAssessment:
        return _build_candidate(
            planet, role, sr_chart, policy,
            profection.profected_longitude,
            sr_asc_idx,
        )

    # Step 3: bound lord (Egyptian primary)
    bound_lord = _bound_lord(
        profection.profected_sign,
        profection.profected_degree_in_sign,
    )
    bound_assessment = _assess(bound_lord, "bound")
    all_candidates.append(bound_assessment)

    # Step 4-5: does bound lord witness SR ASC or sect light?
    if bound_assessment.witnesses_target:
        return LordOfTurnResult(
            lord             = bound_lord,
            method           = LordOfTurnMethod.EGYPTIAN_AL_SIJZI,
            profection       = profection,
            selection_reason = LordOfTurnSelectionReason.BOUND_PRIMARY_WITNESSING,
            candidates       = tuple(all_candidates),
        )

    # Step 6-7: testimony ranking among all planets that witness
    testimony_candidates: list[tuple[int, str, LordOfTurnCandidateAssessment]] = []
    for planet in sorted(_CLASSICAL_PLANETS):
        if planet == bound_lord:
            continue
        a = _assess(planet, "testimony")
        all_candidates.append(a)
        if a.testimony_count > 0 and a.witnesses_target:
            testimony_candidates.append((a.testimony_count, planet, a))

    if testimony_candidates:
        # Highest testimony count wins; alphabetical tiebreak for determinism
        testimony_candidates.sort(key=lambda t: (-t[0], t[1]))
        winner = testimony_candidates[0][2].planet
        return LordOfTurnResult(
            lord             = winner,
            method           = LordOfTurnMethod.EGYPTIAN_AL_SIJZI,
            profection       = profection,
            selection_reason = LordOfTurnSelectionReason.TESTIMONY_WINNER_WITNESSING,
            candidates       = tuple(all_candidates),
        )

    # Step 8: fallback — bound lord even without witnessing
    return LordOfTurnResult(
        lord             = bound_lord,
        method           = LordOfTurnMethod.EGYPTIAN_AL_SIJZI,
        profection       = profection,
        selection_reason = LordOfTurnSelectionReason.BOUND_FALLBACK,
        candidates       = tuple(all_candidates),
    )


# ---------------------------------------------------------------------------
# Phase 10 — Full-Subsystem Hardening
# ---------------------------------------------------------------------------

def validate_lord_of_turn_output(profile: LordOfTurnConditionProfile) -> list[str]:
    """
    Validate the internal consistency of a LordOfTurnConditionProfile result.

    Returns a list of failure strings. Empty = fully consistent.

    Checks:
    1. lord is a classical planet.
    2. profection.profected_longitude in [0, 360).
    3. profection.profected_degree_in_sign in [0, 30).
    4. profection.profected_sign matches profected_longitude.
    5. candidates is non-empty.
    6. Winning candidate planet matches lord.
    7. All candidate sr_house values in [1, 12] or None.
    8. All candidate testimony_count >= 0.
    9. is_well_placed consistency with blocker_reasons.
    10. profile.sect_light is 'Sun' or 'Moon'.
    """
    failures: list[str] = []
    result = profile.result

    # Check 1
    if result.lord not in _CLASSICAL_PLANETS:
        failures.append(f"lord {result.lord!r} is not a classical planet")

    # Check 2
    p = result.profection
    if not (0.0 <= p.profected_longitude < 360.0):
        failures.append(
            f"profected_longitude {p.profected_longitude} not in [0, 360)"
        )

    # Check 3
    if not (0.0 <= p.profected_degree_in_sign < 30.0):
        failures.append(
            f"profected_degree_in_sign {p.profected_degree_in_sign} not in [0, 30)"
        )

    # Check 4
    if p.profected_longitude is not None and isfinite(p.profected_longitude):
        computed_sign, _, _ = sign_of(p.profected_longitude)
        if p.profected_sign != computed_sign:
            failures.append(
                f"profected_sign {p.profected_sign!r} does not match "
                f"sign_of({p.profected_longitude}) = {computed_sign!r}"
            )

    # Check 5
    if not result.candidates:
        failures.append("candidates is empty")

    # Check 6
    winner_planets = [c.planet for c in result.candidates if c.planet == result.lord]
    if not winner_planets:
        failures.append(
            f"no candidate with planet={result.lord!r} found in candidates"
        )

    # Checks 7-9
    for c in result.candidates:
        if c.sr_house is not None and c.sr_house not in range(1, 13):
            failures.append(
                f"candidate {c.planet!r}: sr_house {c.sr_house} not in [1, 12]"
            )
        if c.testimony_count < 0:
            failures.append(
                f"candidate {c.planet!r}: testimony_count must be >= 0"
            )
        if c.is_well_placed and c.blocker_reasons:
            failures.append(
                f"candidate {c.planet!r}: is_well_placed=True but has blockers "
                f"{c.blocker_reasons!r}"
            )

    # Check 10
    if profile.sect_light not in ("Sun", "Moon"):
        failures.append(
            f"sect_light must be 'Sun' or 'Moon', got {profile.sect_light!r}"
        )

    return failures


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_profection(natal_asc: float, age: int) -> LordOfTurnProfection:
    """Compute the profected longitude and sign from natal ASC and age."""
    raw_lon   = (age * 30.0 + natal_asc) % 360.0
    sign_name, _, deg_in_sign = sign_of(raw_lon)
    sign_index = SIGNS.index(sign_name)
    return LordOfTurnProfection(
        natal_asc                = natal_asc % 360.0,
        age                      = age,
        profected_longitude      = raw_lon,
        profected_sign           = sign_name,
        profected_degree_in_sign = deg_in_sign,
        profected_sign_index     = sign_index,
    )


def _domicile_lord_of_sign(sign: str) -> str:
    """Return the traditional domicile ruler of the given sign."""
    for planet, signs in DOMICILE.items():
        if sign in signs:
            return planet
    raise ValueError(f"No domicile ruler found for sign {sign!r}")


def _exaltation_lord_of_sign(sign: str) -> str | None:
    """Return the exaltation ruler of the given sign, or None."""
    for planet, signs in EXALTATION.items():
        if sign in signs:
            return planet
    return None


def _sect_triplicity_ruler(sign: str, is_night: bool) -> str | None:
    """Return the sect-appropriate triplicity ruler (day or night)."""
    try:
        assignment = _triplicity_assignment_for(sign, is_day_chart=not is_night)
        return assignment.active_ruler
    except ValueError:
        return None


def _bound_lord(sign: str, degree_in_sign: float) -> str:
    """Return the Egyptian bound ruler for a given sign and degree within sign."""
    bounds = EGYPTIAN_BOUNDS.get(sign, [])
    for ruler, start, end in bounds:
        if start <= degree_in_sign < end:
            return ruler
    # Fallback: return the domicile lord (should not occur with complete table)
    return _domicile_lord_of_sign(sign)


def _is_combust(planet: str, planet_lon: float, sun_lon: float, orb: float) -> bool:
    """True when planet is within orb degrees of the Sun (combust)."""
    if planet in ("Sun", "Moon"):
        return False
    diff = abs((planet_lon - sun_lon + 180.0) % 360.0 - 180.0)
    return diff <= orb


def _sign_idx(longitude: float) -> int:
    """Return the 0-based sign index for a longitude."""
    sign_name, _, _ = sign_of(longitude % 360.0)
    return SIGNS.index(sign_name)


def _witnesses(planet_sign_idx: int, target_sign_idx: int) -> bool:
    """
    True when the planet's sign casts a major Ptolemaic aspect (whole-sign)
    to the target sign.

    Ptolemaic aspects: conjunction (0), sextile (2/10), square (3/9),
    trine (4/8), opposition (6).
    """
    diff = (planet_sign_idx - target_sign_idx) % 12
    return diff in _WITNESSING_DIFFS


def _testimony_count(planet: str, profected_lon: float, is_day: bool) -> int:
    """
    Count how many of the five dignity types a planet holds at the profected
    longitude (domicile, exaltation, triplicity, bound, face).

    One point per type, maximum 5. Uses binary (holds/does not hold) rather
    than the numeric (5/4/3/2/1) weighting — consistent with Al-Qabisi's
    hierarchical testimony model.
    """
    sign_name, _, deg_in_sign = sign_of(profected_lon % 360.0)
    count = 0

    if sign_name in DOMICILE.get(planet, []):
        count += 1
    if sign_name in EXALTATION.get(planet, []):
        count += 1

    assignment = _triplicity_assignment_for(sign_name, is_day_chart=is_day)
    if planet == assignment.active_ruler:
        count += 1
    elif planet == assignment.participating_ruler:
        count += 1

    for ruler, start, end in EGYPTIAN_BOUNDS.get(sign_name, []):
        if start <= deg_in_sign < end and ruler == planet:
            count += 1
            break

    lon_norm  = profected_lon % 360.0
    decan_idx = int(lon_norm // 10) % 36
    from .longevity import FACE_RULERS
    if FACE_RULERS[decan_idx] == planet:
        count += 1

    return count


def _build_candidate(
    planet: str,
    role: str,
    sr_chart: LordOfTurnSRChart,
    policy: LordOfTurnPolicy,
    profected_lon: float,
    sr_asc_idx: int,
) -> LordOfTurnCandidateAssessment:
    """Build a full condition assessment for one candidate planet."""
    sr_house = sr_chart.house_placements.get(planet)
    planet_lon = sr_chart.planets.get(planet)
    sun_lon    = sr_chart.planets.get("Sun", 0.0)

    combust = (
        _is_combust(planet, planet_lon, sun_lon, policy.combust_orb)
        if planet_lon is not None and "Sun" in sr_chart.planets
        else False
    )
    retro = planet in sr_chart.retrograde_planets

    blockers: list[LordOfTurnBlockerReason] = []
    if sr_house in _CADENT_HOUSES:
        blockers.append(LordOfTurnBlockerReason.CADENT_IN_SR)
    if combust:
        blockers.append(LordOfTurnBlockerReason.COMBUST)
    if retro:
        blockers.append(LordOfTurnBlockerReason.RETROGRADE)

    # well_placed: in good house AND not combust AND not retrograde
    # If no house data available, treat as well_placed (only combust/retro apply)
    in_good_house = (sr_house in _GOOD_HOUSES) if sr_house is not None else True
    well_placed   = in_good_house and not combust and not retro

    # Witnessing: planet's sign aspects the SR Ascendant OR the SR sect light.
    # Target = SR ASC or sect light (directly sourced for Egyptian/Al-Sijzi;
    # informational in Al-Qabisi mode where no tiebreaker is applied).
    planet_sign_idx = (
        _sign_idx(planet_lon) if planet_lon is not None else sr_asc_idx
    )
    sect_lon = sr_chart.sect_light_longitude
    sect_sign_idx = _sign_idx(sect_lon) if sect_lon is not None else sr_asc_idx

    witnesses_sr_asc = _witnesses(planet_sign_idx, sr_asc_idx)
    witnesses_sect   = _witnesses(planet_sign_idx, sect_sign_idx)
    witnesses_target = witnesses_sr_asc or witnesses_sect

    tc = _testimony_count(planet, profected_lon, not sr_chart.is_night)

    return LordOfTurnCandidateAssessment(
        planet           = planet,
        role             = role,
        sr_house         = sr_house,
        is_combust       = combust,
        is_retrograde    = retro,
        is_well_placed   = well_placed,
        blocker_reasons  = tuple(blockers),
        witnesses_target = witnesses_target,
        testimony_count  = tc,
    )


def _validate_inputs(natal_asc: float, age: int) -> None:
    """Raise ValueError for malformed inputs at the system boundary."""
    if not isfinite(natal_asc):
        raise ValueError(f"natal_asc must be finite, got {natal_asc}")
    if age < 0:
        raise ValueError(f"age must be >= 0, got {age}")
