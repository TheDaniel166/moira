"""Contract tests for polar house admissibility REST API endpoints."""

from __future__ import annotations

import importlib

from fastapi.testclient import TestClient
import pytest

from moira.constants import HouseSystem
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.chart import PolarAdmissibilityRequest
from moira_server.services.chart import compute_polar_admissibility


pytestmark = [pytest.mark.loopback, pytest.mark.requires_ephemeris]


@pytest.fixture
def client_with_engine(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_polar_admissibility_campanus_at_80n(client_with_engine: TestClient) -> None:
    payload = {
        "latitude": 80.0,
        "system": "CAMPANUS",
        "armc_start": 0.0,
        "armc_end": 355.0,
        "armc_step": 5.0,
    }
    response = client_with_engine.post("/v1/houses/polar-admissibility", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == HouseSystem.CAMPANUS
    assert data["latitude"] == 80.0
    assert data["total_samples"] == 72
    assert data["armc_start"] == 0.0
    assert data["armc_end"] == 355.0
    assert data["armc_step"] == 5.0
    assert data["last_sampled_armc"] == 355.0
    assert data["maximum_allowed_samples"] == 3601
    assert data["valid_fraction"] > 0.0
    assert data["has_any_window"] is True
    assert len(data["windows"]) > 0


def test_polar_admissibility_regiomontanus_at_77n(client_with_engine: TestClient) -> None:
    payload = {
        "latitude": 77.0,
        "system": "REGIOMONTANUS",
        "armc_start": 0.0,
        "armc_end": 355.0,
        "armc_step": 5.0,
    }
    response = client_with_engine.post("/v1/houses/polar-admissibility", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == HouseSystem.REGIOMONTANUS
    assert data["valid_fraction"] > 0.5
    assert data["has_any_window"] is True


def test_polar_admissibility_topocentric_at_77n(client_with_engine: TestClient) -> None:
    payload = {
        "latitude": 77.0,
        "system": "TOPOCENTRIC",
        "armc_start": 0.0,
        "armc_end": 355.0,
        "armc_step": 5.0,
    }
    response = client_with_engine.post("/v1/houses/polar-admissibility", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == HouseSystem.TOPOCENTRIC
    assert data["valid_fraction"] > 0.0


def test_polar_admissibility_unsupported_system_raises_400(client_with_engine: TestClient) -> None:
    payload = {
        "latitude": 80.0,
        "system": "WHOLE_SIGN",
    }
    response = client_with_engine.post("/v1/houses/polar-admissibility", json=payload)
    assert response.status_code == 400
    assert "No polar admissibility scanner available" in response.json()["detail"]


def test_polar_admissibility_invalid_latitude_raises_422(client_with_engine: TestClient) -> None:
    payload = {
        "latitude": 95.0,
        "system": "CAMPANUS",
    }
    response = client_with_engine.post("/v1/houses/polar-admissibility", json=payload)
    assert response.status_code == 422


def test_polar_admissibility_normalizes_lowercase_code(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/houses/polar-admissibility",
        json={
            "latitude": 80.0,
            "system": "c",
            "armc_start": 0.0,
            "armc_end": 10.0,
            "armc_step": 5.0,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["system"] == HouseSystem.CAMPANUS


def test_polar_admissibility_decimal_grid_has_exact_sample_count(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/houses/polar-admissibility",
        json={
            "latitude": 80.0,
            "system": "CAMPANUS",
            "armc_start": 0.0,
            "armc_end": 1.0,
            "armc_step": 0.1,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["total_samples"] == 11


def test_polar_admissibility_accepts_bounded_nondivisible_grid(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/houses/polar-admissibility",
        json={
            "latitude": 80.0,
            "system": "CAMPANUS",
            "armc_start": 0.0,
            "armc_end": 10.0,
            "armc_step": 3.0,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["total_samples"] == 4
    assert response.json()["last_sampled_armc"] == 9.0


def test_polar_admissibility_applies_placidus_specific_work_limit(
    client_with_engine: TestClient,
) -> None:
    rejected = client_with_engine.post(
        "/v1/houses/polar-admissibility",
        json={
            "latitude": 80.0,
            "system": "PLACIDUS",
            "armc_start": 0.0,
            "armc_end": 73.0,
            "armc_step": 1.0,
        },
    )
    assert rejected.status_code == 422
    assert "maximum of 73 samples" in rejected.json()["message"]

    admitted = client_with_engine.post(
        "/v1/houses/polar-admissibility",
        json={
            "latitude": 80.0,
            "system": "PLACIDUS",
            "armc_start": 0.0,
            "armc_end": 1.0,
            "armc_step": 1.0,
        },
    )
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["maximum_allowed_samples"] == 73


def test_polar_admissibility_binds_placidus_inner_root_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def _scanner(**kwargs):
        observed.update(kwargs)
        return object()

    module = importlib.import_module("moira.experimental_placidus")
    monkeypatch.setattr(module, "scan_experimental_placidus_admissibility", _scanner)

    compute_polar_admissibility(
        PolarAdmissibilityRequest(
            latitude=80.0,
            system="PLACIDUS",
            armc_start=0.0,
            armc_end=1.0,
            armc_step=1.0,
        )
    )

    assert observed["sample_count"] == 12_000


@pytest.mark.parametrize(
    "payload",
    [
        {"latitude": 80.0, "system": "CAMPANUS", "obliquity": 999.0},
        {
            "latitude": 80.0,
            "system": "CAMPANUS",
            "armc_start": 0.0,
            "armc_end": 360.0,
            "armc_step": 0.01,
        },
        {
            "latitude": 80.0,
            "system": "CAMPANUS",
            "armc_start": 0.0,
            "armc_end": 10.0,
            "armc_step": 5e-324,
        },
        {"latitude": 80.0, "system": "CAMPANUS", "rho_max": 0.5},
        {
            "latitude": 80.0,
            "system": "CAMPANUS",
            "armc_start": 0.0,
            "armc_end": 10.0,
            "armc_step": 5.0,
            "stability_radius": 2,
        },
        {
            "latitude": 80.0,
            "system": "CAMPANUS",
            "dt": "2026-09-21T12:00:00",
        },
    ],
)
def test_polar_admissibility_rejects_invalid_or_unbounded_scans(
    client_with_engine: TestClient,
    payload: dict[str, object],
) -> None:
    response = client_with_engine.post(
        "/v1/houses/polar-admissibility",
        json=payload,
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
