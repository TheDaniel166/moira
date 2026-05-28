"""Phase-5 visibility service helpers."""

from __future__ import annotations

from moira import Moira
from moira.sky.visibility import visibility_assessment
from moira.spk_reader import use_reader_override

from ..models.visibility import VisibilityAssessmentRequest


def compute_visibility_assessment(engine: Moira, request: VisibilityAssessmentRequest):
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return visibility_assessment(
            request.body,
            request.jd_ut,
            request.lat,
            request.lon,
        )


def compute_visibility_tonight(engine: Moira, request: VisibilityAssessmentRequest):
    return engine.visibility_tonight(request.body, request.jd_ut, request.lat, request.lon)


__all__ = [
    "compute_visibility_assessment",
    "compute_visibility_tonight",
]
