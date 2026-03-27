"""
Constellation Oracle Package â€” moira/constellations/

Archetype: Oracle (shared concern â€” star catalogue grouping by constellation)

Package architectural role:
    This package groups the fixed-star Oracle API by IAU constellation.
    Each sub-module provides named string constants, a constellation-scoped
    dispatcher, per-star convenience functions, and list/availability helpers
    for the stars of one constellation, all delegating position computation
    to moira.stars.star_at.

Export/re-export stability contract:
    All sub-module exports are stable.  No symbols are re-exported from this
    __init__.py; callers import directly from the sub-module they need
    (e.g. `from moira.constellations.stars_orion import rigel_at`).

Significant dependency boundaries:
    - All position computation delegates to moira.stars.
    - No dependency on moira.planets, moira.gaia, or any computation engine.

Import-time initialization side effects: None.
"""

