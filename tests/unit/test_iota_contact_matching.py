from __future__ import annotations

import pytest

from tests.tools.iota_contact_matching import (
    TimedContactWitness,
    minimum_residual_monotone_same_kind_match,
)


def _contact(label: str, kind: str, epoch: float) -> TimedContactWitness:
    return TimedContactWitness(label=label, kind=kind, epoch_seconds=epoch)


def test_matcher_selects_minimum_total_residual_not_greedy_nearest() -> None:
    observed = (
        _contact("D1", "disappearance", 5.0),
        _contact("D2", "disappearance", 6.0),
    )
    model = (
        _contact("model-0", "disappearance", 0.0),
        _contact("model-1", "disappearance", 5.5),
        _contact("model-2", "disappearance", 100.0),
    )

    result = minimum_residual_monotone_same_kind_match(observed, model)

    # Greedily taking 5.5 for D1 would force D2 to 100.  The globally minimal
    # monotone assignment is 0 -> D1 and 5.5 -> D2.
    assert tuple(match.model_index for match in result.matches) == (0, 1)
    assert result.total_absolute_residual_seconds == pytest.approx(5.5)
    assert result.extra_model_indices == (2,)
    assert result.optimum_is_unique is True
    assert result.second_best_total_absolute_residual_seconds == pytest.approx(94.5)
    assert result.second_best_margin_seconds == pytest.approx(89.0)


def test_matcher_preserves_and_reports_same_kind_microcontacts() -> None:
    observed = (
        _contact("D1", "disappearance", 10.0),
        _contact("R1", "reappearance", 20.0),
    )
    model = (
        _contact("model-D1", "disappearance", 10.2),
        _contact("micro-R", "reappearance", 14.0),
        _contact("micro-D", "disappearance", 15.0),
        _contact("model-R1", "reappearance", 20.1),
    )

    result = minimum_residual_monotone_same_kind_match(observed, model)

    assert tuple(match.model_index for match in result.matches) == (0, 3)
    assert result.extra_model_indices == (1, 2)
    assert tuple(match.kind for match in result.matches) == (
        "disappearance",
        "reappearance",
    )
    assert result.maximum_absolute_residual_seconds == pytest.approx(0.2)
    assert result.optimum_is_unique is True
    assert result.second_best_margin_seconds is not None


def test_matcher_breaks_equal_cost_ties_by_earliest_model_indices() -> None:
    observed = (_contact("D1", "disappearance", 10.0),)
    model = (
        _contact("early", "disappearance", 9.0),
        _contact("late", "disappearance", 11.0),
    )

    result = minimum_residual_monotone_same_kind_match(observed, model)

    assert result.matches[0].model_index == 0
    assert result.extra_model_indices == (1,)
    assert result.optimum_is_unique is False
    assert result.second_best_total_absolute_residual_seconds == pytest.approx(1.0)
    assert result.second_best_margin_seconds == pytest.approx(0.0)


def test_empty_observed_chronology_has_one_unique_empty_assignment() -> None:
    result = minimum_residual_monotone_same_kind_match(
        (),
        (_contact("extra", "disappearance", 1.0),),
    )

    assert result.matches == ()
    assert result.extra_model_indices == (0,)
    assert result.optimum_is_unique is True
    assert result.second_best_total_absolute_residual_seconds is None
    assert result.second_best_margin_seconds is None


def test_matcher_rejects_impossible_or_unordered_chronologies() -> None:
    with pytest.raises(ValueError, match="no monotone same-kind match"):
        minimum_residual_monotone_same_kind_match(
            (_contact("D1", "disappearance", 1.0),),
            (_contact("R1", "reappearance", 1.0),),
        )

    with pytest.raises(ValueError, match="strictly chronological"):
        minimum_residual_monotone_same_kind_match(
            (
                _contact("D1", "disappearance", 2.0),
                _contact("R1", "reappearance", 1.0),
            ),
            (),
        )
