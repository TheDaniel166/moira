"""P9-03 Jaimini service and serializer tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira import Body
from moira.jaimini import (
    KarakaRole,
    jaimini_chart_profile,
    jaimini_karakas,
    karaka_condition_profile,
    karaka_pair,
)
from moira.julian import utc_to_ut1
from moira.sidereal import tropical_to_sidereal
from moira_server.models.jaimini import (
    JaiminiChartRequest,
    JaiminiConditionChartRequest,
    JaiminiConditionDirectRequest,
    JaiminiDirectRequest,
    JaiminiPairChartRequest,
    JaiminiPairDirectRequest,
)
from moira_server.serializers.jaimini import serialize_jaimini_result
from moira_server.services.jaimini import (
    compute_jaimini_chart,
    compute_jaimini_chart_condition,
    compute_jaimini_chart_pair,
    compute_jaimini_chart_profile,
    compute_jaimini_direct,
    compute_jaimini_direct_condition,
    compute_jaimini_direct_pair,
    compute_jaimini_direct_profile,
)


_DT = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
_LONS_7 = {
    "Sun": 25.0,
    "Moon": 52.0,
    "Mars": 80.0,
    "Mercury": 107.0,
    "Jupiter": 134.0,
    "Venus": 160.0,
    "Saturn": 215.0,
}
_LONS_TIE = {**_LONS_7, "Sun": 22.0}


def _lons_8() -> dict[str, float]:
    return {**_LONS_7, "Rahu": 270.0}


def _chart_sidereal_lons(moira_engine, scheme: int = 7) -> dict[str, float]:
    chart = moira_engine.chart(
        _DT,
        bodies=list(_PLANETS),
        include_nodes=(scheme == 8),
    )
    jd_ut = utc_to_ut1(chart.jd_ut)
    lons = chart.longitudes(include_nodes=False)
    sidereal = {
        planet: tropical_to_sidereal(lons[planet], jd_ut, system="Lahiri")
        for planet in _PLANETS
    }
    if scheme == 8:
        sidereal["Rahu"] = tropical_to_sidereal(
            chart.nodes[Body.TRUE_NODE].longitude,
            jd_ut,
            system="Lahiri",
        )
    return sidereal


def test_jaimini_direct_service_matches_engine() -> None:
    request = JaiminiDirectRequest(sidereal_longitudes=_LONS_7)

    assert compute_jaimini_direct(request) == jaimini_karakas(_LONS_7)


def test_jaimini_direct_profile_service_matches_engine() -> None:
    request = JaiminiDirectRequest(sidereal_longitudes=_LONS_7)
    direct = jaimini_chart_profile(jaimini_karakas(_LONS_7))

    assert compute_jaimini_direct_profile(request) == direct


def test_jaimini_direct_condition_service_matches_engine() -> None:
    request = JaiminiConditionDirectRequest(
        sidereal_longitudes=_LONS_7,
        karaka_name=KarakaRole.ATMAKARAKA,
    )
    result = jaimini_karakas(_LONS_7)

    assert compute_jaimini_direct_condition(request) == karaka_condition_profile(
        result.assignments[0],
        result.scheme,
    )


def test_jaimini_direct_pair_service_matches_engine() -> None:
    request = JaiminiPairDirectRequest(
        sidereal_longitudes=_LONS_7,
        role_a=KarakaRole.ATMAKARAKA,
        role_b=KarakaRole.DARAKARAKA,
    )
    result = jaimini_karakas(_LONS_7)

    assert compute_jaimini_direct_pair(request) == karaka_pair(
        result,
        KarakaRole.ATMAKARAKA,
        KarakaRole.DARAKARAKA,
    )


@pytest.mark.requires_ephemeris
def test_jaimini_chart_service_matches_engine(moira_engine) -> None:
    request = JaiminiChartRequest(dt=_DT)
    direct = jaimini_karakas(_chart_sidereal_lons(moira_engine))

    assert compute_jaimini_chart(moira_engine, request) == direct


@pytest.mark.requires_ephemeris
def test_jaimini_chart_profile_service_matches_engine(moira_engine) -> None:
    request = JaiminiChartRequest(dt=_DT)
    direct = jaimini_chart_profile(jaimini_karakas(_chart_sidereal_lons(moira_engine)))

    assert compute_jaimini_chart_profile(moira_engine, request) == direct


@pytest.mark.requires_ephemeris
def test_jaimini_chart_condition_service_matches_engine(moira_engine) -> None:
    request = JaiminiConditionChartRequest(dt=_DT, karaka_name=KarakaRole.ATMAKARAKA)
    direct = jaimini_karakas(_chart_sidereal_lons(moira_engine))

    assert compute_jaimini_chart_condition(moira_engine, request) == karaka_condition_profile(
        direct.assignments[0],
        direct.scheme,
    )


@pytest.mark.requires_ephemeris
def test_jaimini_chart_pair_service_matches_engine(moira_engine) -> None:
    request = JaiminiPairChartRequest(
        dt=_DT,
        role_a=KarakaRole.ATMAKARAKA,
        role_b=KarakaRole.DARAKARAKA,
    )
    direct = jaimini_karakas(_chart_sidereal_lons(moira_engine))

    assert compute_jaimini_chart_pair(moira_engine, request) == karaka_pair(
        direct,
        KarakaRole.ATMAKARAKA,
        KarakaRole.DARAKARAKA,
    )


@pytest.mark.requires_ephemeris
def test_jaimini_chart_scheme_8_sources_rahu_from_true_node(moira_engine) -> None:
    request = JaiminiChartRequest(dt=_DT, scheme=8)
    direct_lons = _chart_sidereal_lons(moira_engine, scheme=8)

    result = compute_jaimini_chart(moira_engine, request)
    rahu = result.by_planet("Rahu")

    assert rahu is not None
    assert rahu.sidereal_longitude == pytest.approx(direct_lons["Rahu"])
    assert rahu.is_rahu_inverted is True


def test_jaimini_serializer_preserves_tie_and_degree_truth() -> None:
    result = jaimini_karakas(_LONS_TIE)

    serialized = serialize_jaimini_result(result)

    assert serialized.has_ties is True
    assert serialized.tie_warnings == result.tie_warnings
    assert serialized.assignments[0].degree_in_sign == pytest.approx(
        result.assignments[0].degree_in_sign
    )
    assert serialized.assignments[0].sidereal_longitude == pytest.approx(
        result.assignments[0].sidereal_longitude
    )


def test_jaimini_direct_scheme_8_preserves_rahu_inversion() -> None:
    request = JaiminiDirectRequest(sidereal_longitudes=_lons_8(), scheme=8)

    result = compute_jaimini_direct(request)
    rahu = result.by_planet("Rahu")

    assert rahu is not None
    assert rahu.is_rahu_inverted is True
    assert rahu.degree_in_sign == pytest.approx(30.0)
