"""Transport contracts for bounded astronomical products."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from moira._geocentric_conjunctions import GeocentricConjunctionUnresolved, GeocentricConjunctionWitness
from moira.phenomena import ConjunctionRangeComputationTruth


from .phenomena import EclipseEventResponse, GeneralVisibilityEventResponse, LastAspectResponse
from .visibility import LunarCrescentDetailsResponse


FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]
VoidMover = Literal["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
ConjunctionBody = Literal[
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
]
StellarCriterion = Literal["named_star_setting", "named_star_dawn_last"]
VisibilityCriterion = StellarCriterion | Literal["yallop_lunar_crescent"]
VisibilityOutcomeStatus = Literal[
    "found", "not_found", "observation_unavailable", "unresolved", "coverage_unavailable",
    "resource_unavailable", "latitude_rejected", "magnitude_rejected", "work_limit",
]


class _StrictModel(BaseModel):
    """Reject extra fields at the transport boundary."""

    model_config = ConfigDict(extra="forbid")


class SearchWindow(_StrictModel):
    """Explicit start and end of an astronomical interval in UT1."""

    jd_start_ut1: FiniteNumber
    jd_end_ut1: FiniteNumber


class NatalEclipseContactsRequest(SearchWindow):
    """Search eclipse maxima against caller-supplied tropical longitudes."""

    natal_longitudes_deg: dict[
        Annotated[str, Field(min_length=1, max_length=80)],
        Annotated[float, Field(strict=True, ge=0, lt=360)],
    ] = Field(min_length=1, max_length=64)
    orb_deg: float = Field(default=1.0, strict=True, ge=0, le=180)
    limit: int = Field(default=256, strict=True, ge=1, le=1024)


class NatalEclipseContactResponse(_StrictModel):
    """A natal match at one eclipse maximum and one axis end."""

    event: EclipseEventResponse
    eclipse_kind: Literal["solar", "lunar"]
    axis_end: Literal["sun", "moon"]
    eclipse_longitude_deg: float
    target_name: str
    target_longitude_deg: float
    separation_deg: float


class NatalEclipseContactsResponse(_StrictModel):
    """Bounded native scan outcome and ordered natal matches."""

    request: NatalEclipseContactsRequest
    status: Literal["complete", "unresolved_phase"]
    hits: list[NatalEclipseContactResponse]
    total_hits: int | None
    truncated: bool
    interval_ownership: Literal["inclusive_maxima"] = "inclusive_maxima"
    search_model: Literal["padded_native_scan_with_python_refinement"] = (
        "padded_native_scan_with_python_refinement"
    )


class EclipseSnapshotRequest(_StrictModel):
    """Evaluate eclipse geometry at an exact UT1 Julian day."""

    jd_ut1: FiniteNumber


class EclipseSnapshotResponse(_StrictModel):
    """Instantaneous, observer-free geometry and eclipse status."""

    jd_ut1: float
    status: Literal["solar_eclipse", "lunar_eclipse", "no_eclipse"]
    eclipse_type: str
    eclipse_magnitude: float
    is_eclipse_season: bool
    sun_longitude_deg: float
    moon_longitude_deg: float
    moon_latitude_deg: float
    node_longitude_deg: float
    sun_node_distance_deg: float
    angular_separation_deg: float
    sun_radius_deg: float
    moon_radius_deg: float
    moon_distance_km: float
    moon_parallax_deg: float
    umbra_radius_deg: float
    penumbra_radius_deg: float
    frame: Literal["geocentric_true_ecliptic_of_date"] = "geocentric_true_ecliptic_of_date"
    time_binding: Literal["ut1_to_ephemeris_tt"] = "ut1_to_ephemeris_tt"
    model: Literal["EclipseCalculator.calculate_jd"] = "EclipseCalculator.calculate_jd"


class MultiBodyVoidRequest(SearchWindow):
    """Search sign windows for selected classical movers and major aspects."""

    bodies: list[VoidMover] = Field(min_length=1, max_length=7)
    aspect_set: Literal["traditional", "modern"] = "traditional"


class BodyVoidPeriodResponse(_StrictModel):
    """An overlapping, unclipped void window for one mover."""

    sign: str
    next_sign: str
    jd_voc_start_ut1: float
    jd_voc_end_ut1: float
    duration_hours: float
    last_aspect: LastAspectResponse | None


class BodyVoidPeriodsResponse(_StrictModel):
    """Complete mover windows or an item-local failure."""

    body: VoidMover
    status: Literal["complete", "coverage_unavailable", "resource_unavailable", "unresolved"]
    windows: list[BodyVoidPeriodResponse]


class MultiBodyVoidResponse(_StrictModel):
    """Per-mover outcomes in caller order under the selected major-aspect set."""

    request: MultiBodyVoidRequest
    results: list[BodyVoidPeriodsResponse]
    interval_ownership: Literal["overlapping_start_inclusive_end_exclusive"] = (
        "overlapping_start_inclusive_end_exclusive"
    )


class GreatConjunctionsRequest(SearchWindow):
    """Search for Jupiter–Saturn roots with optional zodiacal projection."""

    include_zodiac: bool = Field(default=False, strict=True)


class GreatConjunctionRootResponse(_StrictModel):
    """One geocentric Jupiter–Saturn longitude root."""

    jd_ut1: float
    longitude_deg: float


class GreatConjunctionZodiacResponse(_StrictModel):
    """The engine's optional zodiacal and elemental projection of a root."""

    sign: str
    sign_symbol: str
    degree_in_sign: float
    element: str


class GreatConjunctionsResponse(_StrictModel):
    """A location-free sequence, including a completed empty sequence."""

    request: GreatConjunctionsRequest
    roots: list[GreatConjunctionRootResponse]
    zodiac_projection: list[GreatConjunctionZodiacResponse] | None
    frame: Literal["apparent_geocentric_true_ecliptic_of_date"] = (
        "apparent_geocentric_true_ecliptic_of_date"
    )
    interval_ownership: Literal["inclusive_bracketed_roots"] = "inclusive_bracketed_roots"
    engine_entrypoint: Literal["moira.cycles.great_conjunctions"] = "moira.cycles.great_conjunctions"


class GeocentricConjunctionsRequest(SearchWindow):
    """Search up to 32 days for apparent longitude crossings of a distinct body pair."""

    body1: ConjunctionBody
    body2: ConjunctionBody


class GeocentricConjunctionRootResponse(_StrictModel):
    """A represented UT1 root, the first body's longitude, and its interval witness."""

    jd_ut1: float
    longitude_deg: float
    witness: GeocentricConjunctionWitness


class GeocentricConjunctionWorkResponse(_StrictModel):
    """Interval exclusions and measured search work from the engine."""

    excluded_intervals: int
    evaluations: int
    subdivisions: int
    reader_calls: int


class GeocentricConjunctionsResponse(_StrictModel):
    """Ordered proved crossings, unresolved intervals, and serving source identity."""

    request: GeocentricConjunctionsRequest
    status: Literal["complete", "unresolved"]
    roots: list[GeocentricConjunctionRootResponse]
    unresolved_intervals: tuple[GeocentricConjunctionUnresolved, ...]
    planetary_ephemeris: str
    source_sha256: tuple[str, ...]
    work: GeocentricConjunctionWorkResponse
    computation_truth: ConjunctionRangeComputationTruth
    interval_ownership: Literal["inclusive_represented_ut1_roots"] = "inclusive_represented_ut1_roots"


class StellarVisibilityEvidenceResponse(_StrictModel):
    """Source-bound fixed-star transition evidence from the catalogue scan."""

    event_jd_ut1: float | None
    arcus_visionis_deg: float
    elongation_threshold_deg: float
    qualifying_day_offset: int | None
    qualifying_elongation_deg: float | None
    qualifying_solar_altitude_deg: float | None
    transition_confirmed: bool | None
    visibility_run_open: bool | None


class ExplicitVisibilityRequest(_StrictModel):
    """Select an explicit stellar or lunar observation policy for one target."""

    body: str = Field(min_length=1, max_length=80)
    kind: Literal["heliacal_setting", "last_morning_visibility", "evening_first", "morning_last"]
    criterion: VisibilityCriterion
    jd_start: FiniteNumber
    lat: float = Field(strict=True, ge=-90, le=90)
    lon: float = Field(strict=True, ge=-180, le=180)
    search_window_days: int = Field(default=400, strict=True, ge=1, le=400)


class VisibilityCriterionOutcome(_StrictModel):
    """One explicitly selected visibility criterion and its bounded outcome."""

    body: str
    kind: str
    criterion: VisibilityCriterion
    source: Literal["moira.stars.heliacal_catalog_batch", "moira.heliacal.lunar_visibility_event_with_observation_truth"]
    status: VisibilityOutcomeStatus
    observed_days: int | None = None
    unavailable_days: int | None = None
    stellar_evidence: StellarVisibilityEvidenceResponse | None = None
    lunar_event: GeneralVisibilityEventResponse | None = None
    lunar_crescent_details: LunarCrescentDetailsResponse | None = None


class StellarVisibilityCatalogueRequest(_StrictModel):
    """Search an explicit bounded subset under one sovereign-star criterion."""

    names: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(min_length=1, max_length=12)
    criterion: StellarCriterion
    jd_start: FiniteNumber
    lat: float = Field(strict=True, ge=-90, le=90)
    lon: float = Field(strict=True, ge=-180, le=180)
    search_window_days: int = Field(default=400, strict=True, ge=1, le=400)
    max_magnitude: FiniteNumber = 6.5
    max_star_days: int = Field(default=1600, strict=True, ge=1, le=4800)


class StellarVisibilityCatalogueResponse(_StrictModel):
    """Ordered per-name results and the reserved star-day work."""

    request: StellarVisibilityCatalogueRequest
    results: list[VisibilityCriterionOutcome]
    reserved_star_days: int
    source: Literal["moira.stars.heliacal_catalog_batch"] = "moira.stars.heliacal_catalog_batch"
