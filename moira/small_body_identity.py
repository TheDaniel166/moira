"""Catalog-backed identity resolution across Moira's small-body families.

Asteroid names and comet aliases are unique only inside their declared
families. Unified callers therefore resolve a globally unique name, provide
an explicit ``asteroid:`` or ``comet:`` qualifier, or receive a typed
ambiguity error. Dedicated asteroid and comet surfaces retain their
family-local compatibility rules.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal


SmallBodyFamily = Literal["asteroid", "comet"]
_FAMILIES: tuple[SmallBodyFamily, ...] = ("asteroid", "comet")


@dataclass(frozen=True, slots=True)
class SmallBodyIdentity:
    """One released small-body identity as seen by a unified caller."""

    family: SmallBodyFamily
    canonical_name: str
    naif_id: int
    matched_name: str
    is_alias: bool

    @property
    def qualified_name(self) -> str:
        """Return a globally explicit identifier for this identity."""

        return f"{self.family}:{self.canonical_name}"


@dataclass(frozen=True, slots=True)
class SmallBodyNameCollision:
    """A normalized label that names identities in more than one family."""

    normalized_name: str
    candidates: tuple[SmallBodyIdentity, ...]


class AmbiguousSmallBodyNameError(ValueError):
    """Raised when an unqualified name matches multiple small-body families."""

    def __init__(
        self,
        query: str,
        candidates: tuple[SmallBodyIdentity, ...],
    ) -> None:
        self.query = query
        self.candidates = candidates
        details = "; ".join(
            f"{candidate.family} {candidate.canonical_name!r} "
            f"(NAIF {candidate.naif_id})"
            for candidate in candidates
        )
        qualifications = " or ".join(
            repr(f"{candidate.family}:{query}")
            for candidate in candidates
        )
        super().__init__(
            f"small-body name {query!r} is ambiguous across families: "
            f"{details}. Use a family-qualified name such as {qualifications}."
        )


def _identity_key(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _add_identity(
    index: dict[str, SmallBodyIdentity],
    identity: SmallBodyIdentity,
) -> None:
    key = _identity_key(identity.matched_name)
    previous = index.get(key)
    if previous is None:
        index[key] = identity
        return
    if (
        previous.canonical_name != identity.canonical_name
        or previous.naif_id != identity.naif_id
    ):
        raise RuntimeError(
            f"{identity.family} catalog has an ambiguous normalized identity "
            f"for {identity.matched_name!r}"
        )


@lru_cache(maxsize=1)
def _family_indices() -> dict[SmallBodyFamily, dict[str, SmallBodyIdentity]]:
    # Lazy imports avoid a cycle: both position providers import planets.py.
    from .asteroids import ASTEROID_NAIF
    from .comets import _CANONICAL_COMET_NAIF, _COMET_ALIASES

    asteroid_index: dict[str, SmallBodyIdentity] = {}
    for name, naif_id in ASTEROID_NAIF.items():
        _add_identity(
            asteroid_index,
            SmallBodyIdentity(
                family="asteroid",
                canonical_name=name,
                naif_id=naif_id,
                matched_name=name,
                is_alias=False,
            ),
        )

    comet_index: dict[str, SmallBodyIdentity] = {}
    for name, naif_id in _CANONICAL_COMET_NAIF.items():
        _add_identity(
            comet_index,
            SmallBodyIdentity(
                family="comet",
                canonical_name=name,
                naif_id=naif_id,
                matched_name=name,
                is_alias=False,
            ),
        )
    for alias, canonical_name in _COMET_ALIASES.items():
        _add_identity(
            comet_index,
            SmallBodyIdentity(
                family="comet",
                canonical_name=canonical_name,
                naif_id=_CANONICAL_COMET_NAIF[canonical_name],
                matched_name=alias,
                is_alias=True,
            ),
        )

    return {
        "asteroid": asteroid_index,
        "comet": comet_index,
    }


def _coerce_family(value: str) -> SmallBodyFamily:
    family = _identity_key(value.strip())
    if family == "asteroid":
        return "asteroid"
    if family == "comet":
        return "comet"
    raise ValueError(
        f"unknown small-body family {value!r}; expected 'asteroid' or 'comet'"
    )


def _qualified_query(
    query: str,
    family: SmallBodyFamily | None,
) -> tuple[str, SmallBodyFamily | None]:
    prefix, separator, remainder = query.partition(":")
    if not separator:
        return query, family

    qualified_family = _coerce_family(prefix)
    name = remainder.strip()
    if not name:
        raise ValueError("family-qualified small-body names require a name after ':'")
    if family is not None and family != qualified_family:
        raise ValueError(
            f"small-body family {family!r} conflicts with qualifier "
            f"{qualified_family!r}"
        )
    return name, qualified_family


def resolve_small_body_identity(
    name: str,
    *,
    family: SmallBodyFamily | None = None,
) -> SmallBodyIdentity | None:
    """Resolve one identity without inventing cross-family precedence.

    ``family`` restricts lookup to a declared catalog. Unified string-only
    callers may express the same policy as ``"asteroid:Name"`` or
    ``"comet:Name"``. An unqualified label that occurs in both catalogs raises
    :class:`AmbiguousSmallBodyNameError`.
    """

    if not isinstance(name, str):
        raise TypeError("small-body name must be a string")
    query = name.strip()
    if not query:
        return None
    if family is not None:
        family = _coerce_family(family)
    query, family = _qualified_query(query, family)

    indices = _family_indices()
    key = _identity_key(query)
    if family is not None:
        return indices[family].get(key)

    candidates = tuple(
        identity
        for candidate_family in _FAMILIES
        if (identity := indices[candidate_family].get(key)) is not None
    )
    if len(candidates) > 1:
        raise AmbiguousSmallBodyNameError(query, candidates)
    return candidates[0] if candidates else None


def small_body_name_collisions() -> tuple[SmallBodyNameCollision, ...]:
    """Return every current cross-family collision in deterministic order."""

    indices = _family_indices()
    common_keys = sorted(set(indices["asteroid"]) & set(indices["comet"]))
    return tuple(
        SmallBodyNameCollision(
            normalized_name=key,
            candidates=(
                indices["asteroid"][key],
                indices["comet"][key],
            ),
        )
        for key in common_keys
    )


__all__ = [
    "AmbiguousSmallBodyNameError",
    "SmallBodyFamily",
    "SmallBodyIdentity",
    "SmallBodyNameCollision",
    "resolve_small_body_identity",
    "small_body_name_collisions",
]
