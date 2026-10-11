"""Reader-bound travel delegation with lossless engine projection."""
from ..models.muhurta_travel import TravelSnapshotResponse,TravelWindowsResponse
from ..serializers.muhurta_election import election_values


def compute_travel_datetime(engine,request):
    result=engine.travel_election_for_datetime(request.dt,request.latitude,request.longitude,
        timezone=request.timezone,policy=request.policy.to_engine(),context=request.context.to_engine(),limits=request.limits.to_engine())
    return TravelSnapshotResponse(**election_values(result))


def compute_travel_windows(engine,request):
    result=engine.travel_election_windows(request.start,request.end,request.latitude,request.longitude,
        timezone=request.timezone,policy=request.policy.to_engine(),context=request.context.to_engine(),limits=request.limits.to_engine())
    return TravelWindowsResponse(**election_values(result))
