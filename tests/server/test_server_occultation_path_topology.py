"""REST contracts for detailed, polar-safe occultation path topology."""

from __future__ import annotations

from math import degrees, inf, nextafter
from typing import Any

from fastapi.testclient import TestClient
import pytest

from moira.constants import Body, EARTH_RADIUS_KM
from moira.julian import _ut1_to_utc, datetime_from_jd
from moira.occultations import (
    _OccultationPathNotPresentError,
    OccultationGeographicPole,
    OccultationPathBoundaryPoint,
    OccultationPathBoundarySide,
    OccultationPathBoundaryTrack,
    OccultationPathGeometry,
    OccultationPathPoint,
    OccultationPathTopology,
    OccultationPathTopologyKind,
    OccultationPoleCrossing,
    OccultationPoleCrossingPhase,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback

_WGS84_FLATTENING = 1.0 / 298.257223563
_MIN_TOPOLOGY_OBSERVER_ELEV_M = (
    -EARTH_RADIUS_KM * (1.0 - _WGS84_FLATTENING) * 1000.0
)


def _topology(
    occulted_body: str,
    *,
    target_model: str,
    observer_elevation_m: float = 123.5,
) -> OccultationPathTopology:
    greatest_jd = 2_451_545.0
    epochs = tuple(greatest_jd + (index - 4) * 0.001 for index in range(9))
    centers = tuple(
        OccultationPathPoint(
            jd_ut=jd_ut,
            latitude_deg=87.0 + index * 0.2,
            longitude_deg=170.0 + index * 4.0,
            separation_deg=0.08,
            clearance_deg=0.0 if index in {0, 8} else 0.12,
        )
        for index, jd_ut in enumerate(epochs)
    )

    def boundary_points(
        side: OccultationPathBoundarySide,
        latitude_offset: float,
        distance_km: float,
    ) -> tuple[OccultationPathBoundaryPoint, ...]:
        points = []
        for index, center in enumerate(centers):
            if index in {0, len(centers) - 1}:
                points.append(
                    OccultationPathBoundaryPoint(
                        side=side,
                        point=center,
                        cross_track_distance_km=0.0,
                    )
                )
                continue
            points.append(
                OccultationPathBoundaryPoint(
                    side=side,
                    point=OccultationPathPoint(
                        jd_ut=center.jd_ut,
                        latitude_deg=center.latitude_deg + latitude_offset,
                        longitude_deg=center.longitude_deg,
                        separation_deg=0.2,
                        clearance_deg=0.0,
                    ),
                    cross_track_distance_km=distance_km,
                )
            )
        return tuple(points)

    left_points = boundary_points(
        OccultationPathBoundarySide.LEFT,
        degrees(55.0 / EARTH_RADIUS_KM),
        55.0,
    )
    right_points = boundary_points(
        OccultationPathBoundarySide.RIGHT,
        -degrees(65.0 / EARTH_RADIUS_KM),
        65.0,
    )
    summary = OccultationPathGeometry(
        occulting_body=Body.MOON,
        occulted_body=occulted_body,
        jd_greatest_ut=greatest_jd,
        central_line_lats=tuple(point.latitude_deg for point in centers),
        central_line_lons=tuple(point.longitude_deg for point in centers),
        path_width_km=120.0,
        duration_at_greatest_s=600.0,
    )
    pole_crossings = tuple(
        OccultationPoleCrossing(
            pole=OccultationGeographicPole.NORTH,
            phase=phase,
            point=OccultationPathPoint(
                jd_ut=greatest_jd + offset,
                latitude_deg=90.0,
                longitude_deg=123.0,
                separation_deg=0.2,
                clearance_deg=0.0,
            ),
            boundary_side=side,
        )
        for phase, offset, side in (
            (
                OccultationPoleCrossingPhase.INGRESS,
                -0.0005,
                OccultationPathBoundarySide.LEFT,
            ),
            (
                OccultationPoleCrossingPhase.EGRESS,
                0.0005,
                OccultationPathBoundarySide.RIGHT,
            ),
        )
    )
    return OccultationPathTopology(
        summary=summary,
        topology=OccultationPathTopologyKind.TWO_SIDED_BAND,
        centers=centers,
        boundaries=(
            OccultationPathBoundaryTrack(
                side=OccultationPathBoundarySide.LEFT,
                points=left_points,
            ),
            OccultationPathBoundaryTrack(
                side=OccultationPathBoundarySide.RIGHT,
                points=right_points,
            ),
        ),
        greatest_left=left_points[4],
        greatest_right=right_points[4],
        pole_crossings=pole_crossings,
        lunar_limb_model="SPHERICAL_MEAN_LIMB",
        target_model=target_model,
        observer_elevation_m=observer_elevation_m,
    )


class _FakeFacade:
    def __init__(self) -> None:
        self.planet = _topology(Body.MARS, target_model="JPL_EQUATORIAL_SOLID_BODY")
        self.star = _topology("Aldebaran", target_model="POINT_SOURCE")
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def lunar_occultation_path_topology(self, *args: Any, **kwargs: Any):
        self.calls.append(("planet_search", args, kwargs))
        return [self.planet]

    def lunar_occultation_path_topology_at(self, *args: Any, **kwargs: Any):
        self.calls.append(("planet_at", args, kwargs))
        return self.planet

    def lunar_star_occultation_path_topology(self, *args: Any, **kwargs: Any):
        self.calls.append(("star_search", args, kwargs))
        return [self.star]

    def lunar_star_occultation_path_topology_at(self, *args: Any, **kwargs: Any):
        self.calls.append(("star_at", args, kwargs))
        return self.star


@pytest.fixture
def client_and_engine(monkeypatch: pytest.MonkeyPatch):
    engine = _FakeFacade()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine


def _assert_topology_payload(payload: dict[str, Any], target_model: str) -> None:
    assert payload["topology"] == "two_sided_band"
    assert len(payload["centers"]) == 9
    assert [track["side"] for track in payload["boundaries"]] == [
        "left",
        "right",
    ]
    assert payload["summary"]["path_width_km"] == 120.0
    assert payload["greatest_left"]["cross_track_distance_km"] == 55.0
    assert payload["greatest_right"]["cross_track_distance_km"] == 65.0
    assert [crossing["pole"] for crossing in payload["pole_crossings"]] == [
        "north",
        "north",
    ]
    assert [crossing["phase"] for crossing in payload["pole_crossings"]] == [
        "ingress",
        "egress",
    ]
    assert [crossing["boundary_side"] for crossing in payload["pole_crossings"]] == [
        "left",
        "right",
    ]
    assert [crossing["point"]["longitude_deg"] for crossing in payload["pole_crossings"]] == [
        0.0,
        0.0,
    ]
    assert payload["target_model"] == target_model
    assert payload["lunar_limb_model"] == "SPHERICAL_MEAN_LIMB"
    assert payload["observer_elevation_m"] == 123.5
    assert payload["observer_geometry"] == "WGS84_GEODETIC"
    assert payload["width_metric"] == "SPHERICAL_GREAT_CIRCLE_R6378_137_KM"
    assert payload["time_scale"] == "UT1"
    assert payload["atmospheric_refraction"] is False
    assert payload["saturn_rings_included"] is False


def test_all_topology_routes_delegate_to_facade_and_serialize_full_truth(
    client_and_engine,
) -> None:
    client, engine = client_and_engine
    planet_search = client.post(
        "/v1/occultations/lunar-path-topology",
        json={
            "target": Body.MARS,
            "jd_start": 2_451_544.0,
            "jd_end": 2_451_546.0,
            "observer_elev_m": 123.5,
        },
    )
    planet_at = client.post(
        "/v1/occultations/lunar-path-topology-at",
        json={
            "target": Body.MARS,
            "jd_mid": 2_451_545.0,
            "observer_elev_m": 123.5,
        },
    )
    star_search = client.post(
        "/v1/occultations/lunar-star-path-topology",
        json={
            "star_lon": 69.0,
            "star_lat": -5.5,
            "star_name": "Aldebaran",
            "jd_start": 2_451_544.0,
            "jd_end": 2_451_546.0,
            "observer_elev_m": 123.5,
        },
    )
    star_at = client.post(
        "/v1/occultations/lunar-star-path-topology-at",
        json={
            "star_lon": 69.0,
            "star_lat": -5.5,
            "star_name": "Aldebaran",
            "jd_mid": 2_451_545.0,
            "observer_elev_m": 123.5,
        },
    )

    for response in (planet_search, planet_at, star_search, star_at):
        assert response.status_code == 200, response.text
    _assert_topology_payload(
        planet_search.json()["events"][0],
        "JPL_EQUATORIAL_SOLID_BODY",
    )
    _assert_topology_payload(planet_at.json(), "JPL_EQUATORIAL_SOLID_BODY")
    _assert_topology_payload(star_search.json()["events"][0], "POINT_SOURCE")
    _assert_topology_payload(star_at.json(), "POINT_SOURCE")

    assert [call[0] for call in engine.calls] == [
        "planet_search",
        "planet_at",
        "star_search",
        "star_at",
    ]
    assert all(call[2]["sample_count"] == 65 for call in engine.calls)
    assert all(call[2]["observer_elev_m"] == 123.5 for call in engine.calls)

    planet_payload = planet_at.json()
    expected_greatest_utc = datetime_from_jd(
        _ut1_to_utc(engine.planet.summary.jd_greatest_ut)
    ).isoformat()
    expected_center_utc = datetime_from_jd(
        _ut1_to_utc(engine.planet.centers[0].jd_ut)
    ).isoformat()
    assert planet_payload["summary"]["greatest_datetime_utc"] == expected_greatest_utc
    assert planet_payload["centers"][0]["datetime_utc"] == expected_center_utc
    assert planet_payload["summary"]["greatest_datetime_utc"] != datetime_from_jd(
        engine.planet.summary.jd_greatest_ut
    ).isoformat()


@pytest.mark.parametrize("sample_count", [True, 8, 722, 65.0])
def test_topology_route_rejects_non_integer_or_out_of_range_samples(
    client_and_engine,
    sample_count: object,
) -> None:
    client, engine = client_and_engine
    response = client.post(
        "/v1/occultations/lunar-path-topology-at",
        json={
            "target": Body.MARS,
            "jd_mid": 2_451_545.0,
            "sample_count": sample_count,
        },
    )

    assert response.status_code == 422
    assert engine.calls == []


@pytest.mark.parametrize(
    "payload",
    [
        {"star_lon": 69.0, "star_lat": 90.1, "star_name": "Aldebaran"},
        {"star_lon": 69.0, "star_lat": -5.5, "star_name": "   "},
        {"star_lon": 69.0, "star_lat": -5.5, "star_name": " Aldebaran "},
        {"star_lon": 69.0, "star_lat": -5.5, "star_name": "Sun"},
        {
            "star_lon": 69.0,
            "star_lat": -5.5,
            "star_name": "Aldebaran",
            "unknown": 1,
        },
    ],
)
def test_star_topology_route_rejects_invalid_or_extra_input(
    client_and_engine,
    payload: dict[str, Any],
) -> None:
    client, engine = client_and_engine
    response = client.post(
        "/v1/occultations/lunar-star-path-topology-at",
        json={**payload, "jd_mid": 2_451_545.0},
    )

    assert response.status_code == 422
    assert engine.calls == []


def test_topology_routes_enforce_the_wgs84_elevation_floor(
    client_and_engine,
) -> None:
    client, engine = client_and_engine
    below_floor = nextafter(_MIN_TOPOLOGY_OBSERVER_ELEV_M, -inf)

    rejected = client.post(
        "/v1/occultations/lunar-path-topology-at",
        json={
            "target": Body.MARS,
            "jd_mid": 2_451_545.0,
            "observer_elev_m": below_floor,
        },
    )
    assert rejected.status_code == 422
    assert engine.calls == []

    admitted = client.post(
        "/v1/occultations/lunar-path-topology-at",
        json={
            "target": Body.MARS,
            "jd_mid": 2_451_545.0,
            "observer_elev_m": _MIN_TOPOLOGY_OBSERVER_ELEV_M,
        },
    )
    assert admitted.status_code == 200
    assert engine.calls[-1][2]["observer_elev_m"] == pytest.approx(
        _MIN_TOPOLOGY_OBSERVER_ELEV_M,
        abs=1.0e-9,
    )


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/v1/occultations/lunar-path-topology-at",
            {"target": Body.SUN, "jd_mid": 2_451_545.0},
        ),
        (
            "/v1/occultations/lunar-path-topology",
            {
                "target": Body.SUN,
                "jd_start": 2_451_544.0,
                "jd_end": 2_451_545.0,
            },
        ),
    ],
)
def test_planetary_topology_routes_exclude_the_sun(
    client_and_engine,
    path: str,
    payload: dict[str, Any],
) -> None:
    client, engine = client_and_engine
    response = client.post(path, json=payload)

    assert response.status_code == 422
    assert "use the eclipse routes for the Sun" in response.json()["message"]
    assert engine.calls == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"step_days": 0.2500001},
        {"jd_end": 2_451_945.000001},
        {"step_days": 0.0002},
        {"step_days": 5e-324},
        {"jd_end": 2_451_544.0},
    ],
)
def test_topology_search_route_rejects_out_of_policy_scan_work(
    client_and_engine,
    overrides: dict[str, Any],
) -> None:
    client, engine = client_and_engine
    payload = {
        "target": Body.MARS,
        "jd_start": 2_451_544.0,
        "jd_end": 2_451_545.0,
        **overrides,
    }
    response = client.post(
        "/v1/occultations/lunar-path-topology",
        json=payload,
    )

    assert response.status_code == 422
    assert engine.calls == []


def test_star_topology_search_route_enforces_the_same_scan_budget(
    client_and_engine,
) -> None:
    client, engine = client_and_engine
    response = client.post(
        "/v1/occultations/lunar-star-path-topology",
        json={
            "star_lon": 69.0,
            "star_lat": -5.5,
            "star_name": "Aldebaran",
            "jd_start": 2_451_544.0,
            "jd_end": 2_451_545.0,
            "step_days": 0.0002,
        },
    )

    assert response.status_code == 422
    assert engine.calls == []


def test_topology_search_route_rejects_nonadvancing_binary64_lattice(
    client_and_engine,
) -> None:
    client, engine = client_and_engine
    start = 2_451_545.0
    end = nextafter(start, inf)
    response = client.post(
        "/v1/occultations/lunar-path-topology",
        json={
            "target": Body.MARS,
            "jd_start": start,
            "jd_end": end,
            "step_days": (end - start) / 2.0,
        },
    )

    assert response.status_code == 422
    assert "strictly advancing" in response.json()["message"]
    assert engine.calls == []


def test_expected_topology_absence_is_a_domain_validation_response(
    client_and_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = client_and_engine

    def absent(*args: Any, **kwargs: Any):
        raise _OccultationPathNotPresentError(
            "no occultation is present at the supplied greatest epoch"
        )

    monkeypatch.setattr(engine, "lunar_occultation_path_topology_at", absent)
    response = client.post(
        "/v1/occultations/lunar-path-topology-at",
        json={"target": Body.MARS, "jd_mid": 2_451_545.0},
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert "no occultation" in response.json()["message"]


def test_openapi_admits_new_topology_routes_without_replacing_legacy_paths() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    paths = schema["paths"]
    assert {
        "/v1/occultations/lunar-path",
        "/v1/occultations/lunar-path-at",
        "/v1/occultations/lunar-star-path",
        "/v1/occultations/lunar-star-path-at",
        "/v1/occultations/lunar-path-topology",
        "/v1/occultations/lunar-path-topology-at",
        "/v1/occultations/lunar-star-path-topology",
        "/v1/occultations/lunar-star-path-topology-at",
    } <= set(paths)

    legacy_contracts = {
        "/v1/occultations/lunar-path": (
            "LunarOccultationPathRequest",
            "OccultationPathSearchResponse",
        ),
        "/v1/occultations/lunar-path-at": (
            "LunarOccultationPathAtRequest",
            "OccultationPathGeometryResponse",
        ),
        "/v1/occultations/lunar-star-path": (
            "LunarStarOccultationPathRequest",
            "OccultationPathSearchResponse",
        ),
        "/v1/occultations/lunar-star-path-at": (
            "LunarStarOccultationPathAtRequest",
            "OccultationPathGeometryResponse",
        ),
    }
    for path, (request_name, response_name) in legacy_contracts.items():
        operation = paths[path]["post"]
        assert operation["requestBody"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{request_name}"
        }
        assert operation["responses"]["200"]["content"]["application/json"][
            "schema"
        ] == {"$ref": f"#/components/schemas/{response_name}"}

    components = schema["components"]["schemas"]
    request = components["LunarOccultationPathTopologyRequest"]
    assert request["properties"]["sample_count"] == {
        "type": "integer",
        "maximum": 721.0,
        "minimum": 9.0,
        "title": "Sample Count",
        "default": 65,
    }
    assert request["properties"]["step_days"] == {
        "type": "number",
        "exclusiveMinimum": 0.0,
        "maximum": 0.25,
        "title": "Step Days",
        "default": 0.25,
    }
    response = components["OccultationPathTopologyResponse"]
    assert {
        "summary",
        "topology",
        "centers",
        "boundaries",
        "greatest_left",
        "greatest_right",
        "pole_crossings",
        "lunar_limb_model",
        "target_model",
        "observer_elevation_m",
        "observer_geometry",
        "width_metric",
        "time_scale",
        "atmospheric_refraction",
        "saturn_rings_included",
    } == set(response["properties"])
    assert response["properties"]["lunar_limb_model"]["const"] == (
        "SPHERICAL_MEAN_LIMB"
    )
    assert request["properties"]["observer_elev_m"]["minimum"] == pytest.approx(
        _MIN_TOPOLOGY_OBSERVER_ELEV_M,
        abs=1.0e-9,
    )
    assert response["properties"]["observer_elevation_m"] == {
        "type": "number",
        "minimum": pytest.approx(_MIN_TOPOLOGY_OBSERVER_ELEV_M, abs=1.0e-9),
        "title": "Observer Elevation M",
    }
