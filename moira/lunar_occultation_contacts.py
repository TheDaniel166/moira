"""Lunar-topography-conditioned stellar occultation contact chronology.

This module owns one deliberately narrow product: the ordered sequence of
disappearance, reappearance, and limiting-tangency instants predicted by a
prepared lunar-limb profile at one terrestrial observing site.  It does not
replace the spherical-limb :class:`moira.occultations.LunarOccultation`
product, and it does not turn a profile-conditioned prediction into an
observed IOTA timing.

The governing scalar is signed angular clearance (separation minus admitted
lunar-profile radius).  Positive clearance means the star is visible; negative
clearance means it lies behind the admitted lunar profile.  Crossings therefore
have an unambiguous direction, while
a same-sign zero is represented explicitly as a tangency.  Profile loading,
network access, and tile selection must be completed before this solver is
entered; objective evaluation is a pure computational boundary. Stellar
targets are named, epoch-bound ICRS vessels rather than ambiguous ecliptic
longitude/latitude pairs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib
import math
from numbers import Real
from typing import TYPE_CHECKING, Callable, Protocol, Sequence, runtime_checkable

from .julian import (
    CalendarDateTime,
    J2000,
    _ut1_to_utc,
    calendar_datetime_from_jd,
    datetime_from_jd,
)


_SECONDS_PER_DAY = 86_400.0
_AU_KM = 149_597_870.7
_PARSEC_AU = 206_264.80624709636
_MAS_TO_RAD = math.radians(1.0 / 3_600_000.0)
_JULIAN_YEAR_SECONDS = 31_557_600.0
MAX_LUNAR_CONTACT_PROFILE_SLICES = 4096

if TYPE_CHECKING:
    from .lunar_limb import LunarLimbAssetIdentity


class LunarContactKind(str, Enum):
    """Physical transition represented by one topographic contact instant."""

    DISAPPEARANCE = "disappearance"
    REAPPEARANCE = "reappearance"
    TANGENCY = "tangency"


class LunarVisibilityState(str, Enum):
    """Visibility state immediately to either side of a contact."""

    VISIBLE = "visible"
    OCCULTED = "occulted"


class LunarContactGeometryMode(str, Enum):
    """Provenance class for the geometry that generated a chronology."""

    READER_BOUND_DE441 = "reader_bound_de441"
    CALLER_INJECTED = "caller_injected"


def _finite_real(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _nonempty_text(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    result = value.strip()
    if not result:
        raise ValueError(f"{name} must not be empty")
    return result


@dataclass(frozen=True, slots=True)
class LunarContactStar:
    """Catalog-bound astrometric target for lunar contact geometry.

    ``barycentric_icrf_unit`` is the geometric unit direction from the Solar
    System barycentre at ``reference_epoch_jd_tt``.  The named constructor
    :func:`lunar_contact_star_at` obtains that direction by propagating the
    sovereign registry's ICRS position and proper motion to the requested TT
    epoch.  A positive catalog parallax makes the target finite-distance;
    ``None`` is an explicit infinite-distance admission rather than an
    ambient zero-parallax assumption. ``barycentric_distance_km`` is the
    distance of that same linearly propagated Cartesian position at the
    reference epoch; catalog parallax remains visible as source provenance
    and is not incorrectly reused as though distance were epoch-invariant.
    """

    name: str
    nomenclature: str
    catalog_source: str
    catalog_identifier: str
    lookup_kind: str
    reference_epoch_jd_tt: float
    barycentric_icrf_unit: tuple[float, float, float]
    parallax_mas: float | None
    barycentric_distance_km: float | None
    coordinate_frame: str = "ICRS"
    origin: str = "SOLAR_SYSTEM_BARYCENTER"
    reference_time_scale: str = "TT"
    direction_semantics: str = "GEOMETRIC_BARYCENTRIC_UNIT_DIRECTION"
    propagation_model: str = "MOIRA_SOVEREIGN_LINEAR_SPACE_MOTION"

    def __post_init__(self) -> None:
        name = _nonempty_text("name", self.name)
        nomenclature = _nonempty_text("nomenclature", self.nomenclature)
        catalog_source = _nonempty_text("catalog_source", self.catalog_source)
        catalog_identifier = _nonempty_text(
            "catalog_identifier", self.catalog_identifier
        )
        lookup_kind = _nonempty_text("lookup_kind", self.lookup_kind)
        reference_epoch = _finite_real(
            "reference_epoch_jd_tt", self.reference_epoch_jd_tt
        )
        if not isinstance(self.barycentric_icrf_unit, tuple):
            raise TypeError("barycentric_icrf_unit must be a 3-tuple")
        if len(self.barycentric_icrf_unit) != 3:
            raise ValueError("barycentric_icrf_unit must contain three components")
        direction = tuple(
            _finite_real(f"barycentric_icrf_unit[{index}]", value)
            for index, value in enumerate(self.barycentric_icrf_unit)
        )
        norm = math.sqrt(sum(value * value for value in direction))
        if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=2.0e-12):
            raise ValueError("barycentric_icrf_unit must be normalized")
        direction = tuple(value / norm for value in direction)
        parallax = self.parallax_mas
        distance = self.barycentric_distance_km
        if parallax is not None:
            parallax = _finite_real("parallax_mas", parallax)
            if parallax <= 0.0:
                raise ValueError("parallax_mas must be positive when supplied")
            if distance is None:
                raise ValueError(
                    "barycentric_distance_km is required with catalog parallax"
                )
            distance = _finite_real("barycentric_distance_km", distance)
            if distance <= 0.0:
                raise ValueError("barycentric_distance_km must be positive")
        elif distance is not None:
            raise ValueError(
                "barycentric_distance_km must be None without catalog parallax"
            )
        if self.coordinate_frame != "ICRS":
            raise ValueError("coordinate_frame must be ICRS")
        if self.origin != "SOLAR_SYSTEM_BARYCENTER":
            raise ValueError("origin must be SOLAR_SYSTEM_BARYCENTER")
        if self.reference_time_scale != "TT":
            raise ValueError("reference_time_scale must be TT")
        if self.direction_semantics != "GEOMETRIC_BARYCENTRIC_UNIT_DIRECTION":
            raise ValueError(
                "direction_semantics must identify a geometric barycentric unit direction"
            )
        if self.propagation_model != "MOIRA_SOVEREIGN_LINEAR_SPACE_MOTION":
            raise ValueError(
                "propagation_model must identify Moira sovereign linear space motion"
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "nomenclature", nomenclature)
        object.__setattr__(self, "catalog_source", catalog_source)
        object.__setattr__(self, "catalog_identifier", catalog_identifier)
        object.__setattr__(self, "lookup_kind", lookup_kind)
        object.__setattr__(self, "reference_epoch_jd_tt", reference_epoch)
        object.__setattr__(self, "barycentric_icrf_unit", direction)
        object.__setattr__(self, "parallax_mas", parallax)
        object.__setattr__(self, "barycentric_distance_km", distance)

    @property
    def parallax_model(self) -> str:
        if self.parallax_mas is None:
            return "INFINITE_DISTANCE_NO_CATALOG_PARALLAX"
        return "FINITE_DISTANCE_FROM_CATALOG_PARALLAX"


def lunar_contact_star_at(name: str, reference_epoch_jd_tt: float) -> LunarContactStar:
    """Construct a named lunar-contact target from Moira's star registry.

    The registry direction is propagated from its catalog epoch to the
    supplied TT epoch before it is frozen into the result.  No network access
    or secondary astrometry engine participates in this construction.
    """

    from .star_types import DEFAULT_FIXED_STAR_POLICY
    from .stars import _propagate_icrs_vector, _resolve_star_record

    epoch = _finite_real("reference_epoch_jd_tt", reference_epoch_jd_tt)
    record, lookup_kind = _resolve_star_record(
        name,
        DEFAULT_FIXED_STAR_POLICY.lookup,
    )
    direction = _propagate_icrs_vector(record, epoch)
    matching_status = record.provenance.get("matching_status")
    identity_parts = [record.name, record.nomenclature]
    if record.gaia_dr3_id is not None and record.gaia_dr3_id > 0:
        identity_parts.append(f"Gaia DR3 {record.gaia_dr3_id}")
    if isinstance(matching_status, str) and matching_status.strip():
        identity_parts.append(matching_status.strip())
    parallax = (
        record.parallax_mas
        if math.isfinite(record.parallax_mas) and record.parallax_mas > 0.0
        else None
    )
    barycentric_distance_km: float | None = None
    if parallax is not None:
        distance_pc = 1000.0 / parallax
        years = (epoch - J2000) / 365.25
        radial_velocity_pc_per_year = record.radial_velocity_km_s * (
            _JULIAN_YEAR_SECONDS / (_AU_KM * _PARSEC_AU)
        )
        proper_motion_rad_per_year = math.hypot(
            record.pmra_mas_yr,
            record.pmdec_mas_yr,
        ) * _MAS_TO_RAD
        propagated_distance_pc = math.hypot(
            distance_pc + radial_velocity_pc_per_year * years,
            distance_pc * proper_motion_rad_per_year * years,
        )
        if not math.isfinite(propagated_distance_pc) or propagated_distance_pc <= 0.0:
            raise ValueError("propagated catalog-star distance must be positive")
        barycentric_distance_km = propagated_distance_pc * _PARSEC_AU * _AU_KM
    return LunarContactStar(
        name=record.name,
        nomenclature=record.nomenclature,
        catalog_source=(
            "Moira sovereign star registry "
            "(moira/data/star_registry.csv + star_provenance.json)"
        ),
        catalog_identifier="; ".join(identity_parts),
        lookup_kind=lookup_kind,
        reference_epoch_jd_tt=epoch,
        barycentric_icrf_unit=direction,
        parallax_mas=parallax,
        barycentric_distance_km=barycentric_distance_km,
    )


@dataclass(frozen=True, slots=True)
class ContactSearchPolicy:
    """Numerical admission policy for a bounded contact chronology search.

    ``scan_step_seconds`` is also the shortest feature-resolution contract.
    A disappearance/reappearance interval is guaranteed to receive a scan
    sample only when its duration exceeds that step.  Root polishing never
    merges opposite transitions merely because they are close; it rejects
    only contacts closer than the declared chronology resolution.
    ``clearance_tolerance_deg`` is the final residual contract for a
    sign-changing root and must be met together with ``time_tolerance_seconds``;
    same-sign limiting contacts instead use ``tangency_tolerance_deg``.
    ``plateau_tolerance_deg`` classifies the scale of a failed two-sided
    variation witness for diagnostics; closeness within that absolute band is
    never, by itself, evidence that a shallow extremum is non-unique.
    """

    scan_step_seconds: float = 0.01
    time_tolerance_seconds: float = 0.001
    # At modern Julian Days one binary64 step is about 40 microseconds.  With
    # contact-scale angular rates, 1e-9 degree is therefore not an achievable
    # universal residual contract even when the time bracket is fully refined.
    clearance_tolerance_deg: float = 1.0e-7
    tangency_tolerance_deg: float = 2.0e-7
    plateau_tolerance_deg: float = 1.0e-12
    chronology_tolerance_seconds: float = 0.002
    max_refine_iterations: int = 96
    max_scan_samples: int = 250_000

    def __post_init__(self) -> None:
        positive_fields = (
            "scan_step_seconds",
            "time_tolerance_seconds",
            "clearance_tolerance_deg",
            "tangency_tolerance_deg",
            "plateau_tolerance_deg",
            "chronology_tolerance_seconds",
        )
        for name in positive_fields:
            value = _finite_real(name, getattr(self, name))
            if value <= 0.0:
                raise ValueError(f"{name} must be greater than zero")
            object.__setattr__(self, name, value)
        if self.time_tolerance_seconds >= self.scan_step_seconds:
            raise ValueError(
                "time_tolerance_seconds must be smaller than scan_step_seconds"
            )
        if self.clearance_tolerance_deg > self.tangency_tolerance_deg:
            raise ValueError(
                "clearance_tolerance_deg must not exceed tangency_tolerance_deg"
            )
        if self.plateau_tolerance_deg > self.tangency_tolerance_deg:
            raise ValueError(
                "plateau_tolerance_deg must not exceed tangency_tolerance_deg"
            )
        if isinstance(self.max_refine_iterations, bool) or not isinstance(
            self.max_refine_iterations, int
        ):
            raise TypeError("max_refine_iterations must be int")
        if self.max_refine_iterations < 8:
            raise ValueError("max_refine_iterations must be at least 8")
        if isinstance(self.max_scan_samples, bool) or not isinstance(
            self.max_scan_samples, int
        ):
            raise TypeError("max_scan_samples must be int")
        if self.max_scan_samples < 3:
            raise ValueError("max_scan_samples must be at least 3")


@dataclass(frozen=True, slots=True)
class LunarContactProfilePolicy:
    """Admission policy for an event-derived LOLA RDR spot profile.

    ``profile_time_step_seconds`` is an independent upper bound on temporal
    interpolation, not a sample count whose meaning changes with the search
    window. The default PA bin is about 60 m along the lunar reference limb,
    commensurate with the documented nominal LOLA pulse spacing. Requiring the
    PA interpolation gap to equal one bin rejects an unobserved empty bin.
    """

    trajectory_step_seconds: float = 1.0
    position_angle_guard_deg: float = 0.25
    profile_time_step_seconds: float = 15.0
    pa_bin_width_deg: float = 0.002
    max_pa_interpolation_gap_deg: float = 0.002
    lola_query_floor_km: float = 10.0

    def __post_init__(self) -> None:
        for name in (
            "trajectory_step_seconds",
            "position_angle_guard_deg",
            "profile_time_step_seconds",
            "pa_bin_width_deg",
            "max_pa_interpolation_gap_deg",
            "lola_query_floor_km",
        ):
            value = _finite_real(name, getattr(self, name))
            if value <= 0.0:
                raise ValueError(f"{name} must be greater than zero")
            object.__setattr__(self, name, value)
        if self.position_angle_guard_deg >= 10.0:
            raise ValueError("position_angle_guard_deg must be less than 10 degrees")
        if self.pa_bin_width_deg >= 1.0:
            raise ValueError("pa_bin_width_deg must be less than 1 degree")
        if self.max_pa_interpolation_gap_deg < self.pa_bin_width_deg:
            raise ValueError(
                "max_pa_interpolation_gap_deg must admit at least one PA bin"
            )


@dataclass(frozen=True, slots=True)
class ContactGeometry:
    """Instantaneous geometry consumed by the contact chronology solver.

    ``signed_clearance_deg`` follows this module's positive-visible
    convention.  ``position_angle_deg`` is measured at the Moon in the same
    frame used by the supplied limb profile.
    """

    signed_clearance_deg: float
    position_angle_deg: float

    def __post_init__(self) -> None:
        clearance = _finite_real(
            "signed_clearance_deg", self.signed_clearance_deg
        )
        position_angle = _finite_real("position_angle_deg", self.position_angle_deg)
        if not 0.0 <= position_angle < 360.0:
            raise ValueError("position_angle_deg must be in [0, 360)")
        object.__setattr__(self, "signed_clearance_deg", clearance)
        object.__setattr__(self, "position_angle_deg", position_angle)


@runtime_checkable
class LunarLimbContactProfile(Protocol):
    """Prepared, finite-resolution limb profile used during contact search.

    Implementations must be deterministic and must not perform file, network,
    or cache I/O from ``adjustment_deg``.  Resource admission and interpolation
    policy belong to profile construction, before the objective is evaluated.
    """

    source: object

    def angular_adjustment_deg_at(
        self,
        jd_ut1: float,
        position_angle_deg: float,
        moon_distance_km: float,
    ) -> float:
        """Return the signed angular correction to the mean lunar limb."""


class ContactGeometryEvaluator(Protocol):
    """Site-bound, side-effect-free instantaneous geometry evaluator."""

    def __call__(
        self,
        jd_ut1: float,
        profile: LunarLimbContactProfile,
    ) -> ContactGeometry:
        """Evaluate signed clearance and profile-frame position angle."""


@dataclass(frozen=True, slots=True)
class LunarOccultationContact:
    """One immutable profile-conditioned stellar occultation contact."""

    jd_ut1: float
    kind: LunarContactKind
    visibility_before: LunarVisibilityState
    visibility_after: LunarVisibilityState
    position_angle_deg: float
    signed_clearance_deg: float
    bracket_start_jd_ut1: float
    bracket_end_jd_ut1: float

    def __post_init__(self) -> None:
        jd_ut1 = _finite_real("jd_ut1", self.jd_ut1)
        bracket_start = _finite_real(
            "bracket_start_jd_ut1", self.bracket_start_jd_ut1
        )
        bracket_end = _finite_real(
            "bracket_end_jd_ut1", self.bracket_end_jd_ut1
        )
        position_angle = _finite_real("position_angle_deg", self.position_angle_deg)
        clearance = _finite_real(
            "signed_clearance_deg", self.signed_clearance_deg
        )
        if not isinstance(self.kind, LunarContactKind):
            raise TypeError("kind must be LunarContactKind")
        if not isinstance(self.visibility_before, LunarVisibilityState):
            raise TypeError("visibility_before must be LunarVisibilityState")
        if not isinstance(self.visibility_after, LunarVisibilityState):
            raise TypeError("visibility_after must be LunarVisibilityState")
        if bracket_end < bracket_start:
            raise ValueError("contact bracket must be ordered")
        if not bracket_start <= jd_ut1 <= bracket_end:
            raise ValueError("jd_ut1 must lie inside the contact bracket")
        if not 0.0 <= position_angle < 360.0:
            raise ValueError("position_angle_deg must be in [0, 360)")
        expected = {
            LunarContactKind.DISAPPEARANCE: (
                LunarVisibilityState.VISIBLE,
                LunarVisibilityState.OCCULTED,
            ),
            LunarContactKind.REAPPEARANCE: (
                LunarVisibilityState.OCCULTED,
                LunarVisibilityState.VISIBLE,
            ),
        }
        if self.kind is LunarContactKind.TANGENCY:
            if self.visibility_before is not self.visibility_after:
                raise ValueError("a tangency must preserve visibility state")
        elif (
            self.visibility_before,
            self.visibility_after,
        ) != expected[self.kind]:
            raise ValueError("contact kind and visibility transition disagree")
        object.__setattr__(self, "jd_ut1", jd_ut1)
        object.__setattr__(self, "bracket_start_jd_ut1", bracket_start)
        object.__setattr__(self, "bracket_end_jd_ut1", bracket_end)
        object.__setattr__(self, "position_angle_deg", position_angle)
        object.__setattr__(self, "signed_clearance_deg", clearance)

    @property
    def jd_utc(self) -> float:
        """Civil UTC-coded Julian Day obtained by inverting UT1 once."""

        return _ut1_to_utc(self.jd_ut1)

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_utc)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_utc)


@dataclass(frozen=True, slots=True)
class LunarOccultationContactSequence:
    """Validated ordered contacts inside one open UT1 search window."""

    star: LunarContactStar
    observer_latitude_deg: float
    observer_longitude_deg: float
    observer_elevation_m: float
    jd_start_ut1: float
    jd_end_ut1: float
    initial_visibility: LunarVisibilityState
    final_visibility: LunarVisibilityState
    contacts: tuple[LunarOccultationContact, ...]
    profile_model: str
    profile_provenance: str
    policy: ContactSearchPolicy
    geometry_mode: LunarContactGeometryMode
    geometry_provenance: str
    observer_geometry: str = "WGS84_GEODETIC"
    target_model: str = "POINT_SOURCE_CATALOG_STAR"
    atmospheric_refraction: bool = False
    time_scale: str = "UT1"

    def __post_init__(self) -> None:
        if not isinstance(self.star, LunarContactStar):
            raise TypeError("star must be LunarContactStar")
        observer_latitude = _finite_real(
            "observer_latitude_deg", self.observer_latitude_deg
        )
        observer_longitude = _finite_real(
            "observer_longitude_deg", self.observer_longitude_deg
        )
        observer_elevation = _finite_real(
            "observer_elevation_m", self.observer_elevation_m
        )
        jd_start = _finite_real("jd_start_ut1", self.jd_start_ut1)
        jd_end = _finite_real("jd_end_ut1", self.jd_end_ut1)
        profile_model = _nonempty_text("profile_model", self.profile_model)
        profile_provenance = _nonempty_text(
            "profile_provenance", self.profile_provenance
        )
        if not isinstance(self.geometry_mode, LunarContactGeometryMode):
            raise TypeError("geometry_mode must be LunarContactGeometryMode")
        geometry_provenance = _nonempty_text(
            "geometry_provenance", self.geometry_provenance
        )
        if not -90.0 <= observer_latitude <= 90.0:
            raise ValueError("observer_latitude_deg must be in [-90, 90]")
        if not -180.0 <= observer_longitude <= 180.0:
            raise ValueError("observer_longitude_deg must be in [-180, 180]")
        if jd_end <= jd_start:
            raise ValueError("contact search window must be strictly increasing")
        if not isinstance(self.initial_visibility, LunarVisibilityState):
            raise TypeError("initial_visibility must be LunarVisibilityState")
        if not isinstance(self.final_visibility, LunarVisibilityState):
            raise TypeError("final_visibility must be LunarVisibilityState")
        if not isinstance(self.policy, ContactSearchPolicy):
            raise TypeError("policy must be ContactSearchPolicy")
        if self.observer_geometry != "WGS84_GEODETIC":
            raise ValueError("observer_geometry must identify WGS84 geodetic observers")
        if self.target_model != "POINT_SOURCE_CATALOG_STAR":
            raise ValueError("target_model must identify a point-source catalog star")
        if not isinstance(self.atmospheric_refraction, bool):
            raise TypeError("atmospheric_refraction must be bool")
        if self.atmospheric_refraction:
            raise ValueError("topographic contact chronology is an airless product")
        if self.time_scale != "UT1":
            raise ValueError("contact chronology time_scale must be UT1")
        contacts = tuple(self.contacts)
        if any(not isinstance(item, LunarOccultationContact) for item in contacts):
            raise TypeError("contacts must contain LunarOccultationContact values")
        state = self.initial_visibility
        previous_jd = jd_start
        previous_contact_jd: float | None = None
        time_tolerance_days = self.policy.time_tolerance_seconds / _SECONDS_PER_DAY
        chronology_tolerance_days = (
            self.policy.chronology_tolerance_seconds / _SECONDS_PER_DAY
        )
        for contact in contacts:
            if not jd_start < contact.jd_ut1 < jd_end:
                raise ValueError("contacts must lie strictly inside the search window")
            if (
                contact.bracket_start_jd_ut1 < jd_start
                or contact.bracket_end_jd_ut1 > jd_end
            ):
                raise ValueError("contact brackets must lie inside the search window")
            if (
                contact.bracket_end_jd_ut1 - contact.bracket_start_jd_ut1
                > time_tolerance_days
            ):
                raise ValueError(
                    "contact bracket width exceeds policy time_tolerance_seconds"
                )
            residual_tolerance = (
                self.policy.tangency_tolerance_deg
                if contact.kind is LunarContactKind.TANGENCY
                else self.policy.clearance_tolerance_deg
            )
            if abs(contact.signed_clearance_deg) > residual_tolerance:
                tolerance_name = (
                    "tangency_tolerance_deg"
                    if contact.kind is LunarContactKind.TANGENCY
                    else "clearance_tolerance_deg"
                )
                raise ValueError(
                    f"contact signed clearance exceeds policy {tolerance_name}"
                )
            if contact.jd_ut1 <= previous_jd:
                raise ValueError("contacts must be strictly chronological")
            if (
                previous_contact_jd is not None
                and contact.jd_ut1 - previous_contact_jd
                <= chronology_tolerance_days
            ):
                raise ValueError(
                    "distinct contacts are closer than "
                    "policy chronology_tolerance_seconds"
                )
            if contact.visibility_before is not state:
                raise ValueError("contact sequence violates its visibility state machine")
            state = contact.visibility_after
            previous_jd = contact.jd_ut1
            previous_contact_jd = contact.jd_ut1
        if state is not self.final_visibility:
            raise ValueError("final_visibility disagrees with the contact sequence")
        object.__setattr__(self, "observer_latitude_deg", observer_latitude)
        object.__setattr__(self, "observer_longitude_deg", observer_longitude)
        object.__setattr__(self, "observer_elevation_m", observer_elevation)
        object.__setattr__(self, "jd_start_ut1", jd_start)
        object.__setattr__(self, "jd_end_ut1", jd_end)
        object.__setattr__(self, "contacts", contacts)
        object.__setattr__(self, "profile_model", profile_model)
        object.__setattr__(self, "profile_provenance", profile_provenance)
        object.__setattr__(self, "geometry_provenance", geometry_provenance)

    @property
    def target_name(self) -> str:
        return self.star.name

    @property
    def jd_start_utc(self) -> float:
        return _ut1_to_utc(self.jd_start_ut1)

    @property
    def jd_end_utc(self) -> float:
        return _ut1_to_utc(self.jd_end_ut1)

    @property
    def start_datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_start_utc)

    @property
    def end_datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_end_utc)

    @property
    def start_calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_start_utc)

    @property
    def end_calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_end_utc)


@dataclass(frozen=True, slots=True)
class _SolvedContact:
    """Vessel: Structured solved contact data."""
    jd_ut1: float
    kind: LunarContactKind
    visibility_before: LunarVisibilityState
    visibility_after: LunarVisibilityState
    bracket_start_jd_ut1: float
    bracket_end_jd_ut1: float


def _visibility(clearance_deg: float) -> LunarVisibilityState:
    return (
        LunarVisibilityState.VISIBLE
        if clearance_deg > 0.0
        else LunarVisibilityState.OCCULTED
    )


def _evaluate_clearance(
    objective: Callable[[float], float], jd_ut1: float
) -> float:
    value = _finite_real("signed clearance objective", objective(jd_ut1))
    return value


def _refine_crossing(
    objective: Callable[[float], float],
    left_jd: float,
    right_jd: float,
    left_value: float,
    right_value: float,
    policy: ContactSearchPolicy,
) -> tuple[float, float, float, float]:
    """Refine one sign-changing bracket under both numerical contracts.

    The returned tuple is ``(best_jd, best_residual, left_jd, right_jd)``.
    A small objective residual never substitutes for the required time
    bracket, and a narrow time bracket never substitutes for the declared
    clearance residual.
    """

    if left_value == 0.0:
        return left_jd, left_value, left_jd, left_jd
    if right_value == 0.0:
        return right_jd, right_value, right_jd, right_jd
    if left_value * right_value >= 0.0:
        raise ValueError("crossing refinement requires opposite signed bounds")
    tolerance_days = policy.time_tolerance_seconds / _SECONDS_PER_DAY
    for _ in range(policy.max_refine_iterations):
        best_jd, best_value = min(
            ((left_jd, left_value), (right_jd, right_value)),
            key=lambda item: abs(item[1]),
        )
        if (
            right_jd - left_jd <= tolerance_days
            and abs(best_value) <= policy.clearance_tolerance_deg
        ):
            return best_jd, best_value, left_jd, right_jd
        midpoint = (left_jd + right_jd) / 2.0
        if midpoint <= left_jd or midpoint >= right_jd:
            raise RuntimeError(
                "contact crossing cannot satisfy both time_tolerance_seconds "
                "and clearance_tolerance_deg at binary64 Julian-Day resolution"
            )
        midpoint_value = _evaluate_clearance(objective, midpoint)
        if midpoint_value == 0.0:
            return midpoint, midpoint_value, midpoint, midpoint
        if (left_value < 0.0) == (midpoint_value < 0.0):
            left_jd, left_value = midpoint, midpoint_value
        else:
            right_jd, right_value = midpoint, midpoint_value
    best_jd, best_value = min(
        ((left_jd, left_value), (right_jd, right_value)),
        key=lambda item: abs(item[1]),
    )
    if (
        right_jd - left_jd <= tolerance_days
        and abs(best_value) <= policy.clearance_tolerance_deg
    ):
        return best_jd, best_value, left_jd, right_jd
    raise RuntimeError(
        "contact crossing did not satisfy both time_tolerance_seconds and "
        "clearance_tolerance_deg within max_refine_iterations"
    )


def _refine_tangency(
    objective: Callable[[float], float],
    left_jd: float,
    right_jd: float,
    policy: ContactSearchPolicy,
) -> tuple[float, float, float, float] | None:
    """Refine the signed extremum inside one same-sign local bracket.

    The returned tuple is ``(best_jd, best_residual, left_jd, right_jd)``.
    The bounds are the final refined witness, not the coarse scan interval.
    A visible bracket minimizes clearance; an occulted bracket maximizes it.
    If that extremum enters the opposite visibility state, the bracket contains
    an unresolved sub-scan crossing pair and must not be relabelled tangency.
    """

    tolerance_days = policy.time_tolerance_seconds / _SECONDS_PER_DAY
    left_endpoint_value = _evaluate_clearance(objective, left_jd)
    right_endpoint_value = _evaluate_clearance(objective, right_jd)
    if (
        left_endpoint_value == 0.0
        or right_endpoint_value == 0.0
        or (left_endpoint_value < 0.0) != (right_endpoint_value < 0.0)
    ):
        raise ValueError("tangency refinement requires nonzero same-sign bounds")
    visibility_sign = 1.0 if left_endpoint_value > 0.0 else -1.0

    def oriented(value: float) -> float:
        return visibility_sign * value

    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    x1 = right_jd - ratio * (right_jd - left_jd)
    x2 = left_jd + ratio * (right_jd - left_jd)
    if not left_jd < x1 < x2 < right_jd:
        raise RuntimeError("tangency refinement cannot advance at this Julian Day")
    y1 = _evaluate_clearance(objective, x1)
    y2 = _evaluate_clearance(objective, x2)
    best_jd, best_value = min(
        ((x1, y1), (x2, y2)), key=lambda item: oriented(item[1])
    )
    for _ in range(policy.max_refine_iterations):
        if right_jd - left_jd <= tolerance_days:
            break
        if oriented(y1) <= oriented(y2):
            right_jd, x2, y2 = x2, x1, y1
            x1 = right_jd - ratio * (right_jd - left_jd)
            if not left_jd < x1 < right_jd:
                raise RuntimeError("tangency refinement cannot advance")
            y1 = _evaluate_clearance(objective, x1)
            candidate = (x1, y1)
        else:
            left_jd, x1, y1 = x1, x2, y2
            x2 = left_jd + ratio * (right_jd - left_jd)
            if not left_jd < x2 < right_jd:
                raise RuntimeError("tangency refinement cannot advance")
            y2 = _evaluate_clearance(objective, x2)
            candidate = (x2, y2)
        if oriented(candidate[1]) < oriented(best_value):
            best_jd, best_value = candidate
    else:
        raise RuntimeError("contact tangency did not converge within policy")
    midpoint = (left_jd + right_jd) / 2.0
    final_candidates = (
        (left_jd, _evaluate_clearance(objective, left_jd)),
        (x1, y1),
        (midpoint, _evaluate_clearance(objective, midpoint)),
        (x2, y2),
        (right_jd, _evaluate_clearance(objective, right_jd)),
    )
    best_jd, best_value = min(
        (
            candidate
            for candidate in final_candidates
            if left_jd <= candidate[0] <= right_jd
        ),
        key=lambda item: oriented(item[1]),
    )
    best_oriented_value = oriented(best_value)
    if best_oriented_value < 0.0:
        raise ValueError(
            "same-sign tangency bracket contains an unresolved sub-scan "
            "opposite-state excursion"
        )
    if best_oriented_value > policy.tangency_tolerance_deg:
        return None
    # Contact admission requires a unique interior extremum, not merely three
    # small residuals.  A physically realistic grazing clearance is extremely
    # shallow on millisecond scales, so absolute proximity to zero cannot
    # distinguish it from a flat interval.  The final golden-section witness
    # instead has to rise strictly away from the selected extremum on both
    # temporal sides.  Equal minima, a boundary minimum, or a one-sided flat
    # interval remain indeterminate and fail closed.
    left_witness_value = final_candidates[0][1]
    right_witness_value = final_candidates[-1][1]
    left_variation = oriented(left_witness_value) - best_oriented_value
    right_variation = oriented(right_witness_value) - best_oriented_value
    if (
        not left_jd < best_jd < right_jd
        or left_variation <= 0.0
        or right_variation <= 0.0
    ):
        if max(abs(left_variation), abs(right_variation)) <= (
            policy.plateau_tolerance_deg
        ):
            raise ValueError(
                "near-zero clearance plateau has no unique contact instant"
            )
        raise ValueError(
            "near-zero local extremum has no unique two-sided variation witness"
        )
    return best_jd, best_value, left_jd, right_jd


def _solve_signed_clearance_contacts(
    jd_start_ut1: float,
    jd_end_ut1: float,
    objective: Callable[[float], float],
    policy: ContactSearchPolicy,
) -> tuple[
    LunarVisibilityState,
    LunarVisibilityState,
    tuple[_SolvedContact, ...],
]:
    """Solve an ordered contact sequence from a pure signed-clearance scalar."""

    start = _finite_real("jd_start_ut1", jd_start_ut1)
    end = _finite_real("jd_end_ut1", jd_end_ut1)
    if end <= start:
        raise ValueError("contact search window must be strictly increasing")
    if not callable(objective):
        raise TypeError("objective must be callable")
    if not isinstance(policy, ContactSearchPolicy):
        raise TypeError("policy must be ContactSearchPolicy")

    span_seconds = (end - start) * _SECONDS_PER_DAY
    estimated_sample_count = (
        math.ceil(span_seconds / policy.scan_step_seconds) + 1
    )
    if estimated_sample_count > policy.max_scan_samples:
        raise ValueError(
            "contact search exceeds max_scan_samples under the selected scan step"
        )

    step_days = policy.scan_step_seconds / _SECONDS_PER_DAY
    samples: list[tuple[float, float]] = []
    for index in range(estimated_sample_count):
        candidate = start + index * step_days
        jd_ut1 = end if candidate >= end else candidate
        if samples and jd_ut1 <= samples[-1][0]:
            raise RuntimeError(
                "contact scan cannot advance at this Julian Day and scan step"
            )
        samples.append((jd_ut1, _evaluate_clearance(objective, jd_ut1)))
        if jd_ut1 == end:
            break
    if samples[-1][0] < end:
        if len(samples) >= policy.max_scan_samples:
            raise ValueError(
                "contact search exceeds max_scan_samples under the selected scan step"
            )
        samples.append((end, _evaluate_clearance(objective, end)))

    if abs(samples[0][1]) <= policy.tangency_tolerance_deg:
        raise ValueError("contact at the search-window start is endpoint-ambiguous")
    if abs(samples[-1][1]) <= policy.tangency_tolerance_deg:
        raise ValueError("contact at the search-window end is endpoint-ambiguous")

    candidates: list[_SolvedContact] = []
    crossing_edges: set[int] = set()

    # Exact sampled zeros are classified from their representably immediate
    # sides, then reconciled with the enclosing scan witnesses.  Coarse
    # neighbours alone cannot distinguish a true same-state tangency from one
    # edge of a sub-scan crossing pair.
    for index in range(1, len(samples) - 1):
        jd_ut1, value = samples[index]
        if value != 0.0:
            continue
        left_jd, left_value = samples[index - 1]
        right_jd, right_value = samples[index + 1]
        if left_value == 0.0 or right_value == 0.0:
            raise ValueError("zero-clearance plateau has no unique contact instant")
        left_probe_jd = math.nextafter(jd_ut1, left_jd)
        right_probe_jd = math.nextafter(jd_ut1, right_jd)
        if not left_jd <= left_probe_jd < jd_ut1:
            raise RuntimeError("exact-zero left-side probe cannot advance")
        if not jd_ut1 < right_probe_jd <= right_jd:
            raise RuntimeError("exact-zero right-side probe cannot advance")
        left_probe_value = _evaluate_clearance(objective, left_probe_jd)
        right_probe_value = _evaluate_clearance(objective, right_probe_jd)
        if left_probe_value == 0.0 or right_probe_value == 0.0:
            raise ValueError("zero-clearance plateau has no unique contact instant")
        before = _visibility(left_probe_value)
        after = _visibility(right_probe_value)
        if before is not _visibility(left_value) or after is not _visibility(
            right_value
        ):
            raise ValueError(
                "exact sampled zero contains an unresolved sub-scan "
                "visibility excursion"
            )
        if before is after:
            kind = LunarContactKind.TANGENCY
        elif before is LunarVisibilityState.VISIBLE:
            kind = LunarContactKind.DISAPPEARANCE
        else:
            kind = LunarContactKind.REAPPEARANCE
        candidates.append(
            _SolvedContact(jd_ut1, kind, before, after, jd_ut1, jd_ut1)
        )
        crossing_edges.update((index - 1, index))

    # Strict sign changes not already represented by an exact sampled zero.
    for index in range(len(samples) - 1):
        if index in crossing_edges:
            continue
        left_jd, left_value = samples[index]
        right_jd, right_value = samples[index + 1]
        if left_value * right_value >= 0.0:
            continue
        jd_ut1, _residual, refined_left_jd, refined_right_jd = _refine_crossing(
            objective,
            left_jd,
            right_jd,
            left_value,
            right_value,
            policy,
        )
        before = _visibility(left_value)
        after = _visibility(right_value)
        kind = (
            LunarContactKind.DISAPPEARANCE
            if before is LunarVisibilityState.VISIBLE
            else LunarContactKind.REAPPEARANCE
        )
        candidates.append(
            _SolvedContact(
                jd_ut1,
                kind,
                before,
                after,
                refined_left_jd,
                refined_right_jd,
            )
        )
        crossing_edges.add(index)

    # A same-sign zero can occur between samples.  Search only strict local
    # minima of absolute clearance whose adjacent intervals contain no
    # crossing; this avoids reclassifying ordinary roots as tangencies.
    for index in range(1, len(samples) - 1):
        if index - 1 in crossing_edges or index in crossing_edges:
            continue
        left_jd, left_value = samples[index - 1]
        middle_jd, middle_value = samples[index]
        right_jd, right_value = samples[index + 1]
        if not (
            (left_value < 0.0) == (middle_value < 0.0)
            and (middle_value < 0.0) == (right_value < 0.0)
        ):
            continue
        if not (
            abs(middle_value) < abs(left_value)
            and abs(middle_value) <= abs(right_value)
        ):
            continue
        refined = _refine_tangency(objective, left_jd, right_jd, policy)
        if refined is None:
            continue
        jd_ut1, _residual, refined_left_jd, refined_right_jd = refined
        probe_seconds = max(
            policy.time_tolerance_seconds * 4.0,
            min(policy.scan_step_seconds / 8.0, 0.01),
        )
        probe_days = probe_seconds / _SECONDS_PER_DAY
        # Classification probes belong to the same local scan witness as the
        # refined extremum.  A caller may lawfully choose a time tolerance
        # close to the scan step, so an unconstrained ``jd +/- probe`` can
        # otherwise escape the requested search/profile interval for a
        # tangency near either boundary.  Keep the probes on opposite sides of
        # the complete refined witness when possible, clamp them to the local
        # coarse bracket and search window, and fail closed if binary64 cannot
        # represent both sides.
        left_probe_floor = max(start, left_jd)
        right_probe_ceiling = min(end, right_jd)
        if not left_probe_floor < jd_ut1 < right_probe_ceiling:
            raise ValueError(
                "tangency has no two-sided local search bracket for "
                "visibility classification"
            )
        immediate_left_jd = math.nextafter(jd_ut1, left_probe_floor)
        immediate_right_jd = math.nextafter(jd_ut1, right_probe_ceiling)
        left_probe_ceiling = min(refined_left_jd, immediate_left_jd)
        right_probe_floor = max(refined_right_jd, immediate_right_jd)
        left_probe_jd = max(
            left_probe_floor,
            min(jd_ut1 - probe_days, left_probe_ceiling),
        )
        right_probe_jd = min(
            right_probe_ceiling,
            max(jd_ut1 + probe_days, right_probe_floor),
        )
        if not left_probe_floor <= left_probe_jd < jd_ut1:
            raise ValueError(
                "tangency has no representable left-side probe inside its "
                "local search bracket"
            )
        if not jd_ut1 < right_probe_jd <= right_probe_ceiling:
            raise ValueError(
                "tangency has no representable right-side probe inside its "
                "local search bracket"
            )
        before_value = _evaluate_clearance(objective, left_probe_jd)
        after_value = _evaluate_clearance(objective, right_probe_jd)
        if before_value == 0.0 or after_value == 0.0:
            raise ValueError(
                "zero-clearance tangency probe has no classifiable visibility state"
            )
        before = _visibility(before_value)
        after = _visibility(after_value)
        if before is not after:
            # A crossing narrower than the scan policy is not evidence of a
            # tangency; the selected scan resolution cannot classify it.
            raise ValueError(
                "same-sign tangency bracket contains an unresolved visibility crossing"
            )
        candidates.append(
            _SolvedContact(
                jd_ut1,
                LunarContactKind.TANGENCY,
                before,
                after,
                refined_left_jd,
                refined_right_jd,
            )
        )

    candidates.sort(key=lambda item: item.jd_ut1)
    chronology_days = policy.chronology_tolerance_seconds / _SECONDS_PER_DAY
    ordered: list[_SolvedContact] = []
    for candidate in candidates:
        if ordered and candidate.jd_ut1 - ordered[-1].jd_ut1 <= chronology_days:
            if (
                candidate.kind is ordered[-1].kind
                and candidate.visibility_before is ordered[-1].visibility_before
                and candidate.visibility_after is ordered[-1].visibility_after
            ):
                brackets_overlap = (
                    candidate.bracket_start_jd_ut1
                    <= ordered[-1].bracket_end_jd_ut1
                    and ordered[-1].bracket_start_jd_ut1
                    <= candidate.bracket_end_jd_ut1
                )
                if brackets_overlap:
                    # Overlapping local-minimum brackets may rediscover the
                    # same physical root.  Keep the narrower witness only.
                    old_width = (
                        ordered[-1].bracket_end_jd_ut1
                        - ordered[-1].bracket_start_jd_ut1
                    )
                    new_width = (
                        candidate.bracket_end_jd_ut1
                        - candidate.bracket_start_jd_ut1
                    )
                    if new_width < old_width:
                        ordered[-1] = candidate
                    continue
            raise ValueError(
                "distinct contacts are closer than chronology_tolerance_seconds"
            )
        ordered.append(candidate)

    initial = _visibility(samples[0][1])
    state = initial
    for contact in ordered:
        if contact.visibility_before is not state:
            raise ValueError("solved contacts violate visibility-state chronology")
        state = contact.visibility_after
    final = _visibility(samples[-1][1])
    if state is not final:
        raise ValueError("solved contacts do not reconcile the endpoint visibility")
    return initial, final, tuple(ordered)


def _profile_adjustment_callable(
    profile: LunarLimbContactProfile,
) -> Callable[[float, float, float, float, float, float], float]:
    angular_adjustment = getattr(profile, "angular_adjustment_deg_at", None)
    full_adjustment = getattr(profile, "adjustment_deg", None)
    if not callable(angular_adjustment) and not callable(full_adjustment):
        raise TypeError(
            "profile must provide angular_adjustment_deg_at or adjustment_deg"
        )

    def provider(
        jd_ut1: float,
        observer_latitude_deg: float,
        observer_longitude_deg: float,
        observer_elevation_m: float,
        position_angle_deg: float,
        moon_distance_km: float,
    ) -> float:
        if callable(angular_adjustment):
            value = angular_adjustment(
                jd_ut1,
                position_angle_deg,
                moon_distance_km,
            )
        else:
            value = full_adjustment(
                jd_ut1,
                observer_latitude_deg,
                observer_longitude_deg,
                observer_elevation_m,
                position_angle_deg,
                moon_distance_km,
            )
        return _finite_real("profile adjustment", value)

    return provider


def _profile_identity(profile: LunarLimbContactProfile) -> tuple[str, str]:
    """Resolve inspectable identity from either structured or simple profiles."""

    explicit_model = getattr(profile, "model_name", None)
    explicit_provenance = getattr(profile, "provenance", None)
    source = getattr(profile, "source", None)
    if explicit_model is None and source is not None:
        explicit_model = getattr(source, "silhouette_model", None)
    if explicit_provenance is None and source is not None:
        authority = _nonempty_text(
            "profile.source.authority", getattr(source, "authority", None)
        )
        collection = _nonempty_text(
            "profile.source.collection", getattr(source, "collection", None)
        )
        coordinate_frame = _nonempty_text(
            "profile.source.coordinate_frame",
            getattr(source, "coordinate_frame", None),
        )
        translation_model = _nonempty_text(
            "profile.source.translation_model",
            getattr(source, "translation_model", None),
        )
        orientation_model = _nonempty_text(
            "profile.source.orientation_model",
            getattr(source, "orientation_model", None),
        )
        surface_frame_model = _nonempty_text(
            "profile.source.surface_frame_model",
            getattr(source, "surface_frame_model", None),
        )
        alignment_max_m = _finite_real(
            "profile.source.orientation_alignment_max_m",
            getattr(source, "orientation_alignment_max_m", None),
        )
        alignment_interval = _nonempty_text(
            "profile.source.orientation_alignment_interval",
            getattr(source, "orientation_alignment_interval", None),
        )
        query_half_width_km = _finite_real(
            "profile.source.spatial_query_half_width_km",
            getattr(source, "spatial_query_half_width_km", None),
        )
        reference_radius_km = _finite_real(
            "profile.source.reference_radius_km",
            getattr(source, "reference_radius_km", None),
        )
        raw_query_bounds = getattr(
            source,
            "spatial_query_bounds_moon_xyz_km",
            None,
        )
        try:
            query_minimum, query_maximum = raw_query_bounds
            if len(query_minimum) != 3 or len(query_maximum) != 3:
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "profile.source.spatial_query_bounds_moon_xyz_km must contain "
                "two XYZ triples"
            ) from exc
        query_bounds = tuple(
            _finite_real("profile.source.spatial_query_bounds_moon_xyz_km", value)
            for bound in (query_minimum, query_maximum)
            for value in bound
        )
        relief_sources = tuple(
            _nonempty_text("profile.source.relief_observation_source", value)
            for value in getattr(source, "relief_observation_sources", ())
        )
        if not relief_sources:
            raise ValueError(
                "profile.source.relief_observation_sources must not be empty"
            )
        relief_policy = _nonempty_text(
            "profile.source.relief_acquisition_policy",
            getattr(source, "relief_acquisition_policy", None),
        )
        max_relief_km = _finite_real(
            "profile.source.max_absolute_relief_km",
            getattr(source, "max_absolute_relief_km", None),
        )
        observed_highest_km = _finite_real(
            "profile.source.relief_observed_highest_km",
            getattr(source, "relief_observed_highest_km", None),
        )
        observed_approximate_km = _finite_real(
            "profile.source.relief_observed_approximate_absolute_km",
            getattr(source, "relief_observed_approximate_absolute_km", None),
        )
        assets = tuple(getattr(source, "assets", ()))
        if not assets:
            raise ValueError("profile.source.assets must not be empty")
        asset_records: list[str] = []
        for index, asset in enumerate(assets):
            url = _nonempty_text(
                f"profile.source.assets[{index}].url",
                getattr(asset, "url", None),
            )
            byte_length = getattr(asset, "byte_length", None)
            if (
                isinstance(byte_length, bool)
                or not isinstance(byte_length, int)
                or byte_length <= 0
            ):
                raise ValueError(
                    f"profile.source.assets[{index}].byte_length must be a "
                    "positive int"
                )
            digest = _nonempty_text(
                f"profile.source.assets[{index}].sha256",
                getattr(asset, "sha256", None),
            ).lower()
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(
                    f"profile.source.assets[{index}].sha256 must be hexadecimal"
                )
            asset_records.append(f"{url}\0{byte_length}\0{digest}")
        asset_set_sha256 = hashlib.sha256(
            "\n".join(sorted(asset_records)).encode("utf-8")
        ).hexdigest()

        profile_fingerprint = hashlib.sha256()

        def fingerprint_token(name: str, value: object) -> None:
            if isinstance(value, float):
                text = value.hex()
            elif isinstance(value, int) and not isinstance(value, bool):
                text = str(value)
            else:
                text = _nonempty_text(name, value)
            encoded = text.encode("utf-8")
            profile_fingerprint.update(name.encode("utf-8"))
            profile_fingerprint.update(b"\0")
            profile_fingerprint.update(str(len(encoded)).encode("ascii"))
            profile_fingerprint.update(b"\0")
            profile_fingerprint.update(encoded)
            profile_fingerprint.update(b"\n")

        fingerprint_token(
            "silhouette_model",
            _nonempty_text(
                "profile.source.silhouette_model",
                getattr(source, "silhouette_model", None),
            ),
        )
        fingerprint_token(
            "max_time_interpolation_gap_days",
            _finite_real(
                "profile.max_time_interpolation_gap_days",
                getattr(profile, "max_time_interpolation_gap_days", None),
            ),
        )
        for field_name in (
            "observer_latitude_deg",
            "observer_longitude_deg",
            "observer_elevation_m",
        ):
            fingerprint_token(
                field_name,
                _finite_real(
                    f"profile.{field_name}",
                    getattr(profile, field_name, None),
                ),
            )
        slices = tuple(getattr(profile, "slices", ()))
        if not slices:
            raise ValueError("a structured profile source requires realized slices")
        fingerprint_token("slice_count", len(slices))
        for slice_index, profile_slice in enumerate(slices):
            prefix = f"slice[{slice_index}]"
            fingerprint_token(
                f"{prefix}.jd_ut1",
                _finite_real(
                    f"profile.{prefix}.jd_ut1",
                    getattr(profile_slice, "jd_ut1", None),
                ),
            )
            fingerprint_token(
                f"{prefix}.bin_width_deg",
                _finite_real(
                    f"profile.{prefix}.bin_width_deg",
                    getattr(profile_slice, "bin_width_deg", None),
                ),
            )
            fingerprint_token(
                f"{prefix}.max_interpolation_gap_deg",
                _finite_real(
                    f"profile.{prefix}.max_interpolation_gap_deg",
                    getattr(profile_slice, "max_interpolation_gap_deg", None),
                ),
            )
            source_point_count = getattr(profile_slice, "source_point_count", None)
            if (
                isinstance(source_point_count, bool)
                or not isinstance(source_point_count, int)
                or source_point_count < 0
            ):
                raise ValueError(
                    f"profile.{prefix}.source_point_count must be a non-negative int"
                )
            fingerprint_token(f"{prefix}.source_point_count", source_point_count)
            position_angles = tuple(
                getattr(profile_slice, "position_angles_unwrapped_deg", ())
            )
            radii = tuple(getattr(profile_slice, "radii_km", ()))
            if not position_angles or len(position_angles) != len(radii):
                raise ValueError(
                    f"profile.{prefix} PA and radius samples must be non-empty "
                    "and equally sized"
                )
            fingerprint_token(f"{prefix}.sample_count", len(position_angles))
            for sample_index, (position_angle, radius) in enumerate(
                zip(position_angles, radii)
            ):
                fingerprint_token(
                    f"{prefix}.pa[{sample_index}]",
                    _finite_real(
                        f"profile.{prefix}.position_angle",
                        position_angle,
                    ),
                )
                fingerprint_token(
                    f"{prefix}.radius[{sample_index}]",
                    _finite_real(f"profile.{prefix}.radius", radius),
                )
            slice_assets = tuple(getattr(profile_slice, "asset_urls", ()))
            if not slice_assets:
                raise ValueError(f"profile.{prefix}.asset_urls must not be empty")
            fingerprint_token(f"{prefix}.asset_count", len(slice_assets))
            for asset_index, asset_url in enumerate(slice_assets):
                fingerprint_token(
                    f"{prefix}.asset[{asset_index}]",
                    asset_url,
                )
        realized_profile_sha256 = profile_fingerprint.hexdigest()
        formatted_bounds = ",".join(f"{value:.12g}" for value in query_bounds)
        explicit_provenance = (
            f"{authority}; collection={collection}; frame={coordinate_frame}; "
            f"translation={translation_model}; orientation={orientation_model}; "
            f"surface={surface_frame_model}; alignment<={alignment_max_m}m "
            f"over {alignment_interval}; reference_radius={reference_radius_km}km; "
            f"query_half_width={query_half_width_km}km; "
            f"query_bounds_moon_xyz_km={formatted_bounds}; "
            f"relief_bound=+/-{max_relief_km}km; relief_policy={relief_policy}; "
            f"observed_relief_highest={observed_highest_km}km; "
            f"observed_relief_approx_abs={observed_approximate_km}km; "
            f"relief_sources={'|'.join(relief_sources)}; "
            f"silhouette_model={explicit_model}; "
            f"content_identified_assets={len(assets)}; "
            f"asset_set_sha256={asset_set_sha256}; "
            f"realized_profile_sha256={realized_profile_sha256}"
        )
    return (
        _nonempty_text("profile model", explicit_model),
        _nonempty_text("profile provenance", explicit_provenance),
    )


def _validate_profile_time_coverage(
    profile: LunarLimbContactProfile,
    jd_start_ut1: float,
    jd_end_ut1: float,
) -> None:
    coverage_start = getattr(profile, "jd_ut1_start", None)
    coverage_end = getattr(profile, "jd_ut1_end", None)
    if coverage_start is None and coverage_end is None:
        return
    if coverage_start is None or coverage_end is None:
        raise ValueError("profile time coverage must declare both start and end")
    admitted_start = _finite_real("profile.jd_ut1_start", coverage_start)
    admitted_end = _finite_real("profile.jd_ut1_end", coverage_end)
    if admitted_end < admitted_start:
        raise ValueError("profile time coverage must be ordered")
    if jd_start_ut1 < admitted_start or jd_end_ut1 > admitted_end:
        raise ValueError(
            "contact search window lies outside the prepared profile time coverage"
        )


def _validate_profile_site(
    profile: LunarLimbContactProfile,
    observer_latitude_deg: float,
    observer_longitude_deg: float,
    observer_elevation_m: float,
) -> None:
    fields = (
        ("observer_latitude_deg", observer_latitude_deg),
        ("observer_longitude_deg", observer_longitude_deg),
        ("observer_elevation_m", observer_elevation_m),
    )
    declared = [getattr(profile, name, None) for name, _value in fields]
    if all(value is None for value in declared):
        return
    if any(value is None for value in declared):
        raise ValueError("profile site identity must declare latitude, longitude, and elevation")
    for (name, requested), admitted in zip(fields, declared):
        admitted_value = _finite_real(f"profile.{name}", admitted)
        if not math.isclose(admitted_value, requested, rel_tol=0.0, abs_tol=1.0e-12):
            raise ValueError(
                f"contact observer {name} does not match the prepared profile site"
            )


def _observer_star_icrf_direction(
    star: LunarContactStar,
    observer_ssb_icrf: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Return the geometric observer-to-star ICRF ray.

    Finite-distance stars are displaced from their SSB catalog direction by
    the complete reception-epoch observer vector, so annual and diurnal
    parallax are one coherent translation.  Observer-velocity aberration is a
    different coordinate effect and remains deliberately absent.
    """

    if not isinstance(star, LunarContactStar):
        raise TypeError("star must be LunarContactStar")
    if not isinstance(observer_ssb_icrf, tuple) or len(observer_ssb_icrf) != 3:
        raise TypeError("observer_ssb_icrf must be a 3-tuple")
    observer = tuple(
        _finite_real(f"observer_ssb_icrf[{index}]", value)
        for index, value in enumerate(observer_ssb_icrf)
    )
    if star.parallax_mas is None:
        return star.barycentric_icrf_unit
    if star.barycentric_distance_km is None:
        raise ValueError("finite-distance star is missing propagated distance")
    distance_km = star.barycentric_distance_km
    relative = tuple(
        distance_km * star.barycentric_icrf_unit[index] - observer[index]
        for index in range(3)
    )
    norm = math.sqrt(sum(value * value for value in relative))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValueError("observer-to-star distance must be finite and positive")
    return tuple(value / norm for value in relative)


def _contact_klioner_deflected_unit_direction(
    observer_to_source: tuple[float, float, float],
    deflector_to_source: tuple[float, float, float],
    deflector_to_observer: tuple[float, float, float],
    schwarzschild_radius_km: float,
    deflector_distance_km: float,
    limiter: float,
) -> tuple[float, float, float]:
    """Apply one contact-private Klioner Eq. 70 light deflection.

    The three directions are respectively the ``p``, ``q``, and ``e``
    vectors of Klioner (2003), equation 70, and IAU SOFA ``Ld``.  SOFA
    expresses the scale as ``bm * SRS_AU / em_AU``.  Moira's DE441 states
    and Schwarzschild radii are both in kilometres, so the same
    dimensionless scale is explicitly ``R_s_km / distance_km``; neither a
    hidden AU conversion nor a solar-mass rescaling belongs in this path.

    This helper is deliberately private to lunar-contact geometry.  It does
    not alter the correction policy used by planetary products elsewhere in
    the engine.
    """

    def unit_direction(
        name: str,
        value: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        if not isinstance(value, tuple) or len(value) != 3:
            raise TypeError(f"{name} must be a 3-tuple")
        direction = tuple(
            _finite_real(f"{name}[{index}]", component)
            for index, component in enumerate(value)
        )
        norm = math.sqrt(sum(component * component for component in direction))
        if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=2.0e-12):
            raise ValueError(f"{name} must be normalized")
        return tuple(component / norm for component in direction)

    p = unit_direction("observer_to_source", observer_to_source)
    q = unit_direction("deflector_to_source", deflector_to_source)
    e = unit_direction("deflector_to_observer", deflector_to_observer)
    radius_km = _finite_real("schwarzschild_radius_km", schwarzschild_radius_km)
    distance_km = _finite_real("deflector_distance_km", deflector_distance_km)
    admitted_limiter = _finite_real("limiter", limiter)
    if radius_km <= 0.0:
        raise ValueError("schwarzschild_radius_km must be positive")
    if distance_km <= 0.0:
        raise ValueError("deflector_distance_km must be positive")
    if admitted_limiter <= 0.0:
        raise ValueError("limiter must be positive")

    q_plus_e = tuple(q[index] + e[index] for index in range(3))
    denominator = max(
        sum(q[index] * q_plus_e[index] for index in range(3)),
        admitted_limiter,
    )
    scale = radius_km / distance_km / denominator

    # Klioner's vector object is p x (e x q).  Keeping the two cross
    # products visible makes the direction and sign independently auditable.
    e_cross_q = (
        e[1] * q[2] - e[2] * q[1],
        e[2] * q[0] - e[0] * q[2],
        e[0] * q[1] - e[1] * q[0],
    )
    p_cross_e_cross_q = (
        p[1] * e_cross_q[2] - p[2] * e_cross_q[1],
        p[2] * e_cross_q[0] - p[0] * e_cross_q[2],
        p[0] * e_cross_q[1] - p[1] * e_cross_q[0],
    )
    deflected = tuple(
        p[index] + scale * p_cross_e_cross_q[index]
        for index in range(3)
    )
    norm = math.sqrt(sum(component * component for component in deflected))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValueError("deflected contact direction must be finite and non-zero")
    return tuple(component / norm for component in deflected)


def _reader_bound_deflected_star_icrf_direction(
    star: LunarContactStar,
    observer_ssb_icrf: tuple[float, float, float],
    jd_tt: float,
    reader: object,
) -> tuple[float, float, float]:
    """Return the DE441-bound physical stellar ray for lunar contacts.

    Sun, Jupiter, and Saturn are evaluated as DE441 barycentric position and
    velocity states.  Each body is linearly placed at the ray's closest
    passage using the IAU SOFA ``Ldn`` reception-epoch rule, with a zero
    backtrack when the body lies behind the observer.  Contributions are then
    applied in light-passage order with the terrestrial-observer limiters
    declared by SOFA: ``6e-6``, ``3e-9``, and ``3e-10``.

    For a finite catalog star, ``q`` remains the actual backtracked
    deflector-to-source direction.  Only an explicitly infinite-distance star
    uses the running observer ray for both ``p`` and ``q``.
    """

    from .constants import Body, C_KM_PER_DAY
    from .corrections import SCHWARZSCHILD_RADII
    from .planets import _barycentric_state

    observer = tuple(
        _finite_real(f"observer_ssb_icrf[{index}]", component)
        for index, component in enumerate(observer_ssb_icrf)
    )
    direction = _observer_star_icrf_direction(star, observer)
    reception_tt = _finite_real("jd_tt", jd_tt)
    source_ssb = (
        None
        if star.barycentric_distance_km is None
        else tuple(
            star.barycentric_distance_km * component
            for component in star.barycentric_icrf_unit
        )
    )

    policy = (
        (Body.SUN, 6.0e-6),
        (Body.JUPITER, 3.0e-9),
        (Body.SATURN, 3.0e-10),
    )
    states: list[
        tuple[
            float,
            int,
            str,
            float,
            float,
            tuple[float, float, float],
            tuple[float, float, float],
        ]
    ] = []
    for policy_order, (body, limiter) in enumerate(policy):
        raw_position, raw_velocity = _barycentric_state(
            body,
            reception_tt,
            reader,  # type: ignore[arg-type]
        )
        position = tuple(
            _finite_real(f"{body} barycentric position[{index}]", component)
            for index, component in enumerate(raw_position)
        )
        velocity = tuple(
            _finite_real(f"{body} barycentric velocity[{index}]", component)
            for index, component in enumerate(raw_velocity)
        )
        body_to_observer = tuple(
            observer[index] - position[index] for index in range(3)
        )
        passage_offset_days = min(
            sum(
                direction[index] * body_to_observer[index]
                for index in range(3)
            )
            / C_KM_PER_DAY,
            0.0,
        )
        states.append(
            (
                passage_offset_days,
                policy_order,
                body,
                SCHWARZSCHILD_RADII[body],
                limiter,
                position,
                velocity,
            )
        )

    # More-negative passage offsets lie farther upstream along the incoming
    # ray and must contribute first.  The declared policy order breaks only
    # exact ties, including bodies that are all behind the observer.
    states.sort(key=lambda state: (state[0], state[1]))
    for (
        _initial_offset,
        _policy_order,
        body,
        radius_km,
        limiter,
        position,
        velocity,
    ) in states:
        body_to_observer = tuple(
            observer[index] - position[index] for index in range(3)
        )
        passage_offset_days = min(
            sum(
                direction[index] * body_to_observer[index]
                for index in range(3)
            )
            / C_KM_PER_DAY,
            0.0,
        )
        body_at_passage = tuple(
            position[index] + passage_offset_days * velocity[index]
            for index in range(3)
        )
        passage_body_to_observer = tuple(
            observer[index] - body_at_passage[index] for index in range(3)
        )
        deflector_distance_km = math.sqrt(
            sum(component * component for component in passage_body_to_observer)
        )
        if not math.isfinite(deflector_distance_km) or deflector_distance_km <= 0.0:
            raise ValueError(
                f"{body} deflector-to-observer distance must be finite and positive"
            )
        deflector_to_observer = tuple(
            component / deflector_distance_km
            for component in passage_body_to_observer
        )

        if source_ssb is None:
            deflector_to_source = direction
        else:
            source_relative = tuple(
                source_ssb[index] - body_at_passage[index]
                for index in range(3)
            )
            source_distance_km = math.sqrt(
                sum(component * component for component in source_relative)
            )
            if not math.isfinite(source_distance_km) or source_distance_km <= 0.0:
                raise ValueError(
                    f"{body} deflector-to-source distance must be finite and positive"
                )
            deflector_to_source = tuple(
                component / source_distance_km for component in source_relative
            )

        direction = _contact_klioner_deflected_unit_direction(
            direction,
            deflector_to_source,
            deflector_to_observer,
            radius_km,
            deflector_distance_km,
            limiter,
        )
    return direction


def _validate_star_reference_epoch(
    star: LunarContactStar,
    jd_start_ut1: float,
    jd_end_ut1: float,
    reader: object,
) -> None:
    """Bind a frozen propagated direction to the event's TT interval."""

    from ._ephemeris_time import _ut1_to_ephemeris_tt

    start_tt = _ut1_to_ephemeris_tt(jd_start_ut1, reader)  # type: ignore[arg-type]
    end_tt = _ut1_to_ephemeris_tt(jd_end_ut1, reader)  # type: ignore[arg-type]
    if not start_tt <= star.reference_epoch_jd_tt <= end_tt:
        raise ValueError(
            "star reference_epoch_jd_tt must lie inside the contact window in TT"
        )


def _reader_bound_geometry_label(
    reader: object,
    jd_start_ut1: float,
    jd_end_ut1: float,
) -> str:
    """Return one content-derived DE441/LE441 identity across the window."""

    from ._ephemeris_time import _reader_identity_at, _ut1_to_ephemeris_tt

    labels: set[str] = set()
    for jd_ut1 in (
        jd_start_ut1,
        (jd_start_ut1 + jd_end_ut1) / 2.0,
        jd_end_ut1,
    ):
        jd_tt = _ut1_to_ephemeris_tt(jd_ut1, reader)  # type: ignore[arg-type]
        identity = _reader_identity_at(reader, jd_tt)  # type: ignore[arg-type]
        if (
            identity is None
            or identity.planetary_ephemeris != "DE441"
            or identity.lunar_ephemeris != "LE441"
        ):
            label = None if identity is None else identity.summary_label
            raise ValueError(
                "reader-bound topographic contact geometry requires a "
                f"content-identified DE441/LE441 reader; received {label!r}"
            )
        labels.add(identity.summary_label)
    if len(labels) != 1:
        raise ValueError(
            "topographic contact geometry cannot cross reader identity boundaries"
        )
    return next(iter(labels))


def _physical_star_moon_geometry(
    star: LunarContactStar,
    jd_ut1: float,
    observer_latitude_deg: float,
    observer_longitude_deg: float,
    observer_elevation_m: float,
    reader: object,
) -> tuple[float, float, float]:
    """Return physical separation, lunar PA, and topocentric lunar distance.

    This is the shared governing geometry for profile preparation and contact
    solving. The reader-bound lunar light cone is the retarded geometric
    location of the blocking surface, not an apparent direction for photons
    emitted by the Moon. Observer-relative gravitational deflection bends the
    incoming stellar ray only; curvature over the final Earth-Moon segment is
    neglected. The stellar deflection is the contact-private Klioner equation
    70 / IAU SOFA Ld object, using DE441 states and Ldn-style closest-passage
    placement. Observer-motion aberration and air remain excluded.
    """

    from .lunar_limb import _reader_bound_moon_light_cone
    from .occultations import (
        _angular_separation_equatorial,
        _position_angle_equatorial,
    )

    light_cone = _reader_bound_moon_light_cone(
        jd_ut1,
        observer_latitude_deg,
        observer_longitude_deg,
        observer_elevation_m,
        reader,  # type: ignore[arg-type]
    )
    moon_of_date = tuple(
        sum(
            light_cone.icrf_to_true_of_date[row][column]
            * light_cone.observer_to_moon_icrf[column]
            for column in range(3)
        )
        for row in range(3)
    )
    moon_ra = math.degrees(math.atan2(moon_of_date[1], moon_of_date[0])) % 360.0
    moon_dec = math.degrees(
        math.asin(max(-1.0, min(1.0, moon_of_date[2])))
    )
    star_physical_icrf = _reader_bound_deflected_star_icrf_direction(
        star,
        light_cone.observer_ssb_icrf,
        light_cone.jd_tt_reception,
        reader,
    )
    star_of_date = tuple(
        sum(
            light_cone.icrf_to_true_of_date[row][column]
            * star_physical_icrf[column]
            for column in range(3)
        )
        for row in range(3)
    )
    star_ra = math.degrees(math.atan2(star_of_date[1], star_of_date[0])) % 360.0
    star_dec = math.degrees(
        math.asin(max(-1.0, min(1.0, star_of_date[2])))
    )
    return (
        _angular_separation_equatorial(
            moon_ra,
            moon_dec,
            star_ra,
            star_dec,
        ),
        _position_angle_equatorial(
            moon_ra,
            moon_dec,
            star_ra,
            star_dec,
        ),
        light_cone.distance_km,
    )


def prepare_lola_rdr_lunar_star_contact_profile(
    star: LunarContactStar,
    jd_start_ut1: float,
    jd_end_ut1: float,
    observer_latitude_deg: float,
    observer_longitude_deg: float,
    *,
    reader: object,
    observer_elevation_m: float = 0.0,
    policy: LunarContactProfilePolicy | None = None,
    expected_lola_assets: Sequence[LunarLimbAssetIdentity] | None = None,
) -> LunarLimbContactProfile:
    """Materialize a site-bound LOLA profile from the actual contact trajectory.

    The physical star--Moon PA is sampled across the complete search window,
    unwrapped continuously, enlarged by the explicit guard band, and then
    converted into the bounded spatial profile request. The completed profile
    is re-evaluated at every trajectory witness before it is returned.
    """

    from .lunar_limb import build_lola_rdr_lunar_limb_event_profile

    if not isinstance(star, LunarContactStar):
        raise TypeError("star must be LunarContactStar")
    start = _finite_real("jd_start_ut1", jd_start_ut1)
    end = _finite_real("jd_end_ut1", jd_end_ut1)
    latitude = _finite_real("observer_latitude_deg", observer_latitude_deg)
    longitude = _finite_real("observer_longitude_deg", observer_longitude_deg)
    elevation = _finite_real("observer_elevation_m", observer_elevation_m)
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("observer_latitude_deg must be in [-90, 90]")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("observer_longitude_deg must be in [-180, 180]")
    if end <= start:
        raise ValueError("profile preparation window must be strictly increasing")
    if reader is None:
        raise TypeError("reader must be an explicit content-identified DE441 reader")
    selected = LunarContactProfilePolicy() if policy is None else policy
    if not isinstance(selected, LunarContactProfilePolicy):
        raise TypeError("policy must be LunarContactProfilePolicy")

    span_seconds = (end - start) * _SECONDS_PER_DAY
    max_profile_intervals = MAX_LUNAR_CONTACT_PROFILE_SLICES - 1
    if (
        span_seconds
        > selected.profile_time_step_seconds * max_profile_intervals
    ):
        raise ValueError(
            "profile preparation exceeds "
            "MAX_LUNAR_CONTACT_PROFILE_SLICES="
            f"{MAX_LUNAR_CONTACT_PROFILE_SLICES} under the selected "
            "profile_time_step_seconds"
        )
    trajectory_intervals = max(
        1,
        math.ceil(span_seconds / selected.trajectory_step_seconds),
    )
    if trajectory_intervals + 1 > 250_000:
        raise ValueError("profile PA trajectory exceeds the bounded witness count")
    _validate_star_reference_epoch(star, start, end, reader)
    trajectory_epochs = tuple(
        start + (end - start) * index / trajectory_intervals
        for index in range(trajectory_intervals + 1)
    )
    raw_pas = tuple(
        _physical_star_moon_geometry(
            star,
            epoch,
            latitude,
            longitude,
            elevation,
            reader,
        )[1]
        for epoch in trajectory_epochs
    )
    unwrapped_pas: list[float] = [raw_pas[0]]
    for previous_raw, current_raw in zip(raw_pas, raw_pas[1:]):
        delta = ((current_raw - previous_raw + 180.0) % 360.0) - 180.0
        unwrapped_pas.append(unwrapped_pas[-1] + delta)

    lower = min(unwrapped_pas) - selected.position_angle_guard_deg
    upper = max(unwrapped_pas) + selected.position_angle_guard_deg
    center = (lower + upper) / 2.0
    bin_count = math.ceil(
        (upper - lower) / selected.pa_bin_width_deg - 1.0e-12
    )
    if bin_count < 2:
        bin_count = 2
    half_width = bin_count * selected.pa_bin_width_deg / 2.0
    if half_width > 10.0:
        raise ValueError(
            "event-derived PA envelope exceeds the admitted 10-degree "
            "half-width for bounded LOLA tile discovery"
        )

    profile_intervals = max(
        1,
        math.ceil(span_seconds / selected.profile_time_step_seconds),
    )
    if profile_intervals + 1 > MAX_LUNAR_CONTACT_PROFILE_SLICES:
        raise ValueError(
            "profile preparation exceeds "
            "MAX_LUNAR_CONTACT_PROFILE_SLICES="
            f"{MAX_LUNAR_CONTACT_PROFILE_SLICES} under the selected "
            "profile_time_step_seconds"
        )
    profile_epochs = tuple(
        start + (end - start) * index / profile_intervals
        for index in range(profile_intervals + 1)
    )
    profile = build_lola_rdr_lunar_limb_event_profile(
        profile_epochs,
        latitude,
        longitude,
        elevation,
        center,
        reader=reader,  # type: ignore[arg-type]
        position_angle_half_width_deg=half_width,
        pa_bin_width_deg=selected.pa_bin_width_deg,
        max_pa_interpolation_gap_deg=selected.max_pa_interpolation_gap_deg,
        max_time_interpolation_gap_days=(
            selected.profile_time_step_seconds / _SECONDS_PER_DAY
        ),
        lola_query_half_width_km=selected.lola_query_floor_km,
        expected_lola_assets=expected_lola_assets,
    )

    # This is a coverage proof, not a numerical-accuracy oracle: every actual
    # trajectory PA must be evaluable through the frozen spatial/time profile.
    radius_at = getattr(profile, "radius_km_at")
    for epoch, pa in zip(trajectory_epochs, raw_pas):
        radius_at(epoch, pa)
    return profile


def lunar_star_topographic_contacts(
    star: LunarContactStar,
    jd_start_ut1: float,
    jd_end_ut1: float,
    observer_latitude_deg: float,
    observer_longitude_deg: float,
    *,
    profile: LunarLimbContactProfile,
    observer_elevation_m: float = 0.0,
    reader: object | None = None,
    policy: ContactSearchPolicy | None = None,
    geometry_evaluator: ContactGeometryEvaluator | None = None,
) -> LunarOccultationContactSequence:
    """Predict an ordered profile-conditioned stellar contact sequence.

    The search window is open at both ends.  A contact coincident with either
    boundary is rejected because its missing outside state makes chronology
    ambiguous.  ``geometry_evaluator`` is an injectable, already site-bound
    test/research surface; when omitted, Moira lazily delegates instantaneous
    geometry from one reader-bound physical Moon light cone and one received
    stellar ray. An injected evaluator is marked explicitly in the immutable
    result and cannot be combined with an unused reader. Observer-motion
    aberration and atmospheric refraction are excluded from this
    surface-intersection product.

    ``profile`` must already own all admitted data in memory.  This function
    performs no profile loading or network access.
    """

    if not isinstance(star, LunarContactStar):
        raise TypeError("star must be LunarContactStar")
    observer_latitude = _finite_real(
        "observer_latitude_deg", observer_latitude_deg
    )
    observer_longitude = _finite_real(
        "observer_longitude_deg", observer_longitude_deg
    )
    observer_elevation = _finite_real(
        "observer_elevation_m", observer_elevation_m
    )
    start = _finite_real("jd_start_ut1", jd_start_ut1)
    end = _finite_real("jd_end_ut1", jd_end_ut1)
    if not -90.0 <= observer_latitude <= 90.0:
        raise ValueError("observer_latitude_deg must be in [-90, 90]")
    if not -180.0 <= observer_longitude <= 180.0:
        raise ValueError("observer_longitude_deg must be in [-180, 180]")
    if end <= start:
        raise ValueError("contact search window must be strictly increasing")
    profile_model, profile_provenance = _profile_identity(profile)
    _validate_profile_time_coverage(profile, start, end)
    _validate_profile_site(
        profile,
        observer_latitude,
        observer_longitude,
        observer_elevation,
    )
    profile_provider = _profile_adjustment_callable(profile)
    selected_policy = ContactSearchPolicy() if policy is None else policy
    if not isinstance(selected_policy, ContactSearchPolicy):
        raise TypeError("policy must be ContactSearchPolicy")

    if geometry_evaluator is None:
        if reader is None:
            raise TypeError(
                "reader must be supplied for reader-bound physical star geometry"
            )
        _validate_star_reference_epoch(star, start, end, reader)
        reader_label = _reader_bound_geometry_label(reader, start, end)
        profile_source = getattr(profile, "source", None)
        if profile_source is not None:
            translation_model = _nonempty_text(
                "profile.source.translation_model",
                getattr(profile_source, "translation_model", None),
            )
            expected_translation_model = (
                "reader-bound DE441/LE441 physical reception light cone: "
                f"{reader_label}"
            )
            if translation_model != expected_translation_model:
                raise ValueError(
                    "contact reader identity does not match the prepared "
                    "profile translation model"
                )
        geometry_mode = LunarContactGeometryMode.READER_BOUND_DE441
        geometry_provenance = (
            f"content-derived ephemeris={reader_label}; "
            "retarded geometric lunar blocker; observer-relative stellar ray; "
            "contact-private Klioner (2003) Eq.70 / IAU SOFA Ld-Ldn "
            "solar-Jupiter-Saturn deflection from DE441 barycentric states; "
            "closest-passage backtracking with limiters 6e-6/3e-9/3e-10; "
            "exact finite-star deflector-to-source direction; no observer-motion "
            "aberration; no atmospheric refraction"
        )
        # Lazy import preserves the module's pure solver boundary and avoids
        # importing the kernel-backed occultation engine for vessel-only use.
        from .eclipse_geometry import MOON_RADIUS_KM, apparent_radius

        def default_geometry(
            jd_ut1: float,
            _profile: LunarLimbContactProfile,
        ) -> ContactGeometry:
            separation, position_angle, moon_distance_km = (
                _physical_star_moon_geometry(
                    star,
                    jd_ut1,
                    observer_latitude,
                    observer_longitude,
                    observer_elevation,
                    reader,
                )
            )
            lunar_radius = apparent_radius(MOON_RADIUS_KM, moon_distance_km)
            lunar_radius += profile_provider(
                jd_ut1,
                observer_latitude,
                observer_longitude,
                observer_elevation,
                position_angle,
                moon_distance_km,
            )
            return ContactGeometry(
                signed_clearance_deg=separation - lunar_radius,
                position_angle_deg=position_angle,
            )

        selected_evaluator: ContactGeometryEvaluator = default_geometry
    else:
        if not callable(geometry_evaluator):
            raise TypeError("geometry_evaluator must be callable")
        if reader is not None:
            raise ValueError(
                "reader must be omitted when geometry_evaluator is caller-injected"
            )
        geometry_mode = LunarContactGeometryMode.CALLER_INJECTED
        geometry_provenance = (
            "caller-injected ContactGeometryEvaluator; no reader-bound "
            "astronomical geometry claim"
        )
        selected_evaluator = geometry_evaluator

    geometry_cache: dict[float, ContactGeometry] = {}

    def geometry_at(jd_ut1: float) -> ContactGeometry:
        cached = geometry_cache.get(jd_ut1)
        if cached is not None:
            return cached
        geometry = selected_evaluator(jd_ut1, profile)
        if not isinstance(geometry, ContactGeometry):
            raise TypeError("geometry_evaluator must return ContactGeometry")
        geometry_cache[jd_ut1] = geometry
        return geometry

    initial, final, solved = _solve_signed_clearance_contacts(
        start,
        end,
        lambda jd_ut1: geometry_at(jd_ut1).signed_clearance_deg,
        selected_policy,
    )
    contacts = tuple(
        LunarOccultationContact(
            jd_ut1=item.jd_ut1,
            kind=item.kind,
            visibility_before=item.visibility_before,
            visibility_after=item.visibility_after,
            position_angle_deg=geometry_at(item.jd_ut1).position_angle_deg,
            signed_clearance_deg=geometry_at(item.jd_ut1).signed_clearance_deg,
            bracket_start_jd_ut1=item.bracket_start_jd_ut1,
            bracket_end_jd_ut1=item.bracket_end_jd_ut1,
        )
        for item in solved
    )
    return LunarOccultationContactSequence(
        star=star,
        observer_latitude_deg=observer_latitude,
        observer_longitude_deg=observer_longitude,
        observer_elevation_m=observer_elevation,
        jd_start_ut1=start,
        jd_end_ut1=end,
        initial_visibility=initial,
        final_visibility=final,
        contacts=contacts,
        profile_model=profile_model,
        profile_provenance=profile_provenance,
        policy=selected_policy,
        geometry_mode=geometry_mode,
        geometry_provenance=geometry_provenance,
    )


__all__ = [
    "MAX_LUNAR_CONTACT_PROFILE_SLICES",
    "ContactGeometry",
    "ContactGeometryEvaluator",
    "ContactSearchPolicy",
    "LunarContactProfilePolicy",
    "LunarContactStar",
    "LunarContactGeometryMode",
    "LunarContactKind",
    "LunarLimbContactProfile",
    "LunarOccultationContact",
    "LunarOccultationContactSequence",
    "LunarVisibilityState",
    "lunar_contact_star_at",
    "lunar_star_topographic_contacts",
    "prepare_lola_rdr_lunar_star_contact_profile",
]
