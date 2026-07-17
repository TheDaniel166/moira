from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

import moira.facade as facade
from moira import varga as varga_module

shadbala_module = importlib.import_module("moira.shadbala")


def _planet(longitude: float, speed: float = 1.0, latitude: float = 0.0):
    return SimpleNamespace(longitude=longitude, speed=speed, latitude=latitude)


class _Chart:
    jd_ut = 2451545.0

    def __init__(self) -> None:
        self.planets = {
            "Sun": _planet(280.0, 1.0, 0.0),
            "Moon": _planet(35.0, 13.0, 1.0),
            "Mars": _planet(100.0, 0.5, 0.2),
            "Mercury": _planet(210.0, 1.2, -0.1),
            "Jupiter": _planet(45.0, 0.08, 0.05),
            "Venus": _planet(160.0, 1.1, -0.2),
            "Saturn": _planet(300.0, 0.03, 0.03),
        }
        self.nodes = {
            "Rahu": _planet(120.0, -0.05, 0.0),
            "Ketu": _planet(300.0, -0.05, 0.0),
        }

    def longitudes(self, include_nodes: bool = True) -> dict[str, float]:
        values = {name: item.longitude for name, item in self.planets.items()}
        if include_nodes:
            values.update({name: item.longitude for name, item in self.nodes.items()})
        return values


def _houses():
    return SimpleNamespace(
        asc=110.0,
        cusps=tuple((110.0 + index * 30.0) % 360.0 for index in range(12)),
    )


def _sidereal_chart_longitudes(chart: _Chart, bodies: tuple[str, ...]) -> dict[str, float]:
    longitudes = chart.longitudes(include_nodes=True)
    jd_ut1 = facade.utc_to_ut1(chart.jd_ut)
    return {
        body: facade.tropical_to_sidereal(
            longitudes[body],
            jd_ut1,
            system=facade.Ayanamsa.LAHIRI,
        )
        for body in bodies
    }


def test_vedic_facade_sidereal_utilities_delegate_to_engine() -> None:
    engine = facade.Moira()
    jd = 2451545.0
    tropical_longitude = 123.456

    assert engine.ayanamsa(jd) == facade.ayanamsa(jd, facade.Ayanamsa.LAHIRI, "true")
    assert engine.ayanamsa(jd, facade.Ayanamsa.FAGAN_BRADLEY, mode="mean") == facade.ayanamsa(
        jd,
        facade.Ayanamsa.FAGAN_BRADLEY,
        "mean",
    )

    sidereal = engine.tropical_to_sidereal(tropical_longitude, jd)
    assert sidereal == facade.tropical_to_sidereal(
        tropical_longitude,
        jd,
        system=facade.Ayanamsa.LAHIRI,
    )
    assert engine.sidereal_to_tropical(sidereal, jd) == pytest.approx(
        tropical_longitude,
        abs=1e-12,
    )


def test_vedic_facade_sidereal_utility_registry_and_failures_delegate() -> None:
    engine = facade.Moira()

    assert engine.list_ayanamsa_systems() == facade.list_ayanamsa_systems()
    with pytest.raises(ValueError, match="mode must be"):
        engine.ayanamsa(2451545.0, mode="invalid")


def test_vedic_facade_panchanga_delegates_to_engine() -> None:
    engine = facade.Moira()
    chart = _Chart()

    via_facade = engine.panchanga(chart)
    jd_ut1 = facade.utc_to_ut1(chart.jd_ut)
    direct = facade.panchanga_at(
        chart.planets["Sun"].longitude,
        chart.planets["Moon"].longitude,
        jd_ut1,
        ayanamsa_system=facade.Ayanamsa.LAHIRI,
    )

    assert via_facade == direct
    assert engine.panchanga_profile(via_facade) == facade.panchanga_profile(direct)


def test_vedic_facade_jaimini_chart_wrapper_delegates_to_engine() -> None:
    engine = facade.Moira()
    chart = _Chart()
    bodies = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu")

    via_facade = engine.jaimini_karakas_for_chart(chart, scheme=8)
    direct = facade.jaimini_karakas(_sidereal_chart_longitudes(chart, bodies), scheme=8)

    assert via_facade == direct
    assert engine.jaimini_profile(via_facade) == facade.jaimini_chart_profile(direct)
    assert engine.jaimini_pair(
        via_facade,
        facade.KarakaRole.ATMAKARAKA,
        facade.KarakaRole.DARAKARAKA,
    ) == facade.karaka_pair(
        direct,
        facade.KarakaRole.ATMAKARAKA,
        facade.KarakaRole.DARAKARAKA,
    )


def test_vedic_facade_ashtakavarga_chart_wrapper_delegates_to_engine() -> None:
    engine = facade.Moira()
    chart = _Chart()
    houses = _houses()
    bodies = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
    sidereal = _sidereal_chart_longitudes(chart, bodies)
    sidereal["Lagna"] = facade.tropical_to_sidereal(
        houses.asc,
        facade.utc_to_ut1(chart.jd_ut),
        system=facade.Ayanamsa.LAHIRI,
    )

    via_facade = engine.ashtakavarga_for_chart(chart, houses)
    direct = facade.ashtakavarga(sidereal, ayanamsa_system=facade.Ayanamsa.LAHIRI)

    assert via_facade == direct
    assert engine.ashtakavarga_profile(via_facade) == facade.ashtakavarga_chart_profile(direct)
    moon_bhinna = via_facade.for_planet("Moon")
    assert engine.ashtakavarga_sign_profile(moon_bhinna, 0) == facade.sign_strength_profile(
        moon_bhinna,
        0,
    )
    assert engine.ashtakavarga_transit_strength("Moon", 0, moon_bhinna) == facade.transit_strength(
        "Moon",
        0,
        moon_bhinna,
    )


def test_vedic_facade_varga_chart_wrapper_delegates_to_engine() -> None:
    engine = facade.Moira()
    chart = _Chart()
    sidereal_moon = facade.tropical_to_sidereal(
        chart.planets["Moon"].longitude,
        facade.utc_to_ut1(chart.jd_ut),
        system=facade.Ayanamsa.LAHIRI,
    )

    assert engine.varga(sidereal_moon, 9, "Navamsa") == facade.calculate_varga(
        sidereal_moon,
        9,
        "Navamsa",
    )
    assert engine.varga_named(sidereal_moon, "navamsa") == facade.navamsa(sidereal_moon)
    assert engine.varga_for_chart(chart, "Moon", "navamsa") == facade.navamsa(sidereal_moon)
    assert engine.shodashvarga_for_chart(chart, "Moon") == {
        selector: getattr(varga_module, selector)(sidereal_moon)
        for selector in engine._SHODASHVARGA_SELECTORS
    }


def test_vedic_facade_shadbala_chart_wrapper_delegates_to_engine() -> None:
    engine = facade.Moira()
    chart = _Chart()
    houses = _houses()
    bodies = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
    sidereal = _sidereal_chart_longitudes(chart, bodies)
    speeds = {planet: chart.planets[planet].speed for planet in bodies}
    latitudes = {planet: chart.planets[planet].latitude for planet in bodies}
    jd_ut1 = facade.utc_to_ut1(chart.jd_ut)
    panchanga = facade.panchanga_at(
        chart.planets["Sun"].longitude,
        chart.planets["Moon"].longitude,
        jd_ut1,
        ayanamsa_system=facade.Ayanamsa.LAHIRI,
    )
    is_day = facade.is_day_chart(chart.planets["Sun"].longitude, houses.asc)

    via_facade = engine.shadbala_for_chart(chart, houses)
    direct = facade.shadbala(
        sidereal,
        speeds,
        houses,
        jd_ut1,
        panchanga.tithi.number,
        panchanga.vara_lord,
        is_day,
        ayanamsa_system=facade.Ayanamsa.LAHIRI,
        planet_latitudes=latitudes,
    )

    assert via_facade == direct
    assert engine.shadbala_profile(via_facade) == facade.shadbala_chart_profile(direct)
    assert engine.shadbala_condition(via_facade.planets["Moon"]) == facade.shadbala_condition_profile(
        direct.planets["Moon"]
    )
    assert engine.shadbala_network(via_facade) == shadbala_module.shadbala_network_profile(
        direct,
        (),
    )


def test_vedic_facade_bhava_bala_chart_wrapper_delegates_to_engine() -> None:
    engine = facade.Moira()
    chart = _Chart()
    houses = _houses()
    bodies = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
    sidereal = _sidereal_chart_longitudes(chart, bodies)

    graha_result = engine.shadbala_for_chart(chart, houses)
    via_facade = engine.bhava_bala_for_chart(chart, houses)
    direct = facade.bhava_bala(graha_result, sidereal, houses)

    assert via_facade == direct
    assert engine.bhava_bala(graha_result, sidereal, houses) == direct
    assert set(via_facade.houses.keys()) == set(range(1, 13))
    assert via_facade.houses[via_facade.strongest_house].rank == 1


def test_vedic_facade_rejects_unknown_varga_selector() -> None:
    engine = facade.Moira()

    with pytest.raises(ValueError, match="unknown varga selector"):
        engine.varga_named(10.0, "not_a_varga")
