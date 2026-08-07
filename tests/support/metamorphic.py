"""Fail-closed primitives shared by reviewed metamorphic relations."""

from __future__ import annotations

import math
from numbers import Real


class MetamorphicViolation(AssertionError):
    """A relation failure whose exact predicate and mutant remain inspectable."""

    __slots__ = ("relation_id", "mutant_id", "metric", "observed", "limit")

    def __init__(
        self,
        *,
        relation_id: str,
        mutant_id: str,
        metric: str,
        observed: float,
        limit: float,
    ) -> None:
        self.relation_id = _nonblank_text(relation_id, role="relation_id")
        self.mutant_id = _nonblank_text(mutant_id, role="mutant_id")
        self.metric = _nonblank_text(metric, role="metric")
        self.observed = _finite_real(observed, role="observed")
        self.limit = _finite_real(limit, role="limit")
        if self.limit < 0.0:
            raise ValueError("limit must be nonnegative")
        super().__init__(
            f"{self.relation_id} [{self.mutant_id}]: {self.metric} "
            f"observed={self.observed:.17g}, limit={self.limit:.17g}"
        )


def _nonblank_text(value: object, *, role: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{role} must be nonblank text")
    return value


def _finite_real(value: object, *, role: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{role} must be a non-boolean real number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{role} must be finite")
    return converted


def require_relation(
    condition: bool,
    *,
    relation_id: str,
    mutant_id: str,
    metric: str,
    observed: float,
    limit: float,
) -> None:
    """Raise one typed failure when a reviewed relation predicate is false."""

    if type(condition) is not bool:
        raise TypeError("condition must be a boolean relation predicate")
    if condition:
        return
    raise MetamorphicViolation(
        relation_id=relation_id,
        mutant_id=mutant_id,
        metric=metric,
        observed=observed,
        limit=limit,
    )


__all__ = ["MetamorphicViolation", "require_relation"]
