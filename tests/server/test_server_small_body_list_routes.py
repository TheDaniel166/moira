from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira.asteroids import ASTEROID_NAIF
from moira.comets import COMET_NAIF
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


class _FakeReader:
    def __init__(self, covered_ids: set[int]):
        self._covered_ids = frozenset(covered_ids)

    def covered_bodies(self) -> frozenset[int]:
        return self._covered_ids


class _FakeEngine:
    def __init__(self, covered_ids: set[int]):
        self._reader = _FakeReader(covered_ids)


@pytest.fixture
def client_with_small_body_reader(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    covered_ids = {
        ASTEROID_NAIF["Ceres"],
        ASTEROID_NAIF["Vesta"],
        COMET_NAIF["Halley"],
        COMET_NAIF["Encke"],
    }
    monkeypatch.setattr(
        "moira_server.app.create_engine",
        lambda config: _FakeEngine(covered_ids),
    )
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_asteroid_list_route_returns_structured_records_for_loaded_bodies(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get("/v1/asteroids/list")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["bodies"] == [
        {"name": "Ceres", "naif_id": ASTEROID_NAIF["Ceres"]},
        {"name": "Vesta", "naif_id": ASTEROID_NAIF["Vesta"]},
    ]


def test_asteroid_list_route_filters_by_name_or_naif_id(
    client_with_small_body_reader: TestClient,
) -> None:
    by_name = client_with_small_body_reader.get("/v1/asteroids/list?q=ceres")
    by_naif = client_with_small_body_reader.get(f"/v1/asteroids/list?q={ASTEROID_NAIF['Vesta']}")

    assert by_name.status_code == 200
    assert by_name.json() == {
        "bodies": [{"name": "Ceres", "naif_id": ASTEROID_NAIF["Ceres"]}],
        "total": 1,
    }
    assert by_naif.status_code == 200
    assert by_naif.json() == {
        "bodies": [{"name": "Vesta", "naif_id": ASTEROID_NAIF["Vesta"]}],
        "total": 1,
    }


def test_comet_list_route_returns_structured_records_and_filters(
    client_with_small_body_reader: TestClient,
) -> None:
    response = client_with_small_body_reader.get("/v1/comets/list?q=halley")

    assert response.status_code == 200
    assert response.json() == {
        "bodies": [{"name": "Halley", "naif_id": COMET_NAIF["Halley"]}],
        "total": 1,
    }
