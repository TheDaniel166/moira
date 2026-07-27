"""Transport models for the unified, score-free Hellenistic chart profile."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from moira.dignities import TruthEvaluationStatus
from moira.hellenistic import (
    HellenisticProfileComponent,
    HellenisticProfileExclusion,
    HellenisticProfileStatus,
)
from moira.lots import LotsReferenceFailureMode
from moira.profections import (
    LeapDayAnniversaryPolicy,
    MonthlyProfectionIntervalPolicy,
    ProfectionAmbiguousTimePolicy,
)
from moira.timelords import DecennialPolicy
from moira.triplicity import TriplicityDoctrine

from .common import _StrictModel
from .decans import DecanatePositionResponse
from .dignities import (
    BesiegingTruthResponse,
    DignityComputationPolicyRequest,
    EssentialDignityComponentTruthResponse,
    PlanetaryReceptionResponse,
    PlanetarySolarPhaseTruthResponse,
    SectTruthResponse,
    SolarProximityTruthResponse,
)
from .egyptian_bounds import (
    EgyptianBoundTruthResponse,
    EgyptianBoundsPolicyRequest,
)
from .hellenistic_aspects import (
    HellenisticAspectClassificationResponse,
    HellenisticSuperiorityTruthResponse,
)
from .lots import (
    ArabicPartComputationTruthResponse,
    LotAstrologicalConditionTruthResponse,
    LotDependencyCompletenessTruthResponse,
    LotNotEvaluableResponse,
    LotsComputationPolicyRequest,
)
from .timelords import (
    DecennialSequenceAssemblyTruthResponse,
    ProfectionResultResponse,
    ZRReleasingPeriodResponse,
)
from .triplicity import TriplicityAssignmentResponse


_DEFAULT_DECENNIALS = DecennialPolicy()


class HellenisticDecennialPolicyRequest(_StrictModel):
    """Fixed admitted Decennial L1/L2 policy; L3/L4 stays unselectable."""

    start_lord_basis: str = _DEFAULT_DECENNIALS.start_lord_basis
    sequence_mode: str = _DEFAULT_DECENNIALS.sequence_mode
    subperiod_mode: str = _DEFAULT_DECENNIALS.subperiod_mode
    major_months: float = _DEFAULT_DECENNIALS.major_months
    month_basis_days: float = _DEFAULT_DECENNIALS.month_basis_days
    time_basis: str = _DEFAULT_DECENNIALS.time_basis
    calendar_projection_basis: str = (
        _DEFAULT_DECENNIALS.calendar_projection_basis
    )

    @model_validator(mode="after")
    def _admitted_policy_only(self) -> "HellenisticDecennialPolicyRequest":
        expected = _DEFAULT_DECENNIALS
        for field_name in (
            "start_lord_basis",
            "sequence_mode",
            "subperiod_mode",
            "major_months",
            "month_basis_days",
            "time_basis",
            "calendar_projection_basis",
        ):
            if getattr(self, field_name) != getattr(expected, field_name):
                raise ValueError(
                    f"decennials.{field_name} is fixed by the admitted "
                    "Hellenistic L1/L2 policy"
                )
        return self


class HellenisticZRYearPolicyRequest(_StrictModel):
    """Symbolic-year selector for Zodiacal Releasing."""

    year_days: float = 360.0

    @field_validator("year_days")
    @classmethod
    def _positive_finite_year(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("zr_year.year_days must be finite and positive")
        return value


class HellenisticProfilePolicyRequest(_StrictModel):
    """Explicit doctrine and evaluation selectors for profile composition."""

    dignity: DignityComputationPolicyRequest = Field(
        default_factory=DignityComputationPolicyRequest
    )
    lots: LotsComputationPolicyRequest = Field(
        default_factory=LotsComputationPolicyRequest
    )
    triplicity_doctrine: TriplicityDoctrine = (
        TriplicityDoctrine.DOROTHEAN_PINGREE_1976
    )
    bounds: EgyptianBoundsPolicyRequest = Field(
        default_factory=EgyptianBoundsPolicyRequest
    )
    decennials: HellenisticDecennialPolicyRequest = Field(
        default_factory=HellenisticDecennialPolicyRequest
    )
    zr_year: HellenisticZRYearPolicyRequest = Field(
        default_factory=HellenisticZRYearPolicyRequest
    )
    activation_orb_deg: float = Field(default=5.0, ge=0.0)
    leap_day_policy: LeapDayAnniversaryPolicy | None = None
    monthly_profection_interval_policy: MonthlyProfectionIntervalPolicy = (
        MonthlyProfectionIntervalPolicy
        .EQUAL_TWELFTHS_OF_CIVIL_ANNIVERSARY_YEAR
    )
    profection_ambiguous_time_policy: (
        ProfectionAmbiguousTimePolicy | None
    ) = None
    zr_lot_name: Literal["Fortune", "Spirit", "Eros", "Necessity"] = "Spirit"
    zr_levels: int = Field(default=2, ge=1, le=4)
    use_loosing_of_bond: bool = True

    @field_validator("activation_orb_deg")
    @classmethod
    def _finite_activation_orb(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("activation_orb_deg must be finite")
        return value

    @model_validator(mode="after")
    def _admitted_atomic_policies(self) -> "HellenisticProfilePolicyRequest":
        if self.dignity.essential.doctrine.value != "traditional_classic_7":
            raise ValueError(
                "Hellenistic profiles require traditional_classic_7 dignity "
                "doctrine"
            )
        if (
            self.triplicity_doctrine
            is not TriplicityDoctrine.DOROTHEAN_PINGREE_1976
        ):
            raise ValueError(
                "Hellenistic profiles require dorothean_pingree_1976 "
                "triplicity doctrine"
            )
        if (
            self.lots.unresolved_reference_mode
            is not LotsReferenceFailureMode.SKIP
        ):
            raise ValueError(
                "Hellenistic profiles require typed skipped-lot receipts"
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
        return self


class HellenisticChartProfileRequest(_StrictModel):
    """Chart-backed request using exact Whole Sign geometry."""

    natal_dt: datetime
    current_dt: datetime
    civil_timezone: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    observer_lat: float = Field(ge=-90.0, le=90.0)
    observer_lon: float = Field(ge=-180.0, le=180.0)
    observer_elev_m: float = 0.0
    syzygy: float | None = None
    prenatal_new_moon: float | None = None
    prenatal_full_moon: float | None = None
    lord_of_hour: float | None = None
    policy: HellenisticProfilePolicyRequest = Field(
        default_factory=HellenisticProfilePolicyRequest
    )

    @field_validator("natal_dt", "current_dt")
    @classmethod
    def _aware_datetimes(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("profile datetimes must be timezone-aware")
        return value

    @field_validator("civil_timezone")
    @classmethod
    def _trimmed_civil_timezone(cls, value: str | None) -> str | None:
        if value is not None and value != value.strip():
            raise ValueError("civil_timezone must be trimmed")
        return value

    @field_validator("observer_lat", "observer_lon", "observer_elev_m")
    @classmethod
    def _finite_observer_inputs(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("observer inputs must be finite")
        return value

    @field_validator(
        "syzygy",
        "prenatal_new_moon",
        "prenatal_full_moon",
        "lord_of_hour",
    )
    @classmethod
    def _finite_lot_support(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("optional lot support longitudes must be finite")
        return value

    @model_validator(mode="after")
    def _chronological_query(self) -> "HellenisticChartProfileRequest":
        if self.current_dt < self.natal_dt:
            raise ValueError("current_dt must not be earlier than natal_dt")
        return self


class HellenisticPlanetaryJoyTruthResponse(_StrictModel):
    status: TruthEvaluationStatus
    planet: str
    actual_house: int
    joy_house: int | None
    matched: bool | None
    reason: str | None


class HellenisticPlanetProfileResponse(_StrictModel):
    planet: str
    longitude: float
    sign: str
    house: int
    is_retrograde: bool
    essential_components: tuple[EssentialDignityComponentTruthResponse, ...]
    sect_truth: SectTruthResponse
    joy_truth: HellenisticPlanetaryJoyTruthResponse
    solar_proximity_truth: SolarProximityTruthResponse
    planetary_solar_phase_truth: PlanetarySolarPhaseTruthResponse
    besieging_truth: BesiegingTruthResponse
    receptions: tuple[PlanetaryReceptionResponse, ...]
    triplicity_assignment: TriplicityAssignmentResponse
    bound_truth: EgyptianBoundTruthResponse
    face: DecanatePositionResponse


class HellenisticAspectProfileResponse(_StrictModel):
    body1: str
    body2: str
    aspect: str
    symbol: str
    angle: float
    separation: float
    sign_degree1: int
    sign_degree2: int
    classification: HellenisticAspectClassificationResponse
    superiority_truth: HellenisticSuperiorityTruthResponse


class HellenisticLotProfileResponse(_StrictModel):
    name: str
    longitude: float
    formula: str
    category: str
    description: str
    computation_truth: ArabicPartComputationTruthResponse
    dependency_completeness: LotDependencyCompletenessTruthResponse
    astrological_condition_truth: LotAstrologicalConditionTruthResponse


class HellenisticDecennialPeriodResponse(_StrictModel):
    """One active L1/L2 period with deep-subdivision fields absent."""

    level: int = Field(ge=1, le=2)
    level_name: str
    planet: str
    start_jd: float
    end_jd: float
    years: float
    months: float
    days: float
    time_basis: str
    calendar_projection_basis: str
    sequence_origin_jd: float
    start_distribution_day: float
    end_distribution_day: float
    distribution_years: float
    start_date: str
    end_date: str
    major_planet: str | None
    parent_planet: str | None
    parent_level: int | None
    is_day_chart: bool | None
    sect_light: str | None
    sequence_kind: str | None
    major_index: int
    sub_index: int | None
    ancestor_planets: list[str]
    sequence_position: int
    sequence_truth: DecennialSequenceAssemblyTruthResponse


class HellenisticDecennialSnapshotResponse(_StrictModel):
    status: HellenisticProfileStatus
    sequence_truth: DecennialSequenceAssemblyTruthResponse
    active_periods: tuple[HellenisticDecennialPeriodResponse, ...]
    reason: str | None


class HellenisticZodiacalReleasingSnapshotResponse(_StrictModel):
    status: HellenisticProfileStatus
    lot_name: str
    source_lot_name: str
    lot_longitude: float | None
    fortune_longitude: float | None
    levels: int
    use_loosing_of_bond: bool
    active_periods: tuple[ZRReleasingPeriodResponse, ...]
    reason: str | None


class HellenisticProfileNotEvaluableResponse(_StrictModel):
    component: str
    subject: str
    reason: str


class HellenisticObserverContextResponse(_StrictModel):
    latitude: float | None
    longitude: float | None
    elevation_m: float | None
    source: str


class HellenisticProfileProvenanceResponse(_StrictModel):
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
    not_evaluable: tuple[HellenisticProfileNotEvaluableResponse, ...]


class HellenisticChartProfileResponse(_StrictModel):
    """Unified non-interpretive profile; no synthetic aggregate score exists."""

    layer: Literal["hellenistic"] = "hellenistic"
    natal_dt: datetime
    current_dt: datetime
    natal_jd: float
    current_jd: float
    house_system: str
    asc_longitude: float
    mc_longitude: float
    observer: HellenisticObserverContextResponse
    is_day_chart: bool
    sect_light: str
    policy: HellenisticProfilePolicyRequest
    planets: tuple[HellenisticPlanetProfileResponse, ...]
    aspects: tuple[HellenisticAspectProfileResponse, ...]
    lots: tuple[HellenisticLotProfileResponse, ...]
    lots_not_evaluable: tuple[LotNotEvaluableResponse, ...]
    profection: ProfectionResultResponse
    decennials: HellenisticDecennialSnapshotResponse
    zodiacal_releasing: HellenisticZodiacalReleasingSnapshotResponse
    included_components: tuple[HellenisticProfileComponent, ...]
    excluded_components: tuple[HellenisticProfileExclusion, ...]
    provenance: HellenisticProfileProvenanceResponse


__all__ = [
    "HellenisticAspectProfileResponse",
    "HellenisticChartProfileRequest",
    "HellenisticChartProfileResponse",
    "HellenisticDecennialPolicyRequest",
    "HellenisticDecennialPeriodResponse",
    "HellenisticDecennialSnapshotResponse",
    "HellenisticLotProfileResponse",
    "HellenisticObserverContextResponse",
    "HellenisticPlanetProfileResponse",
    "HellenisticPlanetaryJoyTruthResponse",
    "HellenisticProfileNotEvaluableResponse",
    "HellenisticProfilePolicyRequest",
    "HellenisticProfileProvenanceResponse",
    "HellenisticZRYearPolicyRequest",
    "HellenisticZodiacalReleasingSnapshotResponse",
]
