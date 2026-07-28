"""P10-01 Astrocartography route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.astrocartography import acg_lines, subplanetary_points
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.astrocartography import (
    AstrocartographyChartLinesRequest,
    AstrocartographyChartSubplanetaryRequest,
    AstrocartographySubjectChartLinesRequest,
    AstrocartographySubjectChartSubplanetaryRequest,
    AstrocartographySubjectRequest,
)
from moira_server.serializers.astrocartography import (
    serialize_astrocartography_lines,
    serialize_astrocartography_subplanetary,
)
from moira_server.services.astrocartography import (
    compute_astrocartography_chart_lines,
    compute_astrocartography_chart_subplanetary,
    compute_astrocartography_subject_chart_lines,
    compute_astrocartography_subject_chart_subplanetary,
    _physical_subject_identity,
)


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


_DT_ISO = "2000-01-01T12:00:00Z"
_DIRECT_POSITIONS = {
    "Sun": {"right_ascension": 100.0, "declination": 10.0},
}
_DIRECT_RA_DEC = {"Sun": (100.0, 10.0)}
_NON_PLANET_DIRECT_POSITIONS = {
    "Ceres": {"right_ascension": 101.0, "declination": 11.0},
    "Halley": {"right_ascension": 202.0, "declination": -12.0},
    "Sirius": {"right_ascension": 303.0, "declination": -16.0},
}
_NON_PLANET_DIRECT_RA_DEC = {
    body: (position["right_ascension"], position["declination"])
    for body, position in _NON_PLANET_DIRECT_POSITIONS.items()
}


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def _line_map(lines: list[dict]) -> dict[tuple[str, str], dict]:
    return {(line["planet"], line["line_type"]): line for line in lines}


def _point_map(points: list[dict]) -> dict[tuple[str, str], dict]:
    return {(point["planet"], point["point_type"]): point for point in points}


def _subject_map(provenance: dict) -> dict[str, dict]:
    return {
        subject["returned_label"]: subject
        for subject in provenance["subjects"]
    }


def test_explicit_subject_family_disambiguates_halley_identity() -> None:
    asteroid = _physical_subject_identity(
        AstrocartographySubjectRequest(kind="asteroid", name="Halley")
    )
    comet = _physical_subject_identity(
        AstrocartographySubjectRequest(kind="comet", name="Halley")
    )

    assert asteroid == ("asteroid", "Halley", 2_002_688)
    assert comet == ("comet", "1P/Halley", 1_000_001)


def test_astrocartography_direct_lines_route_matches_engine_truth(
    client_with_engine: TestClient,
) -> None:
    expected = acg_lines(_DIRECT_RA_DEC, 20.0, lat_step=10.0, refraction=False)

    response = client_with_engine.post(
        "/v1/astrocartography/lines",
        json={
            "positions": _DIRECT_POSITIONS,
            "gmst_deg": 20.0,
            "lat_step": 10.0,
            "refraction": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    lines = _line_map(body["lines"])
    expected_lines = {(line.planet, line.line_type): line for line in expected}
    assert set(lines) == set(expected_lines)
    assert lines[("Sun", "MC")]["longitude"] == pytest.approx(
        expected_lines[("Sun", "MC")].longitude
    )
    assert lines[("Sun", "IC")]["longitude"] == pytest.approx(
        expected_lines[("Sun", "IC")].longitude
    )
    assert len(lines[("Sun", "ASC")]["points"]) == len(expected_lines[("Sun", "ASC")].points)
    assert lines[("Sun", "ASC")]["points"][0]["latitude"] == pytest.approx(
        expected_lines[("Sun", "ASC")].points[0][0]
    )
    assert lines[("Sun", "ASC")]["points"][0]["longitude"] == pytest.approx(
        expected_lines[("Sun", "ASC")].points[0][1]
    )
    provenance = body["provenance"]
    assert provenance["coordinate_source"] == "direct_ra_dec"
    assert provenance["returned_bodies"] == ["Sun"]
    assert provenance["observer"]["source"] == "direct_none"
    assert _subject_map(provenance)["Sun"]["subject_class"] == "caller_supplied"
    assert _subject_map(provenance)["Sun"]["position_source"] == "caller_supplied_direct_ra_dec"
    assert provenance["lat_step"] == 10.0
    assert provenance["refraction"] is False
    assert provenance["stage_sequence"][0] == "direct_ra_dec_validation"


def test_astrocartography_direct_subplanetary_route_matches_engine_truth(
    client_with_engine: TestClient,
) -> None:
    expected = subplanetary_points(_DIRECT_RA_DEC, 20.0)

    response = client_with_engine.post(
        "/v1/astrocartography/subplanetary",
        json={"positions": _DIRECT_POSITIONS, "gmst_deg": 20.0},
    )

    assert response.status_code == 200
    body = response.json()
    points = _point_map(body["points"])
    expected_points = {(point.planet, point.point_type): point for point in expected}
    assert set(points) == set(expected_points)
    assert points[("Sun", "Zenith")]["latitude"] == pytest.approx(
        expected_points[("Sun", "Zenith")].latitude
    )
    assert points[("Sun", "Zenith")]["longitude"] == pytest.approx(
        expected_points[("Sun", "Zenith")].longitude
    )
    provenance = body["provenance"]
    assert provenance["coordinate_source"] == "direct_ra_dec"
    assert provenance["observer"]["source"] == "direct_none"
    assert _subject_map(provenance)["Sun"]["subject_class"] == "caller_supplied"
    assert provenance["stage_sequence"][0] == "direct_ra_dec_validation"


def test_astrocartography_direct_lines_accepts_selected_non_planet_labels(
    client_with_engine: TestClient,
) -> None:
    expected = acg_lines(
        _NON_PLANET_DIRECT_RA_DEC,
        20.0,
        lat_step=10.0,
        refraction=False,
    )

    response = client_with_engine.post(
        "/v1/astrocartography/lines",
        json={
            "positions": _NON_PLANET_DIRECT_POSITIONS,
            "gmst_deg": 20.0,
            "lat_step": 10.0,
            "refraction": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    expected_keys = {(line.planet, line.line_type) for line in expected}
    assert set(_line_map(body["lines"])) == expected_keys
    assert len(body["lines"]) == 12
    provenance = body["provenance"]
    assert provenance["coordinate_source"] == "direct_ra_dec"
    assert provenance["requested_bodies"] == ["Ceres", "Halley", "Sirius"]
    assert provenance["returned_bodies"] == ["Ceres", "Halley", "Sirius"]
    subjects = _subject_map(provenance)
    assert set(subjects) == {"Ceres", "Halley", "Sirius"}
    assert all(subject["subject_class"] == "caller_supplied" for subject in subjects.values())
    assert all(
        subject["position_source"] == "caller_supplied_direct_ra_dec"
        for subject in subjects.values()
    )


def test_astrocartography_direct_subplanetary_accepts_selected_non_planet_labels(
    client_with_engine: TestClient,
) -> None:
    expected = subplanetary_points(_NON_PLANET_DIRECT_RA_DEC, 20.0)

    response = client_with_engine.post(
        "/v1/astrocartography/subplanetary",
        json={"positions": _NON_PLANET_DIRECT_POSITIONS, "gmst_deg": 20.0},
    )

    assert response.status_code == 200
    body = response.json()
    expected_keys = {(point.planet, point.point_type) for point in expected}
    assert set(_point_map(body["points"])) == expected_keys
    assert len(body["points"]) == 6
    provenance = body["provenance"]
    assert provenance["coordinate_source"] == "direct_ra_dec"
    assert provenance["returned_bodies"] == ["Ceres", "Halley", "Sirius"]
    subjects = _subject_map(provenance)
    assert all(subject["subject_class"] == "caller_supplied" for subject in subjects.values())


@pytest.mark.requires_ephemeris
def test_astrocartography_chart_lines_route_matches_service_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {
        "dt": _DT_ISO,
        "bodies": ["Sun"],
        "observer_lat": 40.7128,
        "observer_lon": -74.0060,
        "lat_step": 10.0,
    }
    expected = serialize_astrocartography_lines(
        compute_astrocartography_chart_lines(
            moira_engine,
            AstrocartographyChartLinesRequest.model_validate(payload),
        )
    ).model_dump(mode="json")

    response = client_with_engine.post("/v1/astrocartography/chart/lines", json=payload)

    assert response.status_code == 200
    assert response.json() == expected
    provenance = response.json()["provenance"]
    assert provenance["coordinate_source"] == "chart_apparent_topocentric_ra_dec"
    assert provenance["observer"]["source"] == "chart_request"
    assert provenance["returned_bodies"] == ["Sun"]
    subject = _subject_map(provenance)["Sun"]
    assert subject["subject_class"] == "planet"
    assert subject["canonical_name"] == "Sun"
    assert subject["position_source"] == "moira.planets.sky_position_at:planet"


@pytest.mark.requires_ephemeris
def test_astrocartography_chart_subplanetary_route_matches_service_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {"dt": _DT_ISO, "bodies": ["Sun"]}
    expected = serialize_astrocartography_subplanetary(
        compute_astrocartography_chart_subplanetary(
            moira_engine,
            AstrocartographyChartSubplanetaryRequest.model_validate(payload),
        )
    ).model_dump(mode="json")

    response = client_with_engine.post(
        "/v1/astrocartography/chart/subplanetary",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == expected
    provenance = response.json()["provenance"]
    assert provenance["coordinate_source"] == "chart_geocentric_ecliptic_to_equatorial"
    assert provenance["observer"]["source"] == "direct_none"
    assert provenance["returned_bodies"] == ["Sun"]
    subject = _subject_map(provenance)["Sun"]
    assert subject["subject_class"] == "planet"
    assert subject["position_source"] == "moira.planets.planet_at:planet"


@pytest.mark.requires_ephemeris
def test_astrocartography_chart_lines_preserves_selected_asteroid_provenance(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/lines",
        json={
            "dt": _DT_ISO,
            "bodies": ["Ceres"],
            "observer_lat": 40.7128,
            "observer_lon": -74.0060,
            "lat_step": 10.0,
        },
    )

    assert response.status_code == 200
    body_json = response.json()
    assert len(body_json["lines"]) == 4
    provenance = body_json["provenance"]
    assert provenance["coordinate_source"] == "chart_apparent_topocentric_ra_dec"
    assert provenance["returned_bodies"] == ["Ceres"]
    subject = _subject_map(provenance)["Ceres"]
    assert subject["subject_class"] == "asteroid"
    assert subject["canonical_name"] == "Ceres"
    assert subject["naif_id"] == 2000001
    assert subject["position_source"] == "moira.planets.sky_position_at:asteroid"


@pytest.mark.requires_ephemeris
def test_astrocartography_chart_lines_defer_comet_topocentric_ra_dec_path(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/lines",
        json={
            "dt": _DT_ISO,
            "bodies": ["1P/Halley"],
            "observer_lat": 40.7128,
            "observer_lon": -74.0060,
            "lat_step": 10.0,
        },
    )

    _assert_validation_envelope(
        response,
        message_fragment="comet bodies currently support only the default apparent geocentric ecliptic path",
    )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("body", "subject_class", "canonical_name", "naif_id"),
    [
        ("Ceres", "asteroid", "Ceres", 2000001),
        ("1P/Halley", "comet", "1P/Halley", 1000001),
    ],
)
def test_astrocartography_chart_subplanetary_preserves_selected_minor_body_provenance(
    client_with_engine: TestClient,
    body: str,
    subject_class: str,
    canonical_name: str,
    naif_id: int,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/subplanetary",
        json={"dt": _DT_ISO, "bodies": [body]},
    )

    assert response.status_code == 200
    body_json = response.json()
    assert len(body_json["points"]) == 2
    provenance = body_json["provenance"]
    assert provenance["coordinate_source"] == "chart_geocentric_ecliptic_to_equatorial"
    assert provenance["returned_bodies"] == [body]
    subject = _subject_map(provenance)[body]
    assert subject["subject_class"] == subject_class
    assert subject["canonical_name"] == canonical_name
    assert subject["naif_id"] == naif_id
    assert subject["position_source"] == f"moira.planets.planet_at:{subject_class}"


@pytest.mark.requires_ephemeris
def test_astrocartography_subject_chart_lines_accepts_mixed_subjects(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {
        "dt": _DT_ISO,
        "observer_lat": 40.7128,
        "observer_lon": -74.0060,
        "lat_step": 10.0,
        "subjects": [
            {"kind": "planet", "name": "Sun"},
            {"kind": "asteroid", "name": "Ceres"},
            {"kind": "comet", "name": "Halley"},
            {"kind": "fixed_star", "name": "Sirius"},
            {"kind": "lot", "name": "Fortune"},
            {
                "kind": "ecliptic_point",
                "label": "Custom Ecliptic",
                "longitude": 123.45,
                "latitude": 0.0,
            },
            {
                "kind": "ra_dec_point",
                "label": "Manual RA/Dec",
                "right_ascension": 210.0,
                "declination": -12.0,
            },
        ],
    }
    expected = serialize_astrocartography_lines(
        compute_astrocartography_subject_chart_lines(
            moira_engine,
            AstrocartographySubjectChartLinesRequest.model_validate(payload),
        )
    ).model_dump(mode="json")

    response = client_with_engine.post(
        "/v1/astrocartography/chart/subjects/lines",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == expected
    body_json = response.json()
    assert len(body_json["lines"]) == 28
    provenance = body_json["provenance"]
    assert provenance["coordinate_source"] == "chart_mixed_subject_ra_dec"
    assert provenance["observer"]["source"] == "chart_request"
    assert provenance["returned_bodies"] == [
        "Sun",
        "Ceres",
        "Halley",
        "Sirius",
        "Fortune",
        "Custom Ecliptic",
        "Manual RA/Dec",
    ]
    subjects = _subject_map(provenance)
    assert subjects["Sun"]["subject_class"] == "planet"
    assert subjects["Sun"]["position_source"] == "moira.planets.sky_position_at:planet"
    assert subjects["Ceres"]["subject_class"] == "asteroid"
    assert subjects["Ceres"]["naif_id"] == 2000001
    assert subjects["Halley"]["subject_class"] == "comet"
    assert subjects["Halley"]["canonical_name"] == "1P/Halley"
    assert subjects["Halley"]["naif_id"] == 1000001
    assert subjects["Halley"]["position_source"] == "moira.planets.planet_at:comet:ecliptic_to_equatorial"
    assert subjects["Sirius"]["subject_class"] == "fixed_star"
    assert subjects["Sirius"]["position_source"] == "moira.stars.star_at:ecliptic_to_equatorial"
    assert subjects["Fortune"]["subject_class"] == "lot"
    assert subjects["Fortune"]["position_source"] == "moira.lots.calculate_parts:ecliptic_point_to_equatorial"
    assert subjects["Custom Ecliptic"]["subject_class"] == "ecliptic_point"
    assert subjects["Manual RA/Dec"]["subject_class"] == "ra_dec_point"


def test_astrocartography_chart_rejects_ambiguous_unqualified_small_body(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/subplanetary",
        json={"dt": _DT_ISO, "bodies": ["Halley"]},
    )

    _assert_validation_envelope(
        response,
        message_fragment="small-body name 'Halley' is ambiguous across families",
    )
    message = response.json()["message"]
    assert "asteroid:Halley" in message
    assert "comet:Halley" in message


@pytest.mark.requires_ephemeris
def test_astrocartography_subject_chart_subplanetary_accepts_mixed_subjects(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {
        "dt": _DT_ISO,
        "observer_lat": 40.7128,
        "observer_lon": -74.0060,
        "subjects": [
            {"kind": "planet", "name": "Sun"},
            {"kind": "fixed_star", "name": "Sirius"},
            {"kind": "lot", "name": "Spirit"},
        ],
    }
    expected = serialize_astrocartography_subplanetary(
        compute_astrocartography_subject_chart_subplanetary(
            moira_engine,
            AstrocartographySubjectChartSubplanetaryRequest.model_validate(payload),
        )
    ).model_dump(mode="json")

    response = client_with_engine.post(
        "/v1/astrocartography/chart/subjects/subplanetary",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == expected
    body_json = response.json()
    assert len(body_json["points"]) == 6
    provenance = body_json["provenance"]
    assert provenance["coordinate_source"] == "chart_mixed_subject_ra_dec"
    assert provenance["observer"]["source"] == "direct_none"
    subjects = _subject_map(provenance)
    assert subjects["Sun"]["position_source"] == "moira.planets.planet_at:planet:ecliptic_to_equatorial"
    assert subjects["Sirius"]["subject_class"] == "fixed_star"
    assert subjects["Spirit"]["subject_class"] == "lot"


def test_astrocartography_routes_are_registered(client_with_engine: TestClient) -> None:
    paths = {
        route.path
        for route in client_with_engine.app.routes
        if route.path.startswith("/v1/astrocartography")
    }

    assert paths == {
        "/v1/astrocartography/lines",
        "/v1/astrocartography/chart/lines",
        "/v1/astrocartography/subplanetary",
        "/v1/astrocartography/chart/subplanetary",
        "/v1/astrocartography/chart/subjects/lines",
        "/v1/astrocartography/chart/subjects/subplanetary",
    }


def test_astrocartography_direct_lines_rejects_invalid_lat_step(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/lines",
        json={
            "positions": _DIRECT_POSITIONS,
            "gmst_deg": 20.0,
            "lat_step": 0.1,
        },
    )

    _assert_validation_envelope(response, message_fragment="greater than or equal to 0.5")


def test_astrocartography_direct_lines_rejects_invalid_declination(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/lines",
        json={
            "positions": {
                "Sun": {"right_ascension": 100.0, "declination": 91.0},
            },
            "gmst_deg": 20.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="declination")


def test_astrocartography_direct_lines_rejects_empty_subject_label(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/lines",
        json={
            "positions": {
                "": {"right_ascension": 100.0, "declination": 10.0},
            },
            "gmst_deg": 20.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="positions keys must be non-empty")


def test_astrocartography_direct_lines_rejects_too_many_subject_labels(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/lines",
        json={
            "positions": {
                f"Subject{i}": {"right_ascension": 100.0, "declination": 10.0}
                for i in range(13)
            },
            "gmst_deg": 20.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="at most 12")


def test_astrocartography_direct_lines_rejects_non_finite_jd_ut(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/lines",
        json={
            "positions": _DIRECT_POSITIONS,
            "gmst_deg": 20.0,
            "jd_ut": "NaN",
        },
    )

    _assert_validation_envelope(response, message_fragment="gmst_deg and jd_ut")


def test_astrocartography_direct_subplanetary_rejects_non_finite_gmst(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/subplanetary",
        json={"positions": _DIRECT_POSITIONS, "gmst_deg": "NaN"},
    )

    _assert_validation_envelope(response, message_fragment="gmst_deg")


def test_astrocartography_chart_route_rejects_naive_datetime(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/lines",
        json={"dt": "2000-01-01T12:00:00", "bodies": ["Sun"]},
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_astrocartography_chart_route_rejects_unsupported_body(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/lines",
        json={"dt": _DT_ISO, "bodies": ["NotAPlanet"]},
    )

    _assert_validation_envelope(response, message_fragment="unsupported chart bodies")


def test_astrocartography_chart_route_rejects_fixed_star_as_chart_body(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/lines",
        json={"dt": _DT_ISO, "bodies": ["Sirius"]},
    )

    _assert_validation_envelope(response, message_fragment="unsupported chart bodies")


def test_astrocartography_chart_subplanetary_rejects_fixed_star_as_chart_body(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/subplanetary",
        json={"dt": _DT_ISO, "bodies": ["Sirius"]},
    )

    _assert_validation_envelope(response, message_fragment="unsupported chart bodies")


def test_astrocartography_chart_route_rejects_partial_observer(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/lines",
        json={"dt": _DT_ISO, "bodies": ["Sun"], "observer_lat": 40.0},
    )

    _assert_validation_envelope(response, message_fragment="observer_lat and observer_lon")


def test_astrocartography_chart_route_rejects_partial_acg_observer_override(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/lines",
        json={"dt": _DT_ISO, "bodies": ["Sun"], "acg_observer_lat": 40.0},
    )

    _assert_validation_envelope(response, message_fragment="acg observer override")


def test_astrocartography_chart_route_rejects_too_many_bodies(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/lines",
        json={
            "dt": _DT_ISO,
            "bodies": [f"Body{i}" for i in range(13)],
        },
    )

    _assert_validation_envelope(response, message_fragment="at most 12")


def test_astrocartography_subject_chart_route_rejects_lot_without_observer(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/subjects/lines",
        json={
            "dt": _DT_ISO,
            "subjects": [{"kind": "lot", "name": "Fortune"}],
        },
    )

    _assert_validation_envelope(
        response,
        message_fragment="lot subjects require observer_lat and observer_lon",
    )


def test_astrocartography_subject_chart_route_rejects_duplicate_labels(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/subjects/lines",
        json={
            "dt": _DT_ISO,
            "subjects": [
                {"kind": "planet", "name": "Sun", "label": "Duplicate"},
                {"kind": "ra_dec_point", "label": "Duplicate", "right_ascension": 1.0, "declination": 2.0},
            ],
        },
    )

    _assert_validation_envelope(
        response,
        message_fragment="astrocartography subject labels must be unique",
    )


def test_astrocartography_subject_chart_route_rejects_incomplete_ra_dec_subject(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/astrocartography/chart/subjects/lines",
        json={
            "dt": _DT_ISO,
            "subjects": [
                {"kind": "ra_dec_point", "label": "Manual", "right_ascension": 1.0},
            ],
        },
    )

    _assert_validation_envelope(
        response,
        message_fragment="ra_dec_point subjects require right_ascension and declination",
    )
