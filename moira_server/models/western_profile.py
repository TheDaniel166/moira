"""Transport models for Western chart-profile bundle endpoints."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from moira.constants import HouseSystem

from .chart import (
    ChartReductionTruthResponse,
    ChartResponse,
    HousePolicyRequest,
    HousesReductionTruthResponse,
    HousesResponse,
)
from .common import _StrictModel
from .dignities import (
    ChartConditionProfileResponse,
    DignitiesResultResponse,
    DignityComputationPolicyRequest,
)
from .profile_bundles import ProfileBundleProvenanceResponse


class WesternProfileIncludeRequest(_StrictModel):
    """Explicit section selection for the Western chart-profile bundle."""

    chart: bool = True
    houses: bool = True
    dignities: bool = True
    dignity_profile: bool = True

    @model_validator(mode="after")
    def _at_least_one_section(self) -> "WesternProfileIncludeRequest":
        if not any(
            (
                self.chart,
                self.houses,
                self.dignities,
                self.dignity_profile,
            )
        ):
            raise ValueError("at least one Western profile section must be requested")
        return self


class WesternChartProfileRequest(_StrictModel):
    """Chart-backed Western convenience bundle request."""

    dt: datetime
    observer_lat: float = Field(ge=-90.0, le=90.0)
    observer_lon: float = Field(ge=-180.0, le=180.0)
    observer_elev_m: float = 0.0
    house_system: str = HouseSystem.PLACIDUS
    bodies: list[str] | None = None
    include_nodes: bool = True
    include: WesternProfileIncludeRequest = Field(
        default_factory=WesternProfileIncludeRequest
    )
    house_policy: HousePolicyRequest | None = None
    dignity_policy: DignityComputationPolicyRequest | None = None

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("observer_lat", "observer_lon", "observer_elev_m")
    @classmethod
    def _finite_observer_input(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("observer inputs must be finite")
        return value

    @field_validator("house_system")
    @classmethod
    def _non_empty_house_system(cls, value: str) -> str:
        if not value:
            raise ValueError("house_system must be non-empty")
        return value


class WesternChartProfileResponse(_StrictModel):
    """Composed Western chart profile with each computational stratum visible."""

    layer: Literal["western"] = "western"
    request: WesternChartProfileRequest
    included_sections: tuple[str, ...]
    chart: ChartResponse | None = None
    chart_reduction: ChartReductionTruthResponse | None = None
    houses: HousesResponse | None = None
    houses_reduction: HousesReductionTruthResponse | None = None
    dignities: DignitiesResultResponse | None = None
    dignity_profile: ChartConditionProfileResponse | None = None
    provenance: ProfileBundleProvenanceResponse


__all__ = [
    "WesternChartProfileRequest",
    "WesternChartProfileResponse",
    "WesternProfileIncludeRequest",
]
