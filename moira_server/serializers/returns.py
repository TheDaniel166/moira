"""Serializers for return endpoints."""

from __future__ import annotations

from moira import datetime_from_jd

from ..models.returns import ReturnEventResponse
from .transits import serialize_transit_computation_truth
from moira.transits import TransitComputationTruth


def serialize_return_event(
    *,
    return_type: str,
    body: str,
    jd_ut: float,
    computation_truth: TransitComputationTruth | None = None,
) -> ReturnEventResponse:
    resp = ReturnEventResponse(
        return_type=return_type,
        body=body,
        jd_ut=jd_ut,
        datetime_utc=datetime_from_jd(jd_ut).isoformat(),
    )
    if computation_truth is not None:
        resp.computation_truth = serialize_transit_computation_truth(computation_truth)
    return resp


__all__ = ["serialize_return_event"]
