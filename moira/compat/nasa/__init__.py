"""
moira.compat.nasa — NASA Eclipse Compatibility Adapter

Architectural role:
    Leaf adapter pillar. Translates Moira's native lunar eclipse outputs into
    the contact-time and geometry parameterization published by NASA's eclipse
    canon. Serves callers who need to compare Moira results directly against
    NASA Five Millennium Canon tables or similar NASA-format references.

Export/re-export stability contract:
    Frozen exports (stable public API):
        NasaLunarEclipseContacts  — contact-time vessel (frozen dataclass)
        NasaLunarEclipseEvent     — full NASA-parameterized event record
        next_nasa_lunar_eclipse()
        previous_nasa_lunar_eclipse()
        translate_lunar_eclipse_event()
    All five names are re-exported via __all__ and are considered stable.

Significant dependency boundaries:
    - Depends on moira.eclipse (EclipseCalculator, EclipseEvent).
    - Depends on moira.eclipse_canon (geometry, contacts, canon method).
    - Depends on moira.julian (ut_to_tt_nasa_canon).
    - No Qt, no database, no OS threads.

Import-time initialization side effects: None.
"""

from .eclipse import (
    NasaLunarEclipseContacts,
    NasaLunarEclipseEvent,
    next_nasa_lunar_eclipse,
    previous_nasa_lunar_eclipse,
    translate_lunar_eclipse_event,
)

__all__ = [
    "NasaLunarEclipseContacts",
    "NasaLunarEclipseEvent",
    "next_nasa_lunar_eclipse",
    "previous_nasa_lunar_eclipse",
    "translate_lunar_eclipse_event",
]
