"""Neutral Mundane event and local-chart receipt composition.

Astronomical roots remain owned by Moira's transit, eclipse, cycle, planetary,
clock, and local-angle engines.  This module revalidates those engine products,
copies their search truth into immutable receipts, composes only explicitly
bound components, and keeps incomplete work visible as typed
``not_evaluable`` evidence.  It provides no mundane interpretation.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import InitVar, dataclass, field
from typing import TypeAlias

from ._strenum import StrEnum
from .houses import HouseCusps, HousePolicy, calculate_houses


__all__ = [
    "MundaneEvaluationStatus",
    "MundaneEventType",
    "MundaneProfileComponent",
    "MundaneProfileExclusion",
    "MundaneNotEvaluableReason",
    "MundaneTimescale",
    "MundaneUtcRealizationStatus",
    "MundaneProvenanceMode",
    "MundaneLongitudeDefinition",
    "MundaneZodiacModality",
    "CardinalIngress",
    "CardinalIngressSelectionPolicy",
    "PrimarySyzygyPhase",
    "EclipseKind",
    "EclipseAnchorEpoch",
    "EclipseContactKind",
    "JupiterSaturnConjunctionDefinition",
    "MundaneMotionState",
    "MundaneLocationRole",
    "MundaneEpoch",
    "MundaneSearchInterval",
    "MundaneRootSearchReceipt",
    "MundaneEventClockReceipt",
    "MundaneAngularRootToleranceReceipt",
    "MundaneEventProvenance",
    "MundaneNotEvaluable",
    "CardinalIngressReceipt",
    "CardinalIngressSelectionReceipt",
    "CardinalIngressSelectionEvidence",
    "MundaneAscendantReceipt",
    "RameseyIngressCadenceReceipt",
    "RameseyIngressCadenceEvidence",
    "PrimarySyzygyReceipt",
    "PrecedingSyzygySelectionReceipt",
    "PrecedingSyzygyEvidence",
    "EclipseNamedEpochReceipt",
    "EclipseContactEpochReceipt",
    "EclipseEventReceipt",
    "JupiterSaturnConjunctionReceipt",
    "JupiterSaturnConjunctionSequenceReceipt",
    "MundaneLocationSelectionReceipt",
    "MundaneHouseComputationReceipt",
    "MundaneLocalProjectionReceipt",
    "MundaneEventEvidence",
    "MundaneLocalProjectionEvidence",
    "MundaneProfileProvenance",
    "MundaneEventChartProfile",
    "MundaneEventReceipt",
    "select_cardinal_ingresses",
    "select_strictly_preceding_primary_syzygy",
    "build_mundane_local_projection",
    "build_mundane_event_clock",
    "assess_transit_cardinal_ingress",
    "assess_transit_primary_syzygy",
    "assess_ramesey_ingress_cadence",
    "compose_mundane_event_chart_profile",
    "eclipse_receipt_from_event",
    "jupiter_saturn_sequence_from_series",
]


class MundaneEvaluationStatus(StrEnum):
    """Evaluation state for one receipt-bearing profile component."""

    EVALUATED = "evaluated"
    NOT_EVALUABLE = "not_evaluable"


class MundaneEventType(StrEnum):
    """Finite global-event types admitted to the neutral v1 contract."""

    CARDINAL_INGRESS = "cardinal_ingress"
    PRIMARY_SYZYGY = "primary_syzygy"
    ECLIPSE = "eclipse"
    JUPITER_SATURN_ECLIPTIC_LONGITUDE_CONJUNCTION = (
        "jupiter_saturn_ecliptic_longitude_conjunction"
    )


class MundaneProfileComponent(StrEnum):
    """Independently evaluable components of a Mundane event-chart profile."""

    ANCHOR_EVENT = "anchor_event"
    CARDINAL_INGRESS_SELECTION = "cardinal_ingress_selection"
    PRECEDING_PRIMARY_SYZYGY = "preceding_primary_syzygy"
    LOCAL_CHART_PROJECTION = "local_chart_projection"
    LOCAL_ECLIPSE_CIRCUMSTANCES = "local_eclipse_circumstances"


class MundaneProfileExclusion(StrEnum):
    """Interpretive branches structurally excluded from the neutral profile."""

    POLITICAL_PREDICTION = "political_prediction"
    ECONOMIC_PREDICTION = "economic_prediction"
    DISASTER_PREDICTION = "disaster_prediction"
    WEATHER_PREDICTION = "weather_prediction"
    CONFLICT_PREDICTION = "conflict_prediction"
    NATIONAL_FATE = "national_fate"
    COUNTRY_SIGN_RULERSHIP = "country_sign_rulership"
    GREAT_MUTATION_INTERPRETATION = "great_mutation_interpretation"


class MundaneNotEvaluableReason(StrEnum):
    """Closed reasons for refusing to fabricate a missing component."""

    GLOBAL_EVENT_UNAVAILABLE = "global_event_unavailable"
    NO_STRICTLY_PRECEDING_SYZYGY = "no_strictly_preceding_syzygy"
    NO_COMMON_TIMESCALE = "no_common_timescale"
    MISSING_LOCATION = "missing_location"
    AMBIGUOUS_LOCATION_SELECTION = "ambiguous_location_selection"
    LOCATION_VALIDITY_UNAVAILABLE = "location_validity_unavailable"
    LOCATION_NOT_VALID_AT_EVENT = "location_not_valid_at_event"
    HOUSE_SYSTEM_NOT_SUPPLIED = "house_system_not_supplied"
    HOUSE_PROJECTION_FAILED = "house_projection_failed"
    INCOMPATIBLE_FRAME = "incompatible_frame"
    INCOMPATIBLE_CORRECTION_REGIME = "incompatible_correction_regime"
    INCOMPATIBLE_PROVENANCE = "incompatible_provenance"
    INCOMPATIBLE_KERNEL_IDENTITY = "incompatible_kernel_identity"
    INCOMPATIBLE_SOLVER_SEMANTICS = "incompatible_solver_semantics"
    LOCAL_ECLIPSE_CIRCUMSTANCES_UNAVAILABLE = (
        "local_eclipse_circumstances_unavailable"
    )
    EVENT_SEMANTICS_MISMATCH = "event_semantics_mismatch"
    SOURCE_RECEIPT_INCOMPLETE = "source_receipt_incomplete"
    HOUSE_INPUT_TIMESCALE_NOT_UT1 = "house_input_timescale_not_ut1"
    INCOMPATIBLE_CLOCK_REALIZATION = "incompatible_clock_realization"


class MundaneTimescale(StrEnum):
    """Timescale attached to one supplied epoch; no conversion is implied."""

    UTC = "utc"
    UT1 = "ut1"
    TT = "tt"
    TDB = "tdb"


class MundaneUtcRealizationStatus(StrEnum):
    """Whether one UT1 epoch has a civil UTC realization in this receipt."""

    REALIZED_POST_1972_ATOMIC = "realized_post_1972_atomic"
    NOT_REALIZED_HISTORICAL_UT1_PROXY = "not_realized_historical_ut1_proxy"


class MundaneProvenanceMode(StrEnum):
    """Origin regime for one caller-supplied astronomical receipt."""

    MOIRA_EPHEMERIS = "moira_ephemeris"
    EXTERNAL_AUTHORITY = "external_authority"
    HISTORICAL_TABLE = "historical_table"
    CALLER_ASSERTED = "caller_asserted"


class MundaneLongitudeDefinition(StrEnum):
    """Distinct longitude products used by the admitted event types."""

    SUN_OBSERVER_CENTERED_GEOCENTRIC_APPARENT_IAU2006_P03_IAU2000A_TRUE_ECLIPTIC_EQUINOX_OF_DATE = (
        "sun_observer_centered_geocentric_apparent_iau2006_p03_iau2000a_"
        "true_ecliptic_equinox_of_date"
    )
    SUN_MOON_OBSERVER_CENTERED_GEOCENTRIC_APPARENT_IAU2006_P03_IAU2000A_TRUE_ECLIPTIC_LONGITUDE_DIFFERENCE = (
        "sun_moon_observer_centered_geocentric_apparent_iau2006_p03_"
        "iau2000a_true_ecliptic_longitude_difference"
    )
    JUPITER_SATURN_GEOCENTRIC_APPARENT_ECLIPTIC_DIFFERENCE = (
        "jupiter_saturn_geocentric_apparent_ecliptic_difference"
    )


class CardinalIngress(StrEnum):
    """The four increasing solar longitude roots admitted by v1."""

    ARIES = "aries"
    CANCER = "cancer"
    LIBRA = "libra"
    CAPRICORN = "capricorn"

    @property
    def target_longitude_deg(self) -> float:
        return {
            CardinalIngress.ARIES: 0.0,
            CardinalIngress.CANCER: 90.0,
            CardinalIngress.LIBRA: 180.0,
            CardinalIngress.CAPRICORN: 270.0,
        }[self]


class CardinalIngressSelectionPolicy(StrEnum):
    """Source-named ingress selection policies; never hidden defaults."""

    ALL_FOUR_CARDINAL_INGRESSES_V1 = "all_four_cardinal_ingresses_v1"
    RAMESEY_1653_ASCENDANT_MODALITY_V1 = "ramesey_1653_ascendant_modality_v1"


class MundaneZodiacModality(StrEnum):
    """Modality of the tropical Ascendant sign used by Ramesey cadence."""

    CARDINAL = "cardinal"
    FIXED = "fixed"
    MUTABLE = "mutable"


class PrimarySyzygyPhase(StrEnum):
    """The two exact phase roots admitted to primary-syzygy selection."""

    NEW_MOON = "new_moon"
    FULL_MOON = "full_moon"


class EclipseKind(StrEnum):
    """Global eclipse family."""

    SOLAR = "solar"
    LUNAR = "lunar"


class EclipseAnchorEpoch(StrEnum):
    """Named eclipse epochs that may anchor a profile."""

    ECLIPTIC_SYZYGY = "ecliptic_syzygy"
    EQUATORIAL_CONJUNCTION = "equatorial_conjunction"
    EQUATORIAL_OPPOSITION = "equatorial_opposition"
    GREATEST_ECLIPSE = "greatest_eclipse"


class EclipseContactKind(StrEnum):
    """Closed global contact names spanning solar and lunar eclipses."""

    C1 = "c1"
    C2 = "c2"
    C3 = "c3"
    C4 = "c4"
    P1 = "p1"
    U1 = "u1"
    U2 = "u2"
    U3 = "u3"
    U4 = "u4"
    P4 = "p4"


class JupiterSaturnConjunctionDefinition(StrEnum):
    """Conjunction-like products that must never be conflated."""

    ECLIPTIC_LONGITUDE = "ecliptic_longitude_conjunction"
    RIGHT_ASCENSION = "right_ascension_conjunction"
    MINIMUM_ELONGATION = "minimum_elongation"


class MundaneMotionState(StrEnum):
    """Motion state retained independently for Jupiter and Saturn."""

    DIRECT = "direct"
    RETROGRADE = "retrograde"
    STATIONARY = "stationary"


class MundaneLocationRole(StrEnum):
    """Closed caller-selected location roles; the engine selects none."""

    USER_SPECIFIED = "user_specified"
    SEAT_OF_GOVERNMENT = "seat_of_government"
    CONSTITUTIONAL_CAPITAL = "constitutional_capital"
    ADMINISTRATIVE_CAPITAL = "administrative_capital"
    REGIONAL_CENTER = "regional_center"


_INSTITUTIONAL_LOCATION_ROLES = frozenset(
    role for role in MundaneLocationRole if role is not MundaneLocationRole.USER_SPECIFIED
)

_MOIRA_SOLAR_APPARENT_LONGITUDE_PRODUCT = (
    "moira_observer_centered_geocentric_apparent_solar_longitude_"
    "iau2006_p03_iau2000a_true_ecliptic_and_equinox_of_date"
)
_PRIMARY_SYZYGY_LONGITUDE_PRODUCT = (
    "moira_observer_centered_geocentric_apparent_sun_moon_longitude_"
    "difference_iau2006_p03_iau2000a_true_ecliptic_and_equinox_of_date"
)
_MOIRA_TRUE_OF_DATE_REFERENCE_FRAME = (
    "iau2006_p03_iau2000a_true_ecliptic_and_equinox_of_date"
)
_SUN_MOON_CORRECTION_REGIME = (
    "geocentric_apparent_light_time_annual_aberration_iau2006_frame_bias_"
    "precession_iau2000a_nutation_true_ecliptic_projection"
)
_JUPITER_SATURN_LONGITUDE_PRODUCT = (
    "moira_geocentric_apparent_jupiter_saturn_ecliptic_longitude_difference_"
    "true_ecliptic_of_date"
)
_JUPITER_SATURN_REFERENCE_FRAME = _MOIRA_TRUE_OF_DATE_REFERENCE_FRAME
_JUPITER_SATURN_CORRECTION_REGIME = (
    "geocentric_apparent_light_time_deflection_aberration_nutation"
)
_JUPITER_SATURN_SOLVER_SEMANTICS = (
    "moira_phenomena_apparent_bisection_and_representable_jd_polish_v1"
)
_ECLIPSE_REFERENCE_FRAME = (
    "moira_native_geocentric_physical_shadow_axis_event_geometry_v1"
)
_SOLAR_ECLIPSE_CORRECTION_REGIME = (
    "earth_reception_light_time_sun_and_moon_shadow_axis_"
    "stellar_aberration_excluded_v1"
)
_LUNAR_ECLIPSE_CORRECTION_REGIME = (
    "earth_reception_light_time_solar_shadow_axis_physical_geocentric_moon_"
    "stellar_aberration_excluded_v1"
)
_MAX_CARDINAL_INGRESS_CYCLE_DAYS = 370.0
_MAX_ECLIPSE_EVENT_SPAN_DAYS = 2.0
_ECLIPSE_GREATEST_RECHECK_TOLERANCE_DAYS = 0.1 / 86400.0
_MAX_ADMITTED_ANGULAR_ROOT_TOLERANCE_DEG = 1e-3
_TRANSIT_ADAPTER_ROOT_TOLERANCE_DEG = 1e-5
_JUPITER_SATURN_ADAPTER_ROOT_TOLERANCE_DEG = 1e-6
_VERIFIED_READER_IDENTITY_TOKEN = object()
_MOIRA_PROVENANCE_TOKEN = object()
_EVENT_CLOCK_TOKEN = object()
_ROOT_SEARCH_TOKEN = object()
_ASCENDANT_RECEIPT_TOKEN = object()
_POST_1972_ATOMIC_UTC_START_JD = 2441317.5
_MUNDANE_CLOCK_ROUTES = ((0, 3), (3, 399), (3, 301), (0, 10))
_MUNDANE_JUPITER_SATURN_ROUTES = _MUNDANE_CLOCK_ROUTES + ((0, 5), (0, 6))


def _trimmed(name: str, value: str) -> None:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty trimmed built-in string")


def _require_builtin_tuple(name: str, value: object) -> None:
    """Reject mutable or behavior-overriding stand-ins for receipt tuples."""

    if type(value) is not tuple:
        raise TypeError(f"{name} must be a built-in tuple")


def _as_builtin_float(name: str, value: object) -> float:
    """Canonicalize only ordinary Python numbers; reject behavioral subclasses."""

    if type(value) not in (int, float):
        raise TypeError(f"{name} must be a built-in int or float")
    canonical = float(value)
    if not math.isfinite(canonical):
        raise ValueError(f"{name} must be finite")
    return canonical


def _longitude(name: str, value: object) -> float:
    canonical = _as_builtin_float(name, value)
    if not 0.0 <= canonical < 360.0:
        raise ValueError(f"{name} must be finite and in [0, 360)")
    return canonical


def _signed_angle_delta(value: float, target: float) -> float:
    return (value - target + 180.0) % 360.0 - 180.0


@dataclass(frozen=True, slots=True)
class MundaneAngularRootToleranceReceipt:
    """Explicit angular admission bound for one supplied numerical root."""

    maximum_abs_residual_deg: float
    basis: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "maximum_abs_residual_deg",
            _as_builtin_float(
                "angular root tolerance",
                self.maximum_abs_residual_deg,
            ),
        )
        if (
            self.maximum_abs_residual_deg <= 0.0
            or self.maximum_abs_residual_deg
            > _MAX_ADMITTED_ANGULAR_ROOT_TOLERANCE_DEG
        ):
            raise ValueError(
                "angular root tolerance must be finite, positive, and no greater "
                f"than {_MAX_ADMITTED_ANGULAR_ROOT_TOLERANCE_DEG} degrees"
            )
        _trimmed("MundaneAngularRootToleranceReceipt basis", self.basis)


@dataclass(frozen=True, slots=True)
class _VerifiedReaderIdentity:
    """Private proof that Moira resolved an SPK content label at one epoch.

    The proof token is an InitVar on purpose: normal direct construction and
    ``dataclasses.replace`` cannot create or alter an engine-verified identity.
    This receipt does not pretend that the multi-gigabyte SPK was hashed.
    """

    summary_label: str
    planetary_ephemeris: str | None
    lunar_ephemeris: str | None
    verification_basis: str = "spk_summary_label_content"
    _verification_token: InitVar[object | None] = None

    def __post_init__(self, _verification_token: object | None) -> None:
        if _verification_token is not _VERIFIED_READER_IDENTITY_TOKEN:
            raise ValueError(
                "verified reader identity must be produced from the active reader"
            )
        _trimmed("verified reader summary_label", self.summary_label)
        if self.planetary_ephemeris is not None:
            _trimmed(
                "verified reader planetary_ephemeris",
                self.planetary_ephemeris,
            )
        if self.lunar_ephemeris is not None:
            _trimmed("verified reader lunar_ephemeris", self.lunar_ephemeris)
        if self.verification_basis != "spk_summary_label_content":
            raise ValueError("verified reader identity basis is fixed")


def _verified_reader_identity_at(
    reader: object,
    jd_ut1: float,
    *,
    required_routes: tuple[tuple[int, int], ...] = _MUNDANE_CLOCK_ROUTES,
) -> _VerifiedReaderIdentity:
    """Resolve a content-derived reader label without hashing the SPK artifact."""

    from ._ephemeris_time import _ut1_to_ephemeris_tt
    from .spk_reader import (
        KernelPool,
        _EphemerisKernelIdentity,
        _OriginalSpkReader,
        _ephemeris_kernel_identity_from_catalog,
    )

    if type(reader) is _OriginalSpkReader:
        if any(
            method_name in getattr(reader, "__dict__", {})
            for method_name in (
                "has_segment_at",
                "position",
                "position_and_velocity",
            )
        ):
            raise TypeError("SpkReader dispatch methods must be the concrete class methods")
        identity_owner = reader
    elif type(reader) is KernelPool:
        if "_ephemeris_kernel_identity_at" in getattr(reader, "__dict__", {}):
            raise TypeError("KernelPool identity resolver must be the concrete class method")
        pool_readers = getattr(reader, "_readers", None)
        if type(pool_readers) is not list:
            raise TypeError("KernelPool reader storage is not the admitted concrete vessel")
    else:
        raise TypeError(
            "Moira event provenance requires a concrete SpkReader or KernelPool"
        )

    jd_tt = _ut1_to_ephemeris_tt(jd_ut1, reader)
    if type(reader) is _OriginalSpkReader:
        if not all(
            _OriginalSpkReader.has_segment_at(reader, center, target, jd_tt)
            for center, target in required_routes
        ):
            raise ValueError(
                "SpkReader does not cover every required Mundane planetary route "
                "at the event epoch"
            )
    else:
        owners = []
        for center, target in required_routes:
            owner = None
            for child in pool_readers:
                try:
                    serves_route = child.has_segment_at(center, target, jd_tt)
                except Exception as exc:
                    raise TypeError(
                        "KernelPool route ownership must be deterministically inspectable"
                    ) from exc
                if type(serves_route) is not bool:
                    raise TypeError("KernelPool route coverage must return a built-in bool")
                if serves_route:
                    owner = child
                    break
            if owner is None:
                raise ValueError(
                    "KernelPool does not cover every required Mundane planetary route"
                )
            if type(owner) is not _OriginalSpkReader:
                raise TypeError(
                    "KernelPool planetary dispatch owner must be a concrete SpkReader"
                )
            if any(
                method_name in getattr(owner, "__dict__", {})
                for method_name in (
                    "has_segment_at",
                    "position",
                    "position_and_velocity",
                )
            ):
                raise TypeError(
                    "KernelPool SpkReader dispatch methods must be concrete class methods"
                )
            if not _OriginalSpkReader.has_segment_at(
                owner,
                center,
                target,
                jd_tt,
            ):
                raise ValueError(
                    "KernelPool dispatch owner does not concretely cover its claimed route"
                )
            owners.append(owner)
        if any(owner is not owners[0] for owner in owners[1:]):
            raise ValueError(
                "KernelPool Mundane planetary routes must share one dispatch owner"
            )
        identity_owner = owners[0]
    cached_identity = getattr(identity_owner, "_kernel_identity", None)
    if cached_identity is None:
        raise ValueError(
            "Moira event adaptation requires a content-identified ephemeris reader"
        )
    if type(cached_identity) is not _EphemerisKernelIdentity:
        raise TypeError("admitted reader exposes a non-canonical ephemeris identity")
    kernel = getattr(identity_owner, "_kernel", None)
    catalog = getattr(kernel, "catalog", None)
    if type(catalog) is not dict:
        raise TypeError("SpkReader identity must derive from its active kernel catalog")
    identity = _ephemeris_kernel_identity_from_catalog(catalog)
    if identity != cached_identity:
        raise ValueError(
            "SpkReader cached identity does not match its active kernel content"
        )
    return _VerifiedReaderIdentity(
        summary_label=identity.summary_label,
        planetary_ephemeris=identity.planetary_ephemeris,
        lunar_ephemeris=identity.lunar_ephemeris,
        _verification_token=_VERIFIED_READER_IDENTITY_TOKEN,
    )


@dataclass(frozen=True, slots=True)
class MundaneEpoch:
    """One JD value under an explicitly named timescale."""

    jd: float
    timescale: MundaneTimescale

    def __post_init__(self) -> None:
        object.__setattr__(self, "jd", _as_builtin_float("MundaneEpoch jd", self.jd))
        if type(self.timescale) is not MundaneTimescale:
            raise TypeError("MundaneEpoch timescale must be a MundaneTimescale")


@dataclass(frozen=True, slots=True)
class MundaneSearchInterval:
    """One explicit half-open event-search interval ``[start, end)``."""

    start: MundaneEpoch
    end: MundaneEpoch

    def __post_init__(self) -> None:
        if type(self.start) is not MundaneEpoch or type(self.end) is not MundaneEpoch:
            raise TypeError("MundaneSearchInterval endpoints must be MundaneEpoch values")
        MundaneEpoch.__post_init__(self.start)
        MundaneEpoch.__post_init__(self.end)
        if self.start.timescale is not self.end.timescale:
            raise ValueError("MundaneSearchInterval endpoints require one timescale")
        if self.end.jd <= self.start.jd:
            raise ValueError("MundaneSearchInterval must be a non-empty half-open interval")

    @property
    def timescale(self) -> MundaneTimescale:
        return self.start.timescale

    def contains(self, epoch: MundaneEpoch) -> bool:
        """Return whether *epoch* lies in this interval without conversion."""

        if type(epoch) is not MundaneEpoch:
            raise TypeError("MundaneSearchInterval contains requires a MundaneEpoch")
        MundaneEpoch.__post_init__(epoch)
        return (
            epoch.timescale is self.timescale
            and self.start.jd <= epoch.jd < self.end.jd
        )


@dataclass(frozen=True, slots=True)
class MundaneRootSearchReceipt:
    """Immutable engine-built copy of one solved crossing's search truth."""

    search_interval: MundaneSearchInterval
    bracket_start: MundaneEpoch
    bracket_end: MundaneEpoch
    root_epoch: MundaneEpoch
    step_days: float
    solver_tolerance_days: float
    target_angle_deg: float
    root_residual_deg: float
    bracket_start_residual_deg: float
    bracket_end_residual_deg: float
    search_kind: str
    solver_method_id: str
    verified_reader_identity: _VerifiedReaderIdentity
    _verification_token: InitVar[object | None] = None

    def __post_init__(self, _verification_token: object | None) -> None:
        if _verification_token is not _ROOT_SEARCH_TOKEN:
            raise ValueError("root search receipt must be produced by a reader-bound adapter")
        for field_name in (
            "step_days",
            "solver_tolerance_days",
            "root_residual_deg",
            "bracket_start_residual_deg",
            "bracket_end_residual_deg",
        ):
            object.__setattr__(
                self,
                field_name,
                _as_builtin_float(
                    f"root search {field_name}",
                    getattr(self, field_name),
                ),
            )
        object.__setattr__(
            self,
            "target_angle_deg",
            _longitude("root search target angle", self.target_angle_deg),
        )
        if type(self.search_interval) is not MundaneSearchInterval:
            raise TypeError("root search interval must be typed")
        for name, epoch in (
            ("bracket_start", self.bracket_start),
            ("bracket_end", self.bracket_end),
            ("root_epoch", self.root_epoch),
        ):
            if type(epoch) is not MundaneEpoch:
                raise TypeError(f"{name} must be a MundaneEpoch")
            if epoch.timescale is not self.search_interval.timescale:
                raise ValueError("root search epochs require one explicit timescale")
        if self.search_interval.timescale is not MundaneTimescale.UT1:
            raise ValueError("reader-bound root search truth requires UT1")
        if not self.search_interval.contains(self.root_epoch):
            raise ValueError("root must lie in the half-open search interval")
        if not (
            self.search_interval.start.jd <= self.bracket_start.jd
            <= self.root_epoch.jd
            <= self.bracket_end.jd
            <= self.search_interval.end.jd
        ):
            raise ValueError("final root bracket must be ordered inside the search interval")
        if self.step_days <= 0.0:
            raise ValueError("root search step_days must be finite and positive")
        if (
            self.solver_tolerance_days <= 0.0
        ):
            raise ValueError("root solver tolerance must be finite and positive")
        bracket_width = self.bracket_end.jd - self.bracket_start.jd
        if bracket_width > self.solver_tolerance_days + 4.0 * math.ulp(
            max(1.0, abs(self.root_epoch.jd))
        ):
            raise ValueError("final root bracket exceeds the declared solver tolerance")
        if self.bracket_start_residual_deg * self.bracket_end_residual_deg > 0.0:
            raise ValueError("final root bracket must contain an angular sign crossing")
        _trimmed("MundaneRootSearchReceipt search_kind", self.search_kind)
        _trimmed("MundaneRootSearchReceipt solver_method_id", self.solver_method_id)
        if type(self.verified_reader_identity) is not _VerifiedReaderIdentity:
            raise TypeError("root search reader identity must be engine-verified")


@dataclass(frozen=True, slots=True)
class MundaneEventClockReceipt:
    """Reader-bound UT1/TT clock reduction with an honest optional UTC label."""

    ut1: MundaneEpoch
    tt: MundaneEpoch
    delta_t_seconds: float
    delta_t_source_product: str
    delta_t_retarget_mode: str
    delta_t_correction_seconds: float
    delta_t_tidal_source_products: tuple[str, ...]
    delta_t_target_reader_identity: str | None
    utc: MundaneEpoch | None
    utc_realization_status: MundaneUtcRealizationStatus
    utc_realization_detail: str
    verified_reader_identity: _VerifiedReaderIdentity
    _verification_token: InitVar[object | None] = None

    def __post_init__(self, _verification_token: object | None) -> None:
        if _verification_token is not _EVENT_CLOCK_TOKEN:
            raise ValueError("event clock receipt must be produced by the engine")
        for field_name in (
            "delta_t_seconds",
            "delta_t_correction_seconds",
        ):
            object.__setattr__(
                self,
                field_name,
                _as_builtin_float(
                    f"event clock {field_name}",
                    getattr(self, field_name),
                ),
            )
        if type(self.ut1) is not MundaneEpoch or self.ut1.timescale is not MundaneTimescale.UT1:
            raise TypeError("event clock ut1 must be an explicit UT1 epoch")
        if type(self.tt) is not MundaneEpoch or self.tt.timescale is not MundaneTimescale.TT:
            raise TypeError("event clock tt must be an explicit TT epoch")
        expected_tt = self.ut1.jd + self.delta_t_seconds / 86400.0
        if not math.isclose(self.tt.jd, expected_tt, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("event clock TT must derive exactly from UT1 and Delta-T")
        _trimmed("event clock Delta-T source product", self.delta_t_source_product)
        if self.delta_t_retarget_mode not in {"declared", "basis_neutral", "policy_locked"}:
            raise ValueError("event clock Delta-T retarget mode is unsupported")
        _trimmed("event clock Delta-T retarget mode", self.delta_t_retarget_mode)
        _require_builtin_tuple(
            "MundaneEventClockReceipt delta_t_tidal_source_products",
            self.delta_t_tidal_source_products,
        )
        if len(self.delta_t_tidal_source_products) != len(
            set(self.delta_t_tidal_source_products)
        ) or any(
            type(item) is not str or not item or item != item.strip()
            for item in self.delta_t_tidal_source_products
        ):
            raise ValueError("Delta-T tidal source products must be unique trimmed strings")
        if self.delta_t_target_reader_identity is not None:
            _trimmed(
                "event clock Delta-T target reader identity",
                self.delta_t_target_reader_identity,
            )
        if type(self.utc_realization_status) is not MundaneUtcRealizationStatus:
            raise TypeError("event clock UTC realization status must be typed")
        _trimmed("event clock UTC realization detail", self.utc_realization_detail)
        if self.utc_realization_status is MundaneUtcRealizationStatus.REALIZED_POST_1972_ATOMIC:
            if (
                type(self.utc) is not MundaneEpoch
                or self.utc.timescale is not MundaneTimescale.UTC
                or self.ut1.jd < _POST_1972_ATOMIC_UTC_START_JD
            ):
                raise ValueError("post-1972 UTC status requires a realized UTC epoch")
        elif self.utc is not None:
            raise ValueError("historical UT1-proxy status must not carry a UTC epoch")
        if type(self.verified_reader_identity) is not _VerifiedReaderIdentity:
            raise TypeError("event clock reader identity must be engine-verified")


def build_mundane_event_clock(
    jd_ut1: float,
    *,
    reader: object,
) -> MundaneEventClockReceipt:
    """Build one reader-bound clock receipt without inventing historical UTC."""

    from ._ephemeris_time import _ephemeris_delta_t
    from .julian import _ut1_to_utc

    jd_ut1 = _as_builtin_float("event clock UT1 epoch", jd_ut1)
    bound = _ephemeris_delta_t(jd_ut1, reader)
    reader_identity = _verified_reader_identity_at(reader, jd_ut1)
    tidal_sources = tuple(
        dict.fromkeys(term.source_product for term in bound.raw.tidal_terms)
    )
    target_identity = None if bound.identity is None else bound.identity.summary_label
    if jd_ut1 >= _POST_1972_ATOMIC_UTC_START_JD:
        utc = MundaneEpoch(_ut1_to_utc(jd_ut1), MundaneTimescale.UTC)
        utc_status = MundaneUtcRealizationStatus.REALIZED_POST_1972_ATOMIC
        utc_detail = "civil UTC realized through Moira's post-1972 atomic/EOP clock model"
    else:
        utc = None
        utc_status = MundaneUtcRealizationStatus.NOT_REALIZED_HISTORICAL_UT1_PROXY
        utc_detail = (
            "no UTC label emitted: this historical epoch remains UT1 rather than "
            "being mislabeled through the pre-1972 proxy convention"
        )
    return MundaneEventClockReceipt(
        ut1=MundaneEpoch(jd_ut1, MundaneTimescale.UT1),
        tt=MundaneEpoch(
            jd_ut1 + bound.seconds / 86400.0,
            MundaneTimescale.TT,
        ),
        delta_t_seconds=bound.seconds,
        delta_t_source_product=bound.raw.source_product,
        delta_t_retarget_mode=bound.raw.retarget_mode,
        delta_t_correction_seconds=bound.correction_seconds,
        delta_t_tidal_source_products=tidal_sources,
        delta_t_target_reader_identity=target_identity,
        utc=utc,
        utc_realization_status=utc_status,
        utc_realization_detail=utc_detail,
        verified_reader_identity=reader_identity,
        _verification_token=_EVENT_CLOCK_TOKEN,
    )


def _root_search_receipt_from_truth(
    truth: object,
    *,
    reader: object,
    residual_at: Callable[[float], float],
    search_kind: str,
    solver_method_id: str,
    target_angle_deg: float,
) -> MundaneRootSearchReceipt:
    """Copy and independently bind one mutable transit search-truth vessel."""

    from .transits import CrossingSearchTruth

    if type(truth) is not CrossingSearchTruth:
        raise TypeError("root search truth must be a CrossingSearchTruth")
    values = (
        truth.search_start_jd_ut,
        truth.search_end_jd_ut,
        truth.step_days,
        truth.bracket_start_jd_ut,
        truth.bracket_end_jd_ut,
        truth.crossing_jd_ut,
        truth.solver_tolerance_days,
    )
    if any(type(value) is not float for value in values):
        raise TypeError("root search truth must retain exact built-in float fields")
    CrossingSearchTruth.__post_init__(truth)
    if not truth.search_start_jd_ut < truth.search_end_jd_ut:
        raise ValueError("root search interval must be non-empty")
    if not truth.search_start_jd_ut <= truth.crossing_jd_ut < truth.search_end_jd_ut:
        raise ValueError("root must lie in the half-open source search interval")
    identity = _verified_reader_identity_at(reader, truth.crossing_jd_ut)
    for epoch in (
        truth.search_start_jd_ut,
        truth.search_end_jd_ut,
        truth.bracket_start_jd_ut,
        truth.bracket_end_jd_ut,
    ):
        if _verified_reader_identity_at(reader, epoch) != identity:
            raise ValueError("root search crosses a reader-identity boundary")
    bracket_start_residual = residual_at(truth.bracket_start_jd_ut)
    bracket_end_residual = residual_at(truth.bracket_end_jd_ut)
    root_residual = residual_at(truth.crossing_jd_ut)
    return MundaneRootSearchReceipt(
        search_interval=MundaneSearchInterval(
            MundaneEpoch(truth.search_start_jd_ut, MundaneTimescale.UT1),
            MundaneEpoch(truth.search_end_jd_ut, MundaneTimescale.UT1),
        ),
        bracket_start=MundaneEpoch(
            truth.bracket_start_jd_ut,
            MundaneTimescale.UT1,
        ),
        bracket_end=MundaneEpoch(
            truth.bracket_end_jd_ut,
            MundaneTimescale.UT1,
        ),
        root_epoch=MundaneEpoch(truth.crossing_jd_ut, MundaneTimescale.UT1),
        step_days=truth.step_days,
        solver_tolerance_days=truth.solver_tolerance_days,
        target_angle_deg=target_angle_deg,
        root_residual_deg=root_residual,
        bracket_start_residual_deg=bracket_start_residual,
        bracket_end_residual_deg=bracket_end_residual,
        search_kind=search_kind,
        solver_method_id=solver_method_id,
        verified_reader_identity=identity,
        _verification_token=_ROOT_SEARCH_TOKEN,
    )


@dataclass(frozen=True, slots=True)
class MundaneEventProvenance:
    """Source and computation identity for a supplied event receipt."""

    mode: MundaneProvenanceMode
    source_id: str
    method_id: str
    provenance_family_id: str
    longitude_product_id: str
    reference_frame: str
    correction_regime: str
    solver_semantics: str
    source_refs: tuple[str, ...]
    verified_reader_identity: _VerifiedReaderIdentity | None = None
    caller_asserted_artifact_id: str | None = None
    caller_asserted_artifact_sha256: str | None = None
    _engine_provenance_token: InitVar[object | None] = None

    def __post_init__(self, _engine_provenance_token: object | None) -> None:
        if type(self.mode) is not MundaneProvenanceMode:
            raise TypeError("MundaneEventProvenance mode must be a MundaneProvenanceMode")
        for name, value in (
            ("source_id", self.source_id),
            ("method_id", self.method_id),
            ("provenance_family_id", self.provenance_family_id),
            ("longitude_product_id", self.longitude_product_id),
            ("reference_frame", self.reference_frame),
            ("correction_regime", self.correction_regime),
            ("solver_semantics", self.solver_semantics),
        ):
            _trimmed(f"MundaneEventProvenance {name}", value)
        _require_builtin_tuple(
            "MundaneEventProvenance source_refs",
            self.source_refs,
        )
        if (
            not self.source_refs
            or len(self.source_refs) != len(set(self.source_refs))
            or any(
                type(item) is not str or not item or item != item.strip()
                for item in self.source_refs
            )
        ):
            raise ValueError(
                "MundaneEventProvenance source_refs must contain unique "
                "non-empty trimmed built-in strings"
            )
        if (
            self.verified_reader_identity is not None
            and type(self.verified_reader_identity) is not _VerifiedReaderIdentity
        ):
            raise TypeError("verified_reader_identity must be engine-produced")
        if self.mode is MundaneProvenanceMode.MOIRA_EPHEMERIS:
            if self.verified_reader_identity is None:
                raise ValueError(
                    "Moira ephemeris provenance requires a content-derived "
                    "reader identity"
                )
            if _engine_provenance_token is not _MOIRA_PROVENANCE_TOKEN:
                raise ValueError("Moira ephemeris provenance must be engine-produced")
        elif self.verified_reader_identity is not None:
            raise ValueError(
                "Only Moira ephemeris provenance may carry verified reader identity"
            )
        if (self.caller_asserted_artifact_id is None) != (
            self.caller_asserted_artifact_sha256 is None
        ):
            raise ValueError(
                "caller-asserted artifact id and SHA-256 must be supplied together"
            )
        if self.caller_asserted_artifact_id is not None:
            _trimmed(
                "MundaneEventProvenance caller_asserted_artifact_id",
                self.caller_asserted_artifact_id,
            )
            if (
                type(self.caller_asserted_artifact_sha256) is not str
                or len(self.caller_asserted_artifact_sha256) != 64
                or any(
                    character not in "0123456789abcdefABCDEF"
                    for character in self.caller_asserted_artifact_sha256
                )
            ):
                raise ValueError(
                    "caller_asserted_artifact_sha256 must be a 64-character "
                    "hexadecimal digest"
                )
        if (
            self.mode is MundaneProvenanceMode.MOIRA_EPHEMERIS
            and self.caller_asserted_artifact_id is not None
        ):
            raise ValueError(
                "Caller-asserted artifact identity cannot masquerade as "
                "engine-verified reader identity"
            )


def _revalidate_verified_reader_identity(identity: _VerifiedReaderIdentity) -> None:
    _VerifiedReaderIdentity.__post_init__(
        identity,
        _VERIFIED_READER_IDENTITY_TOKEN,
    )


def _revalidate_event_provenance(provenance: MundaneEventProvenance) -> None:
    MundaneEventProvenance.__post_init__(
        provenance,
        (
            _MOIRA_PROVENANCE_TOKEN
            if provenance.mode is MundaneProvenanceMode.MOIRA_EPHEMERIS
            else None
        ),
    )
    if provenance.verified_reader_identity is not None:
        _revalidate_verified_reader_identity(provenance.verified_reader_identity)


def _revalidate_event_clock(clock: MundaneEventClockReceipt) -> None:
    MundaneEventClockReceipt.__post_init__(clock, _EVENT_CLOCK_TOKEN)
    MundaneEpoch.__post_init__(clock.ut1)
    MundaneEpoch.__post_init__(clock.tt)
    if clock.utc is not None:
        MundaneEpoch.__post_init__(clock.utc)
    _revalidate_verified_reader_identity(clock.verified_reader_identity)


def _revalidate_root_search(search: MundaneRootSearchReceipt) -> None:
    MundaneRootSearchReceipt.__post_init__(search, _ROOT_SEARCH_TOKEN)
    MundaneSearchInterval.__post_init__(search.search_interval)
    MundaneEpoch.__post_init__(search.search_interval.start)
    MundaneEpoch.__post_init__(search.search_interval.end)
    MundaneEpoch.__post_init__(search.bracket_start)
    MundaneEpoch.__post_init__(search.bracket_end)
    MundaneEpoch.__post_init__(search.root_epoch)
    _revalidate_verified_reader_identity(search.verified_reader_identity)


def _provenance_contract_key(
    provenance: MundaneEventProvenance,
) -> tuple[object, ...]:
    """Return the fields that make two event computations safely composable."""

    return (
        provenance.mode,
        provenance.source_id,
        provenance.method_id,
        provenance.provenance_family_id,
        provenance.longitude_product_id,
        provenance.reference_frame,
        provenance.correction_regime,
        provenance.solver_semantics,
        provenance.source_refs,
        provenance.verified_reader_identity,
        provenance.caller_asserted_artifact_id,
        provenance.caller_asserted_artifact_sha256,
    )


def _provenance_family_key(
    provenance: MundaneEventProvenance,
) -> tuple[object, ...]:
    """Return the identity fields that bind separately defined event stages."""

    return (
        provenance.mode,
        provenance.provenance_family_id,
        provenance.verified_reader_identity,
        provenance.caller_asserted_artifact_id,
        provenance.caller_asserted_artifact_sha256,
    )


def _cross_stage_provenance_key(
    provenance: MundaneEventProvenance,
) -> tuple[object, ...]:
    """Identity shared by different solvers on one astronomical surface."""

    return (
        provenance.mode,
        provenance.provenance_family_id,
        provenance.reference_frame,
        provenance.correction_regime,
        provenance.verified_reader_identity,
        provenance.caller_asserted_artifact_id,
        provenance.caller_asserted_artifact_sha256,
    )


@dataclass(frozen=True, slots=True)
class MundaneNotEvaluable:
    """Typed evidence explaining why one component was not fabricated."""

    component: MundaneProfileComponent
    reason: MundaneNotEvaluableReason
    missing_inputs: tuple[str, ...]
    detail: str

    def __post_init__(self) -> None:
        if type(self.component) is not MundaneProfileComponent:
            raise TypeError("MundaneNotEvaluable component must be typed")
        if type(self.reason) is not MundaneNotEvaluableReason:
            raise TypeError("MundaneNotEvaluable reason must be typed")
        _require_builtin_tuple(
            "MundaneNotEvaluable missing_inputs",
            self.missing_inputs,
        )
        if (
            len(self.missing_inputs) != len(set(self.missing_inputs))
            or any(
                type(item) is not str or not item or item != item.strip()
                for item in self.missing_inputs
            )
        ):
            raise ValueError("missing_inputs must contain unique non-empty trimmed strings")
        _trimmed("MundaneNotEvaluable detail", self.detail)


@dataclass(frozen=True, slots=True)
class CardinalIngressReceipt:
    """One increasing cardinal root of apparent tropical solar longitude."""

    ingress: CardinalIngress
    epoch: MundaneEpoch
    sun_longitude_deg: float
    root_residual_deg: float
    solver_tolerance_days: float
    angular_root_tolerance: MundaneAngularRootToleranceReceipt
    provenance: MundaneEventProvenance
    clock: MundaneEventClockReceipt | None = None
    search_truth: MundaneRootSearchReceipt | None = None
    event_type: MundaneEventType = MundaneEventType.CARDINAL_INGRESS
    longitude_definition: MundaneLongitudeDefinition = (
        MundaneLongitudeDefinition.SUN_OBSERVER_CENTERED_GEOCENTRIC_APPARENT_IAU2006_P03_IAU2000A_TRUE_ECLIPTIC_EQUINOX_OF_DATE
    )
    root_direction: str = "increasing"

    def __post_init__(self) -> None:
        if type(self.ingress) is not CardinalIngress:
            raise TypeError("CardinalIngressReceipt ingress must be a CardinalIngress")
        if type(self.epoch) is not MundaneEpoch:
            raise TypeError("CardinalIngressReceipt epoch must be a MundaneEpoch")
        MundaneEpoch.__post_init__(self.epoch)
        object.__setattr__(
            self,
            "sun_longitude_deg",
            _longitude(
                "CardinalIngressReceipt sun_longitude_deg",
                self.sun_longitude_deg,
            ),
        )
        object.__setattr__(
            self,
            "root_residual_deg",
            _as_builtin_float(
                "CardinalIngressReceipt root residual",
                self.root_residual_deg,
            ),
        )
        object.__setattr__(
            self,
            "solver_tolerance_days",
            _as_builtin_float(
                "CardinalIngressReceipt solver tolerance",
                self.solver_tolerance_days,
            ),
        )
        expected = _signed_angle_delta(
            self.sun_longitude_deg, self.ingress.target_longitude_deg
        )
        if not math.isclose(
            expected,
            self.root_residual_deg,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("CardinalIngressReceipt root residual must derive from longitude")
        if type(self.angular_root_tolerance) is not MundaneAngularRootToleranceReceipt:
            raise TypeError("Cardinal ingress angular root tolerance must be typed")
        MundaneAngularRootToleranceReceipt.__post_init__(self.angular_root_tolerance)
        if (
            abs(self.root_residual_deg)
            > self.angular_root_tolerance.maximum_abs_residual_deg
        ):
            raise ValueError(
                "Cardinal ingress residual exceeds its admitted angular root tolerance"
            )
        if self.solver_tolerance_days <= 0.0:
            raise ValueError("CardinalIngressReceipt solver tolerance must be positive")
        if type(self.provenance) is not MundaneEventProvenance:
            raise TypeError("CardinalIngressReceipt provenance must be typed")
        _revalidate_event_provenance(self.provenance)
        if (
            self.provenance.longitude_product_id
            != _MOIRA_SOLAR_APPARENT_LONGITUDE_PRODUCT
            or self.provenance.reference_frame
            != _MOIRA_TRUE_OF_DATE_REFERENCE_FRAME
            or self.provenance.correction_regime
            != _SUN_MOON_CORRECTION_REGIME
        ):
            raise ValueError(
                "Cardinal ingress provenance must identify Moira's observer-centered "
                "apparent solar longitude in the IAU 2006 P03 / IAU 2000A "
                "true ecliptic and equinox of date"
            )
        if self.clock is not None and type(self.clock) is not MundaneEventClockReceipt:
            raise TypeError("Cardinal ingress clock must be typed")
        if self.search_truth is not None and type(self.search_truth) is not MundaneRootSearchReceipt:
            raise TypeError("Cardinal ingress search truth must be typed")
        if self.clock is not None:
            _revalidate_event_clock(self.clock)
        if self.search_truth is not None:
            _revalidate_root_search(self.search_truth)
        if self.provenance.mode is MundaneProvenanceMode.MOIRA_EPHEMERIS:
            if self.clock is None or self.search_truth is None:
                raise ValueError("Moira cardinal ingress requires clock and search truth")
            if self.clock.ut1 != self.epoch or self.search_truth.root_epoch != self.epoch:
                raise ValueError("Cardinal ingress clock/search must bind the exact root epoch")
            if (
                self.clock.verified_reader_identity
                != self.provenance.verified_reader_identity
                or self.search_truth.verified_reader_identity
                != self.provenance.verified_reader_identity
            ):
                raise ValueError("Cardinal ingress reader identities must match")
            if self.search_truth.solver_tolerance_days != self.solver_tolerance_days:
                raise ValueError("Cardinal ingress must preserve its search tolerance")
            if (
                self.search_truth.target_angle_deg
                != self.ingress.target_longitude_deg
                or not math.isclose(
                    self.search_truth.root_residual_deg,
                    self.root_residual_deg,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            ):
                raise ValueError("Cardinal ingress search truth must bind its exact target")
            if self.search_truth.search_kind != "direct_solar_cardinal_ingress":
                raise ValueError("Cardinal ingress search kind is fixed")
        if self.event_type is not MundaneEventType.CARDINAL_INGRESS:
            raise ValueError("CardinalIngressReceipt event_type is fixed")
        if (
            self.longitude_definition
            is not MundaneLongitudeDefinition.SUN_OBSERVER_CENTERED_GEOCENTRIC_APPARENT_IAU2006_P03_IAU2000A_TRUE_ECLIPTIC_EQUINOX_OF_DATE
        ):
            raise ValueError(
                "Cardinal ingress requires Moira's IAU 2006 P03 / IAU 2000A "
                "true-ecliptic-and-equinox-of-date solar longitude"
            )
        _trimmed("CardinalIngressReceipt root_direction", self.root_direction)
        if self.root_direction != "increasing":
            raise ValueError("Cardinal ingress v1 requires an increasing root")

    @property
    def event_epoch(self) -> MundaneEpoch:
        return self.epoch


@dataclass(frozen=True, slots=True)
class PrimarySyzygyReceipt:
    """One exact new/full Moon receipt, without selection semantics."""

    phase: PrimarySyzygyPhase
    epoch: MundaneEpoch
    sun_longitude_deg: float
    moon_longitude_deg: float
    root_residual_deg: float
    solver_tolerance_days: float
    angular_root_tolerance: MundaneAngularRootToleranceReceipt
    provenance: MundaneEventProvenance
    clock: MundaneEventClockReceipt | None = None
    search_truth: MundaneRootSearchReceipt | None = None
    event_type: MundaneEventType = MundaneEventType.PRIMARY_SYZYGY
    longitude_definition: MundaneLongitudeDefinition = (
        MundaneLongitudeDefinition.SUN_MOON_OBSERVER_CENTERED_GEOCENTRIC_APPARENT_IAU2006_P03_IAU2000A_TRUE_ECLIPTIC_LONGITUDE_DIFFERENCE
    )

    def __post_init__(self) -> None:
        if type(self.phase) is not PrimarySyzygyPhase:
            raise TypeError("PrimarySyzygyReceipt phase must be typed")
        if type(self.epoch) is not MundaneEpoch:
            raise TypeError("PrimarySyzygyReceipt epoch must be typed")
        MundaneEpoch.__post_init__(self.epoch)
        object.__setattr__(
            self,
            "sun_longitude_deg",
            _longitude(
                "PrimarySyzygyReceipt sun_longitude_deg",
                self.sun_longitude_deg,
            ),
        )
        object.__setattr__(
            self,
            "moon_longitude_deg",
            _longitude(
                "PrimarySyzygyReceipt moon_longitude_deg",
                self.moon_longitude_deg,
            ),
        )
        object.__setattr__(
            self,
            "root_residual_deg",
            _as_builtin_float(
                "PrimarySyzygyReceipt root residual",
                self.root_residual_deg,
            ),
        )
        object.__setattr__(
            self,
            "solver_tolerance_days",
            _as_builtin_float(
                "PrimarySyzygyReceipt solver tolerance",
                self.solver_tolerance_days,
            ),
        )
        target = 0.0 if self.phase is PrimarySyzygyPhase.NEW_MOON else 180.0
        expected = _signed_angle_delta(
            self.moon_longitude_deg - self.sun_longitude_deg, target
        )
        if not math.isclose(
            expected,
            self.root_residual_deg,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("PrimarySyzygyReceipt root residual must derive from phase longitudes")
        if type(self.angular_root_tolerance) is not MundaneAngularRootToleranceReceipt:
            raise TypeError("Primary syzygy angular root tolerance must be typed")
        MundaneAngularRootToleranceReceipt.__post_init__(self.angular_root_tolerance)
        if (
            abs(self.root_residual_deg)
            > self.angular_root_tolerance.maximum_abs_residual_deg
        ):
            raise ValueError(
                "Primary syzygy residual exceeds its admitted angular root tolerance"
            )
        if self.solver_tolerance_days <= 0.0:
            raise ValueError("PrimarySyzygyReceipt solver tolerance must be positive")
        if type(self.provenance) is not MundaneEventProvenance:
            raise TypeError("PrimarySyzygyReceipt provenance must be typed")
        _revalidate_event_provenance(self.provenance)
        if (
            self.provenance.longitude_product_id
            != _PRIMARY_SYZYGY_LONGITUDE_PRODUCT
            or self.provenance.reference_frame
            != _MOIRA_TRUE_OF_DATE_REFERENCE_FRAME
            or self.provenance.correction_regime
            != _SUN_MOON_CORRECTION_REGIME
        ):
            raise ValueError(
                "Primary syzygy provenance must identify Moira's observer-centered "
                "apparent Sun-Moon longitude difference in the IAU 2006 P03 / "
                "IAU 2000A true ecliptic and equinox of date"
            )
        if self.clock is not None and type(self.clock) is not MundaneEventClockReceipt:
            raise TypeError("Primary syzygy clock must be typed")
        if self.search_truth is not None and type(self.search_truth) is not MundaneRootSearchReceipt:
            raise TypeError("Primary syzygy search truth must be typed")
        if self.clock is not None:
            _revalidate_event_clock(self.clock)
        if self.search_truth is not None:
            _revalidate_root_search(self.search_truth)
        if self.provenance.mode is MundaneProvenanceMode.MOIRA_EPHEMERIS:
            if self.clock is None or self.search_truth is None:
                raise ValueError("Moira primary syzygy requires clock and search truth")
            if self.clock.ut1 != self.epoch or self.search_truth.root_epoch != self.epoch:
                raise ValueError("Primary syzygy clock/search must bind the exact root epoch")
            if (
                self.clock.verified_reader_identity
                != self.provenance.verified_reader_identity
                or self.search_truth.verified_reader_identity
                != self.provenance.verified_reader_identity
            ):
                raise ValueError("Primary syzygy reader identities must match")
            if self.search_truth.solver_tolerance_days != self.solver_tolerance_days:
                raise ValueError("Primary syzygy must preserve its search tolerance")
            target = 0.0 if self.phase is PrimarySyzygyPhase.NEW_MOON else 180.0
            if (
                self.search_truth.target_angle_deg != target
                or not math.isclose(
                    self.search_truth.root_residual_deg,
                    self.root_residual_deg,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            ):
                raise ValueError("Primary syzygy search truth must bind its exact target")
            expected_kind = (
                "preceding_new_moon"
                if self.phase is PrimarySyzygyPhase.NEW_MOON
                else "preceding_full_moon"
            )
            if self.search_truth.search_kind != expected_kind:
                raise ValueError("Primary syzygy search kind must match its phase")
        if self.event_type is not MundaneEventType.PRIMARY_SYZYGY:
            raise ValueError("PrimarySyzygyReceipt event_type is fixed")
        if (
            self.longitude_definition
            is not MundaneLongitudeDefinition.SUN_MOON_OBSERVER_CENTERED_GEOCENTRIC_APPARENT_IAU2006_P03_IAU2000A_TRUE_ECLIPTIC_LONGITUDE_DIFFERENCE
        ):
            raise ValueError("Primary syzygy requires the admitted Sun-Moon longitude product")

    @property
    def event_epoch(self) -> MundaneEpoch:
        return self.epoch


@dataclass(frozen=True, slots=True)
class EclipseNamedEpochReceipt:
    """One eclipse-bound named epoch with its own computational definition."""

    eclipse_id: str
    eclipse_kind: EclipseKind
    epoch_kind: EclipseAnchorEpoch
    epoch: MundaneEpoch
    provenance: MundaneEventProvenance

    def __post_init__(self) -> None:
        _trimmed("EclipseNamedEpochReceipt eclipse_id", self.eclipse_id)
        if type(self.eclipse_kind) is not EclipseKind:
            raise TypeError("EclipseNamedEpochReceipt eclipse_kind must be typed")
        if type(self.epoch_kind) is not EclipseAnchorEpoch:
            raise TypeError("EclipseNamedEpochReceipt epoch_kind must be typed")
        if type(self.epoch) is not MundaneEpoch:
            raise TypeError("EclipseNamedEpochReceipt epoch must be typed")
        MundaneEpoch.__post_init__(self.epoch)
        if type(self.provenance) is not MundaneEventProvenance:
            raise TypeError("EclipseNamedEpochReceipt provenance must be typed")
        _revalidate_event_provenance(self.provenance)
        if (
            self.eclipse_kind is EclipseKind.SOLAR
            and self.epoch_kind is EclipseAnchorEpoch.EQUATORIAL_OPPOSITION
        ):
            raise ValueError("A solar eclipse cannot use an equatorial-opposition epoch")
        if (
            self.eclipse_kind is EclipseKind.LUNAR
            and self.epoch_kind is EclipseAnchorEpoch.EQUATORIAL_CONJUNCTION
        ):
            raise ValueError("A lunar eclipse cannot use an equatorial-conjunction epoch")


_SOLAR_CONTACT_ORDER = {
    EclipseContactKind.C1: 0,
    EclipseContactKind.C2: 1,
    EclipseContactKind.C3: 2,
    EclipseContactKind.C4: 3,
}
_LUNAR_CONTACT_ORDER = {
    EclipseContactKind.P1: 0,
    EclipseContactKind.U1: 1,
    EclipseContactKind.U2: 2,
    EclipseContactKind.U3: 3,
    EclipseContactKind.U4: 4,
    EclipseContactKind.P4: 5,
}
_CONTACTS_BEFORE_GREATEST = frozenset(
    {
        EclipseContactKind.C1,
        EclipseContactKind.C2,
        EclipseContactKind.P1,
        EclipseContactKind.U1,
        EclipseContactKind.U2,
    }
)
_CONTACTS_AFTER_GREATEST = frozenset(
    {
        EclipseContactKind.C3,
        EclipseContactKind.C4,
        EclipseContactKind.U3,
        EclipseContactKind.U4,
        EclipseContactKind.P4,
    }
)


@dataclass(frozen=True, slots=True)
class EclipseContactEpochReceipt:
    """One event-bound global eclipse contact epoch and provenance receipt."""

    eclipse_id: str
    eclipse_kind: EclipseKind
    contact: EclipseContactKind
    epoch: MundaneEpoch
    provenance: MundaneEventProvenance

    def __post_init__(self) -> None:
        _trimmed("EclipseContactEpochReceipt eclipse_id", self.eclipse_id)
        if type(self.eclipse_kind) is not EclipseKind:
            raise TypeError("Eclipse contact kind must be an EclipseKind")
        if type(self.contact) is not EclipseContactKind:
            raise TypeError("Eclipse contact must be an EclipseContactKind")
        if type(self.epoch) is not MundaneEpoch:
            raise TypeError("Eclipse contact epoch must be a MundaneEpoch")
        MundaneEpoch.__post_init__(self.epoch)
        if type(self.provenance) is not MundaneEventProvenance:
            raise TypeError("Eclipse contact provenance must be typed")
        _revalidate_event_provenance(self.provenance)
        contact_order = (
            _SOLAR_CONTACT_ORDER
            if self.eclipse_kind is EclipseKind.SOLAR
            else _LUNAR_CONTACT_ORDER
        )
        if self.contact not in contact_order:
            raise ValueError("Eclipse contact family does not match the eclipse kind")


@dataclass(frozen=True, slots=True)
class EclipseEventReceipt:
    """Global eclipse identity with typed, non-interchangeable epoch receipts."""

    eclipse_id: str
    eclipse_kind: EclipseKind
    anchor_epoch_kind: EclipseAnchorEpoch
    provenance: MundaneEventProvenance
    named_epochs: tuple[EclipseNamedEpochReceipt, ...]
    global_contacts: tuple[EclipseContactEpochReceipt, ...] = ()
    clock: MundaneEventClockReceipt | None = None
    event_type: MundaneEventType = MundaneEventType.ECLIPSE

    def __post_init__(self) -> None:
        _trimmed("EclipseEventReceipt eclipse_id", self.eclipse_id)
        if type(self.eclipse_kind) is not EclipseKind:
            raise TypeError("EclipseEventReceipt eclipse_kind must be typed")
        if type(self.anchor_epoch_kind) is not EclipseAnchorEpoch:
            raise TypeError("EclipseEventReceipt anchor_epoch_kind must be typed")
        if type(self.provenance) is not MundaneEventProvenance:
            raise TypeError("EclipseEventReceipt provenance must be typed")
        _revalidate_event_provenance(self.provenance)
        _require_builtin_tuple("EclipseEventReceipt named_epochs", self.named_epochs)
        if not self.named_epochs or any(
            type(item) is not EclipseNamedEpochReceipt for item in self.named_epochs
        ):
            raise TypeError("named_epochs must contain typed eclipse epoch receipts")
        for item in self.named_epochs:
            EclipseNamedEpochReceipt.__post_init__(item)
        if any(
            item.eclipse_id != self.eclipse_id or item.eclipse_kind is not self.eclipse_kind
            for item in self.named_epochs
        ):
            raise ValueError("Every named eclipse epoch must belong to this eclipse")
        epoch_kinds = tuple(item.epoch_kind for item in self.named_epochs)
        if len(epoch_kinds) != len(set(epoch_kinds)):
            raise ValueError("Named eclipse epoch kinds must be unique")
        if self.anchor_epoch_kind not in epoch_kinds:
            raise ValueError("The selected eclipse anchor epoch must be supplied")
        anchor_epoch = next(
            item.epoch
            for item in self.named_epochs
            if item.epoch_kind is self.anchor_epoch_kind
        )
        if any(
            _provenance_family_key(item.provenance)
            != _provenance_family_key(self.provenance)
            for item in self.named_epochs
        ):
            raise ValueError("Named eclipse epochs must share the event provenance family")
        _require_builtin_tuple(
            "EclipseEventReceipt global_contacts",
            self.global_contacts,
        )
        if any(
            type(item) is not EclipseContactEpochReceipt
            for item in self.global_contacts
        ):
            raise TypeError("global_contacts must contain EclipseContactEpochReceipt values")
        for item in self.global_contacts:
            EclipseContactEpochReceipt.__post_init__(item)
        if any(
            item.eclipse_id != self.eclipse_id or item.eclipse_kind is not self.eclipse_kind
            for item in self.global_contacts
        ):
            raise ValueError("Every eclipse contact must belong to this eclipse")
        if any(
            _provenance_family_key(item.provenance)
            != _provenance_family_key(self.provenance)
            for item in self.global_contacts
        ):
            raise ValueError("Eclipse contacts must share the event provenance family")
        contact_names = tuple(item.contact for item in self.global_contacts)
        if len(contact_names) != len(set(contact_names)):
            raise ValueError("global eclipse contacts must have unique names")
        contact_order = (
            _SOLAR_CONTACT_ORDER
            if self.eclipse_kind is EclipseKind.SOLAR
            else _LUNAR_CONTACT_ORDER
        )
        if any(item.contact not in contact_order for item in self.global_contacts):
            raise ValueError("Eclipse contact family does not match the eclipse kind")
        ordered_contacts = tuple(
            sorted(self.global_contacts, key=lambda item: contact_order[item.contact])
        )
        if ordered_contacts != self.global_contacts:
            raise ValueError("Eclipse contacts must be supplied in canonical order")
        all_epochs = tuple(item.epoch for item in self.named_epochs) + tuple(
            item.epoch for item in self.global_contacts
        )
        if len({item.timescale for item in all_epochs}) != 1:
            raise ValueError("Mundane v1 eclipse epochs require one shared timescale")
        if max(item.jd for item in all_epochs) - min(item.jd for item in all_epochs) > _MAX_ECLIPSE_EVENT_SPAN_DAYS:
            raise ValueError("Named eclipse epochs must belong to one bounded event window")
        contact_jds = tuple(item.epoch.jd for item in self.global_contacts)
        if any(later <= earlier for earlier, later in zip(contact_jds, contact_jds[1:])):
            raise ValueError("Eclipse contact epochs must be strictly increasing")
        greatest = next(
            (
                item.epoch
                for item in self.named_epochs
                if item.epoch_kind is EclipseAnchorEpoch.GREATEST_ECLIPSE
            ),
            None,
        )
        if greatest is not None:
            if any(
                item.contact in _CONTACTS_BEFORE_GREATEST
                and item.epoch.jd >= greatest.jd
                for item in self.global_contacts
            ):
                raise ValueError(
                    "Ingress-side eclipse contacts must precede greatest eclipse"
                )
            if any(
                item.contact in _CONTACTS_AFTER_GREATEST
                and item.epoch.jd <= greatest.jd
                for item in self.global_contacts
            ):
                raise ValueError(
                    "Egress-side eclipse contacts must follow greatest eclipse"
                )
        if self.clock is not None and type(self.clock) is not MundaneEventClockReceipt:
            raise TypeError("Eclipse event clock must be typed")
        if self.clock is not None:
            _revalidate_event_clock(self.clock)
        if self.provenance.mode is MundaneProvenanceMode.MOIRA_EPHEMERIS:
            if self.clock is None:
                raise ValueError("Moira eclipse event requires an event clock")
            if self.clock.ut1 != anchor_epoch:
                raise ValueError("Eclipse event clock must bind the selected anchor epoch")
            if self.clock.verified_reader_identity != (
                self.provenance.verified_reader_identity
            ):
                raise ValueError("Eclipse event clock must share the event reader identity")
        elif self.clock is not None:
            raise ValueError("Only Moira eclipse provenance may carry an engine event clock")
        if self.event_type is not MundaneEventType.ECLIPSE:
            raise ValueError("EclipseEventReceipt event_type is fixed")

    def named_epoch_receipt(
        self, epoch_kind: EclipseAnchorEpoch
    ) -> EclipseNamedEpochReceipt | None:
        """Return one explicitly named epoch receipt without substituting another."""

        return next(
            (item for item in self.named_epochs if item.epoch_kind is epoch_kind),
            None,
        )

    @property
    def event_epoch(self) -> MundaneEpoch:
        receipt = self.named_epoch_receipt(self.anchor_epoch_kind)
        if receipt is None:  # Constructor invariants make this unreachable.
            raise RuntimeError("Eclipse anchor epoch invariant was not preserved")
        return receipt.epoch

    @property
    def ecliptic_syzygy_epoch(self) -> MundaneEpoch | None:
        receipt = self.named_epoch_receipt(EclipseAnchorEpoch.ECLIPTIC_SYZYGY)
        return None if receipt is None else receipt.epoch

    @property
    def equatorial_conjunction_epoch(self) -> MundaneEpoch | None:
        receipt = self.named_epoch_receipt(EclipseAnchorEpoch.EQUATORIAL_CONJUNCTION)
        return None if receipt is None else receipt.epoch

    @property
    def equatorial_opposition_epoch(self) -> MundaneEpoch | None:
        receipt = self.named_epoch_receipt(EclipseAnchorEpoch.EQUATORIAL_OPPOSITION)
        return None if receipt is None else receipt.epoch

    @property
    def greatest_eclipse_epoch(self) -> MundaneEpoch | None:
        receipt = self.named_epoch_receipt(EclipseAnchorEpoch.GREATEST_ECLIPSE)
        return None if receipt is None else receipt.epoch


@dataclass(frozen=True, slots=True)
class JupiterSaturnConjunctionReceipt:
    """One exact Jupiter-Saturn ecliptic-longitude root."""

    event_id: str
    epoch: MundaneEpoch
    jupiter_longitude_deg: float
    saturn_longitude_deg: float
    root_residual_deg: float
    jupiter_motion: MundaneMotionState
    saturn_motion: MundaneMotionState
    solver_tolerance_days: float
    angular_root_tolerance: MundaneAngularRootToleranceReceipt
    provenance: MundaneEventProvenance
    clock: MundaneEventClockReceipt | None = None
    definition: JupiterSaturnConjunctionDefinition = (
        JupiterSaturnConjunctionDefinition.ECLIPTIC_LONGITUDE
    )
    event_type: MundaneEventType = (
        MundaneEventType.JUPITER_SATURN_ECLIPTIC_LONGITUDE_CONJUNCTION
    )
    longitude_definition: MundaneLongitudeDefinition = (
        MundaneLongitudeDefinition.JUPITER_SATURN_GEOCENTRIC_APPARENT_ECLIPTIC_DIFFERENCE
    )

    def __post_init__(self) -> None:
        _trimmed("JupiterSaturnConjunctionReceipt event_id", self.event_id)
        if type(self.epoch) is not MundaneEpoch:
            raise TypeError("JupiterSaturnConjunctionReceipt epoch must be typed")
        MundaneEpoch.__post_init__(self.epoch)
        object.__setattr__(
            self,
            "jupiter_longitude_deg",
            _longitude("Jupiter longitude", self.jupiter_longitude_deg),
        )
        object.__setattr__(
            self,
            "saturn_longitude_deg",
            _longitude("Saturn longitude", self.saturn_longitude_deg),
        )
        object.__setattr__(
            self,
            "root_residual_deg",
            _as_builtin_float(
                "Jupiter-Saturn root residual",
                self.root_residual_deg,
            ),
        )
        object.__setattr__(
            self,
            "solver_tolerance_days",
            _as_builtin_float(
                "Jupiter-Saturn solver tolerance",
                self.solver_tolerance_days,
            ),
        )
        expected = _signed_angle_delta(
            self.jupiter_longitude_deg - self.saturn_longitude_deg, 0.0
        )
        if not math.isclose(
            expected,
            self.root_residual_deg,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("Jupiter-Saturn root residual must derive from longitudes")
        if type(self.angular_root_tolerance) is not MundaneAngularRootToleranceReceipt:
            raise TypeError("Jupiter-Saturn angular root tolerance must be typed")
        MundaneAngularRootToleranceReceipt.__post_init__(self.angular_root_tolerance)
        if (
            abs(self.root_residual_deg)
            > self.angular_root_tolerance.maximum_abs_residual_deg
        ):
            raise ValueError(
                "Jupiter-Saturn residual exceeds its admitted angular root tolerance"
            )
        if (
            type(self.jupiter_motion) is not MundaneMotionState
            or type(self.saturn_motion) is not MundaneMotionState
        ):
            raise TypeError("Jupiter-Saturn motion states must be typed")
        if self.solver_tolerance_days <= 0.0:
            raise ValueError("Jupiter-Saturn solver tolerance must be positive")
        if type(self.provenance) is not MundaneEventProvenance:
            raise TypeError("Jupiter-Saturn provenance must be typed")
        _revalidate_event_provenance(self.provenance)
        if (
            self.provenance.longitude_product_id
            != _JUPITER_SATURN_LONGITUDE_PRODUCT
            or self.provenance.reference_frame != _JUPITER_SATURN_REFERENCE_FRAME
            or self.provenance.correction_regime
            != _JUPITER_SATURN_CORRECTION_REGIME
        ):
            raise ValueError(
                "Jupiter-Saturn provenance must identify the admitted geocentric "
                "apparent true-ecliptic-of-date longitude-difference product"
            )
        if self.clock is not None and type(self.clock) is not MundaneEventClockReceipt:
            raise TypeError("Jupiter-Saturn event clock must be typed")
        if self.clock is not None:
            _revalidate_event_clock(self.clock)
        if self.provenance.mode is MundaneProvenanceMode.MOIRA_EPHEMERIS:
            if self.clock is None:
                raise ValueError("Moira Jupiter-Saturn root requires an event clock")
            if self.clock.ut1 != self.epoch:
                raise ValueError("Jupiter-Saturn event clock must bind the root epoch")
            if self.clock.verified_reader_identity != (
                self.provenance.verified_reader_identity
            ):
                raise ValueError("Jupiter-Saturn event clock must share the reader identity")
        elif self.clock is not None:
            raise ValueError(
                "Only Moira Jupiter-Saturn provenance may carry an engine event clock"
            )
        if self.definition is not JupiterSaturnConjunctionDefinition.ECLIPTIC_LONGITUDE:
            raise ValueError(
                "Mundane v1 admits only Jupiter-Saturn ecliptic-longitude conjunction roots"
            )
        if self.event_type is not MundaneEventType.JUPITER_SATURN_ECLIPTIC_LONGITUDE_CONJUNCTION:
            raise ValueError("JupiterSaturnConjunctionReceipt event_type is fixed")
        if (
            self.longitude_definition
            is not MundaneLongitudeDefinition.JUPITER_SATURN_GEOCENTRIC_APPARENT_ECLIPTIC_DIFFERENCE
        ):
            raise ValueError("Jupiter-Saturn receipt requires the admitted longitude product")

    @property
    def event_epoch(self) -> MundaneEpoch:
        return self.epoch


MundaneEventReceipt: TypeAlias = (
    CardinalIngressReceipt
    | PrimarySyzygyReceipt
    | EclipseEventReceipt
    | JupiterSaturnConjunctionReceipt
)
_EVENT_RECEIPT_TYPES = (
    CardinalIngressReceipt,
    PrimarySyzygyReceipt,
    EclipseEventReceipt,
    JupiterSaturnConjunctionReceipt,
)


def _revalidate_event_receipt(receipt: MundaneEventReceipt) -> None:
    """Re-run the exact concrete atomic receipt invariant after composition."""

    receipt_type = type(receipt)
    if receipt_type not in _EVENT_RECEIPT_TYPES:
        raise TypeError("event receipt must use an exact concrete Mundane type")
    receipt_type.__post_init__(receipt)


@dataclass(frozen=True, slots=True)
class CardinalIngressSelectionReceipt:
    """Source-named selection over a complete four-ingress input set."""

    policy: CardinalIngressSelectionPolicy
    search_interval: MundaneSearchInterval
    all_events: tuple[CardinalIngressReceipt, ...]
    selected_events: tuple[CardinalIngressReceipt, ...]
    source_reference: str
    ramesey_cadence: RameseyIngressCadenceReceipt | None = None

    def __post_init__(self) -> None:
        if type(self.policy) is not CardinalIngressSelectionPolicy:
            raise TypeError("Ingress selection policy must be typed")
        if type(self.search_interval) is not MundaneSearchInterval:
            raise TypeError("Ingress selection search interval must be typed")
        MundaneSearchInterval.__post_init__(self.search_interval)
        MundaneEpoch.__post_init__(self.search_interval.start)
        MundaneEpoch.__post_init__(self.search_interval.end)
        _require_builtin_tuple(
            "CardinalIngressSelectionReceipt all_events",
            self.all_events,
        )
        if any(type(item) is not CardinalIngressReceipt for item in self.all_events):
            raise TypeError("all_events must contain cardinal ingress receipts")
        for item in self.all_events:
            _revalidate_event_receipt(item)
        expected_order = tuple(CardinalIngress)
        if tuple(item.ingress for item in self.all_events) != expected_order:
            raise ValueError("all_events must contain the four cardinal ingresses in canonical order")
        _require_builtin_tuple(
            "CardinalIngressSelectionReceipt selected_events",
            self.selected_events,
        )
        if any(type(item) is not CardinalIngressReceipt for item in self.selected_events):
            raise TypeError("selected_events must contain cardinal ingress receipts")
        for item in self.selected_events:
            _revalidate_event_receipt(item)
        if not self.selected_events:
            raise ValueError("ingress selection must retain at least one selected event")
        if any(item not in self.all_events for item in self.selected_events):
            raise ValueError("selected ingress events must come from all_events")
        if any(
            item.epoch.timescale is not self.search_interval.timescale
            or not self.search_interval.contains(item.epoch)
            for item in self.all_events
        ):
            raise ValueError(
                "cardinal ingress events must lie in the half-open search interval"
            )
        if self.search_interval.end.jd - self.search_interval.start.jd > _MAX_CARDINAL_INGRESS_CYCLE_DAYS:
            raise ValueError("all-four cardinal ingress enumeration is limited to one cycle")
        event_jds = tuple(item.epoch.jd for item in self.all_events)
        if any(later <= earlier for earlier, later in zip(event_jds, event_jds[1:])):
            raise ValueError("cardinal ingress events must be strictly chronological")
        if len({_provenance_contract_key(item.provenance) for item in self.all_events}) != 1:
            raise ValueError("cardinal ingress events require homogeneous provenance")
        if len({item.solver_tolerance_days for item in self.all_events}) != 1:
            raise ValueError("cardinal ingress events require one solver tolerance")
        if len({item.angular_root_tolerance for item in self.all_events}) != 1:
            raise ValueError(
                "cardinal ingress events require one angular root tolerance"
            )
        _trimmed("CardinalIngressSelectionReceipt source_reference", self.source_reference)
        if self.policy is CardinalIngressSelectionPolicy.ALL_FOUR_CARDINAL_INGRESSES_V1:
            if self.selected_events != self.all_events or self.ramesey_cadence is not None:
                raise ValueError("all-four policy must select all events without cadence")
            if self.source_reference != (
                "neutral all-four-cardinal-ingresses v1 event enumeration"
            ):
                raise ValueError("all-four selection source reference is fixed")
        elif self.policy is CardinalIngressSelectionPolicy.RAMESEY_1653_ASCENDANT_MODALITY_V1:
            if type(self.ramesey_cadence) is not RameseyIngressCadenceReceipt:
                raise ValueError("Ramesey selection requires a cadence receipt")
            RameseyIngressCadenceReceipt.__post_init__(self.ramesey_cadence)
            if self.ramesey_cadence.aries_ingress != self.all_events[0]:
                raise ValueError("Ramesey cadence must bind the supplied Aries event")
            expected_selected = tuple(
                self.all_events[tuple(CardinalIngress).index(ingress)]
                for ingress in self.ramesey_cadence.selected_ingresses
            )
            if self.selected_events != expected_selected:
                raise ValueError("Ramesey selected events must derive from its cadence")
            if self.source_reference != self.ramesey_cadence.source_reference:
                raise ValueError("Ramesey selection must retain its cadence source")
        else:
            raise TypeError("unsupported cardinal ingress selection policy")


@dataclass(frozen=True, slots=True)
class CardinalIngressSelectionEvidence:
    """Evaluated neutral enumeration or typed deferral of chart-dependent policy."""

    status: MundaneEvaluationStatus
    selection: CardinalIngressSelectionReceipt | None
    issue: MundaneNotEvaluable | None

    def __post_init__(self) -> None:
        if self.status is MundaneEvaluationStatus.EVALUATED:
            if (
                type(self.selection) is not CardinalIngressSelectionReceipt
                or self.issue is not None
            ):
                raise ValueError("evaluated ingress selection requires only a receipt")
            CardinalIngressSelectionReceipt.__post_init__(self.selection)
        elif self.status is MundaneEvaluationStatus.NOT_EVALUABLE:
            if self.selection is not None or type(self.issue) is not MundaneNotEvaluable:
                raise ValueError("not-evaluable ingress selection requires only an issue")
            MundaneNotEvaluable.__post_init__(self.issue)
            if (
                self.issue.component
                is not MundaneProfileComponent.CARDINAL_INGRESS_SELECTION
            ):
                raise ValueError("ingress selection issue has the wrong component")
        else:
            raise TypeError("CardinalIngressSelectionEvidence status must be typed")


def select_cardinal_ingresses(
    events: tuple[CardinalIngressReceipt, ...],
    *,
    policy: CardinalIngressSelectionPolicy,
    search_interval: MundaneSearchInterval,
    ramesey_cadence: RameseyIngressCadenceReceipt | None = None,
) -> CardinalIngressSelectionEvidence:
    """Select supplied ingress receipts without solving or changing epochs."""

    if type(events) is not tuple or any(
        type(item) is not CardinalIngressReceipt for item in events
    ):
        raise TypeError("events must contain CardinalIngressReceipt values")
    for event in events:
        _revalidate_event_receipt(event)
    by_ingress = {item.ingress: item for item in events}
    if len(events) != 4 or len(by_ingress) != 4 or set(by_ingress) != set(CardinalIngress):
        raise ValueError("ingress selection requires exactly one receipt for each cardinal ingress")
    ordered = tuple(by_ingress[ingress] for ingress in CardinalIngress)
    if policy is CardinalIngressSelectionPolicy.ALL_FOUR_CARDINAL_INGRESSES_V1:
        return CardinalIngressSelectionEvidence(
            status=MundaneEvaluationStatus.EVALUATED,
            selection=CardinalIngressSelectionReceipt(
                policy=policy,
                search_interval=search_interval,
                all_events=ordered,
                selected_events=ordered,
                source_reference="neutral all-four-cardinal-ingresses v1 event enumeration",
            ),
            issue=None,
        )
    if policy is CardinalIngressSelectionPolicy.RAMESEY_1653_ASCENDANT_MODALITY_V1:
        if type(ramesey_cadence) is not RameseyIngressCadenceReceipt:
            return CardinalIngressSelectionEvidence(
                status=MundaneEvaluationStatus.NOT_EVALUABLE,
                selection=None,
                issue=MundaneNotEvaluable(
                    component=MundaneProfileComponent.CARDINAL_INGRESS_SELECTION,
                    reason=MundaneNotEvaluableReason.SOURCE_RECEIPT_INCOMPLETE,
                    missing_inputs=("evaluated_ramesey_ingress_cadence",),
                    detail="Ramesey selection requires evaluated Aries-chart cadence evidence.",
                ),
            )
        selected = tuple(
            by_ingress[ingress] for ingress in ramesey_cadence.selected_ingresses
        )
        return CardinalIngressSelectionEvidence(
            status=MundaneEvaluationStatus.EVALUATED,
            selection=CardinalIngressSelectionReceipt(
                policy=policy,
                search_interval=search_interval,
                all_events=ordered,
                selected_events=selected,
                source_reference=ramesey_cadence.source_reference,
                ramesey_cadence=ramesey_cadence,
            ),
            issue=None,
        )
    raise TypeError("policy must be a CardinalIngressSelectionPolicy")


@dataclass(frozen=True, slots=True)
class PrecedingSyzygySelectionReceipt:
    """Nearest exact new/full Moon strictly before one supplied anchor."""

    anchor_event: CardinalIngressReceipt
    candidates: tuple[PrimarySyzygyReceipt, ...]
    selected: PrimarySyzygyReceipt
    comparison_timescale: MundaneTimescale
    policy_id: str = "strictly_preceding_primary_syzygy_v1"

    def __post_init__(self) -> None:
        if type(self.anchor_event) is not CardinalIngressReceipt:
            raise TypeError("Preceding syzygy anchor event must be a cardinal ingress")
        _revalidate_event_receipt(self.anchor_event)
        if type(self.selected) is not PrimarySyzygyReceipt:
            raise TypeError("Preceding syzygy selected receipt must be typed")
        _revalidate_event_receipt(self.selected)
        _require_builtin_tuple(
            "PrecedingSyzygySelectionReceipt candidates",
            self.candidates,
        )
        if not self.candidates or any(
            type(item) is not PrimarySyzygyReceipt for item in self.candidates
        ):
            raise TypeError("Preceding syzygy candidates must be typed and non-empty")
        for item in self.candidates:
            _revalidate_event_receipt(item)
        if self.selected not in self.candidates:
            raise ValueError("selected syzygy must be retained in the candidate receipts")
        if self.comparison_timescale is not self.anchor_event.epoch.timescale:
            raise ValueError("comparison timescale must match the anchor epoch")
        if not self.selected.epoch.jd < self.anchor_event.epoch.jd:
            raise ValueError("selected syzygy must be strictly earlier than the anchor")
        if len(
            {_provenance_contract_key(item.provenance) for item in self.candidates}
        ) != 1:
            raise ValueError(
                "preceding syzygy candidates require homogeneous provenance"
            )
        if len({item.angular_root_tolerance for item in self.candidates}) != 1:
            raise ValueError(
                "preceding syzygy candidates require one angular root tolerance"
            )
        if len({item.solver_tolerance_days for item in self.candidates}) != 1:
            raise ValueError(
                "preceding syzygy candidates require one solver tolerance"
            )
        for candidate in self.candidates:
            if candidate.epoch.timescale is not self.comparison_timescale:
                raise ValueError("every syzygy candidate must use the comparison timescale")
            if _cross_stage_provenance_key(candidate.provenance) != (
                _cross_stage_provenance_key(self.anchor_event.provenance)
            ):
                raise ValueError(
                    "every syzygy candidate must share the anchor frame, correction, "
                    "provenance family, and reader identity"
                )
        _trimmed("PrecedingSyzygySelectionReceipt policy_id", self.policy_id)
        if self.policy_id != "strictly_preceding_primary_syzygy_v1":
            raise ValueError("Preceding syzygy policy_id is fixed")
        earlier = tuple(
            item for item in self.candidates if item.epoch.jd < self.anchor_event.epoch.jd
        )
        if not earlier or self.selected != max(earlier, key=lambda item: item.epoch.jd):
            raise ValueError("selected syzygy must be the nearest strictly earlier candidate")

    @property
    def anchor_epoch(self) -> MundaneEpoch:
        return self.anchor_event.epoch


@dataclass(frozen=True, slots=True)
class PrecedingSyzygyEvidence:
    """Evaluated selection or typed refusal for a preceding syzygy."""

    status: MundaneEvaluationStatus
    selection: PrecedingSyzygySelectionReceipt | None
    issue: MundaneNotEvaluable | None

    def __post_init__(self) -> None:
        if self.status is MundaneEvaluationStatus.EVALUATED:
            if (
                type(self.selection) is not PrecedingSyzygySelectionReceipt
                or self.issue is not None
            ):
                raise ValueError("evaluated preceding syzygy evidence requires only a selection")
            PrecedingSyzygySelectionReceipt.__post_init__(self.selection)
        elif self.status is MundaneEvaluationStatus.NOT_EVALUABLE:
            if self.selection is not None or type(self.issue) is not MundaneNotEvaluable:
                raise ValueError("not-evaluable preceding syzygy evidence requires only an issue")
            MundaneNotEvaluable.__post_init__(self.issue)
            if self.issue.component is not MundaneProfileComponent.PRECEDING_PRIMARY_SYZYGY:
                raise ValueError("preceding syzygy issue has the wrong component")
        else:
            raise TypeError("PrecedingSyzygyEvidence status must be typed")


def _preceding_syzygy_issue(
    reason: MundaneNotEvaluableReason,
    missing_inputs: tuple[str, ...],
    detail: str,
) -> PrecedingSyzygyEvidence:
    return PrecedingSyzygyEvidence(
        status=MundaneEvaluationStatus.NOT_EVALUABLE,
        selection=None,
        issue=MundaneNotEvaluable(
            component=MundaneProfileComponent.PRECEDING_PRIMARY_SYZYGY,
            reason=reason,
            missing_inputs=missing_inputs,
            detail=detail,
        ),
    )


def select_strictly_preceding_primary_syzygy(
    anchor_event: MundaneEventReceipt,
    candidates: tuple[PrimarySyzygyReceipt, ...],
) -> PrecedingSyzygyEvidence:
    """Select only after every receipt shares one explicit comparison contract."""

    if type(anchor_event) not in _EVENT_RECEIPT_TYPES:
        raise TypeError("anchor_event must be a Mundane event receipt")
    if type(candidates) is not tuple or any(
        type(item) is not PrimarySyzygyReceipt for item in candidates
    ):
        raise TypeError("candidates must contain PrimarySyzygyReceipt values")
    _revalidate_event_receipt(anchor_event)
    for candidate in candidates:
        _revalidate_event_receipt(candidate)
    if type(anchor_event) is not CardinalIngressReceipt:
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.EVENT_SEMANTICS_MISMATCH,
            ("cardinal_ingress_anchor_receipt",),
            "Strictly preceding primary syzygy v1 requires a cardinal-ingress anchor.",
        )
    anchor_epoch = anchor_event.event_epoch
    anchor_provenance = anchor_event.provenance
    if candidates and any(
        item.epoch.timescale is not anchor_epoch.timescale for item in candidates
    ):
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.NO_COMMON_TIMESCALE,
            ("shared_explicit_timescale",),
            "Candidate and anchor epochs cannot be ordered without one shared timescale.",
        )
    if candidates and any(
        item.provenance.reference_frame != anchor_provenance.reference_frame
        for item in candidates
    ):
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.INCOMPATIBLE_FRAME,
            ("shared_frame_and_equinox_receipt",),
            "Anchor and candidate receipts do not share one frame/equinox definition.",
        )
    if candidates and any(
        item.provenance.correction_regime != anchor_provenance.correction_regime
        for item in candidates
    ):
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.INCOMPATIBLE_CORRECTION_REGIME,
            ("shared_apparent_or_geometric_correction_regime",),
            "Anchor and candidate receipts do not share one correction regime.",
        )
    if candidates and any(
        item.provenance.mode is not anchor_provenance.mode
        or item.provenance.provenance_family_id
        != anchor_provenance.provenance_family_id
        for item in candidates
    ):
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.INCOMPATIBLE_PROVENANCE,
            ("compatible_provenance_family_receipt",),
            "Anchor and candidate receipts do not share one compatible provenance family.",
        )
    if candidates and len(
        {_provenance_contract_key(item.provenance) for item in candidates}
    ) != 1:
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.INCOMPATIBLE_PROVENANCE,
            ("homogeneous_candidate_provenance",),
            "Primary-syzygy candidates do not share one complete provenance contract.",
        )
    if candidates and len({item.angular_root_tolerance for item in candidates}) != 1:
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.INCOMPATIBLE_SOLVER_SEMANTICS,
            ("homogeneous_candidate_angular_root_tolerance",),
            "Primary-syzygy candidates do not share one angular root tolerance.",
        )
    if candidates and len({item.solver_tolerance_days for item in candidates}) != 1:
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.INCOMPATIBLE_SOLVER_SEMANTICS,
            ("homogeneous_candidate_solver_tolerance",),
            "Primary-syzygy candidates do not share one phase-solver tolerance.",
        )
    anchor_kernel = (
        anchor_provenance.verified_reader_identity,
        anchor_provenance.caller_asserted_artifact_id,
        anchor_provenance.caller_asserted_artifact_sha256,
    )
    if candidates and any(
        (
            item.provenance.verified_reader_identity,
            item.provenance.caller_asserted_artifact_id,
            item.provenance.caller_asserted_artifact_sha256,
        )
        != anchor_kernel
        for item in candidates
    ):
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.INCOMPATIBLE_KERNEL_IDENTITY,
            ("matching_verified_reader_or_caller_asserted_artifact_identity",),
            "Anchor and candidate receipts do not share one reader or artifact identity.",
        )
    earlier = tuple(item for item in candidates if item.epoch.jd < anchor_epoch.jd)
    if not earlier:
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.NO_STRICTLY_PRECEDING_SYZYGY,
            ("strictly_earlier_exact_new_or_full_moon",),
            "No supplied exact new/full Moon is strictly earlier than the anchor.",
        )
    selected = max(earlier, key=lambda item: item.epoch.jd)
    return PrecedingSyzygyEvidence(
        status=MundaneEvaluationStatus.EVALUATED,
        selection=PrecedingSyzygySelectionReceipt(
            anchor_event=anchor_event,
            candidates=candidates,
            selected=selected,
            comparison_timescale=anchor_epoch.timescale,
        ),
        issue=None,
    )


@dataclass(frozen=True, slots=True)
class JupiterSaturnConjunctionSequenceReceipt:
    """Ordered roots from one search interval; triple roots remain separate."""

    search_interval: MundaneSearchInterval
    roots: tuple[JupiterSaturnConjunctionReceipt, ...]

    def __post_init__(self) -> None:
        if type(self.search_interval) is not MundaneSearchInterval:
            raise TypeError("Jupiter-Saturn sequence search interval must be typed")
        MundaneSearchInterval.__post_init__(self.search_interval)
        MundaneEpoch.__post_init__(self.search_interval.start)
        MundaneEpoch.__post_init__(self.search_interval.end)
        _require_builtin_tuple(
            "JupiterSaturnConjunctionSequenceReceipt roots",
            self.roots,
        )
        if not self.roots:
            raise ValueError("Jupiter-Saturn sequence requires at least one root")
        if any(type(item) is not JupiterSaturnConjunctionReceipt for item in self.roots):
            raise TypeError("Jupiter-Saturn sequence roots must be typed")
        for item in self.roots:
            JupiterSaturnConjunctionReceipt.__post_init__(item)
        root_jds = tuple(item.epoch.jd for item in self.roots)
        if any(later <= earlier for earlier, later in zip(root_jds, root_jds[1:])):
            raise ValueError("Jupiter-Saturn roots must be strictly increasing by epoch")
        ids = tuple(item.event_id for item in self.roots)
        if len(ids) != len(set(ids)):
            raise ValueError("Jupiter-Saturn roots must have unique event ids")
        timescales = {item.epoch.timescale for item in self.roots}
        if timescales != {self.search_interval.timescale}:
            raise ValueError(
                "Jupiter-Saturn sequence roots require the search-interval timescale"
            )
        if any(not self.search_interval.contains(item.epoch) for item in self.roots):
            raise ValueError(
                "Jupiter-Saturn roots must lie in the half-open search interval"
            )
        if len({_provenance_contract_key(item.provenance) for item in self.roots}) != 1:
            raise ValueError(
                "Jupiter-Saturn roots require one homogeneous provenance contract"
            )
        if len({item.solver_tolerance_days for item in self.roots}) != 1:
            raise ValueError(
                "Jupiter-Saturn roots require one homogeneous solver tolerance"
            )
        if len({item.angular_root_tolerance for item in self.roots}) != 1:
            raise ValueError(
                "Jupiter-Saturn roots require one homogeneous angular root tolerance"
            )


@dataclass(frozen=True, slots=True)
class MundaneLocationSelectionReceipt:
    """Explicit caller-owned geographic and institutional location identity."""

    label: str
    latitude_deg: float
    longitude_deg_east: float
    role: MundaneLocationRole
    source_id: str
    valid_from: MundaneEpoch | None = None
    valid_until: MundaneEpoch | None = None

    def __post_init__(self) -> None:
        _trimmed("Mundane location label", self.label)
        object.__setattr__(
            self,
            "latitude_deg",
            _as_builtin_float("Mundane location latitude", self.latitude_deg),
        )
        object.__setattr__(
            self,
            "longitude_deg_east",
            _as_builtin_float(
                "Mundane location east-positive longitude",
                self.longitude_deg_east,
            ),
        )
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("Mundane location latitude must be in [-90, 90]")
        if not -180.0 <= self.longitude_deg_east <= 180.0:
            raise ValueError("Mundane location east-positive longitude must be in [-180, 180]")
        if type(self.role) is not MundaneLocationRole:
            raise TypeError("Mundane location role must be typed")
        _trimmed("Mundane location source_id", self.source_id)
        if self.role in _INSTITUTIONAL_LOCATION_ROLES and self.valid_from is None:
            raise ValueError("Institutional location roles require an explicit validity start")
        if self.valid_from is not None:
            if type(self.valid_from) is not MundaneEpoch:
                raise TypeError("Location validity start must be a MundaneEpoch")
            MundaneEpoch.__post_init__(self.valid_from)
            if self.valid_until is not None:
                if type(self.valid_until) is not MundaneEpoch:
                    raise TypeError("Location validity end must be a MundaneEpoch")
                MundaneEpoch.__post_init__(self.valid_until)
                if self.valid_from.timescale is not self.valid_until.timescale:
                    raise ValueError("Location validity endpoints require one timescale")
                if self.valid_until.jd <= self.valid_from.jd:
                    raise ValueError("Location validity [start, end) interval must be non-empty")
        elif self.valid_until is not None:
            raise ValueError("Location validity end requires a validity start")

    def valid_at(self, epoch: MundaneEpoch) -> bool | None:
        """Return validity, or None when no comparable institutional scale exists."""

        if type(epoch) is not MundaneEpoch:
            raise TypeError("Location validity query requires a MundaneEpoch")
        if self.valid_from is None:
            return True
        if self.valid_from.timescale is not epoch.timescale:
            return None
        if self.valid_until is None:
            return self.valid_from.jd <= epoch.jd
        return self.valid_from.jd <= epoch.jd < self.valid_until.jd


_TROPICAL_SIGNS = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)
_SIGN_MODALITIES = (
    MundaneZodiacModality.CARDINAL,
    MundaneZodiacModality.FIXED,
    MundaneZodiacModality.MUTABLE,
) * 4


def _sign_and_modality(longitude_deg: float) -> tuple[str, MundaneZodiacModality]:
    _longitude("tropical longitude", longitude_deg)
    index = int(longitude_deg // 30.0)
    return _TROPICAL_SIGNS[index], _SIGN_MODALITIES[index]


@dataclass(frozen=True, slots=True)
class MundaneAscendantReceipt:
    """Engine-built local Ascendant bound to one exact Aries ingress."""

    aries_ingress: CardinalIngressReceipt
    location: MundaneLocationSelectionReceipt
    clock: MundaneEventClockReceipt
    ascendant_longitude_deg: float
    ascendant_sign: str
    ascendant_modality: MundaneZodiacModality
    local_angle_method_id: str = "moira.houses._local_angles_at"
    _verification_token: InitVar[object | None] = None

    def __post_init__(self, _verification_token: object | None) -> None:
        if _verification_token is not _ASCENDANT_RECEIPT_TOKEN:
            raise ValueError("Mundane Ascendant receipt must be produced by the engine")
        if (
            type(self.aries_ingress) is not CardinalIngressReceipt
            or self.aries_ingress.ingress is not CardinalIngress.ARIES
        ):
            raise ValueError("Mundane Ascendant requires an exact Aries ingress receipt")
        _revalidate_event_receipt(self.aries_ingress)
        if type(self.location) is not MundaneLocationSelectionReceipt:
            raise TypeError("Mundane Ascendant location must be typed")
        MundaneLocationSelectionReceipt.__post_init__(self.location)
        if type(self.clock) is not MundaneEventClockReceipt:
            raise TypeError("Mundane Ascendant clock must be typed")
        _revalidate_event_clock(self.clock)
        if self.clock.ut1 != self.aries_ingress.epoch:
            raise ValueError("Mundane Ascendant clock must bind the Aries ingress epoch")
        if (
            self.aries_ingress.clock is None
            or self.clock != self.aries_ingress.clock
            or self.clock.verified_reader_identity
            != self.aries_ingress.provenance.verified_reader_identity
        ):
            raise ValueError("Mundane Ascendant must retain the Aries reader-bound clock")
        validity = self.location.valid_at(self.aries_ingress.epoch)
        if validity is not True:
            raise ValueError("Mundane Ascendant location must be valid at the ingress")
        object.__setattr__(
            self,
            "ascendant_longitude_deg",
            _longitude(
                "Mundane Ascendant longitude",
                self.ascendant_longitude_deg,
            ),
        )
        sign, modality = _sign_and_modality(self.ascendant_longitude_deg)
        _trimmed("Mundane Ascendant sign", self.ascendant_sign)
        if self.ascendant_sign != sign or self.ascendant_modality is not modality:
            raise ValueError("Mundane Ascendant sign/modality must derive from longitude")
        _trimmed("Mundane Ascendant local-angle method", self.local_angle_method_id)
        if self.local_angle_method_id != "moira.houses._local_angles_at":
            raise ValueError("Mundane Ascendant local-angle method is fixed")


@dataclass(frozen=True, slots=True)
class RameseyIngressCadenceReceipt:
    """Non-interpretive chart cadence selected by Aries-ingress Ascendant modality."""

    aries_ingress: CardinalIngressReceipt
    ascendant: MundaneAscendantReceipt
    selected_ingresses: tuple[CardinalIngress, ...]
    chart_count: int
    policy: CardinalIngressSelectionPolicy = (
        CardinalIngressSelectionPolicy.RAMESEY_1653_ASCENDANT_MODALITY_V1
    )
    source_reference: str = "William Ramesey, Astrologia Restaurata (1653), mundane ingress cadence"

    def __post_init__(self) -> None:
        if (
            type(self.aries_ingress) is not CardinalIngressReceipt
            or self.aries_ingress.ingress is not CardinalIngress.ARIES
        ):
            raise ValueError("Ramesey cadence requires an Aries ingress receipt")
        _revalidate_event_receipt(self.aries_ingress)
        if type(self.ascendant) is not MundaneAscendantReceipt:
            raise TypeError("Ramesey cadence Ascendant must be typed")
        MundaneAscendantReceipt.__post_init__(
            self.ascendant,
            _ASCENDANT_RECEIPT_TOKEN,
        )
        if self.ascendant.aries_ingress != self.aries_ingress:
            raise ValueError("Ramesey cadence must preserve the complete Aries receipt")
        _require_builtin_tuple(
            "RameseyIngressCadenceReceipt selected_ingresses",
            self.selected_ingresses,
        )
        expected = {
            MundaneZodiacModality.CARDINAL: tuple(CardinalIngress),
            MundaneZodiacModality.MUTABLE: (
                CardinalIngress.ARIES,
                CardinalIngress.LIBRA,
            ),
            MundaneZodiacModality.FIXED: (CardinalIngress.ARIES,),
        }[self.ascendant.ascendant_modality]
        if (
            self.selected_ingresses != expected
            or type(self.chart_count) is not int
            or self.chart_count != len(expected)
        ):
            raise ValueError("Ramesey cadence must derive exactly from Ascendant modality")
        if self.policy is not CardinalIngressSelectionPolicy.RAMESEY_1653_ASCENDANT_MODALITY_V1:
            raise ValueError("Ramesey cadence policy is fixed")
        _trimmed("Ramesey cadence source reference", self.source_reference)
        if self.source_reference != (
            "William Ramesey, Astrologia Restaurata (1653), mundane ingress cadence"
        ):
            raise ValueError("Ramesey cadence source reference is fixed")


@dataclass(frozen=True, slots=True)
class RameseyIngressCadenceEvidence:
    """Evaluated Ascendant cadence or typed refusal without fabricated geometry."""

    status: MundaneEvaluationStatus
    cadence: RameseyIngressCadenceReceipt | None
    issue: MundaneNotEvaluable | None

    def __post_init__(self) -> None:
        if self.status is MundaneEvaluationStatus.EVALUATED:
            if (
                type(self.cadence) is not RameseyIngressCadenceReceipt
                or self.issue is not None
            ):
                raise ValueError("evaluated Ramesey cadence requires only a receipt")
            RameseyIngressCadenceReceipt.__post_init__(self.cadence)
        elif self.status is MundaneEvaluationStatus.NOT_EVALUABLE:
            if self.cadence is not None or type(self.issue) is not MundaneNotEvaluable:
                raise ValueError("not-evaluable Ramesey cadence requires only an issue")
            MundaneNotEvaluable.__post_init__(self.issue)
            if self.issue.component is not MundaneProfileComponent.CARDINAL_INGRESS_SELECTION:
                raise ValueError("Ramesey cadence issue has the wrong component")
        else:
            raise TypeError("Ramesey cadence status must be typed")


def _ramesey_issue(
    reason: MundaneNotEvaluableReason,
    missing_inputs: tuple[str, ...],
    detail: str,
) -> RameseyIngressCadenceEvidence:
    return RameseyIngressCadenceEvidence(
        status=MundaneEvaluationStatus.NOT_EVALUABLE,
        cadence=None,
        issue=MundaneNotEvaluable(
            component=MundaneProfileComponent.CARDINAL_INGRESS_SELECTION,
            reason=reason,
            missing_inputs=missing_inputs,
            detail=detail,
        ),
    )


def assess_ramesey_ingress_cadence(
    aries_ingress: CardinalIngressReceipt,
    location: MundaneLocationSelectionReceipt | None,
) -> RameseyIngressCadenceEvidence:
    """Evaluate Ramesey's cadence from local angles at an exact Aries root."""

    from .houses import _local_angles_at

    if type(aries_ingress) is not CardinalIngressReceipt:
        raise TypeError("aries_ingress must be a CardinalIngressReceipt")
    _revalidate_event_receipt(aries_ingress)
    if aries_ingress.ingress is not CardinalIngress.ARIES:
        return _ramesey_issue(
            MundaneNotEvaluableReason.EVENT_SEMANTICS_MISMATCH,
            ("exact_aries_ingress_receipt",),
            "Ramesey cadence is evaluated from the Aries ingress chart only.",
        )
    if aries_ingress.clock is None:
        return _ramesey_issue(
            MundaneNotEvaluableReason.SOURCE_RECEIPT_INCOMPLETE,
            ("reader_bound_aries_event_clock",),
            "The Aries ingress lacks an engine-built UT1/TT clock receipt.",
        )
    if location is None:
        return _ramesey_issue(
            MundaneNotEvaluableReason.MISSING_LOCATION,
            ("explicit_location",),
            "Ramesey cadence requires an explicit local Ascendant location.",
        )
    if type(location) is not MundaneLocationSelectionReceipt:
        raise TypeError("location must be a MundaneLocationSelectionReceipt or None")
    validity = location.valid_at(aries_ingress.epoch)
    if validity is None:
        return _ramesey_issue(
            MundaneNotEvaluableReason.LOCATION_VALIDITY_UNAVAILABLE,
            ("location_validity_in_event_timescale",),
            "Location validity cannot be compared to the Aries UT1 epoch.",
        )
    if not validity:
        return _ramesey_issue(
            MundaneNotEvaluableReason.LOCATION_NOT_VALID_AT_EVENT,
            ("location_valid_at_aries_ingress",),
            "The selected location is not valid at the Aries ingress.",
        )
    angles = _local_angles_at(
        aries_ingress.epoch.jd,
        location.latitude_deg,
        location.longitude_deg_east,
    )
    if not math.isclose(
        angles.jd_tt,
        aries_ingress.clock.tt.jd,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        return _ramesey_issue(
            MundaneNotEvaluableReason.INCOMPATIBLE_CLOCK_REALIZATION,
            ("shared_local_angle_and_event_tt_reduction",),
            "The local-angle TT reduction does not match the reader-bound event clock.",
        )
    sign, modality = _sign_and_modality(angles.asc)
    ascendant = MundaneAscendantReceipt(
        aries_ingress=aries_ingress,
        location=location,
        clock=aries_ingress.clock,
        ascendant_longitude_deg=angles.asc,
        ascendant_sign=sign,
        ascendant_modality=modality,
        _verification_token=_ASCENDANT_RECEIPT_TOKEN,
    )
    selected = {
        MundaneZodiacModality.CARDINAL: tuple(CardinalIngress),
        MundaneZodiacModality.MUTABLE: (
            CardinalIngress.ARIES,
            CardinalIngress.LIBRA,
        ),
        MundaneZodiacModality.FIXED: (CardinalIngress.ARIES,),
    }[modality]
    return RameseyIngressCadenceEvidence(
        status=MundaneEvaluationStatus.EVALUATED,
        cadence=RameseyIngressCadenceReceipt(
            aries_ingress=aries_ingress,
            ascendant=ascendant,
            selected_ingresses=selected,
            chart_count=len(selected),
        ),
        issue=None,
    )


@dataclass(frozen=True, slots=True)
class MundaneHouseComputationReceipt:
    """Exact inputs and recomputed strict result of one Moira house computation."""

    event_epoch: MundaneEpoch
    location: MundaneLocationSelectionReceipt
    requested_house_system: str
    policy: HousePolicy = field(init=False)
    houses: HouseCusps = field(init=False)
    calculator_id: str = field(
        init=False,
        default="moira.houses.calculate_houses",
    )

    def __post_init__(self) -> None:
        if type(self.event_epoch) is not MundaneEpoch:
            raise TypeError("House computation event_epoch must be typed")
        MundaneEpoch.__post_init__(self.event_epoch)
        if self.event_epoch.timescale is not MundaneTimescale.UT1:
            raise ValueError("Mundane house computation requires an explicit UT1 epoch")
        if type(self.location) is not MundaneLocationSelectionReceipt:
            raise TypeError("House computation location must be typed")
        MundaneLocationSelectionReceipt.__post_init__(self.location)
        _trimmed(
            "MundaneHouseComputationReceipt requested_house_system",
            self.requested_house_system,
        )
        validity = self.location.valid_at(self.event_epoch)
        if validity is None:
            raise ValueError("Location validity and event epoch require a shared timescale")
        if not validity:
            raise ValueError("Institutional location is not valid at the event epoch")
        policy = HousePolicy.strict()
        houses = calculate_houses(
            self.event_epoch.jd,
            self.location.latitude_deg,
            self.location.longitude_deg_east,
            self.requested_house_system,
            policy=policy,
        )
        if type(houses) is not HouseCusps:
            raise TypeError("House computation result must be a HouseCusps receipt")
        if houses.policy != policy:
            raise ValueError("HouseCusps must preserve the exact strict computation policy")
        if houses.system != self.requested_house_system:
            raise ValueError("House receipt requested system must match computation input")
        if houses.fallback:
            raise ValueError("Mundane v1 forbids silent house-system fallback")
        if houses.effective_system != self.requested_house_system:
            raise ValueError("Effective house system must match the requested system")
        object.__setattr__(self, "policy", policy)
        object.__setattr__(self, "houses", houses)


@dataclass(frozen=True, slots=True)
class MundaneLocalProjectionReceipt:
    """Local projection bound to an exact strict house-computation receipt."""

    anchor_event: MundaneEventReceipt
    house_computation: MundaneHouseComputationReceipt
    chart_epoch_kind: EclipseAnchorEpoch | None

    def __post_init__(self) -> None:
        if type(self.anchor_event) not in _EVENT_RECEIPT_TYPES:
            raise TypeError("Local projection requires a complete anchor event receipt")
        _revalidate_event_receipt(self.anchor_event)
        if type(self.house_computation) is not MundaneHouseComputationReceipt:
            raise TypeError("Local projection requires a house-computation receipt")
        MundaneHouseComputationReceipt.__post_init__(self.house_computation)
        if (
            self.chart_epoch_kind is not None
            and type(self.chart_epoch_kind) is not EclipseAnchorEpoch
        ):
            raise TypeError("chart_epoch_kind must be an EclipseAnchorEpoch or None")
        if type(self.anchor_event) is EclipseEventReceipt:
            if self.chart_epoch_kind is None:
                raise ValueError(
                    "Eclipse local projection requires an explicit chart epoch kind"
                )
            chart_epoch = self.anchor_event.named_epoch_receipt(self.chart_epoch_kind)
            if chart_epoch is None:
                raise ValueError(
                    "Eclipse local projection selected an unavailable named epoch"
                )
            if self.house_computation.event_epoch != chart_epoch.epoch:
                raise ValueError(
                    "Eclipse local projection epoch must match its explicit chart epoch kind"
                )
        else:
            if self.chart_epoch_kind is not None:
                raise ValueError(
                    "Non-eclipse local projections require chart_epoch_kind=None"
                )
            if self.house_computation.event_epoch != self.anchor_event.event_epoch:
                raise ValueError(
                    "Local projection must preserve the complete anchor event epoch"
                )

    @property
    def event_epoch(self) -> MundaneEpoch:
        return self.house_computation.event_epoch

    @property
    def location(self) -> MundaneLocationSelectionReceipt:
        return self.house_computation.location

    @property
    def requested_house_system(self) -> str:
        return self.house_computation.requested_house_system

    @property
    def houses(self) -> HouseCusps:
        return self.house_computation.houses

    @property
    def projection_source_id(self) -> str:
        return self.house_computation.calculator_id


@dataclass(frozen=True, slots=True)
class MundaneEventEvidence:
    """Evaluated anchor event or typed global-event failure."""

    status: MundaneEvaluationStatus
    receipt: MundaneEventReceipt | None
    issue: MundaneNotEvaluable | None

    def __post_init__(self) -> None:
        if self.status is MundaneEvaluationStatus.EVALUATED:
            if type(self.receipt) not in _EVENT_RECEIPT_TYPES or self.issue is not None:
                raise ValueError("evaluated anchor evidence requires only an event receipt")
            _revalidate_event_receipt(self.receipt)
        elif self.status is MundaneEvaluationStatus.NOT_EVALUABLE:
            if self.receipt is not None or type(self.issue) is not MundaneNotEvaluable:
                raise ValueError("not-evaluable anchor evidence requires only an issue")
            MundaneNotEvaluable.__post_init__(self.issue)
            if self.issue.component is not MundaneProfileComponent.ANCHOR_EVENT:
                raise ValueError("anchor event issue has the wrong component")
        else:
            raise TypeError("MundaneEventEvidence status must be typed")


@dataclass(frozen=True, slots=True)
class MundaneLocalProjectionEvidence:
    """Evaluated local chart geometry or typed projection failure."""

    status: MundaneEvaluationStatus
    receipt: MundaneLocalProjectionReceipt | None
    issue: MundaneNotEvaluable | None

    def __post_init__(self) -> None:
        if self.status is MundaneEvaluationStatus.EVALUATED:
            if (
                type(self.receipt) is not MundaneLocalProjectionReceipt
                or self.issue is not None
            ):
                raise ValueError("evaluated local projection evidence requires only a receipt")
            MundaneLocalProjectionReceipt.__post_init__(self.receipt)
        elif self.status is MundaneEvaluationStatus.NOT_EVALUABLE:
            if self.receipt is not None or type(self.issue) is not MundaneNotEvaluable:
                raise ValueError("not-evaluable local projection evidence requires only an issue")
            MundaneNotEvaluable.__post_init__(self.issue)
            if self.issue.component is not MundaneProfileComponent.LOCAL_CHART_PROJECTION:
                raise ValueError("local projection issue has the wrong component")
        else:
            raise TypeError("MundaneLocalProjectionEvidence status must be typed")


def _local_projection_issue(
    reason: MundaneNotEvaluableReason,
    missing_inputs: tuple[str, ...],
    detail: str,
) -> MundaneLocalProjectionEvidence:
    return MundaneLocalProjectionEvidence(
        status=MundaneEvaluationStatus.NOT_EVALUABLE,
        receipt=None,
        issue=MundaneNotEvaluable(
            component=MundaneProfileComponent.LOCAL_CHART_PROJECTION,
            reason=reason,
            missing_inputs=missing_inputs,
            detail=detail,
        ),
    )


def build_mundane_local_projection(
    anchor_event: MundaneEventReceipt,
    location: MundaneLocationSelectionReceipt | None,
    requested_house_system: str | None,
    *,
    chart_epoch_kind: EclipseAnchorEpoch | None,
) -> MundaneLocalProjectionEvidence:
    """Compute one strict local projection through ``calculate_houses``."""

    if type(anchor_event) not in _EVENT_RECEIPT_TYPES:
        raise TypeError("anchor_event must be a Mundane event receipt")
    _revalidate_event_receipt(anchor_event)
    if type(anchor_event) is EclipseEventReceipt:
        if chart_epoch_kind is None:
            return _local_projection_issue(
                MundaneNotEvaluableReason.SOURCE_RECEIPT_INCOMPLETE,
                ("explicit_eclipse_chart_epoch_kind",),
                "An eclipse local chart requires one explicitly named epoch kind.",
            )
        named_epoch = anchor_event.named_epoch_receipt(chart_epoch_kind)
        if named_epoch is None:
            return _local_projection_issue(
                MundaneNotEvaluableReason.SOURCE_RECEIPT_INCOMPLETE,
                ("selected_named_eclipse_epoch",),
                "The selected eclipse chart epoch is not present in the event receipt.",
            )
        event_epoch = named_epoch.epoch
    else:
        if chart_epoch_kind is not None:
            return _local_projection_issue(
                MundaneNotEvaluableReason.EVENT_SEMANTICS_MISMATCH,
                ("chart_epoch_kind_none_for_non_eclipse",),
                "Non-eclipse local charts cannot carry an eclipse epoch kind.",
            )
        event_epoch = anchor_event.event_epoch
    if location is None:
        return _local_projection_issue(
            MundaneNotEvaluableReason.MISSING_LOCATION,
            ("explicit_location",),
            "No local chart is computed without a caller-owned location receipt.",
        )
    if type(location) is not MundaneLocationSelectionReceipt:
        raise TypeError("location must be a MundaneLocationSelectionReceipt or None")
    if (
        requested_house_system is None
        or type(requested_house_system) is not str
        or not requested_house_system.strip()
    ):
        return _local_projection_issue(
            MundaneNotEvaluableReason.HOUSE_SYSTEM_NOT_SUPPLIED,
            ("explicit_house_system",),
            "No local chart is computed without an explicit house system.",
        )
    if requested_house_system != requested_house_system.strip():
        raise ValueError("requested_house_system must be trimmed")
    if event_epoch.timescale is not MundaneTimescale.UT1:
        return _local_projection_issue(
            MundaneNotEvaluableReason.HOUSE_INPUT_TIMESCALE_NOT_UT1,
            ("event_epoch_ut1",),
            "The existing house primitive requires an explicit UT1 event epoch.",
        )
    validity = location.valid_at(event_epoch)
    if validity is None:
        return _local_projection_issue(
            MundaneNotEvaluableReason.LOCATION_VALIDITY_UNAVAILABLE,
            ("location_validity_in_event_timescale",),
            "Location validity and event epoch do not share one explicit timescale.",
        )
    if not validity:
        return _local_projection_issue(
            MundaneNotEvaluableReason.LOCATION_NOT_VALID_AT_EVENT,
            ("location_valid_at_event",),
            "The selected institutional location is not valid at the event epoch.",
        )
    try:
        house_computation = MundaneHouseComputationReceipt(
            event_epoch=event_epoch,
            location=location,
            requested_house_system=requested_house_system,
        )
    except (ArithmeticError, NotImplementedError, ValueError) as exc:
        return _local_projection_issue(
            MundaneNotEvaluableReason.HOUSE_PROJECTION_FAILED,
            ("strict_house_computation",),
            f"Strict house computation failed: {type(exc).__name__}: {exc}",
        )
    return MundaneLocalProjectionEvidence(
        status=MundaneEvaluationStatus.EVALUATED,
        receipt=MundaneLocalProjectionReceipt(
            anchor_event=anchor_event,
            house_computation=house_computation,
            chart_epoch_kind=chart_epoch_kind,
        ),
        issue=None,
    )


@dataclass(frozen=True, slots=True)
class MundaneProfileProvenance:
    """Composition provenance; event computation remains owned by its receipts."""

    source_refs: tuple[str, ...]
    engine_version: str | None = None
    method_id: str = "moira.mundane.compose_mundane_event_chart_profile.v1"
    derivation: str = "engine_composition_of_revalidated_typed_component_receipts"

    def __post_init__(self) -> None:
        _require_builtin_tuple(
            "MundaneProfileProvenance source_refs",
            self.source_refs,
        )
        if (
            not self.source_refs
            or len(self.source_refs) != len(set(self.source_refs))
            or any(
                type(item) is not str or not item or item != item.strip()
                for item in self.source_refs
            )
        ):
            raise ValueError("Mundane profile source_refs must be unique non-empty strings")
        if self.engine_version is not None:
            _trimmed("MundaneProfileProvenance engine_version", self.engine_version)
        _trimmed("MundaneProfileProvenance method_id", self.method_id)
        if self.method_id != "moira.mundane.compose_mundane_event_chart_profile.v1":
            raise ValueError("Mundane profile method_id is fixed")
        _trimmed("MundaneProfileProvenance derivation", self.derivation)
        if self.derivation != "engine_composition_of_revalidated_typed_component_receipts":
            raise ValueError("Mundane profile derivation is fixed")


def _profile_source_refs(
    anchor_event: MundaneEventEvidence,
    cardinal_ingress_selection: CardinalIngressSelectionEvidence,
    preceding_syzygy: PrecedingSyzygyEvidence,
    local_projection: MundaneLocalProjectionEvidence,
) -> tuple[str, ...]:
    """Derive a stable source inventory from the retained component receipts."""

    refs = {"moira.mundane.compose_mundane_event_chart_profile"}
    if anchor_event.receipt is not None:
        receipt = anchor_event.receipt
        refs.update(receipt.provenance.source_refs)
        if type(receipt) is EclipseEventReceipt:
            for epoch_receipt in receipt.named_epochs:
                refs.update(epoch_receipt.provenance.source_refs)
            for contact_receipt in receipt.global_contacts:
                refs.update(contact_receipt.provenance.source_refs)
    if cardinal_ingress_selection.selection is not None:
        selection = cardinal_ingress_selection.selection
        refs.add(selection.source_reference)
        for event in selection.all_events:
            refs.update(event.provenance.source_refs)
        if selection.ramesey_cadence is not None:
            refs.add(selection.ramesey_cadence.source_reference)
            refs.add(selection.ramesey_cadence.ascendant.local_angle_method_id)
            refs.add(selection.ramesey_cadence.ascendant.location.source_id)
    if preceding_syzygy.selection is not None:
        for candidate in preceding_syzygy.selection.candidates:
            refs.update(candidate.provenance.source_refs)
    if local_projection.receipt is not None:
        refs.add(local_projection.receipt.projection_source_id)
        refs.add(local_projection.receipt.location.source_id)
    return tuple(sorted(refs))


@dataclass(frozen=True, slots=True)
class MundaneEventChartProfile:
    """Non-interpretive composition of global event and optional local truth."""

    anchor_event: MundaneEventEvidence
    cardinal_ingress_selection: CardinalIngressSelectionEvidence
    preceding_syzygy: PrecedingSyzygyEvidence
    local_projection: MundaneLocalProjectionEvidence
    provenance: MundaneProfileProvenance = field(init=False)
    additional_not_evaluable: tuple[MundaneNotEvaluable, ...] = ()
    complete_mundane_judgement: bool = False
    scoring: str = "not_provided"
    advice_language: str = "not_provided"

    def __post_init__(self) -> None:
        if type(self.anchor_event) is not MundaneEventEvidence:
            raise TypeError("Mundane profile anchor_event must be typed")
        if type(self.cardinal_ingress_selection) is not CardinalIngressSelectionEvidence:
            raise TypeError("Mundane profile cardinal ingress selection must be typed")
        if type(self.preceding_syzygy) is not PrecedingSyzygyEvidence:
            raise TypeError("Mundane profile preceding_syzygy must be typed")
        if type(self.local_projection) is not MundaneLocalProjectionEvidence:
            raise TypeError("Mundane profile local_projection must be typed")
        MundaneEventEvidence.__post_init__(self.anchor_event)
        CardinalIngressSelectionEvidence.__post_init__(
            self.cardinal_ingress_selection
        )
        PrecedingSyzygyEvidence.__post_init__(self.preceding_syzygy)
        MundaneLocalProjectionEvidence.__post_init__(self.local_projection)
        object.__setattr__(
            self,
            "provenance",
            MundaneProfileProvenance(
                source_refs=_profile_source_refs(
                    self.anchor_event,
                    self.cardinal_ingress_selection,
                    self.preceding_syzygy,
                    self.local_projection,
                )
            ),
        )
        _require_builtin_tuple(
            "MundaneEventChartProfile additional_not_evaluable",
            self.additional_not_evaluable,
        )
        if any(type(item) is not MundaneNotEvaluable for item in self.additional_not_evaluable):
            raise TypeError("additional_not_evaluable must contain typed issues")
        extra_components = tuple(item.component for item in self.additional_not_evaluable)
        if len(extra_components) != len(set(extra_components)):
            raise ValueError("additional not-evaluable components must be unique")
        if any(
            component in {
                MundaneProfileComponent.ANCHOR_EVENT,
                MundaneProfileComponent.CARDINAL_INGRESS_SELECTION,
                MundaneProfileComponent.PRECEDING_PRIMARY_SYZYGY,
                MundaneProfileComponent.LOCAL_CHART_PROJECTION,
            }
            for component in extra_components
        ):
            raise ValueError("primary profile component issues belong in their typed evidence")
        if (
            MundaneProfileComponent.LOCAL_ECLIPSE_CIRCUMSTANCES
            in extra_components
            and self.anchor_event.receipt is not None
            and type(self.anchor_event.receipt) is not EclipseEventReceipt
        ):
            raise ValueError(
                "local eclipse circumstances evidence requires an eclipse anchor"
            )
        if self.anchor_event.status is MundaneEvaluationStatus.NOT_EVALUABLE and (
            self.cardinal_ingress_selection.status is MundaneEvaluationStatus.EVALUATED
            or
            self.preceding_syzygy.status is MundaneEvaluationStatus.EVALUATED
            or self.local_projection.status is MundaneEvaluationStatus.EVALUATED
        ):
            raise ValueError("derived profile components cannot be evaluated without an anchor event")
        if self.anchor_event.receipt is not None:
            anchor_epoch = self.anchor_event.receipt.event_epoch
            if self.cardinal_ingress_selection.selection is not None:
                if type(self.anchor_event.receipt) is not CardinalIngressReceipt:
                    raise ValueError(
                        "evaluated cardinal ingress selection requires a cardinal anchor"
                    )
                if self.anchor_event.receipt not in (
                    self.cardinal_ingress_selection.selection.selected_events
                ):
                    raise ValueError(
                        "profile anchor must be one of the exact selected ingress receipts"
                    )
            if self.preceding_syzygy.selection is not None and (
                self.preceding_syzygy.selection.anchor_event
                != self.anchor_event.receipt
            ):
                raise ValueError(
                    "preceding syzygy selection must preserve the complete profile anchor receipt"
                )
            if self.local_projection.receipt is not None and (
                self.local_projection.receipt.anchor_event
                != self.anchor_event.receipt
            ):
                raise ValueError(
                    "local projection must preserve the complete profile anchor receipt"
                )
            if type(self.anchor_event.receipt) is EclipseEventReceipt:
                if self.local_projection.receipt is not None:
                    chart_epoch_kind = self.local_projection.receipt.chart_epoch_kind
                    if chart_epoch_kind is None:
                        raise ValueError(
                            "Eclipse local projection requires an explicit chart epoch kind"
                        )
                    chart_epoch = {
                        EclipseAnchorEpoch.ECLIPTIC_SYZYGY: (
                            self.anchor_event.receipt.ecliptic_syzygy_epoch
                        ),
                        EclipseAnchorEpoch.EQUATORIAL_CONJUNCTION: (
                            self.anchor_event.receipt.equatorial_conjunction_epoch
                        ),
                        EclipseAnchorEpoch.EQUATORIAL_OPPOSITION: (
                            self.anchor_event.receipt.equatorial_opposition_epoch
                        ),
                        EclipseAnchorEpoch.GREATEST_ECLIPSE: (
                            self.anchor_event.receipt.greatest_eclipse_epoch
                        ),
                    }[chart_epoch_kind]
                    if chart_epoch is None:
                        raise ValueError(
                            "Eclipse local projection selected an unavailable named epoch"
                        )
                    if self.local_projection.receipt.event_epoch != chart_epoch:
                        raise ValueError(
                            "Eclipse local projection epoch must match its explicit chart epoch kind"
                        )
            elif (
                self.local_projection.receipt is not None
                and self.local_projection.receipt.chart_epoch_kind is not None
            ):
                raise ValueError(
                    "Non-eclipse local projections require chart_epoch_kind=None"
                )
            elif self.local_projection.receipt is not None and (
                self.local_projection.receipt.event_epoch != anchor_epoch
            ):
                raise ValueError("local projection must preserve the profile anchor epoch")
        if (
            type(self.complete_mundane_judgement) is not bool
            or self.complete_mundane_judgement is not False
        ):
            raise ValueError("MundaneEventChartProfile is not a complete mundane judgement")
        _trimmed("MundaneEventChartProfile scoring", self.scoring)
        _trimmed("MundaneEventChartProfile advice_language", self.advice_language)
        if self.scoring != "not_provided" or self.advice_language != "not_provided":
            raise ValueError("MundaneEventChartProfile provides no score or advice language")

    @property
    def status(self) -> MundaneEvaluationStatus:
        return self.anchor_event.status

    @property
    def not_evaluable(self) -> tuple[MundaneNotEvaluable, ...]:
        issues = []
        for evidence in (
            self.anchor_event,
            self.cardinal_ingress_selection,
            self.preceding_syzygy,
            self.local_projection,
        ):
            if evidence.issue is not None:
                issues.append(evidence.issue)
        issues.extend(self.additional_not_evaluable)
        return tuple(issues)

    @property
    def included_components(self) -> tuple[MundaneProfileComponent, ...]:
        included = []
        if self.anchor_event.status is MundaneEvaluationStatus.EVALUATED:
            included.append(MundaneProfileComponent.ANCHOR_EVENT)
        if self.cardinal_ingress_selection.status is MundaneEvaluationStatus.EVALUATED:
            included.append(MundaneProfileComponent.CARDINAL_INGRESS_SELECTION)
        if self.preceding_syzygy.status is MundaneEvaluationStatus.EVALUATED:
            included.append(MundaneProfileComponent.PRECEDING_PRIMARY_SYZYGY)
        if self.local_projection.status is MundaneEvaluationStatus.EVALUATED:
            included.append(MundaneProfileComponent.LOCAL_CHART_PROJECTION)
        return tuple(included)

    @property
    def excluded_components(self) -> tuple[MundaneProfileExclusion, ...]:
        return tuple(MundaneProfileExclusion)


def compose_mundane_event_chart_profile(
    *,
    anchor_event: MundaneEventEvidence,
    cardinal_ingress_selection: CardinalIngressSelectionEvidence,
    preceding_syzygy: PrecedingSyzygyEvidence,
    local_projection: MundaneLocalProjectionEvidence,
    additional_not_evaluable: tuple[MundaneNotEvaluable, ...] = (),
) -> MundaneEventChartProfile:
    """Compose a non-interpretive profile with engine-derived provenance."""

    return MundaneEventChartProfile(
        anchor_event=anchor_event,
        cardinal_ingress_selection=cardinal_ingress_selection,
        preceding_syzygy=preceding_syzygy,
        local_projection=local_projection,
        additional_not_evaluable=additional_not_evaluable,
    )


def _unadmitted_anchor_issue(
    reason: MundaneNotEvaluableReason,
    missing_inputs: tuple[str, ...],
    detail: str,
) -> MundaneEventEvidence:
    return MundaneEventEvidence(
        status=MundaneEvaluationStatus.NOT_EVALUABLE,
        receipt=None,
        issue=MundaneNotEvaluable(
            component=MundaneProfileComponent.ANCHOR_EVENT,
            reason=reason,
            missing_inputs=missing_inputs,
            detail=detail,
        ),
    )


def assess_transit_cardinal_ingress(
    event: object,
    *,
    reader: object,
) -> MundaneEventEvidence:
    """Revalidate one complete transit ingress on Moira's true-of-date surface."""

    from .constants import Body
    from .planets import planet_at
    from .transits import (
        CrossingSearchClassification,
        CrossingSearchTruth,
        IngressComputationClassification,
        IngressComputationTruth,
        IngressEvent,
        TransitConditionProfile,
        TransitConditionState,
        TransitRelation,
        TransitRelationBasis,
        TransitRelationKind,
        TransitSearchKind,
        TransitWrapperKind,
        find_ingresses,
    )

    if type(event) is not IngressEvent:
        raise TypeError("event must be a moira.transits.IngressEvent")
    ingress_by_sign = {
        "Aries": CardinalIngress.ARIES,
        "Cancer": CardinalIngress.CANCER,
        "Libra": CardinalIngress.LIBRA,
        "Capricorn": CardinalIngress.CAPRICORN,
    }
    if (
        type(event.body) is not str
        or type(event.sign) is not str
        or type(event.direction) is not str
        or type(event.jd_ut) is not float
        or
        event.body != Body.SUN
        or event.direction != "direct"
        or event.sign not in ingress_by_sign
    ):
        return _unadmitted_anchor_issue(
            MundaneNotEvaluableReason.EVENT_SEMANTICS_MISMATCH,
            ("direct_solar_cardinal_ingress",),
            "The supplied transit event is not a direct solar cardinal ingress.",
        )
    if any(
        item is None
        for item in (
            event.computation_truth,
            event.classification,
            event.relation,
            event.condition_profile,
        )
    ):
        return _unadmitted_anchor_issue(
            MundaneNotEvaluableReason.SOURCE_RECEIPT_INCOMPLETE,
            ("complete_ingress_computation_truth",),
            "The ingress lacks preserved computation, classification, relation, or condition truth.",
        )
    truth = event.computation_truth
    if truth is None:  # Narrowing for static analyzers; handled above.
        raise RuntimeError("complete ingress truth invariant was not preserved")
    if (
        type(truth) is not IngressComputationTruth
        or type(event.classification) is not IngressComputationClassification
        or type(event.relation) is not TransitRelation
        or type(event.condition_profile) is not TransitConditionProfile
        or type(truth.search_truth) is not CrossingSearchTruth
        or type(event.classification.search) is not CrossingSearchClassification
        or type(truth.body) is not str
        or type(truth.sign) is not str
        or type(truth.boundary_longitude) is not float
        or type(event.classification.body) is not str
        or type(event.classification.sign) is not str
        or type(event.classification.search.search_kind) is not TransitSearchKind
        or type(event.classification.search.wrapper_kind) is not TransitWrapperKind
        or type(event.classification.search.uses_bisection) is not bool
        or type(event.classification.search.uses_dynamic_target) is not bool
        or type(event.relation.source_body) is not str
        or type(event.relation.relation_kind) is not TransitRelationKind
        or type(event.relation.basis) is not TransitRelationBasis
        or type(event.relation.target_name) is not str
        or type(event.relation.target_longitude) is not float
        or type(event.relation.is_dynamic_target) is not bool
        or type(event.condition_profile.source_body) is not str
        or type(event.condition_profile.wrapper_kind) is not TransitWrapperKind
        or type(event.condition_profile.search_kind) is not TransitSearchKind
        or type(event.condition_profile.relation_kind) is not TransitRelationKind
        or type(event.condition_profile.relation_basis) is not TransitRelationBasis
        or event.condition_profile.target_kind is not None
        or type(event.condition_profile.uses_dynamic_target) is not bool
        or type(event.condition_profile.condition_state) is not TransitConditionState
        or any(
            type(value) is not float
            for value in (
                truth.search_truth.search_start_jd_ut,
                truth.search_truth.search_end_jd_ut,
                truth.search_truth.step_days,
                truth.search_truth.bracket_start_jd_ut,
                truth.search_truth.bracket_end_jd_ut,
                truth.search_truth.crossing_jd_ut,
                truth.search_truth.solver_tolerance_days,
            )
        )
    ):
        raise TypeError("IngressEvent must contain exact concrete transit truth types")
    CrossingSearchTruth.__post_init__(truth.search_truth)
    IngressComputationTruth.__post_init__(truth)
    CrossingSearchClassification.__post_init__(event.classification.search)
    IngressComputationClassification.__post_init__(event.classification)
    TransitRelation.__post_init__(event.relation)
    TransitConditionProfile.__post_init__(event.condition_profile)
    IngressEvent.__post_init__(event)
    ingress = ingress_by_sign[event.sign]
    if (
        truth.body != Body.SUN
        or truth.sign != event.sign
        or truth.boundary_longitude != ingress.target_longitude_deg
        or truth.search_truth.crossing_jd_ut != event.jd_ut
        or event.classification.body != Body.SUN
        or event.classification.sign != event.sign
        or event.classification.search.search_kind is not TransitSearchKind.SIGN_INGRESS
        or event.classification.search.wrapper_kind is not TransitWrapperKind.INGRESS
        or event.classification.search.uses_bisection is not True
        or event.classification.search.uses_dynamic_target is not False
        or event.relation.source_body != Body.SUN
        or event.relation.relation_kind is not TransitRelationKind.SIGN_INGRESS
        or event.relation.basis is not TransitRelationBasis.SIGN_BOUNDARY
        or event.relation.target_name != event.sign
        or event.relation.target_longitude != ingress.target_longitude_deg
        or event.relation.is_dynamic_target is not False
        or event.condition_profile.source_body != Body.SUN
        or event.condition_profile.wrapper_kind is not TransitWrapperKind.INGRESS
        or event.condition_profile.search_kind is not TransitSearchKind.SIGN_INGRESS
        or event.condition_profile.relation_kind is not TransitRelationKind.SIGN_INGRESS
        or event.condition_profile.relation_basis is not TransitRelationBasis.SIGN_BOUNDARY
        or event.condition_profile.uses_dynamic_target is not False
        or event.condition_profile.condition_state is not TransitConditionState.BOUNDARY_EVENT
    ):
        raise ValueError("IngressEvent computation truth does not identify this cardinal root")
    search_span = (
        truth.search_truth.search_end_jd_ut
        - truth.search_truth.search_start_jd_ut
    )
    if search_span > _MAX_CARDINAL_INGRESS_CYCLE_DAYS:
        raise ValueError("cardinal ingress source search is limited to one cycle")
    recomputed_events = find_ingresses(
        Body.SUN,
        truth.search_truth.search_start_jd_ut,
        truth.search_truth.search_end_jd_ut,
        step_days=truth.search_truth.step_days,
        reader=reader,
    )
    exact_matches = tuple(
        candidate
        for candidate in recomputed_events
        if candidate.jd_ut == event.jd_ut
        and candidate.sign == event.sign
        and candidate.direction == event.direction
    )
    if len(exact_matches) != 1 or exact_matches[0] != event:
        raise ValueError(
            "IngressEvent must exactly match the reader-recomputed find_ingresses "
            "event and complete search history"
        )

    def residual_at(jd_ut1: float) -> float:
        longitude = planet_at(Body.SUN, jd_ut1, reader=reader).longitude
        return _signed_angle_delta(longitude, ingress.target_longitude_deg)

    search_receipt = _root_search_receipt_from_truth(
        truth.search_truth,
        reader=reader,
        residual_at=residual_at,
        search_kind="direct_solar_cardinal_ingress",
        solver_method_id="moira.transits.find_ingresses.bisection_v1",
        target_angle_deg=ingress.target_longitude_deg,
    )
    if (
        search_receipt.bracket_start_residual_deg > 0.0
        or search_receipt.bracket_end_residual_deg < 0.0
    ):
        raise ValueError("Solar cardinal root is not an increasing bracket crossing")
    sun = planet_at(Body.SUN, event.jd_ut, reader=reader)
    residual = _signed_angle_delta(sun.longitude, ingress.target_longitude_deg)
    provenance = _moira_event_provenance(
        reader,
        event.jd_ut,
        source_id="moira.transits.find_ingresses",
        method_id="reader_revalidated_direct_solar_cardinal_ingress_v1",
        provenance_family_id="moira_true_of_date_solar_lunar_events_v1",
        longitude_product_id=_MOIRA_SOLAR_APPARENT_LONGITUDE_PRODUCT,
        reference_frame=_MOIRA_TRUE_OF_DATE_REFERENCE_FRAME,
        correction_regime=_SUN_MOON_CORRECTION_REGIME,
        solver_semantics="moira_transit_ingress_bisection_preserved_search_truth_v1",
        source_refs=("moira.transits.find_ingresses", "moira.planets.planet_at"),
    )
    receipt = CardinalIngressReceipt(
        ingress=ingress,
        epoch=MundaneEpoch(event.jd_ut, MundaneTimescale.UT1),
        sun_longitude_deg=sun.longitude,
        root_residual_deg=residual,
        solver_tolerance_days=truth.search_truth.solver_tolerance_days,
        angular_root_tolerance=MundaneAngularRootToleranceReceipt(
            maximum_abs_residual_deg=_TRANSIT_ADAPTER_ROOT_TOLERANCE_DEG,
            basis="independent planet_at residual recheck at transit ingress root",
        ),
        provenance=provenance,
        clock=build_mundane_event_clock(event.jd_ut, reader=reader),
        search_truth=search_receipt,
    )
    return MundaneEventEvidence(
        status=MundaneEvaluationStatus.EVALUATED,
        receipt=receipt,
        issue=None,
    )


def assess_transit_primary_syzygy(
    anchor_event: CardinalIngressReceipt,
    *,
    reader: object,
    policy: object | None = None,
) -> PrecedingSyzygyEvidence:
    """Solve, revalidate, and select both exact phases preceding an ingress."""

    from .constants import Body
    from .planets import planet_at
    from .transits import (
        TransitComputationPolicy,
        _last_full_moon_search_truth,
        _last_new_moon_search_truth,
    )

    if type(anchor_event) is not CardinalIngressReceipt:
        raise TypeError("anchor_event must be a CardinalIngressReceipt")
    _revalidate_event_receipt(anchor_event)
    if policy is not None and type(policy) is not TransitComputationPolicy:
        raise TypeError("policy must be an exact TransitComputationPolicy or None")
    if (
        anchor_event.provenance.mode is not MundaneProvenanceMode.MOIRA_EPHEMERIS
        or anchor_event.epoch.timescale is not MundaneTimescale.UT1
        or anchor_event.clock is None
        or anchor_event.search_truth is None
    ):
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.SOURCE_RECEIPT_INCOMPLETE,
            ("reader_bound_moira_cardinal_ingress",),
            "Primary-syzygy adaptation requires a complete reader-bound Moira ingress.",
        )
    if _verified_reader_identity_at(reader, anchor_event.epoch.jd) != (
        anchor_event.provenance.verified_reader_identity
    ):
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.INCOMPATIBLE_KERNEL_IDENTITY,
            ("anchor_reader_identity",),
            "The supplied reader does not own the cardinal-ingress receipt.",
        )
    try:
        new_root, new_truth = _last_new_moon_search_truth(
            anchor_event.epoch.jd,
            reader,
            policy,
        )
        full_root, full_truth = _last_full_moon_search_truth(
            anchor_event.epoch.jd,
            reader,
            policy,
        )
    except RuntimeError as exc:
        return _preceding_syzygy_issue(
            MundaneNotEvaluableReason.GLOBAL_EVENT_UNAVAILABLE,
            ("preceding_new_and_full_moon_roots",),
            f"The transit phase search did not supply both candidates: {exc}",
        )

    def adapt_phase(
        phase: PrimarySyzygyPhase,
        root_jd: float,
        search_truth: object,
    ) -> PrimarySyzygyReceipt:
        target = 0.0 if phase is PrimarySyzygyPhase.NEW_MOON else 180.0

        def residual_at(jd_ut1: float) -> float:
            sun_at = planet_at(Body.SUN, jd_ut1, reader=reader)
            moon_at = planet_at(Body.MOON, jd_ut1, reader=reader)
            return _signed_angle_delta(
                moon_at.longitude - sun_at.longitude,
                target,
            )

        search_kind = (
            "preceding_new_moon"
            if phase is PrimarySyzygyPhase.NEW_MOON
            else "preceding_full_moon"
        )
        immutable_search = _root_search_receipt_from_truth(
            search_truth,
            reader=reader,
            residual_at=residual_at,
            search_kind=search_kind,
            solver_method_id="moira.transits.primary_syzygy_bisection_v1",
            target_angle_deg=target,
        )
        if type(root_jd) is not float or root_jd != immutable_search.root_epoch.jd:
            raise ValueError("phase helper root must exactly match its search truth")
        if immutable_search.search_interval.end.jd != anchor_event.epoch.jd:
            raise ValueError("phase search truth must retain the exact ingress anchor")
        if not root_jd < anchor_event.epoch.jd:
            raise ValueError("phase candidate must be strictly preceding")
        sun = planet_at(Body.SUN, root_jd, reader=reader)
        moon = planet_at(Body.MOON, root_jd, reader=reader)
        provenance = _moira_event_provenance(
            reader,
            root_jd,
            source_id="moira.transits.primary_syzygy_search_truth",
            method_id="reader_revalidated_preceding_new_and_full_moon_candidates_v1",
            provenance_family_id="moira_true_of_date_solar_lunar_events_v1",
            longitude_product_id=_PRIMARY_SYZYGY_LONGITUDE_PRODUCT,
            reference_frame=_MOIRA_TRUE_OF_DATE_REFERENCE_FRAME,
            correction_regime=_SUN_MOON_CORRECTION_REGIME,
            solver_semantics="moira_transit_phase_bisection_preserved_search_truth_v1",
            source_refs=(
                "moira.transits._last_new_moon_search_truth",
                "moira.transits._last_full_moon_search_truth",
                "moira.planets.planet_at",
            ),
        )
        return PrimarySyzygyReceipt(
            phase=phase,
            epoch=MundaneEpoch(root_jd, MundaneTimescale.UT1),
            sun_longitude_deg=sun.longitude,
            moon_longitude_deg=moon.longitude,
            root_residual_deg=_signed_angle_delta(
                moon.longitude - sun.longitude,
                target,
            ),
            solver_tolerance_days=immutable_search.solver_tolerance_days,
            angular_root_tolerance=MundaneAngularRootToleranceReceipt(
                maximum_abs_residual_deg=_TRANSIT_ADAPTER_ROOT_TOLERANCE_DEG,
                basis="independent planet_at residual recheck at phase root",
            ),
            provenance=provenance,
            clock=build_mundane_event_clock(root_jd, reader=reader),
            search_truth=immutable_search,
        )

    candidates = (
        adapt_phase(PrimarySyzygyPhase.NEW_MOON, new_root, new_truth),
        adapt_phase(PrimarySyzygyPhase.FULL_MOON, full_root, full_truth),
    )
    return select_strictly_preceding_primary_syzygy(anchor_event, candidates)


def _moira_event_provenance(
    reader: object,
    jd_ut1: float,
    *,
    source_id: str,
    method_id: str,
    provenance_family_id: str,
    longitude_product_id: str,
    reference_frame: str,
    correction_regime: str,
    solver_semantics: str,
    source_refs: tuple[str, ...],
    required_routes: tuple[tuple[int, int], ...] = _MUNDANE_CLOCK_ROUTES,
) -> MundaneEventProvenance:
    """Build engine provenance from the reader's content-derived SPK label."""

    identity = _verified_reader_identity_at(
        reader,
        jd_ut1,
        required_routes=required_routes,
    )
    return MundaneEventProvenance(
        mode=MundaneProvenanceMode.MOIRA_EPHEMERIS,
        source_id=source_id,
        method_id=method_id,
        provenance_family_id=provenance_family_id,
        longitude_product_id=longitude_product_id,
        reference_frame=reference_frame,
        correction_regime=correction_regime,
        solver_semantics=solver_semantics,
        source_refs=source_refs,
        verified_reader_identity=identity,
        _engine_provenance_token=_MOIRA_PROVENANCE_TOKEN,
    )


def eclipse_receipt_from_event(
    event: object,
    *,
    eclipse_id: str,
    reader: object,
) -> EclipseEventReceipt:
    """Revalidate and adapt one reader-bound Moira greatest-eclipse event."""

    from .eclipse import EclipseCalculator, EclipseData, EclipseEvent, EclipseType

    if type(event) is not EclipseEvent:
        raise TypeError("event must be a moira.eclipse.EclipseEvent")
    if type(event.jd_ut) is not float or type(event.data) is not EclipseData:
        raise TypeError("EclipseEvent must retain exact engine epoch and data types")
    if type(event.data.eclipse_type) is not EclipseType:
        raise TypeError("EclipseEvent classification must be an exact EclipseType")
    if any(
        type(value) is not bool
        for value in (
            event.data.is_eclipse_season,
            event.data.is_solar_eclipse,
            event.data.is_lunar_eclipse,
            event.data.metonic_is_reset,
        )
    ):
        raise TypeError("EclipseEvent status fields must be exact built-in booleans")
    _trimmed("eclipse_id", eclipse_id)
    if event.data.is_solar_eclipse == event.data.is_lunar_eclipse:
        raise ValueError("EclipseEvent must identify exactly one solar or lunar family")
    calculator = EclipseCalculator(reader=reader)
    recomputed = calculator.calculate_jd(event.jd_ut)
    for field_name in EclipseData.__dataclass_fields__:
        if type(getattr(event.data, field_name)) is not type(
            getattr(recomputed, field_name)
        ):
            raise TypeError(
                "EclipseEvent data must retain exact engine scalar and receipt types"
            )
    for field_name in EclipseType.__dataclass_fields__:
        if type(getattr(event.data.eclipse_type, field_name)) is not type(
            getattr(recomputed.eclipse_type, field_name)
        ):
            raise TypeError(
                "EclipseEvent classification must retain exact engine scalar types"
            )
    if recomputed != event.data:
        raise ValueError(
            "EclipseEvent geometry is not bound to the supplied ephemeris reader"
        )
    eclipse_kind = (
        EclipseKind.SOLAR if event.data.is_solar_eclipse else EclipseKind.LUNAR
    )
    searched = (
        calculator.next_solar_eclipse(event.jd_ut - 2.0)
        if eclipse_kind is EclipseKind.SOLAR
        else calculator.next_lunar_eclipse(event.jd_ut - 2.0)
    )
    if (
        abs(searched.jd_ut - event.jd_ut)
        > _ECLIPSE_GREATEST_RECHECK_TOLERANCE_DAYS
    ):
        raise ValueError(
            "EclipseEvent is not the reader-recomputed greatest-eclipse event: "
            f"supplied_jd={event.jd_ut!r}, searched_jd={searched.jd_ut!r}, "
            "tolerance_seconds=0.1"
        )
    provenance = _moira_event_provenance(
        reader,
        event.jd_ut,
        source_id="moira.eclipse.EclipseCalculator",
        method_id="revalidated_eclipse_event_greatest_epoch_v1",
        provenance_family_id="moira_eclipse_event_greatest_v1",
        longitude_product_id="not_applicable_to_greatest_eclipse_epoch",
        reference_frame=_ECLIPSE_REFERENCE_FRAME,
        correction_regime=(
            _SOLAR_ECLIPSE_CORRECTION_REGIME
            if eclipse_kind is EclipseKind.SOLAR
            else _LUNAR_ECLIPSE_CORRECTION_REGIME
        ),
        solver_semantics="moira_eclipse_greatest_epoch_revalidation_v1",
        source_refs=("moira.eclipse.EclipseCalculator", "moira.eclipse.EclipseEvent"),
    )
    greatest = EclipseNamedEpochReceipt(
        eclipse_id=eclipse_id,
        eclipse_kind=eclipse_kind,
        epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
        epoch=MundaneEpoch(event.jd_ut, MundaneTimescale.UT1),
        provenance=provenance,
    )
    return EclipseEventReceipt(
        eclipse_id=eclipse_id,
        eclipse_kind=eclipse_kind,
        anchor_epoch_kind=EclipseAnchorEpoch.GREATEST_ECLIPSE,
        provenance=provenance,
        named_epochs=(greatest,),
        clock=build_mundane_event_clock(event.jd_ut, reader=reader),
    )


def _motion_state_from_longitudes(
    before_deg: float,
    after_deg: float,
) -> MundaneMotionState:
    delta = _signed_angle_delta(after_deg, before_deg)
    if delta > 0.0:
        return MundaneMotionState.DIRECT
    if delta < 0.0:
        return MundaneMotionState.RETROGRADE
    return MundaneMotionState.STATIONARY


def jupiter_saturn_sequence_from_series(
    series: object,
    *,
    reader: object,
) -> JupiterSaturnConjunctionSequenceReceipt:
    """Adapt one existing Moira conjunction search without mutation doctrine."""

    from .constants import Body
    from .cycles import GreatConjunction, GreatConjunctionSeries, great_conjunctions
    from .planets import planet_at

    if type(series) is not GreatConjunctionSeries:
        raise TypeError("series must be a moira.cycles.GreatConjunctionSeries")
    if (
        type(series.jd_start) not in (int, float)
        or type(series.jd_end) not in (int, float)
    ):
        raise TypeError("GreatConjunctionSeries interval must use finite built-in floats")
    jd_start = _as_builtin_float("GreatConjunctionSeries jd_start", series.jd_start)
    jd_end = _as_builtin_float("GreatConjunctionSeries jd_end", series.jd_end)
    recomputed_series = great_conjunctions(
        jd_start,
        jd_end,
        reader=reader,
    )
    if type(series.conjunctions) is not tuple or any(
        type(item) is not GreatConjunction for item in series.conjunctions
    ):
        raise TypeError(
            "GreatConjunctionSeries roots must be an immutable tuple of exact roots"
        )
    if any(
        type(value) is not float or not math.isfinite(value)
        for item in series.conjunctions
        for value in (item.jd_ut, item.longitude)
    ):
        raise TypeError(
            "GreatConjunctionSeries astronomical roots must use finite built-in floats"
        )
    supplied_roots = tuple(
        (item.jd_ut, item.longitude) for item in series.conjunctions
    )
    recomputed_roots = tuple(
        (item.jd_ut, item.longitude) for item in recomputed_series.conjunctions
    )
    if supplied_roots != recomputed_roots:
        raise ValueError(
            "GreatConjunctionSeries must exactly match the reader-recomputed "
            "complete search result's astronomical root set"
        )
    if (
        type(series.count) is not int
        or series.count != len(series.conjunctions)
        or series.count != recomputed_series.count
    ):
        raise ValueError("GreatConjunctionSeries count does not match its roots")
    if not recomputed_series.conjunctions:
        raise ValueError("GreatConjunctionSeries contains no roots to adapt")
    provenance = _moira_event_provenance(
        reader,
        recomputed_series.conjunctions[0].jd_ut,
        source_id="moira.cycles.great_conjunctions",
        method_id="revalidated_jupiter_saturn_ecliptic_longitude_roots_v1",
        provenance_family_id="moira_jupiter_saturn_ecliptic_longitude_v1",
        longitude_product_id=_JUPITER_SATURN_LONGITUDE_PRODUCT,
        reference_frame=_JUPITER_SATURN_REFERENCE_FRAME,
        correction_regime=_JUPITER_SATURN_CORRECTION_REGIME,
        solver_semantics=_JUPITER_SATURN_SOLVER_SEMANTICS,
        source_refs=("moira.cycles.great_conjunctions", "moira.planets.planet_at"),
        required_routes=_MUNDANE_JUPITER_SATURN_ROUTES,
    )
    interval = MundaneSearchInterval(
        start=MundaneEpoch(jd_start, MundaneTimescale.UT1),
        end=MundaneEpoch(jd_end, MundaneTimescale.UT1),
    )
    for endpoint in (
        jd_start,
        math.nextafter(jd_end, jd_start),
    ):
        if _verified_reader_identity_at(
            reader,
            endpoint,
            required_routes=_MUNDANE_JUPITER_SATURN_ROUTES,
        ) != (
            provenance.verified_reader_identity
        ):
            raise ValueError(
                "Jupiter-Saturn search interval crosses a reader-identity boundary"
            )
    motion_step_days = 60.0 / 86400.0
    roots = []
    for event in recomputed_series.conjunctions:
        if _verified_reader_identity_at(
            reader,
            event.jd_ut,
            required_routes=_MUNDANE_JUPITER_SATURN_ROUTES,
        ) != (
            provenance.verified_reader_identity
        ):
            raise ValueError(
                "Jupiter-Saturn search crosses a reader-identity boundary"
            )
        jupiter = planet_at(Body.JUPITER, event.jd_ut, reader=reader, apparent=True)
        saturn = planet_at(Body.SATURN, event.jd_ut, reader=reader, apparent=True)
        if abs(_signed_angle_delta(jupiter.longitude, event.longitude)) > 1e-9:
            raise ValueError("GreatConjunction longitude is not the Jupiter root longitude")
        jupiter_before = planet_at(
            Body.JUPITER,
            event.jd_ut - motion_step_days,
            reader=reader,
            apparent=True,
        )
        jupiter_after = planet_at(
            Body.JUPITER,
            event.jd_ut + motion_step_days,
            reader=reader,
            apparent=True,
        )
        saturn_before = planet_at(
            Body.SATURN,
            event.jd_ut - motion_step_days,
            reader=reader,
            apparent=True,
        )
        saturn_after = planet_at(
            Body.SATURN,
            event.jd_ut + motion_step_days,
            reader=reader,
            apparent=True,
        )
        roots.append(
            JupiterSaturnConjunctionReceipt(
                event_id=f"moira_jupiter_saturn_{event.jd_ut:.12f}_ut1",
                epoch=MundaneEpoch(event.jd_ut, MundaneTimescale.UT1),
                jupiter_longitude_deg=jupiter.longitude,
                saturn_longitude_deg=saturn.longitude,
                root_residual_deg=_signed_angle_delta(
                    jupiter.longitude, saturn.longitude
                ),
                jupiter_motion=_motion_state_from_longitudes(
                    jupiter_before.longitude, jupiter_after.longitude
                ),
                saturn_motion=_motion_state_from_longitudes(
                    saturn_before.longitude, saturn_after.longitude
                ),
                solver_tolerance_days=1e-8,
                angular_root_tolerance=MundaneAngularRootToleranceReceipt(
                    maximum_abs_residual_deg=(
                        _JUPITER_SATURN_ADAPTER_ROOT_TOLERANCE_DEG
                    ),
                    basis="independent planet_at residual recheck at adapted root",
                ),
                provenance=provenance,
                clock=build_mundane_event_clock(event.jd_ut, reader=reader),
            )
        )
    return JupiterSaturnConjunctionSequenceReceipt(
        search_interval=interval,
        roots=tuple(roots),
    )
