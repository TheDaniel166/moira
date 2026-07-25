"""
Moira — Asteroid Family Oracle
================================

Archetype: Oracle

Purpose
-------
Governs lookup of Hirayama asteroid family membership from the current
Proper25 main-belt catalog plus the explicitly retained NASA PDS 2015 Hilda
and Jupiter Trojan populations, and detects family resonance across admitted
aspects.

- ``asteroid_family``        — compatibility display family for one asteroid
- ``asteroid_families``      — every catalog membership for one asteroid
- ``family_members``         — all catalog numbers belonging to a named family
- ``families_in_chart``      — group a set of asteroid numbers by shared origin
- ``find_resonant_aspects``  — tag aspects whose both bodies share a family origin
- ``resonance_network``      — group resonant aspects by family
- ``FamilyResonance``        — qualifier vessel for shared origin family
- ``ResonantAspect``         — result vessel for a qualified aspect

Boundary
--------
Owns: in-memory lookup table built from the bundled CSV at first call.
Delegates: nothing.  No ephemeris access, no network, no SPK reads.

Data source
-----------
Nesvorný, D. et al. (2026). "A Census Before Rubin: A Comprehensive
Asteroid Family Classification from 1.25 Million Objects."  Proper25
machine-readable membership distribution.

Proper25 excludes Hilda and Jupiter Trojan families.  Eight such families are
retained from NASA PDS ``ast.nesvorny.families`` V2.0, families_2015.

Membership is many-to-many.  Nested and overlapping HCM families are preserved
rather than collapsed.  ``asteroid_family`` remains a deterministic
compatibility display choice; it is not exclusive physical-origin truth.

Astrological significance
-------------------------
Hirayama families are clusters of asteroids sharing nearly identical
proper orbital elements — fragments of a single parent body shattered
by collision billions of years ago.  Two asteroids may occupy
completely different signs and houses yet be made of the same rock.
``families_in_chart`` surfaces this relationship for any set of bodies.

When two family members form an aspect, that aspect carries a qualifier
beyond its geometric type: both bodies share an origin.  This is the
*family resonance* layer — a new dimension of aspect qualification with
no precedent in traditional astrological software.  The resonance does
not change orb detection (the core aspect engine remains pure) but marks
the aspect as carrying the additional weight of shared physical origin.
``find_resonant_aspects`` and ``resonance_network`` expose this layer.

Import-time side effects
------------------------
None.  The lookup table is built lazily on first function call and
cached for the process lifetime.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .aspects import AspectData

__all__ = [
    "ASTEROID_FAMILY_CATALOG_SOURCE",
    "asteroid_family",
    "asteroid_families",
    "family_members",
    "families_in_chart",
    "find_resonant_aspects",
    "resonance_network",
    "FamilyResonance",
    "ResonantAspect",
]

_DATA_FILE = Path(__file__).resolve().parent / "data" / "asteroid_families.csv"
_METADATA_FILE = (
    Path(__file__).resolve().parent / "data" / "asteroid_families.metadata.json"
)

ASTEROID_FAMILY_CATALOG_SOURCE = (
    "Proper25_2026_plus_NASA_PDS_2015_excluded_populations"
)


@dataclass(frozen=True, slots=True)
class _FamilyCatalog:
    primary_by_number: dict[int, str]
    all_by_number: dict[int, tuple[str, ...]]
    by_family: dict[str, tuple[int, ...]]
    aliases: dict[str, str]


@lru_cache(maxsize=1)
def _load() -> _FamilyCatalog:
    """Build and cache complete and display lookup directions."""
    primary_by_number: dict[int, str] = {}
    all_by_number: dict[int, list[str]] = {}
    by_family: dict[str, set[int]] = {}

    with open(_DATA_FILE, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            number = int(row["asteroid_number"])
            family = row["family_name"]
            all_by_number.setdefault(number, []).append(family)
            by_family.setdefault(family, set()).add(number)
            if row["is_primary"] == "true":
                if number in primary_by_number:
                    raise ValueError(
                        f"multiple primary asteroid families for MPC number {number}"
                    )
                primary_by_number[number] = family

    missing_primary = set(all_by_number) - set(primary_by_number)
    if missing_primary:
        first = min(missing_primary)
        raise ValueError(f"missing primary asteroid family for MPC number {first}")

    metadata = json.loads(_METADATA_FILE.read_text(encoding="utf-8"))
    aliases = {
        str(alias): str(canonical)
        for alias, canonical in metadata.get("family_aliases", {}).items()
    }
    return _FamilyCatalog(
        primary_by_number=primary_by_number,
        all_by_number={
            number: tuple(families) for number, families in all_by_number.items()
        },
        by_family={
            family: tuple(sorted(members)) for family, members in by_family.items()
        },
        aliases=aliases,
    )


def asteroid_family(number: int) -> str | None:
    """Return the compatibility display family for a numbered asteroid.

    This does not assert exclusive membership.  Use :func:`asteroid_families`
    whenever complete nested and overlapping catalog membership is required.

    Parameters
    ----------
    number : MPC catalog number of the asteroid

    Returns
    -------
    Family name string, or None if the asteroid is not in any catalogued family.

    Examples
    --------
    >>> asteroid_family(158)
    'Koronis2'
    >>> asteroid_family(4)     # 4 Vesta
    'Vesta'
    >>> asteroid_family(1)     # 1 Ceres — not in any family
    None
    """
    return _load().primary_by_number.get(number)


def asteroid_families(number: int) -> list[str]:
    """Return every catalog family membership for a numbered asteroid.

    The display-primary family is first, followed by other memberships in
    stable source-specificity order.  An empty list means the asteroid has no
    membership in the admitted catalog, not that its orbit was independently
    proven to be non-familial.

    Examples
    --------
    >>> asteroid_families(8)
    ['Flora', 'Baptistina']
    >>> asteroid_families(1)
    []
    """
    return list(_load().all_by_number.get(number, ()))


def family_members(family_name: str) -> list[int]:
    """Return all catalogued asteroid numbers belonging to a named family.

    The match is case-sensitive and must be the exact name as it appears
    in the Nesvorný catalog (e.g. ``"Koronis"``, ``"Nysa-Polana"``).

    Parameters
    ----------
    family_name : family name as in the catalog

    Returns
    -------
    Sorted list of asteroid numbers.  Empty list if the name is unknown.

    Examples
    --------
    >>> len(family_members("Vesta"))    # 15,252 fragments of 4 Vesta
    15252
    >>> len(family_members("Koronis"))
    ...
    """
    catalog = _load()
    canonical_name = catalog.aliases.get(family_name, family_name)
    return list(catalog.by_family.get(canonical_name, ()))


def families_in_chart(numbers: list[int]) -> dict[str, list[int]]:
    """Group a set of numbered asteroids by their shared dynamical family.

    Bodies with no family membership are silently omitted.  Bodies from
    the same family appear together under one key regardless of their
    ecliptic positions — a relationship invisible to any longitude-only
    chart analysis.

    Parameters
    ----------
    numbers : list of MPC catalog numbers present in the chart

    Returns
    -------
    dict mapping family_name → list of numbers from the input that
    belong to that family, sorted by asteroid number.  Keys are sorted
    by family name.

    Example
    -------
    Given a chart containing overlapping Koronis-region memberships alongside
    4 (Vesta) and 1 (Ceres, uncatalogued):

    >>> families_in_chart([1, 4, 158, 167, 243, 832])
    {'Karin': [158, 167, 832], 'Koronis': [158, 167, 243, 832], 'Koronis2': [158, 167, 832], 'Vesta': [4]}
    """
    catalog = _load()
    groups: dict[str, set[int]] = {}
    for n in numbers:
        for family in catalog.all_by_number.get(n, ()):
            groups.setdefault(family, set()).add(n)
    return {k: sorted(v) for k, v in sorted(groups.items())}


# ---------------------------------------------------------------------------
# Resonance layer
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FamilyResonance:
    """Vessel: Qualifier vessel: both bodies in an aspect share a dynamical origin family.

    This is a new dimension of aspect qualification — not harmonic family
    (trine series, conjunction series) but *physical origin family*: the two
    bodies are fragments of the same parent body, shattered by collision
    billions of years ago.

    The resonance does not alter the aspect's geometric detection or orb.
    It is a qualifier that marks the aspect as carrying the additional weight
    of shared physical origin — present alongside the standard
    ``AspectClassification``, not replacing it.

    Structural invariants
    ---------------------
    - ``family_name`` is always a name present in the Nesvorný catalog.
    - ``body1_number`` and ``body2_number`` are both members of that family.
    - Both are MPC catalog numbers (not NAIF IDs).
    """
    family_name:   str
    body1_number:  int   # MPC catalog number of body1
    body2_number:  int   # MPC catalog number of body2


@dataclass(frozen=True, slots=True)
class ResonantAspect:
    """Vessel: A detected aspect paired with its family resonance qualifier.

    Wraps an ``AspectData`` vessel with a ``FamilyResonance`` qualifier.
    The aspect geometry is unchanged — only the interpretive layer is
    extended by the knowledge that both bodies share a physical origin.

    Structural invariants
    ---------------------
    - ``aspect.body1`` and ``aspect.body2`` correspond to
      ``resonance.body1_number`` and ``resonance.body2_number``
      via the ``body_catalog_numbers`` mapping supplied at detection time.
    - ``resonance.family_name`` is the same family for both bodies.
    """
    aspect:     "AspectData"
    resonance:  FamilyResonance


def find_resonant_aspects(
    aspects: "list[AspectData]",
    body_catalog_numbers: dict[str, int],
) -> list[ResonantAspect]:
    """Find aspects whose both bodies share a dynamical origin family.

    Scans the admitted aspects and returns one qualified result for every
    catalog family shared by both bodies.  Nested families therefore remain
    visible instead of being collapsed to either body's display-primary family.
    Bodies absent from ``body_catalog_numbers`` or not in any family are
    silently skipped — the function never raises on missing data.

    The orb and geometric classification of each aspect are unchanged.
    The ``FamilyResonance`` qualifier is purely additive.

    Parameters
    ----------
    aspects              : list of admitted AspectData (from ``find_aspects``)
    body_catalog_numbers : mapping of body name → MPC catalog number
                           for the asteroid bodies in the chart.
                           Non-asteroid bodies (Sun, Moon, planets) may be
                           omitted; aspects involving them will simply never
                           qualify as resonant.

    Returns
    -------
    List of ResonantAspect sorted by aspect orb (tightest first),
    preserving the same ordering convention as ``find_aspects``.
    """
    catalog = _load()
    results: list[ResonantAspect] = []

    for asp in aspects:
        n1 = body_catalog_numbers.get(asp.body1)
        n2 = body_catalog_numbers.get(asp.body2)
        if n1 is None or n2 is None:
            continue
        families1 = catalog.all_by_number.get(n1, ())
        families2 = set(catalog.all_by_number.get(n2, ()))
        for family in families1:
            if family not in families2:
                continue
            results.append(ResonantAspect(
                aspect=asp,
                resonance=FamilyResonance(
                    family_name=family,
                    body1_number=n1,
                    body2_number=n2,
                ),
            ))

    results.sort(key=lambda r: (r.aspect.orb, r.resonance.family_name))
    return results


def resonance_network(
    resonant_aspects: list[ResonantAspect],
) -> dict[str, list[ResonantAspect]]:
    """Group resonant aspects by family, forming a per-family sub-network.

    Each key is a family name; each value is the list of resonant aspects
    among that family's members, sorted by orb.  Together these form a
    network of qualifier relationships layered over the chart's aspect graph:
    each family's entry is its own sub-graph of the full aspect network,
    admitting only edges (aspects) where both endpoints (bodies) share
    that family's physical origin.

    A family with a single resonant aspect is a simple edge.  A family with
    multiple resonant aspects among three or more members forms a connected
    sub-graph — a resonance cluster — within the larger chart.

    Parameters
    ----------
    resonant_aspects : output of ``find_resonant_aspects``

    Returns
    -------
    dict mapping family_name → list[ResonantAspect], keys sorted
    alphabetically, values sorted by orb (tightest first).
    """
    network: dict[str, list[ResonantAspect]] = {}
    for ra in resonant_aspects:
        network.setdefault(ra.resonance.family_name, []).append(ra)
    return {k: sorted(v, key=lambda r: r.aspect.orb)
            for k, v in sorted(network.items())}
