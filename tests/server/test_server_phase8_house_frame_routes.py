"""Phase-8 house-frame progression route tests (P8-04) and P8-05 completion.

Parity witnesses: confirm route responses match direct engine calls.
Adversarial witnesses: confirm invalid inputs and methods are rejected cleanly.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.julian import jd_from_datetime, utc_to_ut1
from moira.progressions import (
    ascendant_arc,
    converse_ascendant_arc,
    daily_house_frame,
    progression_chart_condition_profile,
    progression_condition_network_profile,
    secondary_progression,
    vertex_arc,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.progressions import HOUSE_FRAME_ARC_METHODS as _HOUSE_FRAME_ARC_METHODS


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


_NATAL_DT = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
_TARGET_DT = datetime(2025, 6, 15, 0, 0, tzinfo=timezone.utc)
_NATAL_ISO = "2000-01-01T12:00:00Z"
_TARGET_ISO = "2025-06-15T00:00:00Z"
_LAT = 51.5074
_LON = -0.1278

_NATAL_PAYLOAD = {"dt": _NATAL_ISO, "latitude": _LAT, "longitude": _LON}
_HF_PAYLOAD = {"natal": _NATAL_PAYLOAD, "target_dt": _TARGET_ISO}


# ---------------------------------------------------------------------------
# P8-04: daily_house_frame parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_house_frame_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = utc_to_ut1(jd_from_datetime(_NATAL_DT))
    direct = daily_house_frame(natal_jd, _TARGET_DT, _LAT, _LON)

    resp = client_with_engine.post("/v1/progressions/house-frame", json=_HF_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["natal_jd_ut"] == pytest.approx(direct.natal_jd_ut)
    assert body["progressed_jd_ut"] == pytest.approx(direct.progressed_jd_ut, rel=1e-9)
    assert body["asc"] == pytest.approx(direct.houses.asc, rel=1e-6)
    assert body["mc"] == pytest.approx(direct.houses.mc, rel=1e-6)
    assert len(body["cusps"]) == 12
    assert body["doctrine_family"] == "house_frame"
    assert body["coordinate_system"] == "local_house_frame"
    assert body["relation_kind"] == direct.relation_kind
    assert body["condition_state"] == direct.condition_state
    assert body["condition_profile"]["uses_house_frame"] is True


@pytest.mark.requires_ephemeris
def test_house_frame_reduction_route_exposes_house_frame_truth(
    client_with_engine: TestClient,
) -> None:
    resp = client_with_engine.post("/v1/progressions/house-frame/reduction", json=_HF_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["chart_type"] == "Daily Houses"
    assert body["reduction"]["requested_latitude"] == pytest.approx(_LAT)
    assert body["reduction"]["requested_longitude"] == pytest.approx(_LON)
    assert body["reduction"]["computation_truth"]["doctrine"]["doctrine_family"] == "house_frame"
    assert body["reduction"]["classification"]["uses_house_frame"] is True
    assert body["reduction"]["stage_sequence"][-1] == "house_frame_assembly"
    assert (
        body["reduction"]["computation_truth"]["progressed_jd_ut"]
        == pytest.approx(body["result"]["progressed_jd_ut"])
    )


# ---------------------------------------------------------------------------
# P8-04: daily_houses (cusps-only) parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_daily_houses_cusps_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = utc_to_ut1(jd_from_datetime(_NATAL_DT))
    direct_frame = daily_house_frame(natal_jd, _TARGET_DT, _LAT, _LON)
    direct_houses = direct_frame.houses

    resp = client_with_engine.post("/v1/progressions/house-frame/cusps", json=_HF_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert body["asc"] == pytest.approx(direct_houses.asc, rel=1e-6)
    assert body["mc"] == pytest.approx(direct_houses.mc, rel=1e-6)
    assert len(body["cusps"]) == 12
    assert body["cusps"][0] == pytest.approx(direct_houses.cusps[0], rel=1e-6)


# ---------------------------------------------------------------------------
# P8-04: ascendant_arc route parity witness
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_ascendant_arc_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = utc_to_ut1(jd_from_datetime(_NATAL_DT))
    direct = ascendant_arc(natal_jd, _TARGET_DT, _LAT, _LON)

    resp = client_with_engine.post(
        "/v1/progressions/house-frame/arc",
        json={**_HF_PAYLOAD, "method": "ascendant_arc"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["solar_arc_deg"] == pytest.approx(direct.solar_arc_deg, rel=1e-6)
    assert body["relation"]["reference_name"] == "Ascendant"
    assert body["is_converse"] is False


@pytest.mark.requires_ephemeris
def test_converse_ascendant_arc_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = utc_to_ut1(jd_from_datetime(_NATAL_DT))
    direct = converse_ascendant_arc(natal_jd, _TARGET_DT, _LAT, _LON)

    resp = client_with_engine.post(
        "/v1/progressions/house-frame/arc",
        json={**_HF_PAYLOAD, "method": "ascendant_arc", "converse": True},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["is_converse"] is True
    assert body["solar_arc_deg"] == pytest.approx(direct.solar_arc_deg, rel=1e-6)


@pytest.mark.requires_ephemeris
def test_vertex_arc_route_matches_engine(client_with_engine: TestClient) -> None:
    natal_jd = utc_to_ut1(jd_from_datetime(_NATAL_DT))
    direct = vertex_arc(natal_jd, _TARGET_DT, _LAT, _LON)

    resp = client_with_engine.post(
        "/v1/progressions/house-frame/arc",
        json={**_HF_PAYLOAD, "method": "vertex_arc"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["chart_type"] == direct.chart_type
    assert body["solar_arc_deg"] == pytest.approx(direct.solar_arc_deg, rel=1e-6)
    assert body["relation"]["reference_name"] == "Vertex"


def test_house_frame_arc_schema_menu_is_fully_dispatched() -> None:
    from moira_server.models.progressions import HOUSE_FRAME_ARC_METHODS
    from moira_server.services.progressions import _HOUSE_FRAME_ARC_DISPATCH

    assert set(_HOUSE_FRAME_ARC_DISPATCH) == set(HOUSE_FRAME_ARC_METHODS)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("converse", [False, True])
@pytest.mark.parametrize("method", sorted(_HOUSE_FRAME_ARC_METHODS))
def test_house_frame_arc_route_dispatches_every_advertised_method(
    client_with_engine: TestClient, method: str, converse: bool
) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/house-frame/arc",
        json={**_HF_PAYLOAD, "method": method, "converse": converse},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body["chart_type"], str) and body["chart_type"]


@pytest.mark.requires_ephemeris
def test_house_frame_arc_reduction_route_exposes_request_context(
    client_with_engine: TestClient,
) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/house-frame/arc/reduction",
        json={**_HF_PAYLOAD, "method": "ascendant_arc", "converse": True},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["chart_type"] == "Converse Ascendant Arc Direction"
    assert body["reduction"]["requested_method"] == "ascendant_arc"
    assert body["reduction"]["requested_converse"] is True
    assert body["reduction"]["requested_latitude"] == pytest.approx(_LAT)
    assert body["reduction"]["requested_longitude"] == pytest.approx(_LON)
    assert body["reduction"]["classification"]["uses_directed_arc"] is True
    assert body["reduction"]["classification"]["uses_reference_body"] is True
    assert body["reduction"]["stage_sequence"][-1] == "directed_chart_assembly"
    assert (
        body["reduction"]["computation_truth"]["directed_arc_deg"]
        == pytest.approx(body["result"]["solar_arc_deg"], rel=1e-6)
    )


# ---------------------------------------------------------------------------
# P8-05 completion: profile with house_frame_items
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_profile_accepts_house_frame_items(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    sp_chart = secondary_progression(natal_jd, _TARGET_DT)
    hf_frame = daily_house_frame(natal_jd, _TARGET_DT, _LAT, _LON)
    direct_profile = progression_chart_condition_profile(
        charts=[sp_chart], house_frames=[hf_frame]
    )

    resp = client_with_engine.post(
        "/v1/progressions/profile",
        json={
            "items": [{"natal": {"dt": _NATAL_ISO}, "target_dt": _TARGET_ISO}],
            "house_frame_items": [_HF_PAYLOAD],
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["profile_count"] == direct_profile.profile_count
    assert body["time_key_count"] == direct_profile.time_key_count
    assert body["house_frame_count"] == direct_profile.house_frame_count
    assert body["house_frame_count"] == 1


@pytest.mark.requires_ephemeris
def test_profile_accepts_house_frame_items_only(client_with_engine: TestClient) -> None:
    """Profile with no chart items and only house-frame items."""
    resp = client_with_engine.post(
        "/v1/progressions/profile",
        json={"items": [], "house_frame_items": [_HF_PAYLOAD]},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["profile_count"] == 1
    assert body["house_frame_count"] == 1
    assert body["time_key_count"] == 0


@pytest.mark.requires_ephemeris
def test_profile_reduction_exposes_mixed_aggregate_truth(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/profile/reduction",
        json={
            "items": [{"natal": {"dt": _NATAL_ISO}, "target_dt": _TARGET_ISO}],
            "house_frame_items": [_HF_PAYLOAD],
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["profile_count"] == 2
    assert body["reduction"]["chart_item_count"] == 1
    assert body["reduction"]["house_frame_item_count"] == 1
    assert len(body["reduction"]["item_profiles"]) == 2
    assert body["reduction"]["stage_sequence"][-1] == "aggregate_condition_profile"
    assert any(
        profile["uses_house_frame"] is True for profile in body["reduction"]["item_profiles"]
    )


@pytest.mark.requires_ephemeris
def test_network_reduction_exposes_component_profiles(client_with_engine: TestClient) -> None:
    natal_jd = jd_from_datetime(_NATAL_DT)
    sp_chart = secondary_progression(natal_jd, _TARGET_DT)
    hf_frame = daily_house_frame(natal_jd, _TARGET_DT, _LAT, _LON)
    direct_net = progression_condition_network_profile(charts=[sp_chart], house_frames=[hf_frame])

    resp = client_with_engine.post(
        "/v1/progressions/network/reduction",
        json={
            "items": [{"natal": {"dt": _NATAL_ISO}, "target_dt": _TARGET_ISO}],
            "house_frame_items": [_HF_PAYLOAD],
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["technique_node_count"] == direct_net.technique_node_count
    assert body["reduction"]["chart_item_count"] == 1
    assert body["reduction"]["house_frame_item_count"] == 1
    assert len(body["reduction"]["item_profiles"]) == 2
    assert body["reduction"]["stage_sequence"][-1] == "aggregate_condition_network"
    assert any(
        profile["relation_kind"] == "house_frame_projection"
        for profile in body["reduction"]["item_profiles"]
    )


# ---------------------------------------------------------------------------
# Adversarial witnesses
# ---------------------------------------------------------------------------

def test_house_frame_rejects_naive_natal_dt(client_with_engine: TestClient) -> None:
    bad = {"natal": {"dt": "2000-01-01T12:00:00", "latitude": _LAT, "longitude": _LON},
           "target_dt": _TARGET_ISO}
    resp = client_with_engine.post("/v1/progressions/house-frame", json=bad)
    assert resp.status_code == 422


def test_house_frame_arc_rejects_unknown_method(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/house-frame/arc",
        json={**_HF_PAYLOAD, "method": "bogus_arc"},
    )
    assert resp.status_code == 422


def test_profile_rejects_both_empty(client_with_engine: TestClient) -> None:
    resp = client_with_engine.post(
        "/v1/progressions/profile",
        json={"items": [], "house_frame_items": []},
    )
    assert resp.status_code == 422
