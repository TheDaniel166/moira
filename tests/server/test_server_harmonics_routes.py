"""P12-02 Stage 1 harmonic projection route admission tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.constants import TROPICAL_YEAR
from moira.harmonics import (
    HARMONIC_PRESETS,
    age_harmonic,
    calculate_harmonic,
    composite_harmonic,
    harmonic_aspects,
    harmonic_conjunctions,
    harmonic_pattern_score,
    harmonic_sweep,
    vibrational_fingerprint,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeEngine:
    pass


_LONS = {
    "Sun": 10.0,
    "Moon": 82.0,
    "Mercury": 30.0,
    "Venus": 154.0,
    "Mars": 244.0,
    "Jupiter": 310.0,
    "Saturn": 358.0,
}


_LONS_PAIR = {"Sun": 10.0, "Moon": 82.0}
_LONS_B = {"Sun": 154.0, "Moon": 244.0}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
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


def test_harmonic_presets_route_preserves_catalog_truth(client: TestClient) -> None:
    response = client.get("/v1/harmonics/presets")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(HARMONIC_PRESETS)
    assert body["presets"] == [
        {
            "harmonic": harmonic,
            "name": name,
            "description": description,
        }
        for harmonic, (name, description) in sorted(HARMONIC_PRESETS.items())
    ]
    assert body["bounds"] == {
        "max_body_count": 64,
        "max_composite_body_count": 32,
        "max_harmonic": 128,
        "default_max_harmonic": 32,
        "max_orb": 30.0,
        "max_label_length": 64,
    }
    assert body["provenance"]["source_module"] == "moira.harmonics"
    assert body["provenance"]["engine_entrypoint"] == "HARMONIC_PRESETS"
    assert body["provenance"]["input_longitude_owner"] == "caller_supplied"
    assert body["provenance"]["chart_construction_owner"] == "not_this_route"
    assert body["provenance"]["stage_sequence"] == [
        "preset_catalog_read",
        "harmonic_preset_serialization",
    ]


def test_harmonic_chart_route_preserves_h1_identity_and_engine_sorting(
    client: TestClient,
) -> None:
    longitudes = {"Sun": 10.0, "Moon": 82.0, "Mars": 244.0}
    direct = calculate_harmonic(longitudes, 1)

    response = client.post(
        "/v1/harmonics/chart",
        json={"longitudes": longitudes, "harmonic": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_harmonic"] == 1.0
    assert body["effective_harmonic"] == 1.0
    assert body["harmonic_kind"] == "integer"
    assert body["input_count"] == len(longitudes)
    assert [position["body"] for position in body["positions"]] == [
        position.planet for position in direct
    ]
    for response_position, direct_position in zip(body["positions"], direct, strict=True):
        assert response_position["natal_longitude"] == pytest.approx(
            direct_position.natal_longitude
        )
        assert response_position["harmonic_longitude"] == pytest.approx(
            direct_position.harmonic_longitude
        )
        assert response_position["harmonic"] == pytest.approx(direct_position.harmonic)
        assert response_position["sign"] == direct_position.sign
        assert response_position["sign_symbol"] == direct_position.sign_symbol
        assert response_position["sign_degree"] == pytest.approx(direct_position.sign_degree)
    assert [p["harmonic_longitude"] for p in body["positions"]] == sorted(
        p["harmonic_longitude"] for p in body["positions"]
    )


def test_harmonic_chart_route_preserves_h5_formula_and_preset_provenance(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/harmonics/chart",
        json={"longitudes": {"Sun": 10.0, "Moon": 82.0}, "harmonic": 5},
    )

    assert response.status_code == 200
    body = response.json()
    by_body = {position["body"]: position for position in body["positions"]}
    assert by_body["Sun"]["harmonic_longitude"] == pytest.approx((10.0 * 5.0) % 360.0)
    assert by_body["Moon"]["harmonic_longitude"] == pytest.approx((82.0 * 5.0) % 360.0)
    assert body["provenance"]["engine_entrypoint"] == "calculate_harmonic"
    assert body["provenance"]["harmonic_kind"] == "integer"
    assert body["provenance"]["preset_name"] == HARMONIC_PRESETS[5][0]
    assert body["provenance"]["preset_description"] == HARMONIC_PRESETS[5][1]
    assert body["provenance"]["stage_sequence"] == [
        "caller_longitude_validation",
        "integer_harmonic_validation",
        "harmonic_projection_computation",
        "harmonic_chart_response_serialization",
    ]


def test_age_harmonic_route_preserves_decimal_harmonic(client: TestClient) -> None:
    longitudes = {"Sun": 10.0, "Moon": 82.0}
    jd_birth = 2451545.0
    jd_now = jd_birth + (37.5 * TROPICAL_YEAR)
    direct = age_harmonic(longitudes, jd_birth, jd_now)

    response = client.post(
        "/v1/harmonics/age-chart",
        json={
            "longitudes": longitudes,
            "jd_birth": jd_birth,
            "jd_now": jd_now,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_harmonic"] == pytest.approx(37.5)
    assert body["effective_harmonic"] == pytest.approx(37.5)
    assert body["harmonic_kind"] == "age_decimal"
    for response_position, direct_position in zip(body["positions"], direct, strict=True):
        assert response_position["body"] == direct_position.planet
        assert response_position["harmonic"] == pytest.approx(direct_position.harmonic)
        assert response_position["harmonic_longitude"] == pytest.approx(
            direct_position.harmonic_longitude
        )
    provenance = body["provenance"]
    assert provenance["engine_entrypoint"] == "age_harmonic"
    assert provenance["jd_birth"] == pytest.approx(jd_birth)
    assert provenance["jd_now"] == pytest.approx(jd_now)
    assert provenance["age_harmonic_basis"] == "(jd_now - jd_birth) / tropical_year"
    assert provenance["stage_sequence"] == [
        "caller_longitude_validation",
        "age_window_validation",
        "decimal_age_harmonic_derivation",
        "harmonic_projection_computation",
        "age_harmonic_response_serialization",
    ]


def test_harmonic_routes_are_registered(client: TestClient) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/harmonics/")
    }

    assert paths == {
        "/v1/harmonics/presets",
        "/v1/harmonics/chart",
        "/v1/harmonics/age-chart",
        "/v1/harmonics/conjunctions",
        "/v1/harmonics/pattern-score",
        "/v1/harmonics/aspects",
        "/v1/harmonics/sweep",
        "/v1/harmonics/fingerprint",
        "/v1/harmonics/composite",
        "/v1/harmonics/transit-forecast",
    }


def test_harmonic_chart_route_rejects_invalid_longitude_maps(
    client: TestClient,
) -> None:
    empty = client.post(
        "/v1/harmonics/chart",
        json={"longitudes": {}, "harmonic": 5},
    )
    empty_name = client.post(
        "/v1/harmonics/chart",
        json={"longitudes": {" ": 10.0}, "harmonic": 5},
    )
    duplicate_after_trim = client.post(
        "/v1/harmonics/chart",
        json={"longitudes": {"Sun": 10.0, " Sun ": 20.0}, "harmonic": 5},
    )
    non_finite = client.post(
        "/v1/harmonics/chart",
        json={"longitudes": {"Sun": "NaN"}, "harmonic": 5},
    )

    _assert_validation_envelope(empty, message_fragment="at least one body")
    _assert_validation_envelope(empty_name, message_fragment="body names must be non-empty")
    _assert_validation_envelope(duplicate_after_trim, message_fragment="unique after trimming")
    _assert_validation_envelope(non_finite, message_fragment="values must be real numbers")


@pytest.mark.parametrize("longitude", [True, "10.0"])
def test_harmonic_routes_reject_coercive_longitude_scalars(
    client: TestClient,
    longitude,
) -> None:
    responses = (
        client.post(
            "/v1/harmonics/chart",
            json={"longitudes": {"Sun": longitude}, "harmonic": 5},
        ),
        client.post(
            "/v1/harmonics/age-chart",
            json={
                "longitudes": {"Sun": longitude},
                "jd_birth": 1.0,
                "jd_now": 2.0,
            },
        ),
        client.post(
            "/v1/harmonics/aspects",
            json={"longitudes": {"Sun": longitude}},
        ),
        client.post(
            "/v1/harmonics/composite",
            json={
                "longitudes_a": {"Sun": longitude},
                "longitudes_b": {"Moon": 72.0},
                "harmonic": 5,
            },
        ),
    )

    for response in responses:
        _assert_validation_envelope(response, message_fragment="real numbers")


def test_harmonic_chart_route_rejects_invalid_harmonic_and_oversized_body_map(
    client: TestClient,
) -> None:
    invalid_harmonic = client.post(
        "/v1/harmonics/chart",
        json={"longitudes": {"Sun": 10.0}, "harmonic": 0},
    )
    oversized = client.post(
        "/v1/harmonics/chart",
        json={
            "longitudes": {f"Body{i}": float(i) for i in range(65)},
            "harmonic": 5,
        },
    )

    _assert_validation_envelope(invalid_harmonic, message_fragment="greater than or equal to 1")
    _assert_validation_envelope(oversized, message_fragment="at most 64 bodies")


def test_age_harmonic_route_rejects_negative_age_and_non_finite_jd(
    client: TestClient,
) -> None:
    negative_age = client.post(
        "/v1/harmonics/age-chart",
        json={
            "longitudes": {"Sun": 10.0},
            "jd_birth": 2451545.0,
            "jd_now": 2451544.0,
        },
    )
    non_finite_jd = client.post(
        "/v1/harmonics/age-chart",
        json={
            "longitudes": {"Sun": 10.0},
            "jd_birth": "NaN",
            "jd_now": 2451545.0,
        },
    )

    _assert_validation_envelope(
        negative_age,
        message_fragment="jd_now must be greater than or equal to jd_birth",
    )
    _assert_validation_envelope(non_finite_jd, message_fragment="Julian Day values must be finite")


def test_harmonic_conjunctions_route_matches_engine_truth(client: TestClient) -> None:
    direct = harmonic_conjunctions(_LONS_PAIR, 5, orb=0.001)

    response = client.post(
        "/v1/harmonics/conjunctions",
        json={"longitudes": _LONS_PAIR, "harmonic": 5, "orb": 0.001},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_harmonic"] == 5.0
    assert body["effective_harmonic"] == 5.0
    assert body["orb"] == pytest.approx(0.001)
    assert body["input_count"] == len(_LONS_PAIR)
    assert body["conjunctions"] == [
        {
            "planet_a": conjunction.planet_a,
            "planet_b": conjunction.planet_b,
            "harmonic": conjunction.harmonic,
            "orb": pytest.approx(conjunction.orb),
            "longitude": pytest.approx(conjunction.longitude),
        }
        for conjunction in direct
    ]
    assert body["provenance"]["engine_entrypoint"] == "harmonic_conjunctions"
    assert body["provenance"]["stage_sequence"] == [
        "caller_longitude_validation",
        "integer_harmonic_validation",
        "orb_validation",
        "harmonic_conjunction_computation",
        "harmonic_conjunction_response_serialization",
    ]


def test_harmonic_pattern_score_route_preserves_cluster_invariants(
    client: TestClient,
) -> None:
    direct = harmonic_pattern_score(_LONS, 5, orb=0.001)

    response = client.post(
        "/v1/harmonics/pattern-score",
        json={"longitudes": _LONS, "harmonic": 5, "orb": 0.001},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pattern_score"] == pytest.approx(direct.score)
    assert body["score"] == pytest.approx(direct.score)
    assert body["cluster_sizes"] == list(direct.cluster_sizes)
    assert len(body["conjunctions"]) == len(direct.conjunctions)
    assert body["provenance"]["engine_entrypoint"] == "harmonic_pattern_score"
    assert "density measure" in body["provenance"]["note"]


def test_harmonic_aspects_route_matches_conjunction_dual_path(
    client: TestClient,
) -> None:
    direct_aspects = harmonic_aspects(_LONS, orb=0.001, max_harmonic=5)
    direct_pairs_h5 = {
        frozenset((aspect.planet_a, aspect.planet_b))
        for aspect in direct_aspects
        if aspect.harmonic == 5
    }
    direct_conj_pairs_h5 = {
        frozenset((conjunction.planet_a, conjunction.planet_b))
        for conjunction in harmonic_conjunctions(_LONS, 5, orb=0.001)
    }

    response = client.post(
        "/v1/harmonics/aspects",
        json={"longitudes": _LONS, "orb": 0.001, "max_harmonic": 5},
    )

    assert response.status_code == 200
    body = response.json()
    response_pairs_h5 = {
        frozenset((aspect["planet_a"], aspect["planet_b"]))
        for aspect in body["aspects"]
        if aspect["harmonic"] == 5
    }
    assert response_pairs_h5 == direct_pairs_h5
    assert response_pairs_h5 == direct_conj_pairs_h5
    assert body["max_harmonic"] == 5
    assert body["orb"] == pytest.approx(0.001)
    assert body["provenance"]["engine_entrypoint"] == "harmonic_aspects"


def test_harmonic_sweep_route_preserves_bounded_ordering_and_count(
    client: TestClient,
) -> None:
    direct = harmonic_sweep(_LONS, max_harmonic=12, orb=0.001)

    response = client.post(
        "/v1/harmonics/sweep",
        json={"longitudes": _LONS, "max_harmonic": 12, "orb": 0.001},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["entries"]) == 12
    assert [entry["harmonic"] for entry in body["entries"]] == [
        entry.harmonic for entry in direct
    ]
    assert [entry["score"] for entry in body["entries"]] == pytest.approx(
        [entry.score for entry in direct]
    )
    assert body["bounds"]["max_harmonic"] == 128
    assert body["provenance"]["engine_entrypoint"] == "harmonic_sweep"
    assert "density measure" in body["provenance"]["note"]


def test_harmonic_fingerprint_route_preserves_peak_and_total_invariants(
    client: TestClient,
) -> None:
    direct = vibrational_fingerprint(_LONS, max_harmonic=12, orb=0.001)

    response = client.post(
        "/v1/harmonics/fingerprint",
        json={"longitudes": _LONS, "max_harmonic": 12, "orb": 0.001},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dominant"] == list(direct.dominant)
    assert body["total_score"] == pytest.approx(direct.total_score)
    assert body["peak_harmonic"] == direct.peak_harmonic
    assert body["peak_score"] == pytest.approx(direct.peak_score)
    assert body["total_score"] == pytest.approx(
        sum(entry["score"] for entry in body["sweep"])
    )
    assert body["provenance"]["engine_entrypoint"] == "vibrational_fingerprint"
    assert "density summary" in body["provenance"]["note"]


def test_harmonic_composite_route_preserves_labels_and_cross_chart_pairs(
    client: TestClient,
) -> None:
    direct = composite_harmonic(
        _LONS_PAIR,
        _LONS_B,
        harmonic=5,
        orb=2.0,
        label_a="Alice",
        label_b="Bob",
    )

    response = client.post(
        "/v1/harmonics/composite",
        json={
            "longitudes_a": _LONS_PAIR,
            "longitudes_b": _LONS_B,
            "harmonic": 5,
            "orb": 2.0,
            "label_a": "Alice",
            "label_b": "Bob",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["label_a"] == "Alice"
    assert body["label_b"] == "Bob"
    assert body["input_count_a"] == len(_LONS_PAIR)
    assert body["input_count_b"] == len(_LONS_B)
    assert len(body["conjunctions"]) == len(direct)
    for conjunction in body["conjunctions"]:
        prefix_a = conjunction["planet_a"].split(":")[0]
        prefix_b = conjunction["planet_b"].split(":")[0]
        assert prefix_a != prefix_b
        assert {prefix_a, prefix_b} == {"Alice", "Bob"}
    assert body["provenance"]["engine_entrypoint"] == "composite_harmonic"


def test_harmonic_analysis_routes_reject_invalid_or_oversized_bounds(
    client: TestClient,
) -> None:
    invalid_orb = client.post(
        "/v1/harmonics/conjunctions",
        json={"longitudes": _LONS_PAIR, "harmonic": 5, "orb": 30.1},
    )
    invalid_max_harmonic = client.post(
        "/v1/harmonics/sweep",
        json={"longitudes": _LONS_PAIR, "max_harmonic": 129, "orb": 1.0},
    )
    bad_label = client.post(
        "/v1/harmonics/composite",
        json={
            "longitudes_a": _LONS_PAIR,
            "longitudes_b": _LONS_B,
            "harmonic": 5,
            "label_a": "A:bad",
            "label_b": "B",
        },
    )
    oversized_composite = client.post(
        "/v1/harmonics/composite",
        json={
            "longitudes_a": {f"Body{i}": float(i) for i in range(33)},
            "longitudes_b": _LONS_B,
            "harmonic": 5,
        },
    )

    _assert_validation_envelope(invalid_orb, message_fragment="less than or equal to 30")
    _assert_validation_envelope(
        invalid_max_harmonic,
        message_fragment="less than or equal to 128",
    )
    _assert_validation_envelope(bad_label, message_fragment="must not contain ':'")
    _assert_validation_envelope(oversized_composite, message_fragment="at most 32 bodies")


def test_fractional_harmonic_routes_preserve_h55_without_h5_truncation(
    client: TestClient,
) -> None:
    chart_response = client.post(
        "/v1/harmonics/chart",
        json={"longitudes": {"Sun": 0.0, "Moon": 72.0}, "harmonic": 5.5},
    )
    conjunction_response = client.post(
        "/v1/harmonics/conjunctions",
        json={
            "longitudes": {"Sun": 0.0, "Moon": 72.0},
            "harmonic": 5.5,
            "orb": 1.0,
        },
    )
    score_response = client.post(
        "/v1/harmonics/pattern-score",
        json={
            "longitudes": {"Sun": 0.0, "Moon": 72.0},
            "harmonic": 5.5,
            "orb": 1.0,
        },
    )
    composite_response = client.post(
        "/v1/harmonics/composite",
        json={
            "longitudes_a": {"Sun": 0.0},
            "longitudes_b": {"Moon": 72.0},
            "harmonic": 5.5,
            "orb": 1.0,
        },
    )

    assert chart_response.status_code == 200
    chart = chart_response.json()
    by_body = {position["body"]: position for position in chart["positions"]}
    assert by_body["Moon"]["harmonic_longitude"] == pytest.approx(36.0)
    assert by_body["Moon"]["harmonic"] == 5.5
    assert chart["effective_harmonic"] == 5.5
    assert chart["harmonic_kind"] == "continuous_multiplier"
    assert chart["provenance"]["preset_name"] is None
    assert chart["provenance"]["longitude_origin"] == "zero_aries"
    assert chart["provenance"]["input_branch"] == "[0,360)"
    assert "continuous_multiplier_validation" in chart["provenance"]["stage_sequence"]

    assert conjunction_response.status_code == 200
    assert conjunction_response.json()["conjunctions"] == []
    assert score_response.status_code == 200
    assert score_response.json()["effective_harmonic"] == 5.5
    assert score_response.json()["score"] == 0.0
    assert composite_response.status_code == 200
    assert composite_response.json()["conjunctions"] == []


def test_harmonic_orb_policy_exposes_addey_source_and_projected_limits(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/harmonics/conjunctions",
        json={
            "longitudes": {"Sun": 0.0, "Moon": 73.1},
            "harmonic": 5,
            "orb": 6.0,
            "orb_policy": {"scaling_mode": "addey_inverse_harmonic"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["conjunctions"]) == 1
    assert body["conjunctions"][0]["orb"] == pytest.approx(5.5)
    truth = body["provenance"]["orb_policy"]
    assert truth == {
        "scaling_mode": "addey_inverse_harmonic",
        "reference_harmonic": 1.0,
        "reference_orb_deg": 6.0,
        "projected_orb_limit_deg": 6.0,
        "source_orb_limit_deg": 1.2,
        "resolved_harmonic": 5.0,
        "authority": "John Addey, Harmonics in Astrology, Ch. 14",
        "source_locator": "Harmonics in Astrology, Chapter 14",
        "formula": "O_H = O_1 / H",
        "continuous_extension": False,
        "request_mode": "explicit_policy",
    }


@pytest.mark.parametrize("orb", [True, "1.0"])
def test_addey_orb_surfaces_reject_coercive_scalars(
    client: TestClient,
    orb,
) -> None:
    conjunction = client.post(
        "/v1/harmonics/conjunctions",
        json={
            "longitudes": {"Sun": 0.0, "Moon": 72.0},
            "harmonic": 5,
            "orb": orb,
        },
    )
    aspects = client.post(
        "/v1/harmonics/aspects",
        json={"longitudes": {"Sun": 0.0, "Moon": 72.0}, "orb": orb},
    )
    composite = client.post(
        "/v1/harmonics/composite",
        json={
            "longitudes_a": {"Sun": 0.0},
            "longitudes_b": {"Moon": 72.0},
            "harmonic": 5,
            "orb": orb,
        },
    )

    for response in (conjunction, aspects, composite):
        _assert_validation_envelope(response, message_fragment="orb")


def test_fractional_harmonic_openapi_is_number_not_integer(client: TestClient) -> None:
    schemas = client.app.openapi()["components"]["schemas"]

    assert schemas["HarmonicChartRequest"]["properties"]["harmonic"]["type"] == "number"
    assert schemas["HarmonicCompositeRequest"]["properties"]["harmonic"]["type"] == "number"
    assert schemas["HarmonicAspectsRequest"]["properties"]["max_harmonic"]["type"] == "integer"


@pytest.mark.parametrize("harmonic", [True, "5.5", "NaN"])
def test_harmonic_chart_rejects_coercive_or_nonfinite_harmonics(
    client: TestClient,
    harmonic,
) -> None:
    response = client.post(
        "/v1/harmonics/chart",
        json={"longitudes": {"Sun": 0.0}, "harmonic": harmonic},
    )

    _assert_validation_envelope(response, message_fragment="harmonic")


def test_sampled_va_informed_harmonic_transit_forecast_route(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/harmonics/transit-forecast",
        json={
            "natal_longitudes": {"Sun": 0.0, "Moon": 72.0},
            "transit_samples": [
                {"jd_ut": 2451545.0, "longitudes": {"Mars": 144.0}},
                {"jd_ut": 2451546.0, "longitudes": {"Mars": 144.1}},
            ],
            "harmonics": [5],
            "modes": ["one_transit_two_natal"],
            "orb": 1.0,
            "orb_policy": {"scaling_mode": "addey_inverse_harmonic"},
            "minimum_observed_duration_days": 1.0,
            "maximum_sample_gap_days": 1.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["window_count"] == 1
    assert body["natal_bodies"] == ["Moon", "Sun"]
    assert body["transit_bodies"] == ["Mars"]
    assert body["transit_sample_count"] == 2
    window = body["windows"][0]
    assert window["harmonic"] == 5
    assert window["mode"] == "one_transit_two_natal"
    assert window["first_sampled_jd_ut"] == 2451545.0
    assert window["peak_sampled_jd_ut"] == 2451545.0
    assert window["last_sampled_jd_ut"] == 2451546.0
    assert window["observed_duration_days"] == 1.0
    assert window["sample_count"] == 2
    assert {member["origin"] for member in window["samples"][0]["members"]} == {
        "natal",
        "transit",
    }
    assert body["provenance"]["geometry"] == "minimum_circular_covering_arc_complete_triple"
    assert "no Sirius parity" in body["provenance"]["claim_boundary"]
    assert body["provenance"]["bounds"]["max_candidate_evaluations"] == 25_000
    assert body["policy"]["orb_policy"]["request_mode"] == "explicit_policy"


def test_harmonic_transit_forecast_accepts_reordered_sample_mapping_keys(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/harmonics/transit-forecast",
        json={
            "natal_longitudes": {"Sun": 0.0, "Moon": 72.0},
            "transit_samples": [
                {
                    "jd_ut": 2451545.0,
                    "longitudes": {"Mars": 144.0, "Venus": 10.0},
                },
                {
                    "jd_ut": 2451546.0,
                    "longitudes": {"Venus": 10.0, "Mars": 144.1},
                },
            ],
            "harmonics": [5],
            "modes": ["one_transit_two_natal"],
        },
    )

    assert response.status_code == 200
    assert response.json()["transit_bodies"] == ["Mars", "Venus"]


@pytest.mark.parametrize("longitude", [True, "144.0"])
def test_harmonic_transit_forecast_rejects_coercive_longitude_scalars(
    client: TestClient,
    longitude,
) -> None:
    for field in ("natal", "transit"):
        payload = {
            "natal_longitudes": {"Sun": 0.0, "Moon": 72.0},
            "transit_samples": [
                {"jd_ut": 1.0, "longitudes": {"Mars": 144.0}},
            ],
            "harmonics": [5],
        }
        if field == "natal":
            payload["natal_longitudes"]["Sun"] = longitude
        else:
            payload["transit_samples"][0]["longitudes"]["Mars"] = longitude

        response = client.post("/v1/harmonics/transit-forecast", json=payload)
        _assert_validation_envelope(response, message_fragment="real numbers")


def test_harmonic_transit_forecast_rejects_oversized_worst_case_output(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/harmonics/transit-forecast",
        json={
            "natal_longitudes": {
                f"Natal {index}": float(index) for index in range(12)
            },
            "transit_samples": [
                {
                    "jd_ut": 1.0,
                    "longitudes": {
                        f"Transit {index}": float(index) for index in range(12)
                    },
                },
            ],
            "harmonics": list(range(1, 17)),
        },
    )

    _assert_validation_envelope(response, message_fragment="25000")


@pytest.mark.parametrize(
    ("payload_update", "message_fragment"),
    [
        ({"harmonics": [5.5]}, "positive integers"),
        (
            {
                "transit_samples": [
                    {"jd_ut": 2.0, "longitudes": {"Mars": 144.0}},
                    {"jd_ut": 1.0, "longitudes": {"Mars": 144.0}},
                ]
            },
            "strictly increasing",
        ),
        (
            {
                "transit_samples": [
                    {"jd_ut": 1.0, "longitudes": {"Mars": 144.0}},
                    {"jd_ut": 2.0, "longitudes": {"Venus": 144.0}},
                ]
            },
            "identity",
        ),
        (
            {
                "transit_samples": [
                    {"jd_ut": -1e308, "longitudes": {"Mars": 144.0}},
                    {"jd_ut": 0.0, "longitudes": {"Mars": 144.0}},
                    {"jd_ut": 1e308, "longitudes": {"Mars": 144.0}},
                ],
                "maximum_sample_gap_days": 1e308,
            },
            "timestamp span must be finite",
        ),
    ],
)
def test_harmonic_transit_forecast_route_rejects_invalid_domains(
    client: TestClient,
    payload_update: dict,
    message_fragment: str,
) -> None:
    payload = {
        "natal_longitudes": {"Sun": 0.0, "Moon": 72.0},
        "transit_samples": [
            {"jd_ut": 1.0, "longitudes": {"Mars": 144.0}},
        ],
        "harmonics": [5],
    }
    payload.update(payload_update)

    response = client.post("/v1/harmonics/transit-forecast", json=payload)

    _assert_validation_envelope(response, message_fragment=message_fragment)
