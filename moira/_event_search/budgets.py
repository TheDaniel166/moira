"""Technique-neutral deterministic work limits; one meter per request."""
from math import isfinite


class SearchBudgetError(ValueError):
    """No incomplete successful result may escape an exhausted request."""
    label = "event search"

    def __init__(self, kind, limit, count, stage):
        self.limit_kind, self.limit, self.count, self.stage = kind, limit, count, stage
        super().__init__(f"{self.label} {kind} budget exceeded at {stage}: {count} > {limit}")


class WorkMeter:
    """RITE: Request-owned work accounting

    THEOREM: A declared work limit is enforced when its running count exceeds it.

    RITE OF PURPOSE:
        Count work units for one search request without choosing scientific
        tolerances, search domains, or the technique owner's limits.

    LAW OF OPERATION:
        Validate positive integer limits at construction and finite,
        nonnegative increments at tick(). Increment before checking the limit;
        an exhausted count remains recorded when the declared budget error is
        raised. The caller owns stage labels and the supplied limits object.
        Counts and stage are mutable, request-local state, not shared counters.

    Canon: Moira deterministic event-search budgets and SearchBudgetError.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira._event_search.budgets.WorkMeter",
      "risk": "medium",
      "api": {"frozen": [], "internal": ["__init__", "tick"]},
      "state": {"mutable": true, "owners": ["one search request"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {
        "thread": "request_local",
        "cross_thread_calls": "forbidden",
        "owner_thread_only_mutation": true
      },
      "failures": {
        "policy": "raise ValueError for invalid limits or increments, the configured SearchBudgetError subtype for exhaustion; unknown kinds or absent limits retain lookup errors"
      },
      "succession": {"stance": "internal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["budget semantics"]}
    }
    [/MACHINE_CONTRACT]
    """

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
