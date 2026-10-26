"""Strict transport contracts for named derived-point models."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator

from moira.derived_points import DerivedPointDefinition, SecondFocusStatus
from moira.nodes import TrueLilithReductionTruth
from moira.orbits import OrbitalCenter, OrbitalFrame, OsculatingElements

FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class DerivedPointEpochRequest(_StrictModel):
    jd_ut: FiniteNumber


class MeanPriapusRequest(DerivedPointEpochRequest):
    nutation: Annotated[bool, Field(strict=True)] = True


class BakerLongitudesRequest(_StrictModel):
    sun_longitude: FiniteNumber
    mercury_longitude: FiniteNumber


class SecondFocusRequest(DerivedPointEpochRequest):
    body: StrictStr | StrictInt
    center: OrbitalCenter
    frame: OrbitalFrame

    @field_validator("body")
    @classmethod
    def _nonempty_body(cls, value: str | int) -> str | int:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("body must be non-empty")
        return value


class BakerVulcanResponse(_StrictModel):
    longitude: float
    sun_longitude: float
    mercury_longitude: float
    frame: str
    jd_ut: float | None
    epoch_tt: float | None
    epoch_tdb: float | None
    kernel_identity: str | None
    model: Literal["baker_vulcan"]
    kind: Literal["symbolic_longitude"]
    source: str


class PriapusResponse(_StrictModel):
    name: str
    model: Literal["mean_priapus", "osculating_priapus"]
    longitude: float
    speed: float
    jd_ut: float
    epoch_tt: float
    frame: str
    speed_method: str
    source_apogee_longitude: float
    source_apogee_truth: TrueLilithReductionTruth | None
    kind: Literal["lunar_perigee"]


class SecondFocusResponse(_StrictModel):
    status: SecondFocusStatus
    vector_au: tuple[float, float, float] | None
    longitude: float | None
    latitude: float | None
    distance_au: float | None
    source_elements: OsculatingElements
    model: Literal["elliptic_second_focus"]
    kind: Literal["geometric_point"]
    origin: Literal["selected_central_focus"]
    formula: str


class DerivedPointCatalogResponse(_StrictModel):
    points: list[DerivedPointDefinition]
    count: int
