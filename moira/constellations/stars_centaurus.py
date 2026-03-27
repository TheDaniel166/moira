"""
Centaurus Constellation Oracle â€” moira/constellations/stars_centaurus.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Centaurus (IAU: Cen).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Centaurus.
    - CENTAURUS_STAR_NAMES mapping (constant â†’ canonical name).
    - centaurus_star_at() dispatcher.
    - Per-star convenience functions (rigil_kentaurus_at, hadar_at, â€¦).
    - list_centaurus_stars() / available_centaurus_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    RIGIL_KENTAURUS, HADAR, MUHLIFAIN, BIRDUN, MENKENT, ALHAKIM,
    KE_KWAN, MA_TI, KABKENT_SECUNDA, KABKENT_TERTIA
    CENTAURUS_STAR_NAMES
    centaurus_star_at() and all per-star _at() functions
    list_centaurus_stars(), available_centaurus_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

RIGIL_KENTAURUS  = "Rigil Kentaurus"
HADAR            = "Hadar"
MUHLIFAIN        = "Muhlifain"
BIRDUN           = "Birdun"
MENKENT          = "Menkent"
ALHAKIM          = "Alhakim"
KE_KWAN          = "Ke Kwan"
MA_TI            = "Ma Ti"
KABKENT_SECUNDA  = "Kabkent Secunda"
KABKENT_TERTIA   = "Kabkent Tertia"

CENTAURUS_STAR_NAMES = {
    RIGIL_KENTAURUS: "Rigil Kentaurus",
    HADAR:           "Hadar",
    MUHLIFAIN:       "Muhlifain",
    BIRDUN:          "Birdun",
    MENKENT:         "Menkent",
    ALHAKIM:         "Alhakim",
    KE_KWAN:         "Ke Kwan",
    MA_TI:           "Ma Ti",
    KABKENT_SECUNDA: "Kabkent Secunda",
    KABKENT_TERTIA:  "Kabkent Tertia",
}


def centaurus_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def rigil_kentaurus_at(jd_tt: float) -> StarPosition:
    return centaurus_star_at(RIGIL_KENTAURUS, jd_tt)

def hadar_at(jd_tt: float) -> StarPosition:
    return centaurus_star_at(HADAR, jd_tt)

def muhlifain_at(jd_tt: float) -> StarPosition:
    return centaurus_star_at(MUHLIFAIN, jd_tt)

def birdun_at(jd_tt: float) -> StarPosition:
    return centaurus_star_at(BIRDUN, jd_tt)

def menkent_at(jd_tt: float) -> StarPosition:
    return centaurus_star_at(MENKENT, jd_tt)

def alhakim_at(jd_tt: float) -> StarPosition:
    return centaurus_star_at(ALHAKIM, jd_tt)

def ke_kwan_at(jd_tt: float) -> StarPosition:
    return centaurus_star_at(KE_KWAN, jd_tt)

def ma_ti_at(jd_tt: float) -> StarPosition:
    return centaurus_star_at(MA_TI, jd_tt)

def kabkent_secunda_at(jd_tt: float) -> StarPosition:
    return centaurus_star_at(KABKENT_SECUNDA, jd_tt)

def kabkent_tertia_at(jd_tt: float) -> StarPosition:
    return centaurus_star_at(KABKENT_TERTIA, jd_tt)


def list_centaurus_stars() -> list[str]:
    return list(CENTAURUS_STAR_NAMES.values())


def available_centaurus_stars() -> list[str]:
    return [name for name in CENTAURUS_STAR_NAMES.values() if _star_name_is_resolvable(name)]





