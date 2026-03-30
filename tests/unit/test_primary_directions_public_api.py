"""
P12 Public API Verification -- tests/unit/test_primary_directions_public_api.py

Verify that the primary-directions subsystem exposes its curated module surface
without leaking into the intentionally thin root `moira` package.
"""

import moira
from moira import primary_directions


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
