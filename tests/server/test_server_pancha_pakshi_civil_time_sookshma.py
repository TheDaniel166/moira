"""Strict REST contracts for Stage 2O civil-time Sookshma routing."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

import moira._ephemeris_time as ephemeris_time
import moira._local_solar_day as local_solar_day
import moira.pancha_pakshi as pakshi
import moira_server.models as public_models
from moira._local_solar_day import LocalSolarDay
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.pancha_pakshi import (
    PanchaPakshiCivilTimeSookshmaSelectionRequest,
    PanchaPakshiCivilTimeSookshmaSelectionResponse,
)
from moira_server.serializers.pancha_pakshi import (
    serialize_civil_time_sookshma_selection,
)
from moira_server.services.pancha_pakshi import (
    compute_civil_time_sookshma_selection,
)


_SCHEDULE = "agastya_madras_1879_akshara_fixed_clock"
_SELECTOR = "bogamuni_chennai_2024_sookshma_temporal_selector"
_ROUTE = "/v1/pancha-pakshi/sookshma/civil-time-select"
_FIXED = "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
_PROPORTIONAL = "solar_proportional_nominal_offsets_over_governing_half_tt_v1"
_WEIGHTED = "bogamuni_2024_weighted_sookshma_samam_v1"
_EQUAL = "bogamuni_2024_eka_sookshma_equal_fifths_v1"
_SUNRISE = 2_460_000.0
_READER = object()


def _engine_result(
    monkeypatch: pytest.MonkeyPatch,
    *,
    requested_jd_ut1: float = _SUNRISE,
    solar_half_hours: float = 12.0,
):
    solar_day = LocalSolarDay(
        jd=requested_jd_ut1,
        latitude=13.0827,
        longitude=80.2707,
        sunrise_jd=_SUNRISE,
        sunset_jd=_SUNRISE + solar_half_hours / 24.0,
        next_sunrise_jd=_SUNRISE + 1.0,
        weekday=0,
    )
    monkeypatch.setattr(
        ephemeris_time,
        "_ut1_to_ephemeris_tt",
        lambda jd, reader: jd + 100.0 / 86_400.0,
    )
    monkeypatch.setattr(
        ephemeris_time,
        "_ephemeris_tt_to_ut1",
        lambda jd, reader: jd - 100.0 / 86_400.0,
    )
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: solar_day,
    )
    return pakshi.pancha_pakshi_civil_time_sookshma_selection_at(
        _SCHEDULE,
        _SELECTOR,
        requested_jd_ut1,
        13.0827,
        80.2707,
        profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
        subject_bird=pakshi.PanchaPakshiBird.CROW,
        timing_policy_id=pakshi.PanchaPakshiSookshmaTimingPolicyId.FIXED_CLOCK,
        selector_policy_id=(
            pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA
        ),
        reader=_READER,  # type: ignore[arg-type]
    )


class _FakeEngine:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def pancha_pakshi_civil_time_sookshma_selection(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result


@pytest.fixture
def routed_client(monkeypatch: pytest.MonkeyPatch):
    engine = _FakeEngine(_engine_result(monkeypatch))
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine


def _payload() -> dict[str, object]:
    return {
        "schedule_profile_id": _SCHEDULE,
        "selector_profile_id": _SELECTOR,
        "dt": "2026-07-21T00:00:00Z",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "profile_paksha": "purva",
        "subject_bird": "crow",
        "timing_policy_id": _FIXED,
        "selector_policy_id": _WEIGHTED,
    }


def test_service_passes_every_explicit_axis_and_serializer_preserves_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _engine_result(monkeypatch)
    engine = _FakeEngine(result)
    request = PanchaPakshiCivilTimeSookshmaSelectionRequest(**_payload())
    computed = compute_civil_time_sookshma_selection(engine, request)
    response = serialize_civil_time_sookshma_selection(computed)

    assert computed is result
    args, kwargs = engine.calls[0]
    assert args[:2] == (_SCHEDULE, _SELECTOR)
    assert args[2] == datetime(2026, 7, 21, tzinfo=timezone.utc)
    assert kwargs["timing_policy_id"] is (
        pakshi.PanchaPakshiSookshmaTimingPolicyId.FIXED_CLOCK
    )
    assert kwargs["selector_policy_id"] is (
        pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA
    )
    assert response.selection_status == "selected"
    assert response.subject_bird is pakshi.PanchaPakshiBird.CROW
    assert response.elapsed_nazhigai is not None
    assert response.elapsed_nazhigai.model_dump() == {
        "numerator": 0,
        "denominator": 1,
    }
    assert response.composition is not None


@pytest.mark.loopback
def test_route_returns_the_full_explicit_stage2o_contract(routed_client) -> None:
    client, engine = routed_client
    response = client.post(_ROUTE, json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["timing_policy_id"] == _FIXED
    assert body["selector_policy_id"] == _WEIGHTED
    assert body["subject_bird"] == "crow"
    assert body["routing_policy"]["automatic_timing_fallback"] == "forbidden"
    assert body["current_cell_selection"]["selection_status"] == "selected"
    assert body["composition"]["sookshma_selection"]["selected_ordinal"] == 1
    assert len(engine.calls) == 1


def test_serializer_preserves_fixed_tail_without_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _engine_result(
        monkeypatch,
        requested_jd_ut1=_SUNRISE + 13.0 / 24.0,
        solar_half_hours=14.0,
    )
    response = serialize_civil_time_sookshma_selection(result)
    assert response.selection_status == "unmaterialized_solar_half_tail"
    assert response.current_cell_selection.selection_status == (
        "unmaterialized_solar_half_tail"
    )
    assert response.current_cell_selection.current_cell is None
    assert response.samam_index is None
    assert response.elapsed_nazhigai is None
    assert response.composition is None


@pytest.mark.loopback
@pytest.mark.parametrize("removed", tuple(_payload()))
def test_route_has_no_default_for_any_stage2o_axis(
    routed_client,
    removed: str,
) -> None:
    client, _ = routed_client
    payload = _payload()
    payload.pop(removed)
    response = client.post(_ROUTE, json=payload)
    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.loopback
def test_openapi_names_both_policy_sets_and_excludes_outcome_inputs(
    routed_client,
) -> None:
    client, _ = routed_client
    schema = client.app.openapi()
    request = schema["components"]["schemas"][
        "PanchaPakshiCivilTimeSookshmaSelectionRequest"
    ]
    response = schema["components"]["schemas"][
        "PanchaPakshiCivilTimeSookshmaSelectionResponse"
    ]
    assert request["additionalProperties"] is False
    assert set(request["required"]) == set(request["properties"])
    assert request["properties"]["timing_policy_id"]["enum"] == [
        _FIXED,
        _PROPORTIONAL,
    ]
    assert request["properties"]["selector_policy_id"]["enum"] == [
        _WEIGHTED,
        _EQUAL,
    ]
    assert not {"outcome", "condition", "score", "forecast"} & set(
        request["properties"]
    )
    assert response["additionalProperties"] is False
    assert public_models.PanchaPakshiCivilTimeSookshmaSelectionRequest is (
        PanchaPakshiCivilTimeSookshmaSelectionRequest
    )
    assert public_models.PanchaPakshiCivilTimeSookshmaSelectionResponse is (
        PanchaPakshiCivilTimeSookshmaSelectionResponse
    )
