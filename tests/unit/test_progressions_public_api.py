"""
tests/unit/test_progressions_public_api.py

Validates that the curated progressions backend public API is exposed from the
owning module while helper machinery remains internal.

Scope: moira.progressions exports only. No computation is performed.
"""

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
    "one_degree_longitude",
    "one_degree_right_ascension",
    "tertiary_progression",
    "tertiary_ii_progression",
    "converse_secondary_progression",
    "converse_solar_arc",
    "converse_solar_arc_right_ascension",
    "converse_naibod_longitude",
    "converse_naibod_right_ascension",
    "converse_one_degree_longitude",
    "converse_one_degree_right_ascension",
    "converse_tertiary_progression",
    "converse_tertiary_ii_progression",
    "ascendant_arc",
    "converse_ascendant_arc",
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


class TestModuleAgreement:
    def test_all_curated_names_resolve_from_moira_progressions(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_progressions_module, name), f"moira.progressions.{name} not found"

    def test_all_curated_names_in_module_all(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert name in _progressions_module.__all__, f"{name!r} missing from moira.progressions.__all__"

    def test_no_internal_names_in_module_all(self):
        for name in _INTERNAL_NAMES:
            assert name not in _progressions_module.__all__, f"{name!r} leaked into moira.progressions.__all__"

    def test_internal_names_remain_accessible_on_module(self):
        for name in _INTERNAL_NAMES:
            assert hasattr(_progressions_module, name), (
                f"moira.progressions.{name} disappeared; helper should remain module-internal"
            )

    def test_curated_count_is_47(self):
        assert len(_CURATED_PUBLIC_NAMES) == 47
