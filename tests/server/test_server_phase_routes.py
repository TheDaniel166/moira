"""P12-03 phase, elongation, angular-diameter, and photometry route tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import moira.phase as phase
from moira.constants import Body
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeEngine:
    pass


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


def test_illuminated_fraction_route_preserves_scalar_boundaries(
    client: TestClient,
) -> None:
    full = client.post("/v1/phase/illuminated-fraction", json={"phase_angle": 0.0})
    new = client.post("/v1/phase/illuminated-fraction", json={"phase_angle": 180.0})

    assert full.status_code == 200
    assert new.status_code == 200
    full_body = full.json()
    new_body = new.json()
    assert full_body["illuminated_fraction"] == pytest.approx(1.0)
    assert new_body["illuminated_fraction"] == pytest.approx(0.0)
    assert full_body["range"] == [0.0, 1.0]
    assert full_body["provenance"]["kernel_required"] is False
    assert full_body["provenance"]["engine_entrypoint"] == "illuminated_fraction"


def test_synodic_route_preserves_angle_wrap_and_state_policy(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.services.phase.synodic_phase_angle", lambda a, b, jd: 20.0)

    response = client.post(
        "/v1/phase/synodic",
        json={"body1": "A", "body2": "B", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["body1"] == "A"
    assert body["body2"] == "B"
    assert body["angle"] == pytest.approx(20.0)
    assert body["state"] == "conjunction"
    assert body["angle_range"] == [0.0, 360.0]
    assert body["state_policy"] == "quadrant_labels_with_45_degree_boundaries"
    assert body["provenance"]["kernel_required"] is True
    assert body["provenance"]["stage_sequence"][0] == "body_pair_validation"


def test_synodic_route_can_omit_state_when_requested(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.services.phase.synodic_phase_angle", lambda a, b, jd: 270.0)

    response = client.post(
        "/v1/phase/synodic",
        json={
            "body1": "A",
            "body2": "B",
            "jd_ut": 2451545.0,
            "include_state": False,
        },
    )

    assert response.status_code == 200
    assert "state" not in response.json()


def test_elongation_route_preserves_range_and_basis(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.services.phase.elongation", lambda body, jd: 87.5)

    response = client.post(
        "/v1/phase/elongation",
        json={"body": "Venus", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["body"] == "Venus"
    assert body["elongation"] == pytest.approx(87.5)
    assert body["angle_range"] == [0.0, 180.0]
    assert body["basis"] == "geocentric_ecliptic_spherical_law_of_cosines"
    assert body["provenance"]["engine_entrypoint"] == "elongation"


def test_phase_angle_route_preserves_vector_basis(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.services.phase.phase_angle", lambda body, jd: 45.25)

    response = client.post(
        "/v1/phase/angle",
        json={"body": "Mars", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["phase_angle"] == pytest.approx(45.25)
    assert body["angle_range"] == [0.0, 180.0]
    assert body["basis"] == "Sun_body_Earth_vector_angle"
    assert body["provenance"]["coordinate_frame"] == "ICRF_barycentric_vectors"


def test_angular_diameter_route_accepts_supported_body(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.services.phase.angular_diameter", lambda body, jd: 31.7)

    response = client.post(
        "/v1/phase/angular-diameter",
        json={"body": "Sun", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["angular_diameter_arcseconds"] == pytest.approx(31.7)
    assert body["radius_source"] == "moira.phase physical radius table"
    assert Body.PLUTO in body["provenance"]["support_set"]
    assert body["provenance"]["engine_entrypoint"] == "angular_diameter"


def test_angular_diameter_route_rejects_unsupported_body(client: TestClient) -> None:
    response = client.post(
        "/v1/phase/angular-diameter",
        json={"body": "Chiron", "jd_ut": 2451545.0},
    )

    _assert_validation_envelope(response, message_fragment="angular_diameter does not support body")


def test_apparent_magnitude_route_accepts_supported_body_with_model_provenance(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.services.phase.apparent_magnitude", lambda body, jd: -4.2)

    response = client.post(
        "/v1/phase/apparent-magnitude",
        json={"body": "Venus", "jd_ut": 2451545.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["apparent_magnitude"] == pytest.approx(-4.2)
    assert body["magnitude_system"] == "V"
    assert body["model_family"] == "Mallama_Hilton_2018"
    assert "Venus" in body["model_name"]
    assert body["model_limitations"]
    assert body["provenance"]["model_family"] == "Mallama_Hilton_2018"
    assert Body.SUN in body["provenance"]["unsupported_exclusions"]
    assert Body.PLUTO in body["provenance"]["unsupported_exclusions"]


def test_apparent_magnitude_route_can_suppress_model_detail(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.services.phase.apparent_magnitude", lambda body, jd: -12.1)

    response = client.post(
        "/v1/phase/apparent-magnitude",
        json={
            "body": "Moon",
            "jd_ut": 2451545.0,
            "include_model_detail": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["apparent_magnitude"] == pytest.approx(-12.1)
    assert "model_name" not in body
    assert body["provenance"]["model_family"] == "Schaefer_1993"


@pytest.mark.parametrize("body", [Body.SUN, Body.PLUTO, "Ceres", "Sirius"])
def test_apparent_magnitude_route_rejects_unsupported_bodies(
    client: TestClient,
    body: str,
) -> None:
    response = client.post(
        "/v1/phase/apparent-magnitude",
        json={"body": body, "jd_ut": 2451545.0},
    )

    _assert_validation_envelope(
        response,
        message_fragment="apparent_magnitude does not support body",
    )


def test_phase_routes_reject_non_finite_jd_and_empty_body(client: TestClient) -> None:
    non_finite_jd = client.post(
        "/v1/phase/elongation",
        json={"body": "Venus", "jd_ut": "NaN"},
    )
    empty_body = client.post(
        "/v1/phase/angle",
        json={"body": " ", "jd_ut": 2451545.0},
    )
    non_finite_angle = client.post(
        "/v1/phase/illuminated-fraction",
        json={"phase_angle": "NaN"},
    )

    _assert_validation_envelope(non_finite_jd, message_fragment="jd_ut must be finite")
    _assert_validation_envelope(empty_body, message_fragment="body must be non-empty")
    _assert_validation_envelope(non_finite_angle, message_fragment="phase_angle must be finite")


def test_phase_routes_are_registered(client: TestClient) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/phase/")
    }

    assert paths == {
        "/v1/phase/illuminated-fraction",
        "/v1/phase/synodic",
        "/v1/phase/elongation",
        "/v1/phase/angle",
        "/v1/phase/angular-diameter",
        "/v1/phase/apparent-magnitude",
    }


def test_kernel_backed_route_errors_are_explicit(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_body: str, _jd: float) -> float:
        raise ValueError("body resolution failed")

    monkeypatch.setattr("moira_server.services.phase.elongation", fail)

    response = client.post(
        "/v1/phase/elongation",
        json={"body": "Imaginary", "jd_ut": 2451545.0},
    )

    _assert_validation_envelope(response, message_fragment="body resolution failed")


def test_synodic_engine_wrap_truth_still_matches_unit_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _P:
        def __init__(self, lon: float) -> None:
            self.longitude = lon
            self.latitude = 0.0

    monkeypatch.setattr(
        phase,
        "planet_at",
        lambda name, jd: _P(350.0 if name == "A" else 10.0),
    )

    assert phase.synodic_phase_angle("A", "B", 2451545.0) == pytest.approx(20.0)
