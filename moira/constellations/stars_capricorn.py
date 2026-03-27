"""
Capricorn Constellation Oracle — moira/constellations/stars_capricorn.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Capricorn (IAU: Cap).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Capricorn.
    - CAPRICORN_STAR_NAMES mapping (constant → canonical name).
    - capricorn_star_at() dispatcher.
    - Per-star convenience functions (algedi_at, dabih_at, …).
    - list_capricorn_stars() / available_capricorn_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ALGEDI, DABIH, NASHIRA, DENEB_ALGEDI, CASTRA, MARAKK,
    ALSHAT, BATEN_ALGIEDI
    CAPRICORN_STAR_NAMES
    capricorn_star_at() and all per-star _at() functions
    list_capricorn_stars(), available_capricorn_stars()

Stars sourced from the Sovereign Star Registry via Gaia DR3.
"""
from ..stars import star_at, GaiaStarPosition, list_stars

ALGEDI        = "Algedi"
DABIH         = "Dabih"
NASHIRA       = "Nashira"
DENEB_ALGEDI  = "Deneb Algedi"
CASTRA        = "Castra"
MARAKK        = "Marakk"
ALSHAT        = "Alshat"
BATEN_ALGIEDI = "Baten Algiedi"

CAPRICORN_STAR_NAMES = {
    ALGEDI:        "Algedi",
    DABIH:         "Dabih",
    NASHIRA:       "Nashira",
    DENEB_ALGEDI:  "Deneb Algedi",
    CASTRA:        "Castra",
    MARAKK:        "Marakk",
    ALSHAT:        "Alshat",
    BATEN_ALGIEDI: "Baten Algiedi",
}


def capricorn_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def algedi_at(jd_tt: float) -> StarPosition:
    return capricorn_star_at(ALGEDI, jd_tt)

def dabih_at(jd_tt: float) -> StarPosition:
    return capricorn_star_at(DABIH, jd_tt)

def nashira_at(jd_tt: float) -> StarPosition:
    return capricorn_star_at(NASHIRA, jd_tt)

def deneb_algedi_at(jd_tt: float) -> StarPosition:
    return capricorn_star_at(DENEB_ALGEDI, jd_tt)

def castra_at(jd_tt: float) -> StarPosition:
    return capricorn_star_at(CASTRA, jd_tt)

def marakk_at(jd_tt: float) -> StarPosition:
    return capricorn_star_at(MARAKK, jd_tt)

def alshat_at(jd_tt: float) -> StarPosition:
    return capricorn_star_at(ALSHAT, jd_tt)

def baten_algiedi_at(jd_tt: float) -> StarPosition:
    return capricorn_star_at(BATEN_ALGIEDI, jd_tt)


def list_capricorn_stars() -> list[str]:
    return list(CAPRICORN_STAR_NAMES.values())


def available_capricorn_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in CAPRICORN_STAR_NAMES.values() if name in catalog]
