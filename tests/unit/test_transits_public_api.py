"""
tests/unit/test_transits_public_api.py

Validates that the curated transits backend public API is exposed from the
owning module while helper machinery remains internal.

Scope: moira.transits exports only. No computation is performed.
"""

import moira.transits as _transits_module


_CURATED_PUBLIC_NAMES = [
    # Enums
    "TransitTargetKind",
    "TransitSearchKind",
    "TransitWrapperKind",
    "TransitRelationKind",
    "TransitRelationBasis",
    "TransitConditionState",
    "TransitConditionNetworkNodeKind",
    # Policy
    "TransitSearchPolicy",
    "ReturnSearchPolicy",
    "SyzygySearchPolicy",
    "TransitComputationPolicy",
    # Truth / classification vessels
    "LongitudeResolutionTruth",
    "CrossingSearchTruth",
    "TransitComputationTruth",
    "IngressComputationTruth",
    "LongitudeResolutionClassification",
    "CrossingSearchClassification",
    "TransitComputationClassification",
    "IngressComputationClassification",
    # Relation / condition / aggregate vessels
    "TransitRelation",
    "TransitConditionProfile",
    "TransitChartConditionProfile",
    "TransitConditionNetworkNode",
    "TransitConditionNetworkEdge",
    "TransitConditionNetworkProfile",
    # Result vessels / entry points
    "TransitEvent",
    "IngressEvent",
    "next_transit",
    "find_transits",
    "find_ingresses",
    "solar_return",
    "lunar_return",
    "last_new_moon",
    "last_full_moon",
    "prenatal_syzygy",
    "planet_return",
    "transit_relations",
    "ingress_relations",
    "transit_condition_profiles",
    "ingress_condition_profiles",
    "transit_chart_condition_profile",
    "transit_condition_network_profile",
]

_INTERNAL_NAMES = [
    "_build_transit_relation",
    "_build_ingress_relation",
    "_build_transit_condition_profile",
    "_build_ingress_condition_profile",
    "_condition_profile_sort_key",
    "_transit_network_target_node_id",
    "_transit_network_edge_sort_key",
    "_validate_policy",
    "_validate_direction",
    "_validate_transit_range",
]


class TestModuleAgreement:
    def test_all_curated_names_resolve_from_moira_transits(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_transits_module, name), f"moira.transits.{name} not found"

    def test_all_curated_names_in_module_all(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert name in _transits_module.__all__, f"{name!r} missing from moira.transits.__all__"

    def test_no_internal_names_in_module_all(self):
        for name in _INTERNAL_NAMES:
            assert name not in _transits_module.__all__, f"{name!r} leaked into moira.transits.__all__"

    def test_internal_names_remain_accessible_on_module(self):
        for name in _INTERNAL_NAMES:
            assert hasattr(_transits_module, name), (
                f"moira.transits.{name} disappeared; helper should remain module-internal"
            )

    def test_curated_count_is_42(self):
        assert len(_CURATED_PUBLIC_NAMES) == 42
