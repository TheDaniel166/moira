"""
Canis Major Constellation Oracle â€” moira/constellations/stars_canis_major.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Canis Major (IAU: CMa).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Canis Major.
    - CANIS_MAJOR_STAR_NAMES mapping (constant â†’ canonical name).
    - canis_major_star_at() dispatcher.
    - Per-star convenience functions (sirius_at, mirzam_at, â€¦).
    - list_canis_major_stars() / available_canis_major_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    SIRIUS, MIRZAM, MULIPHEIN, WEZEN, ADARA, FURUD, ALUDRA, UNURGUNITE
    CANIS_MAJOR_STAR_NAMES
    canis_major_star_at() and all per-star _at() functions
    list_canis_major_stars(), available_canis_major_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

SIRIUS      = "Sirius"
MIRZAM      = "Mirzam"
MULIPHEIN   = "Muliphein"
WEZEN       = "Wezen"
ADARA       = "Adhara"
FURUD       = "Furud"
ALUDRA      = "Aludra"
UNURGUNITE  = "Unurgunite"

CANIS_MAJOR_STAR_NAMES = {
    SIRIUS:     "Sirius",
    MIRZAM:     "Mirzam",
    MULIPHEIN:  "Muliphein",
    WEZEN:      "Wezen",
    ADARA:      "Adhara",
    FURUD:      "Furud",
    ALUDRA:     "Aludra",
    UNURGUNITE: "Unurgunite",
}


def canis_major_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


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
    return [name for name in CANIS_MAJOR_STAR_NAMES.values() if _star_name_is_resolvable(name)]





