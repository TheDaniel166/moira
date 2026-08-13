"""Request-shape regressions for the test-only Horizons client."""

from __future__ import annotations

import json

from tools import horizons


def test_observer_apparent_position_tt_uses_discrete_tt_julian_day(
    monkeypatch,
) -> None:
    captured: dict[str, str] = {}

    def fake_request(params: dict[str, str]) -> str:
        captured.update(params)
        return json.dumps(
            {
                "result": (
                    "$$SOE\n"
                    "2000-Jan-01 12:00 10.0 20.0 1.5 0.0\n"
                    "$$EOE"
                )
            }
        )

    horizons.observer_apparent_position_tt.cache_clear()
    monkeypatch.setattr(horizons, "_request_text", fake_request)

    result = horizons.observer_apparent_position_tt("5", 2451545.123456789)

    assert captured["COMMAND"] == "'5'"
    assert captured["TIME_TYPE"] == "'TT'"
    assert captured["TLIST_TYPE"] == "'JD'"
    assert captured["TLIST"] == "'2451545.123456789181'"
    assert "START_TIME" not in captured
    assert "STOP_TIME" not in captured
    assert "STEP_SIZE" not in captured
    assert result.right_ascension == 10.0
    assert result.declination == 20.0
    assert result.distance_au == 1.5


def test_vector_state_tdb_uses_discrete_tdb_julian_day(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_request(params: dict[str, str]) -> str:
        captured.update(params)
        return (
            "$$SOE\n"
            "2451545.123456789, A.D. 2000-Jan-01 14:57:46.6667, "
            "1.0, 2.0, 3.0, 4.0, 5.0, 6.0\n"
            "$$EOE"
        )

    horizons.vector_state_tdb.cache_clear()
    monkeypatch.setattr(horizons, "_request_text", fake_request)

    result = horizons.vector_state_tdb("5", 2451545.123456789)

    assert captured["COMMAND"] == "'5'"
    assert captured["TIME_TYPE"] == "'TDB'"
    assert captured["TLIST_TYPE"] == "'JD'"
    assert captured["TLIST"] == "'2451545.123456789181'"
    assert captured["VEC_CORR"] == "NONE"
    assert "START_TIME" not in captured
    assert "STOP_TIME" not in captured
    assert "STEP_SIZE" not in captured
    assert result == horizons.VectorState(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
