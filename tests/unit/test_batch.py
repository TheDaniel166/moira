from __future__ import annotations

from datetime import datetime, timezone

import moira.batch as batch_module
import moira.facade as facade_module
from moira.facade import Moira


def test_batch_module_public_exports_are_bound() -> None:
    expected = {
        "PlanetTimeSeries",
        "BatchFailure",
        "ChartBatchRequest",
        "ChartBatchResult",
        "EventBatchRequest",
        "EventBatchResult",
        "ReturnBatchRequest",
        "ReturnBatchResult",
        "TransitBatchRequest",
        "TransitBatchResult",
        "ProgressionBatchRequest",
        "ProgressionBatchResult",
        "BodyVoidWindow",
        "BodyVoidWindows",
        "BATCH_EVENT_KINDS",
        "BATCH_RETURN_KINDS",
        "BATCH_PROGRESSION_TECHNIQUES",
        "planet_time_series",
        "batch_charts",
        "batch_events",
        "batch_transits",
        "batch_returns",
        "batch_progressions",
        "find_all_ingresses",
        "void_periods_all_planets",
    }
    assert expected <= set(batch_module.__all__)
    for name in expected:
        assert hasattr(batch_module, name)


def test_batch_failure_captures_module_and_empty_message_fallback() -> None:
    exc = RuntimeError()
    failure = batch_module._capture_failure(exc)

    assert failure.error_type == "RuntimeError"
    assert failure.error_module == "builtins"
    assert failure.message


def test_batch_result_invariants_reject_ambiguous_state() -> None:
    request = batch_module.ReturnBatchRequest("solar_return", 15.0, year=2025)
    failure = batch_module.BatchFailure("ValueError", "bad", "builtins")

    try:
        batch_module.ReturnBatchResult(request=request)
    except ValueError as exc:
        assert "exactly one" in str(exc)
    else:
        raise AssertionError("ReturnBatchResult accepted neither success nor failure")

    try:
        batch_module.ReturnBatchResult(request=request, jd_ut=1.0, failure=failure)
    except ValueError as exc:
        assert "exactly one" in str(exc)
    else:
        raise AssertionError("ReturnBatchResult accepted both success and failure")


def test_batch_charts_uses_request_objects(monkeypatch) -> None:
    calls: list[tuple[datetime, float | None, float | None, float]] = []

    def fake_chart_at_datetime(
        dt: datetime,
        *,
        reader,
        bodies,
        include_nodes,
        observer_lat,
        observer_lon,
        observer_elev_m,
    ):
        calls.append((dt, observer_lat, observer_lon, observer_elev_m))
        return f"chart:{dt.isoformat()}"

    monkeypatch.setattr(batch_module, "_chart_at_datetime", fake_chart_at_datetime)

    requests = (
        batch_module.ChartBatchRequest(
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            observer_lat=40.0,
            observer_lon=-74.0,
            observer_elev_m=10.0,
        ),
        batch_module.ChartBatchRequest(
            datetime(2024, 1, 2, tzinfo=timezone.utc),
            observer_lat=41.0,
            observer_lon=-73.0,
            observer_elev_m=20.0,
        ),
    )
    results = batch_module.batch_charts(requests, reader=object())

    assert [result.request for result in results] == list(requests)
    assert [result.chart for result in results] == [
        "chart:2024-01-01T00:00:00+00:00",
        "chart:2024-01-02T00:00:00+00:00",
    ]
    assert calls == [
        (requests[0].dt, 40.0, -74.0, 10.0),
        (requests[1].dt, 41.0, -73.0, 20.0),
    ]


def test_batch_charts_rejects_unpaired_topocentric_inputs() -> None:
    results = batch_module.batch_charts(
        (
            batch_module.ChartBatchRequest(
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                observer_lat=40.0,
            ),
        ),
        reader=object(),
    )

    assert results[0].ok is False
    assert results[0].chart is None
    assert results[0].failure is not None
    assert "observer_lat and observer_lon must be provided together" in results[0].failure.message


def test_batch_charts_isolates_per_request_failures(monkeypatch) -> None:
    def fake_chart_at_datetime(dt, **kwargs):
        if dt.day == 2:
            raise ValueError("bad chart request")
        return f"chart:{dt.isoformat()}"

    monkeypatch.setattr(batch_module, "_chart_at_datetime", fake_chart_at_datetime)

    requests = (
        batch_module.ChartBatchRequest(datetime(2024, 1, 1, tzinfo=timezone.utc)),
        batch_module.ChartBatchRequest(datetime(2024, 1, 2, tzinfo=timezone.utc)),
    )
    results = batch_module.batch_charts(requests, reader=object())

    assert results[0].ok is True
    assert results[0].chart == "chart:2024-01-01T00:00:00+00:00"
    assert results[1].ok is False
    assert results[1].failure is not None
    assert results[1].failure.error_type == "ValueError"


def test_batch_transits_preserves_request_order(monkeypatch) -> None:
    def fake_find_transits(
        body,
        target_lon,
        jd_start,
        jd_end,
        *,
        step_days,
        reader,
        policy,
        search_motion,
    ):
        return [f"{body}:{target_lon}:{jd_start}:{jd_end}:{search_motion}"]

    monkeypatch.setattr(batch_module, "find_transits", fake_find_transits)

    requests = (
        batch_module.TransitBatchRequest("Mars", 90.0, 1.0, 2.0),
        batch_module.TransitBatchRequest("Venus", "Sun", 3.0, 4.0, search_motion="backward"),
    )
    results = batch_module.batch_transits(requests, reader=object())

    assert [result.request for result in results] == list(requests)
    assert [result.events for result in results] == [
        ("Mars:90.0:1.0:2.0:forward",),
        ("Venus:Sun:3.0:4.0:backward",),
    ]


def test_batch_transits_isolates_per_request_failures(monkeypatch) -> None:
    def fake_batch_events(requests, *, reader):
        return (
            batch_module.EventBatchResult(
                request=requests[0],
                failure=batch_module.BatchFailure("RuntimeError", "transit failed"),
            ),
            batch_module.EventBatchResult(
                request=requests[1],
                events=("ok",),
            ),
        )

    monkeypatch.setattr(batch_module, "batch_events", fake_batch_events)

    requests = (
        batch_module.TransitBatchRequest("Mars", 90.0, 1.0, 2.0),
        batch_module.TransitBatchRequest("Venus", "Sun", 3.0, 4.0),
    )
    results = batch_module.batch_transits(requests, reader=object())

    assert results[0].ok is False
    assert results[0].failure is not None
    assert results[1].ok is True
    assert results[1].events == ("ok",)


def test_batch_events_dispatches_mixed_event_requests(monkeypatch) -> None:
    def fake_find_transits(body, target_lon, jd_start, jd_end, *, step_days, reader, policy, search_motion):
        return [f"transit:{body}:{target_lon}:{search_motion}"]

    def fake_find_aspect_transits(body, target, angle, orb, jd_start, jd_end, *, step_days, reader, policy, search_motion):
        return [f"aspect:{body}:{target}:{angle}:{orb}:{search_motion}"]

    def fake_find_declination_transits(
        body,
        target,
        jd_start,
        jd_end,
        *,
        is_contra_parallel,
        step_days,
        reader,
        policy,
        search_motion,
    ):
        return [f"decl:{body}:{target}:{is_contra_parallel}:{search_motion}"]

    def fake_find_ingresses(body, jd_start, jd_end, *, step_days, reader, policy):
        return [f"ingress:{body}:{jd_start}:{jd_end}"]

    def fake_find_stations(body, jd_start, jd_end, *, step_days, reader):
        return [f"station:{body}:{jd_start}:{jd_end}"]

    monkeypatch.setattr(batch_module, "find_transits", fake_find_transits)
    monkeypatch.setattr(batch_module, "find_aspect_transits", fake_find_aspect_transits)
    monkeypatch.setattr(batch_module, "find_declination_transits", fake_find_declination_transits)
    monkeypatch.setattr(batch_module, "find_ingresses", fake_find_ingresses)
    monkeypatch.setattr(batch_module, "find_stations", fake_find_stations)

    requests = (
        batch_module.EventBatchRequest("transit", "Mars", 1.0, 2.0, target_lon=90.0),
        batch_module.EventBatchRequest("aspect_transit", "Venus", 3.0, 4.0, target="Sun", angle=120.0, orb=2.0),
        batch_module.EventBatchRequest("declination_transit", "Moon", 5.0, 6.0, target="Mars", is_contra_parallel=True),
        batch_module.EventBatchRequest("ingress", "Mercury", 7.0, 8.0),
        batch_module.EventBatchRequest("station", "Jupiter", 9.0, 10.0),
    )
    results = batch_module.batch_events(requests, reader=object())

    assert [result.request for result in results] == list(requests)
    assert [result.events for result in results] == [
        ("transit:Mars:90.0:forward",),
        ("aspect:Venus:Sun:120.0:2.0:forward",),
        ("decl:Moon:Mars:True:forward",),
        ("ingress:Mercury:7.0:8.0",),
        ("station:Jupiter:9.0:10.0",),
    ]


def test_batch_events_rejects_missing_kind_inputs() -> None:
    results = batch_module.batch_events(
        (batch_module.EventBatchRequest("aspect_transit", "Venus", 1.0, 2.0, target="Sun"),),
        reader=object(),
    )

    assert results[0].ok is False
    assert results[0].failure is not None
    assert "require angle" in results[0].failure.message


def test_batch_events_isolates_per_request_failures(monkeypatch) -> None:
    def fake_find_transits(*args, **kwargs):
        raise RuntimeError("transit blew up")

    def fake_find_ingresses(body, jd_start, jd_end, *, step_days, reader, policy):
        return [f"ingress:{body}"]

    monkeypatch.setattr(batch_module, "find_transits", fake_find_transits)
    monkeypatch.setattr(batch_module, "find_ingresses", fake_find_ingresses)

    requests = (
        batch_module.EventBatchRequest("transit", "Mars", 1.0, 2.0, target_lon=90.0),
        batch_module.EventBatchRequest("ingress", "Venus", 3.0, 4.0),
    )
    results = batch_module.batch_events(requests, reader=object())

    assert results[0].ok is False
    assert results[0].failure is not None
    assert results[1].ok is True
    assert results[1].events == ("ingress:Venus",)


def test_batch_returns_dispatches_scalar_return_requests(monkeypatch) -> None:
    def fake_planet_return(body, natal_lon, jd_start, *, direction, reader, policy):
        return 100.0

    def fake_solar_return(natal_sun_lon, year, *, reader, policy):
        return 200.0

    def fake_lunar_return(natal_moon_lon, jd_start, *, reader, policy):
        return 300.0

    monkeypatch.setattr(batch_module, "planet_return", fake_planet_return)
    monkeypatch.setattr(batch_module, "solar_return", fake_solar_return)
    monkeypatch.setattr(batch_module, "lunar_return", fake_lunar_return)

    requests = (
        batch_module.ReturnBatchRequest("planet_return", 12.5, body="Mars", jd_start=1.0, direction="either"),
        batch_module.ReturnBatchRequest("solar_return", 23.5, year=2025),
        batch_module.ReturnBatchRequest("lunar_return", 34.5, jd_start=2.0),
    )
    results = batch_module.batch_returns(requests, reader=object())

    assert [result.request for result in results] == list(requests)
    assert [result.jd_ut for result in results] == [100.0, 200.0, 300.0]


def test_batch_returns_rejects_missing_kind_inputs() -> None:
    results = batch_module.batch_returns(
        (batch_module.ReturnBatchRequest("planet_return", 12.5, jd_start=1.0),),
        reader=object(),
    )

    assert results[0].ok is False
    assert results[0].jd_ut is None
    assert results[0].failure is not None
    assert "require body" in results[0].failure.message


def test_batch_returns_isolates_per_request_failures(monkeypatch) -> None:
    def fake_planet_return(body, natal_lon, jd_start, *, direction, reader, policy):
        raise RuntimeError("return failed")

    def fake_solar_return(natal_sun_lon, year, *, reader, policy):
        return 200.0

    monkeypatch.setattr(batch_module, "planet_return", fake_planet_return)
    monkeypatch.setattr(batch_module, "solar_return", fake_solar_return)

    requests = (
        batch_module.ReturnBatchRequest("planet_return", 12.5, body="Mars", jd_start=1.0),
        batch_module.ReturnBatchRequest("solar_return", 23.5, year=2025),
    )
    results = batch_module.batch_returns(requests, reader=object())

    assert results[0].ok is False
    assert results[0].failure is not None
    assert results[1].ok is True
    assert results[1].jd_ut == 200.0


def test_batch_progressions_uses_request_objects(monkeypatch) -> None:
    calls: list[tuple[str, float, datetime]] = []

    def fake_progression(request, natal_jd_ut, reader):
        calls.append((request.technique, natal_jd_ut, request.target_date))
        return f"{request.technique}:{request.target_date.isoformat()}"

    monkeypatch.setitem(batch_module._PROGRESSION_FUNCTIONS, "secondary", fake_progression)

    requests = (
        batch_module.ProgressionBatchRequest(
            technique="secondary",
            natal_jd_ut=2451545.0,
            target_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
        batch_module.ProgressionBatchRequest(
            technique="secondary",
            natal_jd_ut=2451546.0,
            target_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )
    results = batch_module.batch_progressions(requests, reader=object())

    assert [result.request for result in results] == list(requests)
    assert [result.result for result in results] == [
        "secondary:2025-01-01T00:00:00+00:00",
        "secondary:2026-01-01T00:00:00+00:00",
    ]
    assert calls == [
        ("secondary", 2451545.0, requests[0].target_date),
        ("secondary", 2451546.0, requests[1].target_date),
    ]


def test_batch_progressions_resolves_natal_datetime(monkeypatch) -> None:
    def fake_progression(request, natal_jd_ut, reader):
        return natal_jd_ut

    monkeypatch.setitem(batch_module._PROGRESSION_FUNCTIONS, "secondary", fake_progression)

    result = batch_module.batch_progressions(
        (
            batch_module.ProgressionBatchRequest(
                technique="secondary",
                natal_dt=datetime(2000, 1, 1, tzinfo=timezone.utc),
                target_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ),
        ),
        reader=object(),
    )

    assert result[0].result == batch_module.jd_from_datetime(datetime(2000, 1, 1, tzinfo=timezone.utc))


def test_batch_progressions_rejects_unknown_technique() -> None:
    results = batch_module.batch_progressions(
        (
            batch_module.ProgressionBatchRequest(
                technique="not_real",
                natal_jd_ut=2451545.0,
                target_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ),
        ),
        reader=object(),
    )

    assert results[0].ok is False
    assert results[0].failure is not None
    assert "batch_progressions: technique" in results[0].failure.message


def test_batch_progressions_requires_arc_body_for_planetary_arc() -> None:
    results = batch_module.batch_progressions(
        (
            batch_module.ProgressionBatchRequest(
                technique="planetary_arc",
                natal_jd_ut=2451545.0,
                target_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ),
        ),
        reader=object(),
    )

    assert results[0].ok is False
    assert results[0].failure is not None
    assert "requires arc_body" in results[0].failure.message


def test_batch_progressions_isolate_per_request_failures(monkeypatch) -> None:
    def fake_good(request, natal_jd_ut, reader):
        return "ok"

    def fake_bad(request, natal_jd_ut, reader):
        raise RuntimeError("progression failed")

    monkeypatch.setitem(batch_module._PROGRESSION_FUNCTIONS, "secondary", fake_good)
    monkeypatch.setitem(batch_module._PROGRESSION_FUNCTIONS, "solar_arc", fake_bad)

    requests = (
        batch_module.ProgressionBatchRequest(
            technique="solar_arc",
            natal_jd_ut=2451545.0,
            target_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
        batch_module.ProgressionBatchRequest(
            technique="secondary",
            natal_jd_ut=2451546.0,
            target_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )
    results = batch_module.batch_progressions(requests, reader=object())

    assert results[0].ok is False
    assert results[0].failure is not None
    assert results[1].ok is True
    assert results[1].result == "ok"


def test_moira_batch_methods_delegate_to_facade(monkeypatch) -> None:
    engine = Moira()
    chart_calls: list[object] = []
    event_calls: list[object] = []
    transit_calls: list[object] = []
    return_calls: list[object] = []
    progression_calls: list[object] = []

    def fake_batch_charts(*args, **kwargs):
        chart_calls.append((args, kwargs))
        return ("chart-batch",)

    def fake_batch_transits(*args, **kwargs):
        transit_calls.append((args, kwargs))
        return ("transit-batch",)

    def fake_batch_returns(*args, **kwargs):
        return_calls.append((args, kwargs))
        return ("return-batch",)

    def fake_batch_events(*args, **kwargs):
        event_calls.append((args, kwargs))
        return ("event-batch",)

    def fake_batch_progressions(*args, **kwargs):
        progression_calls.append((args, kwargs))
        return ("progression-batch",)

    monkeypatch.setattr(facade_module, "batch_charts", fake_batch_charts)
    monkeypatch.setattr(facade_module, "batch_events", fake_batch_events)
    monkeypatch.setattr(facade_module, "batch_transits", fake_batch_transits)
    monkeypatch.setattr(facade_module, "batch_returns", fake_batch_returns)
    monkeypatch.setattr(facade_module, "batch_progressions", fake_batch_progressions)
    chart_result = engine.batch_charts(
        (batch_module.ChartBatchRequest(datetime(2025, 1, 1, tzinfo=timezone.utc)),)
    )
    event_result = engine.batch_events((batch_module.EventBatchRequest("ingress", "Mars", 1.0, 2.0),))
    transit_result = engine.batch_transits((batch_module.TransitBatchRequest("Mars", 0.0, 1.0, 2.0),))
    return_result = engine.batch_returns((batch_module.ReturnBatchRequest("solar_return", 15.0, year=2025),))
    progression_result = engine.batch_progressions(
        (
            batch_module.ProgressionBatchRequest(
                technique="secondary",
                natal_dt=datetime(2000, 1, 1, tzinfo=timezone.utc),
                target_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ),
        ),
    )

    assert chart_result == ("chart-batch",)
    assert event_result == ("event-batch",)
    assert transit_result == ("transit-batch",)
    assert return_result == ("return-batch",)
    assert progression_result == ("progression-batch",)
    assert chart_calls and chart_calls[0][1]["reader"] is engine._reader
    assert event_calls and event_calls[0][1]["reader"] is engine._reader
    assert transit_calls and transit_calls[0][1]["reader"] is engine._reader
    assert return_calls and return_calls[0][1]["reader"] is engine._reader
    assert progression_calls and progression_calls[0][0][0][0].technique == "secondary"
    assert progression_calls[0][1]["reader"] is engine._reader


def test_void_periods_all_planets_builds_distinct_body_windows(monkeypatch) -> None:
    calls: list[tuple[str, float]] = []

    def fake_build(body, jd_ref, reader, modern):
        calls.append((body, jd_ref))
        return batch_module.BodyVoidWindow(
            moving_body=body,
            sign="Aries",
            next_sign="Taurus",
            jd_voc_start=jd_ref,
            jd_voc_end=jd_ref + 0.5,
            last_aspect=None,
            duration_hours=12.0,
        )

    def fake_next_ingress(body, jd_ref, reader):
        return jd_ref + 10.0

    monkeypatch.setattr(batch_module, "_build_body_void_window", fake_build)
    monkeypatch.setattr(batch_module, "_body_next_sign_ingress", fake_next_ingress)

    results = batch_module.void_periods_all_planets(
        100.0,
        115.0,
        bodies=("Mars", "Ceres"),
        reader=object(),
    )

    assert [bundle.body for bundle in results] == ["Mars", "Ceres"]
    assert results[0].windows[0].moving_body == "Mars"
    assert results[1].windows[0].moving_body == "Ceres"
    assert ("Mars", 100.0) in calls
    assert ("Ceres", 100.0) in calls


def test_void_periods_all_planets_isolates_per_body_failures(monkeypatch) -> None:
    def fake_build(body, jd_ref, reader, modern):
        if body == "Mars":
            raise RuntimeError("void failed")
        return batch_module.BodyVoidWindow(
            moving_body=body,
            sign="Aries",
            next_sign="Taurus",
            jd_voc_start=jd_ref,
            jd_voc_end=jd_ref + 0.5,
            last_aspect=None,
            duration_hours=12.0,
        )

    def fake_next_ingress(body, jd_ref, reader):
        return jd_ref + 10.0

    monkeypatch.setattr(batch_module, "_build_body_void_window", fake_build)
    monkeypatch.setattr(batch_module, "_body_next_sign_ingress", fake_next_ingress)

    results = batch_module.void_periods_all_planets(
        100.0,
        115.0,
        bodies=("Mars", "Ceres"),
        reader=object(),
    )

    assert results[0].ok is False
    assert results[0].failure is not None
    assert results[1].ok is True
    assert results[1].windows[0].moving_body == "Ceres"
