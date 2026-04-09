from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import moira.chart as chart_module
import moira.facade as facade
from moira.julian import jd_from_datetime


def test_moira_chart_uses_tt_obliquity_and_jd_delta_t(monkeypatch) -> None:
    fake_reader = SimpleNamespace(path=Path("kernels/de441.bsp"))
    chart_result = {
        "Sun": SimpleNamespace(longitude=15.0, latitude=1.0, speed=0.9),
        "Moon": SimpleNamespace(longitude=44.0, latitude=3.0, speed=12.5),
    }
    node_result = SimpleNamespace(longitude=123.0)

    monkeypatch.setattr(facade, "SpkReader", lambda path: fake_reader)
    monkeypatch.setattr(facade, "all_planets_at", lambda *args, **kwargs: chart_result)
    monkeypatch.setattr(facade, "true_node", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(facade, "mean_node", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(facade, "mean_lilith", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(facade, "ut_to_tt", lambda jd: 2451545.0008)
    monkeypatch.setattr(facade, "true_obliquity", lambda jd: 23.4567 if jd == 2451545.0008 else -1.0)
    monkeypatch.setattr(facade, "delta_t_from_jd", lambda jd: 64.321 if jd == 2451545.0 else -1.0)

    engine = facade.Moira()
    chart = engine.chart(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc))

    assert dict(chart.planets) == chart_result
    assert chart.nodes[facade.Body.TRUE_NODE] is node_result
    assert chart.obliquity == 23.4567
    assert chart.delta_t == 64.321


def test_jd_from_datetime_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware datetime"):
        jd_from_datetime(datetime(2000, 1, 1, 12, 0))


def test_chart_and_chartcontext_reject_mutation() -> None:
    chart = facade.Chart(
        jd_ut=2451545.0,
        planets={"Sun": SimpleNamespace(longitude=15.0, speed=1.0)},
        nodes={},
        obliquity=23.4,
        delta_t=64.0,
    )
    with pytest.raises(TypeError):
        chart.planets["Moon"] = SimpleNamespace(longitude=30.0, speed=12.0)

    ctx = chart_module.ChartContext(
        jd_ut=2451545.0,
        jd_tt=2451545.0007,
        latitude=0.0,
        longitude=0.0,
        planets={},
        nodes={},
        houses=None,
    )
    with pytest.raises(TypeError):
        ctx.nodes["Node"] = SimpleNamespace(longitude=120.0)


def test_create_chart_accepts_explicit_reader_without_touching_singleton(monkeypatch) -> None:
    explicit_reader = object()
    chart_result = {"Sun": SimpleNamespace(longitude=15.0, latitude=1.0, speed=0.9)}
    node_result = SimpleNamespace(longitude=123.0)
    house_result = SimpleNamespace(cusps=[0.0] * 12)

    monkeypatch.setattr(chart_module, "all_planets_at", lambda *args, **kwargs: chart_result)
    monkeypatch.setattr(chart_module, "true_node", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(chart_module, "mean_node", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(chart_module, "mean_lilith", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(chart_module, "true_lilith", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(chart_module, "calculate_houses", lambda *args, **kwargs: house_result)
    monkeypatch.setattr(chart_module, "ut_to_tt", lambda jd: jd + 0.0008)

    ctx = chart_module.create_chart(2451545.0, 10.0, 20.0, reader=explicit_reader)

    assert dict(ctx.planets) == chart_result
    assert ctx.nodes[chart_module.Body.TRUE_NODE] is node_result
    assert ctx.houses is house_result


def test_create_chart_propagates_explicit_house_policy(monkeypatch) -> None:
    explicit_reader = object()
    strict_policy = chart_module.HousePolicy.strict()
    seen: dict[str, object] = {}

    monkeypatch.setattr(chart_module, "all_planets_at", lambda *args, **kwargs: {})
    monkeypatch.setattr(chart_module, "true_node", lambda *args, **kwargs: SimpleNamespace(longitude=1.0))
    monkeypatch.setattr(chart_module, "mean_node", lambda *args, **kwargs: SimpleNamespace(longitude=1.0))
    monkeypatch.setattr(chart_module, "mean_lilith", lambda *args, **kwargs: SimpleNamespace(longitude=1.0))
    monkeypatch.setattr(chart_module, "true_lilith", lambda *args, **kwargs: SimpleNamespace(longitude=1.0))
    monkeypatch.setattr(chart_module, "ut_to_tt", lambda jd: jd + 0.0008)

    def fake_calculate_houses(*args, **kwargs):
        seen["policy"] = kwargs.get("policy")
        return SimpleNamespace(cusps=[0.0] * 12)

    monkeypatch.setattr(chart_module, "calculate_houses", fake_calculate_houses)

    chart_module.create_chart(2451545.0, 10.0, 20.0, reader=explicit_reader, policy=strict_policy)

    assert seen["policy"] is strict_policy
