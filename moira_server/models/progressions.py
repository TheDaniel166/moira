"""Transport models for phase-8 progression route families (P8-01–P8-05)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from .common import _StrictModel


class ProgressionNatalRequest(_StrictModel):
    """Natal basis for a progression technique.

    Progressions require only the birth datetime; no observer location is needed.
    Bodies defaults to all planets when omitted.
    """

    dt: datetime
    bodies: list[str] | None = None


class SecondaryProgressionRequest(_StrictModel):
    natal: ProgressionNatalRequest
    target_dt: datetime
    converse: bool = False


class SecondaryProgressionDeclinationRequest(_StrictModel):
    natal: ProgressionNatalRequest
    target_dt: datetime
    converse: bool = False


# ---------------------------------------------------------------------------
# P8-04 House-frame progression request models
# ---------------------------------------------------------------------------

HOUSE_FRAME_ARC_METHODS = frozenset({"ascendant_arc", "vertex_arc"})


class HouseFrameNatalRequest(_StrictModel):
    """Natal basis for house-frame progressions and angle-arc directions.

    latitude/longitude: observer location — required for all house-frame techniques.
    house_system: optional house system code; defaults to Placidus.
    bodies: optional body list for arc direction methods; ignored by daily_house_frame.
    """

    dt: datetime
    latitude: float
    longitude: float
    house_system: str | None = None
    bodies: list[str] | None = None


class HouseFrameProgressionRequest(_StrictModel):
    """Request for a daily house frame or daily houses surface."""

    natal: HouseFrameNatalRequest
    target_dt: datetime


class HouseFrameArcRequest(_StrictModel):
    """Request for an angle-arc direction chart (ascendant_arc or vertex_arc).

    method: "ascendant_arc" or "vertex_arc".
    converse: when True applies the arc in reverse.
    """

    natal: HouseFrameNatalRequest
    target_dt: datetime
    method: str
    converse: bool = False


# ---------------------------------------------------------------------------
# P8-05 aggregate requests — now accepting house-frame items
# ---------------------------------------------------------------------------

class ProgressionProfileRequest(_StrictModel):
    """Aggregate chart condition profile over progression charts and/or house frames.

    At least one of items or house_frame_items must be non-empty.
    """

    items: list[SecondaryProgressionRequest] = Field(default_factory=list)
    house_frame_items: list[HouseFrameProgressionRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def at_least_one_item(self) -> "ProgressionProfileRequest":
        if not self.items and not self.house_frame_items:
            raise ValueError("at least one of items or house_frame_items must be provided")
        return self


class ProgressionNetworkRequest(_StrictModel):
    """Network condition profile over progression charts and/or house frames.

    All technique names across items and house_frame_items must be distinct.
    """

    items: list[SecondaryProgressionRequest] = Field(default_factory=list)
    house_frame_items: list[HouseFrameProgressionRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def at_least_one_item(self) -> "ProgressionNetworkRequest":
        if not self.items and not self.house_frame_items:
            raise ValueError("at least one of items or house_frame_items must be provided")
        return self


# ---------------------------------------------------------------------------
# Position response vessels
# ---------------------------------------------------------------------------

class ProgressedPositionResponse(_StrictModel):
    name: str
    longitude: float
    speed: float
    retrograde: bool
    sign: str
    sign_symbol: str
    sign_degree: float


class ProgressedDeclinationPositionResponse(_StrictModel):
    name: str
    declination: float


# ---------------------------------------------------------------------------
# Relation and condition-profile response vessels
# ---------------------------------------------------------------------------

class ProgressionRelationResponse(_StrictModel):
    technique_name: str
    relation_kind: str
    basis: str
    reference_name: str | None
    converse: bool
    coordinate_system: str


class ProgressionConditionProfileResponse(_StrictModel):
    technique_name: str
    doctrine_family: str
    relation_kind: str
    relation_basis: str
    coordinate_system: str
    rate_mode: str
    application_mode: str
    converse: bool
    uses_directed_arc: bool
    uses_reference_body: bool
    uses_stepped_key: bool
    uses_house_frame: bool
    structural_state: str


# ---------------------------------------------------------------------------
# P8-04 House-frame response vessels
# ---------------------------------------------------------------------------

class DailyHousesResponse(_StrictModel):
    """Light response carrying only the progressed house cusps and angular points."""

    natal_jd_ut: float
    progressed_jd_ut: float
    target_date: str
    house_system: str
    cusps: list[float]
    asc: float
    mc: float
    vertex: float | None


class ProgressedHouseFrameResponse(_StrictModel):
    """Full progressed house-frame vessel with doctrine, relation, and condition truth."""

    chart_type: str
    natal_jd_ut: float
    progressed_jd_ut: float
    target_date: str
    house_system: str
    cusps: list[float]
    asc: float
    mc: float
    vertex: float | None
    doctrine_family: str
    coordinate_system: str
    rate_mode: str
    application_mode: str
    relation_kind: str
    relation_basis: str
    condition_state: str
    relation: ProgressionRelationResponse
    condition_profile: ProgressionConditionProfileResponse


# ---------------------------------------------------------------------------
# Chart response vessels
# ---------------------------------------------------------------------------

class ProgressedChartResponse(_StrictModel):
    chart_type: str
    natal_jd_ut: float
    progressed_jd_ut: float
    target_date: str
    solar_arc_deg: float
    positions: dict[str, ProgressedPositionResponse]
    doctrine_family: str | None
    coordinate_system: str | None
    is_converse: bool | None
    condition_state: str | None
    relation: ProgressionRelationResponse | None
    condition_profile: ProgressionConditionProfileResponse | None


class ProgressedDeclinationChartResponse(_StrictModel):
    chart_type: str
    natal_jd_ut: float
    progressed_jd_ut: float
    target_date: str
    positions: dict[str, ProgressedDeclinationPositionResponse]
    doctrine_family: str
    coordinate_system: str
    is_converse: bool
    condition_state: str
    relation: ProgressionRelationResponse
    condition_profile: ProgressionConditionProfileResponse


# ---------------------------------------------------------------------------
# Aggregate and network response vessels
# ---------------------------------------------------------------------------

class ProgressionChartConditionProfileResponse(_StrictModel):
    profiles: list[ProgressionConditionProfileResponse]
    profile_count: int
    uniform_count: int
    differential_count: int
    hybrid_count: int
    directing_arc_count: int
    time_key_count: int
    house_frame_count: int
    strongest_techniques: list[str]
    weakest_techniques: list[str]


class ProgressionNetworkNodeResponse(_StrictModel):
    node_id: str
    node_kind: str
    label: str
    incoming_count: int
    outgoing_count: int
    total_degree: int
    is_isolated: bool


class ProgressionNetworkEdgeResponse(_StrictModel):
    source_id: str
    target_id: str
    relation_kind: str
    relation_basis: str


class ProgressionConditionNetworkProfileResponse(_StrictModel):
    nodes: list[ProgressionNetworkNodeResponse]
    edges: list[ProgressionNetworkEdgeResponse]
    technique_node_count: int
    target_node_count: int
    most_connected_nodes: list[str]
    isolated_nodes: list[str]


# ---------------------------------------------------------------------------
# P8-02 Arc direction request
# ---------------------------------------------------------------------------

# Recognised arc method keys and their doctrinal names:
#   "solar_arc"                    — Solar Arc (Sun arc applied to all bodies)
#   "solar_arc_right_ascension"    — Solar Arc in Right Ascension
#   "naibod_longitude"             — Naibod in Longitude
#   "naibod_right_ascension"       — Naibod in Right Ascension
#   "mean_solar_arc_longitude"     — Mean Solar Arc in Longitude (Naibod rate)
#   "mean_solar_arc_right_ascension" — Mean Solar Arc in RA
#   "one_degree_longitude"         — One Degree in Longitude
#   "one_degree_right_ascension"   — One Degree in Right Ascension
#   "planetary_arc"                — Planetary Arc (requires arc_body)

ARC_METHODS = frozenset({
    "solar_arc",
    "solar_arc_right_ascension",
    "naibod_longitude",
    "naibod_right_ascension",
    "mean_solar_arc_longitude",
    "mean_solar_arc_right_ascension",
    "one_degree_longitude",
    "one_degree_right_ascension",
    "planetary_arc",
})


class ArcProgressionRequest(_StrictModel):
    """Request for an arc direction chart (P8-02).

    method: one of the ARC_METHODS keys.
    converse: when True the arc is applied in reverse.
    arc_body: required when method is "planetary_arc"; the reference planet
              whose arc is applied to all natal positions.
    """

    natal: ProgressionNatalRequest
    target_dt: datetime
    method: str
    converse: bool = False
    arc_body: str | None = None


# ---------------------------------------------------------------------------
# P8-03 Time-key progression request
# ---------------------------------------------------------------------------

# Recognised time-key method keys:
#   "tertiary"        — Tertiary (synodic month = one year)
#   "tertiary_ii"     — Tertiary II (tropical month variant)
#   "minor"           — Minor (solar year / synodic month)
#   "duodenary"       — Duodenary (Carter, 2h05m per year)
#   "quotidian_solar" — Quotidian Solar (secondary → day-for-day)
#   "quotidian_lunar" — Quotidian Lunar (lunar month → day-for-day)

TIME_KEY_METHODS = frozenset({
    "tertiary",
    "tertiary_ii",
    "minor",
    "duodenary",
    "quotidian_solar",
    "quotidian_lunar",
})


class TimeKeyProgressionRequest(_StrictModel):
    """Request for a time-key progression chart (P8-03).

    method: one of the TIME_KEY_METHODS keys.
    converse: when True the progressed date advances backward from birth.
    """

    natal: ProgressionNatalRequest
    target_dt: datetime
    method: str
    converse: bool = False


__all__ = [
    "ARC_METHODS",
    "ArcProgressionRequest",
    "DailyHousesResponse",
    "HOUSE_FRAME_ARC_METHODS",
    "HouseFrameArcRequest",
    "HouseFrameNatalRequest",
    "HouseFrameProgressionRequest",
    "ProgressedHouseFrameResponse",
    "ProgressionNatalRequest",
    "SecondaryProgressionRequest",
    "SecondaryProgressionDeclinationRequest",
    "ProgressionProfileRequest",
    "ProgressionNetworkRequest",
    "TIME_KEY_METHODS",
    "TimeKeyProgressionRequest",
    "ProgressedPositionResponse",
    "ProgressedDeclinationPositionResponse",
    "ProgressionRelationResponse",
    "ProgressionConditionProfileResponse",
    "ProgressedChartResponse",
    "ProgressedDeclinationChartResponse",
    "ProgressionChartConditionProfileResponse",
    "ProgressionNetworkNodeResponse",
    "ProgressionNetworkEdgeResponse",
    "ProgressionConditionNetworkProfileResponse",
]
