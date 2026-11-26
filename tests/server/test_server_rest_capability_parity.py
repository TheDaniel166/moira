"""Engine-to-HTTP witnesses for the REST capability parity additions."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.batch import planet_time_series
from moira.constants import Body, HouseSystem, J2000
from moira.cycles import bounded_return_series
from moira.houses import houses_from_armc
from moira.julian import jd_from_datetime, tdb_to_tt, tt_to_tdb, utc_to_ut1
from moira.midpoints import activated_midpoints, calculate_midpoints, midpoint_tree
from moira.nodes import next_moon_node_crossing
from moira.phenomena import heliocentric_conjunctions_in_range_with_truth
from moira.planets import planet_relative_to
from moira.sidereal import UserDefinedAyanamsa, ayanamsa_with_truth
from moira.stars import stars_by_magnitude, stars_near
from moira.transits import prenatal_syzygy
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.dependencies import get_engine


pytestmark = pytest.mark.loopback


@pytest.fixture(scope="module")
def client(moira_engine):
    app = create_app(ServerConfig())
    app.dependency_overrides[get_engine] = lambda: moira_engine
    return TestClient(app)


def _post(client, path, body):
    response = client.post(path, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_custom_and_chart_sidereal_reduction(client, moira_engine):
    dt = datetime(2026, 6, 21, 4, tzinfo=timezone.utc)
    jd = utc_to_ut1(jd_from_datetime(dt))
    natal = moira_engine.chart(dt, bodies=[Body.SUN], include_nodes=False)

    def evaluate(reference):
        selection = {"family": "user_defined", "reference_value_j2000": reference, "drift_per_century": 0.12}
        result = _post(client, "/v1/chart/sidereal", {
            "dt": dt.isoformat(), "bodies": [Body.SUN], "ayanamsa_doctrine": selection, "mode": "mean",
        })
        direct = ayanamsa_with_truth(jd, UserDefinedAyanamsa(reference, 0.12), "mean")
        assert result["jd_ut"] == jd
        assert result["computation_truth"]["jd_tt"] == direct.jd_tt
        assert result["computation_truth"]["doctrine_terms"]["drift_per_century"] == 0.12
        assert result["ayanamsa_offset"] == direct.ayanamsa_unwrapped_deg
        assert result["sidereal_longitudes"][Body.SUN] == (natal.planets[Body.SUN].longitude - result["ayanamsa_offset"]) % 360
        scalar = _post(client, "/v1/sidereal/ayanamsa", {
            "jd_ut": jd, "mode": "mean", "ayanamsa_doctrine": selection,
        })
        assert scalar["ayanamsa_deg"] == direct.ayanamsa_deg
        conversion = _post(client, "/v1/sidereal/convert", {
            "jd_ut": jd, "mode": "mean", "ayanamsa_doctrine": selection,
            "longitude_deg": 100, "direction": "tropical_to_sidereal",
        })
        assert conversion["output_longitude_deg"] == (100 - direct.ayanamsa_unwrapped_deg) % 360
        inverse = _post(client, "/v1/sidereal/convert", {
            "jd_ut": jd, "mode": "mean", "ayanamsa_doctrine": selection,
            "longitude_deg": conversion["output_longitude_deg"], "direction": "sidereal_to_tropical",
        })
        assert inverse["output_longitude_deg"] == pytest.approx(100, abs=1e-12)
        position = _post(client, "/v1/nakshatra/position", {
            "jd_ut": jd, "ayanamsa_doctrine": selection, "tropical_longitude_deg": 100,
        })
        bulk = _post(client, "/v1/nakshatra/bulk", {
            "jd_ut": jd, "ayanamsa_doctrine": selection, "positions": {"Sun": 100},
        })
        true_ayanamsa = ayanamsa_with_truth(jd, UserDefinedAyanamsa(reference, 0.12), "true")
        assert position["position"]["sidereal_longitude_deg"] == (100 - true_ayanamsa.ayanamsa_unwrapped_deg) % 360
        assert bulk["positions"][0]["sidereal_longitude_deg"] == position["position"]["sidereal_longitude_deg"]
        return scalar["ayanamsa_deg"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        mardyks, fiorenza = pool.map(evaluate, (30.017793882, 25.0))
    assert mardyks != fiorenza


@pytest.mark.parametrize(("system", "armc", "latitude"), [
    (HouseSystem.WHOLE_SIGN, 95, -72),
    (HouseSystem.PORPHYRY, 95, -72),
    (HouseSystem.PORPHYRY, 220, 80),
    (HouseSystem.PULLEN_SD, 95, -72),
    (HouseSystem.PULLEN_SD, 220, 80),
])
def test_static_armc_preserves_zodiac_and_physical_geometry(client, system, armc, latitude):
    result = _post(client, "/v1/houses/armc", {
        "armc": armc, "obliquity": 23.4393, "latitude": latitude, "system": system,
        "ayanamsa_offset": 24, "include_boundary_geometry": True,
    })
    expected = houses_from_armc(armc, 23.4393, latitude, system, ayanamsa_offset=24, include_boundary_geometry=True)
    assert result["cusps"] == list(expected.cusps)
    assert result["effective_system"] == expected.effective_system
    assert result["boundary_geometry"]["zodiac_offset_deg"] == 24


def test_static_armc_preserves_polar_fallback_policy(client):
    position = {"armc": 95, "obliquity": 23.4393, "latitude": -72, "system": HouseSystem.KOCH}
    default = _post(client, "/v1/houses/armc", position)
    assert default["effective_system"] == HouseSystem.PORPHYRY
    assert default["fallback"] is True
    strict = client.post("/v1/houses/armc", json={**position, "policy": {"polar_fallback": "raise"}})
    assert strict.status_code == 422, strict.text


def test_supplied_patterns_and_midpoints(client):
    trine = {"Sun": 360, "Moon": 120, "Venus": 240}
    pattern = _post(client, "/v1/patterns/from-longitudes", {"longitudes": trine})
    assert any(event["name"] == "Grand Trine" for event in pattern["events"])
    assert pattern["computation_truth"]["position_source"] == "caller_supplied_longitudes"
    template = {"name": "My H13 triple", "phases": [[0, 1], [1, 13], [2, 13]]}
    custom = _post(client, "/v1/patterns/from-longitudes", {
        "longitudes": {"Sun": 360, "Moon": 360 / 13, "Mars": 720 / 13},
        "templates": [template], "include": [], "optional_sets": ["H13"],
    })
    event, = custom["events"]
    assert event["name"] == template["name"]
    assert event["geometry"]["phases"] == template["phases"]

    lons = {"Sun": 350, "Moon": 10, "Mercury": 180}
    tree = _post(client, "/v1/midpoints/tree", {"focus": 359.5, "longitudes": lons, "dial": 90})
    activation = _post(client, "/v1/midpoints/activations", {
        "transit_longitude": 359.5, "longitudes": lons, "dial": 90,
    })
    assert [hit["orb"] for hit in tree["events"]] == [orb for _, orb in midpoint_tree(359.5, lons, dial=90)]
    assert [hit["orb"] for hit in activation["events"]] == [
        orb for _, orb in activated_midpoints(359.5, calculate_midpoints(lons), dial=90)
    ]


def test_unified_catalog_ambiguity_and_provisional_orbit_class(client):
    conflict = client.get("/v1/small-bodies/identity", params={"body": "Halley"})
    assert conflict.status_code == 409, conflict.text
    candidates = conflict.json()["detail"]["candidates"]
    assert {item["family"] for item in candidates} == {"asteroid", "comet"}
    qualified = client.get("/v1/small-bodies/identity", params={"body": "comet:Halley"})
    assert qualified.status_code == 200, qualified.text
    assert qualified.json()["family"] == "comet"
    missing = client.get("/v1/small-bodies/identity", params={"body": "Definitely Missing"})
    assert missing.status_code == 404
    asteroid = client.get("/v1/asteroids/identity", params={"body": "2006 QH181"})
    assert asteroid.status_code == 200, asteroid.text
    assert asteroid.json()["orbit_class"]["code"] == "TNO"
    assert asteroid.json()["mpc_number"] is None


def test_fixed_star_queries_preserve_engine_order_and_inclusion(client):
    longitude = _post(client, "/v1/stars/search", {
        "kind": "longitude", "jd_tt": J2000, "product": "astrometric", "longitude_deg": 359, "orb_deg": 5, "limit": 10,
    })
    expected = stars_near(359, J2000, 5, product="astrometric")
    assert longitude["total_matches"] == len(expected)
    assert [row["name"] for row in longitude["matches"]] == [star.name for star in expected[:10]]
    bright = _post(client, "/v1/stars/search", {
        "kind": "magnitude", "jd_tt": J2000, "product": "astrometric", "max_magnitude": 1.0,
    })
    assert [row["name"] for row in bright["matches"]] == [
        star.name for star in stars_by_magnitude(1.0, J2000, product="astrometric")
    ]


def test_clock_transformations_and_diagnostics(client):
    for day, tai_minus_utc in ((2457753.5, 36), (2457754.5, 37)):
        result = _post(client, "/v1/time/convert", {"source_scale": "UTC", "target_scale": "TT", "jd": day})
        assert result["provenance"]["tai_minus_utc_seconds"] == tai_minus_utc
    tdb = _post(client, "/v1/time/convert", {"source_scale": "TT", "target_scale": "TDB", "jd": J2000 + 90})
    assert tdb["jd"] == tt_to_tdb(J2000 + 90)
    back = _post(client, "/v1/time/convert", {"source_scale": "TDB", "target_scale": "TT", "jd": tdb["jd"]})
    assert back["jd"] == tdb_to_tt(tdb["jd"])
    calendar = _post(client, "/v1/time/convert", {"source_scale": "UTC", "target_scale": "civil_utc", "jd": J2000})
    assert calendar["calendar_utc"]["year"] == 2000
    for request in ({"kind": "estimate", "jd_ut1": J2000}, {"kind": "breakdown", "year": 1600},
                    {"kind": "distribution", "year": 2200}):
        assert _post(client, "/v1/time/delta-t", request)["units"] == "seconds"


def test_position_series_keeps_explicit_order_and_repeats(client, moira_engine):
    epochs = [J2000 + 1, J2000, J2000 + 1]
    result = _post(client, "/v1/positions/time-series", {"body": "Moon", "jd_ut1": epochs})
    expected = planet_time_series("Moon", epochs, reader=moira_engine._reader)
    assert result["jd_ut1"] == epochs
    assert result["distances_km"] == list(expected.distances)
    assert result["longitudes_deg"] == list(expected.longitudes)


@pytest.mark.parametrize(("month", "latitude", "state"), [
    (6, 78.2232, "always_above_horizon"),
    (12, 78.2232, "always_below_horizon"),
    (6, 0.0, "crosses"),
])
def test_geometric_horizon_availability(client, month, latitude, state):
    jd = jd_from_datetime(datetime(2026, month, 21, tzinfo=timezone.utc))
    result = _post(client, "/v1/rise-set/availability", {
        "body": "Sun", "jd_start_ut1": jd, "latitude": latitude, "longitude": -15.6469,
    })
    assert result["state"] == state
    assert result["minimum_altitude"] <= result["maximum_altitude"]
    assert result["sample_count"] == 145


def test_lunar_event_searches(client, moira_engine):
    for direction in ("ascending", "descending"):
        crossing = _post(client, "/v1/nodes/lunar/next-crossing", {"jd_start_ut1": J2000, "direction": direction})
        assert crossing["jd_ut1"] == next_moon_node_crossing(
            J2000, reader=moira_engine._reader, ascending=direction == "ascending",
        )
    syzygy = _post(client, "/v1/lunar-phases/prenatal-syzygy", {"jd_ut1": J2000})
    assert (syzygy["jd_ut1"], syzygy["phase"]) == prenatal_syzygy(J2000, reader=moira_engine._reader)


def test_heliocentric_events_and_bounded_miss(client, moira_engine):
    reader = moira_engine._reader
    request = {"body": "Mercury", "other_body": "Venus", "jd_start_ut1": J2000}
    result = _post(client, "/v1/phenomena/heliocentric-events", {
        **request, "kind": "conjunctions_in_range", "jd_end_ut1": J2000 + 200,
    })
    expected = heliocentric_conjunctions_in_range_with_truth("Mercury", "Venus", J2000, J2000 + 200, reader)
    assert expected.events
    assert [event["jd_ut1"] for event in result["events"]] == [event.jd_ut for event in expected.events]
    current = planet_relative_to("Mercury", Body.SUN, J2000, reader=reader).longitude
    fixed = {"kind": "next_longitude_crossing", "body": "Mercury", "jd_start_ut1": J2000}
    hit = _post(client, "/v1/phenomena/heliocentric-events", {
        **fixed, "target_longitude_deg": current + 2, "max_days": 20,
    })
    assert hit["status"] == "found"
    assert hit["events"][0]["longitude_deg"] == pytest.approx((current + 2) % 360, abs=0.0001)
    miss = _post(client, "/v1/phenomena/heliocentric-events", {
        **fixed, "target_longitude_deg": current + 180, "max_days": 0.1,
    })
    assert miss["status"] == "no_event" and miss["events"] == []


def test_bounded_half_return_uses_opposition_target(client, moira_engine):
    result = _post(client, "/v1/returns/series", {
        "kind": "half", "body": "Sun", "natal_longitude_deg": 0, "jd_start_ut1": J2000, "jd_end_ut1": J2000 + 366,
    })["series"]
    expected = bounded_return_series("Sun", 0, J2000, J2000 + 366, half=True, reader=moira_engine._reader)
    assert result["target_longitude_deg"] == 180
    assert result["events"][0]["jd_ut1"] == expected.events[0].jd_ut1
    assert result["events"][0]["longitude_deg"] == pytest.approx(180, abs=0.00001)
    lifetime = _post(client, "/v1/returns/series", {
        "kind": "lifetime", "body": "Sun", "natal_longitude_deg": 0, "birth_jd_ut1": J2000, "years": 2,
    })["series"]
    assert lifetime["jd_end_ut1"] == J2000 + 730.5
    assert len(lifetime["events"]) == 2


@pytest.mark.parametrize(("path", "payload"), [
    ("/v1/time/convert", {"source_scale": "UT1", "target_scale": "civil_utc", "jd": J2000}),
    ("/v1/positions/time-series", {"body": "Sun", "jd_ut1": []}),
    ("/v1/houses/armc", {"armc": True, "obliquity": 23, "latitude": 0}),
    ("/v1/patterns/from-longitudes", {"longitudes": {"Sun": "4", "Moon": 9}}),
    ("/v1/sidereal/ayanamsa", {"jd_ut": J2000, "mode": False}),
])
def test_invalid_contract_inputs_fail_closed(client, path, payload):
    assert client.post(path, json=payload).status_code == 422
