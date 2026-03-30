"""
Perseus Constellation Oracle — moira/constellations/stars_perseus.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Perseus (IAU: Per).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Perseus.
    - PERSEUS_STAR_NAMES mapping (constant → canonical name).
    - perseus_star_at() dispatcher.
    - Per-star convenience functions (mirfak_at, algol_at, miram_at).
    - list_perseus_stars() / available_perseus_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    MIRFAK, ALGOL, MIRAM
    PERSEUS_STAR_NAMES
    perseus_star_at() and all per-star _at() functions
    list_perseus_stars(), available_perseus_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

MIRFAK = "Mirfak"
ALGOL  = "Algol"
MIRAM  = "Miram"

PERSEUS_STAR_NAMES = {
    MIRFAK: "Mirfak",
    ALGOL:  "Algol",
    MIRAM:  "Miram",
}


def perseus_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def mirfak_at(jd_tt: float) -> StarPosition:
    return perseus_star_at(MIRFAK, jd_tt)

def algol_at(jd_tt: float) -> StarPosition:
    return perseus_star_at(ALGOL, jd_tt)

def miram_at(jd_tt: float) -> StarPosition:
    return perseus_star_at(MIRAM, jd_tt)


def list_perseus_stars() -> list[str]:
    return list(PERSEUS_STAR_NAMES.values())


def available_perseus_stars() -> list[str]:
    return [name for name in PERSEUS_STAR_NAMES.values() if _star_name_is_resolvable(name)]





