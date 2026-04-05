"""
moira.classical — Traditional and classical astrology surface.

Builds on ``moira.essentials`` and adds the techniques of traditional
Western and Arabic astrology: essential and accidental dignities,
Arabic parts (lots), fixed stars, lunar mansions, midpoints,
profections, planetary hours, time-lord systems (firdaria, zodiacal
releasing, Vimshottari dasha), and Vedic divisional charts.

Usage
-----
    from moira.classical import *

    # Everything from essentials is included, plus:
    dignities = calculate_dignities(chart.longitudes(), houses.asc)
    lots = calculate_lots(chart.longitudes(), houses.asc, is_day=True)

Next step
---------
For transits, progressions, synastry, eclipses, and returns, move to
``moira.predictive``.

For the complete surface, import from ``moira.facade``.
"""

# ── Everything from essentials ───────────────────────────────────────────
from .essentials import *  # noqa: F401,F403
from .essentials import __all__ as _essentials_all

# ── Houses (full) ────────────────────────────────────────────────────────
from .houses import (
    HouseSystemFamily, HouseSystemCuspBasis,
    UnknownSystemPolicy, PolarFallbackPolicy,
    HouseSystemClassification, classify_house_system, HousePolicy,
    HousePlacement, HouseBoundaryProfile,
    HouseAngularity, HouseAngularityProfile,
    HouseSystemComparison, HousePlacementComparison,
    HouseOccupancy, HouseDistributionProfile,
    describe_boundary, describe_angularity,
    compare_systems, compare_placements, distribute_points,
    Quadrant, QuadrantEmphasisProfile, quadrant_of, quadrant_emphasis,
    DiurnalQuadrant, DiurnalPosition, DiurnalEmphasisProfile,
    diurnal_position, diurnal_emphasis,
)

# ── Aspects (full) ───────────────────────────────────────────────────────
from .aspects import (
    AspectDefinition, ASPECT_TIERS,
    CANONICAL_ASPECTS,
    AspectDomain, AspectFamily, AspectPatternKind, AspectTier, MotionState,
    AspectClassification, AspectFamilyProfile, AspectGraph,
    AspectGraphNode, AspectHarmonicProfile,
    AspectStrength, DeclinationAspect,
    aspect_harmonic_profile, aspect_motion_state, aspect_strength,
    aspects_between, aspects_to_point, build_aspect_graph,
    find_declination_aspects, find_patterns,
)

# ── Dignities (full) ─────────────────────────────────────────────────────
from .dignities import (
    ConditionPolarity,
    EssentialDignityKind, AccidentalConditionKind,
    SectStateKind, SolarConditionKind,
    ReceptionKind, ReceptionBasis, ReceptionMode,
    PlanetaryConditionState,
    EssentialDignityDoctrine, MercurySectModel,
    EssentialDignityPolicy, SolarConditionPolicy,
    MutualReceptionPolicy, SectHayzPolicy,
    AccidentalDignityPolicy, DignityComputationPolicy,
    PlanetaryReception, PlanetaryConditionProfile, ChartConditionProfile,
    ConditionNetworkNode, ConditionNetworkEdge, ConditionNetworkProfile,
    EssentialDignityClassification, AccidentalConditionClassification,
    AccidentalDignityClassification, SectClassification,
    SolarConditionClassification, ReceptionClassification,
    EssentialDignityTruth, AccidentalDignityCondition,
    SolarConditionTruth, MutualReceptionTruth,
    SectTruth, AccidentalDignityTruth,
    PlanetaryDignity,
    calculate_dignities, calculate_receptions,
    calculate_condition_profiles, calculate_chart_condition_profile,
    calculate_condition_network_profile,
    DignitiesService,
    sect_light, is_day_chart, almuten_figuris, find_phasis,
    is_in_hayz, is_in_sect,
    mutual_receptions,
)

# ── Lots (Arabic Parts) ─────────────────────────────────────────────────
from .lots import (
    LotReferenceKind, LotReversalKind, LotDependencyRole,
    LotConditionState, LotConditionNetworkEdgeMode,
    LotsReferenceFailureMode, LotsDerivedReferencePolicy,
    LotsExternalReferencePolicy, LotsComputationPolicy,
    LotReferenceTruth, ArabicPartComputationTruth,
    LotReferenceClassification, ArabicPartClassification,
    LotDependency, LotConditionProfile,
    LotChartConditionProfile,
    LotConditionNetworkNode, LotConditionNetworkEdge,
    LotConditionNetworkProfile,
    ArabicPart,
    calculate_lots,
    calculate_lot_dependencies, calculate_all_lot_dependencies,
    calculate_lot_condition_profiles, calculate_lot_chart_condition_profile,
    calculate_lot_condition_network_profile,
    ArabicPartsService, list_parts,
)

# ── Midpoints ────────────────────────────────────────────────────────────
from .midpoints import (
    Midpoint, PlanetaryPicture, MidpointWeight, MidpointCluster,
    MidpointsService, CLASSIC_7, MODERN_3, MODERN_10, EXTENDED,
    calculate_midpoints, midpoints_to_point,
    to_dial, to_dial_90, to_dial_45, to_dial_22_5,
    dial_90_midpoints, dial_45_midpoints, dial_22_5_midpoints,
    midpoint_tree,
    planetary_pictures, midpoint_weighting,
    activated_midpoints, midpoint_clusters,
)

# ── Antiscia ─────────────────────────────────────────────────────────────
from .antiscia import AntisciaAspect, find_antiscia, antiscia_to_point
from .midpoints import antiscion, contra_antiscion

# ── Fixed stars ──────────────────────────────────────────────────────────
from .stars import (
    StarPositionTruth, StarPositionClassification,
    StarRelation, StarConditionState,
    StarConditionProfile, StarChartConditionProfile,
    StarConditionNetworkNode, StarConditionNetworkEdge,
    StarConditionNetworkProfile,
    FixedStarLookupPolicy, FixedStarComputationPolicy,
    DEFAULT_FIXED_STAR_POLICY,
    StarPosition,
    load_catalog, star_at, all_stars_at,
    list_stars, find_stars, star_magnitude,
    star_chart_condition_profile, star_condition_network_profile,
    # Unified star API
    StellarQuality,
    UnifiedStarMergePolicy, UnifiedStarComputationPolicy,
    FixedStarTruth, FixedStarClassification,
    UnifiedStarRelation, FixedStar,
    stars_near, stars_by_magnitude,
    list_named_stars, find_named_stars,
)

# ── Arabic Lunar Mansions ────────────────────────────────────────────────
from .manazil import (
    MansionInfo, MansionPosition, MansionTradition,
    MANSIONS, MANSION_SPAN,
    mansion_of, mansion_of_sidereal,
    all_mansions_at, all_mansions_at_sidereal,
    moon_mansion, variant_nature, variant_signification,
)

# ── Nakshatras ───────────────────────────────────────────────────────────
from .sidereal import NakshatraPosition, nakshatra_of, all_nakshatras_at

# ── Profections ──────────────────────────────────────────────────────────
from .profections import (
    ProfectionResult, annual_profection, monthly_profection, profection_schedule,
)

# ── Planetary hours ──────────────────────────────────────────────────────
from .planetary_hours import PlanetaryHour as PlanetaryHourClassical
from .planetary_hours import PlanetaryHoursDay, planetary_hours

# ── Longevity (Hyleg / Alcocoden) ────────────────────────────────────────
from .longevity import HylegResult, find_hyleg, calculate_longevity

# ── Time lords — Firdaria ────────────────────────────────────────────────
from .timelords import (
    FIRDARIA_DIURNAL, FIRDARIA_NOCTURNAL, FIRDARIA_NOCTURNAL_BONATTI,
    CHALDEAN_ORDER, MINOR_YEARS,
    FirdarSequenceKind, ZRAngularityClass,
    FirdarYearPolicy, ZRYearPolicy,
    TimelordComputationPolicy, DEFAULT_TIMELORD_POLICY,
    FirdarPeriod as FirdarPeriodTL, ReleasingPeriod,
    FirdarMajorGroup, ZRPeriodGroup,
    FirdarConditionProfile, ZRConditionProfile,
    FirdarSequenceProfile, ZRSequenceProfile,
    FirdarActivePair, ZRLevelPair,
    firdaria, current_firdaria,
    zodiacal_releasing, current_releasing,
    group_firdaria, group_releasing,
    firdar_condition_profile, zr_condition_profile,
    firdar_sequence_profile, zr_sequence_profile,
    firdar_active_pair, zr_level_pair,
    validate_firdaria_output, validate_releasing_output,
)

# ── Vimshottari Dasha ────────────────────────────────────────────────────
from .dasha import (
    VIMSHOTTARI_YEARS, VIMSHOTTARI_SEQUENCE, VIMSHOTTARI_TOTAL,
    VIMSHOTTARI_YEAR_BASIS, VIMSHOTTARI_LEVEL_NAMES,
    DashaLordType,
    VimshottariYearPolicy, VimshottariAyanamsaPolicy,
    VimshottariComputationPolicy, DEFAULT_VIMSHOTTARI_POLICY,
    DashaPeriod, DashaActiveLine,
    DashaConditionProfile, DashaSequenceProfile,
    DashaLordPair,
    vimshottari, current_dasha, dasha_balance,
    dasha_active_line,
    dasha_condition_profile, dasha_sequence_profile, dasha_lord_pair,
    validate_vimshottari_output,
)

# ── Varga (Vedic divisional charts) ─────────────────────────────────────
from .varga import (
    VargaPoint, calculate_varga,
    navamsa, saptamsa, dashamansa, dwadashamsa, trimshamsa,
)

# ── Cycles engine ────────────────────────────────────────────────────────
from .cycles import (
    SynodicPhase, GreatMutationElement, PlanetaryAgeName,
    ReturnEvent, ReturnSeries,
    return_series, half_return_series, lifetime_returns,
    SynodicCyclePosition, synodic_cycle_position,
    GreatConjunction, GreatConjunctionSeries, MutationPeriod,
    great_conjunctions, mutation_period_at,
    PlanetaryAgePeriod, PlanetaryAgeProfile,
    planetary_age_at, planetary_age_profile,
)

# ── Huber age point ──────────────────────────────────────────────────────
from .huber import (
    HouseZone, PHI, PHI_COMPLEMENT, CYCLE_YEARS, YEARS_PER_HOUSE,
    HouseZoneProfile, AgePointPosition, DynamicIntensity,
    PlanetIntensityScore, ChartIntensityProfile,
    house_zones, age_point, age_point_contacts,
    dynamic_intensity, intensity_at, chart_intensity_profile,
)


# ── Build __all__ ────────────────────────────────────────────────────────

_CLASSICAL_OWN: list[str] = [
    # Houses full
    "HouseSystemFamily", "HouseSystemCuspBasis",
    "UnknownSystemPolicy", "PolarFallbackPolicy",
    "HouseSystemClassification", "classify_house_system", "HousePolicy",
    "HousePlacement", "HouseBoundaryProfile",
    "HouseAngularity", "HouseAngularityProfile",
    "HouseSystemComparison", "HousePlacementComparison",
    "HouseOccupancy", "HouseDistributionProfile",
    "describe_boundary", "describe_angularity",
    "compare_systems", "compare_placements", "distribute_points",
    "Quadrant", "QuadrantEmphasisProfile", "quadrant_of", "quadrant_emphasis",
    "DiurnalQuadrant", "DiurnalPosition", "DiurnalEmphasisProfile",
    "diurnal_position", "diurnal_emphasis",
    # Aspects full
    "AspectDefinition", "ASPECT_TIERS", "CANONICAL_ASPECTS",
    "AspectDomain", "AspectFamily", "AspectPatternKind", "AspectTier", "MotionState",
    "AspectClassification", "AspectFamilyProfile", "AspectGraph",
    "AspectGraphNode", "AspectHarmonicProfile",
    "AspectStrength", "DeclinationAspect",
    "aspect_harmonic_profile", "aspect_motion_state", "aspect_strength",
    "aspects_between", "aspects_to_point", "build_aspect_graph",
    "find_declination_aspects", "find_patterns",
    # Dignities
    "ConditionPolarity",
    "EssentialDignityKind", "AccidentalConditionKind",
    "SectStateKind", "SolarConditionKind",
    "ReceptionKind", "ReceptionBasis", "ReceptionMode",
    "PlanetaryConditionState",
    "EssentialDignityDoctrine", "MercurySectModel",
    "EssentialDignityPolicy", "SolarConditionPolicy",
    "MutualReceptionPolicy", "SectHayzPolicy",
    "AccidentalDignityPolicy", "DignityComputationPolicy",
    "PlanetaryReception", "PlanetaryConditionProfile", "ChartConditionProfile",
    "ConditionNetworkNode", "ConditionNetworkEdge", "ConditionNetworkProfile",
    "EssentialDignityClassification", "AccidentalConditionClassification",
    "AccidentalDignityClassification", "SectClassification",
    "SolarConditionClassification", "ReceptionClassification",
    "EssentialDignityTruth", "AccidentalDignityCondition",
    "SolarConditionTruth", "MutualReceptionTruth",
    "SectTruth", "AccidentalDignityTruth",
    "PlanetaryDignity",
    "calculate_dignities", "calculate_receptions",
    "calculate_condition_profiles", "calculate_chart_condition_profile",
    "calculate_condition_network_profile",
    "DignitiesService",
    "sect_light", "is_day_chart", "almuten_figuris", "find_phasis",
    "is_in_hayz", "is_in_sect",
    "mutual_receptions",
    # Lots
    "LotReferenceKind", "LotReversalKind", "LotDependencyRole",
    "LotConditionState", "LotConditionNetworkEdgeMode",
    "LotsReferenceFailureMode", "LotsDerivedReferencePolicy",
    "LotsExternalReferencePolicy", "LotsComputationPolicy",
    "LotReferenceTruth", "ArabicPartComputationTruth",
    "LotReferenceClassification", "ArabicPartClassification",
    "LotDependency", "LotConditionProfile", "LotChartConditionProfile",
    "LotConditionNetworkNode", "LotConditionNetworkEdge",
    "LotConditionNetworkProfile",
    "ArabicPart",
    "calculate_lots",
    "calculate_lot_dependencies", "calculate_all_lot_dependencies",
    "calculate_lot_condition_profiles", "calculate_lot_chart_condition_profile",
    "calculate_lot_condition_network_profile",
    "ArabicPartsService", "list_parts",
    # Midpoints
    "Midpoint", "PlanetaryPicture", "MidpointWeight", "MidpointCluster",
    "MidpointsService", "CLASSIC_7", "MODERN_3", "MODERN_10", "EXTENDED",
    "calculate_midpoints", "midpoints_to_point",
    "to_dial", "to_dial_90", "to_dial_45", "to_dial_22_5",
    "dial_90_midpoints", "dial_45_midpoints", "dial_22_5_midpoints",
    "midpoint_tree",
    "antiscion", "contra_antiscion",
    "planetary_pictures", "midpoint_weighting",
    "activated_midpoints", "midpoint_clusters",
    # Antiscia
    "AntisciaAspect", "find_antiscia", "antiscia_to_point",
    # Fixed stars
    "StarPositionTruth", "StarPositionClassification",
    "StarRelation", "StarConditionState",
    "StarConditionProfile", "StarChartConditionProfile",
    "StarConditionNetworkNode", "StarConditionNetworkEdge",
    "StarConditionNetworkProfile",
    "FixedStarLookupPolicy", "FixedStarComputationPolicy",
    "DEFAULT_FIXED_STAR_POLICY",
    "StarPosition",
    "load_catalog", "star_at", "all_stars_at",
    "list_stars", "find_stars", "star_magnitude",
    "star_chart_condition_profile", "star_condition_network_profile",
    "StellarQuality",
    "UnifiedStarMergePolicy", "UnifiedStarComputationPolicy",
    "FixedStarTruth", "FixedStarClassification",
    "UnifiedStarRelation", "FixedStar",
    "stars_near", "stars_by_magnitude",
    "list_named_stars", "find_named_stars",
    # Mansions
    "MansionInfo", "MansionPosition", "MansionTradition",
    "MANSIONS", "MANSION_SPAN",
    "mansion_of", "mansion_of_sidereal",
    "all_mansions_at", "all_mansions_at_sidereal",
    "moon_mansion", "variant_nature", "variant_signification",
    # Nakshatras
    "NakshatraPosition", "nakshatra_of", "all_nakshatras_at",
    # Profections
    "ProfectionResult", "annual_profection", "monthly_profection", "profection_schedule",
    # Planetary hours
    "PlanetaryHourClassical", "PlanetaryHoursDay", "planetary_hours",
    # Longevity
    "HylegResult", "find_hyleg", "calculate_longevity",
    # Timelords — Firdaria
    "FIRDARIA_DIURNAL", "FIRDARIA_NOCTURNAL", "FIRDARIA_NOCTURNAL_BONATTI",
    "CHALDEAN_ORDER", "MINOR_YEARS",
    "FirdarSequenceKind", "ZRAngularityClass",
    "FirdarYearPolicy", "ZRYearPolicy",
    "TimelordComputationPolicy", "DEFAULT_TIMELORD_POLICY",
    "FirdarPeriodTL", "ReleasingPeriod",
    "FirdarMajorGroup", "ZRPeriodGroup",
    "FirdarConditionProfile", "ZRConditionProfile",
    "FirdarSequenceProfile", "ZRSequenceProfile",
    "FirdarActivePair", "ZRLevelPair",
    "firdaria", "current_firdaria",
    "zodiacal_releasing", "current_releasing",
    "group_firdaria", "group_releasing",
    "firdar_condition_profile", "zr_condition_profile",
    "firdar_sequence_profile", "zr_sequence_profile",
    "firdar_active_pair", "zr_level_pair",
    "validate_firdaria_output", "validate_releasing_output",
    # Vimshottari Dasha
    "VIMSHOTTARI_YEARS", "VIMSHOTTARI_SEQUENCE", "VIMSHOTTARI_TOTAL",
    "VIMSHOTTARI_YEAR_BASIS", "VIMSHOTTARI_LEVEL_NAMES",
    "DashaLordType",
    "VimshottariYearPolicy", "VimshottariAyanamsaPolicy",
    "VimshottariComputationPolicy", "DEFAULT_VIMSHOTTARI_POLICY",
    "DashaPeriod", "DashaActiveLine",
    "DashaConditionProfile", "DashaSequenceProfile",
    "DashaLordPair",
    "vimshottari", "current_dasha", "dasha_balance",
    "dasha_active_line",
    "dasha_condition_profile", "dasha_sequence_profile", "dasha_lord_pair",
    "validate_vimshottari_output",
    # Varga
    "VargaPoint", "calculate_varga",
    "navamsa", "saptamsa", "dashamansa", "dwadashamsa", "trimshamsa",
    # Cycles
    "SynodicPhase", "GreatMutationElement", "PlanetaryAgeName",
    "ReturnEvent", "ReturnSeries",
    "return_series", "half_return_series", "lifetime_returns",
    "SynodicCyclePosition", "synodic_cycle_position",
    "GreatConjunction", "GreatConjunctionSeries", "MutationPeriod",
    "great_conjunctions", "mutation_period_at",
    "PlanetaryAgePeriod", "PlanetaryAgeProfile",
    "planetary_age_at", "planetary_age_profile",
    # Huber
    "HouseZone", "PHI", "PHI_COMPLEMENT", "CYCLE_YEARS", "YEARS_PER_HOUSE",
    "HouseZoneProfile", "AgePointPosition", "DynamicIntensity",
    "PlanetIntensityScore", "ChartIntensityProfile",
    "house_zones", "age_point", "age_point_contacts",
    "dynamic_intensity", "intensity_at", "chart_intensity_profile",
]

__all__ = list(_essentials_all) + _CLASSICAL_OWN
