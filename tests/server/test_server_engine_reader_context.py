"""Every request computes with the server's own ephemeris.

Services that call engine functions without passing a reader resolve the
active reader from context. Before the request-scoped reader context, those
routes (phase, progressions, Varshaphal) returned HTTP 500 unless a global
kernel path happened to be set. Each bound route family is sampled here; the
routes bind the reader with ``with_engine_reader`` so kernel-free routes still
never touch the engine.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = pytest.mark.loopback


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/v1/phase/synodic", {"body1": "Mars", "body2": "Venus", "jd_ut": 2451545.0}),
        ("/v1/phase/elongation", {"body": "Mars", "jd_ut": 2451545.0}),
        ("/v1/phase/apparent-magnitude", {"body": "Mars", "jd_ut": 2451545.0}),
        (
            "/v1/progressions/secondary",
            {"natal": {"dt": "2000-01-01T12:00:00Z"}, "target_dt": "2025-06-15T00:00:00Z"},
        ),
        (
            "/v1/progressions/arc",
            {"natal": {"dt": "2000-01-01T12:00:00Z"}, "target_dt": "2025-06-15T00:00:00Z", "method": "solar_arc"},
        ),
        (
            "/v1/progressions/house-frame",
            {
                "natal": {"dt": "2000-01-01T12:00:00Z", "latitude": 51.5, "longitude": -0.1},
                "target_dt": "2025-06-15T00:00:00Z",
            },
        ),
        (
            "/v1/varshaphal/chart",
            {
                "natal_dt": "1985-07-15T06:00:00Z",
                "natal_latitude": 28.6,
                "natal_longitude": 77.2,
                "year": 2025,
                "latitude": 28.6,
                "longitude": 77.2,
            },
        ),
    ],
)
def test_route_works_without_a_global_kernel(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    body: dict,
) -> None:
    import moira.spk_reader as spk_reader

    # No global reader and no reader in the caller's context (test fixtures set
    # one, and the server thread would inherit it): only the server's own
    # engine can supply one, as in production.
    monkeypatch.setattr(spk_reader, "_reader", None)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)

    with spk_reader.use_reader_override(None):
        with TestClient(create_app(ServerConfig()), raise_server_exceptions=False) as client:
            response = client.post(path, json=body)

    assert response.status_code == 200, response.text
