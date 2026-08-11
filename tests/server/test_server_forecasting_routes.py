"""Contract tests for bounded Track-A forecasting transport surfaces."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from moira.constants import Body
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.forecasting import (
    CompositeTransitRequest,
    DynamicAstrocartographyRequest,
    FixedStarAstrocartographyRequest,
    RelocatedReturnRequest,
)
from moira_server.services import forecasting as service


pytestmark = pytest.mark.loopback


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False, prewarm_enabled=False))
    with TestClient(app) as client:
        yield client


def _party(dt: str, latitude: float, longitude: float) -> dict[str, object]:
    return {
        "dt": dt,
        "latitude": latitude,
        "longitude": longitude,
        "include_nodes": True,
    }


def _composite_request(**overrides) -> CompositeTransitRequest:
    data = {
        "chart": {
            "first": _party("2000-01-01T12:00:00Z", 40.0, -75.0),
            "second": _party("2001-01-01T12:00:00Z", 51.5, -0.1),
            "method": "midpoint",
        },
        "moving_bodies": [Body.MARS],
        "jd_start": 2_460_000.0,
        "jd_end": 2_460_100.0,
        "target_names": [Body.SUN],
    }
    data.update(overrides)
    return CompositeTransitRequest.model_validate(data)


def test_forecasting_routes_are_present_in_openapi() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    expected = {
        "/v1/composite/transits",
        "/v1/davison/transits",
        "/v1/astrocartography/fixed-stars",
        "/v1/astrocartography/dynamic/transits",
        "/v1/returns/relocated",
    }
    assert expected <= set(schema["paths"])

    fixed_schema = schema["components"]["schemas"]["FixedStarAstrocartographyRequest"]
    assert {"star_names", "jd_ut", "jd_tt"} <= set(fixed_schema["required"])
    dynamic_schema = schema["components"]["schemas"]["DynamicAstrocartographyRequest"]
    assert {
        "epochs_jd_ut",
        "bodies",
        "observer_latitude",
        "observer_longitude",
    } <= set(dynamic_schema["required"])


def test_fixed_star_route_exposes_identity_geometry_and_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_engine = SimpleNamespace(is_kernel_available=lambda: False)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: fake_engine)
    app = create_app(ServerConfig(docs_enabled=False, prewarm_enabled=False))
    with TestClient(app) as client:
        response = client.post(
            "/v1/astrocartography/fixed-stars",
            json={
                "star_names": ["Sirius"],
                "jd_ut": 2_451_544.9992,
                "jd_tt": 2_451_545.0,
                "lat_step": 20.0,
                "refraction": False,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["subjects"][0]["canonical_name"] == "Sirius"
    assert body["subjects"][0]["position_source"] == (
        "moira.stars.star_at:ecliptic_to_equatorial"
    )
    assert body["subjects"][0]["source_mode"] == "sovereign_registry"
    assert body["subjects"][0]["relation_basis"] == "sovereign_registry"
    assert body["subjects"][0]["true_position"] is True
    assert {line["line_type"] for line in body["lines"]} == {
        "MC",
        "IC",
        "ASC",
        "DSC",
    }
    assert {point["point_type"] for point in body["subplanetary_points"]} == {
        "Zenith",
        "Nadir",
    }
    assert body["computation_truth"]["interpretation"] == "none_geometry_only"


def test_transport_models_fail_closed_on_implicit_or_unbounded_policy() -> None:
    with pytest.raises(ValidationError, match="observer_latitude"):
        DynamicAstrocartographyRequest(
            epochs_jd_ut=[2_460_000.0],
            bodies=[Body.SUN],
        )
    with pytest.raises(ValidationError, match="strictly increasing"):
        DynamicAstrocartographyRequest(
            epochs_jd_ut=[2_460_001.0, 2_460_000.0],
            bodies=[Body.SUN],
            observer_latitude=0.0,
            observer_longitude=0.0,
        )
    with pytest.raises(ValidationError, match="requires year"):
        RelocatedReturnRequest(
            return_kind="solar_return",
            natal_longitude=280.0,
            source_latitude=40.0,
            source_longitude=-75.0,
            relocated_latitude=51.5,
            relocated_longitude=-0.1,
        )
    with pytest.raises(ValidationError, match="36525"):
        _composite_request(jd_end=2_500_000.0)


def test_composite_service_forwards_exact_policy_and_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chart = object()
    result = object()
    captured: dict[str, object] = {}
    reader = object()
    engine = SimpleNamespace(_reader=reader)
    request = _composite_request(
        direction="retrograde",
        search_motion="backward",
        step_days=0.25,
        solver_tolerance_days=2e-7,
    )

    monkeypatch.setattr(service, "compute_composite_chart", lambda *args: chart)
    monkeypatch.setattr(
        service,
        "relationship_chart_targets",
        lambda *args, **kwargs: SimpleNamespace(target_count=1),
    )

    def fake_find(chart_arg, moving_bodies, jd_start, jd_end, **kwargs):
        captured.update(
            chart=chart_arg,
            moving_bodies=moving_bodies,
            jd_start=jd_start,
            jd_end=jd_end,
            **kwargs,
        )
        return result

    monkeypatch.setattr(service, "find_composite_transits", fake_find)

    assert service.compute_composite_transits(engine, request) is result
    assert captured["chart"] is chart
    assert captured["reader"] is reader
    assert captured["direction"] == "retrograde"
    assert captured["search_motion"] == "backward"
    assert captured["step_days"] == 0.25
    policy = captured["policy"]
    assert policy.transit.step_days_override is None
    assert policy.transit.solver_tolerance_days == pytest.approx(2e-7)


def test_relationship_server_budget_rejects_expansive_search_before_solver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _composite_request(
        moving_bodies=[Body.MERCURY, Body.VENUS, Body.MARS, Body.JUPITER],
        tier=2,
        target_names=None,
    )
    monkeypatch.setattr(service, "compute_composite_chart", lambda *args: object())
    monkeypatch.setattr(
        service,
        "relationship_chart_targets",
        lambda *args, **kwargs: SimpleNamespace(target_count=16),
    )
    monkeypatch.setattr(
        service,
        "find_composite_transits",
        lambda *args, **kwargs: pytest.fail("solver must not run past server budget"),
    )

    with pytest.raises(ValueError, match="canonical searches"):
        service.compute_composite_transits(SimpleNamespace(_reader=object()), request)


def test_relationship_server_budget_rejects_tiny_scan_step_before_solver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _composite_request(step_days=0.01, jd_end=2_461_000.0)
    monkeypatch.setattr(service, "compute_composite_chart", lambda *args: object())
    monkeypatch.setattr(
        service,
        "relationship_chart_targets",
        lambda *args, **kwargs: SimpleNamespace(target_count=1),
    )
    monkeypatch.setattr(
        service,
        "find_composite_transits",
        lambda *args, **kwargs: pytest.fail("solver must not run past scan budget"),
    )

    with pytest.raises(ValueError, match="scan samples"):
        service.compute_composite_transits(SimpleNamespace(_reader=object()), request)


def test_relationship_service_rejects_requested_nodes_that_were_not_computed() -> None:
    request = _composite_request(
        chart={
            "first": _party("2000-01-01T12:00:00Z", 40.0, -75.0)
            | {"include_nodes": False},
            "second": _party("2001-01-01T12:00:00Z", 51.5, -0.1),
            "method": "midpoint",
        },
        include_nodes=True,
    )

    with pytest.raises(ValueError, match="both relationship parties"):
        service.compute_composite_transits(SimpleNamespace(_reader=object()), request)


def test_dynamic_service_forwards_explicit_epochs_without_ranking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = object()
    reader = object()
    captured: dict[str, object] = {}
    request = DynamicAstrocartographyRequest(
        epochs_jd_ut=[2_460_000.0, 2_460_001.0],
        bodies=[Body.SUN],
        observer_latitude=40.0,
        observer_longitude=-75.0,
        lat_step=10.0,
    )

    def fake_dynamic(epochs, bodies, **kwargs):
        captured.update(epochs=epochs, bodies=bodies, **kwargs)
        return expected

    monkeypatch.setattr(service, "transiting_astrocartography", fake_dynamic)
    result = service.compute_dynamic_astrocartography(
        SimpleNamespace(_reader=reader),
        request,
    )

    assert result is expected
    assert captured["epochs"] == request.epochs_jd_ut
    assert captured["bodies"] == request.bodies
    assert captured["reader"] is reader
    assert "ranking" not in captured


def test_fixed_star_request_rejects_duplicate_alias_inputs_before_resolution() -> None:
    with pytest.raises(ValidationError, match="must be unique"):
        FixedStarAstrocartographyRequest(
            star_names=["Sirius", "Sirius"],
            jd_ut=2_451_544.9992,
            jd_tt=2_451_545.0,
        )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/v1/composite/transits", "midpoint"),
        ("/v1/davison/transits", "midpoint_location"),
    ],
)
def test_relationship_transit_routes_return_static_target_receipts(
    client_with_engine: TestClient,
    path: str,
    method: str,
) -> None:
    response = client_with_engine.post(
        path,
        json={
            "chart": {
                "first": _party("2000-01-01T12:00:00Z", 40.0, -75.0),
                "second": _party("2000-01-03T12:00:00Z", 51.5, -0.1),
                "method": method,
            },
            "moving_bodies": [Body.MARS],
            "jd_start": 2_451_545.0,
            "jd_end": 2_451_550.0,
            "target_names": [Body.SUN],
            "include_nodes": False,
            "tier": 0,
            "aspect_names": ["Square"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["target_set"]["target_count"] == 1
    assert body["target_set"]["targets"][0]["name"] == Body.SUN
    assert body["target_set"]["identity"]["method"] == method
    assert body["target_set"]["identity"]["construction_truth"]["method"] == method
    assert body["computation_truth"]["search_call_count"] == 2
    assert body["computation_truth"]["aspect_names"] == ["Square"]
    assert body["computation_truth"]["target_motion"] == (
        "static_derived_chart_geometry"
    )
    assert body["computation_truth"]["orb_window_policy"] == "not_computed"
    assert body["computation_truth"]["solver_tolerance_days"] == pytest.approx(1e-6)
    assert body["computation_truth"]["step_policy"] == "canonical_per_body_auto"
    assert body["event_count"] == len(body["events"])


@pytest.mark.requires_ephemeris
def test_dynamic_astrocartography_route_returns_geometry_only_snapshots(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/dynamic/transits",
        json={
            "epochs_jd_ut": [2_451_545.0, 2_451_546.0],
            "bodies": [Body.SUN],
            "observer_latitude": 40.0,
            "observer_longitude": -75.0,
            "lat_step": 20.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["computation_truth"]["snapshot_count"] == 2
    assert body["computation_truth"]["transition_count"] == 4
    assert body["computation_truth"]["progressed_mode"] == "not_admitted"
    assert body["computation_truth"]["directed_mode"] == "not_admitted"
    assert body["computation_truth"]["interpretation"] == "none_geometry_only"
    assert all(len(snapshot["lines"]) == 4 for snapshot in body["snapshots"])
    assert "ranking" not in body


@pytest.mark.requires_ephemeris
def test_relocated_return_route_preserves_epoch_and_sky_snapshot(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/returns/relocated",
        json={
            "return_kind": "solar_return",
            "natal_longitude": 280.0,
            "year": 2000,
            "source_latitude": 40.0,
            "source_longitude": -75.0,
            "relocated_latitude": 51.5,
            "relocated_longitude": -0.1,
            "source_house_system": "E",
            "bodies": [Body.SUN, Body.MOON],
        },
    )

    assert response.status_code == 200
    body = response.json()
    source = body["source_chart"]
    relocated = body["relocated_chart"]
    assert source["jd_ut"] == relocated["jd_ut"]
    assert source["jd_tt"] == relocated["jd_tt"]
    assert source["planets"] == relocated["planets"]
    assert source["nodes"] == relocated["nodes"]
    assert source["latitude"] == 40.0
    assert relocated["latitude"] == 51.5
    assert body["return_truth"]["return_kind"] == "solar_return"
    assert body["return_truth"]["search_policy"]["policy_source"] == "default"
    assert body["return_truth"]["search_policy"]["solver_tolerance_days"] == pytest.approx(1e-6)
    assert body["relocation_truth"]["same_epoch"] is True
    assert body["relocation_truth"]["same_celestial_snapshot"] is True
    assert body["relocation_truth"]["interpretation"] == "none_geometry_only"
