"""Transport models for phase-8 Varshaphal route families (P8-11, P8-13)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import _StrictModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class VarshaphalChartRequest(_StrictModel):
    """Request for a structured Varshaphal annual-return chart.

    natal_latitude/natal_longitude: birth location (for natal house and Muntha).
    latitude/longitude: location for the return chart cast (may differ from natal).
    year: Gregorian year of the Varshaphal return to compute.
    ayanamsa: sidereal ayanamsa key; None defaults to Lahiri.
    house_system: house system code; None defaults to Placidus.
    """

    natal_dt: datetime
    natal_latitude: float
    natal_longitude: float
    year: int
    latitude: float
    longitude: float
    ayanamsa: str | None = None
    house_system: str | None = None
    bodies: list[str] | None = None


class VarshaphalTimingRequest(_StrictModel):
    """Request for Varshaphal timing surfaces (mudda/tasira active period)."""

    natal_dt: datetime
    natal_latitude: float
    natal_longitude: float
    year: int
    latitude: float
    longitude: float
    query_dt: datetime
    ayanamsa: str | None = None
    house_system: str | None = None
    bodies: list[str] | None = None


# ---------------------------------------------------------------------------
# Shared sub-vessels
# ---------------------------------------------------------------------------

class VarshaphalHouseCuspsResponse(_StrictModel):
    system: str
    cusps: list[float]
    asc: float
    mc: float
    vertex: float | None


class VarshaphalSahamResponse(_StrictModel):
    name: str
    longitude: float
    house: int
    ruler: str


class MunthaConditionProfileResponse(_StrictModel):
    muntha_longitude: float
    muntha_house: int
    muntha_sign: str
    muntha_lord: str
    muntha_lord_longitude: float
    muntha_lord_house: int
    muntha_lord_sign: str
    lord_in_kendra: bool
    lord_in_trikona: bool
    lord_in_dusthana: bool
    lord_is_strong: bool
    lord_is_weak: bool


class VarsheshaResultResponse(_StrictModel):
    planet: str
    roles: list[str]
    selection_basis: str
    triplicity_contenders: list[str]


class TajikaAspectResponse(_StrictModel):
    body1: str
    body2: str
    angle: float
    orb: float
    relation: str
    relation_strength: float
    effect: str
    is_benefic_relation: bool
    within_effective_orb: bool


class TajikaYogaResponse(_StrictModel):
    name: str
    body1: str
    body2: str
    favorable: bool
    doctrine: str
    mediator: str | None


# ---------------------------------------------------------------------------
# Mudda dasha vessels (recursive period)
# ---------------------------------------------------------------------------

class MuddaDashaPeriodResponse(_StrictModel):
    level: int
    lord: str
    start_day: float
    end_day: float
    duration_days: float
    start_date: str
    end_date: str
    source_fraction: str
    sub: list[MuddaDashaPeriodResponse] = Field(default_factory=list)


MuddaDashaPeriodResponse.model_rebuild()


class MuddaDashaResponse(_StrictModel):
    school: str
    natal_nakshatra: str
    natal_nakshatra_index: int
    natal_nakshatra_lord: str
    birth_elapsed_ghatis: float
    birth_remaining_ghatis: float
    year_ruler: str
    year_start_date: str
    year_end_date: str
    periods: list[MuddaDashaPeriodResponse]


# ---------------------------------------------------------------------------
# Tasira vessels
# ---------------------------------------------------------------------------

class TasiraPeriodResponse(_StrictModel):
    lord: str
    aspect_angle: float
    aspect_points: float
    nominal_days: float
    start_date: str
    end_date: str


class TasiraDashaResponse(_StrictModel):
    year_start_date: str
    year_end_date: str
    periods: list[TasiraPeriodResponse]


# ---------------------------------------------------------------------------
# P8-11: Full chart response
# ---------------------------------------------------------------------------

class VarshaphalChartResponse(_StrictModel):
    """Core Varshaphal annual-return vessel for P8-11 transport.

    Deeper doctrine products (full judgement profile, year judgement, actor
    rankings, saham priorities) are deferred to P8-12 routes.
    year_judgement_verdict carries the final verdict string as a summary.
    """

    birth_jd: float
    return_year: int
    years_elapsed: int
    jd_ut: float
    return_date: str
    ayanamsa_system: str
    sidereal_planets: dict[str, float]
    sidereal_houses: VarshaphalHouseCuspsResponse
    natal_sidereal_asc: float
    natal_sidereal_planets: dict[str, float]
    muntha_longitude: float
    muntha_house: int
    muntha_lord: str
    muntha_sign: str
    muntha_profile: MunthaConditionProfileResponse
    varshesha: VarsheshaResultResponse
    tajika_aspects: list[TajikaAspectResponse]
    tajika_yogas: list[TajikaYogaResponse]
    sahams: list[VarshaphalSahamResponse]
    natal_sahams: list[VarshaphalSahamResponse]
    mudda_dasha: MuddaDashaResponse
    tasira_dasha: TasiraDashaResponse
    year_judgement_verdict: str


# ---------------------------------------------------------------------------
# P8-13: Timing response vessels
# ---------------------------------------------------------------------------

class MuddaDashaActivationResponse(_StrictModel):
    query_date: str
    major_lord: str
    major_start_date: str
    major_end_date: str
    sub_lord: str
    sub_start_date: str
    sub_end_date: str


class MuddaPeriodResultProfileResponse(_StrictModel):
    period_lord: str
    governing_year_lord: str
    relation_to_varshesha: str
    relation_to_year_lagna_lord: str
    strength_quality: str
    manifestation: str
    result_fullness: str
    doctrine: str


class MuddaPeriodJudgementResponse(_StrictModel):
    activation: MuddaDashaActivationResponse
    major_lord: str
    sub_lord: str
    major_house: int | None
    sub_house: int | None
    major_authority: str | None
    sub_authority: str | None
    major_supportive_yoga_count: int
    major_obstructive_yoga_count: int
    sub_supportive_yoga_count: int
    sub_obstructive_yoga_count: int
    major_result: MuddaPeriodResultProfileResponse
    sub_result: MuddaPeriodResultProfileResponse


# ---------------------------------------------------------------------------
# P8-12: Deeper Varshaphal annual doctrine response models
# These preserve the full engine vessel distinctions without flattening.
# ---------------------------------------------------------------------------

class TajikaPanchavargiStrengthResponse(_StrictModel):
    """Primary-source Tajika five-dignity strength on the 20-point scale."""
    planet: str
    longitude: float
    sign: str
    domicile_lord: str
    domicile_relationship: str
    domicile_score: float
    exaltation_basis_planet: str | None
    exaltation_relationship: str
    exaltation_score: float
    hadda_lord: str
    hadda_relationship: str
    hadda_score: float
    decan_lord: str
    decan_relationship: str
    decan_score: float
    musallaha_lord: str
    musallaha_relationship: str
    musallaha_score: float
    total_score: float


class TajikaKalaBalaResponse(_StrictModel):
    """Primary-source Tajika temporal strength breakdown."""
    planet: str
    sect_strength: float
    luminary_elongation_strength: float
    venus_elongation_strength: float
    night_watch_strength: float
    total_score: float


class TajikaChestaBalaResponse(_StrictModel):
    """Primary-source Tajika motion strength breakdown."""
    planet: str
    motion_mode_strength: float
    benefic_contact_strength: float
    solar_synodic_strength: float
    blocked_by_malefic_contact: bool
    total_score: float


class TajikaDrigBalaResponse(_StrictModel):
    """Primary-source Tajika aspect strength breakdown."""
    planet: str
    ascendant_aspect_strength: float
    benefic_support_strength: float
    blocked_by_malefic_square: bool
    total_score: float


class TajikaShadbalaProfileResponse(_StrictModel):
    """Primary-source Tajika sixfold strength profile for one annual planet."""
    planet: str
    panchavargi_strength: TajikaPanchavargiStrengthResponse
    directional_strength: float
    temporal_strength: TajikaKalaBalaResponse
    natural_strength: float
    motion_strength: TajikaChestaBalaResponse
    aspect_strength: TajikaDrigBalaResponse
    total_score: float


class VarshaphalActorJudgementResponse(_StrictModel):
    """Ranked annual testimony for one governing actor in the return chart."""
    actor: str
    planet: str
    house: int
    supportive_yoga_count: int
    obstructive_yoga_count: int
    panchavargi_strength: TajikaPanchavargiStrengthResponse
    shadbala: TajikaShadbalaProfileResponse
    authority_score: float
    authority: str


class VarshaphalSahamJudgementResponse(_StrictModel):
    """Ranked annual testimony for one Saham through its place and ruler."""
    saham_name: str
    house: int
    ruler: str
    ruler_house: int
    ruler_strength: TajikaShadbalaProfileResponse
    relevance_score: float
    authority: str


class VarshaphalSahamPriorityResponse(_StrictModel):
    """Source-owned gate for whether a Saham should weigh in the annual verdict."""
    saham_name: str
    annual_judgement: VarshaphalSahamJudgementResponse
    natal_judgement: VarshaphalSahamJudgementResponse
    priority: str
    is_considered: bool
    doctrine: str


class VarshaphalJudgementProfileResponse(_StrictModel):
    """First annual judgement scaffold built around the ruler of the year."""
    varshesha: VarsheshaResultResponse
    supportive_yogas: list[str]
    obstructive_yogas: list[str]
    varshesha_house: int
    varshesha_dignity: str  # simplified; engine carries full VedicDignityResult
    varshesha_strength: TajikaPanchavargiStrengthResponse
    varshesha_shadbala: TajikaShadbalaProfileResponse
    muntha_lord_shadbala: TajikaShadbalaProfileResponse
    year_lagna_lord: str
    year_lagna_lord_strong: bool
    actor_rankings: list[VarshaphalActorJudgementResponse]
    key_saham_rankings: list[VarshaphalSahamJudgementResponse]
    # mudda_period is optional and heavy; exposed via dedicated timing routes
    strongest_testimonies: list[str]
    yearly_strength_balance: str
    ascendant_authority_indication: str


class VarshaphalYearJudgementResponse(_StrictModel):
    """Consolidated annual verdict surface over the Varshaphal doctrine layers."""
    profile: VarshaphalJudgementProfileResponse
    dominant_governor: VarshaphalActorJudgementResponse | None
    supporting_governors: list[VarshaphalActorJudgementResponse]
    strained_governors: list[VarshaphalActorJudgementResponse]
    topics: list["VarshaphalTopicJudgementResponse"]
    foreground_topics: list["VarshaphalTopicJudgementResponse"]
    obstructed_topics: list["VarshaphalTopicJudgementResponse"]
    background_topics: list["VarshaphalTopicJudgementResponse"]
    prioritized_sahams: list[VarshaphalSahamPriorityResponse]
    disregarded_sahams: list[VarshaphalSahamPriorityResponse]
    key_sahams: list[VarshaphalSahamJudgementResponse]
    # timed_period exposed via dedicated timing routes
    supportive_yogas: list[str]
    obstructive_yogas: list[str]
    decisive_testimonies: list[str]
    final_verdict: str
    conflict_resolution: str
    verdict_basis: list[str]


class VarshaphalTopicJudgementResponse(_StrictModel):
    """Named annual result channel built from source-owned Sahama and house testimonies."""
    topic: str
    saham_name: str
    polarity: str
    # saham_priority may be heavy; optional for transport economy
    house_numbers: list[int]
    house_rulers: list[str]
    supportive_relation_to_varshesha: bool
    obstructive_relation_to_varshesha: bool
    timed_activation: str
    emphasis_score: float
    judgement: str
    basis: list[str]


class VarshaphalTopicWindowResponse(_StrictModel):
    """Timed activation window for one annual topic within the Mudda or Tāsīra sequence."""
    topic: str
    start_jd: float
    end_jd: float
    source: str
    major_lord: str
    sub_lord: str
    activation_kind: str
    basis: list[str]


class VarshaphalYearSummaryResponse(_StrictModel):
    """Structured summary/report surface for a Varshaphal year."""
    yearly_tone: str
    dominant_governor: str | None
    foreground_topics: list[str]
    obstructed_topics: list[str]
    background_topics: list[str]
    timed_highlights: list[str]
    strongest_testimonies: list[str]
    narrative_basis: list[str]


# Forward refs for recursive / self-referential models
VarshaphalYearJudgementResponse.model_rebuild()
VarshaphalTopicJudgementResponse.model_rebuild()


# Request model for deeper doctrine queries (focus date for timed judgement surfaces)
class VarshaphalDoctrineRequest(VarshaphalChartRequest):
    """Request for deeper annual doctrine surfaces. Inherits chart construction parameters."""
    focus_dt: datetime | None = None  # optional focus moment inside the year for timed profiles


__all__ = [
    "MuddaDashaActivationResponse",
    "MuddaDashaPeriodResponse",
    "MuddaDashaResponse",
    "MuddaPeriodJudgementResponse",
    "MuddaPeriodResultProfileResponse",
    "MunthaConditionProfileResponse",
    "TajikaAspectResponse",
    "TajikaChestaBalaResponse",
    "TajikaDrigBalaResponse",
    "TajikaKalaBalaResponse",
    "TajikaPanchavargiStrengthResponse",
    "TajikaShadbalaProfileResponse",
    "TajikaYogaResponse",
    "TasiraDashaResponse",
    "TasiraPeriodResponse",
    "VarshaphalActorJudgementResponse",
    "VarshaphalChartRequest",
    "VarshaphalChartResponse",
    "VarshaphalDoctrineRequest",
    "VarshaphalHouseCuspsResponse",
    "VarshaphalJudgementProfileResponse",
    "VarshaphalSahamJudgementResponse",
    "VarshaphalSahamPriorityResponse",
    "VarshaphalSahamResponse",
    "VarshaphalTimingRequest",
    "VarshaphalTopicJudgementResponse",
    "VarshaphalTopicWindowResponse",
    "VarshaphalYearJudgementResponse",
    "VarshaphalYearSummaryResponse",
    "VarsheshaResultResponse",
]
