from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira import MissingEphemerisKernelError
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


class _FakeEngine:
    def is_kernel_available(self) -> bool:
        return True

    def get_kernel_status(self) -> str:
        return "Kernel ready: fake.bsp"

    @property
    def available_kernels(self) -> list[str]:
        return ["de441.bsp"]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))

    @app.get("/_test/value-error")
    def raise_value_error():
        raise ValueError("bad client payload")

    @app.get("/_test/missing-kernel")
    def raise_missing_kernel():
        raise MissingEphemerisKernelError("Kernel missing for route")

    return TestClient(app)


def test_value_error_maps_to_validation_envelope(client: TestClient) -> None:
    response = client.get("/_test/value-error")

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["message"] == "bad client payload"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]


def test_missing_kernel_error_maps_to_kernel_readiness_envelope(client: TestClient) -> None:
    response = client.get("/_test/missing-kernel")

    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == "kernel_not_ready"
    assert body["category"] == "kernel_readiness"
    assert body["message"] == "Kernel missing for route"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
