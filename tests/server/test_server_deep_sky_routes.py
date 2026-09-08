"""HTTP contract coverage for the source-bound deep-sky catalog."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.deep_sky import deep_sky_at
from moira.julian import jd_from_datetime, utc_to_tt
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


def _assert_validation_envelope(response, *, message_fragment: str) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert message_fragment in body["message"]


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_server_startup_exposes_deep_sky_discovery_contract(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=True))

    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert {
        "/v1/deep-sky/list",
        "/v1/deep-sky/position",
        "/v1/deep-sky/bulk",
    }.issubset(schema["paths"])
    tag = next(item for item in schema["tags"] if item["name"] == "deep-sky")
    assert tag["x-family"] == "catalogs"


def test_deep_sky_list_route_preserves_release_scope(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.get("/v1/deep-sky/list")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 60
    assert body["returned_count"] == 60
    assert len(body["objects"]) == 60
    assert body["catalog_version"] == "2026.09.07.1"


def test_deep_sky_list_route_filters_class_and_searches_aliases(
    client_with_engine: TestClient,
) -> None:
    filtered = client_with_engine.get(
        "/v1/deep-sky/list",
        params={"object_class": "nebula", "limit": 100},
    )
    searched = client_with_engine.get(
        "/v1/deep-sky/list",
        params={"q": "NGC 224"},
    )

    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert filtered_body["total"] == 15
    assert filtered_body["returned_count"] == 15
    assert {item["object_class"] for item in filtered_body["objects"]} == {"nebula"}
    assert searched.status_code == 200
    searched_body = searched.json()
    assert searched_body["total"] == 1
    assert searched_body["objects"][0]["name"] == "Andromeda Galaxy"


def test_deep_sky_list_route_rejects_invalid_filters(
    client_with_engine: TestClient,
) -> None:
    invalid_class = client_with_engine.get(
        "/v1/deep-sky/list",
        params={"object_class": "comet"},
    )
    invalid_limit = client_with_engine.get(
        "/v1/deep-sky/list",
        params={"limit": 0},
    )

    _assert_validation_envelope(invalid_class, message_fragment="Input should be")
    _assert_validation_envelope(invalid_limit, message_fragment="greater than or equal to 1")


def test_deep_sky_position_route_matches_engine_and_exposes_provenance(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    jd_tt = utc_to_tt(jd_from_datetime(dt))
    direct = deep_sky_at("M31", jd_tt)

    response = client_with_engine.post(
        "/v1/deep-sky/position",
        json={"dt": dt.isoformat(), "object": "M31"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Andromeda Galaxy"
    assert body["longitude"] == pytest.approx(direct.longitude)
    assert body["latitude"] == pytest.approx(direct.latitude)
    provenance = body["provenance"]
    assert provenance["position_source"] == "simbad_catalog_anchor"
    assert provenance["source_ra_deg"] == pytest.approx(10.684708333333333)
    assert provenance["source_dec_deg"] == pytest.approx(41.26875)
    assert provenance["source_frame"] == "ICRS"
    assert provenance["source_epoch_jd_tt"] == pytest.approx(2451545.0)
    assert provenance["jd_tt"] == pytest.approx(jd_tt)
    assert provenance["proper_motion_applied"] is False
    assert provenance["stage_sequence"][0] == "datetime_validation"
    assert provenance["stage_sequence"][-1] == "response_serialization"


def test_deep_sky_host_route_delegates_to_sovereign_star_registry(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2026, 9, 7, 14, 15, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/deep-sky/position",
        json={"dt": dt.isoformat(), "object": "51 Pegasi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Helvetios"
    assert body["object_class"] == "host_star"
    assert body["provenance"]["position_source"] == "sovereign_star_registry"
    assert body["provenance"]["proper_motion_applied"] is True


def test_deep_sky_position_route_rejects_unknown_or_invalid_input(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    unknown = client_with_engine.post(
        "/v1/deep-sky/position",
        json={"dt": dt.isoformat(), "object": "Hale-Bopp"},
    )
    naive = client_with_engine.post(
        "/v1/deep-sky/position",
        json={"dt": "2000-01-01T12:00:00", "object": "M31"},
    )
    empty = client_with_engine.post(
        "/v1/deep-sky/position",
        json={"dt": dt.isoformat(), "object": "   "},
    )

    _assert_validation_envelope(unknown, message_fragment="not in the released catalog")
    _assert_validation_envelope(naive, message_fragment="timezone-aware")
    _assert_validation_envelope(empty, message_fragment="object must be non-empty")


def test_deep_sky_bulk_route_preserves_results_and_collects_missing(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/deep-sky/bulk",
        json={
            "dt": dt.isoformat(),
            "objects": ["M31", "DefinitelyNotDeepSky"],
            "skip_missing": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert list(body["results"]) == ["M31"]
    assert body["results"]["M31"]["name"] == "Andromeda Galaxy"
    assert body["missing"] == ["DefinitelyNotDeepSky"]
    assert body["catalog_version"] == "2026.09.07.1"


def test_deep_sky_bulk_route_can_fail_closed_on_unknown_name(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/deep-sky/bulk",
        json={
            "dt": dt.isoformat(),
            "objects": ["M31", "DefinitelyNotDeepSky"],
            "skip_missing": False,
        },
    )

    _assert_validation_envelope(response, message_fragment="not in the released catalog")


@pytest.mark.parametrize(
    ("objects", "message_fragment"),
    [
        ([], "at least 1 item"),
        (["M31", " "], "objects entries must be non-empty"),
        ([f"Object{i}" for i in range(61)], "at most 60 items"),
    ],
)
def test_deep_sky_bulk_route_enforces_bounds(
    client_with_engine: TestClient,
    objects: list[str],
    message_fragment: str,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

    response = client_with_engine.post(
        "/v1/deep-sky/bulk",
        json={"dt": dt.isoformat(), "objects": objects, "skip_missing": True},
    )

    _assert_validation_envelope(response, message_fragment=message_fragment)
