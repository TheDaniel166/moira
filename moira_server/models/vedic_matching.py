"""Typed transport for the Wave 4 matching and stellar-chain profiles."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from moira.daily_panchanga import PanchangaSunriseDefinition
from moira.kp import KPNodeMode, KPProfileId, KPRulingRole, KPSignificatorRank
from moira.kp_period import KPPeriodAssessment, KPPeriodSubject
from moira.kuta import FactorStatus, KutaProfileId

from ._vedic_inputs import CivilDateTime, ClassicalPlanet, FiniteNumber, NodePlanet, VimshottariYearBasis
from .common import _StrictModel
from .daily_panchanga import PanchangaMomentResponse

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


class KPSignificatorsRequest(_StrictModel):
    """Nine graha longitudes and twelve ordered sidereal opening cusps."""

    planet_longitudes: Annotated[
        dict[ClassicalPlanet | NodePlanet, _SiderealLongitude], Field(min_length=9, max_length=9),
    ]
    cusp_longitudes: Annotated[tuple[_SiderealLongitude, ...], Field(min_length=12, max_length=12)]
    profile_id: KPProfileId = "krishnamurti_moira_placidus"


class KPPlanetPlacementResponse(_StrictModel):
    """The graha, sidereal longitude, occupied house and star lord."""

    planet: ClassicalPlanet | NodePlanet
    sidereal_longitude: float
    occupied_house: int
    star_lord: ClassicalPlanet | NodePlanet


class KPSignificatorEvidenceResponse(_StrictModel):
    """Rank and the occupant or cusp owner supporting it."""

    rank: KPSignificatorRank = Field(
        description="1 occupant's star, 2 occupant, 3 cusp owner's star, 4 cusp owner."
    )
    via: ClassicalPlanet | NodePlanet


class KPSignificatorResponse(_StrictModel):
    """The strongest rank with all direct evidence for that graha."""

    planet: ClassicalPlanet | NodePlanet
    strongest_rank: KPSignificatorRank
    evidence: tuple[KPSignificatorEvidenceResponse, ...]


class KPHouseSignificatorsResponse(_StrictModel):
    """One house's opening cusp and direct significators."""

    house: int
    cusp_longitude: float
    cusp_lord: ClassicalPlanet
    significators: tuple[KPSignificatorResponse, ...]


class KPSignificatorsResponse(_StrictModel):
    """Direct KP ranks and the source and placement evidence behind them."""

    profile_id: KPProfileId
    method: Literal["four_direct_ranks"]
    source_reference: str
    placements: tuple[KPPlanetPlacementResponse, ...]
    houses: tuple[KPHouseSignificatorsResponse, ...]


class KPSignificatorChartResponse(_StrictModel):
    """Reader-bound chart with ranked results when its cusps are available."""

    chart: KPChartResponse
    significators: KPSignificatorsResponse | None


class KPRulingPlanetsRequest(_StrictModel):
    """Supplied KP angles and the already resolved sunrise weekday."""

    moon_sidereal_longitude: _SiderealLongitude
    ascendant_sidereal_longitude: _SiderealLongitude
    weekday: Annotated[int, Field(strict=True, ge=0, le=6, description="Monday=0, Sunday=6.")]
    node_longitudes: Annotated[dict[NodePlanet, _SiderealLongitude], Field(min_length=2, max_length=2)] | None = None
    profile_id: KPProfileId = "krishnamurti_moira_placidus"


class KPRulingPlanetsMomentRequest(_StrictModel):
    """Observation instant, observer and site time zone for sunrise ownership."""

    dt: CivilDateTime
    latitude: Annotated[FiniteNumber, Field(ge=-90, le=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    timezone: Annotated[str, Field(min_length=1, max_length=128)]
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    node_mode: KPNodeMode | None = None
    profile_id: KPProfileId = "krishnamurti_moira_placidus"


class KPRulingPlanetRoleResponse(_StrictModel):
    """One of the five direct ruling-planet roles."""

    role: KPRulingRole
    planet: ClassicalPlanet | NodePlanet


class KPRulingNodeAgentResponse(_StrictModel):
    """A node's sign ownership evidence for the selected direct roles."""

    node: NodePlanet
    sidereal_longitude: float
    represented_planet: ClassicalPlanet
    represented_roles: tuple[KPRulingRole, ...]


class KPRulingPlanetsResponse(_StrictModel):
    """Direct roles, distinct planets and optional sign agents."""

    profile_id: KPProfileId
    source_reference: str
    weekday: int | None
    moon: KPLongitudeResponse
    ascendant: KPLongitudeResponse | None
    roles: tuple[KPRulingPlanetRoleResponse, ...]
    ruling_planets: tuple[ClassicalPlanet | NodePlanet, ...]
    node_policy: Literal["none", "reader_vi_sign_agents"]
    node_agents: tuple[KPRulingNodeAgentResponse, ...]


class KPRulingPlanetsMomentResponse(_StrictModel):
    """Ruling planets with observation and sunrise evidence."""

    moment: PanchangaMomentResponse
    timezone: str
    latitude: float
    longitude: float
    jd_tt: float
    ayanamsa_degrees: float
    ayanamsa_path: str
    sunrise_definition: PanchangaSunriseDefinition
    governing_sunrise: PanchangaMomentResponse | None
    weekday_unavailable_reason: Literal["sunrise_absent", "sunrise_ambiguous"] | None
    ascendant_unavailable_reason: Literal["geographic_pole", "ascendant_undefined"] | None
    node_mode: KPNodeMode | None
    reader_binding: Literal["caller_owned_reader", "active_reader"]
    ephemeris_identity: str
    status: Literal["available", "partial"]
    result: KPRulingPlanetsResponse


class KPPeriodInterpretationRequest(KPSignificatorsRequest):
    """Published or supplied natal geometry and an ordered Vimshottari line."""

    period_lords: Annotated[tuple[ClassicalPlanet | NodePlanet, ...], Field(min_length=1, max_length=4)]
    subject: KPPeriodSubject


class KPPeriodInterpretationMomentRequest(_StrictModel):
    """Natal instant, observation instant and canonical period clock choice."""

    natal_dt: CivilDateTime
    current_dt: CivilDateTime
    latitude: Annotated[FiniteNumber, Field(ge=-90, le=90)]
    longitude: Annotated[FiniteNumber, Field(ge=-180, le=180)]
    node_mode: KPNodeMode
    subject: KPPeriodSubject
    levels: Annotated[int, Field(strict=True, ge=1, le=4)] = 3
    year_basis: VimshottariYearBasis | None = None
    profile_id: KPProfileId = "krishnamurti_moira_placidus"


class KPPeriodPlanetHousesResponse(_StrictModel):
    """House occupancy and cusp ownership of a natal graha."""

    planet: ClassicalPlanet | NodePlanet
    occupied_house: int
    owned_houses: tuple[int, ...]


class KPPeriodHouseMatchesResponse(_StrictModel):
    """The supporting and opposing house matches for a selected topic."""

    supporting: tuple[int, ...]
    opposing: tuple[int, ...]


class KPPeriodHouseEvidenceResponse(_StrictModel):
    """Direct evidence connecting the sub lord with a topic house."""

    house: int
    significator: KPSignificatorResponse


class KPPeriodReadingResponse(_StrictModel):
    """A single period lord's interpretation and supporting evidence."""

    level: int
    level_name: str
    period_lord: KPPeriodPlanetHousesResponse
    star_lord: KPPeriodPlanetHousesResponse
    sub_lord: KPPeriodPlanetHousesResponse
    star_matches: KPPeriodHouseMatchesResponse
    sub_matches: KPPeriodHouseMatchesResponse
    sub_evidence: tuple[KPPeriodHouseEvidenceResponse, ...]
    assessment: KPPeriodAssessment


class KPPeriodInterpretationResponse(_StrictModel):
    """The topic's documented houses and each period lord's evidence."""

    profile_id: KPProfileId
    method: Literal["bhatt_direct_house_evidence"]
    source_reference: str
    subject: KPPeriodSubject
    supporting_houses: tuple[int, ...]
    opposing_houses: tuple[int, ...]
    readings: tuple[KPPeriodReadingResponse, ...]


class KPPeriodWindowResponse(_StrictModel):
    """A canonical Vimshottari interval with both clipped and full UT1 bounds."""

    level: int
    level_name: str
    planet: ClassicalPlanet | NodePlanet
    start_jd_ut1: float
    end_jd_ut1: float
    full_start_jd_ut1: float | None
    full_end_jd_ut1: float | None


class KPPeriodInterpretationMomentResponse(_StrictModel):
    """An active Vimshottari line annotated with its natal KP evidence."""

    chart: KPChartResponse
    current_dt_utc: datetime
    current_jd_ut1: float
    year_basis: str
    active_periods: tuple[KPPeriodWindowResponse, ...]
    interpretation: KPPeriodInterpretationResponse | None
