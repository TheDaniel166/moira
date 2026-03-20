"""
Main Belt Oracle — moira/main_belt.py

Archetype: Oracle
Purpose: Provides named constants and per-body position functions for the
         36 main-belt asteroids tracked by Moira (excluding the classical
         four Ceres/Pallas/Juno/Vesta, centaurs, and TNOs).

Boundary declaration
--------------------
Owns:
    - NAIF ID constants for 36 main-belt bodies (ASTRAEA through VIRGINIA).
    - MAIN_BELT_NAMES mapping (NAIF ID → canonical name).
    - main_belt_at() dispatcher.
    - Per-body convenience functions (astraea_at, hebe_at, … virginia_at).
    - list_main_belt() / available_main_belt() introspection.
Delegates:
    - All position computation to moira.asteroids.asteroid_at.
    - Kernel availability checks to moira.asteroids.available_in_kernel.

Import-time side effects: None.

External dependency assumptions:
    - asteroids.bsp (primary kernel) or sb441-n373s.bsp (secondary) must be
      present before any position query is made; FileNotFoundError is raised
      otherwise.
    - No Qt, no database, no OS threads.

Public surface / exports:
    ASTRAEA, HEBE, IRIS, FLORA, METIS, HYGIEA, PARTHENOPE, VICTORIA,
    EGERIA, IRENE, EUNOMIA, PSYCHE, THETIS, MELPOMENE, FORTUNA, MASSALIA,
    LUTETIA, KALLIOPE, THALIA, THEMIS, PROSERPINA, EUTERPE, BELLONA,
    AMPHITRITE, URANIA, EUPHROSYNE, POMONA, ISIS, ARIADNE, NYSA, EUGENIA,
    HESTIA, AGLAJA, DORIS, PALES, VIRGINIA  (NAIF ID constants)
    MAIN_BELT_NAMES
    main_belt_at() and all per-body _at() functions
    list_main_belt(), available_main_belt()

Bodies covered (Astraea through Virginia):
    Astraea, Hebe, Iris, Flora, Metis, Hygiea, Parthenope, Victoria,
    Egeria, Irene, Eunomia, Psyche, Thetis, Melpomene, Fortuna, Massalia,
    Lutetia, Kalliope, Thalia, Themis, Proserpina, Euterpe, Bellona,
    Amphitrite, Urania, Euphrosyne, Pomona, Isis, Ariadne, Nysa, Eugenia,
    Hestia, Aglaja, Doris, Pales, Virginia

Kernel sources:
    asteroids.bsp  (codes_300ast_20100725.bsp — primary, accurate main-belt)
    sb441-n373s.bsp  (supplemental, DE441-consistent)
"""
from typing import TYPE_CHECKING

from .asteroids import asteroid_at, AsteroidData, available_in_kernel

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# NAIF ID constants
# ---------------------------------------------------------------------------

ASTRAEA    = 2000005
HEBE       = 2000006
IRIS       = 2000007
FLORA      = 2000008
METIS      = 2000009
HYGIEA     = 2000010
PARTHENOPE = 2000011
VICTORIA   = 2000012
EGERIA     = 2000013
IRENE      = 2000014
EUNOMIA    = 2000015
PSYCHE     = 2000016
THETIS     = 2000017
MELPOMENE  = 2000018
FORTUNA    = 2000019
MASSALIA   = 2000020
LUTETIA    = 2000021
KALLIOPE   = 2000022
THALIA     = 2000023
THEMIS     = 2000024
PROSERPINA = 2000026
EUTERPE    = 2000027
BELLONA    = 2000028
AMPHITRITE = 2000029
URANIA     = 2000030
EUPHROSYNE = 2000031
POMONA     = 2000032
ISIS       = 2000042
ARIADNE    = 2000043
NYSA       = 2000044
EUGENIA    = 2000045
HESTIA     = 2000046
AGLAJA     = 2000047
DORIS      = 2000048
PALES      = 2000049
VIRGINIA   = 2000050

# ---------------------------------------------------------------------------
# Name mapping
# ---------------------------------------------------------------------------

MAIN_BELT_NAMES: dict[int, str] = {
    ASTRAEA:    "Astraea",
    HEBE:       "Hebe",
    IRIS:       "Iris",
    FLORA:      "Flora",
    METIS:      "Metis",
    HYGIEA:     "Hygiea",
    PARTHENOPE: "Parthenope",
    VICTORIA:   "Victoria",
    EGERIA:     "Egeria",
    IRENE:      "Irene",
    EUNOMIA:    "Eunomia",
    PSYCHE:     "Psyche",
    THETIS:     "Thetis",
    MELPOMENE:  "Melpomene",
    FORTUNA:    "Fortuna",
    MASSALIA:   "Massalia",
    LUTETIA:    "Lutetia",
    KALLIOPE:   "Kalliope",
    THALIA:     "Thalia",
    THEMIS:     "Themis",
    PROSERPINA: "Proserpina",
    EUTERPE:    "Euterpe",
    BELLONA:    "Bellona",
    AMPHITRITE: "Amphitrite",
    URANIA:     "Urania",
    EUPHROSYNE: "Euphrosyne",
    POMONA:     "Pomona",
    ISIS:       "Isis",
    ARIADNE:    "Ariadne",
    NYSA:       "Nysa",
    EUGENIA:    "Eugenia",
    HESTIA:     "Hestia",
    AGLAJA:     "Aglaja",
    DORIS:      "Doris",
    PALES:      "Pales",
    VIRGINIA:   "Virginia",
}

# ---------------------------------------------------------------------------
# Group dispatcher
# ---------------------------------------------------------------------------

def main_belt_at(name_or_naif: str | int, jd_ut: float) -> AsteroidData:
    """
    Return the position of a main-belt asteroid at jd_ut.

    Delegates to asteroid_at(); accepts either a canonical name string or
    an integer NAIF ID.
    """
    return asteroid_at(name_or_naif, jd_ut)

# ---------------------------------------------------------------------------
# Per-body convenience functions
# ---------------------------------------------------------------------------

def astraea_at(jd_ut: float) -> AsteroidData:
    """Return position of Astraea at jd_ut."""
    return main_belt_at(ASTRAEA, jd_ut)

def hebe_at(jd_ut: float) -> AsteroidData:
    """Return position of Hebe at jd_ut."""
    return main_belt_at(HEBE, jd_ut)

def iris_at(jd_ut: float) -> AsteroidData:
    """Return position of Iris at jd_ut."""
    return main_belt_at(IRIS, jd_ut)

def flora_at(jd_ut: float) -> AsteroidData:
    """Return position of Flora at jd_ut."""
    return main_belt_at(FLORA, jd_ut)

def metis_at(jd_ut: float) -> AsteroidData:
    """Return position of Metis at jd_ut."""
    return main_belt_at(METIS, jd_ut)

def hygiea_at(jd_ut: float) -> AsteroidData:
    """Return position of Hygiea at jd_ut."""
    return main_belt_at(HYGIEA, jd_ut)

def parthenope_at(jd_ut: float) -> AsteroidData:
    """Return position of Parthenope at jd_ut."""
    return main_belt_at(PARTHENOPE, jd_ut)

def victoria_at(jd_ut: float) -> AsteroidData:
    """Return position of Victoria at jd_ut."""
    return main_belt_at(VICTORIA, jd_ut)

def egeria_at(jd_ut: float) -> AsteroidData:
    """Return position of Egeria at jd_ut."""
    return main_belt_at(EGERIA, jd_ut)

def irene_at(jd_ut: float) -> AsteroidData:
    """Return position of Irene at jd_ut."""
    return main_belt_at(IRENE, jd_ut)

def eunomia_at(jd_ut: float) -> AsteroidData:
    """Return position of Eunomia at jd_ut."""
    return main_belt_at(EUNOMIA, jd_ut)

def psyche_at(jd_ut: float) -> AsteroidData:
    """Return position of Psyche at jd_ut."""
    return main_belt_at(PSYCHE, jd_ut)

def thetis_at(jd_ut: float) -> AsteroidData:
    """Return position of Thetis at jd_ut."""
    return main_belt_at(THETIS, jd_ut)

def melpomene_at(jd_ut: float) -> AsteroidData:
    """Return position of Melpomene at jd_ut."""
    return main_belt_at(MELPOMENE, jd_ut)

def fortuna_at(jd_ut: float) -> AsteroidData:
    """Return position of Fortuna at jd_ut."""
    return main_belt_at(FORTUNA, jd_ut)

def massalia_at(jd_ut: float) -> AsteroidData:
    """Return position of Massalia at jd_ut."""
    return main_belt_at(MASSALIA, jd_ut)

def lutetia_at(jd_ut: float) -> AsteroidData:
    """Return position of Lutetia at jd_ut."""
    return main_belt_at(LUTETIA, jd_ut)

def kalliope_at(jd_ut: float) -> AsteroidData:
    """Return position of Kalliope at jd_ut."""
    return main_belt_at(KALLIOPE, jd_ut)

def thalia_at(jd_ut: float) -> AsteroidData:
    """Return position of Thalia at jd_ut."""
    return main_belt_at(THALIA, jd_ut)

def themis_at(jd_ut: float) -> AsteroidData:
    """Return position of Themis at jd_ut."""
    return main_belt_at(THEMIS, jd_ut)

def proserpina_at(jd_ut: float) -> AsteroidData:
    """Return position of Proserpina at jd_ut."""
    return main_belt_at(PROSERPINA, jd_ut)

def euterpe_at(jd_ut: float) -> AsteroidData:
    """Return position of Euterpe at jd_ut."""
    return main_belt_at(EUTERPE, jd_ut)

def bellona_at(jd_ut: float) -> AsteroidData:
    """Return position of Bellona at jd_ut."""
    return main_belt_at(BELLONA, jd_ut)

def amphitrite_at(jd_ut: float) -> AsteroidData:
    """Return position of Amphitrite at jd_ut."""
    return main_belt_at(AMPHITRITE, jd_ut)

def urania_at(jd_ut: float) -> AsteroidData:
    """Return position of Urania at jd_ut."""
    return main_belt_at(URANIA, jd_ut)

def euphrosyne_at(jd_ut: float) -> AsteroidData:
    """Return position of Euphrosyne at jd_ut."""
    return main_belt_at(EUPHROSYNE, jd_ut)

def pomona_at(jd_ut: float) -> AsteroidData:
    """Return position of Pomona at jd_ut."""
    return main_belt_at(POMONA, jd_ut)

def isis_at(jd_ut: float) -> AsteroidData:
    """Return position of Isis at jd_ut."""
    return main_belt_at(ISIS, jd_ut)

def ariadne_at(jd_ut: float) -> AsteroidData:
    """Return position of Ariadne at jd_ut."""
    return main_belt_at(ARIADNE, jd_ut)

def nysa_at(jd_ut: float) -> AsteroidData:
    """Return position of Nysa at jd_ut."""
    return main_belt_at(NYSA, jd_ut)

def eugenia_at(jd_ut: float) -> AsteroidData:
    """Return position of Eugenia at jd_ut."""
    return main_belt_at(EUGENIA, jd_ut)

def hestia_at(jd_ut: float) -> AsteroidData:
    """Return position of Hestia at jd_ut."""
    return main_belt_at(HESTIA, jd_ut)

def aglaja_at(jd_ut: float) -> AsteroidData:
    """Return position of Aglaja at jd_ut."""
    return main_belt_at(AGLAJA, jd_ut)

def doris_at(jd_ut: float) -> AsteroidData:
    """Return position of Doris at jd_ut."""
    return main_belt_at(DORIS, jd_ut)

def pales_at(jd_ut: float) -> AsteroidData:
    """Return position of Pales at jd_ut."""
    return main_belt_at(PALES, jd_ut)

def virginia_at(jd_ut: float) -> AsteroidData:
    """Return position of Virginia at jd_ut."""
    return main_belt_at(VIRGINIA, jd_ut)

# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------

def list_main_belt() -> list[str]:
    """Return names of all main-belt asteroids known to this API."""
    return list(MAIN_BELT_NAMES.values())


def available_main_belt() -> list[str]:
    """Return names of main-belt asteroids actually available in the loaded kernels."""
    available = available_in_kernel()
    return [name for name in MAIN_BELT_NAMES.values() if name in available]
