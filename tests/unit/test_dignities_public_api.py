"""
tests/unit/test_dignities_public_api.py

Validates that the curated dignity backend public API is exposed from the
owning module while helper machinery remains internal.

Scope: moira.dignities exports only. No computation is performed.
"""

from dataclasses import fields
from inspect import signature

import moira.dignities as _dignities_module


_CURATED_PUBLIC_NAMES = [
    # Classification enums
    "TruthEvaluationStatus",
    "HorizonHemisphere",
    "HorizonComputationMethod",
    "SectComponentKind",
    "ConditionPolarity",
    "PlanetarySolarPhaseKind",
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
    "HalbHayzDoctrine",
    "MercurySectModel",
    # Policy
    "EssentialDignityPolicy",
    "SolarConditionPolicy",
    "MutualReceptionPolicy",
    "SectHayzPolicy",
    "AccidentalDignityPolicy",
    "DignityComputationPolicy",
    "DignityHorizonFrame",
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
    "EssentialDignityComponentTruth",
    "PlanetarySolarPhaseTruth",
    "MercuryPhaseTruth",
    "HorizonTruth",
    "SectComponentTruth",
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
    "almuten_of_degree",
    "find_phasis",
    "mutual_receptions",
    "is_in_sect",
    "halb_required_hemisphere",
    "is_in_hayz",
    "is_in_halb",
    "is_in_joy",
    "planetary_solar_phase_truth",
    "oriental_occidental",
    "is_besieged",
    # Tables
    "DOMICILE",
    "MODERN_DOMICILE",
    "EXALTATION",
    "DETRIMENT",
    "MODERN_DETRIMENT",
    "FALL",
    "SECT",
    "PREFERRED_HEMISPHERE",
    "PREFERRED_GENDER",
    "PLANETARY_JOYS",
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

    def test_curated_count_is_107(self):
        assert len(_CURATED_PUBLIC_NAMES) == 107

    def test_unadmitted_valens_score_hook_is_absent(self):
        assert "valens_distribution_scores" not in signature(
            _dignities_module.calculate_dignities
        ).parameters
        assert "valens_distribution_scores" not in signature(
            _dignities_module.DignitiesService.calculate_dignities
        ).parameters
        assert "include_timelord_distributions" not in {
            item.name for item in fields(_dignities_module.AccidentalDignityPolicy)
        }
        assert "timelord_distribution_condition" not in {
            item.name for item in fields(_dignities_module.AccidentalDignityTruth)
        }

    def test_halb_and_phase_inclusion_switches_are_explicit_and_default_on(self):
        policy = _dignities_module.DignityComputationPolicy()
        assert policy.accidental.sect.include_hayz is True
        assert policy.accidental.sect.include_halb is True
        assert policy.accidental.include_oriental_occidental is True

