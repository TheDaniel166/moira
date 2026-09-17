from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from moira import (
    OrbitalAmbiguousBodyError,
    OrbitalBodyNotFoundError,
    OrbitalBodyNotLoadedError,
    OrbitalBodyNotSupportedError,
    OrbitalCenterNotAllowedError,
    OrbitalCoverageError,
    OrbitalFrameUnavailableError,
    OrbitalGravityModelError,
    OrbitalInputError,
    OrbitalKernelMissingError,
    OrbitalLegacyBodyNotAllowedError,
    OrbitalPassageUnavailableError,
    OrbitalSearchError,
    OrbitalSourceReceiptError,
    OrbitalStateDegenerateError,
    OrbitalTimeBasisError,
)
from moira.small_body_identity import SmallBodyIdentity
from moira_server.errors import register_exception_handlers


pytestmark = pytest.mark.loopback


_CANDIDATES = (
    SmallBodyIdentity("asteroid", "Test Body", 2_000_001, "Test Body", False),
    SmallBodyIdentity("comet", "Test Body", 1_000_001, "Test Body", False),
)


_ERROR_FACTORIES: dict[str, Callable[[], Exception]] = {
    "input": lambda: OrbitalInputError("jd_ut", float("nan"), ("finite JD",)),
    "unsupported": lambda: OrbitalBodyNotSupportedError(
        "Sun", "center", "the Sun is a center"
    ),
    "center": lambda: OrbitalCenterNotAllowedError("Moon", "SUN", ("EARTH",)),
    "frame": lambda: OrbitalFrameUnavailableError(
        "TRUE_ECLIPTIC_OF_DATE",
        2_300_000.0,
        ((2_415_020.0, 2_488_070.0),),
    ),
    "legacy": lambda: OrbitalLegacyBodyNotAllowedError(
        "Moon",
        "orbital_elements_at",
        ("Mercury", "Venus", "Earth"),
        "osculating_elements",
    ),
    "ambiguous": lambda: OrbitalAmbiguousBodyError("Test Body", _CANDIDATES),
    "unknown": lambda: OrbitalBodyNotFoundError("No Such Body", ("Moon",)),
    "coverage": lambda: OrbitalCoverageError(
        "Earth",
        399,
        3_000_000.0,
        ((2_287_184.5, 2_688_976.5),),
        ("de441_part-2.bsp",),
        None,
    ),
    "not-loaded": lambda: OrbitalBodyNotLoadedError(
        "Ceres",
        2_000_001,
        "moira-asteroids",
        "2026.08.12.1",
        "https://moira-astro.com/ephemerides",
    ),
    "kernel": lambda: OrbitalKernelMissingError(
        r"C:\operator-private\kernels\de441.bsp"
    ),
    "gravity": lambda: OrbitalGravityModelError("DE430", "DE430", ("DE440", "DE441")),
    "time": lambda: OrbitalTimeBasisError(
        "UT1_TO_TDB", "DE441", None, 2, "MORRISON_STEPHENSON_2021", None
    ),
    "source": lambda: OrbitalSourceReceiptError(
        10, 399, "ThirdPartyReader", "atomic state/source receipt"
    ),
    "degenerate": lambda: OrbitalStateDegenerateError(
        "RECTILINEAR_STATE", "Earth", 2_451_545.0, 1.0, 1.0, 0.0, 1.0e-10
    ),
    "search": lambda: OrbitalSearchError(
        (2_451_545.0, 2_451_546.0),
        96,
        20_000,
        1.0e-8,
        1.0e-7,
        "MOIRA_APSIDAL_PASSAGES_V1",
    ),
    "passage": lambda: OrbitalPassageUnavailableError(
        SimpleNamespace(
            body=SimpleNamespace(name="Earth"),
            pericenter=SimpleNamespace(status="FOUND"),
            apocenter=SimpleNamespace(status="NOT_IN_WINDOW"),
        ),
        ("APOCENTER",),
    ),
}


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()

    @app.get("/_test/orbital/{error_name}")
    def raise_orbital_error(error_name: str) -> None:
        raise _ERROR_FACTORIES[error_name]()

    register_exception_handlers(app)
    return TestClient(app)


@pytest.mark.parametrize(
    ("name", "status", "error_code", "category"),
    (
        ("input", 422, "invalid_parameter", "input_validation"),
        ("unsupported", 422, "body_not_supported", "input_validation"),
        ("center", 422, "center_not_allowed", "input_validation"),
        ("frame", 422, "frame_outside_model_range", "input_validation"),
        ("legacy", 422, "body_not_allowed_in_legacy_api", "input_validation"),
        ("ambiguous", 422, "ambiguous_body", "input_validation"),
        ("unknown", 422, "unknown_body", "input_validation"),
        (
            "coverage",
            422,
            "date_outside_ephemeris_coverage",
            "ephemeris_coverage",
        ),
        (
            "not-loaded",
            503,
            "body_ephemeris_not_installed",
            "ephemeris_availability",
        ),
        ("kernel", 503, "kernel_not_ready", "kernel_readiness"),
        (
            "gravity",
            503,
            "ephemeris_model_not_admitted",
            "server_configuration",
        ),
        ("time", 503, "time_basis_unavailable", "server_configuration"),
        (
            "source",
            503,
            "ephemeris_source_receipt_unavailable",
            "server_configuration",
        ),
        ("degenerate", 500, "computation_failed", "computation"),
        ("search", 500, "computation_failed", "computation"),
        (
            "passage",
            422,
            "passage_unavailable",
            "orbital_event_availability",
        ),
    ),
)
def test_orbital_error_mapping_is_specific(
    client: TestClient,
    name: str,
    status: int,
    error_code: str,
    category: str,
) -> None:
    response = client.get(f"/_test/orbital/{name}")

    assert response.status_code == status
    payload = response.json()
    assert payload["error_code"] == error_code
    assert payload["category"] == category
    assert payload["request_id"]
    assert payload["message"]


def test_coverage_error_exposes_exact_tdb_intervals(client: TestClient) -> None:
    response = client.get("/_test/orbital/coverage")

    assert response.json()["details"] == {
        "body": "Earth",
        "naif_id": 399,
        "requested_epoch_tdb": 3_000_000.0,
        "covered_intervals_tdb": [[2_287_184.5, 2_688_976.5]],
        "source_labels": ["de441_part-2.bsp"],
        "coverage_restricted_to_observed_arc": None,
    }


def test_non_finite_input_is_json_safe(client: TestClient) -> None:
    response = client.get("/_test/orbital/input")

    assert response.json()["details"]["value"] == "NaN"


def test_kernel_error_does_not_expose_operator_path(client: TestClient) -> None:
    response = client.get("/_test/orbital/kernel")

    assert response.json()["details"] is None
    assert "operator-private" not in response.text
    assert "C:\\" not in response.text


def test_computation_failure_has_no_internal_details(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    response = client.get("/_test/orbital/degenerate")

    payload = response.json()
    assert payload["details"] is None
    assert "RECTILINEAR_STATE" not in response.text
    assert payload["request_id"] in caplog.text


def test_passage_unavailable_exposes_only_typed_outcome_summary(
    client: TestClient,
) -> None:
    response = client.get("/_test/orbital/passage")

    assert response.json()["details"] == {
        "body": "Earth",
        "missing_kinds": ["APOCENTER"],
        "pericenter_status": "FOUND",
        "apocenter_status": "NOT_IN_WINDOW",
    }
