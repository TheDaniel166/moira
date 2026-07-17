"""P9-01 Panchanga service and serializer tests.

These tests verify the pre-route transport boundary:
- direct service parity with ``panchanga_at``
- chart-backed service parity with ``engine.chart`` + ``panchanga_at``
- serializer preservation of the rich Nakshatra vessel
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira.julian import jd_from_datetime, utc_to_ut1
from moira.panchanga import panchanga_at, panchanga_profile
from moira_server.models.panchanga import PanchangaChartRequest, PanchangaDirectRequest
from moira_server.serializers.panchanga import (
    serialize_panchanga_profile,
    serialize_panchanga_result,
)
from moira_server.services.panchanga import (
    compute_panchanga_chart,
    compute_panchanga_chart_profile,
    compute_panchanga_direct,
    compute_panchanga_direct_profile,
)


_DT = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
_JD = jd_from_datetime(_DT)
_SUN_LON = 280.0
_MOON_LON = 40.0


def test_panchanga_direct_service_matches_engine() -> None:
    request = PanchangaDirectRequest(
        sun_tropical_lon=_SUN_LON,
        moon_tropical_lon=_MOON_LON,
        jd=_JD,
    )

    direct = panchanga_at(_SUN_LON, _MOON_LON, _JD)
    serviced = compute_panchanga_direct(request)

    assert serviced == direct


def test_panchanga_profile_service_matches_engine() -> None:
    request = PanchangaDirectRequest(
        sun_tropical_lon=_SUN_LON,
        moon_tropical_lon=_MOON_LON,
        jd=_JD,
    )

    direct = panchanga_profile(panchanga_at(_SUN_LON, _MOON_LON, _JD))
    serviced = compute_panchanga_direct_profile(request)

    assert serviced == direct


def test_panchanga_serializer_preserves_nakshatra_vessel() -> None:
    result = panchanga_at(_SUN_LON, _MOON_LON, _JD)

    serialized = serialize_panchanga_result(result)

    assert serialized.nakshatra.nakshatra == result.nakshatra.nakshatra
    assert serialized.nakshatra.nakshatra_index == result.nakshatra.nakshatra_index
    assert serialized.nakshatra.nakshatra_lord == result.nakshatra.nakshatra_lord
    assert serialized.nakshatra.pada == result.nakshatra.pada
    assert serialized.nakshatra.degrees_in == pytest.approx(result.nakshatra.degrees_in)
    assert serialized.nakshatra.sidereal_lon == pytest.approx(result.nakshatra.sidereal_lon)
    assert serialized.tithi.name == result.tithi.name
    assert serialized.vara_lord == result.vara_lord


def test_panchanga_profile_serializer_preserves_profile_fields() -> None:
    profile = panchanga_profile(panchanga_at(_SUN_LON, _MOON_LON, _JD))

    serialized = serialize_panchanga_profile(profile)

    assert serialized.jd == profile.jd
    assert serialized.paksha == profile.paksha
    assert serialized.yoga_class == profile.yoga_class
    assert serialized.karana_type == profile.karana_type
    assert serialized.vara_lord == profile.vara_lord
    assert serialized.vara_lord_type == profile.vara_lord_type
    assert serialized.ayanamsa_system == profile.ayanamsa_system


@pytest.mark.requires_ephemeris
def test_panchanga_chart_service_matches_chart_backed_engine(moira_engine) -> None:
    request = PanchangaChartRequest(dt=_DT)
    chart = moira_engine.chart(_DT, bodies=["Sun", "Moon"], include_nodes=False)
    longitudes = chart.longitudes(include_nodes=False)
    direct = panchanga_at(longitudes["Sun"], longitudes["Moon"], utc_to_ut1(_JD))

    serviced = compute_panchanga_chart(moira_engine, request)

    assert serviced == direct


@pytest.mark.requires_ephemeris
def test_panchanga_chart_profile_service_matches_chart_backed_engine(moira_engine) -> None:
    request = PanchangaChartRequest(dt=_DT)
    chart = moira_engine.chart(_DT, bodies=["Sun", "Moon"], include_nodes=False)
    longitudes = chart.longitudes(include_nodes=False)
    direct = panchanga_profile(
        panchanga_at(longitudes["Sun"], longitudes["Moon"], utc_to_ut1(_JD))
    )

    serviced = compute_panchanga_chart_profile(moira_engine, request)

    assert serviced == direct
