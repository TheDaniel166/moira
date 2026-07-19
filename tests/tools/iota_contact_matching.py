"""Deterministic chronology matching for IOTA validation receipts.

This is validation tooling, not an engine surface.  Every observed contact is
matched to one later model contact of the same physical kind.  Model-only
microcontacts may remain unmatched and are returned explicitly rather than
being discarded or silently paired by nearest-neighbour order.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from typing import Sequence


@dataclass(frozen=True, slots=True)
class TimedContactWitness:
    """One validation contact on a common monotonically increasing clock."""

    label: str
    kind: str
    epoch_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("contact label must be a non-empty string")
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValueError("contact kind must be a non-empty string")
        if isinstance(self.epoch_seconds, bool) or not isinstance(
            self.epoch_seconds, (int, float)
        ):
            raise TypeError("contact epoch_seconds must be a real number")
        if not math.isfinite(float(self.epoch_seconds)):
            raise ValueError("contact epoch_seconds must be finite")
        object.__setattr__(self, "label", self.label.strip())
        object.__setattr__(self, "kind", self.kind.strip())
        object.__setattr__(self, "epoch_seconds", float(self.epoch_seconds))


@dataclass(frozen=True, slots=True)
class ContactMatch:
    """One observed-to-model contact pairing."""

    observed_index: int
    model_index: int
    observed_label: str
    kind: str
    residual_seconds: float


@dataclass(frozen=True, slots=True)
class MonotoneContactMatch:
    """Minimum-total-residual monotone same-kind matching receipt."""

    matches: tuple[ContactMatch, ...]
    extra_model_indices: tuple[int, ...]
    total_absolute_residual_seconds: float
    maximum_absolute_residual_seconds: float
    optimum_is_unique: bool
    second_best_total_absolute_residual_seconds: float | None
    second_best_margin_seconds: float | None


def _require_strict_chronology(
    name: str,
    contacts: Sequence[TimedContactWitness],
) -> tuple[TimedContactWitness, ...]:
    admitted = tuple(contacts)
    if any(not isinstance(item, TimedContactWitness) for item in admitted):
        raise TypeError(f"{name} must contain TimedContactWitness values")
    if any(
        right.epoch_seconds <= left.epoch_seconds
        for left, right in zip(admitted, admitted[1:])
    ):
        raise ValueError(f"{name} contacts must be strictly chronological")
    return admitted


def minimum_residual_monotone_same_kind_match(
    observed: Sequence[TimedContactWitness],
    model: Sequence[TimedContactWitness],
) -> MonotoneContactMatch:
    """Match all observed contacts to a monotone same-kind model subsequence.

    The primary objective is the sum of absolute timing residuals.  The two
    best distinct index assignments are retained so the receipt can distinguish
    a unique optimum from a deterministic lexicographic selection among exact
    ties.  Unselected model contacts are preserved in ``extra_model_indices``
    as explicit model-only topology.
    """

    observed_contacts = _require_strict_chronology("observed", observed)
    model_contacts = _require_strict_chronology("model", model)
    if not observed_contacts:
        return MonotoneContactMatch(
            matches=(),
            extra_model_indices=tuple(range(len(model_contacts))),
            total_absolute_residual_seconds=0.0,
            maximum_absolute_residual_seconds=0.0,
            optimum_is_unique=True,
            second_best_total_absolute_residual_seconds=None,
            second_best_margin_seconds=None,
        )

    @lru_cache(maxsize=None)
    def best_two_from(
        observed_index: int,
        minimum_model_index: int,
    ) -> tuple[tuple[float, tuple[int, ...]], ...]:
        if observed_index == len(observed_contacts):
            return ((0.0, ()),)

        witness = observed_contacts[observed_index]
        candidates: list[tuple[float, tuple[int, ...]]] = []
        for model_index in range(minimum_model_index, len(model_contacts)):
            candidate = model_contacts[model_index]
            if candidate.kind != witness.kind:
                continue
            for tail_cost, tail_indices in best_two_from(
                observed_index + 1,
                model_index + 1,
            ):
                residual = abs(candidate.epoch_seconds - witness.epoch_seconds)
                candidates.append(
                    (residual + tail_cost, (model_index,) + tail_indices)
                )
        if not candidates:
            return ()
        ordered = sorted(candidates, key=lambda item: (item[0], item[1]))
        distinct: list[tuple[float, tuple[int, ...]]] = []
        seen: set[tuple[int, ...]] = set()
        for candidate in ordered:
            if candidate[1] in seen:
                continue
            seen.add(candidate[1])
            distinct.append(candidate)
            if len(distinct) == 2:
                break
        return tuple(distinct)

    solutions = best_two_from(0, 0)
    if not solutions:
        raise ValueError(
            "model chronology has no monotone same-kind match for every "
            "observed contact"
        )

    solution = solutions[0]
    total_absolute_residual, model_indices = solution
    second_best_total = solutions[1][0] if len(solutions) == 2 else None
    second_best_margin = (
        None
        if second_best_total is None
        else second_best_total - total_absolute_residual
    )
    optimum_is_unique = (
        second_best_margin is None
        or not math.isclose(
            second_best_margin,
            0.0,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
    )
    matches = tuple(
        ContactMatch(
            observed_index=observed_index,
            model_index=model_index,
            observed_label=observed_contacts[observed_index].label,
            kind=observed_contacts[observed_index].kind,
            residual_seconds=(
                model_contacts[model_index].epoch_seconds
                - observed_contacts[observed_index].epoch_seconds
            ),
        )
        for observed_index, model_index in enumerate(model_indices)
    )
    selected = set(model_indices)
    extra_model_indices = tuple(
        index for index in range(len(model_contacts)) if index not in selected
    )
    maximum_absolute_residual = max(
        abs(match.residual_seconds) for match in matches
    )
    return MonotoneContactMatch(
        matches=matches,
        extra_model_indices=extra_model_indices,
        total_absolute_residual_seconds=total_absolute_residual,
        maximum_absolute_residual_seconds=maximum_absolute_residual,
        optimum_is_unique=optimum_is_unique,
        second_best_total_absolute_residual_seconds=second_best_total,
        second_best_margin_seconds=second_best_margin,
    )


__all__ = [
    "ContactMatch",
    "MonotoneContactMatch",
    "TimedContactWitness",
    "minimum_residual_monotone_same_kind_match",
]
