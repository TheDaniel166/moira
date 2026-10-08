"""Bind date-derived named Muhurta to the startup engine's reader."""
from moira import Moira
from ..models.named_muhurta import NamedMuhurtaDayRequest
from ..serializers.named_muhurta import serialize_named_muhurta_day


def compute_named_muhurta_day(engine: Moira, request: NamedMuhurtaDayRequest):
    return serialize_named_muhurta_day(engine.named_muhurta_for_date(
        request.local_date, request.latitude, request.longitude,
        timezone=request.timezone, policy=request.policy.to_engine(),
    ))
