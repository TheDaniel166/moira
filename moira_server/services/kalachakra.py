"""Kalachakra transport composition delegates all doctrine and lookup to the engine."""
from moira.kalachakra import kalachakra_sequence, current_kalachakra_periods
from ..models.kalachakra import engine_seed, engine_epoch, engine_projection


def compute_sequence(request, engine):
    kwargs = dict(profile_id=request.profile_id,levels=request.levels,
        birth_epoch=engine_epoch(request.birth_epoch),projection=engine_projection(request.projection))
    seed = engine_seed(request.seed)
    if seed.basis == 'sidereal':
        return kalachakra_sequence(seed,**kwargs)
    return engine.kalachakra_sequence(seed,**kwargs)


def compute_chart_sequence(request, engine):
    return engine.kalachakra_for_datetime(request.birth_datetime,profile_id=request.profile_id,
        ayanamsa_system=request.ayanamsa_system,levels=request.levels,
        projection=engine_projection(request.projection))


def compute_current(request, engine, *, chart=False):
    schedule = compute_chart_sequence(request,engine) if chart else compute_sequence(request,engine)
    return current_kalachakra_periods(schedule,engine_epoch(request.query_epoch))
