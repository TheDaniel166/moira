"""Transport models for station, void-of-course, and rise-set endpoints."""

from __future__ import annotations

from math import ceil, isfinite
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_OCCULTATION_TOPOLOGY_MAX_STEP_DAYS = 0.25
_OCCULTATION_TOPOLOGY_MAX_SPAN_DAYS = 400.0
_OCCULTATION_TOPOLOGY_MAX_SCAN_CELLS = 4096
_WGS84_EQUATORIAL_RADIUS_KM = 6378.137
_WGS84_FLATTENING = 1.0 / 298.257223563
_OCCULTATION_TOPOLOGY_MIN_OBSERVER_ELEV_M = (
    -_WGS84_EQUATORIAL_RADIUS_KM * (1.0 - _WGS84_FLATTENING) * 1000.0
)


def _validate_occultation_topology_search_window(
    jd_start: float,
    jd_end: float,
    step_days: float,
) -> None:
    span = jd_end - jd_start
    if span <= 0.0:
        raise ValueError("jd_end must be greater than jd_start")
    if span > _OCCULTATION_TOPOLOGY_MAX_SPAN_DAYS:
        raise ValueError("occultation topology search span must not exceed 400 days")
    if step_days * _OCCULTATION_TOPOLOGY_MAX_SCAN_CELLS < span:
        raise ValueError(
            "occultation topology search must not exceed 4096 coarse cells"
        )
    segment_count = ceil(span / step_days)
    previous = jd_start
    for index in range(1, segment_count):
        candidate = jd_start + index * step_days
        if not previous < candidate < jd_end:
            raise ValueError(
                "step_days does not produce a strictly advancing Julian-Day lattice"
            )
        previous = candidate


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventInstantResponse(_StrictModel):
    jd_ut: float
    datetime_utc: str


class StationSearchRequest(_StrictModel):
    body: str
    jd_start: float
    jd_end: float
    step_days: float | None = None


class NextStationRequest(_StrictModel):
    body: str
    jd_start: float
    max_days: float = 400.0
    step_days: float | None = None


class StationStateRequest(_StrictModel):
    body: str
    jd_ut: float


class RetrogradePeriodSearchRequest(_StrictModel):
    body: str
    jd_start: float
    jd_end: float
    step_days: float | None = None


class StationEventResponse(_StrictModel):
    body: str
    station_type: str
    jd_ut: float
    datetime_utc: str
    longitude: float


class StationSearchResponse(_StrictModel):
    events: list[StationEventResponse]


class StationStateResponse(_StrictModel):
    body: str
    jd_ut: float
    is_retrograde: bool


class RetrogradePeriodResponse(_StrictModel):
    start: EventInstantResponse
    end: EventInstantResponse


class RetrogradePeriodSearchResponse(_StrictModel):
    periods: list[RetrogradePeriodResponse]


class VoidOfCourseRequest(_StrictModel):
    jd_ut: float
    modern: bool = False


class VoidOfCourseRangeRequest(_StrictModel):
    jd_start: float
    jd_end: float
    modern: bool = False


class LastAspectResponse(_StrictModel):
    body: str
    aspect_name: str
    angle: float
    jd_exact: float
    datetime_utc: str


class VoidOfCourseWindowResponse(_StrictModel):
    moon_sign: str
    moon_sign_next: str
    jd_voc_start: float
    voc_start_datetime_utc: str
    jd_voc_end: float
    voc_end_datetime_utc: str
    last_aspect: LastAspectResponse | None = None
    duration_hours: float
    is_long: bool


class VoidOfCourseRangeResponse(_StrictModel):
    windows: list[VoidOfCourseWindowResponse]


class VoidOfCourseStateResponse(_StrictModel):
    jd_ut: float
    modern: bool
    is_void_of_course: bool


class RiseSetPolicyRequest(_StrictModel):
    disc_reference: str = "limb"
    fixed_disc_size: bool = False
    hindu_rising: bool = False
    refraction: bool = True
    horizon_altitude: float | None = None


class RiseSetPhenomenaRequest(_StrictModel):
    body: str
    jd_start: float
    lat: float
    lon: float
    altitude: float | None = None
    policy: RiseSetPolicyRequest | None = None


class RiseSetTransitRequest(_StrictModel):
    body: str
    jd_day: float
    lat: float
    lon: float
    upper: bool = True


class TwilightRequest(_StrictModel):
    jd_day: float
    lat: float
    lon: float


class RiseSetPhenomenaResponse(_StrictModel):
    rise: EventInstantResponse | None = None
    set: EventInstantResponse | None = None
    transit: EventInstantResponse | None = None
    anti_transit: EventInstantResponse | None = None


class TwilightTimesResponse(_StrictModel):
    jd_day: float
    astronomical_dawn: EventInstantResponse | None = None
    nautical_dawn: EventInstantResponse | None = None
    civil_dawn: EventInstantResponse | None = None
    sunrise: EventInstantResponse | None = None
    sunset: EventInstantResponse | None = None
    civil_dusk: EventInstantResponse | None = None
    nautical_dusk: EventInstantResponse | None = None
    astronomical_dusk: EventInstantResponse | None = None


class EclipseSearchRequest(_StrictModel):
    jd_start: float
    kind: str = "any"


class SolarEclipseLocationRequest(_StrictModel):
    jd_start: float
    latitude: float
    longitude: float
    elevation_m: float = 0.0
    kind: str = "any"
    max_lunations: int = 360


class LunarEclipseLocationRequest(_StrictModel):
    jd_start: float
    latitude: float
    longitude: float
    elevation_m: float = 0.0
    kind: str = "any"
    mode: str = "native"


class EclipseDataResponse(_StrictModel):
    eclipse_type: str
    is_eclipse_season: bool
    is_solar_eclipse: bool
    is_lunar_eclipse: bool
    eclipse_magnitude: float
    sun_longitude: float
    moon_longitude: float
    node_longitude: float
    moon_latitude: float
    sun_node_distance: float
    angular_separation_3d: float
    saros_index: float
    metonic_year: float
    metonic_is_reset: bool


class EclipseEventResponse(_StrictModel):
    jd_ut: float
    datetime_utc: str
    data: EclipseDataResponse


class LocalContactCircumstancesResponse(_StrictModel):
    jd_ut: float
    datetime_utc: str
    azimuth: float
    altitude: float
    visible: bool


class SolarBodyCircumstancesResponse(_StrictModel):
    azimuth: float
    altitude: float
    visible: bool


class SolarEclipseLocalCircumstancesResponse(_StrictModel):
    event: EclipseEventResponse
    latitude: float
    longitude: float
    elevation_m: float
    sun: SolarBodyCircumstancesResponse
    moon: SolarBodyCircumstancesResponse
    topocentric_separation_deg: float
    topocentric_overlap: bool


class LunarEclipseLocalCircumstancesResponse(_StrictModel):
    mode: str
    source_model: str
    canon_method: str | None = None
    event: EclipseEventResponse
    latitude: float
    longitude: float
    elevation_m: float
    greatest: LocalContactCircumstancesResponse
    p1: LocalContactCircumstancesResponse | None = None
    u1: LocalContactCircumstancesResponse | None = None
    u2: LocalContactCircumstancesResponse | None = None
    u3: LocalContactCircumstancesResponse | None = None
    u4: LocalContactCircumstancesResponse | None = None
    p4: LocalContactCircumstancesResponse | None = None


_MIN_COMPUTATIONAL_JD = -40_000_000.0
_MAX_COMPUTATIONAL_JD = 40_000_000.0


LunarEclipseSearchKind = Literal["any", "total", "partial", "penumbral"]
LunarEclipseAnalysisModeValue = Literal["native", "nasa_compat"]
LunarEclipseVisibilityContactKindValue = Literal[
    "p1", "u1", "u2", "greatest", "u3", "u4", "p4"
]


class LunarEclipseGlobalCircumstancesRequest(_StrictModel):
    jd_start: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )
    kind: LunarEclipseSearchKind = "any"
    backward: bool = False
    mode: LunarEclipseAnalysisModeValue = "native"

    @field_validator("jd_start", mode="before")
    @classmethod
    def _valid_jd_start(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("jd_start must be an integer or float")
        parsed = float(value)
        if not isfinite(parsed):
            raise ValueError("jd_start must be finite")
        return parsed

    @field_validator("backward", mode="before")
    @classmethod
    def _valid_backward(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("backward must be a boolean")
        return value


class EclipseEpochResponse(_StrictModel):
    jd_tt: float = Field(allow_inf_nan=False)
    jd_ut1: float = Field(allow_inf_nan=False)
    delta_t_seconds: float = Field(allow_inf_nan=False)
    time_policy: str = Field(min_length=1)


class EclipseGeocentricBodyStateResponse(_StrictModel):
    body: Literal["Sun", "Moon"]
    right_ascension_deg: float = Field(ge=0.0, lt=360.0, allow_inf_nan=False)
    declination_deg: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    distance_km: float = Field(gt=0.0, allow_inf_nan=False)
    semidiameter_deg: float = Field(gt=0.0, lt=90.0, allow_inf_nan=False)
    horizontal_parallax_deg: float = Field(
        gt=0.0,
        lt=90.0,
        allow_inf_nan=False,
    )
    origin: Literal["earth_center"]
    frame: Literal["true_equator_and_equinox_of_date"]
    correction_policy: str = Field(min_length=1)


class LunarEclipseShadowStateResponse(_StrictModel):
    gamma_earth_radii: float = Field(allow_inf_nan=False)
    axis_distance_km: float = Field(ge=0.0, allow_inf_nan=False)
    moon_radius_earth_radii: float = Field(gt=0.0, allow_inf_nan=False)
    umbra_radius_earth_radii: float = Field(gt=0.0, allow_inf_nan=False)
    penumbra_radius_earth_radii: float = Field(gt=0.0, allow_inf_nan=False)
    umbral_magnitude: float = Field(allow_inf_nan=False)
    penumbral_magnitude: float = Field(allow_inf_nan=False)
    shadow_model: str = Field(min_length=1)


class LunarEclipseGlobalCircumstancesResponse(_StrictModel):
    mode: LunarEclipseAnalysisModeValue
    source_model: str = Field(min_length=1)
    canon_method: str | None = None
    event: EclipseEventResponse
    greatest: EclipseEpochResponse
    sun: EclipseGeocentricBodyStateResponse
    moon: EclipseGeocentricBodyStateResponse
    shadow: LunarEclipseShadowStateResponse
    penumbral_duration_seconds: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    partial_duration_seconds: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    total_duration_seconds: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    ephemeris: Literal["DE-0441LE-0441"]


class LunarEclipseVisibilityRequest(_StrictModel):
    jd_start: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )
    kind: LunarEclipseSearchKind = "any"
    backward: bool = False
    mode: LunarEclipseAnalysisModeValue = "native"
    sample_count: int = Field(default=181, ge=9, le=721)

    @field_validator("jd_start", mode="before")
    @classmethod
    def _valid_jd_start(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("jd_start must be an integer or float")
        parsed = float(value)
        if not isfinite(parsed):
            raise ValueError("jd_start must be finite")
        return parsed

    @field_validator("backward", mode="before")
    @classmethod
    def _valid_backward(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("backward must be a boolean")
        return value

    @field_validator("sample_count", mode="before")
    @classmethod
    def _valid_sample_count(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("sample_count must be an integer")
        return value


class LunarEclipseVisibilityPointResponse(_StrictModel):
    latitude_deg: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude_deg: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)


class LunarEclipseVisibilityLimitResponse(_StrictModel):
    contact: LunarEclipseVisibilityContactKindValue
    jd_ut: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )
    datetime_utc: str
    sublunar_point: LunarEclipseVisibilityPointResponse
    points: list[LunarEclipseVisibilityPointResponse] = Field(min_length=9)


class LunarEclipseVisibilityMapResponse(_StrictModel):
    mode: LunarEclipseAnalysisModeValue
    source_model: str
    canon_method: str | None = None
    event: EclipseEventResponse
    limits: list[LunarEclipseVisibilityLimitResponse] = Field(min_length=3)
    ephemeris: Literal["DE-0441LE-0441"]
    surface_model: Literal["WGS84_ZERO_ELEVATION"]
    horizon_model: Literal["RETARDED_GEOMETRIC_MOON_CENTER"]
    time_scale: Literal["UT1"]
    atmospheric_refraction: Literal[False]
    visible_side: Literal["CONTAINS_SUBLUNAR_POINT"]


class SolarEclipsePathRequest(_StrictModel):
    jd_start: float
    kind: str = "any"
    backward: bool = False
    sample_count: int = 9


class SolarEclipsePathResponse(_StrictModel):
    central_line_lats: list[float]
    central_line_lons: list[float]
    umbral_width_km: float
    duration_at_max_s: float
    max_eclipse_lat: float
    max_eclipse_lon: float
    eclipse_data: EclipseDataResponse


SolarEclipseSearchKind = Literal[
    "any", "total", "annular", "partial", "central", "hybrid"
]
SolarEclipseFootprintBoundaryKindValue = Literal[
    "penumbral_north", "penumbral_south", "sunrise", "sunset"
]
SolarEclipsePenumbralContactKindValue = Literal["p1", "p2", "p3", "p4"]
SolarEclipseFootprintTopologyValue = Literal[
    "one_limit_connected", "two_limit_two_loop"
]

class SolarEclipseFootprintRequest(_StrictModel):
    jd_start: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )
    kind: SolarEclipseSearchKind = "any"
    backward: bool = False
    sample_count: int = Field(default=181, ge=9, le=721)

    @field_validator("jd_start", mode="before")
    @classmethod
    def _valid_jd_start(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("jd_start must be an integer or float")
        parsed = float(value)
        if not isfinite(parsed):
            raise ValueError("jd_start must be finite")
        return parsed

    @field_validator("backward", mode="before")
    @classmethod
    def _valid_backward(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("backward must be a boolean")
        return value

    @field_validator("sample_count", mode="before")
    @classmethod
    def _valid_sample_count(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("sample_count must be an integer")
        return value


class SolarEclipseFootprintPointResponse(_StrictModel):
    jd_ut: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )
    datetime_utc: str
    latitude_deg: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude_deg: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)


class SolarEclipsePenumbralContactResponse(_StrictModel):
    kind: SolarEclipsePenumbralContactKindValue
    point: SolarEclipseFootprintPointResponse


class SolarEclipseFootprintContactsResponse(_StrictModel):
    p1: SolarEclipsePenumbralContactResponse
    p2: SolarEclipsePenumbralContactResponse | None = None
    p3: SolarEclipsePenumbralContactResponse | None = None
    p4: SolarEclipsePenumbralContactResponse


class SolarEclipseLimitTrackResponse(_StrictModel):
    kind: SolarEclipseFootprintBoundaryKindValue
    component_id: int = Field(ge=0)
    segment_id: int = Field(ge=0)
    points: list[SolarEclipseFootprintPointResponse] = Field(min_length=2)


class SolarEclipseVisibilityFootprintResponse(_StrictModel):
    event: EclipseEventResponse
    greatest: SolarEclipseFootprintPointResponse
    topology: SolarEclipseFootprintTopologyValue
    contacts: SolarEclipseFootprintContactsResponse
    tracks: list[SolarEclipseLimitTrackResponse] = Field(min_length=3)
    ephemeris: Literal["DE-0441LE-0441"]
    surface_model: Literal["WGS84_ZERO_ELEVATION"]
    limb_model: Literal["SPHERICAL_MEAN_LIMB"]
    time_scale: Literal["UT1"]
    atmospheric_refraction: Literal[False]


class SolarEclipseGlobalCircumstancesRequest(_StrictModel):
    jd_start: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )
    kind: SolarEclipseSearchKind = "any"
    backward: bool = False

    @field_validator("jd_start", mode="before")
    @classmethod
    def _valid_jd_start(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("jd_start must be an integer or float")
        parsed = float(value)
        if not isfinite(parsed):
            raise ValueError("jd_start must be finite")
        return parsed

    @field_validator("backward", mode="before")
    @classmethod
    def _valid_backward(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("backward must be a boolean")
        return value


class SolarEclipseCentralLineLimitResponse(_StrictModel):
    kind: Literal["first", "last"]
    epoch: EclipseEpochResponse
    latitude_deg: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude_deg: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)


class SolarEclipseConjunctionResponse(_StrictModel):
    kind: Literal["equatorial", "ecliptic"]
    epoch: EclipseEpochResponse


class SolarEclipseUmbralContactResponse(_StrictModel):
    kind: Literal["u1", "u2", "u3", "u4"]
    epoch: EclipseEpochResponse
    latitude_deg: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude_deg: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)


class SolarEclipseUmbralContactsResponse(_StrictModel):
    u1: SolarEclipseUmbralContactResponse
    u2: SolarEclipseUmbralContactResponse
    u3: SolarEclipseUmbralContactResponse
    u4: SolarEclipseUmbralContactResponse


class SolarEclipseGreatestSiteResponse(_StrictModel):
    epoch: EclipseEpochResponse
    latitude_deg: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude_deg: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)
    path_width_km: float = Field(ge=0.0, allow_inf_nan=False)
    central_duration_seconds: float = Field(ge=0.0, allow_inf_nan=False)
    sun_altitude_deg: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    sun_azimuth_deg: float = Field(ge=0.0, le=360.0, allow_inf_nan=False)
    moon_altitude_deg: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    moon_azimuth_deg: float = Field(ge=0.0, le=360.0, allow_inf_nan=False)
    separation_deg: float = Field(ge=0.0, le=180.0, allow_inf_nan=False)
    sun_semidiameter_deg: float = Field(gt=0.0, lt=90.0, allow_inf_nan=False)
    moon_semidiameter_deg: float = Field(gt=0.0, lt=90.0, allow_inf_nan=False)
    magnitude: float = Field(ge=0.0, allow_inf_nan=False)
    obscuration: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    local_class: Literal["none", "partial", "annular", "total"]


class SolarBesselianElementsResponse(_StrictModel):
    jd_ut1: float = Field(allow_inf_nan=False)
    jd_tt: float = Field(allow_inf_nan=False)
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)
    d: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    mu: float = Field(ge=0.0, lt=360.0, allow_inf_nan=False)
    l1: float = Field(gt=0.0, allow_inf_nan=False)
    l2: float = Field(allow_inf_nan=False)
    tan_f1: float = Field(gt=0.0, allow_inf_nan=False)
    tan_f2: float = Field(gt=0.0, allow_inf_nan=False)
    ephemeris: Literal["DE-0441LE-0441"]
    axis_model: str
    frame: str
    hour_angle_model: str
    radius_model: str


class SolarEclipseGlobalCircumstancesResponse(_StrictModel):
    event: EclipseEventResponse
    greatest: SolarEclipseGreatestSiteResponse
    greatest_duration: SolarEclipseGreatestSiteResponse | None = None
    equatorial_conjunction: SolarEclipseConjunctionResponse
    ecliptic_conjunction: SolarEclipseConjunctionResponse
    topology: SolarEclipseFootprintTopologyValue
    penumbral_contacts: SolarEclipseFootprintContactsResponse
    besselian: SolarBesselianElementsResponse
    sun: EclipseGeocentricBodyStateResponse
    moon: EclipseGeocentricBodyStateResponse
    gamma_earth_radii: float = Field(allow_inf_nan=False)
    umbral_contacts: SolarEclipseUmbralContactsResponse | None = None
    first_central_line_limit: SolarEclipseCentralLineLimitResponse | None = None
    last_central_line_limit: SolarEclipseCentralLineLimitResponse | None = None
    ephemeris: Literal["DE-0441LE-0441"]
    surface_model: Literal["WGS84_ZERO_ELEVATION"]
    limb_model: Literal["SPHERICAL_MEAN_LIMB"]
    umbral_contacts_admitted: Literal[True]
    greatest_duration_admitted: Literal[True]


class SolarEclipseCartographyRequest(SolarEclipseGlobalCircumstancesRequest):
    magnitude_levels: list[float] = Field(
        default=[0.2, 0.4, 0.6, 0.8, 0.9],
        min_length=1,
        max_length=20,
    )
    obscuration_levels: list[float] = Field(
        default=[0.2, 0.4, 0.6, 0.8, 0.9],
        min_length=1,
        max_length=20,
    )
    mesh_depth: int = Field(default=1, ge=0, le=3)
    time_samples: int = Field(default=17, ge=9, le=129)
    angular_tolerance_deg: float = Field(
        default=8.0,
        ge=0.1,
        le=90.0,
        allow_inf_nan=False,
    )
    field_tolerance: float = Field(
        default=0.01,
        ge=1.0e-6,
        le=0.25,
        allow_inf_nan=False,
    )

    @field_validator("magnitude_levels", "obscuration_levels")
    @classmethod
    def _valid_levels(cls, values: list[float]) -> list[float]:
        if any(not isfinite(value) or not 0.0 < value <= 1.0 for value in values):
            raise ValueError("contour levels must be finite and in (0, 1]")
        if values != sorted(set(values)):
            raise ValueError("contour levels must be strictly increasing and unique")
        return values

    @field_validator("mesh_depth", "time_samples", mode="before")
    @classmethod
    def _integer_policy(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("mesh_depth and time_samples must be integers")
        return value

    @field_validator("time_samples")
    @classmethod
    def _odd_time_samples(cls, value: int) -> int:
        if value % 2 == 0:
            raise ValueError("time_samples must be odd")
        return value


class SolarEclipseMapSampleResponse(_StrictModel):
    latitude_deg: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude_deg: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)
    visible: bool
    magnitude: float = Field(ge=0.0, allow_inf_nan=False)
    magnitude_jd_ut1: float | None = Field(default=None, allow_inf_nan=False)
    obscuration: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    obscuration_jd_ut1: float | None = Field(default=None, allow_inf_nan=False)
    local_class: Literal["none", "partial", "annular", "total"]
    sun_altitude_deg: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        allow_inf_nan=False,
    )


class EclipseContourPointResponse(_StrictModel):
    latitude_deg: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude_deg: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)


class EclipseContourComponentResponse(_StrictModel):
    quantity: Literal["magnitude", "obscuration"]
    threshold: float = Field(gt=0.0, le=1.0, allow_inf_nan=False)
    component_id: int = Field(ge=0)
    segment_id: int = Field(ge=0)
    closed: bool
    points: list[EclipseContourPointResponse] = Field(min_length=2)


class EclipseContourLevelResponse(_StrictModel):
    quantity: Literal["magnitude", "obscuration"]
    threshold: float = Field(gt=0.0, le=1.0, allow_inf_nan=False)
    components: list[EclipseContourComponentResponse]


class SolarEclipseCartographyResponse(_StrictModel):
    global_circumstances: SolarEclipseGlobalCircumstancesResponse
    samples: list[SolarEclipseMapSampleResponse] = Field(min_length=12)
    magnitude_levels: list[EclipseContourLevelResponse]
    obscuration_levels: list[EclipseContourLevelResponse]
    mesh_depth: int = Field(ge=0, le=3)
    achieved_mesh_depth: int = Field(ge=0, le=3)
    mesh_triangle_count: int = Field(ge=20)
    time_samples: int = Field(ge=9, le=129)
    angular_tolerance_deg: float = Field(
        ge=0.1,
        le=90.0,
        allow_inf_nan=False,
    )
    field_tolerance: float = Field(
        ge=1.0e-6,
        le=0.25,
        allow_inf_nan=False,
    )
    maximum_angular_edge_deg: float = Field(
        ge=0.0,
        le=180.0,
        allow_inf_nan=False,
    )
    converged: bool
    unresolved_edge_count: int = Field(ge=0)
    daylight_policy: Literal["GEOMETRIC_SUN_CENTER_NONNEGATIVE_ALTITUDE"]
    duration_contours_available: Literal[False]
    projection: Literal["SPHERICAL_GEOGRAPHIC"]


class CloseApproachRequest(_StrictModel):
    body1: str
    body2: str
    jd_start: float
    jd_end: float
    max_sep_deg: float = 1.0
    step_days: float = 0.5


class LunarOccultationRequest(_StrictModel):
    target: str
    jd_start: float
    jd_end: float
    step_days: float = 0.25
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0


class LunarStarOccultationRequest(_StrictModel):
    star_lon: float
    star_lat: float
    star_name: str
    jd_start: float
    jd_end: float
    step_days: float = 0.25
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0


class AllLunarOccultationsRequest(_StrictModel):
    jd_start: float
    jd_end: float
    planets: list[str] | None = None


class LunarOccultationPathRequest(_StrictModel):
    target: str
    jd_start: float
    jd_end: float
    step_days: float = 0.25
    sample_count: int = 9
    observer_elev_m: float = 0.0


class LunarOccultationPathAtRequest(_StrictModel):
    target: str
    jd_mid: float
    sample_count: int = 9
    observer_elev_m: float = 0.0


class LunarStarOccultationPathRequest(_StrictModel):
    star_lon: float
    star_lat: float
    star_name: str
    jd_start: float
    jd_end: float
    step_days: float = 0.25
    sample_count: int = 9
    observer_elev_m: float = 0.0


class LunarStarOccultationPathAtRequest(_StrictModel):
    star_lon: float
    star_lat: float
    star_name: str
    jd_mid: float
    sample_count: int = 9
    observer_elev_m: float = 0.0


def _parse_topology_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be an integer or float")
    parsed = float(value)
    if not isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _parse_topology_label(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


class _OccultationPathTopologyBaseRequest(_StrictModel):
    sample_count: int = Field(default=65, ge=9, le=721)
    observer_elev_m: float = Field(
        default=0.0,
        ge=_OCCULTATION_TOPOLOGY_MIN_OBSERVER_ELEV_M,
        allow_inf_nan=False,
    )

    @field_validator("sample_count", mode="before")
    @classmethod
    def _valid_sample_count(cls, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("sample_count must be an integer")
        return value

    @field_validator("observer_elev_m", mode="before")
    @classmethod
    def _valid_observer_elevation(cls, value: Any) -> float:
        return _parse_topology_number(value, "observer_elev_m")


class LunarOccultationPathTopologyRequest(_OccultationPathTopologyBaseRequest):
    target: str
    jd_start: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )
    jd_end: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )
    step_days: float = Field(
        default=0.25,
        gt=0.0,
        le=_OCCULTATION_TOPOLOGY_MAX_STEP_DAYS,
        allow_inf_nan=False,
    )

    @field_validator("target", mode="before")
    @classmethod
    def _valid_target(cls, value: Any) -> str:
        return _parse_topology_label(value, "target")

    @field_validator("jd_start", "jd_end", "step_days", mode="before")
    @classmethod
    def _valid_numbers(cls, value: Any, info: Any) -> float:
        return _parse_topology_number(value, info.field_name)

    @model_validator(mode="after")
    def _valid_search_budget(self) -> "LunarOccultationPathTopologyRequest":
        _validate_occultation_topology_search_window(
            self.jd_start,
            self.jd_end,
            self.step_days,
        )
        return self


class LunarOccultationPathTopologyAtRequest(_OccultationPathTopologyBaseRequest):
    target: str
    jd_mid: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )

    @field_validator("target", mode="before")
    @classmethod
    def _valid_target(cls, value: Any) -> str:
        return _parse_topology_label(value, "target")

    @field_validator("jd_mid", mode="before")
    @classmethod
    def _valid_jd_mid(cls, value: Any) -> float:
        return _parse_topology_number(value, "jd_mid")


class _LunarStarOccultationPathTopologyBaseRequest(
    _OccultationPathTopologyBaseRequest
):
    star_lon: float = Field(allow_inf_nan=False)
    star_lat: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    star_name: str

    @field_validator("star_lon", "star_lat", mode="before")
    @classmethod
    def _valid_star_coordinates(cls, value: Any, info: Any) -> float:
        return _parse_topology_number(value, info.field_name)

    @field_validator("star_name", mode="before")
    @classmethod
    def _valid_star_name(cls, value: Any) -> str:
        parsed = _parse_topology_label(value, "star_name")
        if parsed != value:
            raise ValueError("star_name must not contain surrounding whitespace")
        return parsed


class LunarStarOccultationPathTopologyRequest(
    _LunarStarOccultationPathTopologyBaseRequest
):
    jd_start: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )
    jd_end: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )
    step_days: float = Field(
        default=0.25,
        gt=0.0,
        le=_OCCULTATION_TOPOLOGY_MAX_STEP_DAYS,
        allow_inf_nan=False,
    )

    @field_validator("jd_start", "jd_end", "step_days", mode="before")
    @classmethod
    def _valid_numbers(cls, value: Any, info: Any) -> float:
        return _parse_topology_number(value, info.field_name)

    @model_validator(mode="after")
    def _valid_search_budget(self) -> "LunarStarOccultationPathTopologyRequest":
        _validate_occultation_topology_search_window(
            self.jd_start,
            self.jd_end,
            self.step_days,
        )
        return self


class LunarStarOccultationPathTopologyAtRequest(
    _LunarStarOccultationPathTopologyBaseRequest
):
    jd_mid: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )

    @field_validator("jd_mid", mode="before")
    @classmethod
    def _valid_jd_mid(cls, value: Any) -> float:
        return _parse_topology_number(value, "jd_mid")


class CloseApproachResponse(_StrictModel):
    body1: str
    body2: str
    jd_ut: float
    datetime_utc: str
    separation_deg: float
    is_occultation: bool


class LunarOccultationResponse(_StrictModel):
    target: str
    jd_ingress: float
    ingress_datetime_utc: str
    jd_egress: float
    egress_datetime_utc: str
    jd_mid: float
    mid_datetime_utc: str
    min_separation: float
    is_total: bool
    duration_minutes: float


class CloseApproachSearchResponse(_StrictModel):
    events: list[CloseApproachResponse]


class LunarOccultationSearchResponse(_StrictModel):
    events: list[LunarOccultationResponse]


class OccultationPathGeometryResponse(_StrictModel):
    occulting_body: str
    occulted_body: str
    jd_greatest_ut: float
    greatest_datetime_utc: str
    central_line_lats: list[float]
    central_line_lons: list[float]
    path_width_km: float
    duration_at_greatest_s: float


class OccultationPathSearchResponse(_StrictModel):
    events: list[OccultationPathGeometryResponse]


OccultationPathBoundarySideValue = Literal["left", "right"]
OccultationPathTopologyKindValue = Literal["two_sided_band"]
OccultationGeographicPoleValue = Literal["north", "south"]
OccultationPoleCrossingPhaseValue = Literal["ingress", "egress"]
OccultationLunarLimbModelValue = Literal["SPHERICAL_MEAN_LIMB"]
OccultationTargetModelValue = Literal["POINT_SOURCE", "JPL_EQUATORIAL_SOLID_BODY"]


class OccultationPathPointResponse(_StrictModel):
    jd_ut: float = Field(
        ge=_MIN_COMPUTATIONAL_JD,
        le=_MAX_COMPUTATIONAL_JD,
        allow_inf_nan=False,
    )
    datetime_utc: str
    latitude_deg: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude_deg: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)
    separation_deg: float = Field(ge=0.0, allow_inf_nan=False)
    clearance_deg: float = Field(allow_inf_nan=False)


class OccultationPathBoundaryPointResponse(_StrictModel):
    side: OccultationPathBoundarySideValue
    point: OccultationPathPointResponse
    cross_track_distance_km: float = Field(ge=0.0, allow_inf_nan=False)


class OccultationPathBoundaryTrackResponse(_StrictModel):
    side: OccultationPathBoundarySideValue
    points: list[OccultationPathBoundaryPointResponse] = Field(
        min_length=9,
        max_length=721,
    )


class OccultationPoleCrossingResponse(_StrictModel):
    pole: OccultationGeographicPoleValue
    phase: OccultationPoleCrossingPhaseValue
    point: OccultationPathPointResponse
    boundary_side: OccultationPathBoundarySideValue | None


class OccultationPathTopologyResponse(_StrictModel):
    summary: OccultationPathGeometryResponse
    topology: OccultationPathTopologyKindValue
    centers: list[OccultationPathPointResponse] = Field(
        min_length=9,
        max_length=721,
    )
    boundaries: list[OccultationPathBoundaryTrackResponse] = Field(
        min_length=2,
        max_length=2,
    )
    greatest_left: OccultationPathBoundaryPointResponse
    greatest_right: OccultationPathBoundaryPointResponse
    pole_crossings: list[OccultationPoleCrossingResponse]
    lunar_limb_model: OccultationLunarLimbModelValue
    target_model: OccultationTargetModelValue
    observer_elevation_m: float = Field(
        ge=_OCCULTATION_TOPOLOGY_MIN_OBSERVER_ELEV_M,
        allow_inf_nan=False,
    )
    observer_geometry: Literal["WGS84_GEODETIC"]
    width_metric: Literal["SPHERICAL_GREAT_CIRCLE_R6378_137_KM"]
    time_scale: Literal["UT1"]
    atmospheric_refraction: Literal[False]
    saturn_rings_included: Literal[False]


class OccultationPathTopologySearchResponse(_StrictModel):
    events: list[OccultationPathTopologyResponse]


class HeliacalPlanetEventRequest(_StrictModel):
    body: str
    kind: str
    jd_start: float
    lat: float
    lon: float
    search_days: int = 400


class GeneralVisibilityEventRequest(_StrictModel):
    body: str
    kind: str
    jd_start: float
    lat: float
    lon: float
    search_window_days: int = 400


class VisibilityAssessmentCompactResponse(_StrictModel):
    body: str
    jd_ut: float
    criterion_family: str
    effective_limiting_magnitude: float
    apparent_magnitude: float
    true_altitude_deg: float
    apparent_altitude_deg: float
    solar_elongation_deg: float
    observable: bool


class PlanetHeliacalEventResponse(_StrictModel):
    body: str
    kind: str
    jd_ut: float
    datetime_utc: str
    elongation_deg: float
    planet_altitude_deg: float
    sun_altitude_deg: float
    apparent_magnitude: float


class GeneralVisibilityEventResponse(_StrictModel):
    body: str
    target_kind: str
    kind: str
    jd_ut: float
    datetime_utc: str
    elongation_deg: float
    target_altitude_deg: float
    sun_altitude_deg: float
    apparent_magnitude: float
    assessment: VisibilityAssessmentCompactResponse


class ParanSearchRequest(_StrictModel):
    bodies: list[str]
    jd_day: float
    lat: float
    lon: float
    orb_minutes: float = 4.0
    include_crossing_inventory: bool = False
    policy_preset: str = "permissive"


class ParanStarCanonEntryResponse(_StrictModel):
    name: str
    tiers: list[str]
    default_enabled: bool
    available: bool


class ParanStarCanonResponse(_StrictModel):
    entries: list[ParanStarCanonEntryResponse]
    available_tiers: list[str]
    returned_count: int
    canon_count: int


class NatalParanSearchRequest(_StrictModel):
    bodies: list[str]
    natal_jd: float
    lat: float
    lon: float
    orb_minutes: float = 4.0
    include_crossing_inventory: bool = False
    policy_preset: str = "permissive"


class NatalAngularContactsRequest(_StrictModel):
    bodies: list[str]
    natal_jd: float
    lat: float
    lon: float
    orb_minutes: float = 2.0


class ParanTargetRequest(_StrictModel):
    body1: str
    body2: str
    circle1: str
    circle2: str
    jd1: float
    jd2: float
    orb_min: float


class ParanSiteRequest(_StrictModel):
    target: ParanTargetRequest
    jd_day: float
    lat: float
    lon: float
    orb_minutes: float = 4.0
    stability_time_offsets_minutes: list[float] | None = None
    policy_preset: str = "permissive"


class ParanFieldGridRequest(_StrictModel):
    target: ParanTargetRequest
    jd_day: float
    latitudes: list[float]
    longitudes: list[float]
    orb_minutes: float = 4.0
    stability_time_offsets_minutes: list[float] | None = None
    policy_preset: str = "permissive"


class ParanFieldMetricRequest(_StrictModel):
    target: ParanTargetRequest
    jd_day: float
    latitudes: list[float]
    longitudes: list[float]
    metric: str
    threshold: float
    orb_minutes: float = 4.0
    stability_time_offsets_minutes: list[float] | None = None
    policy_preset: str = "permissive"


class ParanCrossingResponse(_StrictModel):
    body: str
    circle: str
    jd: float
    datetime_utc: str
    source_method: str
    altitude_policy: float | None = None


class NatalAngularContactResponse(_StrictModel):
    body: str
    body_family: str
    circle: str
    crossing_jd: float
    natal_jd: float
    delta_minutes: float
    absolute_delta_minutes: float
    crossing: ParanCrossingResponse


class NatalAngularContactsResponse(_StrictModel):
    contacts: list[NatalAngularContactResponse]


class ParanCircleInventoryEntryResponse(_StrictModel):
    circle: str
    status: str
    crossing: ParanCrossingResponse | None = None
    absence_reason: str | None = None


class ParanBodyCrossingInventoryResponse(_StrictModel):
    body: str
    entries: list[ParanCircleInventoryEntryResponse]


class ParanStrengthResponse(_StrictModel):
    orb_minutes: float
    exactness_score: float
    model: str


class ParanStabilitySampleResponse(_StrictModel):
    offset_minutes: float
    survived: bool
    orb_minutes: float | None = None
    exactness_score: float | None = None


class ParanStabilityResponse(_StrictModel):
    method: str
    baseline_orb_minutes: float
    baseline_exactness_score: float
    offsets_minutes: list[float]
    samples: list[ParanStabilitySampleResponse]
    survival_rate: float
    stable_across_window: bool
    worst_orb_minutes: float | None = None
    max_orb_degradation: float | None = None
    worst_exactness_score: float | None = None
    max_exactness_drop: float | None = None


class ParanResponse(_StrictModel):
    body1: str
    body2: str
    circle1: str
    circle2: str
    jd1: float
    jd1_datetime_utc: str
    jd2: float
    jd2_datetime_utc: str
    jd: float
    jd_datetime_utc: str
    orb_min: float
    event_family: str | None = None
    axis_family: str | None = None
    body_family: str | None = None
    crossing1: ParanCrossingResponse | None = None
    crossing2: ParanCrossingResponse | None = None
    strength: ParanStrengthResponse


class ParanSearchResponse(_StrictModel):
    events: list[ParanResponse]
    crossing_inventory: list[ParanBodyCrossingInventoryResponse] | None = None
    effective_policy_preset: str = "permissive"


class ParanSiteResultResponse(_StrictModel):
    lat: float
    lon: float
    matched: bool
    paran: ParanResponse | None = None
    strength: ParanStrengthResponse | None = None
    stability: ParanStabilityResponse | None = None
    effective_policy_preset: str | None = None


class ParanFieldSampleResponse(_StrictModel):
    lat: float
    lon: float
    site_result: ParanSiteResultResponse


class ParanFieldSampleSearchResponse(_StrictModel):
    samples: list[ParanFieldSampleResponse]
    effective_policy_preset: str = "permissive"


class ParanThresholdCrossingResponse(_StrictModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    start_value: float
    end_value: float


class ParanFieldRegionResponse(_StrictModel):
    region_id: int
    sample_count: int
    cells: list[list[float]]
    peak_value: float


class ParanFieldPeakResponse(_StrictModel):
    lat: float
    lon: float
    value: float


class ParanFieldAnalysisResponse(_StrictModel):
    metric: str
    threshold: float
    adjacency: str
    total_samples: int
    active_sample_count: int
    regions: list[ParanFieldRegionResponse]
    peaks: list[ParanFieldPeakResponse]
    threshold_crossings: list[ParanThresholdCrossingResponse]
    effective_policy_preset: str = "permissive"


class ParanContourPointResponse(_StrictModel):
    lat: float
    lon: float


class ParanContourSegmentResponse(_StrictModel):
    start: ParanContourPointResponse
    end: ParanContourPointResponse
    cell_lat_min: float
    cell_lon_min: float
    case_index: int
    ambiguous: bool


class ParanContourExtractionResponse(_StrictModel):
    metric: str
    threshold: float
    interpolation: str
    segments: list[ParanContourSegmentResponse]
    ambiguous_cells: list[list[float]]
    effective_policy_preset: str = "permissive"


class ParanContourPathResponse(_StrictModel):
    points: list[ParanContourPointResponse]
    closed: bool
    segment_count: int
    ambiguous: bool
    source_case_indices: list[int]


class ParanContourPathSetResponse(_StrictModel):
    paths: list[ParanContourPathResponse]
    orphan_segments: list[ParanContourSegmentResponse]
    matching_rule: str
    effective_policy_preset: str = "permissive"


class ParanContourAssociationResponse(_StrictModel):
    path_index: int
    region_id: int | None = None
    associated_peak_indices: list[int]


class ParanContourHierarchyEntryResponse(_StrictModel):
    path_index: int
    parent_index: int | None = None
    depth: int


class ParanFieldStructureResponse(_StrictModel):
    dominant_path_index: int | None = None
    hierarchy: list[ParanContourHierarchyEntryResponse]
    associations: list[ParanContourAssociationResponse]
    matching_rule: str
    effective_policy_preset: str = "permissive"


__all__ = [
    "AllLunarOccultationsRequest",
    "CloseApproachRequest",
    "CloseApproachResponse",
    "CloseApproachSearchResponse",
    "EclipseDataResponse",
    "EclipseEpochResponse",
    "EclipseGeocentricBodyStateResponse",
    "EclipseEventResponse",
    "EclipseSearchRequest",
    "EventInstantResponse",
    "GeneralVisibilityEventRequest",
    "GeneralVisibilityEventResponse",
    "HeliacalPlanetEventRequest",
    "LastAspectResponse",
    "LocalContactCircumstancesResponse",
    "LunarEclipseLocalCircumstancesResponse",
    "LunarEclipseLocationRequest",
    "LunarEclipseGlobalCircumstancesRequest",
    "LunarEclipseGlobalCircumstancesResponse",
    "LunarEclipseShadowStateResponse",
    "LunarEclipseAnalysisModeValue",
    "LunarEclipseSearchKind",
    "LunarEclipseVisibilityContactKindValue",
    "LunarEclipseVisibilityLimitResponse",
    "LunarEclipseVisibilityMapResponse",
    "LunarEclipseVisibilityPointResponse",
    "LunarEclipseVisibilityRequest",
    "LunarOccultationRequest",
    "LunarOccultationPathAtRequest",
    "LunarOccultationPathRequest",
    "LunarOccultationPathTopologyAtRequest",
    "LunarOccultationPathTopologyRequest",
    "LunarOccultationResponse",
    "LunarOccultationSearchResponse",
    "LunarStarOccultationRequest",
    "LunarStarOccultationPathAtRequest",
    "LunarStarOccultationPathRequest",
    "LunarStarOccultationPathTopologyAtRequest",
    "LunarStarOccultationPathTopologyRequest",
    "NextStationRequest",
    "NatalParanSearchRequest",
    "NatalAngularContactsRequest",
    "NatalAngularContactResponse",
    "NatalAngularContactsResponse",
    "OccultationPathGeometryResponse",
    "OccultationGeographicPoleValue",
    "OccultationLunarLimbModelValue",
    "OccultationPathBoundaryPointResponse",
    "OccultationPathBoundarySideValue",
    "OccultationPathBoundaryTrackResponse",
    "OccultationPathPointResponse",
    "OccultationPathSearchResponse",
    "OccultationPathTopologyKindValue",
    "OccultationPathTopologyResponse",
    "OccultationPathTopologySearchResponse",
    "OccultationPoleCrossingPhaseValue",
    "OccultationPoleCrossingResponse",
    "OccultationTargetModelValue",
    "ParanCrossingResponse",
    "ParanCircleInventoryEntryResponse",
    "ParanBodyCrossingInventoryResponse",
    "ParanContourAssociationResponse",
    "ParanContourExtractionResponse",
    "ParanContourHierarchyEntryResponse",
    "ParanContourPathResponse",
    "ParanContourPathSetResponse",
    "ParanContourPointResponse",
    "ParanContourSegmentResponse",
    "ParanFieldAnalysisResponse",
    "ParanFieldGridRequest",
    "ParanFieldMetricRequest",
    "ParanFieldPeakResponse",
    "ParanFieldRegionResponse",
    "ParanFieldSampleResponse",
    "ParanFieldSampleSearchResponse",
    "ParanFieldStructureResponse",
    "ParanResponse",
    "ParanSearchRequest",
    "ParanSearchResponse",
    "ParanStarCanonEntryResponse",
    "ParanStarCanonResponse",
    "ParanSiteRequest",
    "ParanSiteResultResponse",
    "ParanStabilityResponse",
    "ParanStabilitySampleResponse",
    "ParanStrengthResponse",
    "ParanTargetRequest",
    "ParanThresholdCrossingResponse",
    "PlanetHeliacalEventResponse",
    "RetrogradePeriodResponse",
    "RetrogradePeriodSearchRequest",
    "RetrogradePeriodSearchResponse",
    "RiseSetPhenomenaRequest",
    "RiseSetPhenomenaResponse",
    "RiseSetPolicyRequest",
    "RiseSetTransitRequest",
    "SolarBodyCircumstancesResponse",
    "SolarEclipseLocalCircumstancesResponse",
    "SolarEclipseLocationRequest",
    "StationEventResponse",
    "StationSearchRequest",
    "StationSearchResponse",
    "StationStateRequest",
    "StationStateResponse",
    "SolarEclipsePathRequest",
    "SolarEclipsePathResponse",
    "SolarEclipseSearchKind",
    "SolarEclipseFootprintBoundaryKindValue",
    "SolarEclipseFootprintRequest",
    "SolarEclipseGlobalCircumstancesRequest",
    "SolarEclipseGlobalCircumstancesResponse",
    "SolarEclipseCentralLineLimitResponse",
    "SolarEclipseConjunctionResponse",
    "SolarEclipseUmbralContactResponse",
    "SolarEclipseUmbralContactsResponse",
    "SolarEclipseGreatestSiteResponse",
    "SolarBesselianElementsResponse",
    "SolarEclipseCartographyRequest",
    "SolarEclipseCartographyResponse",
    "SolarEclipseMapSampleResponse",
    "EclipseContourPointResponse",
    "EclipseContourComponentResponse",
    "EclipseContourLevelResponse",
    "SolarEclipseFootprintPointResponse",
    "SolarEclipsePenumbralContactKindValue",
    "SolarEclipsePenumbralContactResponse",
    "SolarEclipseFootprintContactsResponse",
    "SolarEclipseFootprintTopologyValue",
    "SolarEclipseLimitTrackResponse",
    "SolarEclipseVisibilityFootprintResponse",
    "TwilightRequest",
    "TwilightTimesResponse",
    "VisibilityAssessmentCompactResponse",
    "VoidOfCourseRangeRequest",
    "VoidOfCourseRangeResponse",
    "VoidOfCourseRequest",
    "VoidOfCourseStateResponse",
    "VoidOfCourseWindowResponse",
]
