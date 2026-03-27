"""
Cancer Constellation Oracle â€” moira/constellations/stars_cancer.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Cancer (IAU: Cnc).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Cancer.
    - CANCER_STAR_NAMES mapping (constant â†’ canonical name).
    - cancer_star_at() dispatcher.
    - Per-star convenience functions (acubens_at, al_tarf_at, â€¦).
    - list_cancer_stars() / available_cancer_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ACUBENS, AL_TARF, ASELLUS_BOREALIS, ASELLUS_AUSTRALIS, TEGMEN, DECAPODA
    CANCER_STAR_NAMES
    cancer_star_at() and all per-star _at() functions
    list_cancer_stars(), available_cancer_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

ACUBENS            = "Acubens"
AL_TARF            = "Tarf"
ASELLUS_BOREALIS   = "Asellus Borealis"
ASELLUS_AUSTRALIS  = "Asellus Australis"
TEGMEN             = "Tegmine"
DECAPODA           = "Decapoda"

CANCER_STAR_NAMES = {
    ACUBENS:           "Acubens",
    AL_TARF:           "Tarf",
    ASELLUS_BOREALIS:  "Asellus Borealis",
    ASELLUS_AUSTRALIS: "Asellus Australis",
    TEGMEN:            "Tegmine",
    DECAPODA:          "Decapoda",
}


def cancer_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def acubens_at(jd_tt: float) -> StarPosition:
    return cancer_star_at(ACUBENS, jd_tt)

def al_tarf_at(jd_tt: float) -> StarPosition:
    return cancer_star_at(AL_TARF, jd_tt)

def asellus_borealis_at(jd_tt: float) -> StarPosition:
    return cancer_star_at(ASELLUS_BOREALIS, jd_tt)

def asellus_australis_at(jd_tt: float) -> StarPosition:
    return cancer_star_at(ASELLUS_AUSTRALIS, jd_tt)

def tegmen_at(jd_tt: float) -> StarPosition:
    return cancer_star_at(TEGMEN, jd_tt)

def decapoda_at(jd_tt: float) -> StarPosition:
    return cancer_star_at(DECAPODA, jd_tt)


def list_cancer_stars() -> list[str]:
    return list(CANCER_STAR_NAMES.values())


def available_cancer_stars() -> list[str]:
    return [name for name in CANCER_STAR_NAMES.values() if _star_name_is_resolvable(name)]





