"""
Public API drift guards for Moira's layered surface modules.

These tests enforce three structural invariants:

1. No symbol name appears more than once in any ``__all__``.
2. Every name declared in ``__all__`` resolves to a bound attribute at
   import time (no phantom exports).
3. The layering contract holds: essentials ⊆ classical ⊆ predictive ⊆ facade.

Failures here mean a module's ``__all__`` has drifted from its bindings,
or the composition chain between surface layers has been broken.
"""

from __future__ import annotations

import importlib

import pytest

# ---------------------------------------------------------------------------
# Surface modules under guard
# ---------------------------------------------------------------------------

_SURFACES = [
    "moira.essentials",
    "moira.classical",
    "moira.predictive",
    "moira.facade",
]


@pytest.fixture(scope="module", params=_SURFACES)
def surface(request: pytest.FixtureRequest):
    return importlib.import_module(request.param)


# ---------------------------------------------------------------------------
# Guard 1 — no duplicate names within a single __all__
# ---------------------------------------------------------------------------

def test_no_duplicate_names_in_all(surface) -> None:
    """Each name must appear exactly once in __all__."""
    names = surface.__all__
    seen: set[str] = set()
    duplicates = []
    for name in names:
        if name in seen:
            duplicates.append(name)
        seen.add(name)
    assert not duplicates, (
        f"{surface.__name__}.__all__ contains duplicate entries: {duplicates}"
    )


# ---------------------------------------------------------------------------
# Guard 2 — every declared name is actually bound
# ---------------------------------------------------------------------------

def test_all_names_are_bound(surface) -> None:
    """Every name in __all__ must resolve to a bound attribute."""
    missing = [name for name in surface.__all__ if not hasattr(surface, name)]
    assert not missing, (
        f"{surface.__name__}.__all__ declares unbound names: {missing}"
    )


# ---------------------------------------------------------------------------
# Guard 3 — layering invariants
# ---------------------------------------------------------------------------

def _all_set(module_name: str) -> set[str]:
    mod = importlib.import_module(module_name)
    return set(mod.__all__)


def test_essentials_subset_of_classical() -> None:
    """Every name in essentials.__all__ must also appear in classical.__all__."""
    missing = _all_set("moira.essentials") - _all_set("moira.classical")
    assert not missing, (
        f"classical.__all__ is missing these essentials names: {sorted(missing)}"
    )


def test_classical_subset_of_predictive() -> None:
    """Every name in classical.__all__ must also appear in predictive.__all__."""
    missing = _all_set("moira.classical") - _all_set("moira.predictive")
    assert not missing, (
        f"predictive.__all__ is missing these classical names: {sorted(missing)}"
    )


def test_predictive_subset_of_facade() -> None:
    """Every name in predictive.__all__ must also appear in facade.__all__."""
    missing = _all_set("moira.predictive") - _all_set("moira.facade")
    assert not missing, (
        f"facade.__all__ is missing these predictive names: {sorted(missing)}"
    )
