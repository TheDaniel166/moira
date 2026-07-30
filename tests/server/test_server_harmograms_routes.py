from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira.harmograms import (
    HarmogramIntensityPolicy,
    HarmogramPolicy,
    HarmogramSamplingPolicy,
    HarmogramTraceFamily,
    HarmonicDomain,
    PointSetHarmonicVectorPolicy,
    SelfPairMode,
    ZeroAriesPartsPolicy,
    harmogram_trace,
    intensity_function_spectrum,
    point_set_harmonic_vector,
    project_harmogram_strength,
    zero_aries_parts_harmonic_vector,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.harmograms import HARMOGRAMS_MAX_TRACE_SAMPLES


pytestmark = pytest.mark.loopback


class _FakeEngine:
    pass


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _positions() -> list[dict[str, float | str]]:
    return [
        {"name": "Sun", "degree": 10.0},
        {"name": "Moon", "degree": 81.5},
        {"name": "Mars", "degree": 190.25},
    ]


def _policy_payload() -> dict[str, object]:
    return {
        "normalization_mode": "mean_resultant",
        "harmonic_domain": {"harmonic_start": 1, "harmonic_stop": 3},
    }


def _intensity_payload() -> dict[str, object]:
    return {
        "family": "cosine_bell_harmonic_aspects",
        "include_conjunction": True,
        "harmonic_domain": {"harmonic_start": 1, "harmonic_stop": 3},
        "orb_width_deg": 24.0,
        "sample_count": 256,
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


def test_harmogram_vector_route_matches_engine(client: TestClient) -> None:
    payload = {"positions": _positions(), "policy": _policy_payload()}
    expected = point_set_harmonic_vector(
        _positions(),
        policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 3)),
    )

    response = client.post("/v1/harmograms/vector", json=payload)

    assert response.status_code == 200
    body = response.json()
    vector = body["vector"]
    assert vector["source_kind"] == "point_set"
    assert vector["body_names"] == ["Sun", "Moon", "Mars"]
    assert vector["point_count"] == 3
    assert vector["harmonic_zero_amplitude"] == pytest.approx(expected.harmonic_zero_amplitude)
    assert [item["harmonic"] for item in vector["components"]] == [1, 2, 3]
    assert vector["components"][0]["amplitude"] == pytest.approx(expected.components[0].amplitude)
    assert body["provenance"]["engine_entrypoint"] == "point_set_harmonic_vector"
    assert body["provenance"]["chart_sampling_owner"] == "not_this_route"


def test_zero_aries_vector_route_matches_engine(client: TestClient) -> None:
    payload = {
        "positions": _positions(),
        "parts_policy": {"pair_construction_mode": "ordered", "self_pair_mode": "exclude"},
        "vector_policy": _policy_payload(),
    }
    expected = zero_aries_parts_harmonic_vector(
        positions=_positions(),
        parts_policy=ZeroAriesPartsPolicy(self_pair_mode=SelfPairMode.EXCLUDE),
        vector_policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 3)),
    )

    response = client.post("/v1/harmograms/zero-aries-vector", json=payload)

    assert response.status_code == 200
    vector = response.json()["vector"]
    assert vector["source_kind"] == "zero_aries_parts"
    assert vector["source_body_names"] == ["Sun", "Moon", "Mars"]
    assert vector["target_body_names"] == ["Sun", "Moon", "Mars"]
    assert vector["parts_count"] == expected.parts_count
    assert vector["components"][1]["phase_deg"] == pytest.approx(expected.components[1].phase_deg)


def test_intensity_spectrum_route_matches_engine(client: TestClient) -> None:
    payload = {"harmonic_number": 5, "policy": _intensity_payload()}
    expected = intensity_function_spectrum(
        5,
        policy=HarmogramIntensityPolicy(
            harmonic_domain=HarmonicDomain(1, 3),
            sample_count=256,
        ),
    )

    response = client.post("/v1/harmograms/intensity-spectrum", json=payload)

    assert response.status_code == 200
    spectrum = response.json()["spectrum"]
    assert spectrum["harmonic_number"] == 5
    assert spectrum["realization_mode"] == "numerical_truncated"
    assert spectrum["harmonic_zero_amplitude"] == pytest.approx(expected.harmonic_zero_amplitude)
    assert spectrum["components"][2]["amplitude"] == pytest.approx(expected.components[2].amplitude)


def test_projection_route_matches_engine(client: TestClient) -> None:
    payload = {
        "positions": _positions(),
        "parts_policy": {"pair_construction_mode": "ordered", "self_pair_mode": "include"},
        "vector_policy": _policy_payload(),
        "harmonic_number": 4,
        "intensity_policy": _intensity_payload(),
    }
    source_vector = zero_aries_parts_harmonic_vector(
        positions=_positions(),
        vector_policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 3)),
    )
    spectrum = intensity_function_spectrum(
        4,
        policy=HarmogramIntensityPolicy(
            harmonic_domain=HarmonicDomain(1, 3),
            sample_count=256,
        ),
    )
    expected = project_harmogram_strength(source_vector, spectrum)

    response = client.post("/v1/harmograms/projection", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["source_vector"]["parts_count"] == source_vector.parts_count
    assert body["projection"]["total_strength"] == pytest.approx(expected.total_strength)
    assert body["projection"]["terms"][0]["signed_contribution"] == pytest.approx(
        expected.terms[0].signed_contribution
    )
    assert body["provenance"]["engine_entrypoint"] == "project_harmogram_strength"


def test_trace_route_matches_engine(client: TestClient) -> None:
    samples = [
        {"time": 0.0, "positions": _positions()},
        {
            "time": 1.0,
            "positions": [
                {"name": "Sun", "degree": 11.0},
                {"name": "Moon", "degree": 82.25},
                {"name": "Mars", "degree": 190.75},
            ],
        },
    ]
    payload = {
        "samples": samples,
        "harmonic_numbers": [1, 2],
        "trace_family": "dynamic_zero_aries_parts",
        "point_set_policy": _policy_payload(),
        "intensity_policy": _intensity_payload(),
    }
    expected = harmogram_trace(
        samples,
        harmonic_numbers=(1, 2),
        policy=HarmogramPolicy(
            point_set_policy=PointSetHarmonicVectorPolicy(harmonic_domain=HarmonicDomain(1, 3)),
            intensity_policy=HarmogramIntensityPolicy(
                harmonic_domain=HarmonicDomain(1, 3),
                sample_count=256,
            ),
            sampling_policy=HarmogramSamplingPolicy(sample_count=2),
            trace_family=HarmogramTraceFamily.DYNAMIC_ZERO_ARIES_PARTS,
        ),
    )

    response = client.post("/v1/harmograms/trace", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["series_count"] == 2
    assert body["sample_times"] == [0.0, 1.0]
    assert body["policy"]["chart_domain"] == "dynamic_sky_only_trace"
    assert body["series"][0]["strengths"][0] == pytest.approx(expected.series[0].strengths[0])
    assert body["series"][1]["samples"][1]["source_vector"]["parts_count"] == 9
    assert body["provenance"]["engine_entrypoint"] == "harmogram_trace"


@pytest.mark.parametrize(
    ("route", "payload", "message_fragment"),
    [
        (
            "/v1/harmograms/vector",
            {
                "positions": [
                    {"name": "Sun", "degree": 10.0},
                    {"name": " Sun ", "degree": 20.0},
                ]
            },
            "positions names must be unique",
        ),
        (
            "/v1/harmograms/intensity-spectrum",
            {
                "harmonic_number": 4,
                "policy": {
                    "family": "gaussian_harmonic_aspects",
                    "sample_count": 256,
                },
            },
            "gaussian intensity families require gaussian_width_deg",
        ),
        (
            "/v1/harmograms/projection",
            {
                "positions": _positions(),
                "vector_policy": {
                    "harmonic_domain": {"harmonic_start": 1, "harmonic_stop": 3},
                },
                "harmonic_number": 4,
                "intensity_policy": {
                    "harmonic_domain": {"harmonic_start": 1, "harmonic_stop": 4},
                    "sample_count": 256,
                },
            },
            "vector_policy and intensity_policy must share",
        ),
        (
            "/v1/harmograms/trace",
            {
                "samples": [{"time": 0.0, "positions": _positions()}]
                * (HARMOGRAMS_MAX_TRACE_SAMPLES + 1),
                "harmonic_numbers": [1],
            },
            "samples may contain at most",
        ),
    ],
)
def test_harmogram_routes_reject_invalid_inputs(
    client: TestClient,
    route: str,
    payload: dict[str, object],
    message_fragment: str,
) -> None:
    response = client.post(route, json=payload)

    _assert_validation_envelope(response, message_fragment=message_fragment)


def test_harmogram_route_methods_are_bounded(client: TestClient) -> None:
    assert client.get("/v1/harmograms/vector").status_code == 405
    assert client.get("/v1/harmograms/zero-aries-vector").status_code == 405
    assert client.get("/v1/harmograms/intensity-spectrum").status_code == 405
    assert client.get("/v1/harmograms/projection").status_code == 405
    assert client.get("/v1/harmograms/trace").status_code == 405
