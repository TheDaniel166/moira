"""REST contract tests for explicit astronomical Pancha Pakshi paksha."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

import moira_server.models as public_models
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network

_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_POLICY_ID = (
    "apparent_geocentric_moon_sun_longitude_paksha_half_open_v1"
)


def _policy() -> SimpleNamespace:
    return SimpleNamespace(
        policy_id=_POLICY_ID,
        input_time_scale="ut1",
        ephemeris_time_scale="reader_bound_tt",
        position_origin="geocentric",
        position_frame="true_ecliptic_of_date",
        apparent=True,
        aberration=True,
        grav_deflection=True,
        nutation=True,
        elongation_definition=(
            "normalized_moon_longitude_minus_sun_longitude"
        ),
        elongation_domain="degrees_half_open_0_360",
        shukla_interval="0_inclusive_180_exclusive",
        krishna_interval="180_inclusive_360_exclusive",
        boundary_tolerance_degrees=0.0,
        ayanamsa_status=(
            "not_applied_common_longitude_offset_cancels"
        ),
        profile_mapping_basis="direct_source_attested_waxing_waning",
        purva_source_locator_id="ia_n16",
        amara_source_locator_id="ia_n26",
        schedule_selection_status="not_performed",
        materialization_status="not_performed",
        natal_identity_status="not_performed",
    )


def _source_locator(locator_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        locator_id=locator_id,
        witness_id="agastya_madras_1879",
        label=f"Archive leaf {locator_id.removeprefix('ia_n')}",
        url=f"https://archive.org/details/example/page/n{locator_id[4:]}",
        evidence_role="paksha_mapping",
    )


def _provenance() -> SimpleNamespace:
    source = SimpleNamespace(
        witness_id="agastya_madras_1879",
        title="Pancha Pakshi Sastram",
        traditional_attribution="Agastya",
        authorship_status="traditional_attribution",
        publication_place="Madras",
        publisher="source_witness",
        publication_year=1879,
        language="Tamil",
        archive_item_url="https://archive.org/details/example",
        archive_original_image_zip_name="example_images.zip",
        archive_original_image_zip_source_status="archive_derivative",
        archive_original_image_zip_md5="0" * 32,
        archive_original_image_zip_sha1="0" * 40,
        archive_pdf_name="example.pdf",
        archive_pdf_source_status="archive_derivative",
        archive_pdf_md5="0" * 32,
        archive_pdf_sha1="0" * 40,
        locally_verified_pdf_sha256="0" * 64,
        catalogued_contributor_note="transport fixture",
        artifact_distribution_status="not_bundled",
        redistribution_policy="metadata_only",
        license_scope="source_metadata_only",
        artifact_distribution_note="No source artifact is bundled.",
    )
    return SimpleNamespace(
        profile_id=_PROFILE_ID,
        admission_status="source_scoped_public",
        product_kind="aksara_prasna_operating_schedule",
        default_selection_allowed=False,
        capabilities=("astronomical_paksha_inference",),
        admission_decision_id="transport_fixture",
        derivation_status="source_scoped",
        assembly_policy="explicit",
        astronomical_routing_status="astronomical_paksha_inference_performed",
        source=source,
        declared_omissions=(),
    )


class _StubEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[str, datetime]] = []

    def pancha_pakshi_astronomical_paksha(
        self,
        profile_id: str,
        dt: datetime,
    ) -> SimpleNamespace:
        self.calls.append((profile_id, dt))
        return SimpleNamespace(
            profile_id=profile_id,
            requested_jd_ut1=2461242.0,
            requested_jd_tt=2461242.0008,
            policy=_policy(),
            sun_longitude_deg=117.0,
            moon_longitude_deg=147.0,
            moon_minus_sun_elongation_deg=30.0,
            astronomical_paksha="shukla",
            profile_paksha="purva",
            mapping_status="direct_source_attested",
            mapping_source_locators=(_source_locator("ia_n16"),),
            provenance=_provenance(),
        )


@pytest.fixture
def client_and_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, _StubEngine]:
    engine = _StubEngine()
    monkeypatch.setattr(
        "moira_server.app.create_engine",
        lambda config: engine,
    )
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, engine


def test_astronomical_paksha_route_is_explicit_and_serialized(
    client_and_engine: tuple[TestClient, _StubEngine],
) -> None:
    client, engine = client_and_engine

    response = client.post(
        "/v1/pancha-pakshi/context/astronomical-paksha",
        json={
            "profile_id": _PROFILE_ID,
            "dt": "2026-07-20T08:00:00-04:00",
            "policy_id": _POLICY_ID,
        },
    )

    assert response.status_code == 200
    assert engine.calls == [
        (_PROFILE_ID, datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc))
    ]
    body = response.json()
    assert body["profile_id"] == _PROFILE_ID
    assert body["astronomical_paksha"] == "shukla"
    assert body["profile_paksha"] == "purva"
    assert body["mapping_status"] == "direct_source_attested"
    assert [
        locator["locator_id"] for locator in body["mapping_source_locators"]
    ] == ["ia_n16"]
    assert body["policy"] == {
        "policy_id": _POLICY_ID,
        "input_time_scale": "ut1",
        "ephemeris_time_scale": "reader_bound_tt",
        "position_origin": "geocentric",
        "position_frame": "true_ecliptic_of_date",
        "apparent": True,
        "aberration": True,
        "grav_deflection": True,
        "nutation": True,
        "elongation_definition": (
            "normalized_moon_longitude_minus_sun_longitude"
        ),
        "elongation_domain": "degrees_half_open_0_360",
        "shukla_interval": "0_inclusive_180_exclusive",
        "krishna_interval": "180_inclusive_360_exclusive",
        "boundary_tolerance_degrees": 0.0,
        "ayanamsa_status": (
            "not_applied_common_longitude_offset_cancels"
        ),
        "profile_mapping_basis": "direct_source_attested_waxing_waning",
        "purva_source_locator_id": "ia_n16",
        "amara_source_locator_id": "ia_n26",
        "schedule_selection_status": "not_performed",
        "materialization_status": "not_performed",
        "natal_identity_status": "not_performed",
    }


def test_astronomical_paksha_transport_models_are_public() -> None:
    expected = {
        "PanchaPakshiAstronomicalPakshaInferencePolicyResponse",
        "PanchaPakshiAstronomicalPakshaRequest",
        "PanchaPakshiAstronomicalPakshaResponse",
    }
    assert expected <= set(public_models.__all__)
    for name in expected:
        assert getattr(public_models, name).__module__ == (
            "moira_server.models.pancha_pakshi"
        )


def test_astronomical_paksha_openapi_preserves_the_explicit_policy(
    client_and_engine: tuple[TestClient, _StubEngine],
) -> None:
    client, _engine = client_and_engine
    schema = client.app.openapi()
    operation = schema["paths"][
        "/v1/pancha-pakshi/context/astronomical-paksha"
    ]["post"]
    request_ref = operation["requestBody"]["content"]["application/json"][
        "schema"
    ]["$ref"]
    response_ref = operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    assert request_ref.endswith("/PanchaPakshiAstronomicalPakshaRequest")
    assert response_ref.endswith("/PanchaPakshiAstronomicalPakshaResponse")

    components = schema["components"]["schemas"]
    request_schema = components["PanchaPakshiAstronomicalPakshaRequest"]
    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {
        "profile_id",
        "dt",
        "policy_id",
    }
    assert request_schema["properties"]["policy_id"]["const"] == _POLICY_ID
    assert "paksha" not in request_schema["properties"]
    assert "latitude" not in request_schema["properties"]
    assert "longitude" not in request_schema["properties"]

    response_schema = components["PanchaPakshiAstronomicalPakshaResponse"]
    assert response_schema["additionalProperties"] is False
    assert set(response_schema["required"]) == {
        "profile_id",
        "requested_jd_ut1",
        "requested_jd_tt",
        "policy",
        "sun_longitude_deg",
        "moon_longitude_deg",
        "moon_minus_sun_elongation_deg",
        "astronomical_paksha",
        "profile_paksha",
        "mapping_status",
        "mapping_source_locators",
        "provenance",
    }
    policy_schema = components[
        "PanchaPakshiAstronomicalPakshaInferencePolicyResponse"
    ]
    assert policy_schema["additionalProperties"] is False
    assert policy_schema["properties"]["policy_id"]["const"] == _POLICY_ID
    assert policy_schema["properties"]["boundary_tolerance_degrees"][
        "const"
    ] == 0.0


@pytest.mark.parametrize(
    "payload",
    [
        {
            "profile_id": _PROFILE_ID,
            "dt": "2026-07-20T12:00:00Z",
        },
        {
            "profile_id": _PROFILE_ID,
            "dt": "2026-07-20T12:00:00Z",
            "policy_id": "ambient_lunar_paksha",
        },
        {
            "profile_id": _PROFILE_ID,
            "dt": "2026-07-20T12:00:00",
            "policy_id": _POLICY_ID,
        },
        {
            "profile_id": _PROFILE_ID,
            "dt": "2026-07-20T12:00:00Z",
            "policy_id": _POLICY_ID,
            "paksha": "purva",
        },
        {
            "profile_id": _PROFILE_ID,
            "dt": 0,
            "policy_id": _POLICY_ID,
        },
        {
            "profile_id": _PROFILE_ID,
            "dt": True,
            "policy_id": _POLICY_ID,
        },
        {
            "profile_id": _PROFILE_ID,
            "dt": "0",
            "policy_id": _POLICY_ID,
        },
        {
            "profile_id": _PROFILE_ID,
            "dt": "1000.5",
            "policy_id": _POLICY_ID,
        },
        {
            "profile_id": _PROFILE_ID,
            "dt": "1234567890",
            "policy_id": _POLICY_ID,
        },
    ],
)
def test_astronomical_paksha_route_rejects_implicit_or_ambiguous_policy(
    client_and_engine: tuple[TestClient, _StubEngine],
    payload: dict[str, object],
) -> None:
    client, engine = client_and_engine

    response = client.post(
        "/v1/pancha-pakshi/context/astronomical-paksha",
        json=payload,
    )

    assert response.status_code == 422
    assert engine.calls == []
