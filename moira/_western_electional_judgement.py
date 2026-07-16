"""Inspectable composition of admitted Western electional doctrine results.

The judgement in this module is a Moira-owned assembly policy.  It does not
claim that Dorotheus, Sahl, and Lilly supplied one historical synthesis.  Each
source-owned component remains intact and the summary state is derived only
from visible component states and requirements.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ._western_electional_context import (
    DorotheusFortificationTestimonyState,
    DorotheusRootedContextEvaluation,
    DorotheusSignificatorCondition,
    DorotheusSupplementaryIndicatorState,
    WesternElectionClass,
)
from ._western_electional_matter import (
    DorotheusMatterProfileEvaluation,
    DorotheusMatterProfileId,
    DorotheusSignNatureVariant,
    dorotheus_matter_profile_at,
)
from ._western_electional_sahl_matter import (
    SahlMatterProfileEvaluation,
    SahlMatterProfileId,
    sahl_matter_profile_at,
)
from .chart import create_chart
from .classical_perfection import (
    ClassicalPerfectionAnalysis,
    ClassicalPerfectionState,
    LILLY_1647_PERFECTION_V1,
    LillyPerfectionKind,
    lilly_perfection_at,
)
from .constants import Body
from .houses import HousePolicy
from .spk_reader import SpkReader, get_reader


__all__ = [
    "WesternElectionalJudgementDoctrine",
    "WesternElectionalJudgementState",
    "WesternElectionalComponentState",
    "WesternElectionalRequirementState",
    "WesternElectionalJudgementPolicy",
    "WesternElectionalJudgementSelection",
    "WesternElectionalComponentSummary",
    "WesternElectionalRequirementWitness",
    "WesternElectionalJudgementEvaluation",
    "WESTERN_ELECTIONAL_JUDGEMENT_V1",
    "assemble_western_electional_judgement",
    "western_electional_judgement_at",
]


_TRADITIONAL_PLANETS = frozenset(
    (
        Body.SUN,
        Body.MOON,
        Body.MERCURY,
        Body.VENUS,
        Body.MARS,
        Body.JUPITER,
        Body.SATURN,
    )
)
_CONSTRUCTIVE_PERFECTIONS = frozenset(
    (
        LillyPerfectionKind.DIRECT,
        LillyPerfectionKind.TRANSLATION,
        LillyPerfectionKind.COLLECTION,
    )
)
_IMPEDING_PERFECTIONS = frozenset(
    (
        LillyPerfectionKind.PROHIBITION,
        LillyPerfectionKind.REFRANATION,
        LillyPerfectionKind.FRUSTRATION,
    )
)
_DOROTHEUS_SIGN_NATURE_PROFILE_IDS = frozenset(
    (
        DorotheusMatterProfileId.LAND_TRAVEL.value,
        DorotheusMatterProfileId.SEA_TRAVEL.value,
    )
)


class WesternElectionalJudgementDoctrine(str, Enum):
    DOROTHEUS = "dorotheus_matter_with_lilly_perfection"
    SAHL = "sahl_matter_with_lilly_perfection"


class WesternElectionalJudgementState(str, Enum):
    COMPLETE = "complete_under_profile"
    IMPEDED = "impeded"
    INDETERMINATE = "indeterminate"


class WesternElectionalComponentState(str, Enum):
    COMPLETE = "complete"
    IMPEDED = "impeded"
    INDETERMINATE = "indeterminate"
    NOT_APPLICABLE = "not_applicable"


class WesternElectionalRequirementState(str, Enum):
    UNRESOLVED = "unresolved"
    EXCLUDED = "excluded"


@dataclass(frozen=True, slots=True)
class WesternElectionalJudgementPolicy:
    profile_id: str = "western_electional_judgement_v1"
    profile_version: str = "1.0.0"
    composition_authority: str = "moira_owned_explicit_cross_source_composition"
    matter_policy: str = "one_admitted_named_matter_profile_required"
    perfection_policy: str = "lilly_1647_caller_declared_significators_required"
    rooted_context_policy: str = "source_applicable_rooted_context_else_not_applicable"
    natal_policy: str = "selected_matter_profile_owns_radicality_requirement"
    precedence_policy: str = "impediment_then_indeterminacy"
    completion_policy: str = "all_required_components_complete_with_constructive_perfection"
    unresolved_policy: str = "blocking_unresolved_requirements_propagate_indeterminacy"
    scoring: str = "not_provided"
    advice_language: str = "not_provided"
    recommendation_language: str = "not_provided"

    def __post_init__(self) -> None:
        for name, field in self.__dataclass_fields__.items():
            if getattr(self, name) != field.default:
                raise ValueError(f"{name} is fixed for the admitted Phase 8 policy")


WESTERN_ELECTIONAL_JUDGEMENT_V1 = WesternElectionalJudgementPolicy()


@dataclass(frozen=True, slots=True)
class WesternElectionalJudgementSelection:
    doctrine: WesternElectionalJudgementDoctrine
    matter_profile_id: str
    perfection_profile_id: str
    perfection_significator_a: str
    perfection_significator_b: str
    perfection_interval_days: float
    election_class: str
    natal_input_provided: bool
    natal_jd_ut: float | None
    natal_latitude: float | None
    natal_longitude: float | None
    natal_house_system: str | None
    unavoidable_time_urgency: bool | None
    moon_flow_previous_window: str | None
    moon_flow_previous_lookback_days: float | None
    moon_flow_modern: bool | None
    dorotheus_sign_nature_variant: str | None
    sahl_burnt_path_variant: str | None
    sahl_eighth_rule_variant: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.doctrine, WesternElectionalJudgementDoctrine):
            raise TypeError("doctrine must be a WesternElectionalJudgementDoctrine")
        expected_prefix = (
            "dorotheus_"
            if self.doctrine is WesternElectionalJudgementDoctrine.DOROTHEUS
            else "sahl_"
        )
        if not self.matter_profile_id.startswith(expected_prefix):
            raise ValueError("matter profile identity must match the selected doctrine")
        if self.perfection_profile_id != LILLY_1647_PERFECTION_V1.profile_id:
            raise ValueError("Phase 8 v1 admits only the named Lilly perfection profile")
        if self.perfection_significator_a not in _TRADITIONAL_PLANETS:
            raise ValueError("perfection_significator_a must be a traditional planet")
        if self.perfection_significator_b not in _TRADITIONAL_PLANETS:
            raise ValueError("perfection_significator_b must be a traditional planet")
        if self.perfection_significator_a == self.perfection_significator_b:
            raise ValueError("perfection significators must be distinct")
        if not math.isfinite(self.perfection_interval_days) or not (
            0.0 < self.perfection_interval_days <= LILLY_1647_PERFECTION_V1.max_span_days
        ):
            raise ValueError("perfection interval must be positive and at most 31 days")
        try:
            election_class = WesternElectionClass(self.election_class)
        except ValueError as exc:
            raise ValueError("election_class must name an admitted election class") from exc
        natal_values = (
            self.natal_jd_ut,
            self.natal_latitude,
            self.natal_longitude,
            self.natal_house_system,
        )
        if self.natal_input_provided != all(value is not None for value in natal_values):
            raise ValueError("natal_input_provided must derive from the complete natal bundle")
        if election_class is WesternElectionClass.EPHEMERAL and any(
            value is not None for value in natal_values
        ):
            raise ValueError("ephemeral selection rejects natal input")
        if election_class is WesternElectionClass.RADICAL and any(
            value is None for value in natal_values
        ):
            raise ValueError("radical selection requires the complete natal bundle")
        if self.unavoidable_time_urgency is not None and not isinstance(
            self.unavoidable_time_urgency, bool
        ):
            raise ValueError("unavoidable_time_urgency must be boolean when supplied")
        if self.moon_flow_previous_window == "current_sign":
            if self.moon_flow_previous_lookback_days is not None:
                raise ValueError("current-sign flow rejects a fixed lookback")
        elif self.moon_flow_previous_window == "fixed_lookback":
            if self.moon_flow_previous_lookback_days is None or not math.isfinite(
                self.moon_flow_previous_lookback_days
            ) or self.moon_flow_previous_lookback_days <= 0.0:
                raise ValueError("fixed-lookback flow requires a positive lookback")
        elif self.moon_flow_previous_window is not None:
            raise ValueError("moon flow must use current_sign or fixed_lookback")
        elif any(
            value is not None
            for value in (
                self.moon_flow_previous_lookback_days,
                self.moon_flow_modern,
            )
        ):
            raise ValueError("flow detail cannot exist without a previous-window policy")
        if self.moon_flow_previous_window is not None and not isinstance(
            self.moon_flow_modern, bool
        ):
            raise ValueError("moon flow must preserve the modern-body policy")
        if self.doctrine is WesternElectionalJudgementDoctrine.SAHL:
            if election_class is not WesternElectionClass.EPHEMERAL:
                raise ValueError("Sahl matter profiles admit only ephemeral elections")
            if (
                self.natal_input_provided
                or self.unavoidable_time_urgency is not None
                or self.moon_flow_previous_window is not None
                or self.dorotheus_sign_nature_variant is not None
            ):
                raise ValueError("Sahl selection rejects Dorothean natal, flow, and sign-nature inputs")
            if self.sahl_burnt_path_variant is None or self.sahl_eighth_rule_variant is None:
                raise ValueError("Sahl selection must preserve both explicit variant choices")
        else:
            if self.sahl_burnt_path_variant is not None or self.sahl_eighth_rule_variant is not None:
                raise ValueError("Dorotheus selection rejects Sahl variant choices")
            if self.matter_profile_id in _DOROTHEUS_SIGN_NATURE_PROFILE_IDS:
                if self.dorotheus_sign_nature_variant not in {
                    DorotheusSignNatureVariant.SOURCE_TEXT_UNRESOLVED.value,
                    DorotheusSignNatureVariant.LILLY_1647_ELEMENTAL_QUALITIES.value,
                }:
                    raise ValueError("land and sea travel selections must preserve sign-nature variant")
            elif self.dorotheus_sign_nature_variant is not None:
                raise ValueError("only land and sea travel selections carry sign-nature variant")


@dataclass(frozen=True, slots=True)
class WesternElectionalComponentSummary:
    component_id: str
    profile_id: str | None
    state: WesternElectionalComponentState
    explanation: str

    def __post_init__(self) -> None:
        if not self.component_id or not self.explanation:
            raise ValueError("component identity and derivation must remain visible")


@dataclass(frozen=True, slots=True)
class WesternElectionalRequirementWitness:
    requirement_id: str
    component_id: str
    state: WesternElectionalRequirementState
    blocking: bool
    explanation: str
    source_reference: str

    def __post_init__(self) -> None:
        if not self.requirement_id or not self.component_id:
            raise ValueError("requirement identity and component must remain visible")
        if not self.explanation or not self.source_reference:
            raise ValueError("requirement explanation and authority must remain visible")
        if self.state is WesternElectionalRequirementState.EXCLUDED and self.blocking:
            raise ValueError("an explicitly excluded requirement cannot block the selected profile")


@dataclass(frozen=True, slots=True)
class WesternElectionalJudgementEvaluation:
    jd_ut: float
    latitude: float
    longitude: float
    requested_house_system: str
    profile_id: str
    profile_version: str
    state: WesternElectionalJudgementState
    policy: WesternElectionalJudgementPolicy
    selection: WesternElectionalJudgementSelection
    general_moon_condition: object
    rooted_context: DorotheusRootedContextEvaluation | None
    matter_profile: DorotheusMatterProfileEvaluation | SahlMatterProfileEvaluation
    perfection_path: ClassicalPerfectionAnalysis
    components: tuple[WesternElectionalComponentSummary, ...]
    unresolved_requirements: tuple[WesternElectionalRequirementWitness, ...]
    excluded_requirements: tuple[WesternElectionalRequirementWitness, ...]
    reader_provenance: str
    authorities: tuple[str, ...]
    complete_electional_judgement: bool = True
    scoring: str = "not_provided"
    advice_language: str = "not_provided"
    recommendation_language: str = "not_provided"

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd_ut):
            raise ValueError("jd_ut must be finite")
        if not -90.0 <= self.latitude <= 90.0 or not -180.0 <= self.longitude <= 180.0:
            raise ValueError("judgement coordinates must be valid")
        if self.profile_id != self.policy.profile_id or self.profile_version != self.policy.profile_version:
            raise ValueError("judgement identity must derive from its policy")
        if self.matter_profile.profile_id.value != self.selection.matter_profile_id:
            raise ValueError("matter result must match the serialized selection")
        if self.general_moon_condition is not self.matter_profile.moon_condition:
            raise ValueError("general Moon condition must be the matter profile's exact vessel")
        if self.perfection_path.profile_id != self.selection.perfection_profile_id:
            raise ValueError("perfection result must match the serialized selection")
        if self.perfection_path.jd_start != self.jd_ut:
            raise ValueError("perfection path must begin at the elected instant")
        if self.rooted_context is not getattr(self.matter_profile, "rooted_context", None):
            raise ValueError("rooted context must be preserved from the selected matter profile")
        expected_ids = (
            "general_moon_condition",
            "rooted_context",
            "matter_profile",
            "perfection_path",
            "natal_or_radical_context",
            "fortification_and_remedy",
        )
        if tuple(item.component_id for item in self.components) != expected_ids:
            raise ValueError("judgement components must remain complete and source ordered")
        if any(item.state is not WesternElectionalRequirementState.UNRESOLVED for item in self.unresolved_requirements):
            raise ValueError("unresolved_requirements may contain only unresolved witnesses")
        if any(item.state is not WesternElectionalRequirementState.EXCLUDED for item in self.excluded_requirements):
            raise ValueError("excluded_requirements may contain only excluded witnesses")
        expected_state = _judgement_state(self.components, self.unresolved_requirements)
        if self.state is not expected_state:
            raise ValueError("judgement state must derive from visible components and requirements")
        if not self.reader_provenance or not self.authorities:
            raise ValueError("reader and authority provenance must remain visible")
        if not self.complete_electional_judgement:
            raise ValueError("this vessel is the complete judgement composition product")
        if any(value != "not_provided" for value in (
            self.scoring, self.advice_language, self.recommendation_language
        )):
            raise ValueError("Phase 8 cannot emit scoring, advice, or recommendation")


def _value(value: object) -> str:
    return str(getattr(value, "value", value))


def _summary(component_id: str, profile_id: str | None, state, explanation: str):
    return WesternElectionalComponentSummary(component_id, profile_id, state, explanation)


def _requirement(requirement_id: str, component_id: str, explanation: str, source_reference: str):
    return WesternElectionalRequirementWitness(
        requirement_id=requirement_id,
        component_id=component_id,
        state=WesternElectionalRequirementState.UNRESOLVED,
        blocking=True,
        explanation=explanation,
        source_reference=source_reference,
    )


def _excluded(requirement_id: str, component_id: str, explanation: str):
    return WesternElectionalRequirementWitness(
        requirement_id=requirement_id,
        component_id=component_id,
        state=WesternElectionalRequirementState.EXCLUDED,
        blocking=False,
        explanation=explanation,
        source_reference="western_electional_judgement_v1 composition boundary",
    )


def _moon_component(moon) -> WesternElectionalComponentSummary:
    status = _value(moon.status)
    state = (
        WesternElectionalComponentState.IMPEDED
        if "one_or_more" in status
        else WesternElectionalComponentState.INDETERMINATE
        if status == "indeterminate"
        else WesternElectionalComponentState.COMPLETE
    )
    return _summary(
        "general_moon_condition",
        moon.profile_id,
        state,
        "State is inherited without modification from the selected source-owned Moon profile.",
    )


def _matter_component(matter) -> WesternElectionalComponentSummary:
    status = _value(matter.status)
    state = (
        WesternElectionalComponentState.IMPEDED
        if "one_or_more" in status
        else WesternElectionalComponentState.INDETERMINATE
        if status == "indeterminate"
        else WesternElectionalComponentState.COMPLETE
    )
    return _summary(
        "matter_profile",
        matter.profile_id.value,
        state,
        "State is inherited from the complete named matter layer; descriptive profiles remain complete evidence rather than favorable verdicts.",
    )


def _rooted_component(rooted: DorotheusRootedContextEvaluation | None):
    if rooted is None:
        return _summary(
            "rooted_context",
            None,
            WesternElectionalComponentState.NOT_APPLICABLE,
            "The selected source profile does not own an admitted Dorothean root/outcome context.",
        )
    conditions = tuple(item.condition for item in rooted.matter_significators)
    supplementary = tuple(item.state for item in rooted.supplementary_indicators)
    state = (
        WesternElectionalComponentState.IMPEDED
        if DorotheusSignificatorCondition.ONE_OR_MORE_COMPUTED_IMPEDIMENTS in conditions
        else WesternElectionalComponentState.INDETERMINATE
        if DorotheusSignificatorCondition.INDETERMINATE in conditions
        or DorotheusSupplementaryIndicatorState.NOT_EVALUABLE in supplementary
        else WesternElectionalComponentState.COMPLETE
    )
    return _summary(
        "rooted_context",
        rooted.profile_id,
        state,
        "Dorothean root, outcome, significator fortification, and supplementary indicators remain visible and non-scored.",
    )


def _perfection_component(perfection: ClassicalPerfectionAnalysis):
    present = frozenset(perfection.present_kinds)
    has_impediment = bool(present & _IMPEDING_PERFECTIONS)
    has_constructive = bool(present & _CONSTRUCTIVE_PERFECTIONS)
    state = (
        WesternElectionalComponentState.IMPEDED
        if has_impediment
        else WesternElectionalComponentState.INDETERMINATE
        if perfection.indeterminate_kinds or not has_constructive
        else WesternElectionalComponentState.COMPLETE
    )
    return _summary(
        "perfection_path",
        perfection.profile_id,
        state,
        "Lilly's constructive and interrupting forms are classified from the returned exact event trace; absence of a constructive form cannot become completion.",
    )


def _fortification_component(matter, rooted):
    if rooted is None:
        state = _matter_component(matter).state
        explanation = (
            "The selected matter profile keeps its source-specific fortification "
            "and gate testimony inside its own clauses; no separate remedy object is invented."
        )
    else:
        root_state = _rooted_component(rooted).state
        remedy_states = tuple(_value(item.applicability) for item in matter.moon_condition.remedies)
        state = (
            WesternElectionalComponentState.IMPEDED
            if root_state is WesternElectionalComponentState.IMPEDED
            else WesternElectionalComponentState.INDETERMINATE
            if root_state is WesternElectionalComponentState.INDETERMINATE
            or "indeterminate" in remedy_states
            else WesternElectionalComponentState.COMPLETE
        )
        explanation = "Dorothean fortification testimony and the non-erasing remedy instruction are preserved from the embedded source components."
    return _summary("fortification_and_remedy", None, state, explanation)


def _requirements(matter, perfection, rooted):
    unresolved: list[WesternElectionalRequirementWitness] = []
    moon = matter.moon_condition
    for rule in moon.rules:
        if _value(rule.state) == "not_evaluable":
            unresolved.append(_requirement(
                f"moon_condition:{rule.rule_id}",
                "general_moon_condition",
                "The selected Moon profile preserves this source clause as not evaluable.",
                rule.source_reference,
            ))
    for clause in matter.clauses:
        if _value(clause.state) == "not_evaluable":
            unresolved.append(_requirement(
                f"matter_profile:{clause.clause_id}",
                "matter_profile",
                "The selected matter profile preserves this source clause as not evaluable.",
                clause.source_reference,
            ))
    if rooted is not None:
        for item in rooted.supplementary_indicators:
            if item.state is DorotheusSupplementaryIndicatorState.NOT_EVALUABLE:
                unresolved.append(_requirement(
                    f"rooted_context:{item.indicator_id}",
                    "rooted_context",
                    item.explanation,
                    item.source_reference,
                ))
        for significator in rooted.matter_significators:
            for testimony in significator.fortification_testimonies:
                if testimony.state is DorotheusFortificationTestimonyState.NOT_EVALUABLE:
                    unresolved.append(_requirement(
                        f"rooted_context:{significator.body}:{testimony.testimony_id}",
                        "fortification_and_remedy",
                        testimony.explanation,
                        testimony.source_reference,
                    ))
    for witness in perfection.witnesses:
        if witness.state is ClassicalPerfectionState.INDETERMINATE:
            unresolved.append(_requirement(
                f"perfection_path:{witness.kind.value}",
                "perfection_path",
                witness.explanation,
                witness.source_reference,
            ))
    if not frozenset(perfection.present_kinds) & _CONSTRUCTIVE_PERFECTIONS:
        unresolved.append(_requirement(
            "perfection_path:no_constructive_perfection",
            "perfection_path",
            "No direct perfection, translation, or collection is present in the declared interval.",
            "; ".join(perfection.authorities),
        ))
    excluded = [
        _excluded("scoring", "judgement", "Phase 9 ranking is not part of the Phase 8 judgement."),
        _excluded("advice_or_recommendation", "judgement", "No advice product has been admitted."),
    ]
    if rooted is None:
        if matter.profile_id.value.startswith("dorotheus_"):
            excluded.extend((
                _excluded("dorotheus_v31_rooted_context", "rooted_context", "The selected Dorothean source layer is not assigned to a V.31 matter family."),
                _excluded("standalone_remedy_profile", "fortification_and_remedy", "The selected Dorothean source layer has no separate remedy profile."),
            ))
        else:
            excluded.extend((
                _excluded("dorothean_rooted_context", "rooted_context", "A Dorothean context is not applied to a Sahl matter profile."),
                _excluded("standalone_remedy_profile", "fortification_and_remedy", "The admitted Sahl matter layer has no separate remedy profile."),
            ))
    return tuple(unresolved), tuple(excluded)


def _judgement_state(components, unresolved_requirements):
    states = tuple(item.state for item in components)
    if WesternElectionalComponentState.IMPEDED in states:
        return WesternElectionalJudgementState.IMPEDED
    if (
        WesternElectionalComponentState.INDETERMINATE in states
        or any(item.blocking for item in unresolved_requirements)
    ):
        return WesternElectionalJudgementState.INDETERMINATE
    return WesternElectionalJudgementState.COMPLETE


def assemble_western_electional_judgement(
    *,
    latitude: float,
    longitude: float,
    requested_house_system: str,
    selection: WesternElectionalJudgementSelection,
    matter_profile: DorotheusMatterProfileEvaluation | SahlMatterProfileEvaluation,
    perfection_path: ClassicalPerfectionAnalysis,
    policy: WesternElectionalJudgementPolicy = WESTERN_ELECTIONAL_JUDGEMENT_V1,
) -> WesternElectionalJudgementEvaluation:
    """Compose already-evaluated source components under the visible v1 law."""

    if not isinstance(policy, WesternElectionalJudgementPolicy):
        raise TypeError("policy must be a WesternElectionalJudgementPolicy")
    rooted = getattr(matter_profile, "rooted_context", None)
    moon = matter_profile.moon_condition
    components = (
        _moon_component(moon),
        _rooted_component(rooted),
        _matter_component(matter_profile),
        _perfection_component(perfection_path),
        _summary(
            "natal_or_radical_context",
            rooted.profile_id if rooted is not None else None,
            (
                WesternElectionalComponentState.COMPLETE
                if rooted is not None
                else WesternElectionalComponentState.NOT_APPLICABLE
            ),
            (
                "Dorothean radicality requirements are preserved by the embedded rooted context."
                if rooted is not None
                else "The selected matter profile does not admit a rooted natal or radicality layer."
            ),
        ),
        _fortification_component(matter_profile, rooted),
    )
    unresolved, excluded = _requirements(matter_profile, perfection_path, rooted)
    authorities = tuple(dict.fromkeys(
        (*matter_profile.authorities, *perfection_path.authorities, policy.composition_authority)
    ))
    if matter_profile.reader_provenance != perfection_path.reader_provenance:
        raise ValueError("matter and perfection components must share one reader provenance")
    return WesternElectionalJudgementEvaluation(
        jd_ut=matter_profile.jd_ut,
        latitude=latitude,
        longitude=longitude,
        requested_house_system=requested_house_system,
        profile_id=policy.profile_id,
        profile_version=policy.profile_version,
        state=_judgement_state(components, unresolved),
        policy=policy,
        selection=selection,
        general_moon_condition=moon,
        rooted_context=rooted,
        matter_profile=matter_profile,
        perfection_path=perfection_path,
        components=components,
        unresolved_requirements=unresolved,
        excluded_requirements=excluded,
        reader_provenance=matter_profile.reader_provenance,
        authorities=authorities,
    )


def western_electional_judgement_at(
    jd_ut: float,
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
    policy: WesternElectionalJudgementPolicy = WESTERN_ELECTIONAL_JUDGEMENT_V1,
) -> WesternElectionalJudgementEvaluation:
    """Evaluate and compose one admitted matter profile and perfection path."""

    if not isinstance(policy, WesternElectionalJudgementPolicy):
        raise TypeError("policy must be a WesternElectionalJudgementPolicy")
    resolved_reader = reader if reader is not None else get_reader()
    raw_profile_id = _value(matter_profile_id)
    natal_values = (natal_jd_ut, natal_latitude, natal_longitude, natal_house_system)
    natal_input_provided = any(value is not None for value in natal_values)
    flow_name = None
    flow_lookback = None
    flow_modern = None
    if moon_flow_policy is not None:
        flow_name = _value(moon_flow_policy.previous_window)
        flow_lookback = moon_flow_policy.previous_lookback_days
        flow_modern = moon_flow_policy.modern

    if raw_profile_id.startswith("dorotheus_"):
        doctrine = WesternElectionalJudgementDoctrine.DOROTHEUS
        profile_id = DorotheusMatterProfileId(raw_profile_id)
        if sahl_burnt_path_variant is not None or sahl_eighth_rule_variant is not None:
            raise ValueError("Dorotheus judgement rejects Sahl variant inputs")
        matter = dorotheus_matter_profile_at(
            jd_ut,
            latitude,
            longitude,
            house_system=house_system,
            profile_id=profile_id,
            election_class=election_class,
            natal_jd_ut=natal_jd_ut,
            natal_latitude=natal_latitude,
            natal_longitude=natal_longitude,
            natal_house_system=natal_house_system,
            unavoidable_time_urgency=unavoidable_time_urgency,
            reader=resolved_reader,
            house_policy=house_policy,
            moon_flow_policy=moon_flow_policy,
            sign_nature_variant=dorotheus_sign_nature_variant,
        )
        sign_nature_name = (
            matter.policy.sign_nature_variant.value
            if raw_profile_id in _DOROTHEUS_SIGN_NATURE_PROFILE_IDS
            else None
        )
        burnt_name = None
        eighth_name = None
    elif raw_profile_id.startswith("sahl_"):
        doctrine = WesternElectionalJudgementDoctrine.SAHL
        profile_id = SahlMatterProfileId(raw_profile_id)
        if WesternElectionClass(election_class) is not WesternElectionClass.EPHEMERAL:
            raise ValueError("Sahl judgement admits only ephemeral elections")
        if (
            natal_input_provided
            or moon_flow_policy is not None
            or unavoidable_time_urgency is not None
            or dorotheus_sign_nature_variant is not None
        ):
            raise ValueError("Sahl judgement rejects Dorothean natal, flow, urgency, and sign-nature inputs")
        if sahl_burnt_path_variant is None:
            raise ValueError("Sahl judgement requires an explicit burnt-path variant")
        matter = sahl_matter_profile_at(
            jd_ut,
            latitude,
            longitude,
            house_system=house_system,
            profile_id=profile_id,
            burnt_path_variant=sahl_burnt_path_variant,
            eighth_rule_variant=sahl_eighth_rule_variant,
            reader=resolved_reader,
            house_policy=house_policy,
        )
        sign_nature_name = None
        burnt_name = _value(sahl_burnt_path_variant)
        eighth_name = _value(matter.moon_condition.eighth_rule_variant)
    else:
        raise ValueError("matter_profile_id must name an admitted Sahl or Dorotheus profile")

    selection = WesternElectionalJudgementSelection(
        doctrine=doctrine,
        matter_profile_id=raw_profile_id,
        perfection_profile_id=LILLY_1647_PERFECTION_V1.profile_id,
        perfection_significator_a=perfection_significator_a,
        perfection_significator_b=perfection_significator_b,
        perfection_interval_days=perfection_interval_days,
        election_class=WesternElectionClass(election_class).value,
        natal_input_provided=natal_input_provided,
        natal_jd_ut=natal_jd_ut,
        natal_latitude=natal_latitude,
        natal_longitude=natal_longitude,
        natal_house_system=natal_house_system,
        unavoidable_time_urgency=unavoidable_time_urgency,
        moon_flow_previous_window=flow_name,
        moon_flow_previous_lookback_days=flow_lookback,
        moon_flow_modern=flow_modern,
        dorotheus_sign_nature_variant=sign_nature_name,
        sahl_burnt_path_variant=burnt_name,
        sahl_eighth_rule_variant=eighth_name,
    )
    chart = create_chart(
        jd_ut,
        latitude,
        longitude,
        house_system=house_system,
        bodies=[Body.SUN],
        reader=resolved_reader,
        policy=house_policy,
    )
    perfection = lilly_perfection_at(
        jd_ut,
        jd_ut + perfection_interval_days,
        perfection_significator_a,
        perfection_significator_b,
        is_day_chart=chart.is_day,
        reader=resolved_reader,
    )
    return assemble_western_electional_judgement(
        latitude=latitude,
        longitude=longitude,
        requested_house_system=house_system,
        selection=selection,
        matter_profile=matter,
        perfection_path=perfection,
        policy=policy,
    )
