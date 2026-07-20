"""Admission tests for named, source-scoped Pancha Pakshi REST routes."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira.pancha_pakshi import (
    PanchaPakshiHalf,
    PanchaPakshiPaksha,
    PanchaPakshiWeekday,
    pancha_pakshi_schedule,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network

_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _assert_validation_envelope(response, *, message_fragment: str) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    assert message_fragment in body["message"]


def _fixed_clock_current_cell_selection(*, tail: bool) -> SimpleNamespace:
    schedule = pancha_pakshi_schedule(
        _PROFILE_ID,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )
    anchor_jd_tt = 2461241.9998
    tt_minus_ut1_days = 69.0 / 86400.0
    fixed_end_jd_tt = anchor_jd_tt + 0.5
    governing_end_jd_tt = anchor_jd_tt + (13.0 if tail else 11.0) / 24.0
    requested_jd_tt = (
        fixed_end_jd_tt + 0.02 if tail else anchor_jd_tt + 0.01
    )
    current_cell = None
    if not tail:
        nominal_cell = schedule.cells[0]
        current_cell = SimpleNamespace(
            schedule_cell_index=0,
            nominal_cell=nominal_cell,
            start_jd_tt=anchor_jd_tt,
            end_jd_tt=(
                anchor_jd_tt
                + float(nominal_cell.end_nazhigai) / 60.0
            ),
            start_jd_ut1=anchor_jd_tt - tt_minus_ut1_days,
            end_jd_ut1=(
                anchor_jd_tt
                + float(nominal_cell.end_nazhigai) / 60.0
                - tt_minus_ut1_days
            ),
            duration_seconds=nominal_cell.duration_nazhigai * 1440,
            solar_half_relation="within_governing_solar_half",
        )

    context = SimpleNamespace(
        profile_id=_PROFILE_ID,
        requested_jd_ut1=requested_jd_tt - tt_minus_ut1_days,
        latitude=13.0827,
        longitude=80.2707,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )
    materialization = SimpleNamespace(
        context=context,
        anchor_jd_tt=anchor_jd_tt,
        anchor_jd_ut1=anchor_jd_tt - tt_minus_ut1_days,
        governing_solar_half_end_jd_tt=governing_end_jd_tt,
        governing_solar_half_end_jd_ut1=(
            governing_end_jd_tt - tt_minus_ut1_days
        ),
        fixed_end_jd_tt=fixed_end_jd_tt,
        fixed_end_jd_ut1=fixed_end_jd_tt - tt_minus_ut1_days,
        signed_fixed_end_minus_solar_end_seconds_tt=(
            fixed_end_jd_tt - governing_end_jd_tt
        )
        * 86400.0,
        solar_boundary_relation=(
            "ends_before_solar_boundary" if tail else "ends_after_solar_boundary"
        ),
    )
    policy = SimpleNamespace(
        policy_id="fixed_clock_current_cell_half_open_solar_precedence_v1",
        materialization_policy_id=(
            "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
        ),
        paksha_basis="caller_supplied_source_label",
        selection_time_scale="reader_bound_tt",
        interval_ownership="half_open",
        solar_half_precedence="resolve_governing_solar_half_before_selection",
        membership_tolerance_seconds=0.0,
        unmaterialized_solar_half_tail="explicit_no_current_cell",
        solar_end_clipping="none",
        fixed_span_wrap="none",
        fixed_span_repeat="none",
        solar_proportional_scaling_status="not_performed",
        astronomical_paksha_inference_status="not_performed",
    )
    return SimpleNamespace(
        materialization=materialization,
        policy=policy,
        requested_jd_tt=requested_jd_tt,
        selection_status=(
            "unmaterialized_solar_half_tail" if tail else "selected"
        ),
        current_cell=current_cell,
        provenance=replace(
            schedule.provenance,
            astronomical_routing_status=(
                "fixed_clock_current_cell_selection_performed_"
                "paksha_caller_supplied_no_scaling_or_inference"
            ),
        ),
    )


def test_profiles_and_profile_info_expose_source_scope_without_a_default(
    client: TestClient,
) -> None:
    profiles = client.get("/v1/pancha-pakshi/profiles")

    assert profiles.status_code == 200
    catalog = profiles.json()
    assert catalog["default_profile_selected"] is False
    assert catalog["total"] >= 1
    descriptor = next(item for item in catalog["profiles"] if item["profile_id"] == _PROFILE_ID)
    assert descriptor["admission_status"] == "source_scoped_public"
    assert descriptor["default_selection_allowed"] is False
    assert set(descriptor["capabilities"]) >= {
        "aksara_identity",
        "nominal_schedule",
        "directed_relationships",
    }

    response = client.get(f"/v1/pancha-pakshi/profiles/{_PROFILE_ID}")

    assert response.status_code == 200
    body = response.json()
    provenance = body["provenance"]
    assert provenance["profile_id"] == _PROFILE_ID
    assert provenance["astronomical_routing_status"] == "not_performed"
    assert provenance["default_selection_allowed"] is False
    assert body["source_locators"]
    assert {item["feature"] for item in provenance["declared_omissions"]} >= {
        "natal_mapping",
        "scoring",
        "seasonal_scaling",
    }


def test_aksara_identity_route_is_explicit_and_not_natal(client: TestClient) -> None:
    response = client.post(
        "/v1/pancha-pakshi/identity/aksara",
        json={"profile_id": _PROFILE_ID, "initial_vowel": "A"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == _PROFILE_ID
    assert body["bird"] == "vulture"
    assert body["is_natal_moon_identity"] is False
    assert body["source_locators"]
    assert body["provenance"]["astronomical_routing_status"] == "not_performed"


def test_nominal_schedule_preserves_exact_fractional_time_and_source_context(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/pancha-pakshi/schedule/nominal",
        json={
            "profile_id": _PROFILE_ID,
            "paksha": "purva",
            "half": "day",
            "weekday": "sunday",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["temporal_model_kind"] == "fixed_nominal_nazhigai_halves"
    assert body["span_nazhigai"] == {"numerator": 30, "denominator": 1}
    assert len(body["cells"]) == 25
    first = body["cells"][0]
    assert first["start_nazhigai"] == {"numerator": 0, "denominator": 1}
    assert first["duration_nazhigai"] == {"numerator": 5, "denominator": 4}
    assert first["source_locators"]
    assert body["provenance"]["astronomical_routing_status"] == "not_performed"


def test_local_solar_context_route_is_policy_explicit_and_does_not_materialize_offsets(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schedule = pancha_pakshi_schedule(
        _PROFILE_ID,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )
    context = SimpleNamespace(
        profile_id=_PROFILE_ID,
        requested_jd_ut1=2461242.1667,
        latitude=13.0827,
        longitude=80.2707,
        sunrise_jd_ut1=2461241.999,
        sunset_jd_ut1=2461242.499,
        next_sunrise_jd_ut1=2461242.999,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
        policy=SimpleNamespace(
            policy_id="local_solar_day_explicit_paksha_v1",
            paksha_basis="caller_supplied_source_label",
            solar_day_basis="topocentric_sunrise_to_next_sunrise",
            solar_event_altitude_deg=-0.833,
            observer_elevation_m=0.0,
            solar_altitude_refraction_mode=(
                "unrefracted_signal_standard_refraction_and_semidiameter_in_threshold"
            ),
            half_basis="topocentric_sunrise_sunset",
            weekday_basis="local_mean_solar_time_at_governing_sunrise",
            offset_materialization_status="not_performed",
        ),
        nominal_schedule=schedule,
        provenance=replace(
            schedule.provenance,
            astronomical_routing_status=(
                "local_solar_half_and_weekday_performed_paksha_caller_supplied"
            ),
        ),
    )
    calls = []

    def compute(_engine, request):
        calls.append(request)
        return context

    monkeypatch.setattr(
        "moira_server.routers.pancha_pakshi.compute_local_solar_context",
        compute,
    )
    response = client.post(
        "/v1/pancha-pakshi/context/local-solar",
        json={
            "profile_id": _PROFILE_ID,
            "dt": "2026-07-20T12:00:00-04:00",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "paksha": "purva",
            "policy_id": "local_solar_day_explicit_paksha_v1",
        },
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0].dt.isoformat() == "2026-07-20T16:00:00+00:00"
    body = response.json()
    assert body["requested_jd_ut1"] == context.requested_jd_ut1
    assert body["half"] == "day"
    assert body["weekday"] == "sunday"
    assert body["policy"]["paksha_basis"] == "caller_supplied_source_label"
    assert body["policy"]["observer_elevation_m"] == 0.0
    assert body["policy"]["solar_altitude_refraction_mode"] == (
        "unrefracted_signal_standard_refraction_and_semidiameter_in_threshold"
    )
    assert body["policy"]["offset_materialization_status"] == "not_performed"
    assert body["nominal_schedule"]["paksha"] == "purva"
    assert body["provenance"]["astronomical_routing_status"] == (
        "local_solar_half_and_weekday_performed_paksha_caller_supplied"
    )


def test_local_solar_context_route_rejects_implicit_policy_naive_time_and_extra_routing(
    client: TestClient,
) -> None:
    base = {
        "profile_id": _PROFILE_ID,
        "dt": "2026-07-20T16:00:00Z",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "paksha": "purva",
        "policy_id": "local_solar_day_explicit_paksha_v1",
    }
    missing_policy = client.post(
        "/v1/pancha-pakshi/context/local-solar",
        json={key: value for key, value in base.items() if key != "policy_id"},
    )
    wrong_policy = client.post(
        "/v1/pancha-pakshi/context/local-solar",
        json={**base, "policy_id": "ambient_default"},
    )
    naive_time = client.post(
        "/v1/pancha-pakshi/context/local-solar",
        json={**base, "dt": "2026-07-20T16:00:00"},
    )
    extra_half = client.post(
        "/v1/pancha-pakshi/context/local-solar",
        json={**base, "half": "day"},
    )
    extra_elevation = client.post(
        "/v1/pancha-pakshi/context/local-solar",
        json={**base, "observer_elevation_m": 100.0},
    )
    bad_latitude = client.post(
        "/v1/pancha-pakshi/context/local-solar",
        json={**base, "latitude": 90.1},
    )

    _assert_validation_envelope(missing_policy, message_fragment="Field required")
    _assert_validation_envelope(wrong_policy, message_fragment="local_solar_day_explicit_paksha_v1")
    _assert_validation_envelope(naive_time, message_fragment="timezone-aware")
    _assert_validation_envelope(extra_half, message_fragment="Extra inputs are not permitted")
    _assert_validation_envelope(
        extra_elevation,
        message_fragment="Extra inputs are not permitted",
    )
    _assert_validation_envelope(bad_latitude, message_fragment="less than or equal to 90")


def test_fixed_clock_materialization_route_serializes_explicit_policy_and_cells(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schedule = pancha_pakshi_schedule(
        _PROFILE_ID,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )
    context = SimpleNamespace(
        profile_id=_PROFILE_ID,
        requested_jd_ut1=2461242.1667,
        latitude=13.0827,
        longitude=80.2707,
        sunrise_jd_ut1=2461241.999,
        sunset_jd_ut1=2461242.499,
        next_sunrise_jd_ut1=2461242.999,
        paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
        policy=SimpleNamespace(
            policy_id="local_solar_day_explicit_paksha_v1",
            paksha_basis="caller_supplied_source_label",
            solar_day_basis="topocentric_sunrise_to_next_sunrise",
            solar_event_altitude_deg=-0.833,
            observer_elevation_m=0.0,
            solar_altitude_refraction_mode=(
                "unrefracted_signal_standard_refraction_and_semidiameter_in_threshold"
            ),
            half_basis="topocentric_sunrise_sunset",
            weekday_basis="local_mean_solar_time_at_governing_sunrise",
            offset_materialization_status="not_performed",
        ),
        nominal_schedule=schedule,
        provenance=replace(
            schedule.provenance,
            astronomical_routing_status=(
                "local_solar_half_and_weekday_performed_paksha_caller_supplied"
            ),
        ),
    )
    anchor_jd_tt = 2461241.9998
    tt_minus_ut1_days = 69.0 / 86400.0
    cells = tuple(
        SimpleNamespace(
            schedule_cell_index=index,
            nominal_cell=cell,
            start_jd_tt=anchor_jd_tt + float(cell.start_nazhigai) / 60.0,
            end_jd_tt=anchor_jd_tt + float(cell.end_nazhigai) / 60.0,
            start_jd_ut1=(
                anchor_jd_tt
                + float(cell.start_nazhigai) / 60.0
                - tt_minus_ut1_days
            ),
            end_jd_ut1=(
                anchor_jd_tt
                + float(cell.end_nazhigai) / 60.0
                - tt_minus_ut1_days
            ),
            duration_seconds=cell.duration_nazhigai * 1440,
            solar_half_relation="within_governing_solar_half",
        )
        for index, cell in enumerate(schedule.cells)
    )
    materialization = SimpleNamespace(
        context=context,
        policy=SimpleNamespace(
            policy_id=(
                "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
            ),
            paksha_basis="caller_supplied_source_label",
            solar_context_basis="topocentric_sunrise_to_next_sunrise",
            day_anchor="governing_topocentric_sunrise",
            night_anchor="governing_topocentric_sunset",
            nazhigai_seconds=1440,
            half_span_nazhigai=30,
            half_span_seconds=43200,
            offset_arithmetic_time_scale="reader_bound_tt",
            published_endpoint_time_scale="ut1",
            interval_ownership="half_open",
            solar_end_clipping="none",
            topology_metric="fixed_end_jd_tt_minus_solar_end_jd_tt",
            topology_coalescence_seconds=0.0001,
            current_cell_status="not_performed",
            solar_proportional_scaling_status="not_performed",
        ),
        anchor_jd_tt=anchor_jd_tt,
        anchor_jd_ut1=anchor_jd_tt - tt_minus_ut1_days,
        governing_solar_half_end_jd_tt=2461242.4998,
        governing_solar_half_end_jd_ut1=2461242.499,
        fixed_end_jd_tt=anchor_jd_tt + 0.5,
        fixed_end_jd_ut1=anchor_jd_tt + 0.5 - tt_minus_ut1_days,
        signed_fixed_end_minus_solar_end_seconds_tt=0.0,
        solar_boundary_relation="ends_at_solar_boundary",
        cells=cells,
        provenance=replace(
            schedule.provenance,
            astronomical_routing_status=(
                "fixed_clock_materialization_performed_paksha_caller_supplied_no_current_cell"
            ),
        ),
    )
    calls = []

    def compute(_engine, request):
        calls.append(request)
        return materialization

    monkeypatch.setattr(
        "moira_server.routers.pancha_pakshi.compute_fixed_clock_materialization",
        compute,
    )
    response = client.post(
        "/v1/pancha-pakshi/schedule/fixed-clock",
        json={
            "profile_id": _PROFILE_ID,
            "dt": "2026-07-20T12:00:00-04:00",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "paksha": "purva",
            "policy_id": (
                "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
            ),
        },
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0].dt.isoformat() == "2026-07-20T16:00:00+00:00"
    body = response.json()
    assert body["local_solar_context"]["policy"]["offset_materialization_status"] == (
        "not_performed"
    )
    assert body["policy"]["offset_arithmetic_time_scale"] == "reader_bound_tt"
    assert body["policy"]["published_endpoint_time_scale"] == "ut1"
    assert body["policy"]["nazhigai_seconds"] == 1440
    assert body["policy"]["half_span_nazhigai"] == 30
    assert body["policy"]["half_span_seconds"] == 43200
    assert body["policy"]["solar_end_clipping"] == "none"
    assert body["policy"]["topology_metric"] == (
        "fixed_end_jd_tt_minus_solar_end_jd_tt"
    )
    assert body["anchor_jd_tt"] == materialization.anchor_jd_tt
    assert body["anchor_jd_ut1"] == materialization.anchor_jd_ut1
    assert body["governing_solar_half_end_jd_tt"] == (
        materialization.governing_solar_half_end_jd_tt
    )
    assert body["fixed_end_jd_ut1"] == materialization.fixed_end_jd_ut1
    assert body["signed_fixed_end_minus_solar_end_seconds_tt"] == 0.0
    assert body["solar_boundary_relation"] == "ends_at_solar_boundary"
    assert len(body["cells"]) == 25
    first = body["cells"][0]
    assert first["schedule_cell_index"] == 0
    assert first["nominal_cell"]["start_nazhigai"] == {
        "numerator": 0,
        "denominator": 1,
    }
    assert first["duration_seconds"] == {"numerator": 1800, "denominator": 1}
    assert first["solar_half_relation"] == "within_governing_solar_half"
    assert "current_cell" not in body
    assert body["provenance"]["astronomical_routing_status"] == (
        "fixed_clock_materialization_performed_paksha_caller_supplied_no_current_cell"
    )


def test_fixed_clock_materialization_route_rejects_implicit_or_scaling_policy(
    client: TestClient,
) -> None:
    base = {
        "profile_id": _PROFILE_ID,
        "dt": "2026-07-20T16:00:00Z",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "paksha": "purva",
        "policy_id": "fixed_24_minute_nazhigai_from_local_solar_half_start_v1",
    }
    missing_policy = client.post(
        "/v1/pancha-pakshi/schedule/fixed-clock",
        json={key: value for key, value in base.items() if key != "policy_id"},
    )
    wrong_policy = client.post(
        "/v1/pancha-pakshi/schedule/fixed-clock",
        json={**base, "policy_id": "solar_proportional_actual_half_v1"},
    )
    naive_time = client.post(
        "/v1/pancha-pakshi/schedule/fixed-clock",
        json={**base, "dt": "2026-07-20T16:00:00"},
    )
    scaling_input = client.post(
        "/v1/pancha-pakshi/schedule/fixed-clock",
        json={**base, "solar_proportional_scaling": True},
    )
    current_cell_input = client.post(
        "/v1/pancha-pakshi/schedule/fixed-clock",
        json={**base, "current_cell": True},
    )

    _assert_validation_envelope(missing_policy, message_fragment="Field required")
    _assert_validation_envelope(
        wrong_policy,
        message_fragment="fixed_24_minute_nazhigai_from_local_solar_half_start_v1",
    )
    _assert_validation_envelope(naive_time, message_fragment="timezone-aware")
    _assert_validation_envelope(
        scaling_input,
        message_fragment="Extra inputs are not permitted",
    )
    _assert_validation_envelope(
        current_cell_input,
        message_fragment="Extra inputs are not permitted",
    )


def test_fixed_clock_current_cell_route_returns_one_bounded_selected_cell(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = _fixed_clock_current_cell_selection(tail=False)
    calls = []

    def compute(_engine, request):
        calls.append(request)
        return selection

    monkeypatch.setattr(
        "moira_server.routers.pancha_pakshi.compute_fixed_clock_current_cell",
        compute,
    )
    response = client.post(
        "/v1/pancha-pakshi/schedule/fixed-clock/current-cell",
        json={
            "profile_id": _PROFILE_ID,
            "dt": "2026-07-20T12:00:00-04:00",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "paksha": "purva",
            "policy_id": (
                "fixed_clock_current_cell_half_open_solar_precedence_v1"
            ),
        },
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0].dt.isoformat() == "2026-07-20T16:00:00+00:00"
    body = response.json()
    assert body["profile_id"] == _PROFILE_ID
    assert body["requested_jd_ut1"] == (
        selection.materialization.context.requested_jd_ut1
    )
    assert body["requested_jd_tt"] == selection.requested_jd_tt
    assert body["latitude"] == 13.0827
    assert body["longitude"] == 80.2707
    assert body["paksha"] == "purva"
    assert body["half"] == "day"
    assert body["weekday"] == "sunday"
    assert body["policy"] == {
        "policy_id": "fixed_clock_current_cell_half_open_solar_precedence_v1",
        "materialization_policy_id": (
            "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
        ),
        "paksha_basis": "caller_supplied_source_label",
        "selection_time_scale": "reader_bound_tt",
        "interval_ownership": "half_open",
        "solar_half_precedence": (
            "resolve_governing_solar_half_before_selection"
        ),
        "membership_tolerance_seconds": 0.0,
        "unmaterialized_solar_half_tail": "explicit_no_current_cell",
        "solar_end_clipping": "none",
        "fixed_span_wrap": "none",
        "fixed_span_repeat": "none",
        "solar_proportional_scaling_status": "not_performed",
        "astronomical_paksha_inference_status": "not_performed",
    }
    assert body["selection_status"] == "selected"
    assert body["current_cell"]["schedule_cell_index"] == 0
    assert body["current_cell"]["duration_seconds"] == {
        "numerator": 1800,
        "denominator": 1,
    }
    assert "cells" not in body
    assert "local_solar_context" not in body
    assert "materialization" not in body


def test_fixed_clock_current_cell_route_preserves_unmaterialized_tail(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = _fixed_clock_current_cell_selection(tail=True)
    monkeypatch.setattr(
        "moira_server.routers.pancha_pakshi.compute_fixed_clock_current_cell",
        lambda _engine, _request: selection,
    )
    response = client.post(
        "/v1/pancha-pakshi/schedule/fixed-clock/current-cell",
        json={
            "profile_id": _PROFILE_ID,
            "dt": "2026-07-20T16:00:00Z",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "paksha": "purva",
            "policy_id": (
                "fixed_clock_current_cell_half_open_solar_precedence_v1"
            ),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selection_status"] == "unmaterialized_solar_half_tail"
    assert body["current_cell"] is None
    assert body["solar_boundary_relation"] == "ends_before_solar_boundary"
    assert body["fixed_end_jd_tt"] < body["requested_jd_tt"]
    assert body["requested_jd_tt"] < body["governing_solar_half_end_jd_tt"]
    assert "cells" not in body
    assert "local_solar_context" not in body
    assert "materialization" not in body


def test_fixed_clock_current_cell_route_rejects_implicit_or_ambient_policy(
    client: TestClient,
) -> None:
    path = "/v1/pancha-pakshi/schedule/fixed-clock/current-cell"
    base = {
        "profile_id": _PROFILE_ID,
        "dt": "2026-07-20T16:00:00Z",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "paksha": "purva",
        "policy_id": "fixed_clock_current_cell_half_open_solar_precedence_v1",
    }
    responses = (
        (
            client.post(
                path,
                json={key: value for key, value in base.items() if key != "policy_id"},
            ),
            "Field required",
        ),
        (
            client.post(path, json={**base, "policy_id": "ambient_current_cell"}),
            "fixed_clock_current_cell_half_open_solar_precedence_v1",
        ),
        (
            client.post(path, json={**base, "dt": "2026-07-20T16:00:00"}),
            "timezone-aware",
        ),
        (
            client.post(path, json={**base, "solar_proportional_scaling": True}),
            "Extra inputs are not permitted",
        ),
        (
            client.post(path, json={**base, "wrap_fixed_span": True}),
            "Extra inputs are not permitted",
        ),
        (
            client.post(path, json={**base, "latitude": -90.1}),
            "greater than or equal to -90",
        ),
    )
    for response, message_fragment in responses:
        _assert_validation_envelope(
            response,
            message_fragment=message_fragment,
        )


def test_directed_relationship_route_does_not_infer_reciprocity(client: TestClient) -> None:
    response = client.post(
        "/v1/pancha-pakshi/relationships/directed",
        json={"profile_id": _PROFILE_ID, "subject": "owl", "target": "peacock"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["relation"] == "friend"
    assert body["is_reciprocal_inference"] is False
    assert body["source_locators"]


def test_routes_reject_implicit_profiles_and_unadmitted_context(client: TestClient) -> None:
    missing_profile = client.post(
        "/v1/pancha-pakshi/identity/aksara",
        json={"initial_vowel": "A"},
    )
    extra_astronomy = client.post(
        "/v1/pancha-pakshi/schedule/nominal",
        json={
            "profile_id": _PROFILE_ID,
            "paksha": "purva",
            "half": "day",
            "weekday": "sunday",
            "jd": 2451545.0,
        },
    )
    self_relation = client.post(
        "/v1/pancha-pakshi/relationships/directed",
        json={"profile_id": _PROFILE_ID, "subject": "crow", "target": "crow"},
    )
    unknown_profile = client.get("/v1/pancha-pakshi/profiles/not-a-profile")
    unmapped_symbol = client.post(
        "/v1/pancha-pakshi/identity/aksara",
        json={"profile_id": _PROFILE_ID, "initial_vowel": "Y"},
    )

    _assert_validation_envelope(missing_profile, message_fragment="Field required")
    _assert_validation_envelope(extra_astronomy, message_fragment="Extra inputs are not permitted")
    _assert_validation_envelope(self_relation, message_fragment="self-relation")
    _assert_validation_envelope(unknown_profile, message_fragment="no default canon")
    _assert_validation_envelope(unmapped_symbol, message_fragment="not explicitly mapped")


def test_pancha_pakshi_routes_are_registered(client: TestClient) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/pancha-pakshi/")
    }

    assert paths == {
        "/v1/pancha-pakshi/profiles",
        "/v1/pancha-pakshi/profiles/{profile_id}",
        "/v1/pancha-pakshi/identity/aksara",
        "/v1/pancha-pakshi/schedule/fixed-clock",
        "/v1/pancha-pakshi/schedule/fixed-clock/current-cell",
        "/v1/pancha-pakshi/schedule/nominal",
        "/v1/pancha-pakshi/context/local-solar",
        "/v1/pancha-pakshi/relationships/directed",
    }


def test_pancha_pakshi_openapi_is_strict_typed_and_source_scoped(
    client: TestClient,
) -> None:
    schema = client.app.openapi()
    components = schema["components"]["schemas"]

    assert "pancha-pakshi" in {tag["name"] for tag in schema["tags"]}
    request = components["PanchaPakshiNominalScheduleRequest"]
    assert request["additionalProperties"] is False
    assert set(request["required"]) == {
        "profile_id",
        "paksha",
        "half",
        "weekday",
    }
    assert components["PanchaPakshiPaksha"]["enum"] == ["purva", "amara"]
    assert components["PanchaPakshiHalf"]["enum"] == ["day", "night"]
    assert components["PanchaPakshiRelation"]["enum"] == ["friend", "enemy"]
    assert components["PanchaPakshiAdmissionStatus"]["enum"] == [
        "research_only",
        "source_scoped_public",
        "corroborated_public",
    ]
    fraction = components["PanchaPakshiFractionResponse"]
    assert set(fraction["required"]) == {"numerator", "denominator"}
    assert fraction["properties"]["denominator"]["exclusiveMinimum"] == 0
    context_request = components["PanchaPakshiLocalSolarContextRequest"]
    assert context_request["additionalProperties"] is False
    assert set(context_request["required"]) == {
        "profile_id",
        "dt",
        "latitude",
        "longitude",
        "paksha",
        "policy_id",
    }
    assert context_request["properties"]["dt"]["format"] == "date-time"
    assert context_request["properties"]["policy_id"]["const"] == (
        "local_solar_day_explicit_paksha_v1"
    )
    policy = components["PanchaPakshiLocalSolarContextPolicyResponse"]
    assert policy["properties"]["offset_materialization_status"]["const"] == (
        "not_performed"
    )
    assert policy["properties"]["solar_altitude_refraction_mode"]["const"] == (
        "unrefracted_signal_standard_refraction_and_semidiameter_in_threshold"
    )
    fixed_request = components["PanchaPakshiFixedClockMaterializationRequest"]
    assert fixed_request["additionalProperties"] is False
    assert set(fixed_request["required"]) == {
        "profile_id",
        "dt",
        "latitude",
        "longitude",
        "paksha",
        "policy_id",
    }
    assert fixed_request["properties"]["dt"]["format"] == "date-time"
    assert fixed_request["properties"]["policy_id"]["const"] == (
        "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
    )
    fixed_policy = components[
        "PanchaPakshiFixedClockMaterializationPolicyResponse"
    ]
    assert fixed_policy["additionalProperties"] is False
    assert fixed_policy["properties"]["nazhigai_seconds"]["const"] == 1440
    assert fixed_policy["properties"]["half_span_seconds"]["const"] == 43200
    assert fixed_policy["properties"]["offset_arithmetic_time_scale"]["const"] == (
        "reader_bound_tt"
    )
    assert fixed_policy["properties"]["solar_end_clipping"]["const"] == "none"
    assert fixed_policy["properties"]["current_cell_status"]["const"] == (
        "not_performed"
    )
    fixed_cell = components["PanchaPakshiFixedClockCellResponse"]
    assert fixed_cell["properties"]["schedule_cell_index"]["minimum"] == 0
    assert set(fixed_cell["required"]) == {
        "schedule_cell_index",
        "nominal_cell",
        "start_jd_tt",
        "end_jd_tt",
        "start_jd_ut1",
        "end_jd_ut1",
        "duration_seconds",
        "solar_half_relation",
    }
    assert components["PanchaPakshiSolarBoundaryRelation"]["enum"] == [
        "ends_before_solar_boundary",
        "ends_at_solar_boundary",
        "ends_after_solar_boundary",
    ]
    assert components["PanchaPakshiMaterializedCellRelation"]["enum"] == [
        "within_governing_solar_half",
        "crosses_governing_solar_half_end",
        "after_governing_solar_half",
    ]
    current_request = components["PanchaPakshiFixedClockCurrentCellRequest"]
    assert current_request["additionalProperties"] is False
    assert set(current_request["required"]) == {
        "profile_id",
        "dt",
        "latitude",
        "longitude",
        "paksha",
        "policy_id",
    }
    assert current_request["properties"]["dt"]["format"] == "date-time"
    assert current_request["properties"]["policy_id"]["const"] == (
        "fixed_clock_current_cell_half_open_solar_precedence_v1"
    )
    current_policy = components[
        "PanchaPakshiFixedClockCurrentCellSelectionPolicyResponse"
    ]
    assert current_policy["additionalProperties"] is False
    assert current_policy["properties"]["materialization_policy_id"]["const"] == (
        "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
    )
    assert current_policy["properties"]["selection_time_scale"]["const"] == (
        "reader_bound_tt"
    )
    assert current_policy["properties"]["interval_ownership"]["const"] == (
        "half_open"
    )
    assert current_policy["properties"]["membership_tolerance_seconds"][
        "const"
    ] == 0.0
    assert current_policy["properties"]["unmaterialized_solar_half_tail"][
        "const"
    ] == "explicit_no_current_cell"
    assert current_policy["properties"]["fixed_span_wrap"]["const"] == "none"
    assert current_policy["properties"]["fixed_span_repeat"]["const"] == "none"
    current_response = components["PanchaPakshiFixedClockCurrentCellResponse"]
    assert current_response["additionalProperties"] is False
    assert set(current_response["required"]) == {
        "profile_id",
        "requested_jd_ut1",
        "requested_jd_tt",
        "latitude",
        "longitude",
        "paksha",
        "half",
        "weekday",
        "policy",
        "anchor_jd_tt",
        "anchor_jd_ut1",
        "governing_solar_half_end_jd_tt",
        "governing_solar_half_end_jd_ut1",
        "fixed_end_jd_tt",
        "fixed_end_jd_ut1",
        "signed_fixed_end_minus_solar_end_seconds_tt",
        "solar_boundary_relation",
        "selection_status",
        "current_cell",
        "provenance",
    }
    current_cell_schema = current_response["properties"]["current_cell"]
    assert {item.get("type") for item in current_cell_schema["anyOf"]} == {
        None,
        "null",
    }
    assert components["PanchaPakshiCurrentCellSelectionStatus"]["enum"] == [
        "selected",
        "unmaterialized_solar_half_tail",
    ]
