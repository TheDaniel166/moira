"""P9-02 Shadbala service and serializer tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira.dignities import is_day_chart
from moira.julian import utc_to_ut1
from moira.panchanga import panchanga_at
from moira.shadbala import (
    graha_yuddha_pairs,
    shadbala,
    shadbala_chart_profile,
    shadbala_condition_profile,
    shadbala_network_profile,
)
from moira.sidereal import tropical_to_sidereal
from moira_server.models.shadbala import ShadbalaChartRequest, ShadbalaConditionChartRequest
from moira_server.serializers.shadbala import (
    serialize_shadbala_network_profile,
    serialize_shadbala_result,
)
from moira_server.services.shadbala import (
    compute_shadbala_chart,
    compute_shadbala_chart_condition,
    compute_shadbala_chart_network,
    compute_shadbala_chart_profile,
)


_DT = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
_LAT = 40.7128
_LON = -74.0060
_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")


def _direct_shadbala(moira_engine, request: ShadbalaChartRequest):
    chart = moira_engine.chart(
        request.dt,
        bodies=list(_PLANETS),
        include_nodes=False,
        observer_lat=request.observer_lat,
        observer_lon=request.observer_lon,
        observer_elev_m=request.observer_elev_m,
    )
    jd_ut = utc_to_ut1(chart.jd_ut)
    houses = moira_engine.houses(
        request.dt,
        latitude=request.observer_lat,
        longitude=request.observer_lon,
        system=request.house_system,
    )
    tropical_longitudes = chart.longitudes(include_nodes=False)
    ayanamsa_system = (
        request.policy.ayanamsa_system
        if request.policy is not None
        else request.ayanamsa_system
    )
    sidereal_longitudes = {
        planet: tropical_to_sidereal(
            tropical_longitudes[planet],
            jd_ut,
            system=ayanamsa_system,
        )
        for planet in _PLANETS
    }
    planet_speeds = {planet: chart.planets[planet].speed for planet in _PLANETS}
    planet_latitudes = {planet: chart.planets[planet].latitude for planet in _PLANETS}
    panchanga_support = panchanga_at(
        tropical_longitudes["Sun"],
        tropical_longitudes["Moon"],
        jd_ut,
        ayanamsa_system=ayanamsa_system,
    )
    return shadbala(
        sidereal_longitudes=sidereal_longitudes,
        planet_speeds=planet_speeds,
        houses=houses,
        jd=jd_ut,
        tithi_number=panchanga_support.tithi.number,
        vara_lord=panchanga_support.vara_lord,
        is_day=is_day_chart(tropical_longitudes["Sun"], houses.asc),
        ayanamsa_system=ayanamsa_system,
        hora_lord=request.hora_lord,
        planet_latitudes=planet_latitudes,
    ), graha_yuddha_pairs(sidereal_longitudes, planet_latitudes)


@pytest.mark.requires_ephemeris
def test_shadbala_chart_service_matches_engine(moira_engine) -> None:
    request = ShadbalaChartRequest(dt=_DT, observer_lat=_LAT, observer_lon=_LON)
    direct, _ = _direct_shadbala(moira_engine, request)

    serviced = compute_shadbala_chart(moira_engine, request)

    assert serviced == direct


@pytest.mark.requires_ephemeris
def test_shadbala_profile_service_matches_engine(moira_engine) -> None:
    request = ShadbalaChartRequest(dt=_DT, observer_lat=_LAT, observer_lon=_LON)
    direct, _ = _direct_shadbala(moira_engine, request)

    serviced = compute_shadbala_chart_profile(moira_engine, request)

    assert serviced == shadbala_chart_profile(direct)


@pytest.mark.requires_ephemeris
def test_shadbala_network_service_matches_engine(moira_engine) -> None:
    request = ShadbalaChartRequest(dt=_DT, observer_lat=_LAT, observer_lon=_LON)
    direct, wars = _direct_shadbala(moira_engine, request)

    serviced = compute_shadbala_chart_network(moira_engine, request)

    assert serviced == shadbala_network_profile(direct, wars)


@pytest.mark.requires_ephemeris
def test_shadbala_condition_service_matches_engine(moira_engine) -> None:
    request = ShadbalaConditionChartRequest(
        dt=_DT,
        observer_lat=_LAT,
        observer_lon=_LON,
        planet="Mars",
    )
    direct, _ = _direct_shadbala(moira_engine, request)

    serviced = compute_shadbala_chart_condition(moira_engine, request)

    assert serviced == shadbala_condition_profile(direct.planets["Mars"])


@pytest.mark.requires_ephemeris
def test_shadbala_serializer_preserves_component_strengths(moira_engine) -> None:
    request = ShadbalaChartRequest(dt=_DT, observer_lat=_LAT, observer_lon=_LON)
    direct, _ = _direct_shadbala(moira_engine, request)

    serialized = serialize_shadbala_result(direct)

    sun = direct.planets["Sun"]
    body = serialized.planets["Sun"]
    assert body.sthana_bala.uchcha == pytest.approx(sun.sthana_bala.uchcha)
    assert body.sthana_bala.saptavargaja == pytest.approx(sun.sthana_bala.saptavargaja)
    assert body.kala_bala.paksha == pytest.approx(sun.kala_bala.paksha)
    assert body.kala_bala.abda_masa_vara_hora == pytest.approx(
        sun.kala_bala.abda_masa_vara_hora
    )
    assert body.dig_bala == pytest.approx(sun.dig_bala)
    assert body.total_rupas == pytest.approx(sun.total_rupas)
    assert body.strength_ratio == pytest.approx(sun.strength_ratio)


def test_shadbala_network_serializer_preserves_war_vessel_shape(
    planetary_reader,
) -> None:
    result = shadbala(
        sidereal_longitudes={
            "Sun": 0.0,
            "Moon": 30.0,
            "Mars": 60.0,
            "Mercury": 60.5,
            "Jupiter": 120.0,
            "Venus": 150.0,
            "Saturn": 180.0,
        },
        planet_speeds={planet: 1.0 for planet in _PLANETS},
        houses=type(
            "_Houses",
            (),
            {"asc": 0.0, "cusps": tuple(float(i * 30) for i in range(12))},
        )(),
        jd=2451545.0,
        tithi_number=1,
        vara_lord="Sun",
        is_day=True,
        planet_latitudes={"Mars": 1.0, "Mercury": 0.0},
    )
    wars = graha_yuddha_pairs(
        {"Mars": 60.0, "Mercury": 60.5},
        {"Mars": 1.0, "Mercury": 0.0},
    )
    profile = shadbala_network_profile(result, wars)

    serialized = serialize_shadbala_network_profile(profile)

    assert len(serialized.active_wars) == len(wars)
    assert serialized.active_wars[0].victor == wars[0].victor
    assert serialized.active_wars[0].loser == wars[0].loser
    assert serialized.active_wars[0].separation_deg == pytest.approx(
        wars[0].separation_deg
    )
