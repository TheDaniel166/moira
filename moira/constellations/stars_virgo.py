"""
Virgo Constellation Oracle â€” moira/constellations/stars_virgo.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Virgo (IAU: Vir).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Virgo.
    - VIRGO_STAR_NAMES mapping (constant â†’ canonical name).
    - virgo_star_at() dispatcher.
    - Per-star convenience functions (spica_at, zavijava_at, â€¦).
    - list_virgo_stars() / available_virgo_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    SPICA, ZAVIJAVA, PORRIMA, AUVA, VINDEMIATRIX, HEZE, ZANIAH,
    SYRMA, KANG, KHAMBALIA, RIJL_AL_AWWA
    VIRGO_STAR_NAMES
    virgo_star_at() and all per-star _at() functions
    list_virgo_stars(), available_virgo_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

SPICA        = "Spica"
ZAVIJAVA     = "Zavijava"
PORRIMA      = "Porrima"
AUVA         = "Auva"
VINDEMIATRIX = "Vindemiatrix"
HEZE         = "Heze"
ZANIAH       = "Zaniah"
SYRMA        = "Syrma"
KANG         = "Kang"
KHAMBALIA    = "Khambalia"
RIJL_AL_AWWA = "Rijl al Awwa"

VIRGO_STAR_NAMES = {
    SPICA:        "Spica",
    ZAVIJAVA:     "Zavijava",
    PORRIMA:      "Porrima",
    AUVA:         "Auva",
    VINDEMIATRIX: "Vindemiatrix",
    HEZE:         "Heze",
    ZANIAH:       "Zaniah",
    SYRMA:        "Syrma",
    KANG:         "Kang",
    KHAMBALIA:    "Khambalia",
    RIJL_AL_AWWA: "Rijl al Awwa",
}


def virgo_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def spica_at(jd_tt: float) -> StarPosition:
    return virgo_star_at(SPICA, jd_tt)

def zavijava_at(jd_tt: float) -> StarPosition:
    return virgo_star_at(ZAVIJAVA, jd_tt)

def porrima_at(jd_tt: float) -> StarPosition:
    return virgo_star_at(PORRIMA, jd_tt)

def auva_at(jd_tt: float) -> StarPosition:
    return virgo_star_at(AUVA, jd_tt)

def vindemiatrix_at(jd_tt: float) -> StarPosition:
    return virgo_star_at(VINDEMIATRIX, jd_tt)

def heze_at(jd_tt: float) -> StarPosition:
    return virgo_star_at(HEZE, jd_tt)

def zaniah_at(jd_tt: float) -> StarPosition:
    return virgo_star_at(ZANIAH, jd_tt)

def syrma_at(jd_tt: float) -> StarPosition:
    return virgo_star_at(SYRMA, jd_tt)

def kang_at(jd_tt: float) -> StarPosition:
    return virgo_star_at(KANG, jd_tt)

def khambalia_at(jd_tt: float) -> StarPosition:
    return virgo_star_at(KHAMBALIA, jd_tt)

def rijl_al_awwa_at(jd_tt: float) -> StarPosition:
    return virgo_star_at(RIJL_AL_AWWA, jd_tt)


def list_virgo_stars() -> list[str]:
    return list(VIRGO_STAR_NAMES.values())


def available_virgo_stars() -> list[str]:
    return [name for name in VIRGO_STAR_NAMES.values() if _star_name_is_resolvable(name)]





