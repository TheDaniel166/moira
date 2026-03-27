"""
Aquarius Constellation Oracle â€” moira/constellations/stars_aquarius.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Aquarius (IAU: Aqr).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Aquarius.
    - AQUARIUS_STAR_NAMES mapping (constant â†’ canonical name).
    - aquarius_star_at() dispatcher.
    - Per-star convenience functions (sadalmelik_at, sadalsuud_at, â€¦).
    - list_aquarius_stars() / available_aquarius_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    SADALMELIK, SADALSUUD, SADALACHBIA, SKAT, ALBALI, HYDRIA, ANCHA,
    SITULA, EKKHYSIS, ALBULAAN, BUNDA
    AQUARIUS_STAR_NAMES
    aquarius_star_at() and all per-star _at() functions
    list_aquarius_stars(), available_aquarius_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition
from . import _star_name_is_resolvable

SADALMELIK   = "Sadalmelik"
SADALSUUD    = "Sadalsuud"
SADALACHBIA  = "Sadachbia"
SKAT         = "Skat"
ALBALI       = "Albali"
HYDRIA       = "Hydria"
ANCHA        = "Ancha"
SITULA       = "Situla"
EKKHYSIS     = "Ekkhysis"
ALBULAAN     = "Albulaan"
BUNDA        = "Bunda"

AQUARIUS_STAR_NAMES = {
    SADALMELIK:  "Sadalmelik",
    SADALSUUD:   "Sadalsuud",
    SADALACHBIA: "Sadachbia",
    SKAT:        "Skat",
    ALBALI:      "Albali",
    HYDRIA:      "Hydria",
    ANCHA:       "Ancha",
    SITULA:      "Situla",
    EKKHYSIS:    "Ekkhysis",
    ALBULAAN:    "Albulaan",
    BUNDA:       "Bunda",
}


def aquarius_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def sadalmelik_at(jd_tt: float) -> StarPosition:
    return aquarius_star_at(SADALMELIK, jd_tt)

def sadalsuud_at(jd_tt: float) -> StarPosition:
    return aquarius_star_at(SADALSUUD, jd_tt)

def sadalachbia_at(jd_tt: float) -> StarPosition:
    return aquarius_star_at(SADALACHBIA, jd_tt)

def skat_at(jd_tt: float) -> StarPosition:
    return aquarius_star_at(SKAT, jd_tt)

def albali_at(jd_tt: float) -> StarPosition:
    return aquarius_star_at(ALBALI, jd_tt)

def hydria_at(jd_tt: float) -> StarPosition:
    return aquarius_star_at(HYDRIA, jd_tt)

def ancha_at(jd_tt: float) -> StarPosition:
    return aquarius_star_at(ANCHA, jd_tt)

def situla_at(jd_tt: float) -> StarPosition:
    return aquarius_star_at(SITULA, jd_tt)

def ekkhysis_at(jd_tt: float) -> StarPosition:
    return aquarius_star_at(EKKHYSIS, jd_tt)

def albulaan_at(jd_tt: float) -> StarPosition:
    return aquarius_star_at(ALBULAAN, jd_tt)

def bunda_at(jd_tt: float) -> StarPosition:
    return aquarius_star_at(BUNDA, jd_tt)


def list_aquarius_stars() -> list[str]:
    return list(AQUARIUS_STAR_NAMES.values())


def available_aquarius_stars() -> list[str]:
    return [name for name in AQUARIUS_STAR_NAMES.values() if _star_name_is_resolvable(name)]





