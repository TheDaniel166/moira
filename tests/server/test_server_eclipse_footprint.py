"""Kernel-free REST and facade contracts for solar visibility footprints."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

import moira.facade as facade_module
from moira._facade_special import SpecialTopicsFacadeMixin
from moira.eclipse import (
    EclipseData,
    EclipseEvent,
    EclipseType,
    SolarEclipseFootprintBoundaryKind,
    SolarEclipseFootprintContacts,
    SolarEclipseFootprintPoint,
    SolarEclipseFootprintTopology,
    SolarEclipseLimitTrack,
    SolarEclipsePenumbralContact,
    SolarEclipsePenumbralContactKind,
    SolarEclipseVisibilityFootprint,
)
from moira.julian import julian_day
from moira_server.app import create_app
from moira_server.config import ServerConfig
import moira_server.models as public_models
import moira_server.models.phenomena as phenomena_models
from moira_server.models.phenomena import (
    SolarEclipseFootprintPointResponse,
    SolarEclipseFootprintRequest,
    SolarEclipseLimitTrackResponse,
    SolarEclipseVisibilityFootprintResponse,
)
import moira_server.serializers as public_serializers
import moira_server.serializers.phenomena as phenomena_serializers
from moira_server.serializers.phenomena import (
    serialize_solar_eclipse_footprint,
    serialize_solar_eclipse_footprint_point,
)
import moira_server.services as public_services
import moira_server.services.phenomena as phenomena_services


pytestmark = pytest.mark.loopback


_P1_JD = 2_451_544.80
_P2_JD = 2_451_544.90
_GREATEST_JD = 2_451_545.00
_P3_JD = 2_451_545.10
_P4_JD = 2_451_545.20


def _point(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
) -> SolarEclipseFootprintPoint:
    return SolarEclipseFootprintPoint(
        jd_ut=jd_ut,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
    )


def _contact(
    kind: SolarEclipsePenumbralContactKind,
    point: SolarEclipseFootprintPoint,
) -> SolarEclipsePenumbralContact:
    return SolarEclipsePenumbralContact(kind=kind, point=point)


def test_footprint_point_serializer_is_bce_safe() -> None:
    point = _point(julian_day(-100, 6, 15), 0.0, 0.0)

    serialized = serialize_solar_eclipse_footprint_point(point)

    assert serialized.datetime_utc.startswith("-0100-")


def test_footprint_public_server_packages_reexport_complete_surface() -> None:
    model_names = (
        "SolarEclipseSearchKind",
        "SolarEclipseFootprintBoundaryKindValue",
        "SolarEclipsePenumbralContactKindValue",
        "SolarEclipseFootprintTopologyValue",
        "SolarEclipseFootprintRequest",
        "SolarEclipseFootprintPointResponse",
        "SolarEclipsePenumbralContactResponse",
        "SolarEclipseFootprintContactsResponse",
        "SolarEclipseLimitTrackResponse",
        "SolarEclipseVisibilityFootprintResponse",
    )
    serializer_names = (
        "serialize_solar_eclipse_footprint",
        "serialize_solar_eclipse_footprint_contacts",
        "serialize_solar_eclipse_footprint_point",
        "serialize_solar_eclipse_limit_track",
        "serialize_solar_eclipse_penumbral_contact",
    )

    for name in model_names:
        assert name in public_models.__all__
        assert getattr(public_models, name) is getattr(phenomena_models, name)
    for name in serializer_names:
        assert name in public_serializers.__all__
        assert getattr(public_serializers, name) is getattr(
            phenomena_serializers,
            name,
        )
    assert "compute_solar_eclipse_footprint" in public_services.__all__
    assert (
        public_services.compute_solar_eclipse_footprint
        is phenomena_services.compute_solar_eclipse_footprint
    )


def _event() -> EclipseEvent:
    eclipse_type = EclipseType(
        is_partial=False,
        is_annular=False,
        is_total=True,
        is_hybrid=False,
        magnitude_umbral=1.031,
        magnitude_penumbra=2.105,
    )
    data = EclipseData(
        sun_longitude=280.25,
        moon_longitude=280.20,
        node_longitude=125.0,
        galactic_center_longitude=266.4,
        moon_latitude=0.12,
        sun_apparent_radius=0.271,
        moon_apparent_radius=0.280,
        moon_distance_km=360_000.0,
        earth_shadow_apparent_radius=0.0,
        earth_penumbra_apparent_radius=0.0,
        sun_stone=1,
        moon_stone=2,
        node_stone=3,
        south_node_stone=31,
        angular_separation_3d=0.13,
        solar_topocentric_separation=0.10,
        sun_node_distance=0.25,
        is_eclipse_season=True,
        is_solar_eclipse=True,
        is_lunar_eclipse=False,
        eclipse_type=eclipse_type,
        eclipse_magnitude=1.031,
        saros_index=42.5,
        metonic_year=7.25,
        metonic_is_reset=False,
        moon_parallax=1.01,
        sun_side=2,
        sun_pos_in_side=4,
    )
    return EclipseEvent(jd_ut=_GREATEST_JD, data=data)


def _footprint() -> SolarEclipseVisibilityFootprint:
    p1 = _point(_P1_JD, -14.4, -22.1)
    p2 = _point(_P2_JD, 27.5, -56.7)
    p3 = _point(_P3_JD, 84.4, 149.7)
    p4 = _point(_P4_JD, 43.4, 83.0)
    south_start = _point(2_451_544.84, -37.8, -33.0)
    north_start = _point(2_451_544.85, 38.5, -54.4)
    north_end = _point(2_451_545.15, 82.7, -99.3)
    south_end = _point(2_451_545.16, 20.2, 93.6)
    tracks = (
        SolarEclipseLimitTrack(
            kind=SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
            component_id=0,
            segment_id=0,
            points=(north_start, north_end),
        ),
        SolarEclipseLimitTrack(
            kind=SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
            component_id=0,
            segment_id=0,
            points=(south_start, south_end),
        ),
        SolarEclipseLimitTrack(
            kind=SolarEclipseFootprintBoundaryKind.SUNRISE,
            component_id=0,
            segment_id=0,
            points=(p1, south_start, north_start, p2),
        ),
        SolarEclipseLimitTrack(
            kind=SolarEclipseFootprintBoundaryKind.SUNSET,
            component_id=0,
            segment_id=0,
            points=(p3, north_end, south_end, p4),
        ),
    )
    return SolarEclipseVisibilityFootprint(
        event=_event(),
        greatest=_point(_GREATEST_JD, 23.25, 16.75),
        topology=SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP,
        contacts=SolarEclipseFootprintContacts(
            p1=_contact(SolarEclipsePenumbralContactKind.P1, p1),
            p2=_contact(SolarEclipsePenumbralContactKind.P2, p2),
            p3=_contact(SolarEclipsePenumbralContactKind.P3, p3),
            p4=_contact(SolarEclipsePenumbralContactKind.P4, p4),
        ),
        tracks=tracks,
        ephemeris="DE-0441LE-0441",
    )


class _FakeFacade:
    def __init__(self, result: SolarEclipseVisibilityFootprint) -> None:
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def solar_eclipse_footprint(
        self,
        jd_start: float,
        *,
        kind: str,
        backward: bool,
        sample_count: int,
    ) -> SolarEclipseVisibilityFootprint:
        self.calls.append(
            {
                "jd_start": jd_start,
                "kind": kind,
                "backward": backward,
                "sample_count": sample_count,
            }
        )
        return self.result


class _ForbiddenCalculator:
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise AssertionError(
            "the REST footprint service must delegate to the Moira facade"
        )


@pytest.fixture
def client_facade_and_result(monkeypatch: pytest.MonkeyPatch):
    result = _footprint()
    engine = _FakeFacade(result)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    monkeypatch.setattr(
        "moira_server.services.phenomena.EclipseCalculator",
        _ForbiddenCalculator,
    )
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine, result


def _serialized_point(point: SolarEclipseFootprintPoint) -> dict[str, Any]:
    return {
        "jd_ut": point.jd_ut,
        "datetime_utc": point.datetime_utc.isoformat(),
        "latitude_deg": point.latitude_deg,
        "longitude_deg": point.longitude_deg,
    }


def _serialized_contact(contact: SolarEclipsePenumbralContact) -> dict[str, Any]:
    return {
        "kind": contact.kind.value,
        "point": _serialized_point(contact.point),
    }


def test_footprint_route_delegates_to_facade_and_serializes_full_vessel(
    client_facade_and_result,
) -> None:
    client, engine, result = client_facade_and_result

    response = client.post(
        "/v1/eclipses/solar/footprint",
        json={
            "jd_start": 2_451_500.5,
            "kind": "total",
            "backward": True,
        },
    )

    assert response.status_code == 200
    assert engine.calls == [
        {
            "jd_start": 2_451_500.5,
            "kind": "total",
            "backward": True,
            "sample_count": 181,
        }
    ]
    assert result.contacts.p2 is not None
    assert result.contacts.p3 is not None
    assert response.json() == {
        "event": {
            "jd_ut": result.event.jd_ut,
            "datetime_utc": result.event.datetime_utc.isoformat(),
            "data": {
                "eclipse_type": "Total",
                "is_eclipse_season": True,
                "is_solar_eclipse": True,
                "is_lunar_eclipse": False,
                "eclipse_magnitude": 1.031,
                "sun_longitude": 280.25,
                "moon_longitude": 280.2,
                "node_longitude": 125.0,
                "moon_latitude": 0.12,
                "sun_node_distance": 0.25,
                "angular_separation_3d": 0.13,
                "saros_index": 42.5,
                "metonic_year": 7.25,
                "metonic_is_reset": False,
            },
        },
        "greatest": _serialized_point(result.greatest),
        "topology": "two_limit_two_loop",
        "contacts": {
            "p1": _serialized_contact(result.contacts.p1),
            "p2": _serialized_contact(result.contacts.p2),
            "p3": _serialized_contact(result.contacts.p3),
            "p4": _serialized_contact(result.contacts.p4),
        },
        "tracks": [
            {
                "kind": track.kind.value,
                "component_id": track.component_id,
                "segment_id": track.segment_id,
                "points": [_serialized_point(point) for point in track.points],
            }
            for track in result.tracks
        ],
        "ephemeris": "DE-0441LE-0441",
        "surface_model": "WGS84_ZERO_ELEVATION",
        "limb_model": "SPHERICAL_MEAN_LIMB",
        "time_scale": "UT1",
        "atmospheric_refraction": False,
    }


@pytest.mark.parametrize("sample_count", [8, 722])
def test_footprint_route_rejects_sample_count_outside_public_bounds(
    client_facade_and_result,
    sample_count: int,
) -> None:
    client, engine, _ = client_facade_and_result

    response = client.post(
        "/v1/eclipses/solar/footprint",
        json={"jd_start": 2_451_500.5, "sample_count": sample_count},
    )

    assert response.status_code == 422
    assert engine.calls == []


@pytest.mark.parametrize("sample_count", [9, 721])
def test_footprint_route_admits_sample_count_boundary_values(
    client_facade_and_result,
    sample_count: int,
) -> None:
    client, engine, _ = client_facade_and_result

    response = client.post(
        "/v1/eclipses/solar/footprint",
        json={"jd_start": 2_451_500.5, "sample_count": sample_count},
    )

    assert response.status_code == 200
    assert engine.calls[0]["sample_count"] == sample_count


@pytest.mark.parametrize(
    "jd_start",
    [True, "2451500.5", float("nan"), float("inf"), float("-inf")],
)
def test_footprint_request_rejects_coercible_or_nonfinite_epochs(
    jd_start: object,
) -> None:
    with pytest.raises(ValidationError):
        SolarEclipseFootprintRequest(jd_start=jd_start)


@pytest.mark.parametrize("jd_start", [2_451_500, 2_451_500.5])
def test_footprint_request_preserves_integer_and_float_epoch_inputs(
    jd_start: int | float,
) -> None:
    request = SolarEclipseFootprintRequest(jd_start=jd_start)

    assert request.jd_start == float(jd_start)


@pytest.mark.parametrize("backward", [0, 1, "false", "true"])
def test_footprint_request_rejects_coercible_non_boolean_direction(
    backward: object,
) -> None:
    with pytest.raises(ValidationError):
        SolarEclipseFootprintRequest(
            jd_start=2_451_500.5,
            backward=backward,
        )


@pytest.mark.parametrize("sample_count", [True, 9.0, "9"])
def test_footprint_request_rejects_coercible_non_integer_sample_counts(
    sample_count: object,
) -> None:
    with pytest.raises(ValidationError):
        SolarEclipseFootprintRequest(
            jd_start=2_451_500.5,
            sample_count=sample_count,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("jd_ut", float("nan")),
        ("jd_ut", 40_000_001.0),
        ("latitude_deg", -90.01),
        ("latitude_deg", float("inf")),
        ("longitude_deg", 180.01),
        ("longitude_deg", float("-inf")),
    ],
)
def test_footprint_point_response_enforces_finite_geographic_epoch_bounds(
    field: str,
    value: float,
) -> None:
    payload: dict[str, object] = {
        "jd_ut": 2_451_545.0,
        "datetime_utc": "2000-01-01T12:00:00+00:00",
        "latitude_deg": 0.0,
        "longitude_deg": 0.0,
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        SolarEclipseFootprintPointResponse.model_validate(payload)


def test_footprint_response_enforces_track_collection_minimums_and_metadata() -> None:
    serialized = serialize_solar_eclipse_footprint(_footprint()).model_dump()

    invalid_track = dict(serialized["tracks"][0])
    invalid_track["points"] = invalid_track["points"][:1]
    with pytest.raises(ValidationError):
        SolarEclipseLimitTrackResponse.model_validate(invalid_track)

    too_few_tracks = dict(serialized)
    too_few_tracks["tracks"] = too_few_tracks["tracks"][:2]
    with pytest.raises(ValidationError):
        SolarEclipseVisibilityFootprintResponse.model_validate(too_few_tracks)

    fixed_metadata = {
        "ephemeris": "DE-0441LE-0441",
        "surface_model": "WGS84_ZERO_ELEVATION",
        "limb_model": "SPHERICAL_MEAN_LIMB",
        "time_scale": "UT1",
        "atmospheric_refraction": False,
    }
    for field, admitted_value in fixed_metadata.items():
        invalid = dict(serialized)
        invalid[field] = not admitted_value if isinstance(admitted_value, bool) else "other"
        with pytest.raises(ValidationError):
            SolarEclipseVisibilityFootprintResponse.model_validate(invalid)


def test_footprint_openapi_is_typed_bounded_and_preserves_path_route() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    paths = schema["paths"]

    assert set(paths["/v1/eclipses/solar/footprint"]) == {"post"}
    footprint_operation = paths["/v1/eclipses/solar/footprint"]["post"]
    assert footprint_operation["requestBody"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/SolarEclipseFootprintRequest"}
    assert footprint_operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {
        "$ref": "#/components/schemas/SolarEclipseVisibilityFootprintResponse"
    }

    sample_schema = schema["components"]["schemas"][
        "SolarEclipseFootprintRequest"
    ]["properties"]["sample_count"]
    assert sample_schema["default"] == 181
    assert sample_schema["minimum"] == 9
    assert sample_schema["maximum"] == 721
    assert sample_schema["type"] == "integer"
    jd_start_schema = schema["components"]["schemas"][
        "SolarEclipseFootprintRequest"
    ]["properties"]["jd_start"]
    assert jd_start_schema["minimum"] == -40_000_000.0
    assert jd_start_schema["maximum"] == 40_000_000.0
    assert jd_start_schema["type"] == "number"
    assert schema["components"]["schemas"]["SolarEclipseFootprintRequest"][
        "properties"
    ]["kind"]["enum"] == [
        "any",
        "total",
        "annular",
        "partial",
        "central",
        "hybrid",
    ]

    track_schema = schema["components"]["schemas"][
        "SolarEclipseLimitTrackResponse"
    ]
    assert "component_id" in track_schema["required"]
    assert track_schema["properties"]["component_id"] == {
        "minimum": 0,
        "title": "Component Id",
        "type": "integer",
    }
    assert "segment_id" in track_schema["required"]
    assert track_schema["properties"]["segment_id"] == {
        "minimum": 0,
        "title": "Segment Id",
        "type": "integer",
    }
    assert track_schema["properties"]["kind"]["enum"] == [
        "penumbral_north",
        "penumbral_south",
        "sunrise",
        "sunset",
    ]
    assert track_schema["properties"]["points"]["minItems"] == 2
    point_schema = schema["components"]["schemas"][
        "SolarEclipseFootprintPointResponse"
    ]["properties"]
    assert point_schema["jd_ut"]["minimum"] == -40_000_000.0
    assert point_schema["jd_ut"]["maximum"] == 40_000_000.0
    assert point_schema["latitude_deg"]["minimum"] == -90.0
    assert point_schema["latitude_deg"]["maximum"] == 90.0
    assert point_schema["longitude_deg"]["minimum"] == -180.0
    assert point_schema["longitude_deg"]["maximum"] == 180.0
    footprint_schema = schema["components"]["schemas"][
        "SolarEclipseVisibilityFootprintResponse"
    ]
    assert footprint_schema["properties"]["tracks"]["minItems"] == 3
    assert footprint_schema["properties"]["topology"]["enum"] == [
        "one_limit_connected",
        "two_limit_two_loop",
    ]
    assert (
        footprint_schema["properties"]["ephemeris"]["const"]
        == "DE-0441LE-0441"
    )
    assert (
        footprint_schema["properties"]["surface_model"]["const"]
        == "WGS84_ZERO_ELEVATION"
    )
    assert (
        footprint_schema["properties"]["limb_model"]["const"]
        == "SPHERICAL_MEAN_LIMB"
    )
    assert footprint_schema["properties"]["time_scale"]["const"] == "UT1"
    assert footprint_schema["properties"]["atmospheric_refraction"]["const"] is False
    contact_schema = schema["components"]["schemas"][
        "SolarEclipsePenumbralContactResponse"
    ]
    assert contact_schema["properties"]["kind"]["enum"] == [
        "p1",
        "p2",
        "p3",
        "p4",
    ]

    assert set(paths["/v1/eclipses/solar/path"]) == {"post"}
    path_operation = paths["/v1/eclipses/solar/path"]["post"]
    assert path_operation["requestBody"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/SolarEclipsePathRequest"}
    assert path_operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/SolarEclipsePathResponse"}
    assert schema["components"]["schemas"]["SolarEclipsePathRequest"][
        "properties"
    ]["sample_count"]["default"] == 9


def test_public_facade_delegates_footprint_with_bound_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel_reader = object()
    sentinel_result = object()
    calls: list[dict[str, Any]] = []

    class _SpyCalculator:
        def __init__(self, *, reader: object) -> None:
            calls.append({"reader": reader})

        def solar_eclipse_footprint(
            self,
            jd_start: float,
            *,
            kind: str,
            backward: bool,
            sample_count: int,
        ) -> object:
            calls.append(
                {
                    "jd_start": jd_start,
                    "kind": kind,
                    "backward": backward,
                    "sample_count": sample_count,
                }
            )
            return sentinel_result

    class _FacadeHost(SpecialTopicsFacadeMixin):
        _reader = sentinel_reader

    monkeypatch.setattr(facade_module, "EclipseCalculator", _SpyCalculator)

    actual = _FacadeHost().solar_eclipse_footprint(
        2_451_500.5,
        kind="annular",
        backward=True,
        sample_count=99,
    )

    assert actual is sentinel_result
    assert calls == [
        {"reader": sentinel_reader},
        {
            "jd_start": 2_451_500.5,
            "kind": "annular",
            "backward": True,
            "sample_count": 99,
        },
    ]
