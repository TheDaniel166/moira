"""Bounded, explicit evidence packets for the free natal discovery tools."""

from __future__ import annotations

from datetime import datetime
import math
import re
from typing import Literal

from pydantic import Field, field_validator, model_validator

from moira.constants import Body
from moira.sidereal import Ayanamsa

from .common import _StrictModel


class NatalDiscoveryRequest(_StrictModel):
    """Accepted chart geometry, with its original civil instant and frame."""

    dt: str = Field(min_length=1, max_length=64)
    longitudes: dict[str, float] = Field(max_length=10)
    zodiac: Literal["Tropical", "Sidereal"] = "Tropical"
    ayanamsa_system: str | None = None
    time_unknown: bool = Field(default=False, strict=True)

    @field_validator("dt")
    @classmethod
    def _aware_iso(cls, value: str) -> str:
        fraction = re.search(r"[T ]\d{2}:\d{2}:\d{2}[.,](\d+)", value)
        if fraction and any(digit != "0" for digit in fraction.group(1)[6:]):
            raise ValueError("dt supports microsecond precision; nonzero sub-microsecond digits are not admitted")
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("dt must include a UTC offset")
        return value

    @field_validator("longitudes", mode="before")
    @classmethod
    def _no_boolean_longitudes(cls, value):
        if isinstance(value, dict) and any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value.values()):
            raise ValueError("longitudes must be numerical degrees, not booleans or text")
        return value

    @field_validator("longitudes")
    @classmethod
    def _selected_planets(cls, value: dict[str, float]) -> dict[str, float]:
        if any(name not in Body.ALL_PLANETS for name in value):
            raise ValueError("longitudes may contain only selected planets Sun through Pluto")
        if any(not math.isfinite(deg) or not 0.0 <= deg < 360.0 for deg in value.values()):
            raise ValueError("longitudes must be finite degrees in [0, 360)")
        return value

    @model_validator(mode="after")
    def _frame(self):
        if self.zodiac == "Sidereal" and self.ayanamsa_system not in Ayanamsa.ALL:
            raise ValueError("Sidereal geometry requires a supported ayanamsa_system")
        if self.zodiac == "Tropical" and self.ayanamsa_system is not None:
            raise ValueError("Tropical geometry does not use an ayanamsa_system")
        return self


class NatalDiscoverySource(_StrictModel):
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut1: float
    zodiac: Literal["Tropical", "Sidereal"]
    ayanamsa_system: str | None
    time_unknown: bool
    reference_kind: Literal["recorded_time", "noon_reference"]
    longitude_basis: Literal["caller_supplied_accepted_chart"] = "caller_supplied_accepted_chart"


class NatalRulership(_StrictModel):
    sign: str
    ruler: str


class NatalDispositorLink(_StrictModel):
    subject: str
    subject_sign: str
    dispositor: str


class NatalDispositorChain(_StrictModel):
    body: str
    sign: str
    longitude_deg: float
    in_scope: bool
    links: list[NatalDispositorLink]
    visited_subjects: list[str]
    termination: Literal["final_dispositor", "terminal_cycle", "missing_selected_ruler", "out_of_scope"]
    terminal_subjects: list[str]
    cycle_members: list[str]
    missing_ruler: str | None


class NatalDispositorsResponse(_StrictModel):
    source: NatalDiscoverySource
    method: Literal["traditional_domicile_classic_7"] = "traditional_domicile_classic_7"
    rulerships: list[NatalRulership]
    chains: list[NatalDispositorChain]
    final_dispositors: list[str]
    terminal_cycles: list[list[str]]
    excluded_subjects: list[str]


class NatalShapePosition(_StrictModel):
    body: str
    longitude_deg: float


class NatalShapeClassification(_StrictModel):
    shape: str
    occupied_arc_deg: float
    largest_gap_deg: float
    leading_planet: str | None
    handle_planet: str | None
    handle_bodies: list[str]
    clusters: list[list[str]]
    metrics_scope: Literal["all_ten", "nine_planet_bowl_core"]


class NatalShapeGap(_StrictModel):
    from_body: str
    to_body: str
    from_longitude_deg: float
    to_longitude_deg: float
    gap_deg: float
    is_largest: bool


class NatalShapeResponse(_StrictModel):
    source: NatalDiscoverySource
    method: Literal["jones_ten_planets"] = "jones_ten_planets"
    status: Literal["classified", "insufficient_selection"]
    missing_bodies: list[str]
    positions: list[NatalShapePosition]
    classification: NatalShapeClassification | None
    gaps: list[NatalShapeGap]
    classification_note: str


class NatalLunarPhase(_StrictModel):
    angle_deg: float
    state: str
    waxing: bool
    physical_phase_angle_deg: float
    illuminated_fraction: float
    sun_longitude_deg: float
    moon_longitude_deg: float
    coordinate_frame: Literal["geocentric"] = "geocentric"
    state_policy: Literal["quadrant_labels_with_45_degree_boundaries"] = "quadrant_labels_with_45_degree_boundaries"


class NatalLunationEvent(_StrictModel):
    phase: Literal["New Moon", "Full Moon"]
    jd_ut1: float
    datetime_utc: str
    sun_longitude_deg: float
    moon_longitude_deg: float
    ayanamsa_deg: float
    days_before_reference: float
    is_prenatal_syzygy: bool


class NatalLunationContact(_StrictModel):
    event_phase: Literal["New Moon", "Full Moon"]
    event_jd_ut1: float
    body: str
    event_moon_longitude_deg: float
    natal_longitude_deg: float
    aspect: str
    angle_deg: float
    separation_deg: float
    orb_deg: float
    allowed_orb_deg: float


class NatalLunarContactPolicy(_StrictModel):
    method: Literal["engine_major_aspects"] = "engine_major_aspects"
    tier: Literal[0] = 0
    orb_factor: Literal[1] = 1
    aspects: list[str]
    motion: Literal["not_evaluated"] = "not_evaluated"
    point: Literal["event_moon_geocentric_longitude"] = "event_moon_geocentric_longitude"


class NatalSourceConsistency(_StrictModel):
    status: Literal["matched"] = "matched"
    tolerance_deg: float
    maximum_residual_deg: float


class NatalLunarContextResponse(_StrictModel):
    source: NatalDiscoverySource
    status: Literal["calculated", "unknown_time", "missing_luminaries"]
    missing_bodies: list[str]
    phase: NatalLunarPhase | None
    events: list[NatalLunationEvent]
    contacts: list[NatalLunationContact]
    contact_policy: NatalLunarContactPolicy | None
    source_consistency: NatalSourceConsistency | None
