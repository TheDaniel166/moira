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
    - Per-star convenience functions (vega_at, sheliak_at, â€¦).
    - list_lyra_stars() / available_lyra_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    VEGA, SHELIAK, SULAPHAT, ALADFAR, ALATHFAR
    LYRA_STAR_NAMES
    lyra_star_at() and all per-star _at() functions
    list_lyra_stars(), available_lyra_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

VEGA     = "Vega"
SHELIAK  = "Sheliak"
SULAPHAT = "Sulafat"
ALADFAR  = "Aladfar"
ALATHFAR = "Aladfar"

LYRA_STAR_NAMES = {
    VEGA:     "Vega",
    SHELIAK:  "Sheliak",
    SULAPHAT: "Sulafat",
    ALADFAR:  "Aladfar",
    ALATHFAR: "Aladfar",
}


def lyra_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


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
    return [name for name in LYRA_STAR_NAMES.values() if _star_name_is_resolvable(name)]





