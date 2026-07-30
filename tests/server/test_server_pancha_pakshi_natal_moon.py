"""Facade, REST, and OpenAPI contracts for Stage 2G natal identity."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

import moira
import moira.facade as facade_surface
from moira._facade_vedic import VedicFacadeMixin
from moira.pancha_pakshi import (
    PanchaPakshiAstronomicalPaksha,
    PanchaPakshiNakshatraBirdMapping,
    PanchaPakshiNatalMoonIdentity,
    PanchaPakshiNatalMoonIdentityPolicy,
    PanchaPakshiPaksha,
    pancha_pakshi_nakshatra_bird_mapping,
    pancha_pakshi_profile_info,
)
import moira.vedic as vedic_surface
import moira_server.models as public_models
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.pancha_pakshi import (
    PanchaPakshiNatalMoonIdentityRequest,
)
from moira_server.serializers.pancha_pakshi import (
    serialize_natal_moon_identity,
)
from moira_server.services.pancha_pakshi import compute_natal_moon_identity


pytestmark = pytest.mark.loopback

_PROFILE_ID = "bogamuni_chennai_2024_nakshatra_natal_identity"
_POLICY_ID = "bogamuni_2024_apparent_lahiri_natal_moon_identity_v1"
_ROUTE = "/v1/pancha-pakshi/identity/natal-moon"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _identity_result() -> SimpleNamespace:
    info = pancha_pakshi_profile_info(_PROFILE_ID)
    provenance = replace(
        info.provenance,
        astronomical_routing_status=(
            "natal_moon_identity_performed_modern_lahiri_composition_no_"
            "schedule_materialization_current_cell_scoring_or_forecast"
        ),
    )
    mapping = replace(
        pancha_pakshi_nakshatra_bird_mapping(
            _PROFILE_ID,
            profile_paksha=PanchaPakshiPaksha.PURVA,
            nakshatra_index=0,
        ),
        provenance=provenance,
    )
    phase_locator = next(
        locator
        for locator in info.source_locators
        if locator.locator_id == "bogar_n167_phase"
    )
    return SimpleNamespace(
        profile_id=_PROFILE_ID,
        requested_jd_ut1=2461241.5,
        requested_jd_tt=2461241.5008,
        policy=PanchaPakshiNatalMoonIdentityPolicy(),
        sun_longitude_deg=5.0,
        moon_tropical_longitude_deg=25.0,
        moon_minus_sun_elongation_deg=20.0,
        astronomical_paksha=PanchaPakshiAstronomicalPaksha.SHUKLA,
        profile_paksha=PanchaPakshiPaksha.PURVA,
        phase_mapping_source_locators=(phase_locator,),
        ayanamsa_deg=24.0,
        moon_sidereal_longitude_deg=1.0,
        nakshatra_index=0,
        nakshatra="Ashwini",
        degrees_in_nakshatra=1.0,
        bird=mapping.bird,
        bird_mapping=mapping,
        provenance=provenance,
    )


def test_stage2g_symbols_are_exported_on_all_public_python_surfaces() -> None:
    for surface in (moira, facade_surface, vedic_surface):
        assert surface.PanchaPakshiNakshatraBirdMapping is (
            PanchaPakshiNakshatraBirdMapping
        )
        assert surface.PanchaPakshiNatalMoonIdentity is PanchaPakshiNatalMoonIdentity
        assert surface.PanchaPakshiNatalMoonIdentityPolicy is (
            PanchaPakshiNatalMoonIdentityPolicy
        )
        assert surface.pancha_pakshi_nakshatra_bird_mapping is (
            pancha_pakshi_nakshatra_bird_mapping
        )
        assert surface.pancha_pakshi_natal_moon_identity_at is (
            moira.pancha_pakshi_natal_moon_identity_at
        )


def test_facade_routes_utc_once_and_keeps_the_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    reader = object()
    seen: dict[str, object] = {}

    def fake_identity(profile_id, jd_utc, *, reader):
        seen.update(profile_id=profile_id, jd_utc=jd_utc, reader=reader)
        return sentinel

    monkeypatch.setattr(
        "moira._facade_vedic._pancha_pakshi."
        "_pancha_pakshi_natal_moon_identity_from_utc",
        fake_identity,
    )
    instance = SimpleNamespace(_reader=reader)
    result = VedicFacadeMixin.pancha_pakshi_natal_moon_identity(
        instance,
        _PROFILE_ID,
        datetime(2026, 7, 20, 12, tzinfo=timezone.utc),
    )

    assert result is sentinel
    assert seen["profile_id"] == _PROFILE_ID
    assert seen["reader"] is reader
    assert seen["jd_utc"] == pytest.approx(2461242.0)


def test_service_delegates_only_profile_and_aware_instant() -> None:
    sentinel = object()

    class Engine:
        def pancha_pakshi_natal_moon_identity(self, profile_id, dt):
            assert profile_id == _PROFILE_ID
            assert dt == datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
            return sentinel

    request = PanchaPakshiNatalMoonIdentityRequest(
        profile_id=_PROFILE_ID,
        dt="2026-07-20T08:00:00-04:00",
        policy_id=_POLICY_ID,
    )

    assert compute_natal_moon_identity(Engine(), request) is sentinel


def test_serializer_exposes_source_mapping_and_modern_composition() -> None:
    response = serialize_natal_moon_identity(_identity_result())

    assert response.policy.composition_status == "modern_moira_policy_not_source_claim"
    assert response.policy.ayanamsa_status == (
        "fixed_modern_moira_policy_not_source_attested"
    )
    assert response.policy.mapping_assembly_policy == (
        "verse_precedence_for_nakshatra_partition"
    )
    assert response.phase_mapping_source_locators[0].locator_id == (
        "bogar_n167_phase"
    )
    assert response.bird_mapping.mapping_status == "direct_source_attested"
    assert response.bird is response.bird_mapping.bird
    assert response.bird_mapping.source_table_semantics == (
        "nakshatra_bird_table_not_explicitly_natal_moon"
    )
    assert response.provenance.source.witness_id == (
        "acc.-no.-44757-panjapatchi-sashthiram-2024"
    )


def test_natal_moon_route_is_strict_and_transparent(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "moira_server.routers.pancha_pakshi.compute_natal_moon_identity",
        lambda engine, request: _identity_result(),
    )
    response = client.post(
        _ROUTE,
        json={
            "profile_id": _PROFILE_ID,
            "dt": "2026-07-20T12:00:00Z",
            "policy_id": _POLICY_ID,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == _PROFILE_ID
    assert body["policy"]["composition_status"] == (
        "modern_moira_policy_not_source_claim"
    )
    assert body["bird_mapping"]["nakshatra"] == "Ashwini"
    assert body["bird"] == body["bird_mapping"]["bird"] == "vulture"
    assert body["bird_mapping"]["source_locators"][0]["locator_id"] == (
        "bogar_n52_purva"
    )
    assert body["provenance"]["astronomical_routing_status"].startswith(
        "natal_moon_identity_performed_"
    )

    forbidden = client.post(
        _ROUTE,
        json={
            "profile_id": _PROFILE_ID,
            "dt": "2026-07-20T12:00:00Z",
            "policy_id": _POLICY_ID,
            "latitude": 13.08,
            "paksha": "purva",
            "nakshatra_index": 0,
            "bird": "vulture",
            "ayanamsa_system": "Lahiri",
            "schedule": True,
            "current_cell": True,
            "scoring": True,
        },
    )
    assert forbidden.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("dt", "2026-07-20T12:00:00"),
        ("dt", "not-a-date"),
        ("policy_id", "caller_selected_natal_policy"),
    ],
    ids=["naive-datetime", "non-iso-datetime", "wrong-policy"],
)
def test_natal_moon_route_rejects_invalid_datetime_and_policy(
    client: TestClient,
    field: str,
    value: str,
) -> None:
    payload = {
        "profile_id": _PROFILE_ID,
        "dt": "2026-07-20T12:00:00Z",
        "policy_id": _POLICY_ID,
    }
    payload[field] = value

    response = client.post(_ROUTE, json=payload)

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


def test_natal_moon_openapi_is_exact_and_publicly_exported(
    client: TestClient,
) -> None:
    schema = client.app.openapi()
    operation = schema["paths"][_ROUTE]["post"]
    components = schema["components"]["schemas"]
    request = components["PanchaPakshiNatalMoonIdentityRequest"]

    assert operation["tags"] == ["pancha-pakshi"]
    assert request["additionalProperties"] is False
    assert set(request["required"]) == {"profile_id", "dt", "policy_id"}
    assert set(request["properties"]) == {"profile_id", "dt", "policy_id"}
    assert request["properties"]["policy_id"]["const"] == _POLICY_ID
    assert request["properties"]["dt"]["format"] == "date-time"

    policy = components["PanchaPakshiNatalMoonIdentityPolicyResponse"]
    assert policy["properties"]["composition_status"]["const"] == (
        "modern_moira_policy_not_source_claim"
    )
    assert policy["properties"]["schedule_selection_status"]["const"] == (
        "not_performed"
    )
    assert policy["properties"]["forecast_status"]["const"] == "not_performed"
    assert public_models.PanchaPakshiNatalMoonIdentityRequest is (
        PanchaPakshiNatalMoonIdentityRequest
    )
    assert public_models.PanchaPakshiNatalMoonIdentityResponse.__name__ == (
        "PanchaPakshiNatalMoonIdentityResponse"
    )
