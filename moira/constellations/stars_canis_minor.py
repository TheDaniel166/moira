"""
Canis Minor Constellation Oracle — moira/constellations/stars_canis_minor.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Canis Minor (IAU: CMi).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Canis Minor.
    - CANIS_MINOR_STAR_NAMES mapping (constant → canonical name).
    - canis_minor_star_at() dispatcher.
    - Per-star convenience functions (procyon_at, gomeisa_at).
    - list_canis_minor_stars() / available_canis_minor_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    PROCYON, GOMEISA
    CANIS_MINOR_STAR_NAMES
    canis_minor_star_at() and all per-star _at() functions
    list_canis_minor_stars(), available_canis_minor_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

PROCYON = "Procyon"
GOMEISA = "Gomeisa"

CANIS_MINOR_STAR_NAMES = {
    PROCYON: "Procyon",
    GOMEISA: "Gomeisa",
}


def canis_minor_star_at(name: str, jd_tt: float) -> StarPosition:
    return fixed_star_at(name, jd_tt)


def procyon_at(jd_tt: float) -> StarPosition:
    return canis_minor_star_at(PROCYON, jd_tt)

def gomeisa_at(jd_tt: float) -> StarPosition:
    return canis_minor_star_at(GOMEISA, jd_tt)


def list_canis_minor_stars() -> list[str]:
    return list(CANIS_MINOR_STAR_NAMES.values())


def available_canis_minor_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in CANIS_MINOR_STAR_NAMES.values() if name in catalog]
