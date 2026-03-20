"""
Cassiopeia Constellation Oracle — moira/constellations/stars_cassiopeia.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Cassiopeia (IAU: Cas).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Cassiopeia.
    - CASSIOPEIA_STAR_NAMES mapping (constant → canonical name).
    - cassiopeia_star_at() dispatcher.
    - Per-star convenience functions (schedar_at, caph_at, …).
    - list_cassiopeia_stars() / available_cassiopeia_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    SCHEDAR, CAPH, TSIH, RUCHBAH, SEGIN, FULU, ACHIRD, MARFAK, CASTULA
    CASSIOPEIA_STAR_NAMES
    cassiopeia_star_at() and all per-star _at() functions
    list_cassiopeia_stars(), available_cassiopeia_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

SCHEDAR  = "Schedar"
CAPH     = "Caph"
TSIH     = "Tsih"
RUCHBAH  = "Ruchbah"
SEGIN    = "Segin"
FULU     = "Fulu"
ACHIRD   = "Achird"
MARFAK   = "Marfak"
CASTULA  = "Castula"

CASSIOPEIA_STAR_NAMES = {
    SCHEDAR: "Schedar",
    CAPH:    "Caph",
    TSIH:    "Tsih",
    RUCHBAH: "Ruchbah",
    SEGIN:   "Segin",
    FULU:    "Fulu",
    ACHIRD:  "Achird",
    MARFAK:  "Marfak",
    CASTULA: "Castula",
}


def cassiopeia_star_at(name: str, jd_tt: float) -> StarPosition:
    return fixed_star_at(name, jd_tt)


def schedar_at(jd_tt: float) -> StarPosition:
    return cassiopeia_star_at(SCHEDAR, jd_tt)

def caph_at(jd_tt: float) -> StarPosition:
    return cassiopeia_star_at(CAPH, jd_tt)

def tsih_at(jd_tt: float) -> StarPosition:
    return cassiopeia_star_at(TSIH, jd_tt)

def ruchbah_at(jd_tt: float) -> StarPosition:
    return cassiopeia_star_at(RUCHBAH, jd_tt)

def segin_at(jd_tt: float) -> StarPosition:
    return cassiopeia_star_at(SEGIN, jd_tt)

def fulu_at(jd_tt: float) -> StarPosition:
    return cassiopeia_star_at(FULU, jd_tt)

def achird_at(jd_tt: float) -> StarPosition:
    return cassiopeia_star_at(ACHIRD, jd_tt)

def marfak_at(jd_tt: float) -> StarPosition:
    return cassiopeia_star_at(MARFAK, jd_tt)

def castula_at(jd_tt: float) -> StarPosition:
    return cassiopeia_star_at(CASTULA, jd_tt)


def list_cassiopeia_stars() -> list[str]:
    return list(CASSIOPEIA_STAR_NAMES.values())


def available_cassiopeia_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in CASSIOPEIA_STAR_NAMES.values() if name in catalog]
