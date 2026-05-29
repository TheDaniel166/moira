"""Transport models for phase-8 Vimshottari Dasha route family (P8-10)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import _StrictModel


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class DashaNatalRequest(_StrictModel):
    """Natal basis for Vimshottari Dasha computations.

    ayanamsa: ayanamsa system key for sidereal Moon longitude conversion.
              None uses the engine default (Lahiri).
    year_basis: "savana_360" or "julian_365.25"; None uses the engine default.
    """

    dt: datetime
    ayanamsa: str | None = None
    year_basis: str | None = None


class DashaSequenceRequest(_StrictModel):
    """Request for the full Vimshottari Dasha sequence.

    levels: number of sub-period levels to generate (1=Mahadasha only,
            2=+Antardasha, ..., 5=+Prana). Defaults to 2 for transport economy.
    """

    natal: DashaNatalRequest
    levels: int = Field(default=2, ge=1, le=5)


class DashaCurrentRequest(_StrictModel):
    """Request for the currently active Vimshottari Dasha chain."""

    natal: DashaNatalRequest
    current_dt: datetime
    levels: int = Field(default=5, ge=1, le=5)


# ---------------------------------------------------------------------------
# Shared period response vessel (recursive — subs populated at deeper levels)
# ---------------------------------------------------------------------------

class DashaPeriodResponse(_StrictModel):
    level: int
    level_name: str
    planet: str
    start_jd: float
    end_jd: float
    years: float
    days: float
    start_date: str
    end_date: str
    year_basis: str | None
    lord_type: str | None
    is_node_dasha: bool
    is_luminary_dasha: bool
    birth_nakshatra: str | None
    nakshatra_fraction: float | None
    sub: list[DashaPeriodResponse] = Field(default_factory=list)


DashaPeriodResponse.model_rebuild()


# ---------------------------------------------------------------------------
# Sequence response
# ---------------------------------------------------------------------------

class DashaSequenceResponse(_StrictModel):
    mahadashas: list[DashaPeriodResponse]
    mahadasha_count: int
    levels_generated: int


# ---------------------------------------------------------------------------
# Balance response
# ---------------------------------------------------------------------------

class DashaBalanceResponse(_StrictModel):
    lord: str
    remaining_years: float


# ---------------------------------------------------------------------------
# Active-line response
# ---------------------------------------------------------------------------

class DashaActiveLineResponse(_StrictModel):
    mahadasha: DashaPeriodResponse
    antardasha: DashaPeriodResponse | None
    pratyantardasha: DashaPeriodResponse | None
    sookshma: DashaPeriodResponse | None
    prana: DashaPeriodResponse | None
    depth: int


# ---------------------------------------------------------------------------
# Condition profile and aggregate response
# ---------------------------------------------------------------------------

class DashaConditionProfileResponse(_StrictModel):
    planet: str
    level: int
    level_name: str
    lord_type: str | None
    years: float
    days: float
    year_basis: str | None
    is_node_dasha: bool
    is_luminary_dasha: bool
    birth_nakshatra: str | None
    nakshatra_fraction: float | None


class DashaSequenceProfileResponse(_StrictModel):
    profiles: list[DashaConditionProfileResponse]
    profile_count: int
    mahadasha_count: int
    luminary_count: int
    inner_count: int
    outer_count: int
    node_count: int
    total_years: float
    has_node_dashas: bool


# ---------------------------------------------------------------------------
# Lord-pair response
# ---------------------------------------------------------------------------

class DashaLordPairResponse(_StrictModel):
    maha_profile: DashaConditionProfileResponse
    antar_profile: DashaConditionProfileResponse | None
    has_antar: bool
    is_same_lord: bool
    is_same_lord_type: bool
    involves_node: bool


__all__ = [
    "DashaActiveLineResponse",
    "DashaBalanceResponse",
    "DashaConditionProfileResponse",
    "DashaCurrentRequest",
    "DashaNatalRequest",
    "DashaPeriodResponse",
    "DashaSequenceProfileResponse",
    "DashaSequenceRequest",
    "DashaSequenceResponse",
    "DashaLordPairResponse",
]
