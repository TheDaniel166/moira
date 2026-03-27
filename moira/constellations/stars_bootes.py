"""
BoÃ¶tes Constellation Oracle â€” moira/constellations/stars_bootes.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in BoÃ¶tes (IAU: Boo).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in BoÃ¶tes.
    - BOOTES_STAR_NAMES mapping (constant â†’ canonical name).
    - bootes_star_at() dispatcher.
    - Per-star convenience functions (arcturus_at, nekkar_at, â€¦).
    - list_bootes_stars() / available_bootes_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ARCTURUS, NEKKAR, SEGINUS, PRINCEPS, IZAR, MUFRID, ASELLUS_PRIMUS,
    ASELLUS_SECUNDUS, ASELLUS_TERTIUS, XUANGE, ALKALUROPS, HEMELEIN_PRIMA,
    HEMELEIN_SECUNDA, CEGINUS, MERGA
    BOOTES_STAR_NAMES
    bootes_star_at() and all per-star _at() functions
    list_bootes_stars(), available_bootes_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

ARCTURUS          = "Arcturus"
NEKKAR            = "Nekkar"
SEGINUS           = "Seginus"
PRINCEPS          = "Princeps"
IZAR              = "Izar"
MUFRID            = "Muphrid"
ASELLUS_PRIMUS    = "Asellus Primus"
ASELLUS_SECUNDUS  = "Asellus Secundus"
ASELLUS_TERTIUS   = "Asellus Tertius"
XUANGE            = "Xuange"
ALKALUROPS        = "Alkalurops"
HEMELEIN_PRIMA    = "Hemelein Prima"
HEMELEIN_SECUNDA  = "Hemelein Secunda"
CEGINUS           = "Seginus"
MERGA             = "Merga"

BOOTES_STAR_NAMES = {
    ARCTURUS:         "Arcturus",
    NEKKAR:           "Nekkar",
    SEGINUS:          "Seginus",
    PRINCEPS:         "Princeps",
    IZAR:             "Izar",
    MUFRID:           "Muphrid",
    ASELLUS_PRIMUS:   "Asellus Primus",
    ASELLUS_SECUNDUS: "Asellus Secundus",
    ASELLUS_TERTIUS:  "Asellus Tertius",
    XUANGE:           "Xuange",
    ALKALUROPS:       "Alkalurops",
    HEMELEIN_PRIMA:   "Hemelein Prima",
    HEMELEIN_SECUNDA: "Hemelein Secunda",
    CEGINUS:          "Seginus",
    MERGA:            "Merga",
}


def bootes_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def arcturus_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(ARCTURUS, jd_tt)

def nekkar_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(NEKKAR, jd_tt)

def seginus_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(SEGINUS, jd_tt)

def princeps_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(PRINCEPS, jd_tt)

def izar_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(IZAR, jd_tt)

def mufrid_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(MUFRID, jd_tt)

def asellus_primus_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(ASELLUS_PRIMUS, jd_tt)

def asellus_secundus_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(ASELLUS_SECUNDUS, jd_tt)

def asellus_tertius_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(ASELLUS_TERTIUS, jd_tt)

def xuange_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(XUANGE, jd_tt)

def alkalurops_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(ALKALUROPS, jd_tt)

def hemelein_prima_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(HEMELEIN_PRIMA, jd_tt)

def hemelein_secunda_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(HEMELEIN_SECUNDA, jd_tt)

def ceginus_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(CEGINUS, jd_tt)

def merga_at(jd_tt: float) -> StarPosition:
    return bootes_star_at(MERGA, jd_tt)


def list_bootes_stars() -> list[str]:
    return list(BOOTES_STAR_NAMES.values())


def available_bootes_stars() -> list[str]:
    return [name for name in BOOTES_STAR_NAMES.values() if _star_name_is_resolvable(name)]





