"""
Hydra Constellation Oracle — moira/constellations/stars_hydra.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Hydra (IAU: Hya).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Hydra.
    - HYDRA_STAR_NAMES mapping (constant → canonical name).
    - hydra_star_at() dispatcher.
    - Per-star convenience functions (alphard_at, cauda_hydrae_at, …).
    - list_hydra_stars() / available_hydra_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ALPHARD, CAUDA_HYDRAE, MAUTINAH, ASHLESHA, HYDROBIUS, PLEURA,
    SATAGHNI, AL_MINLIAR_AL_SHUJA, UKDAH, ZHANG
    HYDRA_STAR_NAMES
    hydra_star_at() and all per-star _at() functions
    list_hydra_stars(), available_hydra_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

ALPHARD             = "Alphard"
CAUDA_HYDRAE        = "Cauda Hydrae"
MAUTINAH            = "Mautinah"
ASHLESHA            = "Ashlesha"
HYDROBIUS           = "Hydrobius"
PLEURA              = "Pleura"
SATAGHNI            = "Sataghni"
AL_MINLIAR_AL_SHUJA = "Al Minliar al Shuja"
UKDAH               = "Ukdah"
ZHANG               = "Zhang"

HYDRA_STAR_NAMES = {
    ALPHARD:             "Alphard",
    CAUDA_HYDRAE:        "Cauda Hydrae",
    MAUTINAH:            "Mautinah",
    ASHLESHA:            "Ashlesha",
    HYDROBIUS:           "Hydrobius",
    PLEURA:              "Pleura",
    SATAGHNI:            "Sataghni",
    AL_MINLIAR_AL_SHUJA: "Al Minliar al Shuja",
    UKDAH:               "Ukdah",
    ZHANG:               "Zhang",
}


def hydra_star_at(name: str, jd_tt: float) -> StarPosition:
    return fixed_star_at(name, jd_tt)


def alphard_at(jd_tt: float) -> StarPosition:
    return hydra_star_at(ALPHARD, jd_tt)

def cauda_hydrae_at(jd_tt: float) -> StarPosition:
    return hydra_star_at(CAUDA_HYDRAE, jd_tt)

def mautinah_at(jd_tt: float) -> StarPosition:
    return hydra_star_at(MAUTINAH, jd_tt)

def ashlesha_at(jd_tt: float) -> StarPosition:
    return hydra_star_at(ASHLESHA, jd_tt)

def hydrobius_at(jd_tt: float) -> StarPosition:
    return hydra_star_at(HYDROBIUS, jd_tt)

def pleura_at(jd_tt: float) -> StarPosition:
    return hydra_star_at(PLEURA, jd_tt)

def sataghni_at(jd_tt: float) -> StarPosition:
    return hydra_star_at(SATAGHNI, jd_tt)

def al_minliar_al_shuja_at(jd_tt: float) -> StarPosition:
    return hydra_star_at(AL_MINLIAR_AL_SHUJA, jd_tt)

def ukdah_at(jd_tt: float) -> StarPosition:
    return hydra_star_at(UKDAH, jd_tt)

def zhang_at(jd_tt: float) -> StarPosition:
    return hydra_star_at(ZHANG, jd_tt)


def list_hydra_stars() -> list[str]:
    return list(HYDRA_STAR_NAMES.values())


def available_hydra_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in HYDRA_STAR_NAMES.values() if name in catalog]
