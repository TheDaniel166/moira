"""REST contract tests for /v1/out-of-bounds/search.

Transport behaviour only: the engine call is stubbed so the contract is
tested without an ephemeris. The engine's own correctness lives in
``tests/unit/test_out_of_bounds.py`` and
``tests/integration/test_out_of_bounds_de441.py``.
"""

from __future__ import annotations

import math

from fastapi.testclient import TestClient
import pytest

from moira.out_of_bounds import (
    OutOfBoundsBudgetError,
    OutOfBoundsCrossing,
    OutOfBoundsCulmination,
    OutOfBoundsExcursion,
    OutOfBoundsPolicy,
    OutOfBoundsReport,
    OutOfBoundsScanTruth,
    OutOfBoundsUnavailableError,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeEngine:
    _reader = None

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.result = None
        self.raises: Exception | None = None

    def out_of_bounds(self, body, jd_start, jd_end, *, policy=None):
        self.calls.append((body, jd_start, jd_end, policy))
        if self.raises is not None:
            raise self.raises
        return self.result


def _crossing(kind: str, jd_ut: float, *, rate: float = 2.0) -> OutOfBoundsCrossing:
    arcsec_per_day = abs(rate) * 3600.0
    return OutOfBoundsCrossing(
        kind=kind,
        jd_ut=jd_ut,
        declination=23.6,
        obliquity=23.44,
        declination_rate_deg_per_day=rate,
        obliquity_rate_deg_per_day=1.0e-5,
        bound_rate_deg_per_day=rate,
        time_sensitivity_days_per_arcsec=(
            1.0 / arcsec_per_day if arcsec_per_day else math.inf
        ),
        achieved_tolerance_days=5.0e-8,
        bracket_start_jd_ut=jd_ut - 2.5e-8,
        bracket_end_jd_ut=jd_ut + 2.5e-8,
        conditioning="well_posed" if abs(rate) > 0.0 else "degenerate",
    )


def _culmination(jd_ut: float, *, at_boundary: bool = False) -> OutOfBoundsCulmination:
    return OutOfBoundsCulmination(
        jd_ut=jd_ut,
        declination=23.9,
        obliquity=23.44,
        excess_deg=0.46,
        at_boundary=at_boundary,
        boundary_edge="range_start" if at_boundary else None,
        interior_critical_points=0 if at_boundary else 1,
    )


def _scan_truth() -> OutOfBoundsScanTruth:
    return OutOfBoundsScanTruth(
        coarse_step_days=0.5,
        measured_max_rate_deg_per_day=5.7,
        measured_median_rate_deg_per_day=3.0,
        rate_bound_deg_per_day=17.1,
        resolved_amplitude_floor_deg=4.3,
        coarse_node_count=18,
        refined_interval_count=42,
        unresolved_intervals=0,
        declination_evaluations=512,
        policy=OutOfBoundsPolicy(),
    )


def _report(
    *,
    excursions: tuple[OutOfBoundsExcursion, ...] = (),
    out_at_start: bool = False,
    out_at_end: bool = False,
    body: str = "Moon",
    resolved_kind: str = "planet",
) -> OutOfBoundsReport:
    return OutOfBoundsReport(
        body=body,
        resolved_name=body,
        resolved_kind=resolved_kind,
        jd_start=2458909.5,
        jd_end=2458918.5,
        excursions=excursions,
        out_of_bounds_at_start=out_at_start,
        out_of_bounds_at_end=out_at_end,
        scan_truth=_scan_truth(),
        obliquity_at_start=23.4365,
        obliquity_at_end=23.4366,
    )


def _complete_excursion() -> OutOfBoundsExcursion:
    entry = _crossing("entry", 2458913.474243)
    departure = _crossing("departure", 2458913.656325, rate=-2.0)
    return OutOfBoundsExcursion(
        body="Moon",
        hemisphere="north",
        jd_start_observed=entry.jd_ut,
        jd_end_observed=departure.jd_ut,
        entry=entry,
        departure=departure,
        entry_clipped=False,
        departure_clipped=False,
        culmination=_culmination(2458913.5654),
        duration_hours=4.37,
        duration_is_lower_bound=False,
    )


def _clipped_excursion() -> OutOfBoundsExcursion:
    departure = _crossing("departure", 2458913.656325, rate=-2.0)
    return OutOfBoundsExcursion(
        body="Moon",
        hemisphere="south",
        jd_start_observed=2458909.5,
        jd_end_observed=departure.jd_ut,
        entry=None,
        departure=departure,
        entry_clipped=True,
        departure_clipped=False,
        culmination=_culmination(2458909.5, at_boundary=True),
        duration_hours=99.75,
        duration_is_lower_bound=True,
    )


@pytest.fixture
def engine() -> _FakeEngine:
    return _FakeEngine()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, engine: _FakeEngine) -> TestClient:
    monkeypatch.setattr(
        "moira_server.app.create_engine", lambda config: engine
    )
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _request(**overrides) -> dict:
    payload = {"body": "Moon", "jd_start": 2458909.5, "jd_end": 2458918.5}
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Happy path and shape
# ---------------------------------------------------------------------------

def test_route_returns_a_complete_excursion(client, engine):
    engine.result = _report(excursions=(_complete_excursion(),))
    response = client.post("/v1/out-of-bounds/search", json=_request())
    assert response.status_code == 200
    body = response.json()
    assert body["body"] == "Moon"
    assert body["resolved_kind"] == "planet"
    assert body["excursion_count"] == 1
    excursion = body["excursions"][0]
    assert excursion["hemisphere"] == "north"
    assert excursion["is_complete"] is True
    assert excursion["entry_clipped"] is False
    assert excursion["departure_clipped"] is False
    assert excursion["duration_is_lower_bound"] is False
    assert excursion["duration_hours"] == pytest.approx(4.37)


def test_every_crossing_carries_its_conditioning_receipt(client, engine):
    """The route's whole value over client-side interpolation."""
    engine.result = _report(excursions=(_complete_excursion(),))
    response = client.post("/v1/out-of-bounds/search", json=_request())
    entry = response.json()["excursions"][0]["entry"]
    assert entry["kind"] == "entry"
    assert entry["declination_rate_deg_per_day"] == pytest.approx(2.0)
    assert entry["obliquity_rate_deg_per_day"] == pytest.approx(1.0e-5)
    assert entry["bound_rate_deg_per_day"] == pytest.approx(2.0)
    assert entry["achieved_tolerance_days"] == pytest.approx(5.0e-8)
    assert entry["conditioning"] == "well_posed"
    # 2 deg/day is 7200 arcsec/day, so one arcsecond costs 12 seconds.
    assert entry["time_sensitivity_seconds_per_arcsec"] == pytest.approx(12.0)
    assert entry["bracket_start_jd_ut"] <= entry["jd_ut"] <= entry["bracket_end_jd_ut"]


def test_datetimes_accompany_every_instant(client, engine):
    engine.result = _report(excursions=(_complete_excursion(),))
    excursion = client.post(
        "/v1/out-of-bounds/search", json=_request()
    ).json()["excursions"][0]
    assert excursion["datetime_start_utc"].startswith("2020-03-")
    assert excursion["datetime_end_utc"].startswith("2020-03-")
    assert excursion["entry"]["datetime_utc"].startswith("2020-03-")
    assert excursion["culmination"]["datetime_utc"].startswith("2020-03-")


def test_culmination_is_reported_with_its_boundary_state(client, engine):
    engine.result = _report(excursions=(_clipped_excursion(),), out_at_start=True)
    excursion = client.post(
        "/v1/out-of-bounds/search", json=_request()
    ).json()["excursions"][0]
    culmination = excursion["culmination"]
    assert culmination["at_boundary"] is True
    assert culmination["boundary_edge"] == "range_start"
    assert culmination["interior_critical_points"] == 0
    assert culmination["excess_deg"] == pytest.approx(0.46)


def test_clipped_window_is_explicit_in_the_response(client, engine):
    """A clipped duration must be marked, not silently truncated."""
    engine.result = _report(excursions=(_clipped_excursion(),), out_at_start=True)
    body = client.post("/v1/out-of-bounds/search", json=_request()).json()
    assert body["out_of_bounds_at_start"] is True
    excursion = body["excursions"][0]
    assert excursion["entry"] is None
    assert excursion["entry_clipped"] is True
    assert excursion["duration_is_lower_bound"] is True
    assert excursion["is_complete"] is False


def test_scan_truth_is_exposed_with_its_policy(client, engine):
    engine.result = _report(excursions=(_complete_excursion(),))
    truth = client.post(
        "/v1/out-of-bounds/search", json=_request()
    ).json()["scan_truth"]
    assert truth["coarse_step_days"] == pytest.approx(0.5)
    assert truth["measured_max_rate_deg_per_day"] == pytest.approx(5.7)
    assert truth["resolved_amplitude_floor_deg"] == pytest.approx(4.3)
    assert truth["unresolved_intervals"] == 0
    assert truth["declination_evaluations"] == 512
    assert truth["policy"]["solver_tolerance_days"] > 0.0
    assert truth["policy"]["close_approach_refinement_depth"] >= 0


def test_empty_result_is_an_empty_list_with_a_scan_receipt(client, engine):
    engine.result = _report()
    body = client.post("/v1/out-of-bounds/search", json=_request()).json()
    assert body["excursion_count"] == 0
    assert body["excursions"] == []
    assert body["scan_truth"]["declination_evaluations"] == 512


def test_degenerate_sensitivity_is_representable(client, engine):
    """An infinite sensitivity must not break JSON encoding."""
    crossing = _crossing("entry", 2458913.0, rate=0.0)
    excursion = OutOfBoundsExcursion(
        body="Moon",
        hemisphere="north",
        jd_start_observed=2458913.0,
        jd_end_observed=2458914.0,
        entry=crossing,
        departure=None,
        entry_clipped=False,
        departure_clipped=True,
        culmination=_culmination(2458913.5),
        duration_hours=24.0,
        duration_is_lower_bound=True,
    )
    engine.result = _report(excursions=(excursion,), out_at_end=True)
    response = client.post("/v1/out-of-bounds/search", json=_request())
    assert response.status_code == 200
    entry = response.json()["excursions"][0]["entry"]
    assert entry["conditioning"] == "degenerate"
    assert entry["time_sensitivity_seconds_per_arcsec"] == -1.0


# ---------------------------------------------------------------------------
# Body admission
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "body",
    ["Moon", "Pluto", "Ceres", "asteroid:Ceres", "2P/Encke", "comet:2P/Encke"],
)
def test_planets_points_asteroids_and_comets_are_admitted(client, engine, body):
    engine.result = _report(body=body)
    response = client.post("/v1/out-of-bounds/search", json=_request(body=body))
    assert response.status_code == 200, response.json()
    assert engine.calls[-1][0] == body


@pytest.mark.parametrize("body", ["Nibiru", "", "   ", "Planet X"])
def test_unknown_body_is_rejected_at_the_transport_boundary(client, engine, body):
    response = client.post("/v1/out-of-bounds/search", json=_request(body=body))
    assert response.status_code == 422
    assert engine.calls == []


@pytest.mark.parametrize(
    "body", ["True Node", "Mean Node", "Lilith", "True Lilith"]
)
def test_longitude_only_points_are_refused_with_their_own_reason(
    client, engine, body
):
    """A node is a known body with no declination, not an unknown body.

    Moira models the lunar nodes and apogees as longitude-only, so no
    declination exists to compare against the obliquity. The message has to say
    that rather than claim the body is unrecognised. A node also lies on the
    ecliptic by construction, so it could never be out of bounds anyway.
    """
    response = client.post("/v1/out-of-bounds/search", json=_request(body=body))
    assert response.status_code == 422
    message = response.json()["message"]
    assert "longitude-only" in message
    assert "unsupported" not in message
    assert engine.calls == []


def test_rejection_message_names_the_small_body_forms(client, engine):
    response = client.post("/v1/out-of-bounds/search", json=_request(body="Nibiru"))
    message = response.json()["message"]
    assert "asteroid/comet" in message


# ---------------------------------------------------------------------------
# Window and control validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("jd_start", "jd_end"),
    [(2458918.5, 2458909.5), (2458909.5, 2458909.5)],
)
def test_unordered_window_is_rejected(client, engine, jd_start, jd_end):
    response = client.post(
        "/v1/out-of-bounds/search",
        json=_request(jd_start=jd_start, jd_end=jd_end),
    )
    assert response.status_code == 422
    assert engine.calls == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"angular_resolution_deg": 0.0},
        {"angular_resolution_deg": -1.0},
        {"max_step_days": 0.0},
        {"solver_tolerance_days": -1.0},
    ],
)
def test_non_positive_controls_are_rejected(client, engine, overrides):
    response = client.post("/v1/out-of-bounds/search", json=_request(**overrides))
    assert response.status_code == 422
    assert engine.calls == []


def test_omitted_controls_leave_the_engine_defaults_in_place(client, engine):
    """Only the route's own ceiling is set when the caller sends no controls."""
    engine.result = _report()
    client.post("/v1/out-of-bounds/search", json=_request())
    policy = engine.calls[-1][3]
    default = OutOfBoundsPolicy()
    assert policy.angular_resolution_deg == default.angular_resolution_deg
    assert policy.max_step_days == default.max_step_days
    assert policy.solver_tolerance_days == default.solver_tolerance_days
    assert policy.max_declination_evaluations == 100_000


def test_supplied_controls_become_an_explicit_policy(client, engine):
    engine.result = _report()
    client.post(
        "/v1/out-of-bounds/search",
        json=_request(
            angular_resolution_deg=0.25,
            max_step_days=1.0,
            solver_tolerance_days=1e-8,
        ),
    )
    policy = engine.calls[-1][3]
    assert isinstance(policy, OutOfBoundsPolicy)
    assert policy.angular_resolution_deg == pytest.approx(0.25)
    assert policy.max_step_days == pytest.approx(1.0)
    assert policy.solver_tolerance_days == pytest.approx(1e-8)


def test_route_always_imposes_an_evaluation_ceiling(client, engine):
    """Cost is linear in the span, so an unbounded span must not be accepted.

    The engine defaults to no ceiling for library callers; the route has to
    supply one of its own even when the caller sends no controls at all.
    """
    engine.result = _report()
    client.post("/v1/out-of-bounds/search", json=_request())
    policy = engine.calls[-1][3]
    assert policy is not None
    assert policy.max_declination_evaluations == 100_000


def test_a_smaller_caller_budget_is_honoured(client, engine):
    engine.result = _report()
    client.post(
        "/v1/out-of-bounds/search",
        json=_request(max_declination_evaluations=5_000),
    )
    assert engine.calls[-1][3].max_declination_evaluations == 5_000


@pytest.mark.parametrize("budget", [0, -1, 100_001, 10_000_000])
def test_a_budget_outside_the_route_ceiling_is_rejected(client, engine, budget):
    response = client.post(
        "/v1/out-of-bounds/search",
        json=_request(max_declination_evaluations=budget),
    )
    assert response.status_code == 422
    assert engine.calls == []


def test_exhausted_budget_is_its_own_error_code(client, engine):
    engine.raises = OutOfBoundsBudgetError("Moon", 100_000, 100_000, "scan")
    response = client.post("/v1/out-of-bounds/search", json=_request())
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "out_of_bounds_search_budget"
    assert body["category"] == "search_budget"
    assert body["details"] == {
        "body": "Moon",
        "budget": 100_000,
        "evaluations": 100_000,
        "stage": "scan",
    }


def test_unknown_request_field_is_rejected(client, engine):
    response = client.post(
        "/v1/out-of-bounds/search", json=_request(step_days=1.0)
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Unavailable, never a silent empty result
# ---------------------------------------------------------------------------

def test_uncovered_ephemeris_is_its_own_error_code(client, engine):
    engine.raises = OutOfBoundsUnavailableError(
        "Apophis", "ephemeris_coverage", "JD(UT1) 2461358.5"
    )
    response = client.post("/v1/out-of-bounds/search", json=_request(body="Eros"))
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "out_of_bounds_date_outside_ephemeris_coverage"
    assert body["category"] == "ephemeris_coverage"
    assert body["details"]["body"] == "Apophis"
    assert body["details"]["reason"] == "ephemeris_coverage"


def test_unresolved_body_from_the_engine_is_input_validation(client, engine):
    engine.raises = OutOfBoundsUnavailableError("Eros", "body_unresolved")
    response = client.post("/v1/out-of-bounds/search", json=_request(body="Eros"))
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "out_of_bounds_unknown_body"
    assert body["category"] == "input_validation"


def test_unavailable_is_not_reported_as_a_generic_validation_error(client, engine):
    """It must not collapse into the ValueError fallback.

    ``OutOfBoundsUnavailableError`` subclasses ``ValueError`` so that engine
    callers can catch it broadly, which means the dedicated handler has to win
    the MRO lookup against the generic handler. This test is what keeps that
    true.
    """
    engine.raises = OutOfBoundsUnavailableError("Eros", "ephemeris_coverage")
    body = client.post(
        "/v1/out-of-bounds/search", json=_request(body="Eros")
    ).json()
    assert body["error_code"] != "validation_error"


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def test_route_is_registered_under_the_predictive_tag(client):
    schema = client.app.openapi()
    path = schema["paths"]["/v1/out-of-bounds/search"]["post"]
    assert "predictive" in path["tags"]
