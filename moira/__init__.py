"""
Moira public package surface.

This module is intentionally thin. The heavyweight facade implementation lives
in ``moira.facade``; subsystem APIs are imported from their owning modules.
"""

import sys as _sys
from ._kernel_paths import find_kernel as _find_kernel

if not _find_kernel("de441.bsp").exists():
    print(
        "\n"
        "  [moira] WARNING: de441.bsp is not installed.\n"
        "  Most Moira features will fail until you download the JPL kernels.\n"
        "  Run the following command to download them:\n"
        "\n"
        "      moira-download-kernels\n"
        "\n"
        "  Or, inside Python:\n"
        "\n"
        "      from moira.download_kernels import download_missing\n"
        "      download_missing()\n",
        file=_sys.stderr,
    )

del _sys, _find_kernel

from .constants import Body, HouseSystem
from .facade import Chart, MissingEphemerisKernelError, Moira, __author__, __version__
from .houses import HouseCusps
from .julian import (
    CalendarDateTime,
    DeltaTPolicy,
    calendar_datetime_from_jd,
    calendar_from_jd,
    datetime_from_jd,
    delta_t,
    format_jd_utc,
    greenwich_mean_sidereal_time,
    jd_from_datetime,
    julian_day,
    local_sidereal_time,
    safe_datetime_from_jd,
)
from .nodes import NodeData
from .orbits import DistanceExtremes, KeplerianElements, distance_extremes_at, orbital_elements_at
from .planets import CartesianPosition, PlanetData, SkyPosition
from .sidereal import Ayanamsa, ayanamsa, list_ayanamsa_systems, sidereal_to_tropical, tropical_to_sidereal
from .aspects import AspectData
from .harmograms import (
    HarmogramChartDomain,
    HarmogramIntensityFamily,
    HarmogramIntensityPolicy,
    HarmogramPolicy,
    HarmogramTraceFamily,
    HarmonicDomain,
    PointSetHarmonicVectorPolicy,
    harmogram_trace,
    intensity_function_spectrum,
    parts_from_zero_aries,
    point_set_harmonic_vector,
    project_harmogram_strength,
    zero_aries_parts_harmonic_vector,
)
from .heliacal import (
    # concrete planet wrappers (V0 baseline)
    PlanetHeliacalEvent,
    planet_acronychal_rising,
    planet_acronychal_setting,
    planet_heliacal_rising,
    planet_heliacal_setting,
    # V5 generalized visibility surface
    HeliacalEventKind,
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

__all__ = [
    "Moira",
    "Chart",
    "MissingEphemerisKernelError",
    "Body",
    "HouseSystem",
    "Ayanamsa",
    "PlanetData",
    "SkyPosition",
    "CartesianPosition",
    "NodeData",
    "HouseCusps",
    "AspectData",
    "HarmonicDomain",
    "PointSetHarmonicVectorPolicy",
    "HarmogramIntensityFamily",
    "HarmogramChartDomain",
    "HarmogramTraceFamily",
    "HarmogramIntensityPolicy",
    "HarmogramPolicy",
    "point_set_harmonic_vector",
    "parts_from_zero_aries",
    "zero_aries_parts_harmonic_vector",
    "intensity_function_spectrum",
    "project_harmogram_strength",
    "harmogram_trace",
    "PlanetHeliacalEvent",
    "planet_heliacal_rising",
    "planet_heliacal_setting",
    "planet_acronychal_rising",
    "planet_acronychal_setting",
    # V5 generalized visibility surface
    "HeliacalEventKind",
    "VisibilityTargetKind",
    "LightPollutionClass",
    "LightPollutionDerivationMode",
    "ObserverAid",
    "ObserverVisibilityEnvironment",
    "VisibilityCriterionFamily",
    "VisibilityExtinctionModel",
    "VisibilityTwilightModel",
    "ExtinctionCoefficient",
    "MoonlightPolicy",
    "VisibilityPolicy",
    "VisibilitySearchPolicy",
    "LunarCrescentVisibilityClass",
    "LunarCrescentDetails",
    "VisibilityAssessment",
    "GeneralVisibilityEvent",
    "visibility_assessment",
    "visual_limiting_magnitude",
    "visibility_event",
    "KeplerianElements",
    "DistanceExtremes",
    "CalendarDateTime",
    "DeltaTPolicy",
    "julian_day",
    "calendar_from_jd",
    "calendar_datetime_from_jd",
    "jd_from_datetime",
    "datetime_from_jd",
    "format_jd_utc",
    "safe_datetime_from_jd",
    "greenwich_mean_sidereal_time",
    "local_sidereal_time",
    "delta_t",
    "orbital_elements_at",
    "distance_extremes_at",
    "ayanamsa",
    "tropical_to_sidereal",
    "sidereal_to_tropical",
    "list_ayanamsa_systems",
    "__version__",
    "__author__",
]
