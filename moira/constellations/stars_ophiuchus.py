"""
Ophiuchus Constellation Oracle — moira/constellations/stars_ophiuchus.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Ophiuchus (IAU: Oph).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Ophiuchus.
    - OPHIUCHUS_STAR_NAMES mapping (constant → canonical name).
    - ophiuchus_star_at() dispatcher.
    - Per-star convenience functions (rasalhague_at, celbalrai_at, â€¦).
    - list_ophiuchus_stars() / available_ophiuchus_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    RASALHAGUE, CELBALRAI, AL_DURAJAH, YED_PRIOR
    OPHIUCHUS_STAR_NAMES
    ophiuchus_star_at() and all per-star _at() functions
    list_ophiuchus_stars(), available_ophiuchus_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

RASALHAGUE  = "Rasalhague"
CELBALRAI   = "Cebalrai"
AL_DURAJAH  = "Al Durajah"
YED_PRIOR   = "Yed Prior"

OPHIUCHUS_STAR_NAMES = {
    RASALHAGUE: "Rasalhague",
    CELBALRAI:  "Cebalrai",
    AL_DURAJAH: "Al Durajah",
    YED_PRIOR:  "Yed Prior",
}


def ophiuchus_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def rasalhague_at(jd_tt: float) -> StarPosition:
    return ophiuchus_star_at(RASALHAGUE, jd_tt)

def celbalrai_at(jd_tt: float) -> StarPosition:
    return ophiuchus_star_at(CELBALRAI, jd_tt)

def al_durajah_at(jd_tt: float) -> StarPosition:
    return ophiuchus_star_at(AL_DURAJAH, jd_tt)

def yed_prior_at(jd_tt: float) -> StarPosition:
    return ophiuchus_star_at(YED_PRIOR, jd_tt)


def list_ophiuchus_stars() -> list[str]:
    return list(OPHIUCHUS_STAR_NAMES.values())


def available_ophiuchus_stars() -> list[str]:
    return [name for name in OPHIUCHUS_STAR_NAMES.values() if _star_name_is_resolvable(name)]





