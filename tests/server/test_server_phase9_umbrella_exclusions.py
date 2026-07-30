"""Phase-9 umbrella route exclusion guards."""

from __future__ import annotations

from moira_server.app import create_app
from moira_server.config import ServerConfig


def test_vedic_umbrella_route_is_not_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}
    admitted_vedic_paths = {"/v1/vedic/chart-profile"}

    assert "/v1/vedic" not in paths
    assert not any(path.startswith("/v1/vedic/") and path not in admitted_vedic_paths for path in paths)
    assert "/v1/vedic/chart-profile" in paths
    assert "/v1/vedic-dignities/dignity" in paths


def test_classical_umbrella_route_is_not_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/classical" not in paths
    assert not any(path.startswith("/v1/classical/") for path in paths)
    assert "/v1/dignities/chart" in paths
    assert "/v1/lots/catalog" in paths
