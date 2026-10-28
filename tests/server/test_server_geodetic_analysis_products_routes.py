"""P10-03b Geodetic analysis routes: overlay, compare, loci, chart houses.

Governing object: docs/architecture/P10-03B_GEODETIC_ANALYSIS_TRANSPORT_DESIGN.md.
Direct routes compose the owners on caller-supplied tropical longitudes and a
declared frame; chart-backed routes call the Moira facade with the server
engine's reader. Neither adds doctrine.

Evidence classes (design record section 6):
- parity: route JSON == the owner (direct) or facade (chart-backed) result
  through the same serializer, plus field checks against the engine objects
  so the serializers themselves are witnessed;
- adversarial: lane law, every declared bound, strict models, duplicate ids;
- isolation: compare isolates failing places; body failures are collected
  only on request and are then visible;
- structural: direct routes never touch the engine; chart-backed routes work
  with no global kernel; the pinned route set.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.aspects import AspectPolicy
from moira.constants import HouseSystem
from moira.geodetic import GeodeticLocation
from moira.geodetic_analysis import (
    GeodeticNamedLocation,
    compare_geodetic_locations,
    geodetic_house_chart,
    geodetic_natal_overlay,
)
from moira.geodetic_curves import GeodeticCurvePolicy, geodetic_angular_loci
from moira.geodetic_inputs import geodetic_snapshot_from_positions
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.geodetic import (
    serialize_geodetic_chart_houses,
    serialize_geodetic_compare,
    serialize_geodetic_loci,
    serialize_geodetic_overlay,
)

pytestmark = pytest.mark.loopback

NATAL_ISO = "2000-01-01T12:00:00Z"
NATAL = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
BODIES = ["Sun", "Moon", "Mars", "Venus"]
PLACE = {"geo_latitude": 40.7, "geo_longitude": -74.0}
NEW_YORK = GeodeticLocation(40.7, -74.0)
LONGITUDES = {"Sun": 280.37, "Moon": 223.32, "Mars": 327.96, "Venus": 241.57}
FRAME = "caller_declared_geocentric_ecliptic"
DIRECT = {"longitudes": LONGITUDES, "source_frame": FRAME, "obliquity": 23.44}
ASPECTS = {"aspect_policy": {"tier": 0}}
POLICY = AspectPolicy(tier=0, orb_factor=1.0)
PLACES = [
    {"location_id": "ny", **PLACE, "display_name": "New York"},
    {"location_id": "ldn", "geo_latitude": 51.5, "geo_longitude": -0.1},
    {"location_id": "north", "geo_latitude": 80.0, "geo_longitude": 10.0},
]


def _places():
    return [GeodeticNamedLocation(p["location_id"], GeodeticLocation(p["geo_latitude"], p["geo_longitude"]),
                                  p.get("display_name")) for p in PLACES]


def _snapshot(zodiac="tropical", offset=None):
    return geodetic_snapshot_from_positions(LONGITUDES, source_frame=FRAME, zodiac=zodiac, ayanamsa_deg=offset)


class _NoEngine:
    def __getattr__(self, name: str):
        raise AssertionError(f"direct Geodetic route touched engine.{name}")


@pytest.fixture
def direct_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _NoEngine())
    with TestClient(create_app(ServerConfig(docs_enabled=False)), raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def engine_client(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False)), raise_server_exceptions=False) as client:
        yield client


def _post(client: TestClient, path: str, body: dict, status: int = 200) -> dict:
    response = client.post(f"/v1/geodetic/{path}", json=body)
    assert response.status_code == status, response.text
    return response.json()


# -- Direct routes: parity with the owners ------------------------------------

@pytest.mark.parametrize("lane", [{}, {"zodiac": "sidereal", "ayanamsa_deg": 23.85}], ids=["tropical", "sidereal"])
@pytest.mark.parametrize("system", [HouseSystem.PLACIDUS, HouseSystem.EQUAL, HouseSystem.WHOLE_SIGN])
def test_direct_overlay_matches_owner(direct_client, lane, system) -> None:
    body = _post(direct_client, "overlay", {**DIRECT, **lane, **PLACE, "system": system, **ASPECTS, "include_cusps": True})
    zodiac, offset = lane.get("zodiac", "tropical"), lane.get("ayanamsa_deg")
    figure = geodetic_house_chart(NEW_YORK, obliquity=23.44, system=system, zodiac=zodiac, ayanamsa_deg=offset,
                                  source_frame=FRAME)
    expected = geodetic_natal_overlay(figure, _snapshot(zodiac, offset), aspect_policy=POLICY, include_cusps=True)
    assert body == serialize_geodetic_overlay(expected).model_dump(mode="json")
    # Serializer witness against the engine objects.
    assert [p["house"] for p in body["overlay"]["placements"]] == [p.placement.house for p in expected.placements]
    assert [(c["body1"], c["body2"], c["aspect"]) for c in body["overlay"]["contacts"]] == [
        (c.body1, c.body2, c.aspect) for c in expected.contacts]
    assert all(c["applying"] is None for c in body["overlay"]["contacts"])
    assert body["overlay"]["figure"]["houses"]["cusps"] == list(figure.houses.cusps)
    assert body["snapshot"]["ayanamsa_deg"] == (offset or 0.0)


def test_direct_compare_matches_owner_and_isolates_failing_places(direct_client) -> None:
    body = _post(direct_client, "compare", {**DIRECT, "system": HouseSystem.PLACIDUS, **ASPECTS, "places": PLACES})
    expected = compare_geodetic_locations(_places(), _snapshot(), obliquity=23.44, system=HouseSystem.PLACIDUS,
                                          aspect_policy=POLICY, error_policy="collect")
    assert body == serialize_geodetic_compare(expected).model_dump(mode="json")
    by_id = {r["place"]["location_id"]: r for r in body["results"]}
    assert by_id["ny"]["overlay"] is not None and by_id["ny"]["failure_type"] is None
    assert by_id["north"]["overlay"] is None and by_id["north"]["reason"]  # strict polar Placidus
    assert body["complete"] is False
    assert by_id["ny"]["place"]["display_name"] == "New York"


def test_direct_compare_raise_policy_refuses_the_whole_request(direct_client) -> None:
    _post(direct_client, "compare", {**DIRECT, "system": HouseSystem.PLACIDUS, **ASPECTS, "places": PLACES,
                                     "place_error_policy": "raise"}, status=422)


def test_direct_loci_match_owner(direct_client) -> None:
    body = _post(direct_client, "loci", {**DIRECT, "angles": ["MC", "ASC"], "curve_policy": {"latitude_step_deg": 5}})
    expected = geodetic_angular_loci(_snapshot(), obliquity=23.44, angles=("MC", "ASC"),
                                     policy=GeodeticCurvePolicy(latitude_step_deg=5))
    assert body == serialize_geodetic_loci(expected).model_dump(mode="json")
    assert body["complete"] is True
    assert body["semantics"] == expected.semantics
    first = expected.loci[0].segments[0][0]
    assert body["loci"][0]["segments"][0][0]["longitude_deg"] == first.longitude_deg


# -- Chart-backed routes: parity with the facade -------------------------------

@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("lane", [{}, {"zodiac": "sidereal", "ayanamsa_system": "Lahiri"}], ids=["tropical", "sidereal"])
def test_chart_houses_match_facade(engine_client, moira_engine, lane) -> None:
    body = _post(engine_client, "chart/houses", {"dt": NATAL_ISO, **PLACE, "system": HouseSystem.PLACIDUS, **lane})
    expected = moira_engine.geodetic_houses(NEW_YORK, NATAL, HouseSystem.PLACIDUS, zodiac=lane.get("zodiac", "tropical"),
                                            ayanamsa_system=lane.get("ayanamsa_system"))
    assert body == serialize_geodetic_chart_houses(expected).model_dump(mode="json")


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("lane", [{}, {"zodiac": "sidereal", "ayanamsa_system": "Lahiri"}], ids=["tropical", "sidereal"])
def test_chart_overlay_matches_facade(engine_client, moira_engine, lane) -> None:
    body = _post(engine_client, "chart/overlay", {"dt": NATAL_ISO, "bodies": BODIES, **PLACE,
                                                  "system": HouseSystem.EQUAL, **ASPECTS, **lane})
    expected = moira_engine.geodetic_overlay(NATAL, NEW_YORK, HouseSystem.EQUAL, aspect_policy=POLICY, bodies=BODIES,
                                             zodiac=lane.get("zodiac", "tropical"), ayanamsa_system=lane.get("ayanamsa_system"))
    assert body == serialize_geodetic_overlay(expected).model_dump(mode="json")
    assert body["snapshot"]["ayanamsa_system"] == lane.get("ayanamsa_system")
    assert body["snapshot"]["jd_tt"] == body["overlay"]["figure"]["jd_tt"]


@pytest.mark.requires_ephemeris
def test_chart_compare_matches_facade(engine_client, moira_engine) -> None:
    body = _post(engine_client, "chart/compare", {"dt": NATAL_ISO, "bodies": BODIES, "system": HouseSystem.PLACIDUS,
                                                  **ASPECTS, "places": PLACES})
    expected = moira_engine.geodetic_compare(NATAL, _places(), HouseSystem.PLACIDUS, aspect_policy=POLICY, bodies=BODIES,
                                             place_error_policy="collect")
    assert body == serialize_geodetic_compare(expected).model_dump(mode="json")


@pytest.mark.requires_ephemeris
def test_chart_loci_match_facade(engine_client, moira_engine) -> None:
    body = _post(engine_client, "chart/loci", {"dt": NATAL_ISO, "bodies": BODIES})
    expected = moira_engine.geodetic_loci(NATAL, bodies=BODIES, curve_policy=GeodeticCurvePolicy())
    assert body == serialize_geodetic_loci(expected).model_dump(mode="json")
    assert body["complete"] is True


@pytest.mark.requires_ephemeris
def test_body_failures_are_collected_only_on_request(engine_client) -> None:
    base = {"dt": NATAL_ISO, "bodies": ["Sun", "asteroid:Definitely Not A Body"]}
    _post(engine_client, "chart/loci", base, status=422)
    body = _post(engine_client, "chart/loci", {**base, "body_error_policy": "collect"})
    assert body["snapshot"]["complete"] is False
    assert [f["requested_name"] for f in body["snapshot"]["failures"]] == ["asteroid:Definitely Not A Body"]
    assert [p["body_id"] for p in body["snapshot"]["positions"]] == ["Sun"]


@pytest.mark.requires_ephemeris
def test_chart_backed_routes_work_without_a_global_kernel(moira_engine, monkeypatch: pytest.MonkeyPatch) -> None:
    import moira.spk_reader as spk_reader

    monkeypatch.setattr(spk_reader, "_reader", None)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with spk_reader.use_reader_override(None):
        with TestClient(create_app(ServerConfig()), raise_server_exceptions=False) as client:
            for path, body in [
                ("chart/houses", {"dt": NATAL_ISO, **PLACE, "system": HouseSystem.EQUAL}),
                ("chart/overlay", {"dt": NATAL_ISO, "bodies": BODIES, **PLACE, "system": HouseSystem.EQUAL, **ASPECTS}),
                ("chart/compare", {"dt": NATAL_ISO, "bodies": BODIES, "system": HouseSystem.EQUAL, **ASPECTS, "places": PLACES[:2]}),
                ("chart/loci", {"dt": NATAL_ISO, "bodies": BODIES}),
            ]:
                assert client.post(f"/v1/geodetic/{path}", json=body).status_code == 200, path


# -- Admission ---------------------------------------------------------------

@pytest.mark.parametrize("path,body,fragment", [
    ("overlay", {**DIRECT, **PLACE, "system": "E", **ASPECTS, "ayanamsa_deg": 0.0}, "tropical zodiac must not carry"),
    ("overlay", {**DIRECT, **PLACE, "system": "E", **ASPECTS, "zodiac": "sidereal"}, "sidereal zodiac requires"),
    ("overlay", {**DIRECT, **PLACE, "system": "E"}, "aspect_policy"),
    ("overlay", {**DIRECT, **PLACE, "system": "E", **ASPECTS, "angles": ["MC", "MC"]}, "unique"),
    ("overlay", {**DIRECT, **PLACE, "system": "E", **ASPECTS, "angles": ["Vertex"]}, "angles"),
    ("overlay", {**DIRECT, **PLACE, "system": "E", "aspect_policy": {"tier": 3}}, "tier"),
    ("overlay", {**DIRECT, **PLACE, "system": "E", "aspect_policy": {"orb_factor": 11}}, "orb_factor"),
    ("overlay", {**DIRECT, "geo_latitude": 90.0, "geo_longitude": 0.0, "system": "E", **ASPECTS}, "geo_latitude"),
    ("overlay", {**DIRECT, "obliquity": 30.0, **PLACE, "system": "E", **ASPECTS}, "Earth obliquity"),
    ("overlay", {**DIRECT, "longitudes": {f"B{i}": float(i) for i in range(13)}, **PLACE, "system": "E", **ASPECTS}, "at most 12"),
    ("overlay", {**DIRECT, **PLACE, "system": "E", **ASPECTS, "unexpected": 1}, "Extra inputs"),
    ("compare", {**DIRECT, "system": "E", **ASPECTS, "places": []}, "places"),
    ("compare", {**DIRECT, "system": "E", **ASPECTS,
                 "places": [{"location_id": f"p{i}", **PLACE} for i in range(25)]}, "places"),
    ("compare", {**DIRECT, "system": "E", **ASPECTS, "places": [PLACES[0], PLACES[0]]}, "unique"),
    ("compare", {**DIRECT, "system": "E", **ASPECTS,
                 "places": [{"location_id": "bad id", **PLACE}]}, "location_id"),
    ("compare", {**DIRECT, "system": "E", **ASPECTS, "places": PLACES, "order_by": "best"}, "order_by"),
    ("loci", {**DIRECT, "curve_policy": {"latitude_step_deg": 0.25}}, "latitude_step_deg"),
    ("loci", {**DIRECT, "curve_policy": {"max_evaluations": 20001}}, "max_evaluations"),
    ("loci", {**DIRECT, "curve_policy": {"round_trip_tolerance_deg": 0.01}}, "round_trip_tolerance_deg"),
    ("loci", {**DIRECT, "angles": []}, "angles"),
])
def test_direct_admission(direct_client, path, body, fragment) -> None:
    response = direct_client.post(f"/v1/geodetic/{path}", json=body)
    assert response.status_code == 422, response.text
    assert fragment in response.text


@pytest.mark.parametrize("path,body,fragment", [
    ("chart/houses", {"dt": "2000-01-01T12:00:00", **PLACE, "system": "E"}, "timezone-aware"),
    ("chart/houses", {"dt": NATAL_ISO, **PLACE, "system": "E", "ayanamsa_system": "Lahiri"}, "tropical zodiac must not carry"),
    ("chart/overlay", {"dt": NATAL_ISO, **PLACE, "system": "E", **ASPECTS, "zodiac": "sidereal"}, "sidereal zodiac requires"),
    ("chart/overlay", {"dt": NATAL_ISO, "bodies": [f"B{i}" for i in range(13)], **PLACE, "system": "E", **ASPECTS}, "at most 12"),
    ("chart/loci", {"dt": NATAL_ISO, "bodies": []}, "non-empty"),
    ("chart/loci", {"dt": NATAL_ISO, "bodies": [" Sun"]}, "trimmed"),
    ("chart/compare", {"dt": NATAL_ISO, "system": "E", **ASPECTS, "places": PLACES, "place_error_policy": "ignore"}, "place_error_policy"),
])
def test_chart_backed_admission(direct_client, path, body, fragment) -> None:
    # Admission fails before any engine access, so the no-engine client suffices.
    response = direct_client.post(f"/v1/geodetic/{path}", json=body)
    assert response.status_code == 422, response.text
    assert fragment in response.text


def test_routes_are_registered_as_post_operations() -> None:
    paths = create_app(ServerConfig()).openapi()["paths"]
    for name in ("chart/houses", "chart/overlay", "chart/compare", "chart/loci", "overlay", "compare", "loci"):
        assert set(paths[f"/v1/geodetic/{name}"]) == {"post"}
