"""Local parity and failure witnesses for the remaining Section 5 products."""

from dataclasses import asdict
from math import inf, nextafter
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira.muhurta_search import MuhurtaSearchPolicy
from moira.stars import star_at, star_chart_condition_profile, star_condition_network_profile
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback
_DT = "2000-01-01T12:00:00Z"


@pytest.fixture
def local_client(monkeypatch):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: SimpleNamespace(_reader=None))
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        yield client


@pytest.fixture
def kernel_client(monkeypatch, moira_engine):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        yield client


def test_planetary_age_catalogue_and_all_source_boundaries(local_client):
    path = "/v1/phenomena/planetary-ages"
    response = local_client.get(path)
    assert response.status_code == 200, response.text
    catalogue = response.json()
    assert catalogue["source"] == "Ptolemy, Tetrabiblos IV.10"
    assert catalogue["current"] is catalogue["queried_age_years"] is None
    boundaries = [0, 4, 14, 22, 41, 56, 68, None]
    periods = catalogue["periods"]
    assert [p["ruler"].lower() for p in periods] == ["moon", "mercury", "venus", "sun", "mars", "jupiter", "saturn"]
    for index, start in enumerate(boundaries[:-1]):
        period = periods[index]
        assert (period["start_age_years"], period["end_age_years"]) == (start, boundaries[index + 1])
        assert local_client.get(path, params={"age_years": start}).json()["current"] == period
        if index:
            before = local_client.get(path, params={"age_years": nextafter(start, -inf)})
            assert before.json()["current"] == periods[index - 1]
    assert local_client.get(path, params={"age_years": 150}).json()["current"] == periods[-1]
    for invalid in ("-1", "nan", "inf"):
        assert local_client.get(path, params={"age_years": invalid}).status_code == 422


def test_fixed_star_conditions_match_shared_sovereign_positions(kernel_client, moira_engine):
    names = ["Sirius", "Regulus"]
    request = {"dt": _DT, "stars": [*names, "DefinitelyNotAStar"], "product": "apparent"}
    response = kernel_client.post("/v1/stars/conditions", json=request)
    bulk = kernel_client.post("/v1/stars/bulk", json=request)
    assert response.status_code == bulk.status_code == 200, response.text
    body = response.json()
    assert body["frame"] == "true_ecliptic_of_date"
    assert body["product"] == "apparent"
    assert body["results"] == bulk.json()["results"]
    assert body["missing"] == ["DefinitelyNotAStar"]
    stars = [star_at(name, body["jd_tt"], product="apparent", reader=moira_engine._reader) for name in names]
    condition = star_chart_condition_profile(fixed_stars=stars)
    network = star_condition_network_profile(fixed_stars=stars)
    assert body["condition_profile"]["profiles"] == [asdict(profile) for profile in condition.profiles]
    assert body["network_profile"]["nodes"] == [asdict(node) for node in network.nodes]
    assert body["network_profile"]["edges"] == [asdict(edge) for edge in network.edges]
    assert {edge["target_id"] for edge in body["network_profile"]["edges"]} == {"star:Regulus", "star:Sirius"}
    assert all(row["provenance"]["position_product"] == "apparent" for row in body["results"].values())


def test_star_conditions_separate_lookup_misses_and_missing_resources(local_client):
    path = "/v1/stars/conditions"
    request = {"dt": _DT, "stars": ["Sirius", "DefinitelyNotAStar"], "product": "astrometric"}
    complete = local_client.post(path, json=request)
    assert complete.status_code == 200, complete.text
    assert complete.json()["missing"] == ["DefinitelyNotAStar"]
    assert complete.json()["results"]["Sirius"]["provenance"]["position_product"] == "astrometric"
    strict = local_client.post(path, json={**request, "skip_missing": False})
    bulk_strict = local_client.post("/v1/stars/bulk", json={**request, "skip_missing": False})
    assert strict.status_code == bulk_strict.status_code == 422
    assert strict.json()["error_code"] == bulk_strict.json()["error_code"]
    assert local_client.post(path, json={**request, "product": "apparent"}).status_code == 503
    for changes in (
        {"stars": ["Sirius", "sirius"]}, {"stars": ["Titawin", "Adhab"]},
        {"product": "incompatible"}, {"dt": "2000-01-01T12:00:00"},
    ):
        assert local_client.post(path, json={**request, **changes}).status_code == 422


def test_progression_aggregates_match_individual_arc_and_time_key(kernel_client):
    natal = {"dt": _DT, "bodies": ["Sun", "Moon", "Mars"]}
    setup = {"natal": natal, "target_dt": "2020-01-01T12:00:00Z"}
    items = {
        "arc_items": [{**setup, "method": "solar_arc", "converse": converse} for converse in (False, True)],
        "time_key_items": [{**setup, "method": "tertiary", "converse": converse} for converse in (False, True)],
    }
    expected = []
    for key, route in (("arc_items", "arc"), ("time_key_items", "time-key")):
        for item in items[key]:
            response = kernel_client.post(f"/v1/progressions/{route}", json=item)
            assert response.status_code == 200, response.text
            profile = response.json()["condition_profile"]
            assert profile["converse"] is item["converse"]
            expected.append(profile)
    for route in ("profile", "network"):
        response = kernel_client.post(f"/v1/progressions/{route}/reduction", json=items)
        plain = kernel_client.post(f"/v1/progressions/{route}", json=items)
        assert response.status_code == plain.status_code == 200, response.text
        body = response.json()
        assert body["result"] == plain.json()
        assert body["reduction"]["item_profiles"] == expected
        assert body["reduction"]["chart_item_count"] == 4
        if route == "network":
            assert {edge["source_id"] for edge in body["result"]["edges"]} == {
                f"technique:{p['technique_name']}" for p in expected
            }
    invalid = {"arc_items": [items["arc_items"][0]] * 17}
    assert kernel_client.post("/v1/progressions/profile", json=invalid).status_code == 422
    duplicate = {"arc_items": [items["arc_items"][0]] * 2}
    assert kernel_client.post("/v1/progressions/network", json=duplicate).status_code == 422


def test_muhurta_sample_opt_in_and_precomputed_clock_match_engine(kernel_client, moira_engine):
    start, end = 2451545.0, 2451545.5
    request = {"start_jd_ut1": start, "end_jd_ut1": end, "janma_moon_sidereal_lon": 100,
               "policy": {"step_minutes": 360, "min_score": 1000}}
    result = moira_engine.find_muhurta_windows(
        start, end, janma_moon_sidereal_lon=100, policy=MuhurtaSearchPolicy(step_days=0.25, min_score=1000),
    )
    response = kernel_client.post("/v1/muhurta/search", json={**request, "include_samples": True})
    plain = kernel_client.post("/v1/muhurta/search", json=request)
    assert response.status_code == plain.status_code == 200, response.text
    body = response.json()
    samples = body.pop("samples")
    assert body == plain.json()
    assert body["windows"] == []
    assert len(samples) == body["sample_count"] == 3
    for row, sample in zip(samples, result.samples, strict=True):
        assert row["jd_ut1"] == sample.jd_ut1 and row["jd_tt"] == sample.jd_tt and row["jd_tdb"] == sample.jd_tdb
        assert row["score_total"] == sample.score.total
        assert row["clock_identity"] == sample.clock_identity
    row = samples[0]
    supplied = {key: row[key] for key in ("jd_ut1", "jd_tt", "sun_tropical_longitude", "moon_tropical_longitude")}
    supplied["janma_moon_sidereal_lon"] = 100
    supplied["delta_t_seconds"] = (row["jd_tt"] - row["jd_ut1"]) * 86400
    path = "/v1/muhurta/precomputed/score"
    scored = kernel_client.post(path, json=supplied)
    assert scored.status_code == 200, scored.text
    decoded = scored.json()
    assert decoded["input_time_basis"] == "supplied_ut1_tt"
    assert decoded["natal_mode"] == "tara_chandra"
    assert decoded["jd_ut1"] == row["jd_ut1"] and decoded["jd_tt"] == row["jd_tt"]
    assert decoded["jd_tdb"] is None
    assert decoded["score"]["total"] == row["score_total"]
    assert decoded["ayanamsa_degrees"] == row["ayanamsa_degrees"]
    conflicting = kernel_client.post(path, json={**supplied, "delta_t_seconds": supplied["delta_t_seconds"] + 1})
    assert conflicting.status_code == 422


def test_muhurta_precomputed_public_scorer_keeps_optional_natal_mode(kernel_client, moira_engine):
    jd_ut1, jd_tt, sun, moon = 2451545.0, 2451545.0007, 280.0, 70.0
    response = kernel_client.post("/v1/muhurta/precomputed/score", json={
        "jd_ut1": jd_ut1, "jd_tt": jd_tt, "sun_tropical_longitude": sun, "moon_tropical_longitude": moon,
        "ayanamsa_system": "True Chitrapaksha",
    })
    assert response.status_code == 200, response.text
    chart = SimpleNamespace(jd_ut=jd_ut1, jd_tt=jd_tt, planets={
        "Sun": SimpleNamespace(longitude=sun), "Moon": SimpleNamespace(longitude=moon),
    })
    expected = moira_engine.muhurta_score_for_chart(chart, ayanamsa_system="True Chitrapaksha")
    body = response.json()
    assert body["natal_mode"] == "omitted"
    assert body["tara"] is body["chandra"] is None
    assert body["ayanamsa_degrees"] == expected.ayanamsa_degrees
    assert body["score"]["breakdown"] == expected.score.breakdown
