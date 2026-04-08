"""
Moira — Varga Engine
=====================

Archetype: Engine

Purpose
-------
Governs computation of Vedic divisional chart (varga) positions, mapping
any sidereal ecliptic longitude into one of the 16 Shodashvarga divisions
(D1 through D60) defined by Parashara.

Each wrapper accepts a **sidereal** longitude.  Tropical-to-sidereal
conversion is the caller's responsibility (see ``moira.sidereal``).

Five divisions require Parashari sign-offset rules that deviate from the
generic ``segment_idx % 12`` formula:

  D2  Hora           — odd/even sign parity selects Leo or Cancer.
  D4  Chaturthamsha  — segments start from the sign's own index.
  D27 Saptavimshamsha — segments start from the triplicity root sign.
  D40 Khavedamsha    — odd signs start Aries; even signs start Libra.
  D45 Akshavedamsha  — odd signs start Aries; even signs start Capricorn.

All remaining vargas use the generic formula.

Tradition and sources
---------------------
Parashara, "Brihat Parashara Hora Shastra" (BPHS), Shodashavarga Adhyaya,
Chapters 6–22.  Specific sign-offset rules are derived from the Parashari
tables as consolidated in B.V. Raman, "How to Judge a Horoscope" and
verified against Jhora (Jagannatha Hora) reference output.

Boundary declaration
--------------------
Owns: varga division arithmetic, Parashari sign-offset rule implementations,
      the ``VargaPoint`` result vessel, and all 16 Shodashvarga convenience
      wrappers.
Delegates: sign name and symbol lookup to ``moira.constants``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required.  No database access.  Pure arithmetic over
sidereal ecliptic longitudes.

Public surface
--------------
``VargaPoint``        — result vessel for a body's position in a varga.
``calculate_varga``   — compute any varga by generic formula.
``navamsa``           — D9  Navamsha.
``saptamsa``          — D7  Saptamsha.
``dashamansa``        — D10 Dashamsha.
``dwadashamsa``       — D12 Dwadashamsha.
``trimshamsa``        — D30 Trimshamsha.
``hora``              — D2  Hora          (Parashari sign-offset rule).
``chaturthamsha``     — D4  Chaturthamsha (Parashari sign-offset rule).
``shashthamsha``      — D6  Shashthamsha  (generic).
``ashtamsha``         — D8  Ashtamsha     (generic).
``shodashamsha``      — D16 Shodashamsha  (generic).
``vimshamsha``        — D20 Vimshamsha    (generic).
``chaturvimshamsha``  — D24 Chaturvimshamsha (generic).
``saptavimshamsha``   — D27 Saptavimshamsha (Parashari triplicity-start rule).
``khavedamsha``       — D40 Khavedamsha  (Parashari odd/even-start rule).
``akshavedamsha``     — D45 Akshavedamsha (Parashari odd/even-start rule).
``shashtiamsha``      — D60 Shashtiamsha (generic).
"""

from dataclasses import dataclass
from .constants import sign_of, SIGNS, SIGN_SYMBOLS

__all__ = [
    # Core
    "VargaPoint",
    "calculate_varga",
    # Original wrappers
    "navamsa",
    "saptamsa",
    "dashamansa",
    "dwadashamsa",
    "trimshamsa",
    # Shodashvarga completion
    "hora",
    "chaturthamsha",
    "shashthamsha",
    "ashtamsha",
    "shodashamsha",
    "vimshamsha",
    "chaturvimshamsha",
    "saptavimshamsha",
    "khavedamsha",
    "akshavedamsha",
    "shashtiamsha",
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
              ``calculate_varga`` or the Parashari wrapper functions).
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
    # but the geometric division is the standard computational alternative.
    return calculate_varga(longitude, 30, "Trimshamsa")


# ---------------------------------------------------------------------------
# Internal helpers — Parashari sign-offset arithmetic
#
# Each function returns the Parashari-correct varga sign index (0–11) for
# the given D1 sign index and degree within that sign.  They are NOT the
# generic segment_idx % 12 result.
# ---------------------------------------------------------------------------

# D27 triplicity start signs: Aries(0) for Fire, Cancer(3) for Earth,
# Libra(6) for Air, Capricorn(9) for Water.  Indexed by D1 sign 0–11.
_D27_TRIPLICITY_START: tuple[int, ...] = (
    0, 3, 6, 9,   # Aries(fire), Taurus(earth), Gemini(air), Cancer(water)
    0, 3, 6, 9,   # Leo(fire), Virgo(earth), Libra(air), Scorpio(water)
    0, 3, 6, 9,   # Sagittarius(fire), Capricorn(earth), Aquarius(air), Pisces(water)
)


def _hora_sign(sign_idx: int, deg_in_sign: float) -> int:
    """
    D2 Hora sign index by Parashari rule.

    Odd D1 signs (sign_idx % 2 == 0 in 0-based indexing, because Aries=0
    is the 1st / odd sign):
        first half  (0°–15°) → Leo (index 4)
        second half (15°–30°) → Cancer (index 3)
    Even D1 signs: reversed.
    """
    half = 0 if deg_in_sign < 15.0 else 1
    is_odd = (sign_idx % 2 == 0)   # 0-based: Aries=0=1st=odd
    if is_odd:
        return 4 if half == 0 else 3   # Leo, Cancer
    else:
        return 3 if half == 0 else 4   # Cancer, Leo


def _d4_sign(sign_idx: int, deg_in_sign: float) -> int:
    """
    D4 Chaturthamsha sign index by Parashari rule.

    Each sign is divided into four 7.5° segments.  The first segment maps
    to the sign itself; subsequent segments advance by one sign each.
    """
    segment = int(deg_in_sign / 7.5)   # 0–3
    return (sign_idx + segment) % 12


def _d27_sign(sign_idx: int, deg_in_sign: float) -> int:
    """
    D27 Saptavimshamsha sign index by Parashari triplicity-start rule.

    Segments start from the triplicity root sign (Aries for fire signs,
    Cancer for earth, Libra for air, Capricorn for water) and advance
    one sign per 30/27° segment.
    """
    start = _D27_TRIPLICITY_START[sign_idx]
    segment = int(deg_in_sign / (30.0 / 27))   # 0–26
    return (start + segment) % 12


def _d40_sign(sign_idx: int, deg_in_sign: float) -> int:
    """
    D40 Khavedamsha sign index by Parashari odd/even-start rule.

    Odd D1 signs start from Aries (index 0); even start from Libra (index 6).
    Each segment spans 30/40 = 0.75°.
    """
    seg = int(deg_in_sign / 0.75)      # 0–39
    start = 0 if (sign_idx % 2 == 0) else 6   # Aries or Libra
    return (start + seg) % 12


def _d45_sign(sign_idx: int, deg_in_sign: float) -> int:
    """
    D45 Akshavedamsha sign index by Parashari odd/even-start rule.

    Odd D1 signs start from Aries (index 0); even start from Capricorn
    (index 9).  Each segment spans 30/45 = 0.6̄°.
    """
    seg = int(deg_in_sign / (30.0 / 45))   # 0–44
    start = 0 if (sign_idx % 2 == 0) else 9   # Aries or Capricorn
    return (start + seg) % 12


def _build_varga_point(
    longitude: float,
    sign_idx: int,
    sign_degree: float,
    n: int,
    name: str,
) -> VargaPoint:
    """Construct a VargaPoint from a pre-computed Parashari sign index."""
    sign_name = SIGNS[sign_idx]
    sign_sym  = SIGN_SYMBOLS[sign_idx]
    return VargaPoint(
        varga_name=name,
        varga_number=n,
        longitude=longitude,
        varga_longitude=sign_idx * 30.0 + sign_degree,
        sign=sign_name,
        sign_symbol=sign_sym,
        sign_degree=sign_degree,
    )


# ---------------------------------------------------------------------------
# Shodashvarga completion — Parashari wrappers
# ---------------------------------------------------------------------------

def hora(sidereal_longitude: float) -> VargaPoint:
    """
    D2 Hora — Wealth and Prosperity.

    Uses the Parashari sign-offset rule: the two 15° halves of each sign
    map to Leo or Cancer depending on whether the sign is odd or even in
    the natural zodiac order.  This is NOT the generic D2 formula.

    Parameters
    ----------
    sidereal_longitude : float
        Sidereal ecliptic longitude in degrees.  Caller is responsible for
        tropical-to-sidereal conversion.

    Returns
    -------
    VargaPoint
        ``varga_number`` is 2.  ``sign`` is always Cancer or Leo.
    """
    lon = sidereal_longitude % 360.0
    sign_idx    = int(lon // 30)
    deg_in_sign = lon % 30.0
    h_sign      = _hora_sign(sign_idx, deg_in_sign)
    sign_degree = (deg_in_sign % 15.0) * 2      # position within the 15° segment scaled to 30°
    return _build_varga_point(lon, h_sign, sign_degree, 2, "Hora")


def chaturthamsha(sidereal_longitude: float) -> VargaPoint:
    """
    D4 Chaturthamsha — Property, Fixed Assets.

    Uses the Parashari sign-offset rule: segments start from the D1 sign
    itself and advance one sign each 7.5°.

    Parameters
    ----------
    sidereal_longitude : float
        Sidereal ecliptic longitude in degrees.

    Returns
    -------
    VargaPoint
        ``varga_number`` is 4.
    """
    lon = sidereal_longitude % 360.0
    sign_idx    = int(lon // 30)
    deg_in_sign = lon % 30.0
    d4_s        = _d4_sign(sign_idx, deg_in_sign)
    sign_degree = (deg_in_sign % 7.5) * 4
    return _build_varga_point(lon, d4_s, sign_degree, 4, "Chaturthamsha")


def shashthamsha(sidereal_longitude: float) -> VargaPoint:
    """D6 Shashthamsha — Health, Enemies, Debts (generic formula)."""
    return calculate_varga(sidereal_longitude, 6, "Shashthamsha")


def ashtamsha(sidereal_longitude: float) -> VargaPoint:
    """D8 Ashtamsha — Longevity, Obstacles (generic formula)."""
    return calculate_varga(sidereal_longitude, 8, "Ashtamsha")


def shodashamsha(sidereal_longitude: float) -> VargaPoint:
    """D16 Shodashamsha — Vehicles, Conveyances (generic formula)."""
    return calculate_varga(sidereal_longitude, 16, "Shodashamsha")


def vimshamsha(sidereal_longitude: float) -> VargaPoint:
    """D20 Vimshamsha — Spiritual Progress (generic formula)."""
    return calculate_varga(sidereal_longitude, 20, "Vimshamsha")


def chaturvimshamsha(sidereal_longitude: float) -> VargaPoint:
    """D24 Chaturvimshamsha — Education, Learning (generic formula)."""
    return calculate_varga(sidereal_longitude, 24, "Chaturvimshamsha")


def saptavimshamsha(sidereal_longitude: float) -> VargaPoint:
    """
    D27 Saptavimshamsha — Strength Assessment (Bala).

    Uses the Parashari triplicity-start rule: the 27 segments within each
    sign begin from the triplicity root sign (Aries for fire, Cancer for
    earth, Libra for air, Capricorn for water).

    Parameters
    ----------
    sidereal_longitude : float
        Sidereal ecliptic longitude in degrees.

    Returns
    -------
    VargaPoint
        ``varga_number`` is 27.
    """
    lon = sidereal_longitude % 360.0
    sign_idx    = int(lon // 30)
    deg_in_sign = lon % 30.0
    d27_s       = _d27_sign(sign_idx, deg_in_sign)
    seg_width   = 30.0 / 27
    sign_degree = (deg_in_sign % seg_width) * 27
    return _build_varga_point(lon, d27_s, sign_degree, 27, "Saptavimshamsha")


def khavedamsha(sidereal_longitude: float) -> VargaPoint:
    """
    D40 Khavedamsha — Auspicious/Inauspicious Effects.

    Uses the Parashari odd/even-start rule: odd signs start from Aries,
    even signs start from Libra.  Each segment spans 0.75°.

    Parameters
    ----------
    sidereal_longitude : float
        Sidereal ecliptic longitude in degrees.

    Returns
    -------
    VargaPoint
        ``varga_number`` is 40.
    """
    lon = sidereal_longitude % 360.0
    sign_idx    = int(lon // 30)
    deg_in_sign = lon % 30.0
    d40_s       = _d40_sign(sign_idx, deg_in_sign)
    sign_degree = (deg_in_sign % 0.75) * 40
    return _build_varga_point(lon, d40_s, sign_degree, 40, "Khavedamsha")


def akshavedamsha(sidereal_longitude: float) -> VargaPoint:
    """
    D45 Akshavedamsha — General Indications (all matters).

    Uses the Parashari odd/even-start rule: odd signs start from Aries,
    even signs start from Capricorn.  Each segment spans 30/45°.

    Parameters
    ----------
    sidereal_longitude : float
        Sidereal ecliptic longitude in degrees.

    Returns
    -------
    VargaPoint
        ``varga_number`` is 45.
    """
    lon = sidereal_longitude % 360.0
    sign_idx    = int(lon // 30)
    deg_in_sign = lon % 30.0
    d45_s       = _d45_sign(sign_idx, deg_in_sign)
    seg_width   = 30.0 / 45
    sign_degree = (deg_in_sign % seg_width) * 45
    return _build_varga_point(lon, d45_s, sign_degree, 45, "Akshavedamsha")


def shashtiamsha(sidereal_longitude: float) -> VargaPoint:
    """
    D60 Shashtiamsha — Past-Life Karma (generic formula).

    The 60 Shashtiamsha divisions each span 0.5°.  Sign assignment uses
    the generic formula.  The optional named Shashtiamsha lords (60
    traditional names from BPHS) are not yet implemented.

    Parameters
    ----------
    sidereal_longitude : float
        Sidereal ecliptic longitude in degrees.

    Returns
    -------
    VargaPoint
        ``varga_number`` is 60.
    """
    return calculate_varga(sidereal_longitude, 60, "Shashtiamsha")
