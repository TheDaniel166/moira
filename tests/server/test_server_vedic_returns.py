"""Source examples and dated HTTP parity for the Vedic return methods."""
from datetime import datetime
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient

from moira.julian import jd_from_datetime, utc_to_ut1
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.vedic_returns import MonthlyTajikaResponse, TithiPraveshaResponse

pytestmark = [pytest.mark.loopback, pytest.mark.requires_ephemeris]

BIRTH = dict(natal_dt="1971-09-12T08:25:00+05:30", return_year=1992, timezone="UTC+05:30",
             latitude=16.3, longitude=80.45)


@pytest.fixture(scope="module")
def return_client(moira_engine):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
            yield client


@pytest.mark.parametrize("selection,expected,sign", [
    ("rao_2014_tropical", "1992-08-22T00:14:02+05:30", 4),
    ("rao_2014_sidereal_comparison", "1992-09-20T09:47:45+05:30", 4),
])
def test_rao_1992_full_year_and_http(return_client, moira_engine, selection, expected, sign):
    request = dict(BIRTH, profile=selection)
    answer = return_client.post("/v1/tithi-pravesha/chart", json=request)
    assert answer.status_code == 200, answer.text
    value = moira_engine.tithi_pravesha(**dict(request, natal_dt=datetime.fromisoformat(request["natal_dt"])))
    assert answer.json() == TithiPraveshaResponse.model_validate(value, from_attributes=True).model_dump(mode="json")
    assert value.status == "available"
    assert len(value.candidates) == 1
    hit = value.candidates[0]
    assert hit.conjunction_sign_index == sign
    assert abs((hit.time.local - datetime.fromisoformat(expected)).total_seconds()) < 1
    assert abs(hit.crossing.residual_degrees * 3600) < 0.03
    assert value.chart.jd_ut1 == hit.crossing.jd_ut1


def test_rao_duplicate_lunations_keep_both_after_full_year_search(moira_engine):
    value = moira_engine.tithi_pravesha(
        datetime.fromisoformat("1975-07-13T16:02:00+05:30"), 2020, 16.7, 81.1,
        timezone="UTC+05:30", profile="rao_2014_tropical",
    )
    assert value.status == "ambiguous"
    assert value.reason == "multiple_matching_lunations"
    assert value.chart is None
    assert [hit.time.local.date().isoformat() for hit in value.candidates] == ["2020-06-26", "2020-07-25"]


def test_rao_no_capricorn_match_and_site_geometry(moira_engine):
    absent = moira_engine.tithi_pravesha(
        datetime.fromisoformat("2019-01-07T00:00:00+00:00"), 2020, 1, 2,
        timezone="UTC", profile="rao_2014_tropical",
    )
    assert absent.natal_conjunction_sign_index == 9
    assert absent.status == "unavailable"
    assert absent.reason == "no_matching_lunation_in_year"
    assert absent.candidates == ()
    assert absent.chart is None

    instant = datetime.fromisoformat(BIRTH["natal_dt"])
    result = moira_engine.tithi_pravesha(instant, 1992, 16.3, 80.45, timezone="UTC+05:30",
                                        profile="rao_2014_tropical")
    relocated = moira_engine.tithi_pravesha(instant, 1992, 51.5, -0.12, timezone="UTC+05:30",
                                           profile="rao_2014_tropical")
    assert result.candidates == relocated.candidates
    assert result.chart.sidereal_ascendant != relocated.chart.sidereal_ascendant


def test_tajika_shujah_modern_projection_and_http(return_client, moira_engine):
    # Gansten explains 19:00 local apparent time. Modern test uses the declared
    # 13:59 UTC display approximation for the corresponding natal instant.
    birth = utc_to_ut1(jd_from_datetime(datetime.fromisoformat("1616-07-02T13:59:00+00:00")))
    place = dict(latitude=25 + 55 / 60, longitude=74.64)
    args = dict(birth_jd_ut1=birth, return_year=1648, **place)
    annual = moira_engine.monthly_tajika(**args, month=1)
    assert annual.time.jd_ut1 == moira_engine.varshaphal(birth, 1648)
    assert annual.crossing is None
    answer = return_client.post("/v1/varshaphal/monthly/chart", json=dict(args, month=2))
    assert answer.status_code == 200, answer.text
    second = moira_engine.monthly_tajika(**args, month=2)
    assert answer.json() == MonthlyTajikaResponse.model_validate(second, from_attributes=True).model_dump(mode="json")
    assert (second.target_sidereal_sun_degrees - annual.target_sidereal_sun_degrees) % 360 == pytest.approx(30)
    assert second.chart.jd_ut1 == second.crossing.jd_ut1
    assert abs(second.crossing.residual_degrees * 3600) < 0.01
    last = moira_engine.monthly_tajika(**args, month=12)
    assert (last.target_sidereal_sun_degrees - annual.target_sidereal_sun_degrees) % 360 == pytest.approx(330)
    assert annual.time.jd_ut1 < second.time.jd_ut1 < last.time.jd_ut1 < last.next_annual_return_jd_ut1
    assert abs((second.time.utc - datetime.fromisoformat("1648-08-03T04:32:15.18+00:00")).total_seconds()) < 0.1


def test_shujah_printed_mixed_radix_worked_arithmetic():
    # Hayanaratna §8.3, pp. 920–921. Preserve both the historical target
    # and the exact ratio in the historical day/ghati/pala units.
    julian_day = Fraction(6815, 3437)
    clock = int((julian_day + Fraction(3 * 3600 + 24 * 60 + 51, 3600)) * 3600)
    assert divmod(clock % 3600, 60) == (23, 49)
    assert (86 + 30 + clock // 3600) % 7 == 2
