"""
Hercules Constellation Oracle â€” moira/constellations/stars_hercules.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Hercules (IAU: Her).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Hercules.
    - HERCULES_STAR_NAMES mapping (constant â†’ canonical name).
    - hercules_star_at() dispatcher.
    - Per-star convenience functions (ras_algethi_at, kornephoros_at, â€¦).
    - list_hercules_stars() / available_hercules_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    RAS_ALGETHI, KORNEPHOROS, RUTILICUS, SARIN, SOFIAN,
    RUKBALGETHI_GENUBI, AL_JATHIYAH, MARSIK, MASYM, MELKARTH,
    FUDAIL, RUKBALGETHI_SHEMALI, CUJAM
    HERCULES_STAR_NAMES
    hercules_star_at() and all per-star _at() functions
    list_hercules_stars(), available_hercules_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition, list_stars

RAS_ALGETHI           = "Ras Algethi"
KORNEPHOROS           = "Kornephoros"
RUTILICUS             = "Rutilicus"
SARIN                 = "Sarin"
SOFIAN                = "Sofian"
RUKBALGETHI_GENUBI    = "Rukbalgethi Genubi"
AL_JATHIYAH           = "Al Jathiyah"
MARSIK                = "Marsik"
MASYM                 = "Masym"
MELKARTH              = "Melkarth"
FUDAIL                = "Fudail"
RUKBALGETHI_SHEMALI   = "Rukbalgethi Shemali"
CUJAM                 = "Cujam"

HERCULES_STAR_NAMES = {
    RAS_ALGETHI:          "Ras Algethi",
    KORNEPHOROS:          "Kornephoros",
    RUTILICUS:            "Rutilicus",
    SARIN:                "Sarin",
    SOFIAN:               "Sofian",
    RUKBALGETHI_GENUBI:   "Rukbalgethi Genubi",
    AL_JATHIYAH:          "Al Jathiyah",
    MARSIK:               "Marsik",
    MASYM:                "Masym",
    MELKARTH:             "Melkarth",
    FUDAIL:               "Fudail",
    RUKBALGETHI_SHEMALI:  "Rukbalgethi Shemali",
    CUJAM:                "Cujam",
}


def hercules_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def ras_algethi_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(RAS_ALGETHI, jd_tt)

def kornephoros_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(KORNEPHOROS, jd_tt)

def rutilicus_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(RUTILICUS, jd_tt)

def sarin_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(SARIN, jd_tt)

def sofian_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(SOFIAN, jd_tt)

def rukbalgethi_genubi_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(RUKBALGETHI_GENUBI, jd_tt)

def al_jathiyah_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(AL_JATHIYAH, jd_tt)

def marsik_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(MARSIK, jd_tt)

def masym_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(MASYM, jd_tt)

def melkarth_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(MELKARTH, jd_tt)

def fudail_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(FUDAIL, jd_tt)

def rukbalgethi_shemali_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(RUKBALGETHI_SHEMALI, jd_tt)

def cujam_at(jd_tt: float) -> StarPosition:
    return hercules_star_at(CUJAM, jd_tt)


def list_hercules_stars() -> list[str]:
    return list(HERCULES_STAR_NAMES.values())


def available_hercules_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in HERCULES_STAR_NAMES.values() if name in catalog]



