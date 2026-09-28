from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.cache import ResponseLRUCache
from moira_server.config import ServerConfig
from moira_server.models.phenomena import (
    LunarOccultationRequest,
    SolarEclipseCartographyRequest,
    SolarEclipseFootprintRequest,
)
from moira_server.models.sade_sati import SadeSatiWindowsResponse
from moira_server.routers import phenomena as phenomena_routes


pytestmark = pytest.mark.loopback


def _http_request(cache: ResponseLRUCache) -> SimpleNamespace:
    state = SimpleNamespace(expensive_response_cache=cache)
    return SimpleNamespace(app=SimpleNamespace(state=state))


@pytest.mark.parametrize(
    ("route_name", "compute_name", "serializer_name", "request_model"),
    (
        (
            "solar_eclipse_footprint_route",
            "compute_solar_eclipse_footprint",
            "serialize_solar_eclipse_footprint",
            SolarEclipseFootprintRequest(jd_start=2451545.0, sample_count=9),
        ),
        (
            "solar_eclipse_cartography_route",
            "compute_solar_eclipse_cartography",
            "serialize_solar_eclipse_cartography",
            SolarEclipseCartographyRequest(
                jd_start=2451545.0,
                magnitude_levels=[0.5],
                obscuration_levels=[0.5],
                mesh_depth=0,
                time_samples=9,
            ),
        ),
    ),
)
def test_expensive_eclipse_routes_cache_completed_responses(
    monkeypatch: pytest.MonkeyPatch,
    route_name: str,
    compute_name: str,
    serializer_name: str,
    request_model,
) -> None:
    cache = ResponseLRUCache(maxsize=4)
    engine = object()
    calls = 0

    def compute(*_args):
        nonlocal calls
        calls += 1
        return object()

    monkeypatch.setattr(phenomena_routes, compute_name, compute)
    monkeypatch.setattr(phenomena_routes, serializer_name, lambda _result: {"ok": True})
    route = getattr(phenomena_routes, route_name)

    first = route(request_model, _http_request(cache), engine)
    second = route(request_model, _http_request(cache), engine)

    assert first == second == {"ok": True}
    assert calls == 1


def test_occultation_route_caches_completed_empty_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = ResponseLRUCache(maxsize=4)
    engine = object()
    request = LunarOccultationRequest(
        target="Venus",
        jd_start=2451545.0,
        jd_end=2451546.0,
    )
    calls = 0

    def compute(*_args):
        nonlocal calls
        calls += 1
        return []

    monkeypatch.setattr(phenomena_routes, "compute_lunar_occultations", compute)

    first = phenomena_routes.lunar_occultations_route(
        request, _http_request(cache), engine
    )
    second = phenomena_routes.lunar_occultations_route(
        request, _http_request(cache), engine
    )

    assert first == second
    assert first.events == []
    assert calls == 1


def test_sade_sati_windows_route_caches_by_validated_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object()
    calls = 0

    def compute(_engine, request):
        nonlocal calls
        calls += 1
        return SadeSatiWindowsResponse(
            janma_rashi_index=1,
            start_jd=2451544.5,
            end_jd=2451910.5,
            ayanamsa_system=request.ayanamsa_system,
            windows=(),
        )

    monkeypatch.setattr("moira_server.app.create_engine", lambda _config: engine)
    monkeypatch.setattr(
        "moira_server.routers.sade_sati.compute_sade_sati_windows",
        compute,
    )
    app = create_app(ServerConfig(docs_enabled=False))
    payload = {
        "natal_moon_sidereal_lon": 35.0,
        "start_dt": "2000-01-01T00:00:00+00:00",
        "end_dt": "2001-01-01T00:00:00+00:00",
    }

    with TestClient(app) as client:
        first = client.post("/v1/sade-sati/windows", json=payload)
        second = client.post("/v1/sade-sati/windows", json=payload)

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert calls == 1
