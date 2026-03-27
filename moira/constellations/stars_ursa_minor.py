"""
Ursa Minor Constellation Oracle — moira/constellations/stars_ursa_minor.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Ursa Minor (IAU: UMi).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Ursa Minor.
    - URSA_MINOR_STAR_NAMES mapping (constant → canonical name).
    - ursa_minor_star_at() dispatcher.
    - Per-star convenience functions (polaris_at, kochab_at, …).
    - list_ursa_minor_stars() / available_ursa_minor_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    POLARIS, KOCHAB, PHERKAD, YILDUN, URODELUS,
    ALIFA_AL_FARKADAIN, PHERKAD_MINOR
    URSA_MINOR_STAR_NAMES
    ursa_minor_star_at() and all per-star _at() functions
    list_ursa_minor_stars(), available_ursa_minor_stars()

Stars sourced from the Sovereign Star Registry via Gaia DR3.
"""
from ..stars import star_at, GaiaStarPosition, list_stars

POLARIS              = "Polaris"
KOCHAB               = "Kochab"
PHERKAD              = "Pherkad"
YILDUN               = "Yildun"
URODELUS             = "Urodelus"
ALIFA_AL_FARKADAIN   = "Alifa Al Farkadain"
PHERKAD_MINOR        = "Pherkad Minor"

URSA_MINOR_STAR_NAMES = {
    POLARIS:            "Polaris",
    KOCHAB:             "Kochab",
    PHERKAD:            "Pherkad",
    YILDUN:             "Yildun",
    URODELUS:           "Urodelus",
    ALIFA_AL_FARKADAIN: "Alifa Al Farkadain",
    PHERKAD_MINOR:      "Pherkad Minor",
}


def ursa_minor_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def polaris_at(jd_tt: float) -> StarPosition:
    return ursa_minor_star_at(POLARIS, jd_tt)

def kochab_at(jd_tt: float) -> StarPosition:
    return ursa_minor_star_at(KOCHAB, jd_tt)

def pherkad_at(jd_tt: float) -> StarPosition:
    return ursa_minor_star_at(PHERKAD, jd_tt)

def yildun_at(jd_tt: float) -> StarPosition:
    return ursa_minor_star_at(YILDUN, jd_tt)

def urodelus_at(jd_tt: float) -> StarPosition:
    return ursa_minor_star_at(URODELUS, jd_tt)

def alifa_al_farkadain_at(jd_tt: float) -> StarPosition:
    return ursa_minor_star_at(ALIFA_AL_FARKADAIN, jd_tt)

def pherkad_minor_at(jd_tt: float) -> StarPosition:
    return ursa_minor_star_at(PHERKAD_MINOR, jd_tt)


def list_ursa_minor_stars() -> list[str]:
    return list(URSA_MINOR_STAR_NAMES.values())


def available_ursa_minor_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in URSA_MINOR_STAR_NAMES.values() if name in catalog]
