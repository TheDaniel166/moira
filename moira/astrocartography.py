"""
Moira - Astrocartography Engine
=================================

Archetype: Engine

Purpose
-------
Governs computation of Astro*Carto*Graphy (ACG) lines - the geographic
curves and meridians showing where each natal planet was on the MC, IC,
Ascendant, or Descendant at the birth moment.

Boundary declaration
--------------------
Owns: MC/IC meridian computation, ASC/DSC curve sampling, and the
      ``ACGLine`` result vessel.
Delegates: apparent RA/Dec retrieval to ``moira.planets.sky_position_at``,
           Greenwich Apparent Sidereal Time to ``moira.julian``,
           nutation to ``moira.obliquity``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Requires caller to supply
apparent geocentric equatorial coordinates (RA/Dec) and GMST, or a
``ChartContext`` for the convenience wrapper.

Public surface
--------------
``ACGLine``        - vessel for a single ACG line (one planet, one line type).
``acg_lines``      - compute all four ACG lines for a dict of bodies.
``acg_from_chart`` - convenience wrapper for a ``ChartContext``.
"""

from __future__ import annotations


import inspect
import math
from dataclasses import dataclass, field

from .constants import DEG2RAD, Body

# WGS-84 first eccentricity squared: e^2 = 1 - (b/a)^2 ~= 0.006694379990
# Used to convert geodetic latitude -> geocentric latitude for the horizon
# hour-angle formula. The maximum difference is ~11.5 arcminutes near +/-45 deg,
# which can shift an ASC/DSC line by several kilometres on a rendered map.
_WGS84_E2 = 0.00669437999014

__all__ = [
    "ACGLine",
    "SubPlanetaryPoint",
    "FixedStarAstrocartographySubject",
    "FixedStarAstrocartographyTruth",
    "FixedStarAstrocartographyResult",
    "acg_lines",
    "acg_from_chart",
    "subplanetary_points",
    "subplanetary_from_chart",
    "fixed_star_equatorial_subject",
    "fixed_star_astrocartography",
    "fixed_star_astrocartography_from_chart",
]


@dataclass(slots=True)
class ACGLine:
    """
    RITE: The Geographic Vessel - a planet's line of power across the Earth.

    THEOREM: Holds the planet name, line type (MC/IC/ASC/DSC), and either
    a single meridian longitude or a list of sampled (latitude, longitude)
    curve points representing one ACG line.

    RITE OF PURPOSE:
        Serves the Astrocartography Engine as the canonical result vessel for
        ACG line data. Each planet produces four primary geographic features;
        without this vessel, callers would have no structured representation
        of the curves and meridians needed for map rendering.

    LAW OF OPERATION:
        Responsibilities:
            - Store the planet name and line type string.
            - For MC/IC lines: store the single geographic longitude.
            - For ASC/DSC lines: store sampled (latitude, longitude) curve points.
        Non-responsibilities:
            - Does not compute lines (delegated to ``acg_lines``).
            - Does not render or project lines onto a map.
        Dependencies:
            - Populated by ``acg_lines()`` or ``acg_from_chart()``.
        Structural invariants:
            - For MC/IC: ``longitude`` is set, ``points`` is empty.
            - For ASC/DSC: ``points`` is non-empty, ``longitude`` is None.
        Succession stance: terminal.

    Canon: Lewis, "Astro*Carto*Graphy" (1976);
           Meeus, "Astronomical Algorithms" Ch. 24.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.astrocartography.ACGLine",
        "risk": "medium",
        "api": {"frozen": ["planet", "line_type", "longitude", "points"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "raise"},
        "succession": {"stance": "terminal"},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    planet: str
    line_type: str
    longitude: float | None = None
    points: list[tuple[float, float]] = field(default_factory=list)

    def __repr__(self) -> str:
        if self.line_type in ("MC", "IC"):
            return (
                f"ACGLine({self.planet!r}, {self.line_type!r}, "
                f"lon={self.longitude:.4f}deg)"
            )
        return (
            f"ACGLine({self.planet!r}, {self.line_type!r}, "
            f"{len(self.points)} points)"
        )


@dataclass(slots=True)
class SubPlanetaryPoint:
    """
    Typed vessel for a body's zenith or nadir geographic point on Earth.

    The governing object is the terrestrial surface point whose local zenith
    (or nadir) is collinear with the body's apparent geocentric equatorial
    direction at a given epoch.
    """

    planet: str
    point_type: str
    latitude: float
    longitude: float

    def __repr__(self) -> str:
        return (
            f"SubPlanetaryPoint({self.planet!r}, {self.point_type!r}, "
            f"lat={self.latitude:.4f}deg, lon={self.longitude:.4f}deg)"
        )


@dataclass(frozen=True, slots=True)
class FixedStarAstrocartographySubject:
    """One source-resolved fixed star in true-of-date equatorial geometry."""

    requested_name: str
    canonical_name: str
    nomenclature: str
    constellation: str | None
    source_kind: str
    lookup_kind: str
    hipparcos_name: str | None
    source_mode: str
    gaia_match_status: str
    gaia_source_index: int | None
    merge_state: str
    observer_mode: str
    relation_kind: str
    relation_basis: str
    true_position: bool
    dedup_applied: bool
    is_topocentric: bool
    longitude: float
    latitude: float
    right_ascension: float
    declination: float
    magnitude: float
    position_source: str = "moira.stars.star_at:ecliptic_to_equatorial"

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                self.requested_name,
                self.canonical_name,
                self.nomenclature,
                self.source_kind,
                self.lookup_kind,
                self.source_mode,
                self.gaia_match_status,
                self.merge_state,
                self.observer_mode,
                self.relation_kind,
                self.relation_basis,
                self.position_source,
            )
        ):
            raise ValueError("fixed-star astrocartography identity fields must not be empty")
        coordinates = (
            self.longitude,
            self.latitude,
            self.right_ascension,
            self.declination,
            self.magnitude,
        )
        if not all(math.isfinite(value) for value in coordinates):
            raise ValueError("fixed-star astrocartography coordinates must be finite")
        object.__setattr__(self, "longitude", self.longitude % 360.0)
        object.__setattr__(self, "right_ascension", self.right_ascension % 360.0)
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("fixed-star ecliptic latitude must lie in [-90, 90]")
        if not -90.0 <= self.declination <= 90.0:
            raise ValueError("fixed-star declination must lie in [-90, 90]")
        if not all(
            isinstance(value, bool)
            for value in (
                self.true_position,
                self.dedup_applied,
                self.is_topocentric,
            )
        ):
            raise ValueError("fixed-star provenance flags must be boolean")


@dataclass(frozen=True, slots=True)
class FixedStarAstrocartographyTruth:
    """Epoch, frame, and source receipt for one fixed-star ACG result."""

    requested_names: tuple[str, ...]
    canonical_names: tuple[str, ...]
    jd_ut: float
    jd_tt: float
    apparent_sidereal_time_deg: float
    true_obliquity_deg: float
    nutation_longitude_deg: float
    lat_step: float
    refraction: bool
    coordinate_frame: str = "true_equator_and_equinox_of_date"
    star_position_source: str = "moira.stars.star_at:true_ecliptic_of_date"
    equatorial_conversion_source: str = "moira.coordinates.ecliptic_to_equatorial"
    line_geometry_source: str = "moira.astrocartography.acg_lines"
    point_geometry_source: str = "moira.astrocartography.subplanetary_points"
    interpretation: str = "none_geometry_only"

    def __post_init__(self) -> None:
        if not self.requested_names or not self.canonical_names:
            raise ValueError("fixed-star astrocartography name sets must not be empty")
        if len(self.requested_names) != len(self.canonical_names):
            raise ValueError("fixed-star requested and canonical name counts must match")
        if len(set(self.requested_names)) != len(self.requested_names):
            raise ValueError("fixed-star requested names must be unique")
        if len(set(self.canonical_names)) != len(self.canonical_names):
            raise ValueError("fixed-star canonical names must be unique")
        values = (
            self.jd_ut,
            self.jd_tt,
            self.apparent_sidereal_time_deg,
            self.true_obliquity_deg,
            self.nutation_longitude_deg,
            self.lat_step,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("fixed-star astrocartography truth values must be finite")
        if self.lat_step <= 0.0 or self.lat_step > 178.0:
            raise ValueError("fixed-star astrocartography lat_step must lie in (0, 178]")
        if not isinstance(self.refraction, bool):
            raise ValueError("fixed-star astrocartography refraction must be bool")


@dataclass(frozen=True, slots=True)
class FixedStarAstrocartographyResult:
    """Fixed-star MC/IC/ASC/DSC lines and zenith/nadir points at one epoch."""

    subjects: tuple[FixedStarAstrocartographySubject, ...]
    lines: tuple[ACGLine, ...]
    subplanetary_points: tuple[SubPlanetaryPoint, ...]
    computation_truth: FixedStarAstrocartographyTruth

    def __post_init__(self) -> None:
        names = tuple(subject.canonical_name for subject in self.subjects)
        if names != self.computation_truth.canonical_names:
            raise ValueError("fixed-star subjects must match computation truth")
        expected_line_keys = {
            (name, line_type)
            for name in names
            for line_type in ("MC", "IC", "ASC", "DSC")
        }
        line_keys = [(line.planet, line.line_type) for line in self.lines]
        if len(line_keys) != len(expected_line_keys) or set(line_keys) != expected_line_keys:
            raise ValueError(
                "fixed-star ACG result must carry exactly one MC/IC/ASC/DSC line per star"
            )
        expected_point_keys = {
            (name, point_type)
            for name in names
            for point_type in ("Zenith", "Nadir")
        }
        point_keys = [
            (point.planet, point.point_type)
            for point in self.subplanetary_points
        ]
        if (
            len(point_keys) != len(expected_point_keys)
            or set(point_keys) != expected_point_keys
        ):
            raise ValueError(
                "fixed-star ACG result must carry exactly one zenith/nadir point per star"
            )


def _wrap_longitude_deg(longitude_deg: float) -> float:
    """Normalize an east longitude into [-180, 180)."""
    wrapped = (longitude_deg + 180.0) % 360.0 - 180.0
    if wrapped == -180.0 and longitude_deg > 0.0:
        return 180.0
    return wrapped


def fixed_star_equatorial_subject(
    name: str,
    jd_tt: float,
    obliquity_deg: float,
) -> FixedStarAstrocartographySubject:
    """Resolve one star and convert its true-of-date ecliptic position to RA/Dec."""

    from .coordinates import ecliptic_to_equatorial
    from .stars import star_at

    if not isinstance(name, str) or not name.strip():
        raise ValueError("fixed-star astrocartography name must not be empty")
    if (
        isinstance(jd_tt, bool)
        or isinstance(obliquity_deg, bool)
        or not isinstance(jd_tt, (int, float))
        or not isinstance(obliquity_deg, (int, float))
        or not math.isfinite(jd_tt)
        or not math.isfinite(obliquity_deg)
    ):
        raise ValueError("fixed-star astrocartography epoch and obliquity must be finite")
    star = star_at(name, jd_tt)
    right_ascension, declination = ecliptic_to_equatorial(
        star.longitude,
        star.latitude,
        obliquity_deg,
    )
    truth = star.computation_truth
    classification = star.classification
    relation = star.relation
    if truth is None or classification is None or relation is None:
        raise ValueError("fixed-star astrocartography requires authoritative star provenance")
    return FixedStarAstrocartographySubject(
        requested_name=name,
        canonical_name=star.name,
        nomenclature=star.nomenclature,
        constellation=star.constellation,
        source_kind=classification.source_kind,
        lookup_kind=truth.lookup_kind,
        hipparcos_name=truth.hipparcos_name,
        source_mode=truth.source_mode,
        gaia_match_status=truth.gaia_match_status,
        gaia_source_index=truth.gaia_source_index,
        merge_state=classification.merge_state,
        observer_mode=classification.observer_mode,
        relation_kind=relation.kind,
        relation_basis=relation.basis,
        true_position=truth.true_position,
        dedup_applied=truth.dedup_applied,
        is_topocentric=truth.is_topocentric,
        longitude=star.longitude,
        latitude=star.latitude,
        right_ascension=right_ascension,
        declination=declination,
        magnitude=star.magnitude,
    )


def fixed_star_astrocartography(
    star_names: list[str] | tuple[str, ...],
    jd_ut: float,
    jd_tt: float,
    *,
    lat_step: float = 2.0,
    refraction: bool = False,
) -> FixedStarAstrocartographyResult:
    """Compute fixed-star ACG lines and subplanetary points at one epoch.

    ``jd_ut`` and ``jd_tt`` are both explicit so the function never guesses a
    clock conversion or silently binds a historical Delta-T basis.
    """

    from .julian import apparent_sidereal_time
    from .obliquity import nutation, true_obliquity

    if isinstance(star_names, (str, bytes)):
        raise ValueError("fixed-star astrocartography requires a sequence of names")
    names = tuple(star_names)
    if not names or any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("fixed-star astrocartography requires non-empty star names")
    if len(set(names)) != len(names):
        raise ValueError("fixed-star astrocartography requested names must be unique")
    if (
        isinstance(jd_ut, bool)
        or isinstance(jd_tt, bool)
        or not isinstance(jd_ut, (int, float))
        or not isinstance(jd_tt, (int, float))
        or not math.isfinite(jd_ut)
        or not math.isfinite(jd_tt)
    ):
        raise ValueError("fixed-star astrocartography jd_ut and jd_tt must be finite")
    if (
        isinstance(lat_step, bool)
        or not isinstance(lat_step, (int, float))
        or not math.isfinite(lat_step)
        or not 0.0 < lat_step <= 178.0
    ):
        raise ValueError("fixed-star astrocartography lat_step must lie in (0, 178]")
    if not isinstance(refraction, bool):
        raise ValueError("fixed-star astrocartography refraction must be bool")

    nutation_longitude, _ = nutation(jd_tt)
    obliquity = true_obliquity(jd_tt)
    sidereal_time = apparent_sidereal_time(jd_ut, nutation_longitude, obliquity)
    subjects = tuple(
        fixed_star_equatorial_subject(name, jd_tt, obliquity)
        for name in names
    )
    canonical_names = tuple(subject.canonical_name for subject in subjects)
    if len(set(canonical_names)) != len(canonical_names):
        raise ValueError("fixed-star aliases resolve to duplicate canonical identities")
    star_ra_dec = {
        subject.canonical_name: (subject.right_ascension, subject.declination)
        for subject in subjects
    }
    lines = tuple(
        acg_lines(
            star_ra_dec,
            sidereal_time,
            lat_step=lat_step,
            jd_ut=jd_ut,
            refraction=refraction,
        )
    )
    points = tuple(subplanetary_points(star_ra_dec, sidereal_time))
    truth = FixedStarAstrocartographyTruth(
        requested_names=names,
        canonical_names=canonical_names,
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        apparent_sidereal_time_deg=sidereal_time,
        true_obliquity_deg=obliquity,
        nutation_longitude_deg=nutation_longitude,
        lat_step=lat_step,
        refraction=refraction,
    )
    return FixedStarAstrocartographyResult(
        subjects=subjects,
        lines=lines,
        subplanetary_points=points,
        computation_truth=truth,
    )


def fixed_star_astrocartography_from_chart(
    chart,
    star_names: list[str] | tuple[str, ...],
    *,
    lat_step: float = 2.0,
    refraction: bool = False,
) -> FixedStarAstrocartographyResult:
    """Compute fixed-star ACG geometry from a chart's explicit UT1/TT pair."""

    jd_ut = getattr(chart, "jd_ut", None)
    jd_tt = getattr(chart, "jd_tt", None)
    if jd_ut is None or jd_tt is None:
        raise TypeError("fixed-star ACG chart must expose explicit jd_ut and jd_tt")
    return fixed_star_astrocartography(
        star_names,
        jd_ut,
        jd_tt,
        lat_step=lat_step,
        refraction=refraction,
    )


def _geodetic_latitude_from_declination(declination_deg: float) -> float:
    """
    Convert a geocentric declination to the matching WGS-84 geodetic latitude.

    Governing object:
        The zenith point is the surface location whose ellipsoidal normal is
        parallel to the body's geocentric apparent direction.
    """
    if not -90.0 <= declination_deg <= 90.0:
        raise ValueError(
            f"declination must lie in [-90, 90] degrees, got {declination_deg!r}"
        )
    if abs(abs(declination_deg) - 90.0) < 1e-12:
        return declination_deg
    declination_r = declination_deg * DEG2RAD
    return math.degrees(math.atan(math.tan(declination_r) / (1.0 - _WGS84_E2)))


def _compute_acg_curve_samples(
    ra: float,
    dec: float,
    gmst_deg: float,
    lats: list[float],
    sin_h0: float,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Return ASC and DSC samples for a fixed RA/Dec body."""
    dec_r = dec * DEG2RAD
    sin_dec = math.sin(dec_r)
    cos_dec = math.cos(dec_r)
    asc_pts: list[tuple[float, float]] = []
    dsc_pts: list[tuple[float, float]] = []

    for phi in lats:
        phi_r = phi * DEG2RAD
        phi_gc_r = math.atan((1.0 - _WGS84_E2) * math.tan(phi_r))
        denom = math.cos(phi_gc_r) * cos_dec
        if abs(denom) < 1e-12:
            continue

        cos_ha = (sin_h0 - math.sin(phi_gc_r) * sin_dec) / denom
        if abs(cos_ha) > 1.0:
            continue

        ha_deg = math.degrees(math.acos(cos_ha))
        asc_pts.append((phi, (ra - gmst_deg - ha_deg) % 360.0))
        dsc_pts.append((phi, (ra - gmst_deg + ha_deg) % 360.0))

    return asc_pts, dsc_pts


def acg_lines(
    planet_ra_dec: dict[str, tuple[float, float]],
    gmst_deg: float,
    lat_step: float = 2.0,
    jd_ut: float | None = None,
    refraction: bool = False,
    reader=None,
) -> list[ACGLine]:
    """
    Compute ACG lines for all planets given their RA/Dec and GMST at birth.

    Parameters
    ----------
    planet_ra_dec : dict of body name -> (RA degrees, Dec degrees).
                    RA and Dec are typically apparent geocentric equatorial
                    coordinates.
    gmst_deg      : Greenwich Apparent Sidereal Time at the birth moment (deg).
    lat_step      : latitude sampling resolution for ASC/DSC curves (degrees).
    jd_ut         : Julian Day (UT1). Required for topocentric lunar correction.
    refraction    : If True, apply atmospheric refraction (~34') to the horizon.
    reader        : Optional explicit ephemeris reader used by the lunar
                    topocentric curve refinement. Other bodies do not consume it.

    Returns
    -------
    list[ACGLine] - four lines per planet (MC, IC, ASC, DSC).
    """
    from .planets import sky_position_at

    if not math.isfinite(gmst_deg):
        raise ValueError(f"gmst_deg must be finite, got {gmst_deg!r}")
    if not math.isfinite(lat_step) or not 0.0 < lat_step <= 178.0:
        raise ValueError(f"lat_step must be finite and in (0, 178], got {lat_step!r}")

    lines: list[ACGLine] = []
    h0 = -0.5667 if refraction else 0.0
    sin_h0 = math.sin(h0 * DEG2RAD)
    lats = [
        -89.0 + i * lat_step
        for i in range(int(178.0 / lat_step) + 1)
        if -89.0 + i * lat_step <= 89.0
    ]

    for body, (ra_geo, dec_geo) in planet_ra_dec.items():
        if not math.isfinite(ra_geo) or not math.isfinite(dec_geo):
            raise ValueError(f"RA/Dec for {body!r} must be finite")
        if not -90.0 <= dec_geo <= 90.0:
            raise ValueError(
                f"declination for {body!r} must lie in [-90, 90] degrees, got {dec_geo!r}"
            )
        lon_mc = (ra_geo - gmst_deg) % 360.0
        lon_ic = (lon_mc + 180.0) % 360.0

        lines.append(ACGLine(planet=body, line_type="MC", longitude=lon_mc))
        lines.append(ACGLine(planet=body, line_type="IC", longitude=lon_ic))

        if body != Body.MOON or jd_ut is None:
            asc_points, dsc_points = _compute_acg_curve_samples(
                ra_geo, dec_geo, gmst_deg, lats, sin_h0
            )
        else:
            asc_points = []
            dsc_points = []
            for phi in lats:
                phi_r = phi * DEG2RAD
                phi_gc_r = math.atan((1.0 - _WGS84_E2) * math.tan(phi_r))

                sky = sky_position_at(
                    body,
                    jd_ut,
                    observer_lat=phi,
                    observer_lon=lon_mc,
                    reader=reader,
                    refraction=refraction,
                )
                ra, dec = sky.right_ascension, sky.declination
                dec_r = dec * DEG2RAD
                denom = math.cos(phi_gc_r) * math.cos(dec_r)
                if abs(denom) < 1e-12:
                    continue

                cos_ha = (sin_h0 - math.sin(phi_gc_r) * math.sin(dec_r)) / denom
                if abs(cos_ha) > 1.0:
                    continue

                ha_deg = math.degrees(math.acos(cos_ha))
                asc_points.append((phi, (ra - gmst_deg - ha_deg) % 360.0))
                dsc_points.append((phi, (ra - gmst_deg + ha_deg) % 360.0))

        lines.append(ACGLine(planet=body, line_type="ASC", points=asc_points))
        lines.append(ACGLine(planet=body, line_type="DSC", points=dsc_points))

    return lines


def acg_from_chart(
    chart,
    bodies: list[str] | None = None,
    lat_step: float = 2.0,
    refraction: bool = False,
    reader=None,
) -> list[ACGLine]:
    """
    Convenience wrapper: compute ACG lines directly from a Moira ChartContext.

    Extracts apparent RA/Dec for each requested body via
    ``moira.planets.sky_position_at()`` and GMST from ``chart.jd_ut``.

    Parameters
    ----------
    chart       : a ``ChartContext`` instance (from ``moira.chart``).
    bodies      : list of body names to include. Defaults to all bodies
                  present in ``chart.planets``.
    lat_step    : latitude sampling step passed through to :func:`acg_lines`.
    refraction  : if True, apply atmospheric refraction to horizon curves.
    reader      : optional explicit ephemeris reader for all position calls.

    Returns
    -------
    list[ACGLine] - four lines per planet.
    """
    from .planets import sky_position_at
    from .julian import apparent_sidereal_time
    from .obliquity import nutation, true_obliquity

    if bodies is None:
        bodies = list(chart.planets.keys())

    jd_tt = chart.jd_tt
    dpsi, _ = nutation(jd_tt)
    obliq = true_obliquity(jd_tt)
    gmst_deg = apparent_sidereal_time(chart.jd_ut, dpsi, obliq)

    planet_ra_dec: dict[str, tuple[float, float]] = {}
    for body in bodies:
        sky = sky_position_at(
            body,
            chart.jd_ut,
            observer_lat=chart.latitude,
            observer_lon=chart.longitude,
            reader=reader,
            refraction=refraction,
        )
        planet_ra_dec[body] = (sky.right_ascension, sky.declination)

    params = inspect.signature(acg_lines).parameters
    kwargs: dict[str, object] = {"lat_step": lat_step}
    if "jd_ut" in params:
        kwargs["jd_ut"] = chart.jd_ut
    if "refraction" in params:
        kwargs["refraction"] = refraction
    if "reader" in params:
        kwargs["reader"] = reader
    return acg_lines(planet_ra_dec, gmst_deg, **kwargs)


def subplanetary_points(
    planet_ra_dec: dict[str, tuple[float, float]],
    gmst_deg: float,
) -> list[SubPlanetaryPoint]:
    """
    Return zenith and nadir geographic points for bodies at one epoch.

    Parameters
    ----------
    planet_ra_dec : dict of body name -> (RA degrees, Dec degrees).
                    Coordinates are interpreted as apparent geocentric
                    equatorial positions in the true equator of date.
    gmst_deg      : Greenwich Apparent Sidereal Time at the epoch (deg).

    Returns
    -------
    list[SubPlanetaryPoint] - two points per body: Zenith and Nadir.
    """
    if not math.isfinite(gmst_deg):
        raise ValueError(f"gmst_deg must be finite, got {gmst_deg!r}")
    points: list[SubPlanetaryPoint] = []
    for body, (right_ascension, declination) in planet_ra_dec.items():
        if not math.isfinite(right_ascension) or not math.isfinite(declination):
            raise ValueError(f"RA/Dec for {body!r} must be finite")
        zenith_latitude = _geodetic_latitude_from_declination(declination)
        zenith_longitude = _wrap_longitude_deg(right_ascension - gmst_deg)
        points.append(
            SubPlanetaryPoint(
                planet=body,
                point_type="Zenith",
                latitude=zenith_latitude,
                longitude=zenith_longitude,
            )
        )
        points.append(
            SubPlanetaryPoint(
                planet=body,
                point_type="Nadir",
                latitude=-zenith_latitude,
                longitude=_wrap_longitude_deg(zenith_longitude + 180.0),
            )
        )
    return points


def subplanetary_from_chart(
    chart,
    bodies: list[str] | None = None,
) -> list[SubPlanetaryPoint]:
    """
    Convenience wrapper: compute sub-planetary zenith/nadir points from a chart.

    Uses the admitted apparent geocentric ecliptic surface, then converts the
    result into true-of-date equatorial RA/Dec so the geographic points remain
    globally defined for the epoch itself and inherit the existing small-body
    admission path.
    """
    from .coordinates import ecliptic_to_equatorial
    from .julian import apparent_sidereal_time, utc_to_tt, utc_to_ut1
    from .obliquity import nutation, true_obliquity
    from .planets import planet_at

    if bodies is None:
        bodies = list(chart.planets.keys())

    # ``moira.chart.ChartContext`` stores a true UT1/TT pair, while the
    # compatibility facade ``Chart`` intentionally stores its civil UTC JD in
    # ``jd_ut`` and has no ``jd_tt`` field.  Resolve either vessel without
    # changing its public shape.
    chart_jd_tt = getattr(chart, "jd_tt", None)
    if chart_jd_tt is None:
        jd_ut1 = utc_to_ut1(chart.jd_ut)
        jd_tt = utc_to_tt(chart.jd_ut)
    else:
        jd_ut1 = chart.jd_ut
        jd_tt = chart_jd_tt
    dpsi, _ = nutation(jd_tt)
    obliquity = true_obliquity(jd_tt)
    gmst_deg = apparent_sidereal_time(jd_ut1, dpsi, obliquity)

    planet_ra_dec: dict[str, tuple[float, float]] = {}
    for body in bodies:
        position = planet_at(body, jd_ut1, jd_tt=jd_tt)
        right_ascension, declination = ecliptic_to_equatorial(
            position.longitude,
            position.latitude,
            obliquity,
        )
        planet_ra_dec[body] = (right_ascension, declination)

    return subplanetary_points(planet_ra_dec, gmst_deg)
