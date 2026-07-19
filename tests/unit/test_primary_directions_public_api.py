"""
P12 Public API Verification -- tests/unit/test_primary_directions_public_api.py

Verify that the primary-directions subsystem exposes its curated module surface
without leaking into the intentionally thin root `moira` package.
"""

import moira
import moira.facade as facade_module
from moira import primary_directions
from moira._facade_special import SpecialTopicsFacadeMixin


EXPECTED_SYMBOLS = [
    "DIRECT",
    "CONVERSE",
    "PrimaryDirectionMethod",
    "PrimaryDirectionAntisciaKind",
    "PrimaryDirectionAntisciaTarget",
    "MorinusAspectContext",
    "PrimaryDirectionFixedStarTarget",
    "PlacidianRaptParallelTarget",
    "PtolemaicParallelRelation",
    "PtolemaicParallelTarget",
    "PrimaryDirectionsPreset",
    "primary_directions_policy_preset",
    "PrimaryDirectionRelationalKind",
    "PrimaryDirectionRelationPolicy",
    "default_positional_relation_policy",
    "antiscia_relation_policy",
    "zodiacal_aspect_relation_policy",
    "ptolemaic_parallel_relation_policy",
    "placidian_rapt_parallel_relation_policy",
    "PrimaryDirectionSpace",
    "PrimaryDirectionMotion",
    "PrimaryDirectionKey",
    "PrimaryDirectionKeyFamily",
    "PrimaryDirectionLatitudeDoctrine",
    "PrimaryDirectionLatitudeSource",
    "PrimaryDirectionConverseDoctrine",
    "PrimaryDirectionTargetClass",
    "PrimaryDirectionPerfectionKind",
    "PrimaryDirectionsConditionState",
    "PrimaryDirectionsPolicy",
    "PrimaryDirectionKeyPolicy",
    "PrimaryDirectionLatitudePolicy",
    "PrimaryDirectionLatitudeSourcePolicy",
    "PrimaryDirectionTargetPolicy",
    "PrimaryDirectionPerfectionPolicy",
    "SpeculumEntry",
    "PrimaryArc",
    "PrimaryDirectionRelation",
    "PrimaryDirectionRelationProfile",
    "PrimaryDirectionsSignificatorProfile",
    "PrimaryDirectionsAggregateProfile",
    "PrimaryDirectionsNetworkNode",
    "PrimaryDirectionsNetworkEdge",
    "PrimaryDirectionsNetworkProfile",
    "speculum",
    "find_primary_arcs",
    "relate_primary_arc",
    "evaluate_primary_direction_relations",
    "evaluate_primary_direction_condition",
    "evaluate_primary_directions_aggregate",
    "evaluate_primary_directions_network",
]


def test_primary_directions_module_exports_curated_surface() -> None:
    missing = [symbol for symbol in EXPECTED_SYMBOLS if not hasattr(primary_directions, symbol)]
    assert not missing, f"Missing symbols in moira.primary_directions: {missing}"
    assert "_mundane_arcs" not in primary_directions.__all__
    assert "_required_ha" not in primary_directions.__all__


def test_moira_root_surface_remains_thin_for_primary_directions() -> None:
    assert "primary_directions" not in moira.__all__
    assert "PrimaryDirectionRelation" not in moira.__all__
    assert not hasattr(moira, "PrimaryDirectionRelation")


def test_primary_arc_does_not_expose_fictional_key_family() -> None:
    from moira.primary_directions import PrimaryArc, PrimaryDirectionMotion

    arc = PrimaryArc(
        significator="Sun",
        promissor="MC",
        arc=12.5,
        direction="D",
        motion=PrimaryDirectionMotion.DIRECT,
    )
    # An arc holds no key, so it must not claim a key family.
    assert not hasattr(arc, "key_family")


def test_special_facade_preserves_legacy_primary_direction_arguments_and_adds_policy_controls(
    monkeypatch,
) -> None:
    calls = []

    def fake_find(*args, **kwargs):
        calls.append((args, kwargs))
        return "arcs"

    monkeypatch.setattr(facade_module, "find_primary_arcs", fake_find)
    facade = SpecialTopicsFacadeMixin()
    result = facade.primary_directions(
        "chart",
        "houses",
        40.0,
        75.0,
        False,
        ["Sun"],
        ["Moon"],
        solar_speed=0.9,
        obliquity=23.4,
        policy="policy",
    )

    assert result == "arcs"
    assert calls == [
        (
            ("chart", "houses", 40.0),
            {
                "max_arc": 75.0,
                "include_converse": False,
                "significators": ["Sun"],
                "promissors": ["Moon"],
                "solar_speed": 0.9,
                "obliquity": 23.4,
                "policy": "policy",
            },
        )
    ]


def test_special_facade_exposes_primary_direction_evaluation_parity(monkeypatch) -> None:
    facade = SpecialTopicsFacadeMixin()
    sentinel = object()
    calls = []

    def record(name):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return sentinel

        return inner

    for name in (
        "primary_directions_policy_preset",
        "evaluate_primary_direction_relations",
        "evaluate_primary_direction_condition",
        "evaluate_primary_directions_aggregate",
        "evaluate_primary_directions_network",
    ):
        monkeypatch.setattr(facade_module, name, record(name))

    assert facade.primary_directions_policy_preset("preset", include_converse=False) is sentinel
    assert facade.primary_direction_relations("arc", policy="policy") is sentinel
    assert facade.primary_direction_condition(["arc"], policy="policy") is sentinel
    assert facade.primary_directions_profile(["arc"], policy="policy") is sentinel
    assert facade.primary_directions_network(["arc"], policy="policy") is sentinel
    assert [name for name, _, _ in calls] == [
        "primary_directions_policy_preset",
        "evaluate_primary_direction_relations",
        "evaluate_primary_direction_condition",
        "evaluate_primary_directions_aggregate",
        "evaluate_primary_directions_network",
    ]
