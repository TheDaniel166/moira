"""Bind the complete named-day product to the serving engine's reader."""
from moira import Moira
from ..models.special_muhurta import SpecialMuhurtaDayRequest
from ..serializers.special_muhurta import serialize_special_muhurta_day


def compute_special_muhurta_day(engine: Moira, request: SpecialMuhurtaDayRequest):
    return serialize_special_muhurta_day(engine.special_muhurta_for_date(
        request.local_date, request.latitude, request.longitude, timezone=request.timezone,
        policy=request.policy.to_engine(),
    ))
