"""Exact arc-to-time projection over REST, with bounded inputs and no fallback."""
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from moira.constants import TROPICAL_YEAR
from moira.julian import jd_from_datetime, utc_to_ut1
from moira._solar import _solar_longitude, _solar_declination_ra
import moira.primary_directions.keys as key_module
from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = [pytest.mark.loopback, pytest.mark.requires_ephemeris]
KEYS = ["solar_ra_dynamic", "solar_lon_dynamic", "naibod", "ptolemy", "cardan", "solar"]
ARC = 4.28487070579817
BASE = {"dt": "1990-06-15T18:32:00Z", "items": [{"id": "benchmark", "arc_deg": ARC, "keys": KEYS}]}


@pytest.fixture
def client(moira_engine, monkeypatch):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False)), raise_server_exceptions=False) as value:
        yield value


def test_six_keys_satisfy_their_laws_and_calendar_invariants(client, moira_engine):
    """Forward solar motion witnesses dynamic roots; static laws are independent."""
    response = client.post("/v1/primary-directions/time-keys", json={
        **BASE, "items": [*BASE["items"], {"id": "origin", "arc_deg": 0, "keys": KEYS}],
    })
    assert response.status_code == 200, response.text
    data = response.json()
    natal = data["natal_jd_ut"]
    assert natal == utc_to_ut1(jd_from_datetime(datetime.fromisoformat(BASE["dt"])))
    rows = {row["key"]: row for row in data["items"][0]["projections"]}
    assert list(rows) == KEYS
    rate = data["natal_solar_rate_deg_per_day"]
    expected = {"naibod": ARC / (360 / 365.25), "ptolemy": ARC,
                "cardan": ARC / (59 / 60 + 12 / 3600), "solar": ARC / rate}
    reader = moira_engine._reader_obj
    for key, row in rows.items():
        age = row["age_years"]
        assert row["perfection_jd_ut"] == pytest.approx(natal + age * TROPICAL_YEAR, abs=1e-9)
        assert jd_from_datetime(datetime.fromisoformat(row["perfection_iso"])) == pytest.approx(row["perfection_jd_ut"], abs=1e-8)
        if key in expected:
            assert age == pytest.approx(expected[key], abs=1e-12)
        else:
            coordinate = _solar_longitude if key == "solar_lon_dynamic" else lambda jd, reader: _solar_declination_ra(jd, reader)[1]
            progress = (coordinate(natal + age, reader) - coordinate(natal, reader)) % 360
            # Bisection's 1e-6 ephemeris-day stopping interval gives <0.003 arcsec.
            assert abs(progress - ARC) * 3600 < 0.003
    for row in data["items"][1]["projections"]:
        assert row["age_years"] == 0
        assert row["perfection_jd_ut"] == natal


@pytest.mark.parametrize("item", [
    {"id": "x", "arc_deg": -1, "keys": ["naibod"]},
    {"id": "x", "arc_deg": True, "keys": ["naibod"]},
    {"id": "x", "arc_deg": "4.2", "keys": ["naibod"]},
    {"id": "x", "arc_deg": 181, "keys": ["naibod"]},
    {"id": "x", "arc_deg": 4.2, "keys": ["unknown"]},
    {"id": "x", "arc_deg": 4.2, "keys": ["naibod", "naibod"]},
    {"id": "", "arc_deg": 4.2, "keys": []},
])
def test_invalid_items_fail_closed(client, item):
    assert client.post("/v1/primary-directions/time-keys", json={**BASE, "items": [item]}).status_code == 422


def test_batch_and_clock_admission(client):
    for payload in [
        {**BASE, "dt": "1990-06-15T18:32:00"},
        {**BASE, "items": BASE["items"] * 2},
        {**BASE, "items": []},
        {**BASE, "items": [{"id": str(i), "arc_deg": 1, "keys": KEYS} for i in range(1025)]},
        {**BASE, "items": [{"id": str(i), "arc_deg": 1, "keys": KEYS} for i in range(342)]},
    ]:
        assert client.post("/v1/primary-directions/time-keys", json=payload).status_code == 422


def test_projection_reuses_duplicate_arc_roots_and_never_changes_key(client, monkeypatch):
    original = key_module.invert_solar_arc_ra
    calls = []
    def watched(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)
    monkeypatch.setattr(key_module, "invert_solar_arc_ra", watched)
    result = client.post("/v1/primary-directions/time-keys", json={**BASE, "items": [
        {"id": "a", "arc_deg": ARC, "keys": ["solar_ra_dynamic"]},
        {"id": "b", "arc_deg": ARC, "keys": ["solar_ra_dynamic"]},
    ]})
    assert result.status_code == 200
    assert len(calls) == 1
    a, b = result.json()["items"]
    assert a["projections"] == b["projections"]
    def unavailable(*args, **kwargs):
        raise RuntimeError("ephemeris inversion unavailable")
    monkeypatch.setattr(key_module, "invert_solar_arc_ra", unavailable)
    failure = client.post("/v1/primary-directions/time-keys", json=BASE)
    assert failure.status_code == 500
    assert "items" not in failure.text
