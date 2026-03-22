"""
tests/unit/test_stars_public_api.py

Validates that the curated unified-star backend public API is exposed at the
moira package root while helper machinery remains internal.

Scope: moira.__init__ unified-star exports only. No computation is performed.
"""

import moira
import moira.fixed_stars as _fixed_stars_module
import moira.stars as _stars_module


_CURATED_PUBLIC_NAMES = [
    # Fixed-star truth / classification / relation / condition
    "StarPositionTruth",
    "StarPositionClassification",
    "StarRelation",
    "StarConditionState",
    "StarConditionProfile",
    "StarChartConditionProfile",
    "StarConditionNetworkNode",
    "StarConditionNetworkEdge",
    "StarConditionNetworkProfile",
    "HeliacalEventTruth",
    "HeliacalEventClassification",
    "HeliacalEvent",
    # Fixed-star policy / result / entry points
    "FixedStarLookupPolicy",
    "HeliacalSearchPolicy",
    "FixedStarComputationPolicy",
    "StarPosition",
    "load_catalog",
    "fixed_star_at",
    "all_stars_at",
    "list_stars",
    "find_stars",
    "star_magnitude",
    "heliacal_rising_event",
    "heliacal_setting_event",
    "heliacal_rising",
    "heliacal_setting",
    "star_chart_condition_profile",
    "star_condition_network_profile",
    # Unified-star policy / truth / relation / result / entry points
    "UnifiedStarMergePolicy",
    "UnifiedStarComputationPolicy",
    "FixedStarTruth",
    "FixedStarClassification",
    "UnifiedStarRelation",
    "FixedStar",
    "star_at",
    "stars_near",
    "stars_by_magnitude",
    "list_named_stars",
    "find_named_stars",
]

_FIXED_STAR_INTERNAL_NAMES = [
    "_classify_star_position_truth",
    "_classify_heliacal_event_truth",
    "_build_star_position_relation",
    "_build_heliacal_event_relation",
    "_build_star_position_condition_profile",
    "_build_heliacal_event_condition_profile",
    "_require_finite",
    "_validate_lat_lon",
    "_validate_fixed_star_policy",
]

_UNIFIED_STAR_INTERNAL_NAMES = [
    "_classify_fixed_star_truth",
    "_build_fixed_star_relation",
    "_build_fixed_star_condition_profile",
    "_resolve_unified_star_policy",
    "_validate_unified_star_policy",
    "_fixed_star_policy_from_unified",
    "_validate_observer_inputs",
]


class TestPackageLevelResolution:
    def test_all_curated_names_resolve_from_moira(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(moira, name), f"moira.{name} not found"

    def test_all_curated_names_in_moira_all(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert name in moira.__all__, f"{name!r} missing from moira.__all__"

    def test_no_internal_names_in_moira_all(self):
        for name in _FIXED_STAR_INTERNAL_NAMES + _UNIFIED_STAR_INTERNAL_NAMES:
            assert name not in moira.__all__, f"{name!r} leaked into moira.__all__"

    def test_internal_names_not_in_package_namespace(self):
        for name in _FIXED_STAR_INTERNAL_NAMES + _UNIFIED_STAR_INTERNAL_NAMES:
            assert not hasattr(moira, name), f"Internal {name!r} leaked into moira"


class TestModuleAgreement:
    def test_fixed_star_curated_names_resolve_from_modules(self):
        fixed_star_names = {
            "StarPositionTruth",
            "StarPositionClassification",
            "StarRelation",
            "StarConditionState",
            "StarConditionProfile",
            "StarChartConditionProfile",
            "StarConditionNetworkNode",
            "StarConditionNetworkEdge",
            "StarConditionNetworkProfile",
            "HeliacalEventTruth",
            "HeliacalEventClassification",
            "HeliacalEvent",
            "FixedStarLookupPolicy",
            "HeliacalSearchPolicy",
            "FixedStarComputationPolicy",
            "StarPosition",
            "load_catalog",
            "fixed_star_at",
            "all_stars_at",
            "list_stars",
            "find_stars",
            "star_magnitude",
            "heliacal_rising_event",
            "heliacal_setting_event",
            "heliacal_rising",
            "heliacal_setting",
            "star_chart_condition_profile",
            "star_condition_network_profile",
        }
        for name in fixed_star_names:
            assert hasattr(_fixed_stars_module, name), f"moira.fixed_stars.{name} not found"
            assert getattr(moira, name) is getattr(_fixed_stars_module, name), (
                f"moira.{name} and moira.fixed_stars.{name} are different objects"
            )

    def test_unified_star_curated_names_resolve_from_modules(self):
        unified_star_names = {
            "UnifiedStarMergePolicy",
            "UnifiedStarComputationPolicy",
            "FixedStarTruth",
            "FixedStarClassification",
            "UnifiedStarRelation",
            "FixedStar",
            "star_at",
            "stars_near",
            "stars_by_magnitude",
            "list_named_stars",
            "find_named_stars",
        }
        for name in unified_star_names:
            assert hasattr(_stars_module, name), f"moira.stars.{name} not found"
            assert getattr(moira, name) is getattr(_stars_module, name), (
                f"moira.{name} and moira.stars.{name} are different objects"
            )

    def test_internal_names_remain_accessible_on_modules(self):
        for name in _FIXED_STAR_INTERNAL_NAMES:
            assert hasattr(_fixed_stars_module, name), (
                f"moira.fixed_stars.{name} disappeared; helper should remain module-internal"
            )
        for name in _UNIFIED_STAR_INTERNAL_NAMES:
            assert hasattr(_stars_module, name), (
                f"moira.stars.{name} disappeared; helper should remain module-internal"
            )

    def test_curated_count_is_39(self):
        assert len(_CURATED_PUBLIC_NAMES) == 39
