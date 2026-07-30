"""Shared sidereal chart context adapter tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from moira import Moira
from moira.sidereal import ayanamsa
from moira_server.models.sidereal_context import SiderealChartBaseRequest
from moira_server.serializers.sidereal_context import (
    serialize_sidereal_chart_context,
    serialize_sidereal_chart_provenance,
)
from moira_server.services.sidereal_context import (
    SIDEREAL_CONTEXT_STAGE_SEQUENCE,
    SiderealChartRequirements,
    derive_sidereal_chart_context,
)

def _engine() -> Moira:
    return Moira()


def _request(**updates) -> SiderealChartBaseRequest:
    payload = {
        "dt": datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        "ayanamsa_system": "Lahiri",
        "bodies": ["Sun", "Moon"],
    }
    payload.update(updates)
    return SiderealChartBaseRequest(**payload)


def test_sidereal_context_request_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _request(dt=datetime(2000, 1, 1, 12, 0))


def test_sidereal_context_request_rejects_empty_ayanamsa() -> None:
    with pytest.raises(ValidationError, match="ayanamsa_system"):
        _request(ayanamsa_system="")


def test_sidereal_context_request_rejects_empty_body_list() -> None:
    with pytest.raises(ValidationError, match="bodies"):
        _request(bodies=[])


def test_sidereal_context_request_rejects_non_finite_observer() -> None:
    with pytest.raises(ValidationError, match="observer"):
        _request(observer_lat=float("nan"), observer_lon=0.0)


def test_sidereal_context_requirements_reject_empty_required_bodies() -> None:
    with pytest.raises(ValueError, match="required_bodies"):
        SiderealChartRequirements(required_bodies=())


def test_sidereal_context_requirements_reject_unsupported_body() -> None:
    with pytest.raises(ValueError, match="unsupported chart bodies"):
        SiderealChartRequirements(required_bodies=("NotAPlanet",))


def test_sidereal_context_rejects_missing_observer_when_lagna_required() -> None:
    request = _request()
    requirements = SiderealChartRequirements(
        required_bodies=("Sun",),
        require_lagna=True,
    )

    with pytest.raises(ValueError, match="observer latitude and longitude"):
        derive_sidereal_chart_context(_engine(), request, requirements)


def test_sidereal_context_derives_sidereal_longitudes_and_sign_indices() -> None:
    request = _request()
    requirements = SiderealChartRequirements(required_bodies=("Sun", "Moon"))

    context = derive_sidereal_chart_context(_engine(), request, requirements)

    assert context.stage_sequence == SIDEREAL_CONTEXT_STAGE_SEQUENCE
    assert context.requested_bodies == ("Sun", "Moon")
    offset = ayanamsa(context.jd_ut, "Lahiri")
    assert context.ayanamsa_offset == offset
    for body, tropical in context.tropical_longitudes.items():
        expected = (tropical - offset) % 360.0
        assert context.sidereal_longitudes[body] == expected
        assert context.sidereal_sign_indices[body] == int(expected // 30.0)


def test_sidereal_context_includes_required_bodies_when_caller_omits_them() -> None:
    request = _request(bodies=["Moon"])
    requirements = SiderealChartRequirements(required_bodies=("Sun",))

    context = derive_sidereal_chart_context(_engine(), request, requirements)

    assert context.requested_bodies == ("Sun", "Moon")
    assert "Sun" in context.sidereal_longitudes
    assert "Moon" in context.sidereal_longitudes


def test_sidereal_context_derives_speeds_only_when_required() -> None:
    request = _request()

    no_speeds = derive_sidereal_chart_context(
        _engine(),
        request,
        SiderealChartRequirements(required_bodies=("Sun",)),
    )
    with_speeds = derive_sidereal_chart_context(
        _engine(),
        request,
        SiderealChartRequirements(required_bodies=("Sun",), require_speeds=True),
    )

    assert no_speeds.speeds is None
    assert with_speeds.speeds is not None
    assert "Sun" in with_speeds.speeds


def test_sidereal_context_derives_lagna_only_when_required() -> None:
    request = _request(observer_lat=51.5, observer_lon=-0.1)

    without_lagna = derive_sidereal_chart_context(
        _engine(),
        request,
        SiderealChartRequirements(required_bodies=("Sun",)),
    )
    with_lagna = derive_sidereal_chart_context(
        _engine(),
        request,
        SiderealChartRequirements(required_bodies=("Sun",), require_lagna=True),
    )

    assert without_lagna.tropical_lagna is None
    assert without_lagna.houses is None
    assert with_lagna.tropical_lagna is not None
    assert with_lagna.sidereal_lagna is not None
    assert with_lagna.sidereal_lagna_sign_index == int(with_lagna.sidereal_lagna // 30.0)
    assert with_lagna.houses is not None


def test_sidereal_context_is_frozen_and_mapping_truth_is_immutable() -> None:
    context = derive_sidereal_chart_context(
        _engine(),
        _request(),
        SiderealChartRequirements(required_bodies=("Sun",)),
    )

    with pytest.raises(FrozenInstanceError):
        context.ayanamsa_system = "Fagan-Bradley"  # type: ignore[misc]
    with pytest.raises(TypeError):
        context.sidereal_longitudes["Sun"] = 0.0  # type: ignore[index]


def test_sidereal_context_repeated_requests_do_not_share_ayanamsa_state() -> None:
    requirements = SiderealChartRequirements(required_bodies=("Sun",))

    lahiri = derive_sidereal_chart_context(_engine(), _request(ayanamsa_system="Lahiri"), requirements)
    fagan = derive_sidereal_chart_context(
        _engine(),
        _request(ayanamsa_system="Fagan-Bradley"),
        requirements,
    )

    assert lahiri.ayanamsa_system == "Lahiri"
    assert fagan.ayanamsa_system == "Fagan-Bradley"
    assert lahiri.ayanamsa_offset != fagan.ayanamsa_offset
    assert lahiri.sidereal_longitudes["Sun"] != fagan.sidereal_longitudes["Sun"]


def test_sidereal_context_serializers_preserve_provenance() -> None:
    context = derive_sidereal_chart_context(
        _engine(),
        _request(observer_lat=51.5, observer_lon=-0.1),
        SiderealChartRequirements(
            required_bodies=("Sun",),
            require_lagna=True,
            require_speeds=True,
        ),
    )

    provenance = serialize_sidereal_chart_provenance(context)
    full = serialize_sidereal_chart_context(context)

    assert provenance.ayanamsa_system == context.ayanamsa_system
    assert provenance.sidereal_longitudes == dict(context.sidereal_longitudes)
    assert provenance.sidereal_lagna == context.sidereal_lagna
    assert full.tropical_longitudes == dict(context.tropical_longitudes)
    assert full.sidereal_sign_indices == dict(context.sidereal_sign_indices)
    assert full.speeds == dict(context.speeds)
    assert full.houses is not None
