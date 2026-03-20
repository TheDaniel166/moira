"""
Lyra Constellation Oracle — moira/constellations/stars_lyra.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Lyra (IAU: Lyr).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Lyra.
    - LYRA_STAR_NAMES mapping (constant → canonical name).
    - lyra_star_at() dispatcher.
    - Per-star convenience functions (vega_at, sheliak_at, …).
    - list_lyra_stars() / available_lyra_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    VEGA, SHELIAK, SULAPHAT, ALADFAR, ALATHFAR
    LYRA_STAR_NAMES
    lyra_star_at() and all per-star _at() functions
    list_lyra_stars(), available_lyra_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

VEGA     = "Vega"
SHELIAK  = "Sheliak"
SULAPHAT = "Sulaphat"
ALADFAR  = "Aladfar"
ALATHFAR = "Alathfar"

LYRA_STAR_NAMES = {
    VEGA:     "Vega",
    SHELIAK:  "Sheliak",
    SULAPHAT: "Sulaphat",
    ALADFAR:  "Aladfar",
    ALATHFAR: "Alathfar",
}


def lyra_star_at(name: str, jd_tt: float) -> StarPosition:
    return fixed_star_at(name, jd_tt)


def vega_at(jd_tt: float) -> StarPosition:
    return lyra_star_at(VEGA, jd_tt)

def sheliak_at(jd_tt: float) -> StarPosition:
    return lyra_star_at(SHELIAK, jd_tt)

def sulaphat_at(jd_tt: float) -> StarPosition:
    return lyra_star_at(SULAPHAT, jd_tt)

def aladfar_at(jd_tt: float) -> StarPosition:
    return lyra_star_at(ALADFAR, jd_tt)

def alathfar_at(jd_tt: float) -> StarPosition:
    return lyra_star_at(ALATHFAR, jd_tt)


def list_lyra_stars() -> list[str]:
    return list(LYRA_STAR_NAMES.values())


def available_lyra_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in LYRA_STAR_NAMES.values() if name in catalog]
