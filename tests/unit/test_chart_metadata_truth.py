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
    monkeypatch.setattr(facade, "true_lilith", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(facade, "utc_to_tt", lambda jd: 2451545.0008)
    monkeypatch.setattr(facade, "true_obliquity", lambda jd: 23.4567 if jd == 2451545.0008 else -1.0)
    monkeypatch.setattr(facade, "delta_t_from_jd", lambda jd: 64.321 if jd == 2451545.0 else -1.0)

    engine = facade.Moira()
    chart = engine.chart(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc))

    assert dict(chart.planets) == chart_result
    assert chart.nodes[facade.Body.TRUE_NODE] is node_result
    assert chart.obliquity == 23.4567
    assert chart.delta_t == 64.321


def test_moira_chart_passes_ut1_to_all_planets_at(monkeypatch) -> None:
    fake_reader = SimpleNamespace(path=Path("kernels/de441.bsp"))
    node_result = SimpleNamespace(longitude=123.0)
    seen: dict[str, object] = {}

    monkeypatch.setattr(facade, "SpkReader", lambda path: fake_reader)
    monkeypatch.setattr(facade, "utc_to_tt", lambda jd: jd + 0.0008)
    monkeypatch.setattr(facade, "utc_to_ut1", lambda jd: jd + 0.1234)
    monkeypatch.setattr(facade, "nutation", lambda jd_tt: (0.2, 0.0))
    monkeypatch.setattr(facade, "local_sidereal_time", lambda *args: 211.0)
    monkeypatch.setattr(facade, "true_obliquity", lambda jd: 23.4)
    monkeypatch.setattr(facade, "delta_t_from_jd", lambda jd: 69.0)
    monkeypatch.setattr(facade, "true_node", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(facade, "mean_node", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(facade, "mean_lilith", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(facade, "true_lilith", lambda *args, **kwargs: node_result)

    def fake_all_planets_at(jd_arg, **kwargs):
        seen["jd_arg"] = jd_arg
        seen["kwargs"] = kwargs
        return {"Sun": SimpleNamespace(longitude=15.0, latitude=1.0, speed=0.9)}

    monkeypatch.setattr(facade, "all_planets_at", fake_all_planets_at)

    engine = facade.Moira()
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    engine.chart(dt, observer_lat=51.5, observer_lon=-0.1)

    assert seen["jd_arg"] == jd_from_datetime(dt) + 0.1234


def test_moira_chart_uses_apparent_lst_for_topocentric_chart(monkeypatch) -> None:
    fake_reader = SimpleNamespace(path=Path("kernels/de441.bsp"))
    node_result = SimpleNamespace(longitude=123.0)
    seen: dict[str, object] = {}

    monkeypatch.setattr(facade, "SpkReader", lambda path: fake_reader)
    monkeypatch.setattr(facade, "utc_to_tt", lambda jd: jd + 0.0008)
    monkeypatch.setattr(facade, "utc_to_ut1", lambda jd: jd + 0.1234)
    monkeypatch.setattr(facade, "nutation", lambda jd_tt: (0.2, 0.0))
    monkeypatch.setattr(facade, "true_obliquity", lambda jd: 23.4567)
    monkeypatch.setattr(facade, "delta_t_from_jd", lambda jd: 69.0)
    monkeypatch.setattr(facade, "true_node", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(facade, "mean_node", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(facade, "mean_lilith", lambda *args, **kwargs: node_result)
    monkeypatch.setattr(facade, "true_lilith", lambda *args, **kwargs: node_result)

    def fake_local_sidereal_time(*args):
        seen["lst_args"] = args
        return 211.0

    def fake_all_planets_at(jd_arg, **kwargs):
        seen["lst_deg"] = kwargs["lst_deg"]
        return {"Sun": SimpleNamespace(longitude=15.0, latitude=1.0, speed=0.9)}

    monkeypatch.setattr(facade, "local_sidereal_time", fake_local_sidereal_time)
    monkeypatch.setattr(facade, "all_planets_at", fake_all_planets_at)

    engine = facade.Moira()
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    engine.chart(dt, observer_lat=51.5, observer_lon=-0.1)

    assert seen["lst_args"] == (
        jd_from_datetime(dt) + 0.1234,
        -0.1,
        0.2,
        23.4567,
    )
    assert seen["lst_deg"] == 211.0


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


def test_relocated_chart_reuses_snapshot_and_propagates_house_policy(monkeypatch) -> None:
    strict_policy = chart_module.HousePolicy.strict()
    source_houses = SimpleNamespace(system=chart_module.HouseSystem.KOCH, cusps=[0.0] * 12)
    source_chart = chart_module.ChartContext(
        jd_ut=2451545.0,
        jd_tt=2451545.0008,
        latitude=51.5,
        longitude=-0.1,
        planets={chart_module.Body.SUN: SimpleNamespace(longitude=15.0, latitude=0.0, speed=1.0)},
        nodes={chart_module.Body.TRUE_NODE: SimpleNamespace(longitude=123.0)},
        houses=source_houses,
    )
    seen: dict[str, object] = {}
    relocated_houses = SimpleNamespace(system=chart_module.HouseSystem.KOCH, cusps=[30.0] * 12)

    def fake_calculate_houses(*args, **kwargs):
        seen["jd_ut"] = args[0]
        seen["latitude"] = args[1]
        seen["longitude"] = args[2]
        seen["system"] = kwargs.get("system")
        seen["policy"] = kwargs.get("policy")
        return relocated_houses

    monkeypatch.setattr(chart_module, "calculate_houses", fake_calculate_houses)

    relocated = chart_module.relocated_chart(
        source_chart,
        40.7128,
        -74.0060,
        policy=strict_policy,
    )

    assert seen == {
        "jd_ut": 2451545.0,
        "latitude": 40.7128,
        "longitude": -74.0060,
        "system": chart_module.HouseSystem.KOCH,
        "policy": strict_policy,
    }
    assert dict(relocated.planets) == dict(source_chart.planets)
    assert dict(relocated.nodes) == dict(source_chart.nodes)
    assert relocated.houses is relocated_houses
    assert relocated.latitude == 40.7128
    assert relocated.longitude == -74.0060


def test_moira_relocated_chart_uses_chart_assembly_pipeline(monkeypatch) -> None:
    seen: dict[str, object] = {}
    fake_context = object()

    monkeypatch.setattr(facade, "utc_to_ut1", lambda jd: jd + 0.123)

    def fake_create_chart(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return fake_context

    monkeypatch.setattr("moira.chart.create_chart", fake_create_chart)

    engine = facade.Moira()
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    result = engine.relocated_chart(
        dt,
        34.05,
        -118.25,
        system=facade.HouseSystem.WHOLE_SIGN,
        bodies=[facade.Body.SUN, facade.Body.MOON],
    )

    assert result is fake_context
    assert seen["args"] == (jd_from_datetime(dt) + 0.123, 34.05, -118.25)
    assert seen["kwargs"]["house_system"] == facade.HouseSystem.WHOLE_SIGN
    assert seen["kwargs"]["bodies"] == [facade.Body.SUN, facade.Body.MOON]
    assert seen["kwargs"]["reader"] is engine._reader


def test_moira_solar_return_chart_delegates_to_predictive_wrapper(monkeypatch) -> None:
    seen: dict[str, object] = {}
    fake_chart = object()

    def fake_solar_return_chart(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return fake_chart

    monkeypatch.setattr(facade, "solar_return_chart", fake_solar_return_chart)

    engine = facade.Moira()
    result = engine.solar_return_chart(
        123.45,
        2026,
        40.7128,
        -74.0060,
        system=facade.HouseSystem.WHOLE_SIGN,
        bodies=[facade.Body.SUN],
    )

    assert result is fake_chart
    assert seen["args"] == (123.45, 2026, 40.7128, -74.0060)
    assert seen["kwargs"]["house_system"] == facade.HouseSystem.WHOLE_SIGN
    assert seen["kwargs"]["bodies"] == [facade.Body.SUN]
    assert seen["kwargs"]["reader"] is engine._reader


def test_moira_varshaphal_chart_delegates_to_predictive_wrapper(monkeypatch) -> None:
    seen: dict[str, object] = {}
    fake_chart = object()

    def fake_varshaphal_chart(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return fake_chart

    monkeypatch.setattr(facade, "varshaphal_chart", fake_varshaphal_chart)

    engine = facade.Moira()
    result = engine.varshaphal_chart(
        2451545.0,
        2026,
        40.7128,
        -74.0060,
        ayanamsa_system=facade.Ayanamsa.KRISHNAMURTI,
        system=facade.HouseSystem.WHOLE_SIGN,
        bodies=[facade.Body.SUN],
    )

    assert result is fake_chart
    assert seen["args"] == (2451545.0, 2026, 40.7128, -74.0060)
    assert seen["kwargs"]["ayanamsa_system"] == facade.Ayanamsa.KRISHNAMURTI
    assert seen["kwargs"]["house_system"] == facade.HouseSystem.WHOLE_SIGN
    assert seen["kwargs"]["bodies"] == [facade.Body.SUN]
    assert seen["kwargs"]["reader"] is engine._reader


def test_moira_build_varshaphal_chart_delegates_to_predictive_wrapper(monkeypatch) -> None:
    seen: dict[str, object] = {}
    fake_bundle = object()

    def fake_build_varshaphal_chart(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return fake_bundle

    monkeypatch.setattr(facade, "build_varshaphal_chart", fake_build_varshaphal_chart)

    engine = facade.Moira()
    result = engine.build_varshaphal_chart(
        2451545.0,
        12.0,
        77.0,
        2026,
        28.6,
        77.2,
        ayanamsa_system=facade.Ayanamsa.KRISHNAMURTI,
        system=facade.HouseSystem.WHOLE_SIGN,
        bodies=[facade.Body.SUN],
    )

    assert result is fake_bundle
    assert seen["args"] == (2451545.0, 12.0, 77.0, 2026, 28.6, 77.2)
    assert seen["kwargs"]["ayanamsa_system"] == facade.Ayanamsa.KRISHNAMURTI
    assert seen["kwargs"]["house_system"] == facade.HouseSystem.WHOLE_SIGN
    assert seen["kwargs"]["bodies"] == [facade.Body.SUN]
    assert seen["kwargs"]["reader"] is engine._reader


def test_moira_decennials_delegates_to_timelord_wrapper(monkeypatch) -> None:
    seen: dict[str, object] = {}
    fake_periods = object()
    policy = object()

    def fake_decennials(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return fake_periods

    monkeypatch.setattr(facade, "decennials", fake_decennials)
    monkeypatch.setattr(facade, "is_day_chart", lambda sun_lon, asc: True)

    engine = facade.Moira()
    natal_dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    natal_chart = SimpleNamespace(
        planets={"Sun": SimpleNamespace(longitude=15.0)},
        longitudes=lambda include_nodes=False: {
            "Sun": 15.0,
            "Moon": 44.0,
            "Mercury": 20.0,
            "Venus": 50.0,
            "Mars": 110.0,
            "Jupiter": 250.0,
            "Saturn": 300.0,
        },
    )
    natal_houses = SimpleNamespace(asc=100.0)

    result = engine.decennials(natal_dt, natal_chart, natal_houses, policy=policy)

    assert result is fake_periods
    assert seen["args"][0] == jd_from_datetime(natal_dt)
    assert seen["args"][1]["Sun"] == 15.0
    assert seen["args"][1]["Moon"] == 44.0
    assert seen["args"][2] is True
    assert seen["kwargs"]["policy"] is policy


def test_moira_current_decennials_delegates_to_timelord_wrapper(monkeypatch) -> None:
    seen: dict[str, object] = {}
    fake_pair = object()
    policy = object()

    def fake_current_decennials(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return fake_pair

    monkeypatch.setattr(facade, "current_decennials", fake_current_decennials)
    monkeypatch.setattr(facade, "is_day_chart", lambda sun_lon, asc: False)

    engine = facade.Moira()
    natal_dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    current_dt = datetime(2005, 1, 1, 12, 0, tzinfo=timezone.utc)
    natal_chart = SimpleNamespace(
        planets={"Sun": SimpleNamespace(longitude=15.0)},
        longitudes=lambda include_nodes=False: {
            "Sun": 15.0,
            "Moon": 44.0,
            "Mercury": 20.0,
            "Venus": 50.0,
            "Mars": 110.0,
            "Jupiter": 250.0,
            "Saturn": 300.0,
        },
    )

    result = engine.current_decennials(natal_dt, current_dt, natal_chart, policy=policy)

    assert result is fake_pair
    assert seen["args"][0] == jd_from_datetime(natal_dt)
    assert seen["args"][1]["Saturn"] == 300.0
    assert seen["args"][2] is False
    assert seen["args"][3] == jd_from_datetime(current_dt)
    assert seen["kwargs"]["policy"] is policy


def test_moira_planetary_node_delegates_to_singular_wrapper(monkeypatch) -> None:
    seen: dict[str, object] = {}
    fake_node = object()

    def fake_planetary_node(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return fake_node

    monkeypatch.setattr(facade, "planetary_node", fake_planetary_node)

    engine = facade.Moira()
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    result = engine.planetary_node("Mars", dt)

    assert result is fake_node
    assert seen["args"] == ("Mars", jd_from_datetime(dt))
    assert seen["kwargs"] == {}


@pytest.mark.requires_ephemeris
def test_relocated_chart_preserves_positions_and_recasts_houses(moira_engine) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    jd_ut1 = facade.utc_to_ut1(jd_from_datetime(dt))

    source = chart_module.create_chart(jd_ut1, 51.5, -0.1, reader=moira_engine._reader)
    relocated = chart_module.relocated_chart(source, 40.7128, -74.0060)

    assert relocated.jd_ut == source.jd_ut
    assert relocated.jd_tt == source.jd_tt
    assert relocated.latitude == 40.7128
    assert relocated.longitude == -74.0060
    assert relocated.planets[chart_module.Body.SUN].longitude == source.planets[chart_module.Body.SUN].longitude
    assert relocated.planets[chart_module.Body.MOON].longitude == source.planets[chart_module.Body.MOON].longitude
    assert relocated.houses.asc != source.houses.asc
    assert relocated.houses.mc != source.houses.mc
