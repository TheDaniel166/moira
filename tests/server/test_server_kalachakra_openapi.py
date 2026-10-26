"""Discovery and schemas expose exact limits and explicit input bases."""
from fastapi.testclient import TestClient
import pytest
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira.sidereal import Ayanamsa

pytestmark = pytest.mark.loopback


def test_openapi_bounds_and_discovery(monkeypatch):
    monkeypatch.setattr('moira_server.app.create_engine',lambda config:object())
    app = create_app(ServerConfig(prewarm_enabled=False))
    schema = app.openapi()
    paths = [p for p in schema['paths'] if p.startswith('/v1/dasha/kalachakra/')]
    assert len(paths)==5
    models = schema['components']['schemas']
    request = models['KalachakraSequenceRequest']
    assert request['additionalProperties'] is False
    assert {'profile_id','seed'} <= set(request['required'])
    assert request['properties']['seed']['discriminator']['propertyName']=='basis'
    assert request['properties']['levels']['minimum']==1
    assert request['properties']['levels']['maximum']==2
    response = models['KalachakraSequenceResponse']['properties']
    assert response['periods']['minItems']==response['periods']['maxItems']==9
    assert response['generated_node_count']['enum']==[9,90]
    assert models['PeriodResponse']['properties']['children']['maxItems']==9
    assert models['ExactRatioResponse']['properties']['numerator']['type']=='string'
    assert models['KalachakraChartRequest']['properties']['ayanamsa_system']['enum']==list(Ayanamsa.ALL)
    assert models['KalachakraCurrentResponse']['properties']['active_line']['maxItems']==2
    for path in paths:
        method = 'get' if path.endswith('/profiles') else 'post'
        assert set(('200','422','500','503')) <= set(schema['paths'][path][method]['responses'])
        assert schema['paths'][path][method]['tags']==['kalachakra-dasha']
    with TestClient(app) as c:
        r = c.get('/v1/dasha/kalachakra/profiles')
        assert r.status_code==200,r.text
        data = r.json()
        assert len(data['conflicts'])==23 and data['maximum_period_nodes']==90
        assert data['ayanamsa_systems']==list(Ayanamsa.ALL)
        assert sum(p['selectable'] for p in data['profiles'])==2
        discovered = c.get('/v1/meta/routes')
        assert discovered.status_code==200
        for path in paths:
            assert path in discovered.text
