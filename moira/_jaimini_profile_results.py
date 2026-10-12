"""Internal failure boundary for computations on already admitted Jaimini inputs."""

from contextlib import contextmanager


class JaiminiInvariantError(RuntimeError):
    """Engine-produced evidence violates its contract; never a caller input error."""


@contextmanager
def result_invariants(family):
    """Translate result construction failures only after caller input admission."""
    try:
        yield
    except (ValueError, TypeError, KeyError) as exc:
        raise JaiminiInvariantError(f"invalid engine {family} result invariant") from exc
