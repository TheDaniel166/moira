"""
tests/unit/test_dignities_public_api.py

Validates that the curated dignity backend public API is exposed at the moira
package root while helper machinery remains internal.

Scope: moira.__init__ dignity exports only. No computation is performed.
"""

import moira
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
    "PlanetaryConditionProfile",
    "ChartConditionProfile",
    "ConditionNetworkNode",
    "ConditionNetworkEdge",
    "ConditionNetworkProfile",
    "PlanetaryDignity",
    # Entry points / legacy helpers
    "calculate_dignities",
    "calculate_receptions",
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
    "_classify_reception_truths",
    "_get_essential_dignity_truth",
]


class TestPackageLevelResolution:
    def test_all_curated_names_resolve_from_moira(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(moira, name), f"moira.{name} not found"

    def test_all_curated_names_in_moira_all(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert name in moira.__all__, f"{name!r} missing from moira.__all__"

    def test_no_internal_names_in_moira_all(self):
        for name in _INTERNAL_NAMES:
            assert name not in moira.__all__, f"{name!r} leaked into moira.__all__"

    def test_internal_names_not_in_package_namespace(self):
        for name in _INTERNAL_NAMES:
            assert not hasattr(moira, name), f"Internal {name!r} leaked into moira"


class TestModuleAgreement:
    def test_all_curated_names_resolve_from_moira_dignities(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_dignities_module, name), f"moira.dignities.{name} not found"

    def test_curated_package_exports_are_module_objects(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert getattr(moira, name) is getattr(_dignities_module, name), (
                f"moira.{name} and moira.dignities.{name} are different objects"
            )

    def test_internal_names_remain_accessible_on_module(self):
        module_internal_names = ["_service"]
        service_internal_names = [
            "_normalize_planet_positions",
            "_build_house_cusps",
            "_find_receptions",
            "_derive_condition_state",
            "_validate_policy",
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

    def test_curated_count_is_47(self):
        assert len(_CURATED_PUBLIC_NAMES) == 47
