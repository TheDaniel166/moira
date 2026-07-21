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
    SolarBesselianElements, SolarEclipsePath,
    SolarEclipseVisibilityFootprint, LunarEclipseAnalysisMode,
    EclipseCalculator
"""

from __future__ import annotations


import math
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
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
    CalendarDateTime,
    _ut1_to_utc,
    apparent_sidereal_time,
    calendar_datetime_from_jd,
    datetime_from_jd,
    decimal_year_from_jd,
    jd_from_datetime,
    utc_to_ut1,
    ut_to_tt_nasa_canon,
)
from ._ephemeris_time import (
    _ephemeris_tt_to_ut1,
    _reader_identity_at,
    _ut1_to_ephemeris_tt,
)
from . import moira_native as _moira_native
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
    _lunar_canon_axis_geometry_tt,
    _lunar_canon_vectors_tt,
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
    "SolarEclipseFootprintBoundaryKind",
    "SolarEclipsePenumbralContactKind",
    "SolarEclipseFootprintTopology",
    "SolarEclipseFootprintPoint",
    "SolarEclipsePenumbralContact",
    "SolarEclipseFootprintContacts",
    "SolarEclipseLimitTrack",
    "SolarEclipseVisibilityFootprint",
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
            - Expose UTC datetime and BCE-safe calendar convenience properties
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
        "internal": ["datetime_utc", "calendar_utc"]
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

    @property
    def calendar_utc(self) -> CalendarDateTime:
        """Return the greatest epoch in the BCE-safe UTC calendar vessel."""

        return calendar_datetime_from_jd(_ut1_to_utc(self.jd_ut))


class SolarEclipseFootprintBoundaryKind(str, Enum):
    """Named boundary families of the swept penumbral visibility product."""

    PENUMBRAL_NORTH = "penumbral_north"
    PENUMBRAL_SOUTH = "penumbral_south"
    SUNRISE = "sunrise"
    SUNSET = "sunset"


class SolarEclipsePenumbralContactKind(str, Enum):
    """External and optional internal penumbral contacts with WGS 84."""

    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class SolarEclipseFootprintTopology(str, Enum):
    """Topological class of the complete penumbral visibility footprint."""

    ONE_LIMIT_CONNECTED = "one_limit_connected"
    TWO_LIMIT_TWO_LOOP = "two_limit_two_loop"


def _footprint_real(owner: str, name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{owner}.{name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{owner}.{name} must be finite")
    return result


def _footprint_points_coincide(
    left: "SolarEclipseFootprintPoint",
    right: "SolarEclipseFootprintPoint",
) -> bool:
    longitude_residual = abs(
        (left.longitude_deg - right.longitude_deg + 180.0) % 360.0 - 180.0
    )
    return (
        abs(left.jd_ut - right.jd_ut) <= 1.0e-10
        and abs(left.latitude_deg - right.latitude_deg) <= 1.0e-9
        and longitude_residual <= 1.0e-9
    )


@dataclass(frozen=True, slots=True)
class SolarEclipseFootprintPoint:
    """One zero-elevation WGS-84 boundary point at a UT1 epoch."""

    jd_ut: float
    latitude_deg: float
    longitude_deg: float

    def __post_init__(self) -> None:
        owner = type(self).__name__
        for name in ("jd_ut", "latitude_deg", "longitude_deg"):
            object.__setattr__(
                self,
                name,
                _footprint_real(owner, name, getattr(self, name)),
            )
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError(f"{owner}.latitude_deg must be within [-90, 90]")
        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError(f"{owner}.longitude_deg must be within [-180, 180]")

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(_ut1_to_utc(self.jd_ut))

    @property
    def calendar_utc(self) -> CalendarDateTime:
        """Return this boundary epoch in the BCE-safe UTC calendar vessel."""

        return calendar_datetime_from_jd(_ut1_to_utc(self.jd_ut))


@dataclass(frozen=True, slots=True)
class SolarEclipsePenumbralContact:
    """One solved external or internal penumbral tangency."""

    kind: SolarEclipsePenumbralContactKind
    point: SolarEclipseFootprintPoint

    def __post_init__(self) -> None:
        try:
            kind = SolarEclipsePenumbralContactKind(self.kind)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid solar penumbral contact kind") from exc
        object.__setattr__(self, "kind", kind)
        if not isinstance(self.point, SolarEclipseFootprintPoint):
            raise TypeError(
                "SolarEclipsePenumbralContact.point must be a "
                "SolarEclipseFootprintPoint"
            )


@dataclass(frozen=True, slots=True)
class SolarEclipseFootprintContacts:
    """P1/P4 plus the paired optional P2/P3 internal tangencies."""

    p1: SolarEclipsePenumbralContact
    p2: SolarEclipsePenumbralContact | None
    p3: SolarEclipsePenumbralContact | None
    p4: SolarEclipsePenumbralContact

    def __post_init__(self) -> None:
        expected = (
            ("p1", self.p1, SolarEclipsePenumbralContactKind.P1),
            ("p2", self.p2, SolarEclipsePenumbralContactKind.P2),
            ("p3", self.p3, SolarEclipsePenumbralContactKind.P3),
            ("p4", self.p4, SolarEclipsePenumbralContactKind.P4),
        )
        for name, contact, kind in expected:
            if contact is None and name in {"p2", "p3"}:
                continue
            if not isinstance(contact, SolarEclipsePenumbralContact):
                raise TypeError(f"SolarEclipseFootprintContacts.{name} has invalid type")
            if contact.kind is not kind:
                raise ValueError(
                    f"SolarEclipseFootprintContacts.{name} must carry {kind.value}"
                )
        if (self.p2 is None) != (self.p3 is None):
            raise ValueError("P2 and P3 must either both be present or both be absent")
        ordered = tuple(
            contact.point.jd_ut
            for contact in (self.p1, self.p2, self.p3, self.p4)
            if contact is not None
        )
        if any(left >= right for left, right in zip(ordered, ordered[1:])):
            raise ValueError("penumbral contacts must be strictly ordered P1 through P4")


@dataclass(frozen=True, slots=True)
class SolarEclipseLimitTrack:
    """One time-ordered segment of a named footprint boundary component.

    ``component_id`` is local to ``kind`` and identifies one connected
    geometric boundary component. ``segment_id`` is local to that component
    and distinguishes the strictly time-monotone pieces created by a temporal
    fold. Geographic longitude is never used to establish continuity.
    """

    kind: SolarEclipseFootprintBoundaryKind
    component_id: int
    segment_id: int
    points: tuple[SolarEclipseFootprintPoint, ...]

    def __post_init__(self) -> None:
        try:
            kind = SolarEclipseFootprintBoundaryKind(self.kind)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid solar footprint boundary kind") from exc
        object.__setattr__(self, "kind", kind)
        if isinstance(self.component_id, bool) or not isinstance(self.component_id, int):
            raise TypeError("SolarEclipseLimitTrack.component_id must be an integer")
        if self.component_id < 0:
            raise ValueError("SolarEclipseLimitTrack.component_id must be non-negative")
        if isinstance(self.segment_id, bool) or not isinstance(self.segment_id, int):
            raise TypeError("SolarEclipseLimitTrack.segment_id must be an integer")
        if self.segment_id < 0:
            raise ValueError("SolarEclipseLimitTrack.segment_id must be non-negative")
        points = tuple(self.points)
        if len(points) < 2:
            raise ValueError("SolarEclipseLimitTrack requires at least two points")
        if not all(isinstance(point, SolarEclipseFootprintPoint) for point in points):
            raise TypeError(
                "SolarEclipseLimitTrack.points must contain only "
                "SolarEclipseFootprintPoint values"
            )
        if any(
            left.jd_ut >= right.jd_ut
            for left, right in zip(points, points[1:])
        ):
            raise ValueError("SolarEclipseLimitTrack.points must be strictly time ordered")
        object.__setattr__(self, "points", points)


@dataclass(frozen=True, slots=True)
class SolarEclipseVisibilityFootprint:
    """Complete mean-limb boundary tracks of solar-eclipse visibility.

    This is the swept penumbral-cone product on the zero-elevation WGS-84
    ellipsoid. It is distinct from the umbral/antumbral central line in
    :class:`SolarEclipsePath` and from observer-local apparent circumstances.
    """

    event: EclipseEvent
    greatest: SolarEclipseFootprintPoint
    topology: SolarEclipseFootprintTopology
    contacts: SolarEclipseFootprintContacts
    tracks: tuple[SolarEclipseLimitTrack, ...]
    ephemeris: str
    surface_model: str = field(default="WGS84_ZERO_ELEVATION", init=False)
    limb_model: str = field(default="SPHERICAL_MEAN_LIMB", init=False)
    time_scale: str = field(default="UT1", init=False)
    atmospheric_refraction: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.event, EclipseEvent):
            raise TypeError("SolarEclipseVisibilityFootprint.event must be an EclipseEvent")
        if not self.event.data.is_solar_eclipse:
            raise ValueError("footprint event must be a solar eclipse")
        if not isinstance(self.greatest, SolarEclipseFootprintPoint):
            raise TypeError(
                "SolarEclipseVisibilityFootprint.greatest must be a "
                "SolarEclipseFootprintPoint"
            )
        if abs(self.greatest.jd_ut - self.event.jd_ut) > 1.0e-10:
            raise ValueError("greatest point epoch must equal the event epoch")
        try:
            topology = SolarEclipseFootprintTopology(self.topology)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid solar eclipse footprint topology") from exc
        object.__setattr__(self, "topology", topology)
        eclipse_type = self.event.data.eclipse_type
        if topology is SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP and (
            eclipse_type.is_partial
            or not (
                eclipse_type.is_annular
                or eclipse_type.is_total
                or eclipse_type.is_hybrid
            )
        ):
            raise ValueError(
                "two-limit footprint requires a central solar eclipse event"
            )
        if not isinstance(self.contacts, SolarEclipseFootprintContacts):
            raise TypeError(
                "SolarEclipseVisibilityFootprint.contacts must be "
                "SolarEclipseFootprintContacts"
            )
        tracks = tuple(self.tracks)
        if not tracks or not all(isinstance(track, SolarEclipseLimitTrack) for track in tracks):
            raise ValueError(
                "SolarEclipseVisibilityFootprint.tracks must contain limit tracks"
            )
        identities = tuple(
            (track.kind, track.component_id, track.segment_id)
            for track in tracks
        )
        if len(set(identities)) != len(identities):
            raise ValueError(
                "footprint track kind/component/segment identities must be unique"
            )
        p1_jd = self.contacts.p1.point.jd_ut
        p4_jd = self.contacts.p4.point.jd_ut
        if not p1_jd < self.event.jd_ut < p4_jd:
            raise ValueError("greatest eclipse epoch must lie strictly within P1/P4")
        if (
            self.contacts.p2 is not None
            and self.contacts.p3 is not None
            and not (
                self.contacts.p2.point.jd_ut
                < self.event.jd_ut
                < self.contacts.p3.point.jd_ut
            )
        ):
            raise ValueError(
                "two-limit greatest eclipse epoch must lie strictly within P2/P3"
            )
        if any(
            point.jd_ut < p1_jd - 1.0e-10 or point.jd_ut > p4_jd + 1.0e-10
            for track in tracks
            for point in track.points
        ):
            raise ValueError("footprint track points must lie within P1 through P4")
        kinds = {track.kind for track in tracks}
        if not {
            SolarEclipseFootprintBoundaryKind.SUNRISE,
            SolarEclipseFootprintBoundaryKind.SUNSET,
        }.issubset(kinds):
            raise ValueError("footprint requires sunrise and sunset boundary tracks")
        penumbral_kinds = kinds & {
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
        }
        if topology is SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED:
            if self.contacts.p2 is not None or len(penumbral_kinds) != 1:
                raise ValueError(
                    "one-limit topology requires no P2/P3 and one penumbral limit"
                )
        elif self.contacts.p2 is None or len(penumbral_kinds) != 2:
            raise ValueError(
                "two-limit topology requires P2/P3 and both penumbral limits"
            )
        horizon_tracks = tuple(
            track
            for track in tracks
            if track.kind in {
                SolarEclipseFootprintBoundaryKind.SUNRISE,
                SolarEclipseFootprintBoundaryKind.SUNSET,
            }
        )
        horizon_points = tuple(
            point
            for track in horizon_tracks
            for point in track.points
        )
        if topology is SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP:
            p2 = self.contacts.p2
            p3 = self.contacts.p3
            if p2 is None or p3 is None:
                raise ValueError("two-limit topology requires P2/P3")
            p2_jd = p2.point.jd_ut
            p3_jd = p3.point.jd_ut
            if any(
                not (
                    p1_jd - 1.0e-10
                    <= track.points[0].jd_ut
                    < track.points[-1].jd_ut
                    <= p2_jd + 1.0e-10
                    or p3_jd - 1.0e-10
                    <= track.points[0].jd_ut
                    < track.points[-1].jd_ut
                    <= p4_jd + 1.0e-10
                )
                for track in horizon_tracks
            ):
                raise ValueError(
                    "two-limit sunrise/sunset tracks must remain within "
                    "P1-P2 or P3-P4"
                )
        contact_points = tuple(
            contact.point
            for contact in (
                self.contacts.p1,
                self.contacts.p2,
                self.contacts.p3,
                self.contacts.p4,
            )
            if contact is not None
        )
        if any(
            not any(
                _footprint_points_coincide(contact_point, horizon_point)
                for horizon_point in horizon_points
            )
            for contact_point in contact_points
        ):
            raise ValueError(
                "every penumbral contact must belong to the sunrise/sunset graph"
            )
        penumbral_components = {
            (track.kind, track.component_id)
            for track in tracks
            if track.kind in penumbral_kinds
        }
        for kind in penumbral_kinds:
            component_ids = tuple(
                sorted(
                    component_id
                    for candidate_kind, component_id in penumbral_components
                    if candidate_kind is kind
                )
            )
            if component_ids != (0,):
                raise ValueError(
                    "each admitted penumbral boundary kind must contain exactly "
                    "one connected component"
                )
        penumbral_horizon_incidences: dict[
            SolarEclipseFootprintBoundaryKind,
            tuple[SolarEclipseFootprintPoint, ...],
        ] = {}
        for kind, component_id in penumbral_components:
            component_tracks = tuple(
                track
                for track in tracks
                if track.kind is kind and track.component_id == component_id
            )
            segment_ids = tuple(sorted(track.segment_id for track in component_tracks))
            if segment_ids != tuple(range(len(segment_ids))):
                raise ValueError(
                    "footprint segment identifiers must be contiguous within a component"
                )
            endpoints = tuple(
                endpoint
                for track in component_tracks
                for endpoint in (track.points[0], track.points[-1])
            )
            horizon_incidence_list: list[SolarEclipseFootprintPoint] = []
            for endpoint in endpoints:
                if not any(
                    _footprint_points_coincide(endpoint, horizon_point)
                    for horizon_point in horizon_points
                ):
                    continue
                if not any(
                    _footprint_points_coincide(endpoint, admitted)
                    for admitted in horizon_incidence_list
                ):
                    horizon_incidence_list.append(endpoint)
            horizon_incidence = tuple(horizon_incidence_list)
            if len(horizon_incidence) != 2:
                raise ValueError(
                    "each connected penumbral component must have exactly two "
                    "sunrise/sunset incidences: "
                    f"{kind.value}[{component_id}] has {len(horizon_incidence)} "
                    f"across {len(component_tracks)} segments"
                )
            penumbral_horizon_incidences[kind] = horizon_incidence
            for endpoint in endpoints:
                if any(
                    _footprint_points_coincide(endpoint, candidate)
                    for candidate in horizon_incidence
                ):
                    continue
                coincident_internal = sum(
                    _footprint_points_coincide(endpoint, candidate)
                    for candidate in endpoints
                )
                if coincident_internal != 2:
                    raise ValueError(
                        "a non-horizon penumbral endpoint must pair with exactly "
                        "one segment endpoint at a temporal fold"
                    )
        if topology is SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP:
            north_incidences = penumbral_horizon_incidences[
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH
            ]
            south_incidences = penumbral_horizon_incidences[
                SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH
            ]
            if any(
                _footprint_points_coincide(north, south)
                for north in north_incidences
                for south in south_incidences
            ):
                raise ValueError(
                    "two-limit topology requires disjoint north/south "
                    "horizon incidences"
                )
        if not isinstance(self.ephemeris, str) or not self.ephemeris.strip():
            raise ValueError("SolarEclipseVisibilityFootprint.ephemeris is required")
        object.__setattr__(self, "tracks", tracks)


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
        assembled by LunarEclipseLocalCircumstances for each of the up to six
        contacts and the separate greatest-eclipse instant. Without it,
        observer-facing eclipse reports would have no structured way to carry
        per-instant azimuth, altitude, and visibility.

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
        lunar_canon_method: LunarCanonMethodId | None = None,
    ) -> EclipseData:
        """Internal eclipse calculation with selectable lunar event geometry."""
        if lunar_canon_method is not None and retarded_moon:
            raise ValueError(
                "lunar_canon_method and retarded_moon are mutually exclusive"
            )
        jd_tt = self._jd_tt_from_ut(jd, delta_t_mode=delta_t_mode)

        if lunar_canon_method is not None:
            sun_xyz, moon_xyz = _lunar_canon_vectors_tt(
                self,
                jd_tt,
                method=lunar_canon_method,
            )
        else:
            sun_xyz = _geocentric(Body.SUN, jd_tt, self._reader)
        if lunar_canon_method is None and retarded_moon:
            earth_ssb = _earth_barycentric(jd_tt, self._reader)
            moon_xyz, _ = apply_light_time(Body.MOON, jd_tt, self._reader, earth_ssb, _barycentric)
        elif lunar_canon_method is None:
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
            if lunar_canon_method is None:
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
            else:
                (
                    native_lunar_axis_km,
                    _northward_offset_km,
                    canon_moon_distance_km,
                    canon_moon_radius_deg,
                    canon_umbra_radius_deg,
                    canon_penumbra_radius_deg,
                ) = _lunar_canon_axis_geometry_tt(
                    self,
                    jd_tt,
                    method=lunar_canon_method,
                )
                native_lunar_moon_radius_km = (
                    math.radians(canon_moon_radius_deg)
                    * canon_moon_distance_km
                )
                native_lunar_umbra_radius_km = (
                    math.radians(canon_umbra_radius_deg)
                    * canon_moon_distance_km
                )
                native_lunar_penumbra_radius_km = (
                    math.radians(canon_penumbra_radius_deg)
                    * canon_moon_distance_km
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

    def solar_eclipse_footprint(
        self,
        jd_start: float,
        *,
        kind: str = "any",
        backward: bool = False,
        sample_count: int = 181,
    ) -> SolarEclipseVisibilityFootprint:
        """Return the complete mean-limb penumbral visibility boundary.

        The product sweeps Moira's DE441 Earth-reception penumbral cone over
        the zero-elevation WGS-84 ellipsoid. It includes the north/south
        penumbral path limits that exist for the solved topology, sunrise and
        sunset limb-closure branches, P1/P4, and optional P2/P3 contacts.
        ``sample_count`` controls emitted interior density, not the solved
        component/segment graph or its structural endpoints.
        Refraction, observer elevation, magnitude contours, and local
        circumstances are deliberately outside this physical product.
        """

        if isinstance(jd_start, bool) or not isinstance(jd_start, Real):
            raise TypeError("jd_start must be a real Julian Day")
        jd_start = float(jd_start)
        if not math.isfinite(jd_start):
            raise ValueError("jd_start must be finite")
        if isinstance(sample_count, bool) or not isinstance(sample_count, int):
            raise TypeError("sample_count must be an integer")
        if not _SOLAR_PENUMBRAL_MIN_SAMPLES <= sample_count <= _SOLAR_PENUMBRAL_MAX_SAMPLES:
            raise ValueError(
                "sample_count must be between "
                f"{_SOLAR_PENUMBRAL_MIN_SAMPLES} and "
                f"{_SOLAR_PENUMBRAL_MAX_SAMPLES}"
            )

        event = self._search_solar_eclipse(
            jd_start,
            kind=kind,
            backward=backward,
        )
        jd_tt = _ut1_to_ephemeris_tt(event.jd_ut, self._reader)
        identity = _reader_identity_at(self._reader, jd_tt)
        if (
            identity is None
            or identity.planetary_ephemeris != "DE441"
            or identity.lunar_ephemeris != "LE441"
        ):
            raise RuntimeError(
                "solar eclipse footprints are admitted only for a "
                "content-identified DE441/LE441 reader"
            )

        contacts, topology = _solve_solar_penumbral_contacts(self, event.jd_ut)
        axis_point = _solar_axis_surface_point(self, event.jd_ut)
        if axis_point is None:
            greatest_point = _solve_solar_penumbral_greatest_point(
                self,
                event.jd_ut,
            )
            greatest_lat = greatest_point.latitude_deg
            greatest_lon = greatest_point.longitude_deg
        else:
            greatest_lat = axis_point.latitude_deg
            greatest_lon = axis_point.longitude_deg
        greatest = SolarEclipseFootprintPoint(
            jd_ut=event.jd_ut,
            latitude_deg=greatest_lat,
            longitude_deg=greatest_lon,
        )
        tracks = _solve_solar_penumbral_tracks(
            self,
            contacts,
            topology,
            sample_count=sample_count,
        )
        return SolarEclipseVisibilityFootprint(
            event=event,
            greatest=greatest,
            topology=topology,
            contacts=contacts,
            tracks=tracks,
            ephemeris=identity.summary_label,
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

    def _lunar_eclipse_near_syzygy(
        self,
        phase_jd: float,
        *,
        kind_key: str,
        use_canon: bool,
    ) -> EclipseEvent | None:
        """Refine and classify one full-moon neighborhood under Python doctrine."""
        phase_data = self.calculate_jd(phase_jd)
        if not phase_data.is_eclipse_season:
            return None

        if use_canon:
            best_jd = find_lunar_contacts_canon(self, phase_jd).greatest_ut
            best_data = self._calculate_jd_internal(
                best_jd,
                delta_t_mode="nasa_canon",
                lunar_canon_method=DEFAULT_LUNAR_CANON_METHOD,
            )
            if _matches_lunar_kind(best_data, kind_key):
                return EclipseEvent(jd_ut=best_jd, data=best_data)
            return None

        # Umbral and penumbral events intentionally retain their separately
        # declared native vector policies. Compute only the requested family.
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
                return EclipseEvent(jd_ut=best_jd, data=best_data)

        if kind_key in {"any", "penumbral"}:
            best_jd = self._refine_lunar_maximum_for_kind(phase_jd, "penumbral")
            best_data = self._calculate_jd_internal(
                best_jd,
                retarded_moon=False,
            )
            if _matches_lunar_kind(best_data, "penumbral"):
                return EclipseEvent(jd_ut=best_jd, data=best_data)
        return None

    def _solar_eclipse_near_syzygy(
        self,
        phase_jd: float,
        *,
        kind_key: str,
    ) -> EclipseEvent | None:
        """Refine and classify one new-moon neighborhood under Python doctrine."""
        phase_data = self.calculate_jd(phase_jd)
        if not phase_data.is_eclipse_season:
            return None

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
        if not kind_matches:
            return None
        return EclipseEvent(jd_ut=best_jd, data=best_data)

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

        def is_in_requested_direction(candidate_jd: float) -> bool:
            # The syzygy and the refined eclipse maximum are distinct epochs.
            # A phase found on the requested side of the seed can therefore
            # refine to a maximum on the wrong side and must be skipped.
            return candidate_jd < jd_start if backward else candidate_jd > jd_start

        if backward:
            phase_jd = last_full_moon(jd_start, reader=self._reader)
        else:
            phase_jd = next_moon_phase("Full Moon", jd_start, reader=self._reader).jd_ut

        for _ in range(max_lunations):
            event = self._lunar_eclipse_near_syzygy(
                phase_jd,
                kind_key=kind_key,
                use_canon=use_canon,
            )
            if event is not None and is_in_requested_direction(event.jd_ut):
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

        def is_in_requested_direction(candidate_jd: float) -> bool:
            # New Moon and the refined solar maximum need not occur in the
            # same order relative to the caller's seed.
            return candidate_jd < jd_start if backward else candidate_jd > jd_start

        if backward:
            phase_jd = last_new_moon(jd_start, reader=self._reader)
        else:
            phase_jd = next_moon_phase("New Moon", jd_start, reader=self._reader).jd_ut

        lunations_searched = 0
        while max_lunations is None or lunations_searched < max_lunations:
            lunations_searched += 1
            event = self._solar_eclipse_near_syzygy(phase_jd, kind_key=kind_key)
            if event is not None and is_in_requested_direction(event.jd_ut):
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

    def _native_eclipse_syzygy_candidates(
        self,
        family: str,
        jd_start: float,
        jd_end: float,
    ) -> list[float] | None:
        """Return native-discovered candidate epochs in UT1, or None if unavailable.

        Native owns only the dense TT separation scan. The 2-degree ceiling is
        intentionally a loose superset gate, not eclipse classification.
        """
        native_reader = self._reader
        if not isinstance(native_reader, SpkReader):
            primary_reader = getattr(
                native_reader,
                "_primary_planetary_reader",
                None,
            )
            native_reader = primary_reader() if callable(primary_reader) else None
        if not isinstance(native_reader, SpkReader):
            return None
        native_find = getattr(
            _moira_native,
            f"find_{family}_syzygy_candidates",
            None,
        )
        if not callable(native_find):
            return None

        padded_start_ut1 = jd_start - _NATIVE_BULK_ECLIPSE_PADDING_DAYS
        padded_end_ut1 = jd_end + _NATIVE_BULK_ECLIPSE_PADDING_DAYS
        padded_start_tt = _ut1_to_ephemeris_tt(padded_start_ut1, self._reader)
        padded_end_tt = _ut1_to_ephemeris_tt(padded_end_ut1, self._reader)

        evaluator_specs = (
            (399, 3),
            (3, 0),
            (10, 0),
            (301, 3),
        )
        evaluators = [
            native_reader.evaluator(
                target,
                center,
                padded_start_tt,
                jd_end_tt=padded_end_tt,
            )
            for target, center in evaluator_specs
        ]
        if any(evaluator is None for evaluator in evaluators):
            return None

        earth_from_emb, emb_from_ssb, sun_from_ssb, moon_from_emb = evaluators
        earth_from_ssb = _moira_native.SumEvaluator(
            earth_from_emb,
            emb_from_ssb,
        )
        sun_from_earth = _moira_native.RelativeEvaluator(
            sun_from_ssb,
            earth_from_ssb,
        )
        moon_from_ssb = _moira_native.SumEvaluator(
            emb_from_ssb,
            moon_from_emb,
        )
        moon_from_earth = _moira_native.RelativeEvaluator(
            moon_from_ssb,
            earth_from_ssb,
        )

        candidates_tt = native_find(
            sun_from_earth,
            moon_from_earth,
            padded_start_tt,
            padded_end_tt,
            _NATIVE_BULK_ECLIPSE_CANDIDATE_SEPARATION_DEG,
            _NATIVE_BULK_ECLIPSE_SCAN_STEP_DAYS,
        )
        return [
            _ephemeris_tt_to_ut1(float(candidate_tt), self._reader)
            for candidate_tt in candidates_tt
        ]

    def _eclipses_from_syzygy_candidates(
        self,
        family: str,
        candidates_ut1: list[float],
        jd_start: float,
        jd_end: float,
    ) -> list[EclipseEvent]:
        """Refine a native candidate superset through Python eclipse doctrine."""
        events: list[EclipseEvent] = []
        for candidate_ut1 in candidates_ut1:
            if family == "solar":
                event = self._solar_eclipse_near_syzygy(
                    candidate_ut1,
                    kind_key="any",
                )
            else:
                event = self._lunar_eclipse_near_syzygy(
                    candidate_ut1,
                    kind_key="any",
                    use_canon=False,
                )
            if event is None or not jd_start <= event.jd_ut <= jd_end:
                continue
            if any(abs(event.jd_ut - prior.jd_ut) <= 1.0e-7 for prior in events):
                continue
            events.append(event)
        events.sort(key=lambda event: event.jd_ut)
        return events

    def _solar_eclipses_in_range_python(
        self,
        jd_start: float,
        jd_end: float,
    ) -> list[EclipseEvent]:
        """Canonical Python range manuscript used for fallback and parity."""
        events: list[EclipseEvent] = []
        jd = math.nextafter(jd_start, -math.inf)
        while True:
            event = self.next_solar_eclipse(jd)
            if event.jd_ut > jd_end:
                break
            events.append(event)
            jd = event.jd_ut + 1.0
        return events

    def _lunar_eclipses_in_range_python(
        self,
        jd_start: float,
        jd_end: float,
    ) -> list[EclipseEvent]:
        """Canonical Python range manuscript used for fallback and parity."""
        events: list[EclipseEvent] = []
        jd = math.nextafter(jd_start, -math.inf)
        while True:
            event = self.next_lunar_eclipse(jd)
            if event.jd_ut > jd_end:
                break
            events.append(event)
            jd = event.jd_ut + 1.0
        return events

    def solar_eclipses_in_range(
        self,
        jd_start: float,
        jd_end: float,
    ) -> list[EclipseEvent]:
        """Return all solar eclipses whose maximum falls within [jd_start, jd_end].

        A native TT scan discovers a conservative candidate superset. Python
        retains phase refinement, classification, event assembly, and inclusive
        range filtering. Readers without one native evaluator spanning the
        padded interval use the canonical Python manuscript.
        """
        if jd_end < jd_start:
            return []
        candidates = self._native_eclipse_syzygy_candidates(
            "solar",
            jd_start,
            jd_end,
        )
        if candidates is None:
            return self._solar_eclipses_in_range_python(jd_start, jd_end)
        return self._eclipses_from_syzygy_candidates(
            "solar",
            candidates,
            jd_start,
            jd_end,
        )

    def lunar_eclipses_in_range(
        self,
        jd_start: float,
        jd_end: float,
    ) -> list[EclipseEvent]:
        """Return all lunar eclipses whose maximum falls within [jd_start, jd_end].

        A native TT scan discovers a conservative candidate superset. Python
        retains phase refinement, classification, event assembly, and inclusive
        range filtering. Readers without one native evaluator spanning the
        padded interval use the canonical Python manuscript.
        """
        if jd_end < jd_start:
            return []
        candidates = self._native_eclipse_syzygy_candidates(
            "lunar",
            jd_start,
            jd_end,
        )
        if candidates is None:
            return self._lunar_eclipses_in_range_python(jd_start, jd_end)
        return self._eclipses_from_syzygy_candidates(
            "lunar",
            candidates,
            jd_start,
            jd_end,
        )

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
_SOLAR_PENUMBRAL_DEFAULT_SAMPLES = 181
_SOLAR_PENUMBRAL_SOLVER_SAMPLES = 721
_SOLAR_PENUMBRAL_MIN_SAMPLES = 9
_SOLAR_PENUMBRAL_MAX_SAMPLES = 721
_SOLAR_PENUMBRAL_AZIMUTH_BRACKETS = 360
_SOLAR_PENUMBRAL_CONTACT_STEP_DAYS = 10.0 / 1440.0
_SOLAR_PENUMBRAL_CONTACT_SCAN_STEPS = 48
_SOLAR_PENUMBRAL_TIME_TOLERANCE_DAYS = 1.0e-9
_SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS = 2.0 / 86400.0
_SOLAR_PENUMBRAL_ENDPOINT_PROBES_DAYS = tuple(
    seconds / 86400.0
    for seconds in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0)
)


_NATIVE_BULK_ECLIPSE_PADDING_DAYS = 35.0
# Public solar/lunar geometry is entered only inside a 1.5-degree syzygy
# neighborhood. Two degrees is therefore a conservative discovery superset,
# not a hidden eclipse classifier.
_NATIVE_BULK_ECLIPSE_CANDIDATE_SEPARATION_DEG = 2.0
_NATIVE_BULK_ECLIPSE_SCAN_STEP_DAYS = 2.0
_SOLAR_PENUMBRAL_TOPOLOGY_MARGIN_KM2 = 1.0e-4
_SOLAR_PENUMBRAL_CLEARANCE_TOLERANCE_KM = 1.0e-3
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
    penumbral_radius_km: float
    penumbral_cone_slope: float
    fundamental_east_unit_itrf: tuple[float, float, float]
    fundamental_north_unit_itrf: tuple[float, float, float]
    sun_xyz_from_earth_itrf_km: tuple[float, float, float]


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


@dataclass(frozen=True, slots=True)
class _PenumbralGeneratorPoint:
    """One first-lawful generator intersection with zero-elevation WGS 84."""

    azimuth_rad: float
    xyz_itrf_km: tuple[float, float, float]
    latitude_deg: float
    longitude_deg: float
    signed_half_chord_sq_km2: float


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

    def tete_to_itrf(
        vector: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        tete_x, tete_y, tete_z = vector
        tirs = (
            cos_gast * tete_x + sin_gast * tete_y,
            -sin_gast * tete_x + cos_gast * tete_y,
            tete_z,
        )
        return mat_vec_mul(tirs_to_itrf, tirs)

    def icrf_to_itrf(
        vector: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        return tete_to_itrf(mat_vec_mul(precession_nutation, vector))

    axis_unit = _shadow_unit(
        icrf_to_itrf(state.axis_unit_away_from_sun),
        label="terrestrial solar shadow axis",
    )
    sun_xyz_itrf_km = icrf_to_itrf(state.sun_xyz_km)
    _shadow_unit(
        sun_xyz_itrf_km,
        label="terrestrial geocentric Sun direction",
    )
    true_pole_itrf = _shadow_unit(
        tete_to_itrf((0.0, 0.0, 1.0)),
        label="terrestrial true celestial pole",
    )
    axis_sunward = _shadow_scale(axis_unit, -1.0)
    fundamental_east = _shadow_unit(
        _shadow_cross(true_pole_itrf, axis_sunward),
        label="terrestrial Besselian east",
    )
    fundamental_north = _shadow_unit(
        _shadow_cross(axis_sunward, fundamental_east),
        label="terrestrial Besselian north",
    )

    sin_f1 = (SUN_RADIUS_KM + MOON_RADIUS_KM) / state.sun_moon_distance_km
    sin_f2 = (SUN_RADIUS_KM - MOON_RADIUS_KM) / state.sun_moon_distance_km
    if not 0.0 < sin_f2 < sin_f1 < 1.0:
        raise ArithmeticError("solar and lunar radii cannot define physical shadow cones")
    cos_f1 = math.sqrt((1.0 - sin_f1) * (1.0 + sin_f1))
    cos_f2 = math.sqrt((1.0 - sin_f2) * (1.0 + sin_f2))
    tan_f1 = sin_f1 / cos_f1
    tan_f2 = sin_f2 / cos_f2
    penumbral_radius = (
        MOON_RADIUS_KM / cos_f1
        - state.axis_projection_km * tan_f1
    )
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
        penumbral_radius_km=penumbral_radius,
        penumbral_cone_slope=tan_f1,
        fundamental_east_unit_itrf=fundamental_east,
        fundamental_north_unit_itrf=fundamental_north,
        sun_xyz_from_earth_itrf_km=sun_xyz_itrf_km,
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


def _penumbral_radial_unit(
    shadow: _EarthFixedSolarShadow,
    azimuth_rad: float,
) -> tuple[float, float, float]:
    """Return one Besselian-east/north radial unit around the shadow axis."""

    return _shadow_add(
        _shadow_scale(
            shadow.fundamental_east_unit_itrf,
            math.cos(azimuth_rad),
        ),
        _shadow_scale(
            shadow.fundamental_north_unit_itrf,
            math.sin(azimuth_rad),
        ),
    )


def _penumbral_generator_line(
    shadow: _EarthFixedSolarShadow,
    azimuth_rad: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    radial = _penumbral_radial_unit(shadow, azimuth_rad)
    origin = _shadow_add(
        shadow.fundamental_plane_point_xyz_km,
        _shadow_scale(radial, shadow.penumbral_radius_km),
    )
    direction = _shadow_add(
        shadow.axis_unit_away_from_sun,
        _shadow_scale(radial, shadow.penumbral_cone_slope),
    )
    return origin, direction


def _penumbral_generator_margin_km2(
    shadow: _EarthFixedSolarShadow,
    azimuth_rad: float,
) -> float:
    origin, direction = _penumbral_generator_line(shadow, azimuth_rad)
    signed_parameter_half_chord_sq, _roots = _wgs84_line_intersection_parameters(
        origin,
        direction,
    )
    return signed_parameter_half_chord_sq * _shadow_dot(direction, direction)


def _penumbral_generator_point(
    shadow: _EarthFixedSolarShadow,
    azimuth_rad: float,
    *,
    tangent: bool = False,
) -> _PenumbralGeneratorPoint | None:
    """Materialize the first lawful generator intersection, or one tangent."""

    azimuth_rad %= math.tau
    origin, direction = _penumbral_generator_line(shadow, azimuth_rad)
    signed_parameter_half_chord_sq, roots = _wgs84_line_intersection_parameters(
        origin,
        direction,
    )
    signed_half_chord_sq_km2 = (
        signed_parameter_half_chord_sq * _shadow_dot(direction, direction)
    )
    if roots is None:
        return None
    if tangent:
        coefficient_a, coefficient_b, _coefficient_c = (
            _wgs84_line_quadratic_coefficients(origin, direction)
        )
        parameter = -coefficient_b / coefficient_a
    else:
        lawful_roots = tuple(
            root for root in roots if root >= shadow.axis_projection_km
        )
        if not lawful_roots:
            return None
        parameter = min(lawful_roots)
    if parameter < shadow.axis_projection_km:
        return None
    if parameter - shadow.axis_projection_km <= MOON_RADIUS_KM:
        raise ArithmeticError(
            "penumbral generator has no physical Earth intersection beyond the Moon"
        )
    xyz_itrf_km = _shadow_add(origin, _shadow_scale(direction, parameter))
    latitude_deg, longitude_deg = _wgs84_geodetic_from_xyz_km(xyz_itrf_km)
    return _PenumbralGeneratorPoint(
        azimuth_rad=azimuth_rad,
        xyz_itrf_km=xyz_itrf_km,
        latitude_deg=latitude_deg,
        longitude_deg=longitude_deg,
        signed_half_chord_sq_km2=signed_half_chord_sq_km2,
    )


def _periodic_scalar_extreme(
    func,
    *,
    maximize: bool,
) -> tuple[float, float]:
    """Refine one global azimuthal extreme from a bounded circular bracket."""

    count = _SOLAR_PENUMBRAL_AZIMUTH_BRACKETS
    step = math.tau / count
    values = tuple(func(index * step) for index in range(count))
    if not all(math.isfinite(value) for value in values):
        raise ArithmeticError("penumbral azimuth objective must remain finite")
    best_index = (
        max(range(count), key=values.__getitem__)
        if maximize
        else min(range(count), key=values.__getitem__)
    )
    left = (best_index - 1) * step
    right = (best_index + 1) * step

    def objective(angle: float) -> float:
        value = func(angle % math.tau)
        return -value if maximize else value

    golden = (math.sqrt(5.0) - 1.0) / 2.0
    x1 = right - golden * (right - left)
    x2 = left + golden * (right - left)
    f1 = objective(x1)
    f2 = objective(x2)
    for _ in range(56):
        if f1 <= f2:
            right = x2
            x2 = x1
            f2 = f1
            x1 = right - golden * (right - left)
            f1 = objective(x1)
        else:
            left = x1
            x1 = x2
            f1 = f2
            x2 = left + golden * (right - left)
            f2 = objective(x2)
    azimuth = ((left + right) / 2.0) % math.tau
    return azimuth, func(azimuth)


def _penumbral_generator_extrema(
    shadow: _EarthFixedSolarShadow,
) -> tuple[tuple[float, float], tuple[float, float]]:
    margin = lambda azimuth: _penumbral_generator_margin_km2(shadow, azimuth)
    return (
        _periodic_scalar_extreme(margin, maximize=True),
        _periodic_scalar_extreme(margin, maximize=False),
    )


def _penumbral_contact_point(
    shadow: _EarthFixedSolarShadow,
    jd_ut: float,
    azimuth_rad: float,
    kind: SolarEclipsePenumbralContactKind,
) -> SolarEclipsePenumbralContact:
    point = _penumbral_generator_point(shadow, azimuth_rad, tangent=True)
    if point is None:
        raise ArithmeticError(f"{kind.value.upper()} tangency could not be materialized")
    return SolarEclipsePenumbralContact(
        kind=kind,
        point=SolarEclipseFootprintPoint(
            jd_ut=jd_ut,
            latitude_deg=point.latitude_deg,
            longitude_deg=point.longitude_deg,
        ),
    )


def _bounded_scalar_maximum(
    func,
    left: float,
    right: float,
) -> tuple[float, float]:
    """Refine one smooth maximum inside a finite bracketing interval."""

    if not math.isfinite(left) or not math.isfinite(right) or left >= right:
        raise ArithmeticError("bounded maximum requires finite ordered bounds")
    golden = (math.sqrt(5.0) - 1.0) / 2.0
    x1 = right - golden * (right - left)
    x2 = left + golden * (right - left)
    f1 = func(x1)
    f2 = func(x2)
    if not math.isfinite(f1) or not math.isfinite(f2):
        raise ArithmeticError("bounded maximum objective must remain finite")
    for _ in range(64):
        if right - left <= _SOLAR_PENUMBRAL_TIME_TOLERANCE_DAYS:
            break
        if f1 >= f2:
            right = x2
            x2 = x1
            f2 = f1
            x1 = right - golden * (right - left)
            f1 = func(x1)
        else:
            left = x1
            x1 = x2
            f1 = f2
            x2 = left + golden * (right - left)
            f2 = func(x2)
    epoch = (left + right) / 2.0
    value = func(epoch)
    if not math.isfinite(value):
        raise ArithmeticError("bounded maximum objective must remain finite")
    return epoch, value


def _solve_solar_penumbral_contacts(
    calc: EclipseCalculator,
    jd_ut: float,
) -> tuple[SolarEclipseFootprintContacts, SolarEclipseFootprintTopology]:
    """Solve P1/P4 and the paired optional P2/P3 from cone tangencies."""

    cache: dict[float, tuple[_EarthFixedSolarShadow, tuple[float, float], tuple[float, float]]] = {}

    def extrema_at(epoch: float):
        key = round(epoch, 14)
        cached = cache.get(key)
        if cached is not None:
            return cached
        shadow = _earth_fixed_solar_shadow(calc, epoch)
        if shadow is None:
            raise ArithmeticError("solar eclipse has no forward penumbral shadow ray")
        maximum, minimum = _penumbral_generator_extrema(shadow)
        result = (shadow, maximum, minimum)
        cache[key] = result
        return result

    center_maximum = extrema_at(jd_ut)[1][1]
    if center_maximum <= 0.0:
        raise ArithmeticError("searched solar eclipse has no penumbral WGS-84 footprint")

    def bracket_external(direction: float) -> tuple[float, float]:
        inside = jd_ut
        for _ in range(_SOLAR_PENUMBRAL_CONTACT_SCAN_STEPS):
            outside = inside + direction * _SOLAR_PENUMBRAL_CONTACT_STEP_DAYS
            if extrema_at(outside)[1][1] <= 0.0:
                return (outside, inside) if direction < 0.0 else (inside, outside)
            inside = outside
        raise _SearchLimitReached(
            "solar penumbral external contact was not bracketed within eight hours"
        )

    def refine_crossing(
        left: float,
        right: float,
        objective,
        *,
        rising: bool,
    ) -> float:
        f_left = objective(left)
        f_right = objective(right)
        if rising:
            if f_left > 0.0 or f_right < 0.0:
                raise ArithmeticError("invalid rising penumbral contact bracket")
        elif f_left < 0.0 or f_right > 0.0:
            raise ArithmeticError("invalid falling penumbral contact bracket")
        for _ in range(48):
            if right - left <= _SOLAR_PENUMBRAL_TIME_TOLERANCE_DAYS:
                break
            midpoint = (left + right) / 2.0
            if midpoint == left or midpoint == right:
                break
            value = objective(midpoint)
            if (value >= 0.0) is rising:
                right = midpoint
            else:
                left = midpoint
        return right if rising else left

    p1_bracket = bracket_external(-1.0)
    p4_bracket = bracket_external(1.0)
    maximum_margin = lambda epoch: extrema_at(epoch)[1][1]
    p1_jd = refine_crossing(*p1_bracket, maximum_margin, rising=True)
    p4_jd = refine_crossing(*p4_bracket, maximum_margin, rising=False)

    topology_samples = _sample_interval(p1_jd, p4_jd, 49)
    minimum_samples = tuple(
        (epoch, extrema_at(epoch)[2][1]) for epoch in topology_samples
    )
    peak_index = max(range(len(minimum_samples)), key=lambda i: minimum_samples[i][1])
    if peak_index == 0 or peak_index == len(minimum_samples) - 1:
        raise ArithmeticError("internal penumbral-margin maximum escaped P1/P4")
    minimum_margin = lambda epoch: extrema_at(epoch)[2][1]
    peak_epoch, peak_minimum = _bounded_scalar_maximum(
        minimum_margin,
        minimum_samples[peak_index - 1][0],
        minimum_samples[peak_index + 1][0],
    )
    sampled_peak_epoch, sampled_peak_minimum = minimum_samples[peak_index]
    if sampled_peak_minimum > peak_minimum:
        peak_epoch = sampled_peak_epoch
        peak_minimum = sampled_peak_minimum
    p2_jd: float | None = None
    p3_jd: float | None = None
    if abs(peak_minimum) <= _SOLAR_PENUMBRAL_TOPOLOGY_MARGIN_KM2:
        raise ArithmeticError(
            "penumbral footprint topology is numerically limiting at P2/P3"
        )
    if peak_minimum > 0.0:
        left_outside = tuple(
            epoch
            for epoch, value in minimum_samples
            if epoch < peak_epoch and value <= 0.0
        )
        right_outside = tuple(
            epoch
            for epoch, value in minimum_samples
            if epoch > peak_epoch and value <= 0.0
        )
        if not left_outside or not right_outside:
            raise ArithmeticError("internal penumbral contacts escaped P1/P4")
        p2_jd = refine_crossing(
            max(left_outside),
            peak_epoch,
            minimum_margin,
            rising=True,
        )
        p3_jd = refine_crossing(
            peak_epoch,
            min(right_outside),
            minimum_margin,
            rising=False,
        )

    def make_contact(
        epoch: float,
        kind: SolarEclipsePenumbralContactKind,
        *,
        internal: bool,
    ) -> SolarEclipsePenumbralContact:
        shadow, maximum, minimum = extrema_at(epoch)
        azimuth = minimum[0] if internal else maximum[0]
        return _penumbral_contact_point(shadow, epoch, azimuth, kind)

    p1 = make_contact(p1_jd, SolarEclipsePenumbralContactKind.P1, internal=False)
    p4 = make_contact(p4_jd, SolarEclipsePenumbralContactKind.P4, internal=False)
    p2 = (
        make_contact(p2_jd, SolarEclipsePenumbralContactKind.P2, internal=True)
        if p2_jd is not None
        else None
    )
    p3 = (
        make_contact(p3_jd, SolarEclipsePenumbralContactKind.P3, internal=True)
        if p3_jd is not None
        else None
    )
    topology = (
        SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP
        if p2 is not None
        else SolarEclipseFootprintTopology.ONE_LIMIT_CONNECTED
    )
    return SolarEclipseFootprintContacts(p1=p1, p2=p2, p3=p3, p4=p4), topology


def _penumbral_clearance_km(
    shadow: _EarthFixedSolarShadow,
    surface_xyz_itrf_km: tuple[float, float, float],
) -> float:
    """Return positive-inside outward-growing penumbral-cone clearance."""

    offset = _shadow_subtract(
        surface_xyz_itrf_km,
        shadow.fundamental_plane_point_xyz_km,
    )
    axial_km = _shadow_dot(offset, shadow.axis_unit_away_from_sun)
    perpendicular = _shadow_subtract(
        offset,
        _shadow_scale(shadow.axis_unit_away_from_sun, axial_km),
    )
    cone_radius_km = (
        shadow.penumbral_radius_km
        + shadow.penumbral_cone_slope * axial_km
    )
    return cone_radius_km - math.sqrt(_shadow_dot(perpendicular, perpendicular))


def _bisect_periodic_root(func, left: float, right: float) -> float:
    f_left = func(left % math.tau)
    f_right = func(right % math.tau)
    if f_left == 0.0:
        return left % math.tau
    if f_right == 0.0:
        return right % math.tau
    if f_left * f_right > 0.0:
        raise ArithmeticError("periodic azimuth root requires a sign-changing bracket")
    for _ in range(52):
        midpoint = (left + right) / 2.0
        f_midpoint = func(midpoint % math.tau)
        if f_midpoint == 0.0:
            return midpoint % math.tau
        if f_left * f_midpoint <= 0.0:
            right = midpoint
            f_right = f_midpoint
        else:
            left = midpoint
            f_left = f_midpoint
    return ((left + right) / 2.0) % math.tau


def _deduplicate_azimuths(values: list[float], *, tolerance_rad: float = 1.0e-9) -> tuple[float, ...]:
    result: list[float] = []
    for value in sorted(value % math.tau for value in values):
        if not result or abs(value - result[-1]) > tolerance_rad:
            result.append(value)
    if (
        len(result) > 1
        and min(result[0] + math.tau - result[-1], result[-1] - result[0])
        <= tolerance_rad
    ):
        result.pop()
    return tuple(result)


def _penumbral_limb_tangent_points(
    shadow: _EarthFixedSolarShadow,
) -> tuple[_PenumbralGeneratorPoint, ...]:
    """Return the two cone-generator/WGS-84 tangencies at one partial overlap."""

    left, right, periodic = _penumbral_lawful_azimuth_interval(shadow)
    if periodic:
        raise ArithmeticError(
            "limb tangencies require a strict partial penumbral intersection"
        )
    roots = (left % math.tau, right % math.tau)
    points = tuple(
        point
        for azimuth in _deduplicate_azimuths(roots)
        if (point := _penumbral_generator_point(shadow, azimuth, tangent=True))
        is not None
    )
    if len(points) != 2:
        raise ArithmeticError(
            "partial penumbral overlap must expose exactly two limb tangencies"
        )
    return points


def _penumbral_lawful_azimuth_interval(
    shadow: _EarthFixedSolarShadow,
) -> tuple[float, float, bool]:
    """Return one unwrapped lawful generator interval and periodicity."""

    maximum, minimum = _penumbral_generator_extrema(shadow)
    maximum_azimuth, maximum_margin = maximum
    _minimum_azimuth, minimum_margin = minimum
    if maximum_margin <= 0.0:
        raise ArithmeticError("penumbral cone has no strict WGS-84 intersection")
    if minimum_margin >= 0.0:
        return maximum_azimuth, maximum_azimuth + math.tau, True

    margin = lambda angle: _penumbral_generator_margin_km2(shadow, angle)
    step = math.tau / _SOLAR_PENUMBRAL_AZIMUTH_BRACKETS

    def root_on_side(direction: float) -> float:
        for index in range(1, _SOLAR_PENUMBRAL_AZIMUTH_BRACKETS + 1):
            outside = maximum_azimuth + direction * index * step
            if margin(outside % math.tau) <= 0.0:
                left, right = (
                    (outside, maximum_azimuth)
                    if direction < 0.0
                    else (maximum_azimuth, outside)
                )
                root = _bisect_periodic_root(margin, left, right)
                delta = (root - maximum_azimuth + math.pi) % math.tau - math.pi
                if direction < 0.0 and delta > 0.0:
                    delta -= math.tau
                elif direction > 0.0 and delta < 0.0:
                    delta += math.tau
                return maximum_azimuth + delta
        raise ArithmeticError("partial penumbral cone arc has no limb endpoint")

    left = root_on_side(-1.0)
    right = root_on_side(1.0)
    if not left < maximum_azimuth < right:
        raise ArithmeticError("lawful penumbral arc does not contain its maximum")
    return left, right, False


def _solar_altitude_derivative_sign(
    before: _EarthFixedSolarShadow,
    after: _EarthFixedSolarShadow,
    surface_xyz_itrf_km: tuple[float, float, float],
) -> float:
    """Return the fixed-site topocentric geometric altitude derivative."""

    before_proxy = _topocentric_solar_altitude_proxy(
        before,
        surface_xyz_itrf_km,
    )
    after_proxy = _topocentric_solar_altitude_proxy(
        after,
        surface_xyz_itrf_km,
    )
    return after_proxy - before_proxy


def _topocentric_solar_altitude_proxy(
    shadow: _EarthFixedSolarShadow,
    surface_xyz_itrf_km: tuple[float, float, float],
) -> float:
    """Return sine of geometric Sun altitude at one fixed WGS-84 site."""

    normal = _wgs84_surface_normal_unit(surface_xyz_itrf_km)
    direction = _shadow_unit(
        _shadow_subtract(
            shadow.sun_xyz_from_earth_itrf_km,
            surface_xyz_itrf_km,
        ),
        label="topocentric geometric Sun direction",
    )
    return _shadow_dot(normal, direction)


def _adaptive_azimuth_roots(
    func,
    left: float,
    right: float,
) -> tuple[float, ...]:
    """Discover sign-changing roots and witnessed close pairs.

    This fixed-grid search supplies deterministic candidates.  Completeness
    for the public footprint is governed separately by continuation from the
    authoritative horizon incidences and by the closed-component invariants;
    this helper alone is not an exhaustive root proof.
    """

    if not math.isfinite(left) or not math.isfinite(right) or left >= right:
        raise ArithmeticError("azimuth root domain must be finite and ordered")
    coarse_step = math.tau / _SOLAR_PENUMBRAL_AZIMUTH_BRACKETS
    cell_count = max(1, math.ceil((right - left) / coarse_step))
    cell_step = (right - left) / cell_count
    minimum_width = math.radians(1.0e-4)
    root_tolerance = 1.0e-12
    cache: dict[float, float] = {}
    roots: list[float] = []

    def value(angle: float) -> float:
        key = round(angle, 15)
        cached = cache.get(key)
        if cached is not None:
            return cached
        result = func(angle % math.tau)
        if not math.isfinite(result):
            raise ArithmeticError("azimuth root objective must remain finite")
        cache[key] = result
        return result

    def bisect(a: float, b: float, fa: float, fb: float) -> float:
        if abs(fa) <= root_tolerance:
            return a
        if abs(fb) <= root_tolerance:
            return b
        if fa * fb > 0.0:
            raise ArithmeticError("azimuth root bisection lost its sign bracket")
        for _ in range(56):
            midpoint = (a + b) / 2.0
            fm = value(midpoint)
            if abs(fm) <= root_tolerance:
                return midpoint
            if fa * fm <= 0.0:
                b = midpoint
                fb = fm
            else:
                a = midpoint
                fa = fm
        return (a + b) / 2.0

    def inspect(a: float, b: float, fa: float, fb: float, depth: int) -> None:
        midpoint = (a + b) / 2.0
        fm = value(midpoint)
        left_crossing = fa * fm < 0.0
        right_crossing = fm * fb < 0.0
        exact = (
            abs(fa) <= root_tolerance
            or abs(fm) <= root_tolerance
            or abs(fb) <= root_tolerance
        )
        slope_reversal = (fm - fa) * (fb - fm) <= 0.0
        magnitude_valley = abs(fm) <= 0.8 * min(abs(fa), abs(fb))
        should_split = (
            left_crossing
            or right_crossing
            or exact
            or slope_reversal
            or magnitude_valley
        )
        if should_split and b - a > minimum_width and depth < 24:
            inspect(a, midpoint, fa, fm, depth + 1)
            inspect(midpoint, b, fm, fb, depth + 1)
            return
        if left_crossing:
            roots.append(bisect(a, midpoint, fa, fm))
        elif abs(fa) <= root_tolerance:
            roots.append(a)
        if right_crossing:
            roots.append(bisect(midpoint, b, fm, fb))
        elif abs(fm) <= root_tolerance:
            roots.append(midpoint)
        if abs(fb) <= root_tolerance:
            roots.append(b)

    def refine_extreme(
        a: float,
        b: float,
        *,
        maximize: bool,
    ) -> tuple[float, float]:
        golden = (math.sqrt(5.0) - 1.0) / 2.0
        x1 = b - golden * (b - a)
        x2 = a + golden * (b - a)

        def score(angle: float) -> float:
            result = value(angle)
            return result if maximize else -result

        f1 = score(x1)
        f2 = score(x2)
        for _ in range(56):
            if f1 >= f2:
                b = x2
                x2 = x1
                f2 = f1
                x1 = b - golden * (b - a)
                f1 = score(x1)
            else:
                a = x1
                x1 = x2
                f1 = f2
                x2 = a + golden * (b - a)
                f2 = score(x2)
        angle = (a + b) / 2.0
        return angle, value(angle)

    points = tuple(left + index * cell_step for index in range(cell_count + 1))
    values = tuple(value(angle) for angle in points)
    for index in range(cell_count):
        inspect(
            points[index],
            points[index + 1],
            values[index],
            values[index + 1],
            0,
        )
    for index in range(1, cell_count):
        left_value = values[index - 1]
        center_value = values[index]
        right_value = values[index + 1]
        if center_value >= left_value and center_value >= right_value:
            angle, extreme_value = refine_extreme(
                points[index - 1],
                points[index + 1],
                maximize=True,
            )
            if extreme_value >= -root_tolerance:
                if left_value * extreme_value <= 0.0:
                    roots.append(
                        bisect(
                            points[index - 1],
                            angle,
                            left_value,
                            extreme_value,
                        )
                    )
                if extreme_value * right_value <= 0.0:
                    roots.append(
                        bisect(
                            angle,
                            points[index + 1],
                            extreme_value,
                            right_value,
                        )
                    )
        elif center_value <= left_value and center_value <= right_value:
            angle, extreme_value = refine_extreme(
                points[index - 1],
                points[index + 1],
                maximize=False,
            )
            if extreme_value <= root_tolerance:
                if left_value * extreme_value <= 0.0:
                    roots.append(
                        bisect(
                            points[index - 1],
                            angle,
                            left_value,
                            extreme_value,
                        )
                    )
                if extreme_value * right_value <= 0.0:
                    roots.append(
                        bisect(
                            angle,
                            points[index + 1],
                            extreme_value,
                            right_value,
                        )
                    )
    # A horizon-incidence branch enters through a lawful-arc endpoint. Close
    # to that incidence its root can be many orders of magnitude nearer the
    # endpoint than a uniform azimuth cell. Resolve both endpoint
    # neighborhoods on a geometric scale so this topological seed cannot be
    # skipped by the presentation-independent coarse grid.
    endpoint_span = min(coarse_step, (right - left) / 2.0)
    for endpoint, direction in ((left, 1.0), (right, -1.0)):
        offsets = tuple(
            sorted(
                {
                    0.0,
                    endpoint_span,
                    *(
                        endpoint_span * math.ldexp(1.0, -power)
                        for power in range(1, 45)
                    ),
                }
            )
        )
        endpoint_points = tuple(
            endpoint + direction * offset for offset in offsets
        )
        endpoint_values = tuple(value(angle) for angle in endpoint_points)
        for first, second, f_first, f_second in zip(
            endpoint_points,
            endpoint_points[1:],
            endpoint_values,
            endpoint_values[1:],
        ):
            a, b, fa, fb = (
                (first, second, f_first, f_second)
                if first < second
                else (second, first, f_second, f_first)
            )
            if fa * fb < 0.0:
                roots.append(bisect(a, b, fa, fb))
            elif abs(fa) <= root_tolerance:
                roots.append(a)
            elif abs(fb) <= root_tolerance:
                roots.append(b)
    return _deduplicate_azimuths(
        [root % math.tau for root in roots],
        tolerance_rad=minimum_width,
    )


def _solve_solar_penumbral_greatest_point(
    calc: EclipseCalculator,
    jd_ut: float,
) -> SolarEclipseFootprintPoint:
    """Maximize physical penumbral clearance on the sunlit WGS-84 surface."""

    shadow = _earth_fixed_solar_shadow(calc, jd_ut)
    if shadow is None:
        raise ArithmeticError("solar greatest epoch has no forward penumbral cone")
    cache: dict[tuple[float, float], float] = {}

    def objective(latitude_deg: float, longitude_deg: float) -> float:
        latitude_deg, longitude_deg = _offset_geographic_km(
            latitude_deg,
            longitude_deg,
            0.0,
            0.0,
        )
        key = (round(latitude_deg, 12), round(longitude_deg, 12))
        value = cache.get(key)
        if value is not None:
            return value
        xyz_itrf_km = _wgs84_surface_xyz_km(latitude_deg, longitude_deg)
        if _topocentric_solar_altitude_proxy(shadow, xyz_itrf_km) < 0.0:
            value = float("-inf")
        else:
            value = _penumbral_clearance_km(shadow, xyz_itrf_km)
        cache[key] = value
        return value

    candidates = [(90.0, 0.0), (-90.0, 0.0)]
    candidates.extend(
        (latitude_deg, longitude_deg)
        for latitude_deg in range(-80, 81, 20)
        for longitude_deg in range(-180, 180, 20)
    )
    best_latitude, best_longitude = max(
        candidates,
        key=lambda candidate: objective(*candidate),
    )
    best_clearance = objective(best_latitude, best_longitude)
    for step_km in (
        1000.0,
        500.0,
        200.0,
        100.0,
        50.0,
        20.0,
        10.0,
        5.0,
        2.0,
        1.0,
        0.5,
        0.2,
        0.1,
        0.05,
        0.02,
        0.01,
        0.005,
        0.002,
        0.001,
    ):
        for _ in range(128):
            origin_latitude = best_latitude
            origin_longitude = best_longitude
            improved = False
            for north_direction in (-1.0, 0.0, 1.0):
                for east_direction in (-1.0, 0.0, 1.0):
                    if north_direction == 0.0 and east_direction == 0.0:
                        continue
                    latitude_deg, longitude_deg = _offset_geographic_km(
                        origin_latitude,
                        origin_longitude,
                        north_direction * step_km,
                        east_direction * step_km,
                    )
                    clearance = objective(latitude_deg, longitude_deg)
                    if clearance > best_clearance:
                        best_latitude = latitude_deg
                        best_longitude = longitude_deg
                        best_clearance = clearance
                        improved = True
            if not improved:
                break
        else:
            raise _SearchLimitReached(
                "penumbral greatest-location refinement did not converge"
            )
    if not math.isfinite(best_clearance) or best_clearance <= 0.0:
        raise ArithmeticError("solar greatest epoch has no sunlit penumbral footprint")
    return SolarEclipseFootprintPoint(
        jd_ut=jd_ut,
        latitude_deg=best_latitude,
        longitude_deg=best_longitude,
    )


def _penumbral_envelope_points(
    shadow: _EarthFixedSolarShadow,
    before: _EarthFixedSolarShadow,
    after: _EarthFixedSolarShadow,
) -> dict[
    SolarEclipseFootprintBoundaryKind,
    tuple[_PenumbralGeneratorPoint, ...],
]:
    """Solve C=0 and fixed-ITRF dC/dt=0 on the generator boundary."""

    def derivative_at(azimuth: float) -> float | None:
        point = _penumbral_generator_point(shadow, azimuth)
        if point is None:
            point = _penumbral_generator_point(shadow, azimuth, tangent=True)
        if point is None:
            return None
        return (
            _penumbral_clearance_km(after, point.xyz_itrf_km)
            - _penumbral_clearance_km(before, point.xyz_itrf_km)
        )

    left, right, _periodic = _penumbral_lawful_azimuth_interval(shadow)

    def objective(angle: float) -> float:
        value = derivative_at(angle)
        if value is None:
            raise ArithmeticError("penumbral envelope root escaped its cone arc")
        return value

    roots = _adaptive_azimuth_roots(objective, left, right)

    admitted: dict[
        SolarEclipseFootprintBoundaryKind,
        list[_PenumbralGeneratorPoint],
    ] = {}
    for azimuth in _deduplicate_azimuths(roots):
        point = _penumbral_generator_point(shadow, azimuth)
        if point is None:
            continue
        center_clearance = _penumbral_clearance_km(shadow, point.xyz_itrf_km)
        before_clearance = _penumbral_clearance_km(before, point.xyz_itrf_km)
        after_clearance = _penumbral_clearance_km(after, point.xyz_itrf_km)
        curvature_witness = (
            before_clearance - 2.0 * center_clearance + after_clearance
        )
        if curvature_witness >= -1.0e-9:
            continue
        north_component = math.sin(azimuth)
        if abs(north_component) <= 1.0e-10:
            raise ArithmeticError("penumbral envelope has ambiguous north/south identity")
        kind = (
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH
            if north_component > 0.0
            else SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH
        )
        admitted.setdefault(kind, []).append(point)
    return {kind: tuple(points) for kind, points in admitted.items()}


def _track_point(
    jd_ut: float,
    point: _PenumbralGeneratorPoint,
) -> SolarEclipseFootprintPoint:
    return SolarEclipseFootprintPoint(
        jd_ut=jd_ut,
        latitude_deg=point.latitude_deg,
        longitude_deg=point.longitude_deg,
    )


def _ordered_unique_track_points(
    points: list[SolarEclipseFootprintPoint],
) -> tuple[SolarEclipseFootprintPoint, ...]:
    ordered = sorted(points, key=lambda point: point.jd_ut)
    result: list[SolarEclipseFootprintPoint] = []
    for point in ordered:
        if result and abs(point.jd_ut - result[-1].jd_ut) <= 1.0e-12:
            result[-1] = point
        else:
            result.append(point)
    return tuple(result)


def _materialize_track_points(
    points: tuple[SolarEclipseFootprintPoint, ...],
    requested_epochs: tuple[float, ...],
    *,
    mandatory_points: tuple[SolarEclipseFootprintPoint, ...] = (),
) -> tuple[SolarEclipseFootprintPoint, ...]:
    """Select presentation density from an already-solved boundary segment."""

    selected = {0, len(points) - 1}
    for mandatory in mandatory_points:
        selected.update(
            index
            for index, point in enumerate(points)
            if _footprint_points_coincide(point, mandatory)
        )
    for epoch in requested_epochs:
        if epoch < points[0].jd_ut or epoch > points[-1].jd_ut:
            continue
        selected.add(
            min(
                range(len(points)),
                key=lambda index: abs(points[index].jd_ut - epoch),
            )
        )
    return tuple(points[index] for index in sorted(selected))


def _itrf_distance_sq(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> float:
    delta = _shadow_subtract(left, right)
    return _shadow_dot(delta, delta)


@dataclass(frozen=True, slots=True)
class _PenumbralEnvelopeNode:
    """One solved point on a time slice of the swept penumbral envelope."""

    jd_ut: float
    generator: _PenumbralGeneratorPoint
    point: SolarEclipseFootprintPoint


def _continuous_site_maximum_clearance(
    shadow_at,
    xyz_itrf_km: tuple[float, float, float],
    witness_epoch: float,
    solver_epochs: tuple[float, ...],
) -> float:
    """Return a bounded continuous maximum of fixed-site cone clearance.

    The fixed internal epoch lattice supplies candidate maxima; every sampled
    local maximum is then refined in continuous UT1. Public output density
    never enters this bounded admission witness.
    """

    epochs = tuple(sorted({*solver_epochs, witness_epoch}))
    values = tuple(
        _penumbral_clearance_km(shadow_at(epoch), xyz_itrf_km)
        for epoch in epochs
    )
    maximum = max(values)
    golden = (math.sqrt(5.0) - 1.0) / 2.0

    def objective(epoch: float) -> float:
        return _penumbral_clearance_km(shadow_at(epoch), xyz_itrf_km)

    for index in range(1, len(epochs) - 1):
        if values[index] < values[index - 1] or values[index] < values[index + 1]:
            continue
        left = epochs[index - 1]
        right = epochs[index + 1]
        x1 = right - golden * (right - left)
        x2 = left + golden * (right - left)
        f1 = objective(x1)
        f2 = objective(x2)
        for _ in range(64):
            if right - left <= _SOLAR_PENUMBRAL_TIME_TOLERANCE_DAYS:
                break
            if f1 >= f2:
                right = x2
                x2 = x1
                f2 = f1
                x1 = right - golden * (right - left)
                f1 = objective(x1)
            else:
                left = x1
                x1 = x2
                f1 = f2
                x2 = left + golden * (right - left)
                f2 = objective(x2)
        maximum = max(maximum, f1, f2, objective((left + right) / 2.0))
    return maximum


def _penumbral_envelope_nodes_at(
    shadow_at,
    epoch: float,
    *,
    globally_admit: bool,
    solver_epochs: tuple[float, ...],
) -> dict[
    SolarEclipseFootprintBoundaryKind,
    tuple[_PenumbralEnvelopeNode, ...],
]:
    shadow = shadow_at(epoch)
    before = shadow_at(epoch - _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
    after = shadow_at(epoch + _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
    solved = _penumbral_envelope_points(shadow, before, after)
    result: dict[
        SolarEclipseFootprintBoundaryKind,
        list[_PenumbralEnvelopeNode],
    ] = {}
    for kind, generators in solved.items():
        for generator in generators:
            if globally_admit:
                maximum = _continuous_site_maximum_clearance(
                    shadow_at,
                    generator.xyz_itrf_km,
                    epoch,
                    solver_epochs,
                )
                if maximum > _SOLAR_PENUMBRAL_CLEARANCE_TOLERANCE_KM:
                    continue
            result.setdefault(kind, []).append(
                _PenumbralEnvelopeNode(
                    jd_ut=epoch,
                    generator=generator,
                    point=_track_point(epoch, generator),
                )
            )
    return {
        kind: tuple(
            sorted(nodes, key=lambda node: node.generator.azimuth_rad)
        )
        for kind, nodes in result.items()
    }


def _continue_penumbral_envelope_node(
    shadow_at,
    epoch: float,
    seed_azimuth_rad: float,
    kind: SolarEclipseFootprintBoundaryKind,
    solver_epochs: tuple[float, ...],
) -> _PenumbralEnvelopeNode | None:
    """Correct one known horizon-connected envelope branch at a new epoch."""

    shadow = shadow_at(epoch)
    before = shadow_at(epoch - _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
    after = shadow_at(epoch + _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
    left, right, periodic = _penumbral_lawful_azimuth_interval(shadow)
    unwrapped_candidates = tuple(
        seed_azimuth_rad + turn * math.tau for turn in range(-2, 3)
    )
    if periodic:
        seed = min(
            unwrapped_candidates,
            key=lambda angle: abs(angle - (left + right) / 2.0),
        )
        while seed < left:
            seed += math.tau
        while seed > right:
            seed -= math.tau
    else:
        seed = min(
            unwrapped_candidates,
            key=lambda angle: (
                0.0 if left <= angle <= right else min(abs(angle - left), abs(angle - right))
            ),
        )
        seed = min(right, max(left, seed))

    trust_radius = 0.25
    trust_left = max(left, seed - trust_radius)
    trust_right = min(right, seed + trust_radius)
    if trust_right - trust_left <= 1.0e-12:
        return None

    def objective(angle: float) -> float:
        generator = _penumbral_generator_point(shadow, angle % math.tau)
        if generator is None:
            generator = _penumbral_generator_point(
                shadow,
                angle % math.tau,
                tangent=True,
            )
        if generator is None:
            raise ArithmeticError("continued envelope root escaped its lawful arc")
        return (
            _penumbral_clearance_km(after, generator.xyz_itrf_km)
            - _penumbral_clearance_km(before, generator.xyz_itrf_km)
        )

    root_tolerance = 1.0e-10
    angle_tolerance = 1.0e-12
    angle = seed
    converged = False
    for _ in range(18):
        value = objective(angle)
        if abs(value) <= root_tolerance:
            converged = True
            break
        derivative_step = min(1.0e-5, max((right - left) / 1024.0, 1.0e-8))
        lower = max(trust_left, angle - derivative_step)
        upper = min(trust_right, angle + derivative_step)
        if upper - lower <= angle_tolerance:
            break
        derivative = (objective(upper) - objective(lower)) / (upper - lower)
        if not math.isfinite(derivative) or abs(derivative) <= 1.0e-12:
            break
        step = max(-0.1, min(0.1, value / derivative))
        candidate = min(trust_right, max(trust_left, angle - step))
        if abs(candidate - angle) <= angle_tolerance:
            break
        angle = candidate

    if not converged and abs(objective(angle)) <= root_tolerance:
        converged = True
    if not converged:
        fallback_seed = angle
        samples = {trust_left, trust_right, fallback_seed}
        span = max(
            fallback_seed - trust_left,
            trust_right - fallback_seed,
        )
        radius = 1.0e-9
        while radius < span:
            samples.add(max(trust_left, fallback_seed - radius))
            samples.add(min(trust_right, fallback_seed + radius))
            radius *= 2.0
        ordered = tuple(sorted(samples))
        values = tuple(objective(candidate) for candidate in ordered)
        brackets = tuple(
            (first, second, f_first, f_second)
            for first, second, f_first, f_second in zip(
                ordered,
                ordered[1:],
                values,
                values[1:],
            )
            if f_first * f_second <= 0.0
        )
        if not brackets:
            return None
        first, second, f_first, f_second = min(
            brackets,
            key=lambda bracket: abs(
                (bracket[0] + bracket[1]) / 2.0 - fallback_seed
            ),
        )
        for _ in range(64):
            if second - first <= angle_tolerance:
                break
            midpoint = (first + second) / 2.0
            f_midpoint = objective(midpoint)
            if abs(f_midpoint) <= root_tolerance:
                first = second = midpoint
                break
            if f_first * f_midpoint <= 0.0:
                second = midpoint
                f_second = f_midpoint
            else:
                first = midpoint
                f_first = f_midpoint
        angle = (first + second) / 2.0

    if not trust_left <= angle <= trust_right:
        return None
    if abs(objective(angle)) > root_tolerance:
        return None
    generator = _penumbral_generator_point(shadow, angle % math.tau)
    if generator is None:
        generator = _penumbral_generator_point(
            shadow,
            angle % math.tau,
            tangent=True,
        )
    if generator is None:
        return None
    center_clearance = _penumbral_clearance_km(shadow, generator.xyz_itrf_km)
    curvature = (
        _penumbral_clearance_km(before, generator.xyz_itrf_km)
        - 2.0 * center_clearance
        + _penumbral_clearance_km(after, generator.xyz_itrf_km)
    )
    if curvature >= -1.0e-9:
        return None
    north_component = math.sin(generator.azimuth_rad)
    if abs(north_component) <= 1.0e-10:
        return None
    north = north_component > 0.0
    if north != (kind is SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH):
        return None
    maximum = _continuous_site_maximum_clearance(
        shadow_at,
        generator.xyz_itrf_km,
        epoch,
        solver_epochs,
    )
    if maximum > _SOLAR_PENUMBRAL_CLEARANCE_TOLERANCE_KM:
        return None
    return _PenumbralEnvelopeNode(
        jd_ut=epoch,
        generator=generator,
        point=_track_point(epoch, generator),
    )


def _refine_penumbral_envelope_fold(
    shadow_at,
    kind: SolarEclipseFootprintBoundaryKind,
    inside_epoch: float,
    outside_epoch: float,
    solver_epochs: tuple[float, ...],
    *,
    inside_nodes_hint: tuple[_PenumbralEnvelopeNode, ...] = (),
) -> _PenumbralEnvelopeNode:
    """Refine the common endpoint where two time-slice roots coalesce."""

    def candidates(epoch: float) -> tuple[_PenumbralEnvelopeNode, ...]:
        return _penumbral_envelope_nodes_at(
            shadow_at,
            epoch,
            globally_admit=False,
            solver_epochs=solver_epochs,
        ).get(kind, ())

    inside_nodes = (
        inside_nodes_hint
        if len(inside_nodes_hint) >= 2
        else candidates(inside_epoch)
    )
    outside_nodes = candidates(outside_epoch)
    if len(inside_nodes) < 2 or len(outside_nodes) >= 2:
        raise ArithmeticError(
            "penumbral fold refinement requires a two/root-free bracket: "
            f"{kind.value} inside={inside_epoch:.12f}/{len(inside_nodes)} "
            f"outside={outside_epoch:.12f}/{len(outside_nodes)}"
        )
    inside = inside_epoch
    outside = outside_epoch
    for _ in range(64):
        if abs(outside - inside) <= _SOLAR_PENUMBRAL_TIME_TOLERANCE_DAYS:
            break
        midpoint = (inside + outside) / 2.0
        midpoint_nodes = candidates(midpoint)
        if len(midpoint_nodes) >= 2:
            inside = midpoint
            inside_nodes = midpoint_nodes
        else:
            outside = midpoint
            outside_nodes = midpoint_nodes

    pair = min(
        (
            (left, right)
            for left_index, left in enumerate(inside_nodes)
            for right in inside_nodes[left_index + 1 :]
        ),
        key=lambda values: _itrf_distance_sq(
            values[0].generator.xyz_itrf_km,
            values[1].generator.xyz_itrf_km,
        ),
    )
    left_azimuth = pair[0].generator.azimuth_rad
    delta = (
        pair[1].generator.azimuth_rad - left_azimuth + math.pi
    ) % math.tau - math.pi
    fold_azimuth = (left_azimuth + delta / 2.0) % math.tau
    fold_generator = _penumbral_generator_point(
        shadow_at(inside),
        fold_azimuth,
    )
    if fold_generator is None:
        fold_generator = min(
            (pair[0].generator, pair[1].generator),
            key=lambda generator: abs(
                _penumbral_clearance_km(
                    shadow_at(inside),
                    generator.xyz_itrf_km,
                )
            ),
        )
    maximum = _continuous_site_maximum_clearance(
        shadow_at,
        fold_generator.xyz_itrf_km,
        inside,
        solver_epochs,
    )
    if maximum > _SOLAR_PENUMBRAL_CLEARANCE_TOLERANCE_KM:
        raise ArithmeticError(
            "refined penumbral fold is not a global path limit: "
            f"maximum={maximum:.9f} km pair_distance="
            f"{math.sqrt(_itrf_distance_sq(pair[0].generator.xyz_itrf_km, pair[1].generator.xyz_itrf_km)):.6f} km"
        )
    return _PenumbralEnvelopeNode(
        jd_ut=inside,
        generator=fold_generator,
        point=_track_point(inside, fold_generator),
    )


def _refine_horizon_direction_transition(
    shadow_at,
    left_epoch: float,
    left_point: _PenumbralGeneratorPoint,
    left_derivative: float,
    right_epoch: float,
    right_point: _PenumbralGeneratorPoint,
    right_derivative: float,
) -> SolarEclipseFootprintPoint:
    """Refine where one continuous limb branch changes rise/set direction."""

    if left_derivative == 0.0:
        return _track_point(left_epoch, left_point)
    if right_derivative == 0.0:
        return _track_point(right_epoch, right_point)
    if left_derivative * right_derivative > 0.0:
        raise ArithmeticError("horizon-direction transition requires a sign change")

    left = left_epoch
    right = right_epoch
    left_private = left_point
    right_private = right_point
    f_left = left_derivative
    for _ in range(48):
        if right - left <= _SOLAR_PENUMBRAL_TIME_TOLERANCE_DAYS:
            break
        midpoint = (left + right) / 2.0
        if midpoint == left or midpoint == right:
            break
        fraction = (midpoint - left) / (right - left)
        target = tuple(
            left_private.xyz_itrf_km[index]
            + fraction
            * (right_private.xyz_itrf_km[index] - left_private.xyz_itrf_km[index])
            for index in range(3)
        )
        current = shadow_at(midpoint)
        candidates = _penumbral_limb_tangent_points(current)
        point = min(
            candidates,
            key=lambda candidate: _itrf_distance_sq(candidate.xyz_itrf_km, target),
        )
        before = shadow_at(midpoint - _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
        after = shadow_at(midpoint + _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
        derivative = _solar_altitude_derivative_sign(
            before,
            after,
            point.xyz_itrf_km,
        )
        if f_left * derivative <= 0.0:
            right = midpoint
            right_private = point
        else:
            left = midpoint
            left_private = point
            f_left = derivative
    epoch = (left + right) / 2.0
    current = shadow_at(epoch)
    target = tuple(
        (left_private.xyz_itrf_km[index] + right_private.xyz_itrf_km[index]) / 2.0
        for index in range(3)
    )
    point = min(
        _penumbral_limb_tangent_points(current),
        key=lambda candidate: _itrf_distance_sq(candidate.xyz_itrf_km, target),
    )
    return _track_point(epoch, point)


def _refine_penumbral_limit_junction(
    shadow_at,
    left_epoch: float,
    left_point: _PenumbralGeneratorPoint,
    left_derivative: float,
    right_epoch: float,
    right_point: _PenumbralGeneratorPoint,
    right_derivative: float,
) -> tuple[SolarEclipseFootprintBoundaryKind, SolarEclipseFootprintPoint]:
    """Refine a C_t=0 junction of one path limit with a limb closure."""

    if left_derivative * right_derivative > 0.0:
        raise ArithmeticError("penumbral limit junction requires a sign change")
    left = left_epoch
    right = right_epoch
    left_private = left_point
    right_private = right_point
    f_left = left_derivative
    for _ in range(48):
        if right - left <= _SOLAR_PENUMBRAL_TIME_TOLERANCE_DAYS:
            break
        midpoint = (left + right) / 2.0
        if midpoint == left or midpoint == right:
            break
        fraction = (midpoint - left) / (right - left)
        target = tuple(
            left_private.xyz_itrf_km[index]
            + fraction
            * (right_private.xyz_itrf_km[index] - left_private.xyz_itrf_km[index])
            for index in range(3)
        )
        current = shadow_at(midpoint)
        point = min(
            _penumbral_limb_tangent_points(current),
            key=lambda candidate: _itrf_distance_sq(candidate.xyz_itrf_km, target),
        )
        before = shadow_at(midpoint - _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
        after = shadow_at(midpoint + _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
        derivative = (
            _penumbral_clearance_km(after, point.xyz_itrf_km)
            - _penumbral_clearance_km(before, point.xyz_itrf_km)
        )
        if f_left * derivative <= 0.0:
            right = midpoint
            right_private = point
        else:
            left = midpoint
            left_private = point
            f_left = derivative
    epoch = (left + right) / 2.0
    current = shadow_at(epoch)
    target = tuple(
        (left_private.xyz_itrf_km[index] + right_private.xyz_itrf_km[index]) / 2.0
        for index in range(3)
    )
    point = min(
        _penumbral_limb_tangent_points(current),
        key=lambda candidate: _itrf_distance_sq(candidate.xyz_itrf_km, target),
    )
    before = shadow_at(epoch - _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
    after = shadow_at(epoch + _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
    center_clearance = _penumbral_clearance_km(current, point.xyz_itrf_km)
    curvature = (
        _penumbral_clearance_km(before, point.xyz_itrf_km)
        - 2.0 * center_clearance
        + _penumbral_clearance_km(after, point.xyz_itrf_km)
    )
    if curvature >= -1.0e-9:
        raise ArithmeticError("limb junction is not a maximum-over-time path limit")
    north_component = math.sin(point.azimuth_rad)
    if abs(north_component) <= 1.0e-10:
        raise ArithmeticError("limb junction has ambiguous north/south identity")
    kind = (
        SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH
        if north_component > 0.0
        else SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH
    )
    return kind, _track_point(epoch, point)


def _solve_solar_penumbral_tracks(
    calc: EclipseCalculator,
    contacts: SolarEclipseFootprintContacts,
    topology: SolarEclipseFootprintTopology,
    *,
    sample_count: int,
) -> tuple[SolarEclipseLimitTrack, ...]:
    """Assemble time-ordered limit and sunrise/sunset boundary branches."""

    p1 = contacts.p1.point
    p4 = contacts.p4.point
    structural_contact_epochs = (
        (contacts.p2.point.jd_ut, contacts.p3.point.jd_ut)
        if contacts.p2 is not None and contacts.p3 is not None
        else ()
    )
    output_times = tuple(
        sorted(
            {
                *_sample_interval(p1.jd_ut, p4.jd_ut, sample_count),
                p1.jd_ut,
                p4.jd_ut,
                *structural_contact_epochs,
            }
        )
    )
    sample_times = tuple(
        sorted(
            {
                *_sample_interval(
                    p1.jd_ut,
                    p4.jd_ut,
                    _SOLAR_PENUMBRAL_SOLVER_SAMPLES,
                ),
                p1.jd_ut,
                p4.jd_ut,
                *structural_contact_epochs,
            }
        )
    )
    shadow_cache: dict[float, _EarthFixedSolarShadow] = {}

    def shadow_at(epoch: float) -> _EarthFixedSolarShadow:
        key = round(epoch, 14)
        shadow = shadow_cache.get(key)
        if shadow is None:
            shadow = _earth_fixed_solar_shadow(calc, epoch)
            if shadow is None:
                raise ArithmeticError("solar footprint lost its forward shadow state")
            shadow_cache[key] = shadow
        return shadow

    expected_limit_kinds = (
        {
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH,
            SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH,
        }
        if topology is SolarEclipseFootprintTopology.TWO_LIMIT_TWO_LOOP
        else None
    )
    horizon_intervals = (
        (
            (contacts.p1.point, contacts.p2.point),
            (contacts.p3.point, contacts.p4.point),
        )
        if contacts.p2 is not None and contacts.p3 is not None
        else ((contacts.p1.point, contacts.p4.point),)
    )
    tracks: list[SolarEclipseLimitTrack] = []

    horizon_runs: dict[
        SolarEclipseFootprintBoundaryKind,
        list[list[SolarEclipseFootprintPoint]],
    ] = {
        SolarEclipseFootprintBoundaryKind.SUNRISE: [],
        SolarEclipseFootprintBoundaryKind.SUNSET: [],
    }
    limit_junctions: dict[
        SolarEclipseFootprintBoundaryKind,
        list[SolarEclipseFootprintPoint],
    ] = {
        SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH: [],
        SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH: [],
    }
    for start, end in horizon_intervals:
        interval_times = tuple(
            sorted(
                {
                    *(
                        epoch
                        for epoch in sample_times
                        if start.jd_ut < epoch < end.jd_ut
                    ),
                    *(
                        start.jd_ut + offset
                        for offset in _SOLAR_PENUMBRAL_ENDPOINT_PROBES_DAYS
                        if start.jd_ut + offset < end.jd_ut
                    ),
                    *(
                        end.jd_ut - offset
                        for offset in _SOLAR_PENUMBRAL_ENDPOINT_PROBES_DAYS
                        if start.jd_ut < end.jd_ut - offset
                    ),
                }
            )
        )
        if not interval_times:
            interval_times = tuple(
                _sample_interval(start.jd_ut, end.jd_ut, 3)[1:-1]
            )
        raw_branches: list[
            list[tuple[float, _PenumbralGeneratorPoint, float, float]]
        ] = [[], []]
        for sample_index, epoch in enumerate(interval_times):
            shadow = shadow_at(epoch)
            before = shadow_at(epoch - _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
            after = shadow_at(epoch + _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS)
            points = list(_penumbral_limb_tangent_points(shadow))
            if sample_index == 0:
                points.sort(key=lambda point: point.azimuth_rad)
            else:
                previous_zero = raw_branches[0][-1][1]
                previous_one = raw_branches[1][-1][1]
                direct = (
                    _itrf_distance_sq(
                        previous_zero.xyz_itrf_km,
                        points[0].xyz_itrf_km,
                    )
                    + _itrf_distance_sq(
                        previous_one.xyz_itrf_km,
                        points[1].xyz_itrf_km,
                    )
                )
                crossed = (
                    _itrf_distance_sq(
                        previous_zero.xyz_itrf_km,
                        points[1].xyz_itrf_km,
                    )
                    + _itrf_distance_sq(
                        previous_one.xyz_itrf_km,
                        points[0].xyz_itrf_km,
                    )
                )
                if crossed < direct:
                    points.reverse()
            for branch_index, point in enumerate(points):
                derivative = _solar_altitude_derivative_sign(
                    before,
                    after,
                    point.xyz_itrf_km,
                )
                if derivative == 0.0:
                    raise ArithmeticError("limb tangency has stationary solar altitude")
                clearance_derivative = (
                    _penumbral_clearance_km(after, point.xyz_itrf_km)
                    - _penumbral_clearance_km(before, point.xyz_itrf_km)
                )
                raw_branches[branch_index].append(
                    (epoch, point, derivative, clearance_derivative)
                )

        for branch in raw_branches:
            for left_entry, right_entry in zip(branch, branch[1:]):
                if left_entry[3] == 0.0:
                    north_component = math.sin(left_entry[1].azimuth_rad)
                    kind = (
                        SolarEclipseFootprintBoundaryKind.PENUMBRAL_NORTH
                        if north_component > 0.0
                        else SolarEclipseFootprintBoundaryKind.PENUMBRAL_SOUTH
                    )
                    limit_junctions[kind].append(
                        _track_point(left_entry[0], left_entry[1])
                    )
                elif left_entry[3] * right_entry[3] < 0.0:
                    kind, junction = _refine_penumbral_limit_junction(
                        shadow_at,
                        left_entry[0],
                        left_entry[1],
                        left_entry[3],
                        right_entry[0],
                        right_entry[1],
                        right_entry[3],
                    )
                    limit_junctions[kind].append(junction)
            first_kind = (
                SolarEclipseFootprintBoundaryKind.SUNRISE
                if branch[0][2] > 0.0
                else SolarEclipseFootprintBoundaryKind.SUNSET
            )
            current_kind = first_kind
            current_run = [start, _track_point(branch[0][0], branch[0][1])]
            previous = branch[0]
            for current in branch[1:]:
                current_entry_kind = (
                    SolarEclipseFootprintBoundaryKind.SUNRISE
                    if current[2] > 0.0
                    else SolarEclipseFootprintBoundaryKind.SUNSET
                )
                if current_entry_kind is not current_kind:
                    transition = _refine_horizon_direction_transition(
                        shadow_at,
                        previous[0],
                        previous[1],
                        previous[2],
                        current[0],
                        current[1],
                        current[2],
                    )
                    current_run.append(transition)
                    horizon_runs[current_kind].append(current_run)
                    current_kind = current_entry_kind
                    current_run = [transition]
                current_run.append(_track_point(current[0], current[1]))
                previous = current
            current_run.append(end)
            horizon_runs[current_kind].append(current_run)

    for junctions in limit_junctions.values():
        for junction in junctions:
            xyz_itrf_km = _wgs84_surface_xyz_km(
                junction.latitude_deg,
                junction.longitude_deg,
            )
            derivative = _solar_altitude_derivative_sign(
                shadow_at(junction.jd_ut - _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS),
                shadow_at(junction.jd_ut + _SOLAR_PENUMBRAL_DERIVATIVE_STEP_DAYS),
                xyz_itrf_km,
            )
            horizon_kind = (
                SolarEclipseFootprintBoundaryKind.SUNRISE
                if derivative > 0.0
                else SolarEclipseFootprintBoundaryKind.SUNSET
            )
            candidate_runs = tuple(
                run
                for run in horizon_runs[horizon_kind]
                if run[0].jd_ut - 1.0e-10
                <= junction.jd_ut
                <= run[-1].jd_ut + 1.0e-10
            )
            if not candidate_runs:
                raise ArithmeticError("penumbral-limit junction escaped horizon tracks")
            chosen = min(
                candidate_runs,
                key=lambda run: min(
                    _itrf_distance_sq(
                        xyz_itrf_km,
                        _wgs84_surface_xyz_km(
                            point.latitude_deg,
                            point.longitude_deg,
                        ),
                    )
                    for point in run
                ),
            )
            chosen.append(junction)

    ordered_junctions = {
        kind: _ordered_unique_track_points(junctions)
        for kind, junctions in limit_junctions.items()
    }
    junction_kinds = {
        kind for kind, junctions in ordered_junctions.items() if junctions
    }
    if expected_limit_kinds is None:
        if len(junction_kinds) != 1:
            raise ArithmeticError(
                "one-limit topology must expose one penumbral-limit junction pair"
            )
        expected_limit_kinds = junction_kinds
    elif junction_kinds != expected_limit_kinds:
        raise ArithmeticError(
            "two-limit topology must expose both penumbral-limit junction pairs"
        )
    for kind in expected_limit_kinds:
        junctions = ordered_junctions[kind]
        if len(junctions) != 2:
            raise ArithmeticError(
                f"{kind.value} must meet the horizon boundary at exactly two junctions"
            )

    # The envelope is a contour in (UT1, generator azimuth), not a
    # single-valued function of time. A temporal fold produces two lawful
    # points at one epoch. Exact horizon incidences and exponentially close
    # inward probes seed those short branches; the fixed solver lattice then
    # carries each branch by terrestrial-space continuity. Public sample_count
    # controls materialization only.
    envelope_epochs = {
        epoch for epoch in sample_times if p1.jd_ut < epoch < p4.jd_ut
    }
    for junctions in ordered_junctions.values():
        for junction in junctions:
            envelope_epochs.add(junction.jd_ut)
            for adjacent in (
                math.nextafter(junction.jd_ut, float("-inf")),
                math.nextafter(junction.jd_ut, float("inf")),
            ):
                if p1.jd_ut < adjacent < p4.jd_ut:
                    envelope_epochs.add(adjacent)
            for offset in _SOLAR_PENUMBRAL_ENDPOINT_PROBES_DAYS:
                for direction in (-1.0, 1.0):
                    epoch = junction.jd_ut + direction * offset
                    if p1.jd_ut < epoch < p4.jd_ut:
                        envelope_epochs.add(epoch)
    ordered_envelope_epochs = tuple(sorted(envelope_epochs))
    global_solver_epochs = tuple(
        _sample_interval(
            p1.jd_ut,
            p4.jd_ut,
            _SOLAR_PENUMBRAL_SOLVER_SAMPLES,
        )
    )

    slices_by_kind: dict[
        SolarEclipseFootprintBoundaryKind,
        list[tuple[float, list[_PenumbralEnvelopeNode]]],
    ] = {kind: [] for kind in expected_limit_kinds}
    for epoch in ordered_envelope_epochs:
        solved = _penumbral_envelope_nodes_at(
            shadow_at,
            epoch,
            globally_admit=True,
            solver_epochs=global_solver_epochs,
        )
        for kind in expected_limit_kinds:
            nodes = list(solved.get(kind, ()))
            for junction in ordered_junctions[kind]:
                if abs(junction.jd_ut - epoch) > 1.0e-12:
                    continue
                junction_xyz = _wgs84_surface_xyz_km(
                    junction.latitude_deg,
                    junction.longitude_deg,
                )
                generator = min(
                    _penumbral_limb_tangent_points(shadow_at(epoch)),
                    key=lambda candidate: _itrf_distance_sq(
                        candidate.xyz_itrf_km,
                        junction_xyz,
                    ),
                )
                coincident_index = next(
                    (
                        index
                        for index, node in enumerate(nodes)
                        if _itrf_distance_sq(
                            node.generator.xyz_itrf_km,
                            generator.xyz_itrf_km,
                        )
                        <= 0.02 * 0.02
                    ),
                    None,
                )
                if coincident_index is not None:
                    nodes[coincident_index] = _PenumbralEnvelopeNode(
                        jd_ut=epoch,
                        generator=generator,
                        point=junction,
                    )
                else:
                    maximum = _continuous_site_maximum_clearance(
                        shadow_at,
                        generator.xyz_itrf_km,
                        epoch,
                        global_solver_epochs,
                    )
                    if maximum > _SOLAR_PENUMBRAL_CLEARANCE_TOLERANCE_KM:
                        raise ArithmeticError(
                            "penumbral/horizon junction is not a global path limit"
                        )
                    nodes.append(
                        _PenumbralEnvelopeNode(
                            jd_ut=epoch,
                            generator=generator,
                            point=junction,
                        )
                    )
            nodes.sort(key=lambda node: node.generator.azimuth_rad)
            slices_by_kind[kind].append((epoch, nodes))

    # Candidate discovery above is deliberately independent of public output
    # density, but a close root pair can still lie wholly inside one azimuth
    # discovery cell.  The governing contour is horizon connected: continue
    # each exact horizon incidence over the fixed structural epochs and repair
    # a missing candidate locally.  Disconnected candidates are left visible
    # so the component-closure checks below can fail closed rather than prune
    # an inconvenient branch.
    fold_join_distance_sq = 100.0 * 100.0
    continuation_distance_sq = 1_000.0 * 1_000.0
    continuation_azimuth_limit_rad = 0.25
    coincident_node_distance_sq = 0.02 * 0.02
    horizon_seed_acquisition_days = 0.25 / 86400.0
    single_root_gap_days = 120.0 / 86400.0

    def circular_azimuth_distance(left: float, right: float) -> float:
        return abs((left - right + math.pi) % math.tau - math.pi)

    for kind in sorted(expected_limit_kinds, key=lambda value: value.value):
        slices = slices_by_kind[kind]
        for junction in ordered_junctions[kind]:
            junction_index = next(
                (
                    index
                    for index, (epoch, _nodes) in enumerate(slices)
                    if abs(epoch - junction.jd_ut) <= 1.0e-12
                ),
                None,
            )
            if junction_index is None:
                raise ArithmeticError(
                    "penumbral continuation lost its horizon seed epoch"
                )
            seed_node = next(
                (
                    node
                    for node in slices[junction_index][1]
                    if _footprint_points_coincide(node.point, junction)
                ),
                None,
            )
            if seed_node is None:
                raise ArithmeticError(
                    "penumbral continuation lost its horizon seed point"
                )
            other_junction = next(
                candidate
                for candidate in ordered_junctions[kind]
                if not _footprint_points_coincide(candidate, junction)
            )

            for direction in (-1, 1):
                last_node = seed_node
                acquired = False
                target_indices = range(
                    junction_index + direction,
                    len(slices) if direction > 0 else -1,
                    direction,
                )
                for step_index, target_index in enumerate(target_indices):
                    epoch, nodes = slices[target_index]
                    gap_days = abs(epoch - last_node.jd_ut)
                    if gap_days > single_root_gap_days:
                        break

                    current: _PenumbralEnvelopeNode | None = None
                    if step_index > 0 and nodes:
                        nearest = min(
                            nodes,
                            key=lambda node: circular_azimuth_distance(
                                node.generator.azimuth_rad,
                                last_node.generator.azimuth_rad,
                            ),
                        )
                        if (
                            circular_azimuth_distance(
                                nearest.generator.azimuth_rad,
                                last_node.generator.azimuth_rad,
                            )
                            <= continuation_azimuth_limit_rad
                            and _itrf_distance_sq(
                                nearest.generator.xyz_itrf_km,
                                last_node.generator.xyz_itrf_km,
                            )
                            <= continuation_distance_sq
                        ):
                            current = nearest

                    if current is None:
                        corrected = _continue_penumbral_envelope_node(
                            shadow_at,
                            epoch,
                            last_node.generator.azimuth_rad,
                            kind,
                            global_solver_epochs,
                        )
                        if corrected is None or (
                            _itrf_distance_sq(
                                corrected.generator.xyz_itrf_km,
                                last_node.generator.xyz_itrf_km,
                            )
                            > continuation_distance_sq
                        ):
                            if not acquired:
                                if gap_days <= horizon_seed_acquisition_days:
                                    continue
                                break
                            continue
                        coincident = (
                            min(
                                nodes,
                                key=lambda node: _itrf_distance_sq(
                                    node.generator.xyz_itrf_km,
                                    corrected.generator.xyz_itrf_km,
                                ),
                            )
                            if nodes
                            else None
                        )
                        if coincident is not None and (
                            _itrf_distance_sq(
                                coincident.generator.xyz_itrf_km,
                                corrected.generator.xyz_itrf_km,
                            )
                            <= coincident_node_distance_sq
                        ):
                            current = coincident
                        else:
                            nodes.append(corrected)
                            nodes.sort(
                                key=lambda node: node.generator.azimuth_rad
                            )
                            current = corrected

                    acquired = True
                    last_node = current
                    if _footprint_points_coincide(
                        current.point,
                        other_junction,
                    ):
                        break

    envelope_tracks: list[SolarEclipseLimitTrack] = []
    for kind in sorted(expected_limit_kinds, key=lambda value: value.value):
        kind_junctions = ordered_junctions[kind]

        def is_horizon_junction(node: _PenumbralEnvelopeNode) -> bool:
            return any(
                _footprint_points_coincide(node.point, junction)
                for junction in kind_junctions
            )

        branches: list[list[_PenumbralEnvelopeNode]] = []
        previous_epoch = p1.jd_ut
        previous_nodes: list[_PenumbralEnvelopeNode] = []
        previous_branch_ids: list[int] = []

        for epoch, current_nodes in slices_by_kind[kind]:
            if (
                len(previous_nodes) == 1
                and not current_nodes
                and epoch - previous_epoch <= single_root_gap_days
            ):
                # A higher-order clearance contact can make the negative-
                # curvature witness indeterminate for an isolated solver
                # epoch. Keep the admitted branch pending; only a nearby
                # reappearance may reconnect it.
                continue
            current_branch_ids: list[int | None] = [None] * len(current_nodes)
            if len(previous_nodes) >= 2 and not current_nodes:
                fold = _refine_penumbral_envelope_fold(
                    shadow_at,
                    kind,
                    previous_epoch,
                    epoch,
                    global_solver_epochs,
                    inside_nodes_hint=tuple(previous_nodes),
                )
                for branch_id in previous_branch_ids:
                    if not _footprint_points_coincide(
                        branches[branch_id][-1].point,
                        fold.point,
                    ):
                        branches[branch_id].append(fold)
            elif not previous_nodes and len(current_nodes) >= 2:
                fold = _refine_penumbral_envelope_fold(
                    shadow_at,
                    kind,
                    epoch,
                    previous_epoch,
                    global_solver_epochs,
                    inside_nodes_hint=tuple(current_nodes),
                )
                for index, node in enumerate(current_nodes):
                    branch_id = len(branches)
                    branches.append([fold, node])
                    current_branch_ids[index] = branch_id
            elif previous_nodes and current_nodes:
                pair_candidates = sorted(
                    (
                        (
                            _itrf_distance_sq(
                                previous.generator.xyz_itrf_km,
                                current.generator.xyz_itrf_km,
                            ),
                            previous_index,
                            current_index,
                        )
                        for previous_index, previous in enumerate(previous_nodes)
                        for current_index, current in enumerate(current_nodes)
                    ),
                    key=lambda entry: entry[0],
                )
                matched_previous: set[int] = set()
                matched_current: set[int] = set()
                for distance_sq, previous_index, current_index in pair_candidates:
                    if distance_sq > continuation_distance_sq:
                        break
                    if (
                        previous_index in matched_previous
                        or current_index in matched_current
                    ):
                        continue
                    branch_id = previous_branch_ids[previous_index]
                    branches[branch_id].append(current_nodes[current_index])
                    current_branch_ids[current_index] = branch_id
                    matched_previous.add(previous_index)
                    matched_current.add(current_index)
                    if len(matched_previous) == min(
                        len(previous_nodes), len(current_nodes)
                    ):
                        break

                for current_index, current in enumerate(current_nodes):
                    if current_index in matched_current:
                        continue
                    branch: list[_PenumbralEnvelopeNode] = []
                    if (
                        not is_horizon_junction(current)
                        and len(previous_nodes) == 1
                        and not is_horizon_junction(previous_nodes[0])
                        and (
                        _itrf_distance_sq(
                            previous_nodes[0].generator.xyz_itrf_km,
                            current.generator.xyz_itrf_km,
                        )
                        <= fold_join_distance_sq
                        )
                    ):
                        branch.append(previous_nodes[0])
                    branch.append(current)
                    branch_id = len(branches)
                    branches.append(branch)
                    current_branch_ids[current_index] = branch_id

                for previous_index, previous in enumerate(previous_nodes):
                    if previous_index in matched_previous:
                        continue
                    if is_horizon_junction(previous):
                        continue
                    nearest = min(
                        current_nodes,
                        key=lambda current: _itrf_distance_sq(
                            previous.generator.xyz_itrf_km,
                            current.generator.xyz_itrf_km,
                        ),
                    )
                    if (
                        _itrf_distance_sq(
                            previous.generator.xyz_itrf_km,
                            nearest.generator.xyz_itrf_km,
                        )
                        <= fold_join_distance_sq
                    ):
                        branch_id = previous_branch_ids[previous_index]
                        branches[branch_id].append(nearest)
            else:
                for index, node in enumerate(current_nodes):
                    branch_id = len(branches)
                    branches.append([node])
                    current_branch_ids[index] = branch_id

            previous_epoch = epoch
            previous_nodes = current_nodes
            previous_branch_ids = [
                branch_id
                for branch_id in current_branch_ids
                if branch_id is not None
            ]

        canonical_branches: list[tuple[SolarEclipseFootprintPoint, ...]] = []
        for branch in branches:
            ordered_nodes = sorted(branch, key=lambda node: node.jd_ut)
            unique_nodes: list[_PenumbralEnvelopeNode] = []
            for node in ordered_nodes:
                if unique_nodes and abs(node.jd_ut - unique_nodes[-1].jd_ut) <= 1.0e-12:
                    if not _footprint_points_coincide(
                        node.point,
                        unique_nodes[-1].point,
                    ):
                        raise ArithmeticError(
                            "one penumbral segment acquired two points at one epoch"
                        )
                    continue
                unique_nodes.append(node)
            if len(unique_nodes) < 2:
                continue
            canonical_branches.append(tuple(node.point for node in unique_nodes))

        if not canonical_branches:
            raise ArithmeticError(f"{kind.value} produced no complete envelope segment")

        unassigned = set(range(len(canonical_branches)))
        component_groups: list[list[int]] = []
        while unassigned:
            seed = min(unassigned)
            unassigned.remove(seed)
            component = [seed]
            frontier = [seed]
            while frontier:
                current_index = frontier.pop()
                current_endpoints = (
                    canonical_branches[current_index][0],
                    canonical_branches[current_index][-1],
                )
                connected = tuple(
                    candidate_index
                    for candidate_index in unassigned
                    if any(
                        _footprint_points_coincide(left, right)
                        for left in current_endpoints
                        for right in (
                            canonical_branches[candidate_index][0],
                            canonical_branches[candidate_index][-1],
                        )
                    )
                )
                for candidate_index in connected:
                    unassigned.remove(candidate_index)
                    component.append(candidate_index)
                    frontier.append(candidate_index)
            component_groups.append(component)

        component_groups.sort(
            key=lambda group: min(
                canonical_branches[index][0].jd_ut for index in group
            )
        )
        for component_id, group in enumerate(component_groups):
            ordered_segments = sorted(
                (canonical_branches[index] for index in group),
                key=lambda points: (
                    points[0].jd_ut,
                    points[-1].jd_ut,
                    points[0].latitude_deg,
                    points[0].longitude_deg,
                ),
            )
            for segment_id, points in enumerate(ordered_segments):
                materialized = _materialize_track_points(
                    points,
                    output_times,
                )
                envelope_tracks.append(
                    SolarEclipseLimitTrack(
                        kind=kind,
                        component_id=component_id,
                        segment_id=segment_id,
                        points=materialized,
                    )
                )

    tracks.extend(envelope_tracks)

    junction_points = tuple(
        point for junctions in ordered_junctions.values() for point in junctions
    )
    for kind in (
        SolarEclipseFootprintBoundaryKind.SUNRISE,
        SolarEclipseFootprintBoundaryKind.SUNSET,
    ):
        for component_id, points in enumerate(horizon_runs[kind]):
            ordered_points = _ordered_unique_track_points(points)
            materialized = _materialize_track_points(
                ordered_points,
                output_times,
                mandatory_points=junction_points,
            )
            tracks.append(
                SolarEclipseLimitTrack(
                    kind=kind,
                    component_id=component_id,
                    segment_id=0,
                    points=materialized,
                )
            )
    return tuple(tracks)


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
