"""HTTP witnesses for proleptic Gregorian conversion on astronomical years."""

import math

import pytest
from fastapi.testclient import TestClient

from moira.julian import julian_day
from moira_server.app import create_app
from moira_server.dependencies import get_engine


pytestmark = pytest.mark.loopback
_PATH = "/v1/time/convert"
_FORWARD = {"source_scale": "civil_utc", "target_scale": "UTC"}
_INVERSE = {"source_scale": "UTC", "target_scale": "civil_utc"}
_DATE = {"year": 0, "month": 2, "day": 29}


@pytest.fixture
def client():
    app = create_app()

    def unexpected_engine():
        pytest.fail("Structured Gregorian conversion needs no ephemeris reader.")

    app.dependency_overrides[get_engine] = unexpected_engine
    return TestClient(app)


def _post(client, payload):
    response = client.post(_PATH, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_calendar_matches_direct_engine_and_inverse(client):
    result = _post(client, {**_FORWARD, "calendar": {**_DATE, "hour": 12}})
    assert result["jd"] == julian_day(0, 2, 29, 12) == 1721119.0
    assert result["model"] == "UTC_coded_civil_JD"
    calendar = {**_DATE, "hour": 12, "minute": 0, "second": 0, "microsecond": 0}
    assert result["request"] == {**_FORWARD, "calendar": calendar}
    inverse = _post(client, {**_INVERSE, "jd": result["jd"]})
    assert inverse["calendar_utc"] == {**calendar, "tzname": "UTC"}


@pytest.mark.parametrize(("year", "month", "day"), [(-400, 2, 29), (-44, 3, 15), (1582, 10, 10)])
def test_fractional_bce_and_pre_reform_dates_match_erfa(client, year, month, day):
    erfa = pytest.importorskip("erfa")
    calendar = {
        "year": year, "month": month, "day": day,
        "hour": 17, "minute": 41, "second": 32, "microsecond": 123456,
    }
    microseconds = ((17 * 60 + 41) * 60 + 32) * 1_000_000 + 123456
    part1, part2 = erfa.cal2jd(year, month, day)
    expected = math.fsum((part1, part2, microseconds / 86_400_000_000))
    jd = _post(client, {**_FORWARD, "calendar": calendar})["jd"]
    assert jd == pytest.approx(expected, rel=0, abs=math.ulp(expected))

    inverse = _post(client, {**_INVERSE, "jd": jd})["calendar_utc"]
    assert (inverse["year"], inverse["month"], inverse["day"]) == (year, month, day)
    recovered = ((inverse["hour"] * 60 + inverse["minute"]) * 60 + inverse["second"]) * 1_000_000
    recovered += inverse["microsecond"]
    assert abs(recovered - microseconds) <= 0.5 * math.ulp(jd) * 86_400_000_000 + 0.5


@pytest.mark.parametrize("year", [-100_000, 100_000])
def test_year_limits_match_gregorian_400_year_cycles(client, year):
    calendar = {**_DATE, "year": year}
    base = _post(client, {**_FORWARD, "calendar": _DATE})["jd"]
    jd = _post(client, {**_FORWARD, "calendar": calendar})["jd"]
    assert jd == base + (year // 400) * 146097
    inverse = _post(client, {**_INVERSE, "jd": jd})["calendar_utc"]
    assert inverse == {**calendar, "hour": 0, "minute": 0, "second": 0, "microsecond": 0, "tzname": "UTC"}


def test_offset_datetime_and_inverse_keep_legacy_response_shapes(client):
    dt = "2000-01-01T08:34:56.123456-04:00"
    aware = _post(client, {**_FORWARD, "dt": dt})
    calendar = {
        "year": 2000, "month": 1, "day": 1,
        "hour": 12, "minute": 34, "second": 56, "microsecond": 123456,
    }
    structured = _post(client, {**_FORWARD, "calendar": calendar})
    assert aware["jd"] == structured["jd"]
    assert aware["model"] == structured["model"] == "UTC_coded_civil_JD"
    assert aware["request"] == {**_FORWARD, "dt": dt, "jd": None}
    assert aware["provenance"]["jd_utc"] == aware["jd"]
    inverse = _post(client, {**_INVERSE, "jd": 2451545})
    assert inverse["request"] == {**_INVERSE, "jd": 2451545, "dt": None}
    assert inverse["calendar_utc"] == {
        "year": 2000, "month": 1, "day": 1, "hour": 12,
        "minute": 0, "second": 0, "microsecond": 0, "tzname": "UTC",
    }


@pytest.mark.parametrize("overrides", [
    {"year": -100}, {"year": 1900}, {"month": 4, "day": 31},
    {"year": -100_001}, {"year": 100_001}, {"year": "0"}, {"year": False},
    {"month": 13}, {"day": 0}, {"hour": 24}, {"minute": 60}, {"second": 60},
    {"microsecond": 1_000_000}, {"tzname": "+04:00"},
])
def test_rejects_invalid_calendar_fields(client, overrides):
    response = client.post(_PATH, json={**_FORWARD, "calendar": {**_DATE, **overrides}})
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("fields", [
    {"calendar": {}, "dt": "2000-01-01T00:00:00Z"},
    {"calendar": _DATE, "dt": "2000-01-01T00:00:00Z"},
    {"calendar": _DATE, "jd": 2451545},
    {"calendar": _DATE, "target_scale": "TT"},
    {**_INVERSE, "calendar": _DATE},
    {"calendar": None},
])
def test_rejects_conflicting_or_mislabelled_epochs(client, fields):
    response = client.post(_PATH, json={**_FORWARD, **fields})
    assert response.status_code == 422, response.text


def test_openapi_advertises_calendar_and_legacy_inputs(client):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"][_PATH]["post"]
    variants = operation["requestBody"]["content"]["application/json"]["schema"]["anyOf"]
    assert {branch["$ref"].rsplit("/", 1)[-1] for branch in variants} == {
        "TimeConversionRequest", "CalendarTimeConversionRequest",
    }
    components = schema["components"]["schemas"]
    request = components["CalendarTimeConversionRequest"]
    assert set(request["required"]) == {"source_scale", "target_scale", "calendar"}
    assert request["properties"]["source_scale"]["const"] == "civil_utc"
    assert request["properties"]["target_scale"]["const"] == "UTC"
    calendar = components["GregorianCalendarInput"]
    assert set(calendar["required"]) == {"year", "month", "day"}
    assert calendar["additionalProperties"] is False
    assert calendar["properties"]["year"] == {
        "title": "Year", "type": "integer", "minimum": -100_000, "maximum": 100_000,
    }
    assert calendar["description"] == "Proleptic Gregorian UTC date and time with astronomical year numbering."
