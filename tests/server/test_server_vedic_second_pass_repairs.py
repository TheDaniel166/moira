"""Actual HTTP acceptance for VA2 composition and provenance repairs."""

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
import math
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from moira.shadbala import shadbala
from moira.shadbala_context import ShadbalaContext, SEVEN
from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = [pytest.mark.loopback, pytest.mark.requires_ephemeris]


@pytest.fixture(scope='module')
def client(moira_engine):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr('moira_server.app.create_engine', lambda config: moira_engine)
        with TestClient(create_app(ServerConfig(prewarm_enabled=False)),
                        raise_server_exceptions=False) as c:
            yield c


def post(client, route, body):
    response = client.post(route, json=body)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize('dt,lord', [('2005-01-01T00:00:00Z', 'Saturn'),
    ('2020-01-01T00:00:00Z', 'Mercury'), ('2020-01-01T05:30:00+05:30', 'Mercury'),
    ('2000-01-01T23:59:59.9Z', 'Saturn')])
def test_midnight_all_shadbala_products_facade_and_lagna(client, moira_engine, dt, lord):
    body = {'dt': dt, 'observer_lat': 28.6, 'observer_lon': 77.2, 'house_system': 'O'}
    chart = post(client, '/v1/shadbala/chart', body)
    assert chart['context']['vara_lord'] == lord
    assert chart['context']['vara_basis'] == 'civil_utc_midnight'
    for suffix in ('profile', 'network', 'condition', 'bhava', 'full'):
        post(client, '/v1/shadbala/chart/'+suffix,
             body | ({'planet': 'Sun'} if suffix == 'condition' else {}))
    lagna = post(client, '/v1/muhurta/lagna/datetime',
        {'dt': dt, 'latitude': 28.6, 'longitude': 77.2, 'include_shadbala': True})
    assert lagna['assessment']['shadbala_result']['context'] == chart['context']
    instant = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    natal = moira_engine.chart(instant)
    houses = moira_engine.houses(instant, latitude=28.6, longitude=77.2, system='O')
    result = moira_engine.shadbala_for_chart(natal, houses,
        observer_latitude=28.6, observer_longitude=77.2)
    assert result.context.vara_lord == lord
    assert asdict(result.context) == asdict(ShadbalaContext(**{
        **chart['context'],
        **{key: tuple(tuple(x) for x in chart['context'][key])
           for key in ('sidereal_longitudes', 'declinations', 'chesta_values')},
    }))


@pytest.fixture(scope='module')
def direct(client):
    lagna = post(client, '/v1/muhurta/lagna/datetime',
        {'dt': '2000-05-18T00:00:00Z', 'latitude': 28.6, 'longitude': 77.2,
         'include_shadbala': True})['assessment']
    receipt = lagna['shadbala_result']
    return {'jd_ut1': receipt['jd'],
            'sidereal_longitudes': dict(receipt['context']['sidereal_longitudes']),
            'lagna_sidereal_longitude': lagna['lagna_sidereal_longitude'],
            'shadbala_result': receipt}


@pytest.mark.parametrize('planet', SEVEN)
@pytest.mark.parametrize('component', ['ojayugma', 'drekkana'])
def test_direct_rejects_balanced_corruption(client, direct, planet, component):
    post(client, '/v1/muhurta/lagna/direct', direct)
    corrupted = deepcopy(direct)
    s = corrupted['shadbala_result']['planets'][planet]['sthana_bala']
    delta = -1 if s[component] else 1
    s[component] += delta
    s['uchcha'] -= delta
    response = client.post('/v1/muhurta/lagna/direct', json=corrupted)
    assert response.status_code == 422, response.text


@pytest.mark.parametrize('field,value', [('vara_lord', 'Sun'),
    ('vara_jd_utc', 2451545.), ('vara_jd_utc', True), ('vara_basis', 'local_midnight')])
def test_direct_rejects_changed_weekday_provenance(client, direct, field, value):
    changed = deepcopy(direct)
    changed['shadbala_result']['context'][field] = value
    response = client.post('/v1/muhurta/lagna/direct', json=changed)
    assert response.status_code == 422, response.text


@pytest.mark.parametrize('sun', [90., 10./3])
def test_direct_discrete_boundary_uses_context_positions(client, sun):
    positions = dict(zip(SEVEN, (sun, 179.9, 135., 31., 150., 210., 270.)))
    jd = 2451545.
    context = ShadbalaContext(jd, 'Lahiri', tuple(positions.items()),
        tuple((p, 0.) for p in SEVEN), tuple((p, 30.) for p in SEVEN), .5,
        jd-.25, jd+.25, jd+.75, 'Sun', 'Moon', 'Sun')
    strength = shadbala(positions, dict.fromkeys(SEVEN, 1.), SimpleNamespace(asc=0.),
        jd, 1, 'Sun', True, context=context)
    body = {'sidereal_longitudes': positions, 'jd_ut1': jd,
            'lagna_sidereal_longitude': 0., 'shadbala_result': asdict(strength)}
    baseline = post(client, '/v1/muhurta/lagna/direct', body)
    positions['Sun'] = math.nextafter(sun, 0.)
    assert post(client, '/v1/muhurta/lagna/direct', body) == baseline


def test_alternate_rejects_foreign_full_interval_year_mismatch_and_clip(client):
    base = {'system': 'yogini', 'level': 1, 'lord': 'Mangala', 'start_jd': 100.,
            'end_jd': 200., 'full_start_jd': 0., 'full_end_jd': 200.,
            'year_days': 360., 'year_basis': 'savana_360'}
    child = base | {'level': 2}
    route = '/v1/dasha/alternate/period-profile'
    post(client, route, base | {'sub': [child]})
    for mutation in ({'full_start_jd': -1e6, 'full_end_jd': 1e6},
                     {'year_days': 365.25, 'year_basis': 'julian_365.25'}):
        assert client.post(route, json=base | {'sub': [child | mutation]}).status_code == 422
    clipped = [child | {'end_jd': 150., 'full_end_jd': 175.},
               child | {'start_jd': 150., 'full_start_jd': 150.}]
    assert client.post(route, json=base | {'sub': clipped}).status_code == 422


@pytest.mark.parametrize('moon,saturn,phase', [(-1e-300, 0., 'setting'),
    (0., -1e-300, 'rising'), (-0., 720., 'peak')])
def test_sade_sati_http_circular_partition(client, moon, saturn, phase):
    data = post(client, '/v1/sade-sati/status',
                {'natal_moon_sidereal_lon': moon, 'saturn_sidereal_lon': saturn})
    assert data['phase'] == phase
    assert 0 <= data['janma_rashi_index'] < 12
    assert 0 <= data['saturn_rashi_index'] < 12
