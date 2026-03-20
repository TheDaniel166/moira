"""
Scorpius Constellation Oracle — moira/constellations/stars_scorpius.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Scorpius (IAU: Sco).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Scorpius.
    - SCORPIUS_STAR_NAMES mapping (constant → canonical name).
    - scorpius_star_at() dispatcher.
    - Per-star convenience functions (antares_at, graffias_at, …).
    - list_scorpius_stars() / available_scorpius_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ANTARES, GRAFFIAS, ACRAB, DSCHUBBA, WEI, SARGAS, GIRTAB, SHAULA,
    XAMIDIMURA, JABBAH, FANG, IKLIL, ALNIYAT, LESATH, PIPIRIMA, FUYUE
    SCORPIUS_STAR_NAMES
    scorpius_star_at() and all per-star _at() functions
    list_scorpius_stars(), available_scorpius_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

ANTARES   = "Antares"
GRAFFIAS  = "Graffias"
ACRAB     = "Acrab"
DSCHUBBA  = "Dschubba"
WEI       = "Wei"
SARGAS    = "Sargas"
GIRTAB    = "Girtab"
SHAULA    = "Shaula"
XAMIDIMURA = "Xamidimura"
JABBAH    = "Jabbah"
FANG      = "Fang"
IKLIL     = "Iklil"
ALNIYAT   = "Alniyat"
LESATH    = "Lesath"
PIPIRIMA  = "Pipirima"
FUYUE     = "Fuyue"

SCORPIUS_STAR_NAMES = {
    ANTARES:    "Antares",
    GRAFFIAS:   "Graffias",
    ACRAB:      "Acrab",
    DSCHUBBA:   "Dschubba",
    WEI:        "Wei",
    SARGAS:     "Sargas",
    GIRTAB:     "Girtab",
    SHAULA:     "Shaula",
    XAMIDIMURA: "Xamidimura",
    JABBAH:     "Jabbah",
    FANG:       "Fang",
    IKLIL:      "Iklil",
    ALNIYAT:    "Alniyat",
    LESATH:     "Lesath",
    PIPIRIMA:   "Pipirima",
    FUYUE:      "Fuyue",
}


def scorpius_star_at(name: str, jd_tt: float) -> StarPosition:
    return fixed_star_at(name, jd_tt)


def antares_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(ANTARES, jd_tt)

def graffias_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(GRAFFIAS, jd_tt)

def acrab_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(ACRAB, jd_tt)

def dschubba_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(DSCHUBBA, jd_tt)

def wei_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(WEI, jd_tt)

def sargas_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(SARGAS, jd_tt)

def girtab_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(GIRTAB, jd_tt)

def shaula_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(SHAULA, jd_tt)

def xamidimura_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(XAMIDIMURA, jd_tt)

def jabbah_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(JABBAH, jd_tt)

def fang_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(FANG, jd_tt)

def iklil_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(IKLIL, jd_tt)

def alniyat_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(ALNIYAT, jd_tt)

def lesath_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(LESATH, jd_tt)

def pipirima_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(PIPIRIMA, jd_tt)

def fuyue_at(jd_tt: float) -> StarPosition:
    return scorpius_star_at(FUYUE, jd_tt)


def list_scorpius_stars() -> list[str]:
    return list(SCORPIUS_STAR_NAMES.values())


def available_scorpius_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in SCORPIUS_STAR_NAMES.values() if name in catalog]
