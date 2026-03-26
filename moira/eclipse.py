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
    Owns: eclipse geometry computation, eclipse classification, event search
    (lunar and solar), contact solving dispatch, observer local circumstances
    assembly, Saros/Metonic cycle indexing, Galactic Center and Aubrey stone
    positioning.
    Delegates: raw planet/node vector computation (moira.planets, moira.nodes),
    time-scale conversion (moira.julian), eclipse geometry primitives
    (moira.eclipse_geometry), search refinement (moira.eclipse_search), canon
    contact solving (moira.eclipse_canon), native contact solving
    (moira.eclipse_contacts), light-time corrections (moira.corrections).

Import-time side effects: None

External dependency assumptions:
    - DE441 SPK kernel must be accessible via moira.spk_reader.get_reader()
      (loaded lazily on first EclipseCalculator method call).
    - jplephem must be importable (used internally by SpkReader).

Public surface / exports:
    EclipseType, EclipseData, EclipseEvent, LunarEclipseAnalysis,
    LocalContactCircumstances, LunarEclipseLocalCircumstances,
    SolarBodyCircumstances, SolarEclipseLocalCircumstances,
    LunarEclipseAnalysisMode, EclipseCalculator
"""


import math
from dataclasses import dataclass
from datetime import datetime, timezone

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
from .julian import datetime_from_jd, decimal_year, jd_from_datetime, ut_to_tt, ut_to_tt_nasa_canon
from .planets import (
    _approx_year,
    _barycentric,
    _earth_barycentric,
    _geocentric,
    planet_at,
    sky_position_at,
)
from .nodes import true_node
from .spk_reader import get_reader, SpkReader
from .phenomena import next_moon_phase
from .transits import last_full_moon, last_new_moon
from .coordinates import icrf_to_true_ecliptic
from .eclipse_canon import (
    DEFAULT_LUNAR_CANON_METHOD,
    LunarCanonContacts,
    find_lunar_contacts_canon,
    lunar_canon_source_model,
    lunar_canon_geometry,
)
from .eclipse_contacts import LunarEclipseContacts, find_lunar_contacts
from .corrections import apply_light_time

__all__ = [
    "EclipseData", "EclipseEvent", "EclipseType", "EclipseCalculator",
    "SolarBodyCircumstances", "SolarEclipseLocalCircumstances",
    "LocalContactCircumstances", "LunarEclipseAnalysis",
    "LunarEclipseLocalCircumstances",
    # Phase 3 — path/where geometry vessel (Defer.Design + Defer.Validation)
    "SolarEclipsePath",
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
    Typed vessel for the geographic path of a solar eclipse's central line.

    Design vessel — Phase 3.  Computation is deferred until a typed
    path/circumstance surface is designed with full validation coverage.

    Doctrine
    --------
    A solar eclipse path ("where" surface) encodes the geographic track of
    the Moon's umbral (or antumbral) shadow across the Earth's surface.
    It is distinct from the local-circumstances surface
    (:class:`SolarEclipseLocalCircumstances`) which answers "what happens at
    a specific observer location."

    Swiss Ephemeris ``swe_sol_eclipse_where`` and ``swe_sol_eclipse_how``
    expose this as raw float arrays indexed by undocumented integer offsets.
    This vessel replaces those arrays with named, typed fields.

    Real blockers before implementation (Blocker B + Blocker C):
        - No public path-computation function exists yet; the geometry
          (umbra/penumbra conic intersection with Earth's ellipsoid) requires
          careful design around the WGS-84 / spherical Earth choice.
        - Validation requires comparison against NASA eclipse path shapefiles
          or USNO data; the comparison infrastructure is not yet in place.

    Validation plan (must exist before ``status=implemented``):
        - ≥10 historical total/annular eclipses from the NASA Five Millennium
          Atlas compared at ≥5 points along each central line.
        - Tolerance: central-line crossing latitude within ±0.01°, duration
          at maximum eclipse within ±2 s.

    Fields
    ------
    central_line_lats : tuple of float
        Geographic latitudes (degrees, north positive) along the central line,
        sampled at equal time intervals from first to last contact.
    central_line_lons : tuple of float
        Geographic longitudes (degrees, east positive) at the same sample
        points.  Same length as ``central_line_lats``.
    umbral_width_km : float
        Width of the umbral (or antumbral) shadow path in kilometres at
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
            - Carry the four mutually-exclusive eclipse-kind flags (partial,
              annular, total, hybrid)
            - Carry the umbral and penumbral magnitude scalars
            - Serve a human-readable string representation via __str__
        Non-responsibilities:
            - Computing eclipse geometry
            - Classifying eclipses (delegates to _classify)
        Dependencies:
            - Populated by _classify() in moira.eclipse
        Structural invariants:
            - Exactly one of is_partial, is_annular, is_total, is_hybrid is
              True for a real eclipse; all False for no-eclipse
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
    solar_topocentric_separation:float
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
            - Carry the UT Julian Day of greatest eclipse (jd_ut)
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
        return datetime_from_jd(self.jd_ut)


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
            - Search for next/previous lunar and solar eclipses
            - Produce specialist-facing LunarEclipseAnalysis bundles
            - Solve observer-specific local circumstances for lunar and solar
              eclipses
            - Cache search results to avoid redundant lunation walks
        Non-responsibilities:
            - Raw planet/node vector computation (delegates to moira.planets,
              moira.nodes)
            - Eclipse geometry primitives (delegates to moira.eclipse_geometry)
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
        "frozen": ["calculate", "calculate_jd", "next_lunar_eclipse",
                   "previous_lunar_eclipse", "next_lunar_eclipse_canon",
                   "previous_lunar_eclipse_canon", "analyze_lunar_eclipse",
                   "lunar_local_circumstances", "solar_local_circumstances",
                   "next_solar_eclipse", "previous_solar_eclipse"],
        "internal": ["_calculate_jd_internal", "_lunar_shadow_axis_distance_km",
                     "_refine_lunar_maximum_for_kind", "_lunar_shadow_geometry_tt",
                     "_native_solar_conjunction_distance_deg",
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

    def __init__(self, reader: SpkReader | None = None) -> None:
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
        self._lunar_search_cache: dict[tuple[float, bool, int], dict[str, EclipseEvent]] = {}
        self._solar_search_cache: dict[tuple[float, bool, int], dict[str, EclipseEvent]] = {}

    def _jd_tt_from_ut(
        self,
        jd_ut: float,
        *,
        delta_t_mode: str = "native",
    ) -> float:
        year, month, *_ = _approx_year(jd_ut)
        year_hint = decimal_year(year, month)
        if delta_t_mode == "native":
            return ut_to_tt(jd_ut, year_hint)
        if delta_t_mode == "nasa_canon":
            return ut_to_tt_nasa_canon(jd_ut, year_hint)
        raise ValueError(f"Unsupported delta_t_mode: {delta_t_mode!r}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate(self, dt: datetime) -> EclipseData:
        """
        Compute complete eclipse geometry for a given UTC datetime.

        Parameters
        ----------
        dt : timezone-aware datetime (naïve treated as UTC)

        Returns
        -------
        EclipseData with all positions, eclipse status, and cycle data.
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return self.calculate_jd(jd_from_datetime(dt))

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
        )
        saros_idx = _saros_index_jd(jd)
        metonic_year, m_reset = _metonic_position_jd(jd, sun_lon, moon_lon)

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
            solar_topocentric_separation=angular_sep,
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
        year, month, *_ = _approx_year(jd_ut)
        jd_tt = ut_to_tt(jd_ut, decimal_year(year, month))
        sun_xyz = _geocentric(Body.SUN, jd_tt, self._reader)
        if retarded_moon:
            earth_ssb = _earth_barycentric(jd_tt, self._reader)
            moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, self._reader, earth_ssb, _barycentric)
        else:
            moon_xyz = _geocentric(Body.MOON, jd_tt, self._reader)
        sun_lon, sun_lat, _sun_dist = icrf_to_true_ecliptic(jd_tt, sun_xyz)
        moon_lon, moon_lat, _moon_dist = icrf_to_true_ecliptic(jd_tt, moon_xyz)
        return _angular_separation(sun_lon, sun_lat, moon_lon, moon_lat)

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
        """Compute complete eclipse geometry for a given UT Julian Day."""
        return self._calculate_jd_internal(jd, retarded_moon=False)

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
                ut_to_tt_nasa_canon(event.jd_ut),
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
        for a specialist eclipse subsystem.
        """
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
        overlap = separation < (
            event.data.sun_apparent_radius + event.data.moon_apparent_radius
        )

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

        cache_key = (jd_start, backward, max_lunations, use_canon)
        results = self._lunar_search_cache.get(cache_key)
        if results is None:
            results = {}
            if backward:
                phase_jd = last_full_moon(jd_start, reader=self._reader)
            else:
                phase_jd = next_moon_phase("Full Moon", jd_start, reader=self._reader).jd_ut

            for _ in range(max_lunations):
                phase_data = self.calculate_jd(phase_jd)
                if phase_data.is_eclipse_season:
                    if use_canon:
                        best_jd = find_lunar_contacts_canon(self, phase_jd).greatest_ut
                        best_data = self.calculate_jd(best_jd)
                        event = EclipseEvent(jd_ut=best_jd, data=best_data)
                        if "any" not in results and _matches_lunar_kind(best_data, "any"):
                            results["any"] = event
                        if "total" not in results and _matches_lunar_kind(best_data, "total"):
                            results["total"] = event
                        if "partial" not in results and _matches_lunar_kind(best_data, "partial"):
                            results["partial"] = event
                        if "penumbral" not in results and _matches_lunar_kind(best_data, "penumbral"):
                            results["penumbral"] = event
                    else:
                        best_jd_umbral = self._refine_lunar_maximum_for_kind(phase_jd, "total")
                        best_data_umbral = self._calculate_jd_internal(best_jd_umbral, retarded_moon=True)
                        event_umbral = EclipseEvent(jd_ut=best_jd_umbral, data=best_data_umbral)
                        best_jd_pen = self._refine_lunar_maximum_for_kind(phase_jd, "penumbral")
                        best_data_pen = self._calculate_jd_internal(best_jd_pen, retarded_moon=False)
                        event_pen = EclipseEvent(jd_ut=best_jd_pen, data=best_data_pen)

                        if "any" not in results:
                            results["any"] = event_umbral if best_data_umbral.is_lunar_eclipse else event_pen
                        if "total" not in results and _matches_lunar_kind(best_data_umbral, "total"):
                            results["total"] = event_umbral
                        if "partial" not in results and _matches_lunar_kind(best_data_umbral, "partial"):
                            results["partial"] = event_umbral
                        if "penumbral" not in results and _matches_lunar_kind(best_data_pen, "penumbral"):
                            results["penumbral"] = event_pen
                    if len(results) == 4:
                        break

                if backward:
                    phase_jd = last_full_moon(phase_jd - 1.0, reader=self._reader)
                else:
                    phase_jd = next_moon_phase("Full Moon", phase_jd + 1.0, reader=self._reader).jd_ut

            self._lunar_search_cache[cache_key] = results

        if kind_key in results:
            return results[kind_key]

        direction = "previous" if backward else "next"
        raise RuntimeError(f"No {direction} lunar eclipse of kind {kind!r} found")

    def _search_solar_eclipse(
        self,
        jd_start: float,
        *,
        kind: str,
        backward: bool,
        max_lunations: int = 180,
    ) -> EclipseEvent:
        """
        Search successive new moons until a solar eclipse of the requested kind
        is found, then refine to the eclipse maximum near that new moon.
        """
        kind_key = kind.strip().lower().replace("-", "_").replace(" ", "_")
        if kind_key not in {"any", "total", "annular", "partial", "central", "hybrid"}:
            raise ValueError(f"Unsupported solar eclipse kind: {kind!r}")

        cache_key = (jd_start, backward, max_lunations)
        results = self._solar_search_cache.get(cache_key)
        if results is None:
            results = {}
            if backward:
                phase_jd = last_new_moon(jd_start, reader=self._reader)
            else:
                phase_jd = next_moon_phase("New Moon", jd_start, reader=self._reader).jd_ut

            for _ in range(max_lunations):
                phase_data = self.calculate_jd(phase_jd)
                if phase_data.is_eclipse_season:
                    best_jd = _refine_solar_maximum(self, phase_jd)
                    best_data = self.calculate_jd(best_jd)
                    event = EclipseEvent(jd_ut=best_jd, data=best_data)
                    if "any" not in results and _matches_solar_kind(best_data, "any"):
                        results["any"] = event
                    if "partial" not in results and _matches_solar_kind(best_data, "partial"):
                        results["partial"] = event
                    if "annular" not in results and _matches_solar_kind(best_data, "annular"):
                        results["annular"] = event
                    if "hybrid" not in results and _matches_solar_kind(best_data, "hybrid"):
                        results["hybrid"] = event
                    if "total" not in results and _matches_solar_kind(best_data, "total"):
                        results["total"] = event
                    if "central" not in results and _matches_solar_kind(best_data, "central"):
                        results["central"] = event
                    if len(results) == 6:
                        break

                if backward:
                    phase_jd = last_new_moon(phase_jd - 1.0, reader=self._reader)
                else:
                    phase_jd = next_moon_phase("New Moon", phase_jd + 1.0, reader=self._reader).jd_ut

            self._solar_search_cache[cache_key] = results

        if kind_key in results:
            return results[kind_key]

        direction = "previous" if backward else "next"
        raise RuntimeError(f"No {direction} solar eclipse of kind {kind!r} found")

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
        c2c      = angular_sep
        c2c_best = max(0.0, c2c - moon_parallax)   # best-case across Earth

        if c2c_best > sun_radius + moon_radius:
            return _none

        if c2c_best < abs(sun_radius - moon_radius):
            if moon_radius > sun_radius:
                mag = 1.0 + (moon_radius - sun_radius - c2c_best) / (2 * sun_radius)
                et  = EclipseType(False, False, True, False, mag, mag)
            else:
                moon_radius_near = _topocentric_near_moon_radius(moon_parallax)
                if moon_radius_near > sun_radius:
                    et = EclipseType(False, False, False, True, 1.0, 1.0)
                    return et, True, False, 1.0
                mag = 1.0 - (sun_radius - moon_radius + c2c_best) / (2 * sun_radius)
                et  = EclipseType(False, True, False, False, mag, mag)
            return et, True, False, mag

        mag = (sun_radius + moon_radius - c2c_best) / (2 * sun_radius)
        et  = EclipseType(True, False, False, False, mag, mag)
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
                return et, False, False, 0.0

        shadow_sep = shadow_axis_offset_deg(angular_sep)

        if shadow_sep < shadow_radius + moon_radius:
            umbral_mag = lunar_umbral_magnitude(shadow_radius, moon_radius, shadow_sep)
            pen_mag = lunar_penumbral_magnitude(penumbra_radius, moon_radius, shadow_sep)

            if shadow_sep < shadow_radius - moon_radius:
                et = EclipseType(False, False, True, False, umbral_mag, pen_mag)
            else:
                et = EclipseType(True, False, False, False, umbral_mag, pen_mag)
            return et, False, True, umbral_mag

        # Penumbral only — not a "real" eclipse for most purposes
        pen_limit = penumbra_radius + moon_radius
        if shadow_sep < pen_limit:
            pen_mag = lunar_penumbral_magnitude(penumbra_radius, moon_radius, shadow_sep)
            et = EclipseType(False, False, False, False, 0.0, pen_mag)
            return et, False, False, 0.0

    return _none


def _matches_lunar_kind(data: EclipseData, kind: str) -> bool:
    """Return True if *data* matches the requested lunar eclipse kind."""
    if kind == "any":
        return data.is_lunar_eclipse or data.eclipse_type.magnitude_penumbra > 0.0
    if kind == "total":
        return data.is_lunar_eclipse and data.eclipse_type.is_total
    if kind == "partial":
        return data.is_lunar_eclipse and data.eclipse_type.is_partial
    if kind == "penumbral":
        return (not data.is_lunar_eclipse) and data.eclipse_type.magnitude_penumbra > 0.0
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


# ---------------------------------------------------------------------------
# Vertex name helper (heptagonal esoteric labelling)
# ---------------------------------------------------------------------------

def vertex_name(side_index: int) -> str:
    """Return the vertex label for a heptagon side index (0–6)."""
    names = ["GC", "V1", "V2", "V3", "V4", "V5", "V6"]
    return names[side_index % HEPTAGON_SIDES]
