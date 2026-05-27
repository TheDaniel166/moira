from __future__ import annotations

import importlib.machinery
import inspect
import json
from pathlib import Path
import subprocess
import sys
import textwrap
import zipfile

import moira
import moira.classical as classical
import moira.essentials as essentials
import moira.facade as facade
import moira.predictive as predictive
import moira.sky as sky
import moira.sky.bodies as sky_bodies
import moira.sky.eclipse as sky_eclipse
import moira.sky.events as sky_events
import moira.sky.frames as sky_frames
import moira.sky.galactic as sky_galactic
import moira.sky.observation as sky_observation
import moira.sky.occultation as sky_occultation
import moira.sky.position as sky_position
import moira.sky.time as sky_time
import moira.sky.visibility as sky_visibility
import moira.vedic as vedic
import pytest


_EXPECTED_ROOT_PUBLIC_NAMES = {
    "ASHTOTTARI_NAKSHATRA_LORD",
    "ASHTOTTARI_SEQUENCE",
    "ASHTOTTARI_TOTAL",
    "ASHTOTTARI_YEARS",
    "AccidentalConditionClassification",
    "AccidentalConditionKind",
    "AccidentalDignityClassification",
    "AccidentalDignityCondition",
    "AccidentalDignityPolicy",
    "AccidentalDignityTruth",
    "AlternateDashaPeriod",
    "AlternateDashaSequenceProfile",
    "AlternatePeriodProfile",
    "AshtakavargaChartProfile",
    "AshtakavargaPolicy",
    "AshtakavargaResult",
    "AshtottariPolicy",
    "AspectData",
    "Ayanamsa",
    "BATCH_PROGRESSION_TECHNIQUES",
    "BhinnashtakavargaResult",
    "Body",
    "BodyVoidWindow",
    "BodyVoidWindows",
    "BatchFailure",
    "COMET_NAIF",
    "CalendarDateTime",
    "CartesianPosition",
    "Chart",
    "ChartConditionProfile",
    "ChartDignityProfile",
    "CometData",
    "CompoundRelationship",
    "ConditionNetworkEdge",
    "ConditionNetworkNode",
    "ConditionNetworkProfile",
    "ConditionPolarity",
    "DEBILITATION_SIGN",
    "DECAN_NAMES",
    "DECAN_RULING_STARS",
    "DETRIMENT",
    "DOMICILE",
    "DecanHour",
    "DecanHoursNight",
    "DeltaTPolicy",
    "DerivedHouseCusps",
    "DignitiesService",
    "DignityComputationPolicy",
    "DignityConditionProfile",
    "DignityTier",
    "DispositorLink",
    "DispositorshipChain",
    "DispositorshipChartConditionProfile",
    "DispositorshipComparisonBundle",
    "DispositorshipComparisonItem",
    "DispositorshipComputationPolicy",
    "DispositorshipConditionProfile",
    "DispositorshipConditionState",
    "DispositorshipNetworkEdge",
    "DispositorshipNetworkEdgeMode",
    "DispositorshipNetworkNode",
    "DispositorshipNetworkProfile",
    "DispositorshipOrderingPolicy",
    "DispositorshipProfile",
    "DispositorshipRulership",
    "DispositorshipRulershipPolicy",
    "DispositorshipSubjectPolicy",
    "DispositorshipSubjectSet",
    "DispositorshipSubsystemProfile",
    "DispositorshipTerminationKind",
    "DispositorshipTerminationPolicy",
    "DispositorshipUnsupportedSubjectPolicy",
    "DistanceExtremes",
    "EXALTATION",
    "EXALTATION_DEGREE",
    "EXALTATION_SIGN",
    "EssentialDignityClassification",
    "EssentialDignityDoctrine",
    "EssentialDignityKind",
    "EssentialDignityPolicy",
    "EssentialDignityTruth",
    "ExtinctionCoefficient",
    "FALL",
    "FamilyResonance",
    "GalacticAngles",
    "GalacticHouseBoundaryProfile",
    "GalacticHouseCusps",
    "GalacticHousePlacement",
    "GeneralVisibilityEvent",
    "HarmogramChartDomain",
    "HarmogramIntensityFamily",
    "HarmogramIntensityPolicy",
    "HarmogramPolicy",
    "HarmogramTraceFamily",
    "HarmonicDomain",
    "HeliacalEventKind",
    "HouseCusps",
    "HouseSystem",
    "JaiminiChartProfile",
    "JaiminiKarakaResult",
    "JaiminiPolicy",
    "KARAKA_NAMES_7",
    "KARAKA_NAMES_8",
    "KARANA_NAMES",
    "KalaBala",
    "KarakaAssignment",
    "KarakaConditionProfile",
    "KarakaPair",
    "KarakaPlanetType",
    "KarakaRole",
    "KaranaType",
    "KeplerianElements",
    "LastAspect",
    "LightPollutionClass",
    "LightPollutionDerivationMode",
    "LunarCrescentDetails",
    "LunarCrescentVisibilityClass",
    "MEAN_DAILY_MOTION",
    "MULATRIKONA_END",
    "MULATRIKONA_SIGN",
    "MULATRIKONA_START",
    "MercurySectModel",
    "MissingEphemerisKernelError",
    "Moira",
    "MoonlightPolicy",
    "MutualReceptionPolicy",
    "MutualReceptionTruth",
    "NAISARGIKA_BALA",
    "NATURAL_ENEMIES",
    "NATURAL_FRIENDS",
    "NATURAL_NEUTRALS",
    "NodeData",
    "NodesAndApsides",
    "OWN_SIGNS",
    "ObserverAid",
    "ObserverVisibilityEnvironment",
    "OrbitalNode",
    "PLANETARY_JOYS",
    "PREFERRED_GENDER",
    "PREFERRED_HEMISPHERE",
    "PanchangaElement",
    "PanchangaPolicy",
    "PanchangaProfile",
    "PanchangaResult",
    "ParticipatingRulerPolicy",
    "PlanetData",
    "PlanetHeliacalEvent",
    "PlanetPhenomena",
    "PlanetShadbala",
    "PlanetTimeSeries",
    "ChartBatchRequest",
    "ChartBatchResult",
    "EventBatchRequest",
    "EventBatchResult",
    "ReturnBatchRequest",
    "ReturnBatchResult",
    "ProgressionBatchRequest",
    "ProgressionBatchResult",
    "PlanetaryConditionProfile",
    "PlanetaryConditionState",
    "PlanetaryDignity",
    "PlanetaryReception",
    "PlanetaryRelationship",
    "PointSetHarmonicVectorPolicy",
    "ProximityEvent",
    "REKHA_TABLES",
    "REQUIRED_RUPAS",
    "ReceptionBasis",
    "ReceptionClassification",
    "ReceptionKind",
    "ReceptionMode",
    "RekhaTier",
    "ResonantAspect",
    "SECT",
    "SectClassification",
    "SectHayzPolicy",
    "SectStateKind",
    "SectTruth",
    "ShadbalaChartProfile",
    "ShadbalaConditionProfile",
    "ShadbalaPolicy",
    "ShadbalaResult",
    "ShadbalaTier",
    "SignStrengthProfile",
    "SkyPosition",
    "SolarConditionClassification",
    "SolarConditionKind",
    "SolarConditionPolicy",
    "SolarConditionTruth",
    "SthanaBala",
    "TITHI_NAMES",
    "TithiConditionProfile",
    "TithiPaksha",
    "TriplicityAssignment",
    "TriplicityDoctrine",
    "TransitBatchRequest",
    "TransitBatchResult",
    "TriplicityElement",
    "UnsupportedSubjectHandling",
    "VARA_LORDS",
    "VARA_NAMES",
    "VaraLordType",
    "VedicDignityPolicy",
    "VedicDignityRank",
    "VedicDignityResult",
    "VisibilityAssessment",
    "VisibilityCriterionFamily",
    "VisibilityExtinctionModel",
    "VisibilityPolicy",
    "VisibilitySearchPolicy",
    "VisibilityTargetKind",
    "VisibilityTwilightModel",
    "VoidOfCourseWindow",
    "YOGA_NAMES",
    "YOGINI_PLANETS",
    "YOGINI_SEQUENCE",
    "YOGINI_TOTAL",
    "YOGINI_YEARS",
    "YogaClass",
    "YoginiPolicy",
    "__author__",
    "__version__",
    "all_comets_at",
    "all_nakshatras_at",
    "all_planetary_nodes",
    "almuten_figuris",
    "alternate_period_profile",
    "alternate_sequence_profile",
    "apparent_sidereal_time_at",
    "ashtakavarga",
    "ashtakavarga_chart_profile",
    "ashtottari",
    "assign_galactic_house",
    "asteroid_family",
    "atmakaraka",
    "available_decans",
    "ayanamsa",
    "batch_charts",
    "batch_progressions",
    "batch_events",
    "batch_returns",
    "batch_transits",
    "bhinnashtakavarga",
    "body_galactic_house_position",
    "calculate_chart_condition_profile",
    "calculate_condition_network_profile",
    "calculate_condition_profiles",
    "calculate_dignities",
    "calculate_dispositorship",
    "calculate_dispositorship_chart_condition_profile",
    "calculate_dispositorship_condition_profiles",
    "calculate_dispositorship_network_profile",
    "calculate_dispositorship_subsystem_profile",
    "calculate_galactic_houses",
    "calculate_receptions",
    "calendar_datetime_from_jd",
    "calendar_from_jd",
    "chart_dignity_profile",
    "chesta_bala",
    "comet_at",
    "compare_dispositorship",
    "datetime_from_jd",
    "decan_at",
    "decan_for_longitude",
    "decan_hours",
    "delta_t",
    "delta_t_from_jd",
    "derived_houses",
    "describe_galactic_boundary",
    "dig_bala",
    "dignity_condition_profile",
    "distance_extremes_at",
    "drig_bala",
    "families_in_chart",
    "family_members",
    "find_phasis",
    "find_all_ingresses",
    "find_resonant_aspects",
    "format_jd_utc",
    "geometric_node",
    "greenwich_mean_sidereal_time",
    "harmogram_trace",
    "hora_lord_at",
    "intensity_function_spectrum",
    "is_besieged",
    "is_day_chart",
    "is_in_halb",
    "is_in_hayz",
    "is_in_joy",
    "is_in_sect",
    "is_void_of_course",
    "jaimini_chart_profile",
    "jaimini_karakas",
    "jd_from_datetime",
    "julian_day",
    "kala_bala",
    "karaka_condition_profile",
    "karaka_pair",
    "list_ayanamsa_systems",
    "list_comets",
    "list_decans",
    "local_sidereal_time",
    "mutual_receptions",
    "nakshatra_of",
    "next_void_of_course",
    "nodes_and_apsides_at",
    "orbital_elements_at",
    "oriental_occidental",
    "panchanga_at",
    "panchanga_profile",
    "parts_from_zero_aries",
    "planet_acronychal_rising",
    "planet_acronychal_setting",
    "planet_heliacal_rising",
    "planet_heliacal_setting",
    "planet_phenomena_at",
    "planet_time_series",
    "planetary_node",
    "planetary_relationships",
    "point_set_harmonic_vector",
    "project_harmogram_strength",
    "proximity_events_in_range",
    "resonance_network",
    "safe_datetime_from_jd",
    "sect_light",
    "shadbala",
    "shadbala_chart_profile",
    "shadbala_condition_profile",
    "sidereal_to_tropical",
    "sign_strength_profile",
    "solar_condition_at",
    "solar_condition_events_in_range",
    "sthana_bala",
    "tithi_condition_profile",
    "transit_strength",
    "triplicity_assignment_for",
    "triplicity_score",
    "tropical_to_sidereal",
    "validate_alternate_dasha_output",
    "validate_ashtakavarga_output",
    "validate_dignity_output",
    "validate_jaimini_output",
    "validate_panchanga_output",
    "validate_shadbala_output",
    "vedic_dignity",
    "visibility_assessment",
    "visibility_event",
    "visual_limiting_magnitude",
    "void_of_course_window",
    "void_periods_all_planets",
    "BATCH_EVENT_KINDS",
    "BATCH_RETURN_KINDS",
    "void_periods_in_range",
    "yogini_dasha",
    "zero_aries_parts_harmonic_vector",
}

_EXPECTED_ROOT_ONLY_NAMES = {
    "ASHTOTTARI_NAKSHATRA_LORD",
    "ASHTOTTARI_SEQUENCE",
    "ASHTOTTARI_TOTAL",
    "ASHTOTTARI_YEARS",
    "AlternateDashaPeriod",
    "AlternateDashaSequenceProfile",
    "AlternatePeriodProfile",
    "AshtakavargaChartProfile",
    "AshtakavargaPolicy",
    "AshtakavargaResult",
    "AshtottariPolicy",
    "BhinnashtakavargaResult",
    "ChartDignityProfile",
    "CompoundRelationship",
    "DEBILITATION_SIGN",
    "DECAN_NAMES",
    "DECAN_RULING_STARS",
    "DETRIMENT",
    "DOMICILE",
    "DecanHour",
    "DecanHoursNight",
    "DignityConditionProfile",
    "DignityTier",
    "DispositorLink",
    "DispositorshipChain",
    "DispositorshipChartConditionProfile",
    "DispositorshipComparisonBundle",
    "DispositorshipComparisonItem",
    "DispositorshipComputationPolicy",
    "DispositorshipConditionProfile",
    "DispositorshipConditionState",
    "DispositorshipNetworkEdge",
    "DispositorshipNetworkEdgeMode",
    "DispositorshipNetworkNode",
    "DispositorshipNetworkProfile",
    "DispositorshipOrderingPolicy",
    "DispositorshipProfile",
    "DispositorshipRulership",
    "DispositorshipRulershipPolicy",
    "DispositorshipSubjectPolicy",
    "DispositorshipSubjectSet",
    "DispositorshipSubsystemProfile",
    "DispositorshipTerminationKind",
    "DispositorshipTerminationPolicy",
    "DispositorshipUnsupportedSubjectPolicy",
    "EXALTATION",
    "EXALTATION_DEGREE",
    "EXALTATION_SIGN",
    "FALL",
    "HarmogramChartDomain",
    "HarmogramIntensityFamily",
    "HarmogramIntensityPolicy",
    "HarmogramPolicy",
    "HarmogramTraceFamily",
    "HarmonicDomain",
    "JaiminiChartProfile",
    "JaiminiKarakaResult",
    "JaiminiPolicy",
    "KARAKA_NAMES_7",
    "KARAKA_NAMES_8",
    "KARANA_NAMES",
    "KalaBala",
    "KarakaAssignment",
    "KarakaConditionProfile",
    "KarakaPair",
    "KarakaPlanetType",
    "KarakaRole",
    "KaranaType",
    "MEAN_DAILY_MOTION",
    "MULATRIKONA_END",
    "MULATRIKONA_SIGN",
    "MULATRIKONA_START",
    "NAISARGIKA_BALA",
    "NATURAL_ENEMIES",
    "NATURAL_FRIENDS",
    "NATURAL_NEUTRALS",
    "OWN_SIGNS",
    "PLANETARY_JOYS",
    "PREFERRED_GENDER",
    "PREFERRED_HEMISPHERE",
    "PanchangaElement",
    "PanchangaPolicy",
    "PanchangaProfile",
    "PanchangaResult",
    "ParticipatingRulerPolicy",
    "PlanetShadbala",
    "PlanetaryRelationship",
    "PointSetHarmonicVectorPolicy",
    "REKHA_TABLES",
    "REQUIRED_RUPAS",
    "RekhaTier",
    "SECT",
    "ShadbalaChartProfile",
    "ShadbalaConditionProfile",
    "ShadbalaPolicy",
    "ShadbalaResult",
    "ShadbalaTier",
    "SignStrengthProfile",
    "SthanaBala",
    "TITHI_NAMES",
    "TithiConditionProfile",
    "TithiPaksha",
    "TriplicityAssignment",
    "TriplicityDoctrine",
    "TriplicityElement",
    "UnsupportedSubjectHandling",
    "VARA_LORDS",
    "VARA_NAMES",
    "VaraLordType",
    "VedicDignityPolicy",
    "VedicDignityRank",
    "VedicDignityResult",
    "YOGA_NAMES",
    "YOGINI_PLANETS",
    "YOGINI_SEQUENCE",
    "YOGINI_TOTAL",
    "YOGINI_YEARS",
    "YogaClass",
    "YoginiPolicy",
    "__author__",
    "__version__",
    "alternate_period_profile",
    "alternate_sequence_profile",
    "ashtakavarga",
    "ashtakavarga_chart_profile",
    "ashtottari",
    "atmakaraka",
    "available_decans",
    "bhinnashtakavarga",
    "calculate_dispositorship",
    "calculate_dispositorship_chart_condition_profile",
    "calculate_dispositorship_condition_profiles",
    "calculate_dispositorship_network_profile",
    "calculate_dispositorship_subsystem_profile",
    "chart_dignity_profile",
    "chesta_bala",
    "compare_dispositorship",
    "decan_at",
    "decan_for_longitude",
    "decan_hours",
    "dig_bala",
    "dignity_condition_profile",
    "drig_bala",
    "harmogram_trace",
    "hora_lord_at",
    "intensity_function_spectrum",
    "is_besieged",
    "is_in_halb",
    "is_in_joy",
    "jaimini_chart_profile",
    "jaimini_karakas",
    "kala_bala",
    "karaka_condition_profile",
    "karaka_pair",
    "list_decans",
    "oriental_occidental",
    "panchanga_at",
    "panchanga_profile",
    "parts_from_zero_aries",
    "planetary_relationships",
    "point_set_harmonic_vector",
    "project_harmogram_strength",
    "shadbala",
    "shadbala_chart_profile",
    "shadbala_condition_profile",
    "sign_strength_profile",
    "sthana_bala",
    "tithi_condition_profile",
    "transit_strength",
    "triplicity_assignment_for",
    "triplicity_score",
    "validate_alternate_dasha_output",
    "validate_ashtakavarga_output",
    "validate_dignity_output",
    "validate_jaimini_output",
    "validate_panchanga_output",
    "validate_shadbala_output",
    "vedic_dignity",
    "yogini_dasha",
    "zero_aries_parts_harmonic_vector",
}

_EXPECTED_MOIRA_METHODS = {
    "antiscia",
    "ascendant_arc_directions",
    "aspect_transits",
    "aspects",
    "astrocartography",
    "batch_charts",
    "batch_events",
    "batch_progressions",
    "batch_returns",
    "batch_transits",
    "calendar_from_jd",
    "chart",
    "close_approaches",
    "composite_chart",
    "composite_chart_reference_place",
    "configure_kernel_path",
    "conjunctions",
    "converse_duodenary_progression",
    "converse_minor_progression",
    "converse_naibod_in_longitude",
    "converse_naibod_in_right_ascension",
    "converse_planetary_arc_directions",
    "converse_progression",
    "converse_quotidian_lunar_progression",
    "converse_quotidian_solar_progression",
    "converse_solar_arc",
    "converse_solar_arc_ra",
    "converse_tertiary_ii_progression",
    "converse_tertiary_progression",
    "current_decennials",
    "daily_house_frame",
    "davison_chart",
    "davison_chart_corrected",
    "davison_chart_reference_place",
    "davison_chart_spherical_midpoint",
    "davison_chart_uncorrected",
    "decennials",
    "declination_transits",
    "dignities",
    "download_missing_kernels",
    "duodenary_progression",
    "eclipse",
    "eclipse_hits_in_range",
    "egyptian_date",
    "electional_windows",
    "firdaria",
    "fixed_star",
    "from_jd",
    "galactic_angles",
    "galactic_chart",
    "galactic_houses",
    "gauquelin_sectors",
    "geodetic",
    "geodetic_planet_equivalents",
    "get_kernel_status",
    "harmonic",
    "heliacal_rising",
    "heliacal_rising_event",
    "heliacal_setting",
    "heliacal_setting_event",
    "heliocentric",
    "house_overlay",
    "houses",
    "ingresses",
    "is_kernel_available",
    "is_moon_void_of_course",
    "jd",
    "local_space",
    "longevity",
    "lots",
    "lunar_mansions",
    "lunar_return",
    "midpoints",
    "midpoints_to_point",
    "minor_progression",
    "moon_phases",
    "moon_void_of_course",
    "multiple_star_components",
    "multiple_star_separation",
    "mutual_house_overlays",
    "mutual_receptions",
    "naibod_in_longitude",
    "naibod_in_right_ascension",
    "nakshatras",
    "next_conjunction",
    "next_ingress",
    "next_ingress_into",
    "occultations",
    "parans",
    "patterns",
    "phase",
    "phenomena",
    "planet_return",
    "planetary_arc_directions",
    "planetary_hours",
    "planetary_node",
    "planetary_nodes",
    "planetocentric",
    "primary_directions",
    "profection",
    "progression",
    "proximity_events",
    "quotidian_lunar_progression",
    "quotidian_solar_progression",
    "received_light",
    "relocated_chart",
    "resonance",
    "retrograde_periods",
    "sidereal_chart",
    "sky_position",
    "solar_arc_directions",
    "solar_arc_directions_ra",
    "solar_condition_at",
    "solar_condition_events",
    "solar_return",
    "solar_return_chart",
    "build_varshaphal_chart",
    "mudda_dasha",
    "varshaphal",
    "varshaphal_chart",
    "sothic_cycle",
    "sothic_epoch_finder",
    "speculum",
    "ssb_chart",
    "stations",
    "synastry_aspects",
    "synodic_phase",
    "syzygy",
    "tertiary_ii_progression",
    "tertiary_progression",
    "transits",
    "twilight",
    "uranian",
    "variable_star_magnitude",
    "variable_star_maxima",
    "variable_star_minima",
    "variable_star_next_maximum",
    "variable_star_next_minimum",
    "variable_star_phase",
    "variable_star_quality",
    "vimshottari_dasha",
    "zodiacal_releasing",
}

_EXPECTED_ESSENTIALS_PUBLIC_NAMES = set(essentials.__all__)
_EXPECTED_CLASSICAL_PUBLIC_NAMES = set(classical.__all__)
_EXPECTED_PREDICTIVE_PUBLIC_NAMES = set(predictive.__all__)
_EXPECTED_FACADE_PUBLIC_NAMES = set(facade.__all__)
_EXPECTED_VEDIC_PUBLIC_NAMES = set(vedic.__all__)
_EXPECTED_SKY_PUBLIC_NAMES = set(sky.__all__)
_EXPECTED_SKY_TIME_PUBLIC_NAMES = set(sky_time.__all__)
_EXPECTED_SKY_POSITION_PUBLIC_NAMES = set(sky_position.__all__)
_EXPECTED_SKY_FRAMES_PUBLIC_NAMES = set(sky_frames.__all__)
_EXPECTED_SKY_VISIBILITY_PUBLIC_NAMES = set(sky_visibility.__all__)
_EXPECTED_SKY_BODIES_PUBLIC_NAMES = set(sky_bodies.__all__)
_EXPECTED_SKY_OBSERVATION_PUBLIC_NAMES = set(sky_observation.__all__)
_EXPECTED_SKY_GALACTIC_PUBLIC_NAMES = set(sky_galactic.__all__)
_EXPECTED_SKY_EVENTS_PUBLIC_NAMES = set(sky_events.__all__)
_EXPECTED_SKY_ECLIPSE_PUBLIC_NAMES = set(sky_eclipse.__all__)
_EXPECTED_SKY_OCCULTATION_PUBLIC_NAMES = set(sky_occultation.__all__)
_EXTENSION_SUFFIXES = tuple(importlib.machinery.EXTENSION_SUFFIXES)


def test_root_public_surface_snapshot_is_exact() -> None:
    actual = set(moira.__all__)
    assert actual == _EXPECTED_ROOT_PUBLIC_NAMES, (
        "moira.__all__ drifted.\n"
        f"Unexpected additions: {sorted(actual - _EXPECTED_ROOT_PUBLIC_NAMES)}\n"
        f"Unexpected removals: {sorted(_EXPECTED_ROOT_PUBLIC_NAMES - actual)}"
    )


def test_root_surface_is_duplicate_free_and_bound() -> None:
    names = list(moira.__all__)
    assert len(names) == len(set(names)), "moira.__all__ contains duplicate names"
    missing = [name for name in names if not hasattr(moira, name)]
    assert not missing, f"moira.__all__ declares unbound names: {missing}"


def test_root_star_import_matches_public_surface() -> None:
    namespace: dict[str, object] = {}
    exec("from moira import *", {}, namespace)

    missing = sorted(_EXPECTED_ROOT_PUBLIC_NAMES - set(namespace))
    extra = sorted(set(namespace) - _EXPECTED_ROOT_PUBLIC_NAMES)
    assert not missing, f"`from moira import *` missed public names: {missing}"
    assert not extra, f"`from moira import *` leaked unexpected names: {extra}"


def test_root_only_surface_snapshot_is_exact() -> None:
    actual = set(moira.__all__) - set(facade.__all__)
    assert not actual, (
        "moira root exports must now be fully covered by moira.facade.\n"
        f"Unexpected remaining root-only names: {sorted(actual)}"
    )


def test_moira_public_method_snapshot_is_exact() -> None:
    actual = {
        name
        for name, member in inspect.getmembers(facade.Moira)
        if not name.startswith("_") and inspect.isfunction(member)
    }
    assert actual == _EXPECTED_MOIRA_METHODS, (
        "Moira() public method surface drifted.\n"
        f"Unexpected additions: {sorted(actual - _EXPECTED_MOIRA_METHODS)}\n"
        f"Unexpected removals: {sorted(_EXPECTED_MOIRA_METHODS - actual)}"
    )


def test_moira_instance_public_methods_are_callable() -> None:
    engine = facade.Moira()

    non_callable = [
        name for name in _EXPECTED_MOIRA_METHODS if not callable(getattr(engine, name))
    ]
    assert not non_callable, f"Moira instance lost callable methods: {non_callable}"


@pytest.mark.slow
@pytest.mark.serial
def test_built_wheel_matches_source_public_surface(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dist_dir = tmp_path / "dist"
    unpack_dir = tmp_path / "wheel_unpack"
    run_dir = tmp_path / "run"
    dist_dir.mkdir()
    unpack_dir.mkdir()
    run_dir.mkdir()

    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(dist_dir),
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    wheels = sorted(dist_dir.glob("moira_astro-*.whl"))
    assert wheels, "wheel build produced no moira_astro artifact"
    wheel_path = wheels[-1]

    with zipfile.ZipFile(wheel_path) as zf:
        wheel_members = zf.namelist()
        zf.extractall(unpack_dir)

    native_members = [
        name
        for name in wheel_members
        if name.startswith("moira/_moira_native") and name.endswith(_EXTENSION_SUFFIXES)
    ]
    assert native_members, "wheel artifact is missing the compiled moira/_moira_native extension"
    assert not any(name.endswith(".exp") for name in wheel_members), "wheel should not ship MSVC .exp byproducts"
    assert not any(name.endswith(".lib") for name in wheel_members), "wheel should not ship MSVC .lib byproducts"

    probe = textwrap.dedent(
        f"""
        import inspect
        import json
        import os
        import sys

        repo_root = os.path.normcase(r"{repo_root}")
        sys.path = [p for p in sys.path if os.path.normcase(os.path.abspath(p or os.curdir)) != repo_root]
        sys.path.insert(0, r"{unpack_dir}")

        import moira
        import moira.classical as classical
        import moira.essentials as essentials
        import moira.facade as facade
        import moira.moira_native as moira_native
        import moira.predictive as predictive
        import moira.sky as sky
        import moira.sky.bodies as sky_bodies
        import moira.sky.eclipse as sky_eclipse
        import moira.sky.events as sky_events
        import moira.sky.frames as sky_frames
        import moira.sky.galactic as sky_galactic
        import moira.sky.observation as sky_observation
        import moira.sky.occultation as sky_occultation
        import moira.sky.position as sky_position
        import moira.sky.time as sky_time
        import moira.sky.visibility as sky_visibility
        import moira.vedic as vedic

        def export_star(module_name):
            ns = {{}}
            exec(f"from {{module_name}} import *", {{}}, ns)
            return sorted(ns)

        data = {{
            "root_all": sorted(moira.__all__),
            "essentials_all": sorted(essentials.__all__),
            "classical_all": sorted(classical.__all__),
            "predictive_all": sorted(predictive.__all__),
            "vedic_all": sorted(vedic.__all__),
            "sky_all": sorted(sky.__all__),
            "sky_time_all": sorted(sky_time.__all__),
            "sky_position_all": sorted(sky_position.__all__),
            "sky_frames_all": sorted(sky_frames.__all__),
            "sky_visibility_all": sorted(sky_visibility.__all__),
            "sky_bodies_all": sorted(sky_bodies.__all__),
            "sky_observation_all": sorted(sky_observation.__all__),
            "sky_galactic_all": sorted(sky_galactic.__all__),
            "sky_events_all": sorted(sky_events.__all__),
            "sky_eclipse_all": sorted(sky_eclipse.__all__),
            "sky_occultation_all": sorted(sky_occultation.__all__),
            "facade_all": sorted(facade.__all__),
            "native_backend_file": os.path.normcase(os.path.abspath(moira_native.__backend_file__)),
            "methods": sorted(
                name for name, member in inspect.getmembers(facade.Moira)
                if not name.startswith("_") and inspect.isfunction(member)
            ),
            "root_star": export_star("moira"),
            "essentials_star": export_star("moira.essentials"),
            "classical_star": export_star("moira.classical"),
            "predictive_star": export_star("moira.predictive"),
            "vedic_star": export_star("moira.vedic"),
            "sky_star": export_star("moira.sky"),
            "sky_time_star": export_star("moira.sky.time"),
            "sky_position_star": export_star("moira.sky.position"),
            "sky_frames_star": export_star("moira.sky.frames"),
            "sky_visibility_star": export_star("moira.sky.visibility"),
            "sky_bodies_star": export_star("moira.sky.bodies"),
            "sky_observation_star": export_star("moira.sky.observation"),
            "sky_galactic_star": export_star("moira.sky.galactic"),
            "sky_events_star": export_star("moira.sky.events"),
            "sky_eclipse_star": export_star("moira.sky.eclipse"),
            "sky_occultation_star": export_star("moira.sky.occultation"),
            "facade_star": export_star("moira.facade"),
            "root_file": os.path.normcase(os.path.abspath(moira.__file__)),
            "essentials_file": os.path.normcase(os.path.abspath(essentials.__file__)),
            "classical_file": os.path.normcase(os.path.abspath(classical.__file__)),
            "predictive_file": os.path.normcase(os.path.abspath(predictive.__file__)),
            "vedic_file": os.path.normcase(os.path.abspath(vedic.__file__)),
            "sky_file": os.path.normcase(os.path.abspath(sky.__file__)),
            "sky_time_file": os.path.normcase(os.path.abspath(sky_time.__file__)),
            "sky_position_file": os.path.normcase(os.path.abspath(sky_position.__file__)),
            "sky_frames_file": os.path.normcase(os.path.abspath(sky_frames.__file__)),
            "sky_visibility_file": os.path.normcase(os.path.abspath(sky_visibility.__file__)),
            "sky_bodies_file": os.path.normcase(os.path.abspath(sky_bodies.__file__)),
            "sky_observation_file": os.path.normcase(os.path.abspath(sky_observation.__file__)),
            "sky_galactic_file": os.path.normcase(os.path.abspath(sky_galactic.__file__)),
            "sky_events_file": os.path.normcase(os.path.abspath(sky_events.__file__)),
            "sky_eclipse_file": os.path.normcase(os.path.abspath(sky_eclipse.__file__)),
            "sky_occultation_file": os.path.normcase(os.path.abspath(sky_occultation.__file__)),
            "facade_file": os.path.normcase(os.path.abspath(facade.__file__)),
        }}
        print(json.dumps(data))
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=run_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["root_file"].startswith(str(unpack_dir).lower()) or payload["root_file"].startswith(str(unpack_dir))
    assert payload["essentials_file"].startswith(str(unpack_dir).lower()) or payload["essentials_file"].startswith(str(unpack_dir))
    assert payload["classical_file"].startswith(str(unpack_dir).lower()) or payload["classical_file"].startswith(str(unpack_dir))
    assert payload["predictive_file"].startswith(str(unpack_dir).lower()) or payload["predictive_file"].startswith(str(unpack_dir))
    assert payload["vedic_file"].startswith(str(unpack_dir).lower()) or payload["vedic_file"].startswith(str(unpack_dir))
    assert payload["sky_file"].startswith(str(unpack_dir).lower()) or payload["sky_file"].startswith(str(unpack_dir))
    assert payload["sky_time_file"].startswith(str(unpack_dir).lower()) or payload["sky_time_file"].startswith(str(unpack_dir))
    assert payload["sky_position_file"].startswith(str(unpack_dir).lower()) or payload["sky_position_file"].startswith(str(unpack_dir))
    assert payload["sky_frames_file"].startswith(str(unpack_dir).lower()) or payload["sky_frames_file"].startswith(str(unpack_dir))
    assert payload["sky_visibility_file"].startswith(str(unpack_dir).lower()) or payload["sky_visibility_file"].startswith(str(unpack_dir))
    assert payload["sky_bodies_file"].startswith(str(unpack_dir).lower()) or payload["sky_bodies_file"].startswith(str(unpack_dir))
    assert payload["sky_observation_file"].startswith(str(unpack_dir).lower()) or payload["sky_observation_file"].startswith(str(unpack_dir))
    assert payload["sky_galactic_file"].startswith(str(unpack_dir).lower()) or payload["sky_galactic_file"].startswith(str(unpack_dir))
    assert payload["sky_events_file"].startswith(str(unpack_dir).lower()) or payload["sky_events_file"].startswith(str(unpack_dir))
    assert payload["sky_eclipse_file"].startswith(str(unpack_dir).lower()) or payload["sky_eclipse_file"].startswith(str(unpack_dir))
    assert payload["sky_occultation_file"].startswith(str(unpack_dir).lower()) or payload["sky_occultation_file"].startswith(str(unpack_dir))
    assert payload["facade_file"].startswith(str(unpack_dir).lower()) or payload["facade_file"].startswith(str(unpack_dir))
    assert payload["native_backend_file"].startswith(str(unpack_dir).lower()) or payload["native_backend_file"].startswith(str(unpack_dir))
    assert set(payload["root_all"]) == _EXPECTED_ROOT_PUBLIC_NAMES
    assert set(payload["essentials_all"]) == _EXPECTED_ESSENTIALS_PUBLIC_NAMES
    assert set(payload["classical_all"]) == _EXPECTED_CLASSICAL_PUBLIC_NAMES
    assert set(payload["predictive_all"]) == _EXPECTED_PREDICTIVE_PUBLIC_NAMES
    assert set(payload["vedic_all"]) == _EXPECTED_VEDIC_PUBLIC_NAMES
    assert set(payload["sky_all"]) == _EXPECTED_SKY_PUBLIC_NAMES
    assert set(payload["sky_time_all"]) == _EXPECTED_SKY_TIME_PUBLIC_NAMES
    assert set(payload["sky_position_all"]) == _EXPECTED_SKY_POSITION_PUBLIC_NAMES
    assert set(payload["sky_frames_all"]) == _EXPECTED_SKY_FRAMES_PUBLIC_NAMES
    assert set(payload["sky_visibility_all"]) == _EXPECTED_SKY_VISIBILITY_PUBLIC_NAMES
    assert set(payload["sky_bodies_all"]) == _EXPECTED_SKY_BODIES_PUBLIC_NAMES
    assert set(payload["sky_observation_all"]) == _EXPECTED_SKY_OBSERVATION_PUBLIC_NAMES
    assert set(payload["sky_galactic_all"]) == _EXPECTED_SKY_GALACTIC_PUBLIC_NAMES
    assert set(payload["sky_events_all"]) == _EXPECTED_SKY_EVENTS_PUBLIC_NAMES
    assert set(payload["sky_eclipse_all"]) == _EXPECTED_SKY_ECLIPSE_PUBLIC_NAMES
    assert set(payload["sky_occultation_all"]) == _EXPECTED_SKY_OCCULTATION_PUBLIC_NAMES
    assert set(payload["facade_all"]) == _EXPECTED_FACADE_PUBLIC_NAMES
    assert set(payload["root_star"]) == _EXPECTED_ROOT_PUBLIC_NAMES
    assert set(payload["essentials_star"]) == _EXPECTED_ESSENTIALS_PUBLIC_NAMES
    assert set(payload["classical_star"]) == _EXPECTED_CLASSICAL_PUBLIC_NAMES
    assert set(payload["predictive_star"]) == _EXPECTED_PREDICTIVE_PUBLIC_NAMES
    assert set(payload["vedic_star"]) == _EXPECTED_VEDIC_PUBLIC_NAMES
    assert set(payload["sky_star"]) == _EXPECTED_SKY_PUBLIC_NAMES
    assert set(payload["sky_time_star"]) == _EXPECTED_SKY_TIME_PUBLIC_NAMES
    assert set(payload["sky_position_star"]) == _EXPECTED_SKY_POSITION_PUBLIC_NAMES
    assert set(payload["sky_frames_star"]) == _EXPECTED_SKY_FRAMES_PUBLIC_NAMES
    assert set(payload["sky_visibility_star"]) == _EXPECTED_SKY_VISIBILITY_PUBLIC_NAMES
    assert set(payload["sky_bodies_star"]) == _EXPECTED_SKY_BODIES_PUBLIC_NAMES
    assert set(payload["sky_observation_star"]) == _EXPECTED_SKY_OBSERVATION_PUBLIC_NAMES
    assert set(payload["sky_galactic_star"]) == _EXPECTED_SKY_GALACTIC_PUBLIC_NAMES
    assert set(payload["sky_events_star"]) == _EXPECTED_SKY_EVENTS_PUBLIC_NAMES
    assert set(payload["sky_eclipse_star"]) == _EXPECTED_SKY_ECLIPSE_PUBLIC_NAMES
    assert set(payload["sky_occultation_star"]) == _EXPECTED_SKY_OCCULTATION_PUBLIC_NAMES
    assert set(payload["facade_star"]) == _EXPECTED_FACADE_PUBLIC_NAMES
    assert set(payload["methods"]) == _EXPECTED_MOIRA_METHODS
    assert set(payload["root_all"]) <= set(payload["facade_all"])
