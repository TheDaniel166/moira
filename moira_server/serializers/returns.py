"""Serializers for return endpoints."""

from __future__ import annotations

from moira import datetime_from_jd

from ..models.returns import ReturnEventResponse


def serialize_return_event(
    *,
    return_type: str,
    body: str,
    jd_ut: float,
) -> ReturnEventResponse:
    return ReturnEventResponse(
        return_type=return_type,
        body=body,
        jd_ut=jd_ut,
        datetime_utc=datetime_from_jd(jd_ut).isoformat(),
    )


__all__ = ["serialize_return_event"]
