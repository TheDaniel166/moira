"""Transport models for generic phenomena and solar-condition endpoints."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from moira.constants import Body


PHENOMENA_MAX_ORBITAL_EVENT_SPAN_DAYS = 5000.0
PHENOMENA_MAX_PROXIMITY_SPAN_DAYS = 1200.0
PHENOMENA_MAX_SOLAR_CONDITION_SPAN_DAYS = 1200.0
PHENOMENA_MAX_PROXIMITY_THRESHOLD_DEG = 30.0

PLANET_PHENOMENA_BODIES = (
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
)

ORBITAL_EVENT_BODIES = (
    Body.MERCURY,
    Body.VENUS,
    Body.EARTH,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)

INNER_ELONGATION_BODIES = (Body.MERCURY, Body.VENUS)

PROXIMITY_BODIES = (
    Body.SUN,
    Body.MOON,
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)

SOLAR_CONDITION_EVENT_BODIES = (
    Body.MERCURY,
    Body.VENUS,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)

ADMITTED_ORBITAL_EVENT_KINDS = (
    "greatest_eastern_elongation",
    "greatest_western_elongation",
    "perihelion",
    "aphelion",
)

ADMITTED_SOLAR_CONDITIONS = (
    "cazimi",
    "combust",
    "under_sunbeams",
)

SOLAR_CONDITION_THRESHOLDS_DEG = {
    "cazimi": 17.0 / 60.0,
    "combust": 8.0,
    "under_sunbeams": 17.0,
}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _clean_body(value: str, field_name: str) -> str:
    body = value.strip()
    if not body:
        raise ValueError(f"{field_name} must be non-empty")
    return body


def _validate_body(value: str, field_name: str, admitted: tuple[str, ...]) -> str:
    body = _clean_body(value, field_name)
    if body not in admitted:
        supported = ", ".join(admitted)
        raise ValueError(f"{field_name} must be one of: {supported}")
    return body


def _validate_finite(value: float, field_name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def _validate_jd_window(jd_start: float, jd_end: float, max_span_days: float) -> None:
    if jd_end < jd_start:
        raise ValueError("jd_end must be greater than or equal to jd_start")
    if jd_end - jd_start > max_span_days:
        raise ValueError(f"search span may not exceed {max_span_days:g} days")


class PlanetPhenomenaRequest(_StrictModel):
    body: str
    jd_ut: float

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str) -> str:
        return _validate_body(value, "body", PLANET_PHENOMENA_BODIES)

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        return _validate_finite(value, "jd_ut")


class OrbitalPhenomenaEventsRequest(_StrictModel):
    body: str
    jd_start: float
    jd_end: float
    event_kinds: list[str] | None = Field(default=None, min_length=1)

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str) -> str:
        return _validate_body(value, "body", ORBITAL_EVENT_BODIES)

    @field_validator("jd_start", "jd_end")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        return _validate_finite(value, "JD values")

    @field_validator("event_kinds")
    @classmethod
    def _valid_event_kinds(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        cleaned: list[str] = []
        for event_kind in value:
            canonical = event_kind.strip().lower()
            if not canonical:
                raise ValueError("event_kinds entries must be non-empty")
            if canonical not in ADMITTED_ORBITAL_EVENT_KINDS:
                supported = ", ".join(ADMITTED_ORBITAL_EVENT_KINDS)
                raise ValueError(f"event_kinds entries must be one of: {supported}")
            cleaned.append(canonical)
        return cleaned

    @model_validator(mode="after")
    def _valid_window_and_inner_planets(self):
        _validate_jd_window(
            self.jd_start,
            self.jd_end,
            PHENOMENA_MAX_ORBITAL_EVENT_SPAN_DAYS,
        )
        event_kinds = self.event_kinds or list(default_orbital_event_kinds(self.body))
        if self.body not in INNER_ELONGATION_BODIES:
            invalid = [
                event_kind
                for event_kind in event_kinds
                if event_kind in {"greatest_eastern_elongation", "greatest_western_elongation"}
            ]
            if invalid:
                raise ValueError("greatest elongation events are admitted only for Mercury and Venus")
        return self


class ProximityEventsRequest(_StrictModel):
    body1: str
    body2: str
    jd_start: float
    jd_end: float
    threshold_deg: float

    @field_validator("body1")
    @classmethod
    def _valid_body1(cls, value: str) -> str:
        return _validate_body(value, "body1", PROXIMITY_BODIES)

    @field_validator("body2")
    @classmethod
    def _valid_body2(cls, value: str) -> str:
        return _validate_body(value, "body2", PROXIMITY_BODIES)

    @field_validator("jd_start", "jd_end")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        return _validate_finite(value, "JD values")

    @field_validator("threshold_deg")
    @classmethod
    def _valid_threshold(cls, value: float) -> float:
        _validate_finite(value, "threshold_deg")
        if value <= 0.0:
            raise ValueError("threshold_deg must be greater than 0")
        if value > PHENOMENA_MAX_PROXIMITY_THRESHOLD_DEG:
            raise ValueError(
                f"threshold_deg may not exceed {PHENOMENA_MAX_PROXIMITY_THRESHOLD_DEG:g}"
            )
        return value

    @model_validator(mode="after")
    def _valid_window_and_pair(self):
        _validate_jd_window(
            self.jd_start,
            self.jd_end,
            PHENOMENA_MAX_PROXIMITY_SPAN_DAYS,
        )
        if self.body1 == self.body2:
            raise ValueError("body1 and body2 must differ")
        return self


class SolarConditionInstantRequest(_StrictModel):
    body: str
    jd_ut: float

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str) -> str:
        return _clean_body(value, "body")

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        return _validate_finite(value, "jd_ut")


class SolarConditionEventsRequest(_StrictModel):
    body: str
    jd_start: float
    jd_end: float
    condition: str = "cazimi"

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str) -> str:
        return _validate_body(value, "body", SOLAR_CONDITION_EVENT_BODIES)

    @field_validator("jd_start", "jd_end")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        return _validate_finite(value, "JD values")

    @field_validator("condition")
    @classmethod
    def _valid_condition(cls, value: str) -> str:
        condition = value.strip().lower()
        if condition not in ADMITTED_SOLAR_CONDITIONS:
            supported = ", ".join(ADMITTED_SOLAR_CONDITIONS)
            raise ValueError(f"condition must be one of: {supported}")
        return condition

    @model_validator(mode="after")
    def _valid_window(self):
        _validate_jd_window(
            self.jd_start,
            self.jd_end,
            PHENOMENA_MAX_SOLAR_CONDITION_SPAN_DAYS,
        )
        return self


class PlanetPhenomenaResponse(_StrictModel):
    body: str
    jd_ut: float
    phase_angle_deg: float
    illuminated_fraction: float
    elongation_deg: float
    angular_diameter_arcsec: float
    apparent_magnitude: float


class PhenomenonEventResponse(_StrictModel):
    body: str
    event_kind: str
    label: str
    jd_ut: float
    datetime_utc: str
    value: float
    value_unit: str


class ProximityEventResponse(_StrictModel):
    body1: str
    body2: str
    jd_ut: float
    datetime_utc: str
    threshold_deg: float
    threshold_abs_deg: float
    body1_longitude: float
    body2_longitude: float
    body2_latitude: float
    body2_retrograde: bool
    is_ingress: bool
    label: str | None = None


class SolarConditionTruthResponse(_StrictModel):
    body: str
    jd_ut: float
    present: bool
    condition: str | None = None
    label: str | None = None
    score: int
    distance_from_sun: float | None = None
    distance_unit: str = "degrees"


class GenericPhenomenaProvenanceResponse(_StrictModel):
    source_module: str = "moira.phenomena"
    engine_entrypoint: str
    reader_owner: str
    time_scale: str = "UT_JD"
    product_kind: str
    event_taxonomy: str
    search_performed: bool | None = None
    phase_photometry_source: str | None = None
    admitted_event_kinds: list[str] | None = None
    value_units_by_kind: dict[str, str] | None = None
    search_span_days: float | None = None
    threshold_unit: str | None = None
    event_direction_model: str | None = None
    thresholds_deg: dict[str, float] | None = None
    luminary_policy: str | None = None
    dignity_interpretation: str | None = None
    recommendation_language: str | None = None
    stage_sequence: list[str]


class PlanetPhenomenaEnvelopeResponse(_StrictModel):
    request: PlanetPhenomenaRequest
    phenomena: PlanetPhenomenaResponse
    provenance: GenericPhenomenaProvenanceResponse


class OrbitalPhenomenaEventsEnvelopeResponse(_StrictModel):
    request: OrbitalPhenomenaEventsRequest
    events: list[PhenomenonEventResponse]
    total: int
    provenance: GenericPhenomenaProvenanceResponse


class ProximityEventsEnvelopeResponse(_StrictModel):
    request: ProximityEventsRequest
    events: list[ProximityEventResponse]
    total: int
    provenance: GenericPhenomenaProvenanceResponse


class SolarConditionInstantEnvelopeResponse(_StrictModel):
    request: SolarConditionInstantRequest
    solar_condition: SolarConditionTruthResponse
    provenance: GenericPhenomenaProvenanceResponse


class SolarConditionEventsEnvelopeResponse(_StrictModel):
    request: SolarConditionEventsRequest
    events: list[ProximityEventResponse]
    total: int
    provenance: GenericPhenomenaProvenanceResponse


def default_orbital_event_kinds(body: str) -> tuple[str, ...]:
    if body in INNER_ELONGATION_BODIES:
        return ADMITTED_ORBITAL_EVENT_KINDS
    return ("perihelion", "aphelion")
