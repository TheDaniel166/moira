"""Additive HTTP contracts, BCE time scales and unavailable product states."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.dependencies import get_engine

SOLAR = '/v1/eclipses/solar/bounded-evidence'
LUNAR = '/v1/eclipses/lunar/bounded-evidence'


@pytest.fixture(scope='module')
def evidence_app():
    app = create_app(ServerConfig(prewarm_enabled=False,docs_enabled=False))
    app.state.engine = SimpleNamespace(_reader=None)
    app.dependency_overrides[get_engine] = lambda:SimpleNamespace(_reader=None)
    return app


def test_openapi_has_typed_product_states_and_preserves_legacy_shapes(evidence_app):
    schema = evidence_app.openapi()
    for path in (SOLAR,LUNAR):
        assert set(schema['paths'][path]) == {'post'}
        assert '$ref' in schema['paths'][path]['post']['responses']['200']['content']['application/json']['schema']
    states = schema['components']['schemas']['EclipseProductEvidence']['properties']['state']['enum']
    assert set(states) == {'proved','bounded','evaluated_zero','not_applicable','not_computed','unsupported','unresolved','error'}
    assert 'status' not in schema['components']['schemas']['EclipseEventResponse']['properties']
    assert 'path_width_status' not in schema['components']['schemas']['SolarEclipseGreatestSiteResponse']['properties']


@pytest.mark.loopback
def test_bce_zero_budget_and_missing_provider_have_honest_json_states(evidence_app):
    with TestClient(evidence_app) as client:
        response = client.post(SOLAR,json={'jd_ut1':1538582.,'max_evaluations':0,
                                          'products':['occurrence','geographic_width']})
        assert response.status_code == 200,response.text
        body = response.json()
        assert body['domain']['time_scale'] == 'UT1' and body['domain']['anchor_jd'] == 1538582.
        assert not body['nearest_event_certified']
        assert {p['state'] for p in body['products']} == {'unresolved','not_computed'}
        lunar = client.post(LUNAR,json={'jd_tt':2459891.96})
        assert lunar.status_code == 200,lunar.text
        assert lunar.json()['domain']['time_scale'] == 'TT'
        assert any(p['state']=='unsupported' for p in lunar.json()['products'])


@pytest.mark.loopback
@pytest.mark.parametrize('path,payload',[
    (SOLAR,{'jd_ut1':True}),(SOLAR,{'jd_ut1':2451545.,'offset_days':[1.,2.]}),
    (SOLAR,{'jd_ut1':2451545.,'products':['occurrence','occurrence']}),
    (LUNAR,{'jd_ut1':2451545.}),(LUNAR,{'jd_tt':2451545.,'policy':'nasa_compat'}),
    (LUNAR,{'jd_tt':2451545.,'earth_radius_scale':1.01}),
])
def test_invalid_or_aliased_models_are_rejected(evidence_app,path,payload):
    with TestClient(evidence_app) as client:
        assert client.post(path,json=payload).status_code == 422


@pytest.mark.loopback
def test_independent_computation_error_remains_an_error_over_asgi(monkeypatch):
    from moira import _eclipse_evidence_solar as adapter
    def fail(*args,**kwargs):
        raise RuntimeError('controlled source failure')
    monkeypatch.setattr(adapter,'prepare_continuous_solar_stage3',fail)
    app = create_app(ServerConfig(prewarm_enabled=False,docs_enabled=False))
    app.dependency_overrides[get_engine] = lambda:SimpleNamespace(_reader=SimpleNamespace(_closed=False))
    with TestClient(app) as client:
        response = client.post(SOLAR,json={'jd_ut1':2457987.267724502})
        assert response.status_code == 200,response.text
        products = {p['product']:p for p in response.json()['products']}
        assert products['geographic_width']['state']=='error'
        assert products['geographic_width']['values']==[]
        assert products['geographic_width']['budget']['used'] is None
        assert not products['geographic_width']['coverage_complete']
        assert all(p['state']!='evaluated_zero' for p in products.values())
