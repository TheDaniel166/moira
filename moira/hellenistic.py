"""
Typed, non-interpretive Hellenistic chart-profile composition.

This module composes already-admitted atomic Moira receipts. It owns no new
astrological scoring, historical interpretation, ephemeris reduction, or
source-table reconstruction. Missing or ambiguous atomic truth remains visible
as typed ``not_evaluable`` evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from math import isfinite

from .aspects import (
    AspectClassification,
    HellenisticAspectEvaluationStatus,
    HellenisticSuperiorityTruth,
    find_whole_sign_aspects,
)
from .constants import HouseSystem
from .decanates import DecanatePosition, chaldean_face
from .dignities import (
    DignityComputationPolicy,
    DignityHorizonFrame,
    EssentialDignityComponentTruth,
    EssentialDignityDoctrine,
    PLANETARY_JOYS,
    PlanetaryReception,
    PlanetarySolarPhaseTruth,
    SectTruth,
    SolarProximityTruth,
    BesiegingTruth,
    TruthEvaluationStatus,
    calculate_dignities,
)
from .egyptian_bounds import (
    EgyptianBoundsPolicy,
    EgyptianBoundTruth,
    egyptian_bound_of,
)
from .julian import jd_from_datetime
from .lots import (
    ArabicPartComputationTruth,
    LotAstrologicalConditionTruth,
    LotDependencyCompletenessTruth,
    LotNotEvaluable,
    LotsComputationPolicy,
    LotsReferenceFailureMode,
    evaluate_lots,
)
from .profections import (
    LeapDayAnniversaryPolicy,
    MonthlyProfectionIntervalPolicy,
    ProfectionAmbiguousTimePolicy,
    ProfectionResult,
    profection_schedule,
)
from .timelords import (
    DecennialPeriod,
    DecennialPolicy,
    DecennialSequenceAssemblyTruth,
    FirdarYearPolicy,
    ReleasingPeriod,
    TimelordComputationPolicy,
    TimelordEvaluationStatus,
    ZRYearPolicy,
    current_decennials,
    decennial_sequence_truth,
    zodiacal_releasing,
)
from .triplicity import (
    TriplicityAssignment,
    TriplicityDoctrine,
    triplicity_assignment_for,
)


HELLENISTIC_CLASSICAL_PLANETS: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
)

HELLENISTIC_PROFILE_LOTS: tuple[str, ...] = (
    "Fortune",
    "Spirit",
    "Eros (Valens)",
    "Necessity (Valens)",
)

_ZR_LOT_TO_PROFILE_LOT: dict[str, str] = {
    "Fortune": "Fortune",
    "Spirit": "Spirit",
    "Eros": "Eros (Valens)",
    "Necessity": "Necessity (Valens)",
}


class HellenisticProfileStatus(StrEnum):
    """Evaluation state for one composed profile section."""

    EVALUATED = "evaluated"
    NOT_EVALUABLE = "not_evaluable"


class HellenisticProfileComponent(StrEnum):
    """Atomic receipt families admitted to the unified profile."""

    WHOLE_SIGN_HOUSES = "whole_sign_houses"
    WHOLE_SIGN_ASPECTS = "whole_sign_aspects"
    ESSENTIAL_DIGNITY_COMPONENTS = "essential_dignity_components"
    SECT_AND_PLANETARY_CONDITION = "sect_and_planetary_condition"
    TRIPLICITY = "triplicity"
    BOUNDS = "bounds"
    CHALDEAN_FACES = "chaldean_faces"
    LOTS = "lots"
    PROFECTION = "profection"
    DECENNIALS_L1_L2 = "decennials_l1_l2"
    ZODIACAL_RELEASING = "zodiacal_releasing"


class HellenisticProfileExclusion(StrEnum):
    """Named branches structurally excluded from this profile contract."""

    FIRDARIA = "firdaria"
    MEDIEVAL_ALMUTENS = "medieval_almutens"
    LATER_ELECTIONAL_RULES = "later_electional_rules"
    UNSCOPED_PRIMARY_DIRECTIONS = "unscoped_primary_directions"
    DECENNIALS_L3_L4 = "decennials_l3_l4"
    HERMETIC_DECAN_GEOMETRY = "hermetic_decan_geometry"
    VALENS_DISTRIBUTION_INTERPRETATION = "valens_distribution_interpretation"
    TRIACONTAETERIS = "triacontaeteris"


@dataclass(frozen=True, slots=True)
class HellenisticProfilePolicy:
    """Explicit selectors governing profile composition."""

    dignity: DignityComputationPolicy = field(
        default_factory=DignityComputationPolicy
    )
    lots: LotsComputationPolicy = field(default_factory=LotsComputationPolicy)
    triplicity_doctrine: TriplicityDoctrine = (
        TriplicityDoctrine.DOROTHEAN_PINGREE_1976
    )
    bounds: EgyptianBoundsPolicy = field(default_factory=EgyptianBoundsPolicy)
    decennials: DecennialPolicy = field(default_factory=DecennialPolicy)
    zr_year: ZRYearPolicy = field(default_factory=ZRYearPolicy)
    activation_orb_deg: float = 5.0
    leap_day_policy: LeapDayAnniversaryPolicy | None = None
    monthly_profection_interval_policy: MonthlyProfectionIntervalPolicy = (
        MonthlyProfectionIntervalPolicy
        .EQUAL_TWELFTHS_OF_CIVIL_ANNIVERSARY_YEAR
    )
    profection_ambiguous_time_policy: (
        ProfectionAmbiguousTimePolicy | None
    ) = None
    zr_lot_name: str = "Spirit"
    zr_levels: int = 2
    use_loosing_of_bond: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.dignity, DignityComputationPolicy):
            raise TypeError(
                "Hellenistic profile dignity must be a "
                "DignityComputationPolicy"
            )
        if not isinstance(self.lots, LotsComputationPolicy):
            raise TypeError(
                "Hellenistic profile lots must be a LotsComputationPolicy"
            )
        if not isinstance(self.bounds, EgyptianBoundsPolicy):
            raise TypeError(
                "Hellenistic profile bounds must be an EgyptianBoundsPolicy"
            )
        if not isinstance(self.decennials, DecennialPolicy):
            raise TypeError(
                "Hellenistic profile decennials must be a DecennialPolicy"
            )
        if not isinstance(self.zr_year, ZRYearPolicy):
            raise TypeError(
                "Hellenistic profile zr_year must be a ZRYearPolicy"
            )
        if (
            self.dignity.essential.doctrine
            is not EssentialDignityDoctrine.TRADITIONAL_CLASSIC_7
        ):
            raise ValueError(
                "Hellenistic profiles require the traditional Classic 7 "
                "essential-dignity doctrine"
            )
        if (
            self.triplicity_doctrine
            is not TriplicityDoctrine.DOROTHEAN_PINGREE_1976
        ):
            raise ValueError(
                "Hellenistic profiles require DOROTHEAN_PINGREE_1976 "
                "triplicity doctrine"
            )
        if (
            self.lots.unresolved_reference_mode
            is not LotsReferenceFailureMode.SKIP
        ):
            raise ValueError(
                "Hellenistic profiles require typed skipped-lot receipts "
                "instead of raise-on-first-missing-reference policy"
            )
        if not (
            self.lots.derived.include_fortune
            and self.lots.derived.include_spirit
            and self.lots.derived.include_eros_valens
        ):
            raise ValueError(
                "Hellenistic profiles require Fortune, Spirit, and Valens "
                "Eros derived references"
            )
        if self.decennials.deep_subdivision_method is not None:
            raise ValueError(
                "Hellenistic profiles exclude Decennial L3/L4 from the "
                "closed L1/L2 contract"
            )
        if self.decennials != DecennialPolicy():
            raise ValueError(
                "Hellenistic profiles require the admitted fixed Decennial "
                "L1/L2 policy"
            )
        if (
            not isfinite(self.zr_year.year_days)
            or self.zr_year.year_days <= 0.0
        ):
            raise ValueError(
                "Hellenistic profile zr_year.year_days must be finite and "
                "positive"
            )
        if not isfinite(self.activation_orb_deg) or self.activation_orb_deg < 0.0:
            raise ValueError(
                "Hellenistic profile activation_orb_deg must be finite and "
                "non-negative"
            )
        if (
            self.leap_day_policy is not None
            and not isinstance(
                self.leap_day_policy,
                LeapDayAnniversaryPolicy,
            )
        ):
            raise TypeError(
                "Hellenistic profile leap_day_policy must be a "
                "LeapDayAnniversaryPolicy or None"
            )
        if (
            self.monthly_profection_interval_policy
            is not MonthlyProfectionIntervalPolicy
            .EQUAL_TWELFTHS_OF_CIVIL_ANNIVERSARY_YEAR
        ):
            raise ValueError(
                "Hellenistic profiles require the admitted equal-twelfths "
                "monthly profection interval policy"
            )
        if (
            self.profection_ambiguous_time_policy is not None
            and not isinstance(
                self.profection_ambiguous_time_policy,
                ProfectionAmbiguousTimePolicy,
            )
        ):
            raise TypeError(
                "Hellenistic profile profection_ambiguous_time_policy must "
                "be a ProfectionAmbiguousTimePolicy or None"
            )
        if self.zr_lot_name not in _ZR_LOT_TO_PROFILE_LOT:
            raise ValueError(
                "Hellenistic profile zr_lot_name must be Fortune, Spirit, "
                "Eros, or Necessity"
            )
        if type(self.zr_levels) is not int or not 1 <= self.zr_levels <= 4:
            raise ValueError("Hellenistic profile zr_levels must be in 1..4")
        if not isinstance(self.use_loosing_of_bond, bool):
            raise TypeError(
                "Hellenistic profile use_loosing_of_bond must be bool"
            )


@dataclass(frozen=True, slots=True)
class HellenisticPlanetaryJoyTruth:
    """Score-free planetary-joy receipt."""

    status: TruthEvaluationStatus
    planet: str
    actual_house: int
    joy_house: int | None
    matched: bool | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class HellenisticPlanetProfile:
    """Score-free composition of admitted atomic truth for one classical planet."""

    planet: str
    longitude: float
    sign: str
    house: int
    is_retrograde: bool
    essential_components: tuple[EssentialDignityComponentTruth, ...]
    sect_truth: SectTruth
    joy_truth: HellenisticPlanetaryJoyTruth
    solar_proximity_truth: SolarProximityTruth
    planetary_solar_phase_truth: PlanetarySolarPhaseTruth
    besieging_truth: BesiegingTruth
    receptions: tuple[PlanetaryReception, ...]
    triplicity_assignment: TriplicityAssignment
    bound_truth: EgyptianBoundTruth
    face: DecanatePosition


@dataclass(frozen=True, slots=True)
class HellenisticAspectProfile:
    """Score-free whole-sign aspect and superiority receipt."""

    body1: str
    body2: str
    aspect: str
    symbol: str
    angle: float
    separation: float
    sign_degree1: int
    sign_degree2: int
    classification: AspectClassification
    superiority_truth: HellenisticSuperiorityTruth


@dataclass(frozen=True, slots=True)
class HellenisticLotProfile:
    """Score-free lot formula, dependency, and condition receipt."""

    name: str
    longitude: float
    formula: str
    category: str
    description: str
    computation_truth: ArabicPartComputationTruth
    dependency_completeness: LotDependencyCompletenessTruth
    astrological_condition_truth: LotAstrologicalConditionTruth


@dataclass(frozen=True, slots=True)
class HellenisticDecennialSnapshot:
    """Current admitted Decennial L1/L2 receipt."""

    status: HellenisticProfileStatus
    sequence_truth: DecennialSequenceAssemblyTruth
    active_periods: tuple[DecennialPeriod, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, HellenisticProfileStatus):
            raise TypeError(
                "HellenisticDecennialSnapshot status must be a "
                "HellenisticProfileStatus"
            )
        if not isinstance(
            self.sequence_truth,
            DecennialSequenceAssemblyTruth,
        ):
            raise TypeError(
                "HellenisticDecennialSnapshot sequence_truth must be a "
                "DecennialSequenceAssemblyTruth"
            )
        if any(
            not isinstance(period, DecennialPeriod)
            for period in self.active_periods
        ):
            raise TypeError(
                "HellenisticDecennialSnapshot active_periods must contain "
                "DecennialPeriod values"
            )
        if self.status is HellenisticProfileStatus.EVALUATED:
            if (
                self.sequence_truth.status
                is not TimelordEvaluationStatus.EVALUATED
                or tuple(period.level for period in self.active_periods)
                != (1, 2)
                or self.reason is not None
            ):
                raise ValueError(
                    "Evaluated Hellenistic Decennials require one active L1 "
                    "and L2 period, evaluated sequence truth, and no reason"
                )
            if any(
                period.sequence_truth != self.sequence_truth
                for period in self.active_periods
            ):
                raise ValueError(
                    "Hellenistic Decennial periods must preserve the snapshot "
                    "sequence truth"
                )
        elif self.active_periods or not self.reason:
            raise ValueError(
                "Not-evaluable Hellenistic Decennials require no active "
                "periods and an explicit reason"
            )


@dataclass(frozen=True, slots=True)
class HellenisticZodiacalReleasingSnapshot:
    """Current Zodiacal Releasing receipt for one selected foundational lot."""

    status: HellenisticProfileStatus
    lot_name: str
    source_lot_name: str
    lot_longitude: float | None
    fortune_longitude: float | None
    levels: int
    use_loosing_of_bond: bool
    active_periods: tuple[ReleasingPeriod, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, HellenisticProfileStatus):
            raise TypeError(
                "HellenisticZodiacalReleasingSnapshot status must be a "
                "HellenisticProfileStatus"
            )
        if self.lot_name not in _ZR_LOT_TO_PROFILE_LOT:
            raise ValueError(
                "Hellenistic Zodiacal Releasing lot_name is not admitted"
            )
        if self.source_lot_name != _ZR_LOT_TO_PROFILE_LOT[self.lot_name]:
            raise ValueError(
                "Hellenistic Zodiacal Releasing source_lot_name must match "
                "lot_name"
            )
        for field_name, longitude in (
            ("lot_longitude", self.lot_longitude),
            ("fortune_longitude", self.fortune_longitude),
        ):
            if longitude is not None and (
                not isfinite(longitude) or not 0.0 <= longitude < 360.0
            ):
                raise ValueError(
                    f"Hellenistic Zodiacal Releasing {field_name} must be "
                    "in [0, 360) or None"
                )
        if type(self.levels) is not int or not 1 <= self.levels <= 4:
            raise ValueError(
                "Hellenistic Zodiacal Releasing levels must be in 1..4"
            )
        if not isinstance(self.use_loosing_of_bond, bool):
            raise TypeError(
                "Hellenistic Zodiacal Releasing use_loosing_of_bond must "
                "be bool"
            )
        if any(
            not isinstance(period, ReleasingPeriod)
            for period in self.active_periods
        ):
            raise TypeError(
                "Hellenistic Zodiacal Releasing active_periods must contain "
                "ReleasingPeriod values"
            )
        if self.status is HellenisticProfileStatus.EVALUATED:
            if (
                self.lot_longitude is None
                or self.fortune_longitude is None
                or tuple(period.level for period in self.active_periods)
                != tuple(range(1, self.levels + 1))
                or self.reason is not None
            ):
                raise ValueError(
                    "Evaluated Hellenistic Zodiacal Releasing requires "
                    "source and Fortune longitudes, one active period per "
                    "requested level, and no reason"
                )
            if any(
                period.lot_name != self.lot_name
                or period.use_loosing_of_bond
                is not self.use_loosing_of_bond
                for period in self.active_periods
            ):
                raise ValueError(
                    "Hellenistic Zodiacal Releasing periods must preserve "
                    "the snapshot policy"
                )
        elif self.active_periods or not self.reason:
            raise ValueError(
                "Not-evaluable Hellenistic Zodiacal Releasing requires no "
                "active periods and an explicit reason"
            )


@dataclass(frozen=True, slots=True)
class HellenisticProfileNotEvaluable:
    """One preserved atomic non-evaluable reason in the composed profile."""

    component: str
    subject: str
    reason: str

    def __post_init__(self) -> None:
        for name, value in (
            ("component", self.component),
            ("subject", self.subject),
            ("reason", self.reason),
        ):
            if (
                not isinstance(value, str)
                or not value
                or value != value.strip()
            ):
                raise ValueError(
                    f"HellenisticProfileNotEvaluable {name} must be a "
                    "non-empty trimmed string"
                )


@dataclass(frozen=True, slots=True)
class HellenisticObserverContext:
    """Geographic input context for the chart geometry, when supplied."""

    latitude: float | None
    longitude: float | None
    elevation_m: float | None
    source: str

    def __post_init__(self) -> None:
        if self.source == "not_supplied_explicit_geometry":
            if (
                self.latitude is not None
                or self.longitude is not None
                or self.elevation_m is not None
            ):
                raise ValueError(
                    "An unsupplied Hellenistic observer cannot carry "
                    "coordinates"
                )
            return
        if self.source != "supplied_geographic_observer":
            raise ValueError(
                "Hellenistic observer source is not an admitted value"
            )
        if (
            self.latitude is None
            or self.longitude is None
            or self.elevation_m is None
            or not isfinite(self.latitude)
            or not -90.0 <= self.latitude <= 90.0
            or not isfinite(self.longitude)
            or not -180.0 <= self.longitude <= 180.0
            or not isfinite(self.elevation_m)
        ):
            raise ValueError(
                "A supplied Hellenistic observer requires finite geographic "
                "coordinates"
            )


@dataclass(frozen=True, slots=True)
class HellenisticProfileProvenance:
    """Composition provenance without a chart-wide interpretation."""

    method_id: str
    lineage: str
    source_refs: tuple[str, ...]
    input_semantics: str
    position_frame: str
    calendar_and_timescale: str
    engine_version: str | None
    kernel_id: str | None
    kernel_coverage: str | None
    derivation_or_evidence: str
    warnings: tuple[str, ...]
    not_evaluable: tuple[HellenisticProfileNotEvaluable, ...]

    def __post_init__(self) -> None:
        for name, value in (
            ("method_id", self.method_id),
            ("lineage", self.lineage),
            ("input_semantics", self.input_semantics),
            ("position_frame", self.position_frame),
            ("calendar_and_timescale", self.calendar_and_timescale),
            ("derivation_or_evidence", self.derivation_or_evidence),
        ):
            if (
                not isinstance(value, str)
                or not value
                or value != value.strip()
            ):
                raise ValueError(
                    f"HellenisticProfileProvenance {name} must be a "
                    "non-empty trimmed string"
                )
        if (
            not self.source_refs
            or len(self.source_refs) != len(set(self.source_refs))
            or any(
                not isinstance(value, str)
                or not value
                or value != value.strip()
                for value in self.source_refs
            )
        ):
            raise ValueError(
                "HellenisticProfileProvenance source_refs must contain "
                "unique non-empty trimmed strings"
            )
        for name, value in (
            ("engine_version", self.engine_version),
            ("kernel_id", self.kernel_id),
            ("kernel_coverage", self.kernel_coverage),
        ):
            if value is not None and (
                not isinstance(value, str)
                or not value
                or value != value.strip()
            ):
                raise ValueError(
                    f"HellenisticProfileProvenance {name} must be a "
                    "non-empty trimmed string or None"
                )
        if (
            len(self.warnings) != len(set(self.warnings))
            or any(
                not isinstance(value, str)
                or not value
                or value != value.strip()
                for value in self.warnings
            )
        ):
            raise ValueError(
                "HellenisticProfileProvenance warnings must be unique "
                "non-empty trimmed strings"
            )
        if any(
            not isinstance(item, HellenisticProfileNotEvaluable)
            for item in self.not_evaluable
        ):
            raise TypeError(
                "HellenisticProfileProvenance not_evaluable must contain "
                "HellenisticProfileNotEvaluable values"
            )


@dataclass(frozen=True, slots=True)
class HellenisticChartProfile:
    """Unified non-interpretive profile assembled from exact atomic receipts."""

    natal_dt: datetime
    current_dt: datetime
    natal_jd: float
    current_jd: float
    house_system: str
    asc_longitude: float
    mc_longitude: float
    observer: HellenisticObserverContext
    is_day_chart: bool
    sect_light: str
    policy: HellenisticProfilePolicy
    planets: tuple[HellenisticPlanetProfile, ...]
    aspects: tuple[HellenisticAspectProfile, ...]
    lots: tuple[HellenisticLotProfile, ...]
    lots_not_evaluable: tuple[LotNotEvaluable, ...]
    profection: ProfectionResult
    decennials: HellenisticDecennialSnapshot
    zodiacal_releasing: HellenisticZodiacalReleasingSnapshot
    included_components: tuple[HellenisticProfileComponent, ...]
    excluded_components: tuple[HellenisticProfileExclusion, ...]
    provenance: HellenisticProfileProvenance

    def __post_init__(self) -> None:
        _aware_datetime("HellenisticChartProfile.natal_dt", self.natal_dt)
        _aware_datetime("HellenisticChartProfile.current_dt", self.current_dt)
        if self.current_dt < self.natal_dt:
            raise ValueError(
                "HellenisticChartProfile current_dt must not precede natal_dt"
            )
        if (
            not isfinite(self.natal_jd)
            or not isfinite(self.current_jd)
            or self.current_jd < self.natal_jd
            or abs(self.natal_jd - jd_from_datetime(self.natal_dt)) > 1e-9
            or abs(self.current_jd - jd_from_datetime(self.current_dt)) > 1e-9
        ):
            raise ValueError(
                "HellenisticChartProfile Julian dates must be finite, "
                "ordered, and match their datetimes"
            )
        if self.house_system != HouseSystem.WHOLE_SIGN:
            raise ValueError(
                "HellenisticChartProfile house_system must be Whole Sign"
            )
        for name, value in (
            ("asc_longitude", self.asc_longitude),
            ("mc_longitude", self.mc_longitude),
        ):
            if not isfinite(value) or not 0.0 <= value < 360.0:
                raise ValueError(
                    f"HellenisticChartProfile {name} must be in [0, 360)"
                )
        if not isinstance(self.observer, HellenisticObserverContext):
            raise TypeError(
                "HellenisticChartProfile observer must be a "
                "HellenisticObserverContext"
            )
        if not isinstance(self.is_day_chart, bool):
            raise TypeError(
                "HellenisticChartProfile is_day_chart must be bool"
            )
        expected_light = "Sun" if self.is_day_chart else "Moon"
        if self.sect_light != expected_light:
            raise ValueError(
                "HellenisticChartProfile sect_light must match chart sect"
            )
        if not isinstance(self.policy, HellenisticProfilePolicy):
            raise TypeError(
                "HellenisticChartProfile policy must be a "
                "HellenisticProfilePolicy"
            )
        if tuple(planet.planet for planet in self.planets) != (
            HELLENISTIC_CLASSICAL_PLANETS
        ):
            raise ValueError(
                "HellenisticChartProfile planets must contain the Classic 7 "
                "in canonical order"
            )
        if any(
            planet.sect_truth.is_day_chart is not self.is_day_chart
            or planet.sect_truth.sect_light != self.sect_light
            or planet.joy_truth.planet != planet.planet
            for planet in self.planets
        ):
            raise ValueError(
                "HellenisticChartProfile planetary receipts must preserve "
                "the profile sect and body identity"
            )
        if any(
            aspect.body1 not in HELLENISTIC_CLASSICAL_PLANETS
            or aspect.body2 not in HELLENISTIC_CLASSICAL_PLANETS
            or aspect.body1 == aspect.body2
            for aspect in self.aspects
        ):
            raise ValueError(
                "HellenisticChartProfile aspects must relate distinct "
                "classical planets"
            )
        evaluated_lot_names = tuple(lot.name for lot in self.lots)
        unresolved_lot_names = tuple(
            lot.name for lot in self.lots_not_evaluable
        )
        if (
            len(evaluated_lot_names) != len(set(evaluated_lot_names))
            or len(unresolved_lot_names) != len(set(unresolved_lot_names))
            or set(evaluated_lot_names).intersection(unresolved_lot_names)
            or set(evaluated_lot_names).union(unresolved_lot_names)
            != set(HELLENISTIC_PROFILE_LOTS)
        ):
            raise ValueError(
                "HellenisticChartProfile lots must partition the exact "
                "foundational profile-lot set"
            )
        if self.profection.chronology is None:
            raise ValueError(
                "HellenisticChartProfile profection must carry dated "
                "chronology"
            )
        if (
            self.profection.chronology.interval_policy
            is not self.policy.monthly_profection_interval_policy
            or self.profection.chronology.ambiguous_time_policy
            is not self.policy.profection_ambiguous_time_policy
        ):
            raise ValueError(
                "HellenisticChartProfile profection chronology must preserve "
                "the profile policy"
            )
        if (
            self.decennials.sequence_truth.is_day_chart
            is not self.is_day_chart
            or self.decennials.sequence_truth.sect_light != self.sect_light
        ):
            raise ValueError(
                "HellenisticChartProfile Decennial sequence must preserve "
                "the profile sect"
            )
        if (
            self.zodiacal_releasing.lot_name != self.policy.zr_lot_name
            or self.zodiacal_releasing.levels != self.policy.zr_levels
            or self.zodiacal_releasing.use_loosing_of_bond
            is not self.policy.use_loosing_of_bond
        ):
            raise ValueError(
                "HellenisticChartProfile Zodiacal Releasing must preserve "
                "the profile policy"
            )
        if self.included_components != _INCLUDED_COMPONENTS:
            raise ValueError(
                "HellenisticChartProfile included_components must match the "
                "closed admitted component contract"
            )
        if self.excluded_components != _EXCLUDED_COMPONENTS:
            raise ValueError(
                "HellenisticChartProfile excluded_components must match the "
                "closed exclusion contract"
            )
        if not isinstance(self.provenance, HellenisticProfileProvenance):
            raise TypeError(
                "HellenisticChartProfile provenance must be a "
                "HellenisticProfileProvenance"
            )
        if (
            self.provenance.method_id
            != "moira.hellenistic_chart_profile.v2"
            or self.provenance.source_refs != _PROFILE_SOURCE_REFS
            or self.provenance.not_evaluable
            != _profile_issues(
                self.planets,
                self.aspects,
                self.lots_not_evaluable,
                self.decennials,
                self.zodiacal_releasing,
            )
        ):
            raise ValueError(
                "HellenisticChartProfile provenance must match the v2 "
                "composition receipt"
            )


_INCLUDED_COMPONENTS: tuple[HellenisticProfileComponent, ...] = tuple(
    HellenisticProfileComponent
)
_EXCLUDED_COMPONENTS: tuple[HellenisticProfileExclusion, ...] = tuple(
    HellenisticProfileExclusion
)

_PROFILE_SOURCE_REFS: tuple[str, ...] = (
    "Dorotheus of Sidon, Carmen Astrologicum I.1, Pingree ed. (1976)",
    "Ptolemy, Tetrabiblos I.13 and I.20/I.21",
    "Vettius Valens, Anthologies, admitted Lots, Decennials, and ZR passages",
    "Agrippa, Three Books of Occult Philosophy II.37; Picatrix I.4 "
    "(admitted Chaldean-face table provenance)",
)


def _aware_datetime(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _observer_context(
    latitude: float | None,
    longitude: float | None,
    elevation_m: float | None,
) -> HellenisticObserverContext:
    supplied = (latitude is not None, longitude is not None, elevation_m is not None)
    if not any(supplied):
        return HellenisticObserverContext(
            latitude=None,
            longitude=None,
            elevation_m=None,
            source="not_supplied_explicit_geometry",
        )
    if latitude is None or longitude is None:
        raise ValueError(
            "observer_latitude and observer_longitude must be supplied together"
        )
    elevation = 0.0 if elevation_m is None else elevation_m
    if (
        not isfinite(latitude)
        or not -90.0 <= latitude <= 90.0
        or not isfinite(longitude)
        or not -180.0 <= longitude <= 180.0
        or not isfinite(elevation)
    ):
        raise ValueError("observer location inputs are invalid or non-finite")
    return HellenisticObserverContext(
        latitude=latitude,
        longitude=longitude,
        elevation_m=elevation,
        source="supplied_geographic_observer",
    )


def _normalize_positions(
    positions: Mapping[str, float],
    speeds: Mapping[str, float],
) -> tuple[dict[str, float], dict[str, float]]:
    normalized: dict[str, float] = {}
    for raw_name, raw_longitude in positions.items():
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValueError("natal position names must be non-empty strings")
        name = raw_name.strip()
        if name in normalized:
            raise ValueError(
                f"duplicate natal position after trimming: {name!r}"
            )
        if not isfinite(raw_longitude):
            raise ValueError(f"natal position for {name!r} must be finite")
        normalized[name] = raw_longitude % 360.0

    missing = [
        planet
        for planet in HELLENISTIC_CLASSICAL_PLANETS
        if planet not in normalized
    ]
    if missing:
        raise ValueError(
            "Hellenistic profile requires all seven classical planets; "
            f"missing {missing}"
        )

    normalized_speeds: dict[str, float] = {}
    for planet in HELLENISTIC_CLASSICAL_PLANETS:
        if planet not in speeds:
            raise ValueError(
                "Hellenistic profile requires an explicit speed for every "
                f"classical planet; missing {planet!r}"
            )
        speed = speeds[planet]
        if not isfinite(speed):
            raise ValueError(f"natal speed for {planet!r} must be finite")
        normalized_speeds[planet] = speed
    return normalized, normalized_speeds


def _circular_distance(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def _normalize_whole_sign_cusps(
    house_cusps: Mapping[int, float],
    asc_longitude: float,
) -> dict[int, float]:
    if not isfinite(asc_longitude):
        raise ValueError("asc_longitude must be finite")
    if set(house_cusps) != set(range(1, 13)):
        raise ValueError(
            "Hellenistic profile requires exactly the twelve house cusp keys 1..12"
        )
    cusps: dict[int, float] = {}
    for number in range(1, 13):
        value = house_cusps[number]
        if not isfinite(value):
            raise ValueError(f"house cusp {number} must be finite")
        cusps[number] = value % 360.0

    first = cusps[1]
    expected_first = int((asc_longitude % 360.0) // 30.0) * 30.0
    if _circular_distance(first, expected_first) > 1e-9:
        raise ValueError(
            "Whole Sign cusp 1 must be the zodiac-sign boundary containing "
            "the Ascendant"
        )
    for number in range(1, 13):
        expected = (first + (number - 1) * 30.0) % 360.0
        if _circular_distance(cusps[number], expected) > 1e-9:
            raise ValueError(
                "Hellenistic profile requires exact Whole Sign cusp spacing"
            )
    return cusps


def _joy_truth(planet: str, house: int) -> HellenisticPlanetaryJoyTruth:
    joy_house = PLANETARY_JOYS.get(planet)
    if joy_house is None:
        return HellenisticPlanetaryJoyTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            planet=planet,
            actual_house=house,
            joy_house=None,
            matched=None,
            reason="planet_has_no_admitted_joy_house",
        )
    return HellenisticPlanetaryJoyTruth(
        status=TruthEvaluationStatus.EVALUATED,
        planet=planet,
        actual_house=house,
        joy_house=joy_house,
        matched=house == joy_house,
    )


def _planet_profiles(
    positions: dict[str, float],
    speeds: dict[str, float],
    cusps: dict[int, float],
    *,
    asc_longitude: float,
    mc_longitude: float,
    policy: HellenisticProfilePolicy,
) -> tuple[tuple[HellenisticPlanetProfile, ...], bool]:
    planet_inputs = [
        {
            "name": planet,
            "degree": positions[planet],
            "is_retrograde": speeds[planet] < 0.0,
        }
        for planet in HELLENISTIC_CLASSICAL_PLANETS
    ]
    house_inputs = [
        {"number": number, "degree": cusps[number]}
        for number in range(1, 13)
    ]
    dignities = calculate_dignities(
        planet_inputs,
        house_inputs,
        policy=policy.dignity,
        horizon_frame=DignityHorizonFrame(
            asc_longitude=asc_longitude,
            mc_longitude=mc_longitude,
        ),
    )
    dignity_by_planet = {dignity.planet: dignity for dignity in dignities}
    if set(dignity_by_planet) != set(HELLENISTIC_CLASSICAL_PLANETS):
        raise ValueError(
            "dignity computation did not return exactly the seven classical planets"
        )
    sun_sect_truth = dignity_by_planet["Sun"].sect_truth
    if sun_sect_truth is None:
        raise ValueError("Sun dignity result did not preserve exact sect truth")
    day_chart = sun_sect_truth.is_day_chart

    profiles: list[HellenisticPlanetProfile] = []
    for planet in HELLENISTIC_CLASSICAL_PLANETS:
        dignity = dignity_by_planet[planet]
        if dignity.essential_truth is None:
            raise ValueError(
                f"{planet} dignity result did not preserve essential truth"
            )
        if dignity.sect_truth is None:
            raise ValueError(f"{planet} dignity result did not preserve sect truth")

        accidental = dignity.accidental_truth
        profiles.append(
            HellenisticPlanetProfile(
                planet=planet,
                longitude=positions[planet],
                sign=dignity.sign,
                house=dignity.house,
                is_retrograde=speeds[planet] < 0.0,
                essential_components=tuple(dignity.essential_truth.components),
                sect_truth=dignity.sect_truth,
                joy_truth=_joy_truth(planet, dignity.house),
                solar_proximity_truth=accidental.solar_proximity_truth,
                planetary_solar_phase_truth=(
                    accidental.planetary_solar_phase_truth
                ),
                besieging_truth=accidental.besieging_truth,
                receptions=tuple(dignity.all_receptions),
                triplicity_assignment=triplicity_assignment_for(
                    dignity.sign,
                    is_day_chart=day_chart,
                    doctrine=policy.triplicity_doctrine,
                ),
                bound_truth=egyptian_bound_of(
                    positions[planet],
                    policy=policy.bounds,
                ),
                face=chaldean_face(positions[planet]),
            )
        )
    return tuple(profiles), day_chart


def _aspect_profiles(
    positions: dict[str, float],
) -> tuple[HellenisticAspectProfile, ...]:
    aspects = find_whole_sign_aspects(
        {
            planet: positions[planet]
            for planet in HELLENISTIC_CLASSICAL_PLANETS
        }
    )
    profiles: list[HellenisticAspectProfile] = []
    for aspect in aspects:
        if aspect.classification is None:
            raise ValueError("whole-sign aspect did not preserve classification")
        if aspect.sign_degree1 is None or aspect.sign_degree2 is None:
            raise ValueError("whole-sign aspect did not preserve sign degrees")
        if aspect.hellenistic_superiority_truth is None:
            raise ValueError("whole-sign aspect did not preserve superiority truth")
        profiles.append(
            HellenisticAspectProfile(
                body1=aspect.body1,
                body2=aspect.body2,
                aspect=aspect.aspect,
                symbol=aspect.symbol,
                angle=aspect.angle,
                separation=aspect.separation,
                sign_degree1=aspect.sign_degree1,
                sign_degree2=aspect.sign_degree2,
                classification=aspect.classification,
                superiority_truth=aspect.hellenistic_superiority_truth,
            )
        )
    return tuple(profiles)


def _lot_profiles(
    positions: dict[str, float],
    cusps: dict[int, float],
    *,
    asc_longitude: float,
    mc_longitude: float,
    day_chart: bool,
    policy: HellenisticProfilePolicy,
    syzygy: float | None,
    prenatal_new_moon: float | None,
    prenatal_full_moon: float | None,
    lord_of_hour: float | None,
) -> tuple[
    tuple[HellenisticLotProfile, ...],
    tuple[LotNotEvaluable, ...],
]:
    evaluation = evaluate_lots(
        positions,
        cusps,
        day_chart,
        policy=policy.lots,
        asc_longitude=asc_longitude,
        mc_longitude=mc_longitude,
        syzygy=syzygy,
        prenatal_new_moon=prenatal_new_moon,
        prenatal_full_moon=prenatal_full_moon,
        lord_of_hour=lord_of_hour,
    )
    parts = {part.name: part for part in evaluation.parts}
    unresolved = {item.name: item for item in evaluation.not_evaluable}

    profiles: list[HellenisticLotProfile] = []
    selected_unresolved: list[LotNotEvaluable] = []
    for name in HELLENISTIC_PROFILE_LOTS:
        part = parts.get(name)
        if part is None:
            not_evaluable = unresolved.get(name)
            if not_evaluable is None:
                raise ValueError(
                    f"foundational profile lot {name!r} is absent from both "
                    "computed and not-evaluable catalogue results"
                )
            selected_unresolved.append(not_evaluable)
            continue
        if part.computation_truth is None:
            raise ValueError(f"profile lot {name!r} lacks computation truth")
        if part.dependency_completeness is None:
            raise ValueError(
                f"profile lot {name!r} lacks dependency-completeness truth"
            )
        profiles.append(
            HellenisticLotProfile(
                name=part.name,
                longitude=part.longitude,
                formula=part.formula,
                category=part.category,
                description=part.description,
                computation_truth=part.computation_truth,
                dependency_completeness=part.dependency_completeness,
                astrological_condition_truth=part.astrological_condition_truth,
            )
        )
    return tuple(profiles), tuple(selected_unresolved)


def _timelord_policy(
    policy: HellenisticProfilePolicy,
) -> TimelordComputationPolicy:
    return TimelordComputationPolicy(
        firdaria_year=FirdarYearPolicy(),
        decennials=policy.decennials,
        zr_year=policy.zr_year,
    )


def _decennial_snapshot(
    natal_jd: float,
    current_jd: float,
    positions: dict[str, float],
    day_chart: bool,
    policy: HellenisticProfilePolicy,
) -> HellenisticDecennialSnapshot:
    classical_positions = {
        planet: positions[planet]
        for planet in HELLENISTIC_CLASSICAL_PLANETS
    }
    sequence_truth = decennial_sequence_truth(classical_positions, day_chart)
    if (
        sequence_truth.status is not TimelordEvaluationStatus.EVALUATED
        or sequence_truth.sequence is None
    ):
        return HellenisticDecennialSnapshot(
            status=HellenisticProfileStatus.NOT_EVALUABLE,
            sequence_truth=sequence_truth,
            reason=sequence_truth.reason or "decennial_sequence_not_evaluable",
        )
    try:
        major, sub = current_decennials(
            natal_jd,
            classical_positions,
            day_chart,
            current_jd,
            levels=2,
            policy=_timelord_policy(policy),
        )
    except ValueError as exc:
        return HellenisticDecennialSnapshot(
            status=HellenisticProfileStatus.NOT_EVALUABLE,
            sequence_truth=sequence_truth,
            reason=str(exc),
        )
    return HellenisticDecennialSnapshot(
        status=HellenisticProfileStatus.EVALUATED,
        sequence_truth=sequence_truth,
        active_periods=(major, sub),
    )


def _active_releasing_periods(
    periods: list[ReleasingPeriod],
    current_jd: float,
    levels: int,
) -> tuple[ReleasingPeriod, ...]:
    active: list[ReleasingPeriod] = []
    for level in range(1, levels + 1):
        level_periods = [period for period in periods if period.level == level]
        found = next(
            (
                period
                for period in level_periods
                if period.start_jd <= current_jd < period.end_jd
            ),
            None,
        )
        if found is None:
            raise ValueError(
                f"no active Zodiacal Releasing period found at level {level}"
            )
        active.append(found)
    return tuple(active)


def _zr_snapshot(
    natal_jd: float,
    current_jd: float,
    lots: tuple[HellenisticLotProfile, ...],
    policy: HellenisticProfilePolicy,
) -> HellenisticZodiacalReleasingSnapshot:
    source_lot_name = _ZR_LOT_TO_PROFILE_LOT[policy.zr_lot_name]
    lot_map = {lot.name: lot for lot in lots}
    source_lot = lot_map.get(source_lot_name)
    fortune = lot_map.get("Fortune")
    if source_lot is None:
        return HellenisticZodiacalReleasingSnapshot(
            status=HellenisticProfileStatus.NOT_EVALUABLE,
            lot_name=policy.zr_lot_name,
            source_lot_name=source_lot_name,
            lot_longitude=None,
            fortune_longitude=None if fortune is None else fortune.longitude,
            levels=policy.zr_levels,
            use_loosing_of_bond=policy.use_loosing_of_bond,
            reason="selected_releasing_lot_not_evaluable",
        )
    if fortune is None:
        return HellenisticZodiacalReleasingSnapshot(
            status=HellenisticProfileStatus.NOT_EVALUABLE,
            lot_name=policy.zr_lot_name,
            source_lot_name=source_lot_name,
            lot_longitude=source_lot.longitude,
            fortune_longitude=None,
            levels=policy.zr_levels,
            use_loosing_of_bond=policy.use_loosing_of_bond,
            reason="fortune_not_evaluable_for_zr_angularity",
        )
    try:
        periods = zodiacal_releasing(
            source_lot.longitude,
            natal_jd,
            levels=policy.zr_levels,
            lot_name=policy.zr_lot_name,
            fortune_longitude=fortune.longitude,
            use_loosing_of_bond=policy.use_loosing_of_bond,
            policy=_timelord_policy(policy),
        )
        active = _active_releasing_periods(
            periods,
            current_jd,
            policy.zr_levels,
        )
    except ValueError as exc:
        return HellenisticZodiacalReleasingSnapshot(
            status=HellenisticProfileStatus.NOT_EVALUABLE,
            lot_name=policy.zr_lot_name,
            source_lot_name=source_lot_name,
            lot_longitude=source_lot.longitude,
            fortune_longitude=fortune.longitude,
            levels=policy.zr_levels,
            use_loosing_of_bond=policy.use_loosing_of_bond,
            reason=str(exc),
        )
    return HellenisticZodiacalReleasingSnapshot(
        status=HellenisticProfileStatus.EVALUATED,
        lot_name=policy.zr_lot_name,
        source_lot_name=source_lot_name,
        lot_longitude=source_lot.longitude,
        fortune_longitude=fortune.longitude,
        levels=policy.zr_levels,
        use_loosing_of_bond=policy.use_loosing_of_bond,
        active_periods=active,
    )


def _profile_issues(
    planets: tuple[HellenisticPlanetProfile, ...],
    aspects: tuple[HellenisticAspectProfile, ...],
    lots_not_evaluable: tuple[LotNotEvaluable, ...],
    decennials: HellenisticDecennialSnapshot,
    zr: HellenisticZodiacalReleasingSnapshot,
) -> tuple[HellenisticProfileNotEvaluable, ...]:
    issues: list[HellenisticProfileNotEvaluable] = []

    def add(component: str, subject: str, reason: str | None) -> None:
        issues.append(
            HellenisticProfileNotEvaluable(
                component=component,
                subject=subject,
                reason=reason or "atomic_receipt_not_evaluable",
            )
        )

    for planet in planets:
        for component in planet.essential_components:
            if component.status is TruthEvaluationStatus.NOT_EVALUABLE:
                add(
                    "essential_dignity",
                    f"{planet.planet}:{component.kind.value}",
                    component.reason,
                )
        for component in planet.sect_truth.components:
            if component.status is TruthEvaluationStatus.NOT_EVALUABLE:
                add(
                    "sect",
                    f"{planet.planet}:{component.kind.value}",
                    component.reason,
                )
        if planet.joy_truth.status is TruthEvaluationStatus.NOT_EVALUABLE:
            add("planetary_joy", planet.planet, planet.joy_truth.reason)
        if (
            planet.solar_proximity_truth.status
            is TruthEvaluationStatus.NOT_EVALUABLE
        ):
            add(
                "solar_proximity",
                planet.planet,
                planet.solar_proximity_truth.reason,
            )
        if (
            planet.planetary_solar_phase_truth.status
            is TruthEvaluationStatus.NOT_EVALUABLE
        ):
            add(
                "planetary_solar_phase",
                planet.planet,
                planet.planetary_solar_phase_truth.reason,
            )
        if planet.besieging_truth.status is TruthEvaluationStatus.NOT_EVALUABLE:
            add("besieging", planet.planet, planet.besieging_truth.reason)

    for aspect in aspects:
        truth = aspect.superiority_truth
        subject = f"{aspect.body1}:{aspect.body2}:{aspect.aspect}"
        if (
            truth.direction_truth.status
            is HellenisticAspectEvaluationStatus.NOT_EVALUABLE
        ):
            add("aspect_direction", subject, truth.direction_truth.reason)
        if (
            truth.overcoming_truth.status
            is HellenisticAspectEvaluationStatus.NOT_EVALUABLE
        ):
            add("aspect_overcoming", subject, truth.overcoming_truth.reason)

    for lot in lots_not_evaluable:
        add("lots", lot.name, lot.reason)
    if decennials.status is HellenisticProfileStatus.NOT_EVALUABLE:
        add("decennials", "current_l1_l2", decennials.reason)
    if zr.status is HellenisticProfileStatus.NOT_EVALUABLE:
        add("zodiacal_releasing", zr.lot_name, zr.reason)
    return tuple(issues)


def hellenistic_chart_profile(
    natal_positions: Mapping[str, float],
    natal_speeds: Mapping[str, float],
    house_cusps: Mapping[int, float],
    asc_longitude: float,
    mc_longitude: float,
    natal_dt: datetime,
    current_dt: datetime,
    *,
    civil_timezone: str | None = None,
    policy: HellenisticProfilePolicy | None = None,
    syzygy: float | None = None,
    prenatal_new_moon: float | None = None,
    prenatal_full_moon: float | None = None,
    lord_of_hour: float | None = None,
    observer_latitude: float | None = None,
    observer_longitude: float | None = None,
    observer_elevation_m: float | None = None,
    position_frame: str = "caller_supplied_position_frame_unspecified",
    engine_version: str | None = None,
    kernel_id: str | None = None,
    kernel_coverage: str | None = None,
) -> HellenisticChartProfile:
    """
    Compose a Hellenistic chart profile from explicit chart geometry.

    The function requires exact Whole Sign cusps plus the actual Ascendant and
    Midheaven, so angle-dependent lots remain distinct from house-sign
    boundaries. It computes no overall score or interpretive verdict.
    """

    _aware_datetime("natal_dt", natal_dt)
    _aware_datetime("current_dt", current_dt)
    if not isfinite(mc_longitude):
        raise ValueError("mc_longitude must be finite")

    resolved_policy = policy or HellenisticProfilePolicy()
    if (
        not isinstance(position_frame, str)
        or not position_frame.strip()
        or position_frame != position_frame.strip()
    ):
        raise ValueError("position_frame must be a non-empty trimmed string")
    observer = _observer_context(
        observer_latitude,
        observer_longitude,
        observer_elevation_m,
    )
    positions, speeds = _normalize_positions(natal_positions, natal_speeds)
    cusps = _normalize_whole_sign_cusps(house_cusps, asc_longitude)
    asc = asc_longitude % 360.0
    mc = mc_longitude % 360.0
    natal_jd = jd_from_datetime(natal_dt)
    current_jd = jd_from_datetime(current_dt)
    if current_jd < natal_jd:
        raise ValueError("current_dt must not be earlier than natal_dt")

    planets, day_chart = _planet_profiles(
        positions,
        speeds,
        cusps,
        asc_longitude=asc,
        mc_longitude=mc,
        policy=resolved_policy,
    )
    aspects = _aspect_profiles(positions)
    lots, lots_not_evaluable = _lot_profiles(
        positions,
        cusps,
        asc_longitude=asc,
        mc_longitude=mc,
        day_chart=day_chart,
        policy=resolved_policy,
        syzygy=syzygy,
        prenatal_new_moon=prenatal_new_moon,
        prenatal_full_moon=prenatal_full_moon,
        lord_of_hour=lord_of_hour,
    )
    profection = profection_schedule(
        asc,
        natal_dt,
        current_dt,
        {
            planet: positions[planet]
            for planet in HELLENISTIC_CLASSICAL_PLANETS
        },
        civil_timezone=civil_timezone,
        leap_day_policy=resolved_policy.leap_day_policy,
        ambiguous_time_policy=(
            resolved_policy.profection_ambiguous_time_policy
        ),
        interval_policy=(
            resolved_policy.monthly_profection_interval_policy
        ),
        activation_orb=resolved_policy.activation_orb_deg,
    )
    decennials = _decennial_snapshot(
        natal_jd,
        current_jd,
        positions,
        day_chart,
        resolved_policy,
    )
    zr = _zr_snapshot(natal_jd, current_jd, lots, resolved_policy)
    issues = _profile_issues(
        planets,
        aspects,
        lots_not_evaluable,
        decennials,
        zr,
    )
    warnings: list[str] = []
    if kernel_id is None:
        warnings.append("kernel_identity_not_supplied")
    if kernel_coverage is None:
        warnings.append("kernel_coverage_not_supplied")
    if observer.latitude is None:
        warnings.append("observer_location_not_supplied")
    if position_frame in {
        "caller_supplied_position_frame_unspecified",
        "chart_supplied_position_frame_not_reconstructed",
    }:
        warnings.append("position_frame_unverified")

    return HellenisticChartProfile(
        natal_dt=natal_dt,
        current_dt=current_dt,
        natal_jd=natal_jd,
        current_jd=current_jd,
        house_system=HouseSystem.WHOLE_SIGN,
        asc_longitude=asc,
        mc_longitude=mc,
        observer=observer,
        is_day_chart=day_chart,
        sect_light="Sun" if day_chart else "Moon",
        policy=resolved_policy,
        planets=planets,
        aspects=aspects,
        lots=lots,
        lots_not_evaluable=lots_not_evaluable,
        profection=profection,
        decennials=decennials,
        zodiacal_releasing=zr,
        included_components=_INCLUDED_COMPONENTS,
        excluded_components=_EXCLUDED_COMPONENTS,
        provenance=HellenisticProfileProvenance(
            method_id="moira.hellenistic_chart_profile.v2",
            lineage="hellenistic_with_explicit_component_boundaries",
            source_refs=_PROFILE_SOURCE_REFS,
            input_semantics=(
                "tropical_ecliptic_longitudes_degrees; explicit_body_speeds; "
                "exact_ascendant_and_midheaven; whole_sign_house_cusps"
            ),
            position_frame=position_frame,
            calendar_and_timescale=(
                "timezone_aware_civil_datetimes_for_profection; "
                "UTC_coded_Julian_day_projection_for_Decennials_and_ZR"
            ),
            engine_version=engine_version,
            kernel_id=kernel_id,
            kernel_coverage=kernel_coverage,
            derivation_or_evidence=(
                "identity_preserving_composition_of_admitted_atomic_receipts"
            ),
            warnings=tuple(warnings),
            not_evaluable=issues,
        ),
    )


__all__ = [
    "HELLENISTIC_CLASSICAL_PLANETS",
    "HELLENISTIC_PROFILE_LOTS",
    "HellenisticAspectProfile",
    "HellenisticChartProfile",
    "HellenisticDecennialSnapshot",
    "HellenisticLotProfile",
    "HellenisticObserverContext",
    "HellenisticPlanetProfile",
    "HellenisticPlanetaryJoyTruth",
    "HellenisticProfileComponent",
    "HellenisticProfileExclusion",
    "HellenisticProfileNotEvaluable",
    "HellenisticProfilePolicy",
    "HellenisticProfileProvenance",
    "HellenisticProfileStatus",
    "HellenisticZodiacalReleasingSnapshot",
    "hellenistic_chart_profile",
]
