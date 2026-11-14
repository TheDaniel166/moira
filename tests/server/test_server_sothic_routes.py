"""Bounded Sothic REST contract tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import moira.sothic as sothic
from moira.spk_reader import MissingEphemerisKernelError, use_reader_override
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


@pytest.mark.parametrize("operation", ("rising", "drift-rate"))
def test_annual_routes_preserve_missing_kernel_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    def _fail(*_args, **_kwargs):
        raise MissingEphemerisKernelError("DE441 is not configured")

    monkeypatch.setattr(sothic, "_heliacal_rising_event", _fail)
    response = client.post(
        f"/v1/sothic/{operation}",
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


@pytest.mark.parametrize("operation", ("rising", "drift-rate"))
def test_annual_routes_reject_reversed_oversized_and_out_of_model_requests(
    client: TestClient,
    operation: str,
) -> None:
    path = f"/v1/sothic/{operation}"
    reversed_range = client.post(
        path,
        json={
            "latitude_deg": 29.8,
            "longitude_deg": 31.3,
            "year_start": 140,
            "year_end": 139,
        },
    )
    oversized = client.post(
        path,
        json={
            "latitude_deg": 29.8,
            "longitude_deg": 31.3,
            "year_start": 0,
            "year_end": 200,
        },
    )
    invalid_arcus = client.post(
        path,
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


def _stub_annual_drifts(
    monkeypatch: pytest.MonkeyPatch,
    year_start: int,
    drifts: list[float | None],
    epoch_jd: float,
) -> list[float]:
    offsets_by_start = {
        sothic.julian_day(year, 1, 1): drift
        for year, drift in enumerate(drifts, start=year_start)
    }
    calls: list[float] = []

    def _search(_name, jd_start, *_args, **kwargs):
        calls.append(jd_start)
        drift = offsets_by_start[jd_start]
        # Choose a day in the 365-day interval with the prescribed civil offset.
        event_jd = None if drift is None else jd_start + (drift - (jd_start - epoch_jd)) % 365
        return _event(
            jd_start,
            event_jd=event_jd,
            arcus_visionis=kwargs["arcus_visionis"],
            search_days=kwargs["search_days"],
        )

    monkeypatch.setattr(sothic, "_heliacal_rising_event", _search)
    return calls


@pytest.mark.parametrize(("initial_drift", "rate"), [(364.5, 0.25), (0.5, -0.25)])
def test_drift_rate_uses_actual_year_spacing_and_unwraps_across_gaps(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    initial_drift: float,
    rate: float,
) -> None:
    year_start, year_end = 139, 145
    years = list(range(year_start, year_end + 1))
    missing = {141, 144}
    expected = {year: initial_drift + rate * (year - year_start) for year in years if year not in missing}
    raw = [expected[year] % 365 if year in expected else None for year in years]
    epoch_jd = 1772044.5
    calls = _stub_annual_drifts(monkeypatch, year_start, raw, epoch_jd)
    payload = {
        "latitude_deg": 29.8,
        "longitude_deg": 31.3,
        "year_start": year_start,
        "year_end": year_end,
        "epoch_jd": epoch_jd,
        "arcus_visionis_deg": 9.0,
    }

    response = client.post("/v1/sothic/drift-rate", json=payload)
    assert response.status_code == 200, response.text
    assert calls == [sothic.julian_day(year, 1, 1) for year in years]
    body = response.json()
    rising = body["rising"]
    assert rising == client.post("/v1/sothic/rising", json=payload).json()
    assert rising["anchor"]["evidence_kind"] == "caller_supplied_calendar_anchor"
    assert rising["anchor"]["jd"] == epoch_jd
    assert rising["arcus_visionis_deg"] == 9.0
    assert rising["found_count"] == 5
    assert [row["year"] for row in rising["outcomes"]] == years
    assert {
        row["year"] for row in rising["outcomes"] if row["status"] == "not_found_within_window"
    } == missing

    fit = body["fit"]
    assert fit["status"] == "estimated"
    assert fit["rate_days_per_year"] == pytest.approx(rate, abs=1e-12, rel=0)
    assert fit["method"] == "ordinary_least_squares"
    assert fit["calendar_year_days"] == 365
    assert fit["missing_year_policy"] == "exclude_without_imputation"
    assert fit["wrap_policy"] == "shortest_signed_step_between_found_years"
    assert fit["samples"] == [
        {"year": year, "drift_days": unwrapped % 365, "unwrapped_drift_days": unwrapped}
        for year, unwrapped in expected.items()
    ]


def test_drift_rate_keeps_the_signed_half_cycle_step_and_a_zero_estimate(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    drifts = [0.0, 182.5, 0.0, 182.5, 0.0]
    _stub_annual_drifts(monkeypatch, 139, drifts, sothic.CENSORINUS_139_ANCHOR.jd)
    response = client.post(
        "/v1/sothic/drift-rate",
        json={"latitude_deg": 29.8, "longitude_deg": 31.3, "year_start": 139, "year_end": 143},
    )

    assert response.status_code == 200, response.text
    fit = response.json()["fit"]
    assert fit["status"] == "estimated"
    assert fit["rate_days_per_year"] == 0.0
    assert fit["half_cycle_tie_policy"] == "retain_signed_step"
    assert [row["unwrapped_drift_days"] for row in fit["samples"]] == drifts


@pytest.mark.parametrize(("found_count", "requested_count"), [(0, 6), (4, 6), (1, 1)])
def test_drift_rate_returns_annual_evidence_when_there_are_too_few_found_years(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    found_count: int,
    requested_count: int,
) -> None:
    drifts = [2.0] * found_count + [None] * (requested_count - found_count)
    _stub_annual_drifts(monkeypatch, 139, drifts, sothic.CENSORINUS_139_ANCHOR.jd)
    response = client.post(
        "/v1/sothic/drift-rate",
        json={
            "latitude_deg": 29.8,
            "longitude_deg": 31.3,
            "year_start": 139,
            "year_end": 138 + requested_count,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rising"]["found_count"] == found_count
    assert body["rising"]["not_found_within_window_count"] == requested_count - found_count
    assert len(body["rising"]["outcomes"]) == requested_count
    assert body["fit"]["status"] == "insufficient_found_years"
    assert body["fit"]["minimum_found_years"] == 5
    assert body["fit"]["rate_days_per_year"] is None
    assert body["fit"]["samples"] == []


@pytest.mark.requires_ephemeris
def test_drift_rate_matches_the_de441_annual_series_and_engine_slope(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as real_client:
        response = real_client.post(
            "/v1/sothic/drift-rate",
            json={"latitude_deg": 29.8, "longitude_deg": 31.3, "year_start": 139, "year_end": 144},
        )
    with use_reader_override(moira_engine._reader):
        series = sothic.sothic_rising_series(29.8, 31.3, 139, 144)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rising"]["found_count"] == series.found_count
    assert [row["status"] for row in body["rising"]["outcomes"]] == [
        outcome.status.value for outcome in series.outcomes
    ]
    assert body["fit"]["status"] == "estimated"
    assert body["fit"]["rate_days_per_year"] == sothic.sothic_drift_rate(list(series.entries))
    assert [(row["year"], row["drift_days"]) for row in body["fit"]["samples"]] == [
        (entry.year, entry.drift_days) for entry in series.entries
    ]


def test_sothic_openapi_surface_is_typed(client: TestClient) -> None:
    schema = client.app.openapi()

    assert set(path for path in schema["paths"] if path.startswith("/v1/sothic/")) == {
        "/v1/sothic/egyptian-date",
        "/v1/sothic/predict-epoch",
        "/v1/sothic/rising",
        "/v1/sothic/drift-rate",
    }
    for path, response in (("rising", "SothicRisingResponse"), ("drift-rate", "SothicDriftRateResponse")):
        operation = schema["paths"][f"/v1/sothic/{path}"]["post"]
        assert operation["requestBody"]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/SothicRisingRequest"
        }
        assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{response}"
        }
    drift = schema["paths"]["/v1/sothic/drift-rate"]["post"]
    for code in ("422", "503"):
        assert drift["responses"][code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorEnvelope"
        }
