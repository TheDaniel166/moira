"""Kernel-free contract witnesses for primary-directions REST orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from moira.primary_directions import (
    PrimaryArc,
    PrimaryDirectionMotion,
    PrimaryDirectionsPreset,
    evaluate_primary_directions_aggregate,
    evaluate_primary_directions_network,
)
from moira.primary_directions.methods import PrimaryDirectionMethod
from moira.primary_directions.spaces import PrimaryDirectionSpace
from moira_server.models.primary_directions import (
    PrimaryDirectionsRelationsRequest,
    PrimaryDirectionsSearchRequest,
)
from moira_server.routers.primary_directions import (
    primary_directions_arcs_route,
    primary_directions_network_reduction_route,
    primary_directions_network_route,
    primary_directions_profile_reduction_route,
    primary_directions_profile_route,
    primary_directions_relations_route,
    router,
)
from moira_server.serializers.primary_directions import (
    serialize_arcs_with_reduction,
    serialize_network,
    serialize_profile,
    serialize_profile_with_reduction,
)
from moira_server.services import primary_directions as service


_DT = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
_SUBMITTED = {
    "significator": "Sun",
    "promissor": "Moon",
    "arc": 5.0,
    "direction": "DIRECT",
}


def _request(**overrides) -> PrimaryDirectionsSearchRequest:
    values = {
        "dt": _DT,
        "latitude": 41.5,
        "longitude": -71.25,
        "observer_lat": 52.0,
        "observer_lon": 0.0,
    }
    values.update(overrides)
    return PrimaryDirectionsSearchRequest(**values)


class _FakeChart:
    jd_ut = 2451545.0
    datetime_utc = _DT


class _FakeHouses:
    effective_system = "PLACIDUS"
    fallback = False
    fallback_reason = None
    armc = 123.0


class _RecordingEngine:
    def __init__(self) -> None:
        self.chart_calls: list[dict] = []
        self.house_calls: list[dict] = []

    def chart(self, dt, **kwargs):
        self.chart_calls.append({"dt": dt, **kwargs})
        return _FakeChart()

    def houses(self, dt, **kwargs):
        self.house_calls.append({"dt": dt, **kwargs})
        return _FakeHouses()


class _ForbiddenEngine:
    def chart(self, *args, **kwargs):
        raise AssertionError("submitted compact evaluation must not construct a chart")

    def houses(self, *args, **kwargs):
        raise AssertionError("submitted compact evaluation must not construct houses")


def _direct_arc(*, arc: float = 5.0) -> PrimaryArc:
    return PrimaryArc(
        significator="Sun",
        promissor="Moon",
        arc=arc,
        direction="D",
        motion=PrimaryDirectionMotion.DIRECT,
    )


def _converse_arc(*, arc: float = 8.0) -> PrimaryArc:
    return PrimaryArc(
        significator="Sun",
        promissor="Moon",
        arc=arc,
        direction="C",
        motion=PrimaryDirectionMotion.CONVERSE,
    )


def test_all_eight_primary_direction_paths_remain_registered() -> None:
    assert {route.path for route in router.routes} == {
        "/v1/primary-directions/speculum",
        "/v1/primary-directions/arcs",
        "/v1/primary-directions/arcs/reduction",
        "/v1/primary-directions/profile",
        "/v1/primary-directions/profile/reduction",
        "/v1/primary-directions/network",
        "/v1/primary-directions/network/reduction",
        "/v1/primary-directions/relations",
    }


def test_policy_resolution_uses_canonical_presets_and_keys() -> None:
    ptolemy = service.resolve_primary_directions_policy(
        PrimaryDirectionsRelationsRequest(
            submitted_arcs=[],
            policy={"preset": "ptolemy_semiarc"},
        )
    )
    assert str(ptolemy.canonical_preset) == "ptolemy_mundane"
    assert ptolemy.policy.method is PrimaryDirectionMethod.PTOLEMY_SEMI_ARC
    assert ptolemy.policy.space is PrimaryDirectionSpace.IN_MUNDO
    assert ptolemy.chosen_key.name == "PTOLEMY"

    meridian = service.resolve_primary_directions_policy(
        PrimaryDirectionsRelationsRequest(
            submitted_arcs=[],
            policy={"method": "MERIDIAN", "space": "IN_ZODIACO"},
        )
    )
    assert str(meridian.canonical_preset) == "meridian_zodiacal"
    assert meridian.policy.space is PrimaryDirectionSpace.IN_ZODIACO


def test_every_canonical_engine_preset_is_transport_resolvable() -> None:
    for preset in PrimaryDirectionsPreset:
        resolved = service.resolve_primary_directions_policy(
            PrimaryDirectionsRelationsRequest(
                submitted_arcs=[],
                policy={"preset": preset.value},
            )
        )
        assert resolved.canonical_preset is preset
        assert resolved.policy is not None


def test_converse_rapt_preset_can_evaluate_its_own_submitted_arc() -> None:
    request = PrimaryDirectionsRelationsRequest(
        submitted_arcs=[
            {
                **_SUBMITTED,
                "direction": "CONVERSE",
                "method": "placidian_classic_semi_arc",
                "relational_kind": "rapt_parallel",
            }
        ],
        policy={"preset": "placidian_mundane_rapt_parallel_converse"},
    )

    profiles = service.compute_relations_service(_ForbiddenEngine(), request)

    assert len(profiles) == 1
    assert profiles[0].arc.motion is PrimaryDirectionMotion.CONVERSE


def test_policy_resolution_rejects_ambiguous_conflicting_and_unknown_tokens() -> None:
    ambiguous = PrimaryDirectionsRelationsRequest(
        submitted_arcs=[],
        policy={"method": "ptolemy_semi_arc", "space": "in_zodiaco"},
    )
    with pytest.raises(ValueError, match="ambiguous"):
        service.resolve_primary_directions_policy(ambiguous)

    conflict = PrimaryDirectionsRelationsRequest(
        submitted_arcs=[],
        policy={"preset": "regiomontanus", "method": "campanus"},
    )
    with pytest.raises(ValueError, match="conflicts"):
        service.resolve_primary_directions_policy(conflict)

    with pytest.raises(ValidationError):
        PrimaryDirectionsRelationsRequest(
            submitted_arcs=[],
            policy={"key": "invented"},
        )


def test_submitted_arcs_are_real_vessels_and_empty_is_not_omission() -> None:
    request = _request(submitted_arcs=[_SUBMITTED], policy={"key": "PTOLEMY"})
    arcs = service.compute_arcs_service(_ForbiddenEngine(), request)
    assert len(arcs) == 1
    assert type(arcs[0]) is PrimaryArc
    assert arcs[0].solar_rate == pytest.approx(360.0 / 365.25, abs=1e-15)
    assert arcs[0].solar_rate_explicit is False

    empty = _request(submitted_arcs=[])
    assert service.compute_arcs_service(_ForbiddenEngine(), empty) == []
    assert service.compute_profile_service(_ForbiddenEngine(), empty) is None
    assert service.compute_network_service(_ForbiddenEngine(), empty) is None


def test_submitted_solar_key_requires_an_explicit_arc_rate() -> None:
    missing_rate = _request(
        submitted_arcs=[_SUBMITTED],
        policy={"key": "solar"},
    )
    with pytest.raises(ValueError, match="explicit solar_rate"):
        service.compute_arcs_service(_ForbiddenEngine(), missing_rate)

    explicit_rate = _request(
        submitted_arcs=[{**_SUBMITTED, "solar_rate": 0.9855}],
        policy={"key": "solar"},
    )
    arcs = service.compute_arcs_service(_ForbiddenEngine(), explicit_rate)
    assert arcs[0].solar_rate == pytest.approx(0.9855)


def test_submitted_arcs_are_bounded_and_cannot_hide_conversion_fallbacks() -> None:
    with pytest.raises(ValidationError):
        _request(submitted_arcs=[_SUBMITTED] * 4097)
    with pytest.raises(ValidationError):
        _request(submitted_arcs=[{**_SUBMITTED, "arc": -1.0}])
    with pytest.raises(ValidationError):
        _request(submitted_arcs=[{**_SUBMITTED, "direction": "sideways"}])

    conflicting = _request(
        submitted_arcs=[{**_SUBMITTED, "method": "campanus"}],
        policy={"preset": "regiomontanus"},
    )
    with pytest.raises(ValueError, match="must match"):
        service.compute_arcs_service(_ForbiddenEngine(), conflicting)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", True),
        ("longitude", "10"),
        ("observer_lat", "20"),
        ("observer_elev_m", "0"),
        ("max_arc", True),
        ("include_nodes", "false"),
        ("include_relations", "false"),
    ],
)
def test_request_boundary_rejects_numeric_and_boolean_coercion(field: str, value) -> None:
    with pytest.raises(ValidationError):
        _request(**{field: value})


def test_compact_route_resolves_canonical_policy_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    original = service.primary_directions_policy_preset

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(service, "primary_directions_policy_preset", counted)
    response = primary_directions_arcs_route(
        _request(submitted_arcs=[_SUBMITTED]),
        _ForbiddenEngine(),
    )
    assert len(response.arcs) == 1
    assert calls == 1


def test_natal_and_direction_coordinates_are_distinct_and_greenwich_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _RecordingEngine()
    monkeypatch.setattr(service, "find_primary_arcs", lambda **kwargs: [_direct_arc()])
    profile, reduction = service.compute_profile_with_reduction_service(engine, _request())

    assert profile is not None
    assert len(engine.chart_calls) == 1
    assert len(engine.house_calls) == 1
    assert engine.chart_calls[0]["observer_lat"] == 41.5
    assert engine.chart_calls[0]["observer_lon"] == -71.25
    assert engine.house_calls[0]["latitude"] == 52.0
    assert engine.house_calls[0]["longitude"] == 0.0
    assert reduction.natal_observer.latitude == 41.5
    assert reduction.observer.latitude == 52.0
    assert reduction.observer.longitude == 0.0
    assert reduction.engine_surfaces == [
        "moira.primary_directions.find_primary_arcs",
        "moira.primary_directions.evaluate_primary_directions_aggregate",
    ]


def test_empty_profile_and_network_are_transport_values_not_invalid_engine_vessels() -> None:
    profile = serialize_profile(None, chosen_key="NAIBOD")
    assert profile.aggregate.total_arcs == 0
    assert profile.aggregate.profiles == []
    assert profile.aggregate.strongest_significator is None

    network = serialize_network(None)
    assert network.network.nodes == []
    assert network.network.edges == []
    assert network.network.most_connected is None


def test_include_relations_is_a_serializer_gate_without_mutation() -> None:
    aggregate = evaluate_primary_directions_aggregate([_direct_arc()])
    hidden = serialize_profile(
        aggregate,
        chosen_key="PTOLEMY",
        include_relations=False,
    )
    shown = serialize_profile(
        aggregate,
        chosen_key="PTOLEMY",
        include_relations=True,
    )
    assert hidden.aggregate.profiles[0].relation_profiles == []
    assert len(shown.aggregate.profiles[0].relation_profiles) == 1
    relation = shown.aggregate.profiles[0].relation_profiles[0].detected_relation
    assert relation.perfection_kind == "mundane_position_perfection"
    assert relation.relational_kind == "conjunction"
    assert relation.key == "PTOLEMY"
    assert relation.years == pytest.approx(5.0)


def test_network_serialization_preserves_directional_and_motion_topology() -> None:
    network = evaluate_primary_directions_network(
        [_direct_arc(arc=5.0), _converse_arc(arc=2.0)]
    )
    response = serialize_network(network)
    nodes = {node.name: node for node in response.network.nodes}
    assert nodes["Moon"].incoming_count == 0
    assert nodes["Moon"].outgoing_count == 2
    assert nodes["Moon"].direct_count == 1
    assert nodes["Moon"].converse_count == 1
    assert nodes["Sun"].incoming_count == 2
    edge = response.network.edges[0]
    assert edge.count == 2
    assert edge.nearest_arc == pytest.approx(2.0)
    assert edge.direct_count == 1
    assert edge.converse_count == 1


def test_submitted_reduction_reports_actual_source_and_empty_profile(
) -> None:
    engine = _RecordingEngine()
    request = _request(submitted_arcs=[])
    profile, reduction = service.compute_profile_with_reduction_service(engine, request)
    response = serialize_profile_with_reduction(
        profile,
        reduction,
        chosen_key=reduction.chosen_key,
    )
    assert response.result.aggregate.total_arcs == 0
    assert response.reduction.search_mode == "submitted_arcs"
    assert response.reduction.engine_surface == "moira.primary_directions.PrimaryArc"
    assert response.reduction.engine_surfaces == ["moira.primary_directions.PrimaryArc"]
    assert len(engine.chart_calls) == 1
    assert len(engine.house_calls) == 1


def test_arc_reduction_reports_primary_arc_source_for_submitted_values() -> None:
    engine = _RecordingEngine()
    request = _request(submitted_arcs=[_SUBMITTED])
    arcs, reduction = service.compute_arcs_with_reduction_service(engine, request)
    response = serialize_arcs_with_reduction(
        arcs,
        reduction,
        chosen_key=reduction.chosen_key,
    )
    assert response.reduction.engine_surface == "moira.primary_directions.PrimaryArc"
    assert response.reduction.result_surface == "primary_direction_submitted_arcs"
    assert response.result.arcs[0].relational_kind == "conjunction"


def test_route_empty_profile_and_network_contracts_match_compact_and_reduction() -> None:
    engine = _RecordingEngine()
    request = _request(submitted_arcs=[])
    profile = primary_directions_profile_route(request, engine)
    profile_reduction = primary_directions_profile_reduction_route(request, engine)
    network = primary_directions_network_route(request, engine)
    network_reduction = primary_directions_network_reduction_route(request, engine)

    assert profile.aggregate.total_arcs == 0
    assert profile_reduction.result.aggregate.total_arcs == 0
    assert network.network.nodes == []
    assert network_reduction.result.network.nodes == []


def test_route_include_relations_gate_and_relations_route_flags() -> None:
    hidden = primary_directions_profile_route(
        _request(submitted_arcs=[_SUBMITTED], include_relations=False),
        _ForbiddenEngine(),
    )
    shown = primary_directions_profile_route(
        _request(submitted_arcs=[_SUBMITTED], include_relations=True),
        _ForbiddenEngine(),
    )

    assert hidden.aggregate.profiles[0].relation_profiles == []
    assert len(shown.aggregate.profiles[0].relation_profiles) == 1
    with pytest.raises(ValueError, match="intrinsically"):
        primary_directions_relations_route(
            PrimaryDirectionsRelationsRequest(
                submitted_arcs=[_SUBMITTED],
                include_relations=False,
            ),
            _ForbiddenEngine(),
        )
    with pytest.raises(ValueError, match="does not expose"):
        primary_directions_relations_route(
            PrimaryDirectionsRelationsRequest(
                submitted_arcs=[_SUBMITTED],
                include_condition=True,
            ),
            _ForbiddenEngine(),
        )


def test_route_network_response_model_preserves_topology_fields() -> None:
    request = _request(
        submitted_arcs=[
            _SUBMITTED,
            {**_SUBMITTED, "arc": 2.0, "direction": "CONVERSE"},
        ]
    )
    response = primary_directions_network_route(request, _ForbiddenEngine())

    nodes = {node.name: node for node in response.network.nodes}
    assert nodes["Moon"].outgoing_count == 2
    assert nodes["Sun"].incoming_count == 2
    assert response.network.edges[0].nearest_arc == pytest.approx(2.0)
    assert response.network.edges[0].direct_count == 1
    assert response.network.edges[0].converse_count == 1


def test_openapi_policy_and_submitted_arc_contracts_are_typed_and_bounded() -> None:
    app = FastAPI()
    app.include_router(router)
    schemas = app.openapi()["components"]["schemas"]
    search = schemas["PrimaryDirectionsSearchRequest"]["properties"]
    submitted = search["submitted_arcs"]["anyOf"][0]
    assert submitted["maxItems"] == 4096
    assert search["max_arc"]["maximum"] == 360.0
    policy = schemas["PrimaryDirectionsPolicyRequest"]["properties"]
    assert "PrimaryDirectionMethod" in str(policy["method"])
    assert "PrimaryDirectionSpace" in str(policy["space"])
    assert "PrimaryDirectionKey" in str(policy["key"])
