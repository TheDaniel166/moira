"""
Corvus Constellation Oracle — moira/constellations/stars_corvus.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Corvus (IAU: Crv).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Corvus.
    - CORVUS_STAR_NAMES mapping (constant → canonical name).
    - corvus_star_at() dispatcher.
    - Per-star convenience functions (alchiba_at, kraz_at, …).
    - list_corvus_stars() / available_corvus_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ALCHIBA, KRAZ, GIENAH, ALGORAB, MINKAR, AVIS_SATYRA
    CORVUS_STAR_NAMES
    corvus_star_at() and all per-star _at() functions
    list_corvus_stars(), available_corvus_stars()

Stars sourced from the Sovereign Star Registry via Gaia DR3.
"""
from ..stars import star_at, GaiaStarPosition, list_stars

ALCHIBA     = "Alchiba"
KRAZ        = "Kraz"
GIENAH      = "Gienah"
ALGORAB     = "Algorab"
MINKAR      = "Minkar"
AVIS_SATYRA = "Avis Satyra"

CORVUS_STAR_NAMES = {
    ALCHIBA:     "Alchiba",
    KRAZ:        "Kraz",
    GIENAH:      "Gienah",
    ALGORAB:     "Algorab",
    MINKAR:      "Minkar",
    AVIS_SATYRA: "Avis Satyra",
}


def corvus_star_at(name: str, jd_tt: float) -> GaiaStarPosition:
    return star_at(name, jd_tt)


def alchiba_at(jd_tt: float) -> StarPosition:
    return corvus_star_at(ALCHIBA, jd_tt)

def kraz_at(jd_tt: float) -> StarPosition:
    return corvus_star_at(KRAZ, jd_tt)

def gienah_at(jd_tt: float) -> StarPosition:
    return corvus_star_at(GIENAH, jd_tt)

def algorab_at(jd_tt: float) -> StarPosition:
    return corvus_star_at(ALGORAB, jd_tt)

def minkar_at(jd_tt: float) -> StarPosition:
    return corvus_star_at(MINKAR, jd_tt)

def avis_satyra_at(jd_tt: float) -> StarPosition:
    return corvus_star_at(AVIS_SATYRA, jd_tt)


def list_corvus_stars() -> list[str]:
    return list(CORVUS_STAR_NAMES.values())


def available_corvus_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in CORVUS_STAR_NAMES.values() if name in catalog]
