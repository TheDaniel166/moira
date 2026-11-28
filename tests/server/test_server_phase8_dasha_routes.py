"""Phase-8 Vimshottari Dasha route tests (P8-10).

Parity witnesses: confirm route responses match direct engine calls.
Adversarial witnesses: confirm invalid inputs are rejected cleanly.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math

import pytest
from fastapi.testclient import TestClient

from moira.dasha import (
    DashaPeriod,
    current_dasha,
    dasha_active_line,
    dasha_balance,
    dasha_lord_pair,
    dasha_sequence_profile,
    vimshottari,
)
from moira.julian import TAI_TT_OFFSET, datetime_from_jd, jd_from_datetime, tt_to_ut, utc_to_ut1
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.dasha import serialize_dasha_sequence


pytestmark = pytest.mark.loopback


@pytest.fixture
def client_with_engine(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


_NATAL_DT = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
_CURRENT_DT = datetime(2025, 6, 15, 0, 0, tzinfo=timezone.utc)
_NATAL_ISO = "2000-01-01T12:00:00Z"
_CURRENT_ISO = "2025-06-15T00:00:00Z"

_NATAL_PAYLOAD = {"dt": _NATAL_ISO}
_SEQ_PAYLOAD = {"natal": _NATAL_PAYLOAD}
_CURRENT_PAYLOAD = {"natal": _NATAL_PAYLOAD, "current_dt": _CURRENT_ISO}


def _moon_lon(moira_engine) -> float:
    chart = moira_engine.chart(_NATAL_DT)
    return chart.longitudes(include_nodes=False)["Moon"]


# ---------------------------------------------------------------------------
# Sequence parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_dasha_sequence_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    moon_lon = _moon_lon(moira_engine)
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = vimshottari(moon_lon, natal_jd, levels=2)

    resp = client_with_engine.post("/v1/dasha/vimshottari/sequence", json=_SEQ_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["mahadasha_count"] == len(direct)
    assert body["levels_generated"] == 2

    first = body["mahadashas"][0]
    assert first["planet"] == direct[0].planet
    assert first["level"] == 1
    assert first["years"] == pytest.approx(direct[0].years, rel=1e-6)
    assert first["lord_type"] == direct[0].lord_type
    assert first["birth_nakshatra"] == direct[0].birth_nakshatra
    # subs should be populated at levels=2
    assert len(first["sub"]) == len(direct[0].sub)
    assert first["sub"][0]["planet"] == direct[0].sub[0].planet


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    "birth",
    [
        datetime.fromisoformat("2024-01-01T18:04:56.123456+05:30"),
        datetime.fromisoformat("1850-01-01T12:34:56.123456+00:00"),
    ],
    ids=["modern-with-offset", "historical-proxy"],
)
def test_dasha_period_start_utc_replays_in_chart(
    client_with_engine: TestClient,
    birth: datetime,
) -> None:
    natal = {"dt": birth.isoformat()}
    sequence = client_with_engine.post("/v1/dasha/vimshottari/sequence", json={"natal": natal})
    assert sequence.status_code == 200, sequence.text
    first, second, *_ = sequence.json()["mahadashas"]

    birth_jd = jd_from_datetime(birth)
    assert first["start_jd"] == utc_to_ut1(birth_jd)
    assert first["full_start_jd"] < first["start_jd"]
    assert first["start_date"] == datetime_from_jd(first["start_jd"]).isoformat()
    birth_replayed = datetime.fromisoformat(first["start_utc"])
    assert birth_replayed.utcoffset() == timezone.utc.utcoffset(birth)
    assert abs(jd_from_datetime(birth_replayed) - birth_jd) <= math.ulp(birth_jd)
    assert (first["start_utc"] != first["start_date"]) == (birth.year == 2024)

    active = client_with_engine.post(
        "/v1/dasha/vimshottari/current",
        json={"natal": natal, "current_dt": birth.replace(day=2).isoformat(), "levels": 2},
    )
    assert active.status_code == 200, active.text
    assert active.json()["mahadasha"]["start_utc"] == first["start_utc"]
    assert active.json()["antardasha"]["start_utc"] == first["sub"][0]["start_utc"]

    for period in (first, second["sub"][1]):
        chart = client_with_engine.post(
            "/v1/chart",
            json={"dt": period["start_utc"], "bodies": ["Sun"], "include_nodes": False},
        )
        assert chart.status_code == 200, chart.text
        replayed_ut1 = chart.json()["computation_truth"]["jd_ut1"]
        assert abs(replayed_ut1 - period["start_jd"]) <= math.ulp(period["start_jd"])


def test_dasha_period_start_inside_leap_second_has_no_chart_datetime() -> None:
    # At the 2016 insertion, the leap second starts at midnight JD plus
    # the pre-insertion TAI-UTC of 36 seconds and the fixed TAI-to-TT offset.
    start_tt = 2457754.5 + (36.0 + TAI_TT_OFFSET + 0.5) / 86400.0
    start_ut1 = tt_to_ut(start_tt)
    period = DashaPeriod(level=1, planet="Moon", start_jd=start_ut1, end_jd=start_ut1 + 1)
    result = serialize_dasha_sequence([period], levels_generated=1).mahadashas[0]

    assert result.start_jd == start_ut1
    assert result.start_date == period.start_dt.isoformat()
    assert result.start_utc is None


# ---------------------------------------------------------------------------
# Balance parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_dasha_balance_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    moon_lon = _moon_lon(moira_engine)
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct_lord, direct_remaining = dasha_balance(moon_lon, natal_jd)

    resp = client_with_engine.post("/v1/dasha/vimshottari/balance", json=_NATAL_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["lord"] == direct_lord
    assert body["remaining_years"] == pytest.approx(direct_remaining, rel=1e-6)


# ---------------------------------------------------------------------------
# Current (active line) parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_dasha_current_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    moon_lon = _moon_lon(moira_engine)
    natal_jd = jd_from_datetime(_NATAL_DT)
    current_jd = jd_from_datetime(_CURRENT_DT)
    direct_active = current_dasha(moon_lon, natal_jd, current_jd, levels=5)
    direct_line = dasha_active_line(direct_active)

    resp = client_with_engine.post("/v1/dasha/vimshottari/current", json=_CURRENT_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["mahadasha"]["planet"] == direct_line.mahadasha.planet
    assert body["mahadasha"]["level"] == 1
    assert body["depth"] == direct_line.depth
    if direct_line.antardasha is not None:
        assert body["antardasha"]["planet"] == direct_line.antardasha.planet
    else:
        assert body["antardasha"] is None


# ---------------------------------------------------------------------------
# Sequence profile parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_dasha_profile_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    moon_lon = _moon_lon(moira_engine)
    natal_jd = jd_from_datetime(_NATAL_DT)
    direct = dasha_sequence_profile(vimshottari(moon_lon, natal_jd, levels=1))

    resp = client_with_engine.post("/v1/dasha/vimshottari/profile", json=_SEQ_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["mahadasha_count"] == direct.mahadasha_count
    assert body["profile_count"] == direct.profile_count
    assert body["luminary_count"] == direct.luminary_count
    assert body["inner_count"] == direct.inner_count
    assert body["outer_count"] == direct.outer_count
    assert body["node_count"] == direct.node_count
    assert body["total_years"] == pytest.approx(direct.total_years, rel=1e-6)
    assert body["has_node_dashas"] == direct.has_node_dashas
    assert body["profiles"][0]["planet"] == direct.profiles[0].planet


# ---------------------------------------------------------------------------
# Lord-pair parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_dasha_lord_pair_route_matches_engine(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    moon_lon = _moon_lon(moira_engine)
    natal_jd = jd_from_datetime(_NATAL_DT)
    current_jd = jd_from_datetime(_CURRENT_DT)
    direct_line = dasha_active_line(current_dasha(moon_lon, natal_jd, current_jd, levels=2))
    direct_pair = dasha_lord_pair(direct_line)

    resp = client_with_engine.post("/v1/dasha/vimshottari/lord-pair", json=_CURRENT_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["maha_profile"]["planet"] == direct_pair.maha_profile.planet
    assert body["has_antar"] == direct_pair.has_antar
    assert body["is_same_lord"] == direct_pair.is_same_lord
    assert body["involves_node"] == direct_pair.involves_node
    if direct_pair.has_antar:
        assert body["antar_profile"]["planet"] == direct_pair.antar_profile.planet


# ---------------------------------------------------------------------------
# Adversarial witnesses
# ---------------------------------------------------------------------------

def test_dasha_sequence_rejects_naive_natal_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/dasha/vimshottari/sequence",
        json={"natal": {"dt": "2000-01-01T12:00:00"}},
    )
    assert resp.status_code == 422


def test_dasha_sequence_rejects_invalid_levels(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/dasha/vimshottari/sequence",
        json={"natal": _NATAL_PAYLOAD, "levels": 6},
    )
    assert resp.status_code == 422


def test_dasha_current_rejects_date_before_birth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    resp = client_with_engine.post(
        "/v1/dasha/vimshottari/current",
        json={"natal": _NATAL_PAYLOAD, "current_dt": "1999-01-01T00:00:00Z"},
    )
    assert resp.status_code == 422


def test_dasha_current_rejects_date_beyond_cycle(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    resp = client_with_engine.post(
        "/v1/dasha/vimshottari/current",
        json={"natal": _NATAL_PAYLOAD, "current_dt": "2200-01-01T00:00:00Z"},
    )
    assert resp.status_code == 422


def test_dasha_balance_rejects_naive_natal_dt(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/dasha/vimshottari/balance",
        json={"dt": "2000-01-01T12:00:00"},
    )
    assert resp.status_code == 422
