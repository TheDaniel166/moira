"""Transport models for Vedic chart-profile bundle endpoints."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, StrictBool, field_validator, model_validator

from moira.constants import HouseSystem

from .chart import ChartReductionTruthResponse, ChartResponse
from .common import _StrictModel
from ._vedic_inputs import (
    CivilDateTime, ClassicalPlanet, FiniteNumber, KnownAyanamsa,
    KnownHouseSystem, VimshottariYearBasis,
)
from .dasha import DashaActiveLineResponse, DashaLordPairResponse
from .panchanga import (
    PanchangaPolicyRequest,
    PanchangaProfileResponse,
    PanchangaResultResponse,
)
from .profile_bundles import ProfileBundleProvenanceResponse
from .shadbala import (
    ShadbalaChartProfileResponse,
    ShadbalaPolicyRequest,
    ShadbalaResultResponse,
)


class VedicProfileIncludeRequest(_StrictModel):
    """Explicit section selection for the Vedic chart-profile bundle."""

    chart: StrictBool = True
    panchanga: StrictBool = True
    panchanga_profile: StrictBool = True
    shadbala: StrictBool = True
    shadbala_profile: StrictBool = True
    dasha_current: StrictBool = False
    dasha_lord_pair: StrictBool = False

    @model_validator(mode="after")
    def _at_least_one_section(self) -> "VedicProfileIncludeRequest":
        if not any(
            (
                self.chart,
                self.panchanga,
                self.panchanga_profile,
                self.shadbala,
                self.shadbala_profile,
                self.dasha_current,
                self.dasha_lord_pair,
            )
        ):
            raise ValueError("at least one Vedic profile section must be requested")
        return self


class VedicChartProfileRequest(_StrictModel):
    """Chart-backed Vedic convenience bundle request."""

    dt: CivilDateTime
    current_dt: CivilDateTime | None = None
    observer_lat: FiniteNumber = Field(ge=-90.0, le=90.0)
    observer_lon: FiniteNumber = Field(ge=-180.0, le=180.0)
    observer_elev_m: FiniteNumber = 0.0
    house_system: KnownHouseSystem = HouseSystem.PLACIDUS
    bodies: list[str] | None = None
    include_nodes: StrictBool = True
    ayanamsa_system: KnownAyanamsa = "Lahiri"
    hora_lord: ClassicalPlanet | None = None
    dasha_levels: int = Field(default=5, strict=True, ge=1, le=5)
    dasha_year_basis: VimshottariYearBasis | None = None
    include: VedicProfileIncludeRequest = Field(
        default_factory=VedicProfileIncludeRequest
    )
    panchanga_policy: PanchangaPolicyRequest | None = None
    shadbala_policy: ShadbalaPolicyRequest | None = None

    @field_validator("dt", "current_dt")
    @classmethod
    def _aware_datetime(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("dt and current_dt must be timezone-aware")
        return value

    @field_validator("observer_lat", "observer_lon", "observer_elev_m")
    @classmethod
    def _finite_observer_input(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("observer inputs must be finite")
        return value

    @field_validator("house_system", "ayanamsa_system")
    @classmethod
    def _non_empty_string_input(cls, value: str) -> str:
        if not value:
            raise ValueError("house_system and ayanamsa_system must be non-empty")
        return value

    @model_validator(mode="after")
    def _current_dt_required_for_dasha(self) -> "VedicChartProfileRequest":
        if (
            self.include.dasha_current or self.include.dasha_lord_pair
        ) and self.current_dt is None:
            raise ValueError(
                "current_dt is required when requesting Vedic dasha snapshot sections"
            )
        return self


class VedicProfilePolicyReceiptResponse(_StrictModel):
    requested_ayanamsa_system: str
    component_ayanamsa_systems: dict[str, str]
    mixed_ayanamsa_frames: bool
    applied_dasha_year_basis: str | None
    inactive_inputs: tuple[str, ...]


class VedicChartProfileResponse(_StrictModel):
    """Composed Vedic chart profile with each computational stratum visible."""

    layer: Literal["vedic"] = "vedic"
    request: VedicChartProfileRequest
    policy_receipt: VedicProfilePolicyReceiptResponse
    included_sections: tuple[str, ...]
    chart: ChartResponse | None = None
    chart_reduction: ChartReductionTruthResponse | None = None
    panchanga: PanchangaResultResponse | None = None
    panchanga_profile: PanchangaProfileResponse | None = None
    shadbala: ShadbalaResultResponse | None = None
    shadbala_profile: ShadbalaChartProfileResponse | None = None
    dasha_current: DashaActiveLineResponse | None = None
    dasha_lord_pair: DashaLordPairResponse | None = None
    provenance: ProfileBundleProvenanceResponse


__all__ = [
    "VedicProfilePolicyReceiptResponse",
    "VedicChartProfileRequest",
    "VedicChartProfileResponse",
    "VedicProfileIncludeRequest",
]
