"""Reader-bound public lunar-month facade delegation."""
from moira import Moira
from moira.lunar_month import LunarMonthPolicy, LunarMonthResult
from ..models.lunar_month import LunarMonthRequest


def compute_lunar_month(engine: Moira, request: LunarMonthRequest) -> LunarMonthResult:
    return engine.lunar_month_at(request.jd_ut1, policy=LunarMonthPolicy(**request.policy.model_dump()))
