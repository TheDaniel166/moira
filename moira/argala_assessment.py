"""Source-scoped Argala formation, count grades and bounded obstruction evidence.

BPHS/Santhanam 31, PVR 2000 10.6-10.7, and Rath's Argala article remain
distinct profiles. Unknown strength and quarter aggregation remain visible.
No Shadbala score, astronomical IO or predictive-outcome inference is made.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Literal

from ._jaimini_profile_inputs import (
    CLASSICAL,
    NINE,
    ArgalaReference,
    JaiminiChart,
    admit_chart,
    admit_references,
    chart_signs,
    finite_number,
    strict_int,
)
from ._jaimini_profile_results import result_invariants
from .jaimini_extended import _RASI_LORDS, rasi_drishti_of
from .jaimini_profile_policy import (
    ARGALA_IDS,
    CHARACTER_ID,
    VERSION,
    JaiminiProfile,
    admit_profile,
)

__all__ = [
    "ArgalaCharacter",
    "ArgalaCountGrade",
    "ArgalaQuarterWitness",
    "ArgalaEligibleBlockers",
    "ArgalaStrengthFactors",
    "ArgalaPairAssessment",
    "ArgalaSpecialThird",
    "ArgalaReferenceAssessment",
    "ArgalaAssessmentResult",
    "assess_argala",
]

_PAIRS = ((2, 12), (4, 10), (11, 3), (5, 9))
_REASONS = (
    "strength_comparator_not_admitted",
    "degrees_required",
    "multioccupant_quarter_composition_unestablished",
    "factor_priority_not_admitted",
)


def _bodies(values):
    if type(values) is not tuple or any(
        type(p) is not str or p not in NINE for p in values
    ):
        raise ValueError("body evidence must be a tuple of admitted names")
    if values != tuple(p for p in NINE if p in values):
        raise ValueError("body evidence must be distinct and canonically ordered")


def _records(values, cls):
    if type(values) is not tuple or any(type(v) is not cls for v in values):
        raise ValueError("evidence must be an immutable tuple of the declared vessel")
    for value in values:
        value.__post_init__()


@dataclass(frozen=True, slots=True)
class ArgalaCharacter:
    """Per-body natural character with an explicit missing-degree reason."""

    body: str
    state: Literal["benefic", "malefic", "indeterminate"]
    reason: Literal[
        "natural_benefic",
        "natural_malefic",
        "bright_half",
        "dark_half",
        "malefic_association",
        "no_malefic_association",
        "requires_longitude",
        "moon_association_unresolved",
    ]

    def __post_init__(self):
        if self.body not in NINE or self.state not in (
            "benefic",
            "malefic",
            "indeterminate",
        ):
            raise ValueError("invalid character evidence")
        if self.reason not in (
            "natural_benefic",
            "natural_malefic",
            "bright_half",
            "dark_half",
            "malefic_association",
            "no_malefic_association",
            "requires_longitude",
            "moon_association_unresolved",
        ):
            raise ValueError("invalid character reason")


@dataclass(frozen=True, slots=True)
class ArgalaCountGrade:
    """Ordinal BPHS count category; no scalar strength or auspiciousness score."""

    status: Literal["assessed", "not_assessed"]
    grade: Literal["none", "limited", "medium", "excellent"] | None
    rule_id: str | None

    def __post_init__(self):
        if (
            self.status == "not_assessed"
            and self.grade is None
            and self.rule_id is None
        ):
            return
        if (
            self.status == "assessed"
            and self.grade in ("none", "limited", "medium", "excellent")
            and self.rule_id == "bphs.31.formation"
        ):
            return
        raise ValueError("invalid count grade")


@dataclass(frozen=True, slots=True)
class ArgalaQuarterWitness:
    """Directed body pair in 7.5-degree sign quarters, with exact endpoint ownership."""

    causer: str
    blocker: str
    causer_degree: float
    blocker_degree: float
    causer_quarter: int
    blocker_quarter: int
    qualifies: bool

    def __post_init__(self):
        if (
            self.causer not in NINE
            or self.blocker not in NINE
            or self.causer == self.blocker
        ):
            raise ValueError("invalid quarter participants")
        for value in (self.causer_degree, self.blocker_degree):
            if not 0 <= finite_number(value, "within-sign degree") < 30:
                raise ValueError("within-sign degree out of range")
        strict_int(self.causer_quarter, 1, 4, "causer_quarter")
        strict_int(self.blocker_quarter, 1, 4, "blocker_quarter")
        if (
            self.causer_quarter != int(self.causer_degree // 7.5) + 1
            or self.blocker_quarter != int(self.blocker_degree // 7.5) + 1
        ):
            raise ValueError("quarter disagrees with within-sign degree")
        if type(self.qualifies) is not bool or self.qualifies != (
            (self.causer_quarter, self.blocker_quarter) in ((1, 4), (2, 3))
        ):
            raise ValueError("invalid directed quarter qualification")


@dataclass(frozen=True, slots=True)
class ArgalaEligibleBlockers:
    """Per-causer eligibility evidence without an invented group matching rule."""

    causer: str
    blockers: tuple[str, ...]

    def __post_init__(self):
        if self.causer not in NINE:
            raise ValueError("invalid causer")
        _bodies(self.blockers)


@dataclass(frozen=True, slots=True)
class ArgalaStrengthFactors:
    """Rath illustration factors; no universal priority or inferred winner."""

    side: Literal["causer", "blocker"]
    sign: int
    own_sign_bodies: tuple[str, ...]
    jupiter_rasi_aspect: bool

    def __post_init__(self):
        strict_int(self.sign, 0, 11, "factor sign")
        _bodies(self.own_sign_bodies)
        if (
            self.side not in ("causer", "blocker")
            or type(self.jupiter_rasi_aspect) is not bool
        ):
            raise ValueError("invalid strength factor")
        if any(p != _RASI_LORDS[self.sign] for p in self.own_sign_bodies):
            raise ValueError("own-sign witness must use classical sign lordship")


@dataclass(frozen=True, slots=True)
class ArgalaPairAssessment:
    """Formation, ordinal grade, character and qualified effect for one pair."""

    causer_house: int
    blocker_house: int
    causer_sign: int
    blocker_sign: int
    causers: tuple[str, ...]
    blockers: tuple[str, ...]
    formation_state: Literal["absent", "present"]
    count_grade: ArgalaCountGrade
    causer_character: Literal["none", "benefic", "malefic", "mixed", "indeterminate"]
    blocker_character: Literal["none", "benefic", "malefic", "mixed", "indeterminate"]
    effect_state: Literal["absent", "unobstructed", "obstructed", "indeterminate"]
    reason_codes: tuple[str, ...]
    strength_comparison: Literal["not_required", "indeterminate"]
    quarter_status: Literal["not_assessed", "unavailable", "no_pairs", "evaluated"]
    quarter_pairs: tuple[ArgalaQuarterWitness, ...]
    eligible_blockers: tuple[ArgalaEligibleBlockers, ...]
    strength_factors: tuple[ArgalaStrengthFactors, ...]

    @property
    def causer_count(self) -> int:
        return len(self.causers)

    @property
    def blocker_count(self) -> int:
        return len(self.blockers)

    def __post_init__(self):
        for name in ("causer_house", "blocker_house"):
            strict_int(getattr(self, name), 1, 12, name)
        for name in ("causer_sign", "blocker_sign"):
            strict_int(getattr(self, name), 0, 11, name)
        _bodies(self.causers)
        _bodies(self.blockers)
        if set(self.causers) & set(self.blockers):
            raise ValueError("a body cannot occupy both opposing positions")
        if self.formation_state != ("present" if self.causers else "absent"):
            raise ValueError("formation must agree with occupants")
        if type(self.count_grade) is not ArgalaCountGrade:
            raise ValueError("invalid count-grade vessel")
        self.count_grade.__post_init__()
        if (
            self.count_grade.status == "assessed"
            and self.count_grade.grade
            != ("none", "limited", "medium", "excellent")[min(3, len(self.causers))]
        ):
            raise ValueError("grade must agree with causer count")
        for state in (self.causer_character, self.blocker_character):
            if state not in ("none", "benefic", "malefic", "mixed", "indeterminate"):
                raise ValueError("unknown group character")
        if self.effect_state not in (
            "absent",
            "unobstructed",
            "obstructed",
            "indeterminate",
        ):
            raise ValueError("unknown effect")
        if (self.effect_state == "absent") != (not self.causers):
            raise ValueError("effect absence must agree with formation")
        if type(self.reason_codes) is not tuple or any(
            r not in _REASONS for r in self.reason_codes
        ):
            raise ValueError("unknown comparison reason")
        if (self.effect_state == "indeterminate") != bool(self.reason_codes):
            raise ValueError("indeterminate effect requires reasons")
        if self.strength_comparison not in ("not_required", "indeterminate"):
            raise ValueError("unknown strength comparison")
        if self.quarter_status not in (
            "not_assessed",
            "unavailable",
            "no_pairs",
            "evaluated",
        ):
            raise ValueError("unknown quarter status")
        _records(self.quarter_pairs, ArgalaQuarterWitness)
        _records(self.eligible_blockers, ArgalaEligibleBlockers)
        _records(self.strength_factors, ArgalaStrengthFactors)
        if self.quarter_status == "evaluated":
            if tuple((q.causer, q.blocker) for q in self.quarter_pairs) != tuple(
                (c, b) for c in self.causers for b in self.blockers
            ):
                raise ValueError("quarter matrix must preserve every directed pair")
            expected = tuple(
                ArgalaEligibleBlockers(
                    c,
                    tuple(
                        q.blocker
                        for q in self.quarter_pairs
                        if q.causer == c and q.qualifies
                    ),
                )
                for c in self.causers
            )
            if self.eligible_blockers != expected:
                raise ValueError("eligible blockers disagree with matrix")
        elif self.quarter_pairs or self.eligible_blockers:
            raise ValueError(
                "unassessed quarters cannot carry invented degree evidence"
            )


@dataclass(frozen=True, slots=True)
class ArgalaSpecialThird:
    """Independent special-third presence; raw blocker roles are preserved elsewhere."""

    state: Literal["present", "absent", "indeterminate", "not_assessed"]
    occupants: tuple[str, ...]
    known_malefics: tuple[str, ...]
    unknown_bodies: tuple[str, ...]
    minimum_malefics: int
    maximum_malefics: int
    reason: Literal[
        "three_malefics",
        "fewer_than_three_possible",
        "character_unresolved",
        "special_third_threshold_not_admitted",
    ]
    source_effect: Literal["favourable_special_intervention"] | None

    def __post_init__(self):
        for values in (self.occupants, self.known_malefics, self.unknown_bodies):
            _bodies(values)
        strict_int(self.minimum_malefics, 0, 9, "minimum_malefics")
        strict_int(self.maximum_malefics, 0, 9, "maximum_malefics")
        if self.minimum_malefics != len(
            self.known_malefics
        ) or self.maximum_malefics != self.minimum_malefics + len(self.unknown_bodies):
            raise ValueError("inconsistent malefic bounds")
        if set(self.known_malefics) & set(self.unknown_bodies) or not set(
            self.known_malefics + self.unknown_bodies
        ) <= set(self.occupants):
            raise ValueError("inconsistent third-house roles")
        if self.state not in ("present", "absent", "indeterminate", "not_assessed"):
            raise ValueError("unknown special-third state")
        if self.state == "not_assessed":
            expected = "special_third_threshold_not_admitted"
        else:
            state = (
                "present"
                if self.minimum_malefics >= 3
                else "absent"
                if self.maximum_malefics < 3
                else "indeterminate"
            )
            if self.state != state:
                raise ValueError("special-third state disagrees with bounds")
            expected = {
                "present": "three_malefics",
                "absent": "fewer_than_three_possible",
                "indeterminate": "character_unresolved",
            }[state]
        if self.reason != expected or self.source_effect != (
            "favourable_special_intervention" if self.state == "present" else None
        ):
            raise ValueError("invalid special-third effect or reason")


@dataclass(frozen=True, slots=True)
class ArgalaReferenceAssessment:
    """Assessment from a semantic reference, including the direction's reason."""

    reference: ArgalaReference
    reference_sign: int
    direction: int
    direction_reason: Literal[
        "ordinary_forward", "node_reference", "ketu_occupied_reference"
    ]
    pairs: tuple[ArgalaPairAssessment, ...]
    special_third: ArgalaSpecialThird

    def __post_init__(self):
        if type(self.reference) is not ArgalaReference:
            raise ValueError("invalid reference")
        self.reference.__post_init__()
        strict_int(self.reference_sign, 0, 11, "reference_sign")
        strict_int(self.direction, -1, 1, "direction")
        if self.direction_reason not in (
            "ordinary_forward",
            "node_reference",
            "ketu_occupied_reference",
        ) or self.direction != (
            1 if self.direction_reason == "ordinary_forward" else -1
        ):
            raise ValueError("inconsistent reference direction")
        _records(self.pairs, ArgalaPairAssessment)
        if type(self.special_third) is not ArgalaSpecialThird:
            raise ValueError("invalid special-third evidence")
        self.special_third.__post_init__()


@dataclass(frozen=True, slots=True)
class ArgalaAssessmentResult:
    """Deeply immutable source profile, input precision and complete assessment evidence."""

    chart: JaiminiChart
    profile: JaiminiProfile
    characters: tuple[ArgalaCharacter, ...]
    references: tuple[ArgalaReferenceAssessment, ...]
    catalogue_version: str = field(init=False, default=VERSION)
    character_component: str = field(init=False, default=CHARACTER_ID)
    participant_pool: tuple[str, ...] = field(init=False, default=NINE)

    def __post_init__(self):
        if self.chart != admit_chart(self.chart, NINE):
            raise ValueError("result chart must be the immutable admitted snapshot")
        if (
            self.catalogue_version != VERSION
            or self.character_component != CHARACTER_ID
            or self.participant_pool != NINE
        ):
            raise ValueError("invalid Argala computation metadata")
        if type(self.profile) is not JaiminiProfile or self.profile != admit_profile(
            self.profile.profile_id, "argala"
        ):
            raise ValueError("invalid Argala profile receipt")
        _records(self.characters, ArgalaCharacter)
        if tuple(c.body for c in self.characters) != NINE:
            raise ValueError("complete canonical character evidence required")
        _records(self.references, ArgalaReferenceAssessment)
        refs = tuple(r.reference for r in self.references)
        if refs != admit_references(refs):
            raise ValueError("references must be canonically ordered")
        expected_pairs = (
            _PAIRS + ((8, 6), (7, 1))
            if self.profile.profile_id == ARGALA_IDS[2]
            else _PAIRS
        )
        signs, lagna = chart_signs(self.chart)
        kind = ARGALA_IDS.index(self.profile.profile_id)
        if self.characters != _characters(self.chart, signs):
            raise ValueError("character evidence disagrees with chart and component")
        states = {c.body: c.state for c in self.characters}
        positions = dict(self.chart.positions)
        occupants = {s: tuple(p for p in NINE if signs[p] == s) for s in range(12)}
        for ref in self.references:
            expected_sign = (
                lagna
                if ref.reference.kind == "lagna"
                else (lagna + ref.reference.value - 1) % 12
                if ref.reference.kind == "house"
                else signs[ref.reference.value]
            )
            if (
                expected_sign != ref.reference_sign
                or tuple((p.causer_house, p.blocker_house) for p in ref.pairs)
                != expected_pairs
            ):
                raise ValueError("reference or pair catalogue mismatch")
            expected_reason = "ordinary_forward"
            if self.profile.profile_id == ARGALA_IDS[0]:
                if ref.reference.kind == "planet" and ref.reference.value in (
                    "Rahu",
                    "Ketu",
                ):
                    expected_reason = "node_reference"
            elif ref.reference_sign == signs["Ketu"]:
                expected_reason = "ketu_occupied_reference"
            if ref.direction_reason != expected_reason:
                raise ValueError("reference reversal disagrees with selected profile")
            for pair in ref.pairs:
                for house, sign, bodies in (
                    (pair.causer_house, pair.causer_sign, pair.causers),
                    (pair.blocker_house, pair.blocker_sign, pair.blockers),
                ):
                    if sign != (
                        ref.reference_sign + ref.direction * (house - 1)
                    ) % 12 or bodies != tuple(p for p in NINE if signs[p] == sign):
                        raise ValueError("pair geometry disagrees with input chart")
                bphs = self.profile.profile_id == ARGALA_IDS[0]
                if (pair.count_grade.status == "assessed") != bphs:
                    raise ValueError("count grade belongs only to the BPHS profile")
                expected_quarter = (
                    "not_assessed"
                    if not bphs
                    else "no_pairs"
                    if not pair.causers or not pair.blockers
                    else "unavailable"
                    if self.chart.basis == "signs"
                    else "evaluated"
                )
                if pair.quarter_status != expected_quarter:
                    raise ValueError(
                        "quarter assessment disagrees with source or precision"
                    )
                for q in pair.quarter_pairs:
                    if (
                        q.causer_degree != positions[q.causer] % 30
                        or q.blocker_degree != positions[q.blocker] % 30
                    ):
                        raise ValueError("quarter degrees disagree with input chart")
                if (
                    pair.causer_character != _group(pair.causers, states)
                    or pair.blocker_character != _group(pair.blockers, states)
                ):
                    raise ValueError("group character disagrees with body evidence")
                effect, reasons = _effect(
                    kind, pair.causers, pair.blockers,
                    pair.quarter_status, pair.quarter_pairs,
                )
                if (
                    pair.effect_state != effect
                    or pair.reason_codes != reasons
                    or pair.strength_comparison
                    != ("indeterminate" if reasons else "not_required")
                ):
                    raise ValueError("effect evidence disagrees with selected profile")
                if pair.strength_factors != _strength_factors(
                    kind, pair.causer_sign, pair.blocker_sign, signs, occupants
                ):
                    raise ValueError("strength factors disagree with chart or profile")
            third = occupants[(ref.reference_sign + ref.direction * 2) % 12]
            if ref.special_third != _special_third(kind, third, states):
                raise ValueError("special-third evidence disagrees with chart or profile")


def _characters(chart, signs):
    states = {
        p: ("benefic", "natural_benefic")
        if p in ("Jupiter", "Venus")
        else ("malefic", "natural_malefic")
        for p in NINE
        if p not in ("Moon", "Mercury")
    }
    if chart.basis == "signs":
        states["Moon"] = ("indeterminate", "requires_longitude")
    else:
        values = dict(chart.positions)
        # Exact binary-input ownership: subtraction near 180 can otherwise
        # round a just-bright-half chart onto the dark-half boundary.
        bright = (Fraction(values["Moon"]) - Fraction(values["Sun"])) % 360 < 180
        states["Moon"] = (
            ("benefic", "bright_half") if bright else ("malefic", "dark_half")
        )
    associates = tuple(
        states[p][0] for p in NINE if p != "Mercury" and signs[p] == signs["Mercury"]
    )
    states["Mercury"] = (
        ("malefic", "malefic_association")
        if "malefic" in associates
        else ("indeterminate", "moon_association_unresolved")
        if "indeterminate" in associates
        else ("benefic", "no_malefic_association")
    )
    return tuple(ArgalaCharacter(p, *states[p]) for p in NINE)


def _group(bodies, characters):
    states = {characters[p] for p in bodies}
    if not states:
        return "none"
    if {"benefic", "malefic"} <= states:
        return "mixed"
    return "indeterminate" if "indeterminate" in states else next(iter(states))


def _effect(kind, causers, blockers, quarter_status, quarters):
    if not causers:
        return "absent", ()
    if not blockers:
        return "unobstructed", ()
    if kind == 2:
        return "indeterminate", ("factor_priority_not_admitted",)
    if len(causers) > len(blockers):
        return "unobstructed", ()
    if kind == 1:
        return (
            ("obstructed", ())
            if len(blockers) > len(causers)
            else ("indeterminate", ("strength_comparator_not_admitted",))
        )
    if quarter_status == "unavailable":
        return "indeterminate", ("degrees_required",)
    if not any(q.qualifies for q in quarters):
        return "unobstructed", ()
    if all(q.qualifies for q in quarters):
        return "indeterminate", ("strength_comparator_not_admitted",)
    return "indeterminate", ("multioccupant_quarter_composition_unestablished",)


def _strength_factors(kind, causer_sign, blocker_sign, signs, occupants):
    """Derive Rath's bounded factors without assigning a comparison priority."""
    if kind != 2:
        return ()
    return tuple(
        ArgalaStrengthFactors(
            side,
            sign,
            tuple(
                p for p in occupants[sign]
                if p in CLASSICAL and _RASI_LORDS[sign] == p
            ),
            sign in rasi_drishti_of(signs["Jupiter"]),
        )
        for side, sign in (("causer", causer_sign), ("blocker", blocker_sign))
    )


def _special_third(kind, third, states):
    """Derive the selected threshold and preserve uncertain character bounds."""
    known = tuple(p for p in third if states[p] == "malefic")
    unknown = tuple(p for p in third if states[p] == "indeterminate")
    low, high = len(known), len(known) + len(unknown)
    state = (
        "not_assessed"
        if kind != 0
        else "present"
        if low >= 3
        else "absent"
        if high < 3
        else "indeterminate"
    )
    reason = {
        "not_assessed": "special_third_threshold_not_admitted",
        "present": "three_malefics",
        "absent": "fewer_than_three_possible",
        "indeterminate": "character_unresolved",
    }[state]
    return ArgalaSpecialThird(
        state, third, known, unknown, low, high, reason,
        "favourable_special_intervention" if state == "present" else None,
    )


def assess_argala(
    chart: JaiminiChart, *, profile_id: str, references: tuple[ArgalaReference, ...]
) -> ArgalaAssessmentResult:
    """Assess one named profile with complete nine-body inputs and explicit references."""
    profile = admit_profile(profile_id, "argala")
    chart = admit_chart(chart, NINE)
    references = admit_references(references)
    with result_invariants("Argala"):
        return _assess_admitted(chart, profile, references)


def _assess_admitted(chart, profile, references):
    """Build result evidence only after caller-owned inputs have been admitted."""
    signs, lagna = chart_signs(chart)
    kind = ARGALA_IDS.index(profile.profile_id)
    characters = _characters(chart, signs)
    states = {c.body: c.state for c in characters}
    positions = dict(chart.positions)
    occupants = {s: tuple(p for p in NINE if signs[p] == s) for s in range(12)}
    pairs = _PAIRS + ((8, 6), (7, 1)) if kind == 2 else _PAIRS
    results = []
    for reference in references:
        ref_sign = (
            lagna
            if reference.kind == "lagna"
            else (lagna + reference.value - 1) % 12
            if reference.kind == "house"
            else signs[reference.value]
        )
        reason = "ordinary_forward"
        if (
            kind == 0
            and reference.kind == "planet"
            and reference.value in ("Rahu", "Ketu")
        ):
            reason = "node_reference"
        elif kind != 0 and ref_sign == signs["Ketu"]:
            reason = "ketu_occupied_reference"
        direction = 1 if reason == "ordinary_forward" else -1
        assessments = []
        for ch, bh in pairs:
            cs, bs = (
                (ref_sign + direction * (ch - 1)) % 12,
                (ref_sign + direction * (bh - 1)) % 12,
            )
            causers, blockers = occupants[cs], occupants[bs]
            grade = (
                ArgalaCountGrade(
                    "assessed",
                    ("none", "limited", "medium", "excellent")[min(3, len(causers))],
                    "bphs.31.formation",
                )
                if kind == 0
                else ArgalaCountGrade("not_assessed", None, None)
            )
            quarters, eligible = (), ()
            qstatus = "not_assessed"
            if kind == 0:
                if not causers or not blockers:
                    qstatus = "no_pairs"
                elif chart.basis == "signs":
                    qstatus = "unavailable"
                else:
                    qstatus = "evaluated"
                    values = []
                    for c in causers:
                        for b in blockers:
                            cd, bd = positions[c] % 30, positions[b] % 30
                            cq, bq = int(cd // 7.5) + 1, int(bd // 7.5) + 1
                            values.append(
                                ArgalaQuarterWitness(
                                    c, b, cd, bd, cq, bq, (cq, bq) in ((1, 4), (2, 3))
                                )
                            )
                    quarters = tuple(values)
                    eligible = tuple(
                        ArgalaEligibleBlockers(
                            c,
                            tuple(
                                q.blocker
                                for q in quarters
                                if q.causer == c and q.qualifies
                            ),
                        )
                        for c in causers
                    )
            factors = _strength_factors(kind, cs, bs, signs, occupants)
            effect, reasons = _effect(kind, causers, blockers, qstatus, quarters)
            assessments.append(
                ArgalaPairAssessment(
                    ch,
                    bh,
                    cs,
                    bs,
                    causers,
                    blockers,
                    "present" if causers else "absent",
                    grade,
                    _group(causers, states),
                    _group(blockers, states),
                    effect,
                    reasons,
                    "indeterminate" if reasons else "not_required",
                    qstatus,
                    quarters,
                    eligible,
                    factors,
                )
            )
        third = occupants[(ref_sign + direction * 2) % 12]
        special = _special_third(kind, third, states)
        results.append(
            ArgalaReferenceAssessment(
                reference, ref_sign, direction, reason, tuple(assessments), special
            )
        )
    return ArgalaAssessmentResult(chart, profile, characters, tuple(results))
