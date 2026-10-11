"""Reader-bound business facade delegation."""
from ..models.muhurta_business import BusinessSnapshotResponse, BusinessWindowsResponse
from ..serializers.muhurta_election import election_values


def compute_business_datetime(engine, request):
    result = engine.business_election_for_datetime(request.dt,request.latitude,request.longitude,
        timezone=request.timezone,policy=request.policy.to_engine(),context=request.context.to_engine(),limits=request.limits.to_engine())
    return BusinessSnapshotResponse(**election_values(result))


def compute_business_windows(engine, request):
    result = engine.business_election_windows(request.start,request.end,request.latitude,request.longitude,
        timezone=request.timezone,policy=request.policy.to_engine(),context=request.context.to_engine(),limits=request.limits.to_engine())
    return BusinessWindowsResponse(**election_values(result))
