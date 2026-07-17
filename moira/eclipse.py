"""
Moira — eclipse.py
Eclipse Engine: governs high-precision eclipse prediction, classification, and
contact solving for both solar and lunar events.

Archetype: Engine (Eclipse Engine)

Purpose:
    Provides the authoritative Moira eclipse surface: eclipse geometry snapshots,
    event search (next/previous solar and lunar eclipses), contact-time solving,
    and observer-specific local circumstances. All results are derived from
    Moira's DE441-backed ephemeris under the native TT-based event model.

Boundary:
    Owns: eclipse geometry computation, instantaneous solar Besselian-element
    assembly, eclipse classification, event search (lunar and solar), contact
    solving dispatch, observer local circumstances assembly, Saros/Metonic
    cycle indexing, Galactic Center and Aubrey stone positioning.
    Delegates: raw planet/node vector computation (moira.planets, moira.nodes),
    time-scale conversion (moira.julian), eclipse geometry primitives
    (moira.eclipse_geometry), search refinement (moira.eclipse_search), canon
    contact solving (moira.eclipse_canon), native contact solving
    (moira.eclipse_contacts), light-time corrections (moira.corrections).

Import-time side effects: None

External dependency assumptions:
    - DE441 SPK kernel must be accessible via moira.spk_reader.get_reader()
      (loaded lazily on first EclipseCalculator method call).
    - SpkReader serves the supported planetary path through Moira's required
      native reader.

Public surface / exports:
    EclipseType, EclipseData, EclipseEvent, LunarEclipseAnalysis,
    LocalContactCircumstances, LunarEclipseLocalCircumstances,
    SolarBodyCircumstances, SolarEclipseLocalCircumstances,
    SolarBesselianElements, SolarEclipsePath, LunarEclipseAnalysisMode,
    EclipseCalculator
"""

from __future__ import annotations


import math
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from numbers import Real

from .constants import Body, J2000
from .eclipse_geometry import (
    EARTH_RADIUS_KM,
    MOON_RADIUS_KM,
    SUN_RADIUS_KM,
    angular_separation as _angular_separation,
    apparent_radius as _apparent_radius,
    lunar_parallax as _parallax,
    penumbra_radius as _penumbra_radius,
    shadow_axis_offset_deg,
    topocentric_near_moon_radius as _topocentric_near_moon_radius,
    umbra_radius as _umbra_radius,
    lunar_penumbral_magnitude,
    lunar_umbral_magnitude,
)
from .eclipse_search import (
    refine_minimum as _refine_minimum,
    refine_lunar_greatest_eclipse as _refine_lunar_maximum,
    refine_solar_greatest_eclipse as _refine_solar_maximum,
)
from .julian import (
    _ut1_to_utc,
    apparent_sidereal_time,
    datetime_from_jd,
    decimal_year_from_jd,
    jd_from_datetime,
    utc_to_ut1,
    ut_to_tt_nasa_canon,
)
from ._ephemeris_time import _reader_identity_at, _ut1_to_ephemeris_tt
from .eclipse_besselian import (
    SolarBesselianElements,
    _SolarShadowAxisState,
    _besselian_elements_from_native_shadow_state,
)
from .planets import (
    _barycentric,
    _earth_barycentric,
    _geocentric,
    planet_at,
    sky_position_at,
)
from .nodes import true_node
from .spk_reader import get_reader, KernelReader, SpkReader
from .phenomena import next_moon_phase
from .transits import last_full_moon, last_new_moon
from .coordinates import (
    icrf_to_true_ecliptic,
    mat_mul,
    mat_vec_mul,
    nutation_matrix_equatorial,
    precession_matrix_equatorial,
)
from .eclipse_canon import (
    DEFAULT_LUNAR_CANON_METHOD,
    LunarCanonContacts,
    find_lunar_contacts_canon,
    lunar_canon_source_model,
    lunar_canon_geometry,
    LunarCanonGeometry,
    LunarCanonMethodId,
    LUNAR_CANON_METHOD_IDS,
)
from .eclipse_contacts import LunarEclipseContacts, find_lunar_contacts
from .corrections import apply_light_time
from .obliquity import nutation, true_obliquity
from .polar_motion import PolarMotionRegistry, polar_motion_matrix
from .geoutils import (
    EARTH_KM_PER_DEG_LAT as _KM_PER_DEG_LAT,
    offset_geographic_km as _offset_geographic_km,
    sample_interval as _sample_interval,
    wrap_longitude_deg as _wrap_longitude_deg,
)

__all__ = [
    "EclipseData", "EclipseEvent", "EclipseType", "EclipseCalculator",
    "EclipseHit",
    "SolarBodyCircumstances", "SolarEclipseLocalCircumstances",
    "LocalContactCircumstances",
    "LunarEclipseAnalysis",
    "LunarEclipseLocalCircumstances",
    "LunarEclipseAnalysisMode",
    "LunarEclipseContacts",
    "LunarCanonContacts",
    "LunarCanonGeometry",
    "find_lunar_contacts",
    "find_lunar_contacts_canon",
    "lunar_canon_geometry",
    "lunar_canon_source_model",
    "DEFAULT_LUNAR_CANON_METHOD",
    "LunarCanonMethodId",
    "LUNAR_CANON_METHOD_IDS",
    "SolarBesselianElements",
    # Phase 3 — path/where geometry vessel (Defer.Design + Defer.Validation)
    "SolarEclipsePath",
    # Observer-specific solar eclipse search
    "next_solar_eclipse_at_location",
    "vertex_name",
    # Constants
    "ECLIPSE_SEASON_THRESHOLD",
    "ECLIPSE_LATITUDE_THRESHOLD",
    "SAROS_SYNODIC_MONTHS",
    "METONIC_PERIOD_DAYS",
    "GALACTIC_CENTER_LON_J2000",
    "PRECESSION_DEG_PER_CENTURY",
    "AUBREY_HOLES",
    "HEPTAGON_SIDES",
    "POSITIONS_PER_SIDE",
    "DEGREES_PER_STONE",
]

# ---------------------------------------------------------------------------
# Astronomical constants
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Eclipse geometry thresholds
# ---------------------------------------------------------------------------

ECLIPSE_SEASON_THRESHOLD  = 18.0   # degrees Sun–Node distance (eclipse window)
ECLIPSE_LATITUDE_THRESHOLD = 2.0   # degrees Moon latitude (grazing limit)

# ---------------------------------------------------------------------------
# Saros / Metonic
# ---------------------------------------------------------------------------

SAROS_SYNODIC_MONTHS = 223         # synodic months in one Saros cycle
METONIC_PERIOD_DAYS  = 6939.6018   # 19 tropical years in days
J2000_DATETIME       = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Galactic Center / Aubrey heptagon
# ---------------------------------------------------------------------------

GALACTIC_CENTER_LON_J2000  = 266.5          # ecliptic longitude at J2000
PRECESSION_DEG_PER_CENTURY  = 1.39688783    # ~50.29″/year
AUBREY_HOLES                = 56            # Stonehenge Aubrey hole count
HEPTAGON_SIDES              = 7
POSITIONS_PER_SIDE          = 8             # 56 / 7
DEGREES_PER_STONE           = 360.0 / AUBREY_HOLES


# ---------------------------------------------------------------------------
# Phase 3 — SolarEclipsePath  (Defer.Design + Defer.Validation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SolarEclipsePath:
    """
    Vessel: The Solar Eclipse Path
    
    Typed vessel for the geographic path of a solar eclipse's central line.

    Initial implemented path vessel.

    Doctrine
    --------
    A solar eclipse path ("where" surface) encodes the geographic track of
    the Moon's umbral (or antumbral) shadow across the Earth's surface.
    It is distinct from the local-circumstances surface
    (:class:`SolarEclipseLocalCircumstances`) which answers "what happens at
    a specific observer location."

    Legacy engines often expose this as raw float arrays indexed by integer
    offsets. This vessel replaces those arrays with named, typed fields.

    Current implementation state
    ----------------------------
    Moira now provides a first numerical path slice:
        - central-eclipse geography from the DE441 lunar-shadow axis
          intersecting the WGS-84 reference ellipsoid
        - sampled central-track geometry between the first and last lawful
          shadow-axis intersections with that ellipsoid
        - central-shadow width as the full cross-track support span of the
          instantaneous cone/ellipsoid footprint
        - partial eclipses represented honestly as a one-point maximum surface

    Validation state
    ----------------
    The current implemented slice is externally checked against named
    NASA/GSFC path products, including the 2015 polar central line, WGS-84
    tangency endpoints, and width at greatest eclipse. This is bounded
    cross-model evidence; full atlas-grade and one-limit/terminator-closure
    validation remain future work.

    Fields
    ------
    central_line_lats : tuple of float
        Geographic latitudes (degrees, north positive) along the central line,
        sampled at equal time intervals from the first to last shadow-axis
        intersection with the WGS-84 ellipsoid. These endpoints are not the
        separate U1/U4 cone tangencies.
    central_line_lons : tuple of float
        Geographic longitudes (degrees, east positive) at the same sample
        points.  Same length as ``central_line_lats``.
    umbral_width_km : float
        Cross-track support width of the umbral (or antumbral) shadow path in
        kilometres at
        maximum eclipse.
    duration_at_max_s : float
        Duration of totality (or annularity) in seconds at the point of
        maximum eclipse.
    max_eclipse_lat : float
        Geographic latitude of the point of greatest eclipse.
    max_eclipse_lon : float
        Geographic longitude of the point of greatest eclipse.
    eclipse_data : EclipseData
        The parent eclipse event from which this path was derived.
    """
    central_line_lats:  tuple
    central_line_lons:  tuple
    umbral_width_km:    float
    duration_at_max_s:  float
    max_eclipse_lat:    float
    max_eclipse_lon:    float
    eclipse_data:       'EclipseData'


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EclipseType:
    """
    RITE: The Eclipse Type Vessel

    THEOREM: Governs the storage of eclipse classification flags and magnitude
    values for a single eclipse event.

    RITE OF PURPOSE:
        EclipseType is the immutable classification record produced by the
        eclipse geometry solver. Without it, callers would have to re-derive
        eclipse kind and magnitude from raw geometry on every access. It is
        consumed by EclipseData and propagated to all higher-level eclipse
        surfaces.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the four mutually-exclusive umbral/central eclipse-kind
              flags (partial, annular, total, hybrid)
            - Carry the umbral and penumbral magnitude scalars
            - Serve a human-readable string representation via __str__
        Non-responsibilities:
            - Computing eclipse geometry
            - Classifying eclipses (delegates to _classify)
        Dependencies:
            - Populated by _classify() in moira.eclipse
        Structural invariants:
            - At most one of is_partial, is_annular, is_total, is_hybrid is
              True. A penumbral-only lunar eclipse has all four False and a
              positive magnitude_penumbra; no-eclipse has both magnitudes zero.
            - magnitude_umbral >= 0.0; magnitude_penumbra >= 0.0

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse.EclipseType",
      "risk": "high",
      "api": {
        "frozen": ["is_partial", "is_annular", "is_total", "is_hybrid",
                   "magnitude_umbral", "magnitude_penumbra"],
        "internal": ["__str__"]
      },
      "state": {"mutable": false, "owners": ["_classify"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    is_partial:         bool
    is_annular:         bool
    is_total:           bool
    is_hybrid:          bool
    magnitude_umbral:   float
    magnitude_penumbra: float

    def __str__(self) -> str:
        if self.is_total:   return "Total"
        if self.is_annular: return "Annular"
        if self.is_hybrid:  return "Hybrid"
        if self.is_partial: return "Partial"
        if self.magnitude_penumbra > 0.0: return "Penumbral"
        return "None"


@dataclass(frozen=True, slots=True)
class EclipseData:
    """
    RITE: The Eclipse Data Vessel

    THEOREM: Governs the complete eclipse geometry snapshot for a single
    Julian Day.

    RITE OF PURPOSE:
        EclipseData is the primary output of EclipseCalculator.calculate_jd().
        It bundles every geometric quantity needed to describe the eclipse
        state at one instant: body longitudes, apparent radii, shadow geometry,
        Aubrey stone positions, cycle indices, and the derived eclipse
        classification. Without it, consumers would need to call multiple
        lower-level functions and assemble results themselves.

    LAW OF OPERATION:
        Responsibilities:
            - Carry all ecliptic positions (Sun, Moon, node, Galactic Center)
            - Carry apparent angular radii and shadow radii
            - Carry Aubrey/heptagonal stone positions
            - Carry Saros and Metonic cycle indices
            - Carry the derived EclipseType classification and magnitude
            - Expose is_eclipse() convenience predicate
        Non-responsibilities:
            - Computing any of the above values (delegates to EclipseCalculator)
            - Persisting or serialising data
        Dependencies:
            - Populated by EclipseCalculator._calculate_jd_internal()
        Structural invariants:
            - eclipse_magnitude >= 0.0
            - sun_stone, moon_stone, node_stone, south_node_stone in [0, 55]
            - sun_side in [0, 6]; sun_pos_in_side in [0, 7]

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse.EclipseData",
      "risk": "high",
      "api": {
        "frozen": ["sun_longitude", "moon_longitude", "node_longitude",
                   "galactic_center_longitude", "moon_latitude",
                   "sun_apparent_radius", "moon_apparent_radius",
                   "moon_distance_km", "earth_shadow_apparent_radius",
                   "earth_penumbra_apparent_radius", "sun_stone", "moon_stone",
                   "node_stone", "south_node_stone", "angular_separation_3d",
                   "solar_topocentric_separation", "sun_node_distance",
                   "is_eclipse_season", "is_solar_eclipse", "is_lunar_eclipse",
                   "eclipse_type", "eclipse_magnitude", "saros_index",
                   "metonic_year", "metonic_is_reset", "moon_parallax",
                   "sun_side", "sun_pos_in_side"],
        "internal": ["is_eclipse", "__str__"]
      },
      "state": {"mutable": false, "owners": ["EclipseCalculator._calculate_jd_internal"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    # Positions
    sun_longitude:               float   # ecliptic longitude, degrees
    moon_longitude:              float
    node_longitude:              float
    galactic_center_longitude:   float   # precession-corrected GC
    moon_latitude:               float   # ecliptic latitude, degrees

    # Apparent angular radii (degrees)
    sun_apparent_radius:         float
    moon_apparent_radius:        float
    moon_distance_km:            float
    earth_shadow_apparent_radius:float
    earth_penumbra_apparent_radius: float

    # Aubrey / heptagonal stone positions (0–55)
    sun_stone:                   int
    moon_stone:                  int
    node_stone:                  int
    south_node_stone:            int

    # Geometry
    angular_separation_3d:       float   # geocentric degrees (Sun–Moon)
    solar_topocentric_separation:float   # Earth-surface estimate; exact when data is localized
    sun_node_distance:           float   # degrees to nearest node

    # Eclipse status
    is_eclipse_season:           bool
    is_solar_eclipse:            bool
    is_lunar_eclipse:            bool
    eclipse_type:                EclipseType
    eclipse_magnitude:           float

    # Cycles
    saros_index:                 float   # position in Saros cycle (0–222)
    metonic_year:                float   # position in 19-year cycle (0–19)
    metonic_is_reset:            bool

    # Parallax
    moon_parallax:               float   # horizontal parallax, degrees

    # Heptagon side
    sun_side:                    int     # 0–6
    sun_pos_in_side:             int     # 0–7

    def is_eclipse(self) -> bool:
        return self.is_solar_eclipse or self.is_lunar_eclipse

    def __str__(self) -> str:
        kind = str(self.eclipse_type)
        if self.is_solar_eclipse:
            return f"Solar Eclipse ({kind}, mag={self.eclipse_magnitude:.3f})"
        if self.is_lunar_eclipse:
            return f"Lunar Eclipse ({kind}, mag={self.eclipse_magnitude:.3f})"
        if self.is_eclipse_season:
            return "Eclipse Season (no eclipse)"
        return "No eclipse"


@dataclass(frozen=True, slots=True)
class EclipseEvent:
    """
    RITE: The Eclipse Event Vessel

    THEOREM: Governs the pairing of a searched eclipse maximum Julian Day with
    its full EclipseData geometry.

    RITE OF PURPOSE:
        EclipseEvent is the unit of exchange returned by all eclipse search
        methods. It binds the UT Julian Day of greatest eclipse to the
        corresponding EclipseData snapshot, giving callers a single object
        that answers both "when?" and "what geometry?". Without it, search
        results and geometry would have to be tracked separately.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the UT1 Julian Day of greatest eclipse (jd_ut)
            - Carry the full EclipseData geometry at that instant
            - Expose a UTC datetime convenience property (datetime_utc)
        Non-responsibilities:
            - Searching for eclipses (delegates to EclipseCalculator)
            - Computing geometry (delegates to EclipseCalculator)
        Dependencies:
            - Populated by EclipseCalculator._search_lunar_eclipse() and
              EclipseCalculator._search_solar_eclipse()

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse.EclipseEvent",
      "risk": "high",
      "api": {
        "frozen": ["jd_ut", "data"],
        "internal": ["datetime_utc"]
      },
      "state": {"mutable": false, "owners": ["EclipseCalculator._search_lunar_eclipse",
                                              "EclipseCalculator._search_solar_eclipse"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    jd_ut: float
    data: EclipseData

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(_ut1_to_utc(self.jd_ut))


LunarEclipseAnalysisMode = str


@dataclass(frozen=True, slots=True)
class LunarEclipseAnalysis:
    """
    RITE: The Lunar Eclipse Analysis Vessel

    THEOREM: Governs the specialist-facing bundle of a lunar eclipse event,
    its contact times, and its source model metadata.

    RITE OF PURPOSE:
        LunarEclipseAnalysis is the rich output of
        EclipseCalculator.analyze_lunar_eclipse(). It combines the searched
        EclipseEvent with the solved contact times and the provenance metadata
        (mode, source model, canon method) needed for downstream display and
        comparison. Without it, callers would have to assemble event, contacts,
        and metadata from three separate calls.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the analysis mode ('native' or 'nasa_compat')
            - Carry the EclipseEvent (greatest eclipse instant + geometry)
            - Carry the contact times (LunarEclipseContacts or LunarCanonContacts)
            - Carry optional gamma (Earth radii) and source model metadata
        Non-responsibilities:
            - Solving contact times (delegates to find_lunar_contacts or
              find_lunar_contacts_canon)
            - Searching for the eclipse event (delegates to EclipseCalculator)
        Dependencies:
            - Populated by EclipseCalculator.analyze_lunar_eclipse()

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse.LunarEclipseAnalysis",
      "risk": "high",
      "api": {
        "frozen": ["mode", "event", "contacts", "gamma_earth_radii",
                   "source_model", "canon_method"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["EclipseCalculator.analyze_lunar_eclipse"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    mode: LunarEclipseAnalysisMode
    event: EclipseEvent
    contacts: LunarEclipseContacts | LunarCanonContacts
    gamma_earth_radii: float | None = None
    source_model: str = "Moira native lunar eclipse model"
    canon_method: str | None = None


@dataclass(frozen=True, slots=True)
class LocalContactCircumstances:
    """
    RITE: The Local Contact Circumstances Vessel

    THEOREM: Governs the observer-specific Moon placement at a single eclipse
    contact instant.

    RITE OF PURPOSE:
        LocalContactCircumstances records the local sky position of the Moon
        at one contact time for a specific observer. It is the atomic unit
        assembled by LunarEclipseLocalCircumstances for each of the up to
        seven contact instants. Without it, observer-facing eclipse reports
        would have no structured way to carry per-contact azimuth, altitude,
        and visibility.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the UT Julian Day of the contact
            - Carry the Moon's topocentric azimuth and altitude at that instant
            - Carry the visibility flag (altitude > 0)
        Non-responsibilities:
            - Computing sky positions (delegates to sky_position_at)
            - Solving contact times (delegates to contact solvers)
        Dependencies:
            - Populated by EclipseCalculator.lunar_local_circumstances()

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse.LocalContactCircumstances",
      "risk": "medium",
      "api": {
        "frozen": ["jd_ut", "azimuth", "altitude", "visible"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["EclipseCalculator.lunar_local_circumstances"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    jd_ut: float
    azimuth: float
    altitude: float
    visible: bool


@dataclass(frozen=True, slots=True)
class LunarEclipseLocalCircumstances:
    """
    RITE: The Lunar Eclipse Local Circumstances Vessel

    THEOREM: Governs the complete set of observer-specific contact circumstances
    for a lunar eclipse.

    RITE OF PURPOSE:
        LunarEclipseLocalCircumstances is the top-level observer report for a
        lunar eclipse at a given geographic location. It bundles the full
        LunarEclipseAnalysis with the observer's coordinates and a
        LocalContactCircumstances record for each available contact (P1, U1,
        U2, U3, U4, P4, and greatest). Without it, callers would have to
        assemble per-contact sky positions manually from raw contact times.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the parent LunarEclipseAnalysis
            - Carry the observer's latitude, longitude, and elevation
            - Carry LocalContactCircumstances for greatest eclipse and each
              available contact (None when a contact does not occur)
        Non-responsibilities:
            - Computing sky positions (delegates to sky_position_at)
            - Solving contact times (delegates to contact solvers)
        Dependencies:
            - Populated by EclipseCalculator.lunar_local_circumstances()

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse.LunarEclipseLocalCircumstances",
      "risk": "medium",
      "api": {
        "frozen": ["analysis", "latitude", "longitude", "elevation_m",
                   "greatest", "p1", "u1", "u2", "u3", "u4", "p4"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["EclipseCalculator.lunar_local_circumstances"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    analysis: LunarEclipseAnalysis
    latitude: float
    longitude: float
    elevation_m: float
    greatest: LocalContactCircumstances
    p1: LocalContactCircumstances | None = None
    u1: LocalContactCircumstances | None = None
    u2: LocalContactCircumstances | None = None
    u3: LocalContactCircumstances | None = None
    u4: LocalContactCircumstances | None = None
    p4: LocalContactCircumstances | None = None


@dataclass(frozen=True, slots=True)
class SolarBodyCircumstances:
    """
    RITE: The Solar Body Circumstances Vessel

    THEOREM: Governs the observer-specific apparent sky placement of the Sun
    or Moon at a solar eclipse instant.

    RITE OF PURPOSE:
        SolarBodyCircumstances is the atomic sky-position record for one body
        (Sun or Moon) at the solar eclipse maximum as seen from a specific
        observer. It is used in pairs inside SolarEclipseLocalCircumstances.
        Without it, the solar local circumstances vessel would have no
        structured way to carry per-body azimuth, altitude, and visibility.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the body's topocentric azimuth and altitude
            - Carry the visibility flag (altitude > 0)
        Non-responsibilities:
            - Computing sky positions (delegates to sky_position_at)
        Dependencies:
            - Populated by EclipseCalculator.solar_local_circumstances()

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse.SolarBodyCircumstances",
      "risk": "medium",
      "api": {
        "frozen": ["azimuth", "altitude", "visible"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["EclipseCalculator.solar_local_circumstances"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    azimuth: float
    altitude: float
    visible: bool


@dataclass(frozen=True, slots=True)
class SolarEclipseLocalCircumstances:
    """
    RITE: The Solar Eclipse Local Circumstances Vessel

    THEOREM: Governs the complete observer-specific circumstances for a solar
    eclipse maximum.

    RITE OF PURPOSE:
        SolarEclipseLocalCircumstances is the top-level observer report for a
        solar eclipse at a given geographic location. It bundles the searched
        EclipseEvent with the observer's coordinates, the apparent sky
        positions of both the Sun and Moon, the topocentric angular separation,
        and the overlap flag. Without it, callers would have to assemble all
        these quantities from separate calls.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the parent EclipseEvent (global maximum)
            - Carry the observer's latitude, longitude, and elevation
            - Carry SolarBodyCircumstances for both Sun and Moon
            - Carry the topocentric angular separation and overlap flag
        Non-responsibilities:
            - Computing sky positions (delegates to sky_position_at)
            - Searching for the eclipse event (delegates to EclipseCalculator)
        Dependencies:
            - Populated by EclipseCalculator.solar_local_circumstances()

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse.SolarEclipseLocalCircumstances",
      "risk": "medium",
      "api": {
        "frozen": ["event", "latitude", "longitude", "elevation_m",
                   "sun", "moon", "topocentric_separation_deg",
                   "topocentric_overlap"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["EclipseCalculator.solar_local_circumstances"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    event: EclipseEvent
    latitude: float
    longitude: float
    elevation_m: float
    sun: SolarBodyCircumstances
    moon: SolarBodyCircumstances
    topocentric_separation_deg: float
    topocentric_overlap: bool


@dataclass(frozen=True, slots=True)
class EclipseHit:
    """A single eclipse-to-natal contact: one eclipse touching one natal point.

    ``eclipse_longitude`` is the active degree of the eclipse — the
    Sun/Moon conjunction degree for solar eclipses, and whichever axis end
    (Moon or opposition Sun) triggered the match for lunar eclipses.
    ``orb`` is the actual angular separation in degrees (≤ the requested orb).
    """

    event: "EclipseEvent"
    eclipse_longitude: float
    eclipse_kind: str        # "solar" | "lunar"
    target_name: str
    target_longitude: float
    orb: float


# ---------------------------------------------------------------------------
# Main calculator
# ---------------------------------------------------------------------------

class EclipseCalculator:
    """
    RITE: The Eclipse Engine

    THEOREM: Governs high-precision eclipse prediction, classification, and
    contact solving backed by Moira's DE441 ephemeris.

    RITE OF PURPOSE:
        EclipseCalculator is the primary public entry point for all eclipse
        computation in Moira. It owns the full pipeline from a Julian Day or
        datetime input to a classified EclipseData snapshot, and from a search
        seed to a fully resolved EclipseEvent with contact times and observer
        circumstances. Without it, no higher-level pillar could obtain eclipse
        predictions or local circumstances without re-implementing the entire
        DE441-backed geometry and search machinery.

    LAW OF OPERATION:
        Responsibilities:
            - Compute complete eclipse geometry snapshots (calculate, calculate_jd)
            - Express the native solar shadow as instantaneous Besselian elements
            - Search for next/previous lunar and solar eclipses
            - Produce specialist-facing LunarEclipseAnalysis bundles
            - Solve observer-specific local circumstances for lunar and solar
              eclipses
            - Cache search results to avoid redundant lunation walks
        Non-responsibilities:
            - Raw planet/node vector computation (delegates to moira.planets,
              moira.nodes)
            - Eclipse geometry primitives (delegates to moira.eclipse_geometry)
            - Besselian coordinate semantics (delegates to
              moira.eclipse_besselian)
            - Search refinement numerics (delegates to moira.eclipse_search)
            - Canon contact solving (delegates to moira.eclipse_canon)
            - Native contact solving (delegates to moira.eclipse_contacts)
        Dependencies:
            - SpkReader (DE441 kernel access via moira.spk_reader)
            - moira.planets, moira.nodes, moira.julian, moira.coordinates
            - moira.eclipse_geometry, moira.eclipse_search
            - moira.eclipse_canon, moira.eclipse_contacts
            - moira.corrections (light-time)
        Behavioral invariants:
            - Native search results are the primary Moira truth surface
            - Eclipse event geometry is solved in TT and reported in UT
            - Compatibility paths (nasa_compat) are isolated from the native
              event model and must not alter native search results

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.eclipse.EclipseCalculator",
      "risk": "critical",
      "api": {
        "frozen": ["calculate", "calculate_jd", "solar_besselian_elements",
                   "next_lunar_eclipse",
                   "previous_lunar_eclipse", "next_lunar_eclipse_canon",
                   "previous_lunar_eclipse_canon", "analyze_lunar_eclipse",
                   "lunar_local_circumstances", "solar_local_circumstances",
                   "next_solar_eclipse", "previous_solar_eclipse"],
        "internal": ["_calculate_jd_internal", "_lunar_shadow_axis_distance_km",
                     "_refine_lunar_maximum_for_kind", "_lunar_shadow_geometry_tt",
                     "_native_solar_conjunction_distance_deg",
                     "_native_solar_shadow_axis_state_tt",
                     "_native_lunar_event_geometry_tt", "_lunar_event_geometry_ut",
                     "_search_lunar_eclipse", "_search_solar_eclipse"]
      },
      "state": {
        "mutable": true,
        "owners": ["__init__"],
        "fields": ["_reader", "_lunar_search_cache", "_solar_search_cache"]
      },
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(self, reader: KernelReader | None = None) -> None:
        """
        Initialise the Eclipse Engine with an optional SpkReader.

        Parameters
        ----------
        reader : SpkReader instance to use for all ephemeris lookups.
            When None, the module-level singleton returned by get_reader()
            is used (lazy-loaded on first access).

        Side effects:
            - Initialises empty lunar and solar search caches
              (_lunar_search_cache, _solar_search_cache).
        """
        self._reader = reader or get_reader()
        self._lunar_search_cache: dict[
            tuple[float, bool, int, bool, str], EclipseEvent
        ] = {}
        self._solar_search_cache: dict[
            tuple[float, bool, int | None, str], EclipseEvent
        ] = {}

    def _jd_tt_from_ut(
        self,
        jd_ut: float,
        *,
        delta_t_mode: str = "native",
    ) -> float:
        if delta_t_mode == "native":
            return _ut1_to_ephemeris_tt(jd_ut, self._reader)
        if delta_t_mode == "nasa_canon":
            year_hint = decimal_year_from_jd(jd_ut)
            return ut_to_tt_nasa_canon(jd_ut, year_hint)
        raise ValueError(f"Unsupported delta_t_mode: {delta_t_mode!r}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate(self, dt: datetime) -> EclipseData:
        """
        Compute geometric eclipse geometry for a given UTC datetime.

        Parameters
        ----------
        dt : timezone-aware datetime

        Returns
        -------
        EclipseData with all positions, eclipse status, and cycle data.

        Notes
        -----
        This surface uses the geometric Moon path for lunar geometry.
        Native lunar maximum search uses a different event model for umbral
        and partial eclipses; use :meth:`calculate_lunar_event_jd` when you
        need that explicit native event geometry.
        """
        return self.calculate_jd(utc_to_ut1(jd_from_datetime(dt)))

    def _calculate_jd_internal(
        self,
        jd: float,
        *,
        retarded_moon: bool = False,
        delta_t_mode: str = "native",
    ) -> EclipseData:
        """Internal eclipse calculation with selectable lunar event geometry."""
        jd_tt = self._jd_tt_from_ut(jd, delta_t_mode=delta_t_mode)

        sun_xyz = _geocentric(Body.SUN, jd_tt, self._reader)
        if retarded_moon:
            earth_ssb = _earth_barycentric(jd_tt, self._reader)
            moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, self._reader, earth_ssb, _barycentric)
        else:
            moon_xyz = _geocentric(Body.MOON, jd_tt, self._reader)
        sun_lon, sun_lat, sun_dist = icrf_to_true_ecliptic(jd_tt, sun_xyz)
        moon_lon, moon_lat, moon_dist = icrf_to_true_ecliptic(jd_tt, moon_xyz)
        node_data = true_node(jd, reader=self._reader, jd_tt=jd_tt)

        node_lon = node_data.longitude
        moon_parallax = _parallax(moon_dist)
        sun_radius = _apparent_radius(SUN_RADIUS_KM, sun_dist)
        moon_radius = _apparent_radius(MOON_RADIUS_KM, moon_dist)
        earth_shadow_radius = _umbra_radius(sun_dist, moon_dist)
        penumbra_radius = _penumbra_radius(sun_dist, moon_dist)
        angular_sep = _angular_separation(sun_lon, sun_lat, moon_lon, moon_lat)
        gc_lon = _galactic_center_lon_jd(jd)
        sun_stone = _to_stone(sun_lon, gc_lon)
        moon_stone = _to_stone(moon_lon, gc_lon)
        node_stone = _to_stone(node_lon, gc_lon)
        south_node_stone = _to_stone((node_lon + 180.0) % 360.0, gc_lon)
        sun_side = sun_stone // POSITIONS_PER_SIDE
        sun_pos_in_side = sun_stone % POSITIONS_PER_SIDE

        sun_node_dist = abs(sun_lon - node_lon) % 360.0
        if sun_node_dist > 180.0:
            sun_node_dist = 360.0 - sun_node_dist
        sun_node_dist = min(sun_node_dist, abs(180.0 - sun_node_dist))
        is_season = sun_node_dist < ECLIPSE_SEASON_THRESHOLD
        native_lunar_axis_km = None
        native_lunar_moon_radius_km = None
        native_lunar_umbra_radius_km = None
        native_lunar_penumbra_radius_km = None
        native_solar_axis_km = None
        native_solar_center_sun_radius = None
        native_solar_center_moon_radius = None
        native_solar_surface_sun_radius = None
        native_solar_surface_moon_radius = None
        if abs(angular_sep - 180.0) < 1.5:
            (
                native_lunar_axis_km,
                native_lunar_moon_radius_km,
                native_lunar_umbra_radius_km,
                native_lunar_penumbra_radius_km,
                _,
            ) = self._native_lunar_event_geometry_tt(
                jd_tt,
                retarded_moon=retarded_moon,
            )
        elif angular_sep < 1.5:
            (
                native_solar_axis_km,
                native_solar_center_sun_radius,
                native_solar_center_moon_radius,
                native_solar_surface_sun_radius,
                native_solar_surface_moon_radius,
            ) = self._native_solar_shadow_geometry_tt(jd_tt)
        eclipse_type, is_solar, is_lunar, magnitude = _classify(
            angular_sep,
            moon_lat,
            sun_node_dist,
            sun_radius,
            moon_radius,
            earth_shadow_radius,
            penumbra_radius,
            moon_parallax,
            native_lunar_axis_km=native_lunar_axis_km,
            native_lunar_moon_radius_km=native_lunar_moon_radius_km,
            native_lunar_umbra_radius_km=native_lunar_umbra_radius_km,
            native_lunar_penumbra_radius_km=native_lunar_penumbra_radius_km,
            native_solar_axis_km=native_solar_axis_km,
            native_solar_center_sun_radius=native_solar_center_sun_radius,
            native_solar_center_moon_radius=native_solar_center_moon_radius,
            native_solar_surface_sun_radius=native_solar_surface_sun_radius,
            native_solar_surface_moon_radius=native_solar_surface_moon_radius,
        )
        saros_idx = _saros_index_jd(jd)
        metonic_year, m_reset = _metonic_position_jd(jd, sun_lon, moon_lon)

        # ``EclipseData`` predates observer-specific result vessels and retains
        # this frozen field name for compatibility.  For a solar snapshot the
        # value is the deterministic minimum separation estimate at Earth's
        # near-side surface; observer products replace it with their solved
        # topocentric separation.  Outside a solar conjunction it remains the
        # geocentric separation and carries no topocentric claim.
        solar_surface_separation = (
            max(0.0, angular_sep - moon_parallax)
            if angular_sep < 1.5
            else angular_sep
        )

        return EclipseData(
            sun_longitude=sun_lon,
            moon_longitude=moon_lon,
            node_longitude=node_lon,
            galactic_center_longitude=gc_lon,
            moon_latitude=moon_lat,
            sun_apparent_radius=sun_radius,
            moon_apparent_radius=moon_radius,
            moon_distance_km=moon_dist,
            earth_shadow_apparent_radius=earth_shadow_radius,
            earth_penumbra_apparent_radius=penumbra_radius,
            sun_stone=sun_stone,
            moon_stone=moon_stone,
            node_stone=node_stone,
            south_node_stone=south_node_stone,
            angular_separation_3d=angular_sep,
            solar_topocentric_separation=solar_surface_separation,
            sun_node_distance=sun_node_dist,
            is_eclipse_season=is_season,
            is_solar_eclipse=is_solar,
            is_lunar_eclipse=is_lunar,
            eclipse_type=eclipse_type,
            eclipse_magnitude=magnitude,
            saros_index=saros_idx,
            metonic_year=metonic_year,
            metonic_is_reset=m_reset,
            moon_parallax=moon_parallax,
            sun_side=sun_side,
            sun_pos_in_side=sun_pos_in_side,
        )

    def _lunar_shadow_axis_distance_km(
        self,
        jd_ut: float,
        *,
        retarded_moon: bool = True,
        delta_t_mode: str = "native",
    ) -> float:
        """
        Geometric distance from the Moon's center to the Earth's shadow axis.

        This is the physically relevant quantity for lunar greatest eclipse and
        is the native search objective for Moira's lunar event model.

        This native objective is intentionally not redefined to match a catalog
        compatibility surface.
        """
        jd_tt = self._jd_tt_from_ut(jd_ut, delta_t_mode=delta_t_mode)
        earth_ssb = _earth_barycentric(jd_tt, self._reader)
        # The shadow axis is set by the retarded direction to the Sun, not by
        # observer-facing apparent corrections and not by the instantaneous
        # geometric Sun vector.
        sun_xyz, _ = apply_light_time(Body.SUN, jd_tt, self._reader, earth_ssb, _barycentric)
        if retarded_moon:
            # Greatest eclipse is observed from Earth. Using the retarded Moon
            # direction materially improves event centering for umbral events.
            moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, self._reader, earth_ssb, _barycentric)
        else:
            moon_xyz = _geocentric(Body.MOON, jd_tt, self._reader)
        sun_norm = math.sqrt(sum(v * v for v in sun_xyz))
        axis_unit = tuple(-v / sun_norm for v in sun_xyz)
        axis_proj = sum(moon_xyz[i] * axis_unit[i] for i in range(3))
        perp = [moon_xyz[i] - axis_proj * axis_unit[i] for i in range(3)]
        return math.sqrt(sum(v * v for v in perp))

    def _refine_lunar_maximum_for_kind(
        self,
        center_jd: float,
        kind: str,
        *,
        delta_t_mode: str = "native",
    ) -> float:
        """Refine the lunar greatest-eclipse JD for the given eclipse kind."""
        use_retarded_moon = kind != "penumbral"
        return _refine_minimum(
            lambda jd: self._lunar_shadow_axis_distance_km(
                jd,
                retarded_moon=use_retarded_moon,
                delta_t_mode=delta_t_mode,
            ),
            center_jd,
            window_days=0.125,
            tol_days=1e-7,
            max_iter=100,
        )

    def _lunar_shadow_geometry_tt(
        self,
        jd_tt: float,
    ) -> tuple[float, float, float, float, float]:
        """
        Return lunar eclipse geometry in physical units at TT:
        (axis_distance_km, moon_distance_km, moon_radius_deg,
         umbra_radius_deg, penumbra_radius_deg)
        """
        sun_xyz = _geocentric(Body.SUN, jd_tt, self._reader)
        moon_xyz = _geocentric(Body.MOON, jd_tt, self._reader)
        sun_lon, sun_lat, sun_dist = icrf_to_true_ecliptic(jd_tt, sun_xyz)
        moon_lon, moon_lat, moon_dist = icrf_to_true_ecliptic(jd_tt, moon_xyz)
        moon_radius = _apparent_radius(MOON_RADIUS_KM, moon_dist)
        umbra_radius = _umbra_radius(sun_dist, moon_dist)
        penumbra_radius = _penumbra_radius(sun_dist, moon_dist)
        sun_norm = math.sqrt(sum(v * v for v in sun_xyz))
        axis_unit = tuple(-v / sun_norm for v in sun_xyz)
        axis_proj = sum(moon_xyz[i] * axis_unit[i] for i in range(3))
        perp = [moon_xyz[i] - axis_proj * axis_unit[i] for i in range(3)]
        axis_km = math.sqrt(sum(v * v for v in perp))
        return axis_km, moon_dist, moon_radius, umbra_radius, penumbra_radius

    def _native_solar_conjunction_distance_deg(
        self,
        jd_ut: float,
        *,
        retarded_moon: bool = True,
    ) -> float:
        """
        Return the native solar-event conjunction objective at UT.

        Native solar search uses the Earth-observed Moon when centering the
        global event.
        """
        jd_tt = _ut1_to_ephemeris_tt(jd_ut, self._reader)
        sun_xyz = _geocentric(Body.SUN, jd_tt, self._reader)
        if retarded_moon:
            earth_ssb = _earth_barycentric(jd_tt, self._reader)
            moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, self._reader, earth_ssb, _barycentric)
        else:
            moon_xyz = _geocentric(Body.MOON, jd_tt, self._reader)
        sun_lon, sun_lat, _sun_dist = icrf_to_true_ecliptic(jd_tt, sun_xyz)
        moon_lon, moon_lat, _moon_dist = icrf_to_true_ecliptic(jd_tt, moon_xyz)
        return _angular_separation(sun_lon, sun_lat, moon_lon, moon_lat)

    def _native_solar_shadow_axis_state_tt(
        self,
        jd_tt: float,
    ) -> _SolarShadowAxisState:
        """Return the shared Earth-reception solar shadow state at one TT epoch.

        Sun and Moon are both evaluated on the same Earth-reception light
        cone: each target state is taken at the emission epoch whose photons
        arrive at the geocentre at ``jd_tt``.  Stellar aberration is excluded;
        this is a shadow-axis construction, not a rendered sky direction.

        The private immutable state preserves the existing physical ray
        geometry while allowing the Besselian coordinate product to consume
        the identical Sun/Moon states and shadow line.
        """

        earth_ssb = _earth_barycentric(jd_tt, self._reader)
        sun_xyz, _ = apply_light_time(
            Body.SUN,
            jd_tt,
            self._reader,
            earth_ssb,
            _barycentric,
        )
        moon_xyz, _ = apply_light_time(
            Body.MOON,
            jd_tt,
            self._reader,
            earth_ssb,
            _barycentric,
        )
        sun_to_moon = tuple(moon_xyz[i] - sun_xyz[i] for i in range(3))
        axis_norm = math.sqrt(sum(value * value for value in sun_to_moon))
        if axis_norm == 0.0:
            raise ValueError("Sun and Moon centers cannot define a zero-length shadow axis")
        axis_unit = tuple(value / axis_norm for value in sun_to_moon)
        axis_projection = sum(moon_xyz[i] * axis_unit[i] for i in range(3))
        sun_distance = math.sqrt(sum(value * value for value in sun_xyz))
        moon_distance = math.sqrt(sum(value * value for value in moon_xyz))
        center_sun_radius = _apparent_radius(SUN_RADIUS_KM, sun_distance)
        center_moon_radius = _apparent_radius(MOON_RADIUS_KM, moon_distance)

        # The closest point on the ray has parameter ``-axis_projection``.
        # It must lie in the away-from-Sun direction from the Moon.
        if axis_projection >= 0.0:
            return _SolarShadowAxisState(
                sun_xyz_km=sun_xyz,
                moon_xyz_km=moon_xyz,
                axis_unit_away_from_sun=axis_unit,
                axis_projection_km=axis_projection,
                fundamental_plane_point_xyz_km=None,
                axis_distance_km=float("inf"),
                sun_moon_distance_km=axis_norm,
                center_sun_radius_deg=center_sun_radius,
                center_moon_radius_deg=center_moon_radius,
                surface_sun_radius_deg=None,
                surface_moon_radius_deg=None,
            )
        perpendicular = tuple(
            moon_xyz[i] - axis_projection * axis_unit[i]
            for i in range(3)
        )
        axis_distance = math.sqrt(sum(value * value for value in perpendicular))
        if axis_distance > EARTH_RADIUS_KM:
            return _SolarShadowAxisState(
                sun_xyz_km=sun_xyz,
                moon_xyz_km=moon_xyz,
                axis_unit_away_from_sun=axis_unit,
                axis_projection_km=axis_projection,
                fundamental_plane_point_xyz_km=perpendicular,
                axis_distance_km=axis_distance,
                sun_moon_distance_km=axis_norm,
                center_sun_radius_deg=center_sun_radius,
                center_moon_radius_deg=center_moon_radius,
                surface_sun_radius_deg=None,
                surface_moon_radius_deg=None,
            )

        closest_parameter = -axis_projection
        half_chord = math.sqrt(
            max(0.0, EARTH_RADIUS_KM * EARTH_RADIUS_KM - axis_distance * axis_distance)
        )
        surface_moon_distance = closest_parameter - half_chord
        if surface_moon_distance <= MOON_RADIUS_KM:
            raise ArithmeticError("solar shadow ray has no physical near-side Earth intersection")
        surface_sun_distance = axis_norm + surface_moon_distance
        return _SolarShadowAxisState(
            sun_xyz_km=sun_xyz,
            moon_xyz_km=moon_xyz,
            axis_unit_away_from_sun=axis_unit,
            axis_projection_km=axis_projection,
            fundamental_plane_point_xyz_km=perpendicular,
            axis_distance_km=axis_distance,
            sun_moon_distance_km=axis_norm,
            center_sun_radius_deg=center_sun_radius,
            center_moon_radius_deg=center_moon_radius,
            surface_sun_radius_deg=_apparent_radius(
                SUN_RADIUS_KM,
                surface_sun_distance,
            ),
            surface_moon_radius_deg=_apparent_radius(
                MOON_RADIUS_KM,
                surface_moon_distance,
            ),
        )

    def _native_solar_shadow_geometry_tt(
        self,
        jd_tt: float,
    ) -> tuple[float, float, float, float | None, float | None]:
        """Return the established native solar geometry tuple at one TT epoch."""

        state = self._native_solar_shadow_axis_state_tt(jd_tt)
        return (
            state.axis_distance_km,
            state.center_sun_radius_deg,
            state.center_moon_radius_deg,
            state.surface_sun_radius_deg,
            state.surface_moon_radius_deg,
        )

    def solar_besselian_elements(self, jd_ut1: float) -> SolarBesselianElements:
        """Return instantaneous native solar Besselian elements at ``jd_ut1``.

        This method does not search for an eclipse.  It converts the supplied
        UT1 Julian Day to the TT coordinate bound to this calculator's
        content-identified ephemeris, requires that identity to be DE441/LE441,
        constructs the same reception-time shadow axis used by native
        solar-eclipse search, and expresses that line on the conventional
        geocentric fundamental plane.

        The forward lunar shadow ray must point toward Earth's fundamental
        plane.  Epochs around the opposite lunar phase therefore fail
        explicitly rather than returning a coordinate product for a
        non-physical backwards extension of the ray.

        NASA/GSFC governs the Besselian field meanings, orientation, units,
        dynamical-time hour angle, and signed ``l2`` convention.  Moira retains
        its DE441/LE441 positions and spherical mean-limb radii; this is not a
        request for NASA's VSOP87/ELP2000 or ``k1``/``k2`` model.  Readers with
        any other or indeterminate DE/LE identity fail closed.
        """

        if isinstance(jd_ut1, bool) or not isinstance(jd_ut1, Real):
            raise TypeError("jd_ut1 must be a real Julian Day")
        jd_ut1 = float(jd_ut1)
        if not math.isfinite(jd_ut1):
            raise ValueError("jd_ut1 must be finite")

        jd_tt = _ut1_to_ephemeris_tt(jd_ut1, self._reader)
        identity = _reader_identity_at(self._reader, jd_tt)
        if (
            identity is None
            or identity.planetary_ephemeris != "DE441"
            or identity.lunar_ephemeris != "LE441"
        ):
            raise RuntimeError(
                "solar Besselian elements are admitted only for a "
                "content-identified DE441/LE441 reader"
            )
        state = self._native_solar_shadow_axis_state_tt(jd_tt)
        return _besselian_elements_from_native_shadow_state(
            jd_ut1=jd_ut1,
            jd_tt=jd_tt,
            ephemeris=identity.summary_label,
            state=state,
        )

    def _native_solar_shadow_axis_distance_km(self, jd_ut: float) -> float:
        """Return the Earth-centre distance to the reception-time shadow axis."""

        jd_tt = _ut1_to_ephemeris_tt(jd_ut, self._reader)
        return self._native_solar_shadow_geometry_tt(jd_tt)[0]

    def _native_lunar_event_geometry_tt(
        self,
        jd_tt: float,
        *,
        retarded_moon: bool,
    ) -> tuple[float, float, float, float, float]:
        """
        Return native lunar-event geometry in physical units at TT.

        This uses the same shadow-axis policy as native event centering:
        retarded Sun for the shadow axis, and either retarded or geometric Moon
        depending on the native event family being modeled.
        """
        earth_ssb = _earth_barycentric(jd_tt, self._reader)
        sun_xyz, _ = apply_light_time(Body.SUN, jd_tt, self._reader, earth_ssb, _barycentric)
        if retarded_moon:
            moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, self._reader, earth_ssb, _barycentric)
        else:
            moon_xyz = _geocentric(Body.MOON, jd_tt, self._reader)

        sun_dist = math.sqrt(sum(v * v for v in sun_xyz))
        moon_dist = math.sqrt(sum(v * v for v in moon_xyz))
        moon_radius_deg = _apparent_radius(MOON_RADIUS_KM, moon_dist)
        umbra_radius_deg = _umbra_radius(sun_dist, moon_dist)
        penumbra_radius_deg = _penumbra_radius(sun_dist, moon_dist)

        axis_unit = tuple(-v / sun_dist for v in sun_xyz)
        axis_proj = sum(moon_xyz[i] * axis_unit[i] for i in range(3))
        perp = [moon_xyz[i] - axis_proj * axis_unit[i] for i in range(3)]
        axis_km = math.sqrt(sum(v * v for v in perp))

        moon_radius_km = math.radians(moon_radius_deg) * moon_dist
        umbra_radius_km = math.radians(umbra_radius_deg) * moon_dist
        penumbra_radius_km = math.radians(penumbra_radius_deg) * moon_dist
        return axis_km, moon_radius_km, umbra_radius_km, penumbra_radius_km, moon_dist

    def _lunar_event_geometry_ut(
        self,
        jd_ut: float,
        *,
        retarded_moon: bool,
        delta_t_mode: str = "native",
    ) -> tuple[float, float, float, float, float]:
        """
        Return native lunar-event geometry in physical units at UT.

        The returned values are all derived from the same Sun/Moon vector policy
        so native contact solving does not mix retarded and geometric lunar
        quantities in one event model.
        """
        jd_tt = self._jd_tt_from_ut(jd_ut, delta_t_mode=delta_t_mode)
        (
            axis_km,
            moon_radius_km,
            umbra_radius_km,
            penumbra_radius_km,
            moon_dist,
        ) = self._native_lunar_event_geometry_tt(
            jd_tt,
            retarded_moon=retarded_moon,
        )
        return axis_km, moon_radius_km, umbra_radius_km, penumbra_radius_km, moon_dist

    def calculate_jd(self, jd: float) -> EclipseData:
        """
        Compute geometric eclipse geometry for a given UT Julian Day.

        For lunar events this uses the geometric Moon path. Native lunar
        greatest-eclipse search uses retarded-Moon geometry for umbral and
        partial event centering; that distinct model is exposed separately via
        :meth:`calculate_lunar_event_jd`.
        """
        return self._calculate_jd_internal(jd, retarded_moon=False)

    def calculate_lunar_event_jd(
        self,
        jd: float,
        *,
        kind: str = "umbral",
        delta_t_mode: str = "native",
    ) -> EclipseData:
        """
        Compute native lunar-event geometry for a given UT Julian Day.

        Parameters
        ----------
        jd : float
            Julian Day (UT) of the event instant to evaluate.
        kind : str
            Native lunar event family. ``"umbral"`` uses the retarded Moon
            path used for umbral and partial greatest-eclipse centering;
            ``"penumbral"`` uses the geometric Moon path used for penumbral
            native search.
        delta_t_mode : str
            Delta-T conversion policy forwarded to the internal TT conversion.
        """
        kind_key = kind.strip().lower().replace("-", "_").replace(" ", "_")
        if kind_key not in {"umbral", "penumbral"}:
            raise ValueError(
                f"Unsupported native lunar event kind: {kind!r}. "
                "Expected 'umbral' or 'penumbral'."
            )
        return self._calculate_jd_internal(
            jd,
            retarded_moon=(kind_key == "umbral"),
            delta_t_mode=delta_t_mode,
        )

    def next_lunar_eclipse(
        self,
        jd_start: float,
        kind: str = "any",
    ) -> EclipseEvent:
        """Return the next lunar eclipse maximum after *jd_start*."""
        return self._search_lunar_eclipse(jd_start, kind=kind, backward=False)

    def previous_lunar_eclipse(
        self,
        jd_start: float,
        kind: str = "any",
    ) -> EclipseEvent:
        """Return the previous lunar eclipse maximum before *jd_start*."""
        return self._search_lunar_eclipse(jd_start, kind=kind, backward=True)

    def next_lunar_eclipse_canon(
        self,
        jd_start: float,
        kind: str = "any",
    ) -> EclipseEvent:
        """Return the next lunar eclipse using the NASA-style canon timing path."""
        return self._search_lunar_eclipse(jd_start, kind=kind, backward=False, use_canon=True)

    def previous_lunar_eclipse_canon(
        self,
        jd_start: float,
        kind: str = "any",
    ) -> EclipseEvent:
        """Return the previous lunar eclipse using the NASA-style canon timing path."""
        return self._search_lunar_eclipse(jd_start, kind=kind, backward=True, use_canon=True)

    def analyze_lunar_eclipse(
        self,
        jd_start: float,
        *,
        kind: str = "any",
        backward: bool = False,
        mode: LunarEclipseAnalysisMode = "native",
    ) -> LunarEclipseAnalysis:
        """
        Return a specialist-facing lunar eclipse analysis bundle.

        Parameters
        ----------
        jd_start : search seed in UT Julian Day
        kind     : eclipse kind selector ('any', 'total', 'partial', 'penumbral')
        backward : search previous instead of next
        mode     : 'native' for Moira's DE441-centric event model or
                   'nasa_compat' for the catalog-facing compatibility path
        """
        if mode == "native":
            event = self._search_lunar_eclipse(jd_start, kind=kind, backward=backward, use_canon=False)
            contacts = find_lunar_contacts(self, event.jd_ut)
            return LunarEclipseAnalysis(
                mode=mode,
                event=event,
                contacts=contacts,
                gamma_earth_radii=None,
                source_model="Moira native lunar eclipse model",
            )

        if mode == "nasa_compat":
            event = self._search_lunar_eclipse(jd_start, kind=kind, backward=backward, use_canon=True)
            contacts = find_lunar_contacts_canon(
                self,
                event.jd_ut,
                method=DEFAULT_LUNAR_CANON_METHOD,
            )
            geom = lunar_canon_geometry(
                self,
                ut_to_tt_nasa_canon(
                    event.jd_ut,
                    decimal_year_from_jd(event.jd_ut),
                ),
                method=DEFAULT_LUNAR_CANON_METHOD,
            )
            return LunarEclipseAnalysis(
                mode=mode,
                event=event,
                contacts=contacts,
                gamma_earth_radii=geom.gamma_earth_radii,
                source_model=lunar_canon_source_model(DEFAULT_LUNAR_CANON_METHOD),
                canon_method=DEFAULT_LUNAR_CANON_METHOD,
            )

        raise ValueError(f"Unsupported lunar eclipse analysis mode: {mode!r}")

    def lunar_local_circumstances(
        self,
        jd_start: float,
        latitude: float,
        longitude: float,
        *,
        elevation_m: float = 0.0,
        kind: str = "any",
        backward: bool = False,
        mode: LunarEclipseAnalysisMode = "native",
    ) -> LunarEclipseLocalCircumstances:
        """
        Return observer-specific lunar eclipse circumstances for a location.

        This packages the Moon's apparent local sky position at greatest
        eclipse and at each available contact.
        """
        _validate_observer_inputs(latitude, longitude, elevation_m)
        analysis = self.analyze_lunar_eclipse(
            jd_start,
            kind=kind,
            backward=backward,
            mode=mode,
        )

        def local_contact(jd_ut: float | None) -> LocalContactCircumstances | None:
            if jd_ut is None:
                return None
            moon = sky_position_at(
                Body.MOON,
                jd_ut,
                latitude,
                longitude,
                elevation_m,
                reader=self._reader,
            )
            return LocalContactCircumstances(
                jd_ut=jd_ut,
                azimuth=moon.azimuth,
                altitude=moon.altitude,
                visible=moon.altitude > 0.0,
            )

        contacts = analysis.contacts
        if mode == "native":
            return LunarEclipseLocalCircumstances(
                analysis=analysis,
                latitude=latitude,
                longitude=longitude,
                elevation_m=elevation_m,
                greatest=local_contact(analysis.event.jd_ut),
                p1=local_contact(contacts.p1),
                u1=local_contact(contacts.u1),
                u2=local_contact(contacts.u2),
                u3=local_contact(contacts.u3),
                u4=local_contact(contacts.u4),
                p4=local_contact(contacts.p4),
            )

        return LunarEclipseLocalCircumstances(
            analysis=analysis,
            latitude=latitude,
            longitude=longitude,
            elevation_m=elevation_m,
            greatest=local_contact(analysis.event.jd_ut),
            p1=local_contact(contacts.p1_ut),
            u1=local_contact(contacts.u1_ut),
            u2=local_contact(contacts.u2_ut),
            u3=local_contact(contacts.u3_ut),
            u4=local_contact(contacts.u4_ut),
            p4=local_contact(contacts.p4_ut),
        )

    def solar_local_circumstances(
        self,
        jd_start: float,
        latitude: float,
        longitude: float,
        *,
        elevation_m: float = 0.0,
        kind: str = "any",
        backward: bool = False,
    ) -> SolarEclipseLocalCircumstances:
        """
        Return observer-specific local sky circumstances for a solar eclipse.

        This is intentionally anchored to the searched global maximum event.
        It exposes the local apparent Sun/Moon placement and overlap state at
        that instant, which is the minimal first-class observer surface needed
        for a specialist eclipse subsystem. The nested ``event`` retains its
        global data coherently; observer-specific separation and overlap live
        on this circumstances vessel. Use
        :meth:`next_solar_eclipse_at_location` for a locally classified event.
        """
        _validate_observer_inputs(latitude, longitude, elevation_m)
        event = self._search_solar_eclipse(jd_start, kind=kind, backward=backward)
        sun = sky_position_at(
            Body.SUN,
            event.jd_ut,
            latitude,
            longitude,
            elevation_m,
            reader=self._reader,
        )
        moon = sky_position_at(
            Body.MOON,
            event.jd_ut,
            latitude,
            longitude,
            elevation_m,
            reader=self._reader,
        )
        separation = _angular_separation(
            sun.right_ascension,
            sun.declination,
            moon.right_ascension,
            moon.declination,
        )
        sun_radius = _apparent_radius(SUN_RADIUS_KM, sun.distance)
        moon_radius = _apparent_radius(MOON_RADIUS_KM, moon.distance)
        overlap = separation < (sun_radius + moon_radius)

        return SolarEclipseLocalCircumstances(
            event=event,
            latitude=latitude,
            longitude=longitude,
            elevation_m=elevation_m,
            sun=SolarBodyCircumstances(
                azimuth=sun.azimuth,
                altitude=sun.altitude,
                visible=sun.altitude > 0.0,
            ),
            moon=SolarBodyCircumstances(
                azimuth=moon.azimuth,
                altitude=moon.altitude,
                visible=moon.altitude > 0.0,
            ),
            topocentric_separation_deg=separation,
            topocentric_overlap=overlap,
        )

    def next_solar_eclipse_at_location(
        self,
        jd_start: float,
        latitude: float,
        longitude: float,
        *,
        elevation_m: float = 0.0,
        kind: str = "any",
        max_lunations: int = 360,
    ) -> SolarEclipseLocalCircumstances:
        """Return local sky circumstances for the next solar eclipse visible at *latitude*, *longitude*.

        Methodology (independently derived):
            1. Iterate over new-moon lunations via the Moon's synodic phase
               angle (Meeus, *Astronomical Algorithms* 2nd ed., Ch. 49).
            2. Check eclipse-season eligibility: Sun–node distance < 18°
               threshold derived from the Earth's shadow-cone geometry
               (Seidelmann, *Explanatory Supplement*, §9.4).
            3. Locate the global maximum with bounded minimization of the
               physical lunar-shadow-axis distance from Earth's centre
               (``eclipse_search.refine_solar_greatest_eclipse``).
            4. Scan a ±4-hour window around the global shadow-axis maximum in
               12-minute steps, computing the full topocentric Sun–Moon
               separation via ``sky_position_at`` (8-step IAU/SOFA
               apparent-position pipeline backed by DE441).
            5. Refine the local minimum with adaptive ternary/grid search
               (``eclipse_search.refine_minimum``).

        Unlike ``solar_local_circumstances``, which always anchors to the next
        *global* eclipse maximum (which may be invisible from the observer's
        location), this method iterates eclipse candidates and accepts one only
        when the refined local instant has both positive disk overlap and a
        positive solar altitude.

        For each candidate global eclipse the method scans a ±4-hour window
        around the global maximum in 12-minute steps, retaining only
        time-steps where the Sun is above the horizon. If at least one such
        step is found, the step with the smallest topocentric Sun–Moon
        separation is refined to the local sub-second maximum. A daylight
        minimum without actual disk overlap is rejected and the lunation scan
        continues. That refined instant becomes the event time returned.

        Parameters
        ----------
        jd_start : float
            Julian Day (UT) to start searching from.
        latitude : float
            Observer geodetic latitude in degrees (positive north).
        longitude : float
            Observer geodetic longitude in degrees (positive east).
        elevation_m : float
            Observer elevation above the geoid in metres.
        kind : str
            Observer-local eclipse type filter: ``'any'``, ``'total'``,
            ``'annular'``, ``'partial'``, or ``'central'``. ``'hybrid'`` is
            necessarily a global path identity; it selects a globally hybrid
            event and returns the actual total, annular, or partial type seen
            at this observer.
        max_lunations : int
            Maximum number of new-moon lunations to scan before giving up.
            Default 360 (~30 years).

        Returns
        -------
        SolarEclipseLocalCircumstances
            Local circumstances at the time of local maximum eclipse.

        Raises
        ------
        RuntimeError
            If no visible eclipse of the requested kind is found within
            *max_lunations* lunations.
        """
        _validate_observer_inputs(latitude, longitude, elevation_m)
        if max_lunations <= 0:
            raise ValueError("max_lunations must be > 0")
        kind_key = kind.strip().lower().replace("-", "_").replace(" ", "_")
        if kind_key not in {"any", "total", "annular", "partial", "central", "hybrid"}:
            raise ValueError(f"Unsupported solar eclipse kind: {kind!r}")

        # Scan window: ±4 hours around global shadow-axis maximum in 12-minute steps
        _SCAN_STEP_DAYS = 12.0 / 1440.0   # 12 minutes
        _SCAN_HALF_WINDOW = 4.0 / 24.0    # ±4 hours

        phase_jd = next_moon_phase("New Moon", jd_start, reader=self._reader).jd_ut

        for _ in range(max_lunations):
            phase_data = self.calculate_jd(phase_jd)
            if phase_data.is_eclipse_season:
                best_jd = _refine_solar_maximum(
                    self,
                    phase_jd,
                    tol_days=1.0e-9,
                )
                best_data = self.calculate_jd(best_jd)

                if _matches_solar_local_candidate_kind(best_data, kind_key):
                    # Scan a ±4-hour window around the global shadow-axis maximum
                    t = best_jd - _SCAN_HALF_WINDOW
                    t_end = best_jd + _SCAN_HALF_WINDOW
                    best_local_jd: float | None = None
                    best_local_sep = float("inf")

                    while t <= t_end:
                        sep, _, _ = _topocentric_solar_geometry(
                            self, t, latitude, longitude, elevation_m
                        )
                        if sep < best_local_sep:
                            best_local_sep = sep
                            best_local_jd = t
                        t += _SCAN_STEP_DAYS

                    if best_local_jd is not None and best_local_sep < float("inf"):
                        # Sun was above horizon at some point — refine the local minimum
                        def _local_sep(jd_t: float) -> float:
                            s, _, _ = _topocentric_solar_geometry(
                                self, jd_t, latitude, longitude, elevation_m
                            )
                            return s

                        refined_jd = _refine_minimum(_local_sep, best_local_jd,
                                                     window_days=_SCAN_STEP_DAYS,
                                                     tol_days=1e-6)

                        # Build local circumstances at refined instant
                        sun = sky_position_at(
                            Body.SUN,
                            refined_jd,
                            latitude,
                            longitude,
                            elevation_m,
                            reader=self._reader,
                        )
                        moon = sky_position_at(
                            Body.MOON,
                            refined_jd,
                            latitude,
                            longitude,
                            elevation_m,
                            reader=self._reader,
                        )
                        separation = _angular_separation(
                            sun.right_ascension,
                            sun.declination,
                            moon.right_ascension,
                            moon.declination,
                        )
                        sun_radius = _apparent_radius(SUN_RADIUS_KM, sun.distance)
                        moon_radius = _apparent_radius(MOON_RADIUS_KM, moon.distance)
                        overlap = separation < (sun_radius + moon_radius)
                        refined_data = _local_solar_eclipse_data(
                            self.calculate_jd(refined_jd),
                            sun_distance_km=sun.distance,
                            moon_distance_km=moon.distance,
                            separation_deg=separation,
                        )
                        local_kind_match = (
                            best_data.eclipse_type.is_hybrid
                            and refined_data.is_solar_eclipse
                            if kind_key == "hybrid"
                            else _matches_solar_kind(refined_data, kind_key)
                        )
                        if overlap and sun.altitude > 0.0 and local_kind_match:
                            refined_event = EclipseEvent(jd_ut=refined_jd, data=refined_data)
                            return SolarEclipseLocalCircumstances(
                                event=refined_event,
                                latitude=latitude,
                                longitude=longitude,
                                elevation_m=elevation_m,
                                sun=SolarBodyCircumstances(
                                    azimuth=sun.azimuth,
                                    altitude=sun.altitude,
                                    visible=True,
                                ),
                                moon=SolarBodyCircumstances(
                                    azimuth=moon.azimuth,
                                    altitude=moon.altitude,
                                    visible=moon.altitude > 0.0,
                                ),
                                topocentric_separation_deg=separation,
                                topocentric_overlap=True,
                            )

            phase_jd = next_moon_phase("New Moon", phase_jd + 1.0, reader=self._reader).jd_ut

        raise RuntimeError(
            f"No solar eclipse of kind {kind!r} visible at "
            f"lat={latitude:.3f} lon={longitude:.3f} found within "
            f"{max_lunations} lunations of JD {jd_start:.1f}"
        )

    def solar_eclipse_path(
        self,
        jd_start: float,
        *,
        kind: str = "any",
        backward: bool = False,
        sample_count: int = 9,
    ) -> SolarEclipsePath:
        """
        Return a typed geographic path surface for a searched solar eclipse.

        Central eclipses use the physical DE441 shadow axis and central-shadow
        cone on the WGS-84 reference ellipsoid. Partial eclipses retain the
        topocentric minimum-separation maximum and return a one-point surface
        with zero central width and duration.
        """
        if sample_count < 1:
            raise ValueError("sample_count must be >= 1")

        event = self._search_solar_eclipse(jd_start, kind=kind, backward=backward)
        axis_maximum = _solar_axis_surface_point(self, event.jd_ut)
        classified_central = any(
            (
                event.data.eclipse_type.is_annular,
                event.data.eclipse_type.is_total,
                event.data.eclipse_type.is_hybrid,
            )
        )
        if axis_maximum is None and classified_central:
            raise ArithmeticError(
                "spherical eclipse classification is central but the physical "
                "shadow axis does not intersect the WGS-84 ellipsoid"
            )
        is_central = axis_maximum is not None
        if axis_maximum is None:
            max_lat, max_lon, _ = _solve_solar_greatest_location(self, event.jd_ut)
        else:
            max_lat = axis_maximum.latitude_deg
            max_lon = axis_maximum.longitude_deg
        path_data = _solar_eclipse_data_at_location(
            self,
            event.data,
            event.jd_ut,
            max_lat,
            max_lon,
            central=is_central,
        )

        if not is_central:
            return SolarEclipsePath(
                central_line_lats=(max_lat,),
                central_line_lons=(max_lon,),
                umbral_width_km=0.0,
                duration_at_max_s=0.0,
                max_eclipse_lat=max_lat,
                max_eclipse_lon=max_lon,
                eclipse_data=path_data,
            )

        start_boundary, end_boundary = _solve_solar_central_interval(
            self,
            event.jd_ut,
        )
        lats: list[float] = []
        lons: list[float] = []
        sample_times = _sample_interval(
            start_boundary.jd_ut,
            end_boundary.jd_ut,
            sample_count,
        )
        for index, jd_ut in enumerate(sample_times):
            if len(sample_times) > 1 and index == 0:
                point = start_boundary.point
            elif len(sample_times) > 1 and index == len(sample_times) - 1:
                point = end_boundary.point
            else:
                point = _solar_axis_surface_point(self, jd_ut)
            if point is None:
                raise ArithmeticError(
                    "sampled central-line epoch has no shadow-axis intersection "
                    "with the WGS-84 ellipsoid"
                )
            lats.append(point.latitude_deg)
            lons.append(point.longitude_deg)

        return SolarEclipsePath(
            central_line_lats=tuple(lats),
            central_line_lons=tuple(lons),
            umbral_width_km=_solve_solar_umbral_width_km(self, event.jd_ut),
            duration_at_max_s=_solve_local_solar_central_duration_s(
                self,
                event.jd_ut,
                max_lat,
                max_lon,
            ),
            max_eclipse_lat=max_lat,
            max_eclipse_lon=max_lon,
            eclipse_data=path_data,
        )

    def next_solar_eclipse(
        self,
        jd_start: float,
        kind: str = "any",
    ) -> EclipseEvent:
        """Return the next solar eclipse maximum after *jd_start*."""
        return self._search_solar_eclipse(jd_start, kind=kind, backward=False)

    def previous_solar_eclipse(
        self,
        jd_start: float,
        kind: str = "any",
    ) -> EclipseEvent:
        """Return the previous solar eclipse maximum before *jd_start*."""
        return self._search_solar_eclipse(jd_start, kind=kind, backward=True)

    def _search_lunar_eclipse(
        self,
        jd_start: float,
        *,
        kind: str,
        backward: bool,
        use_canon: bool = False,
        max_lunations: int = 36,
    ) -> EclipseEvent:
        """
        Search successive full moons until a lunar eclipse of the requested kind
        is found, then refine to the eclipse maximum near that full moon.
        """
        kind_key = kind.strip().lower().replace("-", "_").replace(" ", "_")
        if kind_key not in {"any", "total", "partial", "penumbral"}:
            raise ValueError(f"Unsupported lunar eclipse kind: {kind!r}")
        if max_lunations <= 0:
            raise ValueError("max_lunations must be > 0")

        cache_key = (jd_start, backward, max_lunations, use_canon, kind_key)
        cached = self._lunar_search_cache.get(cache_key)
        if cached is not None:
            return cached

        if backward:
            phase_jd = last_full_moon(jd_start, reader=self._reader)
        else:
            phase_jd = next_moon_phase("Full Moon", jd_start, reader=self._reader).jd_ut

        for _ in range(max_lunations):
            phase_data = self.calculate_jd(phase_jd)
            if phase_data.is_eclipse_season:
                if use_canon:
                    best_jd = find_lunar_contacts_canon(self, phase_jd).greatest_ut
                    best_data = self._calculate_jd_internal(
                        best_jd,
                        retarded_moon=False,
                        delta_t_mode="nasa_canon",
                    )
                    if _matches_lunar_kind(best_data, kind_key):
                        event = EclipseEvent(jd_ut=best_jd, data=best_data)
                        self._lunar_search_cache[cache_key] = event
                        return event
                else:
                    # Umbral and penumbral events intentionally retain their
                    # separately declared native vector policies.  Compute only
                    # the family needed by the requested result.
                    if kind_key in {"any", "total", "partial"}:
                        best_jd = self._refine_lunar_maximum_for_kind(phase_jd, "total")
                        best_data = self._calculate_jd_internal(
                            best_jd,
                            retarded_moon=True,
                        )
                        umbral_match = (
                            _matches_lunar_kind(best_data, kind_key)
                            if kind_key != "any"
                            else (
                                best_data.is_lunar_eclipse
                                and (
                                    best_data.eclipse_type.is_total
                                    or best_data.eclipse_type.is_partial
                                )
                            )
                        )
                        if umbral_match:
                            event = EclipseEvent(jd_ut=best_jd, data=best_data)
                            self._lunar_search_cache[cache_key] = event
                            return event

                    if kind_key in {"any", "penumbral"}:
                        best_jd = self._refine_lunar_maximum_for_kind(phase_jd, "penumbral")
                        best_data = self._calculate_jd_internal(
                            best_jd,
                            retarded_moon=False,
                        )
                        if _matches_lunar_kind(best_data, "penumbral"):
                            event = EclipseEvent(jd_ut=best_jd, data=best_data)
                            self._lunar_search_cache[cache_key] = event
                            return event

            if backward:
                phase_jd = last_full_moon(phase_jd - 1.0, reader=self._reader)
            else:
                phase_jd = next_moon_phase(
                    "Full Moon",
                    phase_jd + 1.0,
                    reader=self._reader,
                ).jd_ut

        direction = "previous" if backward else "next"
        raise RuntimeError(f"No {direction} lunar eclipse of kind {kind!r} found")

    def _search_solar_eclipse(
        self,
        jd_start: float,
        *,
        kind: str,
        backward: bool,
        max_lunations: int | None = None,
    ) -> EclipseEvent:
        """
        Search successive new moons until a solar eclipse of the requested kind
        is found, then refine to the eclipse maximum near that new moon. Public
        callers leave ``max_lunations`` unset, so a rare requested class is
        searched until the active kernel reports its coverage boundary rather
        than being truncated by an undocumented calendar interval.
        """
        kind_key = kind.strip().lower().replace("-", "_").replace(" ", "_")
        if kind_key not in {"any", "total", "annular", "partial", "central", "hybrid"}:
            raise ValueError(f"Unsupported solar eclipse kind: {kind!r}")
        if max_lunations is not None and max_lunations <= 0:
            raise ValueError("max_lunations must be > 0")

        cache_key = (jd_start, backward, max_lunations, kind_key)
        cached = self._solar_search_cache.get(cache_key)
        if cached is not None:
            return cached

        if backward:
            phase_jd = last_new_moon(jd_start, reader=self._reader)
        else:
            phase_jd = next_moon_phase("New Moon", jd_start, reader=self._reader).jd_ut

        lunations_searched = 0
        while max_lunations is None or lunations_searched < max_lunations:
            lunations_searched += 1
            phase_data = self.calculate_jd(phase_jd)
            if phase_data.is_eclipse_season:
                best_jd = _refine_solar_maximum(
                    self,
                    phase_jd,
                    tol_days=1.0e-9,
                )
                best_data = self.calculate_jd(best_jd)
                kind_matches = _matches_solar_kind(best_data, kind_key)
                if kind_key == "central" and kind_matches:
                    kind_matches = (
                        self._native_solar_shadow_axis_distance_km(best_jd)
                        <= EARTH_RADIUS_KM
                    )
                if kind_matches:
                    event = EclipseEvent(jd_ut=best_jd, data=best_data)
                    self._solar_search_cache[cache_key] = event
                    return event

            if backward:
                phase_jd = last_new_moon(phase_jd - 1.0, reader=self._reader)
            else:
                phase_jd = next_moon_phase(
                    "New Moon",
                    phase_jd + 1.0,
                    reader=self._reader,
                ).jd_ut

        direction = "previous" if backward else "next"
        raise RuntimeError(
            f"No {direction} solar eclipse of kind {kind!r} found within "
            f"{max_lunations} lunations"
        )

    def solar_eclipses_in_range(
        self,
        jd_start: float,
        jd_end: float,
    ) -> list[EclipseEvent]:
        """Return all solar eclipses whose maximum falls within [jd_start, jd_end].

        Chains successive ``next_solar_eclipse`` calls, advancing past each
        found event, until the next eclipse maximum falls after *jd_end*.
        """
        events: list[EclipseEvent] = []
        jd = jd_start
        while True:
            event = self.next_solar_eclipse(jd)
            if event.jd_ut > jd_end:
                break
            events.append(event)
            jd = event.jd_ut + 1.0
        return events

    def lunar_eclipses_in_range(
        self,
        jd_start: float,
        jd_end: float,
    ) -> list[EclipseEvent]:
        """Return all lunar eclipses whose maximum falls within [jd_start, jd_end].

        Chains successive ``next_lunar_eclipse`` calls, advancing past each
        found event, until the next eclipse maximum falls after *jd_end*.
        """
        events: list[EclipseEvent] = []
        jd = jd_start
        while True:
            event = self.next_lunar_eclipse(jd)
            if event.jd_ut > jd_end:
                break
            events.append(event)
            jd = event.jd_ut + 1.0
        return events

    def eclipse_hits_in_range(
        self,
        jd_start: float,
        jd_end: float,
        natal_positions: dict[str, float],
        orb: float = 1.0,
    ) -> list["EclipseHit"]:
        """Return every eclipse in [jd_start, jd_end] that falls within *orb*
        degrees of any natal position.

        For solar eclipses the active longitude is the Sun/Moon conjunction
        degree (``data.sun_longitude``).  For lunar eclipses both the Moon
        degree (``data.moon_longitude``) and the opposition Sun degree are
        checked, since a lunar eclipse activates both axis ends.

        Parameters
        ----------
        jd_start, jd_end : float
            Julian Day range (Universal Time) to search.
        natal_positions : dict[str, float]
            Mapping of point name → ecliptic longitude (degrees) for the
            natal chart — e.g. ``{"Sun": 15.3, "Moon": 220.1, "ASC": 5.0}``.
        orb : float
            Maximum angular separation in degrees for a hit to be recorded.
            Default is 1.0°.

        Returns
        -------
        list[EclipseHit]
            One entry per (eclipse, natal point) pair that falls within *orb*.
            Sorted by eclipse Julian Day, then by target name.
        """
        hits: list[EclipseHit] = []

        for event in self.solar_eclipses_in_range(jd_start, jd_end):
            eclipse_lon = event.data.sun_longitude
            for name, natal_lon in natal_positions.items():
                sep = _ecliptic_arc(eclipse_lon, natal_lon)
                if sep <= orb:
                    hits.append(EclipseHit(
                        event=event,
                        eclipse_longitude=eclipse_lon,
                        eclipse_kind="solar",
                        target_name=name,
                        target_longitude=natal_lon,
                        orb=sep,
                    ))

        for event in self.lunar_eclipses_in_range(jd_start, jd_end):
            moon_lon = event.data.moon_longitude
            sun_lon  = event.data.sun_longitude
            for name, natal_lon in natal_positions.items():
                sep_moon = _ecliptic_arc(moon_lon, natal_lon)
                if sep_moon <= orb:
                    hits.append(EclipseHit(
                        event=event,
                        eclipse_longitude=moon_lon,
                        eclipse_kind="lunar",
                        target_name=name,
                        target_longitude=natal_lon,
                        orb=sep_moon,
                    ))
                    continue
                sep_sun = _ecliptic_arc(sun_lon, natal_lon)
                if sep_sun <= orb:
                    hits.append(EclipseHit(
                        event=event,
                        eclipse_longitude=sun_lon,
                        eclipse_kind="lunar",
                        target_name=name,
                        target_longitude=natal_lon,
                        orb=sep_sun,
                    ))

        hits.sort(key=lambda h: (h.event.jd_ut, h.target_name))
        return hits


def _ecliptic_arc(lon_a: float, lon_b: float) -> float:
    """Shortest arc in degrees between two ecliptic longitudes."""
    diff = abs(lon_a - lon_b) % 360.0
    return min(diff, 360.0 - diff)


def _galactic_center_lon_jd(jd: float) -> float:
    """Galactic Center ecliptic longitude precessed from J2000 to *jd*."""
    delta_days = jd - J2000
    centuries  = delta_days / 36525.0
    return (GALACTIC_CENTER_LON_J2000 + PRECESSION_DEG_PER_CENTURY * centuries) % 360.0


def _to_stone(longitude: float, gc_longitude: float) -> int:
    """Convert ecliptic longitude to Aubrey stone position (0–55)."""
    offset = (longitude - gc_longitude) % 360.0
    return int(round(offset / DEGREES_PER_STONE) % AUBREY_HOLES)


def _saros_index_jd(jd: float) -> float:
    """Position within the Saros cycle (0.0–222.9...) for a UT Julian Day."""
    days = jd - J2000
    return (days / 29.53059) % SAROS_SYNODIC_MONTHS


def _metonic_position_jd(
    jd: float, sun_lon: float, moon_lon: float
) -> tuple[float, bool]:
    """
    Position within the 19-year Metonic cycle (0.0–19.0).
    Returns (metonic_year, is_reset).
    """
    days = jd - J2000
    years_in_cycle = 19.0 * (days % METONIC_PERIOD_DAYS) / METONIC_PERIOD_DAYS
    tolerance = 0.08   # ~1 month
    near_reset = years_in_cycle < tolerance or years_in_cycle > (19.0 - tolerance)
    moon_age   = (moon_lon - sun_lon) % 360.0
    phase_match = moon_age < 15.0 or moon_age > 345.0
    return years_in_cycle, bool(near_reset and phase_match)


def _classify(
    angular_sep:    float,
    moon_lat:       float,
    sun_node_dist:  float,
    sun_radius:     float,
    moon_radius:    float,
    shadow_radius:  float,
    penumbra_radius: float,
    moon_parallax:  float,
    native_lunar_axis_km: float | None = None,
    native_lunar_moon_radius_km: float | None = None,
    native_lunar_umbra_radius_km: float | None = None,
    native_lunar_penumbra_radius_km: float | None = None,
    native_solar_axis_km: float | None = None,
    native_solar_center_sun_radius: float | None = None,
    native_solar_center_moon_radius: float | None = None,
    native_solar_surface_sun_radius: float | None = None,
    native_solar_surface_moon_radius: float | None = None,
) -> tuple[EclipseType, bool, bool, float]:
    """
    Classify eclipse type from geometric parameters.

    Returns
    -------
    (EclipseType, is_solar, is_lunar, magnitude)
    """
    _none = EclipseType(False, False, False, False, 0.0, 0.0), False, False, 0.0

    is_new_moon  = angular_sep < 1.5
    is_full_moon = abs(angular_sep - 180.0) < 1.5
    near_node    = (sun_node_dist < ECLIPSE_SEASON_THRESHOLD
                    and abs(moon_lat) < ECLIPSE_LATITUDE_THRESHOLD)

    if not near_node:
        return _none

    # --- Solar eclipse ---
    if is_new_moon:
        c2c_best = max(0.0, angular_sep - moon_parallax)
        moon_radius_surface = _topocentric_near_moon_radius(moon_parallax)

        if (
            native_solar_axis_km is not None
            and native_solar_axis_km <= EARTH_RADIUS_KM
            and native_solar_center_sun_radius is not None
            and native_solar_center_moon_radius is not None
            and native_solar_surface_sun_radius is not None
            and native_solar_surface_moon_radius is not None
        ):
            # The shadow axis actually intersects Earth. Classify at its first
            # surface intersection, not at the fictitious nearest possible
            # observer. If the surface is total while the geocentre remains
            # annular, the cone apex lies within Earth and the global event is
            # hybrid (annular and total on different path sections).
            magnitude = (
                native_solar_surface_moon_radius
                / native_solar_surface_sun_radius
            )
            if native_solar_surface_moon_radius < native_solar_surface_sun_radius:
                eclipse_type = EclipseType(
                    False,
                    True,
                    False,
                    False,
                    magnitude,
                    magnitude,
                )
            elif native_solar_center_moon_radius <= native_solar_center_sun_radius:
                eclipse_type = EclipseType(
                    False,
                    False,
                    False,
                    True,
                    magnitude,
                    magnitude,
                )
            else:
                eclipse_type = EclipseType(
                    False,
                    False,
                    True,
                    False,
                    magnitude,
                    magnitude,
                )
            return eclipse_type, True, False, magnitude

        if c2c_best > sun_radius + moon_radius_surface:
            return _none

        if c2c_best < abs(sun_radius - moon_radius_surface):
            # For central eclipses the published magnitude product is the
            # local Moon/Sun diameter ratio; the radius ratio is identical.
            mag = moon_radius_surface / sun_radius
            if moon_radius_surface > sun_radius:
                if moon_radius <= sun_radius:
                    et = EclipseType(False, False, False, True, mag, mag)
                else:
                    et = EclipseType(False, False, True, False, mag, mag)
            else:
                et = EclipseType(False, True, False, False, mag, mag)
            return et, True, False, mag

        mag = (sun_radius + moon_radius_surface - c2c_best) / (2 * sun_radius)
        et = EclipseType(True, False, False, False, mag, mag)
        return et, True, False, mag

    # --- Lunar eclipse ---
    if is_full_moon:
        if (
            native_lunar_axis_km is not None
            and native_lunar_moon_radius_km is not None
            and native_lunar_umbra_radius_km is not None
            and native_lunar_penumbra_radius_km is not None
        ):
            if native_lunar_axis_km < native_lunar_umbra_radius_km + native_lunar_moon_radius_km:
                umbral_mag = (
                    native_lunar_umbra_radius_km
                    + native_lunar_moon_radius_km
                    - native_lunar_axis_km
                ) / (2.0 * native_lunar_moon_radius_km)
                pen_mag = (
                    native_lunar_penumbra_radius_km
                    + native_lunar_moon_radius_km
                    - native_lunar_axis_km
                ) / (2.0 * native_lunar_moon_radius_km)

                if native_lunar_axis_km < native_lunar_umbra_radius_km - native_lunar_moon_radius_km:
                    et = EclipseType(False, False, True, False, umbral_mag, pen_mag)
                else:
                    et = EclipseType(True, False, False, False, umbral_mag, pen_mag)
                return et, False, True, umbral_mag

            pen_limit_km = native_lunar_penumbra_radius_km + native_lunar_moon_radius_km
            if native_lunar_axis_km < pen_limit_km:
                pen_mag = (
                    pen_limit_km - native_lunar_axis_km
                ) / (2.0 * native_lunar_moon_radius_km)
                et = EclipseType(False, False, False, False, 0.0, pen_mag)
                return et, False, True, pen_mag

        shadow_sep = shadow_axis_offset_deg(angular_sep)

        if shadow_sep < shadow_radius + moon_radius:
            umbral_mag = lunar_umbral_magnitude(shadow_radius, moon_radius, shadow_sep)
            pen_mag = lunar_penumbral_magnitude(penumbra_radius, moon_radius, shadow_sep)

            if shadow_sep < shadow_radius - moon_radius:
                et = EclipseType(False, False, True, False, umbral_mag, pen_mag)
            else:
                et = EclipseType(True, False, False, False, umbral_mag, pen_mag)
            return et, False, True, umbral_mag

        # Penumbral-only lunar eclipse: a first-class eclipse whose main-shadow
        # kind flags remain false by construction.
        pen_limit = penumbra_radius + moon_radius
        if shadow_sep < pen_limit:
            pen_mag = lunar_penumbral_magnitude(penumbra_radius, moon_radius, shadow_sep)
            et = EclipseType(False, False, False, False, 0.0, pen_mag)
            return et, False, True, pen_mag

    return _none


def _matches_lunar_kind(data: EclipseData, kind: str) -> bool:
    """Return True if *data* matches the requested lunar eclipse kind."""
    if kind == "any":
        return data.is_lunar_eclipse
    if kind == "total":
        return data.is_lunar_eclipse and data.eclipse_type.is_total
    if kind == "partial":
        return data.is_lunar_eclipse and data.eclipse_type.is_partial
    if kind == "penumbral":
        return (
            data.is_lunar_eclipse
            and not data.eclipse_type.is_partial
            and not data.eclipse_type.is_total
            and data.eclipse_type.magnitude_penumbra > 0.0
        )
    return False


def _matches_solar_kind(data: EclipseData, kind: str) -> bool:
    """Return True if *data* matches the requested solar eclipse kind."""
    if kind == "any":
        return data.is_solar_eclipse
    if kind == "partial":
        return data.is_solar_eclipse and data.eclipse_type.is_partial
    if kind == "annular":
        return data.is_solar_eclipse and data.eclipse_type.is_annular
    if kind == "hybrid":
        return data.is_solar_eclipse and data.eclipse_type.is_hybrid
    if kind == "total":
        return data.is_solar_eclipse and data.eclipse_type.is_total
    if kind == "central":
        return data.is_solar_eclipse and not data.eclipse_type.is_partial
    return False


def _matches_solar_local_candidate_kind(data: EclipseData, kind: str) -> bool:
    """Admit global events that can realize the requested local eclipse kind."""

    if not data.is_solar_eclipse:
        return False
    if kind in {"any", "partial"}:
        # Every global eclipse can be partial somewhere inside its visibility
        # footprint, so local filtering must wait for the observer solve.
        return True
    if kind == "total":
        return data.eclipse_type.is_total or data.eclipse_type.is_hybrid
    if kind == "annular":
        return data.eclipse_type.is_annular or data.eclipse_type.is_hybrid
    if kind == "central":
        return not data.eclipse_type.is_partial
    if kind == "hybrid":
        # Hybrid is a path-level identity. A single site is total, annular, or
        # partial; the refined local data retains that local classification.
        return data.eclipse_type.is_hybrid
    return False


_GEO_SEARCH_STEPS_DEG = (10.0, 5.0, 2.0, 1.0, 0.5, 0.25, 0.1, 0.05)
_GEO_COARSE_LAT_STEP_DEG = 20.0
_GEO_COARSE_LON_STEP_DEG = 20.0
_GEO_SEARCH_EARLY_EXIT_SEPARATION_DEG = 1.0e-4
_GEO_SEARCH_MAX_OBJECTIVE_EVALS = 4096
_GEO_SEARCH_MAX_PASSES_PER_STEP = 512
_SOLAR_CENTRAL_INTERVAL_STEP_DAYS = 1.0 / 48.0
_SOLAR_CENTRAL_INTERVAL_SCAN_STEPS = 48
_SOLAR_CENTRAL_INTERVAL_MAX_MARGIN_EVALS = 192
_SOLAR_LOCAL_CONTACT_STEP_DAYS = 30.0 / 86400.0
_SOLAR_LOCAL_CONTACT_SCAN_STEPS = 120
_SOLAR_TRACK_TANGENT_STEP_DAYS = 30.0 / 86400.0
_SOLAR_FOOTPRINT_AZIMUTH_SAMPLES = 720
_WGS84_FLATTENING = 1.0 / 298.257223563
_WGS84_POLAR_RADIUS_KM = EARTH_RADIUS_KM * (1.0 - _WGS84_FLATTENING)
_WGS84_AXIS_TANGENCY_TOLERANCE_KM2 = 1.0e-6


@dataclass(frozen=True, slots=True)
class _EarthFixedSolarShadow:
    """One native central-shadow cone expressed in the terrestrial frame.

    The fundamental-plane point is the closest point on the shadow axis to
    Earth's centre. ``axis_projection_km`` is the Moon's signed coordinate on
    that axis and is therefore negative for a forward shadow ray reaching
    Earth. ``central_radius_km`` is signed at the fundamental plane: positive
    for an umbra and negative for an antumbra.
    """

    fundamental_plane_point_xyz_km: tuple[float, float, float]
    axis_unit_away_from_sun: tuple[float, float, float]
    axis_projection_km: float
    central_radius_km: float
    central_cone_slope: float


@dataclass(frozen=True, slots=True)
class _SolarAxisSurfacePoint:
    """The near-side intersection of the central shadow axis and WGS-84."""

    xyz_itrf_km: tuple[float, float, float]
    latitude_deg: float
    longitude_deg: float
    signed_half_chord_sq_km2: float


@dataclass(frozen=True, slots=True)
class _SolarCentralAxisBoundary:
    """One numerical axis/ellipsoid tangency endpoint and its UT1 epoch."""

    jd_ut: float
    point: _SolarAxisSurfacePoint


class _SearchLimitReached(RuntimeError):
    """Vessel: Internal exception thrown when an eclipse search exceeds safety limits."""
    pass


def _validate_observer_inputs(
    latitude: float,
    longitude: float,
    elevation_m: float,
) -> None:
    """Validate one observer without relying on the optional transport layer."""

    if not math.isfinite(latitude) or not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude must be finite and between -90 and 90 degrees")
    if not math.isfinite(longitude) or not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude must be finite and between -180 and 180 degrees")
    if not math.isfinite(elevation_m):
        raise ValueError("elevation_m must be finite")


def _bisection_root(func, left: float, right: float, *, iterations: int = 48) -> float:
    f_left = func(left)
    f_right = func(right)
    if f_left == 0.0:
        return left
    if f_right == 0.0:
        return right
    if f_left * f_right > 0.0:
        raise ValueError("bisection_root requires a bracketing interval")
    a = left
    b = right
    fa = f_left
    for _ in range(iterations):
        mid = (a + b) / 2.0
        fm = func(mid)
        if fm == 0.0:
            return mid
        if fa * fm <= 0.0:
            b = mid
        else:
            a = mid
            fa = fm
    return (a + b) / 2.0


def _topocentric_solar_geometry(
    calc: EclipseCalculator,
    jd_ut: float,
    latitude: float,
    longitude: float,
    elevation_m: float = 0.0,
) -> tuple[float, float, float]:
    sun = sky_position_at(
        Body.SUN,
        jd_ut,
        latitude,
        longitude,
        elevation_m,
        reader=calc._reader,
    )
    if sun.altitude <= 0.0:
        return float("inf"), float("-inf"), float("-inf")

    moon = sky_position_at(
        Body.MOON,
        jd_ut,
        latitude,
        longitude,
        elevation_m,
        reader=calc._reader,
    )
    separation = _angular_separation(
        sun.right_ascension,
        sun.declination,
        moon.right_ascension,
        moon.declination,
    )
    sun_radius = _apparent_radius(SUN_RADIUS_KM, sun.distance)
    moon_radius = _apparent_radius(MOON_RADIUS_KM, moon.distance)
    overlap_margin = (sun_radius + moon_radius) - separation
    central_margin = abs(moon_radius - sun_radius) - separation
    return separation, overlap_margin, central_margin


def _solar_eclipse_data_at_location(
    calc: EclipseCalculator,
    data: EclipseData,
    jd_ut: float,
    latitude: float,
    longitude: float,
    *,
    central: bool,
) -> EclipseData:
    """Bind observer-derived solar fields to an existing global event record."""

    sun = sky_position_at(
        Body.SUN,
        jd_ut,
        latitude,
        longitude,
        0.0,
        reader=calc._reader,
    )
    moon = sky_position_at(
        Body.MOON,
        jd_ut,
        latitude,
        longitude,
        0.0,
        reader=calc._reader,
    )
    separation = _angular_separation(
        sun.right_ascension,
        sun.declination,
        moon.right_ascension,
        moon.declination,
    )
    sun_radius = _apparent_radius(SUN_RADIUS_KM, sun.distance)
    moon_radius = _apparent_radius(MOON_RADIUS_KM, moon.distance)
    if central:
        magnitude = moon_radius / sun_radius
    else:
        magnitude = max(
            0.0,
            (sun_radius + moon_radius - separation) / (2.0 * sun_radius),
        )
    eclipse_type = replace(
        data.eclipse_type,
        magnitude_umbral=magnitude,
        magnitude_penumbra=magnitude,
    )
    return replace(
        data,
        sun_apparent_radius=sun_radius,
        moon_apparent_radius=moon_radius,
        moon_distance_km=moon.distance,
        solar_topocentric_separation=separation,
        eclipse_type=eclipse_type,
        eclipse_magnitude=magnitude,
    )


def _local_solar_eclipse_data(
    data: EclipseData,
    *,
    sun_distance_km: float,
    moon_distance_km: float,
    separation_deg: float,
) -> EclipseData:
    """Bind one observer-local solar maximum to the stable EclipseData shape."""

    sun_radius = _apparent_radius(SUN_RADIUS_KM, sun_distance_km)
    moon_radius = _apparent_radius(MOON_RADIUS_KM, moon_distance_km)
    if separation_deg >= sun_radius + moon_radius:
        eclipse_type = EclipseType(False, False, False, False, 0.0, 0.0)
        magnitude = 0.0
        is_solar_eclipse = False
    elif separation_deg < abs(moon_radius - sun_radius):
        magnitude = moon_radius / sun_radius
        eclipse_type = (
            EclipseType(False, False, True, False, magnitude, magnitude)
            if moon_radius > sun_radius
            else EclipseType(False, True, False, False, magnitude, magnitude)
        )
        is_solar_eclipse = True
    else:
        magnitude = max(
            0.0,
            (sun_radius + moon_radius - separation_deg) / (2.0 * sun_radius),
        )
        eclipse_type = EclipseType(True, False, False, False, magnitude, magnitude)
        is_solar_eclipse = True

    return replace(
        data,
        sun_apparent_radius=sun_radius,
        moon_apparent_radius=moon_radius,
        moon_distance_km=moon_distance_km,
        solar_topocentric_separation=separation_deg,
        is_solar_eclipse=is_solar_eclipse,
        is_lunar_eclipse=False,
        eclipse_type=eclipse_type,
        eclipse_magnitude=magnitude,
    )


def _solve_solar_greatest_location(
    calc: EclipseCalculator,
    jd_ut: float,
) -> tuple[float, float, float]:
    cache: dict[tuple[float, float], float] = {}
    objective_evals = 0

    def objective(latitude: float, longitude: float) -> float:
        nonlocal objective_evals
        canonical_latitude, canonical_longitude = _offset_geographic_km(
            latitude,
            longitude,
            0.0,
            0.0,
        )
        key = (round(canonical_latitude, 6), round(canonical_longitude, 6))
        if key not in cache:
            if objective_evals >= _GEO_SEARCH_MAX_OBJECTIVE_EVALS:
                raise _SearchLimitReached(
                    "solar greatest-location evaluation limit exhausted"
                )
            objective_evals += 1
            separation, _, _ = _topocentric_solar_geometry(
                calc,
                jd_ut,
                canonical_latitude,
                canonical_longitude,
            )
            cache[key] = separation
        return cache[key]

    def limit_reached() -> bool:
        return best_score <= _GEO_SEARCH_EARLY_EXIT_SEPARATION_DEG

    best_lat = 0.0
    best_lon = 0.0
    best_score = float("inf")
    search_complete = False

    # Longitude is undefined at an exact pole.  Search each pole once at the
    # canonical longitude before the regular latitude/longitude grid.
    for latitude, longitude in ((-90.0, 0.0), (90.0, 0.0)):
        score = objective(latitude, longitude)
        if score < best_score:
            best_lat = latitude
            best_lon = longitude
            best_score = score
            if best_score <= _GEO_SEARCH_EARLY_EXIT_SEPARATION_DEG:
                return best_lat, best_lon, best_score

    lat = -80.0
    while lat <= 80.0 + 1e-9 and not search_complete:
        lon = -180.0
        while lon < 180.0 - 1e-9:
            if limit_reached():
                search_complete = True
                break
            score = objective(lat, lon)
            if score < best_score:
                best_lat = lat
                best_lon = lon
                best_score = score
                if best_score <= _GEO_SEARCH_EARLY_EXIT_SEPARATION_DEG:
                    search_complete = True
                    break
            lon += _GEO_COARSE_LON_STEP_DEG
        lat += _GEO_COARSE_LAT_STEP_DEG

    if search_complete:
        return best_lat, best_lon, best_score

    for step in _GEO_SEARCH_STEPS_DEG:
        if limit_reached():
            break
        step_km = step * _KM_PER_DEG_LAT
        improved = True
        passes = 0
        while improved and passes < _GEO_SEARCH_MAX_PASSES_PER_STEP:
            if limit_reached():
                return best_lat, best_lon, best_score
            passes += 1
            improved = False
            origin_lat = best_lat
            origin_lon = best_lon
            pass_best_lat = best_lat
            pass_best_lon = best_lon
            pass_best_score = best_score
            for north_direction in (-1.0, 0.0, 1.0):
                for east_direction in (-1.0, 0.0, 1.0):
                    if north_direction == 0.0 and east_direction == 0.0:
                        continue
                    if limit_reached():
                        return best_lat, best_lon, best_score
                    cand_lat, cand_lon = _offset_geographic_km(
                        origin_lat,
                        origin_lon,
                        north_direction * step_km,
                        east_direction * step_km,
                    )
                    score = objective(cand_lat, cand_lon)
                    if score <= _GEO_SEARCH_EARLY_EXIT_SEPARATION_DEG:
                        return cand_lat, cand_lon, score
                    if score < pass_best_score:
                        pass_best_lat = cand_lat
                        pass_best_lon = cand_lon
                        pass_best_score = score
            if pass_best_score < best_score:
                best_lat = pass_best_lat
                best_lon = pass_best_lon
                best_score = pass_best_score
                improved = True
    return best_lat, best_lon, best_score


def _shadow_dot(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _shadow_add(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def _shadow_subtract(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def _shadow_scale(
    vector: tuple[float, float, float],
    scalar: float,
) -> tuple[float, float, float]:
    return (vector[0] * scalar, vector[1] * scalar, vector[2] * scalar)


def _shadow_cross(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _shadow_unit(
    vector: tuple[float, float, float],
    *,
    label: str,
) -> tuple[float, float, float]:
    magnitude = math.sqrt(_shadow_dot(vector, vector))
    if magnitude == 0.0 or not math.isfinite(magnitude):
        raise ArithmeticError(f"{label} has no finite direction")
    return _shadow_scale(vector, 1.0 / magnitude)


def _transpose_matrix_3x3(matrix):
    return (
        (matrix[0][0], matrix[1][0], matrix[2][0]),
        (matrix[0][1], matrix[1][1], matrix[2][1]),
        (matrix[0][2], matrix[1][2], matrix[2][2]),
    )


def _earth_fixed_solar_shadow(
    calc: EclipseCalculator,
    jd_ut: float,
) -> _EarthFixedSolarShadow | None:
    """Express the native reception-time shadow cone in ITRF coordinates.

    ICRF is rotated through true equator/equinox of date, physical GAST at the
    supplied UT1 epoch, and the inverse admitted polar-motion matrix. This is
    the exact inverse staging of Moira's WGS-84 observer construction.
    """

    jd_tt = _ut1_to_ephemeris_tt(jd_ut, calc._reader)
    state = calc._native_solar_shadow_axis_state_tt(jd_tt)
    plane_point = state.fundamental_plane_point_xyz_km
    if plane_point is None:
        return None

    precession_nutation = mat_mul(
        nutation_matrix_equatorial(jd_tt),
        precession_matrix_equatorial(jd_tt),
    )
    dpsi_deg, _deps_deg = nutation(jd_tt)
    gast_rad = math.radians(
        apparent_sidereal_time(
            jd_ut,
            dpsi_deg,
            true_obliquity(jd_tt),
        )
    )
    cos_gast = math.cos(gast_rad)
    sin_gast = math.sin(gast_rad)
    x_p_arcsec, y_p_arcsec = PolarMotionRegistry.polar_motion_at(jd_ut)
    tirs_to_itrf = _transpose_matrix_3x3(
        polar_motion_matrix(x_p_arcsec, y_p_arcsec)
    )

    def icrf_to_itrf(
        vector: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        tete_x, tete_y, tete_z = mat_vec_mul(precession_nutation, vector)
        tirs = (
            cos_gast * tete_x + sin_gast * tete_y,
            -sin_gast * tete_x + cos_gast * tete_y,
            tete_z,
        )
        return mat_vec_mul(tirs_to_itrf, tirs)

    axis_unit = _shadow_unit(
        icrf_to_itrf(state.axis_unit_away_from_sun),
        label="terrestrial solar shadow axis",
    )
    sin_f2 = (SUN_RADIUS_KM - MOON_RADIUS_KM) / state.sun_moon_distance_km
    if not 0.0 < sin_f2 < 1.0:
        raise ArithmeticError("solar and lunar radii cannot define a central shadow cone")
    cos_f2 = math.sqrt((1.0 - sin_f2) * (1.0 + sin_f2))
    tan_f2 = sin_f2 / cos_f2
    central_radius = (
        MOON_RADIUS_KM / cos_f2
        + state.axis_projection_km * tan_f2
    )
    return _EarthFixedSolarShadow(
        fundamental_plane_point_xyz_km=icrf_to_itrf(plane_point),
        axis_unit_away_from_sun=axis_unit,
        axis_projection_km=state.axis_projection_km,
        central_radius_km=central_radius,
        central_cone_slope=tan_f2,
    )


def _wgs84_line_quadratic_coefficients(
    point_xyz_km: tuple[float, float, float],
    direction: tuple[float, float, float],
) -> tuple[float, float, float]:
    a2 = EARTH_RADIUS_KM * EARTH_RADIUS_KM
    b2 = _WGS84_POLAR_RADIUS_KM * _WGS84_POLAR_RADIUS_KM
    coefficient_a = (
        (direction[0] * direction[0] + direction[1] * direction[1]) / a2
        + direction[2] * direction[2] / b2
    )
    if coefficient_a <= 0.0 or not math.isfinite(coefficient_a):
        raise ArithmeticError("ellipsoid-intersection line has no finite direction")
    coefficient_b = (
        (point_xyz_km[0] * direction[0] + point_xyz_km[1] * direction[1]) / a2
        + point_xyz_km[2] * direction[2] / b2
    )
    coefficient_c = (
        (point_xyz_km[0] * point_xyz_km[0] + point_xyz_km[1] * point_xyz_km[1])
        / a2
        + point_xyz_km[2] * point_xyz_km[2] / b2
        - 1.0
    )
    return coefficient_a, coefficient_b, coefficient_c


def _wgs84_line_intersection_parameters(
    point_xyz_km: tuple[float, float, float],
    direction: tuple[float, float, float],
) -> tuple[float, tuple[float, float] | None]:
    """Return signed half-chord squared and line/WGS-84 parameters.

    The line is ``point + parameter * direction``. The signed scalar is in
    square kilometres: positive intersects, zero is tangent, and negative
    misses. Working from the fundamental plane avoids the catastrophic
    cancellation incurred by anchoring the line at the distant Moon.
    """

    coefficient_a, coefficient_b, coefficient_c = (
        _wgs84_line_quadratic_coefficients(point_xyz_km, direction)
    )
    if hasattr(math, "fma"):
        discriminant = math.fma(-coefficient_a, coefficient_c, coefficient_b * coefficient_b)
    else:  # Python 3.10-3.12 compatibility.
        discriminant = math.fsum(
            (coefficient_b * coefficient_b, -coefficient_a * coefficient_c)
        )
    signed_half_chord_sq_km2 = discriminant / (coefficient_a * coefficient_a)
    if signed_half_chord_sq_km2 < -_WGS84_AXIS_TANGENCY_TOLERANCE_KM2:
        return signed_half_chord_sq_km2, None

    half_chord_km = math.sqrt(max(0.0, signed_half_chord_sq_km2))
    chord_center_km = -coefficient_b / coefficient_a
    return signed_half_chord_sq_km2, (
        chord_center_km - half_chord_km,
        chord_center_km + half_chord_km,
    )


def _wgs84_geodetic_from_xyz_km(
    xyz_km: tuple[float, float, float],
) -> tuple[float, float]:
    """Convert one point on the WGS-84 ellipsoid to geodetic coordinates."""

    x_km, y_km, z_km = xyz_km
    radial_xy_km = math.hypot(x_km, y_km)
    longitude_deg = (
        0.0
        if radial_xy_km == 0.0
        else _wrap_longitude_deg(math.degrees(math.atan2(y_km, x_km)))
    )
    latitude_deg = math.degrees(
        math.atan2(
            z_km / (_WGS84_POLAR_RADIUS_KM * _WGS84_POLAR_RADIUS_KM),
            radial_xy_km / (EARTH_RADIUS_KM * EARTH_RADIUS_KM),
        )
    )
    return latitude_deg, longitude_deg


def _wgs84_surface_xyz_km(
    latitude_deg: float,
    longitude_deg: float,
) -> tuple[float, float, float]:
    """Return the zero-elevation ITRF point for WGS-84 geodetic coordinates."""

    latitude_rad = math.radians(latitude_deg)
    longitude_rad = math.radians(longitude_deg)
    sin_latitude = math.sin(latitude_rad)
    cos_latitude = math.cos(latitude_rad)
    eccentricity_sq = _WGS84_FLATTENING * (2.0 - _WGS84_FLATTENING)
    prime_vertical_radius_km = EARTH_RADIUS_KM / math.sqrt(
        1.0 - eccentricity_sq * sin_latitude * sin_latitude
    )
    return (
        prime_vertical_radius_km * cos_latitude * math.cos(longitude_rad),
        prime_vertical_radius_km * cos_latitude * math.sin(longitude_rad),
        prime_vertical_radius_km
        * (1.0 - eccentricity_sq)
        * sin_latitude,
    )


def _axis_surface_point_from_shadow(
    shadow: _EarthFixedSolarShadow,
) -> _SolarAxisSurfacePoint | None:
    signed_half_chord_sq_km2, roots = _wgs84_line_intersection_parameters(
        shadow.fundamental_plane_point_xyz_km,
        shadow.axis_unit_away_from_sun,
    )
    if roots is None:
        return None
    lawful_roots = tuple(
        root
        for root in roots
        if root >= shadow.axis_projection_km
    )
    if not lawful_roots:
        return None
    near_parameter_km = min(lawful_roots)
    distance_from_moon_km = near_parameter_km - shadow.axis_projection_km
    if distance_from_moon_km <= MOON_RADIUS_KM:
        raise ArithmeticError(
            "central shadow axis has no physical near-side intersection"
        )
    xyz_itrf_km = _shadow_add(
        shadow.fundamental_plane_point_xyz_km,
        _shadow_scale(shadow.axis_unit_away_from_sun, near_parameter_km),
    )
    latitude_deg, longitude_deg = _wgs84_geodetic_from_xyz_km(xyz_itrf_km)
    return _SolarAxisSurfacePoint(
        xyz_itrf_km=xyz_itrf_km,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        signed_half_chord_sq_km2=signed_half_chord_sq_km2,
    )


def _axis_surface_tangent_point_from_shadow(
    shadow: _EarthFixedSolarShadow,
) -> _SolarAxisSurfacePoint | None:
    """Materialize the limiting axis point with the coalesced chord root.

    The central-interval solver retains the last representable inside epoch so
    the line has a real (usually microscopic) chord. Its midpoint is ``-B/A``
    and converges to the unique ellipsoid tangent without choosing either
    numerically ill-conditioned near/far root.
    """

    signed_half_chord_sq_km2, roots = _wgs84_line_intersection_parameters(
        shadow.fundamental_plane_point_xyz_km,
        shadow.axis_unit_away_from_sun,
    )
    if roots is None:
        return None
    coefficient_a, coefficient_b, _coefficient_c = (
        _wgs84_line_quadratic_coefficients(
            shadow.fundamental_plane_point_xyz_km,
            shadow.axis_unit_away_from_sun,
        )
    )
    tangent_parameter_km = -coefficient_b / coefficient_a
    if tangent_parameter_km < shadow.axis_projection_km:
        return None
    distance_from_moon_km = tangent_parameter_km - shadow.axis_projection_km
    if distance_from_moon_km <= MOON_RADIUS_KM:
        raise ArithmeticError(
            "central shadow axis has no physical tangent intersection"
        )
    xyz_itrf_km = _shadow_add(
        shadow.fundamental_plane_point_xyz_km,
        _shadow_scale(shadow.axis_unit_away_from_sun, tangent_parameter_km),
    )
    latitude_deg, longitude_deg = _wgs84_geodetic_from_xyz_km(xyz_itrf_km)
    return _SolarAxisSurfacePoint(
        xyz_itrf_km=xyz_itrf_km,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        signed_half_chord_sq_km2=signed_half_chord_sq_km2,
    )


def _solar_axis_surface_point(
    calc: EclipseCalculator,
    jd_ut: float,
) -> _SolarAxisSurfacePoint | None:
    shadow = _earth_fixed_solar_shadow(calc, jd_ut)
    if shadow is None:
        return None
    return _axis_surface_point_from_shadow(shadow)


def _solar_axis_surface_tangent_point(
    calc: EclipseCalculator,
    jd_ut: float,
) -> _SolarAxisSurfacePoint | None:
    shadow = _earth_fixed_solar_shadow(calc, jd_ut)
    if shadow is None:
        return None
    return _axis_surface_tangent_point_from_shadow(shadow)


def _solar_axis_surface_discriminant_km2(
    calc: EclipseCalculator,
    jd_ut: float,
) -> float:
    shadow = _earth_fixed_solar_shadow(calc, jd_ut)
    if shadow is None:
        return float("-inf")
    signed_half_chord_sq_km2, _roots = _wgs84_line_intersection_parameters(
        shadow.fundamental_plane_point_xyz_km,
        shadow.axis_unit_away_from_sun,
    )
    return signed_half_chord_sq_km2


def _solve_solar_central_interval(
    calc: EclipseCalculator,
    jd_ut: float,
) -> tuple[_SolarCentralAxisBoundary, _SolarCentralAxisBoundary]:
    """Solve the first/last central-axis intersections with WGS-84.

    This interval governs the public central-line samples. It deliberately
    does not represent the separate U1/U4 cone tangencies or observer-local
    visibility/contact intervals.
    """

    margin_evals = 0

    def axis_margin_at_time(t: float) -> float:
        nonlocal margin_evals
        if margin_evals >= _SOLAR_CENTRAL_INTERVAL_MAX_MARGIN_EVALS:
            raise _SearchLimitReached(
                "solar central-interval evaluation limit exhausted"
            )
        margin_evals += 1
        return _solar_axis_surface_discriminant_km2(calc, t)

    center_margin = axis_margin_at_time(jd_ut)
    if center_margin < -_WGS84_AXIS_TANGENCY_TOLERANCE_KM2:
        raise ArithmeticError(
            "central-interval seed has no shadow-axis intersection with WGS-84"
        )

    step = _SOLAR_CENTRAL_INTERVAL_STEP_DAYS

    def solve_boundary(direction: float) -> _SolarCentralAxisBoundary:
        inside_time = jd_ut
        for _ in range(_SOLAR_CENTRAL_INTERVAL_SCAN_STEPS):
            outside_time = inside_time + direction * step
            if axis_margin_at_time(outside_time) <= 0.0:
                for _ in range(48):
                    midpoint = (inside_time + outside_time) / 2.0
                    if axis_margin_at_time(midpoint) >= 0.0:
                        inside_time = midpoint
                    else:
                        outside_time = midpoint
                point = _solar_axis_surface_tangent_point(calc, inside_time)
                if point is None:
                    raise ArithmeticError(
                        "central-axis tangency could not be materialized on WGS-84"
                    )
                return _SolarCentralAxisBoundary(jd_ut=inside_time, point=point)
            inside_time = outside_time
        raise _SearchLimitReached(
            "solar central-axis surface boundary was not bracketed within 24 hours"
        )

    return solve_boundary(-1.0), solve_boundary(1.0)


def _solve_local_solar_central_duration_s(
    calc: EclipseCalculator,
    jd_ut: float,
    latitude: float,
    longitude: float,
) -> float:
    """Solve local U2/U3 (or A2/A3) duration at one central-line site."""

    def margin(t: float) -> float:
        _, _, central_margin = _topocentric_solar_geometry(
            calc,
            t,
            latitude,
            longitude,
        )
        return central_margin

    center_margin = margin(jd_ut)
    if not math.isfinite(center_margin) or center_margin <= 0.0:
        return 0.0

    def solve_boundary(direction: float) -> float:
        current = jd_ut
        for _ in range(_SOLAR_LOCAL_CONTACT_SCAN_STEPS):
            next_time = current + direction * _SOLAR_LOCAL_CONTACT_STEP_DAYS
            if margin(next_time) <= 0.0:
                if direction < 0.0:
                    return _bisection_root(margin, next_time, current)
                return _bisection_root(margin, current, next_time)
            current = next_time
        raise _SearchLimitReached(
            "local solar central contacts were not bracketed within one hour"
        )

    start = solve_boundary(-1.0)
    end = solve_boundary(1.0)
    return max(0.0, (end - start) * 86400.0)


def _wgs84_surface_normal_unit(
    xyz_itrf_km: tuple[float, float, float],
) -> tuple[float, float, float]:
    return _shadow_unit(
        (
            xyz_itrf_km[0] / (EARTH_RADIUS_KM * EARTH_RADIUS_KM),
            xyz_itrf_km[1] / (EARTH_RADIUS_KM * EARTH_RADIUS_KM),
            xyz_itrf_km[2] / (_WGS84_POLAR_RADIUS_KM * _WGS84_POLAR_RADIUS_KM),
        ),
        label="WGS-84 surface normal",
    )


def _central_shadow_clearance_km(
    shadow: _EarthFixedSolarShadow,
    surface_xyz_itrf_km: tuple[float, float, float],
) -> float:
    """Return positive-inside central-shadow clearance at one surface point."""

    offset = _shadow_subtract(
        surface_xyz_itrf_km,
        shadow.fundamental_plane_point_xyz_km,
    )
    axial_km = _shadow_dot(offset, shadow.axis_unit_away_from_sun)
    perpendicular = _shadow_subtract(
        offset,
        _shadow_scale(shadow.axis_unit_away_from_sun, axial_km),
    )
    cone_radius_km = abs(
        shadow.central_radius_km - shadow.central_cone_slope * axial_km
    )
    return cone_radius_km - math.sqrt(_shadow_dot(perpendicular, perpendicular))


def _solar_axis_track_direction_itrf(
    calc: EclipseCalculator,
    jd_ut: float,
    center: _SolarAxisSurfacePoint,
) -> tuple[float, float, float]:
    before = _solar_axis_surface_point(calc, jd_ut - _SOLAR_TRACK_TANGENT_STEP_DAYS)
    after = _solar_axis_surface_point(calc, jd_ut + _SOLAR_TRACK_TANGENT_STEP_DAYS)
    if before is not None and after is not None:
        displacement = _shadow_subtract(after.xyz_itrf_km, before.xyz_itrf_km)
    elif before is not None:
        displacement = _shadow_subtract(center.xyz_itrf_km, before.xyz_itrf_km)
    elif after is not None:
        displacement = _shadow_subtract(after.xyz_itrf_km, center.xyz_itrf_km)
    else:
        raise ArithmeticError("central shadow track has no neighboring surface point")

    normal = _wgs84_surface_normal_unit(center.xyz_itrf_km)
    tangent = _shadow_subtract(
        displacement,
        _shadow_scale(normal, _shadow_dot(displacement, normal)),
    )
    return _shadow_unit(tangent, label="central shadow track tangent")


def _central_shadow_support_width_km(
    shadow: _EarthFixedSolarShadow,
    center_xyz_itrf_km: tuple[float, float, float],
    track_direction_itrf: tuple[float, float, float],
) -> float:
    """Return the full cross-track support span of a closed shadow footprint.

    Each azimuth selects one generator of the physical umbral/antumbral cone.
    Its first lawful intersection with WGS-84 is a point on the instantaneous
    mean-limb path boundary. Projecting the complete boundary onto the local
    cross-track direction captures the tilted footprint; intersecting only a
    centered chord does not.
    """

    surface_normal = _wgs84_surface_normal_unit(center_xyz_itrf_km)
    tangent = _shadow_subtract(
        track_direction_itrf,
        _shadow_scale(
            surface_normal,
            _shadow_dot(track_direction_itrf, surface_normal),
        ),
    )
    tangent = _shadow_unit(tangent, label="central shadow track tangent")
    cross_track = _shadow_unit(
        _shadow_cross(surface_normal, tangent),
        label="central shadow cross-track direction",
    )

    axis_unit = shadow.axis_unit_away_from_sun
    reference = (0.0, 0.0, 1.0) if abs(axis_unit[2]) < 0.9 else (1.0, 0.0, 0.0)
    cone_east = _shadow_unit(
        _shadow_cross(axis_unit, reference),
        label="central shadow cone basis",
    )
    cone_north = _shadow_cross(axis_unit, cone_east)
    projections: list[float] = []

    for index in range(_SOLAR_FOOTPRINT_AZIMUTH_SAMPLES):
        azimuth = math.tau * index / _SOLAR_FOOTPRINT_AZIMUTH_SAMPLES
        radial = _shadow_add(
            _shadow_scale(cone_east, math.cos(azimuth)),
            _shadow_scale(cone_north, math.sin(azimuth)),
        )
        generator_origin = _shadow_add(
            shadow.fundamental_plane_point_xyz_km,
            _shadow_scale(radial, shadow.central_radius_km),
        )
        generator_direction = _shadow_add(
            axis_unit,
            _shadow_scale(radial, -shadow.central_cone_slope),
        )
        _margin_km2, roots = _wgs84_line_intersection_parameters(
            generator_origin,
            generator_direction,
        )
        if roots is None:
            continue
        lawful_roots = tuple(
            root
            for root in roots
            if root >= shadow.axis_projection_km
        )
        if not lawful_roots:
            continue
        boundary_xyz = _shadow_add(
            generator_origin,
            _shadow_scale(generator_direction, min(lawful_roots)),
        )
        projections.append(
            _shadow_dot(
                _shadow_subtract(boundary_xyz, center_xyz_itrf_km),
                cross_track,
            )
        )

    if len(projections) != _SOLAR_FOOTPRINT_AZIMUTH_SAMPLES:
        raise _SearchLimitReached(
            "central-shadow footprint is not a closed two-limit product at this epoch"
        )
    return max(projections) - min(projections)


def _solve_solar_umbral_width_km(
    calc: EclipseCalculator,
    jd_ut: float,
) -> float:
    shadow = _earth_fixed_solar_shadow(calc, jd_ut)
    if shadow is None:
        return 0.0
    center = _axis_surface_point_from_shadow(shadow)
    if center is None:
        return 0.0
    track_direction = _solar_axis_track_direction_itrf(calc, jd_ut, center)
    return _central_shadow_support_width_km(
        shadow,
        center.xyz_itrf_km,
        track_direction,
    )


# ---------------------------------------------------------------------------
# Vertex name helper (heptagonal esoteric labelling)
# ---------------------------------------------------------------------------

def vertex_name(side_index: int) -> str:
    """Return the vertex label for a heptagon side index (0–6)."""
    names = ["GC", "V1", "V2", "V3", "V4", "V5", "V6"]
    return names[side_index % HEPTAGON_SIDES]


# ---------------------------------------------------------------------------
# Module-level convenience wrapper
# ---------------------------------------------------------------------------

def next_solar_eclipse_at_location(
    jd_start: float,
    latitude: float,
    longitude: float,
    *,
    elevation_m: float = 0.0,
    kind: str = "any",
    max_lunations: int = 360,
    reader=None,
) -> SolarEclipseLocalCircumstances:
    """Return local sky circumstances for the next solar eclipse visible at *latitude*, *longitude*.

    Module-level convenience wrapper around
    ``EclipseCalculator.next_solar_eclipse_at_location``.

    All computation is performed by Moira's DE441-backed apparent-position
    pipeline.  See the class method docstring for the full derivation
    methodology and authority citations.

    Parameters
    ----------
    jd_start : float
        Julian Day (UT) to start searching from.
    latitude : float
        Observer geodetic latitude in degrees (positive north).
    longitude : float
        Observer geodetic longitude in degrees (positive east).
    elevation_m : float
        Observer elevation above the geoid in metres.
    kind : str
        Eclipse type filter: 'any', 'total', 'annular', 'partial', 'central', or 'hybrid'.
    max_lunations : int
        Maximum lunations to scan before raising RuntimeError.
    reader : KernelReader | None
        Optional pre-constructed kernel reader.

    Returns
    -------
    SolarEclipseLocalCircumstances
    """
    from .spk_reader import get_reader as _get_reader

    calc = EclipseCalculator(reader=reader or _get_reader())
    return calc.next_solar_eclipse_at_location(
        jd_start,
        latitude,
        longitude,
        elevation_m=elevation_m,
        kind=kind,
        max_lunations=max_lunations,
    )
