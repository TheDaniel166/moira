"""Strict source-selected solar/yoga and complete sunrise-day transport."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from moira.special_muhurta import SpecialMuhurtaPolicy, special_muhurta_from_solar_times
from ._vedic_inputs import FiniteNumber
from .common import _StrictModel
from .daily_panchanga import PanchangaMomentResponse
from .named_muhurta import NamedMuhurtaPolicyRequest, NamedMuhurtaPolicyResponse, NamedMuhurtaDayRequest, NamedMuhurtaDayResponse


class SpecialMuhurtaPolicyRequest(_StrictModel):
    amrita_basis: Literal["sadhana_amrita_siddhi", "kalaprakasika_amirtha"] = "sadhana_amrita_siddhi"
    godhuli_weekday_rule: Literal["vrindavana_visibility", "geometry_only"] = "vrindavana_visibility"
    godhuli_horizon: Literal["standard_refraction_34_arcmin", "geometric_disc"] = "standard_refraction_34_arcmin"
    ayanamsa_system: Annotated[str, Field(strict=True)] = "Lahiri"
    solar_policy: NamedMuhurtaPolicyRequest = Field(default_factory=NamedMuhurtaPolicyRequest)

    @model_validator(mode="after")
    def _admit(self):
        self.to_engine()
        return self

    def to_engine(self):
        return SpecialMuhurtaPolicy(**self.model_dump(exclude={"solar_policy"}), solar_policy=self.solar_policy.to_engine())


class SpecialMuhurtaSolarRequest(_StrictModel):
    weekday: Annotated[int, Field(strict=True, ge=0, le=6, description="Monday=0, Sunday=6; sunrise-date weekday")]
    sunrise_jd_ut1: FiniteNumber | None = None
    sunset_jd_ut1: FiniteNumber | None = None
    half_set_jd_ut1: FiniteNumber | None = None
    upper_limb_sunset_jd_ut1: FiniteNumber | None = None
    policy: SpecialMuhurtaPolicyRequest = Field(default_factory=SpecialMuhurtaPolicyRequest)

    @model_validator(mode="after")
    def _admit(self):
        special_muhurta_from_solar_times(**self.model_dump(exclude={"policy"}), policy=self.policy.to_engine())
        return self


class MuhurtaYogaRequest(_StrictModel):
    weekday: Annotated[int, Field(strict=True, ge=0, le=6, description="Monday=0, Sunday=6; caller owns sunrise weekday")]
    sun_sidereal_longitude: Annotated[FiniteNumber, Field(ge=0, lt=360)]
    moon_sidereal_longitude: Annotated[FiniteNumber, Field(ge=0, lt=360)]
    policy: SpecialMuhurtaPolicyRequest = Field(default_factory=SpecialMuhurtaPolicyRequest)


class SpecialMuhurtaDayRequest(NamedMuhurtaDayRequest):
    policy: SpecialMuhurtaPolicyRequest = Field(default_factory=SpecialMuhurtaPolicyRequest)


class SpecialMuhurtaPolicyResponse(_StrictModel):
    amrita_basis: str
    godhuli_weekday_rule: str
    godhuli_horizon: str
    ayanamsa_system: str
    solar_policy: NamedMuhurtaPolicyResponse
    godhuli_basis: str
    vijaya_basis: str
    ravi_basis: str
    sarvarthasiddhi_basis: str
    weekday_basis: str
    nakshatra_basis: str
    endpoint_convention: str
    godhuli_semidiameter_arcminutes: float
    activity_suitability: Literal["not_evaluated"]


class SpecialMuhurtaBoundaryResponse(_StrictModel):
    kind: str
    jd_ut1: float
    lower_jd_ut1: float
    upper_jd_ut1: float
    moment: PanchangaMomentResponse | None


class SpecialMuhurtaWindowResponse(_StrictModel):
    start: SpecialMuhurtaBoundaryResponse
    end: SpecialMuhurtaBoundaryResponse
    eligibility: Literal["excluded", "not_excluded_by_selected_rule", "not_evaluated"]
    evidence: tuple[str, ...]


class SpecialMuhurtaResultResponse(_StrictModel):
    name: Literal["Godhuli", "Vijaya", "Amrita Siddhi", "Amirtha", "Ravi Yoga", "Sarvarthasiddhi"]
    basis: str
    citations: tuple[str, ...]
    status: Literal["available", "partial", "unavailable"]
    unavailable_reasons: tuple[str, ...]
    windows: tuple[SpecialMuhurtaWindowResponse, ...]
    activity_suitability: Literal["not_evaluated"]


class SpecialMuhurtaSolarResponse(_StrictModel):
    policy: SpecialMuhurtaPolicyResponse
    weekday: int
    anchors: tuple[SpecialMuhurtaBoundaryResponse, ...]
    results: tuple[SpecialMuhurtaResultResponse, ...]
    anchor_basis: Literal["caller_supplied_ut1"]
    status: Literal["available", "partial", "unavailable"]


class MuhurtaYogaMatchResponse(_StrictModel):
    name: Literal["Amrita Siddhi", "Amirtha", "Ravi Yoga", "Sarvarthasiddhi"]
    basis: str
    citations: tuple[str, ...]
    present: bool
    evidence: tuple[str, ...]
    activity_suitability: Literal["not_evaluated"]


class MuhurtaYogaResponse(_StrictModel):
    policy: SpecialMuhurtaPolicyResponse
    weekday: int
    sun_sidereal_longitude: float
    moon_sidereal_longitude: float
    sun_nakshatra_index: int
    moon_nakshatra_index: int
    sun_nakshatra: str
    moon_nakshatra: str
    inclusive_sun_moon_count: int
    results: tuple[MuhurtaYogaMatchResponse, ...]
    longitude_basis: str


class SpecialMuhurtaDayResponse(_StrictModel):
    policy: SpecialMuhurtaPolicyResponse
    named: NamedMuhurtaDayResponse
    anchors: tuple[SpecialMuhurtaBoundaryResponse, ...]
    results: tuple[SpecialMuhurtaResultResponse, ...]
    transition_bands: tuple[SpecialMuhurtaBoundaryResponse, ...]
    yoga_interval_basis: str
    status: Literal["available", "partial", "unavailable"]
