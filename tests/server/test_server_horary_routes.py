"""Focused service and route gates for the bounded Horary contract."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

import moira_server.models as public_models
import moira_server.serializers as public_serializers
import moira_server.services as public_services
from moira.classical_perfection import (
    ClassicalBodyState,
    LILLY_1647_PERFECTION_V1,
    classify_lilly_perfection_events,
)
from moira.constants import Body, HouseSystem
from moira.horary import (
    HoraryEvidenceState,
    HoraryGeometrySourceMode,
    HoraryHouseGeometryReceipt,
    HoraryPlanetaryHourReceipt,
    HoraryQuestionReceipt,
    evaluate_horary_evidence,
)
from moira.houses import HouseCusps, HousePolicy, classify_house_system
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.horary import (
    HoraryEvidenceProfileRequest,
    HoraryEvidenceProfileResponse,
)
from moira_server.serializers.horary import serialize_horary_evidence_profile
from moira_server.services.horary import compute_horary_evidence_profile


pytestmark = pytest.mark.loopback


_CONVERSION_POLICY = "moira.julian.jd_from_datetime+utc_to_ut1:v1"
_PAYLOAD = {
    "question_id": "question-2026-08-11-001",
    "question_instant": "2026-08-11T12:00:00-05:00",
    "stated_basis": "question_proposed_and_figure_erected",
    "stated_basis_source": "Caller states the question and figure share one event",
    "source_calendar": "gregorian",
    "source_instant_label": "11 Aug 2026, 12:00 fixed-offset source clock",
    "conversion_policy_id": _CONVERSION_POLICY,
    "latitude_deg": 40.7128,
    "longitude_deg": -74.006,
    "house_system": HouseSystem.REGIOMONTANUS,
    "perspective_path": [7],
    "terminal_topic_house": 9,
}
_TRADITIONAL_STATES = (
    ClassicalBodyState(Body.SUN, 120.0, 1.0, "Leo"),
    ClassicalBodyState(Body.MOON, 200.0, 13.0, "Libra"),
    ClassicalBodyState(Body.MERCURY, 150.0, 2.0, "Virgo"),
    ClassicalBodyState(Body.VENUS, 40.0, 1.2, "Taurus"),
    ClassicalBodyState(Body.MARS, 280.0, 0.5, "Capricorn"),
    ClassicalBodyState(Body.JUPITER, 5.0, 0.1, "Aries"),
    ClassicalBodyState(Body.SATURN, 330.0, 0.05, "Pisces"),
)


def _houses(system: str) -> HouseCusps:
    cusps = (
        150.0,
        180.0,
        210.0,
        240.0,
        270.0,
        300.0,
        330.0,
        350.0,
        0.0,
        30.0,
        60.0,
        90.0,
    )
    return HouseCusps(
        system=system,
        cusps=cusps,
        asc=150.0,
        mc=30.0,
        armc=0.0,
        effective_system=system,
        fallback=False,
        fallback_reason=None,
        classification=classify_house_system(system),
        policy=HousePolicy.strict(),
    )


def _planetary_hour(question: HoraryQuestionReceipt) -> HoraryPlanetaryHourReceipt:
    jd_ut1 = question.time.normalized_jd_ut1
    assert jd_ut1 is not None
    hour_length = 0.5 / 12.0
    period_start = jd_ut1 - 0.5 * hour_length
    return HoraryPlanetaryHourReceipt(
        question_id=question.question_id,
        jd_ut1=jd_ut1,
        latitude_deg=question.latitude_deg,
        longitude_deg=question.longitude_deg,
        source_id="server-route-fixture-planetary-hour-v1",
        hour_ruler=Body.MERCURY,
        hour_number=1,
        hour_start_jd=period_start,
        hour_end_jd=period_start + hour_length,
        sunrise_jd=period_start,
        sunset_jd=period_start + 0.5,
        local_time_algorithm_id="fixture_unequal_planetary_hours_v1",
    )


def _profile_from_question(
    question: HoraryQuestionReceipt,
    house_policy,
    perfection_jd_end: float | None,
):
    jd_ut1 = question.time.normalized_jd_ut1
    assert jd_ut1 is not None
    geometry = HoraryHouseGeometryReceipt(
        question_id=question.question_id,
        latitude_deg=question.latitude_deg,
        longitude_deg=question.longitude_deg,
        source_id="server-route-fixture-house-geometry-v1",
        source_mode=HoraryGeometrySourceMode.COMPUTED,
        jd_ut1=jd_ut1,
        house_cusps=_houses(house_policy.house_system),
    )
    perfection = None
    if perfection_jd_end is not None:
        # H1 is Virgo (Mercury), while the bounded-perfection request below
        # uses radical H9, whose Aries cusp is ruled by Mars.
        perfection = classify_lilly_perfection_events(
            jd_ut1,
            perfection_jd_end,
            Body.MERCURY,
            Body.MARS,
            is_day_chart=True,
            initial_states=_TRADITIONAL_STATES,
            events=(),
            reader_provenance="server-route-classifier-fixture",
            policy=LILLY_1647_PERFECTION_V1,
        )
    return evaluate_horary_evidence(
        question,
        geometry,
        house_policy=house_policy,
        planetary_hour=_planetary_hour(question),
        perfection_analysis=perfection,
    )


class _FakeHoraryEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[HoraryQuestionReceipt, object, float | None]] = []

    def horary_evidence_at(
        self,
        question,
        *,
        house_policy,
        perfection_jd_end,
    ):
        self.calls.append((question, house_policy, perfection_jd_end))
        return _profile_from_question(question, house_policy, perfection_jd_end)


def _client(
    monkeypatch: pytest.MonkeyPatch,
    engine: _FakeHoraryEngine,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    return TestClient(create_app(ServerConfig(docs_enabled=False)))


def _exact_forbidden_judgement_keys(value: object) -> set[str]:
    forbidden = {"score", "outcome", "advice", "recommendation"}
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(forbidden.intersection(value))
        for item in value.values():
            found.update(_exact_forbidden_judgement_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_exact_forbidden_judgement_keys(item))
    return found


def test_service_builds_exact_question_receipt_and_delegates_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = HoraryEvidenceProfileRequest.model_validate(_PAYLOAD)
    expected = object()

    class RecordingEngine:
        def __init__(self) -> None:
            self.calls = []

        def horary_evidence_at(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return expected

    engine = RecordingEngine()
    seen: list[tuple[str, object]] = []
    monkeypatch.setattr(
        "moira_server.services.horary.jd_from_datetime",
        lambda value: seen.append(("utc", value)) or 2_460_000.5,
    )
    monkeypatch.setattr(
        "moira_server.services.horary.utc_to_ut1",
        lambda value: seen.append(("ut1", value)) or 2_460_000.50001,
    )

    result = compute_horary_evidence_profile(engine, request)

    assert result is expected
    assert len(engine.calls) == 1
    (question,), kwargs = engine.calls[0]
    assert question.question_id == _PAYLOAD["question_id"]
    assert question.time.state is HoraryEvidenceState.EVALUATED
    assert question.time.normalized_instant == datetime(
        2026, 8, 11, 17, 0, tzinfo=timezone.utc
    )
    assert question.time.normalized_jd_ut1 == 2_460_000.50001
    assert question.time.conversion_policy_id == _CONVERSION_POLICY
    assert question.perspective_path == (7,)
    assert question.terminal_topic_house == 9
    assert kwargs["house_policy"].house_system == HouseSystem.REGIOMONTANUS
    assert kwargs["perfection_jd_end"] is None
    assert [kind for kind, _ in seen] == ["utc", "ut1"]


def test_route_preserves_typed_not_evaluable_perfection_and_source_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeHoraryEngine()
    with _client(monkeypatch, engine) as client:
        response = client.post("/v1/horary/evidence-profile", json=_PAYLOAD)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["question"]["question_id"] == _PAYLOAD["question_id"]
    assert body["question"]["time"]["normalized_instant"] == (
        "2026-08-11T17:00:00Z"
    )
    assert body["question"]["time"]["conversion_policy_id"] == (
        _CONVERSION_POLICY
    )
    assert body["house_policy"] == {
        "house_system": HouseSystem.REGIOMONTANUS,
        "exact_system_required": True,
    }
    assert body["turned_house"]["perspective_path"] == [7]
    assert body["turned_house"]["terminal_topic_house"] == 9
    assert body["perfection"] == {
        "state": "not_evaluable",
        "principal_querent": Body.MERCURY,
        "principal_quesited": Body.MARS,
        "analysis": None,
        "reason": "classical_perfection_analysis_not_supplied",
        "search_policy": {
            "policy_id": "moira_horary_perfection_search_safety_31_days_v1",
            "max_span_days": 31.0,
            "authority": (
                "moira_owned_computational_safety_not_historical_doctrine"
            ),
            "interval_selection": "caller_supplied_start_and_end_preserved",
            "historical_duration_claim": False,
        },
    }
    assert body["perfection_analysis_input"] is None
    assert body["provenance"]["complete_horary_judgement"] is False
    assert _exact_forbidden_judgement_keys(body) == set()
    assert len(engine.calls) == 1


def test_route_preserves_bounded_perfection_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeHoraryEngine()
    payload = {
        **_PAYLOAD,
        "perspective_path": [],
        "terminal_topic_house": 9,
        "perfection_end": "2026-08-16T12:00:00-05:00",
    }
    with _client(monkeypatch, engine) as client:
        response = client.post("/v1/horary/evidence-profile", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["perfection"]["state"] == "composed"
    assert body["perfection"]["principal_querent"] == Body.MERCURY
    assert body["perfection"]["principal_quesited"] == Body.MARS
    assert body["perfection"]["analysis"]["profile_id"] == (
        "lilly_1647_perfection_v1"
    )
    assert body["perfection"]["analysis"] == body["perfection_analysis_input"]
    assert engine.calls[0][2] is not None


@pytest.mark.parametrize(
    "patch",
    (
        {"score": 1},
        {"question_instant": "2026-08-11T12:00:00"},
        {"perfection_end": "2026-08-16T12:00:00"},
        {"stated_basis": "understood_by_astrologer"},
        {"source_calendar": "julian"},
        {"conversion_policy_id": "caller_asserted_conversion"},
        {"house_system": "Regiomontanus"},
        {"terminal_topic_house": 13},
        {"terminal_topic_house": True},
        {"perspective_path": [0]},
        {"latitude_deg": True},
    ),
)
def test_route_rejects_extra_naive_or_unadmitted_inputs_before_engine(
    monkeypatch: pytest.MonkeyPatch,
    patch: dict[str, object],
) -> None:
    engine = _FakeHoraryEngine()
    with _client(monkeypatch, engine) as client:
        response = client.post(
            "/v1/horary/evidence-profile",
            json={**_PAYLOAD, **patch},
        )

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert engine.calls == []


def test_route_is_discoverable_in_classical_vedic_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeHoraryEngine()
    with _client(monkeypatch, engine) as client:
        response = client.get(
            "/v1/meta/routes",
            params={"family": "classical-vedic", "tag": "horary"},
        )

    assert response.status_code == 200
    routes = response.json()["routes"]
    assert [(item["path"], item["methods"]) for item in routes] == [
        ("/v1/horary/evidence-profile", ["POST"]),
    ]


def test_horary_server_aggregators_export_contract_by_identity() -> None:
    assert public_models.HoraryEvidenceProfileRequest is (
        HoraryEvidenceProfileRequest
    )
    assert public_models.HoraryEvidenceProfileResponse is (
        HoraryEvidenceProfileResponse
    )
    assert public_serializers.serialize_horary_evidence_profile is (
        serialize_horary_evidence_profile
    )
    assert public_services.compute_horary_evidence_profile is (
        compute_horary_evidence_profile
    )
    assert "HoraryEvidenceProfileRequest" in public_models.__all__
    assert "HoraryEvidenceProfileResponse" in public_models.__all__
    assert "serialize_horary_evidence_profile" in public_serializers.__all__
    assert "compute_horary_evidence_profile" in public_services.__all__
