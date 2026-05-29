"""Transport models for phase-8 profection and timelord route families."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import _StrictModel


class TimelordNativityRequest(_StrictModel):
    dt: datetime
    latitude: float
    longitude: float
    house_system: str | None = None
    bodies: list[str] | None = None
    include_nodes: bool = False
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0
    activation_orb: float = Field(default=5.0, ge=0.0)


class AnnualProfectionRequest(_StrictModel):
    natal: TimelordNativityRequest
    age_years: int = Field(ge=0)


class MonthlyProfectionRequest(_StrictModel):
    natal: TimelordNativityRequest
    age_years: int = Field(ge=0)
    month_index: int = Field(ge=0, le=11)


class ProfectionScheduleRequest(_StrictModel):
    natal: TimelordNativityRequest
    current_dt: datetime


class ProfectionResultResponse(_StrictModel):
    age_years: int
    profected_house: int
    profected_asc_lon: float
    profected_sign: str
    lord_of_year: str
    activated_planets: list[str]
    monthly_lords: list[str]


class MonthlyProfectionResponse(_StrictModel):
    profected_longitude: float
    sign: str
    lord_of_month: str


# ---------------------------------------------------------------------------
# P8-07 Firdaria request models
# ---------------------------------------------------------------------------

class FirdarNatalRequest(_StrictModel):
    """Natal basis for Firdaria computations.

    is_day_chart: True when the Sun is above the horizon at birth (diurnal chart).
    The caller is responsible for supplying the correct sect designation.
    """

    dt: datetime
    is_day_chart: bool


class FirdarBaseRequest(_StrictModel):
    """Base request for sequence-level Firdaria routes."""

    natal: FirdarNatalRequest
    variant: str = "standard"
    include_node_subperiods: bool = False


class FirdarCurrentRequest(_StrictModel):
    """Request for the currently active Firdaria major and sub-period."""

    natal: FirdarNatalRequest
    current_dt: datetime
    variant: str = "standard"
    include_node_subperiods: bool = False


class FirdarActivePairRequest(_StrictModel):
    """Request for the Firdaria active pair at an arbitrary query date."""

    natal: FirdarNatalRequest
    query_dt: datetime
    variant: str = "standard"
    include_node_subperiods: bool = False


# ---------------------------------------------------------------------------
# P8-07 Firdaria response models
# ---------------------------------------------------------------------------

class FirdarPeriodResponse(_StrictModel):
    level: int
    level_name: str
    planet: str
    start_jd: float
    end_jd: float
    years: float
    days: float
    start_date: str
    end_date: str
    is_major: bool
    major_planet: str | None
    is_day_chart: bool | None
    variant: str | None
    sequence_kind: str | None
    is_node_period: bool


class FirdarMajorGroupResponse(_StrictModel):
    major: FirdarPeriodResponse
    subs: list[FirdarPeriodResponse]
    sub_count: int
    has_subs: bool


class FirdarSequenceResponse(_StrictModel):
    periods: list[FirdarPeriodResponse]
    total_count: int
    major_count: int
    sub_count: int


class FirdarGroupsResponse(_StrictModel):
    groups: list[FirdarMajorGroupResponse]
    major_count: int


class FirdarCurrentResponse(_StrictModel):
    major: FirdarPeriodResponse
    sub: FirdarPeriodResponse


class FirdarConditionProfileResponse(_StrictModel):
    planet: str
    level: int
    level_name: str
    is_major: bool
    is_node_period: bool
    lord_type: str
    sequence_kind: str | None
    major_planet: str | None
    is_day_chart: bool | None
    years: float
    days: float


class FirdarSequenceProfileResponse(_StrictModel):
    profiles: list[FirdarConditionProfileResponse]
    profile_count: int
    major_count: int
    luminary_major_count: int
    planet_major_count: int
    node_major_count: int
    total_major_years: float
    sequence_kind: str | None
    has_node_majors: bool


class FirdarActivePairResponse(_StrictModel):
    major_profile: FirdarConditionProfileResponse
    sub_profile: FirdarConditionProfileResponse | None
    has_sub: bool
    is_same_lord: bool
    is_same_lord_type: bool
    involves_node: bool


class FirdarActivePairOptionalResponse(_StrictModel):
    """Wrapper for active-pair result — active=False when query_dt is outside the 75-year cycle."""

    active: bool
    pair: FirdarActivePairResponse | None


# ---------------------------------------------------------------------------
# P8-08 Decennials request models
# ---------------------------------------------------------------------------

class DecennialNatalRequest(_StrictModel):
    """Natal basis for Decennials computations.

    is_day_chart: True for a diurnal (day) chart — governs the sect-light
    anchor and sequence ordering.
    levels: depth of sub-period generation (1=major only, 2=sub, 3=day-sub, 4=hour-sub).
    """

    dt: datetime
    is_day_chart: bool
    levels: int = Field(default=2, ge=1, le=4)


class DecennialBaseRequest(_StrictModel):
    natal: DecennialNatalRequest


class DecennialCurrentRequest(_StrictModel):
    natal: DecennialNatalRequest
    current_dt: datetime


class DecennialActivePairRequest(_StrictModel):
    natal: DecennialNatalRequest
    query_dt: datetime


# ---------------------------------------------------------------------------
# P8-08 Decennials response models
# ---------------------------------------------------------------------------

class DecennialPeriodResponse(_StrictModel):
    level: int
    level_name: str
    planet: str
    start_jd: float
    end_jd: float
    years: float
    months: float
    days: float
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


class DecennialMajorGroupResponse(_StrictModel):
    major: DecennialPeriodResponse
    subs: list[DecennialPeriodResponse]
    sub_count: int


class DecennialSequenceResponse(_StrictModel):
    periods: list[DecennialPeriodResponse]
    total_count: int
    major_count: int
    sub_count: int
    levels_generated: int


class DecennialGroupsResponse(_StrictModel):
    groups: list[DecennialMajorGroupResponse]
    major_count: int


class DecennialCurrentResponse(_StrictModel):
    major: DecennialPeriodResponse
    sub: DecennialPeriodResponse


class DecennialConditionProfileResponse(_StrictModel):
    planet: str
    level: int
    level_name: str
    is_major: bool
    lord_type: str
    sequence_kind: str | None
    major_planet: str | None
    parent_planet: str | None
    parent_level: int | None
    ancestor_planets: list[str]
    effective_major_planet: str
    is_day_chart: bool | None
    sect_light: str | None
    major_index: int
    sub_index: int | None
    sequence_position: int
    deep_subdivision_method: str | None
    years: float
    months: float
    days: float
    month_basis_days: float


class DecennialSequenceProfileResponse(_StrictModel):
    profiles: list[DecennialConditionProfileResponse]
    profile_count: int
    major_count: int
    luminary_major_count: int
    planetary_major_count: int
    total_major_years: float
    total_major_months: float
    sequence_kind: str | None
    sect_light: str | None
    deepest_level: int


class DecennialActivePairResponse(_StrictModel):
    major_profile: DecennialConditionProfileResponse
    sub_profile: DecennialConditionProfileResponse | None
    has_sub: bool
    is_same_lord: bool
    is_same_lord_type: bool
    shares_sect_light: bool


class DecennialActivePairOptionalResponse(_StrictModel):
    """Wrapper — active=False when query_dt falls outside the Decennials cycle."""

    active: bool
    pair: DecennialActivePairResponse | None


class DecennialActivePathResponse(_StrictModel):
    profiles: list[DecennialConditionProfileResponse]
    deepest_level: int
    has_deep_subdivision: bool


class DecennialActivePathOptionalResponse(_StrictModel):
    """Wrapper — active=False when query_dt falls outside the Decennials cycle."""

    active: bool
    path: DecennialActivePathResponse | None


# ---------------------------------------------------------------------------
# P8-09 Zodiacal Releasing request models
# ---------------------------------------------------------------------------

class ZRNatalRequest(_StrictModel):
    """Natal basis for Zodiacal Releasing.

    The caller supplies lot_longitude directly — the engine takes it as an
    input rather than computing it from a chart, preserving doctrinal flexibility.
    fortune_longitude enables Fortune-relative angularity classification (peak periods);
    pass None to omit it.
    """

    dt: datetime
    lot_longitude: float
    lot_name: str = "Spirit"
    fortune_longitude: float | None = None
    use_loosing_of_bond: bool = True


class ZRBaseRequest(_StrictModel):
    """Request for the full Zodiacal Releasing sequence."""

    natal: ZRNatalRequest
    levels: int = Field(default=4, ge=1, le=4)


class ZRCurrentRequest(_StrictModel):
    """Request for the active Zodiacal Releasing periods at a query date."""

    natal: ZRNatalRequest
    current_dt: datetime


class ZRProfileRequest(_StrictModel):
    """Request for the Zodiacal Releasing sequence profile at a chosen level."""

    natal: ZRNatalRequest
    levels: int = Field(default=4, ge=1, le=4)
    profile_level: int = Field(default=1, ge=1, le=4)


class ZRLevelPairRequest(_StrictModel):
    """Request for the active ZRLevelPair between two releasing levels at a query date."""

    natal: ZRNatalRequest
    query_dt: datetime
    upper_level: int = Field(default=1, ge=1, le=3)
    lower_level: int = Field(default=2, ge=2, le=4)


# ---------------------------------------------------------------------------
# P8-09 Zodiacal Releasing response models
# ---------------------------------------------------------------------------

class ZRReleasingPeriodResponse(_StrictModel):
    level: int
    level_name: str
    sign: str
    ruler: str
    start_jd: float
    end_jd: float
    years: float
    days: float
    start_date: str
    end_date: str
    lot_name: str
    is_loosing_of_bond: bool
    is_peak_period: bool
    angularity_from_fortune: int | None
    angularity_class: str | None
    use_loosing_of_bond: bool


class ZRPeriodGroupResponse(_StrictModel):
    period: ZRReleasingPeriodResponse
    sub_groups: list[ZRPeriodGroupResponse] = Field(default_factory=list)
    level: int
    has_sub_groups: bool
    is_leaf: bool
    angularity_class: str | None


ZRPeriodGroupResponse.model_rebuild()


class ZRSequenceResponse(_StrictModel):
    periods: list[ZRReleasingPeriodResponse]
    total_count: int
    level1_count: int
    levels_generated: int


class ZRGroupsResponse(_StrictModel):
    groups: list[ZRPeriodGroupResponse]
    level1_count: int


class ZRCurrentResponse(_StrictModel):
    periods: list[ZRReleasingPeriodResponse]
    active_count: int


class ZRConditionProfileResponse(_StrictModel):
    sign: str
    ruler: str
    level: int
    level_name: str
    lot_name: str
    years: float
    days: float
    is_loosing_of_bond: bool
    is_peak_period: bool
    angularity_from_fortune: int | None
    angularity_class: str | None
    use_loosing_of_bond: bool


class ZRSequenceProfileResponse(_StrictModel):
    profiles: list[ZRConditionProfileResponse]
    profile_count: int
    period_count: int
    peak_period_count: int
    non_peak_count: int
    loosing_of_bond_count: int
    angular_count: int
    succedent_count: int
    cadent_count: int
    total_years: float
    profile_level: int


class ZRLevelPairResponse(_StrictModel):
    upper_profile: ZRConditionProfileResponse
    lower_profile: ZRConditionProfileResponse
    house_distance: int
    signs_are_identical: bool
    is_adjacent_levels: bool
    is_angular_distance: bool
    is_peak_pair: bool


__all__ = [
    "AnnualProfectionRequest",
    "DecennialActivePairOptionalResponse",
    "DecennialActivePairRequest",
    "DecennialActivePairResponse",
    "DecennialActivePathOptionalResponse",
    "DecennialActivePathResponse",
    "DecennialBaseRequest",
    "DecennialConditionProfileResponse",
    "DecennialCurrentRequest",
    "DecennialCurrentResponse",
    "DecennialGroupsResponse",
    "DecennialMajorGroupResponse",
    "DecennialNatalRequest",
    "DecennialPeriodResponse",
    "DecennialSequenceProfileResponse",
    "DecennialSequenceResponse",
    "FirdarActivePairOptionalResponse",
    "FirdarActivePairRequest",
    "FirdarActivePairResponse",
    "FirdarBaseRequest",
    "FirdarConditionProfileResponse",
    "FirdarCurrentRequest",
    "FirdarCurrentResponse",
    "FirdarGroupsResponse",
    "FirdarMajorGroupResponse",
    "FirdarNatalRequest",
    "FirdarPeriodResponse",
    "FirdarSequenceProfileResponse",
    "FirdarSequenceResponse",
    "MonthlyProfectionRequest",
    "MonthlyProfectionResponse",
    "ProfectionResultResponse",
    "ProfectionScheduleRequest",
    "TimelordNativityRequest",
    "ZRBaseRequest",
    "ZRConditionProfileResponse",
    "ZRCurrentRequest",
    "ZRCurrentResponse",
    "ZRGroupsResponse",
    "ZRLevelPairRequest",
    "ZRLevelPairResponse",
    "ZRNatalRequest",
    "ZRPeriodGroupResponse",
    "ZRProfileRequest",
    "ZRReleasingPeriodResponse",
    "ZRSequenceProfileResponse",
    "ZRSequenceResponse",
]
