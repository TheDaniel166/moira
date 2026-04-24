from __future__ import annotations

import importlib
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import moira
import moira.nutation_2000a as nutation_module


def test_nutation_tables_load_lazily() -> None:
    module = importlib.reload(nutation_module)
    assert module._LS_TERMS is None
    assert module._PL_TERMS is None


def test_runtime_version_matches_project_metadata_fallback() -> None:
    assert moira.__version__ == "2.1.2"


def test_moira_behavior_smoke_chart_houses_aspects_lots_and_transits(monkeypatch) -> None:
    fake_reader = SimpleNamespace(path=Path("kernels/de441.bsp"))
    chart_result = {
        "Sun": SimpleNamespace(longitude=15.0, latitude=1.0, speed=0.9),
        "Moon": SimpleNamespace(longitude=44.0, latitude=3.0, speed=12.5),
    }
    node_result = SimpleNamespace(longitude=123.0)
    house_result = SimpleNamespace(asc=10.0, mc=100.0, cusps=[float(i * 30) for i in range(12)])
    aspect_result = [SimpleNamespace(body1="Sun", body2="Moon", aspect="SemiSextile")]
    lot_result = [SimpleNamespace(name="Fortune", longitude=25.0)]
    transit_result = [SimpleNamespace(body="Sun", jd_ut=2451545.5)]

    monkeypatch.setattr(moira.facade, "SpkReader", lambda path: fake_reader)
    monkeypatch.setattr(moira.facade, "all_planets_at", lambda *args, **kwargs: chart_result)
    monkeypatch.setattr(moira.facade, "true_node", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(moira.facade, "mean_node", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(moira.facade, "mean_lilith", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(moira.facade, "true_lilith", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(moira.facade, "ut_to_tt", lambda jd: 2451545.0008)
    monkeypatch.setattr(moira.facade, "true_obliquity", lambda jd: 23.4)
    monkeypatch.setattr(moira.facade, "delta_t_from_jd", lambda jd: 69.0)
    monkeypatch.setattr(moira.facade, "calculate_houses", lambda *args, **kwargs: house_result)
    monkeypatch.setattr(moira.facade, "find_aspects", lambda *args, **kwargs: aspect_result)
    monkeypatch.setattr(moira.facade, "calculate_lots", lambda *args, **kwargs: lot_result)
    monkeypatch.setattr(moira.facade, "find_transits", lambda *args, **kwargs: transit_result)

    engine = moira.Moira()
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    chart = engine.chart(dt)
    houses = engine.houses(dt, latitude=51.5, longitude=-0.1)
    aspects = engine.aspects(chart)
    lots = engine.lots(chart, houses)
    transits = engine.transits("Sun", 15.0, 2451545.0, 2451546.0)

    assert dict(chart.planets) == chart_result
    assert chart.nodes[moira.Body.TRUE_NODE] is node_result
    assert chart.obliquity == 23.4
    assert chart.delta_t == 69.0
    assert houses is house_result
    assert aspects is aspect_result
    assert lots is lot_result
    assert transits is transit_result
