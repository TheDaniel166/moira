"""Inverse geographic loci of fixed zodiacal degrees on Geodetic angles.

The horizon equation is evaluated for ecliptic latitude zero. These are
longitude contacts, not physical horizon tracks of off-ecliptic bodies.
"""

from __future__ import annotations

import math
import heapq
from dataclasses import dataclass
from collections.abc import Sequence

from .geodetic import _circular_delta, _normalize_angle, geodetic_geometry, geodetic_mc
from .geodetic_inputs import GeodeticBodySnapshot

__all__ = [
    "GeodeticCurvePolicy", "GeodeticCurveVertex", "GeodeticCurveExclusion",
    "GeodeticAngularLocus", "GeodeticLociResult", "geodetic_angular_loci",
]


@dataclass(frozen=True, slots=True)
class GeodeticCurvePolicy:
    """Latitude sampling and finite evaluation budget for analytic curves."""

    latitude_step_deg: float = 2.0
    max_evaluations: int = 20000
    round_trip_tolerance_deg: float = 1e-7

    def __post_init__(self):
        if not math.isfinite(self.latitude_step_deg) or not 0 < self.latitude_step_deg <= 30:
            raise ValueError("latitude_step_deg must be in (0, 30]")
        if isinstance(self.max_evaluations, bool) or not isinstance(self.max_evaluations, int) or self.max_evaluations < 1:
            raise ValueError("max_evaluations must be a positive integer")
        if not math.isfinite(self.round_trip_tolerance_deg) or self.round_trip_tolerance_deg <= 0:
            raise ValueError("round_trip_tolerance_deg must be positive")


@dataclass(frozen=True, slots=True)
class GeodeticCurveVertex:
    """Geographic coordinates and forward angular residual for one sample."""

    latitude_deg: float
    longitude_deg: float
    residual_deg: float
    rising_rate: float | None
    boundary: str | None = None


@dataclass(frozen=True, slots=True)
class GeodeticCurveExclusion:
    """A sampled latitude where this requested branch cannot be retained."""

    latitude_deg: float
    reason: str


@dataclass(frozen=True, slots=True)
class GeodeticAngularLocus:
    """Analytic target and segmented sampled geometry for one body/angle."""

    body_id: str
    angle: str
    tropical_target_deg: float
    selected_target_deg: float
    right_ascension_deg: float
    declination_deg: float
    segments: tuple[tuple[GeodeticCurveVertex, ...], ...]
    exclusions: tuple[GeodeticCurveExclusion, ...]
    analytic_definition: str
    complete: bool


@dataclass(frozen=True, slots=True)
class GeodeticLociResult:
    """Common fixed target provenance, bounded work, and inverse loci."""

    snapshot: GeodeticBodySnapshot
    obliquity_deg: float
    policy: GeodeticCurvePolicy
    loci: tuple[GeodeticAngularLocus, ...]
    evaluations: int
    complete: bool
    semantics: str = "zodiacal_degree_ecliptic_latitude_zero_not_body_horizon"
    interpolation: str = "analytic_locus_with_sampled_vertices_not_linear_truth"


def _wrap(value):
    result = (_normalize_angle(value) + 180.0) % 360.0 - 180.0
    return 0.0 if result == 0.0 else result


def geodetic_angular_loci(
    snapshot: GeodeticBodySnapshot, *, obliquity: float,
    angles: Sequence[str] = ("MC", "IC", "ASC", "DSC"),
    policy: GeodeticCurvePolicy | None = None,
) -> GeodeticLociResult:
    """Invert the spherical horizon equation and validate the forward branch.

    ``cos(H) = -tan(phi) tan(delta)`` with H negative for rising and
    positive for setting. ARMC=RA+H is converted back to tropical MC.
    Meridians remain available where a local Ascendant is undefined.
    Equinox targets are solved directly, without division by sin(delta).
    """
    if not isinstance(snapshot, GeodeticBodySnapshot):
        raise TypeError("snapshot must be GeodeticBodySnapshot")
    if not math.isfinite(obliquity) or not 22 <= obliquity <= 25:
        raise ValueError("obliquity must be in [22, 25]")
    if isinstance(angles, str) or not angles or len(set(angles)) != len(angles) or any(a not in ("MC", "IC", "ASC", "DSC") for a in angles):
        raise ValueError("select unique MC, IC, ASC, DSC angles")
    active = GeodeticCurvePolicy() if policy is None else policy
    if not isinstance(active, GeodeticCurvePolicy):
        raise TypeError("policy must be GeodeticCurvePolicy")
    eps = math.radians(obliquity)
    evaluations = 0
    exhausted = False
    loci = []
    for body in snapshot.positions:
        lam = math.radians(body.tropical_longitude_deg)
        ra = math.atan2(math.sin(lam) * math.cos(eps), math.cos(lam))
        dec = math.asin(math.sin(eps) * math.sin(lam))
        for angle in angles:
            segments, exclusions = [], []
            locus_complete = True
            if angle in ("MC", "IC"):
                if evaluations + 2 > active.max_evaluations:
                    exhausted = True
                else:
                    longitude = _wrap(body.tropical_longitude_deg + (180 if angle == "IC" else 0))
                    segments.append(tuple(GeodeticCurveVertex(lat, longitude, 0.0, None, "pole") for lat in (-90.0, 90.0)))
                    evaluations += 2
                definition = "longitude=wrap(tropical_target - angle_offset); all latitudes"
            else:
                limits = (-90.0, 90.0, -(90 - obliquity), 90 - obliquity,
                          -(90 - abs(math.degrees(dec))), 90 - abs(math.degrees(dec)))
                ratio = 180 / active.latitude_step_deg
                if math.isfinite(ratio) and ratio <= active.max_evaluations:
                    n = math.ceil(ratio)
                    # Keep the admitted grid lazy. A grid denser than the
                    # whole budget is refused above, including steps too tiny
                    # to advance a representable geographic latitude.
                    latitudes = heapq.merge((-90 + i * 180 / n for i in range(n + 1)), sorted(set(limits)))
                else:
                    latitudes = ()
                    exhausted = True
                    exclusions.append(GeodeticCurveExclusion(-90.0, "evaluation_budget_exhausted"))
                cache = {}

                def vertex(latitude):
                    nonlocal evaluations, exhausted
                    if latitude in cache:
                        return cache[latitude]
                    if evaluations >= active.max_evaluations:
                        exhausted = True
                        return None, "evaluation_budget_exhausted"
                    evaluations += 1
                    if abs(latitude) >= 90 - 1e-6:
                        result = (None, "pole_nonunique")
                    else:
                        c = -math.tan(math.radians(latitude)) * math.tan(dec)
                        if abs(c) > 1 + 1e-13:
                            result = (None, "circumpolar_no_solution")
                        elif abs(c) >= 1 - 1e-13:
                            result = (None, "zero_rising_rate_endpoint")
                        else:
                            h = math.acos(c) * (-1 if angle == "ASC" else 1)
                            a = ra + h
                            longitude = _wrap(math.degrees(math.atan2(math.sin(a), math.cos(a) * math.cos(eps))))
                            geometry = geodetic_geometry(longitude, latitude, obliquity)
                            if geometry.asc_deg is None:
                                result = (None, geometry.status)
                            else:
                                forward = geodetic_mc(geometry.asc_deg, -180 if angle == "DSC" else 0)
                                residual = abs(_circular_delta(forward, body.tropical_longitude_deg))
                                rate = -math.cos(math.radians(latitude)) * math.cos(dec) * math.sin(h)
                                if residual > active.round_trip_tolerance_deg or (rate <= 0 if angle == "ASC" else rate >= 0):
                                    result = (None, "forward_branch_mismatch")
                                else:
                                    result = (GeodeticCurveVertex(latitude, longitude, residual, rate), None)
                    cache[latitude] = result
                    return result

                current = []
                previous_latitude = None
                for latitude in latitudes:
                    if latitude == previous_latitude:
                        continue
                    previous_latitude = latitude
                    point, reason = vertex(latitude)
                    if point is None:
                        if current:
                            segments.append(tuple(current))
                            current = []
                        exclusions.append(GeodeticCurveExclusion(latitude, reason))
                        if exhausted:
                            break
                        continue
                    if current and abs(point.longitude_deg - current[-1].longitude_deg) > 180:
                        # Refine an actual antimeridian crossing on the analytic
                        # curve; never draw a straight chord across the map seam.
                        left, right = current[-1], point
                        seam = 180.0 if left.longitude_deg > 0 else -180.0
                        for _ in range(48):
                            middle, why = vertex((left.latitude_deg + right.latitude_deg) / 2)
                            if middle is None:
                                break
                            if (middle.longitude_deg > 0) == (left.longitude_deg > 0):
                                left = middle
                            else:
                                right = middle
                            if abs(right.latitude_deg - left.latitude_deg) < 1e-10:
                                break
                        if middle is not None and not exhausted and evaluations < active.max_evaluations:
                            seam_lat = (left.latitude_deg + right.latitude_deg) / 2
                            evaluations += 1
                            witness = geodetic_geometry(seam, seam_lat, obliquity)
                            forward = geodetic_mc(witness.asc_deg, -180 if angle == "DSC" else 0) if witness.asc_deg is not None else math.nan
                            residual = abs(_circular_delta(forward, body.tropical_longitude_deg)) if math.isfinite(forward) else math.inf
                            if residual <= active.round_trip_tolerance_deg:
                                current.append(GeodeticCurveVertex(seam_lat, seam, residual, middle.rising_rate, "antimeridian"))
                                segments.append(tuple(current))
                                current = [GeodeticCurveVertex(seam_lat, -seam, residual, middle.rising_rate, "antimeridian")]
                            else:
                                segments.append(tuple(current))
                                current = []
                                exclusions.append(GeodeticCurveExclusion(seam_lat, "seam_refinement_unresolved"))
                                locus_complete = False
                        else:
                            segments.append(tuple(current))
                            current = []
                            locus_complete = False
                            if evaluations >= active.max_evaluations:
                                exhausted = True
                    current.append(point)
                if current:
                    segments.append(tuple(current))
                definition = "cos(H)=-tan(latitude)*tan(declination); ARMC=RA+H; rising H<0, setting H>0"
            loci.append(GeodeticAngularLocus(body.body_id, angle, body.tropical_longitude_deg,
                                           body.selected_longitude_deg, _normalize_angle(math.degrees(ra)), math.degrees(dec),
                                           tuple(segments), tuple(exclusions), definition, not exhausted and locus_complete))
    return GeodeticLociResult(snapshot, obliquity, active, tuple(loci), evaluations,
                              not exhausted and snapshot.complete and all(locus.complete for locus in loci))
