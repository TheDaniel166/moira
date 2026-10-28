"""Every route without another success-asserting test answers a real request.

Found by the 2026-09-30 route audit: these routes had no test that calls them
and checks for success, so a crash in any of them would ship unnoticed (as the
star search did from 2026-05-31 to 6.9.9). Requests are ones that returned 200
against the production server configuration.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = pytest.mark.loopback

_CASES = [
    ('POST', '/v1/ashtakavarga/chart/transit-strength', None, {'dt': '2000-01-01T12:00:00Z', 'planet': 'Mars', 'transit_sign_index': 1, 'observer_lat': 51.5, 'observer_lon': -0.1}),
    ('POST', '/v1/ashtakavarga/kakshya-transit', None, {'planet': 'Mars', 'transit_sidereal_lon': 120.0, 'sign_indices': {'Sun': 9, 'Moon': 4, 'Mars': 0, 'Mercury': 9, 'Jupiter': 0, 'Venus': 8, 'Saturn': 1, 'Lagna': 3}}),
    ('POST', '/v1/ashtakavarga/shodhya-pinda', None, {'planet': 'Mars', 'reduced_rekhas': [4, 3, 5, 2, 6, 4, 3, 5, 4, 2, 3, 4], 'sign_indices': {'Sun': 9, 'Moon': 4, 'Mars': 0, 'Mercury': 9, 'Jupiter': 0, 'Venus': 8, 'Saturn': 1, 'Lagna': 3}}),
    ('POST', '/v1/avasthas/evaluate', None, {'sidereal_longitudes': {'Sun': 280.5, 'Moon': 120.25, 'Mars': 15.0, 'Mercury': 270.0, 'Jupiter': 25.0, 'Venus': 240.0, 'Saturn': 40.0}, 'lagna_sidereal_lon': 100.0}),
    ('POST', '/v1/dasha/alternate/ashtottari/chart/profile', None, {'dt': '2000-01-01T12:00:00Z'}),
    ('POST', '/v1/dasha/alternate/yogini/chart/sequence', None, {'dt': '2000-01-01T12:00:00Z'}),
    ('POST', '/v1/jaimini/extended/argala', None, {'sidereal_longitudes': {'Sun': 280.5, 'Moon': 120.25, 'Mars': 15.0, 'Mercury': 270.0, 'Jupiter': 25.0, 'Venus': 240.0, 'Saturn': 40.0}, 'lagna_sidereal_lon': 100.0}),
    ('POST', '/v1/jaimini/extended/arudhas', None, {'sidereal_longitudes': {'Sun': 280.5, 'Moon': 120.25, 'Mars': 15.0, 'Mercury': 270.0, 'Jupiter': 25.0, 'Venus': 240.0, 'Saturn': 40.0}, 'lagna_sidereal_lon': 100.0}),
    ('POST', '/v1/jaimini/extended/chara-dasha', None, {'sidereal_longitudes': {'Sun': 280.5, 'Moon': 120.25, 'Mars': 15.0, 'Mercury': 270.0, 'Jupiter': 25.0, 'Venus': 240.0, 'Saturn': 40.0}, 'lagna_sidereal_lon': 100.0, 'birth_jd': 2451545.0}),
    ('POST', '/v1/jaimini/extended/karakamsa', None, {'sidereal_longitudes': {'Sun': 280.5, 'Moon': 120.25, 'Mars': 15.0, 'Mercury': 270.0, 'Jupiter': 25.0, 'Venus': 240.0, 'Saturn': 40.0}}),
    ('POST', '/v1/occultations/lunar', None, {'target': 'Venus', 'jd_start': 2451545.0, 'jd_end': 2451605.0}),
    ('POST', '/v1/occultations/lunar-path', None, {'target': 'Venus', 'jd_start': 2451545.0, 'jd_end': 2451605.0}),
    ('POST', '/v1/occultations/lunar-star-path', None, {'star_lon': 120.0, 'star_lat': 51.5, 'star_name': 'Regulus', 'jd_start': 2451545.0, 'jd_end': 2451605.0}),
    ('POST', '/v1/occultations/lunar-star-path-at', None, {'star_lon': 120.0, 'star_lat': 51.5, 'star_name': 'Regulus', 'jd_mid': 2451545.0}),
    ('POST', '/v1/upagrahas/kalavelas', None, {'dt': '2000-01-01T12:00:00Z', 'latitude': 51.5, 'longitude': -0.1}),
    ('POST', '/v1/upagrahas/sun-based', None, {'sun_sidereal_lon': 120.0}),
    ('POST', '/v1/yogas/evaluate', None, {'sidereal_longitudes': {'Sun': 280.5, 'Moon': 120.25, 'Mars': 15.0, 'Mercury': 270.0, 'Jupiter': 25.0, 'Venus': 240.0, 'Saturn': 40.0}, 'lagna_sidereal_lon': 100.0}),
]


@pytest.fixture(scope="module")
def client(moira_engine) -> TestClient:
    import moira_server.app as app_module

    original = app_module.create_engine
    app_module.create_engine = lambda config: moira_engine
    try:
        with TestClient(create_app(ServerConfig()), raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app_module.create_engine = original


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(("method", "path", "params", "body"), _CASES, ids=[c[1] for c in _CASES])
def test_route_answers_a_real_request(client: TestClient, method, path, params, body) -> None:
    response = client.request(method, path, params=params, json=body)
    assert response.status_code == 200, response.text[:500]
