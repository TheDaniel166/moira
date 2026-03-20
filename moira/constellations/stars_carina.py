"""
Carina Constellation Oracle — moira/constellations/stars_carina.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Carina (IAU: Car).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Carina.
    - CARINA_STAR_NAMES mapping (constant → canonical name).
    - carina_star_at() dispatcher.
    - Per-star convenience functions (canopus_at, miaplacidus_at, …).
    - list_carina_stars() / available_carina_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    CANOPUS, MIAPLACIDUS, AVIOR, ASPIDISKE, VATHORZ_POSTERIOR, VATHORZ_PRIOR
    CARINA_STAR_NAMES
    carina_star_at() and all per-star _at() functions
    list_carina_stars(), available_carina_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

CANOPUS           = "Canopus"
MIAPLACIDUS       = "Miaplacidus"
AVIOR             = "Avior"
ASPIDISKE         = "Aspidiske"
VATHORZ_POSTERIOR = "Vathorz Posterior"
VATHORZ_PRIOR     = "Vathorz Prior"

CARINA_STAR_NAMES = {
    CANOPUS:           "Canopus",
    MIAPLACIDUS:       "Miaplacidus",
    AVIOR:             "Avior",
    ASPIDISKE:         "Aspidiske",
    VATHORZ_POSTERIOR: "Vathorz Posterior",
    VATHORZ_PRIOR:     "Vathorz Prior",
}


def carina_star_at(name: str, jd_tt: float) -> StarPosition:
    return fixed_star_at(name, jd_tt)


def canopus_at(jd_tt: float) -> StarPosition:
    return carina_star_at(CANOPUS, jd_tt)

def miaplacidus_at(jd_tt: float) -> StarPosition:
    return carina_star_at(MIAPLACIDUS, jd_tt)

def avior_at(jd_tt: float) -> StarPosition:
    return carina_star_at(AVIOR, jd_tt)

def aspidiske_at(jd_tt: float) -> StarPosition:
    return carina_star_at(ASPIDISKE, jd_tt)

def vathorz_posterior_at(jd_tt: float) -> StarPosition:
    return carina_star_at(VATHORZ_POSTERIOR, jd_tt)

def vathorz_prior_at(jd_tt: float) -> StarPosition:
    return carina_star_at(VATHORZ_PRIOR, jd_tt)


def list_carina_stars() -> list[str]:
    return list(CARINA_STAR_NAMES.values())


def available_carina_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in CARINA_STAR_NAMES.values() if name in catalog]
