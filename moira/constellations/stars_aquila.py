"""
Aquila Constellation Oracle — moira/constellations/stars_aquila.py

Archetype: Oracle
Purpose: Provides named constants and per-star position functions for stars
         in Aquila (IAU: Aql).

Boundary declaration
--------------------
Owns:
    - Named string constants for each catalogued star in Aquila.
    - AQUILA_STAR_NAMES mapping (constant → canonical name).
    - aquila_star_at() dispatcher.
    - Per-star convenience functions (altair_at, alshain_at, …).
    - list_aquila_stars() / available_aquila_stars() introspection.
Delegates:
    - All position computation to moira.fixed_stars.fixed_star_at.
    - Catalog availability checks to moira.fixed_stars.list_stars.

Import-time side effects: None.

External dependency assumptions:
    - sefstars.txt must be present before any position query is made.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ALTAIR, ALSHAIN, TARAZED, DELTA_AQUILAE, DENEB_EL_OKAB_BOREALIS,
    DENEB_EL_OKAB_AUSTRALIS, BAZAK, TSEEN_FOO, AL_THALIMAIM_POSTERIOR,
    AL_THALIMAIM_ANTERIOR, LIBERTAS, BERED
    AQUILA_STAR_NAMES
    aquila_star_at() and all per-star _at() functions
    list_aquila_stars(), available_aquila_stars()

Stars sourced from sefstars.txt via moira.fixed_stars.
"""
from ..fixed_stars import fixed_star_at, StarPosition, list_stars

ALTAIR                    = "Altair"
ALSHAIN                   = "Alshain"
TARAZED                   = "Tarazed"
DELTA_AQUILAE             = "Delta Aquilae"
DENEB_EL_OKAB_BOREALIS    = "Deneb el Okab Borealis"
DENEB_EL_OKAB_AUSTRALIS   = "Deneb el Okab Australis"
BAZAK                     = "Bazak"
TSEEN_FOO                 = "Tseen Foo"
AL_THALIMAIM_POSTERIOR    = "Al Thalimaim Posterior"
AL_THALIMAIM_ANTERIOR     = "Al Thalimaim Anterior"
LIBERTAS                  = "Libertas"
BERED                     = "Bered"

AQUILA_STAR_NAMES = {
    ALTAIR:                  "Altair",
    ALSHAIN:                 "Alshain",
    TARAZED:                 "Tarazed",
    DELTA_AQUILAE:           "Delta Aquilae",
    DENEB_EL_OKAB_BOREALIS:  "Deneb el Okab Borealis",
    DENEB_EL_OKAB_AUSTRALIS: "Deneb el Okab Australis",
    BAZAK:                   "Bazak",
    TSEEN_FOO:               "Tseen Foo",
    AL_THALIMAIM_POSTERIOR:  "Al Thalimaim Posterior",
    AL_THALIMAIM_ANTERIOR:   "Al Thalimaim Anterior",
    LIBERTAS:                "Libertas",
    BERED:                   "Bered",
}


def aquila_star_at(name: str, jd_tt: float) -> StarPosition:
    return fixed_star_at(name, jd_tt)


def altair_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(ALTAIR, jd_tt)

def alshain_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(ALSHAIN, jd_tt)

def tarazed_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(TARAZED, jd_tt)

def delta_aquilae_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(DELTA_AQUILAE, jd_tt)

def deneb_el_okab_borealis_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(DENEB_EL_OKAB_BOREALIS, jd_tt)

def deneb_el_okab_australis_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(DENEB_EL_OKAB_AUSTRALIS, jd_tt)

def bazak_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(BAZAK, jd_tt)

def tseen_foo_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(TSEEN_FOO, jd_tt)

def al_thalimaim_posterior_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(AL_THALIMAIM_POSTERIOR, jd_tt)

def al_thalimaim_anterior_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(AL_THALIMAIM_ANTERIOR, jd_tt)

def libertas_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(LIBERTAS, jd_tt)

def bered_at(jd_tt: float) -> StarPosition:
    return aquila_star_at(BERED, jd_tt)


def list_aquila_stars() -> list[str]:
    return list(AQUILA_STAR_NAMES.values())


def available_aquila_stars() -> list[str]:
    catalog = set(list_stars())
    return [name for name in AQUILA_STAR_NAMES.values() if name in catalog]
