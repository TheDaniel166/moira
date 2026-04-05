"""
moira.predictive — Forecasting and predictive astrology surface.

Builds on ``moira.classical`` and adds the forecasting toolkit:
transits, progressions (secondary, solar arc, tertiary, converse, etc.),
primary directions, synastry and relationship charts, returns (solar,
lunar, planetary), eclipses, stations, void-of-course Moon, phenomena,
and electional search.

Usage
-----
    from moira.predictive import *

    # Everything from classical is included, plus:
    transits   = find_transits(chart.jd, chart.jd + 365.25, Body.SATURN, natal_lon)
    progressed = secondary_progression(natal_jd, transit_jd)
    sr         = solar_return(natal_jd, 2026)

Next step
---------
For the complete surface (heliacal visibility, parans, astrocartography,
galactic coordinates, uranian points, occultations, harmonics, aspect
patterns, variable stars, and every other subsystem), import from
``moira.facade``.
"""

# ── Everything from classical ────────────────────────────────────────────
from .classical import *  # noqa: F401,F403
from .classical import __all__ as _classical_all

# ── Transits ─────────────────────────────────────────────────────────────
from .transits import (
    TransitTargetKind, TransitSearchKind, TransitWrapperKind,
    TransitRelationKind, TransitRelationBasis, TransitConditionState,
    TransitSearchPolicy, ReturnSearchPolicy, SyzygySearchPolicy,
    TransitComputationPolicy,
    LongitudeResolutionTruth, CrossingSearchTruth,
    TransitComputationTruth, IngressComputationTruth,
    LongitudeResolutionClassification, CrossingSearchClassification,
    TransitComputationClassification, IngressComputationClassification,
    TransitRelation, TransitConditionProfile, TransitChartConditionProfile,
    TransitConditionNetworkNodeKind, TransitConditionNetworkNode,
    TransitConditionNetworkEdge, TransitConditionNetworkProfile,
    TransitEvent, IngressEvent,
    next_transit, find_transits, find_ingresses,
    next_ingress, next_ingress_into,
    solar_return, lunar_return,
    last_new_moon, last_full_moon, prenatal_syzygy,
    planet_return,
    transit_relations, ingress_relations,
    transit_condition_profiles, ingress_condition_profiles,
    transit_chart_condition_profile, transit_condition_network_profile,
)

# ── Progressions ─────────────────────────────────────────────────────────
from .progressions import (
    ProgressionDoctrineTruth, ProgressionComputationTruth,
    ProgressionDoctrineClassification, ProgressionComputationClassification,
    ProgressionRelation,
    ProgressionConditionProfile, ProgressionChartConditionProfile,
    ProgressionConditionNetworkNode, ProgressionConditionNetworkEdge,
    ProgressionConditionNetworkProfile,
    ProgressionTimeKeyPolicy, ProgressionDirectionPolicy,
    ProgressionHouseFramePolicy, ProgressionComputationPolicy,
    ProgressedPosition, ProgressedChart, ProgressedHouseFrame,
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
    progression_chart_condition_profile,
    progression_condition_network_profile,
)

# ── Primary directions ───────────────────────────────────────────────────
from .primary_directions import (
    SpeculumEntry, PrimaryArc,
    speculum, find_primary_arcs,
    DIRECT, CONVERSE,
)

# ── Synastry / relationship charts ───────────────────────────────────────
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
    davison_chart, davison_chart_uncorrected,
    davison_chart_reference_place, davison_chart_spherical_midpoint,
    davison_chart_corrected,
    synastry_contact_relations, mutual_overlay_relations,
    synastry_condition_profiles, synastry_chart_condition_profile,
    synastry_condition_network_profile,
)

# ── Eclipses ─────────────────────────────────────────────────────────────
from .eclipse import (
    EclipseData, EclipseEvent, EclipseType, EclipseCalculator,
    LunarEclipseAnalysis, LocalContactCircumstances,
    LunarEclipseLocalCircumstances,
    SolarBodyCircumstances, SolarEclipseLocalCircumstances,
)
from .compat.nasa.eclipse import (
    NasaLunarEclipseContacts, NasaLunarEclipseEvent,
    next_nasa_lunar_eclipse, previous_nasa_lunar_eclipse,
    translate_lunar_eclipse_event,
)

# ── Stations ─────────────────────────────────────────────────────────────
from .stations import (
    StationEvent, find_stations, next_station,
    is_retrograde, retrograde_periods,
)

# ── Void of Course Moon ──────────────────────────────────────────────────
from .void_of_course import (
    LastAspect, VoidOfCourseWindow,
    void_of_course_window, is_void_of_course,
    next_void_of_course, void_periods_in_range,
)

# ── Phenomena ────────────────────────────────────────────────────────────
from .phenomena import (
    PhenomenonEvent, OrbitalResonance,
    greatest_elongation, perihelion, aphelion,
    next_moon_phase, moon_phases_in_range,
    next_conjunction, conjunctions_in_range, resonance,
)

# ── Electional search ────────────────────────────────────────────────────
from .electional import (
    ElectionalPolicy, ElectionalWindow,
    find_electional_windows, find_electional_moments,
)

# ── Rise / set / twilight ────────────────────────────────────────────────
from .rise_set import RiseSetPolicy, TwilightTimes, twilight_times

# ── Phase / angular diameter ─────────────────────────────────────────────
from .phase import angular_diameter

# ── Heliocentric ─────────────────────────────────────────────────────────
from .planets import HeliocentricData, heliocentric_planet_at, all_heliocentric_at

# ── Orbits ───────────────────────────────────────────────────────────────
from .orbits import KeplerianElements, DistanceExtremes, orbital_elements_at, distance_extremes_at

# ── Planetary nodes / apsides ────────────────────────────────────────────
from .planetary_nodes import OrbitalNode, planetary_node, all_planetary_nodes


# ── Build __all__ ────────────────────────────────────────────────────────

_PREDICTIVE_OWN: list[str] = [
    # Transits
    "TransitTargetKind", "TransitSearchKind", "TransitWrapperKind",
    "TransitRelationKind", "TransitRelationBasis", "TransitConditionState",
    "TransitSearchPolicy", "ReturnSearchPolicy", "SyzygySearchPolicy",
    "TransitComputationPolicy",
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
    "progression_chart_condition_profile",
    "progression_condition_network_profile",
    # Primary directions
    "SpeculumEntry", "PrimaryArc",
    "speculum", "find_primary_arcs",
    "DIRECT", "CONVERSE",
    # Synastry
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
    # Eclipses
    "EclipseData", "EclipseEvent", "EclipseType", "EclipseCalculator",
    "LunarEclipseAnalysis", "LocalContactCircumstances",
    "LunarEclipseLocalCircumstances",
    "SolarBodyCircumstances", "SolarEclipseLocalCircumstances",
    "NasaLunarEclipseContacts", "NasaLunarEclipseEvent",
    "next_nasa_lunar_eclipse", "previous_nasa_lunar_eclipse",
    "translate_lunar_eclipse_event",
    # Stations
    "StationEvent", "find_stations", "next_station",
    "is_retrograde", "retrograde_periods",
    # Void of Course
    "LastAspect", "VoidOfCourseWindow",
    "void_of_course_window", "is_void_of_course",
    "next_void_of_course", "void_periods_in_range",
    # Phenomena
    "PhenomenonEvent", "OrbitalResonance",
    "greatest_elongation", "perihelion", "aphelion",
    "next_moon_phase", "moon_phases_in_range",
    "next_conjunction", "conjunctions_in_range", "resonance",
    # Electional
    "ElectionalPolicy", "ElectionalWindow",
    "find_electional_windows", "find_electional_moments",
    # Rise / set / twilight
    "RiseSetPolicy", "TwilightTimes", "twilight_times",
    # Angular diameter
    "angular_diameter",
    # Heliocentric
    "HeliocentricData", "heliocentric_planet_at", "all_heliocentric_at",
    # Orbits
    "KeplerianElements", "DistanceExtremes",
    "orbital_elements_at", "distance_extremes_at",
    # Planetary nodes
    "OrbitalNode", "planetary_node", "all_planetary_nodes",
]

__all__ = list(_classical_all) + _PREDICTIVE_OWN
