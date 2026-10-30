"""Transport-to-engine adapters for Lilly P2 reception and P3 Moon / void of course."""

from __future__ import annotations

from moira import Moira
from moira.horary_moon import (
    LillyMoonSearchPolicy,
    LillyMoonSequence,
    LillyMoonTrace,
    LillyVOCDefinition,
    LillyVOCResult,
    lilly_moon_sequence,
    lilly_void_of_course,
)
from moira.horary_reception import LillyReceptionNetwork

from ..models.horary_lilly import LillyMoonRequest, LillyReceptionRequest


def compute_lilly_reception(engine: Moira, request: LillyReceptionRequest) -> LillyReceptionNetwork:
    """Delegate once to the facade."""

    return engine.lilly_reception_at(request.jd_ut, is_day_chart=request.is_day_chart, epoch=request.epoch_label)


def compute_lilly_moon(
    engine: Moira, request: LillyMoonRequest,
) -> tuple[LillyMoonTrace, LillyMoonSequence, LillyVOCResult]:
    """Trace once through the facade, then derive the sequence and the selected definition."""

    search = request.search
    policy = (LillyMoonSearchPolicy() if search is None
              else LillyMoonSearchPolicy(past_days=search.past_days, future_days=search.future_days))
    trace = engine.lilly_moon_trace_at(request.jd_ut, is_day_chart=request.is_day_chart, policy=policy,
                                       epoch=request.epoch_label)
    voc = lilly_void_of_course(trace, definition=LillyVOCDefinition(request.voc_definition))
    return trace, lilly_moon_sequence(trace), voc


__all__ = ["compute_lilly_moon", "compute_lilly_reception"]
