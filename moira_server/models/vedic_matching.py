"""Typed transport for the Wave 4 matching and stellar-chain profiles."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from moira.kp import KPNodeMode, KPProfileId
from moira.kuta import FactorStatus, KutaProfileId

from ._vedic_inputs import CivilDateTime, ClassicalPlanet, FiniteNumber, NodePlanet
from .common import _StrictModel

_SiderealLongitude = Annotated[FiniteNumber, Field(ge=0, lt=360)]


class KutaRequest(_StrictModel):
    """Bride and groom Moon longitudes in the same sidereal frame."""

    profile_id: KutaProfileId
    bride_moon: _SiderealLongitude
    groom_moon: _SiderealLongitude


class KutaProfileResponse(_StrictModel):
    """Named matching lineage and its scoring contract."""

    profile_id: KutaProfileId
    source_reference: str
    maximum_points: int | None
    minimum_agreements: int | None


class KutaMoonResponse(_StrictModel):
    """A participant's Moon classification."""

    longitude: float
    sign_index: int
    nakshatra: str
    nakshatra_index: int
    pada: int


class KutaFactorResponse(_StrictModel):
    """Rule, categories, raw and applied outcome, and any score."""

    name: str
    bride_category: str
    groom_category: str
    raw_status: FactorStatus
    applied_status: FactorStatus
    rule: str
    exception: str | None
    raw_points: float | None
    applied_points: float | None
    maximum_points: int | None


class KutaResponse(_StrictModel):
    """Factors and any source-defined total for one matching profile."""

    profile: KutaProfileResponse
    bride: KutaMoonResponse
    groom: KutaMoonResponse
    factors: tuple[KutaFactorResponse, ...]
    total_points: float | None
    confirmed_agreements: int | None


class KPLongitudeRequest(_StrictModel):
    """One canonical sidereal longitude in the selected KP profile."""

    sidereal_longitude: _SiderealLongitude
    profile_id: KPProfileId = "krishnamurti_moira_placidus"


class KPChartRequest(_StrictModel):
    """Natal instant, observer and explicit lunar node policy."""

    dt: CivilDateTime
    latitude: Annotated[FiniteNumber, Field(ge=-90, le=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    node_mode: KPNodeMode
    profile_id: KPProfileId = "krishnamurti_moira_placidus"


class KPProfileResponse(_StrictModel):
    """The KP calculation and coordinate profile."""

    profile_id: KPProfileId
    source_reference: str
    ayanamsa_system: str
    ayanamsa_mode: Literal["true"]
    house_system: str


class KPSectorResponse(_StrictModel):
    """A half-open interval with endpoints in thirds of an arcsecond."""

    lord: ClassicalPlanet | NodePlanet
    start_ticks: int
    end_ticks: int


class KPLongitudeResponse(_StrictModel):
    """One source-backed KP rulership chain and its exact intervals."""

    profile_id: KPProfileId
    sidereal_longitude: float
    sign_index: int
    sign: KPSectorResponse
    nakshatra_index: int
    nakshatra: str
    star: KPSectorResponse
    sub: KPSectorResponse
    sub_sub: KPSectorResponse


class KPChartResponse(_StrictModel):
    """Planet and cusp chains with chart and availability provenance."""

    profile: KPProfileResponse
    dt_utc: datetime
    jd_ut1: float
    jd_tt: float
    latitude: float
    longitude: float
    ayanamsa_degrees: float
    ayanamsa_path: str
    node_mode: KPNodeMode
    reader_binding: Literal["caller_owned_reader", "active_reader"]
    ephemeris_identity: str
    planets: dict[ClassicalPlanet | NodePlanet, KPLongitudeResponse]
    cusps: tuple[KPLongitudeResponse, ...]
    cusp_status: Literal["available", "unavailable"]
    effective_house_system: str | None
    cusp_unavailable_reason: str | None
