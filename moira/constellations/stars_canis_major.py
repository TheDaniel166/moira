"""
Canis Major Constellation Oracle — moira/constellations/stars_canis_major.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Canis Major (IAU: CMa).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Canis Major.
    - CANIS_MAJOR_STAR_NAMES mapping (constant → canonical name).
    - canis_major_star_at() dispatcher.
    - Per-star convenience functions (sirius_at, mirzam_at, …).
    - list_canis_major_stars() / available_canis_major_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    SIRIUS, MIRZAM, MULIPHEIN, WEZEN, ADARA, FURUD, ALUDRA, UNURGUNITE
    CANIS_MAJOR_STAR_NAMES
    canis_major_star_at() and all per-star _at() functions
    list_canis_major_stars(), available_canis_major_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

SIRIUS      = "Sirius"
MIRZAM      = "Mirzam"
MULIPHEIN   = "Muliphein"
WEZEN       = "Wezen"
ADARA       = "Adara"
FURUD       = "Furud"
ALUDRA      = "Aludra"
UNURGUNITE  = "Unurgunite"

CANIS_MAJOR_STAR_NAMES = {
    SIRIUS:     "Sirius",
    MIRZAM:     "Mirzam",
    MULIPHEIN:  "Muliphein",
    WEZEN:      "Wezen",
    ADARA:      "Adara",
    FURUD:      "Furud",
    ALUDRA:     "Aludra",
    UNURGUNITE: "Unurgunite",
}


def canis_major_star_at(name: str, jd_tt: float) -> StarPosition:
    return fixed_star_at(name, jd_tt)


def sirius_at(jd_tt: float) -> StarPosition:
    return canis_major_star_at(SIRIUS, jd_tt)

def mirzam_at(jd_tt: float) -> StarPosition:
    return canis_major_star_at(MIRZAM, jd_tt)

def muliphein_at(jd_tt: float) -> StarPosition:
    return canis_major_star_at(MULIPHEIN, jd_tt)

def wezen_at(jd_tt: float) -> StarPosition:
    return canis_major_star_at(WEZEN, jd_tt)

def adara_at(jd_tt: float) -> StarPosition:
    return canis_major_star_at(ADARA, jd_tt)

def furud_at(jd_tt: float) -> StarPosition:
    return canis_major_star_at(FURUD, jd_tt)

def aludra_at(jd_tt: float) -> StarPosition:
    return canis_major_star_at(ALUDRA, jd_tt)

def unurgunite_at(jd_tt: float) -> StarPosition:
    return canis_major_star_at(UNURGUNITE, jd_tt)


def list_canis_major_stars() -> list[str]:
    return list(CANIS_MAJOR_STAR_NAMES.values())


def available_canis_major_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in CANIS_MAJOR_STAR_NAMES.values() if name in catalog]
