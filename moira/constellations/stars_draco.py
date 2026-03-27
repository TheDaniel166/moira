"""
Draco Constellation Oracle — moira/constellations/stars_draco.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Draco (IAU: Dra).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Draco.
    - DRACO_STAR_NAMES mapping (constant → canonical name).
    - draco_star_at() dispatcher.
    - Per-star convenience functions (thuban_at, eltanin_at, …).
    - list_draco_stars() / available_draco_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    THUBAN, ALWAID, ELTANIN, NODUS_II, TYL, NODUS_I, EDASICH, KETU,
    GIANSAR, ARRAKIS, KUMA, GRUMIUM, ALSAFI, BATENTABAN_BOREALIS,
    DZIBAN, ALDHIBAIN, BATENTABAN_AUSTRALIS
    DRACO_STAR_NAMES
    draco_star_at() and all per-star _at() functions
    list_draco_stars(), available_draco_stars()

Stars sourced from the Sovereign Star Registry via Gaia DR3.
"""
from ..stars import star_at, GaiaStarPosition, list_stars

THUBAN                  = "Thuban"
ALWAID                  = "Alwaid"
ELTANIN                 = "Eltanin"
NODUS_II                = "Nodus II"
TYL                     = "Tyl"
NODUS_I                 = "Nodus I"
EDASICH                 = "Edasich"
KETU                    = "Ketu"
GIANSAR                 = "Giansar"
ARRAKIS                 = "Arrakis"
KUMA                    = "Kuma"
GRUMIUM                 = "Grumium"
ALSAFI                  = "Alsafi"
BATENTABAN_BOREALIS     = "Batentaban Borealis"
DZIBAN                  = "Dziban"
ALDHIBAIN               = "Aldhibain"
BATENTABAN_AUSTRALIS    = "Batentaban Australis"

DRACO_STAR_NAMES = {
    THUBAN:               "Thuban",
    ALWAID:               "Alwaid",
    ELTANIN:              "Eltanin",
    NODUS_II:             "Nodus II",
    TYL:                  "Tyl",
    NODUS_I:              "Nodus I",
    EDASICH:              "Edasich",
    KETU:                 "Ketu",
    GIANSAR:              "Giansar",
    ARRAKIS:              "Arrakis",
    KUMA:                 "Kuma",
    GRUMIUM:              "Grumium",
    ALSAFI:               "Alsafi",
    BATENTABAN_BOREALIS:  "Batentaban Borealis",
    DZIBAN:               "Dziban",
    ALDHIBAIN:            "Aldhibain",
    BATENTABAN_AUSTRALIS: "Batentaban Australis",
}


def draco_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def thuban_at(jd_tt: float) -> StarPosition:
    return draco_star_at(THUBAN, jd_tt)

def alwaid_at(jd_tt: float) -> StarPosition:
    return draco_star_at(ALWAID, jd_tt)

def eltanin_at(jd_tt: float) -> StarPosition:
    return draco_star_at(ELTANIN, jd_tt)

def nodus_ii_at(jd_tt: float) -> StarPosition:
    return draco_star_at(NODUS_II, jd_tt)

def tyl_at(jd_tt: float) -> StarPosition:
    return draco_star_at(TYL, jd_tt)

def nodus_i_at(jd_tt: float) -> StarPosition:
    return draco_star_at(NODUS_I, jd_tt)

def edasich_at(jd_tt: float) -> StarPosition:
    return draco_star_at(EDASICH, jd_tt)

def ketu_at(jd_tt: float) -> StarPosition:
    return draco_star_at(KETU, jd_tt)

def giansar_at(jd_tt: float) -> StarPosition:
    return draco_star_at(GIANSAR, jd_tt)

def arrakis_at(jd_tt: float) -> StarPosition:
    return draco_star_at(ARRAKIS, jd_tt)

def kuma_at(jd_tt: float) -> StarPosition:
    return draco_star_at(KUMA, jd_tt)

def grumium_at(jd_tt: float) -> StarPosition:
    return draco_star_at(GRUMIUM, jd_tt)

def alsafi_at(jd_tt: float) -> StarPosition:
    return draco_star_at(ALSAFI, jd_tt)

def batentaban_borealis_at(jd_tt: float) -> StarPosition:
    return draco_star_at(BATENTABAN_BOREALIS, jd_tt)

def dziban_at(jd_tt: float) -> StarPosition:
    return draco_star_at(DZIBAN, jd_tt)

def aldhibain_at(jd_tt: float) -> StarPosition:
    return draco_star_at(ALDHIBAIN, jd_tt)

def batentaban_australis_at(jd_tt: float) -> StarPosition:
    return draco_star_at(BATENTABAN_AUSTRALIS, jd_tt)


def list_draco_stars() -> list[str]:
    return list(DRACO_STAR_NAMES.values())


def available_draco_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in DRACO_STAR_NAMES.values() if name in catalog]
