"""KP interpretation API, existing Vimshottari timing and reader composition."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from moira import kp_period_interpretation
from moira.dasha import current_dasha
from moira.julian import utc_datetime_from_ut1
from moira.planets import planet_at
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.vedic_matching import KPPeriodInterpretationMomentResponse, KPPeriodInterpretationResponse

pytestmark = pytest.mark.loopback
_NATAL = "2024-04-08T00:00:00Z"


@pytest.fixture(scope="module")
def kp_client(moira_engine):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
            yield client


def test_period_interpretation_direct_http(kp_client, moira_engine):
    request = {
        "planet_longitudes": {
            "Sun": 31, "Moon": 59, "Mercury": 90, "Venus": 105, "Mars": 269,
            "Jupiter": 219, "Saturn": 320, "Rahu": 339, "Ketu": 159,
        },
        "cusp_longitudes": list(range(0, 360, 30)),
        "subject": "education",
        "period_lords": ["Venus", "Moon"],
    }
    route = "/v1/kp/period-interpretation"
    response = kp_client.post(route, json=request)
    assert response.status_code == 200, response.text
    direct = kp_period_interpretation(**request)
    assert moira_engine.kp_period_interpretation(**request) == direct
    assert response.json()["method"] == "bhatt_direct_house_evidence"
    assert response.json() == KPPeriodInterpretationResponse.model_validate(direct, from_attributes=True).model_dump(mode="json")
    for field, value in [
        ("subject", "health"), ("period_lords", ["Venus", "Lagna"]), ("cusp_longitudes", [0] * 12),
    ]:
        assert kp_client.post(route, json={**request, field: value}).status_code == 422


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(("year_basis", "levels", "mode"), [
    ("savana_360", 4, "mean"), ("julian_365.25", 3, "true"),
])
def test_active_period_interpretation_and_clock(kp_client, moira_engine, year_basis, levels, mode):
    request = {
        "natal_dt": _NATAL, "current_dt": _NATAL, "latitude": 40, "longitude": -74,
        "node_mode": mode, "subject": "education", "year_basis": year_basis, "levels": levels,
    }
    path = "/v1/kp/chart/period-interpretation"
    response = kp_client.post(path, json=request)
    assert response.status_code == 200, response.text
    args = {**request, **{name: datetime.fromisoformat(request[name]) for name in ("natal_dt", "current_dt")}}
    result = moira_engine.kp_period_interpretation_for_datetime(**args)
    assert "0441" in result.chart.ephemeris_identity
    assert result.chart.reader_binding == "caller_owned_reader"
    expected = KPPeriodInterpretationMomentResponse.model_validate(result, from_attributes=True)
    assert response.json() == expected.model_dump(mode="json")

    chart = result.chart
    moon = planet_at("Moon", chart.jd_ut1, reader=moira_engine._reader, jd_tt=chart.jd_tt).longitude
    canonical = current_dasha(
        moon, chart.jd_ut1, result.current_jd_ut1, ayanamsa_system=chart.profile.ayanamsa_system,
        year_basis=year_basis, levels=levels,
    )
    assert result.year_basis == year_basis
    assert len(result.active_periods) == len(canonical) == levels
    for window, period in zip(result.active_periods, canonical, strict=True):
        assert (window.level, window.planet) == (period.level, period.planet)
        assert (window.start_jd_ut1, window.end_jd_ut1) == (period.start_jd, period.end_jd)
        assert (window.full_start_jd_ut1, window.full_end_jd_ut1) == (period.full_start_jd, period.full_end_jd)
    assert result.active_periods[0].start_jd_ut1 == chart.jd_ut1
    assert result.active_periods[0].full_start_jd_ut1 < chart.jd_ut1
    plain = kp_period_interpretation(
        planet_longitudes={name: point.sidereal_longitude for name, point in chart.planets.items()},
        cusp_longitudes=tuple(point.sidereal_longitude for point in chart.cusps),
        period_lords=[period.planet for period in canonical], subject=request["subject"],
    )
    assert result.interpretation == plain


@pytest.mark.requires_ephemeris
def test_active_period_switch_at_canonical_boundary(moira_engine):
    birth = datetime.fromisoformat(_NATAL)
    options = dict(natal_dt=birth, latitude=40, longitude=-74, node_mode="mean", subject="service", levels=2)
    initial = moira_engine.kp_period_interpretation_for_datetime(current_dt=birth, **options)
    end = initial.active_periods[-1].end_jd_ut1
    boundary = utc_datetime_from_ut1(end)
    before = moira_engine.kp_period_interpretation_for_datetime(current_dt=boundary - timedelta(milliseconds=2), **options)
    at = moira_engine.kp_period_interpretation_for_datetime(current_dt=boundary, **options)
    boundary_roundtrip = at.current_jd_ut1
    assert boundary_roundtrip == end
    assert before.active_periods[-1].end_jd_ut1 == end
    assert at.active_periods[-1].start_jd_ut1 == end
    assert at.active_periods[-1].planet != before.active_periods[-1].planet


@pytest.mark.requires_ephemeris
def test_unavailable_placidus_retains_canonical_periods(kp_client):
    request = {
        "natal_dt": _NATAL, "current_dt": _NATAL, "latitude": 70, "longitude": -74,
        "node_mode": "mean", "subject": "service",
    }
    path = "/v1/kp/chart/period-interpretation"
    response = kp_client.post(path, json=request)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["active_periods"]) == 3
    assert payload["interpretation"] is None
    assert payload["chart"]["cusp_unavailable_reason"] == "placidus_no_unique_ordered_solution"
    for field, value in [("current_dt", "2024-04-07T23:59:00Z"), ("levels", 5), ("levels", True)]:
        assert kp_client.post(path, json={**request, field: value}).status_code == 422
