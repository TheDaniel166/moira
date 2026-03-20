"""
Trans-Neptunian Oracle — moira/tno.py

Archetype: Oracle
Purpose: Provides named constants and per-body position functions for the
         four astrologically significant Trans-Neptunian Objects (TNOs):
         Ixion, Quaoar, Varuna, and Orcus.

Boundary declaration
--------------------
Owns:
    - NAIF ID constants (IXION, QUAOAR, VARUNA, ORCUS).
    - TNO_NAMES mapping (NAIF ID → canonical name).
    - tno_at() dispatcher.
    - Per-body convenience functions (ixion_at, quaoar_at, varuna_at, orcus_at).
    - list_tnos() / available_tnos() introspection.
Delegates:
    - All position computation to moira.asteroids.asteroid_at.
    - Kernel availability checks to moira.asteroids.available_in_kernel.

Import-time side effects: None.

External dependency assumptions:
    - sb441-n373s.bsp must be present before any position query is made;
      FileNotFoundError is raised otherwise.
    - No Qt, no database, no OS threads.

Public surface / exports:
    IXION, QUAOAR, VARUNA, ORCUS  (NAIF ID constants)
    TNO_NAMES
    tno_at(), ixion_at(), quaoar_at(), varuna_at(), orcus_at()
    list_tnos(), available_tnos()

TNO bodies are calculated using the sb441-n373s.bsp kernel.
"""

from typing import TYPE_CHECKING

from .asteroids import asteroid_at, AsteroidData, available_in_kernel

if TYPE_CHECKING:
    from pathlib import Path

# NAIF IDs for major TNOs
IXION  = 2028978
QUAOAR = 2050000
VARUNA = 2020000
ORCUS  = 2090482

TNO_NAMES = {
    IXION:  "Ixion",
    QUAOAR: "Quaoar",
    VARUNA: "Varuna",
    ORCUS:  "Orcus",
}

def tno_at(name_or_naif: str | int, jd_ut: float) -> AsteroidData:
    """
    Return the high-precision position of a TNO at jd_ut.
    Requires sb441-n373s.bsp in the project root or kernels/ directory.
    """
    return asteroid_at(name_or_naif, jd_ut)

def ixion_at(jd_ut: float) -> AsteroidData:
    """Specialized getter for Ixion."""
    return tno_at(IXION, jd_ut)

def quaoar_at(jd_ut: float) -> AsteroidData:
    """Specialized getter for Quaoar."""
    return tno_at(QUAOAR, jd_ut)

def varuna_at(jd_ut: float) -> AsteroidData:
    """Specialized getter for Varuna."""
    return tno_at(VARUNA, jd_ut)

def orcus_at(jd_ut: float) -> AsteroidData:
    """Specialized getter for Orcus."""
    return tno_at(ORCUS, jd_ut)

def list_tnos() -> list[str]:
    """Return names of TNOs known to this API."""
    return list(TNO_NAMES.values())

def available_tnos() -> list[str]:
    """Return names of TNOs actually available in the loaded kernels."""
    available = available_in_kernel()
    return [name for name in TNO_NAMES.values() if name in available]
