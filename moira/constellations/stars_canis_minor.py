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
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    PROCYON, GOMEISA
    CANIS_MINOR_STAR_NAMES
    canis_minor_star_at() and all per-star _at() functions
    list_canis_minor_stars(), available_canis_minor_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

PROCYON = "Procyon"
GOMEISA = "Gomeisa"

CANIS_MINOR_STAR_NAMES = {
    PROCYON: "Procyon",
    GOMEISA: "Gomeisa",
}


def canis_minor_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def procyon_at(jd_tt: float) -> StarPosition:
    return canis_minor_star_at(PROCYON, jd_tt)

def gomeisa_at(jd_tt: float) -> StarPosition:
    return canis_minor_star_at(GOMEISA, jd_tt)


def list_canis_minor_stars() -> list[str]:
    return list(CANIS_MINOR_STAR_NAMES.values())


def available_canis_minor_stars() -> list[str]:
    return [name for name in CANIS_MINOR_STAR_NAMES.values() if _star_name_is_resolvable(name)]





