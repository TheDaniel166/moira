"""
tests/unit/test_house_public_api.py

Validates that the curated houses public API is correctly exposed from the
owning module and that internal machinery remains unexposed.

Scope: moira.houses.__all__ contract.
No computation is performed; all assertions are import-resolution checks.
"""

import moira.houses as _houses_module

_CURATED_PUBLIC_NAMES = [
    # Enums / doctrine
    "HouseSystemFamily",
    "HouseSystemCuspBasis",
    "UnknownSystemPolicy",
    "PolarFallbackPolicy",
    # Classification / policy
    "HouseSystemClassification",
    "classify_house_system",
    "HousePolicy",
    # Result vessels
    "HouseCusps",
    "HousePlacement",
    "HouseBoundaryProfile",
    "HouseAngularity",
    "HouseAngularityProfile",
    "HouseSystemComparison",
    "HousePlacementComparison",
    "HouseOccupancy",
    "HouseDistributionProfile",
    # Entry points
    "calculate_houses",
    "assign_house",
    "describe_boundary",
    "describe_angularity",
    "compare_systems",
    "compare_placements",
    "distribute_points",
    "CuspSpeed",
    "HouseDynamics",
    "cusp_speeds_at",
    "houses_from_armc",
    "house_dynamics_from_armc",
    "body_house_position",
    # Rudhyar quadrant emphasis
    "Quadrant",
    "QuadrantEmphasisProfile",
    "quadrant_of",
    "quadrant_emphasis",
    # Diurnal quadrants
    "DiurnalQuadrant",
    "DiurnalPosition",
    "DiurnalEmphasisProfile",
    "diurnal_position",
    "diurnal_emphasis",
]

_INTERNAL_NAMES = [
    "_POLAR_SYSTEMS",
    "_KNOWN_SYSTEMS",
    "_CLASSIFICATIONS",
    "_UNKNOWN_CLASSIFICATION",
    "_ANGULARITY_MAP",
    "_MEMBERSHIP_CUSP_TOLERANCE",
    "_NEAR_CUSP_DEFAULT_THRESHOLD",
    "_circular_diff",
]


class TestModuleLevelResolution:
    def test_all_curated_names_resolve_from_moira_houses(self):
        for name in _CURATED_PUBLIC_NAMES:
            assert hasattr(_houses_module, name), f"moira.houses.{name} not found"

    def test_houses_all_exists(self):
        assert hasattr(_houses_module, "__all__"), "moira.houses.__all__ not defined"

    def test_houses_all_contains_exactly_curated_names(self):
        assert set(_houses_module.__all__) == set(_CURATED_PUBLIC_NAMES), (
            f"moira.houses.__all__ mismatch.\n"
            f"  Extra:   {set(_houses_module.__all__) - set(_CURATED_PUBLIC_NAMES)}\n"
            f"  Missing: {set(_CURATED_PUBLIC_NAMES) - set(_houses_module.__all__)}"
        )

    def test_no_internal_names_in_houses_all(self):
        for name in _INTERNAL_NAMES:
            assert name not in _houses_module.__all__, (
                f"{name!r} leaked into moira.houses.__all__"
            )


class TestModuleCounts:
    def test_curated_count_is_38(self):
        assert len(_CURATED_PUBLIC_NAMES) == 38

    def test_houses_all_count_is_38(self):
        assert len(_houses_module.__all__) == 38


class TestInternalsRemainInternal:
    def test_internal_names_are_accessible_on_module_but_not_in_all(self):
        for name in _INTERNAL_NAMES:
            assert hasattr(_houses_module, name), (
                f"moira.houses.{name} disappeared — internal name should still be accessible"
            )
            assert name not in _houses_module.__all__, (
                f"{name!r} leaked into moira.houses.__all__"
            )
