"""Use the serving engine's reader for bounded dosha day composition."""
from moira import Moira
from ..models.muhurta_dosha import DoshaDayRequest
from ..serializers.muhurta_dosha import serialize_dosha_day


def compute_dosha_day(engine: Moira, request: DoshaDayRequest):
    return serialize_dosha_day(engine.muhurta_doshas_for_date(
        request.local_date, request.latitude, request.longitude, timezone=request.timezone,
        necessary_activity=request.necessary_activity, policy=request.policy.to_engine()))
