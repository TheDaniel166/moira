"""
Sagittarius Constellation Oracle — moira/constellations/stars_sagittarius.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Sagittarius (IAU: Sgr).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Sagittarius.
    - SAGITTARIUS_STAR_NAMES mapping (constant → canonical name).
    - sagittarius_star_at() dispatcher.
    - Per-star convenience functions (kaus_australis_at, nunki_at, …).
    - list_sagittarius_stars() / available_sagittarius_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    RUKBAT, ARKAB_PRIOR, ARKAB_POSTERIOR, ALNASL, KAUS_MEDIA,
    KAUS_AUSTRALIS, ASCELLA, SEPHDAR, KAUS_BOREALIS, POLIS,
    MANUBRIUM, ALBALDAH, NUNKI, HECATEBOLUS, NANTO, TEREBELLIUM, FACIES
    SAGITTARIUS_STAR_NAMES
    sagittarius_star_at() and all per-star _at() functions
    list_sagittarius_stars(), available_sagittarius_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

RUKBAT           = "Rukbat"
ARKAB_PRIOR      = "Arkab Prior"
ARKAB_POSTERIOR  = "Arkab Posterior"
ALNASL           = "Alnasl"
KAUS_MEDIA       = "Kaus Media"
KAUS_AUSTRALIS   = "Kaus Australis"
ASCELLA          = "Ascella"
SEPHDAR          = "Sephdar"
KAUS_BOREALIS    = "Kaus Borealis"
POLIS            = "Polis"
MANUBRIUM        = "Manubrium"
ALBALDAH         = "Albaldah"
NUNKI            = "Nunki"
HECATEBOLUS      = "Hecatebolus"
NANTO            = "Nanto"
TEREBELLIUM      = "Terebellium"
FACIES           = "Facies"

SAGITTARIUS_STAR_NAMES = {
    RUKBAT:          "Rukbat",
    ARKAB_PRIOR:     "Arkab Prior",
    ARKAB_POSTERIOR: "Arkab Posterior",
    ALNASL:          "Alnasl",
    KAUS_MEDIA:      "Kaus Media",
    KAUS_AUSTRALIS:  "Kaus Australis",
    ASCELLA:         "Ascella",
    SEPHDAR:         "Sephdar",
    KAUS_BOREALIS:   "Kaus Borealis",
    POLIS:           "Polis",
    MANUBRIUM:       "Manubrium",
    ALBALDAH:        "Albaldah",
    NUNKI:           "Nunki",
    HECATEBOLUS:     "Hecatebolus",
    NANTO:           "Nanto",
    TEREBELLIUM:     "Terebellium",
    FACIES:          "Facies",
}


def sagittarius_star_at(name: str, jd_tt: float) -> StarPosition:
    return fixed_star_at(name, jd_tt)


def rukbat_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(RUKBAT, jd_tt)

def arkab_prior_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(ARKAB_PRIOR, jd_tt)

def arkab_posterior_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(ARKAB_POSTERIOR, jd_tt)

def alnasl_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(ALNASL, jd_tt)

def kaus_media_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(KAUS_MEDIA, jd_tt)

def kaus_australis_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(KAUS_AUSTRALIS, jd_tt)

def ascella_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(ASCELLA, jd_tt)

def sephdar_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(SEPHDAR, jd_tt)

def kaus_borealis_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(KAUS_BOREALIS, jd_tt)

def polis_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(POLIS, jd_tt)

def manubrium_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(MANUBRIUM, jd_tt)

def albaldah_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(ALBALDAH, jd_tt)

def nunki_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(NUNKI, jd_tt)

def hecatebolus_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(HECATEBOLUS, jd_tt)

def nanto_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(NANTO, jd_tt)

def terebellium_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(TEREBELLIUM, jd_tt)

def facies_at(jd_tt: float) -> StarPosition:
    return sagittarius_star_at(FACIES, jd_tt)


def list_sagittarius_stars() -> list[str]:
    return list(SAGITTARIUS_STAR_NAMES.values())


def available_sagittarius_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in SAGITTARIUS_STAR_NAMES.values() if name in catalog]
