"""Focused service and route gates for the neutral Mundane contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

import moira_server.models as public_models
import moira_server.serializers as public_serializers
import moira_server.services as public_services
from moira.mundane import (
    CardinalIngress,
    CardinalIngressReceipt,
    EclipseAnchorEpoch,
    EclipseEventReceipt,
    EclipseKind,
    EclipseNamedEpochReceipt,
    JupiterSaturnConjunctionReceipt,
    JupiterSaturnConjunctionSequenceReceipt,
    MundaneAngularRootToleranceReceipt,
    MundaneEpoch,
    MundaneEvaluationStatus,
    MundaneEventEvidence,
    MundaneEventProvenance,
    MundaneLocationRole,
    MundaneMotionState,
    MundaneProvenanceMode,
    MundaneSearchInterval,
    MundaneTimescale,
    PrimarySyzygyPhase,
    PrimarySyzygyReceipt,
    select_strictly_preceding_primary_syzygy,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.mundane import (
    MundaneEventChartProfileRequest,
    MundaneEventChartProfileResponse,
)
from moira_server.serializers.mundane import serialize_mundane_event_chart_profile
from moira_server.services.mundane import compute_mundane_event_chart_profile


pytestmark = pytest.mark.loopback


_FRAME = "iau2006_p03_iau2000a_true_ecliptic_and_equinox_of_date"
_SUN_MOON_CORRECTIONS = (
    "geocentric_apparent_light_time_annual_aberration_iau2006_frame_bias_"
    "precession_iau2000a_nutation_true_ecliptic_projection"
)
_SOLAR_PRODUCT = (
    "moira_observer_centered_geocentric_apparent_solar_longitude_"
    "iau2006_p03_iau2000a_true_ecliptic_and_equinox_of_date"
)
_SYZYGY_PRODUCT = (
    "moira_observer_centered_geocentric_apparent_sun_moon_longitude_"
    "difference_iau2006_p03_iau2000a_true_ecliptic_and_equinox_of_date"
)
_JUPITER_SATURN_PRODUCT = (
    "moira_geocentric_apparent_jupiter_saturn_ecliptic_longitude_difference_"
    "true_ecliptic_of_date"
)
_ECLIPSE_FRAME = "moira_native_geocentric_physical_shadow_axis_event_geometry_v1"
_SOLAR_ECLIPSE_CORRECTIONS = (
    "earth_reception_light_time_sun_and_moon_shadow_axis_"
    "stellar_aberration_excluded_v1"
)
_TOLERANCE = MundaneAngularRootToleranceReceipt(
    maximum_abs_residual_deg=1e-6,
    basis="server transport invariant fixture",
)


_BASE_PAYLOAD = {
    "search_start_utc": "2025-01-01T00:00:00Z",
    "search_end_utc": "2025-12-30T00:00:00Z",
    "location": {
        "label": "Explicit London test location",
        "role": "user_specified",
        "source_id": "test.location.london",
        "valid_from_utc": None,
        "valid_until_utc": None,
        "latitude_deg": 51.5074,
        "longitude_deg_east": -0.1278,
    },
    "house_system": "P",
}


def _provenance(
    longitude_product: str,
    *,
    reference_frame: str = _FRAME,
    correction_regime: str = _SUN_MOON_CORRECTIONS,
) -> MundaneEventProvenance:
    return MundaneEventProvenance(
        mode=MundaneProvenanceMode.EXTERNAL_AUTHORITY,
        source_id="server.mundane.fixture",
        method_id="server_mundane_fixture_v1",
        provenance_family_id="server_mundane_fixture_family_v1",
        longitude_product_id=longitude_product,
        reference_frame=reference_frame,
        correction_regime=correction_regime,
        solver_semantics="fixture_exact_roots_v1",
        source_refs=("tests.server.test_server_mundane_routes",),
    )


def _ingress(ingress: CardinalIngress, jd: float) -> CardinalIngressReceipt:
    return CardinalIngressReceipt(
        ingress=ingress,
        epoch=MundaneEpoch(jd, MundaneTimescale.UT1),
        sun_longitude_deg=ingress.target_longitude_deg,
        root_residual_deg=0.0,
        solver_tolerance_days=1e-8,
        angular_root_tolerance=_TOLERANCE,
        provenance=_provenance(_SOLAR_PRODUCT),
    )


def _syzygy_selection(anchor: CardinalIngressReceipt):
    provenance = _provenance(_SYZYGY_PRODUCT)
    candidates = (
        PrimarySyzygyReceipt(
            phase=PrimarySyzygyPhase.NEW_MOON,
            epoch=MundaneEpoch(anchor.epoch.jd - 20.0, MundaneTimescale.UT1),
            sun_longitude_deg=10.0,
            moon_longitude_deg=10.0,
            root_residual_deg=0.0,
            solver_tolerance_days=1e-8,
            angular_root_tolerance=_TOLERANCE,
            provenance=provenance,
        ),
        PrimarySyzygyReceipt(
            phase=PrimarySyzygyPhase.FULL_MOON,
            epoch=MundaneEpoch(anchor.epoch.jd - 10.0, MundaneTimescale.UT1),
            sun_longitude_deg=10.0,
            moon_longitude_deg=190.0,
            root_residual_deg=0.0,
            solver_tolerance_days=1e-8,
            angular_root_tolerance=_TOLERANCE,
            provenance=provenance,
        ),
    )
    return select_strictly_preceding_primary_syzygy(anchor, candidates)


def _eclipse(jd: float, eclipse_id: str) -> EclipseEventReceipt:
    provenance = _provenance(
        "not_applicable_to_greatest_eclipse_epoch",
        reference_frame=_ECLIPSE_FRAME,
        correction_regime=_SOLAR_ECLIPSE_CORRECTIONS,
    )
    named = EclipseNamedEpochReceipt(
        eclipse_id=eclipse_id,
        eclipse_kind=EclipseKind.SOLAR,
        epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
        epoch=MundaneEpoch(jd, MundaneTimescale.UT1),
        provenance=provenance,
    )
    return EclipseEventReceipt(
        eclipse_id=eclipse_id,
        eclipse_kind=EclipseKind.SOLAR,
        anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
        provenance=provenance,
        named_epochs=(named,),
    )


def _jupiter_saturn_sequence(start: float, end: float):
    provenance = _provenance(
        _JUPITER_SATURN_PRODUCT,
        correction_regime=(
            "geocentric_apparent_light_time_deflection_aberration_nutation"
        ),
    )
    roots = tuple(
        JupiterSaturnConjunctionReceipt(
            event_id=f"fixture-js-{index}",
            epoch=MundaneEpoch(start + offset, MundaneTimescale.UT1),
            jupiter_longitude_deg=longitude,
            saturn_longitude_deg=longitude,
            root_residual_deg=0.0,
            jupiter_motion=MundaneMotionState.DIRECT,
            saturn_motion=MundaneMotionState.DIRECT,
            solver_tolerance_days=1e-8,
            angular_root_tolerance=_TOLERANCE,
            provenance=provenance,
        )
        for index, (offset, longitude) in enumerate(((80.0, 20.0), (240.0, 21.0)))
    )
    return JupiterSaturnConjunctionSequenceReceipt(
        search_interval=MundaneSearchInterval(
            MundaneEpoch(start, MundaneTimescale.UT1),
            MundaneEpoch(end, MundaneTimescale.UT1),
        ),
        roots=roots,
    )


@dataclass(frozen=True)
class _RawIngress:
    sign: str
    evidence: MundaneEventEvidence


@dataclass(frozen=True)
class _RawEclipse:
    jd_ut: float


@dataclass(frozen=True)
class _RawSeries:
    start: float
    end: float


class _FakeMundaneEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self._reader = object()

    def is_kernel_available(self) -> bool:
        return False

    def ingresses(self, body, start, end):
        self.calls.append(("ingresses", (body, start, end)))
        offsets = (10.0, 100.0, 190.0, 280.0)
        return tuple(
            _RawIngress(
                sign=ingress.value.capitalize(),
                evidence=MundaneEventEvidence(
                    status=MundaneEvaluationStatus.EVALUATED,
                    receipt=_ingress(ingress, start + offset),
                    issue=None,
                ),
            )
            for ingress, offset in zip(CardinalIngress, offsets)
        )

    def assess_transit_cardinal_ingress(self, event):
        self.calls.append(("assess_ingress", event.sign))
        return event.evidence

    def assess_transit_primary_syzygy(self, anchor):
        self.calls.append(("assess_syzygy", anchor.ingress))
        return _syzygy_selection(anchor)

    def eclipse_receipt_from_event(self, event, *, eclipse_id):
        self.calls.append(("adapt_eclipse", eclipse_id))
        return _eclipse(event.jd_ut, eclipse_id)

    def jupiter_saturn_sequence_from_series(self, series):
        self.calls.append(("adapt_jupiter_saturn", series))
        return _jupiter_saturn_sequence(series.start, series.end)


class _FakeEclipseCalculator:
    def __init__(self, *, reader) -> None:
        self.reader = reader

    def next_solar_eclipse(self, start: float) -> _RawEclipse:
        return _RawEclipse(start + 30.0)

    def next_lunar_eclipse(self, start: float) -> _RawEclipse:
        raise AssertionError("solar request must not call the lunar solver")


def _client(monkeypatch: pytest.MonkeyPatch, engine: _FakeMundaneEngine) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    monkeypatch.setattr(
        "moira_server.services.mundane.EclipseCalculator",
        _FakeEclipseCalculator,
    )
    monkeypatch.setattr(
        "moira_server.services.mundane.great_conjunctions",
        lambda start, end, *, reader: _RawSeries(start, end),
    )
    return TestClient(create_app(ServerConfig(docs_enabled=False)))


def _forbidden_keys(value: object) -> set[str]:
    forbidden = {
        "judgement",
        "score",
        "outcome",
        "advice",
        "recommendation",
        "prediction",
    }
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(forbidden.intersection(value))
        for item in value.values():
            found.update(_forbidden_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_forbidden_keys(item))
    return found


def test_cardinal_route_keeps_all_four_and_selected_anchor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeMundaneEngine()
    payload = {
        **_BASE_PAYLOAD,
        "event_type": "cardinal_ingress",
        "selected_ingress": "libra",
        "selection_policy": "all_four_cardinal_ingresses_v1",
    }
    with _client(monkeypatch, engine) as client:
        response = client.post("/v1/mundane/event-chart-profile", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["selection"]["event_type"] == "cardinal_ingress"
    assert [
        item["ingress"] for item in body["selection"]["selection"]["all_events"]
    ] == ["aries", "cancer", "libra", "capricorn"]
    assert body["profile"]["anchor_event"]["receipt"]["ingress"] == "libra"
    assert body["profile"]["preceding_syzygy"]["status"] == "evaluated"
    assert body["profile"]["local_projection"]["status"] == "evaluated"
    assert _forbidden_keys(body) == set()
    assert [name for name, _ in engine.calls].count("assess_ingress") == 4


def test_primary_syzygy_route_preserves_both_candidates_and_strict_predecessor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeMundaneEngine()
    payload = {
        **_BASE_PAYLOAD,
        "event_type": "primary_syzygy",
        "anchor_ingress": "aries",
    }
    with _client(monkeypatch, engine) as client:
        response = client.post("/v1/mundane/event-chart-profile", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    selection = body["selection"]["selection"]
    assert [item["phase"] for item in selection["candidates"]] == [
        "new_moon",
        "full_moon",
    ]
    assert selection["selected"]["phase"] == "full_moon"
    assert body["profile"]["anchor_event"]["receipt"]["event_type"] == (
        "primary_syzygy"
    )
    assert body["profile"]["cardinal_ingress_selection"]["status"] == (
        "not_evaluable"
    )
    assert body["profile"]["preceding_syzygy"]["status"] == "not_evaluable"


def test_eclipse_route_keeps_named_epoch_and_typed_unavailable_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeMundaneEngine()
    payload = {
        **_BASE_PAYLOAD,
        "event_type": "eclipse",
        "eclipse_id": "caller-label-se-2025",
        "eclipse_kind": "solar",
        "chart_epoch_kind": "ecliptic_syzygy",
    }
    with _client(monkeypatch, engine) as client:
        response = client.post("/v1/mundane/event-chart-profile", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["selection"]["event"]["named_epochs"][0]["epoch_kind"] == (
        "greatest_eclipse"
    )
    assert body["selection"]["chart_epoch_kind"] == "ecliptic_syzygy"
    assert body["profile"]["local_projection"]["status"] == "not_evaluable"
    reasons = {item["reason"] for item in body["profile"]["not_evaluable"]}
    assert "source_receipt_incomplete" in reasons
    assert "local_eclipse_circumstances_unavailable" in reasons


def test_jupiter_saturn_route_retains_complete_multi_root_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeMundaneEngine()
    payload = {
        **_BASE_PAYLOAD,
        "event_type": "jupiter_saturn_ecliptic_longitude_conjunction",
        "selected_root_index": 1,
    }
    with _client(monkeypatch, engine) as client:
        response = client.post("/v1/mundane/event-chart-profile", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    roots = body["selection"]["sequence"]["roots"]
    assert [item["event_id"] for item in roots] == ["fixture-js-0", "fixture-js-1"]
    assert body["selection"]["selected_root_index"] == 1
    assert body["profile"]["anchor_event"]["receipt"]["event_id"] == (
        "fixture-js-1"
    )
    assert body["profile"]["local_projection"]["status"] == "evaluated"


@pytest.mark.parametrize(
    "patch",
    (
        {"score": 1},
        {"search_start_utc": "2025-01-01T00:00:00"},
        {"event_type": "national_chart"},
        {"house_system": "Placidus"},
        {"selected_root_index": True},
        {"selected_root_index": -1},
        {"provenance": {"mode": "moira_ephemeris"}},
    ),
)
def test_route_rejects_extra_naive_or_unadmitted_inputs_before_engine(
    monkeypatch: pytest.MonkeyPatch,
    patch: dict[str, object],
) -> None:
    engine = _FakeMundaneEngine()
    payload = {
        **_BASE_PAYLOAD,
        "event_type": "jupiter_saturn_ecliptic_longitude_conjunction",
        "selected_root_index": 0,
        **patch,
    }
    with _client(monkeypatch, engine) as client:
        response = client.post("/v1/mundane/event-chart-profile", json=payload)

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"
    assert engine.calls == []


def test_institutional_location_requires_explicit_validity_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeMundaneEngine()
    payload = {
        **_BASE_PAYLOAD,
        "event_type": "cardinal_ingress",
        "selected_ingress": "aries",
        "selection_policy": "all_four_cardinal_ingresses_v1",
        "location": {
            **_BASE_PAYLOAD["location"],
            "role": MundaneLocationRole.SEAT_OF_GOVERNMENT,
        },
    }
    with _client(monkeypatch, engine) as client:
        response = client.post("/v1/mundane/event-chart-profile", json=payload)

    assert response.status_code == 422
    assert engine.calls == []


def test_route_is_discoverable_in_predictive_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeMundaneEngine()
    with _client(monkeypatch, engine) as client:
        response = client.get(
            "/v1/meta/routes",
            params={"family": "predictive", "tag": "mundane"},
        )

    assert response.status_code == 200
    assert [
        (item["path"], item["methods"]) for item in response.json()["routes"]
    ] == [("/v1/mundane/event-chart-profile", ["POST"])]


def test_mundane_server_aggregators_export_contract_by_identity() -> None:
    assert public_models.MundaneEventChartProfileRequest is (
        MundaneEventChartProfileRequest
    )
    assert public_models.MundaneEventChartProfileResponse is (
        MundaneEventChartProfileResponse
    )
    assert public_serializers.serialize_mundane_event_chart_profile is (
        serialize_mundane_event_chart_profile
    )
    assert public_services.compute_mundane_event_chart_profile is (
        compute_mundane_event_chart_profile
    )
    assert "MundaneEventChartProfileRequest" in public_models.__all__
    assert "MundaneEventChartProfileResponse" in public_models.__all__
    assert "serialize_mundane_event_chart_profile" in public_serializers.__all__
    assert "compute_mundane_event_chart_profile" in public_services.__all__


def test_request_normalizes_aware_offsets_at_transport_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = MundaneEventChartProfileRequest.model_validate(
        {
            **_BASE_PAYLOAD,
            "event_type": "cardinal_ingress",
            "selected_ingress": "aries",
            "selection_policy": "all_four_cardinal_ingresses_v1",
            "search_start_utc": "2025-01-01T00:00:00-05:00",
            "search_end_utc": "2025-12-30T00:00:00-05:00",
        }
    )
    seen: list[datetime] = []
    def fake_jd_from_datetime(instant: datetime) -> float:
        seen.append(instant)
        return 2_460_000.0 if len(seen) == 1 else 2_460_363.0

    monkeypatch.setattr(
        "moira_server.services.mundane.jd_from_datetime",
        fake_jd_from_datetime,
    )
    monkeypatch.setattr(
        "moira_server.services.mundane.utc_to_ut1",
        lambda jd: jd,
    )
    engine = _FakeMundaneEngine()

    compute_mundane_event_chart_profile(engine, request)

    assert seen[:2] == [
        datetime(2025, 1, 1, 5, tzinfo=timezone.utc),
        datetime(2025, 12, 30, 5, tzinfo=timezone.utc),
    ]
