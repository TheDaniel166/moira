"""
Classical Asteroid Oracle — moira/classical_asteroids.py

Archetype: Oracle
Purpose: Provides named constants and per-body position functions for the
         four classical main-belt asteroids: Ceres, Pallas, Juno, and Vesta.

Boundary declaration
--------------------
Owns:
    - NAIF ID constants (CERES, PALLAS, JUNO, VESTA).
    - CLASSICAL_NAMES mapping (NAIF ID → canonical name).
    - classical_asteroid_at() dispatcher.
    - Per-body convenience functions (ceres_at, pallas_at, juno_at, vesta_at).
    - list_classical_asteroids() / available_classical_asteroids() introspection.
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
    CERES, PALLAS, JUNO, VESTA  (NAIF ID constants)
    CLASSICAL_NAMES
    classical_asteroid_at(), ceres_at(), pallas_at(), juno_at(), vesta_at()
    list_classical_asteroids(), available_classical_asteroids()

Classical asteroid positions are resolved through ``asteroid_at`` from
whatever admitted small-body kernel currently provides the NAIF ID.
"""

from __future__ import annotations

from .asteroids import asteroid_at, AsteroidData, available_in_kernel

# NAIF IDs for the four classical main-belt asteroids
CERES  = 2000001
PALLAS = 2000002
JUNO   = 2000003
VESTA  = 2000004

CLASSICAL_NAMES = {
    CERES:  "Ceres",
    PALLAS: "Pallas",
    JUNO:   "Juno",
    VESTA:  "Vesta",
}


def classical_asteroid_at(name_or_naif: str | int, jd_ut: float) -> AsteroidData:
    """Return the position of a Classical Asteroid at jd_ut."""
    return asteroid_at(name_or_naif, jd_ut)


def ceres_at(jd_ut: float) -> AsteroidData:
    """Specialized getter for Ceres."""
    return classical_asteroid_at(CERES, jd_ut)


def pallas_at(jd_ut: float) -> AsteroidData:
    """Specialized getter for Pallas."""
    return classical_asteroid_at(PALLAS, jd_ut)


def juno_at(jd_ut: float) -> AsteroidData:
    """Specialized getter for Juno."""
    return classical_asteroid_at(JUNO, jd_ut)


def vesta_at(jd_ut: float) -> AsteroidData:
    """Specialized getter for Vesta."""
    return classical_asteroid_at(VESTA, jd_ut)


def list_classical_asteroids() -> list[str]:
    """Return names of classical asteroids known to this API."""
    return list(CLASSICAL_NAMES.values())


def available_classical_asteroids() -> list[str]:
    """Return names of classical asteroids actually available in the loaded kernels."""
    available = available_in_kernel()
    return [name for name in CLASSICAL_NAMES.values() if name in available]
