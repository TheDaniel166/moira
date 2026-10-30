"""Transport models for P-GAP-05 sidereal and Nakshatra utility routes."""

from __future__ import annotations

import math
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from moira.sidereal import (
    Ayanamsa,
    GrahalaghavaAyanamsa,
    PolarStarAyanamsa,
    SuryaSiddhantaLibrationAyanamsa,
    SuryadevaTrepidationAyanamsa,
)


SIDEREAL_NAKSHATRA_MAX_BULK_POSITIONS = 64
SIDEREAL_AYANAMSA_MODES = ("true", "mean")
SIDEREAL_CONVERSION_DIRECTIONS = ("tropical_to_sidereal", "sidereal_to_tropical")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _validate_finite(value: float, field_name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def _validate_ayanamsa_system(value: str) -> str:
    system = value.strip()
    if not system:
        raise ValueError("ayanamsa_system must be non-empty")
    if system not in Ayanamsa.ALL:
        raise ValueError(f"ayanamsa_system must be one of {list(Ayanamsa.ALL)!r}")
    return system


class GrahalaghavaSelection(_StrictModel):
    """Grahalāghava 2.7 formula (AYANAMSA_DOCTRINE_STANDARD.md, Section 2.2)."""

    family: Literal["grahalaghava"]
    year_convention: Literal["current", "elapsed"] = "current"
    stepping: Literal["annual", "continuous"] = "annual"

    def to_engine(self) -> GrahalaghavaAyanamsa:
        return GrahalaghavaAyanamsa(self.year_convention, self.stepping)


class PolarStarSelection(_StrictModel):
    """A junction star at its textual polar longitude (Section 2.3)."""

    family: Literal["polar_star"]
    source: Literal["surya_siddhanta", "grahalaghava"]
    nakshatra: Literal["ashvini", "pushya", "chitra", "mula", "revati"]
    star_product: Literal["astrometric", "apparent"] = "astrometric"

    def to_engine(self) -> PolarStarAyanamsa:
        return PolarStarAyanamsa(self.source, self.nakshatra, self.star_product)


class SuryaSiddhantaLibrationSelection(_StrictModel):
    """Sūrya Siddhānta iii.9–10 libration reconstruction (Section 2.4)."""

    family: Literal["surya_siddhanta_libration"]
    cycles_per_mahayuga: Literal[600, 30] = 600

    def to_engine(self) -> SuryaSiddhantaLibrationAyanamsa:
        return SuryaSiddhantaLibrationAyanamsa(self.cycles_per_mahayuga)


class SuryadevaTrepidationSelection(_StrictModel):
    """The ±24° rule quoted by Sūryadeva (Section 2.4)."""

    family: Literal["suryadeva_trepidation"]

    def to_engine(self) -> SuryadevaTrepidationAyanamsa:
        return SuryadevaTrepidationAyanamsa()


AyanamsaDoctrineSelection = Annotated[
    Union[
        GrahalaghavaSelection,
        PolarStarSelection,
        SuryaSiddhantaLibrationSelection,
        SuryadevaTrepidationSelection,
    ],
    Field(discriminator="family"),
]


class _AyanamsaChoice(_StrictModel):
    """A named ``ayanamsa_system`` or, instead, a doctrinal ``ayanamsa_doctrine``."""

    ayanamsa_system: str = Ayanamsa.LAHIRI
    ayanamsa_doctrine: AyanamsaDoctrineSelection | None = None

    @field_validator("ayanamsa_system")
    @classmethod
    def _valid_ayanamsa_system(cls, value: str) -> str:
        return _validate_ayanamsa_system(value)

    @model_validator(mode="after")
    def _one_ayanamsa(self):
        if self.ayanamsa_doctrine is not None and "ayanamsa_system" in self.model_fields_set:
            raise ValueError("give either ayanamsa_system or ayanamsa_doctrine, not both")
        return self

    def engine_system(self):
        """The engine system: a typed doctrinal value or the named system."""
        if self.ayanamsa_doctrine is not None:
            return self.ayanamsa_doctrine.to_engine()
        return self.ayanamsa_system

    def system_name(self) -> str:
        if self.ayanamsa_doctrine is not None:
            return self.ayanamsa_doctrine.to_engine().name
        return self.ayanamsa_system


def _validate_mode(value: str) -> str:
    mode = value.strip().lower()
    if mode not in SIDEREAL_AYANAMSA_MODES:
        raise ValueError("mode must be 'true' or 'mean'")
    return mode


class SiderealAyanamsaRequest(_AyanamsaChoice):
    jd_ut: float
    mode: Literal["true", "mean"] = "true"

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        return _validate_finite(value, "jd_ut")

    @field_validator("mode", mode="before")
    @classmethod
    def _valid_mode(cls, value: str) -> str:
        return _validate_mode(value)


class SiderealConversionRequest(SiderealAyanamsaRequest):
    longitude_deg: float
    direction: Literal["tropical_to_sidereal", "sidereal_to_tropical"]

    @field_validator("longitude_deg")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        return _validate_finite(value, "longitude_deg")

    @field_validator("direction", mode="before")
    @classmethod
    def _valid_direction(cls, value: str) -> str:
        direction = value.strip()
        if direction not in SIDEREAL_CONVERSION_DIRECTIONS:
            raise ValueError(
                "direction must be 'tropical_to_sidereal' or 'sidereal_to_tropical'"
            )
        return direction


class SiderealNakshatraPositionRequest(_AyanamsaChoice):
    tropical_longitude_deg: float
    jd_ut: float

    @field_validator("tropical_longitude_deg")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        return _validate_finite(value, "tropical_longitude_deg")

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        return _validate_finite(value, "jd_ut")


class SiderealNakshatraBulkRequest(_AyanamsaChoice):
    positions: dict[str, float] = Field(
        min_length=1,
        max_length=SIDEREAL_NAKSHATRA_MAX_BULK_POSITIONS,
    )
    jd_ut: float

    @field_validator("positions", mode="before")
    @classmethod
    def _valid_positions(cls, value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            raise ValueError("positions must be a mapping")
        if not value:
            raise ValueError("positions must be non-empty")
        if len(value) > SIDEREAL_NAKSHATRA_MAX_BULK_POSITIONS:
            raise ValueError(
                f"positions may not contain more than {SIDEREAL_NAKSHATRA_MAX_BULK_POSITIONS} entries"
            )

        cleaned: dict[str, float] = {}
        for raw_name, raw_longitude in value.items():
            if not isinstance(raw_name, str):
                raise ValueError("position names must be strings")
            name = raw_name.strip()
            if not name:
                raise ValueError("position names must be non-empty")
            if name in cleaned:
                raise ValueError("position names must be unique after trimming")
            try:
                longitude = float(raw_longitude)
            except (TypeError, ValueError) as exc:
                raise ValueError("position longitude values must be finite") from exc
            _validate_finite(longitude, "position longitude values")
            cleaned[name] = longitude
        return cleaned

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        return _validate_finite(value, "jd_ut")


class SiderealUtilityProvenanceResponse(_StrictModel):
    source_module: str = "moira.sidereal"
    engine_entrypoint: str
    time_scale: str = "UT_JD"
    product_kind: str
    ayanamsa_system: str | None = None
    ayanamsa_mode: str | None = None
    registry_owner: str | None = None
    reference_epoch: str | None = None
    user_defined_ayanamsa: str | None = None
    jd_policy: str | None = None
    mode_policy: str | None = None
    star_anchor_policy: str | None = None
    longitude_input_policy: str | None = None
    conversion_direction: str | None = None
    taxonomy: str | None = None
    span_deg: float | None = None
    pada_span_deg: float | None = None
    interpretation: str | None = None
    panchanga_judgement: str | None = None
    stage_sequence: list[str]


class AyanamsaComputationTruthResponse(_StrictModel):
    jd_ut: float | None
    jd_tt: float
    ayanamsa_system: str
    system_kind: str
    requested_mode: str
    effective_path: str
    ayanamsa_unwrapped_deg: float
    ayanamsa_deg: float
    reference_value_j2000_deg: float | None
    precession_longitude_deg: float | None
    drift_correction_deg: float | None
    nutation_longitude_deg: float | None
    anchor_star: str | None
    anchor_target_sidereal_longitude_deg: float | None
    anchor_tropical_longitude_deg: float | None
    anchor_source_mode: str | None
    fallback_applied: bool
    fallback_reason: str | None
    input_timescale: str
    computation_timescale: str
    output_normalization: str
    # "astrometric" or "apparent" for a live star anchor, else null.
    anchor_product: str | None = None
    # Provenance (AYANAMSA_DOCTRINE_STANDARD.md): family, layer, and the
    # doctrinal family's resolved parameters.
    doctrine_family: str | None = None
    doctrine_layer: str | None = None
    doctrine_terms: dict[str, float | int | str] = Field(default_factory=dict)


class SiderealLongitudeConversionTruthResponse(_StrictModel):
    direction: str
    input_longitude_deg: float
    normalized_input_longitude_deg: float
    output_longitude_deg: float
    source_frame: str
    target_frame: str
    ayanamsa: AyanamsaComputationTruthResponse


class NakshatraComputationTruthResponse(_StrictModel):
    tropical_longitude_deg: float
    normalized_tropical_longitude_deg: float
    sidereal_longitude_deg: float
    nakshatra_index: int
    sector_start_longitude_deg: float
    sector_end_longitude_deg: float
    pada: int
    ayanamsa: AyanamsaComputationTruthResponse
    taxonomy: str
    sector_boundary_policy: str
    interpretation: str


class TextualAttestationResponse(_StrictModel):
    source: str
    date: str
    value_deg: float
    coordinate: str
    latitude_deg: float | None = None
    note: str | None = None


class AyanamsaDoctrineResponse(_StrictModel):
    """What a system holds fixed and where its anchor value comes from."""

    system: str
    family: str
    layer: str
    definition: str
    anchor_star: str | None = None
    anchor_identification: str | None = None
    anchor_target_deg: float | None = None
    anchor_coordinate: str | None = None
    anchor_product: str | None = None
    identification_certainty: str | None = None
    attestations: list[TextualAttestationResponse] = Field(default_factory=list)
    zero_epoch: str | None = None
    sources: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class AyanamsaSystemResponse(_StrictModel):
    system: str
    reference_value_j2000_deg: float
    is_star_anchored: bool
    default_mode: str = "true"
    supported_modes: list[str]
    doctrine: AyanamsaDoctrineResponse


class AyanamsaSystemsEnvelopeResponse(_StrictModel):
    systems: list[AyanamsaSystemResponse]
    total: int
    provenance: SiderealUtilityProvenanceResponse


class SiderealAyanamsaResponse(_StrictModel):
    jd_ut: float
    ayanamsa_system: str
    mode: str
    ayanamsa_deg: float
    value_range: list[float | str]
    provenance: SiderealUtilityProvenanceResponse
    computation_truth: AyanamsaComputationTruthResponse
    doctrine: AyanamsaDoctrineResponse | None = None


class SiderealConversionResponse(_StrictModel):
    direction: str
    jd_ut: float
    ayanamsa_system: str
    mode: str
    input_longitude_deg: float
    output_longitude_deg: float
    ayanamsa_deg: float
    longitude_range: list[float | str]
    provenance: SiderealUtilityProvenanceResponse
    computation_truth: SiderealLongitudeConversionTruthResponse


class SiderealNakshatraPositionResponse(_StrictModel):
    name: str | None = None
    tropical_longitude_deg: float
    jd_ut: float
    ayanamsa_system: str
    nakshatra: str
    nakshatra_index: int
    nakshatra_number: int
    nakshatra_lord: str
    pada: int
    degrees_in: float
    degrees_remaining: float
    sidereal_longitude_deg: float
    computation_truth: NakshatraComputationTruthResponse


class SiderealNakshatraPositionEnvelopeResponse(_StrictModel):
    request: SiderealNakshatraPositionRequest
    position: SiderealNakshatraPositionResponse
    provenance: SiderealUtilityProvenanceResponse


class SiderealNakshatraBulkEnvelopeResponse(_StrictModel):
    request: SiderealNakshatraBulkRequest
    positions: list[SiderealNakshatraPositionResponse]
    total: int
    provenance: SiderealUtilityProvenanceResponse
