from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira import MissingEphemerisKernelError
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeEngine:
    def __init__(
        self,
        *,
        kernel_available: bool,
        status: str,
        kernels: list[str] | None = None,
        chart_error: Exception | None = None,
    ):
        self._kernel_available = kernel_available
        self._status = status
        self._kernels = kernels or []
        self._chart_error = chart_error
        self.chart_calls: list[tuple[datetime, bool]] = []

    def is_kernel_available(self) -> bool:
        return self._kernel_available

    def get_kernel_status(self) -> str:
        return self._status

    @property
    def available_kernels(self) -> list[str]:
        return list(self._kernels)

    def chart(self, dt: datetime, *, include_nodes: bool = True):
        self.chart_calls.append((dt, include_nodes))
        if self._chart_error is not None:
            raise self._chart_error
        return object()


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

    assert response.status_code == 503
    assert response.json() == {
        "ready": False,
        "kernel_available": False,
        "kernel_status": "No planetary kernel is configured.",
    }


def test_server_prewarm_is_opt_in_and_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeEngine(
        kernel_available=True,
        status="Kernel ready: fake.bsp",
    )
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)

    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert engine.chart_calls == []
    assert app.state.startup_readiness.decision_complete is True
    assert app.state.startup_readiness.prewarm_enabled is False


def test_server_prewarm_blocks_startup_until_one_bounded_chart_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeEngine(
        kernel_available=True,
        status="Kernel ready: fake.bsp",
    )
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)

    app = create_app(ServerConfig(docs_enabled=False, prewarm_enabled=True))
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "ready": True,
        "kernel_available": True,
        "kernel_status": "Kernel ready: fake.bsp",
    }
    assert engine.chart_calls == [
        (datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc), False)
    ]
    readiness = app.state.startup_readiness
    assert readiness.decision_complete is True
    assert readiness.prewarm_completed is True
    assert readiness.prewarm_error is None
    assert readiness.prewarm_duration_seconds is not None
    assert readiness.prewarm_duration_seconds >= 0.0


def test_server_prewarm_failure_keeps_liveness_open_and_readiness_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeEngine(
        kernel_available=True,
        status="Kernel ready: fake.bsp",
        chart_error=RuntimeError("synthetic prewarm failure"),
    )
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)

    app = create_app(ServerConfig(docs_enabled=False, prewarm_enabled=True))
    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 503
    assert ready.json() == {
        "ready": False,
        "kernel_available": True,
        "kernel_status": "Kernel ready: fake.bsp",
    }
    readiness = app.state.startup_readiness
    assert readiness.decision_complete is True
    assert readiness.prewarm_completed is False
    assert readiness.prewarm_error == "RuntimeError: synthetic prewarm failure"


def test_server_config_reads_opt_in_prewarm_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MOIRA_SERVER_PREWARM", "yes")

    assert ServerConfig.from_env().prewarm_enabled is True
