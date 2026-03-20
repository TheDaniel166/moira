"""
moira.compat — Compatibility Adapter Pillar

Architectural role:
    Shared concern pillar. Governs all translation layers between Moira's
    native ephemeris model and the parameterizations used by external reference
    systems (NASA eclipse canon, etc.). No computation originates here; every
    sub-package re-expresses Moira outputs in a foreign convention.

Export/re-export stability contract:
    This package exposes no symbols directly. All public surfaces are declared
    by sub-packages (e.g. moira.compat.nasa). Callers must import from the
    appropriate sub-package, not from moira.compat itself.

Significant dependency boundaries:
    - Depends on moira.eclipse, moira.eclipse_canon, and moira.julian for
      source data; never on Qt, database, or OS-level services.
    - Sub-packages may import freely from the moira core pillars.

Import-time initialization side effects: None.
"""
