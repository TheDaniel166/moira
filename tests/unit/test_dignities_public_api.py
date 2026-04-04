"""
tests/unit/test_dignities_public_api.py

Validates that the curated dignity backend public API is exposed from the
owning module while helper machinery remains internal.

Scope: moira.dignities exports only. No computation is performed.
"""

import moira.dignities as _dignities_module


_CURATED_PUBLIC_NAMES = [
    # Classification enums
    "ConditionPolarity",
    "EssentialDignityKind",
    "AccidentalConditionKind",
    "SectStateKind",
    "SolarConditionKind",
    "ReceptionKind",
    "ReceptionBasis",
    "ReceptionMode",
    "DispositorshipSubjectSet",
    "DispositorshipRulership",
    "DispositorshipTerminationKind",
    "UnsupportedSubjectHandling",
    "DispositorshipConditionState",
    "PlanetaryConditionState",
    "EssentialDignityDoctrine",
    "MercurySectModel",
    # Policy
    "EssentialDignityPolicy",
    "SolarConditionPolicy",
    "MutualReceptionPolicy",
    "SectHayzPolicy",
    "AccidentalDignityPolicy",
    "DignityComputationPolicy",
    "DispositorshipSubjectPolicy",
    "DispositorshipRulershipPolicy",
    "DispositorshipTerminationPolicy",
    "DispositorshipUnsupportedSubjectPolicy",
    "DispositorshipOrderingPolicy",
    "DispositorshipComputationPolicy",
    # Truth / classification vessels
    "EssentialDignityClassification",
    "AccidentalConditionClassification",
    "AccidentalDignityClassification",
    "SectClassification",
    "SolarConditionClassification",
    "ReceptionClassification",
    "EssentialDignityTruth",
    "AccidentalDignityCondition",
    "SolarConditionTruth",
    "MutualReceptionTruth",
    "SectTruth",
    "AccidentalDignityTruth",
    # Result vessels
    "PlanetaryReception",
    "DispositorLink",
    "DispositorshipChain",
    "DispositorshipProfile",
    "DispositorshipConditionProfile",
    "DispositorshipChartConditionProfile",
    "DispositorshipNetworkEdgeMode",
    "DispositorshipNetworkNode",
    "DispositorshipNetworkEdge",
    "DispositorshipNetworkProfile",
    "DispositorshipSubsystemProfile",
    "DispositorshipComparisonItem",
    "DispositorshipComparisonBundle",
    "PlanetaryConditionProfile",
    "ChartConditionProfile",
    "ConditionNetworkNode",
    "ConditionNetworkEdge",
    "ConditionNetworkProfile",
    "PlanetaryDignity",
    # Entry points / legacy helpers
    "calculate_dignities",
    "calculate_receptions",
    "calculate_dispositorship",
    "calculate_dispositorship_condition_profiles",
    "calculate_dispositorship_chart_condition_profile",
    "calculate_dispositorship_network_profile",
    "calculate_dispositorship_subsystem_profile",
    "compare_dispositorship",
    "calculate_condition_profiles",
    "calculate_chart_condition_profile",
    "calculate_condition_network_profile",
    "DignitiesService",
    "sect_light",
    "is_day_chart",
    "almuten_figuris",
    "find_phasis",
    "mutual_receptions",
]

_INTERNAL_NAMES = [
    "_service",
    "_normalize_planet_positions",
    "_build_house_cusps",
    "_find_receptions",
    "_derive_condition_state",
    "_validate_policy",
    "_validate_dispositorship_policy",
    "_classify_reception_truths",
    "_get_essential_dignity_truth",
]


class TestModuleAgreement:
    def test_all_curated_names_resolve_from_moira_dignities(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_dignities_module, name), f"moira.dignities.{name} not found"

    def test_all_curated_names_in_module_all(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert name in _dignities_module.__all__, f"{name!r} missing from moira.dignities.__all__"

    def test_no_internal_names_in_module_all(self):
        for name in _INTERNAL_NAMES:
            assert name not in _dignities_module.__all__, f"{name!r} leaked into moira.dignities.__all__"

    def test_internal_names_remain_accessible_on_module(self):
        module_internal_names = ["_service"]
        service_internal_names = [
            "_normalize_planet_positions",
            "_build_house_cusps",
            "_find_receptions",
            "_derive_condition_state",
            "_validate_policy",
            "_validate_dispositorship_policy",
            "_classify_reception_truths",
            "_get_essential_dignity_truth",
        ]
        for name in module_internal_names:
            assert hasattr(_dignities_module, name), (
                f"moira.dignities.{name} disappeared; helper should remain module-internal"
            )
        for name in service_internal_names:
            assert hasattr(_dignities_module.DignitiesService, name), (
                f"DignitiesService.{name} disappeared; helper should remain internal"
            )

    def test_curated_count_is_76(self):
        assert len(_CURATED_PUBLIC_NAMES) == 76
