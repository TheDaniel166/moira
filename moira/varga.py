"""
Moira — Varga Engine
=====================

Archetype: Engine

Purpose
-------
Governs computation of Vedic divisional chart (varga) positions, mapping
any ecliptic longitude into one of the 16 primary Shodashvarga divisions
(D1 through D60) and beyond.

Boundary declaration
--------------------
Owns: varga division arithmetic, sign assignment, the ``VargaPoint`` result
      vessel, and convenience functions for the most common vargas.
Delegates: sign name and symbol lookup to ``moira.constants``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure arithmetic over
ecliptic longitudes.

Public surface
--------------
``VargaPoint``      — vessel for a body's position in a divisional chart.
``calculate_varga`` — compute any varga division for a longitude.
``navamsa``         — D9 Navamsa convenience function.
``saptamsa``        — D7 Saptamsa convenience function.
``dashamansa``      — D10 Dashamansa convenience function.
``dwadashamsa``     — D12 Dwadashamsa convenience function.
``trimshamsa``      — D30 Trimshamsa convenience function.
"""

from dataclasses import dataclass
from .constants import sign_of, SIGNS, SIGN_SYMBOLS

__all__ = [
    "VargaPoint",
    "calculate_varga",
    "navamsa",
    "saptamsa",
    "dashamansa",
    "dwadashamsa",
    "trimshamsa",
]

@dataclass(slots=True)
class VargaPoint:
    """
    RITE: The Division Vessel — a body's place in a Vedic divisional chart.

    THEOREM: Holds the varga name, division number, original longitude,
    varga-mapped longitude, and sign data for a single body's position in
    a specific Vedic divisional chart.

    RITE OF PURPOSE:
        Serves the Varga Engine as the canonical result vessel for all
        divisional chart computations. Without this vessel, callers would
        receive raw sign indices with no varga name, division number, or
        degree-within-sign context, making Jyotish chart display and
        interpretation impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store the varga name (e.g. "Navamsa"), division number (e.g. 9),
              original longitude, varga-mapped longitude, sign name, sign
              symbol, and degree within the varga sign.
        Non-responsibilities:
            - Does not compute the varga position (delegated to
              ``calculate_varga``).
            - Does not apply traditional Parasari sign-offset rules for
              specific vargas (the standard geometric division is used).
        Dependencies:
            - Populated by ``calculate_varga()`` and its convenience wrappers.
        Structural invariants:
            - ``varga_longitude`` is always in [0, 360).
            - ``sign_degree`` is always in [0, 30).
        Succession stance: terminal — not designed for subclassing.

    Canon: Parashara, "Brihat Parashara Hora Shastra" (classical Jyotish
           foundational text).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.varga.VargaPoint",
        "risk": "medium",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": [
                "varga_name", "varga_number", "longitude",
                "varga_longitude", "sign", "sign_symbol", "sign_degree"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "varga_name", "varga_number", "longitude",
                "varga_longitude", "sign", "sign_symbol", "sign_degree"
            ]
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller ensures finite longitude before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    varga_name: str
    varga_number: int
    longitude: float       # Original tropical/sidereal longitude
    varga_longitude: float # Longitude localized to the varga sign
    sign: str
    sign_symbol: str
    sign_degree: float

    def __repr__(self) -> str:
        d = int(self.sign_degree)
        m = int((self.sign_degree - d) * 60)
        return (f"{self.varga_name} (D{self.varga_number}): "
                f"{d}°{m:02d}′ {self.sign} {self.sign_symbol}")

def calculate_varga(longitude: float, n: int, name: str = "") -> VargaPoint:
    """
    Calculate the divisional (varga) position for a given longitude and division 'n'.
    
    Formula:
      SignIndex = floor(longitude / (30/n)) % 12
    
    Note: Standard Parasari vargas often have specific starting offsets 
    per sign (Fire/Earth/Air/Water). 
    """
    longitude = longitude % 360.0

    # Total segments of size (30/n) from 0° Aries
    segment_idx = int(longitude // (30.0 / n))
    
    # The Varga Sign Index
    # For many vargas (D2, D3, D9, D12), the segments simply cycle through the zodiac.
    # D1 (Rashi): index = floor(L/30) % 12
    # D9 (Navamsa): index = floor(L/(30/9)) % 12
    sign_idx = segment_idx % 12
    
    sign_name = SIGNS[sign_idx]
    sign_sym = SIGN_SYMBOLS[sign_idx]
    
    # Degree within the varga sign
    # We map the segment (30/n) to a full sign (30 degrees)
    varga_deg = (longitude % (30.0 / n)) * n
    
    return VargaPoint(
        varga_name=name or f"D{n}",
        varga_number=n,
        longitude=longitude,
        varga_longitude=(sign_idx * 30.0 + varga_deg),
        sign=sign_name,
        sign_symbol=sign_sym,
        sign_degree=varga_deg
    )

def navamsa(longitude: float) -> VargaPoint:
    """Convenience for D9 Navamsa."""
    return calculate_varga(longitude, 9, "Navamsa")

def saptamsa(longitude: float) -> VargaPoint:
    """D7 Saptamsa (Children/Progeny)."""
    return calculate_varga(longitude, 7, "Saptamsa")

def dashamansa(longitude: float) -> VargaPoint:
    """D10 Dashamansa (Career/Status)."""
    return calculate_varga(longitude, 10, "Dashamansa")

def dwadashamsa(longitude: float) -> VargaPoint:
    """D12 Dwadashamsa (Parents/Lineage)."""
    return calculate_varga(longitude, 12, "Dwadashamsa")

def trimshamsa(longitude: float) -> VargaPoint:
    """D30 Trimshamsa (Complexities/Misfortune)."""
    # Note: Traditional D30 has specific degree ranges for planets, 
    # but the geometric division is a standard alternative.
    return calculate_varga(longitude, 30, "Trimshamsa")
