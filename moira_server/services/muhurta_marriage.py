"""Thin reader-bound delegation for marriage election requests."""
from ..serializers.muhurta_marriage import serialize_marriage_snapshot,serialize_marriage_windows


def compute_marriage_datetime(engine,request):
    return serialize_marriage_snapshot(engine.marriage_election_for_datetime(
        request.dt,request.latitude,request.longitude,timezone=request.timezone,
        policy=request.policy.to_engine(),
        personal=None if request.personal is None else request.personal.to_engine(),
        limits=request.limits.to_engine()))


def compute_marriage_windows(engine,request):
    return serialize_marriage_windows(engine.marriage_election_windows(
        request.start,request.end,request.latitude,request.longitude,timezone=request.timezone,
        policy=request.policy.to_engine(),personal=None if request.personal is None else request.personal.to_engine(),
        limits=request.limits.to_engine()))
