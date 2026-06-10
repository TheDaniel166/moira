from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.transits import (
    find_ingresses,
    find_lunar_phases,
    find_transits,
    next_ingress,
)

from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


@pytest.mark.requires_ephemeris
def test_transit_search_route_preserves_selected_event_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    # Default (no step_days) — must match prior behavior exactly.
    direct_default = moira_engine.transits("Sun", 300.0, 2451545.0, 2451545.0 + 365.25)

    response = client_with_engine.post(
        "/v1/transits/search",
        json={
            "body": "Sun",
            "target_lon": 300.0,
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 365.25,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == len(direct_default)
    assert body["events"][0]["jd_ut"] == pytest.approx(direct_default[0].jd_ut)
    assert body["events"][0]["direction"] == direct_default[0].direction
    assert body["events"][0]["relation"]["relation_kind"] == direct_default[0].relation.relation_kind.value
    assert body["events"][0]["classification"]["search"]["wrapper_kind"] == direct_default[0].classification.search.wrapper_kind.value
    assert body["events"][0]["computation_truth"]["target_truth"]["resolved_name"] == direct_default[0].computation_truth.target_truth.resolved_name

    # Explicit step_days (enrichment) — use low-level direct for parity (positions/phenomena precedent).
    reader = getattr(moira_engine, "_reader", None)
    direct_with_step = find_transits(
        "Sun", 300.0, 2451545.0, 2451545.0 + 365.25, step_days=0.25, reader=reader, search_motion="forward"
    )

    response2 = client_with_engine.post(
        "/v1/transits/search",
        json={
            "body": "Sun",
            "target_lon": 300.0,
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 365.25,
            "step_days": 0.25,
            "solver_tolerance_days": 1e-5,
            "direction": "either",
        },
    )

    assert response2.status_code == 200
    body2 = response2.json()
    assert len(body2["events"]) == len(direct_with_step)
    # Rich truth still flows (the main contract for this family).
    assert body2["events"][0]["computation_truth"] is not None
    assert body2["events"][0]["relation"] is not None
    assert body2["events"][0]["jd_ut"] == pytest.approx(direct_with_step[0].jd_ut)
    # Requested echo (B decisions for the unresolved items).
    ct = body2["events"][0]["computation_truth"]
    assert ct["requested_step_days"] == 0.25
    assert ct["requested_tolerance_days"] == 1e-5
    assert ct["requested_direction"] == "either"


@pytest.mark.requires_ephemeris
def test_ingress_search_route_preserves_sign_and_boundary_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct_default = moira_engine.ingresses("Sun", 2451545.0, 2451545.0 + 40.0)

    response = client_with_engine.post(
        "/v1/transits/ingresses",
        json={
            "body": "Sun",
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 40.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == len(direct_default)
    assert body["events"][0]["sign"] == direct_default[0].sign
    assert body["events"][0]["sign_longitude"] == pytest.approx(direct_default[0].sign_longitude)
    assert body["events"][0]["relation"]["basis"] == direct_default[0].relation.basis.value

    # Explicit step_days enrichment + low-level parity.
    reader = getattr(moira_engine, "_reader", None)
    direct_with_step = find_ingresses("Sun", 2451545.0, 2451545.0 + 40.0, step_days=0.5, reader=reader)

    response2 = client_with_engine.post(
        "/v1/transits/ingresses",
        json={
            "body": "Sun",
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 40.0,
            "step_days": 0.5,
            "solver_tolerance_days": 1e-6,
            "direction": "either",
        },
    )

    assert response2.status_code == 200
    body2 = response2.json()
    assert len(body2["events"]) == len(direct_with_step)
    assert body2["events"][0]["computation_truth"] is not None  # rich truth preserved
    assert body2["events"][0]["sign_longitude"] == pytest.approx(direct_with_step[0].sign_longitude)
    ct = body2["events"][0]["computation_truth"]
    assert ct["requested_step_days"] == 0.5
    assert ct.get("requested_tolerance_days") == 1e-6


@pytest.mark.requires_ephemeris
def test_next_ingress_route_matches_engine_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct_default = moira_engine.next_ingress("Sun", 2451545.0)

    response = client_with_engine.post(
        "/v1/transits/next-ingress",
        json={
            "body": "Sun",
            "jd_start": 2451545.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sign"] == direct_default.sign
    assert body["jd_ut"] == pytest.approx(direct_default.jd_ut)
    assert body["direction"] == direct_default.direction

    # With step_days (via policy in low-level) + parity.
    reader = getattr(moira_engine, "_reader", None)
    from moira.transits import TransitComputationPolicy, TransitSearchPolicy
    policy = TransitComputationPolicy(ingress=TransitSearchPolicy(step_days_override=0.5))
    direct_with_step = next_ingress("Sun", 2451545.0, reader=reader, max_days=None, policy=policy)

    response2 = client_with_engine.post(
        "/v1/transits/next-ingress",
        json={
            "body": "Sun",
            "jd_start": 2451545.0,
            "step_days": 0.5,
            "solver_tolerance_days": 1e-6,
            "direction": "either",
        },
    )

    assert response2.status_code == 200
    body2 = response2.json()
    assert body2["sign"] == direct_with_step.sign
    assert body2["computation_truth"] is not None  # rich truth preserved even for next-ingress
    assert body2["jd_ut"] == pytest.approx(direct_with_step.jd_ut)
    ct = body2["computation_truth"]
    assert ct["requested_step_days"] == 0.5
    assert ct.get("requested_tolerance_days") == 1e-6


@pytest.mark.requires_ephemeris
def test_return_routes_match_engine_selected_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    natal = moira_engine.chart(dt, bodies=["Sun", "Moon", "Venus"], include_nodes=False)

    solar_direct = moira_engine.solar_return(natal.planets["Sun"].longitude, 2001)
    lunar_direct = moira_engine.lunar_return(natal.planets["Moon"].longitude, natal.jd_ut + 1.0)
    planet_direct = moira_engine.planet_return("Venus", natal.planets["Venus"].longitude, natal.jd_ut + 1.0)

    solar_response = client_with_engine.post(
        "/v1/returns/solar",
        json={"natal_sun_lon": natal.planets["Sun"].longitude, "year": 2001},
    )
    lunar_response = client_with_engine.post(
        "/v1/returns/lunar",
        json={"natal_moon_lon": natal.planets["Moon"].longitude, "jd_start": natal.jd_ut + 1.0},
    )
    planet_response = client_with_engine.post(
        "/v1/returns/planet",
        json={
            "body": "Venus",
            "natal_lon": natal.planets["Venus"].longitude,
            "jd_start": natal.jd_ut + 1.0,
        },
    )

    assert solar_response.status_code == 200
    assert solar_response.json()["return_type"] == "solar_return"
    assert solar_response.json()["jd_ut"] == pytest.approx(solar_direct)

    assert lunar_response.status_code == 200
    assert lunar_response.json()["return_type"] == "lunar_return"
    assert lunar_response.json()["jd_ut"] == pytest.approx(lunar_direct)

    assert planet_response.status_code == 200
    assert planet_response.json()["body"] == "Venus"
    assert planet_response.json()["jd_ut"] == pytest.approx(planet_direct)


@pytest.mark.requires_ephemeris
def test_lunar_phases_route_matches_engine_phase_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    # Use canonical find_lunar_phases (the thin calendar surface) for direct parity.
    # This matches what the route now delegates to (lunar enrichment).
    reader = getattr(moira_engine, "_reader", None)
    direct = find_lunar_phases(2451545.0, 2451545.0 + 40.0, reader=reader)

    response = client_with_engine.post(
        "/v1/lunar-phases",
        json={
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 40.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == len(direct)
    assert body["events"][0]["phase_type"] == direct[0].phase_type
    assert body["events"][0]["jd_ut"] == pytest.approx(direct[0].jd_ut)
    assert body["events"][0]["phase_angle"] == pytest.approx(direct[0].phase_angle)


@pytest.mark.requires_ephemeris
def test_transit_search_large_step_produces_fewer_or_equal_brackets_but_stable_final_jds(
    moira_engine,
) -> None:
    """Dedicated regression/hardening test for the risk documented in the transits
    enrichment plan (Section 5):

    A deliberately *very large* step_days can cause the linear scan to discover
    fewer sign-change brackets (different "bracket count" before bisection),
    because coarse sampling can jump over a crossing without the (prev, next)
    pair straddling the zero in signed difference.

    However, any crossing that *is* discovered must still be refined by bisection
    to a final JD that is stable (within solver tolerance) compared to a fine-grained
    search. The final .jd_ut and .direction must agree.

    This test exercises the control surface added for step_days and asserts the
    expected "different count, stable result" invariant using the low-level engine
    surface (consistent with other parity tests in this file).
    """
    body = "Moon"          # fast mover (~13°/day) makes coarse steps likely to miss brackets
    target_lon = 0.0
    jd_start = 2451545.0
    jd_end = jd_start + 60.0   # long enough for Moon to produce 1-2 crossings of the target

    reader = getattr(moira_engine, "_reader", None)

    # Fine-grained (small step) — should discover (nearly) all crossings
    fine = find_transits(
        body, target_lon, jd_start, jd_end, step_days=0.05, reader=reader
    )

    # Deliberately very large/coarse step (the risk case)
    coarse = find_transits(
        body, target_lon, jd_start, jd_end, step_days=8.0, reader=reader
    )

    # The risk surface we are making visible:
    # Large step must never produce *more* bracketed crossings than the fine scan.
    # In practice with a fast body + coarse step we often see strictly fewer.
    assert len(coarse) <= len(fine), (
        f"Large step_days produced more brackets ({len(coarse)}) than fine scan ({len(fine)}). "
        "This would indicate a search logic problem."
    )

    # Core invariant: final JD stability + direction agreement for everything the coarse
    # search actually found.
    stability_tol_days = 1e-5   # comfortably inside the normal 1e-6 solver tolerance
    for c in coarse:
        # Find a close match in the fine result set
        matches = [
            f for f in fine
            if abs(f.jd_ut - c.jd_ut) < stability_tol_days and f.direction == c.direction
        ]
        assert matches, (
            f"Coarse crossing (jd={c.jd_ut}, dir={c.direction}) has no stable match "
            f"in the fine-grained search (tolerance={stability_tol_days} days)."
        )

        # As a bonus, the engine's own search_truth should still report a sensible tolerance
        if c.computation_truth is not None:
            tol = c.computation_truth.search_truth.solver_tolerance_days
            assert 0 < tol <= 1e-3, f"Unexpected solver tolerance in truth: {tol}"


def test_phase_three_routes_reject_reversed_windows_and_invalid_bodies(
    client_with_engine: TestClient,
) -> None:
    reversed_window = client_with_engine.post(
        "/v1/lunar-phases",
        json={"jd_start": 2451545.0 + 10.0, "jd_end": 2451545.0},
    )
    invalid_body = client_with_engine.post(
        "/v1/returns/planet",
        json={"body": "NotAPlanet", "natal_lon": 123.0, "jd_start": 2451545.0},
    )

    assert reversed_window.status_code == 422
    assert reversed_window.json()["error_code"] == "validation_error"
    assert "jd_end" in reversed_window.json()["message"]

    assert invalid_body.status_code == 422
    assert invalid_body.json()["error_code"] == "validation_error"
    assert "NotAPlanet" in invalid_body.json()["message"]

    # New control: bad step_days must 422 (validation in service).
    bad_step = client_with_engine.post(
        "/v1/transits/search",
        json={
            "body": "Sun",
            "target_lon": 300.0,
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 10.0,
            "step_days": -1.0,
        },
    )
    assert bad_step.status_code == 422
    assert bad_step.json()["error_code"] == "validation_error"
    assert "step_days" in bad_step.json()["message"]
