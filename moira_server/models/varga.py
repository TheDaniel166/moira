"""Transport models for Phase-9 Varga route family (P9-11)."""

from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, field_validator, model_validator
from moira.varga import D60Method, _require_d60_full_point

from .common import REST_BATCH_MAX_ITEMS, _StrictModel
from ._vedic_inputs import ClassicalPlanet, FiniteNumber
from .sidereal_context import SiderealChartBaseRequest, SiderealChartProvenanceResponse


def _full_d60_method(value: D60Method) -> D60Method:
    _require_d60_full_point(value)
    return value


D60FullPointMethod = Annotated[
    Literal[D60Method.HARMONIC, D60Method.PVR_TEXTBOOK_LINEAR, D60Method.CLASSICAL_DERIVED_LINEAR],
    Field(description="Full positions admit harmonic, pvr_textbook_linear (modern composed), or classical_derived_linear (BPHS signs plus Moira's proportional-degree derivation). The derived profile does not claim a direct classical D60 degree prescription. bphs_santhanam_sign is sign-only; use /v1/varga/d60/sign."),
    AfterValidator(_full_d60_method),
]


class D60SignRequest(_StrictModel):
    sidereal_longitude: FiniteNumber
    method: D60Method = D60Method.HARMONIC


class D60SignResponse(_StrictModel):
    longitude: float
    sign_index: int
    sign: str
    sign_symbol: str
    method: D60Method
    position_scope: Literal["sign_only"]
    source_reference: str


VargaSelector = Literal[
    "hora",
    "chaturthamsha",
    "shashthamsha",
    "saptamsa",
    "ashtamsha",
    "navamsa",
    "dashamansa",
    "dwadashamsa",
    "shodashamsha",
    "vimshamsha",
    "chaturvimshamsha",
    "saptavimshamsha",
    "trimshamsa",
    "khavedamsha",
    "akshavedamsha",
    "shashtiamsha",
]


class VargaGenericRequest(_StrictModel):
    sidereal_longitude: float
    divisor: int = Field(ge=1, le=60)
    name: str | None = None

    @field_validator("sidereal_longitude")
    @classmethod
    def _finite_sidereal_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("sidereal_longitude must be finite")
        return value

    @field_validator("name")
    @classmethod
    def _non_empty_name(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("name must be non-empty when supplied")
        return value


class _D60PlacementRequest(_StrictModel):
    d60_method: D60FullPointMethod = D60Method.HARMONIC

    @model_validator(mode="before")
    @classmethod
    def _strict_profile_longitudes(cls, value):
        # Preserve the legacy harmonic transport's coercion contract. The
        # explicitly admitted source profile has strict numeric inputs.
        if isinstance(value, dict) and value.get("d60_method") in (
            D60Method.PVR_TEXTBOOK_LINEAR, D60Method.CLASSICAL_DERIVED_LINEAR,
        ):
            inputs = []
            if "sidereal_longitude" in value:
                inputs.append(value["sidereal_longitude"])
            if isinstance(value.get("longitudes"), dict):
                inputs.extend(value["longitudes"].values())
            for longitude in inputs:
                if isinstance(longitude, bool) or not isinstance(longitude, (int, float)):
                    raise ValueError("source profile longitudes must be finite numbers without coercion")
                try:
                    finite = math.isfinite(longitude)
                except OverflowError:
                    finite = False
                if not finite:
                    raise ValueError("source profile longitudes must be finite")
        return value

    @model_validator(mode="after")
    def _applicable_d60_method(self):
        if self.d60_method is not D60Method.HARMONIC and getattr(self, "varga", "shashtiamsha") != "shashtiamsha":
            raise ValueError("nondefault d60_method applies only to shashtiamsha")
        return self


class VargaNamedRequest(_D60PlacementRequest):
    sidereal_longitude: float
    varga: VargaSelector

    @field_validator("sidereal_longitude")
    @classmethod
    def _finite_sidereal_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("sidereal_longitude must be finite")
        return value


class VargaShodashvargaRequest(_D60PlacementRequest):
    sidereal_longitude: float

    @field_validator("sidereal_longitude")
    @classmethod
    def _finite_sidereal_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("sidereal_longitude must be finite")
        return value


class VargaNamedBatchRequest(_D60PlacementRequest):
    varga: VargaSelector
    longitudes: dict[str, float] = Field(
        min_length=1,
        max_length=REST_BATCH_MAX_ITEMS,
    )

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        _validate_longitude_map(value)
        return value


class VargaShodashvargaBatchRequest(_D60PlacementRequest):
    longitudes: dict[str, float] = Field(
        min_length=1,
        max_length=REST_BATCH_MAX_ITEMS,
    )

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        _validate_longitude_map(value)
        return value


class VargaChartNamedRequest(SiderealChartBaseRequest, _D60PlacementRequest):
    body: str
    varga: VargaSelector

    @field_validator("body")
    @classmethod
    def _non_empty_body(cls, value: str) -> str:
        if not value:
            raise ValueError("body must be non-empty")
        return value


class VargaChartShodashvargaRequest(SiderealChartBaseRequest, _D60PlacementRequest):
    body: str

    @field_validator("body")
    @classmethod
    def _non_empty_body(cls, value: str) -> str:
        if not value:
            raise ValueError("body must be non-empty")
        return value


class VargaChartShodashvargaBatchRequest(SiderealChartBaseRequest, _D60PlacementRequest):
    bodies: list[str] = Field(
        min_length=1,
        max_length=REST_BATCH_MAX_ITEMS,
    )


class VargaPointResponse(_StrictModel):
    varga_name: str
    varga_number: int
    longitude: float
    varga_longitude: float
    sign: str
    sign_symbol: str
    sign_degree: float
    deity: str | None = None
    d60_method: D60FullPointMethod | None = None
    d60_source_references: tuple[str, ...] = ()
    d60_degree_attribution: Literal["generic_harmonic", "modern_composed", "classical_derived"] | None = Field(
        default=None,
        description="Authority category for D60 degrees; classical_derived records Moira's explicit generalisation, not a direct classical D60 degree law. Null for non-D60 or unknown legacy/manual metadata.",
    )


class VargaShodashvargaResponse(_StrictModel):
    sidereal_longitude: float
    vargas: dict[str, VargaPointResponse]


class VargaNamedBatchResponse(_StrictModel):
    varga: str
    results: dict[str, VargaPointResponse]


class VargaShodashvargaBatchResponse(_StrictModel):
    results: dict[str, dict[str, VargaPointResponse]]


class VargaChartNamedResponse(_StrictModel):
    body: str
    varga: str
    result: VargaPointResponse
    provenance: SiderealChartProvenanceResponse


class VargaChartShodashvargaResponse(_StrictModel):
    body: str
    result: VargaShodashvargaResponse
    provenance: SiderealChartProvenanceResponse


class VargaChartShodashvargaBatchResponse(_StrictModel):
    results: dict[str, dict[str, VargaPointResponse]]
    provenance: SiderealChartProvenanceResponse


def _validate_longitude_map(value: dict[str, float]) -> None:
    if not value:
        raise ValueError("longitudes must be non-empty")
    for key, longitude in value.items():
        if not key:
            raise ValueError("longitudes keys must be non-empty")
        if not math.isfinite(longitude):
            raise ValueError("longitudes values must be finite")


VimshopakaGroup = Literal[
    "shadvarga", "saptavarga", "dashavarga", "shodashavarga"
]

_SEVEN_PLANETS = frozenset(
    {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}
)


class VimshopakaRequest(_StrictModel):
    """Vimshopaka Bala over a varga group from sidereal longitudes."""

    sidereal_longitudes: dict[ClassicalPlanet, FiniteNumber]
    group: VimshopakaGroup = "shodashavarga"
    d60_method: D60Method = D60Method.HARMONIC

    @model_validator(mode="after")
    def _method_applies(self) -> "VimshopakaRequest":
        if self.d60_method is not D60Method.HARMONIC and self.group not in ("dashavarga", "shodashavarga"):
            raise ValueError("nondefault d60_method requires a group containing D60")
        return self

    @field_validator("sidereal_longitudes")
    @classmethod
    def _seven_classical_planets(cls, value: dict[str, float]) -> dict[str, float]:
        _validate_longitude_map(value)
        missing = _SEVEN_PLANETS - set(value)
        if missing:
            raise ValueError(
                f"sidereal_longitudes must include all seven classical "
                f"planets; missing: {sorted(missing)}"
            )
        return value


class VimshopakaVargaEntryResponse(_StrictModel):
    division: int
    varga_sign_index: int
    lord: str
    dignity: str
    vishva: float
    weight: float
    points: float


class VimshopakaBalaResponse(_StrictModel):
    planet: str
    group: str
    entries: tuple[VimshopakaVargaEntryResponse, ...]
    total: float
    d60_method: D60Method | None = None
    d60_source_references: tuple[str, ...] = ()


class VimshopakaChartResponse(_StrictModel):
    """All planets' Vimshopaka Bala plus vargottama flags."""

    group: str
    planets: dict[str, VimshopakaBalaResponse]
    vargottama: tuple[str, ...]


__all__ = [
    "D60SignRequest", "D60SignResponse",
    "VargaGenericRequest",
    "VargaChartNamedRequest",
    "VargaChartNamedResponse",
    "VargaChartShodashvargaBatchRequest",
    "VargaChartShodashvargaBatchResponse",
    "VargaChartShodashvargaRequest",
    "VargaChartShodashvargaResponse",
    "VargaNamedBatchRequest",
    "VargaNamedBatchResponse",
    "VargaNamedRequest",
    "VargaPointResponse",
    "VargaSelector",
    "VargaShodashvargaBatchRequest",
    "VargaShodashvargaBatchResponse",
    "VargaShodashvargaRequest",
    "VargaShodashvargaResponse",
    "VimshopakaGroup",
    "VimshopakaRequest",
    "VimshopakaVargaEntryResponse",
    "VimshopakaBalaResponse",
    "VimshopakaChartResponse",
]
