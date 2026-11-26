"""Contract and reader-backed evidence for bounded astronomical searches."""

from fastapi.testclient import TestClient
import pytest

from moira._eclipse_phase_window import PhaseWindowUnresolved
from moira._geocentric_conjunctions import GeocentricConjunctionBudgetError, GeocentricConjunctionUnresolved
from moira.batch import BatchFailure, BodyVoidWindows, void_periods_all_planets
from moira.cycles import great_conjunctions
from moira.eclipse import EclipseCalculator
from moira.julian import utc_datetime_from_ut1
from moira.planets import planet_at
from moira.spk_reader import MissingEphemerisKernelError, OutOfRangeError
from moira.void_of_course import void_periods_in_range
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


@pytest.fixture
def kernel_client(moira_engine, monkeypatch):
    """Bind the same admitted reader in the HTTP and comparison paths."""
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as client:
        yield client


@pytest.mark.parametrize("jd_ut1", [2451545.0, 2460409.262])
def test_eclipse_snapshot_matches_exact_epoch(kernel_client, moira_engine, jd_ut1):
    """Compare the neutral projection to the exact and aware-datetime engine paths."""
    response = kernel_client.post("/v1/eclipses/snapshot", json={"jd_ut1": jd_ut1})
    assert response.status_code == 200, response.text
    payload = response.json()
    calculator = EclipseCalculator(reader=moira_engine._reader)
    expected = calculator.calculate(utc_datetime_from_ut1(jd_ut1))
    assert payload["jd_ut1"] == jd_ut1
    assert payload["status"] == ("solar_eclipse" if expected.is_solar_eclipse else "no_eclipse")
    assert payload["eclipse_type"] == str(expected.eclipse_type)
    assert payload["moon_longitude_deg"] == pytest.approx(expected.moon_longitude, abs=1e-7, rel=0)
    assert payload["umbra_radius_deg"] == pytest.approx(expected.earth_shadow_apparent_radius, abs=1e-7, rel=0)
    assert payload["frame"] == "geocentric_true_ecliptic_of_date"


def test_natal_eclipse_contacts_use_inclusive_maxima_and_ordered_axes(kernel_client, moira_engine):
    """Verify both lunar axes, solar longitude, wrap, limits, and empty matches."""
    start, end = 2457090.0, 2457130.0
    calculator = EclipseCalculator(reader=moira_engine._reader)
    solar = calculator.solar_eclipses_in_range(start, end)[0]
    lunar = calculator.lunar_eclipses_in_range(start, end)[0]
    natal = {
        "solar_wrap": 0.0,
        "lunar_sun": lunar.data.sun_longitude,
        "lunar_moon": lunar.data.moon_longitude,
    }
    payload = {
        "jd_start_ut1": solar.jd_ut, "jd_end_ut1": lunar.jd_ut,
        "natal_longitudes_deg": natal, "orb_deg": 5.0,
    }
    response = kernel_client.post("/v1/eclipses/natal-contacts", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "complete"
    assert [(hit["target_name"], hit["axis_end"]) for hit in body["hits"]] == [
        ("solar_wrap", "sun"), ("lunar_moon", "moon"), ("lunar_sun", "sun"),
    ]
    assert body["hits"][0]["separation_deg"] == pytest.approx(360.0 - solar.data.sun_longitude)
    limited = kernel_client.post("/v1/eclipses/natal-contacts", json={**payload, "limit": 1}).json()
    assert limited["hits"] == body["hits"][:1]
    assert limited["truncated"] is True
    assert limited["total_hits"] == 3
    boundary = kernel_client.post("/v1/eclipses/natal-contacts", json={
        **payload, "natal_longitudes_deg": {"solar_wrap": 0.0},
        "orb_deg": body["hits"][0]["separation_deg"],
    }).json()
    assert [hit["target_name"] for hit in boundary["hits"]] == ["solar_wrap"]
    empty = kernel_client.post(
        "/v1/eclipses/natal-contacts", json={**payload, "natal_longitudes_deg": {"outside": 90.0}},
    ).json()
    assert empty["status"] == "complete" and empty["hits"] == []


def test_natal_eclipse_contacts_distinguish_coverage_and_refinement(kernel_client, monkeypatch):
    """Fail observably when either padded scan coverage or phase proof is missing."""
    request = {
        "jd_start_ut1": 2451545.0, "jd_end_ut1": 2451546.0,
        "natal_longitudes_deg": {"point": 10.0},
    }
    monkeypatch.setattr(EclipseCalculator, "_native_eclipse_syzygy_candidates", lambda *args: None)
    assert kernel_client.post("/v1/eclipses/natal-contacts", json=request).status_code == 503
    monkeypatch.setattr(EclipseCalculator, "_native_eclipse_syzygy_candidates", lambda *args: [2451545.0])

    def unresolved(*args, **kwargs):
        raise PhaseWindowUnresolved("test unresolved phase")

    monkeypatch.setattr("moira.eclipse._phase_crossing_in_window", unresolved)
    response = kernel_client.post("/v1/eclipses/natal-contacts", json=request)
    assert response.status_code == 200
    assert response.json()["status"] == "unresolved_phase"
    assert response.json()["total_hits"] is None


def test_multi_body_void_preserves_mover_order_and_lunar_control(kernel_client, moira_engine):
    """Compare exact window data to engine batches and the lunar specialist."""
    start, end = 2451545.0, 2451549.0
    bodies = ["Mercury", "Moon"]
    response = kernel_client.post("/v1/void-of-course/multi-body", json={
        "jd_start_ut1": start, "jd_end_ut1": end, "bodies": bodies, "aspect_set": "modern",
    })
    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert [result["body"] for result in results] == bodies
    expected = void_periods_all_planets(start, end, bodies, reader=moira_engine._reader, modern=True)
    for result, bundle in zip(results, expected, strict=True):
        assert result["status"] == "complete"
        assert [(w["jd_voc_start_ut1"], w["jd_voc_end_ut1"]) for w in result["windows"]] == [
            (w.jd_voc_start, w.jd_voc_end) for w in bundle.windows
        ]
    lunar = void_periods_in_range(start, end, reader=moira_engine._reader, modern=True)
    assert [(w.jd_voc_start, w.jd_voc_end) for w in expected[1].windows] == [
        (w.jd_voc_start, w.jd_voc_end) for w in lunar
    ]


def test_multi_body_void_localizes_coverage_failures(kernel_client, monkeypatch):
    """Keep a failed mover distinct from successful emptiness."""
    monkeypatch.setattr("moira_server.services.bounded_searches.void_periods_all_planets", lambda *a, **k: [
        BodyVoidWindows("Mars", failure=BatchFailure("OutOfRangeError", "internal details", "test")),
        BodyVoidWindows("Moon"),
    ])
    response = kernel_client.post("/v1/void-of-course/multi-body", json={
        "jd_start_ut1": 2451545.0, "jd_end_ut1": 2451546.0, "bodies": ["Mars", "Moon"],
    })
    assert response.status_code == 200, response.text
    assert [item["status"] for item in response.json()["results"]] == ["coverage_unavailable", "complete"]
    assert "internal details" not in response.text


def test_great_conjunctions_match_mundane_roots_without_selecting_a_site(kernel_client, moira_engine):
    """Match the 1980–81 triple against the mundane adapter and apparent geometry."""
    start, end = 2444500.0, 2444900.0
    request = {"jd_start_ut1": start, "jd_end_ut1": end, "include_zodiac": True}
    path = "/v1/phenomena/great-conjunctions"
    response = kernel_client.post(path, json=request)
    assert response.status_code == 200, response.text
    independent = great_conjunctions(start, end, reader=moira_engine._reader)
    mundane = moira_engine.jupiter_saturn_sequence_from_series(independent)
    payload = response.json()
    assert len(payload["roots"]) == 3
    assert [root["jd_ut1"] for root in payload["roots"]] == pytest.approx(
        [root.epoch.jd for root in mundane.roots], abs=1e-8, rel=0,
    )
    assert len(payload["zodiac_projection"]) == 3

    def relative_longitude(jd):
        jupiter = planet_at("Jupiter", jd, reader=moira_engine._reader).longitude
        saturn = planet_at("Saturn", jd, reader=moira_engine._reader).longitude
        return (jupiter - saturn + 180.0) % 360.0 - 180.0

    for root in payload["roots"]:
        jd = root["jd_ut1"]
        assert relative_longitude(jd - 0.001) * relative_longitude(jd + 0.001) < 0
        assert abs(relative_longitude(jd)) < 1e-7


def test_great_conjunction_boundary_and_empty_intervals(kernel_client):
    """Include the represented 2020 root at both endpoints and preserve emptiness."""
    root = 2459205.264318665
    path = "/v1/phenomena/great-conjunctions"
    for start, end in [(root, root + 1), (root - 1, root)]:
        response = kernel_client.post(path, json={"jd_start_ut1": start, "jd_end_ut1": end})
        assert response.status_code == 200, response.text
        assert [event["jd_ut1"] for event in response.json()["roots"]] == [root]
        assert response.json()["zodiac_projection"] is None
    empty = kernel_client.post(path, json={"jd_start_ut1": root + 1, "jd_end_ut1": root + 2})
    assert empty.status_code == 200 and empty.json()["roots"] == []


def test_great_conjunctions_distinguish_missing_coverage(kernel_client, monkeypatch):
    """Propagate the actual coverage error rather than returning an empty sequence."""
    def lacking_coverage(*args, **kwargs):
        raise OutOfRangeError("range exceeded source coverage", [2459210.0])

    monkeypatch.setattr("moira_server.services.bounded_searches.great_conjunctions", lacking_coverage)
    response = kernel_client.post("/v1/phenomena/great-conjunctions", json={
        "jd_start_ut1": 2459205.0, "jd_end_ut1": 2459210.0,
    })
    assert response.status_code == 422
    assert response.json()["category"] == "ephemeris_coverage"


_GEOCENTRIC_CONJUNCTION_PATH = "/v1/phenomena/geocentric-conjunctions"
_GEOCENTRIC_CONJUNCTION_REQUEST = {
    "body1": "Jupiter", "body2": "Saturn", "jd_start_ut1": 2459204.0, "jd_end_ut1": 2459207.0,
}


def test_geocentric_conjunction_receipt_proves_a_crossing_and_empty_window(kernel_client, moira_engine):
    response = kernel_client.post(_GEOCENTRIC_CONJUNCTION_PATH, json=_GEOCENTRIC_CONJUNCTION_REQUEST)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["request"] == _GEOCENTRIC_CONJUNCTION_REQUEST
    assert payload["status"] == "complete"
    assert payload["unresolved_intervals"] == []
    assert payload["interval_ownership"] == "inclusive_represented_ut1_roots"
    assert payload["computation_truth"]["center"] == "geocenter"
    assert payload["computation_truth"]["reference_frame"] == "apparent_geocentric_true_ecliptic_of_date"
    assert payload["computation_truth"]["post_event_advance_days"] == 0.0
    assert payload["planetary_ephemeris"] == "DE441"
    assert payload["source_sha256"] and all(len(digest) == 64 for digest in payload["source_sha256"])
    assert payload["work"]["excluded_intervals"] > 0

    root, = payload["roots"]
    assert root["jd_ut1"] == 2459205.264318665
    position = planet_at("Jupiter", root["jd_ut1"], reader=moira_engine._reader, apparent=True)
    assert root["longitude_deg"] == pytest.approx(position.longitude, abs=1e-9, rel=0)
    witness = root["witness"]
    assert witness["lower_jd_ut1"] < root["jd_ut1"] < witness["upper_jd_ut1"]
    assert witness["lower_offset_deg"][1] < 0.0 < witness["upper_offset_deg"][0]
    assert witness["direction"] == 1 and witness["relative_rate_deg_per_day"][0] > 0.0

    empty = kernel_client.post(_GEOCENTRIC_CONJUNCTION_PATH, json={
        **_GEOCENTRIC_CONJUNCTION_REQUEST, "jd_start_ut1": 2459206.0,
    })
    assert empty.status_code == 200, empty.text
    assert empty.json()["status"] == "complete"
    assert empty.json()["roots"] == empty.json()["unresolved_intervals"] == []


def test_geocentric_conjunction_receipt_keeps_unresolved_intervals(kernel_client, monkeypatch):
    gap = GeocentricConjunctionUnresolved(2459205.0, 2459205.1, "crossing_existence_or_multiplicity_unresolved")
    monkeypatch.setattr(
        "moira._geocentric_conjunctions._resolve_crossings", lambda *args: ((), (gap,), 0),
    )
    response = kernel_client.post(_GEOCENTRIC_CONJUNCTION_PATH, json=_GEOCENTRIC_CONJUNCTION_REQUEST)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "unresolved" and payload["roots"] == []
    assert payload["unresolved_intervals"] == [{
        "lower_jd_ut1": 2459205.0, "upper_jd_ut1": 2459205.1,
        "reason": "crossing_existence_or_multiplicity_unresolved",
    }]


@pytest.mark.parametrize(("failure", "category"), [
    (OutOfRangeError("private ephemeris path", [2459205.0]), "ephemeris_coverage"),
    (GeocentricConjunctionBudgetError("evaluations", 1, 2, "apparent_conjunction_search"), "search_budget"),
])
def test_geocentric_conjunction_distinguishes_coverage_and_budget(kernel_client, monkeypatch, failure, category):
    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr("moira_server.services.bounded_searches.conjunctions_in_range_with_truth", fail)
    response = kernel_client.post(_GEOCENTRIC_CONJUNCTION_PATH, json=_GEOCENTRIC_CONJUNCTION_REQUEST)
    assert response.status_code == 422
    assert response.json()["category"] == category
    assert "private ephemeris path" not in response.text


@pytest.mark.parametrize("changes", [
    {"body2": "Jupiter"}, {"body1": "Earth"}, {"jd_end_ut1": 2459204.0},
    {"jd_end_ut1": 2459240.0}, {"jd_start_ut1": 2400000.0, "jd_end_ut1": 2400001.0},
])
def test_geocentric_conjunction_rejects_unsupported_searches(kernel_client, changes):
    response = kernel_client.post(
        _GEOCENTRIC_CONJUNCTION_PATH, json={**_GEOCENTRIC_CONJUNCTION_REQUEST, **changes},
    )
    assert response.status_code == 422


def test_explicit_stellar_setting_and_catalogue_share_the_same_evidence(kernel_client):
    """Observe the Regulus doctrine split and enforce a deterministic batch budget."""
    request = {"jd_start": 2451545.0, "lat": 30.0, "lon": 31.0, "search_window_days": 250}
    path = "/v1/heliacal/visibility-event"
    setting = {"body": "Regulus", "kind": "heliacal_setting"}
    generic = kernel_client.post(path, json={**request, **setting})
    explicit = kernel_client.post(path, json={**request, **setting, "criterion": "named_star_setting"})
    assert generic.status_code == explicit.status_code == 200
    selected = explicit.json()
    assert selected["status"] == "found", selected
    receipt = selected["stellar_evidence"]
    assert receipt["transition_confirmed"] is True
    assert abs(receipt["event_jd_ut1"] - generic.json()["jd_ut"]) > 0.5
    catalogue = kernel_client.post("/v1/heliacal/stellar-catalogue", json={
        **request, "names": ["Regulus", "Sirius"], "criterion": "named_star_setting", "max_star_days": 250,
    })
    assert catalogue.status_code == 200, catalogue.text
    results = catalogue.json()["results"]
    assert catalogue.json()["reserved_star_days"] == 250
    assert results[0] == selected
    assert results[1]["status"] == "work_limit"
    mismatch = kernel_client.post(path, json={
        **request, **setting, "criterion": "named_star_dawn_last",
    })
    assert mismatch.status_code == 422


def test_stellar_catalogue_distinguishes_rejections_and_completed_misses(kernel_client):
    """Independently verify magnitude, geometric latitude, and bounded no-event states."""
    path = "/v1/heliacal/stellar-catalogue"
    request = {
        "names": ["Regulus", "Sirius"], "jd_start": 2451545.0,
        "lat": 30.0, "lon": 31.0, "criterion": "named_star_setting", "search_window_days": 1,
    }
    response = kernel_client.post(path, json={**request, "max_magnitude": 0})
    assert response.status_code == 200, response.text
    assert [item["status"] for item in response.json()["results"]] == ["magnitude_rejected", "not_found"]
    response = kernel_client.post(path, json={
        **request, "names": ["Capella"], "lat": 80.0, "criterion": "named_star_dawn_last",
    })
    assert response.status_code == 200, response.text
    assert response.json()["results"][0]["status"] == "latitude_rejected"
    assert response.json()["results"][0]["kind"] == "last_morning_visibility"


def test_lunar_yallop_reports_observation_availability(kernel_client):
    """Return the admitted lunar crescent model and a typed polar unavailable case."""
    path = "/v1/heliacal/visibility-event"
    request = {
        "body": "Moon", "kind": "evening_first", "jd_start": 2460397.5,
        "lat": 0.0, "lon": 0.0, "criterion": "yallop_lunar_crescent", "search_window_days": 30,
    }
    response = kernel_client.post(path, json=request)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "found"
    details = response.json()["lunar_crescent_details"]
    assert details["observation_window"] == "evening"
    assert 2460409.0 < details["best_time_jd_ut"] < 2460412.0
    morning = kernel_client.post(path, json={**request, "kind": "morning_last"})
    assert morning.status_code == 200, morning.text
    assert morning.json()["status"] == "found"
    old_crescent = morning.json()["lunar_crescent_details"]
    assert old_crescent["observation_window"] == "morning"
    assert 2460406.0 < old_crescent["best_time_jd_ut"] < 2460409.0
    polar = kernel_client.post(path, json={
        **request, "lat": 90.0, "jd_start": 2460480.0, "search_window_days": 2,
    })
    assert polar.status_code == 200, polar.text
    assert polar.json()["status"] == "observation_unavailable"
    assert polar.json()["unavailable_days"] == 2


def test_catalogue_resource_failure_stays_with_its_target(kernel_client, monkeypatch):
    """Retain the missing-resource result within the ordered catalogue."""
    def missing_resource(*args, **kwargs):
        raise MissingEphemerisKernelError("source details")

    monkeypatch.setattr("moira_server.services.bounded_searches.heliacal_catalog_batch", missing_resource)
    response = kernel_client.post("/v1/heliacal/stellar-catalogue", json={
        "names": ["Sirius", "Regulus"], "jd_start": 2451545.0, "lat": 30.0, "lon": 31.0,
        "criterion": "named_star_setting", "search_window_days": 2, "max_star_days": 2,
    })
    assert response.status_code == 200, response.text
    assert [r["status"] for r in response.json()["results"]] == ["resource_unavailable", "work_limit"]
    assert "source details" not in response.text
