"""
Crater Constellation Oracle — moira/constellations/stars_crater.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Crater (IAU: Crt).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Crater.
    - CRATER_STAR_NAMES mapping (constant → canonical name).
    - crater_star_at() dispatcher.
    - Per-star convenience functions (alkes_at, alsharasif_at, labrum_at).
    - list_crater_stars() / available_crater_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ALKES, ALSHARASIF, LABRUM
    CRATER_STAR_NAMES
    crater_star_at() and all per-star _at() functions
    list_crater_stars(), available_crater_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

ALKES       = "Alkes"
ALSHARASIF  = "Alsharasif"
LABRUM      = "Labrum"

CRATER_STAR_NAMES = {
    ALKES:      "Alkes",
    ALSHARASIF: "Alsharasif",
    LABRUM:     "Labrum",
}


def crater_star_at(name: str, jd_tt: float) -> StarPosition:
    return fixed_star_at(name, jd_tt)


def alkes_at(jd_tt: float) -> StarPosition:
    return crater_star_at(ALKES, jd_tt)

def alsharasif_at(jd_tt: float) -> StarPosition:
    return crater_star_at(ALSHARASIF, jd_tt)

def labrum_at(jd_tt: float) -> StarPosition:
    return crater_star_at(LABRUM, jd_tt)


def list_crater_stars() -> list[str]:
    return list(CRATER_STAR_NAMES.values())


def available_crater_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in CRATER_STAR_NAMES.values() if name in catalog]
