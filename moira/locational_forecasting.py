"""Geometry-only composition for relocated returns and dynamic ACG snapshots.

This module owns no return solver, house algorithm, ephemeris reduction, map
projection, ranking, or interpretation.  It composes the canonical return
timing functions with :func:`moira.chart.create_chart` and
:func:`moira.chart.relocated_chart`, and composes explicit transiting epochs
with :func:`moira.astrocartography.acg_lines`.

Progressed and directed cyclocartography remain outside this bounded contract
until their advancement and equatorial-frame policies are source-owned.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ._ephemeris_time import _ut1_to_ephemeris_tt
from ._strenum import StrEnum
from .astrocartography import ACGLine, acg_lines
from .chart import ChartContext, create_chart, relocated_chart
from .constants import Body, HouseSystem
from .houses import HousePolicy
from .julian import apparent_sidereal_time
from .obliquity import nutation, true_obliquity
from .planets import sky_position_at
from .spk_reader import SpkReader, get_reader
from .transits import (
    TransitComputationPolicy,
    lunar_return,
    planet_return,
    solar_return,
)

__all__ = [
    "ReturnKind",
    "ReturnSearchPolicyTruth",
    "ReturnMomentTruth",
    "ReturnRelocationTruth",
    "RelocatedReturnChart",
    "DynamicAstrocartographyMode",
    "DynamicAstrocartographyPosition",
    "DynamicAstrocartographySnapshotTruth",
    "DynamicAstrocartographySnapshot",
    "AstrocartographyCurvePointShift",
    "DynamicAstrocartographyLineTransition",
    "DynamicAstrocartographySeriesTruth",
    "DynamicAstrocartographySeries",
    "relocated_solar_return",
    "relocated_lunar_return",
    "relocated_planetary_return",
    "transiting_astrocartography",
]


_ECLIPTIC_FRAME = "apparent_geocentric_true_ecliptic_of_date"
_EQUATORIAL_FRAME = "apparent_equatorial_true_equinox_of_date"
_TIMESCALE = "UT1_input_with_internal_TT_ephemeris"
_MAX_DYNAMIC_EPOCHS = 128


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _require_return_inputs(
    natal_longitude: float,
    source_latitude: float,
    source_longitude: float,
    relocated_latitude: float,
    relocated_longitude: float,
) -> None:
    values = (
        natal_longitude,
        source_latitude,
        source_longitude,
        relocated_latitude,
        relocated_longitude,
    )
    if not all(_is_finite_number(value) for value in values):
        raise ValueError("relocated return longitudes and coordinates must be finite numbers")
    if not -90.0 <= source_latitude <= 90.0 or not -90.0 <= relocated_latitude <= 90.0:
        raise ValueError("relocated return latitudes must lie in [-90, 90]")
    if not -180.0 <= source_longitude <= 180.0 or not -180.0 <= relocated_longitude <= 180.0:
        raise ValueError("relocated return longitudes must lie in [-180, 180]")


class ReturnKind(StrEnum):
    """Return timing families admitted by the relocation composer."""

    SOLAR = "solar_return"
    LUNAR = "lunar_return"
    PLANETARY = "planetary_return"


@dataclass(frozen=True, slots=True)
class ReturnSearchPolicyTruth:
    """Complete return-search policy preserved even when the solver returns a scalar."""

    step_days_override: float | None
    default_max_days: float | None
    per_body_max_days: tuple[tuple[str, float], ...]
    solver_tolerance_days: float
    policy_source: str

    def __post_init__(self) -> None:
        try:
            normalized_windows = tuple(
                (body, max_days)
                for body, max_days in self.per_body_max_days
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "return per-body policy must contain (body, max_days) pairs"
            ) from exc
        object.__setattr__(self, "per_body_max_days", normalized_windows)
        if self.step_days_override is not None and (
            not _is_finite_number(self.step_days_override)
            or self.step_days_override <= 0.0
        ):
            raise ValueError("return step override must be positive and finite")
        if self.default_max_days is not None and (
            not _is_finite_number(self.default_max_days)
            or self.default_max_days <= 0.0
        ):
            raise ValueError("return default search window must be positive and finite")
        bodies: set[str] = set()
        for body, max_days in self.per_body_max_days:
            if not isinstance(body, str) or not body:
                raise ValueError("return per-body policy names must not be empty")
            if body in bodies:
                raise ValueError("return per-body policy names must be unique")
            if not _is_finite_number(max_days) or max_days <= 0.0:
                raise ValueError("return per-body search windows must be positive and finite")
            bodies.add(body)
        if (
            not _is_finite_number(self.solver_tolerance_days)
            or self.solver_tolerance_days <= 0.0
        ):
            raise ValueError("return solver tolerance must be positive and finite")
        if self.policy_source not in {"default", "caller_supplied"}:
            raise ValueError("return policy source is invalid")


@dataclass(frozen=True, slots=True)
class ReturnMomentTruth:
    """Exact return moment and the canonical timing authority that found it."""

    return_kind: ReturnKind
    body: str
    natal_longitude: float
    jd_return_ut: float
    direction: str
    timing_source: str
    search_policy: ReturnSearchPolicyTruth
    year: int | None = None
    search_start_jd_ut: float | None = None
    reference_frame: str = _ECLIPTIC_FRAME
    timescale: str = _TIMESCALE

    def __post_init__(self) -> None:
        object.__setattr__(self, "return_kind", ReturnKind(self.return_kind))
        if not self.body or not self.timing_source:
            raise ValueError("return moment body and timing_source must not be empty")
        if not isinstance(self.search_policy, ReturnSearchPolicyTruth):
            raise TypeError("return moment search_policy must be ReturnSearchPolicyTruth")
        if not math.isfinite(self.natal_longitude) or not math.isfinite(self.jd_return_ut):
            raise ValueError("return moment longitudes and epochs must be finite")
        object.__setattr__(self, "natal_longitude", self.natal_longitude % 360.0)
        if self.search_start_jd_ut is not None and not math.isfinite(self.search_start_jd_ut):
            raise ValueError("return search_start_jd_ut must be finite when supplied")
        if self.direction not in {"direct", "retrograde", "either"}:
            raise ValueError("return direction must be direct, retrograde, or either")
        if self.return_kind is ReturnKind.SOLAR:
            if self.body != Body.SUN or self.year is None or self.search_start_jd_ut is not None:
                raise ValueError("solar return truth requires Sun and year only")
            if self.direction != "direct" or self.timing_source != "moira.transits.solar_return":
                raise ValueError("solar return truth must preserve solar_return direct timing")
        elif self.return_kind is ReturnKind.LUNAR:
            if self.body != Body.MOON or self.year is not None or self.search_start_jd_ut is None:
                raise ValueError("lunar return truth requires Moon and a search start")
            if self.direction != "direct" or self.timing_source != "moira.transits.lunar_return":
                raise ValueError("lunar return truth must preserve lunar_return direct timing")
        else:
            if self.body not in Body.ALL_PLANETS:
                raise ValueError("planetary return truth requires an admitted planet")
            if self.year is not None or self.search_start_jd_ut is None:
                raise ValueError("planetary return truth requires a search start and no year")
            if self.timing_source != "moira.transits.planet_return":
                raise ValueError("planetary return truth must preserve planet_return timing")


@dataclass(frozen=True, slots=True)
class ReturnRelocationTruth:
    """Explicit source/target house-frame receipt for one relocated return."""

    source_latitude: float
    source_longitude: float
    relocated_latitude: float
    relocated_longitude: float
    source_requested_house_system: str
    source_effective_house_system: str
    source_house_fallback: bool
    relocated_requested_house_system: str
    relocated_effective_house_system: str
    relocated_house_fallback: bool
    same_epoch: bool = True
    same_celestial_snapshot: bool = True
    chart_source: str = "moira.chart.create_chart"
    relocation_source: str = "moira.chart.relocated_chart"
    interpretation: str = "none_geometry_only"

    def __post_init__(self) -> None:
        coordinates = (
            self.source_latitude,
            self.source_longitude,
            self.relocated_latitude,
            self.relocated_longitude,
        )
        if not all(math.isfinite(value) for value in coordinates):
            raise ValueError("return relocation coordinates must be finite")
        if not -90.0 <= self.source_latitude <= 90.0 or not -90.0 <= self.relocated_latitude <= 90.0:
            raise ValueError("return relocation latitudes must lie in [-90, 90]")
        if not -180.0 <= self.source_longitude <= 180.0 or not -180.0 <= self.relocated_longitude <= 180.0:
            raise ValueError("return relocation longitudes must lie in [-180, 180]")
        systems = (
            self.source_requested_house_system,
            self.source_effective_house_system,
            self.relocated_requested_house_system,
            self.relocated_effective_house_system,
        )
        if not all(isinstance(value, str) and value for value in systems):
            raise ValueError("return relocation house-system identities must not be empty")
        if self.source_house_fallback != (
            self.source_requested_house_system != self.source_effective_house_system
        ):
            raise ValueError("source return house fallback must match requested/effective systems")
        if self.relocated_house_fallback != (
            self.relocated_requested_house_system != self.relocated_effective_house_system
        ):
            raise ValueError("relocated return house fallback must match requested/effective systems")
        if not self.same_epoch or not self.same_celestial_snapshot:
            raise ValueError("relocated return composition must preserve epoch and celestial snapshot")


@dataclass(frozen=True, slots=True)
class RelocatedReturnChart:
    """One exact return chart recast at a second geographic location."""

    source_chart: ChartContext
    relocated_chart: ChartContext
    return_truth: ReturnMomentTruth
    relocation_truth: ReturnRelocationTruth

    def __post_init__(self) -> None:
        source = self.source_chart
        relocated = self.relocated_chart
        if not isinstance(source, ChartContext) or not isinstance(relocated, ChartContext):
            raise TypeError("relocated return charts must be ChartContext vessels")
        if source.jd_ut != self.return_truth.jd_return_ut:
            raise ValueError("source return chart epoch must match return truth")
        if source.jd_ut != relocated.jd_ut or source.jd_tt != relocated.jd_tt:
            raise ValueError("relocated return must preserve the source epoch")
        if dict(source.planets) != dict(relocated.planets) or dict(source.nodes) != dict(relocated.nodes):
            raise ValueError("relocated return must preserve planet and node snapshots")
        truth = self.relocation_truth
        if (source.latitude, source.longitude) != (truth.source_latitude, truth.source_longitude):
            raise ValueError("source return chart coordinates must match relocation truth")
        if (relocated.latitude, relocated.longitude) != (
            truth.relocated_latitude,
            truth.relocated_longitude,
        ):
            raise ValueError("relocated return chart coordinates must match relocation truth")
        if source.houses is None or relocated.houses is None:
            raise ValueError("relocated return composition requires both local house frames")
        if source.houses.system != truth.source_requested_house_system:
            raise ValueError("source return house system must match relocation truth")
        if source.houses.effective_system != truth.source_effective_house_system:
            raise ValueError("source return effective house system must match relocation truth")
        if relocated.houses.system != truth.relocated_requested_house_system:
            raise ValueError("relocated return house system must match relocation truth")
        if relocated.houses.effective_system != truth.relocated_effective_house_system:
            raise ValueError("relocated return effective house system must match relocation truth")


class DynamicAstrocartographyMode(StrEnum):
    """Dynamic line modes admitted by this bounded surface."""

    TRANSIT = "transit"


@dataclass(frozen=True, slots=True)
class DynamicAstrocartographyPosition:
    """One body's apparent equatorial position used by an ACG snapshot."""

    body: str
    right_ascension: float
    declination: float
    position_source: str = "moira.planets.sky_position_at:apparent_topocentric"

    def __post_init__(self) -> None:
        if not self.body or not self.position_source:
            raise ValueError("dynamic ACG position identity must not be empty")
        if not math.isfinite(self.right_ascension) or not math.isfinite(self.declination):
            raise ValueError("dynamic ACG position coordinates must be finite")
        object.__setattr__(self, "right_ascension", self.right_ascension % 360.0)
        if not -90.0 <= self.declination <= 90.0:
            raise ValueError("dynamic ACG declination must lie in [-90, 90]")


@dataclass(frozen=True, slots=True)
class DynamicAstrocartographySnapshotTruth:
    """Clock, observer, and frame receipt for one transiting ACG snapshot."""

    jd_ut: float
    jd_tt: float
    bodies: tuple[str, ...]
    observer_latitude: float
    observer_longitude: float
    observer_elevation_m: float
    apparent_sidereal_time_deg: float
    true_obliquity_deg: float
    nutation_longitude_deg: float
    lat_step: float
    refraction: bool
    mode: DynamicAstrocartographyMode = DynamicAstrocartographyMode.TRANSIT
    coordinate_frame: str = _EQUATORIAL_FRAME
    timescale: str = _TIMESCALE
    line_geometry_source: str = "moira.astrocartography.acg_lines"
    interpretation: str = "none_geometry_only"

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", DynamicAstrocartographyMode(self.mode))
        values = (
            self.jd_ut,
            self.jd_tt,
            self.observer_latitude,
            self.observer_longitude,
            self.observer_elevation_m,
            self.apparent_sidereal_time_deg,
            self.true_obliquity_deg,
            self.nutation_longitude_deg,
            self.lat_step,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("dynamic ACG snapshot truth values must be finite")
        if not self.bodies or len(set(self.bodies)) != len(self.bodies):
            raise ValueError("dynamic ACG snapshot bodies must be non-empty and unique")
        if not -90.0 <= self.observer_latitude <= 90.0:
            raise ValueError("dynamic ACG observer latitude must lie in [-90, 90]")
        if not -180.0 <= self.observer_longitude <= 180.0:
            raise ValueError("dynamic ACG observer longitude must lie in [-180, 180]")
        if self.lat_step <= 0.0 or self.lat_step > 178.0:
            raise ValueError("dynamic ACG lat_step must lie in (0, 178]")
        if not isinstance(self.refraction, bool):
            raise ValueError("dynamic ACG refraction must be bool")


@dataclass(frozen=True, slots=True)
class DynamicAstrocartographySnapshot:
    """One explicit-epoch transiting ACG line figure."""

    positions: tuple[DynamicAstrocartographyPosition, ...]
    lines: tuple[ACGLine, ...]
    computation_truth: DynamicAstrocartographySnapshotTruth

    def __post_init__(self) -> None:
        bodies = tuple(position.body for position in self.positions)
        if bodies != self.computation_truth.bodies:
            raise ValueError("dynamic ACG positions must match snapshot truth bodies")
        expected_line_keys = {
            (body, line_type)
            for body in bodies
            for line_type in ("MC", "IC", "ASC", "DSC")
        }
        line_keys = [(line.planet, line.line_type) for line in self.lines]
        if len(line_keys) != len(expected_line_keys) or set(line_keys) != expected_line_keys:
            raise ValueError(
                "dynamic ACG snapshot must contain exactly one MC/IC/ASC/DSC line per body"
            )

    @property
    def jd_ut(self) -> float:
        return self.computation_truth.jd_ut


@dataclass(frozen=True, slots=True)
class AstrocartographyCurvePointShift:
    """Signed shortest-longitude displacement for one shared latitude sample."""

    latitude: float
    source_longitude: float
    target_longitude: float
    signed_delta_deg: float

    def __post_init__(self) -> None:
        if not all(
            math.isfinite(value)
            for value in (
                self.latitude,
                self.source_longitude,
                self.target_longitude,
                self.signed_delta_deg,
            )
        ):
            raise ValueError("dynamic ACG curve shift values must be finite")
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("dynamic ACG curve shift latitude must lie in [-90, 90]")
        expected = _signed_longitude_delta(self.source_longitude, self.target_longitude)
        if abs(expected - self.signed_delta_deg) > 1e-9:
            raise ValueError("dynamic ACG curve shift delta must match its longitudes")


@dataclass(frozen=True, slots=True)
class DynamicAstrocartographyLineTransition:
    """Geometry-only displacement of one ACG line between adjacent epochs."""

    body: str
    line_type: str
    source_jd_ut: float
    target_jd_ut: float
    source_meridian_longitude: float | None
    target_meridian_longitude: float | None
    meridian_signed_delta_deg: float | None
    curve_point_shifts: tuple[AstrocartographyCurvePointShift, ...]
    source_only_latitudes: tuple[float, ...]
    target_only_latitudes: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.body or self.line_type not in {"MC", "IC", "ASC", "DSC"}:
            raise ValueError("dynamic ACG transition identity is invalid")
        if not math.isfinite(self.source_jd_ut) or not math.isfinite(self.target_jd_ut):
            raise ValueError("dynamic ACG transition epochs must be finite")
        if self.target_jd_ut <= self.source_jd_ut:
            raise ValueError("dynamic ACG transition epochs must increase")
        if self.line_type in {"MC", "IC"}:
            if (
                self.source_meridian_longitude is None
                or self.target_meridian_longitude is None
                or self.meridian_signed_delta_deg is None
                or self.curve_point_shifts
            ):
                raise ValueError(
                    "dynamic ACG meridian transition requires longitudes and delta"
                )
            if self.source_only_latitudes or self.target_only_latitudes:
                raise ValueError("dynamic ACG meridian transition cannot carry curve latitude gaps")
            expected = _signed_longitude_delta(
                self.source_meridian_longitude,
                self.target_meridian_longitude,
            )
            if abs(expected - self.meridian_signed_delta_deg) > 1e-9:
                raise ValueError("dynamic ACG meridian delta must match its longitudes")
        elif (
            self.source_meridian_longitude is not None
            or self.target_meridian_longitude is not None
            or self.meridian_signed_delta_deg is not None
        ):
            raise ValueError("dynamic ACG curve transition cannot carry meridian fields")


@dataclass(frozen=True, slots=True)
class DynamicAstrocartographySeriesTruth:
    """Bounded explicit-epoch policy for one transiting ACG series."""

    mode: DynamicAstrocartographyMode
    epochs_jd_ut: tuple[float, ...]
    bodies: tuple[str, ...]
    snapshot_count: int
    transition_count: int
    epoch_policy: str = "caller_supplied_strictly_increasing"
    comparison_policy: str = "adjacent_exact_line_displacements_no_scores"
    progressed_mode: str = "not_admitted"
    directed_mode: str = "not_admitted"
    interpretation: str = "none_geometry_only"

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", DynamicAstrocartographyMode(self.mode))
        if len(self.epochs_jd_ut) < 1 or len(self.epochs_jd_ut) > _MAX_DYNAMIC_EPOCHS:
            raise ValueError("dynamic ACG series epoch count is outside the admitted bound")
        if any(not math.isfinite(value) for value in self.epochs_jd_ut):
            raise ValueError("dynamic ACG series epochs must be finite")
        if any(
            later <= earlier
            for earlier, later in zip(self.epochs_jd_ut, self.epochs_jd_ut[1:])
        ):
            raise ValueError("dynamic ACG series epochs must be strictly increasing")
        if not self.bodies or len(set(self.bodies)) != len(self.bodies):
            raise ValueError("dynamic ACG series bodies must be non-empty and unique")
        if self.snapshot_count != len(self.epochs_jd_ut):
            raise ValueError("dynamic ACG snapshot_count must match epochs")
        expected_transitions = max(0, len(self.epochs_jd_ut) - 1) * len(self.bodies) * 4
        if self.transition_count != expected_transitions:
            raise ValueError("dynamic ACG transition_count must match adjacent line pairs")


@dataclass(frozen=True, slots=True)
class DynamicAstrocartographySeries:
    """Transiting ACG snapshots plus exact adjacent-epoch line displacements."""

    snapshots: tuple[DynamicAstrocartographySnapshot, ...]
    transitions: tuple[DynamicAstrocartographyLineTransition, ...]
    computation_truth: DynamicAstrocartographySeriesTruth

    def __post_init__(self) -> None:
        if tuple(snapshot.jd_ut for snapshot in self.snapshots) != self.computation_truth.epochs_jd_ut:
            raise ValueError("dynamic ACG snapshots must match series epochs")
        if len(self.transitions) != self.computation_truth.transition_count:
            raise ValueError("dynamic ACG transitions must match series truth")
        if any(
            snapshot.computation_truth.bodies != self.computation_truth.bodies
            or snapshot.computation_truth.mode != self.computation_truth.mode
            for snapshot in self.snapshots
        ):
            raise ValueError("dynamic ACG snapshots must share series bodies and mode")
        expected_transitions = tuple(
            (body, line_type, source_jd_ut, target_jd_ut)
            for source_jd_ut, target_jd_ut in zip(
                self.computation_truth.epochs_jd_ut,
                self.computation_truth.epochs_jd_ut[1:],
            )
            for body in self.computation_truth.bodies
            for line_type in ("MC", "IC", "ASC", "DSC")
        )
        actual_transitions = tuple(
            (
                transition.body,
                transition.line_type,
                transition.source_jd_ut,
                transition.target_jd_ut,
            )
            for transition in self.transitions
        )
        if actual_transitions != expected_transitions:
            raise ValueError(
                "dynamic ACG transitions must exactly cover adjacent series line pairs"
            )


def _effective_house_system(chart: ChartContext) -> str:
    if chart.houses is None:
        raise ValueError("return chart is missing its local house frame")
    return chart.houses.effective_system or chart.houses.system


def _return_search_policy_truth(
    policy: TransitComputationPolicy | None,
) -> ReturnSearchPolicyTruth:
    resolved = policy or TransitComputationPolicy()
    returns = resolved.returns
    return ReturnSearchPolicyTruth(
        step_days_override=returns.step_days_override,
        default_max_days=returns.default_max_days,
        per_body_max_days=tuple(returns.per_body_max_days),
        solver_tolerance_days=returns.solver_tolerance_days,
        policy_source=("caller_supplied" if policy is not None else "default"),
    )


def _compose_relocated_return(
    return_truth: ReturnMomentTruth,
    *,
    source_latitude: float,
    source_longitude: float,
    relocated_latitude: float,
    relocated_longitude: float,
    source_house_system: str,
    relocated_house_system: str | None,
    bodies: list[str] | None,
    reader: SpkReader | None,
    house_policy: HousePolicy | None,
) -> RelocatedReturnChart:
    source = create_chart(
        return_truth.jd_return_ut,
        source_latitude,
        source_longitude,
        house_system=source_house_system,
        bodies=bodies,
        reader=reader,
        policy=house_policy,
    )
    relocated = relocated_chart(
        source,
        relocated_latitude,
        relocated_longitude,
        house_system=relocated_house_system,
        policy=house_policy,
    )
    if source.houses is None or relocated.houses is None:
        raise ValueError("return relocation requires source and relocated house frames")
    truth = ReturnRelocationTruth(
        source_latitude=source_latitude,
        source_longitude=source_longitude,
        relocated_latitude=relocated_latitude,
        relocated_longitude=relocated_longitude,
        source_requested_house_system=source.houses.system,
        source_effective_house_system=_effective_house_system(source),
        source_house_fallback=source.houses.fallback,
        relocated_requested_house_system=relocated.houses.system,
        relocated_effective_house_system=_effective_house_system(relocated),
        relocated_house_fallback=relocated.houses.fallback,
    )
    return RelocatedReturnChart(
        source_chart=source,
        relocated_chart=relocated,
        return_truth=return_truth,
        relocation_truth=truth,
    )


def relocated_solar_return(
    natal_sun_longitude: float,
    year: int,
    source_latitude: float,
    source_longitude: float,
    relocated_latitude: float,
    relocated_longitude: float,
    *,
    source_house_system: str = HouseSystem.PLACIDUS,
    relocated_house_system: str | None = None,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    return_policy: TransitComputationPolicy | None = None,
    house_policy: HousePolicy | None = None,
) -> RelocatedReturnChart:
    """Cast one exact solar return at a source and relocated house frame."""

    _require_return_inputs(
        natal_sun_longitude,
        source_latitude,
        source_longitude,
        relocated_latitude,
        relocated_longitude,
    )
    if isinstance(year, bool) or not isinstance(year, int):
        raise ValueError("relocated solar return year must be an integer")
    jd_return = solar_return(
        natal_sun_longitude,
        year,
        reader=reader,
        policy=return_policy,
    )
    truth = ReturnMomentTruth(
        return_kind=ReturnKind.SOLAR,
        body=Body.SUN,
        natal_longitude=natal_sun_longitude,
        jd_return_ut=jd_return,
        direction="direct",
        timing_source="moira.transits.solar_return",
        search_policy=_return_search_policy_truth(return_policy),
        year=year,
    )
    return _compose_relocated_return(
        truth,
        source_latitude=source_latitude,
        source_longitude=source_longitude,
        relocated_latitude=relocated_latitude,
        relocated_longitude=relocated_longitude,
        source_house_system=source_house_system,
        relocated_house_system=relocated_house_system,
        bodies=bodies,
        reader=reader,
        house_policy=house_policy,
    )


def relocated_lunar_return(
    natal_moon_longitude: float,
    jd_start: float,
    source_latitude: float,
    source_longitude: float,
    relocated_latitude: float,
    relocated_longitude: float,
    *,
    source_house_system: str = HouseSystem.PLACIDUS,
    relocated_house_system: str | None = None,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    return_policy: TransitComputationPolicy | None = None,
    house_policy: HousePolicy | None = None,
) -> RelocatedReturnChart:
    """Cast the next exact lunar return at source and relocated house frames."""

    _require_return_inputs(
        natal_moon_longitude,
        source_latitude,
        source_longitude,
        relocated_latitude,
        relocated_longitude,
    )
    if not _is_finite_number(jd_start):
        raise ValueError("relocated lunar return jd_start must be a finite number")
    jd_return = lunar_return(
        natal_moon_longitude,
        jd_start,
        reader=reader,
        policy=return_policy,
    )
    truth = ReturnMomentTruth(
        return_kind=ReturnKind.LUNAR,
        body=Body.MOON,
        natal_longitude=natal_moon_longitude,
        jd_return_ut=jd_return,
        direction="direct",
        timing_source="moira.transits.lunar_return",
        search_policy=_return_search_policy_truth(return_policy),
        search_start_jd_ut=jd_start,
    )
    return _compose_relocated_return(
        truth,
        source_latitude=source_latitude,
        source_longitude=source_longitude,
        relocated_latitude=relocated_latitude,
        relocated_longitude=relocated_longitude,
        source_house_system=source_house_system,
        relocated_house_system=relocated_house_system,
        bodies=bodies,
        reader=reader,
        house_policy=house_policy,
    )


def relocated_planetary_return(
    body: str,
    natal_longitude: float,
    jd_start: float,
    source_latitude: float,
    source_longitude: float,
    relocated_latitude: float,
    relocated_longitude: float,
    *,
    direction: str = "direct",
    source_house_system: str = HouseSystem.PLACIDUS,
    relocated_house_system: str | None = None,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    return_policy: TransitComputationPolicy | None = None,
    house_policy: HousePolicy | None = None,
) -> RelocatedReturnChart:
    """Cast an exact admitted planetary return at two geographic frames."""

    _require_return_inputs(
        natal_longitude,
        source_latitude,
        source_longitude,
        relocated_latitude,
        relocated_longitude,
    )
    if not _is_finite_number(jd_start):
        raise ValueError("relocated planetary return jd_start must be a finite number")
    if body not in Body.ALL_PLANETS:
        raise ValueError("relocated planetary return requires an admitted planet")
    jd_return = planet_return(
        body,
        natal_longitude,
        jd_start,
        direction=direction,
        reader=reader,
        policy=return_policy,
    )
    truth = ReturnMomentTruth(
        return_kind=ReturnKind.PLANETARY,
        body=body,
        natal_longitude=natal_longitude,
        jd_return_ut=jd_return,
        direction=direction,
        timing_source="moira.transits.planet_return",
        search_policy=_return_search_policy_truth(return_policy),
        search_start_jd_ut=jd_start,
    )
    return _compose_relocated_return(
        truth,
        source_latitude=source_latitude,
        source_longitude=source_longitude,
        relocated_latitude=relocated_latitude,
        relocated_longitude=relocated_longitude,
        source_house_system=source_house_system,
        relocated_house_system=relocated_house_system,
        bodies=bodies,
        reader=reader,
        house_policy=house_policy,
    )


def _signed_longitude_delta(source: float, target: float) -> float:
    return (target - source + 180.0) % 360.0 - 180.0


def _line_index(snapshot: DynamicAstrocartographySnapshot) -> dict[tuple[str, str], ACGLine]:
    return {(line.planet, line.line_type): line for line in snapshot.lines}


def _line_transition(
    source: DynamicAstrocartographySnapshot,
    target: DynamicAstrocartographySnapshot,
    body: str,
    line_type: str,
) -> DynamicAstrocartographyLineTransition:
    source_line = _line_index(source)[(body, line_type)]
    target_line = _line_index(target)[(body, line_type)]
    if line_type in {"MC", "IC"}:
        if source_line.longitude is None or target_line.longitude is None:
            raise ValueError("dynamic ACG meridian line is missing longitude")
        return DynamicAstrocartographyLineTransition(
            body=body,
            line_type=line_type,
            source_jd_ut=source.jd_ut,
            target_jd_ut=target.jd_ut,
            source_meridian_longitude=source_line.longitude,
            target_meridian_longitude=target_line.longitude,
            meridian_signed_delta_deg=_signed_longitude_delta(
                source_line.longitude,
                target_line.longitude,
            ),
            curve_point_shifts=(),
            source_only_latitudes=(),
            target_only_latitudes=(),
        )

    source_points = {latitude: longitude for latitude, longitude in source_line.points}
    target_points = {latitude: longitude for latitude, longitude in target_line.points}
    shared = sorted(source_points.keys() & target_points.keys())
    shifts = tuple(
        AstrocartographyCurvePointShift(
            latitude=latitude,
            source_longitude=source_points[latitude],
            target_longitude=target_points[latitude],
            signed_delta_deg=_signed_longitude_delta(
                source_points[latitude],
                target_points[latitude],
            ),
        )
        for latitude in shared
    )
    return DynamicAstrocartographyLineTransition(
        body=body,
        line_type=line_type,
        source_jd_ut=source.jd_ut,
        target_jd_ut=target.jd_ut,
        source_meridian_longitude=None,
        target_meridian_longitude=None,
        meridian_signed_delta_deg=None,
        curve_point_shifts=shifts,
        source_only_latitudes=tuple(sorted(source_points.keys() - target_points.keys())),
        target_only_latitudes=tuple(sorted(target_points.keys() - source_points.keys())),
    )


def transiting_astrocartography(
    epochs_jd_ut: Sequence[float],
    bodies: Sequence[str],
    *,
    observer_latitude: float,
    observer_longitude: float,
    observer_elevation_m: float = 0.0,
    lat_step: float = 2.0,
    refraction: bool = False,
    reader: SpkReader | None = None,
) -> DynamicAstrocartographySeries:
    """Build a bounded transiting ACG series at explicit, increasing epochs."""

    if isinstance(epochs_jd_ut, (str, bytes)):
        raise ValueError("dynamic ACG epochs must be a sequence of numbers")
    if isinstance(bodies, (str, bytes)):
        raise ValueError("dynamic ACG bodies must be a sequence of names")
    epochs = tuple(epochs_jd_ut)
    selected_bodies = tuple(bodies)
    if not 1 <= len(epochs) <= _MAX_DYNAMIC_EPOCHS:
        raise ValueError(f"dynamic ACG requires 1 to {_MAX_DYNAMIC_EPOCHS} explicit epochs")
    if any(not _is_finite_number(value) for value in epochs):
        raise ValueError("dynamic ACG epochs must be finite")
    if any(later <= earlier for earlier, later in zip(epochs, epochs[1:])):
        raise ValueError("dynamic ACG epochs must be strictly increasing")
    if not selected_bodies or any(body not in Body.ALL_PLANETS for body in selected_bodies):
        raise ValueError("dynamic ACG bodies must be admitted planets")
    if len(set(selected_bodies)) != len(selected_bodies):
        raise ValueError("dynamic ACG bodies must be unique")
    observer_values = (observer_latitude, observer_longitude, observer_elevation_m)
    if not all(_is_finite_number(value) for value in observer_values):
        raise ValueError("dynamic ACG observer values must be finite")
    if not -90.0 <= observer_latitude <= 90.0:
        raise ValueError("dynamic ACG observer latitude must lie in [-90, 90]")
    if not -180.0 <= observer_longitude <= 180.0:
        raise ValueError("dynamic ACG observer longitude must lie in [-180, 180]")
    if not _is_finite_number(lat_step) or not 0.0 < lat_step <= 178.0:
        raise ValueError("dynamic ACG lat_step must lie in (0, 178]")
    if not isinstance(refraction, bool):
        raise ValueError("dynamic ACG refraction must be bool")

    resolved_reader = reader if reader is not None else get_reader()
    snapshots: list[DynamicAstrocartographySnapshot] = []
    for jd_ut in epochs:
        jd_tt = _ut1_to_ephemeris_tt(jd_ut, resolved_reader)
        nutation_longitude, _ = nutation(jd_tt)
        obliquity = true_obliquity(jd_tt)
        sidereal_time = apparent_sidereal_time(jd_ut, nutation_longitude, obliquity)
        position_items: list[DynamicAstrocartographyPosition] = []
        for body in selected_bodies:
            sky = sky_position_at(
                body,
                jd_ut,
                observer_lat=observer_latitude,
                observer_lon=observer_longitude,
                observer_elev_m=observer_elevation_m,
                reader=resolved_reader,
                refraction=refraction,
            )
            position_items.append(
                DynamicAstrocartographyPosition(
                    body=body,
                    right_ascension=sky.right_ascension,
                    declination=sky.declination,
                )
            )
        positions = tuple(position_items)
        ra_dec = {
            position.body: (position.right_ascension, position.declination)
            for position in positions
        }
        lines = tuple(
            acg_lines(
                ra_dec,
                sidereal_time,
                lat_step=lat_step,
                jd_ut=jd_ut,
                refraction=refraction,
                reader=resolved_reader,
            )
        )
        snapshot_truth = DynamicAstrocartographySnapshotTruth(
            jd_ut=jd_ut,
            jd_tt=jd_tt,
            bodies=selected_bodies,
            observer_latitude=observer_latitude,
            observer_longitude=observer_longitude,
            observer_elevation_m=observer_elevation_m,
            apparent_sidereal_time_deg=sidereal_time,
            true_obliquity_deg=obliquity,
            nutation_longitude_deg=nutation_longitude,
            lat_step=lat_step,
            refraction=refraction,
        )
        snapshots.append(
            DynamicAstrocartographySnapshot(
                positions=positions,
                lines=lines,
                computation_truth=snapshot_truth,
            )
        )

    transitions = tuple(
        _line_transition(source, target, body, line_type)
        for source, target in zip(snapshots, snapshots[1:])
        for body in selected_bodies
        for line_type in ("MC", "IC", "ASC", "DSC")
    )
    truth = DynamicAstrocartographySeriesTruth(
        mode=DynamicAstrocartographyMode.TRANSIT,
        epochs_jd_ut=epochs,
        bodies=selected_bodies,
        snapshot_count=len(snapshots),
        transition_count=len(transitions),
    )
    return DynamicAstrocartographySeries(
        snapshots=tuple(snapshots),
        transitions=transitions,
        computation_truth=truth,
    )
