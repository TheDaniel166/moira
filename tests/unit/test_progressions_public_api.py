"""
tests/unit/test_progressions_public_api.py

Validates that the curated progressions backend public API is exposed at the
moira package root while helper machinery remains internal.

Scope: moira.__init__ progressions exports only. No computation is performed.
"""

import moira
import moira.progressions as _progressions_module


_CURATED_PUBLIC_NAMES = [
    # Truth / classification
    "ProgressionDoctrineTruth",
    "ProgressionComputationTruth",
    "ProgressionDoctrineClassification",
    "ProgressionComputationClassification",
    # Relation / condition / aggregate vessels
    "ProgressionRelation",
    "ProgressionConditionProfile",
    "ProgressionChartConditionProfile",
    "ProgressionConditionNetworkNode",
    "ProgressionConditionNetworkEdge",
    "ProgressionConditionNetworkProfile",
    # Policy
    "ProgressionTimeKeyPolicy",
    "ProgressionDirectionPolicy",
    "ProgressionHouseFramePolicy",
    "ProgressionComputationPolicy",
    # Result vessels
    "ProgressedPosition",
    "ProgressedChart",
    "ProgressedHouseFrame",
    # Core techniques
    "secondary_progression",
    "solar_arc",
    "solar_arc_right_ascension",
    "naibod_longitude",
    "naibod_right_ascension",
    "tertiary_progression",
    "tertiary_ii_progression",
    "converse_secondary_progression",
    "converse_solar_arc",
    "converse_solar_arc_right_ascension",
    "converse_naibod_longitude",
    "converse_naibod_right_ascension",
    "converse_tertiary_progression",
    "converse_tertiary_ii_progression",
    "ascendant_arc",
    "minor_progression",
    "converse_minor_progression",
    "daily_house_frame",
    "daily_houses",
    # Layered entry points
    "progression_relation",
    "house_frame_relation",
    "progression_condition_profile",
    "house_frame_condition_profile",
    "progression_chart_condition_profile",
    "progression_condition_network_profile",
]

_INTERNAL_NAMES = [
    "_doctrine_truth",
    "_classify_computation_truth",
    "_build_progression_relation",
    "_build_progression_condition_profile",
    "_validate_progression_relation",
    "_validate_progression_condition_profile",
    "_resolve_policy",
    "_validate_policy",
    "_age_years",
    "_default_bodies",
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
    def test_all_curated_names_resolve_from_moira_progressions(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_progressions_module, name), f"moira.progressions.{name} not found"

    def test_curated_package_exports_are_module_objects(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert getattr(moira, name) is getattr(_progressions_module, name), (
                f"moira.{name} and moira.progressions.{name} are different objects"
            )

    def test_internal_names_remain_accessible_on_module(self):
        for name in _INTERNAL_NAMES:
            assert hasattr(_progressions_module, name), (
                f"moira.progressions.{name} disappeared; helper should remain module-internal"
            )

    def test_curated_count_is_42(self):
        assert len(_CURATED_PUBLIC_NAMES) == 42
