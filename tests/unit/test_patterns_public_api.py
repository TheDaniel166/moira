"""
tests/unit/test_patterns_public_api.py

Validates that the curated patterns backend public API is exposed at the moira
package root while helper machinery remains internal.

Scope: moira.__init__ patterns exports only. No computation is performed.
"""

import moira
import moira.patterns as _patterns_module


_CURATED_PUBLIC_NAMES = [
    # Enums
    "PatternSourceKind",
    "PatternSymmetryKind",
    "PatternBodyRoleKind",
    "PatternAspectRoleKind",
    "PatternConditionState",
    # Policy
    "PatternSelectionPolicy",
    "StelliumPolicy",
    "PatternComputationPolicy",
    # Truth / classification vessels
    "PatternBodyRoleTruth",
    "PatternDetectionTruth",
    "PatternBodyRoleClassification",
    "PatternClassification",
    # Relational / aggregate vessels
    "PatternAspectContribution",
    "PatternConditionProfile",
    "PatternChartConditionProfile",
    "PatternConditionNetworkNode",
    "PatternConditionNetworkEdge",
    "PatternConditionNetworkProfile",
    # Result vessels / entry points
    "AspectPattern",
    "all_pattern_contributions",
    "pattern_chart_condition_profile",
    "pattern_condition_network_profile",
    "pattern_condition_profiles",
    "pattern_contributions",
    "find_all_patterns",
    "find_t_squares",
    "find_grand_trines",
    "find_grand_crosses",
    "find_yods",
    "find_mystic_rectangles",
    "find_kites",
    "find_stelliums",
    "find_minor_grand_trines",
    "find_grand_sextiles",
    "find_thors_hammers",
    "find_boomerang_yods",
    "find_wedges",
    "find_cradles",
    "find_trapezes",
    "find_eyes",
    "find_irritation_triangles",
    "find_hard_wedges",
    "find_dominant_triangles",
    "find_grand_quintiles",
    "find_quintile_triangles",
    "find_septile_triangles",
]

_INTERNAL_NAMES = [
    "_aspect_signature",
    "_contribution_signature",
    "_build_pattern_condition_profile",
    "_derive_pattern_condition_state",
    "_validate_policy",
    "_validate_positions",
    "_validate_aspects",
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
    def test_all_curated_names_resolve_from_moira_patterns(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_patterns_module, name), f"moira.patterns.{name} not found"

    def test_curated_package_exports_are_module_objects(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert getattr(moira, name) is getattr(_patterns_module, name), (
                f"moira.{name} and moira.patterns.{name} are different objects"
            )

    def test_internal_names_remain_accessible_on_module(self):
        for name in _INTERNAL_NAMES:
            assert hasattr(_patterns_module, name), (
                f"moira.patterns.{name} disappeared; helper should remain module-internal"
            )

    def test_curated_count_is_46(self):
        assert len(_CURATED_PUBLIC_NAMES) == 46
