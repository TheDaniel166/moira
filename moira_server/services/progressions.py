"""Phase-8 service helpers for progression routes (P8-01–P8-05)."""

from __future__ import annotations

from moira import Moira
from moira.julian import jd_from_datetime
from moira.progressions import (
    ProgressedChart,
    ProgressedDeclinationChart,
    ProgressedHouseFrame,
    ProgressionChartConditionProfile,
    ProgressionConditionNetworkProfile,
    ascendant_arc,
    converse_ascendant_arc,
    converse_duodenary_progression,
    daily_house_frame,
    converse_vertex_arc,
    vertex_arc,
    converse_mean_solar_arc_longitude,
    converse_mean_solar_arc_right_ascension,
    converse_minor_progression,
    converse_naibod_longitude,
    converse_naibod_right_ascension,
    converse_one_degree_longitude,
    converse_one_degree_right_ascension,
    converse_planetary_arc,
    converse_quotidian_lunar_progression,
    converse_quotidian_solar_progression,
    converse_secondary_progression,
    converse_secondary_progression_declination,
    converse_solar_arc,
    converse_solar_arc_right_ascension,
    converse_tertiary_ii_progression,
    converse_tertiary_progression,
    duodenary_progression,
    mean_solar_arc_longitude,
    mean_solar_arc_right_ascension,
    minor_progression,
    naibod_longitude,
    naibod_right_ascension,
    one_degree_longitude,
    one_degree_right_ascension,
    planetary_arc,
    progression_chart_condition_profile,
    progression_condition_network_profile,
    quotidian_lunar_progression,
    quotidian_solar_progression,
    secondary_progression,
    secondary_progression_declination,
    solar_arc,
    solar_arc_right_ascension,
    tertiary_ii_progression,
    tertiary_progression,
)

from ..models.progressions import (
    ARC_METHODS,
    ArcProgressionRequest,
    HOUSE_FRAME_ARC_METHODS,
    HouseFrameArcRequest,
    HouseFrameProgressionRequest,
    ProgressionNetworkRequest,
    ProgressionProfileRequest,
    SecondaryProgressionDeclinationRequest,
    SecondaryProgressionRequest,
    TIME_KEY_METHODS,
    TimeKeyProgressionRequest,
)
from ._shared import require_aware_datetime

# ---------------------------------------------------------------------------
# Dispatch tables
# ---------------------------------------------------------------------------

# Each entry: method key → (direct_fn, converse_fn)
# Functions with the standard (natal_jd_ut, target_date, bodies, ...) signature.
_ARC_DISPATCH = {
    "solar_arc":                    (solar_arc,                    converse_solar_arc),
    "solar_arc_right_ascension":    (solar_arc_right_ascension,    converse_solar_arc_right_ascension),
    "naibod_longitude":             (naibod_longitude,             converse_naibod_longitude),
    "naibod_right_ascension":       (naibod_right_ascension,       converse_naibod_right_ascension),
    "mean_solar_arc_longitude":     (mean_solar_arc_longitude,     converse_mean_solar_arc_longitude),
    "mean_solar_arc_right_ascension": (mean_solar_arc_right_ascension, converse_mean_solar_arc_right_ascension),
    "one_degree_longitude":         (one_degree_longitude,         converse_one_degree_longitude),
    "one_degree_right_ascension":   (one_degree_right_ascension,   converse_one_degree_right_ascension),
    # planetary_arc handled separately — takes arc_body positional arg
}

_TIME_KEY_DISPATCH = {
    "tertiary":        (tertiary_progression,         converse_tertiary_progression),
    "tertiary_ii":     (tertiary_ii_progression,      converse_tertiary_ii_progression),
    "minor":           (minor_progression,            converse_minor_progression),
    "duodenary":       (duodenary_progression,        converse_duodenary_progression),
    "quotidian_solar": (quotidian_solar_progression,  converse_quotidian_solar_progression),
    "quotidian_lunar": (quotidian_lunar_progression,  converse_quotidian_lunar_progression),
}

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _natal_jd_from_request(natal_dt, bodies=None):
    require_aware_datetime(natal_dt)
    return jd_from_datetime(natal_dt)


def _natal_jd(request) -> float:
    require_aware_datetime(request.natal.dt)
    return jd_from_datetime(request.natal.dt)


# ---------------------------------------------------------------------------
# P8-01 secondary progression
# ---------------------------------------------------------------------------

def compute_secondary_progression_chart(
    engine: Moira,
    request: SecondaryProgressionRequest,
) -> ProgressedChart:
    require_aware_datetime(request.target_dt)
    natal_jd = _natal_jd(request)
    fn = converse_secondary_progression if request.converse else secondary_progression
    return fn(natal_jd_ut=natal_jd, target_date=request.target_dt, bodies=request.natal.bodies)


def compute_secondary_progression_declination_chart(
    engine: Moira,
    request: SecondaryProgressionDeclinationRequest,
) -> ProgressedDeclinationChart:
    require_aware_datetime(request.target_dt)
    natal_jd = _natal_jd(request)
    fn = (
        converse_secondary_progression_declination
        if request.converse
        else secondary_progression_declination
    )
    return fn(natal_jd_ut=natal_jd, target_date=request.target_dt, bodies=request.natal.bodies)


# ---------------------------------------------------------------------------
# P8-02 arc direction
# ---------------------------------------------------------------------------

def compute_arc_progression_chart(
    engine: Moira,
    request: ArcProgressionRequest,
) -> ProgressedChart:
    require_aware_datetime(request.target_dt)
    natal_jd = _natal_jd(request)

    if request.method not in ARC_METHODS:
        supported = ", ".join(sorted(ARC_METHODS))
        raise ValueError(
            f"unsupported arc method {request.method!r}; supported: {supported}"
        )

    if request.method == "planetary_arc":
        if not request.arc_body:
            raise ValueError("arc_body is required for method 'planetary_arc'")
        fn = converse_planetary_arc if request.converse else planetary_arc
        return fn(
            natal_jd_ut=natal_jd,
            target_date=request.target_dt,
            arc_body=request.arc_body,
            bodies=request.natal.bodies,
        )

    direct_fn, converse_fn = _ARC_DISPATCH[request.method]
    fn = converse_fn if request.converse else direct_fn
    return fn(natal_jd_ut=natal_jd, target_date=request.target_dt, bodies=request.natal.bodies)


# ---------------------------------------------------------------------------
# P8-03 time-key progression
# ---------------------------------------------------------------------------

def compute_time_key_progression_chart(
    engine: Moira,
    request: TimeKeyProgressionRequest,
) -> ProgressedChart:
    require_aware_datetime(request.target_dt)
    natal_jd = _natal_jd(request)

    if request.method not in TIME_KEY_METHODS:
        supported = ", ".join(sorted(TIME_KEY_METHODS))
        raise ValueError(
            f"unsupported time-key method {request.method!r}; supported: {supported}"
        )

    direct_fn, converse_fn = _TIME_KEY_DISPATCH[request.method]
    fn = converse_fn if request.converse else direct_fn
    return fn(natal_jd_ut=natal_jd, target_date=request.target_dt, bodies=request.natal.bodies)


# ---------------------------------------------------------------------------
# P8-04 house-frame and angle-arc services
# ---------------------------------------------------------------------------

_HOUSE_FRAME_ARC_DISPATCH = {
    "ascendant_arc": (ascendant_arc, converse_ascendant_arc),
    "vertex_arc":    (vertex_arc,    converse_vertex_arc),
}


def compute_daily_house_frame(
    engine: Moira,
    request: HouseFrameProgressionRequest,
) -> ProgressedHouseFrame:
    require_aware_datetime(request.natal.dt)
    require_aware_datetime(request.target_dt)
    natal_jd = jd_from_datetime(request.natal.dt)
    return daily_house_frame(
        natal_jd_ut=natal_jd,
        target_date=request.target_dt,
        latitude=request.natal.latitude,
        longitude=request.natal.longitude,
        system=request.natal.house_system,
    )


def compute_house_frame_arc_chart(
    engine: Moira,
    request: HouseFrameArcRequest,
) -> ProgressedChart:
    require_aware_datetime(request.target_dt)
    natal_jd = jd_from_datetime(request.natal.dt)
    require_aware_datetime(request.natal.dt)

    if request.method not in HOUSE_FRAME_ARC_METHODS:
        supported = ", ".join(sorted(HOUSE_FRAME_ARC_METHODS))
        raise ValueError(
            f"unsupported house-frame arc method {request.method!r}; supported: {supported}"
        )

    direct_fn, converse_fn = _HOUSE_FRAME_ARC_DISPATCH[request.method]
    fn = converse_fn if request.converse else direct_fn
    return fn(
        natal_jd_ut=natal_jd,
        target_date=request.target_dt,
        latitude=request.natal.latitude,
        longitude=request.natal.longitude,
        system=request.natal.house_system,
        bodies=request.natal.bodies,
    )


# ---------------------------------------------------------------------------
# P8-05 aggregate surfaces (now with house-frame support)
# ---------------------------------------------------------------------------

def compute_progression_chart_condition_profile_service(
    engine: Moira,
    request: ProgressionProfileRequest,
) -> ProgressionChartConditionProfile:
    charts = [compute_secondary_progression_chart(engine, item) for item in request.items]
    frames = [compute_daily_house_frame(engine, item) for item in request.house_frame_items]
    return progression_chart_condition_profile(
        charts=charts if charts else None,
        house_frames=frames if frames else None,
    )


def compute_progression_condition_network_profile_service(
    engine: Moira,
    request: ProgressionNetworkRequest,
) -> ProgressionConditionNetworkProfile:
    charts = [compute_secondary_progression_chart(engine, item) for item in request.items]
    frames = [compute_daily_house_frame(engine, item) for item in request.house_frame_items]
    return progression_condition_network_profile(
        charts=charts if charts else None,
        house_frames=frames if frames else None,
    )


__all__ = [
    "compute_arc_progression_chart",
    "compute_daily_house_frame",
    "compute_house_frame_arc_chart",
    "compute_progression_chart_condition_profile_service",
    "compute_progression_condition_network_profile_service",
    "compute_secondary_progression_chart",
    "compute_secondary_progression_declination_chart",
    "compute_time_key_progression_chart",
]
