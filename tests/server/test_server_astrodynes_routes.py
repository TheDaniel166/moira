"""REST and OpenAPI tests for Church of Light natal Astrodynes."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from moira.astrodynes import ASTRODYNE_PLANETS, ASTRODYNE_POINTS
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.astrodynes import AstrodynesChartRequest
from moira_server.models.progressed_astrodynes import (
    ProgressedInfluenceIntegrationRequest,
)
from moira_server.services.astrodynes import compute_astrodynes_chart


pytestmark = pytest.mark.loopback


_DT = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
_CHART_PAYLOAD = {
    "dt": "2000-01-01T12:00:00Z",
    "observer_lat": 40.7128,
    "observer_lon": -74.006,
    "house_system": "P",
}
_PROGRESSED_CHART_PAYLOAD = {
    "natal_dt": "1882-12-12T12:11:26Z",
    "target_dt": "1949-08-29T12:00:00Z",
    "observer_lat": 41 + 37 / 60,
    "observer_lon": -94.0,
    "house_system": "P",
    "allow_house_fallback": False,
}
_PROGRESSED_CONTACT_QUERY = {
    "body_a": "Moon",
    "kind_a": "transit",
    "body_b": "M.C.",
    "kind_b": "radical",
    "aspect": "sextile",
}
_PROGRESSED_SEARCH_PAYLOAD = {
    "natal_dt": "1882-12-12T12:11:26Z",
    "start_dt": "1949-08-29T08:00:00Z",
    "end_dt": "1949-08-29T16:00:00Z",
    "observer_lat": 41 + 37 / 60,
    "observer_lon": -94.0,
    "query": _PROGRESSED_CONTACT_QUERY,
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
_FIXTURE_DIR = Path(__file__).parents[1] / "fixtures"


def test_progressed_integration_request_requires_three_sample_minimum() -> None:
    with pytest.raises(ValueError, match="greater than or equal to 3"):
        ProgressedInfluenceIntegrationRequest(
            **_PROGRESSED_SEARCH_PAYLOAD,
            max_samples=2,
        )


def _progressed_payloads() -> tuple[dict, dict]:
    normal_fixture = json.loads(
        (_FIXTURE_DIR / "progressed_astrodynes_benjamine_normal_1949.json").read_text(
            encoding="utf-8"
        )
    )
    dated_fixture = json.loads(
        (_FIXTURE_DIR / "progressed_astrodynes_benjamine_dated_1949.json").read_text(
            encoding="utf-8"
        )
    )
    normal = {
        "birth_bodies": [
            {"body": body, "power": values[0], "harmony": values[1], "discord": values[2]}
            for body, values in normal_fixture["birth_bodies"].items()
        ],
        "birth_signs": {
            sign: {"power": values[0], "harmony": values[1], "discord": values[2]}
            for sign, values in normal_fixture["birth_signs"].items()
        },
        "birth_houses": {
            house: {"power": values[0], "harmony": values[1], "discord": values[2]}
            for house, values in normal_fixture["birth_houses"].items()
        },
        "placements": [
            {
                "body": body,
                "longitude_deg": values[0],
                "house": 7 if body == "Moon" else values[1],
            }
            for body, values in normal_fixture["placements"].items()
        ],
    }
    practical = {
        "normal": normal,
        "aspects": [
            {
                "relation_id": row["id"],
                "body_a": row["a"],
                "body_b": row["b"],
                "aspect": row["aspect"],
                "direct_terminal_ids": row["direct"],
                "indirect_terminal_ids": row["indirect"],
                "peak_power": row["peak"],
                "distance_arcmin": row["distance"],
            }
            for row in dated_fixture["relations"]
        ],
        "terminal_locations": [
            {"terminal_id": terminal_id, "sign": values[0], "house": values[1]}
            for terminal_id, values in dated_fixture["terminal_locations"].items()
        ],
        "house_cusp_signs": dated_fixture["house_cusp_signs"],
        "mutual_receptions": [
            {
                "allocation_id": row["id"],
                "body": row["body"],
                "direct_terminal_ids": row["direct"],
                "indirect_terminal_ids": row["indirect"],
                "harmony": row["harmony"],
            }
            for row in dated_fixture["mutual_receptions"]
        ],
    }
    return normal, practical


def _progressed_relation_payloads() -> tuple[dict, dict]:
    major = {
        "direct_a": {
            "body": "Sun",
            "kind": "major_progressed",
            "longitude_deg": 0,
            "house_class": "cadent",
        },
        "direct_b": {
            "body": "Moon",
            "kind": "radical",
            "longitude_deg": 45 + 4 / 60,
            "house_class": "succedent",
        },
        "counterpart_a": {
            "body": "Sun",
            "kind": "radical",
            "longitude_deg": 300,
            "house_class": "cadent",
        },
        "counterpart_b": {
            "body": "Moon",
            "kind": "major_progressed",
            "longitude_deg": 90,
            "house_class": "succedent",
        },
        "natal_a": {"body": "Sun", "power": 103.64, "harmony": 0, "discord": 21.65},
        "natal_b": {"body": "Moon", "power": 28.39, "harmony": 11.09, "discord": 0},
        "aspect": "semi-square",
    }
    minor = {
        "moving_terminal": {
            "body": "Neptune",
            "kind": "minor_progressed",
            "longitude_deg": (45 + 4 / 60 + 135 + 9 / 60) % 360,
            "house_class": "cadent",
        },
        "target_terminal": major["direct_b"],
        "target_counterpart": major["counterpart_b"],
        "natal_moving": {"body": "Neptune", "power": 35.04, "harmony": 18.71, "discord": 0},
        "natal_target": major["natal_b"],
        "aspect": "sesqui-square",
    }
    return major, minor


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
    assert (
        kernel_free_client.get("/v1/astrodynes/progressed/normal").status_code
        == 405
    )
    assert (
        kernel_free_client.get("/v1/astrodynes/progressed/chart").status_code
        == 405
    )
    assert kernel_free_client.get("/v1/astrodynes/progressed/search").status_code == 405
    assert kernel_free_client.get("/v1/astrodynes/progressed/integrate").status_code == 405


def test_progressed_doctrine_exposes_source_discrepancies_without_engine(
    kernel_free_client: TestClient,
) -> None:
    response = kernel_free_client.get("/v1/astrodynes/progressed/doctrine")

    assert response.status_code == 200
    body = response.json()
    assert body["doctrine"] == "church_of_light_progressed_astrodynes"
    assert body["parity_status"] == "doctrinal_parity_with_published_anomalies"
    assert body["kernel_required"] is False
    assert body["policy"]["major_carry_factor"] == 0.5
    assert body["policy"]["total_influence_average_factor"] == 0.75
    assert len(body["source_anomalies"]) == 9


def test_progressed_normal_and_practical_routes_reproduce_doctrinal_result(
    kernel_free_client: TestClient,
) -> None:
    normal_payload, practical_payload = _progressed_payloads()

    normal_response = kernel_free_client.post(
        "/v1/astrodynes/progressed/normal", json=normal_payload
    )
    assert normal_response.status_code == 200
    normal = normal_response.json()
    assert normal["checksums_pass"] is True
    assert normal["houses"][6]["total_power"] == 145.09

    practical_response = kernel_free_client.post(
        "/v1/astrodynes/progressed/practical", json=practical_payload
    )
    assert practical_response.status_code == 200
    practical = practical_response.json()
    assert len(practical["signs"]) == 12
    assert len(practical["houses"]) == 12
    assert practical["houses"][6]["total_power"] == 643.8
    assert practical["houses"][8]["total_power"] == 133.76
    assert len(practical["source_anomalies"]) == 9


def test_progressed_dated_aspect_and_total_influence_routes(
    kernel_free_client: TestClient,
) -> None:
    dated = kernel_free_client.post(
        "/v1/astrodynes/progressed/dated-aspect",
        json={
            "relation_id": "sun_moon",
            "body_a": "Sun",
            "body_b": "Moon",
            "aspect": "semi-square",
            "direct_terminal_ids": ["Sun:p", "Moon:r"],
            "indirect_terminal_ids": ["Sun:r", "Moon:p"],
            "peak_power": 16.51,
            "distance_arcmin": 4,
        },
    )
    assert dated.status_code == 200
    assert dated.json()["power"] == 15.96
    assert dated.json()["discord"] == 15.96

    influence = kernel_free_client.post(
        "/v1/astrodynes/progressed/total-influence",
        json={
            "peak_power": 14.37,
            "peak_harmony": 0,
            "peak_discord": 7.185,
            "duration": 36,
            "unit": "year",
        },
    )
    assert influence.status_code == 200
    assert influence.json()["manual_average_power"] == 10.78
    assert influence.json()["manual_total_power"] == 388.08


def test_progressed_relation_and_reenforcement_routes(
    kernel_free_client: TestClient,
) -> None:
    major_payload, minor_payload = _progressed_relation_payloads()

    major = kernel_free_client.post(
        "/v1/astrodynes/progressed/major-relation", json=major_payload
    )
    assert major.status_code == 200
    assert major.json()["manual_peak_power"] == 16.51
    assert major.json()["manual_power"] == 15.96
    assert major.json()["discord"] == 15.96

    minor = kernel_free_client.post(
        "/v1/astrodynes/progressed/accessory-relation", json=minor_payload
    )
    assert minor.status_code == 200
    assert minor.json()["tier"] == "minor"

    reenforcement = kernel_free_client.post(
        "/v1/astrodynes/progressed/reenforcement",
        json={"major": major_payload, "minor": minor_payload},
    )
    assert reenforcement.status_code == 200
    assert reenforcement.json()["target_is_direct"] is True
    assert reenforcement.json()["manual_reenforced_power"] == 19.65
    assert reenforcement.json()["discord_unchanged"] == 15.96


def test_progressed_compound_total_influence_route(
    kernel_free_client: TestClient,
) -> None:
    response = kernel_free_client.post(
        "/v1/astrodynes/progressed/compound-total-influence",
        json={
            "peak_power": 14.37,
            "peak_harmony": 0,
            "peak_discord": 7.185,
            "duration": {"years": 36, "months": 2, "days": 12},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["power"] == {"years": 390, "months": 2, "days": 25.38}
    assert body["discord"] == {"years": 195, "months": 1, "days": 12.69}


@pytest.mark.requires_ephemeris
def test_progressed_chart_route_derives_source_geometry_and_full_result(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrodynes/progressed/chart",
        json=_PROGRESSED_CHART_PAYLOAD,
    )

    assert response.status_code == 200
    body = response.json()
    time = body["geometry"]["time_truth"]
    assert time["limiting_date"] == pytest.approx(
        {"year": 1882, "month": 12, "day": 9.1416666667}
    )
    assert time["major_ephemeris_datetime"].startswith("1883-02-17T")
    assert time["minor_ephemeris_datetime"].startswith("1887-12-09T")

    major = {row["body"]: row for row in body["geometry"]["major_terminals"]}
    minor = {row["body"]: row for row in body["geometry"]["minor_terminals"]}
    transit = {row["body"]: row for row in body["geometry"]["transit_terminals"]}
    assert major["Sun"]["longitude_deg"] == pytest.approx(328.25, abs=0.02)
    assert minor["Moon"]["longitude_deg"] == pytest.approx(178.70, abs=0.02)
    assert minor["Mercury"]["longitude_deg"] == pytest.approx(236.583333, abs=0.02)
    assert minor["Neptune"]["longitude_deg"] == pytest.approx(58.166667, abs=0.02)
    assert transit["Neptune"]["longitude_deg"] == pytest.approx(193.516667, abs=0.02)

    assert len(body["normal"]["signs"]) == 12
    assert len(body["normal"]["houses"]) == 12
    assert body["major_relations"]
    assert body["minor_relations"]
    assert body["transit_relations"]
    assert body["reenforcements"]
    assert len(body["practical"]["signs"]) == 12
    assert len(body["practical"]["houses"]) == 12
    assert body["natal"]["validation_failures"] == []
    assert body["provenance"] == {
        "doctrine": "church_of_light_progressed_astrodynes",
        "engine_entrypoint": "Moira.progressed_astrodynes_chart",
        "kernel_required": True,
        "planetary_frame": "geocentric_apparent",
        "major_time_key": "limiting_date_day_for_year",
        "minor_time_key": "solar_constant_27.3_day_lunar_return",
        "angle_method": "sun_mc_constant_and_natal_latitude_horizon",
        "natal_house_frame": "progressed_terminals_assigned_to_natal_houses",
    }


@pytest.mark.requires_ephemeris
def test_progressed_search_and_variable_integration_routes(
    client_with_engine: TestClient,
) -> None:
    searched = client_with_engine.post(
        "/v1/astrodynes/progressed/search",
        json=_PROGRESSED_SEARCH_PAYLOAD,
    )
    assert searched.status_code == 200
    search = searched.json()
    assert search["provenance"] == (
        "church_of_light_one_degree_band_moira_bounded_search"
    )
    assert len(search["windows"]) == 1
    window = search["windows"][0]
    assert window["entry_clipped"] is False
    assert window["exit_clipped"] is False
    assert window["closest_approaches"][0]["event"] == "perfection"
    assert window["closest_approaches"][0]["distance_arcmin"] <= 0.01

    integrated = client_with_engine.post(
        "/v1/astrodynes/progressed/integrate",
        json={
            **_PROGRESSED_SEARCH_PAYLOAD,
            "start_dt": window["entry"]["dt"],
            "end_dt": window["exit"]["dt"],
            "max_step_hours": 0.25,
        },
    )
    assert integrated.status_code == 200
    influence = integrated.json()
    assert influence["method"] == "composite_trapezoid_actual_ephemeris"
    assert influence["total_power_days"] > 0.0
    assert influence["total_harmony_days"] == pytest.approx(
        influence["total_power_days"]
    )
    assert influence["total_discord_days"] == 0.0
    assert influence["constant_rate_comparator_power_days"] > 0.0


@pytest.mark.parametrize(
    "payload",
    (
        {**_PROGRESSED_CHART_PAYLOAD, "natal_dt": "1882-12-12T12:11:26"},
        {**_PROGRESSED_CHART_PAYLOAD, "target_dt": "1949-08-29T12:00:00"},
        {**_PROGRESSED_CHART_PAYLOAD, "target_dt": "1800-01-01T00:00:00Z"},
        {**_PROGRESSED_CHART_PAYLOAD, "observer_lat": 91},
        {**_PROGRESSED_CHART_PAYLOAD, "unexpected": True},
    ),
)
def test_progressed_chart_route_rejects_invalid_boundaries(
    kernel_free_client: TestClient,
    payload: dict,
) -> None:
    _assert_validation(
        kernel_free_client.post("/v1/astrodynes/progressed/chart", json=payload)
    )


@pytest.mark.parametrize(
    "path,payload,fragment",
    [
        (
            "/v1/astrodynes/progressed/dated-aspect",
            {
                "relation_id": "bad",
                "body_a": "Sun",
                "body_b": "Moon",
                "aspect": "semi-square",
                "direct_terminal_ids": ["Sun:p", "Moon:r"],
                "peak_power": 16.51,
                "distance_arcmin": 60.01,
            },
            "less than or equal to 60",
        ),
        (
            "/v1/astrodynes/progressed/total-influence",
            {
                "peak_power": "NaN",
                "peak_harmony": 0,
                "peak_discord": 0,
                "duration": 1,
                "unit": "year",
            },
            "greater than or equal to 0",
        ),
    ],
)
def test_progressed_routes_reject_invalid_values(
    kernel_free_client: TestClient,
    path: str,
    payload: dict,
    fragment: str,
) -> None:
    _assert_validation(kernel_free_client.post(path, json=payload), fragment)


def test_openapi_registers_strict_astrodynes_contracts(
    kernel_free_client: TestClient,
) -> None:
    schema = kernel_free_client.get("/openapi.json").json()
    assert set(path for path in schema["paths"] if path.startswith("/v1/astrodynes")) == {
        "/v1/astrodynes/doctrine",
        "/v1/astrodynes/geometry",
        "/v1/astrodynes/chart",
        "/v1/astrodynes/progressed/doctrine",
        "/v1/astrodynes/progressed/normal",
        "/v1/astrodynes/progressed/dated-aspect",
        "/v1/astrodynes/progressed/practical",
        "/v1/astrodynes/progressed/total-influence",
        "/v1/astrodynes/progressed/major-relation",
        "/v1/astrodynes/progressed/accessory-relation",
        "/v1/astrodynes/progressed/reenforcement",
        "/v1/astrodynes/progressed/compound-total-influence",
        "/v1/astrodynes/progressed/chart",
        "/v1/astrodynes/progressed/search",
        "/v1/astrodynes/progressed/integrate",
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
    assert schema["components"]["schemas"]["ProgressedPracticalRequest"][
        "additionalProperties"
    ] is False
    assert schema["components"]["schemas"]["ProgressedAstrodynesChartRequest"][
        "additionalProperties"
    ] is False
    assert schema["components"]["schemas"]["ProgressedContactSearchRequest"][
        "additionalProperties"
    ] is False
    assert schema["components"]["schemas"]["ProgressedInfluenceIntegrationRequest"][
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
