"""Bounded sampled and partially refined complete-judgement windows.

The scanner observes complete Phase 8 judgement signatures.  It may refine a
bracket in which two observed signatures differ, but it does not own a complete
inventory of every astronomical boundary capable of changing doctrine.  It
therefore never claims exact continuous windows.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ._western_electional_context import WesternElectionClass
from ._western_electional_judgement import (
    WesternElectionalJudgementEvaluation,
    WesternElectionalJudgementPolicy,
    WESTERN_ELECTIONAL_JUDGEMENT_V1,
    western_electional_judgement_at,
)
from ._western_electional_matter import DorotheusMatterProfileId
from ._western_electional_sahl_matter import SahlMatterProfileId
from .houses import HousePolicy
from .spk_reader import SpkReader, get_reader


__all__ = [
    "WesternElectionalWindowScanMode",
    "WesternElectionalBoundaryResolution",
    "WesternElectionalJudgementWindowPolicy",
    "WesternElectionalJudgementSignature",
    "WesternElectionalTransitionCause",
    "WesternElectionalCandidateEvent",
    "WesternElectionalWindowBoundary",
    "WesternElectionalJudgementWindow",
    "WesternElectionalJudgementWindowScan",
    "WESTERN_ELECTIONAL_JUDGEMENT_WINDOWS_V1",
    "scan_western_electional_judgement_windows",
]


_MAX_SPAN_DAYS = 31.0
_MAX_INITIAL_SAMPLES = 64
_MAX_EVALUATIONS = 256
_MAX_WINDOWS = 64
_MAX_TRANSITIONS = 63
_MAX_REFINEMENT_ITERATIONS = 24
_MAX_EVENT_SEEDS = 128
_MIN_STEP_DAYS = 1.0 / 24.0
_MIN_TOLERANCE_SECONDS = 0.1
_MAX_TOLERANCE_SECONDS = 3600.0


class WesternElectionalWindowScanMode(str, Enum):
    SAMPLED = "sampled"
    PARTIALLY_EVENT_REFINED = "partially_event_refined"


class WesternElectionalBoundaryResolution(str, Enum):
    REQUEST_BOUND = "request_bound"
    SAMPLED_BRACKET = "sampled_bracket"
    ADAPTIVELY_REFINED_BRACKET = "adaptively_refined_bracket"


@dataclass(frozen=True, slots=True)
class WesternElectionalJudgementWindowPolicy:
    profile_id: str = "western_electional_judgement_windows_v1"
    profile_version: str = "1.0.0"
    mode: WesternElectionalWindowScanMode = WesternElectionalWindowScanMode.SAMPLED
    step_days: float = 0.25
    transition_tolerance_seconds: float = 60.0
    max_refinement_iterations: int = 0
    max_initial_samples: int = 64
    max_evaluations: int = 256
    max_windows: int = 64
    max_transitions: int = 63
    max_event_seeds: int = 128
    max_span_days: float = 31.0
    boundary_inventory: str = "incomplete_profile_transition_inventory"
    transition_detector: str = "complete_phase8_signature_change"
    exact_boundary_claimed: bool = False
    continuous_truth_claimed: bool = False
    ranking_integration: str = "separate_phase9_endpoint_not_applied"
    advice_language: str = "not_admitted"
    recommendation_language: str = "not_admitted"

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", WesternElectionalWindowScanMode(self.mode))
        numeric = (
            ("step_days", self.step_days),
            ("transition_tolerance_seconds", self.transition_tolerance_seconds),
            ("max_span_days", self.max_span_days),
        )
        for name, value in numeric:
            if isinstance(value, bool) or not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if not _MIN_STEP_DAYS <= self.step_days <= _MAX_SPAN_DAYS:
            raise ValueError("step_days must be between one hour and 31 days")
        if not _MIN_TOLERANCE_SECONDS <= self.transition_tolerance_seconds <= _MAX_TOLERANCE_SECONDS:
            raise ValueError("transition tolerance must be between 0.1 and 3600 seconds")
        integer_bounds = (
            ("max_refinement_iterations", self.max_refinement_iterations, 0, _MAX_REFINEMENT_ITERATIONS),
            ("max_initial_samples", self.max_initial_samples, 2, _MAX_INITIAL_SAMPLES),
            ("max_evaluations", self.max_evaluations, 2, _MAX_EVALUATIONS),
            ("max_windows", self.max_windows, 1, _MAX_WINDOWS),
            ("max_transitions", self.max_transitions, 0, _MAX_TRANSITIONS),
            ("max_event_seeds", self.max_event_seeds, 0, _MAX_EVENT_SEEDS),
        )
        for name, value, lower, upper in integer_bounds:
            if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
                raise ValueError(f"{name} must be an integer in [{lower}, {upper}]")
        if self.max_evaluations < self.max_initial_samples:
            raise ValueError("max_evaluations cannot be less than max_initial_samples")
        if not 0.0 < self.max_span_days <= _MAX_SPAN_DAYS:
            raise ValueError("max_span_days must be positive and at most 31 days")
        if self.mode is WesternElectionalWindowScanMode.SAMPLED:
            if self.max_refinement_iterations != 0:
                raise ValueError("sampled mode requires max_refinement_iterations=0")
        elif self.max_refinement_iterations < 1:
            raise ValueError("partially refined mode requires at least one refinement iteration")
        fixed = {
            "profile_id": "western_electional_judgement_windows_v1",
            "profile_version": "1.0.0",
            "boundary_inventory": "incomplete_profile_transition_inventory",
            "transition_detector": "complete_phase8_signature_change",
            "exact_boundary_claimed": False,
            "continuous_truth_claimed": False,
            "ranking_integration": "separate_phase9_endpoint_not_applied",
            "advice_language": "not_admitted",
            "recommendation_language": "not_admitted",
        }
        for name, expected in fixed.items():
            if getattr(self, name) != expected:
                raise ValueError(f"{name} is fixed for the admitted Phase 10 policy")


WESTERN_ELECTIONAL_JUDGEMENT_WINDOWS_V1 = WesternElectionalJudgementWindowPolicy()


@dataclass(frozen=True, slots=True)
class WesternElectionalJudgementSignature:
    judgement_state: str
    moon_status: str
    matter_status: str
    component_states: tuple[tuple[str, str], ...]
    moon_rule_states: tuple[tuple[str, str], ...]
    matter_clause_states: tuple[tuple[str, str], ...]
    rooted_significator_conditions: tuple[tuple[str, str], ...]
    rooted_supplementary_states: tuple[tuple[str, str], ...]
    perfection_present_kinds: tuple[str, ...]
    perfection_indeterminate_kinds: tuple[str, ...]
    unresolved_requirement_ids: tuple[str, ...]

    @property
    def contains_unresolved(self) -> bool:
        return bool(self.unresolved_requirement_ids)


@dataclass(frozen=True, slots=True)
class WesternElectionalTransitionCause:
    cause_id: str
    before_value: str
    after_value: str
    semantics: str = "observed_phase8_output_change_not_complete_astronomical_cause"

    def __post_init__(self) -> None:
        if not self.cause_id or self.before_value == self.after_value:
            raise ValueError("transition cause must preserve one changed field")
        if self.semantics != "observed_phase8_output_change_not_complete_astronomical_cause":
            raise ValueError("transition-cause semantics are fixed for Phase 10 v1")


@dataclass(frozen=True, slots=True)
class WesternElectionalCandidateEvent:
    event_id: str
    jd_ut: float
    source_component: str
    event_kind: str
    causal_status: str = "candidate_boundary_seed_not_asserted_cause"

    def __post_init__(self) -> None:
        if not self.event_id or not self.source_component or not self.event_kind:
            raise ValueError("candidate event identity must remain visible")
        if not math.isfinite(self.jd_ut):
            raise ValueError("candidate event epoch must be finite")
        if self.causal_status != "candidate_boundary_seed_not_asserted_cause":
            raise ValueError("Phase 10 candidate events cannot assert causality")


@dataclass(frozen=True, slots=True)
class WesternElectionalWindowBoundary:
    resolution: WesternElectionalBoundaryResolution
    estimate_jd_ut: float
    bracket_start_jd_ut: float
    bracket_end_jd_ut: float
    bracket_width_seconds: float
    causes: tuple[WesternElectionalTransitionCause, ...]
    candidate_events: tuple[WesternElectionalCandidateEvent, ...] = ()
    doctrine_boundary_exact: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "resolution", WesternElectionalBoundaryResolution(self.resolution))
        numeric = (
            self.estimate_jd_ut,
            self.bracket_start_jd_ut,
            self.bracket_end_jd_ut,
            self.bracket_width_seconds,
        )
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("boundary values must be finite")
        if self.bracket_start_jd_ut > self.estimate_jd_ut or self.estimate_jd_ut > self.bracket_end_jd_ut:
            raise ValueError("boundary estimate must lie inside its bracket")
        expected_width = (self.bracket_end_jd_ut - self.bracket_start_jd_ut) * 86400.0
        if not math.isclose(self.bracket_width_seconds, expected_width, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError("boundary width must derive from its bracket")
        if self.resolution is WesternElectionalBoundaryResolution.REQUEST_BOUND:
            if self.bracket_width_seconds != 0.0 or self.causes or self.candidate_events:
                raise ValueError(
                    "request bounds are zero-width and carry no doctrine cause or event seed"
                )
        elif not self.causes:
            raise ValueError("observed transition boundaries must expose their causes")
        if self.doctrine_boundary_exact:
            raise ValueError("Phase 10 v1 cannot claim an exact doctrine boundary")


@dataclass(frozen=True, slots=True)
class WesternElectionalJudgementWindow:
    window_index: int
    exactness: WesternElectionalWindowScanMode
    jd_start_estimate: float
    jd_end_estimate: float
    start_boundary: WesternElectionalWindowBoundary
    end_boundary: WesternElectionalWindowBoundary
    observed_jds: tuple[float, ...]
    signature: WesternElectionalJudgementSignature
    representative_judgement: WesternElectionalJudgementEvaluation
    contains_unresolved: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "exactness", WesternElectionalWindowScanMode(self.exactness))
        if self.window_index < 0 or self.jd_start_estimate > self.jd_end_estimate:
            raise ValueError("window index and estimated bounds must be ordered")
        if self.jd_start_estimate != self.start_boundary.estimate_jd_ut:
            raise ValueError("window start must derive from its boundary witness")
        if self.jd_end_estimate != self.end_boundary.estimate_jd_ut:
            raise ValueError("window end must derive from its boundary witness")
        if not self.observed_jds or tuple(sorted(set(self.observed_jds))) != self.observed_jds:
            raise ValueError("window observations must be distinct and time ordered")
        if self.representative_judgement.jd_ut not in self.observed_jds:
            raise ValueError("representative judgement must be one observed instant")
        if _signature(self.representative_judgement) != self.signature:
            raise ValueError("representative judgement must own the window signature")
        if self.contains_unresolved != self.signature.contains_unresolved:
            raise ValueError("unresolved truth must derive from the visible signature")


@dataclass(frozen=True, slots=True)
class WesternElectionalJudgementWindowScan:
    jd_start: float
    jd_end: float
    latitude: float
    longitude: float
    requested_house_system: str
    profile_id: str
    profile_version: str
    policy: WesternElectionalJudgementWindowPolicy
    windows: tuple[WesternElectionalJudgementWindow, ...]
    initial_sample_count: int
    total_evaluation_count: int
    transition_count: int
    candidate_events: tuple[WesternElectionalCandidateEvent, ...]
    event_seed_count: int
    reader_provenance: str
    authorities: tuple[str, ...]
    boundary_inventory_complete: bool = False
    exact_boundary_claimed: bool = False
    continuous_truth_claimed: bool = False
    ranking_integration: str = "separate_phase9_endpoint_not_applied"
    advice_language: str = "not_admitted"
    recommendation_language: str = "not_admitted"

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd_start) or not math.isfinite(self.jd_end) or self.jd_end <= self.jd_start:
            raise ValueError("scan interval must be finite and increasing")
        if self.profile_id != self.policy.profile_id or self.profile_version != self.policy.profile_version:
            raise ValueError("scan identity must derive from its policy")
        if not self.windows or len(self.windows) > self.policy.max_windows:
            raise ValueError("scan must return a bounded nonempty window sequence")
        if tuple(item.window_index for item in self.windows) != tuple(range(len(self.windows))):
            raise ValueError("window indices must be complete and ordered")
        if any(item.exactness is not self.policy.mode for item in self.windows):
            raise ValueError("every window must expose the selected exactness mode")
        if self.windows[0].jd_start_estimate != self.jd_start or self.windows[-1].jd_end_estimate != self.jd_end:
            raise ValueError("window sequence must cover the requested observed range")
        for left, right in zip(self.windows, self.windows[1:]):
            if left.end_boundary != right.start_boundary:
                raise ValueError("adjacent windows must share one boundary witness")
            if left.signature == right.signature:
                raise ValueError("adjacent equal signatures must be merged")
        if not 2 <= self.initial_sample_count <= self.policy.max_initial_samples:
            raise ValueError("initial sample count exceeds the declared resource policy")
        if not self.initial_sample_count <= self.total_evaluation_count <= self.policy.max_evaluations:
            raise ValueError("total evaluations exceed the declared resource policy")
        if self.transition_count != len(self.windows) - 1:
            raise ValueError("transition count must derive from the returned windows")
        if self.transition_count > self.policy.max_transitions:
            raise ValueError("transition count exceeds the declared resource policy")
        if self.event_seed_count != len(self.candidate_events):
            raise ValueError("event seed count must derive from visible candidate events")
        if self.event_seed_count > self.policy.max_event_seeds:
            raise ValueError("candidate event count exceeds the declared resource policy")
        if tuple(sorted(
            self.candidate_events,
            key=lambda item: (item.jd_ut, item.source_component, item.event_id),
        )) != self.candidate_events:
            raise ValueError("candidate events must be deterministically ordered")
        if any(
            not self.jd_start < item.jd_ut < self.jd_end
            for item in self.candidate_events
        ):
            raise ValueError("candidate events must lie strictly inside the scan interval")
        if not self.reader_provenance or not self.authorities:
            raise ValueError("scan must preserve reader and authority provenance")
        if any((self.boundary_inventory_complete, self.exact_boundary_claimed, self.continuous_truth_claimed)):
            raise ValueError("Phase 10 v1 cannot claim complete or continuous boundary truth")
        if self.ranking_integration != "separate_phase9_endpoint_not_applied":
            raise ValueError("Phase 9 ranking must remain a separate request")
        if self.advice_language != "not_admitted" or self.recommendation_language != "not_admitted":
            raise ValueError("Phase 10 v1 admits no advice or recommendation")


def _value(value: object) -> str:
    return str(getattr(value, "value", value))


def _state_pairs(items, id_name: str, state_name: str = "state") -> tuple[tuple[str, str], ...]:
    return tuple(
        (str(getattr(item, id_name)), _value(getattr(item, state_name)))
        for item in items
    )


def _signature(judgement: WesternElectionalJudgementEvaluation) -> WesternElectionalJudgementSignature:
    moon = judgement.general_moon_condition
    matter = judgement.matter_profile
    rooted = judgement.rooted_context
    rooted_conditions = () if rooted is None else tuple(
        (str(item.body), _value(item.condition)) for item in rooted.matter_significators
    )
    rooted_supplementary = () if rooted is None else tuple(
        (str(item.indicator_id), _value(item.state))
        for item in rooted.supplementary_indicators
    )
    return WesternElectionalJudgementSignature(
        judgement_state=_value(judgement.state),
        moon_status=_value(moon.status),
        matter_status=_value(matter.status),
        component_states=tuple(
            (item.component_id, _value(item.state)) for item in judgement.components
        ),
        moon_rule_states=_state_pairs(moon.rules, "rule_id"),
        matter_clause_states=_state_pairs(matter.clauses, "clause_id"),
        rooted_significator_conditions=rooted_conditions,
        rooted_supplementary_states=rooted_supplementary,
        perfection_present_kinds=tuple(_value(item) for item in judgement.perfection_path.present_kinds),
        perfection_indeterminate_kinds=tuple(
            _value(item) for item in judgement.perfection_path.indeterminate_kinds
        ),
        unresolved_requirement_ids=tuple(
            item.requirement_id for item in judgement.unresolved_requirements
        ),
    )


def _mapping_causes(prefix: str, before, after) -> list[WesternElectionalTransitionCause]:
    left = dict(before)
    right = dict(after)
    causes = []
    for key in sorted(set(left) | set(right)):
        old = left.get(key, "absent")
        new = right.get(key, "absent")
        if old != new:
            causes.append(WesternElectionalTransitionCause(f"{prefix}:{key}", old, new))
    return causes


def _set_causes(prefix: str, before, after) -> list[WesternElectionalTransitionCause]:
    left = set(before)
    right = set(after)
    causes = []
    for value in sorted(left ^ right):
        causes.append(WesternElectionalTransitionCause(
            f"{prefix}:{value}",
            "present" if value in left else "absent",
            "present" if value in right else "absent",
        ))
    return causes


def _transition_causes(
    before: WesternElectionalJudgementSignature,
    after: WesternElectionalJudgementSignature,
) -> tuple[WesternElectionalTransitionCause, ...]:
    causes: list[WesternElectionalTransitionCause] = []
    for name in ("judgement_state", "moon_status", "matter_status"):
        old = getattr(before, name)
        new = getattr(after, name)
        if old != new:
            causes.append(WesternElectionalTransitionCause(name, old, new))
    for name in (
        "component_states",
        "moon_rule_states",
        "matter_clause_states",
        "rooted_significator_conditions",
        "rooted_supplementary_states",
    ):
        causes.extend(_mapping_causes(name, getattr(before, name), getattr(after, name)))
    for name in (
        "perfection_present_kinds",
        "perfection_indeterminate_kinds",
        "unresolved_requirement_ids",
    ):
        causes.extend(_set_causes(name, getattr(before, name), getattr(after, name)))
    if not causes:
        raise ValueError("a transition boundary requires a changed Phase 8 signature")
    return tuple(causes)


def _initial_jds(jd_start: float, jd_end: float, step_days: float) -> tuple[float, ...]:
    values = [jd_start]
    current = jd_start + step_days
    while current < jd_end:
        values.append(current)
        current += step_days
    values.append(jd_end)
    return tuple(values)


def _candidate_events(
    judgement: WesternElectionalJudgementEvaluation,
) -> tuple[WesternElectionalCandidateEvent, ...]:
    events = [
        WesternElectionalCandidateEvent(
            event_id=item.event_id,
            jd_ut=item.jd_ut,
            source_component="lilly_perfection_path",
            event_kind=_value(item.kind),
        )
        for item in judgement.perfection_path.events
    ]
    rooted = judgement.rooted_context
    if rooted is not None and rooted.next_connection is not None:
        connection = rooted.next_connection
        events.append(WesternElectionalCandidateEvent(
            event_id=(
                f"rooted_next_connection:{connection.body}:"
                f"{connection.aspect_name}:{connection.jd_exact:.12f}"
            ),
            jd_ut=connection.jd_exact,
            source_component="dorotheus_rooted_context",
            event_kind="next_moon_connection",
        ))
    flow = getattr(judgement.matter_profile, "moon_connection_flow", None)
    if flow is not None:
        for event in (flow.previous_separation, flow.next_connection):
            if event is not None:
                events.append(WesternElectionalCandidateEvent(
                    event_id=(
                        f"moon_flow:{_value(event.role)}:{event.body}:"
                        f"{event.aspect_name}:{event.jd_exact:.12f}"
                    ),
                    jd_ut=event.jd_exact,
                    source_component="dorotheus_matter_moon_flow",
                    event_kind=_value(event.role),
                ))
    return tuple(events)


def _request_boundary(jd_ut: float) -> WesternElectionalWindowBoundary:
    return WesternElectionalWindowBoundary(
        resolution=WesternElectionalBoundaryResolution.REQUEST_BOUND,
        estimate_jd_ut=jd_ut,
        bracket_start_jd_ut=jd_ut,
        bracket_end_jd_ut=jd_ut,
        bracket_width_seconds=0.0,
        causes=(),
        candidate_events=(),
    )


def scan_western_electional_judgement_windows(
    jd_start: float,
    jd_end: float,
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    matter_profile_id: DorotheusMatterProfileId | SahlMatterProfileId | str,
    perfection_significator_a: str,
    perfection_significator_b: str,
    perfection_interval_days: float,
    election_class: WesternElectionClass = WesternElectionClass.EPHEMERAL,
    natal_jd_ut: float | None = None,
    natal_latitude: float | None = None,
    natal_longitude: float | None = None,
    natal_house_system: str | None = None,
    unavoidable_time_urgency: bool | None = None,
    moon_flow_policy=None,
    dorotheus_sign_nature_variant=None,
    sahl_burnt_path_variant=None,
    sahl_eighth_rule_variant=None,
    reader: SpkReader | None = None,
    house_policy: HousePolicy | None = None,
    judgement_policy: WesternElectionalJudgementPolicy = WESTERN_ELECTIONAL_JUDGEMENT_V1,
    scan_policy: WesternElectionalJudgementWindowPolicy = WESTERN_ELECTIONAL_JUDGEMENT_WINDOWS_V1,
) -> WesternElectionalJudgementWindowScan:
    """Return bounded observed windows without claiming continuous exactness."""

    if not isinstance(scan_policy, WesternElectionalJudgementWindowPolicy):
        raise TypeError("scan_policy must be a WesternElectionalJudgementWindowPolicy")
    numeric = (jd_start, jd_end, latitude, longitude, perfection_interval_days)
    if any(isinstance(value, bool) or not math.isfinite(float(value)) for value in numeric):
        raise ValueError("scan inputs must be finite numbers")
    if jd_end <= jd_start or jd_end - jd_start > scan_policy.max_span_days:
        raise ValueError("scan interval must be increasing and within max_span_days")
    initial_jds = _initial_jds(float(jd_start), float(jd_end), scan_policy.step_days)
    if len(initial_jds) > scan_policy.max_initial_samples:
        raise ValueError("initial sample count exceeds max_initial_samples")
    resolved_reader = reader if reader is not None else get_reader()
    cache: dict[float, WesternElectionalJudgementEvaluation] = {}

    def evaluate(jd_ut: float) -> WesternElectionalJudgementEvaluation:
        if jd_ut in cache:
            return cache[jd_ut]
        if len(cache) >= scan_policy.max_evaluations:
            raise ValueError("adaptive refinement exceeds max_evaluations")
        result = western_electional_judgement_at(
            jd_ut,
            latitude,
            longitude,
            house_system=house_system,
            matter_profile_id=matter_profile_id,
            perfection_significator_a=perfection_significator_a,
            perfection_significator_b=perfection_significator_b,
            perfection_interval_days=perfection_interval_days,
            election_class=election_class,
            natal_jd_ut=natal_jd_ut,
            natal_latitude=natal_latitude,
            natal_longitude=natal_longitude,
            natal_house_system=natal_house_system,
            unavoidable_time_urgency=unavoidable_time_urgency,
            moon_flow_policy=moon_flow_policy,
            dorotheus_sign_nature_variant=dorotheus_sign_nature_variant,
            sahl_burnt_path_variant=sahl_burnt_path_variant,
            sahl_eighth_rule_variant=sahl_eighth_rule_variant,
            reader=resolved_reader,
            house_policy=house_policy,
            policy=judgement_policy,
        )
        cache[jd_ut] = result
        return result

    for jd_ut in initial_jds:
        evaluate(jd_ut)

    candidate_event_map: dict[tuple[str, str, float], WesternElectionalCandidateEvent] = {}
    if scan_policy.mode is WesternElectionalWindowScanMode.PARTIALLY_EVENT_REFINED:
        for jd_ut in initial_jds:
            for event in _candidate_events(evaluate(jd_ut)):
                if jd_start < event.jd_ut < jd_end:
                    key = (event.source_component, event.event_id, event.jd_ut)
                    candidate_event_map[key] = event
        if len(candidate_event_map) > scan_policy.max_event_seeds:
            raise ValueError("candidate event count exceeds max_event_seeds")
        for event in candidate_event_map.values():
            evaluate(event.jd_ut)

    tolerance_days = scan_policy.transition_tolerance_seconds / 86400.0

    def refine(lo: float, hi: float, depth: int) -> None:
        left = evaluate(lo)
        right = evaluate(hi)
        if _signature(left) == _signature(right):
            return
        if (
            scan_policy.mode is WesternElectionalWindowScanMode.SAMPLED
            or hi - lo <= tolerance_days
            or depth >= scan_policy.max_refinement_iterations
        ):
            return
        midpoint = (lo + hi) / 2.0
        evaluate(midpoint)
        refine(lo, midpoint, depth + 1)
        refine(midpoint, hi, depth + 1)

    seeded_jds = tuple(sorted({
        *initial_jds,
        *(item.jd_ut for item in candidate_event_map.values()),
    }))
    for lo, hi in zip(seeded_jds, seeded_jds[1:]):
        refine(lo, hi, 0)

    points = tuple(sorted(cache.items()))
    groups: list[list[tuple[float, WesternElectionalJudgementEvaluation]]] = []
    for point in points:
        if not groups or _signature(groups[-1][-1][1]) != _signature(point[1]):
            groups.append([point])
        else:
            groups[-1].append(point)
    transition_count = len(groups) - 1
    if transition_count > scan_policy.max_transitions:
        raise ValueError("observed transition count exceeds max_transitions")
    if len(groups) > scan_policy.max_windows:
        raise ValueError("observed window count exceeds max_windows")

    boundaries = [_request_boundary(float(jd_start))]
    candidate_events = tuple(sorted(
        candidate_event_map.values(),
        key=lambda item: (item.jd_ut, item.source_component, item.event_id),
    ))
    for left, right in zip(groups, groups[1:]):
        lo, left_result = left[-1]
        hi, right_result = right[0]
        resolution = (
            WesternElectionalBoundaryResolution.SAMPLED_BRACKET
            if scan_policy.mode is WesternElectionalWindowScanMode.SAMPLED
            else WesternElectionalBoundaryResolution.ADAPTIVELY_REFINED_BRACKET
        )
        boundaries.append(WesternElectionalWindowBoundary(
            resolution=resolution,
            estimate_jd_ut=(lo + hi) / 2.0,
            bracket_start_jd_ut=lo,
            bracket_end_jd_ut=hi,
            bracket_width_seconds=(hi - lo) * 86400.0,
            causes=_transition_causes(_signature(left_result), _signature(right_result)),
            candidate_events=tuple(
                item for item in candidate_events if lo <= item.jd_ut <= hi
            ),
        ))
    boundaries.append(_request_boundary(float(jd_end)))

    windows = tuple(
        WesternElectionalJudgementWindow(
            window_index=index,
            exactness=scan_policy.mode,
            jd_start_estimate=boundaries[index].estimate_jd_ut,
            jd_end_estimate=boundaries[index + 1].estimate_jd_ut,
            start_boundary=boundaries[index],
            end_boundary=boundaries[index + 1],
            observed_jds=tuple(jd for jd, _ in group),
            signature=_signature(group[0][1]),
            representative_judgement=group[0][1],
            contains_unresolved=_signature(group[0][1]).contains_unresolved,
        )
        for index, group in enumerate(groups)
    )
    authorities = tuple(dict.fromkeys((
        *(authority for _, item in points for authority in item.authorities),
        "Moira Phase 10 observed-signature scan policy",
    )))
    return WesternElectionalJudgementWindowScan(
        jd_start=float(jd_start),
        jd_end=float(jd_end),
        latitude=float(latitude),
        longitude=float(longitude),
        requested_house_system=house_system,
        profile_id=scan_policy.profile_id,
        profile_version=scan_policy.profile_version,
        policy=scan_policy,
        windows=windows,
        initial_sample_count=len(initial_jds),
        total_evaluation_count=len(cache),
        transition_count=transition_count,
        candidate_events=candidate_events,
        event_seed_count=len(candidate_events),
        reader_provenance=points[0][1].reader_provenance,
        authorities=authorities,
    )
