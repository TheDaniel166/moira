"""
Andromeda Constellation Oracle — moira/constellations/stars_andromeda.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Andromeda (IAU: And).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Andromeda.
    - ANDROMEDA_STAR_NAMES mapping (constant → canonical name).
    - andromeda_star_at() dispatcher.
    - Per-star convenience functions (alpheratz_at, mirach_at, …).
    - list_andromeda_stars() / available_andromeda_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ALPHERATZ, MIRACH, ALMACH, ADHIL, ADHAB, NEMBUS, VERITATE
    ANDROMEDA_STAR_NAMES
    andromeda_star_at() and all per-star _at() functions
    list_andromeda_stars(), available_andromeda_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

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
    return fixed_star_at(name, jd_tt)


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
    catalog = set(list_stars())
    return [name for name in ANDROMEDA_STAR_NAMES.values() if name in catalog]
