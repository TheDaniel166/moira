"""Strict Sayanadi inputs and canonical attributed/status-bearing views."""
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StrictBool, field_validator, model_validator

from moira.avasthas import (
    SayanadiContext, SayanadiGhati, SayanadiName, SayanadiPolicy,
    sayanadi_ghati_from_elapsed,
)
from moira.daily_panchanga import PanchangaSunriseDefinition, _resolve_timezone
from moira.sayanadi_dated import SayanadiBirthPolicy
from ._vedic_inputs import CivilDateTime, FiniteNumber, KnownAyanamsa
from .common import _StrictModel
from .gochara_dated import GocharaEpochResponse

SayanadiPlanet = Literal["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
PositiveOrdinal = Annotated[int, Field(strict=True, ge=1)]


class SayanadiNameRequest(_StrictModel):
    value: Annotated[int, Field(strict=True, ge=1, le=5)] | None = None
    sound: Annotated[str, Field(strict=True, min_length=1, max_length=1)] | None = None

    @model_validator(mode="after")
    def _name(self):
        self.to_engine()
        return self

    def to_engine(self):
        return SayanadiName(value=self.value, sound=self.sound)


class SayanadiOrdinalRequest(_StrictModel):
    kind: Literal["ordinal"]
    ordinal: PositiveOrdinal

    def to_engine(self):
        return SayanadiGhati(self.ordinal)


class SayanadiSecondsRequest(_StrictModel):
    kind: Literal["elapsed_seconds"]
    elapsed_seconds: Annotated[FiniteNumber, Field(ge=0)]

    def to_engine(self):
        return sayanadi_ghati_from_elapsed(elapsed_seconds=self.elapsed_seconds)


class SayanadiGhatiVighatiRequest(_StrictModel):
    kind: Literal["ghati_vighati"]
    whole_ghatis: Annotated[int, Field(strict=True, ge=0)]
    vighatis: Annotated[int, Field(strict=True, ge=0, le=59)]

    def to_engine(self):
        return sayanadi_ghati_from_elapsed(whole_ghatis=self.whole_ghatis, vighatis=self.vighatis)


SayanadiClockRequest = Annotated[
    SayanadiOrdinalRequest | SayanadiSecondsRequest | SayanadiGhatiVighatiRequest,
    Field(discriminator="kind"),
]


class SayanadiPolicyRequest(_StrictModel):
    formulation: Literal["bphs_navamsa_ordinal"] = "bphs_navamsa_ordinal"

    def to_engine(self):
        return SayanadiPolicy(self.formulation)


class SayanadiContextRequest(_StrictModel):
    clock: SayanadiClockRequest
    name: SayanadiNameRequest
    policy: SayanadiPolicyRequest = Field(default_factory=SayanadiPolicyRequest)
    evaluate_nodes: StrictBool = False

    @model_validator(mode="after")
    def _context(self):
        self.to_engine()
        return self

    def to_engine(self):
        return SayanadiContext(self.clock.to_engine(), self.name.to_engine(),
                               self.policy.to_engine(), self.evaluate_nodes)


class SayanadiRequest(_StrictModel):
    planet: SayanadiPlanet
    sidereal_longitudes: dict[SayanadiPlanet, FiniteNumber] = Field(min_length=1, max_length=9)
    lagna_sidereal_lon: FiniteNumber
    context: SayanadiContextRequest

    @model_validator(mode="after")
    def _subject(self):
        if self.planet not in self.sidereal_longitudes or "Moon" not in self.sidereal_longitudes:
            raise ValueError("subject and Moon longitudes are required")
        if self.context.evaluate_nodes:
            raise ValueError("standalone subject is explicit; evaluate_nodes is a chart control")
        return self


class AvasthaDoctrineRequest(_StrictModel):
    deeptadi_source: Literal["bphs_9", "saravali_9", "jataka_parijata_10", "phaladeepika_11"] = "bphs_9"
    relationship_scheme: Literal["compound", "natural"] = "compound"
    vriddha_fraction: Annotated[FiniteNumber, Field(ge=0, le=1)] | None = None


class SayanadiBirthPolicyRequest(_StrictModel):
    ayanamsa_system: KnownAyanamsa = "Lahiri"
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    solver_tolerance_seconds: Annotated[FiniteNumber, Field(ge=0.01, le=1)] = 0.1
    evaluate_nodes: StrictBool = False
    lajjitadi_nodes: StrictBool = False
    sayanadi: SayanadiPolicyRequest = Field(default_factory=SayanadiPolicyRequest)

    def to_engine(self):
        return SayanadiBirthPolicy(**self.model_dump(exclude={"sayanadi"}), sayanadi=self.sayanadi.to_engine())


class AvasthaBirthRequest(_StrictModel):
    birth: CivilDateTime
    latitude: Annotated[FiniteNumber, Field(gt=-90, lt=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    timezone_name: Annotated[str, Field(strict=True, min_length=1, max_length=128)] | None = None
    name: SayanadiNameRequest
    policy: SayanadiBirthPolicyRequest = Field(default_factory=SayanadiBirthPolicyRequest)
    avastha_policy: AvasthaDoctrineRequest = Field(default_factory=AvasthaDoctrineRequest)

    @field_validator("birth")
    @classmethod
    def _adjacent_dates(cls, value):
        if not 2 <= value.year <= 9998:
            raise ValueError("birth year must allow adjacent civil dates [2, 9998]")
        return value

    @field_validator("timezone_name")
    @classmethod
    def _zone(cls, value):
        if value is not None:
            _resolve_timezone(value)
        return value


class _SayanadiView(_StrictModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class SayanadiPolicyResponse(_SayanadiView):
    formulation: Literal["bphs_navamsa_ordinal"]
    source_profile: str
    name_table: str
    partition: str
    state_names: str
    citations: tuple[str, ...]


class SayanadiNameResponse(_SayanadiView):
    value: int | None
    sound: str | None
    resolved_value: int
    basis: Literal["caller_supplied_value", "canonical_devanagari_sound"]


class SayanadiGhatiResponse(_SayanadiView):
    ordinal: int
    basis: Literal["caller_supplied_ordinal", "elapsed_seconds", "elapsed_ghati_vighati", "sunrise_derived_ut1"]
    elapsed_seconds: float | None
    whole_ghatis: int | None
    vighatis: int | None
    rounding: str


class SayanadiContextResponse(_SayanadiView):
    ghati: SayanadiGhatiResponse
    name: SayanadiNameResponse
    policy: SayanadiPolicyResponse
    evaluate_nodes: bool


class SayanadiTraceResponse(_SayanadiView):
    planet: SayanadiPlanet
    planet_longitude: float
    moon_longitude: float
    lagna_longitude: float
    normalized_planet_longitude: float
    normalized_moon_longitude: float
    normalized_lagna_longitude: float
    planet_nakshatra: int
    navamsa_ordinal: int
    moon_nakshatra: int
    lagna_sign: int
    planet_multiplier: int
    planet_addend: int
    total: int
    state_remainder: int
    stage1_remainder: int
    stage2_remainder: int
    context: SayanadiContextResponse


class SayanadiEffectProvenanceResponse(_SayanadiView):
    catalogue: str
    audit_status: Literal["not_source_certified"]
    conditions_evaluated: Literal[False]


class SayanadiResponse(_SayanadiView):
    planet: SayanadiPlanet
    state: str
    substate: Literal["Drishti", "Cheshta", "Vicheshta"]
    avastha_index: int
    effect: str
    trace: SayanadiTraceResponse | None
    effect_provenance: SayanadiEffectProvenanceResponse | None


class SayanadiBirthPolicyResponse(_SayanadiView):
    ayanamsa_system: str
    sunrise_definition: PanchangaSunriseDefinition
    solver_tolerance_seconds: float
    evaluate_nodes: bool
    lajjitadi_nodes: bool
    sayanadi: SayanadiPolicyResponse
    node_mode: str
    longitude_frame: str
    ayanamsa_mode: str
    horizon_model: str
    clock_basis: str
    maximum_civil_dates: int


class SayanadiMomentResponse(_SayanadiView):
    jd_ut1: float
    utc: CivilDateTime
    local: CivilDateTime


class SayanadiSunriseBracketResponse(_SayanadiView):
    moment: SayanadiMomentResponse
    lower_jd_ut1: float
    upper_jd_ut1: float
    bracket_width_seconds: float


class AvasthaDoctrineResponse(_SayanadiView):
    deeptadi_source: str
    relationship_scheme: str
    vriddha_fraction: float | None


class AvasthaBirthEvidenceResponse(_SayanadiView):
    status: Literal["evaluated", "unavailable"]
    unavailable_reasons: tuple[str, ...]
    birth: CivilDateTime
    birth_jd_ut1: float
    latitude: float
    longitude: float
    timezone: str
    name: SayanadiNameResponse
    policy: SayanadiBirthPolicyResponse
    avastha_policy: AvasthaDoctrineResponse
    reader_binding: str
    sunrise: SayanadiSunriseBracketResponse | None
    next_sunrise: SayanadiSunriseBracketResponse | None
    elapsed_seconds_lower: float | None
    elapsed_seconds_upper: float | None
    ghati_candidates: tuple[int, ...]
    epoch: GocharaEpochResponse | None
    lagna_tropical: float | None
    lagna_sidereal: float | None
    node_longitudes: dict[str, float]
