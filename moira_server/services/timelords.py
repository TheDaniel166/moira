"""Phase-8 service helpers for profection and timelord routes."""

from __future__ import annotations

from moira import Moira
from moira.julian import jd_from_datetime
from moira.profections import annual_profection, monthly_profection, profection_schedule
from moira.timelords import (
    DecennialActivePair,
    DecennialActivePath,
    DecennialMajorGroup,
    DecennialPeriod,
    DecennialSequenceProfile,
    FirdarActivePair,
    FirdarMajorGroup,
    FirdarPeriod,
    FirdarSequenceProfile,
    ReleasingPeriod,
    ZRLevelPair,
    ZRPeriodGroup,
    ZRSequenceProfile,
    current_decennials,
    current_firdaria,
    current_releasing,
    decennial_active_pair,
    decennial_active_path,
    decennial_sequence_profile,
    decennials,
    firdar_active_pair,
    firdar_sequence_profile,
    firdaria,
    group_decennials,
    group_firdaria,
    group_releasing,
    zodiacal_releasing,
    zr_level_pair,
    zr_sequence_profile,
)

from ..models.chart import ChartRequest, HousesRequest
from ..models.timelords import (
    AnnualProfectionRequest,
    DecennialActivePairRequest,
    DecennialBaseRequest,
    DecennialCurrentRequest,
    DecennialNatalRequest,
    FirdarActivePairRequest,
    FirdarBaseRequest,
    FirdarCurrentRequest,
    MonthlyProfectionRequest,
    ProfectionScheduleRequest,
    TimelordNativityRequest,
    ZRBaseRequest,
    ZRCurrentRequest,
    ZRLevelPairRequest,
    ZRNatalRequest,
    ZRProfileRequest,
)
from ._shared import build_chart_with_houses_context, require_aware_datetime, require_supported_chart_bodies


def _natal_artifacts(engine: Moira, request: TimelordNativityRequest):
    require_aware_datetime(request.dt)
    require_supported_chart_bodies(request.bodies)
    return build_chart_with_houses_context(
        engine,
        ChartRequest(
            dt=request.dt,
            bodies=request.bodies,
            include_nodes=request.include_nodes,
            observer_lat=request.observer_lat,
            observer_lon=request.observer_lon,
            observer_elev_m=request.observer_elev_m,
        ),
        HousesRequest(
            dt=request.dt,
            latitude=request.latitude,
            longitude=request.longitude,
            system=request.house_system,
        ),
    )


def _natal_positions(chart, include_nodes: bool) -> dict[str, float]:
    return chart.longitudes(include_nodes=include_nodes)


def compute_annual_profection(engine: Moira, request: AnnualProfectionRequest):
    chart, houses = _natal_artifacts(engine, request.natal)
    return annual_profection(
        natal_asc=houses.asc,
        age_years=request.age_years,
        natal_positions=_natal_positions(chart, request.natal.include_nodes),
        activation_orb=request.natal.activation_orb,
    )


def compute_monthly_profection(engine: Moira, request: MonthlyProfectionRequest):
    _, houses = _natal_artifacts(engine, request.natal)
    return monthly_profection(
        natal_asc=houses.asc,
        age_years=request.age_years,
        month_index=request.month_index,
    )


def compute_profection_schedule(engine: Moira, request: ProfectionScheduleRequest):
    chart, houses = _natal_artifacts(engine, request.natal)
    require_aware_datetime(request.current_dt)
    return profection_schedule(
        natal_asc=houses.asc,
        natal_jd=jd_from_datetime(request.natal.dt),
        current_jd=jd_from_datetime(request.current_dt),
        natal_positions=_natal_positions(chart, request.natal.include_nodes),
    )


# ---------------------------------------------------------------------------
# P8-07 Firdaria services
# ---------------------------------------------------------------------------

def _firdaria_periods(request: FirdarBaseRequest) -> list[FirdarPeriod]:
    require_aware_datetime(request.natal.dt)
    natal_jd = jd_from_datetime(request.natal.dt)
    return firdaria(
        natal_jd,
        request.natal.is_day_chart,
        variant=request.variant,
        include_node_subperiods=request.include_node_subperiods,
    )


def compute_firdaria_sequence(engine: Moira, request: FirdarBaseRequest) -> list[FirdarPeriod]:
    return _firdaria_periods(request)


def compute_firdaria_groups(engine: Moira, request: FirdarBaseRequest) -> list[FirdarMajorGroup]:
    periods = _firdaria_periods(request)
    return group_firdaria(periods)


def compute_current_firdaria(
    engine: Moira,
    request: FirdarCurrentRequest,
) -> tuple[FirdarPeriod, FirdarPeriod]:
    require_aware_datetime(request.natal.dt)
    require_aware_datetime(request.current_dt)
    natal_jd = jd_from_datetime(request.natal.dt)
    current_jd = jd_from_datetime(request.current_dt)
    return current_firdaria(
        natal_jd,
        current_jd,
        request.natal.is_day_chart,
        variant=request.variant,
        include_node_subperiods=request.include_node_subperiods,
    )


def compute_firdar_sequence_profile_service(
    engine: Moira,
    request: FirdarBaseRequest,
) -> FirdarSequenceProfile:
    periods = _firdaria_periods(request)
    return firdar_sequence_profile(periods)


def compute_firdar_active_pair_service(
    engine: Moira,
    request: FirdarActivePairRequest,
) -> FirdarActivePair | None:
    require_aware_datetime(request.natal.dt)
    require_aware_datetime(request.query_dt)
    natal_jd = jd_from_datetime(request.natal.dt)
    query_jd = jd_from_datetime(request.query_dt)
    base = FirdarBaseRequest(
        natal=request.natal,
        variant=request.variant,
        include_node_subperiods=request.include_node_subperiods,
    )
    periods = _firdaria_periods(base)
    return firdar_active_pair(periods, query_jd)


# ---------------------------------------------------------------------------
# P8-08 Decennials services
# ---------------------------------------------------------------------------

def _natal_positions_and_jd(engine: Moira, natal_request: DecennialNatalRequest):
    """Derive natal planetary longitudes and Julian Day for decennials computation."""
    require_aware_datetime(natal_request.dt)
    natal_jd = jd_from_datetime(natal_request.dt)
    chart = engine.chart(natal_request.dt)
    natal_positions = chart.longitudes(include_nodes=False)
    return natal_positions, natal_jd


def _decennial_periods(engine: Moira, request: DecennialBaseRequest) -> list[DecennialPeriod]:
    natal_positions, natal_jd = _natal_positions_and_jd(engine, request.natal)
    return decennials(
        natal_jd,
        natal_positions,
        request.natal.is_day_chart,
        levels=request.natal.levels,
    )


def compute_decennials_sequence(
    engine: Moira,
    request: DecennialBaseRequest,
) -> list[DecennialPeriod]:
    return _decennial_periods(engine, request)


def compute_decennials_groups(
    engine: Moira,
    request: DecennialBaseRequest,
) -> list[DecennialMajorGroup]:
    periods = _decennial_periods(engine, request)
    return group_decennials(periods)


def compute_current_decennials_service(
    engine: Moira,
    request: DecennialCurrentRequest,
) -> tuple[DecennialPeriod, DecennialPeriod]:
    require_aware_datetime(request.natal.dt)
    require_aware_datetime(request.current_dt)
    natal_positions, natal_jd = _natal_positions_and_jd(engine, request.natal)
    current_jd = jd_from_datetime(request.current_dt)
    return current_decennials(
        natal_jd,
        natal_positions,
        request.natal.is_day_chart,
        current_jd,
        levels=request.natal.levels,
    )


def compute_decennial_sequence_profile_service(
    engine: Moira,
    request: DecennialBaseRequest,
) -> DecennialSequenceProfile:
    periods = _decennial_periods(engine, request)
    return decennial_sequence_profile(periods)


def compute_decennial_active_pair_service(
    engine: Moira,
    request: DecennialActivePairRequest,
) -> DecennialActivePair | None:
    require_aware_datetime(request.query_dt)
    base = DecennialBaseRequest(natal=request.natal)
    periods = _decennial_periods(engine, base)
    query_jd = jd_from_datetime(request.query_dt)
    return decennial_active_pair(periods, query_jd)


def compute_decennial_active_path_service(
    engine: Moira,
    request: DecennialActivePairRequest,
) -> DecennialActivePath | None:
    require_aware_datetime(request.query_dt)
    base = DecennialBaseRequest(natal=request.natal)
    periods = _decennial_periods(engine, base)
    query_jd = jd_from_datetime(request.query_dt)
    return decennial_active_path(periods, query_jd)


# ---------------------------------------------------------------------------
# P8-09 Zodiacal Releasing services
# ---------------------------------------------------------------------------

def _zr_params(natal: ZRNatalRequest) -> dict:
    require_aware_datetime(natal.dt)
    return dict(
        lot_longitude=natal.lot_longitude,
        natal_jd=jd_from_datetime(natal.dt),
        lot_name=natal.lot_name,
        fortune_longitude=natal.fortune_longitude,
        use_loosing_of_bond=natal.use_loosing_of_bond,
    )


def compute_zr_sequence(
    engine: Moira,
    request: ZRBaseRequest,
) -> list[ReleasingPeriod]:
    params = _zr_params(request.natal)
    return zodiacal_releasing(
        params["lot_longitude"],
        params["natal_jd"],
        levels=request.levels,
        lot_name=params["lot_name"],
        fortune_longitude=params["fortune_longitude"],
        use_loosing_of_bond=params["use_loosing_of_bond"],
    )


def compute_zr_groups(
    engine: Moira,
    request: ZRBaseRequest,
) -> list[ZRPeriodGroup]:
    periods = compute_zr_sequence(engine, request)
    return group_releasing(periods)


def compute_current_releasing_service(
    engine: Moira,
    request: ZRCurrentRequest,
) -> list[ReleasingPeriod]:
    require_aware_datetime(request.current_dt)
    params = _zr_params(request.natal)
    current_jd = jd_from_datetime(request.current_dt)
    return current_releasing(
        params["lot_longitude"],
        params["natal_jd"],
        current_jd,
        lot_name=params["lot_name"],
        fortune_longitude=params["fortune_longitude"],
        use_loosing_of_bond=params["use_loosing_of_bond"],
    )


def compute_zr_sequence_profile_service(
    engine: Moira,
    request: ZRProfileRequest,
) -> ZRSequenceProfile:
    base = ZRBaseRequest(natal=request.natal, levels=request.levels)
    periods = compute_zr_sequence(engine, base)
    return zr_sequence_profile(periods, level=request.profile_level)


def compute_zr_level_pair_service(
    engine: Moira,
    request: ZRLevelPairRequest,
) -> ZRLevelPair:
    require_aware_datetime(request.query_dt)
    if request.upper_level >= request.lower_level:
        raise ValueError("upper_level must be less than lower_level")
    current_req = ZRCurrentRequest(natal=request.natal, current_dt=request.query_dt)
    active = compute_current_releasing_service(engine, current_req)
    by_level = {p.level: p for p in active}
    if request.upper_level not in by_level:
        raise ValueError(
            f"no active period found at level {request.upper_level}"
        )
    if request.lower_level not in by_level:
        raise ValueError(
            f"no active period found at level {request.lower_level}"
        )
    return zr_level_pair(by_level[request.upper_level], by_level[request.lower_level])


__all__ = [
    "compute_annual_profection",
    "compute_current_decennials_service",
    "compute_current_firdaria",
    "compute_current_releasing_service",
    "compute_decennial_active_pair_service",
    "compute_decennial_active_path_service",
    "compute_decennial_sequence_profile_service",
    "compute_decennials_groups",
    "compute_decennials_sequence",
    "compute_firdar_active_pair_service",
    "compute_firdar_sequence_profile_service",
    "compute_firdaria_groups",
    "compute_firdaria_sequence",
    "compute_monthly_profection",
    "compute_profection_schedule",
    "compute_zr_groups",
    "compute_zr_level_pair_service",
    "compute_zr_sequence",
    "compute_zr_sequence_profile_service",
]
