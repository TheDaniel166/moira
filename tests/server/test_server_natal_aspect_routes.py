from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira.constants import Body
from moira.facade import Moira
from moira.planets import planet_at
from moira.transits_aspects import find_aspect_transits_to_longitudes

from moira_server.app import create_app
from moira_server.config import ServerConfig
import moira.facade as facade_module
import moira_server.models as public_models


pytestmark = pytest.mark.loopback

_NATAL_ASPECTS_PATH = "/v1/transits/natal-aspects"


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_natal_aspects_route_is_registered_and_typed_in_openapi(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    schema = create_app(ServerConfig(docs_enabled=True)).openapi()

    assert _NATAL_ASPECTS_PATH in schema["paths"]
    operation = schema["paths"][_NATAL_ASPECTS_PATH]["post"]
    assert operation["tags"] == ["predictive"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/NatalAspectSearchRequest"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/NatalAspectSearchResponse"
    }
    assert "frozen" in operation["description"].lower()
    assert "natal" in operation["description"].lower()

    request_schema = schema["components"]["schemas"]["NatalAspectSearchRequest"]
    assert request_schema["additionalProperties"] is False
    assert {
        "body",
        "natal_longitudes",
        "aspect_angles",
        "jd_start",
        "jd_end",
    } <= set(request_schema["required"])
    properties = request_schema["properties"]
    for name in ("natal_longitudes", "aspect_angles", "aspect_orbs"):
        assert name in properties, name
        assert "description" in properties[name]
    assert "frozen" in properties["natal_longitudes"]["description"].lower()
    assert "moon" in properties["body"]["description"].lower()
    assert properties["natal_longitudes"]["type"] == "array"
    assert properties["natal_longitudes"]["items"]["type"] == "number"
    assert properties["aspect_angles"]["type"] == "array"
    assert properties["aspect_orbs"]["type"] == "array"

    response_schema = schema["components"]["schemas"]["NatalAspectSearchResponse"]
    assert response_schema["additionalProperties"] is False
    events_items = response_schema["properties"]["events"]["items"]
    assert events_items == {"$ref": "#/components/schemas/AspectTransitEventResponse"}

    batch_item = schema["components"]["schemas"]["EventBatchItemRequest"]
    assert "natal_longitudes" in batch_item["properties"]
    assert "aspect_angles" in batch_item["properties"]
    assert "aspect_orbs" in batch_item["properties"]
    assert "frozen" in batch_item["properties"]["natal_longitudes"]["description"].lower()

    assert public_models.NatalAspectSearchRequest is not None
    assert public_models.NatalAspectSearchResponse is not None
    assert "find_aspect_transits_to_longitudes" in facade_module.__all__
    assert hasattr(Moira, "natal_aspect_transits")


def test_natal_aspects_route_rejects_unknown_fields(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        _NATAL_ASPECTS_PATH,
        json={
            "body": "Jupiter",
            "natal_longitudes": [10.0],
            "aspect_angles": [0.0],
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 10.0,
            "unexpected_field": True,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert "unexpected_field" in body["message"] or "Extra inputs" in body["message"]


@pytest.mark.requires_ephemeris
def test_natal_aspects_route_matches_engine_grid(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    jd_start = 2451545.0
    jd_end = jd_start + 400.0
    reader = getattr(moira_engine, "_reader", None)
    jupiter = planet_at(Body.JUPITER, jd_start, reader=reader).longitude
    natal_longitudes = [(jupiter + 4.0) % 360.0, (jupiter + 6.0) % 360.0]
    aspect_angles = [0.0]
    aspect_orbs = [1.0]
    specs = [
        (longitude, angle, orb)
        for longitude in natal_longitudes
        for angle, orb in zip(aspect_angles, aspect_orbs, strict=True)
    ]
    direct = find_aspect_transits_to_longitudes(
        Body.JUPITER,
        specs,
        jd_start,
        jd_end,
        reader=reader,
    )
    facade_events = moira_engine.natal_aspect_transits(
        Body.JUPITER,
        natal_longitudes,
        aspect_angles,
        jd_start,
        jd_end,
        aspect_orbs=aspect_orbs,
    )

    response = client_with_engine.post(
        _NATAL_ASPECTS_PATH,
        json={
            "body": "Jupiter",
            "natal_longitudes": natal_longitudes,
            "aspect_angles": aspect_angles,
            "aspect_orbs": aspect_orbs,
            "jd_start": jd_start,
            "jd_end": jd_end,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == len(direct)
    assert len(body["events"]) == len(facade_events)
    assert body["events"], "Jupiter should hit at least one frozen longitude in 400 days"
    for event, expected in zip(body["events"], direct, strict=True):
        assert event["event_type"] == "aspect_transit"
        assert event["body"] == expected.body
        assert event["target"] == pytest.approx(float(expected.target))
        assert event["angle"] == pytest.approx(expected.angle)
        assert event["jd_exact"] == pytest.approx(expected.jd_exact)
        assert event["is_retrograde_hit"] is expected.is_retrograde_hit


@pytest.mark.requires_ephemeris
def test_batch_events_natal_aspect_transits_still_works(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    jd_start = 2451545.0
    jd_end = jd_start + 400.0
    reader = getattr(moira_engine, "_reader", None)
    jupiter = planet_at(Body.JUPITER, jd_start, reader=reader).longitude
    natal_longitudes = [(jupiter + 4.0) % 360.0]
    aspect_angles = [0.0]
    aspect_orbs = [1.0]
    direct = find_aspect_transits_to_longitudes(
        Body.JUPITER,
        ((natal_longitudes[0], 0.0, 1.0),),
        jd_start,
        jd_end,
        reader=reader,
    )

    response = client_with_engine.post(
        "/v1/batch/events",
        json={
            "requests": [
                {
                    "kind": "natal_aspect_transits",
                    "body": "Jupiter",
                    "jd_start": jd_start,
                    "jd_end": jd_end,
                    "natal_longitudes": natal_longitudes,
                    "aspect_angles": aspect_angles,
                    "aspect_orbs": aspect_orbs,
                }
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["ok"] is True
    events = body["results"][0]["events"]
    assert len(events) == len(direct)
    assert events[0]["event_type"] == "aspect_transit"
    assert events[0]["jd_exact"] == pytest.approx(direct[0].jd_exact)


def _natal_aspects_request(body: str) -> dict:
    return {
        "body": body,
        "natal_longitudes": [10.0],
        "aspect_angles": [0.0],
        "jd_start": 2451545.0,
        "jd_end": 2451545.0 + 30.0,
    }


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("body", ["True Node", "Mean Node", "Lilith", "True Lilith"])
def test_natal_aspects_route_admits_lunar_points(client_with_engine: TestClient, body: str) -> None:
    response = client_with_engine.post(_NATAL_ASPECTS_PATH, json=_natal_aspects_request(body))
    assert response.status_code == 200, response.text
    assert "events" in response.json()


@pytest.mark.requires_ephemeris
def test_natal_aspects_route_admits_asteroid_movers(client_with_engine: TestClient) -> None:
    # The session engine may carry no small-body shard; admission is what is
    # under test here, so a kernel-availability 422 is acceptable, an
    # unsupported-mover 422 is not.
    response = client_with_engine.post(_NATAL_ASPECTS_PATH, json=_natal_aspects_request("Ceres"))
    assert response.status_code in (200, 422), response.text
    if response.status_code == 422:
        assert "unsupported natal-aspect mover" not in response.json()["message"]
        assert "small-body kernel" in response.json()["message"]
    else:
        assert "events" in response.json()


def test_natal_aspects_route_and_batch_reject_the_same_unknown_mover(client_with_engine: TestClient) -> None:
    route = client_with_engine.post(
        _NATAL_ASPECTS_PATH,
        json={
            "body": "Planet X",
            "natal_longitudes": [10.0],
            "aspect_angles": [0.0],
            "jd_start": 2451545.0,
            "jd_end": 2451555.0,
        },
    )
    assert route.status_code == 422
    assert "unsupported natal-aspect mover 'Planet X'" in route.json()["message"]

    batch = client_with_engine.post(
        "/v1/batch/events",
        json={
            "requests": [
                {
                    "kind": "natal_aspect_transits",
                    "body": "Planet X",
                    "jd_start": 2451545.0,
                    "jd_end": 2451555.0,
                    "natal_longitudes": [10.0],
                    "aspect_angles": [0.0],
                }
            ]
        },
    )
    assert batch.status_code == 200
    item = batch.json()["results"][0]
    assert item["ok"] is False
    assert "unsupported natal-aspect mover 'Planet X'" in item["failure"]["message"]
