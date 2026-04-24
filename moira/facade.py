"""
Moira Primary Public Surface — moira/__init__.py

Archetype: Engine (primary interface)
Purpose: Exposes the complete public API of the Moira ephemeris engine through
         a single import surface. Provides the Moira facade class, the Chart
         vessel, and re-exports every stable symbol from the core pillars.

Coverage: 13200 BC → 17191 AD (JPL DE441)

Boundary declaration
--------------------
Owns:
    - Chart dataclass — complete astrological chart snapshot vessel.
    - Moira class — primary facade over all computation pillars.
    - __all__ — the canonical frozen export list.
    - __version__, __author__ — package metadata.
Delegates:
    - All computation to the respective pillar modules (planets, houses,
      aspects, eclipse, fixed_stars, etc.).
    - Kernel I/O to moira.spk_reader.

Import-time side effects:
    - Registers all pillar modules in the Python module cache (standard
      import machinery). No file I/O, no network, no threads.

External dependency assumptions:
    - A compatible JPL SPK planetary kernel must be locatable before any Moira() instance method that
      queries planetary positions is called.
    - No Qt, no database, no OS threads required at import time.

Public surface / exports:
    Moira, Chart
    (all symbols listed in __all__ below)

Export stability tiers:
    Frozen (stable):  Moira, Chart, Body, HouseSystem, Ayanamsa,
                      PlanetData, SkyPosition, CartesianPosition, NodeData, HouseCusps,
                      AspectData, EclipseData, EclipseEvent, EclipseType,
                      EclipseCalculator, and all symbols present in __all__.
    Provisional:      None currently designated.

Usage
-----
    from moira import Moira
    from datetime import datetime, timezone

    m = Moira()

    # Planetary positions
    chart = m.chart(datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc))
    for body, data in chart.planets.items():
        print(data)

    # House cusps
    houses = m.houses(
        datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        latitude=51.5,
        longitude=-0.1,
    )
    print(houses.asc, houses.mc)

    # Aspects
    print(m.aspects(chart))
"""

from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from types import MappingProxyType

from .constants import Body, HouseSystem, AspectDefinition, ASPECT_TIERS
from ._facade_astronomy import AstronomyFacadeMixin
from ._facade_classical import ClassicalFacadeMixin
from ._facade_core import CoreFacadeMixin
from ._kernel_paths import find_kernel, find_planetary_kernel, user_kernels_dir
from ._facade_kernel import KernelFacadeMixin
from ._facade_predictive import PredictiveFacadeMixin
from ._facade_relationships import RelationshipFacadeMixin
from ._facade_special import SpecialTopicsFacadeMixin
from ._facade_spatial import SpatialFacadeMixin
from .julian import (
    CalendarDateTime, DeltaTPolicy, julian_day, calendar_from_jd, calendar_datetime_from_jd,
    jd_from_datetime, datetime_from_jd, format_jd_utc, safe_datetime_from_jd,
    greenwich_mean_sidereal_time, local_sidereal_time, delta_t,
    ut_to_tt,
    delta_t_from_jd, apparent_sidereal_time_at,
)
from .delta_t_physical import DeltaTBreakdown, delta_t_breakdown
from .obliquity import mean_obliquity, true_obliquity, nutation
from .coordinates import (
    icrf_to_ecliptic, icrf_to_equatorial, ecliptic_to_equatorial,
    equatorial_to_horizontal, horizontal_to_equatorial,
    cotrans_sp,
    atmospheric_refraction, atmospheric_refraction_extended,
    equation_of_time,
    angular_distance, normalize_degrees,
)
from .spk_reader import get_reader, use_reader_override, KernelReader, SpkReader, MissingKernelError
from .planets import (
    PlanetData, SkyPosition, CartesianPosition,
    planet_at, sky_position_at, all_planets_at, sun_longitude,
    planet_relative_to, next_heliocentric_transit,
)
from .nodes import mean_node, true_node, mean_lilith, true_lilith, NodeData, next_moon_node_crossing, NodesAndApsides, nodes_and_apsides_at
from .houses import (
    HouseSystemFamily,
    HouseSystemCuspBasis,
    UnknownSystemPolicy,
    PolarFallbackPolicy,
    HouseSystemClassification,
    classify_house_system,
    HousePolicy,
    HouseCusps,
    HousePlacement,
    HouseBoundaryProfile,
    HouseAngularity,
    HouseAngularityProfile,
    HouseSystemComparison,
    HousePlacementComparison,
    HouseOccupancy,
    HouseDistributionProfile,
    calculate_houses,
    houses_from_armc,
    assign_house,
    body_house_position,
    CuspSpeed,
    HouseDynamics,
    cusp_speeds_at,
    describe_boundary,
    describe_angularity,
    compare_systems,
    compare_placements,
    distribute_points,
    Quadrant,
    QuadrantEmphasisProfile,
    quadrant_of,
    quadrant_emphasis,
    DiurnalQuadrant,
    DiurnalPosition,
    DiurnalEmphasisProfile,
    diurnal_position,
    diurnal_emphasis,
)
from .cycles import (
    SynodicPhase,
    GreatMutationElement,
    PlanetaryAgeName,
    ReturnEvent,
    ReturnSeries,
    return_series,
    half_return_series,
    lifetime_returns,
    SynodicCyclePosition,
    synodic_cycle_position,
    GreatConjunction,
    GreatConjunctionSeries,
    MutationPeriod,
    great_conjunctions,
    mutation_period_at,
    PlanetaryAgePeriod,
    PlanetaryAgeProfile,
    planetary_age_at,
    planetary_age_profile,
    FirdarPeriod,
    FirdarSubPeriod,
    FirdarSeries,
    firdar_series,
    firdar_at,
    PlanetaryDayInfo,
    PlanetaryHoursProfile,
    planetary_day_ruler,
    planetary_hours_for_day,
)
from .huber import (
    HouseZone,
    PHI,
    PHI_COMPLEMENT,
    CYCLE_YEARS,
    YEARS_PER_HOUSE,
    HouseZoneProfile,
    AgePointPosition,
    DynamicIntensity,
    PlanetIntensityScore,
    ChartIntensityProfile,
    house_zones,
    age_point,
    age_point_contacts,
    dynamic_intensity,
    intensity_at,
    chart_intensity_profile,
)
from .aspects import (
    CANONICAL_ASPECTS,
    DEFAULT_POLICY,
    TRADITIONAL_MOIETY_ORBS,
    AspectDomain,
    AspectFamily,
    AspectPatternKind,
    AspectTier,
    MotionState,
    AspectClassification,
    AspectData,
    AspectFamilyProfile,
    AspectGraph,
    AspectGraphNode,
    AspectHarmonicProfile,
    AspectPolicy,
    AspectStrength,
    DeclinationAspect,
    aspect_harmonic_profile,
    aspect_motion_state,
    aspect_strength,
    aspects_between,
    aspects_to_point,
    build_aspect_graph,
    find_aspects,
    find_declination_aspects,
    find_patterns,
)
from .sidereal import ayanamsa, tropical_to_sidereal, sidereal_to_tropical, Ayanamsa, UserDefinedAyanamsa, list_ayanamsa_systems
from .heliacal import (
    HeliacalEventKind, VisibilityModel, HeliacalPolicy,
    PlanetHeliacalEvent,
    planet_heliacal_rising, planet_heliacal_setting,
    planet_acronychal_rising, planet_acronychal_setting,
    # V5 generalized visibility surface
    VisibilityTargetKind,
    LightPollutionClass,
    LightPollutionDerivationMode,
    ObserverAid,
    ObserverVisibilityEnvironment,
    VisibilityCriterionFamily,
    VisibilityExtinctionModel,
    VisibilityTwilightModel,
    ExtinctionCoefficient,
    MoonlightPolicy,
    VisibilityPolicy,
    VisibilitySearchPolicy,
    LunarCrescentVisibilityClass,
    LunarCrescentDetails,
    VisibilityAssessment,
    GeneralVisibilityEvent,
    visibility_assessment,
    visual_limiting_magnitude,
    visibility_event,
)
from .orbits import KeplerianElements, DistanceExtremes, orbital_elements_at, distance_extremes_at
from .eclipse import (
    EclipseData,
    EclipseEvent,
    EclipseType,
    EclipseCalculator,
    SolarBodyCircumstances,
    SolarEclipseLocalCircumstances,
    LocalContactCircumstances,
    LunarEclipseAnalysis,
    LunarEclipseLocalCircumstances,
    SolarEclipsePath,
    next_solar_eclipse_at_location,
)
from .compat.nasa.eclipse import (
    NasaLunarEclipseContacts,
    NasaLunarEclipseEvent,
    next_nasa_lunar_eclipse,
    previous_nasa_lunar_eclipse,
    translate_lunar_eclipse_event,
)
from .lots import (
    LotReferenceKind,
    LotReversalKind,
    LotDependencyRole,
    LotConditionState,
    LotConditionNetworkEdgeMode,
    LotsReferenceFailureMode,
    LotsDerivedReferencePolicy,
    LotsExternalReferencePolicy,
    LotsComputationPolicy,
    LotReferenceTruth,
    ArabicPartComputationTruth,
    LotReferenceClassification,
    ArabicPartClassification,
    LotDependency,
    LotConditionProfile,
    LotChartConditionProfile,
    LotConditionNetworkNode,
    LotConditionNetworkEdge,
    LotConditionNetworkProfile,
    ArabicPart,
    calculate_lots,
    calculate_lot_dependencies,
    calculate_all_lot_dependencies,
    calculate_lot_condition_profiles,
    calculate_lot_chart_condition_profile,
    calculate_lot_condition_network_profile,
    ArabicPartsService,
    list_parts,
)
from .dignities import (
    ConditionPolarity,
    EssentialDignityKind,
    AccidentalConditionKind,
    SectStateKind,
    SolarConditionKind,
    ReceptionKind,
    ReceptionBasis,
    ReceptionMode,
    PlanetaryConditionState,
    EssentialDignityDoctrine,
    MercurySectModel,
    EssentialDignityPolicy,
    SolarConditionPolicy,
    MutualReceptionPolicy,
    SectHayzPolicy,
    AccidentalDignityPolicy,
    DignityComputationPolicy,
    PlanetaryReception,
    PlanetaryConditionProfile,
    ChartConditionProfile,
    ConditionNetworkNode,
    ConditionNetworkEdge,
    ConditionNetworkProfile,
    EssentialDignityClassification,
    AccidentalConditionClassification,
    AccidentalDignityClassification,
    SectClassification,
    SolarConditionClassification,
    ReceptionClassification,
    EssentialDignityTruth,
    AccidentalDignityCondition,
    SolarConditionTruth,
    MutualReceptionTruth,
    SectTruth,
    AccidentalDignityTruth,
    PlanetaryDignity,
    calculate_dignities,
    calculate_receptions,
    calculate_condition_profiles,
    calculate_chart_condition_profile,
    calculate_condition_network_profile,
    DignitiesService,
)
from .midpoints import (
    Midpoint, MidpointsService,
    PlanetaryPicture, MidpointWeight, MidpointCluster,
    CLASSIC_7, MODERN_3, MODERN_10, EXTENDED,
    calculate_midpoints, midpoints_to_point,
    to_dial, to_dial_90, to_dial_45, to_dial_22_5,
    dial_90_midpoints, dial_45_midpoints, dial_22_5_midpoints,
    midpoint_tree,
    antiscion, contra_antiscion,
    planetary_pictures, midpoint_weighting,
    activated_midpoints, midpoint_clusters,
)
from .harmonics import (
    HarmonicPosition, HarmonicConjunction, HarmonicPatternScore,
    HarmonicSweepEntry, HarmonicAspect, VibrationFingerprint,
    HarmonicsService,
    HARMONIC_PRESETS,
    calculate_harmonic, age_harmonic,
    harmonic_conjunctions, harmonic_pattern_score, harmonic_sweep,
    harmonic_aspects, composite_harmonic, vibrational_fingerprint,
)
from .progressions import (
    ProgressionDoctrineTruth,
    ProgressionComputationTruth,
    ProgressionDoctrineClassification,
    ProgressionComputationClassification,
    ProgressionRelation,
    ProgressionConditionProfile,
    ProgressionChartConditionProfile,
    ProgressionConditionNetworkNode,
    ProgressionConditionNetworkEdge,
    ProgressionConditionNetworkProfile,
    ProgressionTimeKeyPolicy,
    ProgressionDirectionPolicy,
    ProgressionHouseFramePolicy,
    ProgressionComputationPolicy,
    ProgressedPosition,
    ProgressedChart,
    ProgressedHouseFrame,
    secondary_progression, solar_arc, solar_arc_right_ascension,
    naibod_longitude, naibod_right_ascension,
    tertiary_progression, tertiary_ii_progression,
    converse_secondary_progression, converse_solar_arc,
    converse_solar_arc_right_ascension,
    converse_naibod_longitude, converse_naibod_right_ascension,
    converse_tertiary_progression, converse_tertiary_ii_progression,
    ascendant_arc, minor_progression, converse_minor_progression,
    daily_house_frame, daily_houses,
    duodenary_progression, converse_duodenary_progression,
    quotidian_solar_progression, converse_quotidian_solar_progression,
    quotidian_lunar_progression, converse_quotidian_lunar_progression,
    planetary_arc, converse_planetary_arc,
    progression_relation, house_frame_relation,
    progression_condition_profile, house_frame_condition_profile,
    progression_chart_condition_profile, progression_condition_network_profile,
)
from .primary_directions import (
    SpeculumEntry, PrimaryArc,
    speculum, find_primary_arcs,
    DIRECT, CONVERSE,
)
from .synastry import (
    SynastryAspectTruth, SynastryAspectContact,
    SynastryOverlayTruth,
    CompositeComputationTruth, DavisonComputationTruth,
    SynastryAspectClassification, SynastryOverlayClassification,
    CompositeClassification, DavisonClassification,
    SynastryRelation,
    SynastryConditionState, SynastryConditionProfile,
    SynastryChartConditionProfile,
    SynastryConditionNetworkNode, SynastryConditionNetworkEdge,
    SynastryConditionNetworkProfile,
    SynastryAspectPolicy, SynastryOverlayPolicy,
    SynastryCompositePolicy, SynastryDavisonPolicy,
    SynastryComputationPolicy,
    SynastryHouseOverlay, MutualHouseOverlay,
    CompositeChart, DavisonChart, DavisonInfo,
    synastry_aspects, synastry_contacts,
    house_overlay, mutual_house_overlays,
    composite_chart, composite_chart_reference_place,
    davison_chart, davison_chart_uncorrected, davison_chart_reference_place,
    davison_chart_spherical_midpoint, davison_chart_corrected,
    synastry_contact_relations, mutual_overlay_relations,
    synastry_condition_profiles, synastry_chart_condition_profile,
    synastry_condition_network_profile,
)
from .transits import (
    TransitTargetKind,
    TransitSearchKind,
    TransitWrapperKind,
    TransitRelationKind,
    TransitRelationBasis,
    TransitConditionState,
    TransitSearchPolicy,
    ReturnSearchPolicy,
    SyzygySearchPolicy,
    TransitComputationPolicy,
    LongitudeResolutionTruth,
    CrossingSearchTruth,
    TransitComputationTruth,
    IngressComputationTruth,
    LongitudeResolutionClassification,
    CrossingSearchClassification,
    TransitComputationClassification,
    IngressComputationClassification,
    TransitRelation,
    TransitConditionProfile,
    TransitChartConditionProfile,
    TransitConditionNetworkNodeKind,
    TransitConditionNetworkNode,
    TransitConditionNetworkEdge,
    TransitConditionNetworkProfile,
    TransitEvent,
    IngressEvent,
    next_transit,
    find_transits,
    find_ingresses,
    next_ingress,
    next_ingress_into,
    solar_return,
    lunar_return,
    last_new_moon,
    last_full_moon,
    prenatal_syzygy,
    planet_return,
    transit_relations,
    ingress_relations,
    transit_condition_profiles,
    ingress_condition_profiles,
    transit_chart_condition_profile,
    transit_condition_network_profile,
)
from .stations import StationEvent, find_stations, next_station, is_retrograde, retrograde_periods
from .planetary_hours import PlanetaryHour, PlanetaryHoursDay, planetary_hours
from .planetary_hours import PlanetaryHour as PlanetaryHourClassical
from .stars import (
    StarPositionTruth,
    StarPositionClassification,
    StarRelation,
    StarConditionState,
    StarConditionProfile,
    StarChartConditionProfile,
    StarConditionNetworkNode,
    StarConditionNetworkEdge,
    StarConditionNetworkProfile,
    HeliacalEventTruth,
    HeliacalEventClassification,
    HeliacalEvent,
    HeliacalBatchResult,
    FixedStarLookupPolicy,
    HeliacalSearchPolicy,
    FixedStarComputationPolicy,
    DEFAULT_FIXED_STAR_POLICY,
    StarPosition,
    star_at, all_stars_at,
    list_stars, find_stars, star_magnitude, load_catalog,
    heliacal_rising, heliacal_setting,
    heliacal_rising_event, heliacal_setting_event,
    heliacal_catalog_batch,
    star_chart_condition_profile, star_condition_network_profile,
)
from .asteroids import (
    AsteroidData, asteroid_at, all_asteroids_at,
    list_asteroids, available_in_kernel,
    load_asteroid_kernel, load_secondary_kernel, load_tertiary_kernel,
    ASTEROID_NAIF,
)
from .comets import (
    CometData, comet_at, all_comets_at, list_comets,
    load_comet_kernel, COMET_NAIF,
)
from .planets import HeliocentricData, heliocentric_planet_at, all_heliocentric_at
from .planetocentric import (
    PlanetocentricData,
    VALID_OBSERVER_BODIES,
    planetocentric_at,
    all_planetocentric_at,
)
from .ssb import (
    SSBPosition,
    SSB_BODIES,
    ssb_position_at,
    all_ssb_positions_at,
)
from .light_cone import (
    ReceivedLightPosition,
    RECEIVED_LIGHT_BODIES,
    received_light_at,
    all_received_light_at,
)
from .rise_set import RiseSetPolicy, TwilightTimes, twilight_times
from .phase import angular_diameter
from .dignities import (
    sect_light, is_day_chart, almuten_figuris, find_phasis,
    is_in_hayz, is_in_sect, SectStateKind, SectTruth, SectClassification,
)
from .sidereal import NakshatraPosition, nakshatra_of, all_nakshatras_at
from .antiscia import AntisciaAspect, find_antiscia, antiscia_to_point
from .profections import ProfectionResult, annual_profection, monthly_profection, profection_schedule
from .timelords import (
    FIRDARIA_DIURNAL, FIRDARIA_NOCTURNAL, FIRDARIA_NOCTURNAL_BONATTI,
    CHALDEAN_ORDER, MINOR_YEARS,
    FirdarSequenceKind, ZRAngularityClass,
    FirdarYearPolicy, ZRYearPolicy, TimelordComputationPolicy, DEFAULT_TIMELORD_POLICY,
    FirdarPeriod, ReleasingPeriod,
    FirdarPeriod as FirdarPeriodTL,
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
from .varga import (
    VargaPoint, calculate_varga,
    navamsa, saptamsa, dashamansa, dwadashamsa, trimshamsa,
)
from .decanates import DecanatePosition, chaldean_face, triplicity_decan, vedic_drekkana
from .astrocartography import ACGLine, acg_lines, acg_from_chart
from .geodetic import (
    GeodeticChart,
    geodetic_mc,
    geodetic_asc,
    geodetic_chart,
    geodetic_chart_from_chart,
    geodetic_equivalents,
    geodetic_equivalents_from_chart,
)
from .local_space import LocalSpacePosition, local_space_positions, local_space_from_chart
from .parans import (
    CIRCLE_TYPES,
    DEFAULT_PARAN_POLICY,
    Paran,
    ParanCrossing,
    ParanSignature,
    ParanPolicy,
    ParanStrength,
    ParanStability,
    ParanStabilitySample,
    evaluate_paran_stability,
    ParanSiteResult,
    ParanFieldSample,
    evaluate_paran_site,
    sample_paran_field,
    ParanFieldAnalysis,
    ParanFieldRegion,
    ParanFieldPeak,
    ParanThresholdCrossing,
    analyze_paran_field,
    ParanContourExtraction,
    ParanContourSegment,
    ParanContourPoint,
    extract_paran_field_contours,
    ParanContourPathSet,
    ParanContourPath,
    consolidate_paran_contours,
    ParanFieldStructure,
    ParanContourHierarchyEntry,
    ParanContourAssociation,
    analyze_paran_field_structure,
    find_parans,
    natal_parans,
)
from .longevity import HylegResult, find_hyleg, calculate_longevity
from .planetary_nodes import OrbitalNode, planetary_node, all_planetary_nodes, geometric_node
from .gauquelin import GauquelinPosition, gauquelin_sector, all_gauquelin_sectors
from .galactic import (
    GalacticPosition,
    equatorial_to_galactic, galactic_to_equatorial,
    ecliptic_to_galactic, galactic_to_ecliptic,
    galactic_position_of, all_galactic_positions,
    galactic_reference_points,
)
from .galactic_houses import (
    GalacticAngles,
    GalacticHouseCusps,
    GalacticHousePlacement,
    GalacticHouseBoundaryProfile,
    calculate_galactic_houses,
    assign_galactic_house,
    body_galactic_house_position,
    describe_galactic_boundary,
)
from .uranian import UranianBody, UranianPosition, uranian_at, all_uranian_at, list_uranian
from .patterns import (
    PatternSourceKind,
    PatternSymmetryKind,
    PatternBodyRoleKind,
    PatternAspectRoleKind,
    PatternConditionState,
    PatternSelectionPolicy,
    StelliumPolicy,
    PatternComputationPolicy,
    PatternBodyRoleTruth,
    PatternDetectionTruth,
    PatternBodyRoleClassification,
    PatternClassification,
    PatternAspectContribution,
    PatternConditionProfile,
    PatternChartConditionProfile,
    PatternConditionNetworkNode,
    PatternConditionNetworkEdge,
    PatternConditionNetworkProfile,
    AspectPattern,
    all_pattern_contributions,
    pattern_chart_condition_profile,
    pattern_condition_network_profile,
    pattern_condition_profiles,
    pattern_contributions,
    find_all_patterns,
    find_t_squares, find_grand_trines, find_grand_crosses, find_yods,
    find_mystic_rectangles, find_kites, find_stelliums, find_minor_grand_trines,
    find_grand_sextiles, find_thors_hammers, find_boomerang_yods, find_wedges,
    find_cradles, find_trapezes, find_eyes, find_irritation_triangles,
    find_hard_wedges, find_dominant_triangles,
    find_grand_quintiles, find_quintile_triangles, find_septile_triangles,
)
from .chart_shape import ChartShapeType, ChartShape, classify_chart_shape
from .phenomena import (
    PhenomenonEvent, OrbitalResonance, greatest_elongation, perihelion, aphelion,
    next_moon_phase, moon_phases_in_range,
    next_conjunction, conjunctions_in_range, resonance,
    PlanetPhenomena, planet_phenomena_at,
)
from .manazil import (
    MansionInfo, MansionPosition, MansionTradition, MANSIONS, MANSION_SPAN,
    mansion_of, mansion_of_sidereal, all_mansions_at, all_mansions_at_sidereal,
    moon_mansion, variant_nature, variant_signification,
)
from .dignities import mutual_receptions
from .occultations import (
    CloseApproach, LunarOccultation,
    close_approaches, lunar_occultation, lunar_star_occultation, all_lunar_occultations,
    OccultationPathGeometry,
)
from .sothic import (
    SothicCalendarPolicy, SothicHeliacalPolicy, SothicEpochPolicy,
    SothicPredictionPolicy, SothicComputationPolicy,
    EgyptianCalendarTruth, SothicComputationTruth,
    EgyptianCalendarClassification, SothicComputationClassification,
    SothicRelation, SothicConditionState, SothicConditionProfile,
    SothicChartConditionProfile, SothicConditionNetworkNode,
    SothicConditionNetworkEdge, SothicConditionNetworkProfile,
    EgyptianDate, SothicEntry, SothicEpoch,
    EGYPTIAN_MONTHS, EGYPTIAN_SEASONS, EPAGOMENAL_BIRTHS,
    HISTORICAL_SOTHIC_EPOCHS,
    sothic_rising, sothic_epochs, sothic_drift_rate,
    egyptian_civil_date, days_from_1_thoth,
    predicted_sothic_epoch_year, sothic_chart_condition_profile,
    sothic_condition_network_profile,
)
from .stars import (
    StellarQuality,
    UnifiedStarMergePolicy,
    UnifiedStarComputationPolicy,
    FixedStarTruth,
    FixedStarClassification,
    UnifiedStarRelation,
    FixedStar,
    star_at, stars_near, stars_by_magnitude,
    list_named_stars, find_named_stars,
)
from .variable_stars import (
    VarType, VariableStar,
    VarStarPolicy, DEFAULT_VAR_STAR_POLICY,
    StarPhaseState, star_phase_state,
    VarStarConditionProfile, star_condition_profile,
    CatalogProfile, catalog_profile,
    StarStatePair, star_state_pair,
    variable_star, list_variable_stars, variable_stars_by_type,
    phase_at, magnitude_at, next_minimum, next_maximum,
    minima_in_range, maxima_in_range,
    malefic_intensity, benefic_strength, is_in_eclipse,
    algol_phase, algol_magnitude, algol_next_minimum, algol_is_eclipsed,
    validate_variable_star_catalog,
)
from .multiple_stars import (
    MultiType, StarComponent, OrbitalElements, MultipleStarSystem,
    angular_separation_at, position_angle_at,
    is_resolvable, dominant_component, combined_magnitude, components_at,
    multiple_star, list_multiple_stars, multiple_stars_by_type,
    sirius_ab_separation_at, sirius_b_resolvable,
    castor_separation_at, alpha_cen_separation_at,
)
from .void_of_course import (
    LastAspect, VoidOfCourseWindow,
    void_of_course_window, is_void_of_course,
    next_void_of_course, void_periods_in_range,
)
from .electional import (
    ElectionalPolicy, ElectionalWindow,
    find_electional_windows, find_electional_moments,
)
from .chart import ChartContext
from typing import Callable

__all__ = [
    "Moira", "Chart", "MissingEphemerisKernelError",
    "Body", "HouseSystem", "Ayanamsa",
    "PlanetData", "SkyPosition", "CartesianPosition", "NodeData", "AspectData",
    "NodesAndApsides", "nodes_and_apsides_at",
    # Houses backend public surface
    "HouseSystemFamily", "HouseSystemCuspBasis",
    "UnknownSystemPolicy", "PolarFallbackPolicy",
    "HouseSystemClassification", "classify_house_system", "HousePolicy",
    "HouseCusps", "HousePlacement", "HouseBoundaryProfile",
    "HouseAngularity", "HouseAngularityProfile",
    "HouseSystemComparison", "HousePlacementComparison",
    "HouseOccupancy", "HouseDistributionProfile",
    "calculate_houses", "assign_house", "describe_boundary", "describe_angularity",
    "compare_systems", "compare_placements", "distribute_points",
    "Quadrant", "QuadrantEmphasisProfile", "quadrant_of", "quadrant_emphasis",
    "DiurnalQuadrant", "DiurnalPosition", "DiurnalEmphasisProfile",
    "diurnal_position", "diurnal_emphasis",
    # Cycles engine
    "SynodicPhase", "GreatMutationElement", "PlanetaryAgeName",
    "ReturnEvent", "ReturnSeries",
    "return_series", "half_return_series", "lifetime_returns",
    "SynodicCyclePosition", "synodic_cycle_position",
    "GreatConjunction", "GreatConjunctionSeries", "MutationPeriod",
    "great_conjunctions", "mutation_period_at",
    "PlanetaryAgePeriod", "PlanetaryAgeProfile",
    "planetary_age_at", "planetary_age_profile",
    "FirdarSubPeriod", "FirdarSeries",
    "firdar_series", "firdar_at",
    "PlanetaryDayInfo", "PlanetaryHoursProfile",
    "planetary_day_ruler", "planetary_hours_for_day",
    # Huber engine
    "HouseZone", "PHI", "PHI_COMPLEMENT", "CYCLE_YEARS", "YEARS_PER_HOUSE",
    "HouseZoneProfile", "AgePointPosition", "DynamicIntensity",
    "PlanetIntensityScore", "ChartIntensityProfile",
    "house_zones", "age_point", "age_point_contacts",
    "dynamic_intensity", "intensity_at", "chart_intensity_profile",
    "EclipseData", "EclipseEvent", "EclipseType", "EclipseCalculator",
    "LunarEclipseAnalysis", "LocalContactCircumstances", "LunarEclipseLocalCircumstances",
    "SolarBodyCircumstances", "SolarEclipseLocalCircumstances",
    "next_solar_eclipse_at_location",
    "NasaLunarEclipseContacts", "NasaLunarEclipseEvent",
    "next_nasa_lunar_eclipse", "previous_nasa_lunar_eclipse",
    "translate_lunar_eclipse_event",
    "CalendarDateTime", "DeltaTPolicy", "julian_day", "calendar_from_jd", "calendar_datetime_from_jd",
    "jd_from_datetime", "datetime_from_jd", "format_jd_utc", "safe_datetime_from_jd",
    "greenwich_mean_sidereal_time", "local_sidereal_time", "delta_t",
    "delta_t_from_jd", "apparent_sidereal_time_at",
    "DeltaTBreakdown", "delta_t_breakdown",
    # Obliquity & nutation
    "mean_obliquity", "true_obliquity", "nutation",
    # Coordinate utilities
    "icrf_to_ecliptic", "icrf_to_equatorial", "ecliptic_to_equatorial",
    "equatorial_to_horizontal", "horizontal_to_equatorial",
    "cotrans_sp",
    "atmospheric_refraction", "atmospheric_refraction_extended",
    "equation_of_time",
    "angular_distance", "normalize_degrees",
    "ayanamsa", "tropical_to_sidereal", "sidereal_to_tropical", "list_ayanamsa_systems",
    "AspectDefinition", "ASPECT_TIERS",
    # Aspect backend public surface
    "CANONICAL_ASPECTS", "DEFAULT_POLICY", "TRADITIONAL_MOIETY_ORBS",
    "AspectDomain", "AspectFamily", "AspectPatternKind", "AspectTier", "MotionState",
    "AspectClassification", "AspectFamilyProfile", "AspectGraph",
    "AspectGraphNode", "AspectHarmonicProfile", "AspectPolicy",
    "AspectStrength", "DeclinationAspect",
    "aspect_harmonic_profile", "aspect_motion_state", "aspect_strength",
    "aspects_between", "aspects_to_point", "build_aspect_graph",
    "find_aspects", "find_declination_aspects", "find_patterns",
    # Lots
    "LotReferenceKind",
    "LotReversalKind",
    "LotDependencyRole",
    "LotConditionState",
    "LotConditionNetworkEdgeMode",
    "LotsReferenceFailureMode",
    "LotsDerivedReferencePolicy",
    "LotsExternalReferencePolicy",
    "LotsComputationPolicy",
    "LotReferenceTruth",
    "ArabicPartComputationTruth",
    "LotReferenceClassification",
    "ArabicPartClassification",
    "LotDependency",
    "LotConditionProfile",
    "LotChartConditionProfile",
    "LotConditionNetworkNode",
    "LotConditionNetworkEdge",
    "LotConditionNetworkProfile",
    "ArabicPart",
    "calculate_lots",
    "calculate_lot_dependencies",
    "calculate_all_lot_dependencies",
    "calculate_lot_condition_profiles",
    "calculate_lot_chart_condition_profile",
    "calculate_lot_condition_network_profile",
    "ArabicPartsService",
    "list_parts",
    # Dignities
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
    "EssentialDignityPolicy",
    "SolarConditionPolicy",
    "MutualReceptionPolicy",
    "SectHayzPolicy",
    "AccidentalDignityPolicy",
    "DignityComputationPolicy",
    "PlanetaryReception",
    "PlanetaryConditionProfile",
    "ChartConditionProfile",
    "ConditionNetworkNode",
    "ConditionNetworkEdge",
    "ConditionNetworkProfile",
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
    "PlanetaryDignity",
    "calculate_dignities",
    "calculate_receptions",
    "calculate_condition_profiles",
    "calculate_chart_condition_profile",
    "calculate_condition_network_profile",
    "DignitiesService",
    # Midpoints — result types
    "Midpoint", "PlanetaryPicture", "MidpointWeight", "MidpointCluster",
    # Midpoints — service + planet sets
    "MidpointsService", "CLASSIC_7", "MODERN_3", "MODERN_10", "EXTENDED",
    # Midpoints — core computation
    "calculate_midpoints", "midpoints_to_point",
    # Midpoints — dial projections
    "to_dial", "to_dial_90", "to_dial_45", "to_dial_22_5",
    "dial_90_midpoints", "dial_45_midpoints", "dial_22_5_midpoints",
    "midpoint_tree",
    # Midpoints — antiscia
    "antiscion", "contra_antiscion",
    # Midpoints — advanced analysis
    "planetary_pictures", "midpoint_weighting",
    "activated_midpoints", "midpoint_clusters",
    # Harmonics
    "HarmonicPosition", "HarmonicsService", "calculate_harmonic", "HARMONIC_PRESETS",
    # Progressions
    "ProgressionDoctrineTruth", "ProgressionComputationTruth",
    "ProgressionDoctrineClassification", "ProgressionComputationClassification",
    "ProgressionRelation",
    "ProgressionConditionProfile", "ProgressionChartConditionProfile",
    "ProgressionConditionNetworkNode", "ProgressionConditionNetworkEdge",
    "ProgressionConditionNetworkProfile",
    "ProgressionTimeKeyPolicy", "ProgressionDirectionPolicy",
    "ProgressionHouseFramePolicy", "ProgressionComputationPolicy",
    "ProgressedPosition", "ProgressedChart", "ProgressedHouseFrame",
    "secondary_progression", "solar_arc", "solar_arc_right_ascension",
    "naibod_longitude", "naibod_right_ascension",
    "tertiary_progression", "tertiary_ii_progression",
    "converse_secondary_progression", "converse_solar_arc",
    "converse_solar_arc_right_ascension",
    "converse_naibod_longitude", "converse_naibod_right_ascension",
    "converse_tertiary_progression", "converse_tertiary_ii_progression",
    "ascendant_arc", "minor_progression", "converse_minor_progression",
    "daily_house_frame", "daily_houses",
    "duodenary_progression", "converse_duodenary_progression",
    "quotidian_solar_progression", "converse_quotidian_solar_progression",
    "quotidian_lunar_progression", "converse_quotidian_lunar_progression",
    "planetary_arc", "converse_planetary_arc",
    "progression_relation", "house_frame_relation",
    "progression_condition_profile", "house_frame_condition_profile",
    "progression_chart_condition_profile", "progression_condition_network_profile",
    # Primary directions
    "SpeculumEntry", "PrimaryArc",
    "speculum", "find_primary_arcs",
    "DIRECT", "CONVERSE",
    # Synastry / relationship charts
    "SynastryAspectTruth", "SynastryAspectContact",
    "SynastryOverlayTruth",
    "CompositeComputationTruth", "DavisonComputationTruth",
    "SynastryAspectClassification", "SynastryOverlayClassification",
    "CompositeClassification", "DavisonClassification",
    "SynastryRelation",
    "SynastryConditionState", "SynastryConditionProfile",
    "SynastryChartConditionProfile",
    "SynastryConditionNetworkNode", "SynastryConditionNetworkEdge",
    "SynastryConditionNetworkProfile",
    "SynastryAspectPolicy", "SynastryOverlayPolicy",
    "SynastryCompositePolicy", "SynastryDavisonPolicy",
    "SynastryComputationPolicy",
    "SynastryHouseOverlay", "MutualHouseOverlay",
    "CompositeChart", "DavisonChart", "DavisonInfo",
    "synastry_aspects", "synastry_contacts",
    "house_overlay", "mutual_house_overlays",
    "composite_chart", "composite_chart_reference_place",
    "davison_chart", "davison_chart_uncorrected",
    "davison_chart_reference_place", "davison_chart_spherical_midpoint",
    "davison_chart_corrected",
    "synastry_contact_relations", "mutual_overlay_relations",
    "synastry_condition_profiles", "synastry_chart_condition_profile",
    "synastry_condition_network_profile",
    # Transits
    "TransitTargetKind", "TransitSearchKind", "TransitWrapperKind",
    "TransitRelationKind", "TransitRelationBasis", "TransitConditionState",
    "TransitSearchPolicy", "ReturnSearchPolicy", "SyzygySearchPolicy", "TransitComputationPolicy",
    "LongitudeResolutionTruth", "CrossingSearchTruth",
    "TransitComputationTruth", "IngressComputationTruth",
    "LongitudeResolutionClassification", "CrossingSearchClassification",
    "TransitComputationClassification", "IngressComputationClassification",
    "TransitRelation", "TransitConditionProfile", "TransitChartConditionProfile",
    "TransitConditionNetworkNodeKind", "TransitConditionNetworkNode",
    "TransitConditionNetworkEdge", "TransitConditionNetworkProfile",
    "TransitEvent", "IngressEvent",
    "next_transit", "find_transits", "find_ingresses",
    "next_ingress", "next_ingress_into",
    "solar_return", "lunar_return",
    "last_new_moon", "last_full_moon", "prenatal_syzygy",
    "planet_return",
    "transit_relations", "ingress_relations",
    "transit_condition_profiles", "ingress_condition_profiles",
    "transit_chart_condition_profile", "transit_condition_network_profile",
    # Stations
    "StationEvent", "find_stations", "next_station", "is_retrograde", "retrograde_periods",
    # Planetary Hours
    "PlanetaryHour", "PlanetaryHourClassical", "PlanetaryHoursDay", "planetary_hours",
    # Heliocentric positions
    "HeliocentricData", "heliocentric_planet_at", "all_heliocentric_at",
    # Planetocentric positions
    "PlanetocentricData", "VALID_OBSERVER_BODIES",
    "planetocentric_at", "all_planetocentric_at",
    # Solar System Barycenter chart
    "SSBPosition", "SSB_BODIES",
    "ssb_position_at", "all_ssb_positions_at",
    # Received-Light (light-cone) chart
    "ReceivedLightPosition", "RECEIVED_LIGHT_BODIES",
    "received_light_at", "all_received_light_at",
    # Phase 2 specialist helpers
    "planet_relative_to", "next_heliocentric_transit",
    "next_moon_node_crossing",
    "true_lilith",
    "houses_from_armc", "body_house_position",
    # Phase 3 design vessels
    "UserDefinedAyanamsa",
    "HeliacalEventKind", "VisibilityModel", "HeliacalPolicy",
    "PlanetHeliacalEvent",
    "planet_heliacal_rising", "planet_heliacal_setting",
    "planet_acronychal_rising", "planet_acronychal_setting",
    # V5 generalized visibility surface
    "VisibilityTargetKind",
    "LightPollutionClass", "LightPollutionDerivationMode",
    "ObserverAid",
    "ObserverVisibilityEnvironment",
    "VisibilityCriterionFamily",
    "VisibilityExtinctionModel", "VisibilityTwilightModel", "ExtinctionCoefficient", "MoonlightPolicy",
    "VisibilityPolicy", "VisibilitySearchPolicy",
    "LunarCrescentVisibilityClass", "LunarCrescentDetails",
    "VisibilityAssessment", "GeneralVisibilityEvent",
    "visibility_assessment", "visual_limiting_magnitude", "visibility_event",
    "SolarEclipsePath",
    "OccultationPathGeometry",
    "KeplerianElements", "DistanceExtremes", "orbital_elements_at", "distance_extremes_at",
    "CuspSpeed", "HouseDynamics", "cusp_speeds_at",
    # Twilight
    "RiseSetPolicy", "TwilightTimes", "twilight_times",
    # Angular diameter
    "angular_diameter",
    # Dignities extensions
    "sect_light", "is_day_chart", "almuten_figuris", "find_phasis",
    "is_in_hayz", "is_in_sect",
    # Nakshatras
    "NakshatraPosition", "nakshatra_of", "all_nakshatras_at",
    # Antiscia
    "AntisciaAspect", "find_antiscia", "antiscia_to_point",
    # Profections
    "ProfectionResult", "annual_profection", "monthly_profection", "profection_schedule",
    # Time lords — Firdaria
    "FIRDARIA_DIURNAL", "FIRDARIA_NOCTURNAL", "FIRDARIA_NOCTURNAL_BONATTI",
    "CHALDEAN_ORDER", "MINOR_YEARS",
    "FirdarSequenceKind", "ZRAngularityClass",
    "FirdarYearPolicy", "ZRYearPolicy", "TimelordComputationPolicy", "DEFAULT_TIMELORD_POLICY",
    "FirdarPeriod", "FirdarPeriodTL", "ReleasingPeriod",
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
    # Varga (Vedic divisional charts)
    "VargaPoint", "calculate_varga",
    "navamsa", "saptamsa", "dashamansa", "dwadashamsa", "trimshamsa",
    # Decanates
    "DecanatePosition", "chaldean_face", "triplicity_decan", "vedic_drekkana",
    # Astrocartography
    "ACGLine", "acg_lines", "acg_from_chart",
    # Geodetic
    "GeodeticChart",
    "geodetic_mc", "geodetic_asc", "geodetic_chart", "geodetic_chart_from_chart",
    "geodetic_equivalents", "geodetic_equivalents_from_chart",
    # Local Space
    "LocalSpacePosition", "local_space_positions", "local_space_from_chart",
    # Parans
    "CIRCLE_TYPES", "DEFAULT_PARAN_POLICY",
    "Paran", "ParanCrossing", "ParanSignature", "ParanPolicy", "ParanStrength",
    "ParanStability", "ParanStabilitySample", "evaluate_paran_stability",
    "ParanSiteResult", "ParanFieldSample", "evaluate_paran_site", "sample_paran_field",
    "ParanFieldAnalysis", "ParanFieldRegion", "ParanFieldPeak", "ParanThresholdCrossing",
    "analyze_paran_field",
    "ParanContourExtraction", "ParanContourSegment", "ParanContourPoint",
    "extract_paran_field_contours",
    "ParanContourPathSet", "ParanContourPath", "consolidate_paran_contours",
    "ParanFieldStructure", "ParanContourHierarchyEntry", "ParanContourAssociation",
    "analyze_paran_field_structure",
    "find_parans", "natal_parans",
    # Longevity (Hyleg/Alcocoden)
    "HylegResult", "find_hyleg", "calculate_longevity",
    # Planetary nodes/apsides
    "OrbitalNode", "planetary_node", "all_planetary_nodes", "geometric_node",
    # Gauquelin sectors
    "GauquelinPosition", "gauquelin_sector", "all_gauquelin_sectors",
    # Galactic coordinate system
    "GalacticPosition",
    "equatorial_to_galactic", "galactic_to_equatorial",
    "ecliptic_to_galactic", "galactic_to_ecliptic",
    "galactic_position_of", "all_galactic_positions",
    "galactic_reference_points",
    # Galactic houses
    "GalacticAngles", "GalacticHouseCusps",
    "GalacticHousePlacement", "GalacticHouseBoundaryProfile",
    "calculate_galactic_houses", "assign_galactic_house",
    "body_galactic_house_position", "describe_galactic_boundary",
    # Uranian planets
    "UranianBody", "UranianPosition", "uranian_at", "all_uranian_at", "list_uranian",
    # Aspect patterns
    "PatternSourceKind",
    "PatternSymmetryKind",
    "PatternBodyRoleKind",
    "PatternAspectRoleKind",
    "PatternConditionState",
    "PatternSelectionPolicy",
    "StelliumPolicy",
    "PatternComputationPolicy",
    "PatternBodyRoleTruth",
    "PatternDetectionTruth",
    "PatternBodyRoleClassification",
    "PatternClassification",
    "PatternAspectContribution",
    "PatternConditionProfile",
    "PatternChartConditionProfile",
    "PatternConditionNetworkNode",
    "PatternConditionNetworkEdge",
    "PatternConditionNetworkProfile",
    "AspectPattern",
    "all_pattern_contributions",
    "pattern_chart_condition_profile",
    "pattern_condition_network_profile",
    "pattern_condition_profiles",
    "pattern_contributions",
    "find_all_patterns",
    "find_t_squares", "find_grand_trines", "find_grand_crosses", "find_yods",
    "find_mystic_rectangles", "find_kites", "find_stelliums", "find_minor_grand_trines",
    "find_grand_sextiles", "find_thors_hammers", "find_boomerang_yods", "find_wedges",
    "find_cradles", "find_trapezes", "find_eyes", "find_irritation_triangles",
    "find_hard_wedges", "find_dominant_triangles",
    "find_grand_quintiles", "find_quintile_triangles", "find_septile_triangles",
    # Chart shape (Jones temperament types)
    "ChartShapeType", "ChartShape", "classify_chart_shape",
    # Planetary phenomena
    "PhenomenonEvent", "OrbitalResonance", "greatest_elongation", "perihelion", "aphelion",
    "next_moon_phase", "moon_phases_in_range",
    "next_conjunction", "conjunctions_in_range", "resonance",
    "PlanetPhenomena", "planet_phenomena_at",
    # Arabic Lunar Mansions
    "MansionInfo", "MansionPosition", "MansionTradition", "MANSIONS", "MANSION_SPAN",
    "mansion_of", "mansion_of_sidereal", "all_mansions_at", "all_mansions_at_sidereal",
    "moon_mansion", "variant_nature", "variant_signification",
    # Mutual receptions
    "mutual_receptions",
    # Occultations
    "CloseApproach", "LunarOccultation",
    "close_approaches", "lunar_occultation", "lunar_star_occultation", "all_lunar_occultations",
    # Sothic cycle
    "SothicCalendarPolicy", "SothicHeliacalPolicy", "SothicEpochPolicy",
    "SothicPredictionPolicy", "SothicComputationPolicy",
    "EgyptianCalendarTruth", "SothicComputationTruth",
    "EgyptianCalendarClassification", "SothicComputationClassification",
    "SothicRelation", "SothicConditionState", "SothicConditionProfile",
    "SothicChartConditionProfile", "SothicConditionNetworkNode",
    "SothicConditionNetworkEdge", "SothicConditionNetworkProfile",
    "EgyptianDate", "SothicEntry", "SothicEpoch",
    "EGYPTIAN_MONTHS", "EGYPTIAN_SEASONS", "EPAGOMENAL_BIRTHS",
    "HISTORICAL_SOTHIC_EPOCHS",
    "sothic_rising", "sothic_epochs", "sothic_drift_rate",
    "egyptian_civil_date", "days_from_1_thoth", "predicted_sothic_epoch_year",
    "sothic_chart_condition_profile", "sothic_condition_network_profile",
    # Variable stars
    "VarType", "VariableStar",
    "VarStarPolicy", "DEFAULT_VAR_STAR_POLICY",
    "StarPhaseState", "star_phase_state",
    "VarStarConditionProfile", "star_condition_profile",
    "CatalogProfile", "catalog_profile",
    "StarStatePair", "star_state_pair",
    "variable_star", "list_variable_stars", "variable_stars_by_type",
    "phase_at", "magnitude_at", "next_minimum", "next_maximum",
    "minima_in_range", "maxima_in_range",
    "malefic_intensity", "benefic_strength", "is_in_eclipse",
    "algol_phase", "algol_magnitude", "algol_next_minimum", "algol_is_eclipsed",
    "validate_variable_star_catalog",
    # Fixed stars (sovereign registry)
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
    "HeliacalBatchResult",
    "FixedStarLookupPolicy",
    "HeliacalSearchPolicy",
    "FixedStarComputationPolicy",
    "DEFAULT_FIXED_STAR_POLICY",
    "StarPosition",
    "load_catalog", "star_at", "all_stars_at",
    "list_stars", "find_stars", "star_magnitude",
    "heliacal_rising_event", "heliacal_setting_event",
    "heliacal_catalog_batch",
    "heliacal_rising", "heliacal_setting",
    "star_chart_condition_profile", "star_condition_network_profile",
    # Unified star API
    "StellarQuality",
    "UnifiedStarMergePolicy",
    "UnifiedStarComputationPolicy",
    "FixedStarTruth",
    "FixedStarClassification",
    "UnifiedStarRelation",
    "FixedStar",
    "stars_near", "stars_by_magnitude",
    "list_named_stars", "find_named_stars",
    # Multiple star systems
    "MultiType", "StarComponent", "OrbitalElements", "MultipleStarSystem",
    "angular_separation_at", "position_angle_at",
    "is_resolvable", "dominant_component", "combined_magnitude", "components_at",
    "multiple_star", "list_multiple_stars", "multiple_stars_by_type",
    "sirius_ab_separation_at", "sirius_b_resolvable",
    "castor_separation_at", "alpha_cen_separation_at",
    # Void of Course Moon
    "LastAspect", "VoidOfCourseWindow",
    "void_of_course_window", "is_void_of_course",
    "next_void_of_course", "void_periods_in_range",
    # Electional search
    "ElectionalPolicy", "ElectionalWindow",
    "find_electional_windows", "find_electional_moments",
    # Comets
    "CometData", "COMET_NAIF",
    "comet_at", "all_comets_at", "list_comets", "load_comet_kernel",
]


try:
    __version__ = package_version("moira-astro")
except PackageNotFoundError:
    __version__ = "2.1.1"
__author__  = "Moira contributors"


# ---------------------------------------------------------------------------
# Chart result
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class Chart:
    """
    RITE: Vessel of the Heavens

    THEOREM: Immutable dataclass holding a complete astrological chart snapshot
             for a single Julian Day, including planetary positions, lunar nodes,
             obliquity, and ΔT.

    RITE OF PURPOSE:
        Chart is the primary cross-pillar data vessel produced by Moira.chart().
        It carries the full positional state of the sky at a given moment so
        that downstream pillars (aspects, dignities, lots, progressions, etc.)
        can operate on a single coherent snapshot without re-querying the
        ephemeris. Without Chart, every technique would need to independently
        manage JD bookkeeping and body-position retrieval.

    LAW OF OPERATION:
        Responsibilities:
            - Hold jd_ut, planets dict, nodes dict, obliquity, and delta_t.
            - Provide longitudes() and speeds() convenience accessors.
            - Expose datetime_utc and calendar_utc properties for human-readable
              time representation.
        Non-responsibilities:
            - Does not compute positions; all fields are injected by Moira.chart().
            - Does not validate physical consistency of the stored positions.
            - Does not own house cusps (HouseCusps is a separate vessel).
        Dependencies:
            - moira.julian.datetime_from_jd, calendar_datetime_from_jd
              (used by properties).
        Mutation authority:
            - Fields are frozen post-construction and mapping fields are
              exposed read-only.

    LAW OF THE DATA PATH:
        Chart is a cross-pillar vessel. It is produced by moira/__init__.py
        (Moira.chart()) and consumed by every technique pillar that operates
        on a snapshot (aspects, dignities, lots, progressions, synastry, etc.).
        It does not own any persistent state; it is always reconstructed from
        the ephemeris on demand.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.__init__.Chart",
        "risk": "critical",
        "api": {
            "inputs": ["jd_ut", "planets", "nodes", "obliquity", "delta_t"],
            "outputs": ["Chart instance", "longitudes()", "speeds()",
                        "datetime_utc", "calendar_utc"]
        },
        "state": "frozen_snapshot",
        "effects": {
            "io": [],
            "signals_emitted": [],
            "mutations": ["none"]
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": ["AttributeError if accessed before construction completes"],
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    jd_ut:      float
    planets:    dict[str, PlanetData]
    nodes:      dict[str, NodeData]
    obliquity:  float
    delta_t:    float       # seconds

    def __post_init__(self) -> None:
        object.__setattr__(self, "planets", MappingProxyType(dict(self.planets)))
        object.__setattr__(self, "nodes", MappingProxyType(dict(self.nodes)))

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_ut)

    def longitudes(self, include_nodes: bool = True) -> dict[str, float]:
        """Return a flat dict of body name → ecliptic longitude."""
        lons: dict[str, float] = {b: p.longitude for b, p in self.planets.items()}
        if include_nodes:
            lons.update({n: d.longitude for n, d in self.nodes.items()})
        return lons

    def speeds(self) -> dict[str, float]:
        return {b: p.speed for b, p in self.planets.items()}


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class MissingEphemerisKernelError(RuntimeError):
    """Raised when a kernel-dependent operation is attempted without a planetary kernel."""


class Moira(
    KernelFacadeMixin,
    CoreFacadeMixin,
    RelationshipFacadeMixin,
    PredictiveFacadeMixin,
    ClassicalFacadeMixin,
    AstronomyFacadeMixin,
    SpatialFacadeMixin,
    SpecialTopicsFacadeMixin,
):
    """Primary engine facade with deferred planetary kernel readiness."""
