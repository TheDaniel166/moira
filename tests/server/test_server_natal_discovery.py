"""Natal packet admission, selected-scope and geometric transport invariants.

Synthetic charts prove the declared classic-seven/Jones transport semantics.
Real DE-kernel checks use the session fixture at J2000 and current source engine
methods; they prove composition and source consistency, not external authority
accuracy. Circular residual tolerance is 1e-6 degrees (serialization admission).
Lunation root separation is checked within 1e-4 degrees (existing search policy).
"""

from datetime import datetime, timezone
import math

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from moira.constants import Body
from moira.coordinates import angular_distance
from moira.julian import _ut1_to_utc, datetime_from_jd, jd_from_datetime, utc_to_ut1
from moira.phase import illuminated_fraction, phase_angle
from moira.sidereal import ayanamsa
from moira.spk_reader import use_reader_override
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.natal_discovery import NatalDiscoveryRequest
from moira_server.services.natal_discovery import compute_natal_lunar_context


pytestmark = pytest.mark.loopback
_PREFIX = "/v1/natal-discovery"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as session:
        yield session


@pytest.fixture
def kernel_client(moira_engine, monkeypatch):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as session:
        yield session


def _request(longitudes, **fields):
    return {"dt": "2000-01-01T12:00:00Z", "longitudes": longitudes, **fields}


def _real_request(engine, *, zodiac="Tropical", selected=None, dt=None):
    instant = dt or datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
    positions = engine.chart(instant, bodies=selected, include_nodes=False).planets
    values = {name: position.longitude for name, position in positions.items()}
    extras = {"zodiac": zodiac}
    if zodiac == "Sidereal":
        with use_reader_override(engine._reader):
            offset = ayanamsa(utc_to_ut1(jd_from_datetime(instant)), "Lahiri", "true")
        values = {name: (degree - offset) % 360 for name, degree in values.items()}
        extras["ayanamsa_system"] = "Lahiri"
    return {"dt": instant.isoformat(), "longitudes": values, **extras}


def test_dispositor_cycles_and_multiple_final_sinks_are_distinct(client):
    cycle = client.post(f"{_PREFIX}/dispositors", json=_request({"Sun": 100, "Moon": 130})).json()
    assert cycle["terminal_cycles"] == [["Sun", "Moon"]]
    assert cycle["final_dispositors"] == []
    assert all(chain["termination"] == "terminal_cycle" for chain in cycle["chains"])
    finals = client.post(f"{_PREFIX}/dispositors", json=_request({"Sun": 130, "Moon": 100, "Mercury": 70})).json()
    assert finals["terminal_cycles"] == []
    assert finals["final_dispositors"] == ["Sun", "Moon", "Mercury"]
    assert all(chain["terminal_subjects"] == [chain["body"]] for chain in finals["chains"])


def test_missing_ruler_is_visible_and_unselected_bodies_are_not_added(client):
    response = client.post(f"{_PREFIX}/dispositors", json=_request({"Mars": 150, "Uranus": 0}))
    assert response.status_code == 200
    packet = response.json()
    assert [chain["body"] for chain in packet["chains"]] == ["Mars", "Uranus"]
    chain = packet["chains"][0]
    assert chain["termination"] == "missing_selected_ruler"
    assert chain["missing_ruler"] == "Mercury"
    assert chain["links"] == [{"subject": "Mars", "subject_sign": "Virgo", "dispositor": "Mercury"}]
    assert packet["excluded_subjects"] == ["Uranus"]
    assert packet["chains"][1]["termination"] == "out_of_scope"
    assert len(packet["rulerships"]) == 12


def test_zero_degree_and_empty_selection_are_not_unavailable(client):
    selected = client.post(f"{_PREFIX}/dispositors", json=_request({"Mars": 0})).json()
    assert selected["chains"][0]["longitude_deg"] == 0
    assert selected["chains"][0]["termination"] == "final_dispositor"
    empty = client.post(f"{_PREFIX}/dispositors", json=_request({})).json()
    assert empty["chains"] == []
    assert empty["final_dispositors"] == []


def test_shape_requires_selected_ten_planets_and_keeps_partial_evidence(client):
    response = client.post(f"{_PREFIX}/shape", json=_request({"Sun": 0, "Moon": 100}))
    assert response.status_code == 200
    packet = response.json()
    assert packet["status"] == "insufficient_selection"
    assert packet["classification"] is None
    assert packet["gaps"] == []
    assert packet["missing_bodies"] == Body.ALL_PLANETS[2:]
    assert packet["positions"] == [{"body": "Sun", "longitude_deg": 0}, {"body": "Moon", "longitude_deg": 100}]


def test_bucket_core_metrics_are_separate_from_ten_planet_gaps(client):
    # Existing Jones fixture geometry: nine in 120 degrees, Pluto opposite.
    positions = dict(zip(Body.ALL_PLANETS, [0, 15, 30, 45, 60, 75, 90, 105, 120, 240]))
    response = client.post(f"{_PREFIX}/shape", json=_request(positions))
    assert response.status_code == 200
    packet = response.json()
    shape = packet["classification"]
    assert shape["shape"] == "Bucket"
    assert shape["handle_bodies"] == ["Pluto"]
    assert shape["metrics_scope"] == "nine_planet_bowl_core"
    assert shape["occupied_arc_deg"] == 120
    assert shape["largest_gap_deg"] == 240
    assert max(gap["gap_deg"] for gap in packet["gaps"]) == 120
    assert sum(gap["gap_deg"] for gap in packet["gaps"]) == 360
    assert len(packet["gaps"]) == 10
    assert {body for cluster in shape["clusters"] for body in cluster} == set(positions)


def test_splash_residual_policy_is_explained(client):
    response = client.post(f"{_PREFIX}/shape", json=_request(dict(zip(Body.ALL_PLANETS, range(0, 360, 36)))))
    assert response.json()["classification"]["shape"] == "Splash"
    assert "borderline" in response.json()["classification_note"]


@pytest.mark.parametrize("fields", [
    {"dt": "2000-01-01T12:00:00"},
    {"dt": "2000-01-01T12:00:00.1234567Z"},
    {"longitudes": {"Sun": True}},
    {"longitudes": {"Sun": "90"}},
    {"longitudes": {"Sun": 360}},
    {"longitudes": {"Asc": 90}},
    {"zodiac": "Sidereal"},
    {"zodiac": "Sidereal", "ayanamsa_system": "Unknown"},
    {"ayanamsa_system": "Lahiri"},
    {"method": "modern"},
    {"time_unknown": "false"},
])
def test_direct_rest_rejects_unadmitted_request_geometry(client, fields):
    response = client.post(f"{_PREFIX}/dispositors", json={**_request({"Sun": 0}), **fields})
    assert response.status_code == 422
    assert response.json()["category"] == "input_validation"


@pytest.mark.parametrize("degree", [math.nan, math.inf, -math.inf])
def test_nonfinite_longitudes_are_rejected_before_computation(degree):
    with pytest.raises(ValidationError, match="finite degrees"):
        NatalDiscoveryRequest(**_request({"Sun": degree}))


def test_source_echo_preserves_offset_and_microseconds(client):
    timestamp = "2000-01-01T07:00:00.123456000-05:00"
    response = client.post(f"{_PREFIX}/dispositors", json=_request({"Sun": 0}, dt=timestamp))
    assert response.status_code == 200
    source = response.json()["source"]
    assert source["requested_datetime"] == timestamp
    assert source["normalized_datetime_utc"] == "2000-01-01T12:00:00.123456+00:00"
    assert source["longitude_basis"] == "caller_supplied_accepted_chart"


def test_unknown_time_and_missing_luminaries_do_not_touch_ephemeris(client):
    unknown = client.post(f"{_PREFIX}/lunar-context", json=_request({"Sun": 0, "Moon": 100}, time_unknown=True)).json()
    assert unknown["status"] == "unknown_time"
    assert unknown["source"]["reference_kind"] == "noon_reference"
    assert unknown["phase"] is None and unknown["events"] == [] and unknown["contacts"] == []
    assert unknown["source_consistency"] is None
    missing = client.post(f"{_PREFIX}/lunar-context", json=_request({"Sun": 0})).json()
    assert missing["status"] == "missing_luminaries"
    assert missing["missing_bodies"] == ["Moon"]


@pytest.mark.parametrize("zodiac", ["Tropical", "Sidereal"])
def test_real_kernel_packet_has_strict_prior_events_and_named_frame_contacts(kernel_client, moira_engine, zodiac):
    request = _real_request(moira_engine, zodiac=zodiac)
    response = kernel_client.post(f"{_PREFIX}/lunar-context", json=request)
    assert response.status_code == 200, response.text
    packet = response.json()
    assert packet["status"] == "calculated"
    phase = packet["phase"]
    assert phase["sun_longitude_deg"] == request["longitudes"]["Sun"]
    assert phase["moon_longitude_deg"] == request["longitudes"]["Moon"]
    assert phase["angle_deg"] == pytest.approx((request["longitudes"]["Moon"] - request["longitudes"]["Sun"]) % 360, abs=1e-12)
    assert packet["source_consistency"]["maximum_residual_deg"] < 1e-6
    with use_reader_override(moira_engine._reader):
        physical_angle = phase_angle("Moon", packet["source"]["jd_ut1"])
    assert phase["physical_phase_angle_deg"] == pytest.approx(physical_angle, abs=1e-12)
    assert phase["illuminated_fraction"] == pytest.approx(illuminated_fraction(physical_angle), abs=1e-12)
    assert 0 <= phase["illuminated_fraction"] <= 1
    assert len(packet["events"]) == 2
    assert all(event["jd_ut1"] < packet["source"]["jd_ut1"] for event in packet["events"])
    assert [event["is_prenatal_syzygy"] for event in packet["events"]] == [False, True]
    for event in packet["events"]:
        separation = angular_distance(event["sun_longitude_deg"], event["moon_longitude_deg"])
        assert separation == pytest.approx(0 if event["phase"] == "New Moon" else 180, abs=1e-4)
        civil = datetime.fromisoformat(event["datetime_utc"])
        assert utc_to_ut1(jd_from_datetime(civil)) == pytest.approx(event["jd_ut1"], abs=1e-8)
        assert event["ayanamsa_deg"] > 0 if zodiac == "Sidereal" else event["ayanamsa_deg"] == 0
    assert packet["contacts"]
    for contact in packet["contacts"]:
        assert contact["body"] in request["longitudes"]
        assert contact["natal_longitude_deg"] == request["longitudes"][contact["body"]]
        assert contact["orb_deg"] <= contact["allowed_orb_deg"]
        assert contact["orb_deg"] == pytest.approx(abs(contact["separation_deg"] - contact["angle_deg"]), abs=1e-12)
    assert packet["contact_policy"]["motion"] == "not_evaluated"


def test_source_mismatch_is_rejected_and_matching_serialized_value_is_preserved(kernel_client, moira_engine):
    request = _real_request(moira_engine, selected=["Sun", "Moon"])
    request["longitudes"]["Moon"] += 1e-7
    response = kernel_client.post(f"{_PREFIX}/lunar-context", json=request)
    assert response.status_code == 200
    assert response.json()["phase"]["moon_longitude_deg"] == request["longitudes"]["Moon"]
    assert {contact["body"] for contact in response.json()["contacts"]} <= {"Sun", "Moon"}
    request["longitudes"]["Moon"] += 1
    rejected = kernel_client.post(f"{_PREFIX}/lunar-context", json=request)
    assert rejected.status_code == 422
    assert "do not match" in rejected.json()["message"]


def test_strict_preceding_event_at_a_solved_lunation(moira_engine):
    first = compute_natal_lunar_context(moira_engine, NatalDiscoveryRequest(**_real_request(moira_engine)))
    solved = first.events[-1].jd_ut1
    instant = datetime_from_jd(_ut1_to_utc(solved))
    second = compute_natal_lunar_context(moira_engine, NatalDiscoveryRequest(**_real_request(moira_engine, dt=instant)))
    assert all(event.jd_ut1 < second.source.jd_ut1 for event in second.events)


def test_openapi_describes_all_three_stable_packets():
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    for route, response in (("dispositors", "NatalDispositorsResponse"), ("shape", "NatalShapeResponse"), ("lunar-context", "NatalLunarContextResponse")):
        assert schema["paths"][f"{_PREFIX}/{route}"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(response)
