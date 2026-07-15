"""Policy, event-order, and public-surface tests for neutral lunar flow."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import moira
import moira.aspect_events as events
import moira.facade as facade
from moira.aspect_events import (
    MoonConnectionFlowPolicy,
    MoonFlowEventRole,
    MoonPreviousEventWindowPolicy,
    moon_connection_flow_at,
)
from moira.void_of_course import LastAspect


def test_flow_policy_requires_an_explicit_coherent_previous_window() -> None:
    with pytest.raises(ValueError, match="requires positive finite"):
        MoonConnectionFlowPolicy(MoonPreviousEventWindowPolicy.FIXED_LOOKBACK)
    with pytest.raises(ValueError, match="rejects previous_lookback_days"):
        MoonConnectionFlowPolicy(
            MoonPreviousEventWindowPolicy.CURRENT_SIGN,
            previous_lookback_days=2.0,
        )
    fixed = MoonConnectionFlowPolicy(
        MoonPreviousEventWindowPolicy.FIXED_LOOKBACK,
        previous_lookback_days=3.0,
    )
    assert fixed.previous_lookback_days == 3.0


def test_flow_selects_last_previous_and_first_next_with_visible_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query = 100.0
    monkeypatch.setattr(events, "_moon_last_sign_ingress", lambda jd, reader: 99.0)
    monkeypatch.setattr(events, "_moon_next_sign_ingress", lambda jd, reader: 101.0)
    monkeypatch.setattr(
        events,
        "_moon_longitude",
        lambda jd, reader: (220.0 + (jd - query) * 12.0) % 360.0,
    )

    calls: list[tuple[float, float]] = []

    def perfections(start, end, bodies, reader):
        calls.append((start, end))
        if end == query:
            return [
                LastAspect("Jupiter", "Trine", 120.0, 98.0),
                LastAspect("Saturn", "Opposition", 180.0, 99.75),
            ]
        return [
            LastAspect("Mars", "Square", 90.0, 100.25),
            LastAspect("Venus", "Sextile", 60.0, 100.75),
        ]

    monkeypatch.setattr(events, "_find_aspect_perfections", perfections)

    longitudes = {"Moon": 220.0, "Saturn": 39.0, "Mars": 130.0, "Venus": 160.0}
    speeds = {"Moon": 12.0, "Saturn": 0.05, "Mars": 0.5, "Venus": 1.0}
    monkeypatch.setattr(
        events,
        "planet_at",
        lambda body, jd, reader=None: SimpleNamespace(
            longitude=(longitudes.get(body, 100.0) + (jd - query) * speeds.get(body, 0.2)) % 360.0,
            speed=speeds.get(body, 0.2),
        ),
    )

    result = moon_connection_flow_at(
        query,
        policy=MoonConnectionFlowPolicy(
            MoonPreviousEventWindowPolicy.FIXED_LOOKBACK,
            previous_lookback_days=2.0,
        ),
        reader=object(),
    )

    assert calls == [(98.0, 100.0), (100.0, 101.0)]
    assert result.previous_search_start == 98.0
    assert result.jd_sign_ingress == 99.0
    assert result.jd_sign_egress == 101.0
    assert result.previous_separation is not None
    assert result.previous_separation.role is MoonFlowEventRole.PREVIOUS_SEPARATION
    assert result.previous_separation.body == "Saturn"
    assert result.previous_separation.hours_from_query == pytest.approx(-6.0)
    assert result.previous_motion is not None
    assert result.previous_motion.state.value == "separating"
    assert result.next_connection is not None
    assert result.next_connection.role is MoonFlowEventRole.NEXT_CONNECTION
    assert result.next_connection.body == "Mars"
    assert result.next_connection.hours_from_query == pytest.approx(6.0)
    assert result.previous_no_event_reason is None
    assert result.next_no_event_reason is None


def test_flow_preserves_no_event_reasons(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(events, "_moon_last_sign_ingress", lambda jd, reader: jd - 1.0)
    monkeypatch.setattr(events, "_moon_next_sign_ingress", lambda jd, reader: jd + 1.0)
    monkeypatch.setattr(events, "_moon_longitude", lambda jd, reader: 5.0)
    monkeypatch.setattr(events, "_find_aspect_perfections", lambda *args: [])

    result = moon_connection_flow_at(
        100.0,
        policy=MoonConnectionFlowPolicy(
            MoonPreviousEventWindowPolicy.CURRENT_SIGN
        ),
        reader=object(),
    )

    assert result.previous_separation is None
    assert result.previous_motion is None
    assert result.previous_no_event_reason == (
        "no_exact_perfection_in_selected_previous_window"
    )
    assert result.next_connection is None
    assert result.next_no_event_reason == (
        "no_exact_perfection_before_current_sign_egress"
    )


def test_flow_surface_is_public_through_module_root_and_facade() -> None:
    names = {
        "MoonPreviousEventWindowPolicy",
        "MoonFlowEventRole",
        "MoonAspectEvent",
        "MoonConnectionFlowPolicy",
        "MoonConnectionFlow",
        "moon_connection_flow_at",
    }
    assert names == set(events.__all__)
    assert names <= set(moira.__all__)
    assert names <= set(facade.__all__)
    assert hasattr(moira.Moira, "moon_connection_flow_at")
