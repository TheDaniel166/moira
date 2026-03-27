"""
Star Catalogue Oracle — moira/stars.py

Archetype: Oracle
Purpose: Unified Star Surface for Tier 1 (Traditional) and Tier 2 (Unified) star handling.
         100% Sovereign. 100% Gaia-Primed.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from .gaia import (
    GaiaStarPosition, StellarQuality, load_gaia_catalog as _load_catalog,
    gaia_star_by_id, gaia_stars_near, gaia_stars_by_magnitude
)
from .data.star_registry import STAR_REGISTRY
from .star_types import (
    FixedStarLookupPolicy, HeliacalSearchPolicy, FixedStarComputationPolicy,
    DEFAULT_FIXED_STAR_POLICY, UnifiedStarMergePolicy, UnifiedStarComputationPolicy,
    DEFAULT_UNIFIED_STAR_POLICY, StarPositionTruth, StarPositionClassification,
    StarRelation, StarConditionState, StarConditionProfile, StarPosition,
    FixedStarTruth, FixedStarClassification, UnifiedStarRelation,
    StarChartConditionProfile, StarConditionNetworkNode, StarConditionNetworkEdge,
    StarConditionNetworkProfile, HeliacalEventTruth, HeliacalEventClassification,
    HeliacalEvent
)

__all__ = [
    # Tier 1
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

    # Tier 2
    "UnifiedStarMergePolicy", "UnifiedStarComputationPolicy",
    "FixedStarTruth", "FixedStarClassification", "UnifiedStarRelation", "FixedStar",
    "stars_near", "stars_by_magnitude", "list_named_stars", "find_named_stars",
]

# ---------------------------------------------------------------------------
# Tier 2 Result Result
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FixedStar:
    """The Tier 2 Unified Result (Re-exported from Tier 1 for convenience)."""
    name:           str
    nomenclature:   str
    longitude:      float
    latitude:       float
    magnitude:      float
    bp_rp:          float           = math.nan
    teff_k:         float           = math.nan
    parallax_mas:   float           = math.nan
    distance_ly:    float           = math.nan
    quality:        StellarQuality | None = None
    source:         str             = "gaia"
    is_topocentric: bool            = False
    computation_truth: FixedStarTruth | None = None
    classification: FixedStarClassification | None = None
    relation: UnifiedStarRelation | None = None
    condition_profile: StarConditionProfile | None = None

    def __post_init__(self) -> None:
        from .constants import SIGNS
        self.longitude = self.longitude % 360.0

    @property
    def sign(self) -> str:
        from .constants import SIGNS
        return SIGNS[int(self.longitude // 30)]

# ---------------------------------------------------------------------------
# Core Computation (Sovereign Engine)
# ---------------------------------------------------------------------------

def star_at(name: str, jd_tt: float, **kwargs) -> FixedStar:
    """The Sovereign Identity Anchor for both Tier 1 and Tier 2."""
    sid = STAR_REGISTRY.get(name)
    if sid is None:
        nl = name.lower()
        for k, v in STAR_REGISTRY.items():
            if k.lower() == nl: sid = v; break
    if sid is None: raise KeyError(f"Star {name!r} not in Sovereign Registry.")
    
    pos = gaia_star_by_id(sid, jd_tt, **kwargs)
    return FixedStar(
        name=name, nomenclature="", longitude=pos.longitude, latitude=pos.latitude,
        magnitude=pos.magnitude, parallax_mas=pos.parallax_mas, distance_ly=pos.distance_ly,
        source="gaia", is_topocentric=pos.is_topocentric
    )

def stars_near(longitude_deg: float, jd_tt: float, orb: float = 1.0, **kwargs) -> list[FixedStar]:
    nearby = gaia_stars_near(longitude_deg, jd_tt, orb=orb, **kwargs)
    return [FixedStar(name="", nomenclature="", longitude=p.longitude, latitude=p.latitude, magnitude=p.magnitude, source="gaia") for p in nearby]

def stars_by_magnitude(max_magnitude: float, jd_tt: float, **kwargs) -> list[FixedStar]:
    stars = gaia_stars_by_magnitude(max_magnitude, jd_tt, **kwargs)
    return [FixedStar(name="", nomenclature="", longitude=p.longitude, latitude=p.latitude, magnitude=p.magnitude, source="gaia") for p in stars]

# Aliases
all_stars_at = lambda jd_tt: {n: star_at(n, jd_tt) for n in STAR_REGISTRY.keys()}
list_named_stars = lambda: sorted(STAR_REGISTRY.keys())
list_stars = list_named_stars
find_named_stars = lambda frag, **kwargs: sorted([n for n in STAR_REGISTRY.keys() if frag.lower() in n.lower()])
find_stars = find_named_stars
star_magnitude = lambda name: star_at(name, 2451545.0).magnitude
load_catalog = lambda: _load_catalog()

# Stubs
heliacal_rising = lambda *a, **k: None
heliacal_setting = lambda *a, **k: None
heliacal_rising_event = lambda *a, **k: None
heliacal_setting_event = lambda *a, **k: None
star_chart_condition_profile = lambda *a, **k: None
star_condition_network_profile = lambda *a, **k: None
