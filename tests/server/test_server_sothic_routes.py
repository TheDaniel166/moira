"""Bounded Sothic REST contract tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import moira.sothic as sothic
from moira.spk_reader import MissingEphemerisKernelError
from moira.star_types import (
    HeliacalEvent,
    HeliacalEventClassification,
    HeliacalEventTruth,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeEngine:
    _reader = None


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _event(
    jd_start: float,
    *,
    event_jd: float | None,
    arcus_visionis: float,
    search_days: int,
) -> HeliacalEvent:
    found = event_jd is not None
    return HeliacalEvent(
        event_kind="heliacal_rising",
        star_name="Sirius",
        jd_ut=event_jd,
        is_found=found,
        computation_truth=HeliacalEventTruth(
            event_kind="heliacal_rising",
            star_name="Sirius",
            jd_start=jd_start,
            search_days=search_days,
            arcus_visionis=arcus_visionis,
            elongation_threshold=0.0,
            conjunction_offset=None,
            qualifying_day_offset=180 if found else None,
            qualifying_elongation=-10.0 if found else None,
            qualifying_sun_altitude=-arcus_visionis if found else None,
            event_jd_ut=event_jd,
        ),
        classification=HeliacalEventClassification(
            event_kind="heliacal_rising",
            search_kind="forward_visibility_scan",
            visibility_state="found" if found else "not_found",
        ),
    )


def _assert_validation(response, message_fragment: str) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert message_fragment in body["message"]


def test_egyptian_date_route_exposes_anchor_calendar_semantics(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/sothic/egyptian-date",
        json={"jd": 1772027.5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["date"] == {
        "month_name": "Thoth",
        "month_number": 1,
        "day": 1,
        "season": "Akhet",
        "day_of_year": 1,
        "epagomenal_birth": None,
    }
    assert body["anchor"]["anchor_id"] == "censorinus_139_calendar_anchor"
    assert body["anchor"]["julian_calendar_date"] == "0139-07-20"
    assert body["anchor"]["proleptic_gregorian_date"] == "0139-07-19"
    assert body["anchor"]["evidence_kind"] == "primary_text_calendar_anchor"
    assert body["provenance"]["calendar_basis"] == "egyptian_civil_mod_365"

    custom = client.post(
        "/v1/sothic/egyptian-date",
        json={"jd": 1772027.5, "epoch_jd": 1772026.5},
    )
    assert custom.status_code == 200
    custom_body = custom.json()
    assert custom_body["anchor"]["anchor_id"] == "caller_supplied_epoch_jd"
    assert custom_body["anchor"]["evidence_kind"] == (
        "caller_supplied_calendar_anchor"
    )
    assert custom_body["date"]["day"] == 2


def test_prediction_route_labels_fixed_cycle_output_as_schematic(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/sothic/predict-epoch",
        json={"known_epoch_year": 139, "n_cycles": -1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["predicted_astronomical_year"] == pytest.approx(-1321.0)
    assert body["year_numbering"] == "astronomical"
    assert body["model"] == "schematic_1460_julian_year"
    assert body["evidence_kind"] == "schematic_projection"

    custom = client.post(
        "/v1/sothic/predict-epoch",
        json={
            "known_epoch_year": 139,
            "n_cycles": 1,
            "cycle_length_years": 1500.0,
        },
    )
    assert custom.status_code == 200
    custom_body = custom.json()
    assert custom_body["predicted_astronomical_year"] == pytest.approx(1639.0)
    assert custom_body["model"] == "custom_fixed_year_interval"
    assert custom_body["evidence_kind"] == "schematic_projection"


def test_rising_route_returns_one_explicit_outcome_per_year(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def _search(_name, jd_start, _latitude, _longitude, **kwargs):
        nonlocal calls
        calls += 1
        event_jd = 1772026.592026045 if calls == 1 else None
        return _event(
            jd_start,
            event_jd=event_jd,
            arcus_visionis=kwargs["arcus_visionis"],
            search_days=kwargs["search_days"],
        )

    monkeypatch.setattr(sothic, "_heliacal_rising_event", _search)
    response = client.post(
        "/v1/sothic/rising",
        json={
            "latitude_deg": 29.8,
            "longitude_deg": 31.3,
            "year_start": 139,
            "year_end": 140,
            "arcus_visionis_deg": 10.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_year_count"] == 2
    assert body["found_count"] == 1
    assert body["not_found_within_window_count"] == 1
    assert [outcome["status"] for outcome in body["outcomes"]] == [
        "found",
        "not_found_within_window",
    ]
    assert body["outcomes"][0]["entry"]["calendar_year"] == 139
    assert body["outcomes"][0]["event"]["visibility_state"] == "found"
    assert body["outcomes"][1]["entry"] is None
    assert body["outcomes"][1]["event"]["visibility_state"] == "not_found"
    assert body["provenance"]["delegated_source"] == (
        "moira.stars.heliacal_rising_event"
    )
    assert body["provenance"]["cycle_model"] == (
        "schematic_1460_julian_year_cycle_position_only"
    )
    assert body["provenance"]["route_max_years"] == 200


def test_rising_route_preserves_missing_kernel_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail(*_args, **_kwargs):
        raise MissingEphemerisKernelError("DE441 is not configured")

    monkeypatch.setattr(sothic, "_heliacal_rising_event", _fail)
    response = client.post(
        "/v1/sothic/rising",
        json={
            "latitude_deg": 29.8,
            "longitude_deg": 31.3,
            "year_start": 139,
            "year_end": 139,
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == "kernel_not_ready"
    assert body["category"] == "kernel_readiness"


def test_rising_route_rejects_reversed_oversized_and_out_of_model_requests(
    client: TestClient,
) -> None:
    reversed_range = client.post(
        "/v1/sothic/rising",
        json={
            "latitude_deg": 29.8,
            "longitude_deg": 31.3,
            "year_start": 140,
            "year_end": 139,
        },
    )
    oversized = client.post(
        "/v1/sothic/rising",
        json={
            "latitude_deg": 29.8,
            "longitude_deg": 31.3,
            "year_start": 0,
            "year_end": 200,
        },
    )
    invalid_arcus = client.post(
        "/v1/sothic/rising",
        json={
            "latitude_deg": 29.8,
            "longitude_deg": 31.3,
            "year_start": 139,
            "year_end": 139,
            "arcus_visionis_deg": 13.0,
        },
    )

    _assert_validation(reversed_range, "year_end must be greater")
    _assert_validation(oversized, "limited to 200 years")
    _assert_validation(invalid_arcus, "less than or equal to 12")


def test_sothic_openapi_surface_is_typed(client: TestClient) -> None:
    schema = client.app.openapi()

    assert set(path for path in schema["paths"] if path.startswith("/v1/sothic/")) == {
        "/v1/sothic/egyptian-date",
        "/v1/sothic/predict-epoch",
        "/v1/sothic/rising",
    }
    operation = schema["paths"]["/v1/sothic/rising"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SothicRisingRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SothicRisingResponse"
    }
