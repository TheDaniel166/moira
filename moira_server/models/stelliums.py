"""Bounded snapshot transport for the independent planet-first stellium product."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from moira.stelliums import (
    STELLIUM_CORE,
    StelliumAnalysisPolicy,
    StelliumContext,
    StelliumSelection,
)
from .chart import HousesResponse


Criterion = Literal["sign", "house", "tight"]
Zodiac = Literal["tropical", "sidereal", "draconic"]
FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class StelliumPolicyRequest(_Model):
    preset: Literal["strict", "broad"] = "strict"
    max_span_degrees: FiniteNumber = Field(default=8.0, ge=0, lt=180)
    criteria: list[Criterion] = Field(
        default_factory=lambda: ["sign", "house", "tight"], min_length=1, max_length=3
    )

    @model_validator(mode="after")
    def validate_policy(self):
        StelliumAnalysisPolicy(self.preset, self.max_span_degrees, tuple(self.criteria))
        return self


class StelliumContextRequest(_Model):
    source_id: str = Field(min_length=1, max_length=256)
    zodiac: Zodiac
    zodiac_offset_degrees: FiniteNumber = 0.0
    ayanamsa: str | None = Field(default=None, min_length=1, max_length=128)
    coordinate_regime: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def validate_context(self):
        StelliumContext(**self.model_dump())
        return self


class StelliumSelectionRequest(_Model):
    core: list[str] = Field(default_factory=lambda: list(STELLIUM_CORE), max_length=10)
    associated: list[str] = Field(default_factory=list, max_length=256)

    @model_validator(mode="after")
    def validate_selection(self):
        StelliumSelection(tuple(self.core), tuple(self.associated))
        return self


class StelliumHouseSnapshot(HousesResponse):
    """Existing engine house receipt plus an explicit longitude frame.

    No per-body client-assigned house integers are accepted. Spatial boundary
    metadata is retained and admitted by the canonical engine vessels.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    longitude_frame: Zodiac

    @model_validator(mode="before")
    @classmethod
    def reject_coerced_or_unbounded_geometry(cls, value):
        if not isinstance(value, dict):
            return value
        numeric = {
            "asc",
            "mc",
            "armc",
            "dsc",
            "ic",
            "east_point",
            "vertex",
            "anti_vertex",
            "cusp_longitude",
            "right_ascension_deg",
            "declination_deg",
            "event_fraction",
            "obliquity_deg",
            "observer_latitude_deg",
            "zodiac_offset_deg",
        }
        vectors = {"cusps", "direction", "anchor_direction", "plane_normal"}

        inspected = 0

        def inspect(item, depth=0):
            nonlocal inspected
            inspected += 1
            if depth > 8 or inspected > 20000:
                raise ValueError("house geometry exceeds snapshot bound")
            if isinstance(item, dict):
                for key, child in item.items():
                    if key in numeric and child is not None:
                        if isinstance(child, bool) or not isinstance(
                            child, (int, float)
                        ):
                            raise ValueError(
                                f"house {key} must be numeric without coercion"
                            )
                    elif key in vectors and child is not None:
                        if not isinstance(child, (list, tuple)) or len(child) > 12:
                            raise ValueError(f"house {key} must be a bounded vector")
                        if any(
                            isinstance(n, bool) or not isinstance(n, (int, float))
                            for n in child
                        ):
                            raise ValueError(
                                f"house {key} must contain numbers without coercion"
                            )
                    elif key == "house" and type(child) is not int:
                        raise ValueError(
                            "house number must be an integer without coercion"
                        )
                    elif (
                        key
                        in (
                            "fallback",
                            "classification_latitude_sensitive",
                            "classification_polar_capable",
                        )
                        and child is not None
                        and type(child) is not bool
                    ):
                        raise ValueError(
                            f"house {key} must be boolean without coercion"
                        )
                    inspect(child, depth + 1)
            elif isinstance(item, (list, tuple)):
                if len(item) > 512:
                    raise ValueError("house geometry exceeds snapshot bound")
                for child in item:
                    inspect(child, depth + 1)

        inspect(value)
        return value


class StelliumAnalysisRequest(_Model):
    schema_version: Literal["moira.stellium.v1"]
    positions: dict[str, FiniteNumber] = Field(max_length=256)
    policy: StelliumPolicyRequest = Field(default_factory=StelliumPolicyRequest)
    selection: StelliumSelectionRequest = Field(
        default_factory=StelliumSelectionRequest
    )
    context: StelliumContextRequest
    houses: StelliumHouseSnapshot | None = None
    house_unavailable_reason: str | None = Field(
        default=None, min_length=1, max_length=512
    )


class StelliumPolicyResponse(StelliumPolicyRequest):
    min_planets: Literal[3, 4]

    @model_validator(mode="after")
    def validate_count(self):
        if self.min_planets != (4 if self.preset == "strict" else 3):
            raise ValueError("resolved stellium count disagrees with policy")
        return self


class StelliumCoverageResponse(_Model):
    requested_core: list[str]
    computed_core: list[str]
    missing_core: list[str]
    missing_associated: list[str]
    excluded: list[str]


class StelliumEvaluationResponse(_Model):
    criterion: Criterion
    status: Literal["evaluated", "partial", "not_evaluable", "not_requested"]
    reason: str | None = None


class StelliumHouseReceiptResponse(_Model):
    requested_system: str
    effective_system: str
    fallback: bool
    fallback_reason: str | None
    longitude_frame: Zodiac


class StelliumArcResponse(_Model):
    start: FiniteNumber
    end: FiniteNumber
    span: FiniteNumber
    wraps: bool


class StelliumAssociationResponse(_Model):
    body: str
    longitude: FiniteNumber


class StelliumMatchResponse(_Model):
    id: str
    criterion: Criterion
    sign_index: int | None = None
    sign_name: str | None = None
    house: int | None = None
    arc: StelliumArcResponse | None = None
    associations: list[StelliumAssociationResponse]


class StelliumGroupResponse(_Model):
    id: str
    core_members: list[str]
    core_count: int
    matches: list[StelliumMatchResponse]


class StelliumAnalysisResponse(_Model):
    schema_version: Literal["moira.stellium.v1"]
    input_fingerprint: str
    status: Literal["complete", "partial", "not_evaluable"]
    policy: StelliumPolicyResponse
    context: StelliumContextRequest
    coverage: StelliumCoverageResponse
    evaluations: list[StelliumEvaluationResponse]
    houses: StelliumHouseReceiptResponse | None
    groups: list[StelliumGroupResponse]


__all__ = [
    "StelliumAnalysisRequest",
    "StelliumAnalysisResponse",
    "StelliumHouseSnapshot",
    "StelliumPolicyRequest",
    "StelliumPolicyResponse",
    "StelliumContextRequest",
    "StelliumSelectionRequest",
    "StelliumCoverageResponse",
    "StelliumEvaluationResponse",
    "StelliumHouseReceiptResponse",
    "StelliumArcResponse",
    "StelliumAssociationResponse",
    "StelliumMatchResponse",
    "StelliumGroupResponse",
]
