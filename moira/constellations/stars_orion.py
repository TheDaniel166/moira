"""
Orion Constellation Oracle â€” moira/constellations/stars_orion.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Orion (IAU: Ori).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Orion.
    - ORION_STAR_NAMES mapping (constant â†’ canonical name).
    - orion_star_at() dispatcher.
    - Per-star convenience functions (betelgeuse_at, rigel_at, â€¦).
    - list_orion_stars() / available_orion_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    BETELGEUSE, RIGEL, BELLATRIX, MINTAKA, ALNILAM, ALNITAK,
    ENSIS, HATSYA, SAIPH, MEISSA, TABIT, THABIT
    ORION_STAR_NAMES
    orion_star_at() and all per-star _at() functions
    list_orion_stars(), available_orion_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition, list_stars

BETELGEUSE = "Betelgeuse"
RIGEL      = "Rigel"
BELLATRIX  = "Bellatrix"
MINTAKA    = "Mintaka"
ALNILAM    = "Alnilam"
ALNITAK    = "Alnitak"
ENSIS      = "Ensis"
HATSYA     = "Hatsya"
SAIPH      = "Saiph"
MEISSA     = "Meissa"
TABIT      = "Tabit"
THABIT     = "Thabit"

ORION_STAR_NAMES = {
    BETELGEUSE: "Betelgeuse",
    RIGEL:      "Rigel",
    BELLATRIX:  "Bellatrix",
    MINTAKA:    "Mintaka",
    ALNILAM:    "Alnilam",
    ALNITAK:    "Alnitak",
    ENSIS:      "Ensis",
    HATSYA:     "Hatsya",
    SAIPH:      "Saiph",
    MEISSA:     "Meissa",
    TABIT:      "Tabit",
    THABIT:     "Thabit",
}


def orion_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def betelgeuse_at(jd_tt: float) -> StarPosition:
    return orion_star_at(BETELGEUSE, jd_tt)

def rigel_at(jd_tt: float) -> StarPosition:
    return orion_star_at(RIGEL, jd_tt)

def bellatrix_at(jd_tt: float) -> StarPosition:
    return orion_star_at(BELLATRIX, jd_tt)

def mintaka_at(jd_tt: float) -> StarPosition:
    return orion_star_at(MINTAKA, jd_tt)

def alnilam_at(jd_tt: float) -> StarPosition:
    return orion_star_at(ALNILAM, jd_tt)

def alnitak_at(jd_tt: float) -> StarPosition:
    return orion_star_at(ALNITAK, jd_tt)

def ensis_at(jd_tt: float) -> StarPosition:
    return orion_star_at(ENSIS, jd_tt)

def hatsya_at(jd_tt: float) -> StarPosition:
    return orion_star_at(HATSYA, jd_tt)

def saiph_at(jd_tt: float) -> StarPosition:
    return orion_star_at(SAIPH, jd_tt)

def meissa_at(jd_tt: float) -> StarPosition:
    return orion_star_at(MEISSA, jd_tt)

def tabit_at(jd_tt: float) -> StarPosition:
    return orion_star_at(TABIT, jd_tt)

def thabit_at(jd_tt: float) -> StarPosition:
    return orion_star_at(THABIT, jd_tt)


def list_orion_stars() -> list[str]:
    return list(ORION_STAR_NAMES.values())


def available_orion_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in ORION_STAR_NAMES.values() if name in catalog]



