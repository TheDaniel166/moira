"""
Occultation Engine — moira/occultations.py

Archetype: Engine
Purpose: Detects close approaches and occultations between solar system bodies
         and between the Moon and fixed stars, by scanning for angular
         separation minima and refining ingress/egress contacts via bisection.

Boundary declaration:
    Owns: angular separation computation (ecliptic and equatorial), golden-
          section minimum search, ingress/egress bisection, and the
          CloseApproach and LunarOccultation result types.
    Delegates: geocentric planetary positions to moira.planets.planet_at;
               topocentric positions to moira.planets.sky_position_at;
               fixed-star positions to moira.stars.star_at (lazy import);
               obliquity to moira.obliquity.true_obliquity; coordinate
               conversion to moira.coordinates.ecliptic_to_equatorial;
               kernel I/O to moira.spk_reader.

Import-time side effects: None

External dependency assumptions:
    - moira.planets.planet_at returns a PlanetData with .longitude and
      .latitude fields in ecliptic degrees.
    - moira.planets.sky_position_at returns a SkyPosition with
      .right_ascension and .declination fields.
    - moira.spk_reader.get_reader() is callable without arguments.

Public surface / exports:
    CloseApproach             — result dataclass for a minimum-separation event
    LunarOccultation          — result dataclass for a Moon occultation event
    close_approaches()        — all close approaches between two bodies
    lunar_occultation()       — Moon occultations of a planet in a date range
    lunar_occultation_path_at() / lunar_occultation_path()
                              — typed path geometry for planetary occultations
    lunar_star_occultation()  — Moon occultations of a fixed star
    lunar_star_occultation_path_at() / lunar_star_occultation_path()
                              — typed path geometry for stellar occultations
    all_lunar_occultations()  — Moon occultations of all visible planets
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Callable
from enum import Enum
from numbers import Real

from .constants import Body, EARTH_RADIUS_KM, SUN_RADIUS_KM
from .planets import planet_at, sky_position_at, _earth_barycentric_state, _geocentric
from .julian import (
    CalendarDateTime,
    calendar_datetime_from_jd,
    datetime_from_jd,
    format_jd_utc,
    local_sidereal_time,
)
from ._ephemeris_time import _ut1_to_ephemeris_tt
from .spk_reader import get_reader, SpkReader
from .coordinates import (
    ecliptic_to_equatorial,
    equatorial_to_horizontal,
    horizontal_to_equatorial,
    icrf_to_equatorial,
    mat_vec_mul,
    precession_matrix_equatorial,
    nutation_matrix_equatorial,
)
from .obliquity import nutation, true_obliquity
from .eclipse_geometry import apparent_radius as _apparent_radius, MOON_RADIUS_KM
from .corrections import (
    apply_aberration,
    apply_deflection,
    apply_frame_bias,
    apply_refraction,
    SCHWARZSCHILD_RADII,
)
from .geoutils import (
    EARTH_KM_PER_DEG_LAT as _EARTH_KM_PER_DEG_LAT,
    offset_geographic_km as _offset_geographic_km,
    sample_interval as _sample_interval,
    wrap_longitude_deg as _wrap_longitude_deg,
)

__all__ = [
    "CloseApproach",
    "LunarOccultation",
    "OccultationPathBoundaryPoint",
    "OccultationPathBoundarySide",
    "OccultationPathBoundaryTrack",
    "OccultationGeographicPole",
    "OccultationPoleCrossing",
    "OccultationPoleCrossingPhase",
    "GrazeCircumstances",
    "GrazeTableRow",
    "GrazeProductGeometry",
    "GrazeProductTrack",
    "close_approaches",
    "lunar_occultation",
    "lunar_occultation_path_at",
    "lunar_occultation_path",
    "lunar_occultation_path_topology_at",
    "lunar_occultation_path_topology",
    "lunar_star_graze_latitude",
    "lunar_star_graze_line",
    "lunar_star_graze_product_at",
    "lunar_star_graze_product_track",
    "lunar_star_practical_graze_latitude",
    "lunar_star_graze_table",
    "lunar_star_occultation",
    "lunar_star_graze_circumstances",
    "lunar_star_occultation_path_at",
    "lunar_star_occultation_path",
    "lunar_star_occultation_path_topology_at",
    "lunar_star_occultation_path_topology",
    "all_lunar_occultations",
    "OccultationPathGeometry",
    "OccultationPathPoint",
    "OccultationPathTopology",
    "OccultationPathTopologyKind",
]

# ---------------------------------------------------------------------------
# Phase 3 — OccultationPathGeometry  (Defer.Design + Defer.Validation)
# ---------------------------------------------------------------------------

_OCCULTATION_TOPOLOGY_DEFAULT_SAMPLES = 65
_OCCULTATION_TOPOLOGY_MIN_SAMPLES = 9
_OCCULTATION_TOPOLOGY_MAX_SAMPLES = 721

@dataclass(frozen=True, slots=True)
class OccultationPathGeometry:
    """
    Typed vessel for the geographic path of a planetary or stellar occultation.

    Initial typed vessel for occultation path geometry.

    Doctrine
    --------
    An occultation path encodes the geographic track of the occulting body's
    shadow (or umbra for deep occultations) across the Earth's surface.
    It is distinct from :class:`LunarOccultation` (which records the event at
    a single observer) and from :class:`~moira.eclipse.SolarEclipsePath`
    (which covers the Moon's umbral shadow during solar eclipses).

    The surface answers: "where on Earth can this occultation be seen, and
    what are the ingress/egress times at each latitude band?"

    Legacy engines expose this as raw float arrays. This vessel expresses the
    same information as
    named, typed fields.

    Current implementation state
    ----------------------------
    Moira now exposes an initial exact-JD path builder for lunar occultations
    of planets and fixed stars. The current surface solves the greatest
    geography numerically from topocentric separation and samples the
    visibility track around the supplied greatest-occultation instant.

    Validation state
    ----------------
    The current implemented slice is externally checked against a local
    reference fixture for greatest-geography agreement and
    against external IOTA graze/limit text files for fixed-longitude graze
    boundary agreement on multiple bright-star events (currently El Nath,
    Spica north/south limits, epsilon Ari, Alcyone, Merope, Asellus
    Borealis, and Regulus). Where an IOTA file declares a nominal site
    altitude, that altitude is now carried into the graze solve. Moira also
    exposes an explicit lunar-limb profile correction hook for future
    topography-backed graze work, but no sovereign built-in profile dataset
    is yet bound into this module.

    Fields
    ------
    occulting_body : str
        Name of the body causing the occultation (e.g. ``Body.MOON``).
    occulted_body : str
        Name of the body being occulted (e.g. ``Body.MARS`` or a star name).
    jd_greatest_ut : float
        Julian Day (UT1) at greatest occultation (closest approach on the
        central line).
    central_line_lats : tuple of float
        Geographic latitudes (degrees) along the path of greatest occultation,
        sampled from first to last external contact.
    central_line_lons : tuple of float
        Geographic longitudes (degrees) at the same sample points.
    path_width_km : float
        Width of the occultation visibility zone in kilometres at greatest
        occultation.  Derived from the occulting body's angular diameter and
        the shadow geometry.
    duration_at_greatest_s : float
        Duration of occultation in seconds at the point of greatest occultation.
    """
    occulting_body:          str
    occulted_body:           str
    jd_greatest_ut:          float
    central_line_lats:       tuple
    central_line_lons:       tuple
    path_width_km:           float
    duration_at_greatest_s:  float


class OccultationPathBoundarySide(str, Enum):
    """Intrinsic side of an occultation path relative to increasing UT1."""

    LEFT = "left"
    RIGHT = "right"


class OccultationPathTopologyKind(str, Enum):
    """Admitted topology of an occultation path on the Earth sphere."""

    TWO_SIDED_BAND = "two_sided_band"


class OccultationGeographicPole(str, Enum):
    """Canonical geographic pole participating in a path boundary contact."""

    NORTH = "north"
    SOUTH = "south"


class OccultationPoleCrossingPhase(str, Enum):
    """Whether a pole enters or leaves the instantaneous occultation region."""

    INGRESS = "ingress"
    EGRESS = "egress"


def _path_real(owner: str, name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{owner}.{name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{owner}.{name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class OccultationPathPoint:
    """One inspectable point on an occultation center or limit track."""

    jd_ut: float
    latitude_deg: float
    longitude_deg: float
    separation_deg: float
    clearance_deg: float

    def __post_init__(self) -> None:
        owner = type(self).__name__
        for name in (
            "jd_ut",
            "latitude_deg",
            "longitude_deg",
            "separation_deg",
            "clearance_deg",
        ):
            object.__setattr__(
                self,
                name,
                _path_real(owner, name, getattr(self, name)),
            )
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError(f"{owner}.latitude_deg must be within [-90, 90]")
        longitude = (
            0.0
            if abs(self.latitude_deg) == 90.0
            else _wrap_longitude_deg(self.longitude_deg)
        )
        object.__setattr__(self, "longitude_deg", longitude)
        if self.separation_deg < 0.0:
            raise ValueError(f"{owner}.separation_deg must be non-negative")

@dataclass(frozen=True, slots=True)
class OccultationPathBoundaryPoint:
    """One oriented cross-track limit point and its center distance."""

    side: OccultationPathBoundarySide
    point: OccultationPathPoint
    cross_track_distance_km: float

    def __post_init__(self) -> None:
        try:
            side = OccultationPathBoundarySide(self.side)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid occultation path boundary side") from exc
        object.__setattr__(self, "side", side)
        if not isinstance(self.point, OccultationPathPoint):
            raise TypeError("OccultationPathBoundaryPoint.point must be an OccultationPathPoint")
        distance = _path_real(
            type(self).__name__,
            "cross_track_distance_km",
            self.cross_track_distance_km,
        )
        if distance < 0.0:
            raise ValueError("cross_track_distance_km must be non-negative")
        if abs(self.point.clearance_deg) > _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG:
            raise ValueError("boundary-point clearance residual exceeds tolerance")
        object.__setattr__(self, "cross_track_distance_km", distance)


@dataclass(frozen=True, slots=True)
class OccultationPathBoundaryTrack:
    """One time-continuous intrinsic limit of an occultation band."""

    side: OccultationPathBoundarySide
    points: tuple[OccultationPathBoundaryPoint, ...]

    def __post_init__(self) -> None:
        try:
            side = OccultationPathBoundarySide(self.side)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid occultation path boundary side") from exc
        points = tuple(self.points)
        if len(points) < _OCCULTATION_TOPOLOGY_MIN_SAMPLES:
            raise ValueError(
                "OccultationPathBoundaryTrack requires at least "
                f"{_OCCULTATION_TOPOLOGY_MIN_SAMPLES} points"
            )
        if any(not isinstance(point, OccultationPathBoundaryPoint) for point in points):
            raise TypeError(
                "OccultationPathBoundaryTrack.points must contain boundary points"
            )
        if any(point.side is not side for point in points):
            raise ValueError("boundary track point sides must match the track side")
        if any(
            left.point.jd_ut >= right.point.jd_ut
            for left, right in zip(points, points[1:])
        ):
            raise ValueError("occultation boundary points must be strictly time ordered")
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "points", points)


@dataclass(frozen=True, slots=True)
class OccultationPoleCrossing:
    """One exact-pole zero-clearance contact solved continuously in UT1."""

    pole: OccultationGeographicPole
    phase: OccultationPoleCrossingPhase
    point: OccultationPathPoint
    boundary_side: OccultationPathBoundarySide | None

    def __post_init__(self) -> None:
        try:
            pole = OccultationGeographicPole(self.pole)
            phase = OccultationPoleCrossingPhase(self.phase)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid occultation pole-crossing identity") from exc
        if not isinstance(self.point, OccultationPathPoint):
            raise TypeError("OccultationPoleCrossing.point must be OccultationPathPoint")
        expected_latitude = 90.0 if pole is OccultationGeographicPole.NORTH else -90.0
        if self.point.latitude_deg != expected_latitude or self.point.longitude_deg != 0.0:
            raise ValueError("pole-crossing point must use the canonical exact pole")
        if abs(self.point.clearance_deg) > _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG:
            raise ValueError("pole-crossing clearance residual exceeds tolerance")
        side = self.boundary_side
        if side is not None:
            try:
                side = OccultationPathBoundarySide(side)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid pole-crossing boundary side") from exc
        object.__setattr__(self, "pole", pole)
        object.__setattr__(self, "phase", phase)
        object.__setattr__(self, "boundary_side", side)


@dataclass(frozen=True, slots=True)
class OccultationPathTopology:
    """Detailed, pole-safe topology behind an occultation path summary."""

    summary: OccultationPathGeometry
    topology: OccultationPathTopologyKind
    centers: tuple[OccultationPathPoint, ...]
    boundaries: tuple[OccultationPathBoundaryTrack, ...]
    greatest_left: OccultationPathBoundaryPoint
    greatest_right: OccultationPathBoundaryPoint
    pole_crossings: tuple[OccultationPoleCrossing, ...]
    lunar_limb_model: str
    target_model: str
    observer_elevation_m: float
    observer_geometry: str = "WGS84_GEODETIC"
    width_metric: str = "SPHERICAL_GREAT_CIRCLE_R6378_137_KM"
    time_scale: str = "UT1"
    atmospheric_refraction: bool = False
    saturn_rings_included: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.summary, OccultationPathGeometry):
            raise TypeError("OccultationPathTopology.summary must be OccultationPathGeometry")
        try:
            topology = OccultationPathTopologyKind(self.topology)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid occultation path topology") from exc
        if topology is not OccultationPathTopologyKind.TWO_SIDED_BAND:
            raise ValueError("only the two-sided occultation band is admitted")
        if self.summary.occulting_body != Body.MOON:
            raise ValueError("occultation topology requires the Moon as occulting body")
        if self.target_model == "JPL_EQUATORIAL_SOLID_BODY":
            if self.summary.occulted_body not in _TOPOLOGY_JPL_EQUATORIAL_TARGET_RADII_KM:
                raise ValueError(
                    "JPL solid-body topology requires an admitted non-solar planet"
                )
        elif self.target_model == "POINT_SOURCE":
            if self.summary.occulted_body.casefold() in (
                _SOLAR_SYSTEM_BODY_LABELS_CASEFOLD
            ):
                raise ValueError(
                    "point-source topology cannot identify a Solar System body"
                )
        else:
            raise ValueError("invalid target_model")
        centers = tuple(self.centers)
        if not _OCCULTATION_TOPOLOGY_MIN_SAMPLES <= len(centers) <= _OCCULTATION_TOPOLOGY_MAX_SAMPLES:
            raise ValueError("occultation topology center count is outside the admitted range")
        if any(not isinstance(point, OccultationPathPoint) for point in centers):
            raise TypeError("OccultationPathTopology.centers must contain path points")
        if any(left.jd_ut >= right.jd_ut for left, right in zip(centers, centers[1:])):
            raise ValueError("occultation topology centers must be strictly time ordered")
        if any(
            point.clearance_deg < -_OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG
            for point in centers
        ):
            raise ValueError("occultation topology centers must remain inside the footprint")
        if abs(centers[0].clearance_deg) > _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG or (
            abs(centers[-1].clearance_deg)
            > _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG
        ):
            raise ValueError("occultation topology endpoints must be zero-clearance contacts")
        boundaries = tuple(self.boundaries)
        if tuple(track.side for track in boundaries) != (
            OccultationPathBoundarySide.LEFT,
            OccultationPathBoundarySide.RIGHT,
        ):
            raise ValueError("occultation topology requires ordered left and right tracks")
        if any(len(track.points) != len(centers) for track in boundaries):
            raise ValueError("occultation centers and boundary tracks must share one epoch lattice")
        for track in boundaries:
            if any(
                center.jd_ut != boundary.point.jd_ut
                for center, boundary in zip(centers, track.points)
            ):
                raise ValueError("occultation center and boundary epochs must match")
            for center, boundary in zip(centers, track.points):
                measured_distance = _surface_distance_km(
                    center.latitude_deg,
                    center.longitude_deg,
                    boundary.point.latitude_deg,
                    boundary.point.longitude_deg,
                )
                if abs(measured_distance - boundary.cross_track_distance_km) > (
                    _OCCULTATION_PUBLIC_DISTANCE_TOLERANCE_KM
                ):
                    raise ValueError(
                        "boundary half-width must equal its spherical center distance"
                    )
        if self.summary.central_line_lats != tuple(
            point.latitude_deg for point in centers
        ) or self.summary.central_line_lons != tuple(
            point.longitude_deg for point in centers
        ):
            raise ValueError("summary central line must be the exact center-track projection")
        if self.greatest_left.side is not OccultationPathBoundarySide.LEFT:
            raise ValueError("greatest_left must carry the left boundary side")
        if self.greatest_right.side is not OccultationPathBoundarySide.RIGHT:
            raise ValueError("greatest_right must carry the right boundary side")
        if self.greatest_left.point.jd_ut != self.summary.jd_greatest_ut or (
            self.greatest_right.point.jd_ut != self.summary.jd_greatest_ut
        ):
            raise ValueError("greatest boundary epochs must equal summary greatest UT1")
        greatest_index = next(
            (
                index
                for index, center in enumerate(centers)
                if center.jd_ut == self.summary.jd_greatest_ut
            ),
            None,
        )
        if greatest_index is None or self.greatest_left != boundaries[0].points[
            greatest_index
        ] or self.greatest_right != boundaries[1].points[greatest_index]:
            raise ValueError("greatest boundaries must be their track samples")
        if self.summary.path_width_km != (
            self.greatest_left.cross_track_distance_km
            + self.greatest_right.cross_track_distance_km
        ):
            raise ValueError("summary width must equal the two greatest half-widths")
        duration_at_greatest_s = _path_real(
            type(self).__name__,
            "summary.duration_at_greatest_s",
            self.summary.duration_at_greatest_s,
        )
        if duration_at_greatest_s <= 0.0:
            raise ValueError("occultation topology greatest-site duration must be positive")
        # The public vessel intentionally exposes the duration, not its private
        # fixed-site contact instants.  The strongest public invariant is
        # therefore that a site's occultation cannot outlive the global moving
        # footprint represented by the center-track endpoints.
        global_duration_s = (centers[-1].jd_ut - centers[0].jd_ut) * 86400.0
        duration_tolerance_s = max(
            1.0e-6,
            8.0
            * math.ulp(max(abs(centers[0].jd_ut), abs(centers[-1].jd_ut)))
            * 86400.0,
        )
        if duration_at_greatest_s > global_duration_s + duration_tolerance_s:
            raise ValueError(
                "greatest-site duration cannot exceed the global footprint lifetime"
            )
        pole_crossings = tuple(self.pole_crossings)
        if any(not isinstance(crossing, OccultationPoleCrossing) for crossing in pole_crossings):
            raise TypeError("pole_crossings must contain OccultationPoleCrossing values")
        if any(
            left.point.jd_ut >= right.point.jd_ut
            for left, right in zip(pole_crossings, pole_crossings[1:])
        ):
            raise ValueError("pole crossings must be strictly time ordered")
        if any(
            crossing.point.jd_ut < centers[0].jd_ut
            or crossing.point.jd_ut > centers[-1].jd_ut
            for crossing in pole_crossings
        ):
            raise ValueError("pole crossings must lie within the topology epoch window")
        for pole in OccultationGeographicPole:
            pole_events = tuple(
                crossing for crossing in pole_crossings if crossing.pole is pole
            )
            if pole_events and tuple(event.phase for event in pole_events) != (
                OccultationPoleCrossingPhase.INGRESS,
                OccultationPoleCrossingPhase.EGRESS,
            ):
                raise ValueError(
                    "each admitted pole containment requires one ingress then one egress"
                )
        if self.observer_geometry != "WGS84_GEODETIC":
            raise ValueError("observer_geometry must identify WGS84 geodetic observers")
        if self.width_metric != "SPHERICAL_GREAT_CIRCLE_R6378_137_KM":
            raise ValueError("width_metric must identify Moira's admitted spherical metric")
        if self.time_scale != "UT1":
            raise ValueError("occultation path topology time_scale must be UT1")
        observer_elevation_m = _validate_topology_observer_elevation(
            self.observer_elevation_m
        )
        if not isinstance(self.atmospheric_refraction, bool):
            raise TypeError("atmospheric_refraction must be bool")
        if self.atmospheric_refraction:
            raise ValueError("occultation path topology is an airless product")
        if not isinstance(self.saturn_rings_included, bool):
            raise TypeError("saturn_rings_included must be bool")
        if self.saturn_rings_included:
            raise ValueError("Saturn's rings are excluded from solid-body occultation width")
        if self.lunar_limb_model != "SPHERICAL_MEAN_LIMB":
            raise ValueError(
                "first-class occultation topology admits only the spherical mean limb"
            )
        object.__setattr__(self, "topology", topology)
        object.__setattr__(self, "centers", centers)
        object.__setattr__(self, "boundaries", boundaries)
        object.__setattr__(self, "pole_crossings", pole_crossings)
        object.__setattr__(self, "observer_elevation_m", observer_elevation_m)


@dataclass(frozen=True, slots=True)
class GrazeCircumstances:
    """
    Local lunar graze circumstances for a fixed star at a single site and instant.

    This is the first explicit circumstance layer for Occult/GRAZPREP-style
    graze work. It exposes the local quantities needed for higher-authority
    graze semantics without changing the currently ratified path solver.
    """
    jd_ut: float
    observer_lat: float
    observer_lon: float
    observer_elev_m: float
    moon_altitude_deg: float
    sun_altitude_deg: float
    zenith_distance_deg: float
    tan_z: float
    position_angle_deg: float
    axis_angle_deg: float
    cusp_angle_deg: float
    cusp_pole: str
    margin_deg: float
    apparent_separation_deg: float


@dataclass(frozen=True, slots=True)
class GrazeTableRow:
    """
    Local graze-table row in the Occult/GRAZPREP circumstance style.
    """
    jd_ut: float
    longitude_deg: float
    latitude_deg: float
    observer_elev_m: float
    sun_altitude_deg: float
    moon_altitude_deg: float
    moon_azimuth_deg: float
    tan_z: float
    position_angle_deg: float
    axis_angle_deg: float
    cusp_angle_deg: float
    cusp_pole: str


@dataclass(frozen=True, slots=True)
class GrazeProductGeometry:
    """
    Explicit graze-product vessel.

    This keeps nominal graze-limit truth separate from any future
    profile-conditioned observing band.
    """
    product_kind: str
    jd_ut: float
    longitude_deg: float
    nominal_limit_latitude_deg: float
    practical_line_latitude_deg: float
    profile_band_south_latitude_deg: float | None
    profile_band_north_latitude_deg: float | None
    observer_elev_m: float
    has_profile_conditioned_band: bool


@dataclass(frozen=True, slots=True)
class GrazeProductTrack:
    """
    Longitude-indexed graze-product track.

    This is the multi-row graze-product surface parallel to the single-point
    ``GrazeProductGeometry`` vessel.
    """
    product_kind: str
    jd_ut: tuple[float, ...]
    longitude_deg: tuple[float, ...]
    nominal_limit_latitude_deg: tuple[float, ...]
    practical_line_latitude_deg: tuple[float, ...]
    profile_band_south_latitude_deg: tuple[float, ...] | None
    profile_band_north_latitude_deg: tuple[float, ...] | None
    observer_elev_m: float
    has_profile_conditioned_band: bool


# ---------------------------------------------------------------------------
# Physical angular radii (degrees) — used for occultation detection
# ---------------------------------------------------------------------------

# Moon's angular radius at mean distance (~384,400 km): ~0.2605°
_MOON_MEAN_RADIUS_DEG = 0.2605

# Approximate angular radii of planets at mean geocentric distance (degrees)
# Used as a rough threshold; true value computed from angular_diameter() if needed
_PLANET_MEAN_RADIUS_DEG: dict[str, float] = {
    Body.SUN:     0.2667,
    Body.MOON:    0.2605,
    Body.MERCURY: 0.00326,
    Body.VENUS:   0.00536,
    Body.MARS:    0.00261,
    Body.JUPITER: 0.02326,
    Body.SATURN:  0.00832,
    Body.URANUS:  0.00196,
    Body.NEPTUNE: 0.00113,
    Body.PLUTO:   0.000045,
}
_SOLAR_SYSTEM_BODY_LABELS_CASEFOLD = frozenset(
    {Body.EARTH.casefold(), *(body.casefold() for body in _PLANET_MEAN_RADIUS_DEG)}
)

# JPL Solar System Dynamics planetary physical parameters, equatorial radii
# in kilometres: https://ssd.jpl.nasa.gov/planets/phys_par.html .  These values
# govern the admitted first-class lunar-occultation topology targets.  The Sun
# belongs to eclipse geometry, not this topology surface.  The older mean
# angular thresholds above remain legacy event-detection policy.  Saturn's
# rings are not part of the solid-body radius.
_TOPOLOGY_JPL_EQUATORIAL_TARGET_RADII_KM: dict[str, float] = {
    Body.MERCURY: 2440.53,
    Body.VENUS: 6051.8,
    Body.MARS: 3396.19,
    Body.JUPITER: 71492.0,
    Body.SATURN: 60268.0,
    Body.URANUS: 25559.0,
    Body.NEPTUNE: 24764.0,
    Body.PLUTO: 1188.3,
}

# Legacy path APIs historically accept the Sun.  Keep that compatibility
# radius separate so it cannot accidentally re-admit the Sun to topology.
_LEGACY_SOLID_BODY_TARGET_RADII_KM: dict[str, float] = {
    Body.SUN: SUN_RADIUS_KM,
    **_TOPOLOGY_JPL_EQUATORIAL_TARGET_RADII_KM,
}

LunarLimbProfileProvider = Callable[[float, float, float, float, float, float], float]


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CloseApproach:
    """
    RITE: The Near Miss — the moment two wandering lights draw closest
          together in the sky, whether they merely brush or one swallows
          the other entirely.

    THEOREM: Immutable record of a minimum angular separation event between
             two solar system bodies, carrying both body names, the JD of
             closest approach, the separation in degrees, and a flag
             indicating whether the event constitutes a true occultation.

    RITE OF PURPOSE:
        CloseApproach is the primary result vessel of close_approaches().
        It gives callers a uniform type for any two-body proximity event,
        from a wide conjunction to a full occultation, without requiring
        them to inspect raw separation floats.  Without this vessel,
        callers would need to reconstruct event semantics from bare numbers.

    LAW OF OPERATION:
        Responsibilities:
            - Store body1, body2, jd_ut, separation_deg, and is_occultation.
            - Provide convenience properties for UTC datetime and
              CalendarDateTime representations.
            - Render a compact repr distinguishing occultations from close
              approaches and expressing separation in arcminutes.
        Non-responsibilities:
            - Does not compute separation; that is the Engine's role.
            - Does not validate that body1 and body2 are distinct.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.julian.datetime_from_jd, calendar_datetime_from_jd,
              format_jd_utc for time formatting.
        Structural invariants:
            - jd_ut is a finite float representing a valid Julian Day.
            - separation_deg >= 0.
            - is_occultation is True iff separation_deg < sum of angular radii.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.occultations.CloseApproach",
        "risk": "low",
        "api": {"frozen": ["body1", "body2", "jd_ut", "separation_deg", "is_occultation"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {
            "signals_emitted": [],
            "io": [],
            "mutation": "none"
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    body1:          str
    body2:          str
    jd_ut:          float
    separation_deg: float       # angular separation at closest point
    is_occultation: bool        # True if disks overlap

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_ut)

    def __repr__(self) -> str:
        kind = "OCCULTATION" if self.is_occultation else "Close Approach"
        return (
            f"{kind}: {self.body1} — {self.body2}  "
            f"sep={self.separation_deg * 60:.2f}′  "
            f"{format_jd_utc(self.jd_ut)}"
        )


@dataclass(slots=True)
class LunarOccultation:
    """
    RITE: The Moon's Veil — the interval during which the Moon's disk
          passes before a planet or fixed star, hiding it from earthly sight.

    THEOREM: Immutable record of a single lunar occultation event, carrying
             the target name, ingress and egress JDs, the JD of closest
             approach, the minimum angular separation, and a flag indicating
             whether the occultation is total or grazing.

    RITE OF PURPOSE:
        LunarOccultation is the result vessel of lunar_occultation() and
        lunar_star_occultation().  It encapsulates the full temporal extent
        of an occultation — ingress, mid-point, and egress — so that callers
        can compute duration, plan observations, or filter by totality without
        re-running the search.  Without this vessel, the three contact times
        would be returned as an unstructured tuple.

    LAW OF OPERATION:
        Responsibilities:
            - Store target name, jd_ingress, jd_egress, jd_mid,
              min_separation, and is_total.
            - Provide convenience properties for ingress/egress UTC datetime
              and CalendarDateTime, and duration in minutes.
            - Render a compact repr showing totality, ingress, egress, and
              minimum separation in arcminutes.
        Non-responsibilities:
            - Does not compute contact times; that is the Engine's role.
            - Does not validate that jd_ingress < jd_mid < jd_egress.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.julian.datetime_from_jd, calendar_datetime_from_jd,
              format_jd_utc for time formatting.
        Structural invariants:
            - jd_ingress <= jd_mid <= jd_egress.
            - min_separation >= 0.
            - is_total is True iff min_separation < Moon_radius − target_radius.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.occultations.LunarOccultation",
        "risk": "low",
        "api": {"frozen": ["target", "jd_ingress", "jd_egress", "jd_mid", "min_separation", "is_total"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {
            "signals_emitted": [],
            "io": [],
            "mutation": "none"
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    target:           str        # planet name or star name
    jd_ingress:       float      # Moon's limb first touches target
    jd_egress:        float      # Moon's limb last touches target
    jd_mid:           float      # closest approach
    min_separation:   float      # minimum angular distance (degrees)
    is_total:         bool       # target fully behind Moon disk

    @property
    def datetime_ingress(self) -> datetime:
        return datetime_from_jd(self.jd_ingress)

    @property
    def calendar_ingress(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_ingress)

    @property
    def datetime_egress(self) -> datetime:
        return datetime_from_jd(self.jd_egress)

    @property
    def calendar_egress(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_egress)

    @property
    def duration_minutes(self) -> float:
        return (self.jd_egress - self.jd_ingress) * 1440.0

    def __repr__(self) -> str:
        kind = "Total" if self.is_total else "Grazing"
        return (
            f"Lunar Occultation of {self.target} [{kind}]  "
            f"ingress={format_jd_utc(self.jd_ingress)}  "
            f"egress={format_jd_utc(self.jd_egress)}  "
            f"min_sep={self.min_separation * 60:.2f}′"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _angular_separation(
    lon1: float, lat1: float,
    lon2: float, lat2: float,
) -> float:
    """
    Great-circle angular separation between two ecliptic positions (degrees).
    Uses the haversine formula for numerical stability at small angles.
    """
    dlon = math.radians(lon2 - lon1)
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    a = (math.sin((math.radians(lat2) - math.radians(lat1)) / 2.0) ** 2
         + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlon / 2.0) ** 2)
    return math.degrees(2.0 * math.asin(math.sqrt(max(0.0, min(1.0, a)))))


def _sep_between(body1: str, body2: str, jd: float, reader: SpkReader) -> float:
    """Angular separation between two solar system bodies (degrees)."""
    p1 = planet_at(body1, jd, reader=reader)
    p2 = planet_at(body2, jd, reader=reader)
    return _angular_separation(p1.longitude, p1.latitude, p2.longitude, p2.latitude)


def _angular_separation_equatorial(
    ra1: float,
    dec1: float,
    ra2: float,
    dec2: float,
) -> float:
    """
    Great-circle separation between two equatorial positions (degrees).
    Uses the haversine formula for numerical stability at small angles.
    """
    ra1r = math.radians(ra1)
    dec1r = math.radians(dec1)
    ra2r = math.radians(ra2)
    dec2r = math.radians(dec2)

    dra = ra2r - ra1r
    ddec = dec2r - dec1r

    a = (math.sin(ddec / 2.0)**2
         + math.cos(dec1r) * math.cos(dec2r) * math.sin(dra / 2.0)**2)
    sep_rad = 2.0 * math.asin(math.sqrt(max(0.0, min(1.0, a))))
    return math.degrees(sep_rad)


def _sep_between_topocentric(
    body1: str,
    body2: str,
    jd: float,
    lat: float,
    lon: float,
    elev_m: float,
    reader: SpkReader,
) -> float:
    """Topocentric apparent angular separation between two solar-system bodies."""
    p1 = sky_position_at(body1, jd, lat, lon, elev_m, reader=reader)
    p2 = sky_position_at(body2, jd, lat, lon, elev_m, reader=reader)
    return _angular_separation_equatorial(
        p1.right_ascension, p1.declination,
        p2.right_ascension, p2.declination,
    )


def _bisect_minimum(
    f,
    a: float,
    b: float,
    tol: float = 1e-6,
) -> tuple[float, float]:
    """
    Find the minimum of f on [a, b] using golden-section search.
    Returns (x_min, f_min).
    """
    a = float(a)
    b = float(b)
    tol = float(tol)
    if not math.isfinite(a) or not math.isfinite(b):
        raise ValueError("minimum-search bounds must be finite")
    if b < a:
        raise ValueError("minimum-search bounds must be ordered")
    if not math.isfinite(tol) or tol <= 0.0:
        raise ValueError("minimum-search tolerance must be finite and positive")
    if a == b:
        return a, f(a)

    gr = (math.sqrt(5.0) + 1.0) / 2.0
    c = b - (b - a) / gr
    d = a + (b - a) / gr
    best_x = c
    c_value = f(c)
    best_value = c_value
    d_value = f(d)
    if d_value < best_value:
        best_x = d
        best_value = d_value

    # At large Julian Days, a requested tolerance can be smaller than one
    # binary64 ULP.  Stop when the interval no longer advances, and retain a
    # deterministic cap as a final guard against malformed objectives.
    for _ in range(256):
        if b - a <= tol:
            break
        old_a = a
        old_b = b
        if c_value < d_value:
            b = d
            d = c
            d_value = c_value
            c = b - (b - a) / gr
            c_value = f(c)
        else:
            a = c
            c = d
            c_value = d_value
            d = a + (b - a) / gr
            d_value = f(d)
        if c_value < best_value:
            best_x = c
            best_value = c_value
        if d_value < best_value:
            best_x = d
            best_value = d_value
        if (a == old_a and b == old_b) or c == d or c <= a or d >= b:
            break
    x = (a + b) / 2.0
    x_value = f(x)
    if x_value < best_value:
        return x, x_value
    return best_x, best_value


_GEO_SEARCH_STEPS_DEG = (
    10.0,
    5.0,
    2.0,
    1.0,
    0.5,
    0.25,
    0.1,
    0.05,
    0.02,
    0.01,
    0.005,
    0.002,
    0.001,
    0.0005,
    0.0002,
    0.0001,
)
_GEO_GREATEST_TANGENT_SEARCH_STEPS_DEG = (
    *_GEO_SEARCH_STEPS_DEG,
    0.00005,
    0.00002,
    0.00001,
    0.000005,
    0.000002,
    0.000001,
    0.0000005,
    0.0000002,
    0.0000001,
)
_GEO_COARSE_LAT_STEP_DEG = 20.0
_GEO_COARSE_LON_STEP_DEG = 20.0
_GEO_SEARCH_EARLY_EXIT_SEPARATION_DEG = 1.0e-4
_GEO_SEARCH_MAX_OBJECTIVE_EVALS = 4096
_GEO_SEARCH_MAX_PASSES_PER_STEP = 512
_GEO_SEARCH_TIE_TOLERANCE_DEG = 1.0e-12
_OCCULTATION_TEMPORAL_SCAN_STEP_DAYS = 1.0 / 48.0
_OCCULTATION_TEMPORAL_SCAN_LIMIT = 48
_OCCULTATION_COMPONENT_MAXIMUM_STEP_DAYS = 1.0 / 48.0
_OCCULTATION_COMPONENT_MAXIMUM_MAX_CELLS = 128
_OCCULTATION_COMPONENT_PEAK_TIME_TOLERANCE_DAYS = 1.0e-8
_OCCULTATION_TRACK_TANGENT_STEP_DAYS = 1.0 / 1440.0
_OCCULTATION_POLE_PEAK_TIME_TOLERANCE_DAYS = 1.0e-8
_OCCULTATION_POLE_CLEARANCE_MAX_STEP_DAYS = 1.0 / 48.0
_OCCULTATION_POLE_SIDE_DEGENERACY_TOLERANCE = 1.0e-12
_OCCULTATION_TOPOLOGY_MAX_STEP_DAYS = 0.25
_OCCULTATION_TOPOLOGY_MAX_SPAN_DAYS = 400.0
_OCCULTATION_TOPOLOGY_MAX_CANDIDATE_CELLS = 4096
_WGS84_FLATTENING = 1.0 / 298.257223563
_OCCULTATION_TOPOLOGY_MIN_OBSERVER_ELEV_M = (
    -EARTH_RADIUS_KM * (1.0 - _WGS84_FLATTENING) * 1000.0
)
_OCCULTATION_CANDIDATE_DEDUP_MIN_TOLERANCE_DAYS = 4.0e-8
_OCCULTATION_CANDIDATE_DEDUP_ULPS = 8.0
_OCCULTATION_BOUNDARY_SCAN_STEP_KM = 25.0
_OCCULTATION_BOUNDARY_DISTANCE_TOLERANCE_KM = 1.0e-6
_OCCULTATION_CLEARANCE_TOLERANCE_DEG = 1.0e-10
_OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG = 1.0e-7
_OCCULTATION_BRANCH_SWAP_TOLERANCE_KM = 1.0e-6
_OCCULTATION_PUBLIC_DISTANCE_TOLERANCE_KM = 1.0e-5


class _OccultationPathSolveError(ArithmeticError):
    """The requested occultation path could not be solved honestly."""


class _OccultationPathNotPresentError(ValueError):
    """No positive-clearance occultation exists at the supplied greatest epoch."""


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
    fb = f_right
    for _ in range(iterations):
        mid = (a + b) / 2.0
        if mid == a or mid == b:
            return a if abs(fa) <= abs(fb) else b
        fm = func(mid)
        if fm == 0.0:
            return mid
        if fa * fm <= 0.0:
            b = mid
            fb = fm
        else:
            a = mid
            fa = fm
    return (a + b) / 2.0


def _star_geometric_icrf_direction(
    star_lon: float,
    star_lat: float,
    jd_tt: float,
) -> tuple[float, float, float]:
    """Recover the geometric ICRF ray behind Moira's true-ecliptic star surface."""

    obliquity = true_obliquity(jd_tt)
    true_ra_star, true_dec_star = ecliptic_to_equatorial(star_lon, star_lat, obliquity)

    # Recover the geometric ICRF direction from the validated geometric
    # true-ecliptic star surface, then apply the same apparent-place stages
    # Moira already uses for planets: deflection -> aberration -> frame bias
    # -> precession -> nutation.
    ra_r = math.radians(true_ra_star)
    dec_r = math.radians(true_dec_star)
    true_equ = (
        math.cos(dec_r) * math.cos(ra_r),
        math.cos(dec_r) * math.sin(ra_r),
        math.sin(dec_r),
    )

    prec = precession_matrix_equatorial(jd_tt)
    nut = nutation_matrix_equatorial(jd_tt)

    def _transpose(mat: tuple[tuple[float, float, float], ...]) -> tuple[tuple[float, float, float], ...]:
        return (
            (mat[0][0], mat[1][0], mat[2][0]),
            (mat[0][1], mat[1][1], mat[2][1]),
            (mat[0][2], mat[1][2], mat[2][2]),
        )

    return mat_vec_mul(_transpose(prec), mat_vec_mul(_transpose(nut), true_equ))


def _star_physical_equatorial(
    star_lon: float,
    star_lat: float,
    jd: float,
    *,
    reader: SpkReader,
) -> tuple[float, float]:
    """Return the unrefracted, unaberrated physical stellar ray of date.

    Solar-system gravitational deflection is retained because it changes the
    received photon path. Annual and diurnal aberration are coordinate effects
    of observer motion and do not belong in the physical Moon-surface
    intersection geometry.
    """

    jd_tt = _ut1_to_ephemeris_tt(jd, reader)
    xyz_icrf = _star_geometric_icrf_direction(star_lon, star_lat, jd_tt)
    deflectors = [(_geocentric(Body.SUN, jd_tt, reader), SCHWARZSCHILD_RADII["Sun"])]
    deflectors.append((_geocentric(Body.JUPITER, jd_tt, reader), SCHWARZSCHILD_RADII["Jupiter"]))
    deflectors.append((_geocentric(Body.SATURN, jd_tt, reader), SCHWARZSCHILD_RADII["Saturn"]))
    xyz_physical = apply_deflection(xyz_icrf, deflectors)
    xyz_physical = apply_frame_bias(xyz_physical)
    xyz_physical = mat_vec_mul(precession_matrix_equatorial(jd_tt), xyz_physical)
    xyz_physical = mat_vec_mul(nutation_matrix_equatorial(jd_tt), xyz_physical)
    ra_star, dec_star, _ = icrf_to_equatorial(xyz_physical)
    return ra_star, dec_star


def _star_topocentric_equatorial(
    star_lon: float,
    star_lat: float,
    jd: float,
    lat: float,
    lon: float,
    observer_elev_m: float = 0.0,
    *,
    reader: SpkReader,
) -> tuple[float, float, float]:
    jd_tt = _ut1_to_ephemeris_tt(jd, reader)
    obliquity = true_obliquity(jd_tt)
    dpsi, _ = nutation(jd_tt)
    xyz_icrf = _star_geometric_icrf_direction(star_lon, star_lat, jd_tt)
    _, earth_vel = _earth_barycentric_state(jd_tt, reader)
    deflectors = [(_geocentric(Body.SUN, jd_tt, reader), SCHWARZSCHILD_RADII["Sun"])]
    deflectors.append((_geocentric(Body.JUPITER, jd_tt, reader), SCHWARZSCHILD_RADII["Jupiter"]))
    deflectors.append((_geocentric(Body.SATURN, jd_tt, reader), SCHWARZSCHILD_RADII["Saturn"]))

    xyz_apparent = apply_deflection(xyz_icrf, deflectors)
    xyz_apparent = apply_aberration(xyz_apparent, earth_vel)
    xyz_apparent = apply_frame_bias(xyz_apparent)
    xyz_apparent = mat_vec_mul(precession_matrix_equatorial(jd_tt), xyz_apparent)
    xyz_apparent = mat_vec_mul(nutation_matrix_equatorial(jd_tt), xyz_apparent)

    ra_star, dec_star, _ = icrf_to_equatorial(xyz_apparent)
    lst = local_sidereal_time(jd, lon, dpsi, obliquity)
    _, altitude = equatorial_to_horizontal(ra_star, dec_star, lst, lat)
    return ra_star, dec_star, altitude


def _refracted_topocentric_equatorial(
    ra_deg: float,
    dec_deg: float,
    jd_ut: float,
    lat_deg: float,
    lon_deg: float,
    *,
    reader: SpkReader,
) -> tuple[float, float, float]:
    """
    Convert a geometric/apparent topocentric equatorial place into the
    refraction-adjusted local apparent place used by graze-limit products.
    """
    jd_tt = _ut1_to_ephemeris_tt(jd_ut, reader)
    obliquity = true_obliquity(jd_tt)
    dpsi, _ = nutation(jd_tt)
    lst = local_sidereal_time(jd_ut, lon_deg, dpsi, obliquity)
    az_deg, alt_deg = equatorial_to_horizontal(ra_deg, dec_deg, lst, lat_deg)
    refracted_alt_deg = apply_refraction(alt_deg)
    refracted_ra_deg, refracted_dec_deg = horizontal_to_equatorial(
        az_deg,
        refracted_alt_deg,
        lst,
        lat_deg,
    )
    return refracted_ra_deg, refracted_dec_deg, refracted_alt_deg


def _position_angle_equatorial(
    ra_from_deg: float,
    dec_from_deg: float,
    ra_to_deg: float,
    dec_to_deg: float,
) -> float:
    ra_from = math.radians(ra_from_deg)
    dec_from = math.radians(dec_from_deg)
    ra_to = math.radians(ra_to_deg)
    dec_to = math.radians(dec_to_deg)
    delta_ra = ra_to - ra_from
    y = math.sin(delta_ra)
    x = (
        math.cos(dec_from) * math.tan(dec_to)
        - math.sin(dec_from) * math.cos(delta_ra)
    )
    return math.degrees(math.atan2(y, x)) % 360.0


def _angle_diff_deg(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0) - 180.0


def _reduce_angle_deg(angle_deg: float) -> float:
    return angle_deg % 360.0


def _moon_axis_position_angle_deg(
    jd_tt: float,
    reader: SpkReader | None = None,
) -> float:
    """
    Position angle of the Moon's rotation axis.

    Implemented from the Meeus / Eckhardt formulation reflected in the
    PyMeeus `moon_position_angle_axis()` method.
    """
    moon = planet_at(Body.MOON, jd_tt, jd_tt=jd_tt, reader=reader)
    eps = true_obliquity(jd_tt)
    delta_psi, _ = nutation(jd_tt)
    moon_ra_deg, moon_dec_deg = ecliptic_to_equatorial(moon.longitude, moon.latitude, eps)

    T = (jd_tt - 2451545.0) / 36525.0
    D = _reduce_angle_deg(
        297.8501921
        + (445267.1114034 + (-0.0018819 + (1.0 / 545868.0 - T / 113065000.0) * T) * T) * T
    )
    M = _reduce_angle_deg(
        357.5291092
        + (35999.0502909 + (-0.0001536 + T / 24490000.0) * T) * T
    )
    Mprime = _reduce_angle_deg(
        134.9633964
        + (477198.8675055 + (0.0087414 + (1.0 / 69699.9 + T / 14712000.0) * T) * T) * T
    )
    F = _reduce_angle_deg(
        93.2720950
        + (483202.0175233 + (-0.0036539 + (-1.0 / 3526000.0 + T / 863310000.0) * T) * T) * T
    )
    Omega = _reduce_angle_deg(
        125.0445479
        + (-1934.1362891 + (0.0020754 + (1.0 / 476441.0 - T / 60616000.0) * T) * T) * T
    )
    E = 1.0 + (-0.002516 - 0.0000074 * T) * T
    k1 = _reduce_angle_deg(119.75 + 131.849 * T)
    k2 = _reduce_angle_deg(72.56 + 20.186 * T)

    Dr = math.radians(D)
    Mr = math.radians(M)
    Mpr = math.radians(Mprime)
    Fr = math.radians(F)
    Omegar = math.radians(Omega)
    k1r = math.radians(k1)
    k2r = math.radians(k2)
    ir = math.radians(1.54242)
    sinI = math.sin(ir)

    w_deg = _reduce_angle_deg(moon.longitude - delta_psi - Omega)
    wr = math.radians(w_deg)
    betar = math.radians(moon.latitude)
    sinW = math.sin(wr)
    cosW = math.cos(wr)
    sinB = math.sin(betar)
    cosB = math.cos(betar)

    Ar = math.atan2(
        sinW * cosB * math.cos(ir) - sinB * sinI,
        cosW * cosB,
    )
    bprimer = math.asin(-sinW * cosB * sinI - sinB * math.cos(ir))

    rho = math.radians(
        -0.02752 * math.cos(Mpr) - 0.02245 * math.sin(Fr)
        + 0.00684 * math.cos(Mpr - 2.0 * Fr) - 0.00293 * math.cos(2.0 * Fr)
        - 0.00085 * math.cos(2.0 * (Fr - Dr))
        - 0.00054 * math.cos(Mpr - 2.0 * Dr) - 0.0002 * math.sin(Mpr + Fr)
        - 0.0002 * math.cos(Mpr + 2.0 * Fr) - 0.0002 * math.cos(Mpr - Fr)
        + 0.00014 * math.cos(Mpr + 2.0 * (Fr - Dr))
    )
    sigma = math.radians(
        -0.02816 * math.sin(Mpr) + 0.02244 * math.cos(Fr)
        - 0.00682 * math.sin(Mpr - 2.0 * Fr) - 0.00279 * math.sin(2.0 * Fr)
        - 0.00083 * math.sin(2.0 * (Fr - Dr))
        + 0.00069 * math.sin(Mpr - 2.0 * Dr)
        + 0.0004 * math.cos(Mpr + Fr) - 0.00025 * math.sin(2.0 * Mpr)
        - 0.00023 * math.sin(Mpr + 2.0 * Fr)
        + 0.0002 * math.cos(Mpr - Fr) + 0.00019 * math.sin(Mpr - Fr)
        + 0.00013 * math.sin(Mpr + 2.0 * (Fr - Dr))
        - 0.0001 * math.cos(Mpr - 3.0 * Fr)
    )
    tau = math.radians(
        0.0252 * E * math.sin(Mr) + 0.00473 * math.sin(2.0 * (Mpr - Fr))
        - 0.00467 * math.sin(Mpr) + 0.00396 * math.sin(k1r)
        + 0.00276 * math.sin(2.0 * (Mpr - Dr)) + 0.00196 * math.sin(Omegar)
        - 0.00183 * math.cos(Mpr - Fr)
        + 0.00115 * math.sin(Mpr - 2.0 * Dr)
        - 0.00096 * math.sin(Mpr - Dr) + 0.00046 * math.sin(2.0 * (Fr - Dr))
        - 0.00039 * math.sin(Mpr - Fr) - 0.00032 * math.sin(Mpr - Mr - Dr)
        + 0.00027 * math.sin(2.0 * (Mpr - Dr) - Mr) + 0.00023 * math.sin(k2r)
        - 0.00014 * math.sin(2.0 * Dr) + 0.00014 * math.cos(2.0 * (Mpr - Fr))
        - 0.00012 * math.sin(Mpr - 2.0 * Fr)
        - 0.00012 * math.sin(2.0 * Mpr)
        + 0.00011 * math.sin(2.0 * (Mpr - Mr - Dr))
    )

    lpp = -tau + (rho * math.cos(Ar) + sigma * math.sin(Ar)) * math.tan(bprimer)
    bpp = sigma * math.cos(Ar) - rho * math.sin(Ar)
    btot = bprimer + bpp

    v = math.radians(_reduce_angle_deg(Omega + delta_psi + math.degrees(sigma / sinI)))
    x = math.sin(ir + rho) * math.sin(v)
    y = math.sin(ir + rho) * math.cos(v) * math.cos(math.radians(eps)) - math.cos(ir + rho) * math.sin(math.radians(eps))
    w = math.atan2(x, y)
    p = math.asin((math.hypot(x, y) * math.cos(math.radians(moon_ra_deg) - w)) / math.cos(btot))
    return _reduce_angle_deg(math.degrees(p))


def _graze_axis_angle_deg(
    position_angle_deg: float,
    moon_axis_position_angle_deg: float,
) -> float:
    return _reduce_angle_deg(position_angle_deg - moon_axis_position_angle_deg)


def _graze_cusp_angle(
    axis_angle_deg: float,
    bright_limb_position_angle_deg: float,
    moon_axis_position_angle_deg: float,
) -> tuple[float, str]:
    bright_axis_angle = _graze_axis_angle_deg(bright_limb_position_angle_deg, moon_axis_position_angle_deg)
    delta = _angle_diff_deg(axis_angle_deg, bright_axis_angle)
    if abs(delta) <= 90.0:
        magnitude = 90.0 - abs(delta)
        sign = -1.0
    else:
        magnitude = abs(delta) - 90.0
        sign = 1.0

    north_cusp = _reduce_angle_deg(bright_axis_angle - 90.0)
    south_cusp = _reduce_angle_deg(bright_axis_angle + 90.0)
    north_diff = abs(_angle_diff_deg(axis_angle_deg, north_cusp))
    south_diff = abs(_angle_diff_deg(axis_angle_deg, south_cusp))
    cusp_pole = "N" if north_diff <= south_diff else "S"
    return sign * magnitude, cusp_pole


def _limb_profile_adjustment_deg(
    provider: LunarLimbProfileProvider | None,
    jd: float,
    lat: float,
    lon: float,
    observer_elev_m: float,
    position_angle_deg: float,
    moon_distance_km: float,
) -> float:
    if provider is None:
        return 0.0
    return float(provider(jd, lat, lon, observer_elev_m, position_angle_deg, moon_distance_km))


_GRAZE_LATITUDE_SCAN_STEP_DEG = 0.5
_GRAZE_DIRECTED_SCAN_STEP_DEG = 1.0


def _solve_nearest_latitude_root(
    margin: Callable[[float], float],
    guess_latitude_deg: float,
    *,
    max_span_deg: float,
    scan_step_deg: float,
    iterations: int,
) -> float:
    """Return the nearest sign-changing latitude root on the legal Earth domain."""

    if not math.isfinite(guess_latitude_deg) or not -90.0 <= guess_latitude_deg <= 90.0:
        raise ValueError("guess_latitude_deg must be finite and between -90 and 90 degrees")
    if not math.isfinite(max_span_deg) or max_span_deg <= 0.0:
        raise ValueError("max_span_deg must be finite and positive")
    if not math.isfinite(scan_step_deg) or scan_step_deg <= 0.0:
        raise ValueError("scan_step_deg must be finite and positive")
    if iterations <= 0:
        raise ValueError("iterations must be positive")

    cache: dict[float, float] = {}

    def evaluate(latitude: float) -> float:
        if not -90.0 <= latitude <= 90.0:
            raise ValueError("graze latitude search left the legal Earth domain")
        if latitude not in cache:
            value = margin(latitude)
            if not math.isfinite(value):
                raise ValueError("graze latitude margin returned a non-finite value")
            cache[latitude] = value
        return cache[latitude]

    center_value = evaluate(guess_latitude_deg)
    if center_value == 0.0:
        return guess_latitude_deg

    brackets: list[tuple[float, float]] = []
    previous = {
        -1.0: (guess_latitude_deg, center_value),
        1.0: (guess_latitude_deg, center_value),
    }
    active_directions = {-1.0, 1.0}
    travelled = 0.0
    while travelled < max_span_deg and active_directions and not brackets:
        travelled = min(max_span_deg, travelled + scan_step_deg)
        for direction in (-1.0, 1.0):
            if direction not in active_directions:
                continue
            previous_latitude, previous_value = previous[direction]
            candidate = max(
                -90.0,
                min(90.0, guess_latitude_deg + direction * travelled),
            )
            if candidate == previous_latitude:
                active_directions.remove(direction)
                continue
            candidate_value = evaluate(candidate)
            if candidate_value == 0.0:
                brackets.append((candidate, candidate))
            elif previous_value * candidate_value < 0.0:
                brackets.append(
                    (previous_latitude, candidate)
                    if previous_latitude < candidate
                    else (candidate, previous_latitude)
                )
            previous[direction] = (candidate, candidate_value)
            if abs(candidate) == 90.0:
                active_directions.remove(direction)

    if not brackets:
        raise ValueError("Could not bracket lunar star graze latitude")

    roots: list[float] = []
    for left, right in brackets:
        if left == right:
            roots.append(left)
            continue
        roots.append(_bisection_root(evaluate, left, right, iterations=iterations))
    return min(roots, key=lambda root: (abs(root - guess_latitude_deg), root))


def _solve_directed_latitude_root(
    margin: Callable[[float], float],
    interior_latitude_deg: float,
    direction: int,
    *,
    scan_step_deg: float = _GRAZE_DIRECTED_SCAN_STEP_DEG,
    iterations: int = 50,
) -> float:
    """Solve one north/south occultation-band boundary from a known interior."""

    if not math.isfinite(interior_latitude_deg) or not -90.0 <= interior_latitude_deg <= 90.0:
        raise ValueError("interior_latitude_deg must be finite and between -90 and 90 degrees")
    if direction not in {-1, 1}:
        raise ValueError("direction must be -1 (south) or 1 (north)")
    if not math.isfinite(scan_step_deg) or scan_step_deg <= 0.0:
        raise ValueError("scan_step_deg must be finite and positive")

    def evaluate(latitude: float) -> float:
        if not -90.0 <= latitude <= 90.0:
            raise ValueError("graze latitude search left the legal Earth domain")
        value = margin(latitude)
        if not math.isfinite(value):
            raise ValueError("graze latitude margin returned a non-finite value")
        return value

    current = interior_latitude_deg
    current_value = evaluate(current)
    if current_value == 0.0:
        return current
    if current_value < 0.0:
        raise ValueError("directed graze boundary requires a positive-margin interior latitude")

    pole = 90.0 if direction > 0 else -90.0
    while current != pole:
        candidate = (
            min(pole, current + scan_step_deg)
            if direction > 0
            else max(pole, current - scan_step_deg)
        )
        candidate_value = evaluate(candidate)
        if candidate_value == 0.0:
            return candidate
        if candidate_value < 0.0:
            left, right = sorted((current, candidate))
            return _bisection_root(evaluate, left, right, iterations=iterations)
        current = candidate
        current_value = candidate_value

    raise ValueError("Could not bracket lunar star graze latitude before the pole")


def _solve_star_graze_latitude(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    longitude_deg: float,
    guess_latitude_deg: float,
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> float:
    reader = get_reader() if reader is None else reader

    def margin(latitude: float, provider: LunarLimbProfileProvider | None) -> float:
        return _star_topocentric_target_geometry(
            star_lon,
            star_lat,
            jd_ut,
            latitude,
            longitude_deg,
            reader,
            observer_elev_m,
            provider,
            refraction_adjusted,
        )[1]

    def solve_with_provider(
        provider: LunarLimbProfileProvider | None,
        center_guess: float,
        *,
        half_width: float,
        expand_step: float,
        max_expand: int,
        iterations: int,
    ) -> float:
        return _solve_nearest_latitude_root(
            lambda latitude: margin(latitude, provider),
            center_guess,
            max_span_deg=half_width + max_expand * expand_step,
            scan_step_deg=min(
                _GRAZE_LATITUDE_SCAN_STEP_DEG,
                half_width,
                expand_step,
            ),
            iterations=iterations,
        )

    smooth_root = solve_with_provider(
        None,
        guess_latitude_deg,
        half_width=3.0,
        expand_step=2.0,
        max_expand=20,
        iterations=50,
    )
    if limb_profile_provider is None:
        return smooth_root

    deriv_step = 1.0 / 120.0
    deriv_left = max(-90.0, smooth_root - deriv_step)
    deriv_right = min(90.0, smooth_root + deriv_step)
    if deriv_right == deriv_left:
        raise ValueError("Could not refine lunar star graze latitude at a degenerate pole")
    deriv = (
        margin(deriv_right, None) - margin(deriv_left, None)
    ) / (deriv_right - deriv_left)
    if abs(deriv) < 1e-9:
        return solve_with_provider(
            limb_profile_provider,
            smooth_root,
            half_width=0.25,
            expand_step=0.25,
            max_expand=8,
            iterations=20,
        )

    refined_root = smooth_root - margin(smooth_root, limb_profile_provider) / deriv
    if not -90.0 <= refined_root <= 90.0:
        return solve_with_provider(
            limb_profile_provider,
            smooth_root,
            half_width=0.25,
            expand_step=0.25,
            max_expand=8,
            iterations=20,
        )
    refined_margin = margin(refined_root, limb_profile_provider)
    if abs(refined_margin) > 1e-4:
        corrected_root = refined_root - refined_margin / deriv
        if not -90.0 <= corrected_root <= 90.0:
            return solve_with_provider(
                limb_profile_provider,
                smooth_root,
                half_width=0.25,
                expand_step=0.25,
                max_expand=8,
                iterations=20,
            )
        refined_root = corrected_root
        if abs(margin(refined_root, limb_profile_provider)) > 1e-4:
            return solve_with_provider(
                limb_profile_provider,
                smooth_root,
                half_width=0.25,
                expand_step=0.25,
                max_expand=8,
                iterations=20,
            )
    return refined_root


def _solve_occultation_greatest_location(
    objective: Callable[[float, float], float],
    *,
    preferred_location: tuple[float, float] | None = None,
    early_exit_score: float | None = _GEO_SEARCH_EARLY_EXIT_SEPARATION_DEG,
    complete_surface: bool = True,
    refinement_steps_deg: tuple[float, ...] = _GEO_SEARCH_STEPS_DEG,
) -> tuple[float, float, float]:
    """Minimize a surface objective without treating a pole as a boundary.

    Lower objective values govern.  A continuation preference only resolves
    numerical ties; it can never displace a materially better surface point.
    """

    cache: dict[tuple[float, float], float] = {}
    objective_evals = 0

    def score(latitude: float, longitude: float) -> float:
        nonlocal objective_evals
        canonical_latitude, canonical_longitude = _offset_geographic_km(
            latitude,
            longitude,
            0.0,
            0.0,
        )
        key = (round(canonical_latitude, 8), round(canonical_longitude, 8))
        if key not in cache:
            if objective_evals >= _GEO_SEARCH_MAX_OBJECTIVE_EVALS:
                raise _OccultationPathSolveError(
                    "occultation greatest-location evaluation limit exhausted"
                )
            objective_evals += 1
            value = float(objective(canonical_latitude, canonical_longitude))
            if not math.isfinite(value):
                raise _OccultationPathSolveError(
                    "occultation greatest-location objective returned a non-finite value"
                )
            cache[key] = value
        return cache[key]

    preferred = None
    if preferred_location is not None:
        preferred = _offset_geographic_km(
            float(preferred_location[0]),
            float(preferred_location[1]),
            0.0,
            0.0,
        )

    best_lat = 0.0
    best_lon = 0.0
    best_score = float("inf")

    def surface_distance_to_preference(latitude: float, longitude: float) -> float:
        if preferred is None:
            return 0.0
        return _surface_distance_km(
            latitude,
            longitude,
            preferred[0],
            preferred[1],
        )

    def admit(latitude: float, longitude: float) -> bool:
        nonlocal best_lat, best_lon, best_score
        canonical_latitude, canonical_longitude = _offset_geographic_km(
            latitude,
            longitude,
            0.0,
            0.0,
        )
        value = score(canonical_latitude, canonical_longitude)
        better = value < best_score - _GEO_SEARCH_TIE_TOLERANCE_DEG
        tied = abs(value - best_score) <= _GEO_SEARCH_TIE_TOLERANCE_DEG
        if tied:
            candidate_key = (
                surface_distance_to_preference(canonical_latitude, canonical_longitude),
                canonical_latitude,
                canonical_longitude,
            )
            best_key = (
                surface_distance_to_preference(best_lat, best_lon),
                best_lat,
                best_lon,
            )
            better = candidate_key < best_key
        if better:
            best_lat = canonical_latitude
            best_lon = canonical_longitude
            best_score = value
        return early_exit_score is not None and best_score <= early_exit_score

    def refine_from_current() -> bool:
        nonlocal best_lat, best_lon, best_score
        for step in refinement_steps_deg:
            step_km = step * _EARTH_KM_PER_DEG_LAT
            improved = True
            passes = 0
            while improved and passes < _GEO_SEARCH_MAX_PASSES_PER_STEP:
                passes += 1
                improved = False
                origin_lat = best_lat
                origin_lon = best_lon
                origin_score = best_score
                for north_direction in (-1.0, 0.0, 1.0):
                    for east_direction in (-1.0, 0.0, 1.0):
                        if north_direction == 0.0 and east_direction == 0.0:
                            continue
                        cand_lat, cand_lon = _offset_geographic_km(
                            origin_lat,
                            origin_lon,
                            north_direction * step_km,
                            east_direction * step_km,
                        )
                        if admit(cand_lat, cand_lon):
                            return True
                improved = best_score < origin_score - _GEO_SEARCH_TIE_TOLERANCE_DEG
        return False

    if preferred is not None:
        admit(*preferred)
        if refine_from_current():
            return best_lat, best_lon, best_score
        if not complete_surface:
            return best_lat, best_lon, best_score

    # Longitude is undefined at an exact pole.  Each pole is one canonical
    # surface point and is evaluated before the regular coordinate grid.
    for latitude, longitude in ((-90.0, 0.0), (90.0, 0.0)):
        if admit(latitude, longitude):
            return best_lat, best_lon, best_score

    lat = -80.0
    while lat <= 80.0 + 1e-9:
        lon = -180.0
        while lon < 180.0 - 1e-9:
            if admit(lat, lon):
                return best_lat, best_lon, best_score
            lon += _GEO_COARSE_LON_STEP_DEG
        lat += _GEO_COARSE_LAT_STEP_DEG

    refine_from_current()
    return best_lat, best_lon, best_score


def _planet_topocentric_target_geometry(
    target: str,
    jd: float,
    lat: float,
    lon: float,
    reader: SpkReader,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
) -> tuple[float, float, float, float]:
    moon = sky_position_at(Body.MOON, jd, lat, lon, observer_elev_m, reader=reader)
    target_pos = sky_position_at(target, jd, lat, lon, observer_elev_m, reader=reader)
    try:
        target_physical_radius_km = _LEGACY_SOLID_BODY_TARGET_RADII_KM[target]
    except KeyError as exc:
        raise ValueError(
            f"No JPL equatorial solid-body radius is admitted for {target!r}"
        ) from exc
    separation = _angular_separation_equatorial(
        moon.right_ascension,
        moon.declination,
        target_pos.right_ascension,
        target_pos.declination,
    )
    position_angle = _position_angle_equatorial(
        moon.right_ascension,
        moon.declination,
        target_pos.right_ascension,
        target_pos.declination,
    )
    moon_radius = _apparent_radius(MOON_RADIUS_KM, moon.distance) + _limb_profile_adjustment_deg(
        limb_profile_provider,
        jd,
        lat,
        lon,
        observer_elev_m,
        position_angle,
        moon.distance,
    )
    target_radius = _apparent_radius(
        target_physical_radius_km,
        target_pos.distance,
    )
    margin = moon_radius + target_radius - separation
    return separation, margin, moon.azimuth, moon.altitude


def _star_topocentric_target_geometry(
    star_lon: float,
    star_lat: float,
    jd: float,
    lat: float,
    lon: float,
    reader: SpkReader | None,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> tuple[float, float, float, float]:
    reader = get_reader() if reader is None else reader
    moon = sky_position_at(Body.MOON, jd, lat, lon, observer_elev_m, reader=reader)
    ra_star, dec_star, _ = _star_topocentric_equatorial(
        star_lon,
        star_lat,
        jd,
        lat,
        lon,
        observer_elev_m,
        reader=reader,
    )
    moon_ra = moon.right_ascension
    moon_dec = moon.declination
    if refraction_adjusted:
        moon_ra, moon_dec, _ = _refracted_topocentric_equatorial(
            moon.right_ascension,
            moon.declination,
            jd,
            lat,
            lon,
            reader=reader,
        )
        ra_star, dec_star, star_altitude = _refracted_topocentric_equatorial(
            ra_star,
            dec_star,
            jd,
            lat,
            lon,
            reader=reader,
        )
    else:
        jd_tt = _ut1_to_ephemeris_tt(jd, reader)
        obliquity = true_obliquity(jd_tt)
        dpsi, _ = nutation(jd_tt)
        lst = local_sidereal_time(jd, lon, dpsi, obliquity)
        _, star_altitude = equatorial_to_horizontal(ra_star, dec_star, lst, lat)
    separation = _angular_separation_equatorial(
        moon_ra,
        moon_dec,
        ra_star,
        dec_star,
    )
    position_angle = _position_angle_equatorial(
        moon_ra,
        moon_dec,
        ra_star,
        dec_star,
    )
    moon_radius = _apparent_radius(MOON_RADIUS_KM, moon.distance) + _limb_profile_adjustment_deg(
        limb_profile_provider,
        jd,
        lat,
        lon,
        observer_elev_m,
        position_angle,
        moon.distance,
    )
    margin = moon_radius - separation
    return separation, margin, moon.azimuth, star_altitude


def lunar_star_graze_circumstances(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    observer_lat: float,
    observer_lon: float,
    reader: SpkReader | None = None,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
) -> GrazeCircumstances:
    """
    Compute local lunar graze circumstances for a fixed star.

    This exposes the explicit local quantities used by graze-prediction
    semantics, while keeping the existing path solver unchanged.
    """
    reader = get_reader() if reader is None else reader
    moon = sky_position_at(
        Body.MOON,
        jd_ut,
        observer_lat,
        observer_lon,
        observer_elev_m,
        reader=reader,
    )
    moon_geometric = sky_position_at(
        Body.MOON,
        jd_ut,
        observer_lat,
        observer_lon,
        observer_elev_m,
        reader=reader,
        refraction=False,
    )
    sun = sky_position_at(
        Body.SUN,
        jd_ut,
        observer_lat,
        observer_lon,
        observer_elev_m,
        reader=reader,
    )
    sun_geometric = sky_position_at(
        Body.SUN,
        jd_ut,
        observer_lat,
        observer_lon,
        observer_elev_m,
        reader=reader,
        refraction=False,
    )
    ra_star, dec_star, star_altitude = _star_topocentric_equatorial(
        star_lon,
        star_lat,
        jd_ut,
        observer_lat,
        observer_lon,
        observer_elev_m,
        reader=reader,
    )
    apparent_separation, margin, _, _ = _star_topocentric_target_geometry(
        star_lon,
        star_lat,
        jd_ut,
        observer_lat,
        observer_lon,
        reader,
        observer_elev_m,
        limb_profile_provider,
    )
    position_angle = _position_angle_equatorial(
        moon.right_ascension,
        moon.declination,
        ra_star,
        dec_star,
    )
    moon_axis_angle = _moon_axis_position_angle_deg(
        _ut1_to_ephemeris_tt(jd_ut, reader),
        reader,
    )
    axis_angle = _graze_axis_angle_deg(position_angle, moon_axis_angle)
    bright_limb_pa = _position_angle_equatorial(
        moon.right_ascension,
        moon.declination,
        sun.right_ascension,
        sun.declination,
    )
    cusp_angle, cusp_pole = _graze_cusp_angle(
        axis_angle,
        bright_limb_pa,
        moon_axis_angle,
    )
    zenith_distance = max(0.0, 90.0 - moon_geometric.altitude)
    tan_z = math.tan(math.radians(zenith_distance))
    return GrazeCircumstances(
        jd_ut=jd_ut,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_elev_m=observer_elev_m,
        moon_altitude_deg=moon_geometric.altitude,
        sun_altitude_deg=sun_geometric.altitude,
        zenith_distance_deg=zenith_distance,
        tan_z=tan_z,
        position_angle_deg=position_angle,
        axis_angle_deg=axis_angle,
        cusp_angle_deg=cusp_angle,
        cusp_pole=cusp_pole,
        margin_deg=margin,
        apparent_separation_deg=apparent_separation,
    )


def lunar_star_graze_table(
    star_lon: float,
    star_lat: float,
    jd_ut: float | tuple[float, ...] | list[float],
    longitudes_deg: tuple[float, ...] | list[float],
    guess_latitudes_deg: tuple[float, ...] | list[float],
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
) -> tuple[GrazeTableRow, ...]:
    """
    Build a typed local graze table along a supplied longitude track.

    Each row solves the graze latitude for the requested longitude, then
    computes the local circumstance columns in the same semantic frame as the
    published IOTA/Occult graze tables.
    """
    if len(longitudes_deg) != len(guess_latitudes_deg):
        raise ValueError("longitudes_deg and guess_latitudes_deg must have the same length")
    if isinstance(jd_ut, (tuple, list)):
        jd_values = tuple(float(value) for value in jd_ut)
        if len(jd_values) != len(longitudes_deg):
            raise ValueError("jd_ut sequence must match longitudes_deg length")
    else:
        jd_values = tuple(float(jd_ut) for _ in longitudes_deg)
    reader = get_reader() if reader is None else reader

    rows: list[GrazeTableRow] = []
    for jd_value, longitude_deg, guess_latitude_deg in zip(jd_values, longitudes_deg, guess_latitudes_deg):
        latitude_deg = _solve_star_graze_latitude(
            star_lon,
            star_lat,
            jd_value,
            float(longitude_deg),
            float(guess_latitude_deg),
            observer_elev_m=observer_elev_m,
            reader=reader,
            limb_profile_provider=limb_profile_provider,
        )
        moon = sky_position_at(
            Body.MOON,
            jd_value,
            latitude_deg,
            float(longitude_deg),
            observer_elev_m,
            reader=reader,
            refraction=False,
        )
        circumstances = lunar_star_graze_circumstances(
            star_lon,
            star_lat,
            jd_value,
            latitude_deg,
            float(longitude_deg),
            reader=reader,
            observer_elev_m=observer_elev_m,
            limb_profile_provider=limb_profile_provider,
        )
        rows.append(
            GrazeTableRow(
                jd_ut=jd_value,
                longitude_deg=float(longitude_deg),
                latitude_deg=latitude_deg,
                observer_elev_m=observer_elev_m,
                sun_altitude_deg=circumstances.sun_altitude_deg,
                moon_altitude_deg=circumstances.moon_altitude_deg,
                moon_azimuth_deg=moon.azimuth,
                tan_z=circumstances.tan_z,
                position_angle_deg=circumstances.position_angle_deg,
                axis_angle_deg=circumstances.axis_angle_deg,
                cusp_angle_deg=circumstances.cusp_angle_deg,
                cusp_pole=circumstances.cusp_pole,
            )
        )
    return tuple(rows)


def lunar_star_graze_latitude(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    longitude_deg: float,
    guess_latitude_deg: float,
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> float:
    """
    Solve the graze-limit latitude for a fixed star at a supplied longitude.

    This is the engine-owned stellar graze-limit solver used by the graze-table
    surface and by the external IOTA path validation layer.
    """
    return _solve_star_graze_latitude(
        star_lon,
        star_lat,
        jd_ut,
        longitude_deg,
        guess_latitude_deg,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=limb_profile_provider,
        refraction_adjusted=refraction_adjusted,
    )


def lunar_star_practical_graze_latitude(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    longitude_deg: float,
    guess_latitude_deg: float,
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> float:
    """
    Return the practical graze line at a longitude.

    Without a limb profile provider, this is identical to the nominal limit.
    With a real profile provider, it resolves to the effective line of the
    profile-conditioned product.
    """
    product = lunar_star_graze_product_at(
        star_lon,
        star_lat,
        jd_ut,
        longitude_deg,
        guess_latitude_deg,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=limb_profile_provider,
        refraction_adjusted=refraction_adjusted,
    )
    return product.practical_line_latitude_deg


def lunar_star_graze_line(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    longitude_deg: float,
    guess_latitude_deg: float,
    *,
    semantics: str = "nominal",
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> float:
    """
    Return the requested graze line for a fixed star.

    Supported semantics:
    - ``"nominal"``: the nominal graze limit
    - ``"practical"``: the practical/profile-conditioned line
    """
    if semantics == "nominal":
        return lunar_star_graze_latitude(
            star_lon,
            star_lat,
            jd_ut,
            longitude_deg,
            guess_latitude_deg,
            observer_elev_m=observer_elev_m,
            reader=reader,
            # Nominal means the spherical apparent limb by definition.  A
            # supplied topographic provider belongs only to the explicitly
            # practical/profile-conditioned branch below.
            limb_profile_provider=None,
            refraction_adjusted=refraction_adjusted,
        )
    if semantics == "practical":
        return lunar_star_practical_graze_latitude(
            star_lon,
            star_lat,
            jd_ut,
            longitude_deg,
            guess_latitude_deg,
            observer_elev_m=observer_elev_m,
            reader=reader,
            limb_profile_provider=limb_profile_provider,
            refraction_adjusted=refraction_adjusted,
        )
    raise ValueError("semantics must be 'nominal' or 'practical'")


def lunar_star_graze_product_at(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    longitude_deg: float,
    guess_latitude_deg: float,
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> GrazeProductGeometry:
    """
    Build the graze product for a fixed star at one longitude.

    Current constitutional split:
    - always returns the nominal graze limit
    - only returns a profile-conditioned band when a real limb-profile provider
      is explicitly supplied
    """
    reader = get_reader() if reader is None else reader
    nominal_limit = _solve_star_graze_latitude(
        star_lon,
        star_lat,
        jd_ut,
        longitude_deg,
        guess_latitude_deg,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=None,
        refraction_adjusted=refraction_adjusted,
    )
    if limb_profile_provider is None:
        return GrazeProductGeometry(
            product_kind="nominal_limit",
            jd_ut=jd_ut,
            longitude_deg=longitude_deg,
            nominal_limit_latitude_deg=nominal_limit,
            practical_line_latitude_deg=nominal_limit,
            profile_band_south_latitude_deg=None,
            profile_band_north_latitude_deg=None,
            observer_elev_m=observer_elev_m,
            has_profile_conditioned_band=False,
        )

    # Keep the two directional profile searches on the closed geographic
    # latitude domain.  Near a pole, the pole itself is the lawful endpoint
    # seed; the strict solver then scans back toward the interior as needed.
    north_seed = min(90.0, nominal_limit + 1.0)
    south_seed = max(-90.0, nominal_limit - 1.0)
    north = _solve_star_graze_latitude(
        star_lon,
        star_lat,
        jd_ut,
        longitude_deg,
        north_seed,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=limb_profile_provider,
        refraction_adjusted=refraction_adjusted,
    )
    south = _solve_star_graze_latitude(
        star_lon,
        star_lat,
        jd_ut,
        longitude_deg,
        south_seed,
        observer_elev_m=observer_elev_m,
        reader=reader,
        limb_profile_provider=limb_profile_provider,
        refraction_adjusted=refraction_adjusted,
    )
    practical_line = (south + north) / 2.0
    return GrazeProductGeometry(
        product_kind="profile_conditioned_band",
        jd_ut=jd_ut,
        longitude_deg=longitude_deg,
        nominal_limit_latitude_deg=nominal_limit,
        practical_line_latitude_deg=practical_line,
        profile_band_south_latitude_deg=min(south, north),
        profile_band_north_latitude_deg=max(south, north),
        observer_elev_m=observer_elev_m,
        has_profile_conditioned_band=True,
    )


def lunar_star_graze_product_track(
    star_lon: float,
    star_lat: float,
    jd_ut: float | tuple[float, ...] | list[float],
    longitudes_deg: tuple[float, ...] | list[float],
    guess_latitudes_deg: tuple[float, ...] | list[float],
    *,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    refraction_adjusted: bool = False,
) -> GrazeProductTrack:
    """
    Build a graze-product track over a longitude sequence.
    """
    if len(longitudes_deg) != len(guess_latitudes_deg):
        raise ValueError("longitudes_deg and guess_latitudes_deg must have the same length")
    if isinstance(jd_ut, (tuple, list)):
        jd_values = tuple(float(value) for value in jd_ut)
        if len(jd_values) != len(longitudes_deg):
            raise ValueError("jd_ut sequence must match longitudes_deg length")
    else:
        jd_values = tuple(float(jd_ut) for _ in longitudes_deg)
    reader = get_reader() if reader is None else reader

    products = tuple(
        lunar_star_graze_product_at(
            star_lon,
            star_lat,
            jd_value,
            float(longitude_deg),
            float(guess_latitude_deg),
            observer_elev_m=observer_elev_m,
            reader=reader,
            limb_profile_provider=limb_profile_provider,
            refraction_adjusted=refraction_adjusted,
        )
        for jd_value, longitude_deg, guess_latitude_deg in zip(jd_values, longitudes_deg, guess_latitudes_deg)
    )

    if limb_profile_provider is None:
        return GrazeProductTrack(
            product_kind="nominal_limit",
            jd_ut=tuple(product.jd_ut for product in products),
            longitude_deg=tuple(product.longitude_deg for product in products),
            nominal_limit_latitude_deg=tuple(product.nominal_limit_latitude_deg for product in products),
            practical_line_latitude_deg=tuple(product.practical_line_latitude_deg for product in products),
            profile_band_south_latitude_deg=None,
            profile_band_north_latitude_deg=None,
            observer_elev_m=observer_elev_m,
            has_profile_conditioned_band=False,
        )

    return GrazeProductTrack(
        product_kind="profile_conditioned_band",
        jd_ut=tuple(product.jd_ut for product in products),
        longitude_deg=tuple(product.longitude_deg for product in products),
        nominal_limit_latitude_deg=tuple(product.nominal_limit_latitude_deg for product in products),
        practical_line_latitude_deg=tuple(product.practical_line_latitude_deg for product in products),
        profile_band_south_latitude_deg=tuple(
            product.profile_band_south_latitude_deg if product.profile_band_south_latitude_deg is not None else product.nominal_limit_latitude_deg
            for product in products
        ),
        profile_band_north_latitude_deg=tuple(
            product.profile_band_north_latitude_deg if product.profile_band_north_latitude_deg is not None else product.nominal_limit_latitude_deg
            for product in products
        ),
        observer_elev_m=observer_elev_m,
        has_profile_conditioned_band=True,
    )


def _unit_sphere_xyz(latitude_deg: float, longitude_deg: float) -> tuple[float, float, float]:
    latitude_deg, longitude_deg = _offset_geographic_km(
        latitude_deg,
        longitude_deg,
        0.0,
        0.0,
    )
    latitude = math.radians(latitude_deg)
    longitude = math.radians(longitude_deg)
    cos_latitude = math.cos(latitude)
    return (
        cos_latitude * math.cos(longitude),
        cos_latitude * math.sin(longitude),
        math.sin(latitude),
    )


def _surface_distance_km(
    left_latitude_deg: float,
    left_longitude_deg: float,
    right_latitude_deg: float,
    right_longitude_deg: float,
) -> float:
    left = _unit_sphere_xyz(left_latitude_deg, left_longitude_deg)
    right = _unit_sphere_xyz(right_latitude_deg, right_longitude_deg)
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))
    cross = (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )
    return EARTH_RADIUS_KM * math.atan2(math.sqrt(sum(value * value for value in cross)), dot)


def _track_direction_ne(
    before: OccultationPathPoint,
    center: OccultationPathPoint,
    after: OccultationPathPoint,
) -> tuple[float, float]:
    before_xyz = _unit_sphere_xyz(before.latitude_deg, before.longitude_deg)
    center_xyz = _unit_sphere_xyz(center.latitude_deg, center.longitude_deg)
    after_xyz = _unit_sphere_xyz(after.latitude_deg, after.longitude_deg)
    displacement = tuple(a - b for a, b in zip(after_xyz, before_xyz))
    radial = sum(a * b for a, b in zip(displacement, center_xyz))
    tangent = tuple(a - radial * b for a, b in zip(displacement, center_xyz))
    norm = math.sqrt(sum(value * value for value in tangent))
    if norm <= 1.0e-15:
        raise _OccultationPathSolveError(
            "occultation center-track tangent is degenerate"
        )
    tangent = tuple(value / norm for value in tangent)

    latitude = math.radians(center.latitude_deg)
    longitude = math.radians(center.longitude_deg)
    north_basis = (
        -math.sin(latitude) * math.cos(longitude),
        -math.sin(latitude) * math.sin(longitude),
        math.cos(latitude),
    )
    east_basis = (-math.sin(longitude), math.cos(longitude), 0.0)
    north = sum(a * b for a, b in zip(tangent, north_basis))
    east = sum(a * b for a, b in zip(tangent, east_basis))
    component_norm = math.hypot(north, east)
    if component_norm <= 1.0e-15:
        raise _OccultationPathSolveError(
            "occultation center-track tangent is degenerate"
        )
    return north / component_norm, east / component_norm


def _sample_times_with_greatest(
    jd_start: float,
    jd_end: float,
    sample_count: int,
    jd_greatest: float,
) -> tuple[float, ...]:
    if sample_count == 1:
        return (jd_greatest,)
    if sample_count == 2:
        # Two endpoints cannot also carry an interior greatest epoch.  This is
        # the established legacy summary shape; the detailed topology always
        # has enough samples to materialize greatest explicitly.
        return (jd_start, jd_end)
    values = list(_sample_interval(jd_start, jd_end, sample_count))
    replace_index = min(
        range(1, len(values) - 1),
        key=lambda index: abs(values[index] - jd_greatest),
    )
    values[replace_index] = jd_greatest
    values.sort()
    if any(left >= right for left, right in zip(values, values[1:])):
        raise _OccultationPathSolveError(
            "occultation output epochs could not admit greatest UT1 uniquely"
        )
    return tuple(values)


def _solve_cross_track_boundary(
    position_func,
    center: OccultationPathPoint,
    track_direction_ne: tuple[float, float],
    side: OccultationPathBoundarySide,
) -> OccultationPathBoundaryPoint:
    if center.clearance_deg < -_OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG:
        raise _OccultationPathSolveError(
            "occultation center lies outside the admitted positive-clearance region"
        )
    if center.clearance_deg <= _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG:
        return OccultationPathBoundaryPoint(side, center, 0.0)

    track_north, track_east = track_direction_ne
    # In the local (east, north) tangent plane, LEFT is the +90-degree
    # rotation of the increasing-UT1 track: (E, N) -> (-N, E).
    cross_north = track_east
    cross_east = -track_north
    sign = 1.0 if side is OccultationPathBoundarySide.LEFT else -1.0

    def evaluate(distance_km: float) -> tuple[float, float, float, float, float, float]:
        latitude, longitude = _offset_geographic_km(
            center.latitude_deg,
            center.longitude_deg,
            sign * cross_north * distance_km,
            sign * cross_east * distance_km,
        )
        separation, clearance, azimuth, altitude = position_func(
            center.jd_ut,
            latitude,
            longitude,
        )
        if not math.isfinite(separation) or not math.isfinite(clearance):
            raise _OccultationPathSolveError(
                "occultation cross-track objective returned a non-finite value"
            )
        return latitude, longitude, separation, clearance, azimuth, altitude

    maximum_distance = math.pi * EARTH_RADIUS_KM
    low = 0.0
    high = min(_OCCULTATION_BOUNDARY_SCAN_STEP_KM, maximum_distance)
    high_geometry = evaluate(high)
    while high_geometry[3] > 0.0 and high < maximum_distance:
        low = high
        high = min(high + _OCCULTATION_BOUNDARY_SCAN_STEP_KM, maximum_distance)
        high_geometry = evaluate(high)
    if high_geometry[3] > 0.0:
        raise _OccultationPathSolveError(
            "occultation cross-track boundary did not close before the antipode"
        )

    while high - low > _OCCULTATION_BOUNDARY_DISTANCE_TOLERANCE_KM:
        midpoint = (low + high) / 2.0
        geometry = evaluate(midpoint)
        if geometry[3] > 0.0:
            low = midpoint
        else:
            high = midpoint
            high_geometry = geometry
    distance = (low + high) / 2.0
    latitude, longitude, separation, clearance, _azimuth, _altitude = evaluate(distance)
    if abs(clearance) > _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG:
        raise _OccultationPathSolveError(
            "occultation cross-track boundary residual exceeds tolerance"
        )
    return OccultationPathBoundaryPoint(
        side=side,
        point=OccultationPathPoint(
            jd_ut=center.jd_ut,
            latitude_deg=latitude,
            longitude_deg=longitude,
            separation_deg=separation,
            clearance_deg=clearance,
        ),
        cross_track_distance_km=distance,
    )


def _solve_occultation_pole_crossings(
    position_func,
    center_at: Callable[[float], OccultationPathPoint],
    jd_start: float,
    jd_end: float,
) -> tuple[OccultationPoleCrossing, ...]:
    """Solve exact-pole containment and its two roots in continuous UT1.

    Pole admission uses its own at-most-30-minute clearance lattice, independent
    of the caller's output sampling.  Bounded extrema refine that lattice; one
    connected positive-clearance interval is admitted, while a tangent or
    multiple disjoint intervals are not represented as a crossing pair.
    """

    span_days = jd_end - jd_start
    if not math.isfinite(span_days) or span_days <= 0.0:
        raise _OccultationPathSolveError(
            "occultation pole window must be finite and strictly ordered"
        )
    segment_count = max(
        1,
        math.ceil(span_days / _OCCULTATION_POLE_CLEARANCE_MAX_STEP_DAYS),
    )
    lattice_times = tuple(
        jd_start + span_days * index / segment_count
        for index in range(segment_count)
    ) + (jd_end,)
    crossings: list[OccultationPoleCrossing] = []

    for pole in (OccultationGeographicPole.NORTH, OccultationGeographicPole.SOUTH):
        latitude = 90.0 if pole is OccultationGeographicPole.NORTH else -90.0
        clearance_by_epoch: dict[float, float] = {}

        def clearance(jd_ut: float) -> float:
            known = clearance_by_epoch.get(jd_ut)
            if known is not None:
                return known
            value = float(position_func(jd_ut, latitude, 0.0)[1])
            if not math.isfinite(value):
                raise _OccultationPathSolveError(
                    "occultation exact-pole clearance returned a non-finite value"
                )
            clearance_by_epoch[jd_ut] = value
            return value

        lattice_clearances = tuple(clearance(jd_ut) for jd_ut in lattice_times)
        start_clearance = lattice_clearances[0]
        end_clearance = lattice_clearances[-1]

        maximum_brackets = {
            (lattice_times[0], lattice_times[1]),
            (lattice_times[-2], lattice_times[-1]),
        }
        maximum_brackets.update(
            (lattice_times[index - 1], lattice_times[index + 1])
            for index in range(1, len(lattice_times) - 1)
            if lattice_clearances[index] >= lattice_clearances[index - 1]
            and lattice_clearances[index] >= lattice_clearances[index + 1]
        )
        minimum_brackets = {
            (lattice_times[index - 1], lattice_times[index + 1])
            for index in range(1, len(lattice_times) - 1)
            if lattice_clearances[index] <= lattice_clearances[index - 1]
            and lattice_clearances[index] <= lattice_clearances[index + 1]
        }

        peak_candidates: list[tuple[float, float]] = list(
            zip(lattice_times, lattice_clearances)
        )
        topology_witnesses: list[tuple[float, float]] = list(peak_candidates)
        for bracket_left, bracket_right in sorted(maximum_brackets):
            candidate_jd, negative_clearance = _bisect_minimum(
                lambda jd_ut: -clearance(jd_ut),
                bracket_left,
                bracket_right,
                tol=_OCCULTATION_POLE_PEAK_TIME_TOLERANCE_DAYS,
            )
            candidate = (candidate_jd, -negative_clearance)
            peak_candidates.append(candidate)
            topology_witnesses.append(candidate)
        for bracket_left, bracket_right in sorted(minimum_brackets):
            candidate_jd, candidate_clearance = _bisect_minimum(
                clearance,
                bracket_left,
                bracket_right,
                tol=_OCCULTATION_POLE_PEAK_TIME_TOLERANCE_DAYS,
            )
            topology_witnesses.append((candidate_jd, candidate_clearance))

        peak_jd, peak_clearance = max(
            peak_candidates,
            key=lambda candidate: (candidate[1], -candidate[0]),
        )
        if peak_clearance <= _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG:
            continue
        if start_clearance > _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG or (
            end_clearance > _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG
        ):
            raise _OccultationPathSolveError(
                "occultation pole containment is not closed within the path window"
            )

        # Count connected positive regions using both the fixed lattice and
        # refined maxima/minima.  Values inside the declared boundary residual
        # band coalesce with the boundary and do not manufacture a new region.
        ordered_witnesses = sorted(
            {
                jd_ut: (jd_ut, candidate_clearance)
                for jd_ut, candidate_clearance in topology_witnesses
            }.values()
        )
        positive_regions = 0
        separated_from_positive = True
        for _jd_ut, candidate_clearance in ordered_witnesses:
            if candidate_clearance > _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG:
                if separated_from_positive:
                    positive_regions += 1
                    separated_from_positive = False
            elif candidate_clearance < -_OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG:
                separated_from_positive = True
        if positive_regions != 1:
            raise _OccultationPathSolveError(
                "multiple disjoint pole-containment intervals are not admitted"
            )

        ingress = (
            jd_start
            if start_clearance >= -_OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG
            else _bisection_root(clearance, jd_start, peak_jd)
        )
        egress = (
            jd_end
            if end_clearance >= -_OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG
            else _bisection_root(clearance, peak_jd, jd_end)
        )
        roots = (
            (ingress, OccultationPoleCrossingPhase.INGRESS),
            (egress, OccultationPoleCrossingPhase.EGRESS),
        )

        for root, phase in roots:

            separation, root_clearance, _azimuth, _altitude = position_func(
                root,
                latitude,
                0.0,
            )
            center = center_at(root)
            tangent_before = center_at(root - _OCCULTATION_TRACK_TANGENT_STEP_DAYS)
            tangent_after = center_at(root + _OCCULTATION_TRACK_TANGENT_STEP_DAYS)
            direction = _track_direction_ne(tangent_before, center, tangent_after)
            boundary_side = _classify_occultation_pole_side(direction, pole)

            crossings.append(
                OccultationPoleCrossing(
                    pole=pole,
                    phase=phase,
                    point=OccultationPathPoint(
                        jd_ut=root,
                        latitude_deg=latitude,
                        longitude_deg=0.0,
                        separation_deg=separation,
                        clearance_deg=root_clearance,
                    ),
                    boundary_side=boundary_side,
                )
            )

    return tuple(sorted(crossings, key=lambda crossing: crossing.point.jd_ut))


def _classify_occultation_pole_side(
    track_direction_ne: tuple[float, float],
    pole: OccultationGeographicPole,
) -> OccultationPathBoundarySide | None:
    """Classify a pole against the intrinsic increasing-UT1 path normal."""

    track_north, track_east = track_direction_ne
    left_north = track_east
    left_east = -track_north
    pole_north = 1.0 if pole is OccultationGeographicPole.NORTH else -1.0
    projection = pole_north * left_north + 0.0 * left_east
    if projection > _OCCULTATION_POLE_SIDE_DEGENERACY_TOLERANCE:
        return OccultationPathBoundarySide.LEFT
    if projection < -_OCCULTATION_POLE_SIDE_DEGENERACY_TOLERANCE:
        return OccultationPathBoundarySide.RIGHT
    return None


def _solve_occultation_clearance_center(
    position_func,
    jd_ut: float,
    *,
    preferred_location: tuple[float, float] | None = None,
    complete_surface: bool,
    refinement_steps_deg: tuple[float, ...] = _GEO_SEARCH_STEPS_DEG,
) -> OccultationPathPoint:
    latitude, longitude, _negative_clearance = _solve_occultation_greatest_location(
        lambda candidate_latitude, candidate_longitude: -position_func(
            jd_ut,
            candidate_latitude,
            candidate_longitude,
        )[1],
        preferred_location=preferred_location,
        early_exit_score=None,
        complete_surface=complete_surface,
        refinement_steps_deg=refinement_steps_deg,
    )
    separation, clearance, _azimuth, _altitude = position_func(
        jd_ut,
        latitude,
        longitude,
    )
    if not math.isfinite(separation) or not math.isfinite(clearance):
        raise _OccultationPathSolveError(
            "occultation center geometry returned a non-finite value"
        )
    return OccultationPathPoint(
        jd_ut=jd_ut,
        latitude_deg=latitude,
        longitude_deg=longitude,
        separation_deg=separation,
        clearance_deg=clearance,
    )


@dataclass(frozen=True, slots=True)
class _OccultationPathCalculation:
    jd_start: float
    jd_end: float
    jd_greatest: float
    duration_at_greatest_s: float
    centers: tuple[OccultationPathPoint, ...]
    boundaries: tuple[OccultationPathBoundaryTrack, OccultationPathBoundaryTrack]
    greatest_left: OccultationPathBoundaryPoint
    greatest_right: OccultationPathBoundaryPoint
    pole_crossings: tuple[OccultationPoleCrossing, ...]


def _make_occultation_center_resolver(
    position_func,
    *,
    initial_refinement_steps_deg: tuple[float, ...] = _GEO_SEARCH_STEPS_DEG,
) -> Callable[[float], OccultationPathPoint]:
    centers_by_epoch: dict[float, OccultationPathPoint] = {}

    def center_at(jd_ut: float) -> OccultationPathPoint:
        known = centers_by_epoch.get(jd_ut)
        if known is not None:
            return known
        preferred = None
        if centers_by_epoch:
            nearest = min(
                centers_by_epoch.values(),
                key=lambda point: abs(point.jd_ut - jd_ut),
            )
            preferred = (nearest.latitude_deg, nearest.longitude_deg)
        point = _solve_occultation_clearance_center(
            position_func,
            jd_ut,
            preferred_location=preferred,
            complete_surface=preferred is None,
            refinement_steps_deg=(
                initial_refinement_steps_deg
                if preferred is None
                else _GEO_SEARCH_STEPS_DEG
            ),
        )
        centers_by_epoch[jd_ut] = point
        return point

    return center_at


def _solve_occultation_greatest_track_direction(
    position_func,
    greatest_center: OccultationPathPoint,
) -> tuple[float, float]:
    """Return a history-independent local tangent at greatest occultation.

    Both one-minute witnesses refine the continuous center-track branch from
    the same greatest-center anchor.  They therefore cannot inherit whichever
    temporal-boundary sample happened to populate a shared cache most recently.
    """

    preferred_location = (
        greatest_center.latitude_deg,
        greatest_center.longitude_deg,
    )
    before = _solve_occultation_clearance_center(
        position_func,
        greatest_center.jd_ut - _OCCULTATION_TRACK_TANGENT_STEP_DAYS,
        preferred_location=preferred_location,
        complete_surface=False,
        refinement_steps_deg=_GEO_GREATEST_TANGENT_SEARCH_STEPS_DEG,
    )
    after = _solve_occultation_clearance_center(
        position_func,
        greatest_center.jd_ut + _OCCULTATION_TRACK_TANGENT_STEP_DAYS,
        preferred_location=preferred_location,
        complete_surface=False,
        refinement_steps_deg=_GEO_GREATEST_TANGENT_SEARCH_STEPS_DEG,
    )
    return _track_direction_ne(before, greatest_center, after)


def _solve_occultation_temporal_interval(
    center_at: Callable[[float], OccultationPathPoint],
    jd_mid: float,
) -> tuple[float, float]:
    def margin_at_time(jd_ut: float) -> float:
        return center_at(jd_ut).clearance_deg

    left_inside = jd_mid
    left = None
    for _ in range(_OCCULTATION_TEMPORAL_SCAN_LIMIT):
        candidate = left_inside - _OCCULTATION_TEMPORAL_SCAN_STEP_DAYS
        if margin_at_time(candidate) <= 0.0:
            left = _bisection_root(margin_at_time, candidate, left_inside)
            break
        left_inside = candidate
    if left is None:
        raise _OccultationPathSolveError(
            "occultation temporal boundary was not bracketed before greatest"
        )

    right_inside = jd_mid
    right = None
    for _ in range(_OCCULTATION_TEMPORAL_SCAN_LIMIT):
        candidate = right_inside + _OCCULTATION_TEMPORAL_SCAN_STEP_DAYS
        if margin_at_time(candidate) <= 0.0:
            right = _bisection_root(margin_at_time, right_inside, candidate)
            break
        right_inside = candidate
    if right is None:
        raise _OccultationPathSolveError(
            "occultation temporal boundary was not bracketed after greatest"
        )
    return left, right


def _solve_occultation_greatest_site_duration(
    position_func,
    greatest_center: OccultationPathPoint,
    jd_start: float,
    jd_end: float,
) -> float:
    """Solve fixed-site contacts at the greatest center, in seconds."""

    def site_clearance(jd_ut: float) -> float:
        value = float(
            position_func(
                jd_ut,
                greatest_center.latitude_deg,
                greatest_center.longitude_deg,
            )[1]
        )
        if not math.isfinite(value):
            raise _OccultationPathSolveError(
                "occultation greatest-site clearance returned a non-finite value"
            )
        return value

    greatest_clearance = site_clearance(greatest_center.jd_ut)
    if greatest_clearance <= _OCCULTATION_CLEARANCE_TOLERANCE_DEG:
        raise _OccultationPathSolveError(
            "occultation greatest site is not inside the footprint"
        )
    start_clearance = site_clearance(jd_start)
    end_clearance = site_clearance(jd_end)
    if start_clearance > _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG or (
        end_clearance > _OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG
    ):
        raise _OccultationPathSolveError(
            "occultation greatest-site contacts are not closed by the global path window"
        )
    ingress = (
        jd_start
        if start_clearance >= -_OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG
        else _bisection_root(
            site_clearance,
            jd_start,
            greatest_center.jd_ut,
        )
    )
    egress = (
        jd_end
        if end_clearance >= -_OCCULTATION_BOUNDARY_RESIDUAL_TOLERANCE_DEG
        else _bisection_root(
            site_clearance,
            greatest_center.jd_ut,
            jd_end,
        )
    )
    duration_s = (egress - ingress) * 86400.0
    if not math.isfinite(duration_s) or duration_s <= 0.0:
        raise _OccultationPathSolveError(
            "occultation greatest-site duration is not positive and finite"
        )
    return duration_s


def _calculate_occultation_path(
    *,
    jd_mid: float,
    position_func,
    detail_sample_count: int,
    solve_pole_crossings: bool,
) -> _OccultationPathCalculation:
    if (
        isinstance(detail_sample_count, bool)
        or not isinstance(detail_sample_count, int)
        or not _OCCULTATION_TOPOLOGY_MIN_SAMPLES
        <= detail_sample_count
        <= _OCCULTATION_TOPOLOGY_MAX_SAMPLES
    ):
        raise ValueError(
            "detailed occultation sample_count must be an integer in "
            f"[{_OCCULTATION_TOPOLOGY_MIN_SAMPLES}, {_OCCULTATION_TOPOLOGY_MAX_SAMPLES}]"
        )
    if not math.isfinite(jd_mid):
        raise ValueError("jd_mid must be finite")

    center_at = _make_occultation_center_resolver(
        position_func,
        initial_refinement_steps_deg=_GEO_GREATEST_TANGENT_SEARCH_STEPS_DEG,
    )

    greatest_center = center_at(jd_mid)
    if greatest_center.clearance_deg <= _OCCULTATION_CLEARANCE_TOLERANCE_DEG:
        raise _OccultationPathNotPresentError(
            "no occultation is present at the supplied greatest epoch"
        )

    left, right = _solve_occultation_temporal_interval(center_at, jd_mid)
    duration_at_greatest_s = _solve_occultation_greatest_site_duration(
        position_func,
        greatest_center,
        left,
        right,
    )

    detail_times = _sample_times_with_greatest(
        left,
        right,
        detail_sample_count,
        jd_mid,
    )
    # Greatest width must not depend on output sampling or center-cache history.
    fixed_track_direction = _solve_occultation_greatest_track_direction(
        position_func,
        greatest_center,
    )
    detail_centers = tuple(center_at(epoch) for epoch in detail_times)

    left_points: list[OccultationPathBoundaryPoint] = []
    right_points: list[OccultationPathBoundaryPoint] = []
    greatest_left = None
    greatest_right = None
    for index, center in enumerate(detail_centers):
        if center.jd_ut == jd_mid:
            track_direction = fixed_track_direction
        elif index == 0:
            before = center
            after = detail_centers[index + 1]
        elif index == len(detail_centers) - 1:
            before = detail_centers[index - 1]
            after = center
        else:
            before = detail_centers[index - 1]
            after = detail_centers[index + 1]
        if center.jd_ut != jd_mid:
            track_direction = _track_direction_ne(before, center, after)
        left_point = _solve_cross_track_boundary(
            position_func,
            center,
            track_direction,
            OccultationPathBoundarySide.LEFT,
        )
        right_point = _solve_cross_track_boundary(
            position_func,
            center,
            track_direction,
            OccultationPathBoundarySide.RIGHT,
        )
        left_points.append(left_point)
        right_points.append(right_point)
        if center.jd_ut == jd_mid:
            greatest_left = left_point
            greatest_right = right_point

    if greatest_left is None or greatest_right is None:
        raise _OccultationPathSolveError(
            "occultation greatest slice was not materialized"
        )

    for previous_left, current_left, previous_right, current_right in zip(
        left_points,
        left_points[1:],
        right_points,
        right_points[1:],
    ):
        same_assignment = _surface_distance_km(
            previous_left.point.latitude_deg,
            previous_left.point.longitude_deg,
            current_left.point.latitude_deg,
            current_left.point.longitude_deg,
        ) + _surface_distance_km(
            previous_right.point.latitude_deg,
            previous_right.point.longitude_deg,
            current_right.point.latitude_deg,
            current_right.point.longitude_deg,
        )
        swapped_assignment = _surface_distance_km(
            previous_left.point.latitude_deg,
            previous_left.point.longitude_deg,
            current_right.point.latitude_deg,
            current_right.point.longitude_deg,
        ) + _surface_distance_km(
            previous_right.point.latitude_deg,
            previous_right.point.longitude_deg,
            current_left.point.latitude_deg,
            current_left.point.longitude_deg,
        )
        if swapped_assignment + _OCCULTATION_BRANCH_SWAP_TOLERANCE_KM < same_assignment:
            raise _OccultationPathSolveError(
                "occultation boundary continuation is topologically ambiguous"
            )

    pole_crossings = (
        _solve_occultation_pole_crossings(
            position_func,
            center_at,
            left,
            right,
        )
        if solve_pole_crossings
        else ()
    )
    return _OccultationPathCalculation(
        jd_start=left,
        jd_end=right,
        jd_greatest=jd_mid,
        duration_at_greatest_s=duration_at_greatest_s,
        centers=detail_centers,
        boundaries=(
            OccultationPathBoundaryTrack(
                OccultationPathBoundarySide.LEFT,
                tuple(left_points),
            ),
            OccultationPathBoundaryTrack(
                OccultationPathBoundarySide.RIGHT,
                tuple(right_points),
            ),
        ),
        greatest_left=greatest_left,
        greatest_right=greatest_right,
        pole_crossings=pole_crossings,
    )


def _occultation_summary_from_centers(
    *,
    occulted_body: str,
    calculation: _OccultationPathCalculation,
    centers: tuple[OccultationPathPoint, ...],
) -> OccultationPathGeometry:
    return OccultationPathGeometry(
        occulting_body=Body.MOON,
        occulted_body=occulted_body,
        jd_greatest_ut=calculation.jd_greatest,
        central_line_lats=tuple(point.latitude_deg for point in centers),
        central_line_lons=tuple(point.longitude_deg for point in centers),
        path_width_km=(
            calculation.greatest_left.cross_track_distance_km
            + calculation.greatest_right.cross_track_distance_km
        ),
        duration_at_greatest_s=calculation.duration_at_greatest_s,
    )


def _build_occultation_path_topology(
    *,
    occulted_body: str,
    jd_mid: float,
    position_func,
    detail_sample_count: int,
    target_model: str,
    observer_elevation_m: float,
) -> OccultationPathTopology:
    calculation = _calculate_occultation_path(
        jd_mid=jd_mid,
        position_func=position_func,
        detail_sample_count=detail_sample_count,
        solve_pole_crossings=True,
    )
    summary = _occultation_summary_from_centers(
        occulted_body=occulted_body,
        calculation=calculation,
        centers=calculation.centers,
    )
    return OccultationPathTopology(
        summary=summary,
        topology=OccultationPathTopologyKind.TWO_SIDED_BAND,
        centers=calculation.centers,
        boundaries=calculation.boundaries,
        greatest_left=calculation.greatest_left,
        greatest_right=calculation.greatest_right,
        pole_crossings=calculation.pole_crossings,
        lunar_limb_model="SPHERICAL_MEAN_LIMB",
        target_model=target_model,
        observer_elevation_m=observer_elevation_m,
    )


def _build_occultation_path_geometry(
    *,
    occulted_body: str,
    jd_mid: float,
    position_func,
    sample_count: int,
) -> OccultationPathGeometry:
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count < 1
    ):
        raise ValueError("legacy occultation sample_count must be an integer >= 1")
    if not math.isfinite(jd_mid):
        raise ValueError("jd_mid must be finite")

    center_at = _make_occultation_center_resolver(
        position_func,
        initial_refinement_steps_deg=_GEO_GREATEST_TANGENT_SEARCH_STEPS_DEG,
    )
    greatest_center = center_at(jd_mid)
    if greatest_center.clearance_deg <= _OCCULTATION_CLEARANCE_TOLERANCE_DEG:
        # Historical path-at surfaces represent a polished non-event as one
        # zero-width/zero-duration point.  First-class topology intentionally
        # fails closed instead and never receives this compatibility vessel.
        return OccultationPathGeometry(
            occulting_body=Body.MOON,
            occulted_body=occulted_body,
            jd_greatest_ut=jd_mid,
            central_line_lats=(greatest_center.latitude_deg,),
            central_line_lons=(greatest_center.longitude_deg,),
            path_width_km=0.0,
            duration_at_greatest_s=0.0,
        )

    left, right = _solve_occultation_temporal_interval(center_at, jd_mid)
    duration_at_greatest_s = _solve_occultation_greatest_site_duration(
        position_func,
        greatest_center,
        left,
        right,
    )
    track_direction = _solve_occultation_greatest_track_direction(
        position_func,
        greatest_center,
    )
    greatest_left = _solve_cross_track_boundary(
        position_func,
        greatest_center,
        track_direction,
        OccultationPathBoundarySide.LEFT,
    )
    greatest_right = _solve_cross_track_boundary(
        position_func,
        greatest_center,
        track_direction,
        OccultationPathBoundarySide.RIGHT,
    )
    center_times = _sample_times_with_greatest(
        left,
        right,
        sample_count,
        jd_mid,
    )
    centers = tuple(center_at(jd_ut) for jd_ut in center_times)
    return OccultationPathGeometry(
        occulting_body=Body.MOON,
        occulted_body=occulted_body,
        jd_greatest_ut=jd_mid,
        central_line_lats=tuple(point.latitude_deg for point in centers),
        central_line_lons=tuple(point.longitude_deg for point in centers),
        path_width_km=(
            greatest_left.cross_track_distance_km
            + greatest_right.cross_track_distance_km
        ),
        duration_at_greatest_s=duration_at_greatest_s,
    )


def _build_star_occultation_path_geometry(
    *,
    star_lon: float,
    star_lat: float,
    star_name: str,
    jd_mid: float,
    sample_count: int,
    observer_elev_m: float,
    limb_profile_provider: LunarLimbProfileProvider | None,
    reader: SpkReader,
) -> OccultationPathGeometry:
    def position_func(jd: float, lat: float, lon: float) -> tuple[float, float, float, float]:
        return _star_topocentric_target_geometry(
            star_lon,
            star_lat,
            jd,
            lat,
            lon,
            reader,
            observer_elev_m,
            limb_profile_provider,
        )

    return _build_occultation_path_geometry(
        occulted_body=star_name,
        jd_mid=jd_mid,
        position_func=position_func,
        sample_count=sample_count,
    )


_OCCULTATION_MAX_ABS_JD = 40_000_000.0


def _topology_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _validate_topology_jd(name: str, value: object) -> float:
    result = _topology_real(name, value)
    if abs(result) > _OCCULTATION_MAX_ABS_JD:
        raise ValueError(
            f"{name} lies outside Moira's representable JD domain "
            f"[-{_OCCULTATION_MAX_ABS_JD:g}, {_OCCULTATION_MAX_ABS_JD:g}]"
        )
    return result


def _validate_topology_sample_count(sample_count: object) -> int:
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or not _OCCULTATION_TOPOLOGY_MIN_SAMPLES
        <= sample_count
        <= _OCCULTATION_TOPOLOGY_MAX_SAMPLES
    ):
        raise ValueError(
            "detailed occultation sample_count must be an integer in "
            f"[{_OCCULTATION_TOPOLOGY_MIN_SAMPLES}, {_OCCULTATION_TOPOLOGY_MAX_SAMPLES}]"
        )
    return sample_count


def _validate_planetary_topology_target(target: object) -> str:
    if (
        not isinstance(target, str)
        or target not in _TOPOLOGY_JPL_EQUATORIAL_TARGET_RADII_KM
    ):
        raise ValueError(
            f"target must identify an admitted JPL solid-body planet: {target!r}"
        )
    return target


def _validate_star_topology_identity(
    star_lon: object,
    star_lat: object,
    star_name: object,
) -> tuple[float, float, str]:
    longitude = _topology_real("star_lon", star_lon)
    latitude = _topology_real("star_lat", star_lat)
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("star_lat must be within [-90, 90]")
    if not isinstance(star_name, str) or not star_name.strip():
        raise ValueError("star_name must be a non-blank string")
    if star_name != star_name.strip():
        raise ValueError("star_name must not contain surrounding whitespace")
    if star_name.casefold() in _SOLAR_SYSTEM_BODY_LABELS_CASEFOLD:
        raise ValueError("star_name must not identify a Solar System body")
    return longitude, latitude, star_name


def _validate_topology_observer_elevation(value: object) -> float:
    elevation_m = _topology_real("observer_elev_m", value)
    if elevation_m < _OCCULTATION_TOPOLOGY_MIN_OBSERVER_ELEV_M:
        raise ValueError(
            "observer_elev_m lies below the WGS84 semi-minor-axis "
            "computational floor"
        )
    return elevation_m


def _validate_topology_range(
    jd_start: object,
    jd_end: object,
    step_days: object,
) -> tuple[float, float, float, int]:
    start = _validate_topology_jd("jd_start", jd_start)
    end = _validate_topology_jd("jd_end", jd_end)
    step = _topology_real("step_days", step_days)
    if end <= start:
        raise ValueError("jd_end must be greater than jd_start")
    if not 0.0 < step <= _OCCULTATION_TOPOLOGY_MAX_STEP_DAYS:
        raise ValueError(
            "step_days must be within "
            f"(0, {_OCCULTATION_TOPOLOGY_MAX_STEP_DAYS}]"
        )
    span_days = end - start
    if span_days > _OCCULTATION_TOPOLOGY_MAX_SPAN_DAYS:
        raise ValueError(
            "occultation topology range cannot exceed "
            f"{_OCCULTATION_TOPOLOGY_MAX_SPAN_DAYS:g} days"
        )
    segment_count = _topology_candidate_segment_count(start, end, step)
    return start, end, step, segment_count


def _topology_candidate_segment_count(
    jd_start: float,
    jd_end: float,
    step_days: float,
) -> int:
    """Return the deterministic bounded candidate-cell count."""

    span_days = jd_end - jd_start
    # Compare by multiplication before division so a subnormal positive step
    # fails by policy instead of overflowing span/step to infinity in ceil().
    if step_days * _OCCULTATION_TOPOLOGY_MAX_CANDIDATE_CELLS < span_days:
        raise ValueError(
            "occultation topology candidate scan exceeds "
            f"{_OCCULTATION_TOPOLOGY_MAX_CANDIDATE_CELLS} cells"
        )
    segment_count = math.ceil(span_days / step_days)
    previous = jd_start
    for index in range(1, segment_count):
        candidate = jd_start + index * step_days
        if not previous < candidate < jd_end:
            raise ValueError(
                "step_days does not produce a strictly advancing Julian-Day lattice"
            )
        previous = candidate
    return segment_count


def _occultation_candidate_time_tolerance(
    jd_start: float,
    jd_end: float,
) -> float:
    return max(
        _OCCULTATION_CANDIDATE_DEDUP_MIN_TOLERANCE_DAYS,
        _OCCULTATION_CANDIDATE_DEDUP_ULPS
        * math.ulp(max(abs(jd_start), abs(jd_end))),
    )


def _deduplicate_occultation_candidates(
    candidates: list[tuple[float, float]],
    *,
    tolerance_days: float,
) -> tuple[tuple[float, float], ...]:
    """Merge solver-equivalent epochs, retaining strongest then earliest."""

    if not candidates:
        return ()
    ordered = sorted(candidates)
    groups: list[list[tuple[float, float]]] = [[ordered[0]]]
    for candidate in ordered[1:]:
        if candidate[0] - groups[-1][-1][0] <= tolerance_days:
            groups[-1].append(candidate)
        else:
            groups.append([candidate])
    return tuple(
        max(group, key=lambda candidate: (candidate[1], -candidate[0]))
        for group in groups
    )


def _group_occultation_candidates_by_positive_support(
    candidates: list[tuple[float, float, float, float]],
    *,
    tolerance_days: float,
) -> tuple[tuple[tuple[float, float, float, float], ...], ...]:
    """Group raw maxima by their connected positive-clearance time support."""

    if not candidates:
        return ()
    ordered = sorted(candidates, key=lambda candidate: (candidate[2], candidate[3]))
    groups: list[list[tuple[float, float, float, float]]] = [[ordered[0]]]
    support_end = ordered[0][3]
    for candidate in ordered[1:]:
        # Supports are open positive-clearance intervals.  A zero-clearance
        # tangency, or endpoint contact indistinguishable within solver time
        # uncertainty, must not join two otherwise separate components.
        if candidate[2] < support_end - tolerance_days:
            groups[-1].append(candidate)
            support_end = max(support_end, candidate[3])
        else:
            groups.append([candidate])
            support_end = candidate[3]
    return tuple(tuple(group) for group in groups)


def _solve_occultation_component_greatest(
    center_at: Callable[[float], OccultationPathPoint],
    support_start: float,
    support_end: float,
    raw_witnesses: tuple[tuple[float, float], ...],
) -> tuple[float, float]:
    """Solve the strongest time-local maximum on one positive component.

    Connected positive clearance does not imply a unimodal time profile.  A
    private at-most-30-minute lattice discovers every resolved local maximum;
    each is refined independently, while support endpoints and the already
    refined raw bracket witnesses remain explicit candidates.
    """

    span_days = support_end - support_start
    if not math.isfinite(span_days) or span_days <= 0.0:
        raise _OccultationPathSolveError(
            "occultation component support must be finite and ordered"
        )
    segment_count = max(
        1,
        math.ceil(span_days / _OCCULTATION_COMPONENT_MAXIMUM_STEP_DAYS),
    )
    if segment_count > _OCCULTATION_COMPONENT_MAXIMUM_MAX_CELLS:
        raise _OccultationPathSolveError(
            "occultation component maximum lattice budget exceeded"
        )
    lattice_times = tuple(
        support_start + span_days * index / segment_count
        for index in range(segment_count)
    ) + (support_end,)
    if any(left >= right for left, right in zip(lattice_times, lattice_times[1:])):
        raise _OccultationPathSolveError(
            "occultation component maximum lattice did not advance"
        )
    lattice_candidates = tuple(
        (jd_ut, center_at(jd_ut).clearance_deg)
        for jd_ut in lattice_times
    )

    brackets = {
        (lattice_times[0], lattice_times[1]),
        (lattice_times[-2], lattice_times[-1]),
    }
    brackets.update(
        (lattice_times[index - 1], lattice_times[index + 1])
        for index in range(1, len(lattice_times) - 1)
        if lattice_candidates[index][1] >= lattice_candidates[index - 1][1]
        and lattice_candidates[index][1] >= lattice_candidates[index + 1][1]
    )
    for jd_ut, _clearance in raw_witnesses:
        if not support_start <= jd_ut <= support_end:
            raise _OccultationPathSolveError(
                "occultation component raw witness lies outside its support"
            )
        brackets.add(
            (
                max(support_start, jd_ut - _OCCULTATION_COMPONENT_MAXIMUM_STEP_DAYS),
                min(support_end, jd_ut + _OCCULTATION_COMPONENT_MAXIMUM_STEP_DAYS),
            )
        )

    refined_candidates: list[tuple[float, float]] = []
    for bracket_left, bracket_right in sorted(brackets):
        if bracket_left == bracket_right:
            continue
        peak_jd, negative_peak = _bisect_minimum(
            lambda jd_ut: -center_at(jd_ut).clearance_deg,
            bracket_left,
            bracket_right,
            tol=_OCCULTATION_COMPONENT_PEAK_TIME_TOLERANCE_DAYS,
        )
        refined_candidates.append((peak_jd, -negative_peak))

    return max(
        (
            *raw_witnesses,
            *lattice_candidates,
            *refined_candidates,
        ),
        key=lambda candidate: (candidate[1], -candidate[0]),
    )


def _horizontal_parallax_deg(distance_km: float, observer_radius_km: float) -> float:
    if not math.isfinite(distance_km) or distance_km <= 0.0:
        raise _OccultationPathSolveError("invalid geocentric distance in candidate envelope")
    if not math.isfinite(observer_radius_km) or observer_radius_km < 0.0:
        raise _OccultationPathSolveError("invalid observer radius in candidate envelope")
    if observer_radius_km >= distance_km:
        # Once the observer sphere reaches beyond the body, an observer on the
        # outward radial ray can see the topocentric direction reverse by
        # 180 degrees.  asin(R / d) governs only the exterior-observer case
        # R < d; clamping that ratio to one would cease to be an upper bound.
        return 180.0
    return math.degrees(math.asin(observer_radius_km / distance_km))


def _planet_occultation_candidate_envelope(
    target: str,
    jd_ut: float,
    observer_elevation_m: float,
    reader: SpkReader,
) -> float:
    moon = planet_at(Body.MOON, jd_ut, reader=reader)
    target_position = planet_at(target, jd_ut, reader=reader)
    observer_radius_km = EARTH_RADIUS_KM + max(0.0, observer_elevation_m) / 1000.0
    separation = _angular_separation(
        moon.longitude,
        moon.latitude,
        target_position.longitude,
        target_position.latitude,
    )
    return (
        _horizontal_parallax_deg(moon.distance, observer_radius_km)
        + _horizontal_parallax_deg(target_position.distance, observer_radius_km)
        + _apparent_radius(MOON_RADIUS_KM, moon.distance)
        + _apparent_radius(
            _TOPOLOGY_JPL_EQUATORIAL_TARGET_RADII_KM[target],
            target_position.distance,
        )
        - separation
    )


def _star_occultation_candidate_envelope(
    star_lon: float,
    star_lat: float,
    jd_ut: float,
    observer_elevation_m: float,
    reader: SpkReader,
) -> float:
    moon = planet_at(Body.MOON, jd_ut, reader=reader)
    observer_radius_km = EARTH_RADIUS_KM + max(0.0, observer_elevation_m) / 1000.0
    separation = _angular_separation(
        moon.longitude,
        moon.latitude,
        star_lon,
        star_lat,
    )
    return (
        _horizontal_parallax_deg(moon.distance, observer_radius_km)
        + _apparent_radius(MOON_RADIUS_KM, moon.distance)
        - separation
    )


def _find_global_occultation_epochs(
    *,
    jd_start: float,
    jd_end: float,
    step_days: float,
    segment_count: int,
    candidate_envelope: Callable[[float], float],
    position_func,
) -> tuple[float, ...]:
    """Find global greatest-overlap epochs without geocentric exclusion.

    The inexpensive envelope is a necessary parallax-plus-radii admission
    bound.  Every admitted candidate is then verified by maximizing the exact
    signed topocentric clearance over the Earth sphere and in UT1.
    """

    expected_segment_count = _topology_candidate_segment_count(
        jd_start,
        jd_end,
        step_days,
    )
    if (
        isinstance(segment_count, bool)
        or not isinstance(segment_count, int)
        or segment_count != expected_segment_count
    ):
        raise ValueError("segment_count must equal ceil((jd_end - jd_start) / step_days)")

    # Range policy is fully checked before allocating this at-most-4097 point
    # lattice or invoking the ephemeris-backed envelope.
    sample_times = [jd_start]
    for index in range(1, segment_count):
        next_time = jd_start + index * step_days
        if not sample_times[-1] < next_time < jd_end:
            raise _OccultationPathSolveError(
                "global occultation candidate scan did not advance"
            )
        sample_times.append(next_time)
    sample_times.append(jd_end)
    envelope_values = [float(candidate_envelope(jd_ut)) for jd_ut in sample_times]
    if any(not math.isfinite(value) for value in envelope_values):
        raise _OccultationPathSolveError(
            "global occultation candidate envelope returned a non-finite value"
        )

    # The first and last cells are unconditional: a narrow positive maximum
    # can be hidden between two negative samples at either range boundary.
    brackets = {
        (sample_times[0], sample_times[1]),
        (sample_times[-2], sample_times[-1]),
    }
    brackets.update(
        (sample_times[index - 1], sample_times[index + 1])
        for index in range(1, len(sample_times) - 1)
        if envelope_values[index] >= envelope_values[index - 1]
        and envelope_values[index] >= envelope_values[index + 1]
    )

    solver_time_tolerance_days = _occultation_candidate_time_tolerance(
        jd_start,
        jd_end,
    )
    raw_candidates: list[tuple[float, float, float, float]] = []
    for bracket_left, bracket_right in sorted(brackets):
        envelope_peak_jd, negative_envelope = _bisect_minimum(
            lambda jd_ut: -float(candidate_envelope(jd_ut)),
            bracket_left,
            bracket_right,
            tol=1.0e-8,
        )
        envelope_candidates = (
            (bracket_left, float(candidate_envelope(bracket_left))),
            (envelope_peak_jd, -negative_envelope),
            (bracket_right, float(candidate_envelope(bracket_right))),
        )
        envelope_peak_jd, envelope_peak = max(
            envelope_candidates,
            key=lambda candidate: (candidate[1], -candidate[0]),
        )
        if envelope_peak <= 0.0:
            continue

        centers_by_epoch: dict[float, OccultationPathPoint] = {}
        seed = _solve_occultation_clearance_center(
            position_func,
            envelope_peak_jd,
            complete_surface=True,
        )
        centers_by_epoch[envelope_peak_jd] = seed

        def exact_center_at(jd_ut: float) -> OccultationPathPoint:
            point = centers_by_epoch.get(jd_ut)
            if point is None:
                nearest = min(
                    centers_by_epoch.values(),
                    key=lambda candidate: abs(candidate.jd_ut - jd_ut),
                )
                point = _solve_occultation_clearance_center(
                    position_func,
                    jd_ut,
                    preferred_location=(nearest.latitude_deg, nearest.longitude_deg),
                    complete_surface=False,
                )
                centers_by_epoch[jd_ut] = point
            return point

        def maximum_clearance(jd_ut: float) -> float:
            return exact_center_at(jd_ut).clearance_deg

        left_index = sample_times.index(bracket_left)
        right_index = sample_times.index(bracket_right)
        exact_witnesses = [
            (envelope_peak_jd, maximum_clearance(envelope_peak_jd)),
        ]
        for _ in range(math.ceil(math.log2(segment_count + 1)) + 2):
            exact_bracket_left = sample_times[left_index]
            exact_bracket_right = sample_times[right_index]
            exact_peak_jd, negative_exact_peak = _bisect_minimum(
                lambda jd_ut: -maximum_clearance(jd_ut),
                exact_bracket_left,
                exact_bracket_right,
                tol=1.0e-8,
            )
            exact_witnesses.extend(
                (
                    (
                        exact_bracket_left,
                        maximum_clearance(exact_bracket_left),
                    ),
                    (exact_peak_jd, -negative_exact_peak),
                    (
                        exact_bracket_right,
                        maximum_clearance(exact_bracket_right),
                    ),
                )
            )
            exact_peak_jd, exact_peak = max(
                (
                    candidate
                    for candidate in exact_witnesses
                    if exact_bracket_left <= candidate[0] <= exact_bracket_right
                ),
                key=lambda candidate: (candidate[1], -candidate[0]),
            )
            touches_left = (
                exact_peak_jd - exact_bracket_left
                <= solver_time_tolerance_days
            )
            touches_right = (
                exact_bracket_right - exact_peak_jd
                <= solver_time_tolerance_days
            )
            expand_left = touches_left and left_index > 0
            expand_right = touches_right and right_index < segment_count
            if not expand_left and not expand_right:
                break
            width = right_index - left_index
            if expand_left:
                left_index = max(0, left_index - width)
            if expand_right:
                right_index = min(segment_count, right_index + width)
        else:
            raise _OccultationPathSolveError(
                "global occultation exact-maximum bracket did not stabilize"
            )
        if exact_peak <= _OCCULTATION_CLEARANCE_TOLERANCE_DEG:
            continue
        # An endpoint optimum is only a constrained range result, not a solved
        # greatest event.  Unconditional edge-cell brackets exist to recover a
        # hidden interior peak, never to relabel a monotonic range boundary.
        if exact_peak_jd - jd_start <= solver_time_tolerance_days or (
            jd_end - exact_peak_jd <= solver_time_tolerance_days
        ):
            continue
        support_start, support_end = _solve_occultation_temporal_interval(
            exact_center_at,
            exact_peak_jd,
        )
        raw_candidates.append(
            (exact_peak_jd, exact_peak, support_start, support_end)
        )

    # Event identity is the connected exact-positive temporal component, not
    # proximity between optimizer outputs.  Flat maxima from overlapping scan
    # brackets can legitimately differ by many solver time tolerances while
    # still belonging to the same physical occultation.
    results: list[float] = []
    for group in _group_occultation_candidates_by_positive_support(
        raw_candidates,
        tolerance_days=solver_time_tolerance_days,
    ):
        support_start = min(candidate[2] for candidate in group)
        support_end = max(candidate[3] for candidate in group)
        solver_equivalent_peaks = _deduplicate_occultation_candidates(
            [(candidate[0], candidate[1]) for candidate in group],
            tolerance_days=solver_time_tolerance_days,
        )
        seed_jd, _seed_clearance = max(
            solver_equivalent_peaks,
            key=lambda candidate: (candidate[1], -candidate[0]),
        )
        component_center_at = _make_occultation_center_resolver(
            position_func,
            initial_refinement_steps_deg=_GEO_GREATEST_TANGENT_SEARCH_STEPS_DEG,
        )
        component_center_at(seed_jd)
        component_peak_jd, component_peak = _solve_occultation_component_greatest(
            component_center_at,
            support_start,
            support_end,
            solver_equivalent_peaks,
        )
        if component_peak <= _OCCULTATION_CLEARANCE_TOLERANCE_DEG:
            raise _OccultationPathSolveError(
                "connected occultation candidate lost positive clearance"
            )
        # A component is emitted only when its unconstrained global greatest,
        # not merely one smaller interior hump, lies strictly in the request.
        if component_peak_jd - jd_start <= solver_time_tolerance_days or (
            jd_end - component_peak_jd <= solver_time_tolerance_days
        ):
            continue
        results.append(component_peak_jd)

    return tuple(sorted(results))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def close_approaches(
    body1: str,
    body2: str,
    jd_start: float,
    jd_end: float,
    max_sep_deg: float = 1.0,
    step_days: float = 0.5,
    reader: SpkReader | None = None,
) -> list[CloseApproach]:
    """
    Find all close approaches between two bodies within a date range.

    Parameters
    ----------
    body1, body2  : body names (Body.* constants)
    jd_start      : search start JD
    jd_end        : search end JD
    max_sep_deg   : maximum angular separation to report (degrees)
    step_days     : coarse scan step (smaller = slower but more precise)
    reader        : SpkReader (uses default if None)

    Returns
    -------
    List of CloseApproach, sorted chronologically.
    """
    if reader is None:
        reader = get_reader()

    results: list[CloseApproach] = []
    jd = jd_start
    sep_prev2 = _sep_between(body1, body2, jd - step_days, reader)
    sep_prev1 = _sep_between(body1, body2, jd, reader)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        sep_cur = _sep_between(body1, body2, jd_next, reader)

        # Local minimum: prev1 <= prev2 and prev1 <= cur
        if sep_prev1 <= sep_prev2 and sep_prev1 <= sep_cur and sep_prev1 <= max_sep_deg:
            jd_min, sep_min = _bisect_minimum(
                lambda t: _sep_between(body1, body2, t, reader),
                jd - step_days,
                jd_next,
                tol=1e-6,
            )
            if sep_min <= max_sep_deg:
                # Check if it's a true occultation (disks overlap)
                r1 = _PLANET_MEAN_RADIUS_DEG.get(body1, 0.0)
                r2 = _PLANET_MEAN_RADIUS_DEG.get(body2, 0.0)
                is_occ = sep_min < (r1 + r2)
                results.append(CloseApproach(
                    body1=body1,
                    body2=body2,
                    jd_ut=jd_min,
                    separation_deg=sep_min,
                    is_occultation=is_occ,
                ))

        sep_prev2 = sep_prev1
        sep_prev1 = sep_cur
        jd = jd_next

    return sorted(results, key=lambda e: e.jd_ut)


def lunar_occultation(
    target: str,
    jd_start: float,
    jd_end: float,
    step_days: float = 0.25,
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
) -> list[LunarOccultation]:
    """
    Find all occultations of a planet by the Moon in a date range.

    The Moon's angular radius (~0.26°) is used as the occultation threshold.
    Ingress/egress are bracketed to ~1 minute precision.

    Parameters
    ----------
    target     : planet name to check for occultation
    jd_start   : search start JD
    jd_end     : search end JD
    step_days  : coarse scan step (default 0.25 day = 6 hours)
    reader     : SpkReader (uses default if None)

    Returns
    -------
    List of LunarOccultation events.
    """
    if reader is None:
        reader = get_reader()

    results: list[LunarOccultation] = []
    threshold = _MOON_MEAN_RADIUS_DEG  # occultation when sep < Moon radius
    if observer_lat is not None and observer_lon is not None:
        sep_func = lambda t: _sep_between_topocentric(Body.MOON, target, t, observer_lat, observer_lon, observer_elev_m, reader)
    else:
        sep_func = lambda t: _sep_between(Body.MOON, target, t, reader)

    jd = jd_start
    sep_prev2 = sep_func(jd - step_days)
    sep_prev1 = sep_func(jd)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        sep_cur = sep_func(jd_next)

        if sep_prev1 <= sep_prev2 and sep_prev1 <= sep_cur:
            left = max(jd_start, jd - step_days)
            right = min(jd_end, jd_next)
            jd_mid, sep_min = _bisect_minimum(sep_func, left, right, tol=1e-6)
            if sep_min >= threshold:
                sep_prev2 = sep_prev1
                sep_prev1 = sep_cur
                jd = jd_next
                continue

            lo, hi = left, jd_mid
            for _ in range(40):
                mid = (lo + hi) / 2.0
                if sep_func(mid) < threshold:
                    hi = mid
                else:
                    lo = mid
            jd_ingress = (lo + hi) / 2.0

            lo, hi = jd_mid, right
            for _ in range(40):
                mid = (lo + hi) / 2.0
                if sep_func(mid) < threshold:
                    lo = mid
                else:
                    hi = mid
            jd_egress = (lo + hi) / 2.0

            target_r = _PLANET_MEAN_RADIUS_DEG.get(target, 0.0)
            is_total = sep_min < (_MOON_MEAN_RADIUS_DEG - target_r)

            if not results or abs(results[-1].jd_mid - jd_mid) > 1e-4:
                results.append(LunarOccultation(
                    target=target,
                    jd_ingress=jd_ingress,
                    jd_egress=jd_egress,
                    jd_mid=jd_mid,
                    min_separation=sep_min,
                    is_total=is_total,
                ))

        sep_prev2 = sep_prev1
        sep_prev1 = sep_cur
        jd = jd_next

    return results


def lunar_occultation_path(
    target: str,
    jd_start: float,
    jd_end: float,
    step_days: float = 0.25,
    sample_count: int = 9,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    reader: SpkReader | None = None,
) -> list[OccultationPathGeometry]:
    """
    Build typed geographic path surfaces for planetary lunar occultations.
    """
    if sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    if reader is None:
        reader = get_reader()

    events = lunar_occultation(
        target,
        jd_start,
        jd_end,
        step_days=step_days,
        reader=reader,
    )
    return [
        lunar_occultation_path_at(
            target,
            event.jd_mid,
            sample_count=sample_count,
            observer_elev_m=observer_elev_m,
            limb_profile_provider=limb_profile_provider,
            reader=reader,
        )
        for event in events
    ]


def lunar_occultation_path_at(
    target: str,
    jd_mid: float,
    *,
    sample_count: int = 9,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    reader: SpkReader | None = None,
) -> OccultationPathGeometry:
    """
    Build the geographic path surface for a planetary lunar occultation at
    a supplied greatest-occultation instant.
    """
    if sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    if reader is None:
        reader = get_reader()

    return _build_occultation_path_geometry(
        occulted_body=target,
        jd_mid=jd_mid,
        position_func=lambda jd, lat, lon, *, _target=target: _planet_topocentric_target_geometry(
            _target,
            jd,
            lat,
            lon,
            reader,
            observer_elev_m,
            limb_profile_provider,
        ),
        sample_count=sample_count,
    )


def lunar_occultation_path_topology(
    target: str,
    jd_start: float,
    jd_end: float,
    step_days: float = 0.25,
    sample_count: int = _OCCULTATION_TOPOLOGY_DEFAULT_SAMPLES,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
) -> list[OccultationPathTopology]:
    """Return detailed pole-safe path topology for planetary occultations."""

    target = _validate_planetary_topology_target(target)
    jd_start, jd_end, step_days, segment_count = _validate_topology_range(
        jd_start,
        jd_end,
        step_days,
    )
    sample_count = _validate_topology_sample_count(sample_count)
    observer_elev_m = _validate_topology_observer_elevation(observer_elev_m)
    if reader is None:
        reader = get_reader()

    def position_func(jd: float, lat: float, lon: float) -> tuple[float, float, float, float]:
        return _planet_topocentric_target_geometry(
            target,
            jd,
            lat,
            lon,
            reader,
            observer_elev_m,
            None,
        )

    epochs = _find_global_occultation_epochs(
        jd_start=jd_start,
        jd_end=jd_end,
        step_days=step_days,
        segment_count=segment_count,
        candidate_envelope=lambda jd_ut: _planet_occultation_candidate_envelope(
            target,
            jd_ut,
            observer_elev_m,
            reader,
        ),
        position_func=position_func,
    )
    return [
        lunar_occultation_path_topology_at(
            target,
            jd_greatest,
            sample_count=sample_count,
            observer_elev_m=observer_elev_m,
            reader=reader,
        )
        for jd_greatest in epochs
    ]


def lunar_occultation_path_topology_at(
    target: str,
    jd_mid: float,
    *,
    sample_count: int = _OCCULTATION_TOPOLOGY_DEFAULT_SAMPLES,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
) -> OccultationPathTopology:
    """Return the detailed topology at a supplied planetary greatest epoch."""

    target = _validate_planetary_topology_target(target)
    jd_mid = _validate_topology_jd("jd_mid", jd_mid)
    sample_count = _validate_topology_sample_count(sample_count)
    observer_elev_m = _validate_topology_observer_elevation(observer_elev_m)
    if reader is None:
        reader = get_reader()

    def position_func(jd: float, lat: float, lon: float) -> tuple[float, float, float, float]:
        return _planet_topocentric_target_geometry(
            target,
            jd,
            lat,
            lon,
            reader,
            observer_elev_m,
            None,
        )

    return _build_occultation_path_topology(
        occulted_body=target,
        jd_mid=jd_mid,
        position_func=position_func,
        detail_sample_count=sample_count,
        target_model="JPL_EQUATORIAL_SOLID_BODY",
        observer_elevation_m=observer_elev_m,
    )


def lunar_star_occultation(
    star_lon: float,
    star_lat: float,
    star_name: str,
    jd_start: float,
    jd_end: float,
    step_days: float = 0.25,
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
) -> list[LunarOccultation]:
    """
    Find all occultations of a fixed star by the Moon.

    Since fixed stars move very slowly (proper motion negligible over years),
    their position is treated as fixed at the given ecliptic coordinates.

    Parameters
    ----------
    star_lon   : star ecliptic longitude (degrees, tropical)
    star_lat   : star ecliptic latitude (degrees)
    star_name  : name label for the returned events
    jd_start   : search start JD
    jd_end     : search end JD
    step_days  : coarse scan step
    reader     : SpkReader (uses default if None)

    Returns
    -------
    List of LunarOccultation events.
    """
    if reader is None:
        reader = get_reader()

    def _moon_star_sep(jd: float) -> float:
        if observer_lat is not None and observer_lon is not None:
            jd_tt = _ut1_to_ephemeris_tt(jd, reader)
            moon = sky_position_at(
                Body.MOON,
                jd,
                observer_lat,
                observer_lon,
                observer_elev_m,
                reader=reader,
            )
            from .stars import star_at

            star = star_at(
                star_name,
                jd_tt,
                observer_lat=observer_lat,
                observer_lon=observer_lon,
                observer_elev_m=observer_elev_m,
            )
            ra_star, dec_star = ecliptic_to_equatorial(
                star.longitude,
                star.latitude,
                true_obliquity(jd_tt),
            )
            return _angular_separation_equatorial(
                moon.right_ascension,
                moon.declination,
                ra_star,
                dec_star,
            )

        moon = planet_at(Body.MOON, jd, reader=reader)
        return _angular_separation(moon.longitude, moon.latitude, star_lon, star_lat)

    threshold = _MOON_MEAN_RADIUS_DEG
    results: list[LunarOccultation] = []
    jd = jd_start
    sep_prev2 = _moon_star_sep(jd - step_days)
    sep_prev1 = _moon_star_sep(jd)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        sep_cur = _moon_star_sep(jd_next)

        if sep_prev1 <= sep_prev2 and sep_prev1 <= sep_cur:
            left = max(jd_start, jd - step_days)
            right = min(jd_end, jd_next)
            jd_mid, sep_min = _bisect_minimum(_moon_star_sep, left, right, tol=1e-6)
            if sep_min >= threshold:
                sep_prev2 = sep_prev1
                sep_prev1 = sep_cur
                jd = jd_next
                continue

            lo, hi = left, jd_mid
            for _ in range(40):
                mid = (lo + hi) / 2.0
                if _moon_star_sep(mid) < threshold:
                    hi = mid
                else:
                    lo = mid
            jd_ingress = (lo + hi) / 2.0

            lo, hi = jd_mid, right
            for _ in range(40):
                mid = (lo + hi) / 2.0
                if _moon_star_sep(mid) < threshold:
                    lo = mid
                else:
                    hi = mid
            jd_egress = (lo + hi) / 2.0

            if not results or abs(results[-1].jd_mid - jd_mid) > 1e-4:
                results.append(LunarOccultation(
                    target=star_name,
                    jd_ingress=jd_ingress,
                    jd_egress=jd_egress,
                    jd_mid=jd_mid,
                    min_separation=sep_min,
                    is_total=(sep_min < _MOON_MEAN_RADIUS_DEG),
                ))

        sep_prev2 = sep_prev1
        sep_prev1 = sep_cur
        jd = jd_next

    return results


def lunar_star_occultation_path(
    star_lon: float,
    star_lat: float,
    star_name: str,
    jd_start: float,
    jd_end: float,
    step_days: float = 0.25,
    sample_count: int = 9,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    reader: SpkReader | None = None,
) -> list[OccultationPathGeometry]:
    """
    Build typed geographic path surfaces for lunar occultations of a fixed star.
    """
    if sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    if reader is None:
        reader = get_reader()

    events = lunar_star_occultation(
        star_lon,
        star_lat,
        star_name,
        jd_start,
        jd_end,
        step_days=step_days,
        reader=reader,
    )
    return [
        lunar_star_occultation_path_at(
            star_lon,
            star_lat,
            star_name,
            event.jd_mid,
            sample_count=sample_count,
            observer_elev_m=observer_elev_m,
            limb_profile_provider=limb_profile_provider,
            reader=reader,
        )
        for event in events
    ]


def lunar_star_occultation_path_at(
    star_lon: float,
    star_lat: float,
    star_name: str,
    jd_mid: float,
    *,
    sample_count: int = 9,
    observer_elev_m: float = 0.0,
    limb_profile_provider: LunarLimbProfileProvider | None = None,
    reader: SpkReader | None = None,
) -> OccultationPathGeometry:
    """
    Build the geographic path surface for a fixed-star lunar occultation at
    a supplied greatest-occultation instant.
    """
    if sample_count < 1:
        raise ValueError("sample_count must be >= 1")
    if reader is None:
        reader = get_reader()

    return _build_star_occultation_path_geometry(
        star_lon=star_lon,
        star_lat=star_lat,
        star_name=star_name,
        jd_mid=jd_mid,
        sample_count=sample_count,
        observer_elev_m=observer_elev_m,
        limb_profile_provider=limb_profile_provider,
        reader=reader,
    )


def lunar_star_occultation_path_topology(
    star_lon: float,
    star_lat: float,
    star_name: str,
    jd_start: float,
    jd_end: float,
    step_days: float = 0.25,
    sample_count: int = _OCCULTATION_TOPOLOGY_DEFAULT_SAMPLES,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
) -> list[OccultationPathTopology]:
    """Return detailed pole-safe path topology for stellar occultations."""

    star_lon, star_lat, star_name = _validate_star_topology_identity(
        star_lon,
        star_lat,
        star_name,
    )
    jd_start, jd_end, step_days, segment_count = _validate_topology_range(
        jd_start,
        jd_end,
        step_days,
    )
    sample_count = _validate_topology_sample_count(sample_count)
    observer_elev_m = _validate_topology_observer_elevation(observer_elev_m)
    if reader is None:
        reader = get_reader()

    def position_func(jd: float, lat: float, lon: float) -> tuple[float, float, float, float]:
        return _star_topocentric_target_geometry(
            star_lon,
            star_lat,
            jd,
            lat,
            lon,
            reader,
            observer_elev_m,
            None,
        )

    epochs = _find_global_occultation_epochs(
        jd_start=jd_start,
        jd_end=jd_end,
        step_days=step_days,
        segment_count=segment_count,
        candidate_envelope=lambda jd_ut: _star_occultation_candidate_envelope(
            star_lon,
            star_lat,
            jd_ut,
            observer_elev_m,
            reader,
        ),
        position_func=position_func,
    )
    return [
        lunar_star_occultation_path_topology_at(
            star_lon,
            star_lat,
            star_name,
            jd_greatest,
            sample_count=sample_count,
            observer_elev_m=observer_elev_m,
            reader=reader,
        )
        for jd_greatest in epochs
    ]


def lunar_star_occultation_path_topology_at(
    star_lon: float,
    star_lat: float,
    star_name: str,
    jd_mid: float,
    *,
    sample_count: int = _OCCULTATION_TOPOLOGY_DEFAULT_SAMPLES,
    observer_elev_m: float = 0.0,
    reader: SpkReader | None = None,
) -> OccultationPathTopology:
    """Return the detailed topology at a supplied stellar greatest epoch."""

    star_lon, star_lat, star_name = _validate_star_topology_identity(
        star_lon,
        star_lat,
        star_name,
    )
    jd_mid = _validate_topology_jd("jd_mid", jd_mid)
    sample_count = _validate_topology_sample_count(sample_count)
    observer_elev_m = _validate_topology_observer_elevation(observer_elev_m)
    if reader is None:
        reader = get_reader()

    def position_func(jd: float, lat: float, lon: float) -> tuple[float, float, float, float]:
        return _star_topocentric_target_geometry(
            star_lon,
            star_lat,
            jd,
            lat,
            lon,
            reader,
            observer_elev_m,
            None,
        )

    return _build_occultation_path_topology(
        occulted_body=star_name,
        jd_mid=jd_mid,
        position_func=position_func,
        detail_sample_count=sample_count,
        target_model="POINT_SOURCE",
        observer_elevation_m=observer_elev_m,
    )


def all_lunar_occultations(
    jd_start: float,
    jd_end: float,
    planets: list[str] | None = None,
    reader: SpkReader | None = None,
) -> list[LunarOccultation]:
    """
    Find all Moon occultations of the visible planets in a date range.

    Parameters
    ----------
    jd_start : search start JD
    jd_end   : search end JD
    planets  : list of planets to check (defaults to Mercury–Saturn)
    reader   : SpkReader (uses default if None)

    Returns
    -------
    All LunarOccultation events sorted chronologically.
    """
    if reader is None:
        reader = get_reader()
    if planets is None:
        planets = [
            Body.MERCURY, Body.VENUS, Body.MARS,
            Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE,
        ]

    all_events: list[LunarOccultation] = []
    for planet in planets:
        all_events.extend(lunar_occultation(planet, jd_start, jd_end, reader=reader))

    return sorted(all_events, key=lambda e: e.jd_ingress)
