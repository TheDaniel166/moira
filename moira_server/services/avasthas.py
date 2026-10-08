"""Bind birth-time composition to the startup engine and its reader."""
from moira import Moira
from moira.avasthas import AvasthaPolicy
from ..models.sayanadi import AvasthaBirthRequest


def compute_avastha_birth(engine: Moira, request: AvasthaBirthRequest):
    return engine.avasthas_for_datetime(
        request.birth, request.latitude, request.longitude,
        name=request.name.to_engine(), timezone_name=request.timezone_name,
        policy=request.policy.to_engine(), avastha_policy=AvasthaPolicy(**request.avastha_policy.model_dump()),
    )
