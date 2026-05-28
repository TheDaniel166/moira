from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira import MissingEphemerisKernelError
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


class _FakeEngine:
    def __init__(self, *, kernel_available: bool, status: str, kernels: list[str] | None = None):
        self._kernel_available = kernel_available
        self._status = status
        self._kernels = kernels or []

    def is_kernel_available(self) -> bool:
        return self._kernel_available

    def get_kernel_status(self) -> str:
        return self._status

    @property
    def available_kernels(self) -> list[str]:
        return list(self._kernels)


def test_server_startup_and_meta_routes_reuse_stable_engine_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[_FakeEngine] = []

    def _fake_create_engine(config: ServerConfig) -> _FakeEngine:
        engine = _FakeEngine(
            kernel_available=True,
            status="Kernel ready: fake.bsp",
            kernels=["de441.bsp"],
        )
        created.append(engine)
        return engine

    monkeypatch.setattr("moira_server.app.create_engine", _fake_create_engine)

    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")
        version = client.get("/meta/version")
        kernel = client.get("/meta/kernel")

    assert len(created) == 1
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json()["ready"] is True
    assert ready.json()["kernel_available"] is True
    assert ready.json()["kernel_status"] == "Kernel ready: fake.bsp"
    assert version.status_code == 200
    assert version.json()["server_version"] == "0.1.0"
    assert "engine_version" in version.json()
    assert kernel.status_code == 200
    assert kernel.json() == {
        "kernel_available": True,
        "kernel_status": "Kernel ready: fake.bsp",
        "available_kernels": ["de441.bsp"],
    }


def test_server_startup_fails_clearly_when_kernel_is_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_create_engine(config: ServerConfig):
        raise MissingEphemerisKernelError("No planetary kernel is configured.")

    monkeypatch.setattr("moira_server.app.create_engine", _fake_create_engine)

    app = create_app(ServerConfig(require_kernel_ready=True, docs_enabled=False))
    with pytest.raises(MissingEphemerisKernelError, match="No planetary kernel is configured"):
        with TestClient(app):
            pass


def test_server_can_start_for_phase_one_operational_routes_without_kernel_requirement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "moira_server.app.create_engine",
        lambda config: _FakeEngine(
            kernel_available=False,
            status="No planetary kernel is configured.",
            kernels=[],
        ),
    )

    app = create_app(ServerConfig(require_kernel_ready=False, docs_enabled=False))
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "ready": False,
        "kernel_available": False,
        "kernel_status": "No planetary kernel is configured.",
    }
