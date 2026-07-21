"""Stage 2K exact, explicit Sookshma temporal-selector contracts."""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import moira._pancha_pakshi as internal
import moira.pancha_pakshi as pakshi


_ROOT = Path(__file__).resolve().parents[2]
_PROFILE_ID = "bogamuni_chennai_2024_sookshma_temporal_selector"
_DECISION_ID = (
    "pancha_pakshi_bogamuni_2024_sookshma_temporal_selector_2026_07_21"
)
_PROFILE_PATH = (
    _ROOT
    / "moira"
    / "data"
    / "pancha_pakshi_bogamuni_chennai_2024_sookshma_temporal_selector.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_ADMISSION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_bogamuni_2024_sookshma_temporal_selector_2026_07_21.json"
)
_RESEARCH_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_vinadi_stage2j_research_2026_07_21.json"
)
_PROFILE_SHA256 = (
    "596c003c62ebbda913ca28aef318d77cb7b1cf42d92d3b1b7a20a44a01dd6526"
)
_MANIFEST_SHA256 = (
    "584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955"
)
_ADMISSION_SHA256 = (
    "10bcfbd70dda28fd399e5c95b8bfa237b8e48f3b2cb20901fc21e0261a73cf70"
)
_RESEARCH_SHA256 = (
    "d04ed0f3716fe605dc5d8172114dc759b30c4e87be968eebc36e35a23d789243"
)
_CAPABILITIES = (
    pakshi.PanchaPakshiCapability.SOOKSHMA_TEMPORAL_SELECTION,
)


def _digest(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def _document() -> dict:
    return json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))


def _parse(document: dict):
    return internal._parse_sookshma_selector_profile_document(
        document,
        admission_status=pakshi.PanchaPakshiAdmissionStatus.SOURCE_SCOPED_PUBLIC,
        default_selection_allowed=False,
        capabilities=_CAPABILITIES,
        admission_decision_id=_DECISION_ID,
    )


def _select(policy_id, parent_activity, elapsed):
    return pakshi.pancha_pakshi_sookshma_temporal_selection(
        _PROFILE_ID,
        policy_id=policy_id,
        parent_activity=parent_activity,
        elapsed_nazhigai=elapsed,
    )


def test_stage2k_profile_manifest_and_decision_are_exactly_bound() -> None:
    profile = internal.load_pancha_pakshi_profile(_PROFILE_ID)
    decision = json.loads(_ADMISSION_PATH.read_text(encoding="utf-8"))

    assert isinstance(profile, internal.PanchaPakshiSookshmaSelectorProfile)
    assert profile.product_kind == "sookshma_temporal_selector"
    assert profile.capabilities == _CAPABILITIES
    assert profile.default_selection_allowed is False
    assert profile.automatic_policy_selection == "forbidden"
    assert profile.uromarisi_composition_status == (
        "not_performed_requires_separate_explicit_cross_witness_decision"
    )
    assert _digest(_PROFILE_PATH) == _PROFILE_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert _digest(_ADMISSION_PATH) == _ADMISSION_SHA256
    assert _digest(_RESEARCH_PATH) == _RESEARCH_SHA256
    assert decision["prior_research"]["fixture_sha256"] == _RESEARCH_SHA256
    assert decision["primary_source"]["human_language_reviewer_dependency"] == (
        "none"
    )


def test_weighted_policy_rotates_source_order_and_closes_exactly() -> None:
    expected_durations = {
        pakshi.PanchaPakshiActivity.EAT: Fraction(3, 2),
        pakshi.PanchaPakshiActivity.WALK: Fraction(5, 4),
        pakshi.PanchaPakshiActivity.RULE: Fraction(2),
        pakshi.PanchaPakshiActivity.SLEEP: Fraction(3, 4),
        pakshi.PanchaPakshiActivity.DIE: Fraction(1, 2),
    }
    source_order = tuple(pakshi.PanchaPakshiActivity)

    for parent in source_order:
        result = _select(
            pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA,
            parent,
            Fraction(),
        )
        start = source_order.index(parent)
        expected_order = source_order[start:] + source_order[:start]
        assert tuple(cell.activity for cell in result.intervals) == expected_order
        assert tuple(cell.duration_nazhigai for cell in result.intervals) == tuple(
            expected_durations[activity] for activity in expected_order
        )
        assert result.intervals[0].start_nazhigai == 0
        assert result.intervals[-1].end_nazhigai == 6
        assert sum(
            (cell.duration_nazhigai for cell in result.intervals),
            Fraction(),
        ) == 6


def test_equal_fifths_are_exact_ordinal_only_half_open_cells() -> None:
    result = _select(
        pakshi.PanchaPakshiSookshmaSelectorPolicyId.EKA_SOOKSHMA_EQUAL_FIFTHS,
        pakshi.PanchaPakshiActivity.RULE,
        Fraction(12, 5),
    )

    assert tuple(cell.activity for cell in result.intervals) == (None,) * 5
    assert tuple(cell.start_nazhigai for cell in result.intervals) == tuple(
        Fraction(6 * index, 5) for index in range(5)
    )
    assert tuple(cell.end_nazhigai for cell in result.intervals) == tuple(
        Fraction(6 * index, 5) for index in range(1, 6)
    )
    assert {cell.duration_nazhigai for cell in result.intervals} == {
        Fraction(6, 5)
    }
    assert result.selected_ordinal == 3
    assert result.selected_interval.start_nazhigai == Fraction(12, 5)
    assert result.policy.activity_assignment_status == "not_attested"
    assert result.policy.activity_durations_nazhigai == ()


def test_half_open_boundaries_select_exactly_one_interval() -> None:
    policy = (
        pakshi.PanchaPakshiSookshmaSelectorPolicyId.EKA_SOOKSHMA_EQUAL_FIFTHS
    )
    for ordinal, boundary in enumerate(
        (Fraction(), Fraction(6, 5), Fraction(12, 5), Fraction(18, 5), Fraction(24, 5)),
        start=1,
    ):
        result = _select(policy, pakshi.PanchaPakshiActivity.EAT, boundary)
        assert result.selected_ordinal == ordinal
    assert _select(
        policy,
        pakshi.PanchaPakshiActivity.EAT,
        Fraction(6) - Fraction(1, 10_000),
    ).selected_ordinal == 5


def test_policy_and_exact_offset_are_mandatory_with_no_hidden_inputs() -> None:
    signature = inspect.signature(
        pakshi.pancha_pakshi_sookshma_temporal_selection
    )
    assert signature.parameters["policy_id"].default is inspect.Parameter.empty
    assert set(signature.parameters) == {
        "profile_id",
        "policy_id",
        "parent_activity",
        "elapsed_nazhigai",
    }
    with pytest.raises(TypeError, match="there is no default"):
        _select("bogamuni_2024_weighted_sookshma_samam_v1", pakshi.PanchaPakshiActivity.EAT, Fraction())
    with pytest.raises(TypeError, match="exact Fraction"):
        _select(
            pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA,
            pakshi.PanchaPakshiActivity.EAT,
            0.5,
        )
    for invalid in (Fraction(-1, 100), Fraction(6)):
        with pytest.raises(ValueError, match=r"\[0, 6\)"):
            _select(
                pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA,
                pakshi.PanchaPakshiActivity.EAT,
                invalid,
            )


def test_selection_vessels_are_immutable_and_revalidate_canonical_data() -> None:
    result = _select(
        pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA,
        pakshi.PanchaPakshiActivity.EAT,
        Fraction(1),
    )
    with pytest.raises(FrozenInstanceError):
        result.selected_ordinal = 5
    with pytest.raises(ValueError, match="canonical"):
        replace(result, intervals=tuple(reversed(result.intervals)))
    with pytest.raises(ValueError, match="canonical"):
        replace(
            result.policy,
            activity_durations_nazhigai=(
                (pakshi.PanchaPakshiActivity.EAT, Fraction(6)),
            ),
        )


@pytest.mark.parametrize(
    "mutation",
    (
        "default_policy",
        "weighted_duration",
        "equal_activity",
        "sequence_policy",
        "unknown_locator",
        "missing_policy",
    ),
)
def test_profile_parser_fails_closed_on_policy_drift(mutation: str) -> None:
    document = copy.deepcopy(_document())
    if mutation == "default_policy":
        document["policy_relation"]["default_policy_id"] = (
            "bogamuni_2024_weighted_sookshma_samam_v1"
        )
    elif mutation == "weighted_duration":
        document["selector_policies"][0]["activity_durations_nazhigai"][0][
            "duration"
        ] = {"numerator": 1, "denominator": 1}
    elif mutation == "equal_activity":
        document["selector_policies"][1]["activity_durations_nazhigai"] = [
            {
                "activity": "eat",
                "duration": {"numerator": 6, "denominator": 5},
            }
        ]
    elif mutation == "sequence_policy":
        document["selector_policies"][0]["sequence_policy"] = "invented"
    elif mutation == "unknown_locator":
        document["selector_policies"][0]["source_locators"][1] = "unknown"
    else:
        document["selector_policies"].pop()

    with pytest.raises(pakshi.PanchaPakshiDataError):
        _parse(document)


def test_prior_profiles_remain_separate_and_no_default() -> None:
    descriptors = {
        descriptor.profile_id: descriptor
        for descriptor in pakshi.available_pancha_pakshi_profiles()
    }
    assert len(descriptors) == 4
    assert descriptors[_PROFILE_ID].capabilities == _CAPABILITIES
    assert all(
        descriptor.default_selection_allowed is False
        for descriptor in descriptors.values()
    )
    assert descriptors[
        "bogamuni_chennai_2024_padu_bird_mapping"
    ].capabilities == (pakshi.PanchaPakshiCapability.PADU_BIRD_MAPPING,)
    assert descriptors[
        "bogamuni_chennai_2024_nakshatra_natal_identity"
    ].capabilities == (
        pakshi.PanchaPakshiCapability.NAKSHATRA_BIRD_MAPPING,
        pakshi.PanchaPakshiCapability.NATAL_IDENTITY,
    )
