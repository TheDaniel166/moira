"""Engine-owned fixed-star selection doctrine for paran products.

This module defines identity membership only. It delegates all catalog
availability and position truth to :mod:`moira.stars` and reuses the existing
working, Royal, Behenian, and Ptolemaic star groups without copying data.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .behenian_stars import BEHENIAN_STAR_NAMES
from .fixed_star_groups import FIXED_STAR_NAMES, PTOLEMY_STARS
from .royal_stars import ROYAL_STAR_NAMES


class ParanStarTier(str, Enum):
    """Stable membership tags for the engine-owned paran star canon."""

    WORKING_CANON = "working_canon"
    ROYAL = "royal"
    BEHENIAN = "behenian"
    PTOLEMAIC = "ptolemaic"


@dataclass(frozen=True, slots=True)
class ParanStarCanonEntry:
    """One fixed-star identity and its paran-canon memberships."""

    name: str
    tiers: tuple[ParanStarTier, ...]
    default_enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("paran star canon name must be non-empty")
        if not self.tiers or self.tiers[0] is not ParanStarTier.WORKING_CANON:
            raise ValueError("paran star canon entries must belong to working_canon")
        if len(set(self.tiers)) != len(self.tiers):
            raise ValueError("paran star canon tiers must be unique")


_ROYAL_NAMES = frozenset(ROYAL_STAR_NAMES.values())
_BEHENIAN_NAMES = frozenset(BEHENIAN_STAR_NAMES.values())
_PTOLEMAIC_NAMES = frozenset(PTOLEMY_STARS)


def _tiers_for(name: str) -> tuple[ParanStarTier, ...]:
    tiers = [ParanStarTier.WORKING_CANON]
    if name in _ROYAL_NAMES:
        tiers.append(ParanStarTier.ROYAL)
    if name in _BEHENIAN_NAMES:
        tiers.append(ParanStarTier.BEHENIAN)
    if name in _PTOLEMAIC_NAMES:
        tiers.append(ParanStarTier.PTOLEMAIC)
    return tuple(tiers)


PARAN_STAR_CANON: tuple[ParanStarCanonEntry, ...] = tuple(
    ParanStarCanonEntry(name=name, tiers=_tiers_for(name))
    for name in FIXED_STAR_NAMES.values()
)


def paran_star_tiers() -> tuple[ParanStarTier, ...]:
    """Return supported tier identifiers in stable doctrine order."""

    return tuple(ParanStarTier)


def _resolve_tiers(
    tiers: Iterable[ParanStarTier | str] | None,
) -> frozenset[ParanStarTier] | None:
    if tiers is None:
        return None
    resolved: set[ParanStarTier] = set()
    for tier in tiers:
        try:
            resolved.add(tier if isinstance(tier, ParanStarTier) else ParanStarTier(tier))
        except ValueError as exc:
            allowed = ", ".join(item.value for item in ParanStarTier)
            raise ValueError(f"unknown paran star tier {tier!r}; expected one of: {allowed}") from exc
    return frozenset(resolved)


def list_paran_stars(
    *,
    tiers: Iterable[ParanStarTier | str] | None = None,
    available_only: bool = True,
) -> tuple[ParanStarCanonEntry, ...]:
    """Return canon entries matching any requested tier in stable order."""

    selected_tiers = _resolve_tiers(tiers)
    available: set[str] | None = None
    if available_only:
        from .stars import list_stars

        available = set(list_stars())

    return tuple(
        entry
        for entry in PARAN_STAR_CANON
        if (selected_tiers is None or selected_tiers.intersection(entry.tiers))
        and (available is None or entry.name in available)
    )


__all__ = [
    "PARAN_STAR_CANON",
    "ParanStarCanonEntry",
    "ParanStarTier",
    "list_paran_stars",
    "paran_star_tiers",
]
