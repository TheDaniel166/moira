"""Transparent caller-weighted ranking of complete Western judgements.

This module owns a Moira decision-support product, not a historical score.
It consumes complete Phase 8 judgements, admits only three source-visible
constructive-perfection presence signals, and partitions incomplete candidates
instead of converting uncertainty or impediment into numeric zero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from ._western_electional_context import WesternElectionClass
from ._western_electional_judgement import (
    WesternElectionalJudgementEvaluation,
    WesternElectionalJudgementState,
    WesternElectionalJudgementPolicy,
    WESTERN_ELECTIONAL_JUDGEMENT_V1,
    western_electional_judgement_at,
)
from ._western_electional_matter import DorotheusMatterProfileId
from ._western_electional_sahl_matter import SahlMatterProfileId
from .classical_perfection import LillyPerfectionKind
from .houses import HousePolicy
from .spk_reader import SpkReader, get_reader


__all__ = [
    "WesternElectionalRankingContributionId",
    "WesternElectionalRankingCandidateState",
    "ElectionalRankingPolicy",
    "WesternElectionalRankingWeight",
    "WesternElectionalRankingContribution",
    "WesternElectionalRankedCandidate",
    "WesternElectionalExcludedCandidate",
    "WesternElectionalRankingEvaluation",
    "WESTERN_ELECTIONAL_RANKING_V1",
    "assemble_western_electional_ranking",
    "western_electional_ranking_at",
]


class WesternElectionalRankingContributionId(str, Enum):
    """Vessel: Registry of western electional ranking contribution id values."""
    DIRECT_PERFECTION_PRESENT = "direct_perfection_present"
    TRANSLATION_OF_LIGHT_PRESENT = "translation_of_light_present"
    COLLECTION_OF_LIGHT_PRESENT = "collection_of_light_present"


class WesternElectionalRankingCandidateState(str, Enum):
    """Vessel: Registry of western electional ranking candidate state values."""
    RANKED = "ranked_complete_under_profile"
    EXCLUDED_IMPEDED = "excluded_impeded"
    EXCLUDED_INDETERMINATE = "excluded_indeterminate"


_CONTRIBUTION_PERFECTION_KIND = {
    WesternElectionalRankingContributionId.DIRECT_PERFECTION_PRESENT: (
        LillyPerfectionKind.DIRECT
    ),
    WesternElectionalRankingContributionId.TRANSLATION_OF_LIGHT_PRESENT: (
        LillyPerfectionKind.TRANSLATION
    ),
    WesternElectionalRankingContributionId.COLLECTION_OF_LIGHT_PRESENT: (
        LillyPerfectionKind.COLLECTION
    ),
}


@dataclass(frozen=True, slots=True)
class ElectionalRankingPolicy:
    """Vessel: Structured electional ranking policy data."""
    profile_id: str = "western_electional_ranking_v1"
    profile_version: str = "1.0.0"
    ranking_authority: str = "moira_owned_caller_weighted_numeric_decision_support"
    candidate_scope: str = "explicit_distinct_instants_same_phase8_selection"
    contribution_scope: str = "constructive_lilly_perfection_presence_only"
    weight_policy: str = "caller_supplied_unique_finite_nonzero_no_default"
    normalization_policy: str = "weighted_sum_divided_by_sum_absolute_weights"
    eligibility_policy: str = "complete_under_profile_only"
    incomplete_candidate_policy: str = "partition_with_complete_judgement_evidence"
    tie_break_policy: str = "score_descending_jd_ascending_input_index_ascending"
    min_candidates: int = 2
    max_candidates: int = 64
    score_minimum: float = -1.0
    score_maximum: float = 1.0
    advice_language: str = "not_admitted"
    recommendation_language: str = "not_admitted"
    empirical_claim: str = "not_provided"

    def __post_init__(self) -> None:
        for name, field in self.__dataclass_fields__.items():
            if getattr(self, name) != field.default:
                raise ValueError(f"{name} is fixed for the admitted Phase 9 policy")


WESTERN_ELECTIONAL_RANKING_V1 = ElectionalRankingPolicy()


@dataclass(frozen=True, slots=True)
class WesternElectionalRankingWeight:
    """Vessel: Structured western electional ranking weight data."""
    contribution_id: WesternElectionalRankingContributionId
    weight: float

    def __post_init__(self) -> None:
        try:
            contribution_id = WesternElectionalRankingContributionId(
                self.contribution_id
            )
        except ValueError as exc:
            raise ValueError("contribution_id is not admitted by Phase 9 v1") from exc
        object.__setattr__(self, "contribution_id", contribution_id)
        if isinstance(self.weight, bool) or not math.isfinite(float(self.weight)):
            raise ValueError("ranking weight must be finite")
        if float(self.weight) == 0.0:
            raise ValueError("ranking weight must be nonzero")
        object.__setattr__(self, "weight", float(self.weight))


@dataclass(frozen=True, slots=True)
class WesternElectionalRankingContribution:
    """Vessel: Structured western electional ranking contribution data."""
    contribution_id: WesternElectionalRankingContributionId
    raw_value: float
    normalization: str
    normalized_value: float
    weight: float
    weighted_value: float

    def __post_init__(self) -> None:
        if self.normalization != "binary_presence_identity":
            raise ValueError("Phase 9 v1 contributions use binary presence identity")
        numeric = (
            self.raw_value,
            self.normalized_value,
            self.weight,
            self.weighted_value,
        )
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("ranking contribution values must be finite")
        if self.raw_value not in (0.0, 1.0):
            raise ValueError("ranking contribution raw value must be binary")
        if self.normalized_value != self.raw_value:
            raise ValueError("binary presence normalization must be identity")
        if not math.isclose(
            self.weighted_value,
            self.normalized_value * self.weight,
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise ValueError("weighted value must derive from value and weight")


@dataclass(frozen=True, slots=True)
class WesternElectionalRankedCandidate:
    """Vessel: Structured western electional ranked candidate data."""
    input_index: int
    jd_ut: float
    state: WesternElectionalRankingCandidateState
    rank: int
    score: float
    normalization_divisor: float
    contributions: tuple[WesternElectionalRankingContribution, ...]
    judgement: WesternElectionalJudgementEvaluation

    def __post_init__(self) -> None:
        if self.input_index < 0 or self.rank < 1:
            raise ValueError("ranked candidate indices must be non-negative and ranked")
        if self.state is not WesternElectionalRankingCandidateState.RANKED:
            raise ValueError("ranked candidate must carry the ranked state")
        if self.judgement.state is not WesternElectionalJudgementState.COMPLETE:
            raise ValueError("only complete Phase 8 judgements may be ranked")
        if self.jd_ut != self.judgement.jd_ut:
            raise ValueError("ranked candidate epoch must match its judgement")
        if not math.isfinite(self.score) or not -1.0 <= self.score <= 1.0:
            raise ValueError("normalized ranking score must be in [-1, 1]")
        if not math.isfinite(self.normalization_divisor) or self.normalization_divisor <= 0.0:
            raise ValueError("normalization divisor must be positive and finite")
        expected = sum(item.weighted_value for item in self.contributions)
        if not math.isclose(
            self.score,
            expected / self.normalization_divisor,
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise ValueError("score must derive from every visible contribution")


@dataclass(frozen=True, slots=True)
class WesternElectionalExcludedCandidate:
    """Vessel: Structured western electional excluded candidate data."""
    input_index: int
    jd_ut: float
    state: WesternElectionalRankingCandidateState
    reason: str
    judgement: WesternElectionalJudgementEvaluation

    def __post_init__(self) -> None:
        expected = {
            WesternElectionalJudgementState.IMPEDED: (
                WesternElectionalRankingCandidateState.EXCLUDED_IMPEDED
            ),
            WesternElectionalJudgementState.INDETERMINATE: (
                WesternElectionalRankingCandidateState.EXCLUDED_INDETERMINATE
            ),
        }
        if self.input_index < 0 or self.jd_ut != self.judgement.jd_ut:
            raise ValueError("excluded candidate identity must match its judgement")
        if expected.get(self.judgement.state) is not self.state:
            raise ValueError("excluded candidate state must derive from its judgement")
        if not self.reason:
            raise ValueError("excluded candidate must preserve its partition reason")


@dataclass(frozen=True, slots=True)
class WesternElectionalRankingEvaluation:
    """Vessel: Structured western electional ranking evaluation data."""
    profile_id: str
    profile_version: str
    policy: ElectionalRankingPolicy
    weights: tuple[WesternElectionalRankingWeight, ...]
    candidate_jds: tuple[float, ...]
    ranked_candidates: tuple[WesternElectionalRankedCandidate, ...]
    excluded_candidates: tuple[WesternElectionalExcludedCandidate, ...]
    reader_provenance: str
    authorities: tuple[str, ...]
    ranking_is_decision_support: bool = True
    advice_language: str = "not_admitted"
    recommendation_language: str = "not_admitted"
    empirical_claim: str = "not_provided"

    def __post_init__(self) -> None:
        if self.profile_id != self.policy.profile_id or self.profile_version != self.policy.profile_version:
            raise ValueError("ranking identity must derive from its policy")
        if not self.policy.min_candidates <= len(self.candidate_jds) <= self.policy.max_candidates:
            raise ValueError("candidate count must remain within the admitted bounds")
        if len(set(self.candidate_jds)) != len(self.candidate_jds):
            raise ValueError("candidate instants must be distinct")
        if not all(math.isfinite(value) for value in self.candidate_jds):
            raise ValueError("candidate instants must be finite")
        if not self.weights or len({item.contribution_id for item in self.weights}) != len(self.weights):
            raise ValueError("ranking weights must be nonempty and unique")
        observed = {
            item.input_index for item in (*self.ranked_candidates, *self.excluded_candidates)
        }
        if observed != set(range(len(self.candidate_jds))):
            raise ValueError("every candidate must be ranked or explicitly excluded")
        ordered_candidates = tuple(sorted(
            (*self.ranked_candidates, *self.excluded_candidates),
            key=lambda item: item.input_index,
        ))
        if tuple(item.jd_ut for item in ordered_candidates) != self.candidate_jds:
            raise ValueError("candidate_jds must map exactly to every original input index")
        _validate_common_judgement_contract(
            tuple(item.judgement for item in ordered_candidates),
            self.policy,
        )
        weight_ids = tuple(item.contribution_id for item in self.weights)
        divisor = sum(abs(item.weight) for item in self.weights)
        for candidate in self.ranked_candidates:
            if tuple(item.contribution_id for item in candidate.contributions) != weight_ids:
                raise ValueError("every ranked candidate must expose every selected contribution")
            if not math.isclose(
                candidate.normalization_divisor,
                divisor,
                rel_tol=0.0,
                abs_tol=1e-15,
            ):
                raise ValueError("candidate normalization must derive from all selected weights")
            if any(
                contribution.weight != weight.weight
                for contribution, weight in zip(candidate.contributions, self.weights)
            ):
                raise ValueError("candidate contribution weights must match the ranking policy")
        expected_order = tuple(sorted(
            self.ranked_candidates,
            key=lambda item: (-item.score, item.jd_ut, item.input_index),
        ))
        if expected_order != self.ranked_candidates:
            raise ValueError("ranked candidates must follow the serialized tie-break law")
        if tuple(item.rank for item in self.ranked_candidates) != tuple(
            range(1, len(self.ranked_candidates) + 1)
        ):
            raise ValueError("candidate ranks must be complete and ordinal")
        if tuple(sorted(self.excluded_candidates, key=lambda item: item.input_index)) != self.excluded_candidates:
            raise ValueError("excluded candidates must preserve request order")
        if not self.reader_provenance or not self.authorities:
            raise ValueError("ranking must preserve reader and authority provenance")
        if not self.ranking_is_decision_support:
            raise ValueError("Phase 9 ranking must identify itself as decision support")
        if (
            self.advice_language != "not_admitted"
            or self.recommendation_language != "not_admitted"
            or self.empirical_claim != "not_provided"
        ):
            raise ValueError("Phase 9 v1 admits no advice, recommendation, or empirical claim")


def _coerce_weights(
    weights: Iterable[WesternElectionalRankingWeight],
) -> tuple[WesternElectionalRankingWeight, ...]:
    result = tuple(
        item if isinstance(item, WesternElectionalRankingWeight)
        else WesternElectionalRankingWeight(*item)
        for item in weights
    )
    if not result:
        raise ValueError("at least one caller-supplied ranking weight is required")
    if len({item.contribution_id for item in result}) != len(result):
        raise ValueError("ranking contribution weights must be unique")
    return result


def _validate_common_judgement_contract(
    judgements: tuple[WesternElectionalJudgementEvaluation, ...],
    policy: ElectionalRankingPolicy,
) -> None:
    if not policy.min_candidates <= len(judgements) <= policy.max_candidates:
        raise ValueError("Phase 9 requires between 2 and 64 candidate judgements")
    base = judgements[0]
    for item in judgements:
        if not isinstance(item, WesternElectionalJudgementEvaluation):
            raise TypeError("ranking candidates must be complete Phase 8 judgement vessels")
        if (
            item.latitude != base.latitude
            or item.longitude != base.longitude
            or item.requested_house_system != base.requested_house_system
            or item.selection != base.selection
            or item.policy != base.policy
        ):
            raise ValueError(
                "all ranking candidates must share coordinates, house system, doctrine, matter, inputs, and Phase 8 policy"
            )
        if item.reader_provenance != base.reader_provenance:
            raise ValueError("all ranking candidates must share one reader provenance")
    if len({item.jd_ut for item in judgements}) != len(judgements):
        raise ValueError("ranking candidate instants must be distinct")


def _contributions(
    judgement: WesternElectionalJudgementEvaluation,
    weights: tuple[WesternElectionalRankingWeight, ...],
) -> tuple[WesternElectionalRankingContribution, ...]:
    present = frozenset(judgement.perfection_path.present_kinds)
    return tuple(
        WesternElectionalRankingContribution(
            contribution_id=item.contribution_id,
            raw_value=(
                1.0
                if _CONTRIBUTION_PERFECTION_KIND[item.contribution_id] in present
                else 0.0
            ),
            normalization="binary_presence_identity",
            normalized_value=(
                1.0
                if _CONTRIBUTION_PERFECTION_KIND[item.contribution_id] in present
                else 0.0
            ),
            weight=item.weight,
            weighted_value=(
                item.weight
                if _CONTRIBUTION_PERFECTION_KIND[item.contribution_id] in present
                else 0.0
            ),
        )
        for item in weights
    )


def assemble_western_electional_ranking(
    judgements: Iterable[WesternElectionalJudgementEvaluation],
    weights: Iterable[WesternElectionalRankingWeight],
    *,
    policy: ElectionalRankingPolicy = WESTERN_ELECTIONAL_RANKING_V1,
) -> WesternElectionalRankingEvaluation:
    """Rank complete Phase 8 judgements and partition every incomplete one."""

    if not isinstance(policy, ElectionalRankingPolicy):
        raise TypeError("policy must be an ElectionalRankingPolicy")
    candidates = tuple(judgements)
    resolved_weights = _coerce_weights(weights)
    _validate_common_judgement_contract(candidates, policy)
    divisor = sum(abs(item.weight) for item in resolved_weights)
    eligible: list[tuple[int, WesternElectionalJudgementEvaluation, float, tuple]] = []
    excluded: list[WesternElectionalExcludedCandidate] = []
    for index, judgement in enumerate(candidates):
        if judgement.state is WesternElectionalJudgementState.COMPLETE:
            contributions = _contributions(judgement, resolved_weights)
            score = sum(item.weighted_value for item in contributions) / divisor
            eligible.append((index, judgement, score, contributions))
        else:
            state = (
                WesternElectionalRankingCandidateState.EXCLUDED_IMPEDED
                if judgement.state is WesternElectionalJudgementState.IMPEDED
                else WesternElectionalRankingCandidateState.EXCLUDED_INDETERMINATE
            )
            excluded.append(WesternElectionalExcludedCandidate(
                input_index=index,
                jd_ut=judgement.jd_ut,
                state=state,
                reason=(
                    "Phase 8 judgement is impeded and cannot enter the complete-candidate ranking."
                    if judgement.state is WesternElectionalJudgementState.IMPEDED
                    else "Phase 8 judgement is indeterminate and cannot be converted to numeric zero."
                ),
                judgement=judgement,
            ))
    eligible.sort(key=lambda item: (-item[2], item[1].jd_ut, item[0]))
    ranked = tuple(
        WesternElectionalRankedCandidate(
            input_index=index,
            jd_ut=judgement.jd_ut,
            state=WesternElectionalRankingCandidateState.RANKED,
            rank=rank,
            score=score,
            normalization_divisor=divisor,
            contributions=contributions,
            judgement=judgement,
        )
        for rank, (index, judgement, score, contributions) in enumerate(eligible, start=1)
    )
    authorities = tuple(dict.fromkeys((
        *(authority for item in candidates for authority in item.authorities),
        policy.ranking_authority,
    )))
    return WesternElectionalRankingEvaluation(
        profile_id=policy.profile_id,
        profile_version=policy.profile_version,
        policy=policy,
        weights=resolved_weights,
        candidate_jds=tuple(item.jd_ut for item in candidates),
        ranked_candidates=ranked,
        excluded_candidates=tuple(excluded),
        reader_provenance=candidates[0].reader_provenance,
        authorities=authorities,
    )


def western_electional_ranking_at(
    candidate_jds: Iterable[float],
    latitude: float,
    longitude: float,
    *,
    house_system: str,
    matter_profile_id: DorotheusMatterProfileId | SahlMatterProfileId | str,
    perfection_significator_a: str,
    perfection_significator_b: str,
    perfection_interval_days: float,
    weights: Iterable[WesternElectionalRankingWeight],
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
    ranking_policy: ElectionalRankingPolicy = WESTERN_ELECTIONAL_RANKING_V1,
) -> WesternElectionalRankingEvaluation:
    """Evaluate explicit candidate instants under one selection, then rank."""

    jds = tuple(candidate_jds)
    if not ranking_policy.min_candidates <= len(jds) <= ranking_policy.max_candidates:
        raise ValueError("Phase 9 requires between 2 and 64 candidate instants")
    if any(isinstance(value, bool) or not math.isfinite(float(value)) for value in jds):
        raise ValueError("candidate instants must be finite numbers")
    if len(set(float(value) for value in jds)) != len(jds):
        raise ValueError("candidate instants must be distinct")
    resolved_reader = reader if reader is not None else get_reader()
    judgements = tuple(
        western_electional_judgement_at(
            float(jd_ut),
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
        for jd_ut in jds
    )
    return assemble_western_electional_ranking(
        judgements,
        weights,
        policy=ranking_policy,
    )
