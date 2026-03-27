"""
Gemini Constellation Oracle — moira/constellations/stars_gemini.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Gemini (IAU: Gem).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Gemini.
    - GEMINI_STAR_NAMES mapping (constant → canonical name).
    - gemini_star_at() dispatcher.
    - Per-star convenience functions (castor_at, pollux_at, …).
    - list_gemini_stars() / available_gemini_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    CASTOR, POLLUX, ALHENA, WASAT
    GEMINI_STAR_NAMES
    gemini_star_at() and all per-star _at() functions
    list_gemini_stars(), available_gemini_stars()

Stars sourced from the Sovereign Star Registry via Gaia DR3.
"""
from ..stars import star_at, GaiaStarPosition, list_stars

CASTOR = "Castor"
POLLUX = "Pollux"
ALHENA = "Alhena"
WASAT  = "Wasat"

GEMINI_STAR_NAMES = {
    CASTOR: "Castor",
    POLLUX: "Pollux",
    ALHENA: "Alhena",
    WASAT:  "Wasat",
}


def gemini_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def castor_at(jd_tt: float) -> StarPosition:
    return gemini_star_at(CASTOR, jd_tt)

def pollux_at(jd_tt: float) -> StarPosition:
    return gemini_star_at(POLLUX, jd_tt)

def alhena_at(jd_tt: float) -> StarPosition:
    return gemini_star_at(ALHENA, jd_tt)

def wasat_at(jd_tt: float) -> StarPosition:
    return gemini_star_at(WASAT, jd_tt)


def list_gemini_stars() -> list[str]:
    return list(GEMINI_STAR_NAMES.values())


def available_gemini_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in GEMINI_STAR_NAMES.values() if name in catalog]
