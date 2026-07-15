"""Bounded, non-scored scanning for admitted Western Moon profiles.

This module turns a named profile status into an explicit discrete predicate.
It does not reinterpret historical doctrine as a score, rank, recommendation,
or claim of continuous truth between sampled instants.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .houses import HousePolicy
from .spk_reader import SpkReader, get_reader


__all__ = [
    "WesternElectionalProfileId",
    "WesternElectionalQualificationStatus",
    "WesternElectionalProfileParameter",
    "WesternElectionalProfileScanPolicy",
    "WesternElectionalStatusCount",
    "WesternElectionalProfileWindow",
    "WesternElectionalProfileScan",
    "scan_western_electional_profile",
]


class WesternElectionalProfileId(str, Enum):
    RAMESEY_MOON_CONDITION_V1 = "ramesey_moon_condition_v1"
    SAHL_MOON_CONDITION_V1 = "sahl_moon_condition_v1"
    DOROTHEUS_MOON_CONDITION_V1 = "dorotheus_moon_condition_v1"


class WesternElectionalQualificationStatus(str, Enum):
    CLEAR = "clear_of_profile_impediments"
    TRIGGERED = "one_or_more_profile_impediments"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class WesternElectionalProfileParameter:
    name: str
    value: str | bool | None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("profile parameter name must be non-empty")


@dataclass(frozen=True, slots=True)
class WesternElectionalProfileScanPolicy:
    step_days: float = 1.0 / 24.0
    merge_gap_days: float | None = None
    max_scan_points: int = 256
    max_windows: int = 64
    qualifying_statuses: tuple[WesternElectionalQualificationStatus, ...] = (
        WesternElectionalQualificationStatus.CLEAR,
    )

    def __post_init__(self) -> None:
        if (
            isinstance(self.step_days, bool)
            or not isinstance(self.step_days, (int, float))
            or not math.isfinite(self.step_days)
            or self.step_days <= 0.0
        ):
            raise ValueError("step_days must be finite and positive")
        if self.merge_gap_days is not None and (
            isinstance(self.merge_gap_days, bool)
            or not isinstance(self.merge_gap_days, (int, float))
            or not math.isfinite(self.merge_gap_days)
            or self.merge_gap_days < 0.0
        ):
            raise ValueError("merge_gap_days must be finite and non-negative")
        if (
            isinstance(self.max_scan_points, bool)
            or not isinstance(self.max_scan_points, int)
            or self.max_scan_points < 2
        ):
            raise ValueError("max_scan_points must be an integer of at least 2")
        if (
            isinstance(self.max_windows, bool)
            or not isinstance(self.max_windows, int)
            or self.max_windows < 1
        ):
            raise ValueError("max_windows must be a positive integer")
        statuses = tuple(
            WesternElectionalQualificationStatus(status)
            for status in self.qualifying_statuses
        )
        if not statuses:
            raise ValueError("qualifying_statuses must not be empty")
        if len(set(statuses)) != len(statuses):
            raise ValueError("qualifying_statuses must not contain duplicates")
        object.__setattr__(self, "qualifying_statuses", statuses)

    @property
    def effective_merge_gap_days(self) -> float:
        return self.step_days * 1.5 if self.merge_gap_days is None else self.merge_gap_days


@dataclass(frozen=True, slots=True)
class WesternElectionalStatusCount:
    status: WesternElectionalQualificationStatus
    count: int

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError("status count must be non-negative")


@dataclass(frozen=True, slots=True)
class WesternElectionalProfileWindow:
    jd_start: float
    jd_end: float
    duration_hours: float
    qualifying_jds: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.qualifying_jds:
            raise ValueError("profile window must contain a qualifying sample")
        if self.qualifying_jds[0] != self.jd_start:
            raise ValueError("first qualifying JD must equal jd_start")
        if self.qualifying_jds[-1] != self.jd_end:
            raise ValueError("last qualifying JD must equal jd_end")
        if tuple(sorted(self.qualifying_jds)) != self.qualifying_jds:
            raise ValueError("qualifying JDs must be chronological")
        expected = (self.jd_end - self.jd_start) * 24.0
        if not math.isclose(self.duration_hours, expected, abs_tol=1e-12):
            raise ValueError("duration_hours must derive from the sampled bounds")


@dataclass(frozen=True, slots=True)
class WesternElectionalProfileScan:
    profile_id: WesternElectionalProfileId
    profile_version: str
    jd_start: float
    jd_end: float
    latitude: float
    longitude: float
    house_system: str
    policy: WesternElectionalProfileScanPolicy
    scan_point_count: int
    status_counts: tuple[WesternElectionalStatusCount, ...]
    windows: tuple[WesternElectionalProfileWindow, ...]
    windows_truncated: bool
    profile_parameters: tuple[WesternElectionalProfileParameter, ...]
    reader_provenance: str
    predicate_semantics: str = "profile_status_exact_match_at_discrete_sample"
    continuous_boundary_claim: str = "not_provided"
    scoring: str = "not_provided"
    ranking: str = "not_provided"
    advice: str = "not_provided"
    recommendation: str = "not_provided"

    def __post_init__(self) -> None:
        if sum(item.count for item in self.status_counts) != self.scan_point_count:
            raise ValueError("status counts must account for every scanned point")
        statuses = tuple(item.status for item in self.status_counts)
        if statuses != tuple(WesternElectionalQualificationStatus):
            raise ValueError("status counts must preserve the canonical status order")


def _scan_point_count(jd_start: float, jd_end: float, step_days: float) -> int:
    quotient = (jd_end - jd_start) / step_days
    nearest = round(quotient)
    ratio_tolerance = max(
        1e-12,
        4.0 * math.ulp(max(abs(jd_start), abs(jd_end))) / step_days,
    )
    if abs(quotient - nearest) <= ratio_tolerance:
        quotient = float(nearest)
    return int(math.floor(quotient)) + 1


def _merge_samples(
    qualifying_jds: list[float],
    merge_gap_days: float,
) -> list[WesternElectionalProfileWindow]:
    if not qualifying_jds:
        return []
    groups: list[list[float]] = [[qualifying_jds[0]]]
    for jd in qualifying_jds[1:]:
        if jd - groups[-1][-1] <= merge_gap_days:
            groups[-1].append(jd)
        else:
            groups.append([jd])
    return [
        WesternElectionalProfileWindow(
            jd_start=group[0],
            jd_end=group[-1],
            duration_hours=(group[-1] - group[0]) * 24.0,
            qualifying_jds=tuple(group),
        )
        for group in groups
    ]


def scan_western_electional_profile(
    jd_start: float,
    jd_end: float,
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    profile_id: WesternElectionalProfileId,
    scan_policy: WesternElectionalProfileScanPolicy | None = None,
    unavoidable_time_urgency: bool | None = None,
    sahl_burnt_path_variant=None,
    sahl_eighth_rule_variant=None,
    reader: SpkReader | None = None,
    house_policy: HousePolicy | None = None,
) -> WesternElectionalProfileScan:
    """Scan one admitted Moon profile by exact non-scored summary status."""

    values = (jd_start, jd_end, latitude, longitude)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in values
    ):
        raise ValueError("scan bounds and location must be finite numbers")
    if jd_end <= jd_start:
        raise ValueError("jd_end must be greater than jd_start")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude must be in [-90, 90]")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude must be in [-180, 180]")
    profile_id = WesternElectionalProfileId(profile_id)
    if unavoidable_time_urgency is not None and not isinstance(
        unavoidable_time_urgency, bool
    ):
        raise ValueError("unavoidable_time_urgency must be a boolean or None")
    policy = scan_policy or WesternElectionalProfileScanPolicy()
    if not isinstance(policy, WesternElectionalProfileScanPolicy):
        raise TypeError("scan_policy must be a WesternElectionalProfileScanPolicy")
    point_count = _scan_point_count(jd_start, jd_end, policy.step_days)
    if point_count > policy.max_scan_points:
        raise ValueError(
            f"scan point count {point_count} exceeds maximum {policy.max_scan_points}"
        )

    from . import western_electional as western

    if profile_id is WesternElectionalProfileId.SAHL_MOON_CONDITION_V1:
        if unavoidable_time_urgency is not None:
            raise ValueError("Sahl scan does not accept unavoidable_time_urgency")
    elif sahl_burnt_path_variant is not None or sahl_eighth_rule_variant is not None:
        raise ValueError("Sahl variants are valid only for the Sahl profile")

    resolved_reader = reader if reader is not None else get_reader()
    reader_path = getattr(resolved_reader, "path", None)
    provenance = (
        str(reader_path)
        if reader_path is not None
        else f"{type(resolved_reader).__module__}.{type(resolved_reader).__qualname__}"
    )
    counts = {status: 0 for status in WesternElectionalQualificationStatus}
    qualifying: list[float] = []
    profile_version: str | None = None
    parameters: tuple[WesternElectionalProfileParameter, ...] | None = None
    qualifying_set = {status.value for status in policy.qualifying_statuses}

    for index in range(point_count):
        jd_ut = jd_start + index * policy.step_days
        if profile_id is WesternElectionalProfileId.RAMESEY_MOON_CONDITION_V1:
            evaluation = western.ramesey_moon_condition_at(
                jd_ut,
                latitude,
                longitude,
                house_system=house_system,
                unavoidable_time_urgency=unavoidable_time_urgency,
                reader=resolved_reader,
                house_policy=house_policy,
            )
            current_parameters = (
                WesternElectionalProfileParameter(
                    "unavoidable_time_urgency", unavoidable_time_urgency
                ),
            )
        elif profile_id is WesternElectionalProfileId.SAHL_MOON_CONDITION_V1:
            evaluation = western.sahl_moon_condition_at(
                jd_ut,
                latitude,
                longitude,
                house_system=house_system,
                burnt_path_variant=sahl_burnt_path_variant,
                eighth_rule_variant=sahl_eighth_rule_variant,
                reader=resolved_reader,
                house_policy=house_policy,
            )
            current_parameters = (
                WesternElectionalProfileParameter(
                    "burnt_path_variant", evaluation.burnt_path_variant.value
                ),
                WesternElectionalProfileParameter(
                    "eighth_rule_variant", evaluation.eighth_rule_variant.value
                ),
            )
        else:
            evaluation = western.dorotheus_moon_condition_at(
                jd_ut,
                latitude,
                longitude,
                house_system=house_system,
                unavoidable_time_urgency=unavoidable_time_urgency,
                reader=resolved_reader,
                house_policy=house_policy,
            )
            current_parameters = (
                WesternElectionalProfileParameter(
                    "unavoidable_time_urgency", unavoidable_time_urgency
                ),
            )
        status = WesternElectionalQualificationStatus(evaluation.status.value)
        counts[status] += 1
        if status.value in qualifying_set:
            qualifying.append(jd_ut)
        if profile_version is None:
            profile_version = evaluation.profile_version
            parameters = current_parameters

    all_windows = _merge_samples(qualifying, policy.effective_merge_gap_days)
    windows_truncated = len(all_windows) > policy.max_windows
    return WesternElectionalProfileScan(
        profile_id=profile_id,
        profile_version=str(profile_version),
        jd_start=jd_start,
        jd_end=jd_end,
        latitude=latitude,
        longitude=longitude,
        house_system=house_system,
        policy=policy,
        scan_point_count=point_count,
        status_counts=tuple(
            WesternElectionalStatusCount(status, counts[status])
            for status in WesternElectionalQualificationStatus
        ),
        windows=tuple(all_windows[: policy.max_windows]),
        windows_truncated=windows_truncated,
        profile_parameters=parameters or (),
        reader_provenance=provenance,
    )
