"""Route dated Shuddhi through the serving engine's existing reader."""
from moira import Moira
from ..models.panchanga_shuddhi import ShuddhiDayRequest
from ..serializers.panchanga_shuddhi import serialize_shuddhi_day


def compute_shuddhi_day(engine: Moira, request: ShuddhiDayRequest):
    return serialize_shuddhi_day(engine.panchanga_shuddhi_for_date(
        request.local_date, request.latitude, request.longitude, timezone=request.timezone,
        natal_nakshatra_index=request.natal_nakshatra_index, policy=request.policy.to_engine()))
