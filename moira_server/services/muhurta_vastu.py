"""Observer-bound facade delegation, without a server-side rule engine."""
from ..models.muhurta_vastu import VastuSnapshotResponse, VastuWindowsResponse
from ..serializers.muhurta_election import election_values


def compute_vastu_datetime(engine, request):
    result = engine.vastu_election_for_datetime(request.dt, request.latitude, request.longitude,
        timezone=request.timezone, policy=request.policy.to_engine(), context=request.context.to_engine(),
        limits=request.limits.to_engine())
    return VastuSnapshotResponse(**election_values(result))


def compute_vastu_windows(engine, request):
    result = engine.vastu_election_windows(request.start, request.end, request.latitude, request.longitude,
        timezone=request.timezone, policy=request.policy.to_engine(), context=request.context.to_engine(),
        limits=request.limits.to_engine())
    return VastuWindowsResponse(**election_values(result))
