"""
Taurus Constellation Oracle â€” moira/constellations/stars_taurus.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Taurus (IAU: Tau).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Taurus.
    - TAURUS_STAR_NAMES mapping (constant â†’ canonical name).
    - taurus_star_at() dispatcher.
    - Per-star convenience functions (aldebaran_at, alcyone_at, â€¦).
    - list_taurus_stars() / available_taurus_stars() introspection.
Delegates:
    - All position computation to moira.stars.star_at.
    - Catalog availability checks to moira.stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - moira/data/star_registry.csv and companion sovereign metadata must exist.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ALDEBARAN, ELNATH, PRIMA_HYADUM, HYADUM_I, SECUNDA_HYADUM, HYADUM_II,
    AIN, AL_HECKA, ALCYONE, PHAEO, PHAESULA, ALTHAUR, FURIBUNDUS,
    USHAKARON, ATIRSAGNE, CELAENO, ELECTRA, TAYGETA, MAIA, ASTEROPE,
    STEROPE_I, STEROPE_II, MEROPE, ATLAS, PLEIONE
    TAURUS_STAR_NAMES
    taurus_star_at() and all per-star _at() functions
    list_taurus_stars(), available_taurus_stars()

Stars sourced from the Sovereign Star Registry.
"""
from ..stars import star_at, StarPosition, list_stars

ALDEBARAN       = "Aldebaran"
ELNATH          = "Elnath"
PRIMA_HYADUM    = "Prima Hyadum"
HYADUM_I        = "Hyadum I"
SECUNDA_HYADUM  = "Secunda Hyadum"
HYADUM_II       = "Hyadum II"
AIN             = "Ain"
AL_HECKA        = "Al Hecka"
ALCYONE         = "Alcyone"
PHAEO           = "Phaeo"
PHAESULA        = "Phaesula"
ALTHAUR         = "Althaur"
FURIBUNDUS      = "Furibundus"
USHAKARON       = "Ushakaron"
ATIRSAGNE       = "Atirsagne"
CELAENO         = "Celaeno"
ELECTRA         = "Electra"
TAYGETA         = "Taygeta"
MAIA            = "Maia"
ASTEROPE        = "Asterope"
STEROPE_I       = "Sterope I"
STEROPE_II      = "Sterope II"
MEROPE          = "Merope"
ATLAS           = "Atlas"
PLEIONE         = "Pleione"

TAURUS_STAR_NAMES = {
    ALDEBARAN:      "Aldebaran",
    ELNATH:         "Elnath",
    PRIMA_HYADUM:   "Prima Hyadum",
    HYADUM_I:       "Hyadum I",
    SECUNDA_HYADUM: "Secunda Hyadum",
    HYADUM_II:      "Hyadum II",
    AIN:            "Ain",
    AL_HECKA:       "Al Hecka",
    ALCYONE:        "Alcyone",
    PHAEO:          "Phaeo",
    PHAESULA:       "Phaesula",
    ALTHAUR:        "Althaur",
    FURIBUNDUS:     "Furibundus",
    USHAKARON:      "Ushakaron",
    ATIRSAGNE:      "Atirsagne",
    CELAENO:        "Celaeno",
    ELECTRA:        "Electra",
    TAYGETA:        "Taygeta",
    MAIA:           "Maia",
    ASTEROPE:       "Asterope",
    STEROPE_I:      "Sterope I",
    STEROPE_II:     "Sterope II",
    MEROPE:         "Merope",
    ATLAS:          "Atlas",
    PLEIONE:        "Pleione",
}


def taurus_star_at(name: str, jd_tt: float) -> StarPosition:
    return star_at(name, jd_tt)


def aldebaran_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(ALDEBARAN, jd_tt)

def elnath_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(ELNATH, jd_tt)

def prima_hyadum_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(PRIMA_HYADUM, jd_tt)

def hyadum_i_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(HYADUM_I, jd_tt)

def secunda_hyadum_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(SECUNDA_HYADUM, jd_tt)

def hyadum_ii_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(HYADUM_II, jd_tt)

def ain_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(AIN, jd_tt)

def al_hecka_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(AL_HECKA, jd_tt)

def alcyone_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(ALCYONE, jd_tt)

def phaeo_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(PHAEO, jd_tt)

def phaesula_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(PHAESULA, jd_tt)

def althaur_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(ALTHAUR, jd_tt)

def furibundus_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(FURIBUNDUS, jd_tt)

def ushakaron_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(USHAKARON, jd_tt)

def atirsagne_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(ATIRSAGNE, jd_tt)

def celaeno_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(CELAENO, jd_tt)

def electra_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(ELECTRA, jd_tt)

def taygeta_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(TAYGETA, jd_tt)

def maia_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(MAIA, jd_tt)

def asterope_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(ASTEROPE, jd_tt)

def sterope_i_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(STEROPE_I, jd_tt)

def sterope_ii_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(STEROPE_II, jd_tt)

def merope_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(MEROPE, jd_tt)

def atlas_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(ATLAS, jd_tt)

def pleione_at(jd_tt: float) -> StarPosition:
    return taurus_star_at(PLEIONE, jd_tt)


def list_taurus_stars() -> list[str]:
    return list(TAURUS_STAR_NAMES.values())


def available_taurus_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in TAURUS_STAR_NAMES.values() if name in catalog]



