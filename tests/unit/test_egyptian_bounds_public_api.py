"""
P12 Public API Verification -- tests/unit/test_egyptian_bounds_public_api.py

Verify that the Egyptian bounds subsystem exposes its curated module surface
without leaking into the intentionally thin root `moira` package.
"""

import moira
from moira import egyptian_bounds


EXPECTED_SYMBOLS = [
    "BOUND_RULERS",
    "BoundHostNature",
    "EgyptianBoundsDoctrine",
    "EgyptianBoundsPolicy",
    "EgyptianBoundRelationKind",
    "EgyptianBoundConditionState",
    "EgyptianBoundNetworkMode",
    "EgyptianBoundSegment",
    "EgyptianBoundTruth",
    "EgyptianBoundClassification",
    "EgyptianBoundRelation",
    "EgyptianBoundRelationProfile",
    "EgyptianBoundConditionProfile",
    "EgyptianBoundsAggregateProfile",
    "EgyptianBoundsNetworkNode",
    "EgyptianBoundsNetworkEdge",
    "EgyptianBoundsNetworkProfile",
    "EGYPTIAN_BOUNDS",
    "egyptian_bound_of",
    "bound_ruler",
    "classify_egyptian_bound",
    "is_in_own_egyptian_bound",
    "relate_planet_to_egyptian_bound",
    "evaluate_egyptian_bound_relations",
    "evaluate_egyptian_bound_condition",
    "evaluate_egyptian_bounds_aggregate",
    "evaluate_egyptian_bounds_network",
]


def test_egyptian_bounds_module_exports_curated_surface() -> None:
    missing = [symbol for symbol in EXPECTED_SYMBOLS if not hasattr(egyptian_bounds, symbol)]
    assert not missing, f"Missing symbols in moira.egyptian_bounds: {missing}"
    assert "_profile_rank" not in egyptian_bounds.__all__
    assert "_validate_bounds_table" not in egyptian_bounds.__all__


def test_moira_root_surface_remains_thin() -> None:
    assert "egyptian_bounds" not in moira.__all__
    assert "EgyptianBoundTruth" not in moira.__all__
    assert not hasattr(moira, "EgyptianBoundTruth")
