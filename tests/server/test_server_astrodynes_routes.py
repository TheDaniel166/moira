"""REST and OpenAPI tests for Church of Light natal Astrodynes."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.astrodynes import ASTRODYNE_PLANETS, ASTRODYNE_POINTS
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.astrodynes import AstrodynesChartRequest
from moira_server.services.astrodynes import compute_astrodynes_chart


pytestmark = pytest.mark.network


_DT = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
_CHART_PAYLOAD = {
    "dt": "2000-01-01T12:00:00Z",
    "observer_lat": 40.7128,
    "observer_lon": -74.006,
    "house_system": "P",
}
_GEOMETRY_PAYLOAD = {
    "planet_longitudes": dict(
        zip(ASTRODYNE_PLANETS, (5, 45, 95, 125, 155, 185, 215, 245, 275, 335))
    ),
    "declinations": {
        **dict(zip(ASTRODYNE_PLANETS, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10))),
        "M.C.": 11,
        "Asc.": 12,
    },
    "cusp_longitudes": tuple(range(0, 360, 30)),
    "mc_longitude": 270,
    "asc_longitude": 0,
}


class _ForbiddenEngine:
    def __getattr__(self, name: str):
        raise AssertionError(f"kernel-free route attempted engine access: {name}")


@pytest.fixture
def kernel_free_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "moira_server.app.create_engine", lambda config: _ForbiddenEngine()
    )
    app = create_app(ServerConfig(docs_enabled=True))
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client_with_engine(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=True))
    with TestClient(app) as client:
        yield client


def _assert_validation(response, fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"] == response.headers["X-Request-ID"]
    if fragment is not None:
        assert fragment in body["message"]


def test_doctrine_route_exposes_fixed_source_tables_without_engine(
    kernel_free_client: TestClient,
) -> None:
    response = kernel_free_client.get("/v1/astrodynes/doctrine")

    assert response.status_code == 200
    body = response.json()
    assert body["doctrine"] == "church_of_light_natal_astrodynes"
    assert tuple(body["planets"]) == ASTRODYNE_PLANETS
    assert tuple(body["points"]) == ASTRODYNE_POINTS
    mercury = next(row for row in body["dignity_rows"] if row["planet"] == "Mercury")
    assert mercury["exaltation_sign"] == "Aquarius"
    assert mercury["exaltation_degree"] == 15.0
    assert body["policy"] == {
        "degree_emphasis_orb_deg": 1.0,
        "parallel_orb_arcmin": 60.0,
        "parallel_geometry": "magnitude_difference",
        "mercury_orb_rule": "planet_presence_luminary_score",
        "mutual_reception_bonus": 5.0,
    }
    assert len(body["house_power_rows"]) == 12
    assert len(body["aspect_orb_rows"]) == 9
    assert {group["family"] for group in body["summary_groups"]} == {
        "society",
        "trinity",
        "element",
        "quality",
    }


def test_geometry_route_is_kernel_free_and_preserves_all_truth_layers(
    kernel_free_client: TestClient,
) -> None:
    response = kernel_free_client.post(
        "/v1/astrodynes/geometry", json=_GEOMETRY_PAYLOAD
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provenance"]["source_mode"] == "explicit_geometry"
    assert body["provenance"]["planetary_frame"] == "caller_supplied"
    assert body["provenance"]["kernel_required"] is False
    assert body["geometry"]["requested_house_system"] is None
    assert body["geometry"]["effective_house_system"] is None
    assert body["geometry"]["house_fallback"] is False
    assert body["geometry"]["dt"] is None
    assert body["geometry"]["jd_ut"] is None
    assert len(body["inputs"]) == len(body["profiles"]) == 12
    assert len(body["relations"]) == 177
    assert body["admitted_relation_count"] <= len(body["relations"])
    assert body["scored_relation_count"] <= body["admitted_relation_count"]
    assert body["aggregate"]["checksums_pass"] is True
    assert body["validation_failures"] == []

    relation_ids = {item["relation_id"] for item in body["relations"]}
    assert len(relation_ids) == len(body["relations"])
    for relation in body["relations"]:
        assert relation["detected"] is True
        assert relation["scored"] is False or relation["admitted"] is True
        assert relation["net_harmony"] == pytest.approx(
            relation["harmony"] - relation["discord"]
        )
    for profile in body["profiles"]:
        assert set(profile["relation_ids"]) <= relation_ids
        assert profile["net_harmony"] == pytest.approx(
            profile["total_harmony"] - profile["total_discord"]
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda payload: payload["planet_longitudes"].pop("Pluto"), "exactly the ten"),
        (lambda payload: payload["declinations"].pop("Asc."), "ten planets plus"),
        (lambda payload: payload.update(cusp_longitudes=[0] * 12), "ordered zodiacal circuit"),
        (lambda payload: payload.update(mc_longitude=271), "mc_longitude must equal"),
        (lambda payload: payload.update(asc_longitude=1), "asc_longitude must equal"),
        (lambda payload: payload["declinations"].update({"Sun": 91}), "[-90, 90]"),
        (lambda payload: payload.update(unexpected=True), "Extra inputs are not permitted"),
    ),
)
def test_geometry_route_rejects_incomplete_incoherent_and_extra_input(
    kernel_free_client: TestClient,
    mutation,
    message: str,
) -> None:
    payload = deepcopy(_GEOMETRY_PAYLOAD)
    mutation(payload)

    _assert_validation(
        kernel_free_client.post("/v1/astrodynes/geometry", json=payload), message
    )


def test_geometry_route_normalizes_longitudes_in_response(
    kernel_free_client: TestClient,
) -> None:
    payload = deepcopy(_GEOMETRY_PAYLOAD)
    payload["planet_longitudes"]["Sun"] = 725.0
    payload["cusp_longitudes"] = tuple(value + 360.0 for value in range(0, 360, 30))
    payload["mc_longitude"] = 630.0
    payload["asc_longitude"] = 360.0

    response = kernel_free_client.post("/v1/astrodynes/geometry", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["geometry"]["planet_longitudes"]["Sun"] == 5.0
    assert body["geometry"]["cusp_longitudes"] == list(range(0, 360, 30))
    assert body["geometry"]["mc_longitude"] == 270.0
    assert body["geometry"]["asc_longitude"] == 0.0


def test_geometry_route_rejects_unvalidated_multi_cusp_sign_distribution(
    kernel_free_client: TestClient,
) -> None:
    payload = deepcopy(_GEOMETRY_PAYLOAD)
    payload["cusp_longitudes"] = (0, 5, 10, 20, 40, 70, 100, 150, 200, 250, 300, 330)
    payload["mc_longitude"] = 250

    _assert_validation(
        kernel_free_client.post("/v1/astrodynes/geometry", json=payload),
        "at most two house cusps per sign",
    )


@pytest.mark.requires_ephemeris
def test_chart_route_matches_service_and_discloses_house_and_frame_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    request = AstrodynesChartRequest(
        dt=_DT,
        observer_lat=40.7128,
        observer_lon=-74.006,
        house_system="P",
    )
    direct = compute_astrodynes_chart(moira_engine, request)

    response = client_with_engine.post("/v1/astrodynes/chart", json=_CHART_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["provenance"]["source_mode"] == "chart_backed"
    assert body["provenance"]["planetary_frame"] == "geocentric_apparent"
    assert body["provenance"]["kernel_required"] is True
    assert body["geometry"]["requested_house_system"] == "P"
    assert body["geometry"]["effective_house_system"] == "P"
    assert body["geometry"]["house_fallback"] is False
    assert body["geometry"]["dt"] == "2000-01-01T12:00:00Z"
    assert body["geometry"]["observer_lat"] == 40.7128
    assert body["geometry"]["observer_lon"] == -74.006
    assert body["geometry"]["jd_ut"] == pytest.approx(2451545.0)
    assert body["geometry"]["obliquity_deg"] == pytest.approx(
        moira_engine.chart(
            _DT, bodies=list(ASTRODYNE_PLANETS), include_nodes=False
        ).obliquity
    )
    assert body["geometry"]["planet_longitudes"] == pytest.approx(
        direct.planet_longitudes
    )
    assert body["aggregate"]["checksums_pass"] is True
    assert body["validation_failures"] == []


@pytest.mark.requires_ephemeris
def test_chart_service_does_not_make_planets_topocentric(moira_engine) -> None:
    class RecordingEngine:
        def __init__(self, target):
            self.target = target
            self.chart_kwargs = None

        def chart(self, *args, **kwargs):
            self.chart_kwargs = kwargs
            return self.target.chart(*args, **kwargs)

        def houses(self, *args, **kwargs):
            return self.target.houses(*args, **kwargs)

        def astrodynes_from_geometry(self, *args, **kwargs):
            return self.target.astrodynes_from_geometry(*args, **kwargs)

    recording = RecordingEngine(moira_engine)
    request = AstrodynesChartRequest(
        dt=_DT,
        observer_lat=40.7128,
        observer_lon=-74.006,
        house_system="P",
    )

    compute_astrodynes_chart(recording, request)

    assert recording.chart_kwargs == {
        "bodies": list(ASTRODYNE_PLANETS),
        "include_nodes": False,
    }


@pytest.mark.requires_ephemeris
def test_chart_route_rejects_polar_fallback_by_default_and_discloses_opt_in(
    client_with_engine: TestClient,
) -> None:
    # This polar meridian produces a valid Porphyry fallback figure without
    # collapsing three or more cusps into one sign.
    polar = {**_CHART_PAYLOAD, "observer_lat": 89.0, "observer_lon": 0.0}

    _assert_validation(
        client_with_engine.post("/v1/astrodynes/chart", json=polar),
        "policy is RAISE",
    )
    response = client_with_engine.post(
        "/v1/astrodynes/chart",
        json={**polar, "allow_house_fallback": True},
    )

    assert response.status_code == 200
    geometry = response.json()["geometry"]
    assert geometry["requested_house_system"] == "P"
    assert geometry["effective_house_system"] == "O"
    assert geometry["house_fallback"] is True
    assert geometry["house_fallback_reason"]


@pytest.mark.requires_ephemeris
def test_chart_route_reports_unvalidated_polar_cusp_distribution_precisely(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrodynes/chart",
        json={
            **_CHART_PAYLOAD,
            "observer_lat": 89.0,
            "allow_house_fallback": True,
        },
    )

    _assert_validation(response, "at most two house cusps per sign")


@pytest.mark.requires_ephemeris
def test_chart_route_rejects_unknown_system_by_default_and_discloses_opt_in(
    client_with_engine: TestClient,
) -> None:
    unknown = {**_CHART_PAYLOAD, "house_system": "not-a-house-system"}

    _assert_validation(
        client_with_engine.post("/v1/astrodynes/chart", json=unknown),
        "unknown house system",
    )
    response = client_with_engine.post(
        "/v1/astrodynes/chart",
        json={**unknown, "allow_house_fallback": True},
    )

    assert response.status_code == 200
    geometry = response.json()["geometry"]
    assert geometry["requested_house_system"] == "not-a-house-system"
    assert geometry["effective_house_system"] == "P"
    assert geometry["house_fallback"] is True
    assert "unknown system code" in geometry["house_fallback_reason"]


@pytest.mark.parametrize(
    "payload",
    (
        {**_CHART_PAYLOAD, "dt": "2000-01-01T12:00:00"},
        {**_CHART_PAYLOAD, "observer_lat": 91},
        {**_CHART_PAYLOAD, "observer_lon": -181},
        {**_CHART_PAYLOAD, "house_system": ""},
        {**_CHART_PAYLOAD, "unexpected": True},
    ),
)
def test_chart_route_rejects_bad_datetime_location_system_and_extra_fields(
    kernel_free_client: TestClient,
    payload: dict,
) -> None:
    _assert_validation(
        kernel_free_client.post("/v1/astrodynes/chart", json=payload)
    )


def test_astrodynes_routes_are_method_strict(kernel_free_client: TestClient) -> None:
    assert kernel_free_client.get("/v1/astrodynes/geometry").status_code == 405
    assert kernel_free_client.get("/v1/astrodynes/chart").status_code == 405
    assert kernel_free_client.post("/v1/astrodynes/doctrine").status_code == 405


def test_openapi_registers_strict_astrodynes_contracts(
    kernel_free_client: TestClient,
) -> None:
    schema = kernel_free_client.get("/openapi.json").json()
    assert set(path for path in schema["paths"] if path.startswith("/v1/astrodynes")) == {
        "/v1/astrodynes/doctrine",
        "/v1/astrodynes/geometry",
        "/v1/astrodynes/chart",
    }
    tag = next(item for item in schema["tags"] if item["name"] == "astrodynes")
    assert tag["x-family"] == "classical-vedic"
    assert tag["x-displayName"] == "Astrodynes"
    assert schema["components"]["schemas"]["AstrodynesGeometryRequest"][
        "additionalProperties"
    ] is False
    assert schema["components"]["schemas"]["AstrodynesChartRequest"][
        "additionalProperties"
    ] is False
    assert schema["components"]["schemas"][
        "AstrodyneZodiacalAspectTruthResponse"
    ]["additionalProperties"] is False
    power_truth = schema["components"]["schemas"]["AstrodyneRelationResponse"][
        "properties"
    ]["power_truth"]["anyOf"]
    assert {item.get("$ref") for item in power_truth if "$ref" in item} == {
        "#/components/schemas/AstrodyneZodiacalAspectTruthResponse",
        "#/components/schemas/AstrodyneParallelAspectTruthResponse",
    }
    operation_ids = [
        operation["operationId"]
        for path_item in schema["paths"].values()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]
    assert len(operation_ids) == len(set(operation_ids))
