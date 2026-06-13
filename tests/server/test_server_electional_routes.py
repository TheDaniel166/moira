"""P13-01 bounded electional-window route admission tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from moira.houses import HouseCusps, classify_house_system
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


class _FakeEngine:
    _reader = "READER"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())

    def fake_chart(*, jd_ut, latitude, longitude, house_system, bodies, reader):
        assert reader == "READER"
        sun = (jd_ut * 10.0) % 360.0
        moon = (sun + 60.0) % 360.0
        houses = HouseCusps(
            system=house_system,
            effective_system=house_system,
            classification=classify_house_system(house_system),
            cusps=tuple(float(i * 30.0) for i in range(12)),
            asc=0.0,
            mc=90.0,
            armc=90.0,
        )
        return SimpleNamespace(
            jd_ut=jd_ut,
            planets={
                "Sun": SimpleNamespace(longitude=sun),
                "Moon": SimpleNamespace(longitude=moon),
                "Mars": SimpleNamespace(longitude=(sun + 90.0) % 360.0),
            },
            nodes={},
            houses=houses,
        )

    monkeypatch.setattr("moira.electional.create_chart", fake_chart)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _assert_validation_envelope(response, *, message_fragment: str) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    assert message_fragment in body["message"]


def test_predicate_profiles_route_lists_stage_one_profiles(client: TestClient) -> None:
    response = client.get("/v1/electional/predicate-profiles")

    assert response.status_code == 200
    body = response.json()
    ids = {profile["profile_id"] for profile in body["profiles"]}
    assert ids == {
        "body_longitude_range_v1",
        "body_house_membership_v1",
        "body_angular_separation_range_v1",
    }
    assert body["bounds"]["max_scan_points"] == 1000
    assert body["provenance"]["western_electional_doctrine"] == "not_admitted"


def test_scorer_profiles_route_lists_stage_one_profiles(client: TestClient) -> None:
    response = client.get("/v1/electional/scorer-profiles")

    assert response.status_code == 200
    body = response.json()
    ids = {profile["profile_id"] for profile in body["profiles"]}
    assert ids == {
        "body_longitude_target_closeness_v1",
        "body_angular_separation_target_closeness_v1",
    }
    assert body["bounds"]["max_windows"] == 64
    assert body["provenance"]["score_scale"] == [0.0, 1.0]
    assert body["provenance"]["score_direction"] == "higher_is_closer_numeric_fit"
    assert body["provenance"]["western_electional_doctrine"] == "not_admitted"


def test_windows_route_returns_longitude_range_scan_witnesses(client: TestClient) -> None:
    response = client.post(
        "/v1/electional/windows",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 5.0,
            },
            "policy": {"step_days": 0.25, "bodies": ["Sun"]},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["predicate"]["owner"] == "server_defined"
    assert body["predicate"]["doctrine_status"] == "scan_predicate_not_electional_judgement"
    assert body["policy"]["effective_step_days"] == 0.25
    assert body["policy"]["effective_merge_gap_days"] == pytest.approx(0.375)
    assert body["policy"]["effective_bodies"] == ["Sun"]
    assert body["scan"] == {
        "jd_start": 0.0,
        "jd_end": 1.0,
        "span_days": 1.0,
        "scan_point_count": 5,
        "discrete_scan": True,
        "continuous_truth_claimed": False,
        "exact_boundary_claimed": False,
    }
    assert len(body["windows"]) == 1
    assert body["windows"][0]["qualifying_jds"] == [0.0, 0.25, 0.5]
    assert body["windows"][0]["window_kind"] == "merged_scan_witness"
    assert body["validation"] == {"included": True, "passed": True, "failures": []}
    provenance = body["provenance"]
    assert provenance["scan_semantics"] == "discrete_sampled_chart_states"
    assert provenance["western_electional_doctrine"] == "not_admitted"
    assert provenance["advice_language"] == "not_provided"
    assert provenance["moments_route"] == "admitted_separately_in_p13_02"


def test_scored_route_returns_longitude_target_closeness_scores(client: TestClient) -> None:
    response = client.post(
        "/v1/electional/scored",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 10.0,
            },
            "scorer_profile": "body_longitude_target_closeness_v1",
            "scorer_parameters": {
                "subject": "Sun",
                "target_longitude": 5.0,
                "max_orb": 10.0,
            },
            "policy": {"step_days": 0.25, "bodies": ["Sun"]},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["predicate"]["owner"] == "server_defined"
    assert body["scorer"] == {
        "profile_id": "body_longitude_target_closeness_v1",
        "profile_version": "1",
        "parameters": {"subject": "Sun", "target_longitude": 5.0, "max_orb": 10.0},
        "owner": "server_defined",
        "score_scale": [0.0, 1.0],
        "score_direction": "higher_is_closer_numeric_fit",
        "doctrine_status": "numeric_fit_not_electional_judgement",
    }
    assert body["policy"]["max_windows_semantics"] == "chronological_early_exit"
    assert body["scan"]["exact_peak_claimed"] is False
    assert len(body["scored_windows"]) == 1
    scored = body["scored_windows"][0]
    assert scored["qualifying_jds"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert scored["score"] == pytest.approx(1.0)
    assert scored["peak_jd"] == pytest.approx(0.5)
    assert scored["score_rank"] == 1
    assert scored["peak_kind"] == "highest_scored_qualifying_scan_point"
    assert body["score_summary"] == {
        "count": 1,
        "highest_score": 1.0,
        "lowest_score": 1.0,
        "score_rank_basis": "score_desc_peak_jd_asc_window_start_asc",
        "rank_scope": "returned_windows_only",
        "global_best_claimed": False,
    }
    provenance = body["provenance"]
    assert provenance["engine_entrypoint"] == "find_scored_windows"
    assert provenance["score_semantics"] == "numeric_fit_to_declared_scorer_profile"
    assert provenance["score_rank_semantics"] == "returned_windows_only"
    assert provenance["peak_semantics"] == "highest_scored_qualifying_scan_point"
    assert provenance["western_electional_doctrine"] == "not_admitted"
    assert provenance["advice_language"] == "not_provided"
    assert provenance["recommendation_language"] == "not_provided"


def test_scored_route_supports_angular_separation_target_closeness(client: TestClient) -> None:
    response = client.post(
        "/v1/electional/scored",
        json={
            "jd_start": 0.0,
            "jd_end": 0.5,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_angular_separation_range_v1",
            "predicate_parameters": {
                "subject_a": "Sun",
                "subject_b": "Moon",
                "min_angle": 59.0,
                "max_angle": 61.0,
            },
            "scorer_profile": "body_angular_separation_target_closeness_v1",
            "scorer_parameters": {
                "subject_a": "Sun",
                "subject_b": "Moon",
                "target_angle": 60.0,
                "max_orb": 5.0,
            },
            "policy": {"step_days": 0.25, "bodies": ["Sun", "Moon"]},
            "include_qualifying_jds": False,
            "include_score_rank": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["scored_windows"]) == 1
    scored = body["scored_windows"][0]
    assert scored["qualifying_count"] == 3
    assert scored["qualifying_jds"] is None
    assert scored["score"] == pytest.approx(1.0)
    assert scored["peak_jd"] == pytest.approx(0.0)
    assert scored["score_rank"] is None


def test_windows_route_supports_house_membership_predicate(client: TestClient) -> None:
    response = client.post(
        "/v1/electional/windows",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_house_membership_v1",
            "predicate_parameters": {"subject": "Moon", "houses": [3]},
            "policy": {"step_days": 0.25, "bodies": ["Moon"], "house_system": "P"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["windows"]) == 1
    assert body["windows"][0]["qualifying_jds"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert body["policy"]["effective_house_system"] == "P"


def test_windows_route_supports_angular_separation_predicate(client: TestClient) -> None:
    response = client.post(
        "/v1/electional/windows",
        json={
            "jd_start": 0.0,
            "jd_end": 0.5,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_angular_separation_range_v1",
            "predicate_parameters": {
                "subject_a": "Sun",
                "subject_b": "Moon",
                "min_angle": 59.0,
                "max_angle": 61.0,
            },
            "policy": {"step_days": 0.25, "bodies": ["Sun", "Moon"]},
            "include_qualifying_jds": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["windows"]) == 1
    assert body["windows"][0]["qualifying_count"] == 3
    assert body["windows"][0]["qualifying_jds"] is None


def test_windows_route_can_return_empty_result(client: TestClient) -> None:
    response = client.post(
        "/v1/electional/windows",
        json={
            "jd_start": 0.0,
            "jd_end": 0.5,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 100.0,
                "end_longitude": 110.0,
            },
            "policy": {"step_days": 0.25, "bodies": ["Sun"]},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["windows"] == []
    assert body["scan"]["scan_point_count"] == 3


def test_moments_route_returns_longitude_range_scan_points(client: TestClient) -> None:
    response = client.post(
        "/v1/electional/moments",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 5.0,
            },
            "policy": {"step_days": 0.25, "bodies": ["Sun"]},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["predicate"]["owner"] == "server_defined"
    assert body["policy"]["effective_step_days"] == 0.25
    assert body["policy"]["effective_bodies"] == ["Sun"]
    assert body["policy"]["max_windows_applicable"] is False
    assert body["policy"]["effective_max_windows"] is None
    assert body["policy"]["boundary_refinement_applicable"] is False
    assert body["scan"] == {
        "jd_start": 0.0,
        "jd_end": 1.0,
        "span_days": 1.0,
        "scan_point_count": 5,
        "discrete_scan": True,
        "continuous_truth_claimed": False,
        "exact_boundary_claimed": False,
    }
    assert body["moments"] == {
        "count": 3,
        "jds": [0.0, 0.25, 0.5],
        "first_jd": 0.0,
        "last_jd": 0.5,
        "moment_kind": "qualifying_scan_point",
        "sorted_temporally": True,
    }
    provenance = body["provenance"]
    assert provenance["engine_entrypoint"] == "find_electional_moments"
    assert provenance["moment_semantics"] == "raw_qualifying_scan_points"
    assert provenance["window_merge"] == "not_applied"
    assert provenance["boundary_semantics"] == "not_applicable_to_raw_moments"
    assert provenance["western_electional_doctrine"] == "not_admitted"


def test_moments_route_supports_house_membership_predicate(client: TestClient) -> None:
    response = client.post(
        "/v1/electional/moments",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_house_membership_v1",
            "predicate_parameters": {"subject": "Moon", "houses": [3]},
            "policy": {"step_days": 0.25, "bodies": ["Moon"], "house_system": "P"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["moments"]["jds"] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert body["policy"]["effective_house_system"] == "P"


def test_moments_route_supports_angular_separation_predicate(client: TestClient) -> None:
    response = client.post(
        "/v1/electional/moments",
        json={
            "jd_start": 0.0,
            "jd_end": 0.5,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_angular_separation_range_v1",
            "predicate_parameters": {
                "subject_a": "Sun",
                "subject_b": "Moon",
                "min_angle": 59.0,
                "max_angle": 61.0,
            },
            "policy": {"step_days": 0.25, "bodies": ["Sun", "Moon"]},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["moments"]["count"] == 3
    assert body["moments"]["jds"] == [0.0, 0.25, 0.5]


def test_moments_route_can_omit_raw_moment_list_and_return_empty_result(client: TestClient) -> None:
    response = client.post(
        "/v1/electional/moments",
        json={
            "jd_start": 0.0,
            "jd_end": 0.5,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 100.0,
                "end_longitude": 110.0,
            },
            "policy": {"step_days": 0.25, "bodies": ["Sun"]},
            "include_moments": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["moments"] == {
        "count": 0,
        "jds": None,
        "first_jd": None,
        "last_jd": None,
        "moment_kind": "qualifying_scan_point",
        "sorted_temporally": True,
    }
    assert body["scan"]["scan_point_count"] == 3


def test_windows_route_rejects_invalid_inputs(client: TestClient) -> None:
    reversed_window = client.post(
        "/v1/electional/windows",
        json={
            "jd_start": 2.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 1.0,
            },
        },
    )
    bad_profile = client.post(
        "/v1/electional/windows",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "freeform_python",
            "predicate_parameters": {},
        },
    )
    bad_subject = client.post(
        "/v1/electional/windows",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "North Node",
                "start_longitude": 0.0,
                "end_longitude": 1.0,
            },
        },
    )
    missing_required_body = client.post(
        "/v1/electional/windows",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 1.0,
            },
            "policy": {"bodies": ["Moon"]},
        },
    )
    scan_overflow = client.post(
        "/v1/electional/windows",
        json={
            "jd_start": 0.0,
            "jd_end": 20.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 1.0,
            },
            "policy": {"step_days": 0.011},
        },
    )
    bad_boundary_controls = client.post(
        "/v1/electional/windows",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 1.0,
            },
            "policy": {"boundary_refine_steps": 1},
            "include_boundary_brackets": False,
        },
    )
    bad_house_frame = client.post(
        "/v1/electional/windows",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_house_membership_v1",
            "predicate_parameters": {"subject": "Moon", "houses": [3]},
            "policy": {"zodiac_frame": "sidereal"},
        },
    )
    bad_moment_boundary = client.post(
        "/v1/electional/moments",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 1.0,
            },
            "policy": {"boundary_refine_steps": 1},
        },
    )

    _assert_validation_envelope(reversed_window, message_fragment="jd_end must be greater")
    _assert_validation_envelope(bad_profile, message_fragment="Input should be")
    _assert_validation_envelope(bad_subject, message_fragment="must be one of")
    _assert_validation_envelope(
        missing_required_body,
        message_fragment="policy.bodies must include predicate-required or scorer-required subjects",
    )
    _assert_validation_envelope(scan_overflow, message_fragment="scan point count")
    _assert_validation_envelope(
        bad_boundary_controls,
        message_fragment="boundary_refine_steps requires include_boundary_brackets=true",
    )
    _assert_validation_envelope(
        bad_house_frame,
        message_fragment="body_house_membership_v1 supports tropical evaluation only",
    )
    _assert_validation_envelope(
        bad_moment_boundary,
        message_fragment="boundary_refine_steps must be 0 for electional moments",
    )


def test_scored_route_rejects_invalid_inputs(client: TestClient) -> None:
    bad_profile = client.post(
        "/v1/electional/scored",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 1.0,
            },
            "scorer_profile": "freeform_python",
            "scorer_parameters": {},
        },
    )
    bad_orb = client.post(
        "/v1/electional/scored",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 1.0,
            },
            "scorer_profile": "body_longitude_target_closeness_v1",
            "scorer_parameters": {
                "subject": "Sun",
                "target_longitude": 5.0,
                "max_orb": 0.0,
            },
        },
    )
    missing_scorer_body = client.post(
        "/v1/electional/scored",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 1.0,
            },
            "scorer_profile": "body_angular_separation_target_closeness_v1",
            "scorer_parameters": {
                "subject_a": "Sun",
                "subject_b": "Moon",
                "target_angle": 60.0,
                "max_orb": 5.0,
            },
            "policy": {"bodies": ["Sun"]},
        },
    )
    bad_rank_flag = client.post(
        "/v1/electional/scored",
        json={
            "jd_start": 0.0,
            "jd_end": 1.0,
            "latitude": 0.0,
            "longitude": 0.0,
            "predicate_profile": "body_longitude_range_v1",
            "predicate_parameters": {
                "subject": "Sun",
                "start_longitude": 0.0,
                "end_longitude": 1.0,
            },
            "scorer_profile": "body_longitude_target_closeness_v1",
            "scorer_parameters": {
                "subject": "Sun",
                "target_longitude": 5.0,
                "max_orb": 10.0,
            },
            "include_score_rank": "yes",
        },
    )

    _assert_validation_envelope(bad_profile, message_fragment="Input should be")
    _assert_validation_envelope(bad_orb, message_fragment="max_orb must be in")
    _assert_validation_envelope(
        missing_scorer_body,
        message_fragment="policy.bodies must include predicate-required or scorer-required subjects",
    )
    _assert_validation_envelope(bad_rank_flag, message_fragment="include_score_rank")


def test_electional_routes_are_registered(client: TestClient) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/electional/")
    }

    assert paths == {
        "/v1/electional/predicate-profiles",
        "/v1/electional/scorer-profiles",
        "/v1/electional/moments",
        "/v1/electional/scored",
        "/v1/electional/windows",
    }
