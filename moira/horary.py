"""Source-bounded Horary evidence composition.

This module owns no universal Horary judgement.  It preserves the question
event selected by the caller, resolves explicit turned-house arithmetic,
assigns Lilly's principal significators from caller-supplied house geometry,
and composes an already-computed Lilly perfection analysis.  It never emits a
yes/no answer, score, advice, or inferred question topic.

Authority
---------
William Lilly, *Christian Astrology* (London, 1647), Books I-II, especially
printed pp. 47-56, 110-113, 121-126, and 442-445; Wellcome/Internet Archive
scan ``b30338724``.  Where Lilly does not provide a finite computational rule,
the evidence remains unresolved or must arrive as an explicit caller receipt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from ._strenum import StrEnum
from .classical_perfection import (
    ClassicalPerfectionAnalysis,
    ClassicalPerfectionEventKind,
    ClassicalPerfectionState,
    LILLY_1647_PERFECTION_V1,
    LillyPerfectionKind,
    LillyPerfectionPolicy,
    classify_lilly_perfection_events,
    lilly_perfection_at,
)
from .constants import Body, HOUSE_SYSTEM_NAMES, SIGNS
from .dignities import solar_proximity_truth
from .dignities_types import SolarProximityBand, SolarProximityTruth, TruthEvaluationStatus
from .houses import HouseCusps, HousePolicy, calculate_houses, house_of
from .planetary_hours import planetary_hours
from .planets import planet_at
from .profections import DOMICILE_RULERS
from .spk_reader import KernelReader


__all__ = [
    "HoraryEvidenceState",
    "HoraryRuleState",
    "HoraryHourRuleState",
    "HoraryHourAgreementState",
    "HoraryPerfectionState",
    "HoraryChartSect",
    "HoraryTurnStepKind",
    "HorarySignificatorRole",
    "HoraryQuestionTimeBasis",
    "HorarySourceCalendar",
    "HoraryGeometrySourceMode",
    "HoraryQuestionTimeReceipt",
    "HoraryQuestionReceipt",
    "HoraryHousePolicy",
    "HoraryHouseGeometryReceipt",
    "HoraryChartPolicyReceipt",
    "HoraryTurnStepReceipt",
    "HoraryTurnedHouseReceipt",
    "HorarySignificatorEvidence",
    "HorarySignificatorSet",
    "HoraryPlanetaryHourReceipt",
    "HoraryChartSectReceipt",
    "HoraryHourRuleEvidence",
    "HoraryHourAgreementEvidence",
    "HoraryBodyPlacementReceipt",
    "HorarySolarProximityReceipt",
    "HoraryConsiderationInputs",
    "HoraryConsiderationEvidence",
    "HoraryPerfectionEvidence",
    "HoraryPerfectionSearchPolicy",
    "MOIRA_HORARY_PERFECTION_SEARCH_SAFETY_V1",
    "HoraryProvenance",
    "LILLY_1647_HORARY_V1",
    "HoraryEvidenceProfile",
    "resolve_turned_house",
    "evaluate_horary_evidence",
    "horary_evidence_at",
]


_AUTHORITY = (
    "William Lilly, Christian Astrology (London, 1647), Books I-II, printed "
    "pp. 47-56, 110-113, 121-126, and 442-445; Wellcome scan b30338724"
)
_PERFECTION_AUTHORITY = (
    "William Lilly, Christian Astrology (London, 1647), Book I, printed "
    "pp. 110-113 and 125-126; Wellcome Collection scan b30338724"
)
_PERFECTION_WITNESS_ORDER = tuple(LillyPerfectionKind)
_JD_BIND_TOL = 1e-9
_COORD_BIND_TOL = 1e-12
_TURN_COUNTING_SEMANTICS = "inclusive_one_based_from_each_preceding_perspective"
_TRADITIONAL_BODIES = (
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
)
_CONSIDERATION_RULE_IDS = (
    "ascendant_below_three_degrees",
    "ascendant_at_or_above_twenty_seven_degrees",
    "moon_in_via_combusta",
    "saturn_in_first_house",
    "saturn_in_seventh_house",
    "first_house_ruler_combust",
)
_HOUR_RULE_IDS = (
    "same_planet",
    "triplicity",
    "same_nature",
)
_SIGN_ELEMENT = MappingProxyType({
    "Aries": "fire",
    "Taurus": "earth",
    "Gemini": "air",
    "Cancer": "water",
    "Leo": "fire",
    "Virgo": "earth",
    "Libra": "air",
    "Scorpio": "water",
    "Sagittarius": "fire",
    "Capricorn": "earth",
    "Aquarius": "air",
    "Pisces": "water",
})
_HOUR_TRIPLICITY_RULERS = MappingProxyType({
    "fire": (Body.SUN, Body.JUPITER),
    "earth": (Body.VENUS, Body.MOON),
    "air": (Body.SATURN, Body.MERCURY),
    "water": (Body.MARS, Body.MARS),
})
_PLANETARY_NATURE = MappingProxyType({
    Body.SUN: ("hot", "dry"),
    Body.MOON: ("cold", "moist"),
    Body.MERCURY: ("cold", "dry"),
    Body.VENUS: ("cold", "moist"),
    Body.MARS: ("hot", "dry"),
    Body.JUPITER: ("hot", "moist"),
    Body.SATURN: ("cold", "dry"),
})
_EXCLUDED_COMPONENTS = (
    "yes_no_outcome",
    "confidence_or_strength_score",
    "advice_or_recommendation",
    "degrees_to_time_conversion",
    "question_topic_inference",
    "house_system_inference",
    "late_moon_numeric_rule",
    "void_of_course_sign_mitigation",
    "seventh_cusp_or_ruler_impediment",
    "balanced_testimony_aggregation",
    "topic_specific_significator_overrides",
    "modern_planets_and_minor_aspects",
)
_UNRESOLVED_POLICIES = (
    "early_ascendant_contextual_qualifications_not_composed",
    "late_ascendant_contextual_qualifications_not_composed",
    "lilly_late_moon_degrees_have_no_finite_numeric_boundary",
    "void_of_course_sign_mitigation_requires_separate_source_contract",
    "seventh_cusp_or_ruler_impediment_requires_separate_input_contract",
    "fortunate_unfortunate_testimony_balance_requires_separate_source_contract",
)


class HoraryEvidenceState(StrEnum):
    """Evaluation state for an atomic Horary evidence component."""

    EVALUATED = "evaluated"
    NOT_EVALUABLE = "not_evaluable"


class HoraryRuleState(StrEnum):
    """State of one consideration before judgement."""

    SATISFIED = "satisfied"
    CAUTION = "caution"
    NOT_APPLICABLE = "not_applicable"
    NOT_EVALUABLE = "not_evaluable"


class HoraryHourRuleState(StrEnum):
    """State of one hour-agreement path."""

    MATCHED = "matched"
    NOT_MATCHED = "not_matched"
    NOT_EVALUABLE = "not_evaluable"


class HoraryHourAgreementState(StrEnum):
    """Three-valued composition of the visible hour-agreement paths."""

    AGREES = "agrees"
    DOES_NOT_AGREE = "does_not_agree"
    NOT_EVALUABLE = "not_evaluable"


class HoraryPerfectionState(StrEnum):
    """Composition state for caller-supplied Lilly perfection evidence."""

    COMPOSED = "composed"
    NOT_EVALUABLE = "not_evaluable"


class HoraryChartSect(StrEnum):
    """Day/night state proven by the question's exact planetary-hour interval."""

    DAY = "day"
    NIGHT = "night"


class HoraryTurnStepKind(StrEnum):
    """Role of one count in a turned-house path."""

    PERSPECTIVE = "perspective"
    TERMINAL_TOPIC = "terminal_topic"


class HorarySignificatorRole(StrEnum):
    """The three bounded significator roles admitted in v1."""

    PRINCIPAL_QUERENT = "principal_querent"
    QUERENT_CO_SIGNIFICATOR = "querent_co_significator"
    PRINCIPAL_QUESITED = "principal_quesited"


class HoraryQuestionTimeBasis(StrEnum):
    """Closed question-event bases preserved by the atomic receipt."""

    QUESTION_PROPOSED_AND_FIGURE_ERECTED = "question_proposed_and_figure_erected"
    UNDERSTOOD_BY_ASTROLOGER = "understood_by_astrologer"
    LETTER_OPENED_AND_UNDERSTOOD = "letter_opened_and_understood"
    SETTLED_SELF_QUESTION = "settled_self_question"
    CALLER_SUPPLIED_OTHER = "caller_supplied_other"


class HorarySourceCalendar(StrEnum):
    """Calendar attached to the source instant before normalization."""

    GREGORIAN = "gregorian"
    JULIAN = "julian"


class HoraryGeometrySourceMode(StrEnum):
    """Whether geometry is computed at an epoch or copied from a source chart."""

    COMPUTED = "computed"
    HISTORICAL_SOURCE_CHART_ASSIGNMENT = "historical_source_chart_assignment"


def _valid_house(value: int, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 12:
        raise ValueError(f"{name} must be an integer in [1, 12]")
    return value


def _valid_longitude(value: float, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result < 360.0:
        raise ValueError(f"{name} must be finite in [0, 360)")
    return result


def _nonempty(value: str, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class HoraryQuestionTimeReceipt:
    """Source-event metadata plus an optional normalized computational epoch."""

    state: HoraryEvidenceState
    stated_basis: HoraryQuestionTimeBasis
    stated_basis_source: str
    source_calendar: HorarySourceCalendar
    source_instant_label: str
    normalized_instant: datetime | None
    normalized_jd_ut1: float | None
    conversion_policy_id: str | None
    reason: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, HoraryEvidenceState):
            raise TypeError("question-time state must be a HoraryEvidenceState")
        if not isinstance(self.stated_basis, HoraryQuestionTimeBasis):
            raise TypeError("stated_basis must be a HoraryQuestionTimeBasis")
        if not isinstance(self.source_calendar, HorarySourceCalendar):
            raise TypeError("source_calendar must be a HorarySourceCalendar")
        _nonempty(self.stated_basis_source, name="stated_basis_source")
        _nonempty(self.source_instant_label, name="source_instant_label")
        if self.state is HoraryEvidenceState.EVALUATED:
            if self.stated_basis is not HoraryQuestionTimeBasis.QUESTION_PROPOSED_AND_FIGURE_ERECTED:
                raise ValueError(
                    "only question_proposed_and_figure_erected can carry an evaluated atomic epoch"
                )
            if not isinstance(self.normalized_instant, datetime):
                raise TypeError("evaluated question time requires normalized_instant")
            if (
                self.normalized_instant.tzinfo is None
                or self.normalized_instant.utcoffset() is None
            ):
                raise ValueError("normalized_instant must be timezone-aware")
            if (
                self.normalized_jd_ut1 is None
                or not math.isfinite(self.normalized_jd_ut1)
            ):
                raise ValueError("evaluated question time requires finite normalized_jd_ut1")
            if self.conversion_policy_id is None:
                raise ValueError("evaluated question time requires conversion_policy_id")
            _nonempty(self.conversion_policy_id, name="conversion_policy_id")
            if self.reason is not None:
                raise ValueError("evaluated question time cannot carry a failure reason")
        else:
            if any(
                value is not None
                for value in (
                    self.normalized_instant,
                    self.normalized_jd_ut1,
                    self.conversion_policy_id,
                )
            ):
                raise ValueError("unresolved question time cannot carry a normalized epoch")
            if not self.reason:
                raise ValueError("unresolved question time requires an explicit reason")


@dataclass(frozen=True, slots=True)
class HoraryQuestionReceipt:
    """Caller-owned identity and timing receipt for one question event."""

    question_id: str
    latitude_deg: float
    longitude_deg: float
    time: HoraryQuestionTimeReceipt
    perspective_path: tuple[int, ...]
    terminal_topic_house: int

    def __post_init__(self) -> None:
        _nonempty(self.question_id, name="question_id")
        if (
            isinstance(self.latitude_deg, bool)
            or not isinstance(self.latitude_deg, (int, float))
            or not math.isfinite(self.latitude_deg)
            or not -90.0 <= self.latitude_deg <= 90.0
        ):
            raise ValueError("latitude_deg must be finite in [-90, 90]")
        if (
            isinstance(self.longitude_deg, bool)
            or not isinstance(self.longitude_deg, (int, float))
            or not math.isfinite(self.longitude_deg)
            or not -180.0 <= self.longitude_deg <= 180.0
        ):
            raise ValueError("longitude_deg must be finite in [-180, 180]")
        if not isinstance(self.time, HoraryQuestionTimeReceipt):
            raise TypeError("time must be a HoraryQuestionTimeReceipt")
        object.__setattr__(self, "perspective_path", tuple(self.perspective_path))
        for index, house in enumerate(self.perspective_path, start=1):
            _valid_house(house, name=f"perspective_path[{index - 1}]")
        _valid_house(self.terminal_topic_house, name="terminal_topic_house")


@dataclass(frozen=True, slots=True)
class HoraryHousePolicy:
    """Caller-declared house policy; v1 requires exact, no-fallback geometry."""

    house_system: str
    exact_system_required: bool = True

    def __post_init__(self) -> None:
        if type(self.house_system) is not str:
            raise TypeError("house_system must be a concrete str")
        _nonempty(self.house_system, name="house_system")
        if self.house_system not in HOUSE_SYSTEM_NAMES:
            raise ValueError(f"unsupported house system code {self.house_system!r}")
        if self.exact_system_required is not True:
            raise ValueError("Horary v1 requires exact house geometry without fallback")


@dataclass(frozen=True, slots=True)
class HoraryHouseGeometryReceipt:
    """Question-bound house geometry and its computation/source identity."""

    question_id: str
    latitude_deg: float
    longitude_deg: float
    source_id: str
    source_mode: HoraryGeometrySourceMode
    jd_ut1: float | None
    house_cusps: HouseCusps

    def __post_init__(self) -> None:
        _nonempty(self.question_id, name="question_id")
        _nonempty(self.source_id, name="source_id")
        if not isinstance(self.source_mode, HoraryGeometrySourceMode):
            raise TypeError("source_mode must be a HoraryGeometrySourceMode")
        if not math.isfinite(self.latitude_deg) or not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("geometry latitude_deg must be finite in [-90, 90]")
        if not math.isfinite(self.longitude_deg) or not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("geometry longitude_deg must be finite in [-180, 180]")
        if not isinstance(self.house_cusps, HouseCusps):
            raise TypeError("house_cusps must be a HouseCusps")
        if self.source_mode is HoraryGeometrySourceMode.COMPUTED:
            if self.jd_ut1 is None or not math.isfinite(self.jd_ut1):
                raise ValueError("computed house geometry requires finite jd_ut1")
        elif self.jd_ut1 is not None:
            raise ValueError("historical source-chart assignment cannot claim a normalized epoch")


@dataclass(frozen=True, slots=True)
class HoraryChartPolicyReceipt:
    """Comparison between caller policy and supplied house-result truth."""

    state: HoraryEvidenceState
    requested_system: str
    effective_system: str
    fallback: bool
    reason: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, HoraryEvidenceState):
            raise TypeError("state must be a HoraryEvidenceState")
        _nonempty(self.requested_system, name="requested_system")
        if self.state is HoraryEvidenceState.EVALUATED:
            if self.effective_system != self.requested_system or self.fallback or self.reason is not None:
                raise ValueError("evaluated chart policy requires exact no-fallback geometry")
        elif not self.reason:
            raise ValueError("not-evaluable chart policy requires a reason")


@dataclass(frozen=True, slots=True)
class HoraryTurnStepReceipt:
    """One explicit 1-based count from a preceding house perspective."""

    index: int
    kind: HoraryTurnStepKind
    from_radical_house: int
    counted_house: int
    resolved_radical_house: int

    def __post_init__(self) -> None:
        if not isinstance(self.kind, HoraryTurnStepKind):
            raise TypeError("kind must be a HoraryTurnStepKind")
        if isinstance(self.index, bool) or not isinstance(self.index, int) or self.index < 1:
            raise ValueError("turn-step index must be a positive integer")
        _valid_house(self.from_radical_house, name="from_radical_house")
        _valid_house(self.counted_house, name="counted_house")
        _valid_house(self.resolved_radical_house, name="resolved_radical_house")
        expected = ((self.from_radical_house + self.counted_house - 2) % 12) + 1
        if self.resolved_radical_house != expected:
            raise ValueError("resolved radical house must derive from the visible count")


@dataclass(frozen=True, slots=True)
class HoraryTurnedHouseReceipt:
    """Complete perspective path and terminal topic-house resolution."""

    perspective_path: tuple[int, ...]
    terminal_topic_house: int
    steps: tuple[HoraryTurnStepReceipt, ...]
    resolved_radical_house: int
    counting_semantics: str = _TURN_COUNTING_SEMANTICS

    def __post_init__(self) -> None:
        if self.counting_semantics != _TURN_COUNTING_SEMANTICS:
            raise ValueError("counting_semantics is fixed for Horary turned houses")
        object.__setattr__(self, "perspective_path", tuple(self.perspective_path))
        object.__setattr__(self, "steps", tuple(self.steps))
        if any(not isinstance(step, HoraryTurnStepReceipt) for step in self.steps):
            raise TypeError("steps must contain HoraryTurnStepReceipt")
        for index, house in enumerate(self.perspective_path):
            _valid_house(house, name=f"perspective_path[{index}]")
        _valid_house(self.terminal_topic_house, name="terminal_topic_house")
        _valid_house(self.resolved_radical_house, name="resolved_radical_house")
        if len(self.steps) != len(self.perspective_path) + 1:
            raise ValueError("turn receipt requires every perspective and one terminal step")
        expected_kinds = (HoraryTurnStepKind.PERSPECTIVE,) * len(self.perspective_path) + (
            HoraryTurnStepKind.TERMINAL_TOPIC,
        )
        if tuple(step.kind for step in self.steps) != expected_kinds:
            raise ValueError("turn steps must preserve perspective order then terminal topic")
        expected_counts = self.perspective_path + (self.terminal_topic_house,)
        if tuple(step.counted_house for step in self.steps) != expected_counts:
            raise ValueError("turn steps must preserve every caller-supplied count")
        current = 1
        for index, step in enumerate(self.steps, start=1):
            if step.index != index or step.from_radical_house != current:
                raise ValueError("turn steps must form one ordered, contiguous perspective path")
            current = step.resolved_radical_house
        if self.steps[-1].resolved_radical_house != self.resolved_radical_house:
            raise ValueError("resolved house must derive from the terminal step")


@dataclass(frozen=True, slots=True)
class HorarySignificatorEvidence:
    """One principal or co-significator assignment, without interpretation."""

    role: HorarySignificatorRole
    state: HoraryEvidenceState
    body: str | None
    radical_house: int | None
    cusp_longitude_deg: float | None
    sign: str | None
    reason: str | None
    source_reference: str = _AUTHORITY

    def __post_init__(self) -> None:
        if not isinstance(self.role, HorarySignificatorRole):
            raise TypeError("role must be a HorarySignificatorRole")
        if not isinstance(self.state, HoraryEvidenceState):
            raise TypeError("state must be a HoraryEvidenceState")
        if self.state is HoraryEvidenceState.NOT_EVALUABLE:
            if any(value is not None for value in (self.body, self.radical_house, self.cusp_longitude_deg, self.sign)):
                raise ValueError("not-evaluable significator evidence cannot invent assignment truth")
            if not self.reason:
                raise ValueError("not-evaluable significator evidence requires a reason")
            return
        if self.body not in _TRADITIONAL_BODIES or self.reason is not None:
            raise ValueError("evaluated significator evidence requires one traditional body")
        if self.role is HorarySignificatorRole.QUERENT_CO_SIGNIFICATOR:
            if self.body != Body.MOON or any(
                value is not None for value in (self.radical_house, self.cusp_longitude_deg, self.sign)
            ):
                raise ValueError("the Moon co-significator remains distinct from house assignment")
            return
        if self.radical_house is None or self.cusp_longitude_deg is None or self.sign not in SIGNS:
            raise ValueError("principal significators require house, cusp, and sign evidence")
        _valid_house(self.radical_house, name="radical_house")
        _valid_longitude(self.cusp_longitude_deg, name="cusp_longitude_deg")
        if DOMICILE_RULERS[self.sign] != self.body:
            raise ValueError("principal significator must be the classical domicile ruler")


@dataclass(frozen=True, slots=True)
class HorarySignificatorSet:
    """The bounded querent/Moon/quesited assignment set."""

    state: HoraryEvidenceState
    principal_querent: HorarySignificatorEvidence
    querent_co_significator: HorarySignificatorEvidence
    principal_quesited: HorarySignificatorEvidence
    same_body_principals: bool | None
    reason: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, HoraryEvidenceState):
            raise TypeError("state must be a HoraryEvidenceState")
        for value, name in (
            (self.principal_querent, "principal_querent"),
            (self.querent_co_significator, "querent_co_significator"),
            (self.principal_quesited, "principal_quesited"),
        ):
            if not isinstance(value, HorarySignificatorEvidence):
                raise TypeError(f"{name} must be a HorarySignificatorEvidence")
        expected_roles = (
            HorarySignificatorRole.PRINCIPAL_QUERENT,
            HorarySignificatorRole.QUERENT_CO_SIGNIFICATOR,
            HorarySignificatorRole.PRINCIPAL_QUESITED,
        )
        actual_roles = (
            self.principal_querent.role,
            self.querent_co_significator.role,
            self.principal_quesited.role,
        )
        if actual_roles != expected_roles:
            raise ValueError("significator roles must remain source ordered")
        evidence = (self.principal_querent, self.querent_co_significator, self.principal_quesited)
        if self.state is HoraryEvidenceState.NOT_EVALUABLE:
            if any(item.state is HoraryEvidenceState.EVALUATED for item in evidence):
                raise ValueError("not-evaluable significator set cannot carry evaluated assignments")
            if self.same_body_principals is not None or not self.reason:
                raise ValueError("not-evaluable significator set requires only a reason")
            return
        if any(item.state is not HoraryEvidenceState.EVALUATED for item in evidence) or self.reason is not None:
            raise ValueError("evaluated significator set requires three evaluated roles")
        expected_collision = self.principal_querent.body == self.principal_quesited.body
        if self.same_body_principals is not expected_collision:
            raise ValueError("same-body truth must derive from the principal assignments")


@dataclass(frozen=True, slots=True)
class HoraryPlanetaryHourReceipt:
    """Caller-supplied planetary-hour truth for exact-lord comparison."""

    question_id: str
    jd_ut1: float
    latitude_deg: float
    longitude_deg: float
    source_id: str
    hour_ruler: str
    hour_number: int
    hour_start_jd: float
    hour_end_jd: float
    sunrise_jd: float
    sunset_jd: float
    local_time_algorithm_id: str

    def __post_init__(self) -> None:
        _nonempty(self.question_id, name="question_id")
        _nonempty(self.source_id, name="source_id")
        if not math.isfinite(self.jd_ut1):
            raise ValueError("planetary-hour event jd_ut1 must be finite")
        if not math.isfinite(self.latitude_deg) or not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("planetary-hour latitude_deg must be finite in [-90, 90]")
        if not math.isfinite(self.longitude_deg) or not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("planetary-hour longitude_deg must be finite in [-180, 180]")
        if self.hour_ruler not in _TRADITIONAL_BODIES:
            raise ValueError("hour_ruler must be one of the traditional seven")
        if isinstance(self.hour_number, bool) or not isinstance(self.hour_number, int) or not 1 <= self.hour_number <= 24:
            raise ValueError("hour_number must be an integer in [1, 24]")
        values = (self.hour_start_jd, self.hour_end_jd, self.sunrise_jd, self.sunset_jd)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("planetary-hour epochs must be finite")
        _validate_planetary_hour_semantics(self)
        _nonempty(self.local_time_algorithm_id, name="local_time_algorithm_id")

    @property
    def sect(self) -> HoraryChartSect:
        """Return the sect proven by the validated solar-event ordering."""

        return (
            HoraryChartSect.DAY
            if self.sunrise_jd < self.sunset_jd
            else HoraryChartSect.NIGHT
        )


@dataclass(frozen=True, slots=True)
class HoraryChartSectReceipt:
    """Question-bound day/night truth derived from one exact planetary hour."""

    state: HoraryEvidenceState
    question_id: str
    jd_ut1: float | None
    latitude_deg: float
    longitude_deg: float
    sect: HoraryChartSect | None
    planetary_hour_source_id: str | None
    reason: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, HoraryEvidenceState):
            raise TypeError("state must be a HoraryEvidenceState")
        _nonempty(self.question_id, name="question_id")
        if self.jd_ut1 is not None and not math.isfinite(self.jd_ut1):
            raise ValueError("chart-sect jd_ut1 must be finite or None")
        if not math.isfinite(self.latitude_deg) or not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("chart-sect latitude_deg must be finite in [-90, 90]")
        if not math.isfinite(self.longitude_deg) or not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("chart-sect longitude_deg must be finite in [-180, 180]")
        if self.planetary_hour_source_id is not None:
            _nonempty(self.planetary_hour_source_id, name="planetary_hour_source_id")
        if self.sect is not None and not isinstance(self.sect, HoraryChartSect):
            raise TypeError("sect must be a HoraryChartSect or None")
        if self.state is HoraryEvidenceState.EVALUATED:
            if self.jd_ut1 is None:
                raise ValueError("evaluated chart sect requires a question epoch")
            if self.sect is None:
                raise ValueError("evaluated chart sect requires a HoraryChartSect")
            if self.planetary_hour_source_id is None:
                raise ValueError("evaluated chart sect requires planetary-hour provenance")
            if self.reason is not None:
                raise ValueError("evaluated chart sect cannot carry a failure reason")
        else:
            if self.sect is not None:
                raise ValueError("not-evaluable chart sect cannot claim day or night")
            if not self.reason:
                raise ValueError("not-evaluable chart sect requires a reason")


@dataclass(frozen=True, slots=True)
class HoraryHourRuleEvidence:
    """One visible path by which hour agreement may or may not be shown."""

    rule_id: str
    state: HoraryHourRuleState
    derived_by: str
    observed: tuple[tuple[str, str | bool | int | float], ...]
    reason: str | None
    source_reference: str = _AUTHORITY

    def __post_init__(self) -> None:
        if not isinstance(self.state, HoraryHourRuleState):
            raise TypeError("state must be a HoraryHourRuleState")
        if self.rule_id not in _HOUR_RULE_IDS:
            raise ValueError("unknown hour-agreement rule id")
        _nonempty(self.derived_by, name="derived_by")
        object.__setattr__(self, "observed", tuple(self.observed))
        for name, value in self.observed:
            _nonempty(name, name="hour-rule observation name")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("hour-rule observations must be finite")
        if self.state is HoraryHourRuleState.NOT_EVALUABLE:
            if not self.reason:
                raise ValueError("not-evaluable hour rule requires a reason")
        elif self.reason is not None:
            raise ValueError("evaluated hour rule cannot carry a failure reason")


@dataclass(frozen=True, slots=True)
class HoraryHourAgreementEvidence:
    """Non-fatal radicality evidence; never a chart-rejection Boolean."""

    state: HoraryHourAgreementState
    ascendant_lord: str | None
    hour_ruler: str | None
    planetary_hour_receipt: HoraryPlanetaryHourReceipt | None
    rules: tuple[HoraryHourRuleEvidence, ...]
    reason: str | None
    semantics: str = "evidence_only_not_chart_rejection"

    def __post_init__(self) -> None:
        if not isinstance(self.state, HoraryHourAgreementState):
            raise TypeError("state must be a HoraryHourAgreementState")
        object.__setattr__(self, "rules", tuple(self.rules))
        if any(not isinstance(item, HoraryHourRuleEvidence) for item in self.rules):
            raise TypeError("rules must contain HoraryHourRuleEvidence")
        if self.planetary_hour_receipt is not None and not isinstance(
            self.planetary_hour_receipt, HoraryPlanetaryHourReceipt
        ):
            raise TypeError("planetary_hour_receipt must be typed or None")
        for body, name in (
            (self.ascendant_lord, "ascendant_lord"),
            (self.hour_ruler, "hour_ruler"),
        ):
            if body is not None and body not in _TRADITIONAL_BODIES:
                raise ValueError(f"{name} must be one of the traditional seven or None")
        if tuple(item.rule_id for item in self.rules) != _HOUR_RULE_IDS:
            raise ValueError("hour-agreement rules must remain source ordered")
        matched = any(item.state is HoraryHourRuleState.MATCHED for item in self.rules)
        unresolved = any(item.state is HoraryHourRuleState.NOT_EVALUABLE for item in self.rules)
        expected = (
            HoraryHourAgreementState.AGREES
            if matched
            else HoraryHourAgreementState.NOT_EVALUABLE
            if unresolved
            else HoraryHourAgreementState.DOES_NOT_AGREE
        )
        if self.state is not expected:
            raise ValueError("hour-agreement state must derive from visible rule paths")
        if self.state is HoraryHourAgreementState.NOT_EVALUABLE:
            if not self.reason:
                raise ValueError("not-evaluable hour agreement requires a reason")
        elif self.reason is not None:
            raise ValueError("evaluated hour agreement cannot carry a failure reason")


@dataclass(frozen=True, slots=True)
class HoraryBodyPlacementReceipt:
    """One body placement bound to a question event and house geometry."""

    question_id: str
    body: str
    longitude_deg: float
    house: int
    latitude_deg: float
    longitude_location_deg: float
    geometry_source_id: str
    source_id: str
    source_mode: HoraryGeometrySourceMode
    jd_ut1: float | None

    def __post_init__(self) -> None:
        _nonempty(self.question_id, name="question_id")
        if self.body not in _TRADITIONAL_BODIES:
            raise ValueError("placement body must be one of the traditional seven")
        _valid_longitude(self.longitude_deg, name="longitude_deg")
        _valid_house(self.house, name="house")
        if not math.isfinite(self.latitude_deg) or not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("placement latitude_deg must be finite in [-90, 90]")
        if not math.isfinite(self.longitude_location_deg) or not -180.0 <= self.longitude_location_deg <= 180.0:
            raise ValueError("placement longitude_location_deg must be finite in [-180, 180]")
        _nonempty(self.geometry_source_id, name="geometry_source_id")
        _nonempty(self.source_id, name="source_id")
        if not isinstance(self.source_mode, HoraryGeometrySourceMode):
            raise TypeError("placement source_mode must be a HoraryGeometrySourceMode")
        if self.source_mode is HoraryGeometrySourceMode.COMPUTED:
            if self.jd_ut1 is None or not math.isfinite(self.jd_ut1):
                raise ValueError("computed body placement requires finite jd_ut1")
        elif self.jd_ut1 is not None:
            raise ValueError("historical source-chart placement cannot claim jd_ut1")


@dataclass(frozen=True, slots=True)
class HorarySolarProximityReceipt:
    """Identity-bound composition receipt for existing solar-proximity truth."""

    question_id: str
    body: str
    truth: SolarProximityTruth
    calculation_policy_id: str
    latitude_deg: float
    longitude_deg: float
    geometry_source_id: str
    source_id: str
    source_mode: HoraryGeometrySourceMode
    jd_ut1: float | None
    source_component: str = "moira.dignities_types.SolarProximityTruth"

    def __post_init__(self) -> None:
        _nonempty(self.question_id, name="question_id")
        if self.body not in _TRADITIONAL_BODIES:
            raise ValueError("solar-proximity receipt body must be one of the traditional seven")
        if not isinstance(self.truth, SolarProximityTruth):
            raise TypeError("solar-proximity receipt truth must be a SolarProximityTruth")
        _nonempty(self.calculation_policy_id, name="calculation_policy_id")
        if not math.isfinite(self.latitude_deg) or not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("solar-proximity latitude_deg must be finite in [-90, 90]")
        if not math.isfinite(self.longitude_deg) or not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("solar-proximity longitude_deg must be finite in [-180, 180]")
        _nonempty(self.geometry_source_id, name="geometry_source_id")
        _nonempty(self.source_id, name="source_id")
        if not isinstance(self.source_mode, HoraryGeometrySourceMode):
            raise TypeError("solar-proximity source_mode must be a HoraryGeometrySourceMode")
        if self.source_mode is HoraryGeometrySourceMode.COMPUTED:
            if self.jd_ut1 is None or not math.isfinite(self.jd_ut1):
                raise ValueError("computed solar-proximity receipt requires finite jd_ut1")
        elif self.jd_ut1 is not None:
            raise ValueError("historical solar-proximity receipt cannot claim jd_ut1")
        if self.source_component != "moira.dignities_types.SolarProximityTruth":
            raise ValueError("source_component is fixed to the admitted typed truth")


@dataclass(frozen=True, slots=True)
class HoraryConsiderationInputs:
    """Explicit dependencies for the finite, mechanically evaluable v1 rules."""

    moon_placement: HoraryBodyPlacementReceipt | None = None
    saturn_placement: HoraryBodyPlacementReceipt | None = None
    first_ruler_solar_proximity: HorarySolarProximityReceipt | None = None

    def __post_init__(self) -> None:
        for value, body, name in (
            (self.moon_placement, Body.MOON, "moon_placement"),
            (self.saturn_placement, Body.SATURN, "saturn_placement"),
        ):
            if value is not None and not isinstance(value, HoraryBodyPlacementReceipt):
                raise TypeError(f"{name} must be a HoraryBodyPlacementReceipt or None")
            if value is not None and value.body != body:
                raise ValueError(f"{name} must identify {body}")
        if self.first_ruler_solar_proximity is not None and not isinstance(
            self.first_ruler_solar_proximity, HorarySolarProximityReceipt
        ):
            raise TypeError(
                "first_ruler_solar_proximity must be a HorarySolarProximityReceipt or None"
            )


@dataclass(frozen=True, slots=True)
class HoraryConsiderationEvidence:
    """One consideration before judgement, kept separate from all others."""

    rule_id: str
    state: HoraryRuleState
    observed: tuple[tuple[str, str | bool | int | float], ...]
    reason: str | None
    source_reference: str = _AUTHORITY

    def __post_init__(self) -> None:
        if not isinstance(self.state, HoraryRuleState):
            raise TypeError("state must be a HoraryRuleState")
        if self.rule_id not in _CONSIDERATION_RULE_IDS:
            raise ValueError("unknown Horary consideration rule id")
        object.__setattr__(self, "observed", tuple(self.observed))
        for name, value in self.observed:
            _nonempty(name, name="observation name")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("consideration observations must be finite")
        if self.state is HoraryRuleState.NOT_EVALUABLE:
            if not self.reason:
                raise ValueError("not-evaluable consideration requires a reason")
        elif self.reason is not None:
            raise ValueError("evaluated consideration cannot carry a failure reason")


@dataclass(frozen=True, slots=True)
class HoraryPerfectionSearchPolicy:
    """Moira-owned finite safety limit; not a historical duration doctrine."""

    policy_id: str = "moira_horary_perfection_search_safety_31_days_v1"
    max_span_days: float = 31.0
    authority: str = "moira_owned_computational_safety_not_historical_doctrine"
    interval_selection: str = "caller_supplied_start_and_end_preserved"
    historical_duration_claim: bool = False

    def __post_init__(self) -> None:
        if type(self.policy_id) is not str:
            raise TypeError("Horary perfection search policy_id must be a concrete str")
        if type(self.max_span_days) is not float:
            raise TypeError("Horary perfection max_span_days must be a concrete float")
        if type(self.authority) is not str:
            raise TypeError("Horary perfection search authority must be a concrete str")
        if type(self.interval_selection) is not str:
            raise TypeError("Horary perfection interval_selection must be a concrete str")
        if type(self.historical_duration_claim) is not bool:
            raise TypeError("historical_duration_claim must be a bool")
        if self.policy_id != "moira_horary_perfection_search_safety_31_days_v1":
            raise ValueError("Horary perfection search policy_id is fixed")
        if self.max_span_days != 31.0:
            raise ValueError("Horary perfection max_span_days is fixed at 31")
        if self.authority != "moira_owned_computational_safety_not_historical_doctrine":
            raise ValueError("Horary perfection search authority is fixed as Moira-owned")
        if self.interval_selection != "caller_supplied_start_and_end_preserved":
            raise ValueError("Horary perfection interval selection must remain caller-owned")
        if self.historical_duration_claim is not False:
            raise ValueError("Horary perfection safety policy cannot claim historical duration")


MOIRA_HORARY_PERFECTION_SEARCH_SAFETY_V1 = HoraryPerfectionSearchPolicy()


def _validate_perfection_analysis_contract(
    principal_querent: str | None,
    principal_quesited: str | None,
    analysis: ClassicalPerfectionAnalysis,
    search_policy: HoraryPerfectionSearchPolicy,
) -> None:
    """Reject any perfection vessel outside the exact admitted Lilly contract."""

    if not isinstance(analysis, ClassicalPerfectionAnalysis):
        raise TypeError("analysis must be a ClassicalPerfectionAnalysis")
    if type(search_policy) is not HoraryPerfectionSearchPolicy:
        raise TypeError("search_policy must be a HoraryPerfectionSearchPolicy")
    if search_policy is not MOIRA_HORARY_PERFECTION_SEARCH_SAFETY_V1:
        raise ValueError("only the fixed Moira Horary perfection safety policy is admitted")
    if (
        principal_querent not in _TRADITIONAL_BODIES
        or principal_quesited not in _TRADITIONAL_BODIES
        or principal_querent == principal_quesited
    ):
        raise ValueError("composed perfection evidence requires two distinct principals")
    if {principal_querent, principal_quesited} != {
        analysis.significator_a,
        analysis.significator_b,
    }:
        raise ValueError("perfection analysis must describe the principal pair")
    if type(analysis.policy) is not LillyPerfectionPolicy:
        raise TypeError("perfection analysis policy must be the concrete LillyPerfectionPolicy")
    if analysis.policy is not LILLY_1647_PERFECTION_V1:
        raise ValueError("perfection analysis must preserve the canonical Lilly policy identity")
    if (
        analysis.profile_id != LILLY_1647_PERFECTION_V1.profile_id
        or analysis.profile_version != LILLY_1647_PERFECTION_V1.profile_version
    ):
        raise ValueError("perfection analysis must preserve the exact admitted Lilly policy")
    if type(analysis.is_day_chart) is not bool:
        raise TypeError("perfection analysis is_day_chart must be a bool")
    if (
        not math.isfinite(analysis.jd_start)
        or not math.isfinite(analysis.jd_end)
        or analysis.jd_end <= analysis.jd_start
        or analysis.jd_end - analysis.jd_start > search_policy.max_span_days
    ):
        raise ValueError(
            "perfection analysis interval exceeds the fixed finite Moira Horary safety policy"
        )
    if not isinstance(analysis.reader_provenance, str) or not analysis.reader_provenance.strip():
        raise ValueError("perfection analysis requires non-empty reader provenance")
    initial_bodies = tuple(item.body for item in analysis.initial_states)
    if len(initial_bodies) != len(_TRADITIONAL_BODIES) or set(initial_bodies) != set(
        _TRADITIONAL_BODIES
    ):
        raise ValueError("perfection analysis requires all seven unique initial body states")
    if any(
        not isinstance(item.kind, ClassicalPerfectionEventKind)
        for item in analysis.events
    ):
        raise TypeError("perfection event kind must be a ClassicalPerfectionEventKind")
    if any(
        not isinstance(item.kind, LillyPerfectionKind)
        or not isinstance(item.state, ClassicalPerfectionState)
        for item in analysis.witnesses
    ):
        raise TypeError("perfection witness kind and state must be enum instances")
    if any(
        not isinstance(item, LillyPerfectionKind)
        for item in (*analysis.present_kinds, *analysis.indeterminate_kinds)
    ):
        raise TypeError("perfection summary kinds must be LillyPerfectionKind instances")
    if tuple(item.kind for item in analysis.witnesses) != _PERFECTION_WITNESS_ORDER:
        raise ValueError("perfection analysis requires the six source-ordered witnesses")
    if any(
        not isinstance(item.source_reference, str)
        or not item.source_reference.startswith(f"{_PERFECTION_AUTHORITY}; ")
        for item in analysis.witnesses
    ):
        raise ValueError("perfection witness authority receipt is not admitted")
    if analysis.authorities != (_PERFECTION_AUTHORITY,):
        raise ValueError("perfection analysis authority receipt is not admitted")
    if analysis.complete_electional_judgement is not False:
        raise ValueError("perfection analysis cannot claim complete judgement")
    if analysis.scoring != "not_provided":
        raise ValueError("perfection analysis scoring must remain not_provided")
    if analysis.advice_language != "not_provided":
        raise ValueError("perfection analysis advice must remain not_provided")
    reconstructed = classify_lilly_perfection_events(
        analysis.jd_start,
        analysis.jd_end,
        analysis.significator_a,
        analysis.significator_b,
        is_day_chart=analysis.is_day_chart,
        initial_states=analysis.initial_states,
        events=analysis.events,
        reader_provenance=analysis.reader_provenance,
        policy=LILLY_1647_PERFECTION_V1,
    )
    if analysis.events != reconstructed.events:
        raise ValueError("perfection analysis events must remain canonically ordered")
    if (
        analysis.witnesses != reconstructed.witnesses
        or analysis.present_kinds != reconstructed.present_kinds
        or analysis.indeterminate_kinds != reconstructed.indeterminate_kinds
    ):
        raise ValueError(
            "perfection witness truth must be reconstructed from the preserved inputs and events"
        )


@dataclass(frozen=True, slots=True)
class HoraryPerfectionEvidence:
    """Question-owned wrapper around an existing Lilly perfection analysis."""

    state: HoraryPerfectionState
    principal_querent: str | None
    principal_quesited: str | None
    analysis: ClassicalPerfectionAnalysis | None
    reason: str | None
    search_policy: HoraryPerfectionSearchPolicy = (
        MOIRA_HORARY_PERFECTION_SEARCH_SAFETY_V1
    )

    def __post_init__(self) -> None:
        if not isinstance(self.state, HoraryPerfectionState):
            raise TypeError("state must be a HoraryPerfectionState")
        if type(self.search_policy) is not HoraryPerfectionSearchPolicy:
            raise TypeError("search_policy must be a HoraryPerfectionSearchPolicy")
        if self.state is HoraryPerfectionState.COMPOSED:
            if self.analysis is None or self.reason is not None:
                raise ValueError("composed perfection evidence requires only an analysis")
            _validate_perfection_analysis_contract(
                self.principal_querent,
                self.principal_quesited,
                self.analysis,
                self.search_policy,
            )
        else:
            if self.search_policy is not MOIRA_HORARY_PERFECTION_SEARCH_SAFETY_V1:
                raise ValueError("not-evaluable perfection evidence must preserve search policy")
            if self.analysis is not None or not self.reason:
                raise ValueError("not-evaluable perfection evidence requires only a reason")


@dataclass(frozen=True, slots=True)
class HoraryProvenance:
    """Fixed scope and authority receipt for the bounded v1 profile."""

    lineage_id: str = "lilly_1647_ca_books_i_ii_v1"
    profile_version: str = "1.0.0"
    authority: str = _AUTHORITY
    unresolved_policies: tuple[str, ...] = _UNRESOLVED_POLICIES
    excluded_components: tuple[str, ...] = _EXCLUDED_COMPONENTS
    complete_horary_judgement: bool = False
    scoring: str = "not_provided"
    outcome_language: str = "not_provided"
    advice_language: str = "not_provided"

    def __post_init__(self) -> None:
        expected = {
            "lineage_id": "lilly_1647_ca_books_i_ii_v1",
            "profile_version": "1.0.0",
            "authority": _AUTHORITY,
            "unresolved_policies": _UNRESOLVED_POLICIES,
            "excluded_components": _EXCLUDED_COMPONENTS,
            "complete_horary_judgement": False,
            "scoring": "not_provided",
            "outcome_language": "not_provided",
            "advice_language": "not_provided",
        }
        for name, value in expected.items():
            if getattr(self, name) != value:
                raise ValueError(f"{name} is fixed for the admitted Horary v1 profile")


LILLY_1647_HORARY_V1 = HoraryProvenance()


@dataclass(frozen=True, slots=True)
class HoraryEvidenceProfile:
    """Atomic, non-interpretive Horary evidence composition."""

    question: HoraryQuestionReceipt
    house_policy: HoraryHousePolicy
    house_geometry: HoraryHouseGeometryReceipt
    chart_policy: HoraryChartPolicyReceipt
    turned_house: HoraryTurnedHouseReceipt
    significators: HorarySignificatorSet
    chart_sect: HoraryChartSectReceipt
    hour_agreement: HoraryHourAgreementEvidence
    consideration_inputs: HoraryConsiderationInputs
    considerations: tuple[HoraryConsiderationEvidence, ...]
    perfection_analysis_input: ClassicalPerfectionAnalysis | None
    perfection: HoraryPerfectionEvidence
    provenance: HoraryProvenance = LILLY_1647_HORARY_V1

    def __post_init__(self) -> None:
        object.__setattr__(self, "considerations", tuple(self.considerations))
        if type(self.house_policy) is not HoraryHousePolicy:
            raise TypeError("house_policy must be the concrete HoraryHousePolicy")
        typed_fields = (
            (self.question, HoraryQuestionReceipt, "question"),
            (self.house_policy, HoraryHousePolicy, "house_policy"),
            (self.house_geometry, HoraryHouseGeometryReceipt, "house_geometry"),
            (self.chart_policy, HoraryChartPolicyReceipt, "chart_policy"),
            (self.turned_house, HoraryTurnedHouseReceipt, "turned_house"),
            (self.significators, HorarySignificatorSet, "significators"),
            (self.chart_sect, HoraryChartSectReceipt, "chart_sect"),
            (self.hour_agreement, HoraryHourAgreementEvidence, "hour_agreement"),
            (self.consideration_inputs, HoraryConsiderationInputs, "consideration_inputs"),
            (self.perfection, HoraryPerfectionEvidence, "perfection"),
            (self.provenance, HoraryProvenance, "provenance"),
        )
        for value, expected_type, name in typed_fields:
            if not isinstance(value, expected_type):
                raise TypeError(f"{name} must be a {expected_type.__name__}")
        if any(
            not isinstance(item, HoraryConsiderationEvidence)
            for item in self.considerations
        ):
            raise TypeError("considerations must contain HoraryConsiderationEvidence")
        if self.perfection_analysis_input is not None and not isinstance(
            self.perfection_analysis_input,
            ClassicalPerfectionAnalysis,
        ):
            raise TypeError(
                "perfection_analysis_input must be a ClassicalPerfectionAnalysis or None"
            )

        expected = _compose_profile_components(
            self.question,
            self.house_geometry,
            self.house_policy,
            planetary_hour=self.hour_agreement.planetary_hour_receipt,
            consideration_inputs=self.consideration_inputs,
            perfection_analysis=self.perfection_analysis_input,
        )
        actual = (
            self.turned_house,
            self.chart_policy,
            self.significators,
            self.chart_sect,
            self.hour_agreement,
            self.considerations,
            self.perfection,
        )
        component_names = (
            "turned_house",
            "chart_policy",
            "significators",
            "chart_sect",
            "hour_agreement",
            "considerations",
            "perfection",
        )
        for name, actual_value, expected_value in zip(component_names, actual, expected):
            if actual_value != expected_value:
                raise ValueError(f"{name} must derive from the profile's bound input receipts")


def resolve_turned_house(
    perspective_path: tuple[int, ...],
    terminal_topic_house: int,
) -> HoraryTurnedHouseReceipt:
    """Resolve explicit 1-based perspective counts to one radical house.

    The count starts at the radical first.  Each perspective path item becomes
    the new first house, and the terminal topic is counted from the last
    perspective.  Thus perspective ``(7,)`` plus topic ``2`` resolves to the
    radical eighth.  No topic or additional turn is inferred.
    """

    path = tuple(perspective_path)
    for index, house in enumerate(path):
        _valid_house(house, name=f"perspective_path[{index}]")
    _valid_house(terminal_topic_house, name="terminal_topic_house")
    current = 1
    steps: list[HoraryTurnStepReceipt] = []
    for index, house in enumerate(path, start=1):
        resolved = ((current + house - 2) % 12) + 1
        steps.append(
            HoraryTurnStepReceipt(
                index=index,
                kind=HoraryTurnStepKind.PERSPECTIVE,
                from_radical_house=current,
                counted_house=house,
                resolved_radical_house=resolved,
            )
        )
        current = resolved
    resolved = ((current + terminal_topic_house - 2) % 12) + 1
    steps.append(
        HoraryTurnStepReceipt(
            index=len(steps) + 1,
            kind=HoraryTurnStepKind.TERMINAL_TOPIC,
            from_radical_house=current,
            counted_house=terminal_topic_house,
            resolved_radical_house=resolved,
        )
    )
    return HoraryTurnedHouseReceipt(
        perspective_path=path,
        terminal_topic_house=terminal_topic_house,
        steps=tuple(steps),
        resolved_radical_house=resolved,
    )


def _chart_policy_receipt(
    question: HoraryQuestionReceipt,
    geometry: HoraryHouseGeometryReceipt,
    policy: HoraryHousePolicy,
) -> HoraryChartPolicyReceipt:
    house_cusps = geometry.house_cusps
    effective = house_cusps.effective_system
    strict_house_policy = HousePolicy.strict()
    if geometry.question_id != question.question_id:
        reason = "house_geometry_question_id_mismatch"
    elif not math.isclose(
        geometry.latitude_deg,
        question.latitude_deg,
        rel_tol=0.0,
        abs_tol=_COORD_BIND_TOL,
    ) or not math.isclose(
        geometry.longitude_deg,
        question.longitude_deg,
        rel_tol=0.0,
        abs_tol=_COORD_BIND_TOL,
    ):
        reason = "house_geometry_location_mismatch"
    elif (
        type(house_cusps.policy) is not HousePolicy
        or house_cusps.policy.unknown_system is not strict_house_policy.unknown_system
        or house_cusps.policy.polar_fallback is not strict_house_policy.polar_fallback
    ):
        reason = "house_result_policy_is_not_strict"
    elif (
        geometry.source_mode is HoraryGeometrySourceMode.COMPUTED
        and question.time.state is not HoraryEvidenceState.EVALUATED
    ):
        reason = "computed_house_geometry_requires_evaluated_question_epoch"
    elif (
        geometry.source_mode is HoraryGeometrySourceMode.COMPUTED
        and not math.isclose(
            float(geometry.jd_ut1),
            float(question.time.normalized_jd_ut1),
            rel_tol=0.0,
            abs_tol=_JD_BIND_TOL,
        )
    ):
        reason = "house_geometry_epoch_mismatch"
    elif house_cusps.system != policy.house_system:
        reason = "house_result_requested_system_does_not_match_caller_policy"
    elif not effective:
        reason = "house_result_missing_effective_system_truth"
    elif effective != policy.house_system:
        reason = "house_result_effective_system_does_not_match_caller_policy"
    elif house_cusps.fallback:
        reason = "house_result_used_fallback_geometry"
    else:
        return HoraryChartPolicyReceipt(
            state=HoraryEvidenceState.EVALUATED,
            requested_system=policy.house_system,
            effective_system=effective,
            fallback=False,
            reason=None,
        )
    return HoraryChartPolicyReceipt(
        state=HoraryEvidenceState.NOT_EVALUABLE,
        requested_system=policy.house_system,
        effective_system=effective,
        fallback=house_cusps.fallback,
        reason=reason,
    )


def _not_evaluable_significator(
    role: HorarySignificatorRole,
    reason: str,
) -> HorarySignificatorEvidence:
    return HorarySignificatorEvidence(
        role=role,
        state=HoraryEvidenceState.NOT_EVALUABLE,
        body=None,
        radical_house=None,
        cusp_longitude_deg=None,
        sign=None,
        reason=reason,
    )


def _principal_significator(
    role: HorarySignificatorRole,
    house: int,
    house_cusps: HouseCusps,
) -> HorarySignificatorEvidence:
    longitude = float(house_cusps.cusps[house - 1])
    sign = house_cusps.sign_of_cusp(house)[0]
    return HorarySignificatorEvidence(
        role=role,
        state=HoraryEvidenceState.EVALUATED,
        body=DOMICILE_RULERS[sign],
        radical_house=house,
        cusp_longitude_deg=longitude,
        sign=sign,
        reason=None,
    )


def _significators(
    chart_policy: HoraryChartPolicyReceipt,
    house_cusps: HouseCusps,
    topic_house: int,
) -> HorarySignificatorSet:
    if chart_policy.state is HoraryEvidenceState.NOT_EVALUABLE:
        reason = chart_policy.reason or "house_geometry_not_evaluable"
        return HorarySignificatorSet(
            state=HoraryEvidenceState.NOT_EVALUABLE,
            principal_querent=_not_evaluable_significator(
                HorarySignificatorRole.PRINCIPAL_QUERENT, reason
            ),
            querent_co_significator=_not_evaluable_significator(
                HorarySignificatorRole.QUERENT_CO_SIGNIFICATOR, reason
            ),
            principal_quesited=_not_evaluable_significator(
                HorarySignificatorRole.PRINCIPAL_QUESITED, reason
            ),
            same_body_principals=None,
            reason=reason,
        )
    querent = _principal_significator(
        HorarySignificatorRole.PRINCIPAL_QUERENT, 1, house_cusps
    )
    co_significator = HorarySignificatorEvidence(
        role=HorarySignificatorRole.QUERENT_CO_SIGNIFICATOR,
        state=HoraryEvidenceState.EVALUATED,
        body=Body.MOON,
        radical_house=None,
        cusp_longitude_deg=None,
        sign=None,
        reason=None,
    )
    quesited = _principal_significator(
        HorarySignificatorRole.PRINCIPAL_QUESITED, topic_house, house_cusps
    )
    return HorarySignificatorSet(
        state=HoraryEvidenceState.EVALUATED,
        principal_querent=querent,
        querent_co_significator=co_significator,
        principal_quesited=quesited,
        same_body_principals=querent.body == quesited.body,
        reason=None,
    )


def _hour_rule(
    rule_id: str,
    value: bool | None,
    *,
    derived_by: str,
    missing_reason: str,
    observed: tuple[tuple[str, str | bool | int | float], ...] = (),
) -> HoraryHourRuleEvidence:
    state = (
        HoraryHourRuleState.NOT_EVALUABLE
        if value is None
        else HoraryHourRuleState.MATCHED
        if value
        else HoraryHourRuleState.NOT_MATCHED
    )
    return HoraryHourRuleEvidence(
        rule_id=rule_id,
        state=state,
        derived_by=derived_by,
        observed=observed,
        reason=missing_reason if value is None else None,
    )


def _validate_planetary_hour_semantics(
    receipt: HoraryPlanetaryHourReceipt,
) -> HoraryChartSect:
    """Revalidate exact unequal-hour geometry, including after object forgery."""

    if receipt.hour_number <= 12:
        period_start = receipt.sunrise_jd
        period_end = receipt.sunset_jd
        period_index = receipt.hour_number - 1
        expected_sect = HoraryChartSect.DAY
    else:
        period_start = receipt.sunset_jd
        period_end = receipt.sunrise_jd
        period_index = receipt.hour_number - 13
        expected_sect = HoraryChartSect.NIGHT
    if period_end <= period_start:
        if expected_sect is HoraryChartSect.DAY:
            raise ValueError("daytime planetary hours require sunrise before sunset")
        raise ValueError(
            "nighttime planetary hours require preceding sunset before following sunrise"
        )
    hour_length = (period_end - period_start) / 12.0
    expected_start = period_start + period_index * hour_length
    expected_end = expected_start + hour_length
    if not math.isclose(
        receipt.hour_start_jd,
        expected_start,
        rel_tol=0.0,
        abs_tol=_JD_BIND_TOL,
    ) or not math.isclose(
        receipt.hour_end_jd,
        expected_end,
        rel_tol=0.0,
        abs_tol=_JD_BIND_TOL,
    ):
        raise ValueError(
            "planetary-hour interval must be the exact twelfth of its sunrise/sunset period"
        )
    if not expected_start <= receipt.jd_ut1 < expected_end:
        raise ValueError("planetary-hour event jd_ut1 must lie inside its exact hour interval")
    derived_sect = receipt.sect
    if derived_sect is not expected_sect:
        raise ValueError("planetary-hour number conflicts with sunrise/sunset-derived sect")
    return derived_sect


def _planetary_hour_binding_reason(
    question: HoraryQuestionReceipt,
    geometry: HoraryHouseGeometryReceipt,
    receipt: HoraryPlanetaryHourReceipt | None,
) -> str | None:
    if question.time.state is HoraryEvidenceState.NOT_EVALUABLE:
        return "question_epoch_not_evaluable"
    if geometry.source_mode is not HoraryGeometrySourceMode.COMPUTED:
        return "historical_source_chart_has_no_event_bound_planetary_hour"
    if geometry.question_id != question.question_id:
        return "planetary_hour_geometry_question_id_mismatch"
    if not math.isclose(
        geometry.latitude_deg,
        question.latitude_deg,
        rel_tol=0.0,
        abs_tol=_COORD_BIND_TOL,
    ) or not math.isclose(
        geometry.longitude_deg,
        question.longitude_deg,
        rel_tol=0.0,
        abs_tol=_COORD_BIND_TOL,
    ):
        return "planetary_hour_geometry_location_mismatch"
    if receipt is None:
        return "planetary_hour_receipt_not_supplied"
    _validate_planetary_hour_semantics(receipt)
    if receipt.question_id != question.question_id:
        return "planetary_hour_question_id_mismatch"
    if not math.isclose(
        receipt.latitude_deg,
        question.latitude_deg,
        rel_tol=0.0,
        abs_tol=_COORD_BIND_TOL,
    ) or not math.isclose(
        receipt.longitude_deg,
        question.longitude_deg,
        rel_tol=0.0,
        abs_tol=_COORD_BIND_TOL,
    ):
        return "planetary_hour_location_mismatch"
    if not math.isclose(
        receipt.jd_ut1,
        float(question.time.normalized_jd_ut1),
        rel_tol=0.0,
        abs_tol=_JD_BIND_TOL,
    ):
        return "planetary_hour_question_epoch_mismatch"
    if not math.isclose(
        receipt.jd_ut1,
        float(geometry.jd_ut1),
        rel_tol=0.0,
        abs_tol=_JD_BIND_TOL,
    ):
        return "planetary_hour_geometry_epoch_mismatch"
    return None


def _chart_sect_receipt(
    question: HoraryQuestionReceipt,
    geometry: HoraryHouseGeometryReceipt,
    receipt: HoraryPlanetaryHourReceipt | None,
) -> HoraryChartSectReceipt:
    reason = _planetary_hour_binding_reason(question, geometry, receipt)
    question_jd = (
        question.time.normalized_jd_ut1
        if question.time.state is HoraryEvidenceState.EVALUATED
        else None
    )
    if reason is not None:
        return HoraryChartSectReceipt(
            state=HoraryEvidenceState.NOT_EVALUABLE,
            question_id=question.question_id,
            jd_ut1=question_jd,
            latitude_deg=question.latitude_deg,
            longitude_deg=question.longitude_deg,
            sect=None,
            planetary_hour_source_id=None if receipt is None else receipt.source_id,
            reason=reason,
        )
    assert receipt is not None
    return HoraryChartSectReceipt(
        state=HoraryEvidenceState.EVALUATED,
        question_id=question.question_id,
        jd_ut1=question_jd,
        latitude_deg=question.latitude_deg,
        longitude_deg=question.longitude_deg,
        sect=_validate_planetary_hour_semantics(receipt),
        planetary_hour_source_id=receipt.source_id,
        reason=None,
    )


def _hour_agreement(
    significators: HorarySignificatorSet,
    chart_sect: HoraryChartSectReceipt,
    receipt: HoraryPlanetaryHourReceipt | None,
) -> HoraryHourAgreementEvidence:
    ascendant_lord = significators.principal_querent.body
    binding_reason: str | None = None
    if significators.state is HoraryEvidenceState.NOT_EVALUABLE:
        binding_reason = "ascendant_lord_not_evaluable"
    elif chart_sect.state is HoraryEvidenceState.NOT_EVALUABLE:
        binding_reason = chart_sect.reason

    if binding_reason is not None:
        rules = tuple(
            _hour_rule(
                rule_id,
                None,
                derived_by="not_computed",
                missing_reason=binding_reason,
                observed=(),
            )
            for rule_id in _HOUR_RULE_IDS
        )
        return HoraryHourAgreementEvidence(
            state=HoraryHourAgreementState.NOT_EVALUABLE,
            ascendant_lord=ascendant_lord,
            hour_ruler=None if receipt is None else receipt.hour_ruler,
            planetary_hour_receipt=receipt,
            rules=rules,
            reason=binding_reason,
        )
    assert receipt is not None
    assert ascendant_lord is not None
    rising_sign = significators.principal_querent.sign
    assert rising_sign is not None
    assert chart_sect.sect is not None
    sect = chart_sect.sect.value
    element = _SIGN_ELEMENT[rising_sign]
    triplicity_ruler = _HOUR_TRIPLICITY_RULERS[element][0 if sect == "day" else 1]
    hour_nature = _PLANETARY_NATURE[receipt.hour_ruler]
    ascendant_lord_nature = _PLANETARY_NATURE[ascendant_lord]
    rules = (
        _hour_rule(
            _HOUR_RULE_IDS[0],
            receipt.hour_ruler == ascendant_lord,
            derived_by="exact_planet_identity",
            missing_reason="",
            observed=(
                ("hour_lord", receipt.hour_ruler),
                ("ascendant_lord", ascendant_lord),
            ),
        ),
        _hour_rule(
            _HOUR_RULE_IDS[1],
            receipt.hour_ruler == triplicity_ruler,
            derived_by="lilly_rising_sign_day_night_triplicity_table",
            missing_reason="",
            observed=(
                ("rising_sign", rising_sign),
                ("element", element),
                ("sect", sect),
                ("triplicity_ruler", triplicity_ruler),
                ("hour_lord", receipt.hour_ruler),
            ),
        ),
        _hour_rule(
            _HOUR_RULE_IDS[2],
            hour_nature == ascendant_lord_nature,
            derived_by="lilly_primary_hot_cold_moist_dry_nature_table",
            missing_reason="",
            observed=(
                ("hour_lord", receipt.hour_ruler),
                ("hour_lord_nature", "_".join(hour_nature)),
                ("ascendant_lord", ascendant_lord),
                ("ascendant_lord_nature", "_".join(ascendant_lord_nature)),
            ),
        ),
    )
    matched = any(item.state is HoraryHourRuleState.MATCHED for item in rules)
    state = (
        HoraryHourAgreementState.AGREES
        if matched
        else HoraryHourAgreementState.DOES_NOT_AGREE
    )
    return HoraryHourAgreementEvidence(
        state=state,
        ascendant_lord=ascendant_lord,
        hour_ruler=receipt.hour_ruler,
        planetary_hour_receipt=receipt,
        rules=rules,
        reason=None,
    )


def _consideration(
    rule_id: str,
    state: HoraryRuleState,
    observed: tuple[tuple[str, str | bool | int | float], ...] = (),
    reason: str | None = None,
) -> HoraryConsiderationEvidence:
    return HoraryConsiderationEvidence(
        rule_id=rule_id,
        state=state,
        observed=observed,
        reason=reason,
    )


def _bound_receipt_reason(
    question: HoraryQuestionReceipt,
    geometry: HoraryHouseGeometryReceipt,
    *,
    question_id: str,
    latitude_deg: float,
    longitude_deg: float,
    geometry_source_id: str,
    source_mode: HoraryGeometrySourceMode,
    jd_ut1: float | None,
    prefix: str,
) -> str | None:
    if question_id != question.question_id:
        return f"{prefix}_question_id_mismatch"
    if geometry_source_id != geometry.source_id:
        return f"{prefix}_geometry_source_mismatch"
    if source_mode is not geometry.source_mode:
        return f"{prefix}_source_mode_mismatch"
    if not math.isclose(
        latitude_deg,
        question.latitude_deg,
        rel_tol=0.0,
        abs_tol=_COORD_BIND_TOL,
    ) or not math.isclose(
        longitude_deg,
        question.longitude_deg,
        rel_tol=0.0,
        abs_tol=_COORD_BIND_TOL,
    ):
        return f"{prefix}_location_mismatch"
    if source_mode is HoraryGeometrySourceMode.COMPUTED:
        if question.time.state is not HoraryEvidenceState.EVALUATED:
            return f"{prefix}_requires_evaluated_question_epoch"
        if jd_ut1 is None:
            return f"{prefix}_missing_epoch"
        if not math.isclose(
            jd_ut1,
            float(question.time.normalized_jd_ut1),
            rel_tol=0.0,
            abs_tol=_JD_BIND_TOL,
        ):
            return f"{prefix}_question_epoch_mismatch"
        if not math.isclose(
            jd_ut1,
            float(geometry.jd_ut1),
            rel_tol=0.0,
            abs_tol=_JD_BIND_TOL,
        ):
            return f"{prefix}_geometry_epoch_mismatch"
    elif jd_ut1 is not None:
        return f"{prefix}_historical_mode_cannot_claim_epoch"
    return None


def _placement_binding_reason(
    question: HoraryQuestionReceipt,
    geometry: HoraryHouseGeometryReceipt,
    placement: HoraryBodyPlacementReceipt,
) -> str | None:
    reason = _bound_receipt_reason(
        question,
        geometry,
        question_id=placement.question_id,
        latitude_deg=placement.latitude_deg,
        longitude_deg=placement.longitude_location_deg,
        geometry_source_id=placement.geometry_source_id,
        source_mode=placement.source_mode,
        jd_ut1=placement.jd_ut1,
        prefix=f"{placement.body.lower()}_placement",
    )
    if reason is not None:
        return reason
    if house_of(placement.longitude_deg, geometry.house_cusps) != placement.house:
        return f"{placement.body.lower()}_placement_house_mismatch"
    return None


def _considerations(
    question: HoraryQuestionReceipt,
    chart_policy: HoraryChartPolicyReceipt,
    geometry: HoraryHouseGeometryReceipt,
    significators: HorarySignificatorSet,
    inputs: HoraryConsiderationInputs,
) -> tuple[HoraryConsiderationEvidence, ...]:
    house_cusps = geometry.house_cusps
    if chart_policy.state is HoraryEvidenceState.EVALUATED:
        asc_degree = house_cusps.sign_of_cusp(1)[2]
        early = _consideration(
            _CONSIDERATION_RULE_IDS[0],
            HoraryRuleState.CAUTION if asc_degree < 3.0 else HoraryRuleState.SATISFIED,
            (("ascendant_degree_in_sign", asc_degree), ("threshold_deg", 3.0)),
        )
        late = _consideration(
            _CONSIDERATION_RULE_IDS[1],
            HoraryRuleState.CAUTION if asc_degree >= 27.0 else HoraryRuleState.SATISFIED,
            (("ascendant_degree_in_sign", asc_degree), ("threshold_deg", 27.0)),
        )
    else:
        reason = "exact_house_geometry_not_evaluable"
        early = _consideration(
            _CONSIDERATION_RULE_IDS[0], HoraryRuleState.NOT_EVALUABLE, reason=reason
        )
        late = _consideration(
            _CONSIDERATION_RULE_IDS[1], HoraryRuleState.NOT_EVALUABLE, reason=reason
        )

    moon_placement = inputs.moon_placement
    moon_binding_reason = (
        chart_policy.reason
        if chart_policy.state is HoraryEvidenceState.NOT_EVALUABLE
        else None
        if moon_placement is None
        else _placement_binding_reason(question, geometry, moon_placement)
    )
    if moon_placement is None:
        via = _consideration(
            _CONSIDERATION_RULE_IDS[2],
            HoraryRuleState.NOT_EVALUABLE,
            reason="moon_placement_receipt_not_supplied",
        )
    elif moon_binding_reason is not None:
        via = _consideration(
            _CONSIDERATION_RULE_IDS[2],
            HoraryRuleState.NOT_EVALUABLE,
            (("moon_placement_source_id", moon_placement.source_id),),
            moon_binding_reason,
        )
    else:
        moon_longitude = moon_placement.longitude_deg
        in_via = 195.0 <= moon_longitude < 225.0
        via = _consideration(
            _CONSIDERATION_RULE_IDS[2],
            HoraryRuleState.CAUTION if in_via else HoraryRuleState.SATISFIED,
            (
                ("moon_longitude_deg", moon_longitude),
                ("interval_start_deg_inclusive", 195.0),
                ("interval_end_deg_exclusive", 225.0),
            ),
        )

    saturn_placement = inputs.saturn_placement
    saturn_binding_reason = (
        chart_policy.reason
        if chart_policy.state is HoraryEvidenceState.NOT_EVALUABLE
        else None
        if saturn_placement is None
        else _placement_binding_reason(question, geometry, saturn_placement)
    )
    if saturn_placement is None:
        saturn_first = _consideration(
            _CONSIDERATION_RULE_IDS[3],
            HoraryRuleState.NOT_EVALUABLE,
            reason="saturn_placement_receipt_not_supplied",
        )
        saturn_seventh = _consideration(
            _CONSIDERATION_RULE_IDS[4],
            HoraryRuleState.NOT_EVALUABLE,
            reason="saturn_placement_receipt_not_supplied",
        )
    elif saturn_binding_reason is not None:
        observed = (("saturn_placement_source_id", saturn_placement.source_id),)
        saturn_first = _consideration(
            _CONSIDERATION_RULE_IDS[3],
            HoraryRuleState.NOT_EVALUABLE,
            observed,
            saturn_binding_reason,
        )
        saturn_seventh = _consideration(
            _CONSIDERATION_RULE_IDS[4],
            HoraryRuleState.NOT_EVALUABLE,
            observed,
            saturn_binding_reason,
        )
    else:
        saturn_house = saturn_placement.house
        saturn_first = _consideration(
            _CONSIDERATION_RULE_IDS[3],
            HoraryRuleState.CAUTION if saturn_house == 1 else HoraryRuleState.SATISFIED,
            (("saturn_house", saturn_house),),
        )
        saturn_seventh = _consideration(
            _CONSIDERATION_RULE_IDS[4],
            HoraryRuleState.CAUTION if saturn_house == 7 else HoraryRuleState.SATISFIED,
            (("saturn_house", saturn_house),),
        )

    first_ruler = significators.principal_querent.body
    if significators.state is HoraryEvidenceState.NOT_EVALUABLE:
        combust = _consideration(
            _CONSIDERATION_RULE_IDS[5],
            HoraryRuleState.NOT_EVALUABLE,
            reason="first_house_ruler_not_evaluable",
        )
    elif first_ruler == Body.SUN:
        combust = _consideration(
            _CONSIDERATION_RULE_IDS[5],
            HoraryRuleState.NOT_APPLICABLE,
            (("first_house_ruler", Body.SUN),),
        )
    elif inputs.first_ruler_solar_proximity is None:
        combust = _consideration(
            _CONSIDERATION_RULE_IDS[5],
            HoraryRuleState.NOT_EVALUABLE,
            (("first_house_ruler", first_ruler or ""),),
            "first_house_ruler_solar_proximity_truth_not_supplied",
        )
    elif inputs.first_ruler_solar_proximity.body != first_ruler:
        receipt = inputs.first_ruler_solar_proximity
        combust = _consideration(
            _CONSIDERATION_RULE_IDS[5],
            HoraryRuleState.NOT_EVALUABLE,
            (
                ("first_house_ruler", first_ruler or ""),
                ("solar_proximity_receipt_body", receipt.body),
            ),
            "solar_proximity_receipt_body_does_not_match_first_house_ruler",
        )
    elif (
        binding_reason := _bound_receipt_reason(
            question,
            geometry,
            question_id=inputs.first_ruler_solar_proximity.question_id,
            latitude_deg=inputs.first_ruler_solar_proximity.latitude_deg,
            longitude_deg=inputs.first_ruler_solar_proximity.longitude_deg,
            geometry_source_id=inputs.first_ruler_solar_proximity.geometry_source_id,
            source_mode=inputs.first_ruler_solar_proximity.source_mode,
            jd_ut1=inputs.first_ruler_solar_proximity.jd_ut1,
            prefix="solar_proximity",
        )
    ) is not None:
        receipt = inputs.first_ruler_solar_proximity
        combust = _consideration(
            _CONSIDERATION_RULE_IDS[5],
            HoraryRuleState.NOT_EVALUABLE,
            (
                ("first_house_ruler", first_ruler or ""),
                ("solar_proximity_source_id", receipt.source_id),
            ),
            binding_reason,
        )
    elif inputs.first_ruler_solar_proximity.truth.status is TruthEvaluationStatus.NOT_EVALUABLE:
        proximity = inputs.first_ruler_solar_proximity.truth
        combust = _consideration(
            _CONSIDERATION_RULE_IDS[5],
            HoraryRuleState.NOT_EVALUABLE,
            (
                ("first_house_ruler", first_ruler or ""),
                ("solar_proximity_status", proximity.status.value),
                ("solar_proximity_reason", proximity.reason or "unspecified"),
            ),
            "first_house_ruler_solar_proximity_truth_not_evaluable",
        )
    else:
        proximity = inputs.first_ruler_solar_proximity.truth
        assert proximity.band is not None and proximity.distance_from_sun_deg is not None
        combust = _consideration(
            _CONSIDERATION_RULE_IDS[5],
            HoraryRuleState.CAUTION
            if proximity.band is SolarProximityBand.COMBUST
            else HoraryRuleState.SATISFIED,
            (
                ("first_house_ruler", first_ruler or ""),
                ("solar_proximity_band", proximity.band.value),
                ("distance_from_sun_deg", proximity.distance_from_sun_deg),
            ),
        )
    return (
        early,
        late,
        via,
        saturn_first,
        saturn_seventh,
        combust,
    )


def _perfection(
    question: HoraryQuestionReceipt,
    geometry: HoraryHouseGeometryReceipt,
    significators: HorarySignificatorSet,
    chart_sect: HoraryChartSectReceipt,
    analysis: ClassicalPerfectionAnalysis | None,
) -> HoraryPerfectionEvidence:
    querent = significators.principal_querent.body
    quesited = significators.principal_quesited.body
    if significators.state is HoraryEvidenceState.NOT_EVALUABLE:
        return HoraryPerfectionEvidence(
            state=HoraryPerfectionState.NOT_EVALUABLE,
            principal_querent=None,
            principal_quesited=None,
            analysis=None,
            reason="principal_significators_not_evaluable",
        )
    if question.time.state is HoraryEvidenceState.NOT_EVALUABLE:
        return HoraryPerfectionEvidence(
            state=HoraryPerfectionState.NOT_EVALUABLE,
            principal_querent=querent,
            principal_quesited=quesited,
            analysis=None,
            reason="question_epoch_not_evaluable_for_perfection",
        )
    if geometry.source_mode is not HoraryGeometrySourceMode.COMPUTED:
        return HoraryPerfectionEvidence(
            state=HoraryPerfectionState.NOT_EVALUABLE,
            principal_querent=querent,
            principal_quesited=quesited,
            analysis=None,
            reason="historical_source_chart_assignment_has_no_perfection_epoch",
        )
    if significators.same_body_principals:
        if analysis is not None:
            raise ValueError("same-body principal collision cannot accept pairwise perfection")
        return HoraryPerfectionEvidence(
            state=HoraryPerfectionState.NOT_EVALUABLE,
            principal_querent=querent,
            principal_quesited=quesited,
            analysis=None,
            reason="principal_significators_are_same_body",
        )
    if analysis is None:
        return HoraryPerfectionEvidence(
            state=HoraryPerfectionState.NOT_EVALUABLE,
            principal_querent=querent,
            principal_quesited=quesited,
            analysis=None,
            reason="classical_perfection_analysis_not_supplied",
        )
    if type(analysis.is_day_chart) is not bool:
        raise TypeError("perfection analysis is_day_chart must be a bool")
    if chart_sect.state is HoraryEvidenceState.EVALUATED:
        assert chart_sect.sect is not None
        expected_is_day_chart = chart_sect.sect is HoraryChartSect.DAY
        if analysis.is_day_chart is not expected_is_day_chart:
            raise ValueError(
                "perfection analysis sect does not match the bound question chart sect"
            )
    _validate_perfection_analysis_contract(
        querent,
        quesited,
        analysis,
        MOIRA_HORARY_PERFECTION_SEARCH_SAFETY_V1,
    )
    if not math.isclose(
        analysis.jd_start,
        float(question.time.normalized_jd_ut1),
        rel_tol=0.0,
        abs_tol=_JD_BIND_TOL,
    ):
        raise ValueError("perfection analysis jd_start must match the question epoch")
    if not math.isclose(
        analysis.jd_start,
        float(geometry.jd_ut1),
        rel_tol=0.0,
        abs_tol=_JD_BIND_TOL,
    ):
        raise ValueError("perfection analysis jd_start must match the house geometry epoch")
    if chart_sect.state is HoraryEvidenceState.NOT_EVALUABLE:
        return HoraryPerfectionEvidence(
            state=HoraryPerfectionState.NOT_EVALUABLE,
            principal_querent=querent,
            principal_quesited=quesited,
            analysis=None,
            reason="chart_sect_not_evaluable_for_perfection",
        )
    return HoraryPerfectionEvidence(
        state=HoraryPerfectionState.COMPOSED,
        principal_querent=querent,
        principal_quesited=quesited,
        analysis=analysis,
        reason=None,
    )


def _compose_profile_components(
    question: HoraryQuestionReceipt,
    house_geometry: HoraryHouseGeometryReceipt,
    house_policy: HoraryHousePolicy,
    *,
    planetary_hour: HoraryPlanetaryHourReceipt | None,
    consideration_inputs: HoraryConsiderationInputs,
    perfection_analysis: ClassicalPerfectionAnalysis | None,
) -> tuple[
    HoraryTurnedHouseReceipt,
    HoraryChartPolicyReceipt,
    HorarySignificatorSet,
    HoraryChartSectReceipt,
    HoraryHourAgreementEvidence,
    tuple[HoraryConsiderationEvidence, ...],
    HoraryPerfectionEvidence,
]:
    """Derive every cross-bound component from the preserved atomic inputs."""

    turned = resolve_turned_house(
        question.perspective_path,
        question.terminal_topic_house,
    )
    chart_policy = _chart_policy_receipt(question, house_geometry, house_policy)
    assignments = _significators(
        chart_policy,
        house_geometry.house_cusps,
        turned.resolved_radical_house,
    )
    chart_sect = _chart_sect_receipt(
        question,
        house_geometry,
        planetary_hour,
    )
    hour_agreement = _hour_agreement(
        assignments,
        chart_sect,
        planetary_hour,
    )
    considerations = _considerations(
        question,
        chart_policy,
        house_geometry,
        assignments,
        consideration_inputs,
    )
    perfection = _perfection(
        question,
        house_geometry,
        assignments,
        chart_sect,
        perfection_analysis,
    )
    return (
        turned,
        chart_policy,
        assignments,
        chart_sect,
        hour_agreement,
        considerations,
        perfection,
    )


def evaluate_horary_evidence(
    question: HoraryQuestionReceipt,
    house_geometry: HoraryHouseGeometryReceipt,
    *,
    house_policy: HoraryHousePolicy,
    planetary_hour: HoraryPlanetaryHourReceipt | None = None,
    considerations: HoraryConsiderationInputs | None = None,
    perfection_analysis: ClassicalPerfectionAnalysis | None = None,
) -> HoraryEvidenceProfile:
    """Compose one atomic Horary evidence profile from explicit inputs.

    House geometry and any perfection analysis are caller-supplied products.
    This function performs no astronomical search.  It reclassifies the
    preserved perfection trace to authenticate its six witnesses, without
    calling the ephemeris-backed perfection search.  Exact house-policy
    mismatch or fallback yields typed not-evaluable evidence rather than
    silent substitution.
    """

    if type(question) is not HoraryQuestionReceipt:
        raise TypeError("question must be the concrete HoraryQuestionReceipt")
    if not isinstance(house_geometry, HoraryHouseGeometryReceipt):
        raise TypeError("house_geometry must be a HoraryHouseGeometryReceipt")
    if type(house_policy) is not HoraryHousePolicy:
        raise TypeError("house_policy must be the concrete HoraryHousePolicy")
    if planetary_hour is not None and not isinstance(planetary_hour, HoraryPlanetaryHourReceipt):
        raise TypeError("planetary_hour must be a HoraryPlanetaryHourReceipt or None")
    resolved_inputs = considerations or HoraryConsiderationInputs()
    if not isinstance(resolved_inputs, HoraryConsiderationInputs):
        raise TypeError("considerations must be a HoraryConsiderationInputs or None")
    if perfection_analysis is not None and not isinstance(
        perfection_analysis, ClassicalPerfectionAnalysis
    ):
        raise TypeError("perfection_analysis must be a ClassicalPerfectionAnalysis or None")

    (
        turned,
        chart_policy,
        assignments,
        chart_sect,
        hour_agreement,
        consideration_evidence,
        perfection,
    ) = _compose_profile_components(
        question,
        house_geometry,
        house_policy,
        planetary_hour=planetary_hour,
        consideration_inputs=resolved_inputs,
        perfection_analysis=perfection_analysis,
    )
    return HoraryEvidenceProfile(
        question=question,
        house_policy=house_policy,
        house_geometry=house_geometry,
        chart_policy=chart_policy,
        turned_house=turned,
        significators=assignments,
        chart_sect=chart_sect,
        hour_agreement=hour_agreement,
        consideration_inputs=resolved_inputs,
        considerations=consideration_evidence,
        perfection_analysis_input=perfection_analysis,
        perfection=perfection,
    )


def horary_evidence_at(
    question: HoraryQuestionReceipt,
    *,
    house_policy: HoraryHousePolicy,
    perfection_jd_end: float | None = None,
    reader: KernelReader,
) -> HoraryEvidenceProfile:
    """Compute the admitted Horary evidence profile at one question epoch.

    This is the engine-owned assembly boundary above
    :func:`evaluate_horary_evidence`.  It requires the caller's already
    normalized question receipt, an explicit exact house-system policy, and an
    explicit ephemeris reader.  It computes strict no-fallback house geometry,
    unequal planetary-hour truth, the traditional-seven planetary positions,
    and the admitted finite consideration inputs.  Pairwise Lilly perfection
    is searched only when ``perfection_jd_end`` is supplied and the principal
    significators and chart sect are computationally evaluable.

    No topic, house system, duration, score, outcome, or advice is inferred.
    ``perfection_jd_end`` is UT1 and remains bounded by Moira's fixed 31-day
    computational safety policy; that bound is not historical doctrine.
    """

    if type(question) is not HoraryQuestionReceipt:
        raise TypeError("question must be the concrete HoraryQuestionReceipt")
    if type(house_policy) is not HoraryHousePolicy:
        raise TypeError("house_policy must be the concrete HoraryHousePolicy")
    if reader is None:
        raise TypeError("reader must be supplied explicitly")
    if question.time.state is not HoraryEvidenceState.EVALUATED:
        raise ValueError(
            "horary_evidence_at requires an evaluated normalized question epoch"
        )
    jd_ut1 = question.time.normalized_jd_ut1
    if (
        isinstance(jd_ut1, bool)
        or not isinstance(jd_ut1, (int, float))
        or not math.isfinite(jd_ut1)
    ):
        raise ValueError("question normalized_jd_ut1 must be a finite real number")
    jd_ut1 = float(jd_ut1)

    if perfection_jd_end is not None:
        if (
            isinstance(perfection_jd_end, bool)
            or not isinstance(perfection_jd_end, (int, float))
            or not math.isfinite(perfection_jd_end)
        ):
            raise ValueError("perfection_jd_end must be a finite real number or None")
        perfection_jd_end = float(perfection_jd_end)
        if perfection_jd_end <= jd_ut1:
            raise ValueError("perfection_jd_end must be later than the question epoch")
        if (
            perfection_jd_end - jd_ut1
            > MOIRA_HORARY_PERFECTION_SEARCH_SAFETY_V1.max_span_days
        ):
            raise ValueError(
                "perfection interval exceeds the fixed 31-day Moira Horary safety policy"
            )

    positions = {
        body: planet_at(
            body,
            jd_ut1,
            reader=reader,
            apparent=True,
            aberration=True,
            grav_deflection=True,
            nutation=True,
            center="geocentric",
            frame="ecliptic",
        )
        for body in _TRADITIONAL_BODIES
    }
    for body, position in positions.items():
        if getattr(position, "name", None) != body:
            raise ValueError("planet_at result identity does not match requested body")
    strict_house_policy = HousePolicy.strict()
    house_cusps = calculate_houses(
        jd_ut1,
        question.latitude_deg,
        question.longitude_deg,
        house_policy.house_system,
        policy=strict_house_policy,
        sun_longitude=positions[Body.SUN].longitude,
    )
    geometry_source_id = (
        "moira.houses.calculate_houses:"
        f"{house_policy.house_system}:strict_no_fallback:v1"
    )
    geometry = HoraryHouseGeometryReceipt(
        question_id=question.question_id,
        latitude_deg=question.latitude_deg,
        longitude_deg=question.longitude_deg,
        source_id=geometry_source_id,
        source_mode=HoraryGeometrySourceMode.COMPUTED,
        jd_ut1=jd_ut1,
        house_cusps=house_cusps,
    )

    hours_day = planetary_hours(
        jd_ut1,
        question.latitude_deg,
        question.longitude_deg,
        reader=reader,
    )
    if not math.isclose(
        hours_day.latitude,
        question.latitude_deg,
        rel_tol=0.0,
        abs_tol=_COORD_BIND_TOL,
    ) or not math.isclose(
        hours_day.longitude,
        question.longitude_deg,
        rel_tol=0.0,
        abs_tol=_COORD_BIND_TOL,
    ):
        raise ValueError("planetary-hours result location does not match the question")
    selected_hour = hours_day.hour_at(jd_ut1)
    planetary_hour_receipt: HoraryPlanetaryHourReceipt | None = None
    if selected_hour is not None:
        if selected_hour.is_daytime:
            sunrise_jd = hours_day.sunrise_jd
            sunset_jd = hours_day.sunset_jd
        else:
            sunrise_jd = hours_day.hours[-1].jd_end
            sunset_jd = hours_day.sunset_jd
        planetary_hour_receipt = HoraryPlanetaryHourReceipt(
            question_id=question.question_id,
            jd_ut1=jd_ut1,
            latitude_deg=question.latitude_deg,
            longitude_deg=question.longitude_deg,
            source_id="moira.planetary_hours.planetary_hours:explicit_reader:v1",
            hour_ruler=selected_hour.ruler,
            hour_number=selected_hour.hour_number,
            hour_start_jd=selected_hour.jd_start,
            hour_end_jd=selected_hour.jd_end,
            sunrise_jd=sunrise_jd,
            sunset_jd=sunset_jd,
            local_time_algorithm_id=(
                "moira_unequal_planetary_hours_sunrise_sunset:v1"
            ),
        )

    placements = {
        body: HoraryBodyPlacementReceipt(
            question_id=question.question_id,
            body=body,
            longitude_deg=position.longitude,
            house=house_of(position.longitude, house_cusps),
            latitude_deg=question.latitude_deg,
            longitude_location_deg=question.longitude_deg,
            geometry_source_id=geometry.source_id,
            source_id=(
                "moira.planets.planet_at:"
                f"{body}:apparent_geocentric_true_ecliptic_of_date:explicit_reader:v1"
            ),
            source_mode=HoraryGeometrySourceMode.COMPUTED,
            jd_ut1=jd_ut1,
        )
        for body, position in positions.items()
    }
    first_house_sign = house_cusps.sign_of_cusp(1)[0]
    first_house_ruler = DOMICILE_RULERS[first_house_sign]
    first_ruler_proximity = solar_proximity_truth(
        first_house_ruler,
        positions[first_house_ruler].longitude,
        positions[Body.SUN].longitude,
    )
    consideration_inputs = HoraryConsiderationInputs(
        moon_placement=placements[Body.MOON],
        saturn_placement=placements[Body.SATURN],
        first_ruler_solar_proximity=HorarySolarProximityReceipt(
            question_id=question.question_id,
            body=first_house_ruler,
            truth=first_ruler_proximity,
            calculation_policy_id="moira.dignities.solar_proximity_truth:v1",
            latitude_deg=question.latitude_deg,
            longitude_deg=question.longitude_deg,
            geometry_source_id=geometry.source_id,
            source_id=(
                "moira.dignities.solar_proximity_truth:"
                f"{first_house_ruler}:v1"
            ),
            source_mode=HoraryGeometrySourceMode.COMPUTED,
            jd_ut1=jd_ut1,
        ),
    )

    profile = evaluate_horary_evidence(
        question,
        geometry,
        house_policy=house_policy,
        planetary_hour=planetary_hour_receipt,
        considerations=consideration_inputs,
    )
    if perfection_jd_end is None:
        return profile
    if (
        profile.significators.state is HoraryEvidenceState.NOT_EVALUABLE
        or profile.significators.same_body_principals
        or profile.chart_sect.state is HoraryEvidenceState.NOT_EVALUABLE
    ):
        return profile

    principal_querent = profile.significators.principal_querent.body
    principal_quesited = profile.significators.principal_quesited.body
    assert principal_querent is not None and principal_quesited is not None
    assert profile.chart_sect.sect is not None
    perfection_analysis = lilly_perfection_at(
        jd_ut1,
        perfection_jd_end,
        principal_querent,
        principal_quesited,
        is_day_chart=profile.chart_sect.sect is HoraryChartSect.DAY,
        reader=reader,
        policy=LILLY_1647_PERFECTION_V1,
    )
    return evaluate_horary_evidence(
        question,
        geometry,
        house_policy=house_policy,
        planetary_hour=planetary_hour_receipt,
        considerations=consideration_inputs,
        perfection_analysis=perfection_analysis,
    )
