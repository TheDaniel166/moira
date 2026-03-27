"""
tests/unit/test_lots_public_api.py

Validates that the curated lots backend public API is exposed from the owning
module while helper machinery remains internal.

Scope: moira.lots exports only. No computation is performed.
"""

import moira.lots as _lots_module


_CURATED_PUBLIC_NAMES = [
    # Enums
    "LotReferenceKind",
    "LotReversalKind",
    "LotDependencyRole",
    "LotConditionState",
    "LotConditionNetworkEdgeMode",
    "LotsReferenceFailureMode",
    # Policy
    "LotsDerivedReferencePolicy",
    "LotsExternalReferencePolicy",
    "LotsComputationPolicy",
    # Truth / classification vessels
    "LotReferenceTruth",
    "ArabicPartComputationTruth",
    "LotReferenceClassification",
    "ArabicPartClassification",
    # Relational / aggregate vessels
    "LotDependency",
    "LotConditionProfile",
    "LotChartConditionProfile",
    "LotConditionNetworkNode",
    "LotConditionNetworkEdge",
    "LotConditionNetworkProfile",
    # Result vessels / entry points
    "ArabicPart",
    "calculate_lots",
    "calculate_lot_dependencies",
    "calculate_all_lot_dependencies",
    "calculate_lot_condition_profiles",
    "calculate_lot_chart_condition_profile",
    "calculate_lot_condition_network_profile",
    "ArabicPartsService",
    "list_parts",
]

_INTERNAL_NAMES = [
    "_service",
    "_build_refs",
    "_classify_part",
    "_build_part_dependencies",
    "_build_condition_profile",
    "_validate_policy",
    "_validate_planet_longitudes",
    "_validate_house_cusps",
]


class TestModuleAgreement:
    def test_all_curated_names_resolve_from_moira_lots(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_lots_module, name), f"moira.lots.{name} not found"

    def test_all_curated_names_in_module_all(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert name in _lots_module.__all__, f"{name!r} missing from moira.lots.__all__"

    def test_no_internal_names_in_module_all(self):
        for name in _INTERNAL_NAMES:
            assert name not in _lots_module.__all__, f"{name!r} leaked into moira.lots.__all__"

    def test_internal_names_remain_accessible_on_module(self):
        module_internal_names = ["_service"]
        service_internal_names = [
            "_build_refs",
            "_classify_part",
            "_build_part_dependencies",
            "_build_condition_profile",
            "_validate_policy",
            "_validate_planet_longitudes",
            "_validate_house_cusps",
        ]
        for name in module_internal_names:
            assert hasattr(_lots_module, name), (
                f"moira.lots.{name} disappeared; helper should remain module-internal"
            )
        for name in service_internal_names:
            assert hasattr(_lots_module.ArabicPartsService, name), (
                f"ArabicPartsService.{name} disappeared; helper should remain internal"
            )

    def test_curated_count_is_28(self):
        assert len(_CURATED_PUBLIC_NAMES) == 28
