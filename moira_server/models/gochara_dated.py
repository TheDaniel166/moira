"""Strict date-derived Gochar requests and explicit astronomical receipts."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, field_validator, model_validator

from moira.gochara import GocharaPolicy, GocharaCompleteness
from moira.gochara_dated import GocharaDatePolicy, GocharaNatalBavMode
from moira.sidereal import Ayanamsa
from ._vedic_inputs import FiniteNumber, VedicReference, ClassicalPlanet
from .common import _StrictModel
from .gochara import (
    _GocharaView, GocharaPolicyRequest, GocharaPolicyResponse,
    GocharaPositionResponse, GocharaSubsystemProfileResponse,
    GocharaDoctrineOptionResponse,
)

_NamedAyanamsa = Literal[tuple(Ayanamsa.ALL)]


class GocharaBirthLocationRequest(_StrictModel):
    latitude: Annotated[FiniteNumber, Field(gt=-90, lt=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]


class GocharaDatePolicyRequest(_StrictModel):
    ayanamsa_system: _NamedAyanamsa = "Lahiri"
    natal_bav_mode: GocharaNatalBavMode = GocharaNatalBavMode.OMIT
    gochara_policy: GocharaPolicyRequest = Field(default_factory=lambda: GocharaPolicyRequest(
        completeness=GocharaCompleteness.REQUIRE_COMPLETE,
    ))

    @model_validator(mode="after")
    def _admitted_choices(self):
        GocharaDatePolicy(self.ayanamsa_system, self.natal_bav_mode,
                         GocharaPolicy(**self.gochara_policy.model_dump()))
        return self


class _GocharaDatedRequest(_StrictModel):
    birth_location: GocharaBirthLocationRequest | None = None
    policy: GocharaDatePolicyRequest = Field(default_factory=GocharaDatePolicyRequest)

    @model_validator(mode="after")
    def _birth_scope(self):
        compute = self.policy.natal_bav_mode is GocharaNatalBavMode.COMPUTE_RAW
        if compute != (self.birth_location is not None):
            raise ValueError("birth_location is required exactly when natal_bav_mode=compute_raw")
        return self


class GocharaEpochRequest(_GocharaDatedRequest):
    natal_jd_ut1: Annotated[FiniteNumber, Field(ge=-10_000_000, le=10_000_000)]
    transit_jd_ut1: Annotated[FiniteNumber, Field(ge=-10_000_000, le=10_000_000)]


class GocharaDatetimeRequest(_GocharaDatedRequest):
    natal_dt: AwareDatetime
    transit_dt: AwareDatetime

    @field_validator("natal_dt", "transit_dt", mode="before")
    @classmethod
    def _civil_instant(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("civil instants must be timezone-aware datetime strings")
        return value


class GocharaDatePolicyResponse(_GocharaView):
    ayanamsa_system: _NamedAyanamsa
    natal_bav_mode: GocharaNatalBavMode
    gochara_policy: GocharaPolicyResponse
    longitude_origin: Literal["apparent_geocentric"]
    longitude_frame: Literal["true_ecliptic_of_date"]
    ayanamsa_mode: Literal["true"]
    light_time: Literal[True]
    aberration: Literal[True]
    gravitational_deflection: Literal[True]
    nutation: Literal[True]
    selected_options: tuple[GocharaDoctrineOptionResponse, ...]


class GocharaDatedPositionResponse(_GocharaView):
    planet: ClassicalPlanet
    tropical_longitude: float
    ayanamsa_degrees: float
    position: GocharaPositionResponse


class GocharaEpochResponse(_GocharaView):
    jd_ut1: float
    jd_tt: float
    jd_tdb: float
    delta_t_seconds: float
    delta_t_correction_seconds: float
    tdb_minus_tt_seconds: float
    delta_t_source: str
    kernel_label: str
    planetary_ephemeris: str
    lunar_ephemeris: str
    lunar_tidal_acceleration_arcsec_per_cy2: float
    ayanamsa_system: _NamedAyanamsa
    ayanamsa_degrees: float
    ayanamsa_method: Literal["live_star_anchor", "polynomial_true"]
    ayanamsa_anchor: str | None
    tropical_longitudes: tuple[float, ...]
    positions: tuple[GocharaDatedPositionResponse, ...]


class GocharaBirthLocationResponse(_GocharaView):
    latitude: float
    longitude: float


class GocharaDateResponse(_GocharaView):
    natal: GocharaEpochResponse
    transit: GocharaEpochResponse
    policy: GocharaDatePolicyResponse
    birth_location: GocharaBirthLocationResponse | None
    natal_ascendant_tropical: float | None
    natal_ascendant_sidereal: float | None
    natal_sign_indices: tuple[tuple[VedicReference, int], ...]
    bav_source: str | None
    profile: GocharaSubsystemProfileResponse
