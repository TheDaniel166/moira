"""Technique-neutral deterministic work limits; one meter per request."""
from math import isfinite


class SearchBudgetError(ValueError):
    """No incomplete successful result may escape an exhausted request."""
    label = "event search"

    def __init__(self, kind, limit, count, stage):
        self.limit_kind, self.limit, self.count, self.stage = kind, limit, count, stage
        super().__init__(f"{self.label} {kind} budget exceeded at {stage}: {count} > {limit}")


class WorkMeter:
    """Count declared work units; scientific owners supply immutable limits."""

    def __init__(self, limits, *, budget_error=SearchBudgetError, kinds):
        if not isinstance(budget_error, type) or not issubclass(budget_error, SearchBudgetError):
            raise ValueError("budget_error must preserve the canonical budget error contract")
        self.budget_error = budget_error
        self.limits = limits
        self.counts = dict.fromkeys(kinds, 0)
        self.stage = "preflight"
        for kind in self.counts:
            value = getattr(limits, "max_" + kind)
            if type(value) is not int or value <= 0:
                raise ValueError("work limits must be positive integers")

    def tick(self, kind, amount=1):
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not isfinite(amount) or amount < 0:
            raise ValueError("work increments must be finite and nonnegative")
        self.counts[kind] += amount
        maximum = getattr(self.limits, "max_" + kind)
        if self.counts[kind] > maximum:
            raise self.budget_error(kind, maximum, self.counts[kind], self.stage)
