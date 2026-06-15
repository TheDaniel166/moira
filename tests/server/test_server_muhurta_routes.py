from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.julian import jd_from_datetime
from moira.muhurta import classify_muhurta, score_muhurta
from moira.panchanga import panchanga_at
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


_DT = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
_JD = jd_from_datetime(_DT)
_DT_ISO = "2000-01-01T12:00:00Z"
_SUN_LON = 280.0
_MOON_LON = 70.0
_DIRECT_PAYLOAD = {
    "sun_tropical_lon": _SUN_LON,
    "moon_tropical_lon": _MOON_LON,
    "jd": _JD,
}


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def test_muhurta_direct_classification_route_matches_engine(client_with_engine: TestClient) -> None:
    panchanga = panchanga_at(_SUN_LON, _MOON_LON, _JD)
    direct = classify_muhurta(panchanga)

    response = client_with_engine.post("/v1/muhurta/direct/classification", json=_DIRECT_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["request"]["source"] == "direct_inputs"
    assert body["panchanga"]["nakshatra"]["nakshatra"] == panchanga.nakshatra.nakshatra
    assert body["classification"]["overall"] == direct.overall
    assert body["classification"]["nakshatra"] == direct.nakshatra
    assert body["provenance"]["source_module"] == "moira.muhurta"
    assert body["provenance"]["engine_entrypoint"] == "classify_muhurta"
    assert body["provenance"]["western_electional_doctrine"] == "not_admitted"
    assert body["provenance"]["search_semantics"] == "not_admitted"


def test_muhurta_direct_score_route_matches_engine_and_policy_weights(
    client_with_engine: TestClient,
) -> None:
    payload = {
        **_DIRECT_PAYLOAD,
        "muhurta_policy": {
            "weight_tithi": 1.0,
            "weight_vara": 1.0,
            "weight_nakshatra": 2.0,
            "weight_yoga": 1.5,
            "weight_karana": 0.8,
        },
    }
    panchanga = panchanga_at(_SUN_LON, _MOON_LON, _JD)
    from moira.muhurta import MuhurtaPolicy

    direct = score_muhurta(panchanga, MuhurtaPolicy(weight_nakshatra=2.0))

    response = client_with_engine.post("/v1/muhurta/direct/score", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["score"]["total"] == pytest.approx(direct.total)
    assert body["score"]["breakdown"]["nakshatra"] == pytest.approx(direct.breakdown["nakshatra"])
    assert body["score"]["score_scale"] == "engine_raw_unbounded"
    assert body["score"]["score_direction"] == "higher_is_more_favorable_under_policy"
    assert body["policy"]["weight_nakshatra"] == pytest.approx(2.0)
    assert "use_classical_ashubha_yoga" in body["policy"]["omitted_policy_fields"]


@pytest.mark.requires_ephemeris
def test_muhurta_chart_classification_route_matches_chart_backed_panchanga(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    chart = moira_engine.chart(_DT, bodies=["Sun", "Moon"], include_nodes=False)
    longitudes = chart.longitudes(include_nodes=False)
    panchanga = panchanga_at(longitudes["Sun"], longitudes["Moon"], _JD)
    direct = classify_muhurta(panchanga)

    response = client_with_engine.post("/v1/muhurta/chart/classification", json={"dt": _DT_ISO})

    assert response.status_code == 200
    body = response.json()
    assert body["request"]["source"] == "chart_backed"
    assert body["classification"]["overall"] == direct.overall
    assert body["panchanga"]["tithi"]["name"] == panchanga.tithi.name
    assert body["provenance"]["chart_construction"] == "Moira.chart"
    assert body["provenance"]["reader_owner"] == "Moira engine instance"


@pytest.mark.requires_ephemeris
def test_muhurta_chart_score_route_matches_chart_backed_panchanga(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    chart = moira_engine.chart(_DT, bodies=["Sun", "Moon"], include_nodes=False)
    longitudes = chart.longitudes(include_nodes=False)
    panchanga = panchanga_at(longitudes["Sun"], longitudes["Moon"], _JD)
    direct = score_muhurta(panchanga)

    response = client_with_engine.post("/v1/muhurta/chart/score", json={"dt": _DT_ISO})

    assert response.status_code == 200
    body = response.json()
    assert body["score"]["total"] == pytest.approx(direct.total)
    assert body["score"]["breakdown"] == pytest.approx(direct.breakdown)
    assert body["provenance"]["engine_entrypoint"] == "score_muhurta"
    assert "muhurta_scoring" in body["provenance"]["stage_sequence"]


def test_muhurta_routes_reject_naive_datetime(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/muhurta/chart/classification",
        json={"dt": "2000-01-01T12:00:00"},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_muhurta_chart_route_rejects_incomplete_observer_pair(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/muhurta/chart/score",
        json={"dt": _DT_ISO, "observer_lat": 35.0},
    )

    _assert_validation_envelope(response, message_fragment="observer_lat and observer_lon")


def test_muhurta_direct_route_rejects_non_finite_inputs(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/muhurta/direct/classification",
        json={**_DIRECT_PAYLOAD, "sun_tropical_lon": "NaN"},
    )

    _assert_validation_envelope(response, message_fragment="numeric Muhurta direct inputs")


def test_muhurta_route_rejects_invalid_policy_weight(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/muhurta/direct/score",
        json={**_DIRECT_PAYLOAD, "muhurta_policy": {"weight_tithi": -0.1}},
    )

    _assert_validation_envelope(response, message_fragment="non-negative")


def test_muhurta_route_rejects_invalid_ayanamsa_name(client_with_engine: TestClient) -> None:
    response = client_with_engine.post(
        "/v1/muhurta/direct/classification",
        json={**_DIRECT_PAYLOAD, "ayanamsa_system": "NotARealAyanamsa"},
    )

    _assert_validation_envelope(response, message_fragment="Unknown ayanamsa")


def test_muhurta_compute_routes_do_not_admit_get(client_with_engine: TestClient) -> None:
    response = client_with_engine.get("/v1/muhurta/direct/classification")

    assert response.status_code == 405
