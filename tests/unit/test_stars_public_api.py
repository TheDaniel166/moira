"""
P12 Public API Verification — tests/unit/test_stars_public_api.py

Verify that the Sovereign Star Engine exports all symbols required by the 
Moira library surface (39 symbols across Tier 1 and Tier 2).
"""

import pytest
from moira import stars

EXPECTED_SYMBOLS = [
    # Tier 1 (Legacy)
    "StarPositionTruth", "StarPositionClassification", "StarRelation",
    "StarConditionState", "StarConditionProfile", "StarChartConditionProfile",
    "StarConditionNetworkNode", "StarConditionNetworkEdge", "StarConditionNetworkProfile",
    "HeliacalEventTruth", "HeliacalEventClassification", "HeliacalEvent",
    "FixedStarLookupPolicy", "HeliacalSearchPolicy", "FixedStarComputationPolicy",
    "DEFAULT_FIXED_STAR_POLICY", "StarPosition",
    "star_at", "all_stars_at", "list_stars", "find_stars", "star_magnitude",
    "load_catalog", "heliacal_rising", "heliacal_setting",
    "heliacal_rising_event", "heliacal_setting_event",
    "star_chart_condition_profile", "star_condition_network_profile",

    # Tier 2 (Unified)
    "UnifiedStarMergePolicy", "UnifiedStarComputationPolicy",
    "FixedStarTruth", "FixedStarClassification", "UnifiedStarRelation", "FixedStar",
    "stars_near", "stars_by_magnitude", "list_named_stars", "find_named_stars",
]

def test_stars_exports_all_required_symbols():
    """Manifest check for the Star Engine surface."""
    missing = [sym for sym in EXPECTED_SYMBOLS if not hasattr(stars, sym)]
    assert not missing, f"Missing symbols in moira.stars: {missing}"

def test_moira_init_can_import_all_star_symbols():
    """Verify that moira/__init__.py itself can be imported without ImportError."""
    import moira
    assert hasattr(moira, "star_at")
    assert hasattr(moira, "FixedStar")
    assert hasattr(moira, "StarPosition")
