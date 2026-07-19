"""
Official lunar limb and topography support for profile-aware graze work.

This module binds authoritative external sources rather than inventing a local
profile model:

- NAIF/SPICE lunar orientation kernels
- USGS Astrogeology / LOLA cloud-optimized point-cloud tiles

The contact-facing implementation solves the finite-distance tangent locus for
a sky-plane position angle, samples official LOLA topography around that locus,
and records a perspective-equivalent angular-radius profile. The older
single-point adjustment helper remains a separate compatibility product.

Boundary
--------
Owns:
    - official-kernel cache and loading
    - official LOLA tile lookup, download, cache, and sampling
    - position-angle to selenographic limb-point projection
    - profile correction in angular degrees for occultation work

Delegates:
    - nominal topocentric occultation geometry to moira.occultations
    - topographic contact chronology to moira.lunar_occultation_contacts

Import-time side effects: none
"""

from __future__ import annotations

import math
import os
import json
import hashlib
import errno
import time
from bisect import bisect_left
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import RLock
from tempfile import NamedTemporaryFile

_requests_exc = None
try:
    import requests
    _HAS_REQUESTS = True
except ImportError as exc:
    requests = None
    _HAS_REQUESTS = False
    _requests_exc = exc
_laspy_exc = None
try:
    import laspy
    from laspy.copc import Bounds, CopcReader, load_octree_for_query
    _HAS_LASPY = True
except ImportError as exc:
    laspy = None
    Bounds = None
    CopcReader = None
    load_octree_for_query = None
    _HAS_LASPY = False
    _laspy_exc = exc

_spiceypy_exc = None
try:
    import spiceypy as sp
    _HAS_SPICEYPY = True
except ImportError as exc:
    sp = None
    _HAS_SPICEYPY = False
    _spiceypy_exc = exc

from .constants import MOON_RADIUS_KM
from ._ephemeris_time import _reader_identity_at, _ut1_to_ephemeris_tt
from .julian import J2000, _ut1_to_utc, tt_to_tdb
from .spk_reader import KernelReader
try:
    from . import moira_native
except ImportError:
    moira_native = None

from typing import Mapping, Sequence

__all__ = [
    "MAX_LUNAR_LIMB_EVENT_PROFILE_SLICES",
    "LunarLimbAssetIdentity",
    "LunarLimbEventProfile",
    "LunarLimbProfileCoverageError",
    "LunarLimbProfileError",
    "LunarLimbProfileSlice",
    "LunarLimbProfileSource",
    "LunarLimbResourceError",
    "build_lola_rdr_lunar_limb_event_profile",
    "official_lunar_limb_profile_adjustment",
]


# NASA/LRO reports the measured lunar high point as 10.786 km above the
# 1,737.4 km mean radius.  NASA's broader LOLA summary describes the lunar
# topographic scale as approximately -10 km through +10 km.  Those are source
# observations, not Moira's acquisition bound:
#
# https://science.nasa.gov/photojournal/highest-point-on-the-moon/
# https://science.nasa.gov/solar-system/moon/10-cool-things-nasas-lunar-reconnaissance-orbiter-is-teaching-us-about-the-moon/
_NASA_LRO_HIGHEST_POINT_KM = 10.786
_NASA_LOLA_APPROXIMATE_ABSOLUTE_RELIEF_KM = 10.0
_NASA_LRO_HIGHEST_POINT_URL = (
    "https://science.nasa.gov/photojournal/highest-point-on-the-moon/"
)
_NASA_LOLA_TOPOGRAPHY_SCALE_URL = (
    "https://science.nasa.gov/solar-system/moon/"
    "10-cool-things-nasas-lunar-reconnaissance-orbiter-is-teaching-us-about-the-moon/"
)

# Moira conservatively admits a continuous lunar radial surface within
# |r - R| <= 12 km.  This is an engine acquisition policy, deliberately wider
# than the NASA/LRO observations above; it is not attributed to NASA.
_LOLA_MAX_ABSOLUTE_RELIEF_KM = 12.0
_LOLA_RELIEF_ACQUISITION_POLICY_ID = (
    "MOIRA_CONTINUOUS_RADIAL_SURFACE_ABSOLUTE_RELIEF_12_KM_V1"
)
_LOLA_INNER_RELIEF_RADIUS_KM = MOON_RADIUS_KM - _LOLA_MAX_ABSOLUTE_RELIEF_KM
_LOLA_OUTER_RELIEF_RADIUS_KM = MOON_RADIUS_KM + _LOLA_MAX_ABSOLUTE_RELIEF_KM

# A summit on the outer admitted shell can compete with the mean reference
# limb over this central-angle guard.  Its same-PA Euclidean displacement from
# the mean-radius tangent site is the corresponding law-of-cosines chord.
_LOLA_MEAN_LIMB_CENTRAL_GUARD_RAD = math.acos(
    MOON_RADIUS_KM / _LOLA_OUTER_RELIEF_RADIUS_KM
)
_LOLA_MEAN_LIMB_CENTRAL_GUARD_DEG = math.degrees(
    _LOLA_MEAN_LIMB_CENTRAL_GUARD_RAD
)
_LOLA_MEAN_LIMB_CHORD_MARGIN_KM = math.sqrt(
    _LOLA_OUTER_RELIEF_RADIUS_KM**2 - MOON_RADIUS_KM**2
)
_LOLA_RELIEF_BOUND_TOLERANCE_KM = 1.0e-6

# Explicit resource/work ceilings.  The 2024 IOTA Spica witness resolves 16
# tiles by 16 slices; its largest COPC node upper bound is 28,116,911 points,
# the cumulative node upper bound is 302,308,085, and the corresponding
# projection-work upper bound is 4,836,929,360 point visits.  The per-tile cap
# is the smallest measured-safe whole-million ceiling; cumulative ceilings add
# at least 25 percent margin while failing before an accidental global decode
# or unbounded repeated projection.
MAX_LUNAR_LIMB_EVENT_PROFILE_SLICES = 4_096
_MAX_CONTACT_LOLA_TILES = 96
_MAX_CONTACT_LOLA_POINTS_PER_TILE = 32_000_000
_MAX_CONTACT_LOLA_NODE_POINTS_TOTAL = 384_000_000
_MAX_CONTACT_LOLA_TILE_PROJECTIONS = 320
_MAX_CONTACT_LOLA_POINT_PROJECTION_WORK = 6_100_000_000


class LunarLimbProfileError(RuntimeError):
    """Base error for an admitted lunar topography profile product."""


class LunarLimbProfileCoverageError(LunarLimbProfileError):
    """The immutable profile does not cover a requested epoch or limb angle."""


class LunarLimbResourceError(LunarLimbProfileError):
    """An authoritative lunar-limb resource could not be admitted safely."""


class _NoLolaTileError(FileNotFoundError):
    """Private sentinel for an authoritative STAC query with no matching tile."""


def _finite_float(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    admitted = float(value)
    if not math.isfinite(admitted):
        raise ValueError(f"{name} must be finite")
    return admitted


def _nonempty_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _same_float(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)


@dataclass(frozen=True, slots=True)
class LunarLimbAssetIdentity:
    """Immutable byte identity for one admitted profile resource."""

    url: str
    byte_length: int
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", _nonempty_text("url", self.url))
        if isinstance(self.byte_length, bool) or not isinstance(self.byte_length, int):
            raise TypeError("byte_length must be int")
        if self.byte_length <= 0:
            raise ValueError("byte_length must be positive")
        digest = _nonempty_text("sha256", self.sha256).lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("sha256 must be a 64-character hexadecimal digest")
        object.__setattr__(self, "sha256", digest)


def _unwrap_position_angle_for_coverage(
    position_angle_deg: float,
    lower_unwrapped_deg: float,
    upper_unwrapped_deg: float,
) -> float:
    """Map a circular PA onto one unique, sub-360-degree coverage interval."""

    pa = _finite_float("position_angle_deg", position_angle_deg) % 360.0
    midpoint = (lower_unwrapped_deg + upper_unwrapped_deg) / 2.0
    nearest = pa + 360.0 * round((midpoint - pa) / 360.0)
    candidates = (nearest - 360.0, nearest, nearest + 360.0)
    covered = tuple(
        candidate
        for candidate in candidates
        if lower_unwrapped_deg - 1e-12 <= candidate <= upper_unwrapped_deg + 1e-12
    )
    if not covered:
        raise LunarLimbProfileCoverageError(
            f"position angle {position_angle_deg!r} deg is outside profile coverage "
            f"[{lower_unwrapped_deg}, {upper_unwrapped_deg}] deg (unwrapped)"
        )
    return min(covered, key=lambda candidate: abs(candidate - midpoint))


@dataclass(frozen=True, slots=True)
class LunarLimbProfileSource:
    """Immutable provenance for a topographic lunar-limb event profile.

    ``spatial_query_bounds_moon_xyz_km`` is the governing rectangular COPC
    envelope. ``spatial_query_half_width_km`` is only its maximum half-extent,
    retained as a compact compatibility summary; it does not describe a cube.
    The observed relief fields remain source evidence, while
    ``max_absolute_relief_km`` belongs to the named Moira acquisition policy.
    """

    authority: str
    collection: str
    coordinate_frame: str
    translation_model: str
    orientation_model: str
    surface_frame_model: str
    orientation_alignment_max_m: float
    orientation_alignment_interval: str
    reference_radius_km: float
    spatial_query_half_width_km: float
    spatial_query_bounds_moon_xyz_km: tuple[
        tuple[float, float, float],
        tuple[float, float, float],
    ]
    relief_observation_sources: tuple[str, ...]
    relief_observed_highest_km: float
    relief_observed_approximate_absolute_km: float
    relief_acquisition_policy: str
    max_absolute_relief_km: float
    assets: tuple[LunarLimbAssetIdentity, ...]
    time_scale: str = "UT1"
    silhouette_model: str = (
        "PERSPECTIVE_EQUIVALENT_HALF_OPEN_PA_BIN_MAXIMUM_"
        "CENTER_SAMPLE_LINEAR_RECONSTRUCTION"
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "authority", _nonempty_text("authority", self.authority))
        object.__setattr__(self, "collection", _nonempty_text("collection", self.collection))
        object.__setattr__(
            self,
            "coordinate_frame",
            _nonempty_text("coordinate_frame", self.coordinate_frame),
        )
        object.__setattr__(
            self,
            "translation_model",
            _nonempty_text("translation_model", self.translation_model),
        )
        object.__setattr__(
            self,
            "orientation_model",
            _nonempty_text("orientation_model", self.orientation_model),
        )
        object.__setattr__(
            self,
            "surface_frame_model",
            _nonempty_text("surface_frame_model", self.surface_frame_model),
        )
        alignment = _finite_float(
            "orientation_alignment_max_m", self.orientation_alignment_max_m
        )
        if alignment < 0.0:
            raise ValueError("orientation_alignment_max_m cannot be negative")
        object.__setattr__(self, "orientation_alignment_max_m", alignment)
        object.__setattr__(
            self,
            "orientation_alignment_interval",
            _nonempty_text(
                "orientation_alignment_interval",
                self.orientation_alignment_interval,
            ),
        )
        radius = _finite_float("reference_radius_km", self.reference_radius_km)
        if radius <= 0.0:
            raise ValueError("reference_radius_km must be positive")
        object.__setattr__(self, "reference_radius_km", radius)
        query_width = _finite_float(
            "spatial_query_half_width_km", self.spatial_query_half_width_km
        )
        if query_width <= 0.0:
            raise ValueError("spatial_query_half_width_km must be positive")
        object.__setattr__(self, "spatial_query_half_width_km", query_width)

        try:
            raw_minimum, raw_maximum = self.spatial_query_bounds_moon_xyz_km
            if len(raw_minimum) != 3 or len(raw_maximum) != 3:
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "spatial_query_bounds_moon_xyz_km must contain two XYZ triples"
            ) from exc
        minimum = tuple(
            _finite_float("spatial_query_bounds_moon_xyz_km minimum", value)
            for value in raw_minimum
        )
        maximum = tuple(
            _finite_float("spatial_query_bounds_moon_xyz_km maximum", value)
            for value in raw_maximum
        )
        if any(upper <= lower for lower, upper in zip(minimum, maximum)):
            raise ValueError(
                "spatial_query_bounds_moon_xyz_km maximum must exceed minimum "
                "on every axis"
            )
        maximum_half_extent = max(
            (upper - lower) / 2.0
            for lower, upper in zip(minimum, maximum)
        )
        if not math.isclose(
            query_width,
            maximum_half_extent,
            rel_tol=0.0,
            abs_tol=1.0e-9,
        ):
            raise ValueError(
                "spatial_query_half_width_km must equal the maximum half-extent "
                "of spatial_query_bounds_moon_xyz_km"
            )
        object.__setattr__(
            self,
            "spatial_query_bounds_moon_xyz_km",
            (minimum, maximum),
        )

        if isinstance(self.relief_observation_sources, str):
            raise TypeError("relief_observation_sources must be a sequence of identities")
        observation_sources = tuple(
            _nonempty_text("relief_observation_source", value)
            for value in self.relief_observation_sources
        )
        if not observation_sources or len(set(observation_sources)) != len(
            observation_sources
        ):
            raise ValueError(
                "relief_observation_sources must contain unique source identities"
            )
        object.__setattr__(
            self,
            "relief_observation_sources",
            observation_sources,
        )
        observed_highest = _finite_float(
            "relief_observed_highest_km", self.relief_observed_highest_km
        )
        observed_approximate = _finite_float(
            "relief_observed_approximate_absolute_km",
            self.relief_observed_approximate_absolute_km,
        )
        relief_bound = _finite_float(
            "max_absolute_relief_km", self.max_absolute_relief_km
        )
        if observed_highest < 0.0 or observed_approximate < 0.0:
            raise ValueError("observed relief values cannot be negative")
        if relief_bound <= 0.0:
            raise ValueError("max_absolute_relief_km must be positive")
        if relief_bound < max(observed_highest, observed_approximate):
            raise ValueError(
                "max_absolute_relief_km cannot be narrower than its cited "
                "relief observations"
            )
        object.__setattr__(self, "relief_observed_highest_km", observed_highest)
        object.__setattr__(
            self,
            "relief_observed_approximate_absolute_km",
            observed_approximate,
        )
        object.__setattr__(
            self,
            "relief_acquisition_policy",
            _nonempty_text(
                "relief_acquisition_policy", self.relief_acquisition_policy
            ),
        )
        object.__setattr__(self, "max_absolute_relief_km", relief_bound)

        assets = tuple(self.assets)
        if not assets or any(not isinstance(item, LunarLimbAssetIdentity) for item in assets):
            raise ValueError("assets must contain at least one LunarLimbAssetIdentity")
        if len({item.url for item in assets}) != len(assets):
            raise ValueError("profile asset URLs must be unique")
        object.__setattr__(self, "assets", assets)

        if self.time_scale != "UT1":
            raise ValueError("lunar-limb event profile epochs must be declared in UT1")
        if self.silhouette_model != (
            "PERSPECTIVE_EQUIVALENT_HALF_OPEN_PA_BIN_MAXIMUM_"
            "CENTER_SAMPLE_LINEAR_RECONSTRUCTION"
        ):
            raise ValueError("unsupported lunar-limb silhouette model")

    @property
    def asset_urls(self) -> tuple[str, ...]:
        return tuple(item.url for item in self.assets)


@dataclass(frozen=True, slots=True)
class LunarLimbProfileSlice:
    """One immutable finite-resolution lunar-limb profile at a UT1 epoch.

    ``position_angles_unwrapped_deg`` are bin centres on a strictly increasing
    unwrapped axis.  The corresponding radii are independent radial maxima in
    explicit half-open PA bins. They are center samples of a declared linear
    reconstruction, not exact radii at every source point inside a bin.
    Interpolation is linear only between admitted neighbouring samples whose
    separation does not exceed the declared gap. Consequently the product
    resolves depressions and summits only at its admitted bin scale; it makes
    no claim about sub-bin topography.
    """

    jd_ut1: float
    position_angles_unwrapped_deg: tuple[float, ...]
    radii_km: tuple[float, ...]
    bin_width_deg: float
    max_interpolation_gap_deg: float
    source_point_count: int
    asset_urls: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "jd_ut1", _finite_float("jd_ut1", self.jd_ut1))
        angles = tuple(
            _finite_float("position_angle_unwrapped_deg", value)
            for value in self.position_angles_unwrapped_deg
        )
        radii = tuple(_finite_float("radius_km", value) for value in self.radii_km)
        if len(angles) != len(radii):
            raise ValueError("position-angle and radius samples must have equal length")
        if len(angles) < 2:
            raise ValueError("a lunar-limb profile slice requires at least two samples")
        if any(right <= left for left, right in zip(angles, angles[1:])):
            raise ValueError("unwrapped position-angle samples must be strictly increasing")
        if angles[-1] - angles[0] >= 360.0:
            raise ValueError("one profile slice must cover less than 360 degrees")
        if any(radius <= 0.0 for radius in radii):
            raise ValueError("lunar-limb radii must be positive")
        object.__setattr__(self, "position_angles_unwrapped_deg", angles)
        object.__setattr__(self, "radii_km", radii)

        bin_width = _finite_float("bin_width_deg", self.bin_width_deg)
        max_gap = _finite_float(
            "max_interpolation_gap_deg", self.max_interpolation_gap_deg
        )
        if bin_width <= 0.0 or bin_width >= 360.0:
            raise ValueError("bin_width_deg must be in (0, 360)")
        if max_gap <= 0.0 or max_gap >= 360.0:
            raise ValueError("max_interpolation_gap_deg must be in (0, 360)")
        object.__setattr__(self, "bin_width_deg", bin_width)
        object.__setattr__(self, "max_interpolation_gap_deg", max_gap)

        if isinstance(self.source_point_count, bool) or not isinstance(
            self.source_point_count, int
        ):
            raise TypeError("source_point_count must be an integer")
        if self.source_point_count < len(angles):
            raise ValueError("source_point_count cannot be smaller than the bin sample count")
        urls = tuple(_nonempty_text("asset_url", url) for url in self.asset_urls)
        if not urls:
            raise ValueError("a lunar-limb profile slice must retain its source assets")
        if len(set(urls)) != len(urls):
            raise ValueError("slice asset_urls must be unique")
        object.__setattr__(self, "asset_urls", urls)

    @property
    def position_angle_start_unwrapped_deg(self) -> float:
        return self.position_angles_unwrapped_deg[0]

    @property
    def position_angle_end_unwrapped_deg(self) -> float:
        return self.position_angles_unwrapped_deg[-1]

    def radius_km_at(self, position_angle_deg: float) -> float:
        """Evaluate the admitted center-sample linear profile without I/O."""

        angles = self.position_angles_unwrapped_deg
        pa = _unwrap_position_angle_for_coverage(
            position_angle_deg,
            angles[0],
            angles[-1],
        )
        index = bisect_left(angles, pa)
        if index < len(angles) and _same_float(angles[index], pa):
            return self.radii_km[index]
        if index > 0 and _same_float(angles[index - 1], pa):
            return self.radii_km[index - 1]
        if index == 0 or index == len(angles):
            raise LunarLimbProfileCoverageError(
                f"position angle {position_angle_deg!r} deg is outside sampled profile coverage"
            )

        left_pa = angles[index - 1]
        right_pa = angles[index]
        gap = right_pa - left_pa
        if gap > self.max_interpolation_gap_deg + 1e-12:
            raise LunarLimbProfileCoverageError(
                f"position-angle sample gap {gap} deg exceeds admitted "
                f"{self.max_interpolation_gap_deg} deg"
            )
        fraction = (pa - left_pa) / gap
        return self.radii_km[index - 1] + fraction * (
            self.radii_km[index] - self.radii_km[index - 1]
        )


@dataclass(frozen=True, slots=True)
class LunarLimbEventProfile:
    """Immutable time sequence of finite-resolution lunar-limb slices."""

    source: LunarLimbProfileSource
    slices: tuple[LunarLimbProfileSlice, ...]
    max_time_interpolation_gap_days: float
    observer_latitude_deg: float
    observer_longitude_deg: float
    observer_elevation_m: float

    def __post_init__(self) -> None:
        if not isinstance(self.source, LunarLimbProfileSource):
            raise TypeError("source must be a LunarLimbProfileSource")
        if not math.isclose(
            self.source.reference_radius_km,
            MOON_RADIUS_KM,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise ValueError(
                "lunar-limb event profiles must use Moira's canonical "
                f"{MOON_RADIUS_KM} km lunar reference radius"
            )
        slices = tuple(self.slices)
        if not slices:
            raise ValueError("a lunar-limb event profile requires at least one slice")
        if not all(isinstance(item, LunarLimbProfileSlice) for item in slices):
            raise TypeError("slices must contain only LunarLimbProfileSlice values")
        if any(right.jd_ut1 <= left.jd_ut1 for left, right in zip(slices, slices[1:])):
            raise ValueError("lunar-limb profile slice epochs must be strictly increasing")
        source_assets = set(self.source.asset_urls)
        minimum_radius = (
            self.source.reference_radius_km - self.source.max_absolute_relief_km
        )
        maximum_radius = (
            self.source.reference_radius_km + self.source.max_absolute_relief_km
        )
        for item in slices:
            if not set(item.asset_urls).issubset(source_assets):
                raise ValueError("slice asset provenance is absent from the profile source")
            if any(
                radius
                < minimum_radius - _LOLA_RELIEF_BOUND_TOLERANCE_KM
                or radius
                > maximum_radius + _LOLA_RELIEF_BOUND_TOLERANCE_KM
                for radius in item.radii_km
            ):
                raise ValueError(
                    "realized lunar-limb radii must remain inside the "
                    "source-declared absolute-relief shell"
                )
        object.__setattr__(self, "slices", slices)

        max_gap = _finite_float(
            "max_time_interpolation_gap_days",
            self.max_time_interpolation_gap_days,
        )
        if max_gap < 0.0:
            raise ValueError("max_time_interpolation_gap_days cannot be negative")
        if len(slices) > 1 and max_gap == 0.0:
            raise ValueError("multi-slice profiles require a positive time interpolation gap")
        object.__setattr__(self, "max_time_interpolation_gap_days", max_gap)
        latitude = _finite_float("observer_latitude_deg", self.observer_latitude_deg)
        longitude = _finite_float("observer_longitude_deg", self.observer_longitude_deg)
        elevation = _finite_float("observer_elevation_m", self.observer_elevation_m)
        if not -90.0 <= latitude <= 90.0:
            raise ValueError("observer_latitude_deg must be in [-90, 90]")
        if not -180.0 <= longitude <= 180.0:
            raise ValueError("observer_longitude_deg must be in [-180, 180]")
        object.__setattr__(self, "observer_latitude_deg", latitude)
        object.__setattr__(self, "observer_longitude_deg", longitude)
        object.__setattr__(self, "observer_elevation_m", elevation)

    @property
    def jd_ut1_start(self) -> float:
        return self.slices[0].jd_ut1

    @property
    def jd_ut1_end(self) -> float:
        return self.slices[-1].jd_ut1

    def radius_km_at(self, jd_ut1: float, position_angle_deg: float) -> float:
        """Evaluate PA and time interpolation from the frozen in-memory profile."""

        epoch = _finite_float("jd_ut1", jd_ut1)
        epochs = tuple(item.jd_ut1 for item in self.slices)
        index = bisect_left(epochs, epoch)
        if index < len(epochs) and _same_float(epochs[index], epoch):
            return self.slices[index].radius_km_at(position_angle_deg)
        if index > 0 and _same_float(epochs[index - 1], epoch):
            return self.slices[index - 1].radius_km_at(position_angle_deg)
        if index == 0 or index == len(epochs):
            raise LunarLimbProfileCoverageError(
                f"UT1 epoch {epoch} is outside profile coverage "
                f"[{epochs[0]}, {epochs[-1]}]"
            )

        left = self.slices[index - 1]
        right = self.slices[index]
        gap = right.jd_ut1 - left.jd_ut1
        if gap > self.max_time_interpolation_gap_days + 1e-12:
            raise LunarLimbProfileCoverageError(
                f"time sample gap {gap} days exceeds admitted "
                f"{self.max_time_interpolation_gap_days} days"
            )
        left_radius = left.radius_km_at(position_angle_deg)
        right_radius = right.radius_km_at(position_angle_deg)
        fraction = (epoch - left.jd_ut1) / gap
        return left_radius + fraction * (right_radius - left_radius)

    def elevation_m_at(self, jd_ut1: float, position_angle_deg: float) -> float:
        return (
            self.radius_km_at(jd_ut1, position_angle_deg)
            - self.source.reference_radius_km
        ) * 1000.0

    def angular_adjustment_deg_at(
        self,
        jd_ut1: float,
        position_angle_deg: float,
        moon_distance_km: float,
    ) -> float:
        distance = _finite_float("moon_distance_km", moon_distance_km)
        radius = self.radius_km_at(jd_ut1, position_angle_deg)
        if distance <= radius:
            raise ValueError("moon_distance_km must exceed the admitted lunar radius")
        base = math.degrees(math.asin(self.source.reference_radius_km / distance))
        adjusted = math.degrees(math.asin(radius / distance))
        return adjusted - base


def _require_lunar_extra() -> None:
    missing: list[str] = []
    causes: list[str] = []
    if not _HAS_SPICEYPY:
        missing.append("spiceypy")
        if _spiceypy_exc is not None:
            causes.append(f"spiceypy: {_spiceypy_exc}")
    if not _HAS_LASPY:
        missing.append("laspy[lazrs]")
        if _laspy_exc is not None:
            causes.append(f"laspy: {_laspy_exc}")
    if not _HAS_REQUESTS:
        missing.append("requests")
        if _requests_exc is not None:
            causes.append(f"requests: {_requests_exc}")
    if not missing:
        return

    detail = f" Missing dependencies: {', '.join(missing)}."
    if causes:
        detail += " Import errors: " + "; ".join(causes) + "."
    raise ImportError(
        "Official lunar limb / graze support requires the optional "
        "`moira-astro[lunar-graze]` extra." + detail
    )


def _require_spiceypy() -> None:
    if _HAS_SPICEYPY:
        return
    detail = "" if _spiceypy_exc is None else f" Import error: {_spiceypy_exc}."
    raise ImportError(
        "Lunar orientation computation requires `spiceypy` from the "
        "`moira-astro[lunar-graze]` extra." + detail
    )


def _require_laspy() -> None:
    if _HAS_LASPY:
        return
    detail = "" if _laspy_exc is None else f" Import error: {_laspy_exc}."
    raise ImportError(
        "LOLA point-cloud computation requires `laspy[lazrs]` from the "
        "`moira-astro[lunar-graze]` extra." + detail
    )


def _require_requests() -> None:
    if _HAS_REQUESTS:
        return
    detail = "" if _requests_exc is None else f" Import error: {_requests_exc}."
    raise ImportError(
        "Lunar resource acquisition requires `requests` from the "
        "`moira-astro[lunar-graze]` extra; fully cached computation does not."
        + detail
    )


_CACHE_LOCK = RLock()
_CACHE_LOCK_TIMEOUT_SECONDS = 30.0 * 60.0
_CACHE_LOCK_POLL_SECONDS = 0.1
_KERNELS_LOADED = False

_NAIF_KERNELS: dict[str, str] = {
    "naif0012.tls": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls",
    "pck00011.tpc": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc",
    "moon_pa_de440_200625.bpc": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de440_200625.bpc",
    "moon_assoc_me.tf": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_assoc_me.tf",
    "moon_de440_250416.tf": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_de440_250416.tf",
    "de440.bsp": "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440.bsp",
}
_NAIF_KERNEL_BYTE_IDENTITIES: dict[str, tuple[int, str]] = {
    "naif0012.tls": (
        5_257,
        "678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b",
    ),
    "pck00011.tpc": (
        131_226,
        "3dff7b1dbeceaa01f25467767d3fa25816051c85d162d1edf04acb310ee28bb1",
    ),
    "moon_pa_de440_200625.bpc": (
        12_863_488,
        "60cd55aa401ea2ea97360636f567554bfe4e37bb829f901b4460a455dfaf783f",
    ),
    "moon_assoc_me.tf": (
        8_468,
        "52c622043ce0447d575e59ee01642f1894921e68c10f934ceff065f362da6c1c",
    ),
    "moon_de440_250416.tf": (
        19_478,
        "a47c71e9c9f33796bdafb2c9d69a7ee447b6016ecad80f71cd6f3e479f9cf768",
    ),
    "de440.bsp": (
        119_799_808,
        "a4ce9bf9b3282becc9f4b2ac3cebe03a2ae7599981aabd7265fd8482fff7c4b5",
    ),
}
_CONTACT_ORIENTATION_KERNEL_NAMES = (
    "moon_pa_de440_200625.bpc",
    "moon_de440_250416.tf",
)
_CONTACT_ORIENTATION_FRAME = "MOON_ME_DE440_ME421"
_CONTACT_SURFACE_FRAME = "DE421 mean Earth/polar axis (ME) cartographic frame"
_CONTACT_FRAME_ALIGNMENT_MAX_M = 0.534
_CONTACT_FRAME_ALIGNMENT_INTERVAL = "2000-01-01 through 2040-01-01 TDB"
_LIGHT_SPEED_KM_S = 299_792.458

_STAC_SEARCH_URL = "https://stac.astrogeology.usgs.gov/api/search"
_LOLA_COLLECTION = "lunar_orbiter_laser_altimeter"
_LOLA_MEAN_RADIUS_M = MOON_RADIUS_KM * 1000.0
_LOLA_TILE_STEP_DEG = 15
_LOLA_TILE_DISCOVERY_STEP_DEG = 0.25
_LIMB_TILE_EXTENT = 1
_LIMB_PA_WINDOW_DEG = 10.0
_LIMB_BIN_WIDTH_DEG = 0.1
_NATIVE_LSK_MIN_JD_UTC = 2441317.5
_MIN_LOLA_QUERY_HALF_WIDTH_KM = 250.0
_MIN_CONTACT_QUERY_HALF_WIDTH_KM = 10.0
_DEFAULT_LOLA_QUERY_HALF_WIDTH_KM = 250.0
_DEFAULT_PROFILE_MAX_PA_GAP_FACTOR = 1.5
_LOLA_COORDINATE_WKT_TOKENS = (
    'GEODCRS["IAU_2015MoonXYZ"',
    'ELLIPSOID["Moon(2015)-Sphere",1737400,0,LENGTHUNIT["metre",1,ID["EPSG",9001]]]',
    "CS[Cartesian,3]",
    'AXIS["(X)",geocentricX,ORDER[1],LENGTHUNIT["metre",1]]',
    'AXIS["(Y)",geocentricY,ORDER[2],LENGTHUNIT["metre",1]]',
    'AXIS["(Z)",geocentricZ,ORDER[3],LENGTHUNIT["metre",1]]',
    'ID["IAU",30000,2015]',
)


def _stac_tile_cache_path(cache_root: Path) -> Path:
    return cache_root / "stac_tile_cache.json"


def _load_stac_tile_cache(cache_root: Path) -> dict[str, str]:
    cache_path = _stac_tile_cache_path(cache_root)
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _store_stac_tile_cache(cache_root: Path, cache: dict[str, str]) -> None:
    cache_path = _stac_tile_cache_path(cache_root)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with _interprocess_cache_lock(cache_path.with_suffix(".lock")):
        merged = _load_stac_tile_cache(cache_root)
        merged.update(cache)
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=cache_path.name + ".",
            suffix=".part",
            dir=cache_path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(merged, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(cache_path)


@dataclass(frozen=True, slots=True)
class _LolaTile:
    """One builder-owned LOLA point cloud in native substrate storage."""

    point_cloud: "moira_native.LolaPointCloud"
    decompression_point_upper_bound: int | None = None

    def __post_init__(self) -> None:
        upper_bound = self.decompression_point_upper_bound
        if upper_bound is not None and (
            isinstance(upper_bound, bool)
            or not isinstance(upper_bound, int)
            or upper_bound <= 0
        ):
            raise ValueError(
                "decompression_point_upper_bound must be a positive integer"
            )

    @property
    def point_count(self) -> int:
        return int(self.point_cloud.size())


@dataclass(frozen=True, slots=True)
class _LolaCartesianBounds:
    """One closed Moon-XYZ Cartesian acquisition envelope, in kilometres."""

    minimum_km: tuple[float, float, float]
    maximum_km: tuple[float, float, float]

    def __post_init__(self) -> None:
        minimum = tuple(
            _finite_float("LOLA Cartesian minimum", value)
            for value in self.minimum_km
        )
        maximum = tuple(
            _finite_float("LOLA Cartesian maximum", value)
            for value in self.maximum_km
        )
        if len(minimum) != 3 or len(maximum) != 3:
            raise ValueError("LOLA Cartesian bounds must contain XYZ triples")
        if any(upper <= lower for lower, upper in zip(minimum, maximum)):
            raise ValueError(
                "LOLA Cartesian maximum must exceed minimum on every axis"
            )
        object.__setattr__(self, "minimum_km", minimum)
        object.__setattr__(self, "maximum_km", maximum)

    @property
    def maximum_half_extent_km(self) -> float:
        return max(
            (upper - lower) / 2.0
            for lower, upper in zip(self.minimum_km, self.maximum_km)
        )

    def to_laspy_bounds(self) -> object:
        if Bounds is None:
            raise ImportError("laspy COPC bounds are unavailable")
        return Bounds(
            tuple(value * 1000.0 for value in self.minimum_km),
            tuple(value * 1000.0 for value in self.maximum_km),
        )


@dataclass(frozen=True, slots=True)
class _LolaSphericalCap:
    """A relief-capable surface-direction envelope around one tangent sample."""

    center_unit: tuple[float, float, float]
    center_lon_deg: float
    center_lat_deg: float
    angular_radius_rad: float

    def __post_init__(self) -> None:
        center = tuple(
            _finite_float("LOLA spherical-cap centre", value)
            for value in self.center_unit
        )
        if len(center) != 3 or not math.isclose(
            math.sqrt(sum(value * value for value in center)),
            1.0,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise ValueError("LOLA spherical-cap centre must be a unit XYZ vector")
        longitude = _finite_float("LOLA spherical-cap longitude", self.center_lon_deg)
        latitude = _finite_float("LOLA spherical-cap latitude", self.center_lat_deg)
        radius = _finite_float("LOLA spherical-cap radius", self.angular_radius_rad)
        if not -90.0 <= latitude <= 90.0:
            raise ValueError("LOLA spherical-cap latitude must be in [-90, 90]")
        if not 0.0 < radius < math.pi:
            raise ValueError("LOLA spherical-cap radius must be in (0, pi)")
        object.__setattr__(self, "center_unit", center)
        object.__setattr__(self, "center_lon_deg", _normalize_lon_deg(longitude))
        object.__setattr__(self, "center_lat_deg", latitude)
        object.__setattr__(self, "angular_radius_rad", radius)


@dataclass(frozen=True, slots=True)
class _ObserverLimbContext:
    """Vessel: Ephemeris and orientation context for a specific lunar-limb observer epoch."""
    subobserver_lon_deg: float
    subobserver_lat_deg: float
    observer_distance_km: float
    los_j2000: Sequence[float]
    observer_dir_moon: Sequence[float]
    sky_north_moon: Sequence[float]
    sky_east_moon: Sequence[float]


@dataclass(frozen=True, slots=True)
class _TopocentricMoonLightCone:
    """Reader-bound physical Moon-to-observer geometry at one reception epoch."""

    jd_tt_reception: float
    jd_tt_emission: float
    et_emission: float
    distance_km: float
    observer_ssb_icrf: tuple[float, float, float]
    observer_to_moon_icrf: tuple[float, float, float]
    icrf_to_true_of_date: tuple[tuple[float, float, float], ...]
    translation_label: str


def _default_cache_root() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "Moira" / "lunar_limb"
    return Path.home() / ".cache" / "moira" / "lunar_limb"


def _downloads_disabled() -> bool:
    return os.environ.get("MOIRA_NO_DOWNLOAD", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@contextmanager
def _interprocess_cache_lock(
    path: Path,
    *,
    timeout_seconds: float = _CACHE_LOCK_TIMEOUT_SECONDS,
    poll_interval_seconds: float = _CACHE_LOCK_POLL_SECONDS,
):
    """Serialize cache mutation across local workers without extra packages.

    Windows ``LK_LOCK`` retries only ten times at one-second intervals.  A
    lawful COPC download can take longer, so use non-blocking acquisition with
    Moira-owned polling and a bounded thirty-minute wait on every platform.
    OS locks are released automatically if their owning process exits.
    """

    timeout = _finite_float("timeout_seconds", timeout_seconds)
    poll_interval = _finite_float("poll_interval_seconds", poll_interval_seconds)
    if timeout <= 0.0:
        raise ValueError("timeout_seconds must be positive")
    if poll_interval <= 0.0:
        raise ValueError("poll_interval_seconds must be positive")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        deadline = time.monotonic() + timeout
        if os.name == "nt":
            import msvcrt

            while True:
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        raise
                    remaining = deadline - time.monotonic()
                    if remaining <= 0.0:
                        raise LunarLimbResourceError(
                            f"timed out after {timeout:g} seconds waiting for "
                            f"lunar-limb cache lock: {path}"
                        ) from exc
                    time.sleep(min(poll_interval, remaining))
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError as exc:
                    if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                        raise
                    remaining = deadline - time.monotonic()
                    if remaining <= 0.0:
                        raise LunarLimbResourceError(
                            f"timed out after {timeout:g} seconds waiting for "
                            f"lunar-limb cache lock: {path}"
                        ) from exc
                    time.sleep(min(poll_interval, remaining))
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_resource_bytes(
    path: Path,
    expected_identity: tuple[int, str] | None,
) -> None:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise LunarLimbResourceError(f"cannot stat lunar-limb resource: {path}") from exc
    if size <= 0:
        raise LunarLimbResourceError(f"lunar-limb resource is empty: {path}")
    if expected_identity is None:
        return
    expected_size, expected_sha256 = expected_identity
    if (
        isinstance(expected_size, bool)
        or not isinstance(expected_size, int)
        or expected_size <= 0
    ):
        raise ValueError("expected resource byte length must be a positive int")
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or any(character not in "0123456789abcdef" for character in expected_sha256)
    ):
        raise ValueError(
            "expected resource SHA-256 must be a lowercase hexadecimal digest"
        )
    if size != expected_size:
        raise LunarLimbResourceError(
            f"lunar-limb resource byte length mismatch for {path}: "
            f"expected {expected_size}, received {size}"
        )
    received_sha256 = _sha256_file(path)
    if received_sha256 != expected_sha256:
        raise LunarLimbResourceError(
            f"lunar-limb resource SHA-256 mismatch for {path}: "
            f"expected {expected_sha256}, received {received_sha256}"
        )


def _expected_lola_asset_map(
    assets: Sequence[LunarLimbAssetIdentity] | None,
) -> dict[str, LunarLimbAssetIdentity] | None:
    """Normalize an optional exact external-fixture tile identity set."""

    if assets is None:
        return None
    admitted: dict[str, LunarLimbAssetIdentity] = {}
    for asset in assets:
        if not isinstance(asset, LunarLimbAssetIdentity):
            raise TypeError(
                "expected_lola_assets must contain LunarLimbAssetIdentity values"
            )
        if asset.url in admitted:
            raise ValueError(
                f"expected_lola_assets contains duplicate URL {asset.url!r}"
            )
        admitted[asset.url] = asset
    return admitted


def _admit_expected_lola_tile_urls(
    resolved_urls: Sequence[str],
    expected_assets: Mapping[str, LunarLimbAssetIdentity] | None,
) -> None:
    """Fail before tile download/decode unless the fixture URL set is exact."""

    if expected_assets is None:
        return
    resolved = set(resolved_urls)
    expected = set(expected_assets)
    if resolved != expected:
        unexpected = tuple(sorted(resolved - expected))
        missing = tuple(sorted(expected - resolved))
        raise LunarLimbResourceError(
            "resolved LOLA tile URL set does not match the externally admitted "
            f"fixture identities: unexpected={unexpected!r}, missing={missing!r}"
        )


def _optional_resource_identity(
    expected_byte_length: int | None,
    expected_sha256: str | None,
) -> tuple[int, str] | None:
    if expected_byte_length is None and expected_sha256 is None:
        return None
    if expected_byte_length is None or expected_sha256 is None:
        raise ValueError(
            "expected byte length and SHA-256 must be supplied together"
        )
    return expected_byte_length, expected_sha256


def _asset_identity(url: str, path: Path) -> LunarLimbAssetIdentity:
    _validate_resource_bytes(path, None)
    return LunarLimbAssetIdentity(
        url=url,
        byte_length=path.stat().st_size,
        sha256=_sha256_file(path),
    )


def _download_file(
    url: str,
    dest: Path,
    *,
    expected_identity: tuple[int, str] | None = None,
) -> Path:
    if dest.exists():
        _validate_resource_bytes(dest, expected_identity)
        return dest
    if _downloads_disabled():
        raise LunarLimbResourceError(
            f"required lunar-limb resource is not cached and MOIRA_NO_DOWNLOAD is set: {dest}"
        )
    if not _HAS_REQUESTS:
        _require_requests()

    with _CACHE_LOCK, _interprocess_cache_lock(
        dest.with_name(dest.name + ".lock")
    ):
        if dest.exists():
            _validate_resource_bytes(dest, expected_identity)
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="wb",
                prefix=dest.name + ".",
                suffix=".part",
                dir=dest.parent,
                delete=False,
            ) as handle:
                tmp = Path(handle.name)
                with requests.get(url, stream=True, timeout=120) as response:
                    response.raise_for_status()
                    for chunk in response.iter_content(1024 * 1024):
                        if chunk:
                            handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            _validate_resource_bytes(tmp, expected_identity)
            tmp.replace(dest)
        except LunarLimbResourceError:
            if tmp is not None and tmp.exists():
                tmp.unlink()
            raise
        except Exception as exc:
            if tmp is not None and tmp.exists():
                tmp.unlink()
            raise LunarLimbResourceError(
                f"failed to download authoritative lunar-limb resource: {url}"
            ) from exc
        return dest


def _ensure_kernels_loaded(cache_root: Path) -> None:
    _require_spiceypy()
    global _KERNELS_LOADED
    if _KERNELS_LOADED:
        return
    with _CACHE_LOCK:
        if _KERNELS_LOADED:
            return
        kernels_dir = cache_root / "kernels"
        for filename, url in _NAIF_KERNELS.items():
            path = _download_file(
                url,
                kernels_dir / filename,
                expected_identity=_NAIF_KERNEL_BYTE_IDENTITIES[filename],
            )
            sp.furnsh(str(path))
            if filename == "naif0012.tls" and moira_native is not None and hasattr(moira_native, "load_naif_lsk"):
                moira_native.load_naif_lsk(str(path))
        _KERNELS_LOADED = True


def _ensure_contact_orientation_kernels_loaded(cache_root: Path) -> tuple[Path, ...]:
    """Load only the pinned lunar PCK/FK needed by DE441 contact profiles.

    Translation is deliberately absent from this SPICE kernel set.  The
    contact-facing line of sight comes from the caller's content-identified
    DE441/LE441 reader; SPICE owns only the explicitly named lunar orientation
    transform.
    """

    _require_spiceypy()
    paths: list[Path] = []
    kernels_dir = cache_root / "kernels"
    with _CACHE_LOCK:
        for filename in _CONTACT_ORIENTATION_KERNEL_NAMES:
            url = _NAIF_KERNELS[filename]
            path = _download_file(
                url,
                kernels_dir / filename,
                expected_identity=_NAIF_KERNEL_BYTE_IDENTITIES[filename],
            )
            try:
                sp.kinfo(str(path))
            except Exception:
                sp.furnsh(str(path))
            paths.append(path)
    return tuple(paths)


def _jd_utc_to_et(jd_utc: float) -> float:
    """
    Convert an explicitly UTC-coded Julian Day to SPICE ET.

    The native admitted regime begins at 1972-01-01 UTC, the first epoch
    explicitly covered by the loaded NAIF leap-second schedule. Earlier UTC
    epochs retain SPICE's LSK-backed text parser.
    """
    admitted_utc = _finite_float("jd_utc", jd_utc)
    if (
        moira_native is not None
        and hasattr(moira_native, "jd_utc_to_et_seconds_past_j2000")
        and admitted_utc >= _NATIVE_LSK_MIN_JD_UTC
    ):
        return float(moira_native.jd_utc_to_et_seconds_past_j2000(admitted_utc))
    _require_spiceypy()
    return sp.str2et(f"JD {admitted_utc}")


def _jd_ut_to_et(jd_ut: float) -> float:
    """Convert a Moira UT1 Julian Day to ET through the admitted UTC inverse.

    The private name remains for compatibility with the existing lunar-limb
    call sites, but its input is now truthfully UT1. It is never passed to
    SPICE as though it were already UTC.
    """

    admitted_ut1 = _finite_float("jd_ut", jd_ut)
    return _jd_utc_to_et(_ut1_to_utc(admitted_ut1))


def _normalize_lon_deg(lon_deg: float) -> float:
    return ((lon_deg + 180.0) % 360.0) - 180.0


def _lunar_surface_chord_km(
    first_lon_deg: float,
    first_lat_deg: float,
    second_lon_deg: float,
    second_lat_deg: float,
) -> float:
    """Return the reference-sphere chord between two lunar surface sites."""

    first_lon = math.radians(first_lon_deg)
    first_lat = math.radians(first_lat_deg)
    second_lon = math.radians(second_lon_deg)
    second_lat = math.radians(second_lat_deg)
    first = (
        math.cos(first_lat) * math.cos(first_lon),
        math.cos(first_lat) * math.sin(first_lon),
        math.sin(first_lat),
    )
    second = (
        math.cos(second_lat) * math.cos(second_lon),
        math.cos(second_lat) * math.sin(second_lon),
        math.sin(second_lat),
    )
    return MOON_RADIUS_KM * math.sqrt(
        sum((left - right) ** 2 for left, right in zip(first, second))
    )


def _norm(vec: Sequence[float]) -> tuple[float, float, float]:
    m = math.sqrt(sum(x*x for x in vec))
    if m == 0:
        return (vec[0], vec[1], vec[2])
    return (vec[0] / m, vec[1] / m, vec[2] / m)


def _dot(v1: Sequence[float], v2: Sequence[float]) -> float:
    return sum(x*y for x, y in zip(v1, v2))


def _project_onto_sky(vec: Sequence[float], los: Sequence[float]) -> tuple[float, float, float]:
    d = _dot(vec, los)
    return (vec[0] - d * los[0], vec[1] - d * los[1], vec[2] - d * los[2])


def _add(v1: Sequence[float], v2: Sequence[float]) -> tuple[float, float, float]:
    return (v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2])


def _scale(vec: Sequence[float], s: float) -> tuple[float, float, float]:
    return (vec[0] * s, vec[1] * s, vec[2] * s)


def _earth_observer_position_km(
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
) -> tuple[float, float, float]:
    if moira_native is not None and hasattr(moira_native, "geodetic_to_cartesian_wgs84"):
        pos = moira_native.geodetic_to_cartesian_wgs84(
            observer_lon,
            observer_lat,
            observer_elev_m,
        )
        return (float(pos.x), float(pos.y), float(pos.z))

    _, radii = sp.bodvrd("EARTH", "RADII", 3)
    equatorial_radius_km = float(radii[0])
    polar_radius_km = float(radii[2])
    flattening = (equatorial_radius_km - polar_radius_km) / equatorial_radius_km
    pos = sp.georec(
        math.radians(observer_lon),
        math.radians(observer_lat),
        observer_elev_m / 1000.0,
        equatorial_radius_km,
        flattening,
    )
    return (float(pos[0]), float(pos[1]), float(pos[2]))


def _observer_limb_context(
    et: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
) -> _ObserverLimbContext:
    observer_pos_iau_earth = _earth_observer_position_km(
        observer_lat,
        observer_lon,
        observer_elev_m,
    )
    moon_state_j2000, _ = sp.spkcpo(
        "MOON",
        et,
        "J2000",
        "OBSERVER",
        "LT+S",
        list(observer_pos_iau_earth),
        "EARTH",
        "IAU_EARTH",
    )
    observer_to_moon_j2000 = (float(moon_state_j2000[0]), float(moon_state_j2000[1]), float(moon_state_j2000[2]))
    observer_distance_km = math.sqrt(
        sum(component * component for component in observer_to_moon_j2000)
    )
    los_j2000 = _norm(observer_to_moon_j2000)
    moon_to_observer_j2000 = (-observer_to_moon_j2000[0], -observer_to_moon_j2000[1], -observer_to_moon_j2000[2])
    j2000_to_moon = sp.pxform("J2000", "MOON_ME", et)
    if moira_native is not None and hasattr(moira_native, "rotation_matrix_apply"):
        m_obs_moon_raw = moira_native.rotation_matrix_apply(j2000_to_moon, moon_to_observer_j2000)
    else:
        m_obs_moon_raw = sp.mxv(j2000_to_moon, list(moon_to_observer_j2000))
    moon_to_observer_moon = _norm((float(m_obs_moon_raw[0]), float(m_obs_moon_raw[1]), float(m_obs_moon_raw[2])))
    
    if moira_native is not None and hasattr(moira_native, "vec3_to_lonlat_signed"):
        lon_deg, lat_deg, _ = moira_native.vec3_to_lonlat_signed(moira_native.Vec3(*moon_to_observer_moon))
    else:
        _, lon_rad, lat_rad = sp.reclat(list(moon_to_observer_moon))
        lon_deg = lon_rad * sp.dpr()
        lat_deg = lat_rad * sp.dpr()
    moon_to_j2000 = sp.pxform("MOON_ME", "J2000", et)
    
    if moira_native is not None and hasattr(moira_native, "rotation_matrix_apply"):
        m_north_j2000_raw = moira_native.rotation_matrix_apply(moon_to_j2000, (0.0, 0.0, 1.0))
    else:
        m_north_j2000_raw = sp.mxv(moon_to_j2000, [0.0, 0.0, 1.0])
    moon_north_j2000 = _norm((float(m_north_j2000_raw[0]), float(m_north_j2000_raw[1]), float(m_north_j2000_raw[2])))
    
    celestial_north_j2000 = (0.0, 0.0, 1.0)
    sky_north_j2000 = _norm(_project_onto_sky(celestial_north_j2000, los_j2000))
    
    cross_raw = (
        los_j2000[1]*sky_north_j2000[2] - los_j2000[2]*sky_north_j2000[1],
        los_j2000[2]*sky_north_j2000[0] - los_j2000[0]*sky_north_j2000[2],
        los_j2000[0]*sky_north_j2000[1] - los_j2000[1]*sky_north_j2000[0]
    )
    sky_east_j2000 = _norm(cross_raw)
    
    if moira_native is not None and hasattr(moira_native, "rotation_matrix_apply"):
        s_north_moon_raw = moira_native.rotation_matrix_apply(j2000_to_moon, sky_north_j2000)
    else:
        s_north_moon_raw = sp.mxv(j2000_to_moon, list(sky_north_j2000))
    sky_north_moon = _norm((float(s_north_moon_raw[0]), float(s_north_moon_raw[1]), float(s_north_moon_raw[2])))
    
    if moira_native is not None and hasattr(moira_native, "rotation_matrix_apply"):
        s_east_moon_raw = moira_native.rotation_matrix_apply(j2000_to_moon, sky_east_j2000)
    else:
        s_east_moon_raw = sp.mxv(j2000_to_moon, list(sky_east_j2000))
    sky_east_moon = _norm((float(s_east_moon_raw[0]), float(s_east_moon_raw[1]), float(s_east_moon_raw[2])))
    
    return _ObserverLimbContext(
        subobserver_lon_deg=float(lon_deg),
        subobserver_lat_deg=float(lat_deg),
        observer_distance_km=observer_distance_km,
        los_j2000=los_j2000,
        observer_dir_moon=moon_to_observer_moon,
        sky_north_moon=sky_north_moon,
        sky_east_moon=sky_east_moon,
    )


def _matrix_columns_from_transform(transform) -> tuple[tuple[float, ...], ...]:
    columns = tuple(transform(axis) for axis in (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    ))
    return (
        (columns[0][0], columns[1][0], columns[2][0]),
        (columns[0][1], columns[1][1], columns[2][1]),
        (columns[0][2], columns[1][2], columns[2][2]),
    )


def _transpose_matrix_vector(
    matrix: Sequence[Sequence[float]],
    vector: Sequence[float],
) -> tuple[float, float, float]:
    return (
        sum(matrix[row][0] * vector[row] for row in range(3)),
        sum(matrix[row][1] * vector[row] for row in range(3)),
        sum(matrix[row][2] * vector[row] for row in range(3)),
    )


def _reader_bound_moon_light_cone(
    jd_ut1: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
    reader: KernelReader,
) -> _TopocentricMoonLightCone:
    """Solve the physical DE441 Moon-to-observer light cone in ICRF.

    The terrestrial observer is fixed at the UT1 reception epoch.  The Moon is
    iterated to its retarded TT emission epoch using the same content-identified
    DE441/LE441 reader.  Annual and diurnal aberration are deliberately absent:
    this vector is a physical surface-projection ray, not an observer-rest-frame
    apparent direction.
    """

    from .corrections import apply_frame_bias, _observer_position_icrf
    from .julian import local_sidereal_time
    from .obliquity import nutation, true_obliquity
    from .planets import (
        _apply_rotation_matrix,
        _compose_rotation_matrix,
    )

    epoch = _finite_float("jd_ut1", jd_ut1)
    jd_tt = _ut1_to_ephemeris_tt(epoch, reader)
    identity = _reader_identity_at(reader, jd_tt)
    if (
        identity is None
        or identity.planetary_ephemeris != "DE441"
        or identity.lunar_ephemeris != "LE441"
    ):
        label = None if identity is None else identity.summary_label
        raise LunarLimbResourceError(
            "topographic contact profiles require a content-identified "
            f"DE441/LE441 reader; received {label!r}"
        )

    rotation = _compose_rotation_matrix(jd_tt, with_nutation=True)

    def icrf_to_true_of_date(vector: Sequence[float]) -> tuple[float, float, float]:
        biased = apply_frame_bias((float(vector[0]), float(vector[1]), float(vector[2])))
        rotated = _apply_rotation_matrix(rotation, biased)
        return (float(rotated[0]), float(rotated[1]), float(rotated[2]))

    full_rotation = _matrix_columns_from_transform(icrf_to_true_of_date)
    dpsi_deg, _ = nutation(jd_tt)
    lst_deg = local_sidereal_time(
        epoch,
        observer_lon,
        dpsi_deg,
        true_obliquity(jd_tt),
    )
    observer_true_of_date = _observer_position_icrf(
        observer_lat,
        observer_lon,
        lst_deg,
        observer_elev_m,
        jd_ut=epoch,
        observer_frame="equatorial_of_date",
    )
    observer_icrf = _transpose_matrix_vector(
        full_rotation,
        observer_true_of_date,
    )

    ssb_emb_reception = reader.position(0, 3, jd_tt)
    emb_earth_reception = reader.position(3, 399, jd_tt)
    observer_ssb = tuple(
        float(ssb_emb_reception[index])
        + float(emb_earth_reception[index])
        + observer_icrf[index]
        for index in range(3)
    )

    seconds_per_day = 86_400.0
    # The lunar one-way light time is about 1.3 seconds, not 1.3 days.  A
    # physically scaled seed also avoids asking a boundary-near kernel for an
    # unnecessary, day-retarded first witness.
    light_time_days = 1.3 / seconds_per_day
    moon_to_observer = (0.0, 0.0, 0.0)
    emission_jd_tt = jd_tt - light_time_days
    for _iteration in range(16):
        emission_jd_tt = jd_tt - light_time_days
        ssb_emb_emission = reader.position(0, 3, emission_jd_tt)
        emb_moon_emission = reader.position(3, 301, emission_jd_tt)
        moon_to_observer = tuple(
            observer_ssb[index]
            - float(ssb_emb_emission[index])
            - float(emb_moon_emission[index])
            for index in range(3)
        )
        distance_km = math.sqrt(sum(value * value for value in moon_to_observer))
        if not math.isfinite(distance_km) or distance_km <= 0.0:
            raise LunarLimbResourceError(
                "DE441 lunar light-cone distance must be finite and positive"
            )
        next_light_time_days = distance_km / (_LIGHT_SPEED_KM_S * seconds_per_day)
        # 1e-12 day is about 86 ns (2.6 cm of light path), far below the
        # millisecond public contact tolerance while remaining stable against
        # binary64 SPK evaluation noise during dense root refinement.
        if abs(next_light_time_days - light_time_days) <= 1.0e-12:
            light_time_days = next_light_time_days
            break
        light_time_days = next_light_time_days
    else:
        raise LunarLimbResourceError("DE441 lunar light-cone iteration did not converge")

    observer_to_moon_icrf = _norm(tuple(-value for value in moon_to_observer))
    et_emission = (tt_to_tdb(emission_jd_tt) - J2000) * seconds_per_day
    return _TopocentricMoonLightCone(
        jd_tt_reception=jd_tt,
        jd_tt_emission=emission_jd_tt,
        et_emission=et_emission,
        distance_km=distance_km,
        observer_ssb_icrf=observer_ssb,
        observer_to_moon_icrf=observer_to_moon_icrf,
        icrf_to_true_of_date=full_rotation,
        translation_label=identity.summary_label,
    )


def _reader_bound_observer_limb_context(
    jd_ut1: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
    reader: KernelReader,
) -> tuple[_ObserverLimbContext, str, float]:
    """Rotate the physical DE441 light cone and its tangent basis into lunar ME."""

    light_cone = _reader_bound_moon_light_cone(
        jd_ut1,
        observer_lat,
        observer_lon,
        observer_elev_m,
        reader,
    )
    los_j2000 = light_cone.observer_to_moon_icrf
    los_of_date = _norm(
        tuple(
            sum(
                light_cone.icrf_to_true_of_date[row][column] * los_j2000[column]
                for column in range(3)
            )
            for row in range(3)
        )
    )
    ra = math.atan2(los_of_date[1], los_of_date[0])
    dec = math.asin(max(-1.0, min(1.0, los_of_date[2])))
    north_of_date = (
        -math.sin(dec) * math.cos(ra),
        -math.sin(dec) * math.sin(ra),
        math.cos(dec),
    )
    east_of_date = (-math.sin(ra), math.cos(ra), 0.0)
    north_j2000 = _norm(
        _transpose_matrix_vector(light_cone.icrf_to_true_of_date, north_of_date)
    )
    east_j2000 = _norm(
        _transpose_matrix_vector(light_cone.icrf_to_true_of_date, east_of_date)
    )

    j2000_to_moon = sp.pxform(
        "J2000",
        _CONTACT_ORIENTATION_FRAME,
        light_cone.et_emission,
    )

    def rotate_to_moon(vector: Sequence[float]) -> tuple[float, float, float]:
        if moira_native is not None and hasattr(
            moira_native,
            "rotation_matrix_apply",
        ):
            raw = moira_native.rotation_matrix_apply(j2000_to_moon, vector)
        else:
            raw = sp.mxv(j2000_to_moon, list(vector))
        return _norm((float(raw[0]), float(raw[1]), float(raw[2])))

    moon_to_observer_moon = rotate_to_moon(
        (-los_j2000[0], -los_j2000[1], -los_j2000[2])
    )
    sky_north_moon = rotate_to_moon(north_j2000)
    sky_east_moon = rotate_to_moon(east_j2000)
    if moira_native is not None and hasattr(moira_native, "vec3_to_lonlat_signed"):
        lon_deg, lat_deg, _ = moira_native.vec3_to_lonlat_signed(
            moira_native.Vec3(*moon_to_observer_moon)
        )
    else:
        _, lon_rad, lat_rad = sp.reclat(list(moon_to_observer_moon))
        lon_deg = math.degrees(lon_rad)
        lat_deg = math.degrees(lat_rad)

    context = _ObserverLimbContext(
        subobserver_lon_deg=float(lon_deg),
        subobserver_lat_deg=float(lat_deg),
        observer_distance_km=light_cone.distance_km,
        los_j2000=los_j2000,
        observer_dir_moon=moon_to_observer_moon,
        sky_north_moon=sky_north_moon,
        sky_east_moon=sky_east_moon,
    )
    return context, light_cone.translation_label, light_cone.et_emission


def _limb_point_lon_lat_deg(
    jd_ut: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
    position_angle_deg: float,
) -> tuple[float, float]:
    et = _jd_ut_to_et(jd_ut)
    context = _observer_limb_context(
        et,
        observer_lat,
        observer_lon,
        observer_elev_m,
    )
    return _limb_point_lon_lat_from_context(context, position_angle_deg)


def _limb_point_lon_lat_from_context(
    context: _ObserverLimbContext,
    position_angle_deg: float,
) -> tuple[float, float]:
    # At finite distance the spherical tangent circle is not the great circle
    # perpendicular to the Moon--observer direction.  If ``o`` points from
    # the Moon to the observer, the unit surface tangent is
    #
    #   u = (R / D) o + sqrt(1 - (R / D)^2) q,
    #
    # where q is the requested sky-plane PA direction.  The former q-only
    # approximation displaced the sampled lunar terrain by about 7.8 km at
    # ordinary lunar distance.
    pa_rad = math.radians(position_angle_deg)
    sky_plane_direction = _norm(_add(
        _scale(context.sky_north_moon, math.cos(pa_rad)),
        _scale(context.sky_east_moon, math.sin(pa_rad))
    ))
    tangent_cosine = MOON_RADIUS_KM / context.observer_distance_km
    if not 0.0 < tangent_cosine < 1.0:
        raise LunarLimbResourceError(
            "observer distance must exceed the lunar reference radius"
        )
    limb_vec_moon = _norm(_add(
        _scale(context.observer_dir_moon, tangent_cosine),
        _scale(sky_plane_direction, math.sqrt(1.0 - tangent_cosine * tangent_cosine)),
    ))
    if moira_native is not None and hasattr(moira_native, "vec3_to_lonlat_signed"):
        lon_deg, lat_deg, _ = moira_native.vec3_to_lonlat_signed(moira_native.Vec3(*limb_vec_moon))
        return _normalize_lon_deg(float(lon_deg)), float(lat_deg)

    _, lon_rad, lat_rad = sp.reclat(limb_vec_moon)
    return _normalize_lon_deg(lon_rad * sp.dpr()), lat_rad * sp.dpr()


@lru_cache(maxsize=128)
def _lola_tile_asset_url(lon_bin: int, lat_bin: int, cache_root_str: str) -> str:
    cache_root = Path(cache_root_str)
    # Version 1 queried the shared corner of four 15-degree cells with
    # ``limit=1``. STAC could lawfully return any neighbour, so those cached
    # mappings are not admissible for contact work. Query the strict interior
    # of the requested cell and use a versioned cache key.
    cache_key = f"cell-center-v2:{lon_bin},{lat_bin}"
    cache = _load_stac_tile_cache(cache_root)
    cached_url = cache.get(cache_key)
    if cached_url:
        return cached_url
    if _downloads_disabled():
        raise LunarLimbResourceError(
            "LOLA STAC lookup is not cached and MOIRA_NO_DOWNLOAD is set: "
            f"lon={lon_bin}, lat={lat_bin}"
        )

    query_lon = _normalize_lon_deg(lon_bin + _LOLA_TILE_STEP_DEG / 2.0)
    query_lat = lat_bin + _LOLA_TILE_STEP_DEG / 2.0
    if not -90.0 < query_lat < 90.0:
        raise _NoLolaTileError(
            f"No lawful LOLA cell centre for lon={lon_bin}, lat={lat_bin}"
        )
    bbox = [query_lon - 0.01, query_lat - 0.01, query_lon + 0.01, query_lat + 0.01]
    try:
        if not _HAS_REQUESTS:
            _require_requests()
        response = requests.post(
            _STAC_SEARCH_URL,
            json={
                "collections": [_LOLA_COLLECTION],
                "bbox": bbox,
                "limit": 4,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise LunarLimbResourceError(
            f"official LOLA STAC lookup failed for lon={lon_bin}, lat={lat_bin}"
        ) from exc
    if not isinstance(payload, dict):
        raise LunarLimbResourceError("official LOLA STAC response must be a JSON object")
    features = payload.get("features", [])
    if not isinstance(features, list):
        raise LunarLimbResourceError("official LOLA STAC response has invalid features")
    if not features:
        raise _NoLolaTileError(
            f"No official LOLA tile found for lon={lon_bin}, lat={lat_bin}"
        )
    containing: list[dict[str, object]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        feature_bbox = feature.get("bbox")
        if not isinstance(feature_bbox, list) or len(feature_bbox) < 4:
            continue
        try:
            west, south, east, north = (float(value) for value in feature_bbox[:4])
        except (TypeError, ValueError):
            continue
        if west < query_lon < east and south < query_lat < north:
            containing.append(feature)
    if len(containing) != 1:
        raise LunarLimbResourceError(
            "official LOLA STAC lookup must identify exactly one tile whose "
            f"interior contains lon={query_lon}, lat={query_lat}; got {len(containing)}"
        )
    try:
        url = str(containing[0]["assets"]["data"]["href"])
    except (KeyError, TypeError) as exc:
        raise LunarLimbResourceError(
            "official LOLA STAC feature lacks assets.data.href"
        ) from exc
    if not url.startswith("https://"):
        raise LunarLimbResourceError(
            f"official LOLA STAC asset must use HTTPS, got {url!r}"
        )
    with _CACHE_LOCK:
        cache = _load_stac_tile_cache(cache_root)
        cache[cache_key] = url
        _store_stac_tile_cache(cache_root, cache)
    return url


def _validate_lola_coordinate_header(header: object) -> None:
    """Admit only the documented IAU 2015 Moon-centred Cartesian CRS.

    LASPy's high-level CRS parser imports ``pyproj``, which is deliberately
    outside Moira's lunar-graze dependency boundary. The authoritative WKT VLR
    is therefore inspected directly and matched against the governing frame,
    spherical reference radius, dimensionality, and IAU identifier.
    """

    vlrs = getattr(header, "vlrs", ())
    wkts = tuple(
        value
        for item in vlrs
        if getattr(item, "user_id", None) == "LASF_Projection"
        and getattr(item, "record_id", None) == 2112
        and isinstance((value := getattr(item, "string", None)), str)
    )
    if len(wkts) != 1:
        raise LunarLimbResourceError(
            "LOLA LAS/COPC asset must contain exactly one WKT coordinate-system VLR"
        )
    compact = "".join(wkts[0].split())
    missing = tuple(token for token in _LOLA_COORDINATE_WKT_TOKENS if token not in compact)
    if missing:
        raise LunarLimbResourceError(
            "LOLA LAS/COPC coordinate system is not the admitted IAU 2015 "
            f"Moon XYZ sphere: missing {missing!r}"
        )


def _lola_tile_from_las(
    las: object,
    *,
    url: str,
    max_points: int | None,
    decompression_point_upper_bound: int | None = None,
) -> _LolaTile:
    """Copy one admitted LAS selection into bounded native storage."""

    try:
        point_count = len(las)
    except TypeError as exc:
        raise LunarLimbResourceError(
            f"LOLA decoder returned an invalid point collection for {url}"
        ) from exc
    if point_count <= 0:
        raise LunarLimbResourceError(
            f"LOLA Cartesian acquisition envelope returned no points for {url}"
        )
    if max_points is not None and point_count > max_points:
        raise LunarLimbResourceError(
            f"LOLA tile query returned {point_count} points for {url}, exceeding "
            f"the per-tile bound {max_points}"
        )
    point_cloud = moira_native.LolaPointCloud(
        [float(value) / 1000.0 for value in las.x],
        [float(value) / 1000.0 for value in las.y],
        [float(value) / 1000.0 for value in las.z],
    )
    return _LolaTile(
        point_cloud=point_cloud,
        decompression_point_upper_bound=decompression_point_upper_bound,
    )


def _load_lola_tile_uncached(
    url: str,
    cache_root_str: str,
    expected_byte_length: int | None = None,
    expected_sha256: str | None = None,
    *,
    max_points: int | None = None,
) -> _LolaTile:
    _require_laspy()
    if moira_native is None:
        raise ImportError("Native Moira backend required for LOLA processing.")

    expected_identity = _optional_resource_identity(
        expected_byte_length,
        expected_sha256,
    )
    cache_root = Path(cache_root_str)
    tile_path = _download_file(
        url,
        cache_root / "lola_tiles" / Path(url).name,
        expected_identity=expected_identity,
    )
    if tile_path.suffixes[-2:] == [".copc", ".laz"]:
        with CopcReader.open(tile_path) as reader:
            _validate_lola_coordinate_header(reader.header)
            bounds = Bounds(reader.header.mins, reader.header.maxs)
            las = reader.query(bounds=bounds)
    else:
        las = laspy.read(tile_path)
        _validate_lola_coordinate_header(las.header)

    return _lola_tile_from_las(las, url=url, max_points=max_points)


@lru_cache(maxsize=16)
def _load_lola_tile(
    url: str,
    cache_root_str: str,
    expected_byte_length: int | None = None,
    expected_sha256: str | None = None,
) -> _LolaTile:
    """Compatibility whole-tile cache used outside event-profile builders."""

    return _load_lola_tile_uncached(
        url,
        cache_root_str,
        expected_byte_length,
        expected_sha256,
    )


def _load_lola_tile_cartesian_region(
    url: str,
    cache_root_str: str,
    query_bounds: _LolaCartesianBounds,
    expected_byte_length: int | None = None,
    expected_sha256: str | None = None,
    *,
    max_points: int = _MAX_CONTACT_LOLA_POINTS_PER_TILE,
    max_decompression_points: int = _MAX_CONTACT_LOLA_POINTS_PER_TILE,
) -> _LolaTile:
    """Decode one bounded COPC selection without process-global retention."""

    _require_laspy()
    if moira_native is None:
        raise ImportError("Native Moira backend required for LOLA processing.")
    if not isinstance(query_bounds, _LolaCartesianBounds):
        raise TypeError("query_bounds must be a _LolaCartesianBounds")
    if isinstance(max_points, bool) or not isinstance(max_points, int):
        raise TypeError("max_points must be an integer")
    if max_points <= 0:
        raise ValueError("max_points must be positive")
    if (
        isinstance(max_decompression_points, bool)
        or not isinstance(max_decompression_points, int)
    ):
        raise TypeError("max_decompression_points must be an integer")
    if max_decompression_points <= 0:
        raise ValueError("max_decompression_points must be positive")

    expected_identity = _optional_resource_identity(
        expected_byte_length,
        expected_sha256,
    )
    cache_root = Path(cache_root_str)
    tile_path = _download_file(
        url,
        cache_root / "lola_tiles" / Path(url).name,
        expected_identity=expected_identity,
    )

    if tile_path.suffixes[-2:] != [".copc", ".laz"]:
        raise LunarLimbResourceError(
            "contact-profile spatial acquisition requires a .copc.laz asset; "
            f"received {tile_path.name!r}"
        )

    with CopcReader.open(tile_path) as reader:
        _validate_lola_coordinate_header(reader.header)
        laspy_bounds = query_bounds.to_laspy_bounds().ensure_3d(
            reader.header.mins,
            reader.header.maxs,
        )
        if load_octree_for_query is None:
            raise ImportError("laspy COPC octree query support is unavailable")
        nodes = load_octree_for_query(
            reader.source,
            reader.copc_info,
            reader.root_page,
            query_bounds=laspy_bounds,
            level_range=None,
        )
        decompression_upper_bound = sum(int(node.point_count) for node in nodes)
        if decompression_upper_bound > max_decompression_points:
            raise LunarLimbResourceError(
                f"LOLA COPC query for {url} can decompress up to "
                f"{decompression_upper_bound} points, exceeding the remaining "
                f"admitted bound {max_decompression_points}"
            )
        las = reader.query(bounds=laspy_bounds)
    return _lola_tile_from_las(
        las,
        url=url,
        max_points=max_points,
        decompression_point_upper_bound=decompression_upper_bound,
    )


def _load_lola_tile_region(
    url: str,
    cache_root_str: str,
    center_lon_deg: float,
    center_lat_deg: float,
    half_width_km: float,
    expected_byte_length: int | None = None,
    expected_sha256: str | None = None,
) -> _LolaTile:
    """Compatibility cube wrapper around the non-retaining region loader."""

    width = _finite_float("half_width_km", half_width_km)
    if width <= 0.0:
        raise ValueError("half_width_km must be positive")
    lon = math.radians(_finite_float("center_lon_deg", center_lon_deg))
    lat = math.radians(_finite_float("center_lat_deg", center_lat_deg))
    center = (
        MOON_RADIUS_KM * math.cos(lat) * math.cos(lon),
        MOON_RADIUS_KM * math.cos(lat) * math.sin(lon),
        MOON_RADIUS_KM * math.sin(lat),
    )
    bounds = _LolaCartesianBounds(
        tuple(value - width for value in center),
        tuple(value + width for value in center),
    )
    return _load_lola_tile_cartesian_region(
        url,
        cache_root_str,
        bounds,
        expected_byte_length,
        expected_sha256,
    )


def _lola_neighbor_tile_urls(lon_deg: float, lat_deg: float, cache_root: Path) -> tuple[str, ...]:
    lon_bin = int(math.floor(lon_deg / _LOLA_TILE_STEP_DEG) * _LOLA_TILE_STEP_DEG)
    lat_bin = int(math.floor(lat_deg / _LOLA_TILE_STEP_DEG) * _LOLA_TILE_STEP_DEG)
    seen: set[str] = set()
    urls: list[str] = []
    for lon_offset in range(
        -_LIMB_TILE_EXTENT * _LOLA_TILE_STEP_DEG,
        (_LIMB_TILE_EXTENT + 1) * _LOLA_TILE_STEP_DEG,
        _LOLA_TILE_STEP_DEG,
    ):
        for lat_offset in range(
            -_LIMB_TILE_EXTENT * _LOLA_TILE_STEP_DEG,
            (_LIMB_TILE_EXTENT + 1) * _LOLA_TILE_STEP_DEG,
            _LOLA_TILE_STEP_DEG,
        ):
            try:
                url = _lola_tile_asset_url(lon_bin + lon_offset, lat_bin + lat_offset, str(cache_root))
            except _NoLolaTileError:
                continue
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return tuple(urls)


def _lola_relief_competition_guard_rad(
    observer_distance_km: float,
    minimum_chord_margin_km: float = 0.0,
) -> float:
    """Return the full finite-distance guard for relief-shell completeness.

    The completeness floor is the inner admitted shell ``R-H``; it is not a
    replacement radius.  An outer-shell summit ``R+H`` can compete with that
    valley over ``acos((R-H)/(R+H))`` in the infinite-distance limit.  The two
    ``asin`` terms add the conservative finite-perspective far-side offset
    from the mean-radius tangent circle.  A caller-supplied query floor may
    widen, but never narrow, this physical guard.
    """

    distance = _finite_float("observer_distance_km", observer_distance_km)
    if distance <= _LOLA_OUTER_RELIEF_RADIUS_KM:
        raise LunarLimbResourceError(
            "observer distance must exceed the outer admitted lunar relief shell"
        )
    requested_margin = _finite_float(
        "minimum_chord_margin_km", minimum_chord_margin_km
    )
    if requested_margin < 0.0:
        raise ValueError("minimum_chord_margin_km cannot be negative")
    physical_guard = (
        math.acos(_LOLA_INNER_RELIEF_RADIUS_KM / _LOLA_OUTER_RELIEF_RADIUS_KM)
        + math.asin(MOON_RADIUS_KM / distance)
        - math.asin(_LOLA_INNER_RELIEF_RADIUS_KM / distance)
    )

    admitted_margin = max(
        requested_margin,
        _LOLA_MEAN_LIMB_CHORD_MARGIN_KM,
    )
    maximum_chord = MOON_RADIUS_KM + _LOLA_OUTER_RELIEF_RADIUS_KM
    if admitted_margin >= maximum_chord:
        raise ValueError(
            "minimum_chord_margin_km must be smaller than the lunar-shell diameter"
        )
    chord_cosine = (
        MOON_RADIUS_KM**2
        + _LOLA_OUTER_RELIEF_RADIUS_KM**2
        - admitted_margin**2
    ) / (2.0 * MOON_RADIUS_KM * _LOLA_OUTER_RELIEF_RADIUS_KM)
    chord_guard = math.acos(max(-1.0, min(1.0, chord_cosine)))
    return max(physical_guard, chord_guard)


def _lola_acquisition_caps(
    observer_context: _ObserverLimbContext,
    position_angle_center_deg: float,
    position_angle_half_width_deg: float,
    minimum_chord_margin_km: float = 0.0,
) -> tuple[_LolaSphericalCap, ...]:
    """Cover the continuous PA locus with relief-shell spherical caps."""

    center = _finite_float(
        "position_angle_center_deg", position_angle_center_deg
    )
    half_width = _finite_float(
        "position_angle_half_width_deg", position_angle_half_width_deg
    )
    if half_width <= 0.0 or half_width > _LIMB_PA_WINDOW_DEG:
        raise ValueError(
            "position_angle_half_width_deg must be in "
            f"(0, {_LIMB_PA_WINDOW_DEG}]"
        )
    segment_count = max(
        1,
        int(
            math.ceil(
                2.0 * half_width / _LOLA_TILE_DISCOVERY_STEP_DEG
            )
        ),
    )
    actual_step_deg = 2.0 * half_width / segment_count
    acquisition_guard = _lola_relief_competition_guard_rad(
        observer_context.observer_distance_km,
        minimum_chord_margin_km,
    ) + math.radians(actual_step_deg / 2.0)
    caps: list[_LolaSphericalCap] = []
    for index in range(segment_count + 1):
        pa = center - half_width + actual_step_deg * index
        longitude, latitude = _limb_point_lon_lat_from_context(
            observer_context,
            pa,
        )
        lon_rad = math.radians(longitude)
        lat_rad = math.radians(latitude)
        unit = (
            math.cos(lat_rad) * math.cos(lon_rad),
            math.cos(lat_rad) * math.sin(lon_rad),
            math.sin(lat_rad),
        )
        caps.append(
            _LolaSphericalCap(
                center_unit=unit,
                center_lon_deg=longitude,
                center_lat_deg=latitude,
                angular_radius_rad=acquisition_guard,
            )
        )
    return tuple(caps)


def _minimum_longitude_delta_rad(
    longitude_deg: float,
    west_deg: float,
    east_deg: float,
) -> float:
    """Minimum circular longitude distance to one non-wrapping cell interval."""

    deltas: list[float] = []
    for shifted in (
        longitude_deg - 360.0,
        longitude_deg,
        longitude_deg + 360.0,
    ):
        if west_deg <= shifted <= east_deg:
            return 0.0
        deltas.extend((abs(shifted - west_deg), abs(shifted - east_deg)))
    return math.radians(min(deltas))


def _lola_cell_maximum_cap_dot(
    cap: _LolaSphericalCap,
    lon_bin_deg: int,
    lat_bin_deg: int,
) -> float:
    """Exact maximum centre dot product over one 15-degree lon/lat cell."""

    west = float(lon_bin_deg)
    east = west + _LOLA_TILE_STEP_DEG
    south = math.radians(lat_bin_deg)
    north = math.radians(lat_bin_deg + _LOLA_TILE_STEP_DEG)
    delta_lon = _minimum_longitude_delta_rad(
        cap.center_lon_deg,
        west,
        east,
    )
    center_lat = math.radians(cap.center_lat_deg)
    sine_coefficient = math.sin(center_lat)
    cosine_coefficient = math.cos(center_lat) * math.cos(delta_lon)
    candidates = [south, north]
    stationary = math.atan2(sine_coefficient, cosine_coefficient)
    for offset in (-math.pi, 0.0, math.pi):
        candidate = stationary + offset
        if south <= candidate <= north:
            candidates.append(candidate)
    return max(
        sine_coefficient * math.sin(latitude)
        + cosine_coefficient * math.cos(latitude)
        for latitude in candidates
    )


def _lola_envelope_tile_cells(
    observer_context: _ObserverLimbContext,
    position_angle_center_deg: float,
    position_angle_half_width_deg: float,
    minimum_chord_margin_km: float = 0.0,
) -> tuple[tuple[int, int], ...]:
    """Return every 15-degree cell intersecting the continuous relief envelope."""

    caps = _lola_acquisition_caps(
        observer_context,
        position_angle_center_deg,
        position_angle_half_width_deg,
        minimum_chord_margin_km,
    )
    cells: list[tuple[int, int]] = []
    for lat_bin in range(-90, 90, _LOLA_TILE_STEP_DEG):
        for lon_bin in range(-180, 180, _LOLA_TILE_STEP_DEG):
            if any(
                _lola_cell_maximum_cap_dot(cap, lon_bin, lat_bin)
                >= math.cos(cap.angular_radius_rad) - 2.0e-15
                for cap in caps
            ):
                cells.append((lon_bin, lat_bin))
    if len(cells) > _MAX_CONTACT_LOLA_TILES:
        raise LunarLimbResourceError(
            f"LOLA relief envelope intersects {len(cells)} cells, exceeding "
            f"the admitted tile bound {_MAX_CONTACT_LOLA_TILES}"
        )
    return tuple(cells)


def _lola_envelope_tile_urls(
    observer_context: _ObserverLimbContext,
    position_angle_center_deg: float,
    position_angle_half_width_deg: float,
    cache_root: Path,
    minimum_chord_margin_km: float = 0.0,
) -> tuple[str, ...]:
    """Resolve all official cells intersecting the relief-capable PA envelope."""

    urls: list[str] = []
    for lon_bin, lat_bin in _lola_envelope_tile_cells(
        observer_context,
        position_angle_center_deg,
        position_angle_half_width_deg,
        minimum_chord_margin_km,
    ):
        # Every intersecting relief-shell cell is part of the completeness
        # proof.  An absent official mapping is therefore a hard resource
        # failure, not permission to silently narrow the lunar surface.
        url = _lola_tile_asset_url(lon_bin, lat_bin, str(cache_root))
        if url not in urls:
            urls.append(url)
    return tuple(urls)


def _lola_cap_coordinate_extrema(
    center_coordinate: float,
    angular_radius_rad: float,
) -> tuple[float, float]:
    """Exact extrema of one unit Cartesian coordinate over a spherical cap."""

    cosine = math.cos(angular_radius_rad)
    sine = math.sin(angular_radius_rad)
    perpendicular = math.sqrt(max(0.0, 1.0 - center_coordinate**2))
    minimum = (
        -1.0
        if center_coordinate <= -cosine
        else center_coordinate * cosine - perpendicular * sine
    )
    maximum = (
        1.0
        if center_coordinate >= cosine
        else center_coordinate * cosine + perpendicular * sine
    )
    return max(-1.0, minimum), min(1.0, maximum)


def _lola_cartesian_query_bounds(
    caps: Sequence[_LolaSphericalCap],
) -> _LolaCartesianBounds:
    """Bound all admitted relief-shell points in a cap union, in Moon XYZ."""

    admitted_caps = tuple(caps)
    if not admitted_caps or any(
        not isinstance(cap, _LolaSphericalCap) for cap in admitted_caps
    ):
        raise ValueError("caps must contain at least one _LolaSphericalCap")
    minimum = [math.inf, math.inf, math.inf]
    maximum = [-math.inf, -math.inf, -math.inf]
    for cap in admitted_caps:
        for axis, center_coordinate in enumerate(cap.center_unit):
            unit_minimum, unit_maximum = _lola_cap_coordinate_extrema(
                center_coordinate,
                cap.angular_radius_rad,
            )
            radial_minimum = (
                _LOLA_OUTER_RELIEF_RADIUS_KM * unit_minimum
                if unit_minimum < 0.0
                else _LOLA_INNER_RELIEF_RADIUS_KM * unit_minimum
            )
            radial_maximum = (
                _LOLA_OUTER_RELIEF_RADIUS_KM * unit_maximum
                if unit_maximum > 0.0
                else _LOLA_INNER_RELIEF_RADIUS_KM * unit_maximum
            )
            minimum[axis] = min(minimum[axis], radial_minimum)
            maximum[axis] = max(maximum[axis], radial_maximum)
    return _LolaCartesianBounds(tuple(minimum), tuple(maximum))


def _lola_common_cartesian_query_bounds(
    observer_contexts: Sequence[_ObserverLimbContext],
    position_angle_center_deg: float,
    position_angle_half_width_deg: float,
    minimum_chord_margin_km: float = 0.0,
) -> _LolaCartesianBounds:
    """Return one cap-union Moon-XYZ envelope shared by all profile slices."""

    contexts = tuple(observer_contexts)
    if not contexts:
        raise ValueError("observer_contexts must contain at least one context")
    caps = tuple(
        cap
        for context in contexts
        for cap in _lola_acquisition_caps(
            context,
            position_angle_center_deg,
            position_angle_half_width_deg,
            minimum_chord_margin_km,
        )
    )
    return _lola_cartesian_query_bounds(caps)


def _collect_lola_projected_points(
    lon_deg: float,
    lat_deg: float,
    observer_context: _ObserverLimbContext,
    position_angle_deg: float,
    cache_root: Path,
    query_half_width_km: float,
    position_angle_half_width_deg: float = _LIMB_PA_WINDOW_DEG,
    tile_urls: Sequence[str] | None = None,
    expected_lola_assets: Mapping[str, LunarLimbAssetIdentity] | None = None,
    loaded_tiles: Mapping[str, _LolaTile] | None = None,
) -> tuple[
    tuple[float, ...],
    tuple[float, ...],
    tuple[float, ...],
    tuple[float, ...],
    tuple[str, ...],
]:
    """Load, native-filter, and native-project the bounded official LOLA cloud."""

    if moira_native is None:
        raise ImportError("Native Moira backend required for LOLA processing.")

    all_east: list[float] = []
    all_north: list[float] = []
    all_radius: list[float] = []
    all_pa: list[float] = []
    admitted_urls: list[str] = []
    obs_vec = moira_native.Vec3(*observer_context.observer_dir_moon)
    east_vec = moira_native.Vec3(*observer_context.sky_east_moon)
    north_vec = moira_native.Vec3(*observer_context.sky_north_moon)

    resolved_tile_urls = (
        tuple(tile_urls)
        if tile_urls is not None
        else _lola_envelope_tile_urls(
            observer_context,
            position_angle_deg,
            position_angle_half_width_deg,
            cache_root,
        )
    )
    for tile_url in resolved_tile_urls:
        expected_asset = (
            None
            if expected_lola_assets is None
            else expected_lola_assets.get(tile_url)
        )
        if expected_lola_assets is not None and expected_asset is None:
            raise LunarLimbResourceError(
                "LOLA tile URL lacks an externally admitted byte identity: "
                f"{tile_url}"
            )
        if loaded_tiles is None:
            tile = _load_lola_tile_region(
                tile_url,
                str(cache_root),
                lon_deg,
                lat_deg,
                query_half_width_km,
                None if expected_asset is None else expected_asset.byte_length,
                None if expected_asset is None else expected_asset.sha256,
            )
        else:
            try:
                tile = loaded_tiles[tile_url]
            except KeyError as exc:
                raise LunarLimbResourceError(
                    f"builder-local LOLA tile was not loaded for {tile_url}"
                ) from exc
        admitted_urls.append(tile_url)
        # Contact profiles use the complete radial envelope.  A near-side
        # visibility filter can discard a far-side summit that defines the
        # apparent silhouette, while the legacy mean-minus-1-km floor can
        # erase a real depression.  The outermost projected point in each PA
        # bin supplies self-occlusion directly, so only the bounded PA filter
        # is lawful here.
        filtered_pc = tile.point_cloud.filter_by_position_angle(
            east_vec,
            north_vec,
            position_angle_deg,
            position_angle_half_width_deg,
        )
        if filtered_pc.size() == 0:
            continue
        projected = filtered_pc.project_to_sky_plane(
            obs_vec,
            east_vec,
            north_vec,
            observer_context.observer_distance_km,
        )
        all_east.extend(float(value) for value in projected.east_km)
        all_north.extend(float(value) for value in projected.north_km)
        all_radius.extend(float(value) for value in projected.radius_km)
        all_pa.extend(float(value) for value in projected.pa_deg)

    return (
        tuple(all_east),
        tuple(all_north),
        tuple(all_radius),
        tuple(all_pa),
        tuple(dict.fromkeys(admitted_urls)),
    )


def _profile_slice_from_bin_maxima(
    *,
    jd_ut1: float,
    maxima: Mapping[int, float],
    position_angle_center_deg: float,
    position_angle_half_width_deg: float,
    bin_width_deg: float,
    max_interpolation_gap_deg: float,
    source_point_count: int,
    asset_urls: Sequence[str],
) -> LunarLimbProfileSlice:
    """Admit one already-reduced, half-open-bin silhouette profile."""

    epoch = _finite_float("jd_ut1", jd_ut1)
    center = _finite_float("position_angle_center_deg", position_angle_center_deg)
    half_width = _finite_float(
        "position_angle_half_width_deg", position_angle_half_width_deg
    )
    width = _finite_float("bin_width_deg", bin_width_deg)
    max_gap = _finite_float(
        "max_interpolation_gap_deg", max_interpolation_gap_deg
    )
    if isinstance(source_point_count, bool) or not isinstance(source_point_count, int):
        raise TypeError("source_point_count must be an integer")
    if source_point_count < 0:
        raise ValueError("source_point_count cannot be negative")
    if half_width <= 0.0 or half_width >= 180.0:
        raise ValueError("position_angle_half_width_deg must be in (0, 180)")
    if width <= 0.0 or width >= 2.0 * half_width:
        raise ValueError(
            "bin_width_deg must be positive and narrower than the profile window"
        )
    span = 2.0 * half_width
    bin_count_float = span / width
    bin_count = round(bin_count_float)
    if bin_count < 2 or not math.isclose(
        bin_count_float,
        bin_count,
        rel_tol=0.0,
        abs_tol=1e-10,
    ):
        raise ValueError(
            "the full position-angle window must contain an integer number of bins"
        )
    admitted_maxima = {
        int(index): _finite_float("profile bin maximum", radius)
        for index, radius in maxima.items()
    }
    if any(index < 0 or index >= bin_count for index in admitted_maxima):
        raise ValueError("profile bin maximum index is outside the PA window")
    if len(admitted_maxima) < 2:
        raise LunarLimbProfileCoverageError(
            "official LOLA projection did not populate at least two admitted PA bins"
        )

    indices = tuple(sorted(admitted_maxima))
    lower = center - half_width
    upper = center + half_width
    sample_angles = tuple(lower + (index + 0.5) * width for index in indices)
    sample_radii = tuple(admitted_maxima[index] for index in indices)
    if any(
        radius < _LOLA_INNER_RELIEF_RADIUS_KM - _LOLA_RELIEF_BOUND_TOLERANCE_KM
        for radius in sample_radii
    ):
        raise LunarLimbProfileCoverageError(
            "official LOLA projection did not demonstrate the admitted R-H "
            "physical silhouette floor in every populated PA bin"
        )
    if any(
        radius > _LOLA_OUTER_RELIEF_RADIUS_KM + _LOLA_RELIEF_BOUND_TOLERANCE_KM
        for radius in sample_radii
    ):
        raise LunarLimbResourceError(
            "official LOLA projection exceeds Moira's admitted absolute-relief bound"
        )
    required_first = lower + 0.5 * width
    required_last = upper - 0.5 * width
    if (
        sample_angles[0] > required_first + 1.0e-12
        or sample_angles[-1] < required_last - 1.0e-12
    ):
        raise LunarLimbProfileCoverageError(
            "official LOLA projection does not cover both requested PA boundaries: "
            f"sampled [{sample_angles[0]}, {sample_angles[-1]}], required "
            f"[{required_first}, {required_last}] deg"
        )
    largest_gap = max(
        right - left for left, right in zip(sample_angles, sample_angles[1:])
    )
    if largest_gap > max_gap + 1.0e-12:
        raise LunarLimbProfileCoverageError(
            f"official LOLA projection contains a {largest_gap} deg PA gap, "
            f"exceeding the admitted {max_gap} deg"
        )
    result = LunarLimbProfileSlice(
        jd_ut1=epoch,
        position_angles_unwrapped_deg=sample_angles,
        radii_km=sample_radii,
        bin_width_deg=width,
        max_interpolation_gap_deg=max_gap,
        source_point_count=source_point_count,
        asset_urls=tuple(asset_urls),
    )
    # Construction proves the centre as well as both boundaries and every
    # intervening gap, so later pure evaluation cannot discover a guessed
    # spatial-coverage hole inside this slice.
    result.radius_km_at(center)
    return result


def _merge_profile_bin_maxima(
    maxima: dict[int, float],
    projected_position_angles_deg: Sequence[float],
    projected_radii_km: Sequence[float],
    *,
    position_angle_center_deg: float,
    position_angle_half_width_deg: float,
    bin_width_deg: float,
    bin_count: int,
) -> int:
    """Merge one projected tile into exact half-open PA-bin maxima."""

    if len(projected_position_angles_deg) != len(projected_radii_km):
        raise ValueError(
            "projected position-angle and radius vectors must have equal length"
        )
    lower = position_angle_center_deg - position_angle_half_width_deg
    upper = position_angle_center_deg + position_angle_half_width_deg
    center_normalized = position_angle_center_deg % 360.0
    point_count = 0
    for raw_pa, raw_radius in zip(
        projected_position_angles_deg,
        projected_radii_km,
    ):
        pa = _finite_float("projected_position_angle_deg", raw_pa)
        radius = _finite_float("projected_radius_km", raw_radius)
        point_count += 1
        if radius <= 0.0:
            raise ValueError("projected lunar radii must be positive")
        delta = ((pa % 360.0 - center_normalized + 180.0) % 360.0) - 180.0
        unwrapped = position_angle_center_deg + delta
        # This second admission check, after the native coarse filter, owns the
        # exact half-open bin doctrine used by the immutable public profile.
        if unwrapped < lower or unwrapped >= upper:
            continue
        if radius > (
            _LOLA_OUTER_RELIEF_RADIUS_KM + _LOLA_RELIEF_BOUND_TOLERANCE_KM
        ):
            raise LunarLimbResourceError(
                "official LOLA projection exceeds Moira's admitted "
                "absolute-relief bound"
            )
        bin_index = math.floor((unwrapped - lower) / bin_width_deg)
        if 0 <= bin_index < bin_count:
            previous = maxima.get(bin_index)
            if previous is None or radius > previous:
                maxima[bin_index] = radius
    return point_count


def _profile_slice_from_projected_radii(
    *,
    jd_ut1: float,
    projected_position_angles_deg: Sequence[float],
    projected_radii_km: Sequence[float],
    position_angle_center_deg: float,
    position_angle_half_width_deg: float,
    bin_width_deg: float,
    max_interpolation_gap_deg: float,
    source_point_count: int,
    asset_urls: Sequence[str],
) -> LunarLimbProfileSlice:
    """Select one perspective-equivalent maximum per half-open PA bin."""

    epoch = _finite_float("jd_ut1", jd_ut1)
    center = _finite_float("position_angle_center_deg", position_angle_center_deg)
    half_width = _finite_float(
        "position_angle_half_width_deg", position_angle_half_width_deg
    )
    width = _finite_float("bin_width_deg", bin_width_deg)
    max_gap = _finite_float(
        "max_interpolation_gap_deg", max_interpolation_gap_deg
    )
    if half_width <= 0.0 or half_width >= 180.0:
        raise ValueError("position_angle_half_width_deg must be in (0, 180)")
    if width <= 0.0 or width >= 2.0 * half_width:
        raise ValueError("bin_width_deg must be positive and narrower than the profile window")
    span = 2.0 * half_width
    bin_count_float = span / width
    bin_count = round(bin_count_float)
    if bin_count < 2 or not math.isclose(
        bin_count_float,
        bin_count,
        rel_tol=0.0,
        abs_tol=1e-10,
    ):
        raise ValueError(
            "the full position-angle window must contain an integer number of bins"
        )

    pas = tuple(
        _finite_float("projected_position_angle_deg", value)
        for value in projected_position_angles_deg
    )
    radii = tuple(
        _finite_float("projected_radius_km", value) for value in projected_radii_km
    )
    if len(pas) != len(radii):
        raise ValueError("projected position-angle and radius vectors must have equal length")
    if source_point_count != len(pas):
        raise ValueError("source_point_count must equal the projected point count")

    maxima: dict[int, float] = {}
    _merge_profile_bin_maxima(
        maxima,
        pas,
        radii,
        position_angle_center_deg=center,
        position_angle_half_width_deg=half_width,
        bin_width_deg=width,
        bin_count=bin_count,
    )

    return _profile_slice_from_bin_maxima(
        jd_ut1=epoch,
        maxima=maxima,
        position_angle_center_deg=center,
        position_angle_half_width_deg=half_width,
        bin_width_deg=width,
        max_interpolation_gap_deg=max_gap,
        source_point_count=source_point_count,
        asset_urls=tuple(asset_urls),
    )


def _merge_loaded_lola_tile_profile_maxima(
    maxima: dict[int, float],
    *,
    tile: _LolaTile,
    url: str,
    observer_context: _ObserverLimbContext,
    position_angle_center_deg: float,
    position_angle_half_width_deg: float,
    bin_width_deg: float,
    bin_count: int,
) -> int:
    """Fuse projection/binning for one tile into one slice accumulator."""

    observer_vector = moira_native.Vec3(*observer_context.observer_dir_moon)
    east_vector = moira_native.Vec3(*observer_context.sky_east_moon)
    north_vector = moira_native.Vec3(*observer_context.sky_north_moon)
    lower = position_angle_center_deg - position_angle_half_width_deg
    upper = position_angle_center_deg + position_angle_half_width_deg
    try:
        reduced = tile.point_cloud.project_max_radius_per_pa_bin(
            observer_vector,
            east_vector,
            north_vector,
            lower,
            upper,
            bin_width_deg,
            observer_context.observer_distance_km,
            _LOLA_INNER_RELIEF_RADIUS_KM,
            _LOLA_OUTER_RELIEF_RADIUS_KM,
        )
    except ValueError as exc:
        raise LunarLimbResourceError(
            f"LOLA tile violates the admitted radial relief shell: {url}"
        ) from exc
    if int(reduced.bin_count) != bin_count:
        raise LunarLimbResourceError(
            "native LOLA reducer returned a bin-count contract mismatch"
        )
    source_point_count = int(reduced.admitted_source_point_count)
    reduced_indices = tuple(reduced.bin_indices)
    reduced_centers = tuple(reduced.bin_centers_unwrapped_deg)
    reduced_radii = tuple(reduced.radii_km)
    if not (
        len(reduced_indices) == len(reduced_centers) == len(reduced_radii)
    ):
        raise LunarLimbResourceError(
            "native LOLA reducer returned mismatched sparse result vectors"
        )
    for raw_index, raw_center, raw_radius in zip(
        reduced_indices,
        reduced_centers,
        reduced_radii,
    ):
        index = int(raw_index)
        bin_center = _finite_float("native LOLA bin centre", raw_center)
        radius = _finite_float("native LOLA bin maximum", raw_radius)
        if not 0 <= index < bin_count:
            raise LunarLimbResourceError(
                "native LOLA reducer returned an out-of-range bin index"
            )
        expected_center = lower + (index + 0.5) * bin_width_deg
        if not math.isclose(
            bin_center,
            expected_center,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise LunarLimbResourceError(
                "native LOLA reducer returned a bin-centre contract mismatch"
            )
        previous = maxima.get(index)
        if previous is None or radius > previous:
            maxima[index] = radius
    return source_point_count


def _profile_slice_from_loaded_lola_tiles(
    *,
    jd_ut1: float,
    observer_context: _ObserverLimbContext,
    position_angle_center_deg: float,
    position_angle_half_width_deg: float,
    bin_width_deg: float,
    max_interpolation_gap_deg: float,
    tile_urls: Sequence[str],
    loaded_tiles: Mapping[str, _LolaTile],
    expected_lola_assets: Mapping[str, LunarLimbAssetIdentity] | None,
) -> LunarLimbProfileSlice:
    """Project union tiles incrementally, retaining only per-bin maxima."""

    span = 2.0 * position_angle_half_width_deg
    bin_count_float = span / bin_width_deg
    bin_count = round(bin_count_float)
    if bin_count < 2 or not math.isclose(
        bin_count_float,
        bin_count,
        rel_tol=0.0,
        abs_tol=1.0e-10,
    ):
        raise ValueError(
            "the full position-angle window must contain an integer number of bins"
        )
    maxima: dict[int, float] = {}
    source_point_count = 0
    admitted_urls: list[str] = []
    for url in tile_urls:
        if expected_lola_assets is not None and url not in expected_lola_assets:
            raise LunarLimbResourceError(
                "LOLA tile URL lacks an externally admitted byte identity: "
                f"{url}"
            )
        try:
            tile = loaded_tiles[url]
        except KeyError as exc:
            raise LunarLimbResourceError(
                f"builder-local LOLA tile was not loaded for {url}"
            ) from exc
        admitted_urls.append(url)
        source_point_count += _merge_loaded_lola_tile_profile_maxima(
            maxima,
            tile=tile,
            url=url,
            observer_context=observer_context,
            position_angle_center_deg=position_angle_center_deg,
            position_angle_half_width_deg=position_angle_half_width_deg,
            bin_width_deg=bin_width_deg,
            bin_count=bin_count,
        )
    return _profile_slice_from_bin_maxima(
        jd_ut1=jd_ut1,
        maxima=maxima,
        position_angle_center_deg=position_angle_center_deg,
        position_angle_half_width_deg=position_angle_half_width_deg,
        bin_width_deg=bin_width_deg,
        max_interpolation_gap_deg=max_interpolation_gap_deg,
        source_point_count=source_point_count,
        asset_urls=tuple(dict.fromkeys(admitted_urls)),
    )


def _lola_predecode_node_limit(
    cumulative_node_points: int,
    cumulative_projection_work: int,
    slice_use_count: int,
) -> int:
    """Return the lawful next COPC node upper bound before any decode."""

    for name, value in (
        ("cumulative_node_points", cumulative_node_points),
        ("cumulative_projection_work", cumulative_projection_work),
        ("slice_use_count", slice_use_count),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
    if cumulative_node_points < 0 or cumulative_projection_work < 0:
        raise ValueError("cumulative LOLA work counters cannot be negative")
    if slice_use_count <= 0:
        raise ValueError("slice_use_count must be positive")
    remaining_node_points = (
        _MAX_CONTACT_LOLA_NODE_POINTS_TOTAL - cumulative_node_points
    )
    remaining_projection_work = (
        _MAX_CONTACT_LOLA_POINT_PROJECTION_WORK
        - cumulative_projection_work
    )
    limit = min(
        _MAX_CONTACT_LOLA_POINTS_PER_TILE,
        remaining_node_points,
        remaining_projection_work // slice_use_count,
    )
    if limit <= 0:
        raise LunarLimbResourceError(
            "LOLA profile exhausted its admitted node/projection work bound"
        )
    return limit


def build_lola_rdr_lunar_limb_event_profile(
    jd_ut1_samples: Sequence[float],
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
    position_angle_center_deg: float,
    *,
    reader: KernelReader,
    position_angle_half_width_deg: float = _LIMB_PA_WINDOW_DEG,
    pa_bin_width_deg: float = _LIMB_BIN_WIDTH_DEG,
    max_pa_interpolation_gap_deg: float | None = None,
    max_time_interpolation_gap_days: float | None = None,
    lola_query_half_width_km: float = _DEFAULT_LOLA_QUERY_HALF_WIDTH_KM,
    expected_lola_assets: Sequence[LunarLimbAssetIdentity] | None = None,
) -> LunarLimbEventProfile:
    """Materialize a Moira-derived event profile from official LOLA RDR spots.

    Resource discovery, network access, SPICE orientation, native point-cloud
    filtering, and sky-plane projection occur only here. The returned profile
    owns defensive tuples and performs only bounded piecewise-linear PA/time
    interpolation; evaluating it never performs I/O or calls SPICE.

    Each profile sample is the maximum finite-distance equivalent lunar radius
    in one explicit half-open unwrapped PA bin, assigned to that bin's centre.
    The equivalent radius preserves the actual observer-centre/observer-surface
    angular separation through ``asin(radius / observer_distance)``. Adjacent
    populated bin-centre samples and event epochs are reconstructed linearly;
    no exact sub-bin topography is claimed. No convex hull or mean-radius
    fallback is admitted by this contact-facing product.

    Acquisition assumes the continuous radial surface declared by the source
    relief policy. Every cap capable of competing with the ``R-H`` silhouette
    floor is admitted, and every decoded point must remain inside that radial
    shell. COPC tiles are decoded one at a time, reused across all profile
    slices that need them, reduced natively to sparse bin maxima, and released
    before the next tile is materialized.
    ``lola_query_half_width_km`` is retained as a caller-requested minimum
    chord margin; it may widen the relief-derived cap but can never narrow it.

    An external validation fixture may supply ``expected_lola_assets``. In
    that mode the resolved tile URL set must match exactly, and every cached or
    downloaded tile must pass its declared byte length and SHA-256 before the
    COPC reader is opened. Multi-slice callers must also supply an independent
    ``max_time_interpolation_gap_days`` policy; the builder never blesses its
    own widest observed gap as an accuracy bound.
    """

    try:
        sample_count = len(jd_ut1_samples)
    except TypeError as exc:
        raise TypeError("jd_ut1_samples must be a sized sequence") from exc
    if sample_count == 0:
        raise ValueError("jd_ut1_samples must contain at least one event epoch")
    if sample_count > MAX_LUNAR_LIMB_EVENT_PROFILE_SLICES:
        raise ValueError(
            f"jd_ut1_samples contains {sample_count} epochs, exceeding the "
            f"admitted bound {MAX_LUNAR_LIMB_EVENT_PROFILE_SLICES}"
        )
    epochs = tuple(_finite_float("jd_ut1_sample", value) for value in jd_ut1_samples)
    if any(right <= left for left, right in zip(epochs, epochs[1:])):
        raise ValueError("jd_ut1_samples must be strictly increasing")
    latitude = _finite_float("observer_lat", observer_lat)
    longitude = _finite_float("observer_lon", observer_lon)
    elevation = _finite_float("observer_elev_m", observer_elev_m)
    center = _finite_float("position_angle_center_deg", position_angle_center_deg)
    half_width = _finite_float(
        "position_angle_half_width_deg", position_angle_half_width_deg
    )
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("observer_lat must be in [-90, 90]")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("observer_lon must be in [-180, 180]")
    if half_width <= 0.0 or half_width > _LIMB_PA_WINDOW_DEG:
        raise ValueError(
            "position_angle_half_width_deg must be in "
            f"(0, {_LIMB_PA_WINDOW_DEG}] for bounded LOLA tile discovery"
        )
    requested_query_width = _finite_float(
        "lola_query_half_width_km", lola_query_half_width_km
    )
    if requested_query_width < _MIN_CONTACT_QUERY_HALF_WIDTH_KM:
        raise ValueError(
            "lola_query_half_width_km must be at least "
            f"{_MIN_CONTACT_QUERY_HALF_WIDTH_KM} km for contact profiles."
        )
    bin_width = _finite_float("pa_bin_width_deg", pa_bin_width_deg)
    if bin_width <= 0.0 or bin_width >= 2.0 * half_width:
        raise ValueError("pa_bin_width_deg must be positive and narrower than the profile window")
    bin_count_float = 2.0 * half_width / bin_width
    if round(bin_count_float) < 2 or not math.isclose(
        bin_count_float,
        round(bin_count_float),
        rel_tol=0.0,
        abs_tol=1e-10,
    ):
        raise ValueError(
            "the full position-angle window must contain an integer number of bins"
        )
    bin_count = int(round(bin_count_float))
    if max_pa_interpolation_gap_deg is None:
        pa_gap = bin_width * _DEFAULT_PROFILE_MAX_PA_GAP_FACTOR
    else:
        pa_gap = _finite_float(
            "max_pa_interpolation_gap_deg", max_pa_interpolation_gap_deg
        )
    if max_time_interpolation_gap_days is None:
        if len(epochs) > 1:
            raise ValueError(
                "max_time_interpolation_gap_days is required for a "
                "multi-slice profile"
            )
        time_gap = 0.0
    else:
        time_gap = _finite_float(
            "max_time_interpolation_gap_days", max_time_interpolation_gap_days
        )
    if pa_gap <= 0.0 or pa_gap >= 360.0:
        raise ValueError("max_pa_interpolation_gap_deg must be in (0, 360)")
    if time_gap < 0.0 or (len(epochs) > 1 and time_gap == 0.0):
        raise ValueError(
            "max_time_interpolation_gap_days must be positive for a multi-slice profile"
        )
    expected_asset_map = _expected_lola_asset_map(expected_lola_assets)

    if reader is None:
        raise TypeError("reader must be an explicit content-identified DE441 reader")
    cache_root = _default_cache_root()
    orientation_paths = _ensure_contact_orientation_kernels_loaded(cache_root)
    contexts: list[_ObserverLimbContext] = []
    translation_labels: set[str] = set()
    for epoch in epochs:
        context, translation_label, _orientation_et = _reader_bound_observer_limb_context(
            epoch,
            latitude,
            longitude,
            elevation,
            reader,
        )
        translation_labels.add(translation_label)
        contexts.append(context)

    context_tile_urls = tuple(
        _lola_envelope_tile_urls(
            context,
            center,
            half_width,
            cache_root,
            requested_query_width,
        )
        for context in contexts
    )
    resolved_tile_urls = tuple(
        dict.fromkeys(
            url for urls_for_context in context_tile_urls for url in urls_for_context
        )
    )
    _admit_expected_lola_tile_urls(resolved_tile_urls, expected_asset_map)
    if len(resolved_tile_urls) > _MAX_CONTACT_LOLA_TILES:
        raise LunarLimbResourceError(
            f"LOLA profile resolves {len(resolved_tile_urls)} unique tiles, "
            f"exceeding the admitted bound {_MAX_CONTACT_LOLA_TILES}"
        )
    projection_work = sum(len(urls) for urls in context_tile_urls)
    if projection_work > _MAX_CONTACT_LOLA_TILE_PROJECTIONS:
        raise LunarLimbResourceError(
            f"LOLA profile requires {projection_work} tile projections, "
            f"exceeding the admitted work bound "
            f"{_MAX_CONTACT_LOLA_TILE_PROJECTIONS}"
        )

    # All slices share one Moon-XYZ AABB enclosing the union of their sampled
    # smooth-limb locus and the complete finite-perspective relief shell.  The
    # inner shell R-H is only a silhouette-completeness floor: real valley
    # maxima remain unchanged, and missing PA bins still fail closed.
    query_bounds = _lola_common_cartesian_query_bounds(
        contexts,
        center,
        half_width,
        requested_query_width,
    )

    slice_maxima: list[dict[int, float]] = [{} for _ in contexts]
    slice_source_point_counts = [0 for _ in contexts]
    slice_asset_urls: list[list[str]] = [[] for _ in contexts]
    cumulative_node_points = 0
    cumulative_projection_work = 0
    for url in resolved_tile_urls:
        context_indices = tuple(
            index
            for index, urls_for_context in enumerate(context_tile_urls)
            if url in urls_for_context
        )
        if not context_indices:
            raise LunarLimbResourceError(
                f"resolved LOLA tile is unused by every profile slice: {url}"
            )
        max_decompression_points = _lola_predecode_node_limit(
            cumulative_node_points,
            cumulative_projection_work,
            len(context_indices),
        )
        expected_asset = (
            None if expected_asset_map is None else expected_asset_map.get(url)
        )
        if expected_asset_map is not None and expected_asset is None:
            raise LunarLimbResourceError(
                "LOLA tile URL lacks an externally admitted byte identity: "
                f"{url}"
            )
        tile = _load_lola_tile_cartesian_region(
            url,
            str(cache_root),
            query_bounds,
            None if expected_asset is None else expected_asset.byte_length,
            None if expected_asset is None else expected_asset.sha256,
            max_points=_MAX_CONTACT_LOLA_POINTS_PER_TILE,
            max_decompression_points=max_decompression_points,
        )
        try:
            node_upper_bound = tile.decompression_point_upper_bound
            if node_upper_bound is None:
                raise LunarLimbResourceError(
                    "contact LOLA tile lacks its COPC node upper-bound witness"
                )
            cumulative_node_points += node_upper_bound
            cumulative_projection_work += node_upper_bound * len(context_indices)
            if cumulative_node_points > _MAX_CONTACT_LOLA_NODE_POINTS_TOTAL:
                raise LunarLimbResourceError(
                    "LOLA profile exceeds its cumulative COPC node bound"
                )
            if (
                cumulative_projection_work
                > _MAX_CONTACT_LOLA_POINT_PROJECTION_WORK
            ):
                raise LunarLimbResourceError(
                    "LOLA profile exceeds its cumulative point-projection work bound"
                )
            for index in context_indices:
                slice_source_point_counts[index] += (
                    _merge_loaded_lola_tile_profile_maxima(
                        slice_maxima[index],
                        tile=tile,
                        url=url,
                        observer_context=contexts[index],
                        position_angle_center_deg=center,
                        position_angle_half_width_deg=half_width,
                        bin_width_deg=bin_width,
                        bin_count=bin_count,
                    )
                )
                slice_asset_urls[index].append(url)
        finally:
            # Each bounded native cloud is reused across every slice that needs
            # it, then released before the next union tile is decoded.
            del tile

    slices = [
        _profile_slice_from_bin_maxima(
            jd_ut1=epoch,
            maxima=slice_maxima[index],
            position_angle_center_deg=center,
            position_angle_half_width_deg=half_width,
            bin_width_deg=bin_width,
            max_interpolation_gap_deg=pa_gap,
            source_point_count=slice_source_point_counts[index],
            asset_urls=tuple(slice_asset_urls[index]),
        )
        for index, epoch in enumerate(epochs)
    ]
    all_tile_urls = [
        url
        for urls_for_context in context_tile_urls
        for url in urls_for_context
    ]

    if len(translation_labels) != 1:
        raise LunarLimbResourceError(
            "lunar-limb event profile crosses an ambiguous DE441 reader identity"
        )
    ordered_urls = tuple(
        dict.fromkeys(
            (
                *(
                    _NAIF_KERNELS[name]
                    for name in _CONTACT_ORIENTATION_KERNEL_NAMES
                ),
                *all_tile_urls,
            )
        )
    )
    orientation_path_by_url = {
        _NAIF_KERNELS[name]: path
        for name, path in zip(_CONTACT_ORIENTATION_KERNEL_NAMES, orientation_paths)
    }
    assets = tuple(
        _asset_identity(
            url,
            orientation_path_by_url.get(
                url,
                cache_root / "lola_tiles" / Path(url).name,
            ),
        )
        for url in ordered_urls
    )
    source = LunarLimbProfileSource(
        authority="USGS Astrogeology LOLA and NAIF/JPL SPICE",
        collection=_LOLA_COLLECTION,
        coordinate_frame=(
            "USGS IAU_2015MoonXYZ Cartesian metres in the DE421 ME-aligned "
            "lunar cartographic frame"
        ),
        translation_model=(
            "reader-bound DE441/LE441 physical reception light cone: "
            + next(iter(translation_labels))
        ),
        orientation_model=(
            "NAIF moon_pa_de440_200625.bpc at retarded emission epoch; "
            + _CONTACT_ORIENTATION_FRAME
        ),
        surface_frame_model=_CONTACT_SURFACE_FRAME,
        orientation_alignment_max_m=_CONTACT_FRAME_ALIGNMENT_MAX_M,
        orientation_alignment_interval=_CONTACT_FRAME_ALIGNMENT_INTERVAL,
        reference_radius_km=MOON_RADIUS_KM,
        spatial_query_half_width_km=query_bounds.maximum_half_extent_km,
        spatial_query_bounds_moon_xyz_km=(
            query_bounds.minimum_km,
            query_bounds.maximum_km,
        ),
        relief_observation_sources=(
            _NASA_LRO_HIGHEST_POINT_URL,
            _NASA_LOLA_TOPOGRAPHY_SCALE_URL,
        ),
        relief_observed_highest_km=_NASA_LRO_HIGHEST_POINT_KM,
        relief_observed_approximate_absolute_km=(
            _NASA_LOLA_APPROXIMATE_ABSOLUTE_RELIEF_KM
        ),
        relief_acquisition_policy=_LOLA_RELIEF_ACQUISITION_POLICY_ID,
        max_absolute_relief_km=_LOLA_MAX_ABSOLUTE_RELIEF_KM,
        assets=assets,
    )
    return LunarLimbEventProfile(
        source=source,
        slices=tuple(slices),
        max_time_interpolation_gap_days=time_gap,
        observer_latitude_deg=latitude,
        observer_longitude_deg=longitude,
        observer_elevation_m=elevation,
    )




def _sample_lola_limb_elevation_m(
    lon_deg: float,
    lat_deg: float,
    observer_context: _ObserverLimbContext,
    position_angle_deg: float,
    cache_root: Path,
    query_half_width_km: float,
) -> float:
    """
    Sample LOLA elevation near the limb using native substrate kernels.
    """
    if moira_native is None:
        raise ImportError("Native Moira backend required for LOLA processing.")

    all_east, all_north, all_radius, all_pa, _ = _collect_lola_projected_points(
        lon_deg,
        lat_deg,
        observer_context,
        position_angle_deg,
        cache_root,
        query_half_width_km,
    )
        
    if not all_east:
        return 0.0
        
    # 3. Global Binning
    bins = moira_native.bin_by_position_angle(all_pa, position_angle_deg, _LIMB_BIN_WIDTH_DEG)
    
    # 4. Lexsort and selection of max radius per bin
    indices = moira_native.lexsort_by_bin_and_radius(bins, all_radius)
    
    # Extract the point with maximum radius for each bin
    # Since lexsort is (bin, radius) ascending, the last occurrence of each bin is the max
    best_indices: list[int] = []
    if len(indices) > 0:
        for i in range(len(indices) - 1):
            if bins[indices[i]] != bins[indices[i+1]]:
                best_indices.append(indices[i])
        best_indices.append(indices[-1])
        
    hull_pts = [moira_native.Point2D(all_east[i], all_north[i]) for i in best_indices]
    
    # 5. Native Convex Hull
    hull = moira_native.convex_hull_2d(hull_pts)
    
    # 6. Native Ray-Hull Intersection
    silhouette_radius_km = moira_native.ray_hull_intersection(hull, position_angle_deg, MOON_RADIUS_KM)
    
    return silhouette_radius_km * 1000.0 - _LOLA_MEAN_RADIUS_M


def official_lunar_limb_profile_adjustment(
    jd_ut: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
    position_angle_deg: float,
    moon_distance_km: float,
    *,
    lola_query_half_width_km: float = _DEFAULT_LOLA_QUERY_HALF_WIDTH_KM,
) -> float:
    """
    Return an official-source lunar-limb correction in angular degrees.

    The current implementation uses:
    - NAIF lunar orientation kernels for body-frame geometry
    - official USGS/LOLA COPC tiles for limb topography

    Runtime policy:
    - `lola_query_half_width_km` controls the bounded COPC neighborhood sampled
      around the smooth-limb target. This is an explicit performance policy, not
      a hidden astronomical model change.
    - widths below `250 km` are not admitted because narrower windows failed the
      oracle safety sweep on the current validation corpus.

    """
    if lola_query_half_width_km < _MIN_LOLA_QUERY_HALF_WIDTH_KM:
        raise ValueError(
            f"lola_query_half_width_km must be at least {_MIN_LOLA_QUERY_HALF_WIDTH_KM} km."
        )

    cache_root = _default_cache_root()
    _ensure_kernels_loaded(cache_root)

    observer_context = _observer_limb_context(
        _jd_ut_to_et(jd_ut),
        observer_lat,
        observer_lon,
        observer_elev_m,
    )
    limb_lon_deg, limb_lat_deg = _limb_point_lon_lat_from_context(
        observer_context,
        position_angle_deg,
    )
    elevation_m = _sample_lola_limb_elevation_m(
        limb_lon_deg,
        limb_lat_deg,
        observer_context,
        position_angle_deg,
        cache_root,
        lola_query_half_width_km,
    )

    base_radius_deg = math.degrees(math.asin(max(-1.0, min(1.0, MOON_RADIUS_KM / moon_distance_km))))
    adjusted_radius_deg = math.degrees(
        math.asin(
            max(
                -1.0,
                min(1.0, (MOON_RADIUS_KM + elevation_m / 1000.0) / moon_distance_km),
            )
        )
    )
    return adjusted_radius_deg - base_radius_deg
