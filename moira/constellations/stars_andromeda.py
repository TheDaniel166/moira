"""
Andromeda Constellation Oracle â€” moira/constellations/stars_andromeda.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Andromeda (IAU: And).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Andromeda.
    - ANDROMEDA_STAR_NAMES mapping (constant â†’ canonical name).
    - andromeda_star_at() dispatcher.
    - Per-star convenience functions (alpheratz_at, mirach_at, â€¦).
    - list_andromeda_stars() / available_andromeda_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ALPHERATZ, MIRACH, ALMACH, ADHIL, ADHAB, NEMBUS, VERITATE
    ANDROMEDA_STAR_NAMES
    andromeda_star_at() and all per-star _at() functions
    list_andromeda_stars(), available_andromeda_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

ALPHERATZ = "Alpheratz"
MIRACH    = "Mirach"
ALMACH    = "Almach"
ADHIL     = "Adhil"
ADHAB     = "Adhab"
NEMBUS    = "Nembus"
VERITATE  = "Veritate"

ANDROMEDA_STAR_NAMES = {
    ALPHERATZ: "Alpheratz",
    MIRACH:    "Mirach",
    ALMACH:    "Almach",
    ADHIL:     "Adhil",
    ADHAB:     "Adhab",
    NEMBUS:    "Nembus",
    VERITATE:  "Veritate",
}


def andromeda_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def alpheratz_at(jd_tt: float) -> StarPosition:
    return andromeda_star_at(ALPHERATZ, jd_tt)

def mirach_at(jd_tt: float) -> StarPosition:
    return andromeda_star_at(MIRACH, jd_tt)

def almach_at(jd_tt: float) -> StarPosition:
    return andromeda_star_at(ALMACH, jd_tt)

def adhil_at(jd_tt: float) -> StarPosition:
    return andromeda_star_at(ADHIL, jd_tt)

def adhab_at(jd_tt: float) -> StarPosition:
    return andromeda_star_at(ADHAB, jd_tt)

def nembus_at(jd_tt: float) -> StarPosition:
    return andromeda_star_at(NEMBUS, jd_tt)

def veritate_at(jd_tt: float) -> StarPosition:
    return andromeda_star_at(VERITATE, jd_tt)


def list_andromeda_stars() -> list[str]:
    return list(ANDROMEDA_STAR_NAMES.values())


def available_andromeda_stars() -> list[str]:
    return [name for name in ANDROMEDA_STAR_NAMES.values() if _star_name_is_resolvable(name)]





