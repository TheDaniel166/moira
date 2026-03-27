"""
Cygnus Constellation Oracle — moira/constellations/stars_cygnus.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Cygnus (IAU: Cyg).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Cygnus.
    - CYGNUS_STAR_NAMES mapping (constant → canonical name).
    - cygnus_star_at() dispatcher.
    - Per-star convenience functions (deneb_at, albireo_at, sador_at).
    - list_cygnus_stars() / available_cygnus_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    DENEB, ALBIREO, SADOR
    CYGNUS_STAR_NAMES
    cygnus_star_at() and all per-star _at() functions
    list_cygnus_stars(), available_cygnus_stars()

Stars sourced from the Sovereign Star Registry via Gaia DR3.
"""
from ..stars import star_at, GaiaStarPosition, list_stars

DENEB   = "Deneb"
ALBIREO = "Albireo"
SADOR   = "Sador"

CYGNUS_STAR_NAMES = {
    DENEB:   "Deneb",
    ALBIREO: "Albireo",
    SADOR:   "Sador",
}


def cygnus_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def deneb_at(jd_tt: float) -> StarPosition:
    return cygnus_star_at(DENEB, jd_tt)

def albireo_at(jd_tt: float) -> StarPosition:
    return cygnus_star_at(ALBIREO, jd_tt)

def sador_at(jd_tt: float) -> StarPosition:
    return cygnus_star_at(SADOR, jd_tt)


def list_cygnus_stars() -> list[str]:
    return list(CYGNUS_STAR_NAMES.values())


def available_cygnus_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in CYGNUS_STAR_NAMES.values() if name in catalog]
