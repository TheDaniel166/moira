"""Bounded, non-scored scanning for admitted Western Moon profiles.

This module turns a named profile status into an explicit discrete predicate.
It does not reinterpret historical doctrine as a score, rank, recommendation,
or claim of continuous truth between sampled instants.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import Enum

from .chart import create_chart
from .constants import Body
from .houses import HousePolicy
from .spk_reader import SpkReader, get_reader
from .void_of_course import VoidOfCourseWindow, void_periods_in_range


__all__ = [
    "WesternElectionalProfileId",
    "WesternElectionalQualificationStatus",
    "WesternElectionalProfileParameter",
    "WesternElectionalProfileScanPolicy",
    "WesternElectionalStatusCount",
    "WesternElectionalSampleWitness",
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
    qualifying_statuses: tuple[WesternElectionalQualificationStatus, ...]
    step_days: float = 1.0 / 24.0
    merge_gap_days: float | None = None
    max_scan_points: int = 256
    max_windows: int = 64
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
class WesternElectionalSampleWitness:
    jd_ut: float
    status: WesternElectionalQualificationStatus
    qualifies: bool
    triggered_rule_ids: tuple[str, ...]
    not_evaluable_rule_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd_ut):
            raise ValueError("sample JD must be finite")
        if len(set(self.triggered_rule_ids)) != len(self.triggered_rule_ids):
            raise ValueError("triggered rule IDs must be unique")
        if len(set(self.not_evaluable_rule_ids)) != len(self.not_evaluable_rule_ids):
            raise ValueError("not-evaluable rule IDs must be unique")
        if set(self.triggered_rule_ids) & set(self.not_evaluable_rule_ids):
            raise ValueError("one rule cannot be both triggered and not evaluable")


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
    samples: tuple[WesternElectionalSampleWitness, ...]
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
        if len(self.samples) != self.scan_point_count:
            raise ValueError("one sample witness is required for every scanned point")
        if tuple(sample.jd_ut for sample in self.samples) != tuple(
            sorted(sample.jd_ut for sample in self.samples)
        ):
            raise ValueError("sample witnesses must be chronological")
        derived_counts = {
            status: sum(sample.status is status for sample in self.samples)
            for status in WesternElectionalQualificationStatus
        }
        if any(item.count != derived_counts[item.status] for item in self.status_counts):
            raise ValueError("status counts must derive from sample witnesses")
        qualifying_statuses = set(self.policy.qualifying_statuses)
        if any(
            sample.qualifies != (sample.status in qualifying_statuses)
            for sample in self.samples
        ):
            raise ValueError("sample qualification must derive from the scan policy")
        qualifying_jds = {
            sample.jd_ut for sample in self.samples if sample.qualifies
        }
        if any(
            jd not in qualifying_jds
            for window in self.windows
            for jd in window.qualifying_jds
        ):
            raise ValueError("window samples must satisfy the qualification policy")


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


def _void_at(jd_ut: float, windows: tuple[VoidOfCourseWindow, ...]) -> bool:
    return any(
        window.jd_voc_start <= jd_ut <= window.jd_voc_end
        for window in windows
    )


def _sample_witness(evaluation, qualifies: bool) -> WesternElectionalSampleWitness:
    triggered = tuple(
        rule.rule_id for rule in evaluation.rules if rule.state.value == "triggered"
    )
    not_evaluable = tuple(
        rule.rule_id
        for rule in evaluation.rules
        if rule.state.value == "not_evaluable"
    )
    return WesternElectionalSampleWitness(
        jd_ut=evaluation.jd_ut,
        status=WesternElectionalQualificationStatus(evaluation.status.value),
        qualifies=qualifies,
        triggered_rule_ids=triggered,
        not_evaluable_rule_ids=not_evaluable,
    )


def scan_western_electional_profile(
    jd_start: float,
    jd_end: float,
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    profile_id: WesternElectionalProfileId,
    scan_policy: WesternElectionalProfileScanPolicy,
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
    policy = scan_policy
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
        if sahl_burnt_path_variant is None:
            raise ValueError(
                "Sahl scan requires an explicit sahl_burnt_path_variant"
            )
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
    samples: list[WesternElectionalSampleWitness] = []
    profile_version: str | None = None
    parameters: tuple[WesternElectionalProfileParameter, ...] | None = None
    qualifying_set = {status.value for status in policy.qualifying_statuses}
    voc_windows: tuple[VoidOfCourseWindow, ...] = ()
    if profile_id in (
        WesternElectionalProfileId.RAMESEY_MOON_CONDITION_V1,
        WesternElectionalProfileId.SAHL_MOON_CONDITION_V1,
    ):
        voc_windows = tuple(
            void_periods_in_range(
                jd_start,
                jd_end,
                reader=resolved_reader,
                modern=False,
            )
        )

    resolved_sahl_policy = None
    if profile_id is WesternElectionalProfileId.SAHL_MOON_CONDITION_V1:
        if not isinstance(sahl_burnt_path_variant, western.SahlBurntPathVariant):
            raise TypeError("sahl_burnt_path_variant must be a SahlBurntPathVariant")
        overrides = {"burnt_path_variant": sahl_burnt_path_variant}
        if sahl_eighth_rule_variant is not None:
            if not isinstance(sahl_eighth_rule_variant, western.SahlEighthRuleVariant):
                raise TypeError("sahl_eighth_rule_variant must be a SahlEighthRuleVariant")
            overrides["eighth_rule_variant"] = sahl_eighth_rule_variant
        resolved_sahl_policy = (
            replace(western.SAHL_MOON_CONDITION_V1, **overrides)
            if overrides
            else western.SAHL_MOON_CONDITION_V1
        )

    for index in range(point_count):
        jd_ut = jd_start + index * policy.step_days
        if profile_id is WesternElectionalProfileId.RAMESEY_MOON_CONDITION_V1:
            chart = create_chart(
                jd_ut,
                latitude,
                longitude,
                house_system=house_system,
                bodies=[Body.SUN, Body.MOON, Body.MARS, Body.SATURN],
                reader=resolved_reader,
                policy=house_policy,
            )
            evaluation = western.evaluate_ramesey_moon_condition(
                chart,
                void_of_course=_void_at(jd_ut, voc_windows),
                unavoidable_time_urgency=unavoidable_time_urgency,
                position_product=western.RAMESEY_MOON_CONDITION_V1.position_product,
                reader_provenance=provenance,
            )
            current_parameters = (
                WesternElectionalProfileParameter(
                    "unavoidable_time_urgency", unavoidable_time_urgency
                ),
            )
        elif profile_id is WesternElectionalProfileId.SAHL_MOON_CONDITION_V1:
            chart = create_chart(
                jd_ut,
                latitude,
                longitude,
                house_system=house_system,
                bodies=[Body.SUN, Body.MOON, Body.MARS, Body.SATURN],
                reader=resolved_reader,
                policy=house_policy,
            )
            evaluation = western.evaluate_sahl_moon_condition(
                chart,
                void_of_course=_void_at(jd_ut, voc_windows),
                position_product=resolved_sahl_policy.position_product,
                reader_provenance=provenance,
                policy=resolved_sahl_policy,
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
        qualifies = status.value in qualifying_set
        samples.append(_sample_witness(evaluation, qualifies))
        if qualifies:
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
        samples=tuple(samples),
        windows=tuple(all_windows[: policy.max_windows]),
        windows_truncated=windows_truncated,
        profile_parameters=parameters or (),
        reader_provenance=provenance,
    )
