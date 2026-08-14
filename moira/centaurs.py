"""
Centaur Oracle — moira/centaurs.py

Archetype: Oracle
Purpose: Provides named constants and per-body position functions for the
         six astrologically significant Centaur bodies: Chiron, Pholus,
         Nessus, Asbolus, Chariklo, and Hylonome.

Boundary declaration
--------------------
Owns:
    - NAIF ID constants (CHIRON, PHOLUS, NESSUS, ASBOLUS, CHARIKLO, HYLONOME).
    - CENTAUR_NAMES mapping (NAIF ID → canonical name).
    - centaur_at() dispatcher.
    - Per-body convenience functions (chiron_at, pholus_at, nessus_at).
    - list_centaurs() / available_centaurs() introspection.
Delegates:
    - All position computation to moira.asteroids.asteroid_at.
    - Kernel availability checks to moira.asteroids.available_in_kernel.

Import-time side effects: None.

External dependency assumptions:
    - Positions come from any admitted small-body reader that carries the
      body's NAIF ID (wheel catalog ``moira-asteroids-wheel`` is sufficient
      for this named set; the full 10,025-body catalog also covers them).
    - No Qt, no database, no OS threads.

Public surface / exports:
    CHIRON, PHOLUS, NESSUS, ASBOLUS, CHARIKLO, HYLONOME  (NAIF ID constants)
    CENTAUR_NAMES
    centaur_at(), chiron_at(), pholus_at(), nessus_at()
    list_centaurs(), available_centaurs()

Centaur positions are resolved through ``asteroid_at`` from whatever
admitted small-body kernel currently provides the NAIF ID.
"""

from __future__ import annotations

from .asteroids import asteroid_at, AsteroidData, available_in_kernel

# NAIF IDs for major centaurs
CHIRON   = 2002060
PHOLUS   = 2005145
NESSUS   = 2007066
ASBOLUS  = 2008405
CHARIKLO = 2010199
HYLONOME = 2010370

CENTAUR_NAMES = {
    CHIRON:   "Chiron",
    PHOLUS:   "Pholus",
    NESSUS:   "Nessus",
    ASBOLUS:  "Asbolus",
    CHARIKLO: "Chariklo",
    HYLONOME: "Hylonome",
}

def centaur_at(name_or_naif: str | int, jd_ut: float) -> AsteroidData:
    """Return the high-precision position of a Centaur at jd_ut."""
    return asteroid_at(name_or_naif, jd_ut)

def chiron_at(jd_ut: float) -> AsteroidData:
    """Specialized getter for Chiron."""
    return centaur_at(CHIRON, jd_ut)

def pholus_at(jd_ut: float) -> AsteroidData:
    """Specialized getter for Pholus."""
    return centaur_at(PHOLUS, jd_ut)

def nessus_at(jd_ut: float) -> AsteroidData:
    """Specialized getter for Nessus."""
    return centaur_at(NESSUS, jd_ut)

def list_centaurs() -> list[str]:
    """Return names of centaurs known to this API."""
    return list(CENTAUR_NAMES.values())

def available_centaurs() -> list[str]:
    """Return names of centaurs actually available in the loaded kernels."""
    available = available_in_kernel()
    return [name for name in CENTAUR_NAMES.values() if name in available]
