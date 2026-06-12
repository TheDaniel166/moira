"""P9-09 Ashtakavarga route tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.ashtakavarga import (
    AshtakavargaPolicy,
    ashtakavarga,
    ashtakavarga_chart_profile,
    sign_strength_profile,
    transit_strength,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


_ALL_LONS = {
    "Sun": 10.0,
    "Moon": 33.0,
    "Mars": 280.0,
    "Mercury": 155.0,
    "Jupiter": 130.0,
    "Venus": 357.0,
    "Saturn": 200.0,
    "Lagna": 220.0,
}

_SIGN_INDICES = {
    "Sun": 0,
    "Moon": 1,
    "Mars": 9,
    "Mercury": 5,
    "Jupiter": 4,
    "Venus": 11,
    "Saturn": 6,
    "Lagna": 7,
}


def _client() -> TestClient:
    return TestClient(create_app(ServerConfig(docs_enabled=False)))


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def test_ashtakavarga_result_route_preserves_bav_sav_truth() -> None:
    direct = ashtakavarga(_ALL_LONS, ayanamsa_system="Lahiri")

    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/result",
            json={"sidereal_longitudes": _ALL_LONS},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ayanamsa_system"] == direct.ayanamsa_system == "Lahiri"
    assert body["sarvashtakavarga"] == list(direct.sarvashtakavarga)
    assert set(body["bhinnashtakavarga"]) == set(direct.bhinnashtakavarga)
    assert body["bhinnashtakavarga"]["Sun"]["planet"] == "Sun"
    assert body["bhinnashtakavarga"]["Sun"]["rekhas"] == list(
        direct.bhinnashtakavarga["Sun"].rekhas
    )
    assert body["bhinnashtakavarga"]["Sun"]["total_rekhas"] == (
        direct.bhinnashtakavarga["Sun"].total_rekhas
    )
    assert body["shodhana_bhinnashtakavarga"] is None
    assert body["shodhana_sarvashtakavarga"] is None


def test_ashtakavarga_result_route_accepts_sign_indices_without_chart_derivation() -> None:
    direct = ashtakavarga(
        {body: float(sign_index * 30) for body, sign_index in _SIGN_INDICES.items()}
    )

    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/result",
            json={"sign_indices": _SIGN_INDICES},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["sarvashtakavarga"] == list(direct.sarvashtakavarga)


def test_ashtakavarga_result_route_preserves_shodhana_policy() -> None:
    policy = AshtakavargaPolicy(
        ayanamsa_system="Krishnamurti",
        apply_trikona_shodhana=True,
        apply_ekadhipatya_shodhana=True,
    )
    direct = ashtakavarga(_ALL_LONS, ayanamsa_system="Krishnamurti", policy=policy)

    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/result",
            json={
                "sidereal_longitudes": _ALL_LONS,
                "policy": {
                    "ayanamsa_system": "Krishnamurti",
                    "apply_trikona_shodhana": True,
                    "apply_ekadhipatya_shodhana": True,
                },
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ayanamsa_system"] == "Krishnamurti"
    assert body["shodhana_sarvashtakavarga"] == list(
        direct.shodhana_sarvashtakavarga
    )
    assert body["shodhana_bhinnashtakavarga"]["Venus"]["rekhas"] == list(
        direct.shodhana_bhinnashtakavarga["Venus"].rekhas
    )


def test_ashtakavarga_profile_route_matches_engine_profile() -> None:
    result = ashtakavarga(_ALL_LONS)
    direct = ashtakavarga_chart_profile(result)

    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/profile",
            json={"sidereal_longitudes": _ALL_LONS},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["sarva_total"] == direct.sarva_total
    assert body["sarva_max"] == direct.sarva_max
    assert body["sarva_max_sign_idx"] == direct.sarva_max_sign_idx
    assert body["sarva_min"] == direct.sarva_min
    assert body["sarva_min_sign_idx"] == direct.sarva_min_sign_idx
    assert body["strong_planet_sign_counts"] == direct.strong_planet_sign_counts
    assert body["result"]["sarvashtakavarga"] == list(result.sarvashtakavarga)


def test_ashtakavarga_sign_profile_route_matches_engine_profile() -> None:
    policy = AshtakavargaPolicy(strong_threshold=5)
    result = ashtakavarga(_ALL_LONS, policy=policy)
    direct = sign_strength_profile(result.for_planet("Sun"), 0, policy)

    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/sign-profile",
            json={
                "sidereal_longitudes": _ALL_LONS,
                "planet": "Sun",
                "sign_index": 0,
                "policy": {"strong_threshold": 5},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["planet"] == direct.planet
    assert body["sign_idx"] == direct.sign_idx
    assert body["rekha_count"] == direct.rekha_count
    assert body["tier"] == direct.tier
    assert body["ayanamsa_system"] == "Lahiri"


def test_ashtakavarga_transit_strength_route_matches_engine_truth() -> None:
    result = ashtakavarga(_ALL_LONS)
    bhinna = result.for_planet("Saturn")
    direct = transit_strength("Saturn", 6, bhinna)

    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/transit-strength",
            json={
                "sidereal_longitudes": _ALL_LONS,
                "planet": "Saturn",
                "transit_sign_index": 6,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["planet"] == "Saturn"
    assert body["transit_sign_index"] == 6
    assert body["rekha_count"] == direct
    assert body["tier"] in {"strong", "weak"}


def test_ashtakavarga_route_rejects_missing_lagna() -> None:
    payload = dict(_ALL_LONS)
    payload.pop("Lagna")

    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/result",
            json={"sidereal_longitudes": payload},
        )

    _assert_validation_envelope(response, message_fragment="Lagna")


def test_ashtakavarga_route_rejects_dual_input_forms() -> None:
    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/result",
            json={
                "sidereal_longitudes": _ALL_LONS,
                "sign_indices": _SIGN_INDICES,
            },
        )

    _assert_validation_envelope(response, message_fragment="exactly one")


def test_ashtakavarga_route_rejects_empty_ayanamsa_label() -> None:
    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/result",
            json={
                "sidereal_longitudes": _ALL_LONS,
                "policy": {"ayanamsa_system": ""},
            },
        )

    _assert_validation_envelope(response, message_fragment="ayanamsa_system")


def test_ashtakavarga_route_rejects_invalid_shodhana_policy() -> None:
    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/result",
            json={
                "sidereal_longitudes": _ALL_LONS,
                "policy": {"apply_ekadhipatya_shodhana": True},
            },
        )

    _assert_validation_envelope(
        response,
        message_fragment="apply_ekadhipatya_shodhana",
    )


def test_ashtakavarga_route_rejects_bad_sign_index() -> None:
    payload = dict(_SIGN_INDICES)
    payload["Lagna"] = 12

    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/result",
            json={"sign_indices": payload},
        )

    _assert_validation_envelope(response, message_fragment="sign_indices")


def test_ashtakavarga_routes_are_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/ashtakavarga/result" in paths
    assert "/v1/ashtakavarga/profile" in paths
    assert "/v1/ashtakavarga/sign-profile" in paths
    assert "/v1/ashtakavarga/transit-strength" in paths
    assert "/v1/ashtakavarga/chart/result" in paths
    assert "/v1/ashtakavarga/chart/profile" in paths
    assert "/v1/ashtakavarga/chart/sign-profile" in paths
    assert "/v1/ashtakavarga/chart/transit-strength" in paths


def _chart_payload() -> dict[str, object]:
    return {
        "dt": datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
        "ayanamsa_system": "Lahiri",
        "observer_lat": 40.7128,
        "observer_lon": -74.0060,
    }


def _direct_longitudes_from_chart_response(body: dict[str, object]) -> dict[str, float]:
    provenance = body["provenance"]
    sidereal = dict(provenance["sidereal_longitudes"])
    sidereal["Lagna"] = provenance["sidereal_lagna"]
    return sidereal


def test_ashtakavarga_chart_result_route_matches_direct_route() -> None:
    with _client() as client:
        chart_response = client.post(
            "/v1/ashtakavarga/chart/result",
            json=_chart_payload(),
        )

    assert chart_response.status_code == 200
    chart_body = chart_response.json()

    with _client() as client:
        direct_response = client.post(
            "/v1/ashtakavarga/result",
            json={
                "sidereal_longitudes": _direct_longitudes_from_chart_response(chart_body),
                "policy": {"ayanamsa_system": "Lahiri"},
            },
        )

    assert direct_response.status_code == 200
    assert chart_body["result"] == direct_response.json()
    assert chart_body["provenance"]["sidereal_lagna"] is not None
    assert chart_body["provenance"]["observer"]["latitude"] == pytest.approx(40.7128)


def test_ashtakavarga_chart_profile_route_matches_direct_route() -> None:
    with _client() as client:
        chart_response = client.post(
            "/v1/ashtakavarga/chart/profile",
            json=_chart_payload(),
        )

    assert chart_response.status_code == 200
    chart_body = chart_response.json()

    with _client() as client:
        direct_response = client.post(
            "/v1/ashtakavarga/profile",
            json={
                "sidereal_longitudes": _direct_longitudes_from_chart_response(chart_body),
                "policy": {"ayanamsa_system": "Lahiri"},
            },
        )

    assert direct_response.status_code == 200
    assert chart_body["result"] == direct_response.json()


def test_ashtakavarga_chart_sign_profile_route_matches_direct_route() -> None:
    payload = _chart_payload()
    payload.update({"planet": "Sun", "sign_index": 0})

    with _client() as client:
        chart_response = client.post(
            "/v1/ashtakavarga/chart/sign-profile",
            json=payload,
        )

    assert chart_response.status_code == 200
    chart_body = chart_response.json()

    with _client() as client:
        direct_response = client.post(
            "/v1/ashtakavarga/sign-profile",
            json={
                "sidereal_longitudes": _direct_longitudes_from_chart_response(chart_body),
                "planet": "Sun",
                "sign_index": 0,
                "policy": {"ayanamsa_system": "Lahiri"},
            },
        )

    assert direct_response.status_code == 200
    assert chart_body["result"] == direct_response.json()


def test_ashtakavarga_chart_route_rejects_missing_observer() -> None:
    with _client() as client:
        response = client.post(
            "/v1/ashtakavarga/chart/result",
            json={
                "dt": datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
            },
        )

    _assert_validation_envelope(response, message_fragment="observer latitude")


def test_ashtakavarga_chart_route_rejects_policy_ayanamsa_mismatch() -> None:
    payload = _chart_payload()
    payload["policy"] = {"ayanamsa_system": "Krishnamurti"}

    with _client() as client:
        response = client.post("/v1/ashtakavarga/chart/result", json=payload)

    _assert_validation_envelope(response, message_fragment="must match")
