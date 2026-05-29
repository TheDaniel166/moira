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


__all__ = [
    "MuddaDashaActivationResponse",
    "MuddaDashaPeriodResponse",
    "MuddaDashaResponse",
    "MuddaPeriodJudgementResponse",
    "MuddaPeriodResultProfileResponse",
    "MunthaConditionProfileResponse",
    "TajikaAspectResponse",
    "TajikaYogaResponse",
    "TasiraDashaResponse",
    "TasiraPeriodResponse",
    "VarshaphalChartRequest",
    "VarshaphalChartResponse",
    "VarshaphalHouseCuspsResponse",
    "VarshaphalSahamResponse",
    "VarshaphalTimingRequest",
    "VarsheshaResultResponse",
]
