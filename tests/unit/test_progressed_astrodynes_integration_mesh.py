"""Numerical-mesh invariants for progressed Astrodyne integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import moira.progressed_astrodynes_search as search_module
from moira.progressed_astrodynes_search import ProgressedContactQuery


_START = datetime(2000, 1, 1, tzinfo=timezone.utc)
_QUERY = ProgressedContactQuery(
    "Moon", "transit", "M.C.", "radical", "sextile"
)


class _CountingEvaluator:
    last_instance: "_CountingEvaluator | None" = None

    def __init__(self, *args, **kwargs) -> None:
        self.cache: dict[datetime, object] = {}
        type(self).last_instance = self

    def __call__(self, value: datetime):
        if value in self.cache:
            return self.cache[value]
        elapsed_days = (value - _START).total_seconds() / 86400.0
        moment = SimpleNamespace(
            distance_arcmin=30.0,
            power=1.0 + elapsed_days * elapsed_days,
            harmony=1.0 + elapsed_days * elapsed_days,
            discord=0.0,
        )
        result = SimpleNamespace(
            moment=moment,
            relation=SimpleNamespace(
                peak_truth=SimpleNamespace(peak_power=1.0)
            ),
        )
        self.cache[value] = result
        return result


@pytest.fixture(autouse=True)
def _counting_evaluator(monkeypatch: pytest.MonkeyPatch) -> None:
    _CountingEvaluator.last_instance = None
    monkeypatch.setattr(search_module, "_Evaluator", _CountingEvaluator)


def _integrate(*, hours: float, max_step_hours: float, max_samples: int):
    return search_module.integrate_progressed_influence(
        _START,
        _START,
        _START + timedelta(hours=hours),
        0.0,
        0.0,
        _QUERY,
        max_step_hours=max_step_hours,
        max_samples=max_samples,
        reader=object(),
    )


def test_odd_required_interval_count_rounds_to_nested_even_mesh() -> None:
    with pytest.raises(
        ValueError,
        match=r"requires 7 samples, exceeding max_samples=6",
    ):
        _integrate(hours=5.0, max_step_hours=1.0, max_samples=6)
    assert _CountingEvaluator.last_instance is None

    result = _integrate(hours=5.0, max_step_hours=1.0, max_samples=7)
    evaluator = _CountingEvaluator.last_instance

    assert evaluator is not None
    assert result.sample_count == 7
    assert len(evaluator.cache) == 7
    assert sorted(evaluator.cache) == [
        _START + timedelta(minutes=50 * index) for index in range(7)
    ]
    assert result.power_error_estimate_days == pytest.approx(
        abs(result.total_power_days - result.coarse_total_power_days) / 3.0
    )


def test_integration_requires_three_samples_for_real_refinement_pair() -> None:
    with pytest.raises(ValueError, match="max_samples must be at least 3"):
        _integrate(hours=1.0, max_step_hours=6.0, max_samples=2)
    assert _CountingEvaluator.last_instance is None

    result = _integrate(hours=1.0, max_step_hours=6.0, max_samples=3)
    evaluator = _CountingEvaluator.last_instance

    assert evaluator is not None
    assert result.sample_count == len(evaluator.cache) == 3
    assert sorted(evaluator.cache) == [
        _START,
        _START + timedelta(minutes=30),
        _START + timedelta(hours=1),
    ]
