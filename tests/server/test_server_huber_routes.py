"""P12-07 direct Huber route admission tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.constants import HouseSystem
from moira.houses import HouseCusps, classify_house_system
from moira.huber import PHI, PHI_COMPLEMENT, age_point, dynamic_intensity, house_zones
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeEngine:
    pass


def _frame_payload(*, system: str = HouseSystem.KOCH) -> dict[str, object]:
    return {
        "cusps": [float(i * 30) for i in range(12)],
        "asc": 0.0,
        "mc": 270.0,
        "armc": 270.0,
        "system": system,
    }


def _house_frame(*, system: str = HouseSystem.KOCH) -> dict[str, object]:
    return {"source": "direct_cusps", "direct": _frame_payload(system=system)}


def _cusps(*, system: str = HouseSystem.KOCH) -> HouseCusps:
    return HouseCusps(
        system=system,
        cusps=tuple(float(i * 30) for i in range(12)),
        asc=0.0,
        mc=270.0,
        armc=270.0,
        effective_system=system,
        classification=classify_house_system(system),
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _assert_validation_envelope(response, *, message_fragment: str) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    assert message_fragment in body["message"]


def test_dynamic_intensity_route_preserves_curve_values(client: TestClient) -> None:
    expected = dynamic_intensity(1, PHI)

    response = client.post(
        "/v1/huber/dynamic-intensity",
        json={"house": 1, "fraction": PHI},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["house"] == 1
    assert body["requested_fraction"] == pytest.approx(PHI)
    assert body["effective_fraction"] == pytest.approx(expected.fraction)
    assert body["intensity"] == pytest.approx(expected.intensity)
    assert body["zone"] == expected.zone.value
    assert body["curve_basis"] == "piecewise_half_cosine_reconstruction"
    assert body["provenance"]["source_module"] == "moira.huber"
    assert body["provenance"]["engine_entrypoint"] == "dynamic_intensity"
    assert body["provenance"]["psychological_interpretation"] == "not_provided"


def test_dynamic_intensity_route_rejects_invalid_inputs(client: TestClient) -> None:
    bad_house = client.post(
        "/v1/huber/dynamic-intensity",
        json={"house": 0, "fraction": 0.5},
    )
    bad_fraction = client.post(
        "/v1/huber/dynamic-intensity",
        json={"house": 1, "fraction": 1.1},
    )
    non_finite = client.post(
        "/v1/huber/dynamic-intensity",
        json={"house": 1, "fraction": "NaN"},
    )

    _assert_validation_envelope(bad_house, message_fragment="greater than or equal to 1")
    _assert_validation_envelope(bad_fraction, message_fragment="less than or equal to 1")
    _assert_validation_envelope(non_finite, message_fragment="fraction must be finite")


def test_house_zones_route_preserves_direct_koch_frame_truth(client: TestClient) -> None:
    direct = house_zones(_cusps())

    response = client.post(
        "/v1/huber/house-zones",
        json={"house_frame": _house_frame()},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["zones"]) == 12
    assert [zone["house"] for zone in body["zones"]] == list(range(1, 13))
    first = body["zones"][0]
    assert first["cusp_longitude"] == pytest.approx(direct[0].cusp_longitude)
    assert first["next_cusp_longitude"] == pytest.approx(direct[0].next_cusp_longitude)
    assert first["balance_point_fraction"] == pytest.approx(PHI_COMPLEMENT)
    assert first["low_point_fraction"] == pytest.approx(PHI)
    assert body["house_frame"]["source"] == "direct_cusps"
    provenance = body["house_frame_provenance"]
    assert provenance["house_frame_source"] == "caller_supplied"
    assert provenance["cusp_derivation_owner"] == "caller_supplied"
    assert provenance["effective_system"] == HouseSystem.KOCH
    assert provenance["is_koch_effective"] is True
    assert provenance["chart_backed_derivation"] == "not_admitted_for_p12_07"


def test_house_zones_route_reports_non_koch_frame_without_relabeling(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/huber/house-zones",
        json={"house_frame": _house_frame(system=HouseSystem.WHOLE_SIGN)},
    )

    assert response.status_code == 200
    provenance = response.json()["house_frame_provenance"]
    assert provenance["effective_system"] == HouseSystem.WHOLE_SIGN
    assert provenance["is_koch_effective"] is False
    assert "non-Koch" in provenance["note"]


@pytest.mark.parametrize("age", [0.0, 18.0, 36.0, 54.0, 72.0])
def test_age_point_route_preserves_engine_truth(client: TestClient, age: float) -> None:
    expected = age_point(age, _cusps())

    response = client.post(
        "/v1/huber/age-point",
        json={"age_years": age, "house_frame": _house_frame()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["age_years"] == pytest.approx(expected.age_years)
    assert body["cycle"] == expected.cycle
    assert body["house"] == expected.house
    assert body["fraction_through_house"] == pytest.approx(expected.fraction_through_house)
    assert body["longitude"] == pytest.approx(expected.longitude)
    assert body["zone"] == expected.zone.value
    assert body["years_into_house"] == pytest.approx(expected.years_into_house)
    assert body["intensity"] == pytest.approx(expected.intensity)
    assert body["provenance"]["engine_entrypoint"] == "age_point"


def test_intensity_at_route_preserves_house_assignment(client: TestClient) -> None:
    response = client.post(
        "/v1/huber/intensity-at",
        json={"longitude": 15.0, "house_frame": _house_frame()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["longitude"] == pytest.approx(15.0)
    assert body["house"] == 1
    assert body["fraction"] == pytest.approx(0.5)
    assert 0.0 <= body["intensity"] <= 1.0
    assert body["house_frame_provenance"]["is_koch_effective"] is True


def test_chart_intensity_profile_route_preserves_point_names_and_flags(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/huber/chart-intensity-profile",
        json={
            "points": {"OnCusp": 0.0, "AtLowPoint": PHI * 30.0, "Middle": 10.0},
            "house_frame": _house_frame(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["point_count"] == 3
    assert [score["name"] for score in body["scores"]] == ["OnCusp", "AtLowPoint", "Middle"]
    assert [score["name"] for score in body["high_intensity"]] == ["OnCusp"]
    assert [score["name"] for score in body["low_intensity"]] == ["AtLowPoint"]
    assert 0.0 <= body["mean_intensity"] <= 1.0
    assert body["provenance"]["engine_entrypoint"] == "chart_intensity_profile"


def test_age_point_contacts_route_preserves_bounded_scan(client: TestClient) -> None:
    response = client.post(
        "/v1/huber/age-point-contacts",
        json={
            "points": {"AscendantPoint": 0.0},
            "house_frame": _house_frame(),
            "orb": 0.1,
            "start_age": 0.0,
            "end_age": 1.0,
            "step_years": 1.0 / 12.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["orb"] == pytest.approx(0.1)
    assert body["start_age"] == pytest.approx(0.0)
    assert body["end_age"] == pytest.approx(1.0)
    assert body["step_years"] == pytest.approx(1.0 / 12.0)
    assert body["scan_bounds"]["point_count"] == 1
    assert body["contacts"][0]["age_years"] == pytest.approx(0.0)
    assert body["contacts"][0]["point_name"] == "AscendantPoint"
    assert body["contacts"][0]["separation_degrees"] == pytest.approx(0.0)
    assert body["provenance"]["engine_entrypoint"] == "age_point_contacts"


def test_huber_routes_reject_malformed_house_frames(client: TestClient) -> None:
    short_cusps = _frame_payload()
    short_cusps["cusps"] = [0.0] * 11
    non_finite = _frame_payload()
    non_finite["cusps"] = [0.0] * 11 + ["NaN"]
    chart_backed = {"source": "server_chart_backed", "direct": _frame_payload()}

    short_response = client.post(
        "/v1/huber/house-zones",
        json={"house_frame": {"source": "direct_cusps", "direct": short_cusps}},
    )
    non_finite_response = client.post(
        "/v1/huber/house-zones",
        json={"house_frame": {"source": "direct_cusps", "direct": non_finite}},
    )
    chart_backed_response = client.post(
        "/v1/huber/house-zones",
        json={"house_frame": chart_backed},
    )

    _assert_validation_envelope(short_response, message_fragment="at least 12 items")
    _assert_validation_envelope(non_finite_response, message_fragment="house_frame.cusps must be finite")
    _assert_validation_envelope(chart_backed_response, message_fragment="only source='direct_cusps'")


def test_huber_routes_reject_invalid_point_maps_and_scan_bounds(
    client: TestClient,
) -> None:
    empty_points = client.post(
        "/v1/huber/chart-intensity-profile",
        json={"points": {}, "house_frame": _house_frame()},
    )
    duplicate_after_trim = client.post(
        "/v1/huber/chart-intensity-profile",
        json={"points": {"Mars": 10.0, " Mars ": 20.0}, "house_frame": _house_frame()},
    )
    oversized_points = client.post(
        "/v1/huber/chart-intensity-profile",
        json={
            "points": {f"Point{i}": float(i) for i in range(65)},
            "house_frame": _house_frame(),
        },
    )
    bad_window = client.post(
        "/v1/huber/age-point-contacts",
        json={
            "points": {"Sun": 0.0},
            "house_frame": _house_frame(),
            "start_age": 10.0,
            "end_age": 9.0,
        },
    )
    too_fine_step = client.post(
        "/v1/huber/age-point-contacts",
        json={
            "points": {"Sun": 0.0},
            "house_frame": _house_frame(),
            "step_years": 0.001,
        },
    )

    _assert_validation_envelope(empty_points, message_fragment="at least one entry")
    _assert_validation_envelope(duplicate_after_trim, message_fragment="unique after trimming")
    _assert_validation_envelope(oversized_points, message_fragment="at most 64 entries")
    _assert_validation_envelope(bad_window, message_fragment="end_age must be greater than or equal")
    _assert_validation_envelope(too_fine_step, message_fragment="greater than or equal")


def test_huber_routes_are_registered(client: TestClient) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/huber/")
    }

    assert paths == {
        "/v1/huber/dynamic-intensity",
        "/v1/huber/house-zones",
        "/v1/huber/age-point",
        "/v1/huber/intensity-at",
        "/v1/huber/chart-intensity-profile",
        "/v1/huber/age-point-contacts",
    }
