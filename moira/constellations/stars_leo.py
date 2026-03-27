"""
Leo Constellation Oracle â€” moira/constellations/stars_leo.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Leo (IAU: Leo).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Leo.
    - LEO_STAR_NAMES mapping (constant â†’ canonical name).
    - leo_star_at() dispatcher.
    - Per-star convenience functions (regulus_at, denebola_at, â€¦).
    - list_leo_stars() / available_leo_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    REGULUS, DENEBOLA, ALGIEBA, ZOSMA, RAS_ELASED_AUSTRALIS, ADHAFERA,
    AL_JABHAH, TSE_TSENG, ALMINHAR, ALTERF, RAS_ELASED_BOREALIS,
    SUBRA, COXA, SHIR
    LEO_STAR_NAMES
    leo_star_at() and all per-star _at() functions
    list_leo_stars(), available_leo_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition, list_stars

REGULUS               = "Regulus"
DENEBOLA              = "Denebola"
ALGIEBA               = "Algieba"
ZOSMA                 = "Zosma"
RAS_ELASED_AUSTRALIS  = "Ras Elased Australis"
ADHAFERA              = "Adhafera"
AL_JABHAH             = "Al Jabhah"
TSE_TSENG             = "Tse Tseng"
ALMINHAR              = "Alminhar"
ALTERF                = "Alterf"
RAS_ELASED_BOREALIS   = "Ras Elased Borealis"
SUBRA                 = "Subra"
COXA                  = "Coxa"
SHIR                  = "Shir"

LEO_STAR_NAMES = {
    REGULUS:              "Regulus",
    DENEBOLA:             "Denebola",
    ALGIEBA:              "Algieba",
    ZOSMA:                "Zosma",
    RAS_ELASED_AUSTRALIS: "Ras Elased Australis",
    ADHAFERA:             "Adhafera",
    AL_JABHAH:            "Al Jabhah",
    TSE_TSENG:            "Tse Tseng",
    ALMINHAR:             "Alminhar",
    ALTERF:               "Alterf",
    RAS_ELASED_BOREALIS:  "Ras Elased Borealis",
    SUBRA:                "Subra",
    COXA:                 "Coxa",
    SHIR:                 "Shir",
}


def leo_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def regulus_at(jd_tt: float) -> StarPosition:
    return leo_star_at(REGULUS, jd_tt)

def denebola_at(jd_tt: float) -> StarPosition:
    return leo_star_at(DENEBOLA, jd_tt)

def algieba_at(jd_tt: float) -> StarPosition:
    return leo_star_at(ALGIEBA, jd_tt)

def zosma_at(jd_tt: float) -> StarPosition:
    return leo_star_at(ZOSMA, jd_tt)

def ras_elased_australis_at(jd_tt: float) -> StarPosition:
    return leo_star_at(RAS_ELASED_AUSTRALIS, jd_tt)

def adhafera_at(jd_tt: float) -> StarPosition:
    return leo_star_at(ADHAFERA, jd_tt)

def al_jabhah_at(jd_tt: float) -> StarPosition:
    return leo_star_at(AL_JABHAH, jd_tt)

def tse_tseng_at(jd_tt: float) -> StarPosition:
    return leo_star_at(TSE_TSENG, jd_tt)

def alminhar_at(jd_tt: float) -> StarPosition:
    return leo_star_at(ALMINHAR, jd_tt)

def alterf_at(jd_tt: float) -> StarPosition:
    return leo_star_at(ALTERF, jd_tt)

def ras_elased_borealis_at(jd_tt: float) -> StarPosition:
    return leo_star_at(RAS_ELASED_BOREALIS, jd_tt)

def subra_at(jd_tt: float) -> StarPosition:
    return leo_star_at(SUBRA, jd_tt)

def coxa_at(jd_tt: float) -> StarPosition:
    return leo_star_at(COXA, jd_tt)

def shir_at(jd_tt: float) -> StarPosition:
    return leo_star_at(SHIR, jd_tt)


def list_leo_stars() -> list[str]:
    return list(LEO_STAR_NAMES.values())


def available_leo_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in LEO_STAR_NAMES.values() if name in catalog]



