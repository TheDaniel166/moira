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
from ._kernel_paths import find_kernel, find_planetary_kernel, user_kernels_dir
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


class Moira:
    """Primary engine facade with deferred planetary kernel readiness."""

    def __init__(self, kernel_path: str | None = None) -> None:
        self._kernel_path: str | None = kernel_path
        self._reader_obj: KernelReader | None = None
        self._kernel_init_error: FileNotFoundError | MissingKernelError | None = None

        self._try_initialize_reader()

    def _try_initialize_reader(self) -> None:
        try:
            path = self._kernel_path
            if path is None:
                from ._kernel_paths import find_planetary_kernel
                discovered = find_planetary_kernel()
                if discovered is not None:
                    path = str(discovered)
            if path is None:
                raise MissingKernelError(
                    "No planetary kernel is configured and none was found on disk."
                )
            self._reader_obj = SpkReader(Path(path))
            self._kernel_init_error = None
        except (FileNotFoundError, MissingKernelError) as exc:
            self._reader_obj = None
            self._kernel_init_error = exc

    def __getattribute__(self, name: str):
        attr = object.__getattribute__(self, name)
        if (
            callable(attr)
            and not name.startswith("_")
            and name not in {
                "is_kernel_available",
                "get_kernel_status",
                "kernel_status",
                "available_kernels",
                "configure_kernel_path",
                "download_missing_kernels",
            }
        ):
            def _wrapped(*args, **kwargs):
                reader = object.__getattribute__(self, "_reader_obj")
                if reader is None:
                    return attr(*args, **kwargs)
                with use_reader_override(reader):
                    return attr(*args, **kwargs)
            return _wrapped
        return attr

    @property
    def _reader(self) -> SpkReader:
        if self._reader_obj is None:
            self._try_initialize_reader()
        if self._reader_obj is None:
            raise MissingEphemerisKernelError(self.get_kernel_status())
        return self._reader_obj

    def is_kernel_available(self) -> bool:
        if self._reader_obj is not None:
            return True
        self._try_initialize_reader()
        return self._reader_obj is not None

    @property
    def kernel_status(self) -> str:
        return self.get_kernel_status()

    def get_kernel_status(self) -> str:
        if self._reader_obj is not None:
            return f"Kernel ready: {self._reader_obj.path}"

        if self._kernel_path:
            base = (
                f"No ephemeris kernel is loaded. Configured path: {self._kernel_path}. "
                f"User kernel directory: {user_kernels_dir()}."
            )
        else:
            base = (
                "No planetary kernel is configured. "
                f"User kernel directory: {user_kernels_dir()}."
            )
        if self._kernel_init_error is not None:
            base = f"{base} Last load error: {self._kernel_init_error}"
        return (
            f"{base} Run `moira-download-kernels` or configure a kernel path with "
            "`Moira.configure_kernel_path(path)`."
        )

    @property
    def available_kernels(self) -> list[str]:
        from ._kernel_paths import PLANETARY_KERNELS
        planetary = [name for name in PLANETARY_KERNELS if find_kernel(name).exists()]
        supplemental = [
            name for name in ["asteroids.bsp", "sb441-n373s.bsp", "centaurs.bsp", "minor_bodies.bsp"]
            if find_kernel(name).exists()
        ]
        return planetary + supplemental

    def configure_kernel_path(self, path: str) -> None:
        self._kernel_path = path
        self._try_initialize_reader()
        if self._reader_obj is None:
            raise MissingEphemerisKernelError(self.get_kernel_status())

    def download_missing_kernels(self, interactive: bool = False) -> None:
        from .download_kernels import download_missing

        download_missing(interactive=interactive)
        self._try_initialize_reader()

    # ------------------------------------------------------------------
    # Core chart
    # ------------------------------------------------------------------

    def chart(
        self,
        dt: datetime,
        bodies: list[str] | None = None,
        include_nodes: bool = True,
        observer_lat: float | None = None,
        observer_lon: float | None = None,
        observer_elev_m: float = 0.0,
    ) -> Chart:
        """
        Compute a complete set of planetary positions for a datetime.

        Parameters
        ----------
        dt              : timezone-aware datetime
        bodies          : list of Body.* constants (defaults to ALL_PLANETS)
        include_nodes   : include True Node, Mean Node, Lilith
        observer_lat    : geographic latitude for topocentric Moon (degrees)
        observer_lon    : geographic east longitude for topocentric Moon (degrees)
        observer_elev_m : observer elevation above sea level (metres)

        Returns
        -------
        Chart instance
        """
        jd = jd_from_datetime(dt)

        lst_deg: float | None = None
        if observer_lat is not None and observer_lon is not None:
            lst_deg = local_sidereal_time(jd, observer_lon)

        planets = all_planets_at(
            jd, bodies=bodies, reader=self._reader,
            observer_lat=observer_lat, observer_lon=observer_lon,
            observer_elev_m=observer_elev_m, lst_deg=lst_deg,
        )

        nodes: dict[str, NodeData] = {}
        if include_nodes:
            nodes[Body.TRUE_NODE] = true_node(jd, reader=self._reader)
            nodes[Body.MEAN_NODE] = mean_node(jd)
            nodes[Body.LILITH]      = mean_lilith(jd)
            nodes[Body.TRUE_LILITH] = true_lilith(jd, reader=self._reader)

        jd_tt = ut_to_tt(jd)
        obl = true_obliquity(jd_tt)
        dt_s = delta_t_from_jd(jd)

        return Chart(
            jd_ut=jd,
            planets=planets,
            nodes=nodes,
            obliquity=obl,
            delta_t=dt_s,
        )

    # ------------------------------------------------------------------
    # Houses
    # ------------------------------------------------------------------

    def houses(
        self,
        dt: datetime,
        latitude: float,
        longitude: float,
        system: str = HouseSystem.PLACIDUS,
        policy: HousePolicy | None = None,
    ) -> HouseCusps:
        """
        Calculate house cusps for a time and geographic location.

        Parameters
        ----------
        dt        : timezone-aware datetime
        latitude  : geographic latitude (degrees, north positive)
        longitude : geographic longitude (degrees, east positive)
        system    : HouseSystem.* constant
        """
        jd = jd_from_datetime(dt)
        return calculate_houses(jd, latitude, longitude, system, policy=policy)

    def sky_position(
        self,
        dt: datetime,
        body: str,
        latitude: float,
        longitude: float,
        elevation_m: float = 0.0,
    ) -> SkyPosition:
        """
        Calculate apparent topocentric RA/Dec and horizontal coordinates.

        This is useful for archaeoastronomy, horizon work, and astrology
        techniques that rely on declination or local sky placement.
        """
        jd = jd_from_datetime(dt)
        return sky_position_at(
            body,
            jd,
            observer_lat=latitude,
            observer_lon=longitude,
            observer_elev_m=elevation_m,
            reader=self._reader,
        )

    # ------------------------------------------------------------------
    # Aspects
    # ------------------------------------------------------------------

    def aspects(
        self,
        chart: Chart,
        orbs: dict[float, float] | None = None,
        include_minor: bool = True,
    ) -> list[AspectData]:
        """
        Find all aspects in a chart.

        Parameters
        ----------
        chart         : Chart instance
        orbs          : custom orb table (uses defaults if None)
        include_minor : include minor aspects
        """
        return find_aspects(
            chart.longitudes(),
            orbs=orbs,
            include_minor=include_minor,
            speeds=chart.speeds(),
        )

    # ------------------------------------------------------------------
    # Julian Day utilities (convenience pass-throughs)
    # ------------------------------------------------------------------

    def jd(self, year: int, month: int, day: int, hour: float = 0.0) -> float:
        """Compute Julian Day Number from a calendar date and decimal UT hour."""
        return julian_day(year, month, day, hour)

    def from_jd(self, jd: float) -> datetime:
        """Convert Julian Day to UTC datetime."""
        return datetime_from_jd(jd)

    def calendar_from_jd(self, jd: float) -> CalendarDateTime:
        """Convert Julian Day to a BCE-safe UTC calendar date-time."""
        return calendar_datetime_from_jd(jd)

    # ------------------------------------------------------------------
    # Sidereal
    # ------------------------------------------------------------------

    def sidereal_chart(
        self,
        dt: datetime,
        ayanamsa_system: str = Ayanamsa.LAHIRI,
        bodies: list[str] | None = None,
    ) -> dict[str, float]:
        """
        Return sidereal longitudes for all bodies.

        Returns
        -------
        Dict mapping body name → sidereal ecliptic longitude (degrees)
        """
        jd = jd_from_datetime(dt)
        chart = self.chart(dt, bodies=bodies)
        ayan  = ayanamsa(jd, ayanamsa_system)
        return {
            name: (p.longitude - ayan) % 360.0
            for name, p in chart.planets.items()
        }

    # ------------------------------------------------------------------
    # Eclipse
    # ------------------------------------------------------------------

    def eclipse(self, dt: datetime) -> EclipseData:
        """
        Compute eclipse geometry and classification for a given datetime.

        Parameters
        ----------
        dt : timezone-aware datetime

        Returns
        -------
        EclipseData — positions, classification, Saros/Metonic cycles,
                      Aubrey stone positions, and magnitude.
        """
        return EclipseCalculator(reader=self._reader).calculate(dt)

    # ------------------------------------------------------------------
    # Synastry / Relationship Charts
    # ------------------------------------------------------------------

    def synastry_aspects(
        self,
        chart_a: Chart,
        chart_b: Chart,
        tier: int = 2,
        orbs: dict[float, float] | None = None,
        orb_factor: float = 1.0,
        include_nodes: bool = True,
    ) -> list[AspectData]:
        """
        Find inter-aspects between two natal charts (synastry bi-wheel).

        Parameters
        ----------
        chart_a / chart_b : natal Chart instances
        tier              : aspect set (1=major, 2=all)
        orbs              : custom orb table
        orb_factor        : multiplier for default orbs
        include_nodes     : include True Node / Mean Node / Lilith
        """
        return synastry_aspects(
            chart_a, chart_b,
            tier=tier, orbs=orbs, orb_factor=orb_factor,
            include_nodes=include_nodes,
        )

    def house_overlay(
        self,
        chart_source: Chart,
        target_houses: HouseCusps,
        include_nodes: bool = True,
        source_label: str = "A",
        target_label: str = "B",
    ) -> SynastryHouseOverlay:
        """Place one chart's points into another chart's houses."""

        return house_overlay(
            chart_source,
            target_houses,
            include_nodes=include_nodes,
            source_label=source_label,
            target_label=target_label,
        )

    def mutual_house_overlays(
        self,
        chart_a: Chart,
        houses_a: HouseCusps,
        chart_b: Chart,
        houses_b: HouseCusps,
        include_nodes: bool = True,
    ) -> MutualHouseOverlay:
        """Compute house overlays in both synastry directions."""

        return mutual_house_overlays(
            chart_a,
            houses_a,
            chart_b,
            houses_b,
            include_nodes=include_nodes,
        )

    def composite_chart(
        self,
        chart_a: Chart,
        chart_b: Chart,
        houses_a: HouseCusps | None = None,
        houses_b: HouseCusps | None = None,
    ) -> CompositeChart:
        """
        Build a Composite chart (midpoints of corresponding positions).

        Parameters
        ----------
        chart_a / chart_b   : natal Chart instances
        houses_a / houses_b : optional HouseCusps for composite house cusps
        """
        return composite_chart(chart_a, chart_b, houses_a, houses_b)

    def composite_chart_reference_place(
        self,
        chart_a: Chart,
        chart_b: Chart,
        houses_a: HouseCusps,
        houses_b: HouseCusps,
        reference_latitude: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy: SynastryComputationPolicy | None = None,
    ) -> CompositeChart:
        """Build a composite chart using the reference-place house method."""

        return composite_chart_reference_place(
            chart_a,
            chart_b,
            houses_a,
            houses_b,
            reference_latitude,
            house_system=house_system,
            policy=policy,
        )

    def davison_chart(
        self,
        dt_a: datetime,
        lat_a: float,
        lon_a: float,
        dt_b: datetime,
        lat_b: float,
        lon_b: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy: SynastryComputationPolicy | None = None,
    ) -> DavisonChart:
        """
        Calculate a Davison Relationship Chart.

        Casts a real chart for the midpoint in time and space between
        two birth data sets.

        Parameters
        ----------
        dt_a / dt_b       : birth datetimes (timezone-aware recommended)
        lat_a / lat_b     : geographic latitudes (°, north positive)
        lon_a / lon_b     : geographic longitudes (°, east positive)
        house_system      : house system to use
        """
        return davison_chart(
            dt_a, lat_a, lon_a,
            dt_b, lat_b, lon_b,
            house_system=house_system,
            reader=self._reader,
            policy=policy,
        )

    def davison_chart_uncorrected(
        self,
        dt_a: datetime,
        lat_a: float,
        lon_a: float,
        dt_b: datetime,
        lat_b: float,
        lon_b: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy: SynastryComputationPolicy | None = None,
    ) -> DavisonChart:
        """Davison chart using arithmetic midpoint time and arithmetic location."""

        return davison_chart_uncorrected(
            dt_a, lat_a, lon_a,
            dt_b, lat_b, lon_b,
            house_system=house_system,
            reader=self._reader,
            policy=policy,
        )

    def davison_chart_reference_place(
        self,
        dt_a: datetime,
        dt_b: datetime,
        reference_latitude: float,
        reference_longitude: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy: SynastryComputationPolicy | None = None,
    ) -> DavisonChart:
        """Davison chart using midpoint time and an explicit reference place."""

        return davison_chart_reference_place(
            dt_a,
            dt_b,
            reference_latitude,
            reference_longitude,
            house_system=house_system,
            reader=self._reader,
            policy=policy,
        )

    def davison_chart_spherical_midpoint(
        self,
        dt_a: datetime,
        lat_a: float,
        lon_a: float,
        dt_b: datetime,
        lat_b: float,
        lon_b: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy: SynastryComputationPolicy | None = None,
    ) -> DavisonChart:
        """Davison chart using midpoint time and spherical geographic midpoint."""

        return davison_chart_spherical_midpoint(
            dt_a, lat_a, lon_a,
            dt_b, lat_b, lon_b,
            house_system=house_system,
            reader=self._reader,
            policy=policy,
        )

    def davison_chart_corrected(
        self,
        dt_a: datetime,
        lat_a: float,
        lon_a: float,
        dt_b: datetime,
        lat_b: float,
        lon_b: float,
        house_system: str = HouseSystem.PLACIDUS,
        policy: SynastryComputationPolicy | None = None,
    ) -> DavisonChart:
        """Davison chart with midpoint location and corrected midpoint time."""

        return davison_chart_corrected(
            dt_a, lat_a, lon_a,
            dt_b, lat_b, lon_b,
            house_system=house_system,
            reader=self._reader,
            policy=policy,
        )

    # ------------------------------------------------------------------
    # Primary Directions
    # ------------------------------------------------------------------

    def speculum(
        self,
        chart: Chart,
        houses: HouseCusps,
        geo_lat: float,
    ) -> list[SpeculumEntry]:
        """
        Compute the Placidus mundane speculum for a natal chart.

        Parameters
        ----------
        chart    : natal Chart instance
        houses   : natal HouseCusps (provides ARMC and obliquity)
        geo_lat  : geographic latitude in degrees

        Returns
        -------
        List of SpeculumEntry for each planet, node, and angle.
        """
        return speculum(chart, houses, geo_lat)

    def primary_directions(
        self,
        chart:            Chart,
        houses:           HouseCusps,
        geo_lat:          float,
        max_arc:          float = 90.0,
        include_converse: bool  = True,
        significators:    list[str] | None = None,
        promissors:       list[str] | None = None,
    ) -> list[PrimaryArc]:
        """
        Find all Placidus mundane primary direction arcs.

        Parameters
        ----------
        chart             : natal Chart instance
        houses            : natal HouseCusps (Placidus recommended)
        geo_lat           : geographic latitude (degrees, north positive)
        max_arc           : maximum arc in degrees (default 90 ≈ 90 years)
        include_converse  : also include converse directions
        significators     : body names to use as significators (default = all)
        promissors        : body names to use as promissors (default = all)

        Returns
        -------
        List of PrimaryArc, sorted by arc ascending.
        Call arc.years() or arc.years("ptolemy") to get the event year.
        """
        return find_primary_arcs(
            chart, houses, geo_lat,
            max_arc=max_arc,
            include_converse=include_converse,
            significators=significators,
            promissors=promissors,
        )

    # ------------------------------------------------------------------
    # Arabic Parts / Lots
    # ------------------------------------------------------------------

    def lots(self, chart: Chart, houses: HouseCusps) -> list[ArabicPart]:
        """
        Compute Arabic Parts (Hermetic Lots) for a chart.

        Parameters
        ----------
        chart  : Chart instance
        houses : HouseCusps computed for the same datetime/location
        """
        lons      = chart.longitudes(include_nodes=False)
        cusps_map = {i + 1: c for i, c in enumerate(houses.cusps)}
        day       = is_day_chart(lons.get("Sun", 0.0), houses.asc)
        return calculate_lots(lons, cusps_map, day)

    # ------------------------------------------------------------------
    # Dignities
    # ------------------------------------------------------------------

    def dignities(
        self,
        chart: Chart,
        houses: HouseCusps,
    ) -> list[PlanetaryDignity]:
        """
        Compute essential and accidental dignities for the classic seven planets.

        Parameters
        ----------
        chart  : Chart instance
        houses : HouseCusps computed for the same datetime/location
        """
        planet_dicts = [
            {
                "name": name,
                "degree": data.longitude,
                "is_retrograde": data.speed < 0,
            }
            for name, data in chart.planets.items()
        ]
        house_dicts = [
            {"number": i + 1, "degree": cusp}
            for i, cusp in enumerate(houses.cusps)
        ]
        return calculate_dignities(planet_dicts, house_dicts)

    def mutual_receptions(
        self,
        chart: Chart,
        by_exaltation: bool = False,
    ) -> list[tuple[str, str, str]]:
        """
        Find mutual receptions between planets.

        Returns a list of (planet_a, planet_b, reception_type) tuples.
        """
        return mutual_receptions(chart.longitudes(include_nodes=False),
                                 by_exaltation=by_exaltation)

    # ------------------------------------------------------------------
    # Midpoints
    # ------------------------------------------------------------------

    def midpoints(self, chart: Chart, planet_set: str = "classic") -> list[Midpoint]:
        """
        Calculate all planetary midpoints.

        Parameters
        ----------
        planet_set : 'classic', 'modern', or 'extended' (default 'classic')
        """
        return calculate_midpoints(chart.longitudes(), planet_set)

    def midpoints_to_point(
        self,
        chart: Chart,
        longitude: float,
        orb: float = 1.5,
    ) -> list[tuple[Midpoint, float]]:
        """Find midpoints that fall at (or oppose) a given longitude."""
        return midpoints_to_point(longitude, chart.longitudes(), orb=orb)

    # ------------------------------------------------------------------
    # Harmonics
    # ------------------------------------------------------------------

    def harmonic(self, chart: Chart, number: int) -> list[HarmonicPosition]:
        """
        Compute a harmonic chart.

        Parameters
        ----------
        number : harmonic number (e.g. 4 = 4th harmonic)
        """
        return calculate_harmonic(chart.longitudes(include_nodes=False), number)

    # ------------------------------------------------------------------
    # Progressions
    # ------------------------------------------------------------------

    def progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """
        Secondary Progressed chart (1 day after birth = 1 year of life).

        Parameters
        ----------
        natal_dt  : birth datetime
        target_dt : real-world date to progress to
        """
        return secondary_progression(jd_from_datetime(natal_dt), target_dt,
                                     bodies=bodies, reader=self._reader)

    def solar_arc_directions(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Solar Arc directed chart."""
        return solar_arc(jd_from_datetime(natal_dt), target_dt,
                         bodies=bodies, reader=self._reader)

    def solar_arc_directions_ra(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Solar Arc directed chart measured in right ascension."""
        return solar_arc_right_ascension(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def naibod_in_longitude(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Naibod directions in ecliptic longitude."""
        return naibod_longitude(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def naibod_in_right_ascension(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Naibod directions in right ascension."""
        return naibod_right_ascension(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def tertiary_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Tertiary Progressed chart (1 day = 1 lunar month)."""
        return tertiary_progression(jd_from_datetime(natal_dt), target_dt,
                                    bodies=bodies, reader=self._reader)

    def tertiary_ii_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Tertiary II / Klaus Wessel progression."""
        return tertiary_ii_progression(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Secondary Progressed chart."""
        return converse_secondary_progression(jd_from_datetime(natal_dt), target_dt,
                                              bodies=bodies, reader=self._reader)

    def converse_solar_arc(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Solar Arc directed chart."""
        return converse_solar_arc(jd_from_datetime(natal_dt), target_dt,
                                  bodies=bodies, reader=self._reader)

    def converse_solar_arc_ra(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Solar Arc directed chart measured in right ascension."""
        return converse_solar_arc_right_ascension(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_tertiary_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Tertiary Progressed chart."""
        return converse_tertiary_progression(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_tertiary_ii_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Tertiary II / Klaus Wessel progression."""
        return converse_tertiary_ii_progression(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def minor_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Minor Progressed chart (1 lunar month = 1 year)."""
        return minor_progression(jd_from_datetime(natal_dt), target_dt,
                                 bodies=bodies, reader=self._reader)

    def converse_naibod_in_longitude(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Naibod directions in ecliptic longitude."""
        return converse_naibod_longitude(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_naibod_in_right_ascension(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Naibod directions in right ascension."""
        return converse_naibod_right_ascension(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_minor_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Minor Progressed chart (reverse current minor mapping rule)."""
        return converse_minor_progression(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def duodenary_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Duodenary progression (Carter — 1/12 day per year)."""
        return duodenary_progression(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_duodenary_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Duodenary progression."""
        return converse_duodenary_progression(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def quotidian_solar_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Quotidian solar progression (Sepharial — day per day within secondary chart)."""
        return quotidian_solar_progression(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_quotidian_solar_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Quotidian solar progression."""
        return converse_quotidian_solar_progression(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def quotidian_lunar_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Quotidian lunar progression (French school — synodic month rate)."""
        return quotidian_lunar_progression(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_quotidian_lunar_progression(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Quotidian lunar progression."""
        return converse_quotidian_lunar_progression(
            jd_from_datetime(natal_dt),
            target_dt,
            bodies=bodies,
            reader=self._reader,
        )

    def planetary_arc_directions(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        arc_body: str,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Planetary Arc directed chart (arc of any chosen planet)."""
        return planetary_arc(
            jd_from_datetime(natal_dt),
            target_dt,
            arc_body=arc_body,
            bodies=bodies,
            reader=self._reader,
        )

    def converse_planetary_arc_directions(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        arc_body: str,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Converse Planetary Arc directed chart."""
        return converse_planetary_arc(
            jd_from_datetime(natal_dt),
            target_dt,
            arc_body=arc_body,
            bodies=bodies,
            reader=self._reader,
        )

    def ascendant_arc_directions(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        latitude: float,
        longitude: float,
        bodies: list[str] | None = None,
    ) -> ProgressedChart:
        """Ascendant Arc directed chart."""
        return ascendant_arc(
            jd_from_datetime(natal_dt),
            target_dt,
            latitude,
            longitude,
            bodies=bodies,
            reader=self._reader,
        )

    def daily_house_frame(
        self,
        natal_dt: datetime,
        target_dt: datetime,
        latitude: float,
        longitude: float,
        system: str = HouseSystem.PLACIDUS,
    ) -> HouseCusps:
        """Daily Houses progressed house frame."""
        return daily_houses(
            jd_from_datetime(natal_dt),
            target_dt,
            latitude,
            longitude,
            system=system,
        )

    # ------------------------------------------------------------------
    # Transits    # ------------------------------------------------------------------

    def transits(
        self,
        body: str,
        target_lon: float,
        jd_start: float,
        jd_end: float,
    ) -> list[TransitEvent]:
        """
        Find all transits of a body to a given longitude.

        Parameters
        ----------
        body       : Body.* constant
        target_lon : target ecliptic longitude (degrees)
        jd_start   : search start (JD UT)
        jd_end     : search end (JD UT)
        """
        return find_transits(body, target_lon, jd_start, jd_end, reader=self._reader)

    def ingresses(
        self,
        body: str,
        jd_start: float,
        jd_end: float,
    ) -> list[IngressEvent]:
        """
        Find all sign ingresses for a body in a date range.

        Parameters
        ----------
        body     : Body.* constant
        jd_start : search start (JD UT)
        jd_end   : search end (JD UT)
        """
        return find_ingresses(body, jd_start, jd_end, reader=self._reader)

    def next_ingress(
        self, body: str, jd_start: float, max_days: float | None = None
    ) -> IngressEvent | None:
        """
        Find the next sign ingress of *body* after jd_start (any sign).

        Parameters
        ----------
        body      : Body.* constant
        jd_start  : search start JD (UT)
        max_days  : search horizon (default: auto per body)

        Returns
        -------
        IngressEvent, or None if not found within max_days.
        """
        return next_ingress(body, jd_start, reader=self._reader, max_days=max_days)

    def next_ingress_into(
        self, body: str, sign: str, jd_start: float, max_days: float | None = None
    ) -> IngressEvent | None:
        """
        Find the next time *body* enters a specific zodiac *sign* after jd_start.

        Parameters
        ----------
        body      : Body.* constant (e.g. Body.JUPITER)
        sign      : zodiac sign name (e.g. "Aries", "Capricorn")
        jd_start  : search start JD (UT)
        max_days  : search horizon (default: auto per body)

        Returns
        -------
        IngressEvent, or None if not found within max_days.

        Raises
        ------
        ValueError if sign is not a valid zodiac sign name.
        """
        return next_ingress_into(body, sign, jd_start, reader=self._reader, max_days=max_days)

    def solar_return(self, natal_sun_lon: float, year: int) -> float:
        """
        Find the exact Julian Day of the Solar Return for a given year.

        Parameters
        ----------
        natal_sun_lon : natal Sun longitude (degrees)
        year          : calendar year of the return

        Returns
        -------
        JD UT of the exact Solar Return
        """
        return solar_return(natal_sun_lon, year, reader=self._reader)

    def lunar_return(self, natal_moon_lon: float, jd_start: float) -> float:
        """
        Find the next Lunar Return after jd_start.

        Returns
        -------
        JD UT of the next exact Lunar Return
        """
        return lunar_return(natal_moon_lon, jd_start, reader=self._reader)

    def planet_return(
        self,
        body: str,
        natal_lon: float,
        jd_start: float,
        direction: str = "direct",
    ) -> float:
        """
        Find the next return of any planet to its natal longitude.

        Returns
        -------
        JD UT of the next return
        """
        return planet_return(body, natal_lon, jd_start,
                             direction=direction, reader=self._reader)

    def syzygy(self, jd: float) -> tuple[float, str]:
        """
        Find the prenatal syzygy (last New or Full Moon before jd).

        Returns
        -------
        (jd_ut, kind) where kind is 'New Moon' or 'Full Moon'
        """
        return prenatal_syzygy(jd, reader=self._reader)

    # ------------------------------------------------------------------
    # Stations / Retrograde
    # ------------------------------------------------------------------

    def stations(
        self,
        body: str,
        jd_start: float,
        jd_end: float,
    ) -> list[StationEvent]:
        """Find all retrograde and direct stations for a body in a date range."""
        return find_stations(body, jd_start, jd_end, reader=self._reader)

    def retrograde_periods(
        self,
        body: str,
        jd_start: float,
        jd_end: float,
    ) -> list[tuple[float, float]]:
        """Return list of (jd_start, jd_end) retrograde intervals for a body."""
        return retrograde_periods(body, jd_start, jd_end, reader=self._reader)

    # ------------------------------------------------------------------
    # Planetary Hours
    # ------------------------------------------------------------------

    def planetary_hours(
        self,
        dt: datetime,
        latitude: float,
        longitude: float,
    ) -> PlanetaryHoursDay:
        """
        Calculate planetary hours for a date and location.

        Parameters
        ----------
        dt        : timezone-aware date or datetime
                    (calendar date is used; time-of-day is ignored)
        latitude  : geographic latitude (degrees)
        longitude : geographic east longitude (degrees)
        """
        return planetary_hours(jd_from_datetime(dt), latitude, longitude,
                               reader=self._reader)

    # ------------------------------------------------------------------
    # Heliocentric positions
    # ------------------------------------------------------------------

    def heliocentric(
        self,
        dt: datetime,
        bodies: list[str] | None = None,
    ) -> dict[str, HeliocentricData]:
        """Return heliocentric ecliptic positions for all (or specified) planets."""
        return all_heliocentric_at(jd_from_datetime(dt), bodies=bodies,
                                   reader=self._reader)

    # ------------------------------------------------------------------
    # Planetocentric positions
    # ------------------------------------------------------------------

    def planetocentric(
        self,
        observer: str,
        dt: datetime,
        bodies: list[str] | None = None,
    ) -> dict[str, PlanetocentricData]:
        """
        Return ecliptic positions of all (or specified) bodies as seen from
        the center of ``observer``.

        Parameters
        ----------
        observer : Body name of the observer planet (e.g. ``Body.MARS``).
                   Must be a member of ``VALID_OBSERVER_BODIES``.
        dt       : Datetime of the computation (timezone-aware recommended).
        bodies   : Target bodies to include.  Defaults to all
                   ``VALID_OBSERVER_BODIES`` except ``observer`` itself.
        """
        return all_planetocentric_at(
            observer, jd_from_datetime(dt), bodies=bodies, reader=self._reader
        )

    # ------------------------------------------------------------------
    # Solar System Barycenter (SSB) chart
    # ------------------------------------------------------------------

    def ssb_chart(
        self,
        dt: datetime,
        bodies: list[str] | None = None,
    ) -> dict[str, SSBPosition]:
        """
        Return ecliptic positions of bodies relative to the Solar System
        Barycenter (SSB) at the given moment.

        The SSB is the true inertial center-of-mass of the solar system.
        The Sun wanders up to ~0.010 AU from this point; all other bodies
        are measured from this same inertial origin.  Positions are expressed
        in the true-of-date ecliptic frame (precession + nutation applied),
        consistent with all other Moira position products.

        Parameters
        ----------
        dt     : Datetime of the computation (timezone-aware recommended).
        bodies : Bodies to compute.  Defaults to all ``SSB_BODIES``
                 (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn,
                 Uranus, Neptune, Pluto, Earth).
        """
        return all_ssb_positions_at(
            jd_from_datetime(dt), bodies=bodies, reader=self._reader
        )

    # ------------------------------------------------------------------
    # Received-Light (light-cone) chart
    # ------------------------------------------------------------------

    def received_light(
        self,
        dt: datetime,
        bodies: list[str] | None = None,
    ) -> dict[str, ReceivedLightPosition]:
        """
        Return received-light positions for the given bodies at ``dt``.

        Each result carries both the apparent ecliptic position (where the
        body was when it emitted the light reaching Earth at ``dt``) and
        the geometric position (where the body physically is at ``dt``),
        along with the light travel time, emission Julian Date, and angular
        displacement between the two.

        Parameters
        ----------
        dt     : Datetime of the computation (timezone-aware recommended).
        bodies : Bodies to compute.  Defaults to all ``RECEIVED_LIGHT_BODIES``
                 (Sun, Moon, and all major planets).
        """
        return all_received_light_at(
            jd_from_datetime(dt), bodies=bodies, reader=self._reader
        )

    # ------------------------------------------------------------------
    # Rise / Set / Twilight
    # ------------------------------------------------------------------

    def twilight(
        self,
        dt: datetime,
        latitude: float,
        longitude: float,
    ) -> TwilightTimes:
        """
        Calculate civil, nautical, and astronomical twilight times.

        Parameters
        ----------
        dt        : timezone-aware date or datetime
        latitude  : geographic latitude (degrees)
        longitude : geographic east longitude (degrees)
        """
        return twilight_times(jd_from_datetime(dt), latitude, longitude)

    # ------------------------------------------------------------------
    # Phase / angular diameter / apparent magnitude
    # ------------------------------------------------------------------

    def phase(self, body: str, dt: datetime) -> dict[str, float]:
        """
        Return phase metrics for a body at a given time.

        Returns
        -------
        dict with keys: phase_angle, illumination,
                        angular_diameter_arcsec, apparent_magnitude
        """
        from .phase import (phase_angle as _pa, illuminated_fraction as _ill,
                            apparent_magnitude as _mag)
        jd   = jd_from_datetime(dt)
        pa   = _pa(body, jd)
        return {
            "phase_angle":             pa,
            "illumination":            _ill(pa),
            "angular_diameter_arcsec": angular_diameter(body, jd),
            "apparent_magnitude":      _mag(body, jd),
        }

    def synodic_phase(self, body1: str, body2: str, dt: datetime) -> dict[str, float | str]:
        """
        Return synodic phase metrics for an arbitrary body pair.

        Returns
        -------
        dict with keys: phase_angle, phase_fraction, phase_state
        """
        _ = self._reader  # Ensure kernel readiness with Moira-specific error surface.
        from .phase import synodic_phase_angle as _spa, synodic_phase_state as _sps

        jd = jd_from_datetime(dt)
        ang = _spa(body1, body2, jd)
        return {
            "phase_angle": ang,
            "phase_fraction": ang / 360.0,
            "phase_state": _sps(ang),
        }

    # ------------------------------------------------------------------
    # Fixed stars
    # ------------------------------------------------------------------

    def fixed_star(self, name: str, dt: datetime) -> FixedStar:
        """
        Return the tropical ecliptic position of a fixed star, enriched with
        sovereign registry metadata when available.

        Parameters
        ----------
        name : traditional or Bayer/Flamsteed name (case-insensitive)
        dt   : datetime

        Returns
        -------
        FixedStar with longitude, latitude, magnitude, and — when the Gaia
        catalog is loaded — bp_rp, teff_k, parallax_mas, distance_ly, and
        quality (StellarQuality).  Fields unavailable from Gaia are NaN / None.
        """
        from .julian import ut_to_tt as _utt
        from .stars import star_at as _star_at
        jd = jd_from_datetime(dt)
        return _star_at(name, _utt(jd))

    def heliacal_rising(
        self,
        star_name: str,
        dt: datetime,
        latitude: float,
        longitude: float,
    ) -> float | None:
        """
        Find the JD of the heliacal rising of a fixed star.

        Returns
        -------
        JD UT of the heliacal rising, or None if not found within 400 days
        """
        from .stars import heliacal_rising as _hr
        return _hr(star_name, jd_from_datetime(dt), latitude, longitude)

    def heliacal_setting(
        self,
        star_name: str,
        dt: datetime,
        latitude: float,
        longitude: float,
    ) -> float | None:
        """
        Find the JD of the heliacal setting of a fixed star.

        Returns
        -------
        JD UT of the heliacal setting, or None if not found within 400 days
        """
        from .stars import heliacal_setting as _hs
        return _hs(star_name, jd_from_datetime(dt), latitude, longitude)

    def heliacal_rising_event(
        self,
        star_name: str,
        dt: datetime,
        latitude: float,
        longitude: float,
    ) -> HeliacalEvent:
        """
        Find the next heliacal rising of a fixed star and preserve event metadata.
        """
        from .stars import heliacal_rising_event as _hre
        return _hre(star_name, jd_from_datetime(dt), latitude, longitude)

    def heliacal_setting_event(
        self,
        star_name: str,
        dt: datetime,
        latitude: float,
        longitude: float,
    ) -> HeliacalEvent:
        """
        Find the next heliacal setting of a fixed star and preserve event metadata.
        """
        from .stars import heliacal_setting_event as _hse
        return _hse(star_name, jd_from_datetime(dt), latitude, longitude)

    # ------------------------------------------------------------------
    # Nakshatras
    # ------------------------------------------------------------------

    def nakshatras(
        self,
        chart: Chart,
        ayanamsa_system: str = Ayanamsa.LAHIRI,
    ) -> dict[str, NakshatraPosition]:
        """
        Compute nakshatra positions for all planets in a chart.

        Parameters
        ----------
        ayanamsa_system : ayanamsa for sidereal conversion (default: Lahiri)
        """
        return all_nakshatras_at(chart.longitudes(include_nodes=False),
                                 chart.jd_ut, ayanamsa_system)

    # ------------------------------------------------------------------
    # Antiscia
    # ------------------------------------------------------------------

    def antiscia(self, chart: Chart, orb: float = 1.0) -> list[AntisciaAspect]:
        """
        Find antiscia and contra-antiscia aspects in a chart.

        Parameters
        ----------
        orb : orb in degrees (default 1.0°)
        """
        return find_antiscia(chart.longitudes(), orb=orb)

    # ------------------------------------------------------------------
    # Profections
    # ------------------------------------------------------------------

    def profection(
        self,
        natal_asc: float,
        natal_dt: datetime,
        current_dt: datetime,
        natal_positions: dict[str, float] | None = None,
    ) -> ProfectionResult:
        """
        Compute the current annual profection.

        Parameters
        ----------
        natal_asc       : natal Ascendant longitude (degrees)
        natal_dt        : birth datetime
        current_dt      : date to evaluate
        natal_positions : optional natal longitudes for activated-planet detection
        """
        return profection_schedule(
            natal_asc,
            jd_from_datetime(natal_dt),
            jd_from_datetime(current_dt),
            natal_positions,
        )

    # ------------------------------------------------------------------
    # Hellenistic Time Lords
    # ------------------------------------------------------------------

    def firdaria(
        self,
        natal_dt: datetime,
        natal_chart: Chart,
        natal_houses: HouseCusps | None = None,
    ) -> list[FirdarPeriod]:
        """
        Compute the Firdaria (Persian time lords) from birth.

        Parameters
        ----------
        natal_dt     : birth datetime
        natal_chart  : natal Chart instance
        natal_houses : optional HouseCusps to determine sect precisely
        """
        sun = natal_chart.planets.get("Sun")
        asc = natal_houses.asc if natal_houses is not None else 0.0
        day = is_day_chart(sun.longitude if sun else 0.0, asc)
        return firdaria(jd_from_datetime(natal_dt), day)

    def zodiacal_releasing(
        self,
        lot_longitude: float,
        natal_dt: datetime,
        levels: int = 4,
    ) -> list[ReleasingPeriod]:
        """
        Generate Zodiacal Releasing periods from a Lot.

        Parameters
        ----------
        lot_longitude : natal longitude of the Lot (Fortune, Spirit, etc.)
        natal_dt      : birth datetime
        levels        : number of levels to generate (1–4, default 4)
        """
        return zodiacal_releasing(lot_longitude, jd_from_datetime(natal_dt),
                                  levels=levels)

    # ------------------------------------------------------------------
    # Vimshottari Dasha
    # ------------------------------------------------------------------

    def vimshottari_dasha(
        self,
        natal_chart: Chart,
        natal_dt: datetime,
        levels: int = 2,
        ayanamsa_system: str = Ayanamsa.LAHIRI,
    ) -> list[DashaPeriod]:
        """
        Compute the Vimshottari Dasha sequence from birth.

        Parameters
        ----------
        natal_chart     : natal Chart (Moon longitude is read from it)
        natal_dt        : birth datetime
        levels          : 1=Mahadasha only, 2=+Antardasha, 3=+Pratyantardasha
        ayanamsa_system : ayanamsa for Moon's nakshatra (default: Lahiri)
        """
        moon = natal_chart.planets.get("Moon")
        if moon is None:
            raise ValueError("Moon not found in natal chart — include it when calling chart()")
        return vimshottari(moon.longitude, jd_from_datetime(natal_dt),
                           levels=levels, ayanamsa_system=ayanamsa_system)

    # ------------------------------------------------------------------
    # Astrocartography
    # ------------------------------------------------------------------

    def astrocartography(
        self,
        chart: Chart,
        observer_lat: float = 0.0,
        observer_lon: float = 0.0,
        bodies: list[str] | None = None,
        lat_step: float = 2.0,
    ) -> list[ACGLine]:
        """
        Compute Astro*Carto*Graphy lines for a chart.

        Parameters
        ----------
        chart        : natal Chart instance
        observer_lat : birth location latitude (degrees)
        observer_lon : birth location east longitude (degrees)
        bodies       : bodies to include (default: all chart planets)
        lat_step     : latitude grid step for line tracing (default 2°)
        """
        from .julian import apparent_sidereal_time as _gast, ut_to_tt as _utt
        from .obliquity import nutation as _nut, true_obliquity as _tob

        if bodies is None:
            bodies = list(chart.planets.keys())

        jd_tt    = _utt(chart.jd_ut)
        dpsi, _  = _nut(jd_tt)
        gmst_deg = _gast(chart.jd_ut, dpsi, _tob(jd_tt))

        planet_ra_dec: dict[str, tuple[float, float]] = {}
        for body in bodies:
            sky = sky_position_at(body, chart.jd_ut,
                                  observer_lat=observer_lat,
                                  observer_lon=observer_lon,
                                  reader=self._reader)
            planet_ra_dec[body] = (sky.right_ascension, sky.declination)

        return acg_lines(planet_ra_dec, gmst_deg, lat_step=lat_step)

    # ------------------------------------------------------------------
    # Geodetic Astrology
    # ------------------------------------------------------------------

    def geodetic(
        self,
        chart: Chart,
        zodiac: str = "tropical",
        ayanamsa_system: str | None = None,
    ) -> GeodeticChart:
        """
        Compute the Geodetic chart for the chart's birth location.

        The Geodetic MC is the zodiac degree native to the birth longitude;
        the Geodetic Ascendant is derived from the MC and birth latitude.
        No birth time is used in the derivation — only the location.
        Obliquity is taken at the natal epoch (``chart.jd_tt``).

        Parameters
        ----------
        chart            : natal Chart instance (location is taken from it)
        zodiac           : "tropical" (default) or "sidereal"
        ayanamsa_system  : required when ``zodiac="sidereal"``; a system name
                           from ``moira.sidereal.Ayanamsa``
        """
        return geodetic_chart_from_chart(
            chart,
            zodiac=zodiac,
            ayanamsa_system=ayanamsa_system,
        )

    def geodetic_planet_equivalents(
        self,
        chart: Chart,
        bodies: list[str] | None = None,
        zodiac: str = "tropical",
        ayanamsa_system: str | None = None,
    ) -> dict[str, float]:
        """
        Geographic longitudes where each natal planet is the Geodetic MC.

        For each body, returns the geographic longitude at which that
        planet's ecliptic position falls exactly on the Geodetic MC.

        Parameters
        ----------
        chart            : natal Chart instance
        bodies           : bodies to include (default: all chart planets)
        zodiac           : "tropical" (default) or "sidereal"
        ayanamsa_system  : required when ``zodiac="sidereal"``
        """
        return geodetic_equivalents_from_chart(
            chart,
            bodies=bodies,
            zodiac=zodiac,
            ayanamsa_system=ayanamsa_system,
        )

    # ------------------------------------------------------------------
    # Local Space
    # ------------------------------------------------------------------

    def local_space(
        self,
        chart: Chart,
        latitude: float,
        longitude: float,
        bodies: list[str] | None = None,
    ) -> list[LocalSpacePosition]:
        """
        Compute a Local Space chart (azimuth and altitude for each planet).

        Parameters
        ----------
        chart     : natal Chart instance
        latitude  : observer geographic latitude (degrees)
        longitude : observer geographic east longitude (degrees)
        bodies    : bodies to include (default: all chart planets)
        """
        from .julian import local_sidereal_time as _lst, ut_to_tt as _utt
        from .obliquity import nutation as _nut, true_obliquity as _tob

        if bodies is None:
            bodies = list(chart.planets.keys())

        jd_tt    = _utt(chart.jd_ut)
        dpsi, _  = _nut(jd_tt)
        lst_deg  = _lst(chart.jd_ut, longitude, dpsi, _tob(jd_tt))

        planet_ra_dec: dict[str, tuple[float, float]] = {}
        for body in bodies:
            sky = sky_position_at(body, chart.jd_ut,
                                  observer_lat=latitude,
                                  observer_lon=longitude,
                                  reader=self._reader)
            planet_ra_dec[body] = (sky.right_ascension, sky.declination)

        return local_space_positions(planet_ra_dec, latitude, lst_deg)

    # ------------------------------------------------------------------
    # Parans
    # ------------------------------------------------------------------

    def parans(
        self,
        natal_dt: datetime,
        latitude: float,
        longitude: float,
        bodies: list[str] | None = None,
        orb_minutes: float = 4.0,
    ) -> list[Paran]:
        """
        Find natal parans — simultaneous horizon crossings on the birth day.

        Parameters
        ----------
        natal_dt    : birth datetime
        latitude    : birth location latitude (degrees)
        longitude   : birth location east longitude (degrees)
        bodies      : bodies to check (default: all classical planets)
        orb_minutes : time orb in minutes (default 4.0)
        """
        from .constants import Body as _B
        if bodies is None:
            bodies = list(_B.ALL_PLANETS)
        return natal_parans(bodies, jd_from_datetime(natal_dt),
                            latitude, longitude, orb_minutes=orb_minutes)

    # ------------------------------------------------------------------
    # Longevity (Hyleg / Alcocoden)
    # ------------------------------------------------------------------

    def longevity(self, chart: Chart, houses: HouseCusps) -> HylegResult:
        """
        Calculate the Hyleg and Alcocoden for traditional longevity analysis.

        Parameters
        ----------
        chart  : natal Chart instance
        houses : natal HouseCusps
        """
        lons = chart.longitudes(include_nodes=False)
        day  = is_day_chart(lons.get("Sun", 0.0), houses.asc)
        return calculate_longevity(lons, houses.cusps, day)

    # ------------------------------------------------------------------
    # Planetary Nodes / Apsides
    # ------------------------------------------------------------------

    def planetary_nodes(self, dt: datetime) -> dict[str, OrbitalNode]:
        """
        Return heliocentric orbital nodes and apsides for all planets.

        Returns
        -------
        Dict of body name → OrbitalNode (ascending node, descending node,
        perihelion, aphelion longitudes)
        """
        return all_planetary_nodes(jd_from_datetime(dt))

    # ------------------------------------------------------------------
    # Gauquelin Sectors
    # ------------------------------------------------------------------

    def gauquelin_sectors(
        self,
        chart: Chart,
        latitude: float,
        longitude: float,
        bodies: list[str] | None = None,
    ) -> list[GauquelinPosition]:
        """
        Compute Gauquelin sectors for all planets.

        Parameters
        ----------
        chart     : natal Chart instance
        latitude  : observer geographic latitude (degrees)
        longitude : observer geographic east longitude (degrees)
        bodies    : bodies to include (default: all chart planets)
        """
        from .julian import local_sidereal_time as _lst, ut_to_tt as _utt
        from .obliquity import nutation as _nut, true_obliquity as _tob

        if bodies is None:
            bodies = list(chart.planets.keys())

        jd_tt    = _utt(chart.jd_ut)
        dpsi, _  = _nut(jd_tt)
        lst_deg  = _lst(chart.jd_ut, longitude, dpsi, _tob(jd_tt))

        planet_ra_dec: dict[str, tuple[float, float]] = {}
        for body in bodies:
            sky = sky_position_at(body, chart.jd_ut,
                                  observer_lat=latitude,
                                  observer_lon=longitude,
                                  reader=self._reader)
            planet_ra_dec[body] = (sky.right_ascension, sky.declination)

        return all_gauquelin_sectors(planet_ra_dec, latitude, lst_deg)

    # ------------------------------------------------------------------
    # Galactic Coordinate System
    # ------------------------------------------------------------------

    def galactic_chart(
        self,
        chart: Chart,
        bodies: list[str] | None = None,
    ) -> list[GalacticPosition]:
        """
        Compute galactic (ℓ, b) coordinates for all planets in a chart.

        Parameters
        ----------
        chart  : natal Chart instance
        bodies : bodies to include (default: all chart planets + nodes)

        Returns
        -------
        List of GalacticPosition, one per body.
        """
        obliquity = chart.obliquity
        if bodies is None:
            planet_data = {
                name: (p.longitude, p.latitude)
                for name, p in chart.planets.items()
            }
            planet_data.update({
                name: (n.longitude, 0.0)
                for name, n in chart.nodes.items()
            })
        else:
            planet_data = {}
            for name in bodies:
                if name in chart.planets:
                    p = chart.planets[name]
                    planet_data[name] = (p.longitude, p.latitude)
                elif name in chart.nodes:
                    planet_data[name] = (chart.nodes[name].longitude, 0.0)
        from .julian import ut_to_tt as _utt
        jd_tt = _utt(chart.jd_ut)
        return all_galactic_positions(planet_data, obliquity, jd_tt)

    def galactic_angles(self, chart: Chart) -> dict[str, tuple[float, float]]:
        """
        Return ecliptic positions of the five principal galactic reference
        points at the obliquity of the given chart.

        Returns
        -------
        dict: point name → (ecliptic_longitude, ecliptic_latitude) in degrees.

        Keys: "Galactic Center", "Galactic Anti-Center",
              "North Galactic Pole", "South Galactic Pole",
              "Super-Galactic Center"
        """
        from .julian import ut_to_tt as _utt
        jd_tt = _utt(chart.jd_ut)
        return galactic_reference_points(chart.obliquity, jd_tt)

    def galactic_houses(
        self,
        dt: datetime,
        latitude: float,
        longitude: float,
    ) -> GalacticHouseCusps:
        """
        Compute Galactic Porphyry house cusps for a time and observer location.

        Galactic house membership is defined natively on ``cusps_gal``.
        ``cusps_ecl`` are provided for interoperability and display.
        """
        jd = jd_from_datetime(dt)
        return calculate_galactic_houses(jd, latitude, longitude)

    # ------------------------------------------------------------------
    # Uranian Planets (Hamburg School)
    # ------------------------------------------------------------------

    def uranian(self, dt: datetime) -> dict[str, UranianPosition]:
        """Compute positions for all Uranian/Transneptunian hypothetical planets."""
        return all_uranian_at(jd_from_datetime(dt))

    # ------------------------------------------------------------------
    # Aspect Patterns
    # ------------------------------------------------------------------

    def patterns(
        self,
        chart: Chart,
        orb_factor: float = 1.0,
    ) -> list[AspectPattern]:
        """
        Find all aspect patterns in a chart.

        Parameters
        ----------
        orb_factor : multiplier for default pattern orbs (default 1.0)

        Returns
        -------
        List of all found patterns (T-Squares, Grand Trines, Yods, etc.)
        """
        positions = chart.longitudes()
        asps = find_aspects(positions, speeds=chart.speeds())
        return find_all_patterns(positions, aspects=asps, orb_factor=orb_factor)

    # ------------------------------------------------------------------
    # Planetary Phenomena
    # ------------------------------------------------------------------

    def phenomena(
        self,
        body: str,
        jd_start: float,
        jd_end: float,
    ) -> list[PhenomenonEvent]:
        """
        Find greatest elongations, perihelion, and aphelion for a body.

        Parameters
        ----------
        body     : Body.* constant (Mercury/Venus for elongations)
        jd_start : search start (JD UT)
        jd_end   : search end (JD UT)
        """
        from .constants import Body as _B
        events: list[PhenomenonEvent] = []
        if body in (_B.MERCURY, _B.VENUS):
            east = greatest_elongation(body, jd_start, direction="east", reader=self._reader, max_days=jd_end - jd_start)
            west = greatest_elongation(body, jd_start, direction="west", reader=self._reader, max_days=jd_end - jd_start)
            for event in (east, west):
                if event is not None and jd_start <= event.jd_ut <= jd_end:
                    events.append(event)
        peri = perihelion(body, jd_start, reader=self._reader, max_days=jd_end - jd_start)
        aphe = aphelion(body, jd_start, reader=self._reader, max_days=jd_end - jd_start)
        for event in (peri, aphe):
            if event is not None and jd_start <= event.jd_ut <= jd_end:
                events.append(event)
        events.sort(key=lambda e: e.jd_ut)
        return events

    def moon_phases(self, jd_start: float, jd_end: float) -> list[PhenomenonEvent]:
        """Return all 8 Moon phases in a date range."""
        return moon_phases_in_range(jd_start, jd_end, reader=self._reader)

    def next_conjunction(
        self, body1: str, body2: str, jd_start: float, max_days: float = 1200.0
    ) -> PhenomenonEvent | None:
        """Find the next conjunction between any two bodies."""
        return next_conjunction(body1, body2, jd_start, reader=self._reader, max_days=max_days)

    def conjunctions(
        self, body1: str, body2: str, jd_start: float, jd_end: float
    ) -> list[PhenomenonEvent]:
        """Find all conjunctions between two bodies in a date range."""
        return conjunctions_in_range(body1, body2, jd_start, jd_end, reader=self._reader)

    def resonance(self, body1: str, body2: str) -> OrbitalResonance:
        """Compute the orbital resonance and synodic cycle of two bodies."""
        return resonance(body1, body2)

    # ------------------------------------------------------------------
    # Arabic Lunar Mansions (Manazil al-Qamar)
    # ------------------------------------------------------------------

    def lunar_mansions(self, chart: Chart) -> dict[str, MansionPosition]:
        """Compute the Arabic lunar mansion for each planet in a chart."""
        return all_mansions_at(chart.longitudes(include_nodes=False))

    # ------------------------------------------------------------------
    # Occultations
    # ------------------------------------------------------------------

    def occultations(
        self,
        jd_start: float,
        jd_end: float,
        targets: list[str] | None = None,
    ) -> list[LunarOccultation]:
        """
        Find all lunar occultations of planets in a date range.

        Parameters
        ----------
        jd_start : search start (JD UT)
        jd_end   : search end (JD UT)
        targets  : planet bodies to check (default: Mercury through Neptune)
        """
        return all_lunar_occultations(jd_start, jd_end,
                                      planets=targets, reader=self._reader)

    def close_approaches(
        self,
        body1: str,
        body2: str,
        jd_start: float,
        jd_end: float,
        max_sep_deg: float = 1.0,
    ) -> list[CloseApproach]:
        """
        Find all close approaches between two bodies.

        Parameters
        ----------
        body1 / body2 : Body.* constants
        jd_start      : search start (JD UT)
        jd_end        : search end (JD UT)
        max_sep_deg   : maximum separation to report (degrees, default 1.0°)
        """
        return close_approaches(body1, body2, jd_start, jd_end,
                                max_sep_deg=max_sep_deg, reader=self._reader)

    # ------------------------------------------------------------------
    # Sothic cycle
    # ------------------------------------------------------------------

    def sothic_cycle(
        self,
        latitude: float,
        longitude: float,
        year_start: int,
        year_end: int,
        arcus_visionis: float = 10.0,
    ) -> list[SothicEntry]:
        """
        Compute the heliacal rising of Sirius for each year in the given range.

        Returns a year-by-year record of when Sirius first appeared on the
        eastern horizon before sunrise, and where that moment fell in the
        Egyptian civil calendar relative to the 139 AD Sothic epoch.

        Parameters
        ----------
        latitude / longitude : observer location (degrees)
        year_start / year_end : astronomical years (negative = BC)
        arcus_visionis : solar depression required for Sirius to be visible
                         (degrees).  Default 10° is correct for Sirius
                         magnitude −1.46 in a clear ancient sky.

        Returns
        -------
        list[SothicEntry], one per year where the heliacal rising was found.
        Years where Sirius never rises at the given latitude are omitted.

        Example
        -------
        >>> m = Moira()
        >>> # The Nile flood calendar at Memphis
        >>> cycle = m.sothic_cycle(29.8, 31.3, -3000, 200)
        >>> for e in cycle[:5]:
        ...     print(e)
        """
        return sothic_rising(latitude, longitude, year_start, year_end,
                              arcus_visionis=arcus_visionis)

    def sothic_epoch_finder(
        self,
        latitude: float,
        longitude: float,
        year_start: int,
        year_end: int,
        tolerance_days: float = 1.0,
    ) -> list[SothicEpoch]:
        """
        Find Sothic epochs in a year range — years where Sirius's heliacal
        rising returns to within *tolerance_days* of 1 Thoth.

        Parameters
        ----------
        latitude / longitude : observer location
        year_start / year_end : search range (astronomical years)
        tolerance_days : closeness threshold (default ±1 day)

        Returns
        -------
        list[SothicEpoch]
        """
        return sothic_epochs(latitude, longitude, year_start, year_end,
                              tolerance_days=tolerance_days)

    def egyptian_date(
        self,
        dt: datetime,
        epoch_jd: float | None = None,
    ) -> EgyptianDate:
        """
        Convert a datetime to an Egyptian civil calendar date.

        The Egyptian civil year has 365 days (12 months × 30 days + 5
        epagomenal days).  The calendar is anchored to the 139 AD Sothic epoch
        (Censorinus) by default.

        Parameters
        ----------
        dt       : datetime to convert
        epoch_jd : reference JD for 1 Thoth (default: 139 AD Sothic epoch)

        Returns
        -------
        EgyptianDate with month name, day, season, and epagomenal deity
        """
        from .sothic import _SOTHIC_EPOCH_139_JD
        jd = jd_from_datetime(dt)
        return egyptian_civil_date(jd, epoch_jd or _SOTHIC_EPOCH_139_JD)

    # ------------------------------------------------------------------
    # Variable stars
    # ------------------------------------------------------------------

    def variable_star_phase(self, name: str, dt: datetime) -> float:
        """
        Return the phase (0–1) of a variable star at a given time.

        Phase 0 = primary minimum for eclipsing binaries;
        phase 0 = maximum light for pulsating/Mira types.

        Parameters
        ----------
        name : star name, e.g. 'Algol', 'Mira', 'Delta Cephei'
        dt   : datetime
        """
        return phase_at(variable_star(name), jd_from_datetime(dt))

    def variable_star_magnitude(self, name: str, dt: datetime) -> float:
        """
        Estimate the V magnitude of a variable star at a given time.

        Parameters
        ----------
        name : star name or designation (case-insensitive)
        dt   : datetime
        """
        return magnitude_at(variable_star(name), jd_from_datetime(dt))

    def variable_star_next_minimum(self, name: str, dt: datetime) -> float | None:
        """
        Return the JD of the next primary minimum after dt.

        Returns None for irregular stars with no defined period.
        """
        return next_minimum(variable_star(name), jd_from_datetime(dt))

    def variable_star_next_maximum(self, name: str, dt: datetime) -> float | None:
        """
        Return the JD of the next maximum after dt.

        Returns None for irregular stars with no defined period.
        """
        return next_maximum(variable_star(name), jd_from_datetime(dt))

    def variable_star_minima(
        self,
        name: str,
        jd_start: float,
        jd_end: float,
    ) -> list[float]:
        """Return all primary minima JDs for a variable star in [jd_start, jd_end]."""
        return minima_in_range(variable_star(name), jd_start, jd_end)

    def variable_star_maxima(
        self,
        name: str,
        jd_start: float,
        jd_end: float,
    ) -> list[float]:
        """Return all maxima JDs for a variable star in [jd_start, jd_end]."""
        return maxima_in_range(variable_star(name), jd_start, jd_end)

    def variable_star_quality(self, name: str, dt: datetime) -> dict[str, float]:
        """
        Return the astrological quality scores for a variable star at dt.

        Returns
        -------
        dict with keys:
          phase             — current phase (0–1)
          magnitude         — estimated V magnitude
          malefic_intensity — 0.0 (inert) → 1.0 (peak malefic power)
          benefic_strength  — 0.0 (depleted) → 1.0 (peak benefic power)
          is_eclipsed       — True if an eclipsing binary is currently in eclipse
        """
        star = variable_star(name)
        jd   = jd_from_datetime(dt)
        return {
            "phase":             phase_at(star, jd),
            "magnitude":         magnitude_at(star, jd),
            "malefic_intensity": malefic_intensity(star, jd),
            "benefic_strength":  benefic_strength(star, jd),
            "is_eclipsed":       is_in_eclipse(star, jd),
        }

    # ------------------------------------------------------------------
    # Multiple star systems
    # ------------------------------------------------------------------

    def multiple_star_separation(
        self, name: str, dt: datetime, aperture_mm: float = 100.0
    ) -> dict:
        """
        Return the orbital state of a multiple star system at a given time.

        Parameters
        ----------
        name        : system name or designation (e.g. "Sirius", "alp CMa")
        dt          : datetime (UTC)
        aperture_mm : telescope aperture for resolvability check (default 100 mm)

        Returns
        -------
        dict with keys:
          separation_arcsec    — float: current A–B angular separation
          position_angle_deg   — float: position angle (N through E)
          is_resolvable        — bool:  splittable with aperture_mm telescope
          dominant_component   — str:   label of brightest component
          combined_magnitude   — float: total V magnitude of the system
          system_type          — str:   MultiType constant
        """
        system = multiple_star(name)
        jd     = jd_from_datetime(dt)
        return {
            "separation_arcsec":  angular_separation_at(system, jd),
            "position_angle_deg": position_angle_at(system, jd),
            "is_resolvable":      is_resolvable(system, jd, aperture_mm),
            "dominant_component": dominant_component(system).label,
            "combined_magnitude": combined_magnitude(system),
            "system_type":        system.system_type,
        }

    def multiple_star_components(self, name: str, dt: datetime) -> dict:
        """
        Return the full component snapshot of a multiple star system at dt.

        Parameters
        ----------
        name : system name or designation
        dt   : datetime (UTC)

        Returns
        -------
        dict from components_at() — separation, PA, resolvability flags,
        dominant component label, and per-component magnitude/spectral data.
        """
        return components_at(multiple_star(name), jd_from_datetime(dt))

    # ------------------------------------------------------------------
    # Void of Course Moon
    # ------------------------------------------------------------------

    def moon_void_of_course(
        self, dt: datetime, modern: bool = False
    ) -> VoidOfCourseWindow:
        """
        Return the Void of Course window for the Moon's current sign at dt.

        Parameters
        ----------
        dt     : datetime (UTC)
        modern : if True, include Uranus, Neptune, Pluto as aspecting bodies

        Returns
        -------
        VoidOfCourseWindow describing when the VOC starts/ends within the
        Moon's current sign, the last applying aspect, and duration in hours.
        """
        return void_of_course_window(jd_from_datetime(dt), reader=self._reader, modern=modern)

    def is_moon_void_of_course(
        self, dt: datetime, modern: bool = False
    ) -> bool:
        """
        Return True if the Moon is Void of Course at the given datetime.

        Parameters
        ----------
        dt     : datetime (UTC)
        modern : if True, include Uranus, Neptune, Pluto as aspecting bodies
        """
        return is_void_of_course(jd_from_datetime(dt), reader=self._reader, modern=modern)

    # ------------------------------------------------------------------
    # Electional search
    # ------------------------------------------------------------------

    def electional_windows(
        self,
        dt_start: datetime,
        dt_end: datetime,
        latitude: float,
        longitude: float,
        predicate: Callable[[ChartContext], bool],
        policy: ElectionalPolicy | None = None,
    ) -> list[ElectionalWindow]:
        """
        Find time windows where the caller-supplied predicate is satisfied.

        Scans from dt_start to dt_end at the step defined in policy (default
        one hour), constructs a ChartContext at each step, and evaluates the
        predicate. Consecutive qualifying moments are merged into windows.

        The predicate receives a fully populated ChartContext and must return
        True when the chart satisfies the election criteria. It must be pure
        (no side effects, deterministic).

        Parameters
        ----------
        dt_start  : search range start (UTC datetime)
        dt_end    : search range end   (UTC datetime)
        latitude  : election location latitude, degrees [-90, 90]
        longitude : election location longitude, degrees [-180, 180]
        predicate : ChartContext → bool
        policy    : ElectionalPolicy (defaults to 1-hour step, Placidus)

        Returns
        -------
        list[ElectionalWindow] in chronological order.

        Example
        -------
        Find hours when Jupiter is in the 1st house and Moon is not VOC::

            from moira import Moira
            from moira.electional import ElectionalPolicy
            from moira.constants import Body
            from moira.void_of_course import is_void_of_course
            from datetime import datetime, timezone

            m = Moira()

            def good_election(chart):
                jup = chart.planets.get(Body.JUPITER)
                if jup is None or chart.houses is None:
                    return False
                from moira.houses import assign_house
                placement = assign_house(jup.longitude, chart.houses)
                if placement.house != 1:
                    return False
                return not is_void_of_course(chart.jd_ut)

            windows = m.electional_windows(
                datetime(2026, 6, 1, tzinfo=timezone.utc),
                datetime(2026, 6, 30, tzinfo=timezone.utc),
                latitude=51.5,
                longitude=-0.1,
                predicate=good_election,
            )
        """
        from typing import Callable as _Callable
        return find_electional_windows(
            jd_start=jd_from_datetime(dt_start),
            jd_end=jd_from_datetime(dt_end),
            latitude=latitude,
            longitude=longitude,
            predicate=predicate,
            policy=policy,
            reader=self._reader,
        )

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        if self._reader_obj is not None:
            kernel_name = self._reader_obj.path.name
        else:
            kernel_name = "unavailable"
        return f"Moira(kernel='{kernel_name}', v{__version__})"
