"""
Pegasus Constellation Oracle â€” moira/constellations/stars_pegasus.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Pegasus (IAU: Peg).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Pegasus.
    - PEGASUS_STAR_NAMES mapping (constant â†’ canonical name).
    - pegasus_star_at() dispatcher.
    - Per-star convenience functions (markab_at, scheat_at, â€¦).
    - list_pegasus_stars() / available_pegasus_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    MARKAB, SCHEAT, ALGENIB, ENIF, HOMAM, MATAR, BIHAM
    PEGASUS_STAR_NAMES
    pegasus_star_at() and all per-star _at() functions
    list_pegasus_stars(), available_pegasus_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

MARKAB  = "Markab"
SCHEAT  = "Scheat"
ALGENIB = "Algenib"
ENIF    = "Enif"
HOMAM   = "Homam"
MATAR   = "Matar"
BIHAM   = "Biham"

PEGASUS_STAR_NAMES = {
    MARKAB:  "Markab",
    SCHEAT:  "Scheat",
    ALGENIB: "Algenib",
    ENIF:    "Enif",
    HOMAM:   "Homam",
    MATAR:   "Matar",
    BIHAM:   "Biham",
}


def pegasus_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def markab_at(jd_tt: float) -> StarPosition:
    return pegasus_star_at(MARKAB, jd_tt)

def scheat_at(jd_tt: float) -> StarPosition:
    return pegasus_star_at(SCHEAT, jd_tt)

def algenib_at(jd_tt: float) -> StarPosition:
    return pegasus_star_at(ALGENIB, jd_tt)

def enif_at(jd_tt: float) -> StarPosition:
    return pegasus_star_at(ENIF, jd_tt)

def homam_at(jd_tt: float) -> StarPosition:
    return pegasus_star_at(HOMAM, jd_tt)

def matar_at(jd_tt: float) -> StarPosition:
    return pegasus_star_at(MATAR, jd_tt)

def biham_at(jd_tt: float) -> StarPosition:
    return pegasus_star_at(BIHAM, jd_tt)


def list_pegasus_stars() -> list[str]:
    return list(PEGASUS_STAR_NAMES.values())


def available_pegasus_stars() -> list[str]:
    return [name for name in PEGASUS_STAR_NAMES.values() if _star_name_is_resolvable(name)]





