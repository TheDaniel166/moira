from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.parans import _crossing_times, find_parans, natal_parans
from moira.rise_set import find_phenomena, get_transit


@pytest.mark.slow
def test_crossing_times_match_rise_set_engine() -> None:
    jd_day = 2451544.5
    lat = 51.5
    lon = -0.1

    for body in [Body.SUN, Body.MOON, "Regulus"]:
        crossings = {c.circle: c.jd for c in _crossing_times(body, jd_day, lat, lon)}
        altitude = -0.5667
        phenomena = find_phenomena(body, jd_day, lat, lon, altitude=altitude)

        if "Rise" in phenomena:
            assert crossings["Rising"] == pytest.approx(phenomena["Rise"], abs=1e-6)
        if "Set" in phenomena:
            assert crossings["Setting"] == pytest.approx(phenomena["Set"], abs=1e-6)

        assert crossings["Culminating"] == pytest.approx(
            get_transit(body, jd_day, lat, lon, upper=True),
            abs=1e-6,
        )
        assert crossings["AntiCulminating"] == pytest.approx(
            get_transit(body, jd_day, lat, lon, upper=False),
            abs=1e-6,
        )
        assert jd_day <= crossings["AntiCulminating"] < jd_day + 1.0


@pytest.mark.slow
def test_find_parans_returns_sorted_unique_body_pairs() -> None:
    parans = find_parans([Body.SUN, Body.MOON, "Regulus"], 2451544.5, 51.5, -0.1, orb_minutes=30.0)

    assert parans == sorted(parans, key=lambda p: p.orb_min)
    seen = {(p.body1, p.body2, p.circle1, p.circle2, round(p.jd, 9)) for p in parans}
    assert len(seen) == len(parans)
    for paran in parans:
        assert paran.body1 != paran.body2
        assert paran.orb_min >= 0.0


def test_natal_parans_uses_ut_day_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, float] = {}

    def fake_find_parans(bodies, jd_day, lat, lon, orb_minutes=4.0):
        captured["jd_day"] = jd_day
        return []

    monkeypatch.setattr("moira.parans.find_parans", fake_find_parans)
    natal_parans([Body.SUN, Body.MOON], 2451545.2, 40.0, -74.0)

    assert captured["jd_day"] == math.floor(2451545.2 - 0.5) + 0.5
