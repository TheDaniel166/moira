"""
Pisces Constellation Oracle — moira/constellations/stars_pisces.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Pisces (IAU: Psc).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Pisces.
    - PISCES_STAR_NAMES mapping (constant → canonical name).
    - pisces_star_at() dispatcher.
    - Per-star convenience functions (alrischa_at, fum_alsamakah_at, …).
    - list_pisces_stars() / available_pisces_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ALRISCHA, FUM_ALSAMAKAH, SIMMAH, LINTEUM, KAHT, AL_PHERG,
    TORCULARIS_SEPTENTRIONALIS
    PISCES_STAR_NAMES
    pisces_star_at() and all per-star _at() functions
    list_pisces_stars(), available_pisces_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

ALRISCHA                    = "Alrischa"
FUM_ALSAMAKAH               = "Fum Alsamakah"
SIMMAH                      = "Simmah"
LINTEUM                     = "Linteum"
KAHT                        = "Kaht"
AL_PHERG                    = "Al Pherg"
TORCULARIS_SEPTENTRIONALIS  = "Torcularis Septentrionalis"

PISCES_STAR_NAMES = {
    ALRISCHA:                   "Alrischa",
    FUM_ALSAMAKAH:              "Fum Alsamakah",
    SIMMAH:                     "Simmah",
    LINTEUM:                    "Linteum",
    KAHT:                       "Kaht",
    AL_PHERG:                   "Al Pherg",
    TORCULARIS_SEPTENTRIONALIS: "Torcularis Septentrionalis",
}


def pisces_star_at(name: str, jd_tt: float) -> StarPosition:
    return fixed_star_at(name, jd_tt)


def alrischa_at(jd_tt: float) -> StarPosition:
    return pisces_star_at(ALRISCHA, jd_tt)

def fum_alsamakah_at(jd_tt: float) -> StarPosition:
    return pisces_star_at(FUM_ALSAMAKAH, jd_tt)

def simmah_at(jd_tt: float) -> StarPosition:
    return pisces_star_at(SIMMAH, jd_tt)

def linteum_at(jd_tt: float) -> StarPosition:
    return pisces_star_at(LINTEUM, jd_tt)

def kaht_at(jd_tt: float) -> StarPosition:
    return pisces_star_at(KAHT, jd_tt)

def al_pherg_at(jd_tt: float) -> StarPosition:
    return pisces_star_at(AL_PHERG, jd_tt)

def torcularis_septentrionalis_at(jd_tt: float) -> StarPosition:
    return pisces_star_at(TORCULARIS_SEPTENTRIONALIS, jd_tt)


def list_pisces_stars() -> list[str]:
    return list(PISCES_STAR_NAMES.values())


def available_pisces_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in PISCES_STAR_NAMES.values() if name in catalog]
