"""
Ursa Major Constellation Oracle â€” moira/constellations/stars_ursa_major.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Ursa Major (IAU: UMa).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Ursa Major.
    - URSA_MAJOR_STAR_NAMES mapping (constant â†’ canonical name).
    - ursa_major_star_at() dispatcher.
    - Per-star convenience functions (dubhe_at, merak_at, â€¦).
    - list_ursa_major_stars() / available_ursa_major_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    DUBHE, MERAK, PHECDA, MEGREZ, ALIOTH, MIZAR, ALKAID, AL_HAUD,
    TALITHA, TALITHA_AUSTRALIS, TANIA_BOREALIS, TANIA_AUSTRALIS,
    ALULA_BOREALIS, ALULA_AUSTRALIS, MUSCIDA, EL_KOPHRAH, ALCOR
    URSA_MAJOR_STAR_NAMES
    ursa_major_star_at() and all per-star _at() functions
    list_ursa_major_stars(), available_ursa_major_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition, list_stars

DUBHE              = "Dubhe"
MERAK              = "Merak"
PHECDA             = "Phecda"
MEGREZ             = "Megrez"
ALIOTH             = "Alioth"
MIZAR              = "Mizar"
ALKAID             = "Alkaid"
AL_HAUD            = "Al Haud"
TALITHA            = "Talitha"
TALITHA_AUSTRALIS  = "Talitha Australis"
TANIA_BOREALIS     = "Tania Borealis"
TANIA_AUSTRALIS    = "Tania Australis"
ALULA_BOREALIS     = "Alula Borealis"
ALULA_AUSTRALIS    = "Alula Australis"
MUSCIDA            = "Muscida"
EL_KOPHRAH         = "El Kophrah"
ALCOR              = "Alcor"

URSA_MAJOR_STAR_NAMES = {
    DUBHE:             "Dubhe",
    MERAK:             "Merak",
    PHECDA:            "Phecda",
    MEGREZ:            "Megrez",
    ALIOTH:            "Alioth",
    MIZAR:             "Mizar",
    ALKAID:            "Alkaid",
    AL_HAUD:           "Al Haud",
    TALITHA:           "Talitha",
    TALITHA_AUSTRALIS: "Talitha Australis",
    TANIA_BOREALIS:    "Tania Borealis",
    TANIA_AUSTRALIS:   "Tania Australis",
    ALULA_BOREALIS:    "Alula Borealis",
    ALULA_AUSTRALIS:   "Alula Australis",
    MUSCIDA:           "Muscida",
    EL_KOPHRAH:        "El Kophrah",
    ALCOR:             "Alcor",
}


def ursa_major_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def dubhe_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(DUBHE, jd_tt)

def merak_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(MERAK, jd_tt)

def phecda_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(PHECDA, jd_tt)

def megrez_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(MEGREZ, jd_tt)

def alioth_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(ALIOTH, jd_tt)

def mizar_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(MIZAR, jd_tt)

def alkaid_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(ALKAID, jd_tt)

def al_haud_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(AL_HAUD, jd_tt)

def talitha_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(TALITHA, jd_tt)

def talitha_australis_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(TALITHA_AUSTRALIS, jd_tt)

def tania_borealis_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(TANIA_BOREALIS, jd_tt)

def tania_australis_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(TANIA_AUSTRALIS, jd_tt)

def alula_borealis_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(ALULA_BOREALIS, jd_tt)

def alula_australis_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(ALULA_AUSTRALIS, jd_tt)

def muscida_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(MUSCIDA, jd_tt)

def el_kophrah_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(EL_KOPHRAH, jd_tt)

def alcor_at(jd_tt: float) -> StarPosition:
    return ursa_major_star_at(ALCOR, jd_tt)


def list_ursa_major_stars() -> list[str]:
    return list(URSA_MAJOR_STAR_NAMES.values())


def available_ursa_major_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in URSA_MAJOR_STAR_NAMES.values() if name in catalog]



