"""HTTP contracts for opt-in eclipse diagnostics and their uncertainty."""
from __future__ import annotations

import asyncio
import math
from concurrent.futures import ThreadPoolExecutor
import sys
from types import SimpleNamespace

import httpx
import pytest

from moira.julian import julian_day
from moira.solar_visibility_witness import solar_visibility_at_site
from moira.spk_reader import OutOfRangeError
from moira_server.app import create_app
from moira_server.config import ServerConfig


SOLAR_HYBRID = "/v1/eclipses/solar/central-path-diagnostic"
LUNAR_SHADOW = "/v1/eclipses/lunar/shadow-candidate"
SOLAR_SITE = "/v1/eclipses/solar/visibility-site"
SOLAR_REFINEMENT = "/v1/eclipses/solar/visibility-refinement"
SOLAR_CAP = "/v1/eclipses/solar/central-cap-diagnostic"
SOLAR_SWEPT = "/v1/eclipses/solar/swept-interior-witness"


@pytest.fixture(scope="module")
def diagnostic_client(eclipse_calculator):
    # Exercise the real ASGI app in process while injecting the discovered
    # session kernel; this avoids starting a listener or a separate server.
    app = create_app(ServerConfig(docs_enabled=False, prewarm_enabled=False))
    app.state.engine = SimpleNamespace(_reader=eclipse_calculator._reader)

    class Client:
        def post(self, path, **kwargs):
            async def invoke():
                # A periodic callback wakes the socket-free loop to process
                # call_soon_threadsafe completions from AnyIO's worker pool.
                loop = asyncio.get_running_loop()
                timer = None

                def tick():
                    nonlocal timer
                    timer = loop.call_later(0.01, tick)

                tick()
                transport = httpx.ASGITransport(app=app)
                try:
                    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                        return await client.post(path, **kwargs)
                finally:
                    timer.cancel()

            def run():
                if sys.platform != "win32":
                    return asyncio.run(asyncio.wait_for(invoke(), timeout=25))

                # The Windows sandbox blocks the loopback socketpair normally
                # created by asyncio, even though ASGITransport uses no socket.
                # Run in a worker (avoiding main-thread signal installation)
                # with a test-only proactor whose timed wakeups replace its pipe.
                class SocketFreeLoop(asyncio.ProactorEventLoop):
                    def _make_self_pipe(self):
                        self._ssock = self._csock = None

                    def _close_self_pipe(self):
                        pass

                    def _write_to_self(self):
                        pass

                    def _loop_self_reading(self, future=None):
                        pass

                with asyncio.Runner(loop_factory=SocketFreeLoop) as runner:
                    return runner.run(asyncio.wait_for(invoke(), timeout=25))

            with ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(run).result(timeout=30)

    return Client()


def test_openapi_exposes_only_opt_in_diagnostic_contracts():
    app = create_app(ServerConfig(docs_enabled=False))
    schema = app.openapi()
    paths = schema["paths"]
    for path in (SOLAR_HYBRID, LUNAR_SHADOW, SOLAR_SITE, SOLAR_REFINEMENT, SOLAR_CAP, SOLAR_SWEPT):
        assert set(paths[path]) == {"post"}
        operation = paths[path]["post"]
        assert "$ref" in operation["requestBody"]["content"]["application/json"]["schema"]
        assert "$ref" in operation["responses"]["200"]["content"]["application/json"]["schema"]
    models = schema["components"]["schemas"]
    assert "status" not in models["EclipseEventResponse"]["properties"]
    assert "umbral_width_status" not in models["SolarEclipsePathResponse"]["properties"]
    assert "path_width_status" not in models["SolarEclipseGreatestSiteResponse"]["properties"]


@pytest.mark.loopback
def test_existing_solar_search_response_is_unchanged_by_diagnostic(diagnostic_client):
    legacy_payload = {"jd_start": 2460054.0}
    before = diagnostic_client.post("/v1/eclipses/solar/next", json=legacy_payload)
    assert before.status_code == 200, before.text
    response = diagnostic_client.post(SOLAR_HYBRID, json={"jd_start_ut1": 2460054.0})
    assert response.status_code == 200, response.text
    after = diagnostic_client.post("/v1/eclipses/solar/next", json=legacy_payload)
    assert after.status_code == 200, after.text
    assert before.json() == after.json()
    assert set(after.json()) == {"jd_ut", "datetime_utc", "data"}


@pytest.mark.loopback
def test_ancient_solar_diagnostic_survives_bce_serialization(diagnostic_client):
    response = diagnostic_client.post(SOLAR_HYBRID, json={"jd_start_ut1": 1582759.5516342013})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "hybrid"
    assert body["subtype"] is None
    assert body["annular_witness"]["signed_radius_km"] < 0.0
    assert body["total_witness"]["signed_radius_km"] > 0.0
    assert body["annular_witness"]["sun_altitude_deg"] > 0.0
    assert body["total_witness"]["sun_altitude_deg"] > 0.0
    assert body["transitions"]


@pytest.mark.loopback
def test_solar_budget_exhaustion_is_transported_as_unresolved(diagnostic_client):
    response = diagnostic_client.post(SOLAR_HYBRID, json={
        "jd_start_ut1": 2457986.0, "max_evaluations": 1,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "unresolved"
    assert body["budget_exhausted"] is True
    assert body["evaluation_count"] == 1
    assert body["subtype"] is None


@pytest.mark.loopback
@pytest.mark.parametrize("seed,backward,expected", (
    # 2023 New Moon precedes greatest; the seed is between those instants.
    (2460054.676, False, 2460054.6783184963),
    # 2024 greatest precedes New Moon; the seed is between those instants.
    (2460409.26325, True, 2460409.2620393815),
))
def test_nearest_event_selection_across_new_moon_and_greatest(
    diagnostic_client, seed, backward, expected,
):
    response = diagnostic_client.post(SOLAR_HYBRID, json={
        "jd_start_ut1": seed, "backward": backward,
    })
    assert response.status_code == 200, response.text
    # One second is a regression tolerance, not an ephemeris accuracy claim.
    assert abs(response.json()["event_jd_ut1"] - expected) * 86400 < 1.0


@pytest.mark.loopback
@pytest.mark.parametrize("backward", (False, True))
@pytest.mark.parametrize("offset", (-1, 0, 1))
def test_diagnostic_uses_same_strict_event_order_as_public_search(
    diagnostic_client, eclipse_calculator, backward, offset,
):
    # 2024-04-08 is a real DE441 event for which phase and maximum differ.
    # Identity is compared to the public search, not to a rounded catalog time.
    event = eclipse_calculator.next_solar_eclipse(2460408.0)
    query = event.jd_ut
    if offset:
        query = math.nextafter(query, math.inf if offset > 0 else -math.inf)
    search = (eclipse_calculator.previous_solar_eclipse if backward
              else eclipse_calculator.next_solar_eclipse)
    expected = search(query)
    response = diagnostic_client.post(SOLAR_HYBRID, json={
        "jd_start_ut1": query, "backward": backward, "max_evaluations": 1,
    })
    assert response.status_code == 200, response.text
    actual = response.json()["event_jd_ut1"]
    assert actual == expected.jd_ut
    assert actual < query if backward else actual > query


@pytest.mark.loopback
@pytest.mark.parametrize("payload", (
    {"jd_start_ut1": True},
    {"jd_start_ut1": "2460054.0"},
    {"jd_start_ut1": 2460054.0, "max_evaluations": True},
    {"jd_start_ut1": 2460054.0, "max_evaluations": 0},
    {"jd_start_ut1": 2460054.0, "max_evaluations": 999999999},
    {"jd_start_ut1": 2460054.0, "backward": 1},
    {"jd_start_ut1": 2460054.0, "unknown": 1},
))
def test_solar_request_rejects_ambiguous_or_unbounded_values(diagnostic_client, payload):
    response = diagnostic_client.post(SOLAR_HYBRID, json=payload)
    assert response.status_code == 422, response.text


@pytest.mark.loopback
@pytest.mark.parametrize("value", ("NaN", "Infinity", "-Infinity"))
def test_nonfinite_solar_epoch_returns_json_validation_error(diagnostic_client, value):
    response = diagnostic_client.post(
        SOLAR_HYBRID,
        content='{"jd_start_ut1": ' + value + '}',
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422, response.text
    assert response.json()


@pytest.mark.loopback
def test_concurrent_solar_diagnostics_are_deterministic(diagnostic_client):
    payload = {"jd_start_ut1": 2460054.0}
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: diagnostic_client.post(SOLAR_HYBRID, json=payload), range(8)))
    assert all(response.status_code == 200 for response in responses)
    bodies = [response.json() for response in responses]
    assert all(body == bodies[0] for body in bodies[1:])


@pytest.mark.loopback
@pytest.mark.parametrize("policy,scale", (("danjon_angular", 1.0), ("static_finite_cone", 1.01)))
def test_lunar_candidate_retains_policy_contacts_and_incompleteness(
    diagnostic_client, policy, scale,
):
    center = julian_day(2022, 11, 8, 11.0)
    response = diagnostic_client.post(LUNAR_SHADOW, json={
        "center_jd_ut1": center, "policy": policy, "earth_radius_scale": scale,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "detected"
    assert body["complete"] is False
    assert body["time_scale"] == "UT1"
    assert body["event"]["policy"] == policy
    assert body["event"]["earth_radius_scale"] == scale
    assert body["event"]["candidate_type"] == "total"
    assert body["event"]["contacts"]["p1_jd_ut1"] < body["event"]["greatest_jd_ut1"]
    assert body["event"]["contacts"]["p4_jd_ut1"] > body["event"]["greatest_jd_ut1"]


@pytest.mark.loopback
def test_site_and_refinement_keep_caller_metadata_and_bounds(diagnostic_client, eclipse_calculator):
    jd = julian_day(2024, 4, 8, 18 + 40 / 60)
    site = {"jd_ut1": jd, "latitude_deg": 32.7767, "longitude_deg": -96.7970}
    request = {**site, "lunation": 777, "tolerance_rad": 1e-9}
    response = diagnostic_client.post(SOLAR_SITE, json=request)
    assert response.status_code == 200, response.text
    body = response.json()
    direct = solar_visibility_at_site(eclipse_calculator, **request)
    assert body["geometry"]["status"] == direct.geometry.status == "visible"
    assert body["geometry"]["tolerance_rad"] == 1e-9
    assert body["lunation"] == 777
    assert body["jd_ut1"] == jd
    assert body["time_scale"] == "UT1"
    assert body["ephemeris"] == direct.ephemeris

    refinement = {
        "seed": site,
        "time_bounds_ut1": [jd - 60 / 86400, jd + 60 / 86400],
        "latitude_bounds_deg": [32.7, 32.9],
        "longitude_bounds_deg": [-96.9, -96.7],
        "max_iterations": 4,
        "lunation": 777,
        "tolerance_rad": 1e-9,
    }
    refined = diagnostic_client.post(SOLAR_REFINEMENT, json=refinement)
    assert refined.status_code == 200, refined.text
    result = refined.json()
    assert result["status"] == "witness_found"
    assert result["complete"] is False
    assert result["witness"]["lunation"] == 777
    assert result["witness"]["geometry"]["tolerance_rad"] == 1e-9
    assert result["domain"] == [refinement["time_bounds_ut1"],
                                refinement["latitude_bounds_deg"],
                                refinement["longitude_bounds_deg"]]


@pytest.mark.loopback
def test_swept_interior_witness_preserves_supplied_interval_and_lunation(diagnostic_client):
    t = julian_day(2003, 5, 31, 4 + 8 / 60)
    request = {
        "latitude_deg": 64.02666666666667, "longitude_deg": -28.0,
        "times_ut1": [t, t + 60 / 86400],
        "interval_ut1": [t, t + 120 / 86400],
        "lunation": 42, "tolerance_rad": 1e-9,
    }
    response = diagnostic_client.post(SOLAR_SWEPT, json=request)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "interior_witness"
    assert body["complete"] is False
    assert body["interval_ut1"] == request["interval_ut1"]
    assert body["lunation"] == 42
    assert body["witness"]["jd_ut1"] == request["times_ut1"][1]
    assert body["witness"]["geometry"]["tolerance_rad"] == 1e-9


@pytest.mark.loopback
@pytest.mark.parametrize("jd,status", ((2688474.069791377, "candidate"),
                                      (2457997.5, "unresolved")))
def test_central_cap_candidate_or_uncertainty_round_trips(diagnostic_client, jd, status):
    response = diagnostic_client.post(SOLAR_CAP, json={"jd_ut1": jd, "arc_samples": 17})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == status
    assert body["complete"] is False
    assert body["jd_ut1"] == jd
    if status == "unresolved":
        assert body["reason"]
        assert body["boundary"] is None
    else:
        assert body["reason"] is None
        boundary = body["boundary"]
        assert boundary["cone_arc"][-1] == boundary["horizon_arc"][0]
        assert boundary["cone_arc"][0] == boundary["horizon_arc"][-1]


@pytest.mark.loopback
@pytest.mark.parametrize("route,payload", (
    (LUNAR_SHADOW, {"center_jd_ut1": 2450000.0, "policy": "unknown"}),
    (LUNAR_SHADOW, {"center_jd_ut1": 2450000.0, "policy": "danjon_angular", "earth_radius_scale": 1.01}),
    (LUNAR_SHADOW, {"center_jd_ut1": 2450000.0, "policy": "static_finite_cone", "window_days": 1.0, "coarse_step_seconds": 10.0}),
    (SOLAR_SITE, {"jd_ut1": 2450000.0, "latitude_deg": 91.0, "longitude_deg": 0.0}),
    (SOLAR_SITE, {"jd_ut1": 2450000.0, "latitude_deg": 0.0, "longitude_deg": 0.0, "tolerance_rad": 1e-13}),
    (SOLAR_CAP, {"jd_ut1": 2450000.0, "arc_samples": 2050}),
    (SOLAR_REFINEMENT, {"seed": {"jd_ut1": 2450000.0, "latitude_deg": 0.0, "longitude_deg": 0.0},
                        "time_bounds_ut1": [2450000.0, 2450001.0], "latitude_bounds_deg": [2.0, 1.0],
                        "longitude_bounds_deg": [0.0, 1.0]}),
    (SOLAR_SWEPT, {"latitude_deg": 0.0, "longitude_deg": 0.0,
                   "times_ut1": [2450001.0], "interval_ut1": [2450000.0, 2450000.5]}),
))
def test_other_diagnostic_requests_enforce_model_and_domain_bounds(diagnostic_client, route, payload):
    response = diagnostic_client.post(route, json=payload)
    assert response.status_code == 422, response.text


@pytest.mark.loopback
def test_ephemeris_coverage_error_is_distinct_from_bad_input(diagnostic_client, monkeypatch):
    def outside_coverage(*_args, **_kwargs):
        raise OutOfRangeError("injected missing retarded-epoch coverage", out_of_range_times=True)

    monkeypatch.setattr(
        "moira_server.routers.eclipse_diagnostics.compute_hybrid_diagnostic", outside_coverage,
    )
    coverage = diagnostic_client.post(SOLAR_HYBRID, json={"jd_start_ut1": 2460054.0})
    assert coverage.status_code == 422, coverage.text
    assert coverage.json()["category"] == "ephemeris_coverage"
    assert coverage.json()["error_code"] == "eclipse_ephemeris_coverage_unavailable"
    invalid = diagnostic_client.post(SOLAR_HYBRID, json={"jd_start_ut1": "not a Julian day"})
    assert invalid.status_code == 422, invalid.text
    assert invalid.json()["category"] == "input_validation"


@pytest.mark.loopback
@pytest.mark.parametrize("backward", (False, True))
def test_hybrid_public_search_coverage_failure_reaches_transport(
    diagnostic_client, monkeypatch, backward,
):
    # Inject the failure in the shared calculation, not in the router, so the
    # test covers the complete service-to-error-mapping path in each direction.
    def missing_coverage(*_args, **_kwargs):
        raise OutOfRangeError("injected phase-window coverage", out_of_range_times=True)

    method = "previous_solar_eclipse" if backward else "next_solar_eclipse"
    monkeypatch.setattr("moira.eclipse.EclipseCalculator." + method, missing_coverage)
    response = diagnostic_client.post(SOLAR_HYBRID, json={
        "jd_start_ut1": 2460000.0, "backward": backward,
    })
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["category"] == "ephemeris_coverage"
    assert body["error_code"] == "eclipse_ephemeris_coverage_unavailable"
