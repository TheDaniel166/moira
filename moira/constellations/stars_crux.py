"""
Crux Constellation Oracle â€” moira/constellations/stars_crux.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Crux (IAU: Cru).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Crux.
    - CRUX_STAR_NAMES mapping (constant â†’ canonical name).
    - crux_star_at() dispatcher.
    - Per-star convenience functions (acrux_at, mimosa_at, â€¦).
    - list_crux_stars() / available_crux_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ACRUX, MIMOSA, GACRUX, DECRUX, JUXTA_CRUCEM
    CRUX_STAR_NAMES
    crux_star_at() and all per-star _at() functions
    list_crux_stars(), available_crux_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition, list_stars

ACRUX        = "Acrux"
MIMOSA       = "Mimosa"
GACRUX       = "Gacrux"
DECRUX       = "Decrux"
JUXTA_CRUCEM = "Juxta Crucem"

CRUX_STAR_NAMES = {
    ACRUX:        "Acrux",
    MIMOSA:       "Mimosa",
    GACRUX:       "Gacrux",
    DECRUX:       "Decrux",
    JUXTA_CRUCEM: "Juxta Crucem",
}


def crux_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def acrux_at(jd_tt: float) -> StarPosition:
    return crux_star_at(ACRUX, jd_tt)

def mimosa_at(jd_tt: float) -> StarPosition:
    return crux_star_at(MIMOSA, jd_tt)

def gacrux_at(jd_tt: float) -> StarPosition:
    return crux_star_at(GACRUX, jd_tt)

def decrux_at(jd_tt: float) -> StarPosition:
    return crux_star_at(DECRUX, jd_tt)

def juxta_crucem_at(jd_tt: float) -> StarPosition:
    return crux_star_at(JUXTA_CRUCEM, jd_tt)


def list_crux_stars() -> list[str]:
    return list(CRUX_STAR_NAMES.values())


def available_crux_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in CRUX_STAR_NAMES.values() if name in catalog]



