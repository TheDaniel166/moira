"""
Aries Constellation Oracle â€” moira/constellations/stars_aries.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Aries (IAU: Ari).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Aries.
    - ARIES_STAR_NAMES mapping (constant â†’ canonical name).
    - aries_star_at() dispatcher.
    - Per-star convenience functions (hamal_at, sheratan_at, â€¦).
    - list_aries_stars() / available_aries_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    HAMAL, SHERATAN, MESARTHIM, BOTEIN, LILII_BOREA, BHARANI
    ARIES_STAR_NAMES
    aries_star_at() and all per-star _at() functions
    list_aries_stars(), available_aries_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition, list_stars

HAMAL       = "Hamal"
SHERATAN    = "Sheratan"
MESARTHIM   = "Mesarthim"
BOTEIN      = "Botein"
LILII_BOREA = "Lilii Borea"
BHARANI     = "Bharani"

ARIES_STAR_NAMES = {
    HAMAL:       "Hamal",
    SHERATAN:    "Sheratan",
    MESARTHIM:   "Mesarthim",
    BOTEIN:      "Botein",
    LILII_BOREA: "Lilii Borea",
    BHARANI:     "Bharani",
}


def aries_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def hamal_at(jd_tt: float) -> StarPosition:
    return aries_star_at(HAMAL, jd_tt)

def sheratan_at(jd_tt: float) -> StarPosition:
    return aries_star_at(SHERATAN, jd_tt)

def mesarthim_at(jd_tt: float) -> StarPosition:
    return aries_star_at(MESARTHIM, jd_tt)

def botein_at(jd_tt: float) -> StarPosition:
    return aries_star_at(BOTEIN, jd_tt)

def lilii_borea_at(jd_tt: float) -> StarPosition:
    return aries_star_at(LILII_BOREA, jd_tt)

def bharani_at(jd_tt: float) -> StarPosition:
    return aries_star_at(BHARANI, jd_tt)


def list_aries_stars() -> list[str]:
    return list(ARIES_STAR_NAMES.values())


def available_aries_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in ARIES_STAR_NAMES.values() if name in catalog]



