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

All remaining full-position wrappers default to the generic formula. D60
also admits Santhanam sign-only, PVR textbook/linear, and an explicitly
classical-derived proportional full-position profile.

Tradition and sources
---------------------
Parashara, "Brihat Parashara Hora Shastra" (BPHS), Shodashavarga Adhyaya.
The existing five sign-offset wrappers retain their arithmetic; their
historical Raman/JHora attribution is not newly source-validated here.

D60 admission: R. Santhanam, BPHS Vol. I, chapter 6.33-41, printed p.83
(PDF p.82). The commentary supports sign selection, not a continuous
degree mapping. See wiki/02_standards/D60_SOURCE_ADMISSION_STANDARD.md;
software agreement does not supply source authority for that mapping.
The separately named PVR profile combines Rao's 2000 textbook, section
6.2.20, with his 2013 divisional-longitude scaling rule. It is an explicitly
composed modern profile, not a continuous-degree attribution to BPHS.
The classical-derived profile combines the selected BPHS sign law with
Moira's proportional-coordinate extension, supported separately by Saravali
3.18, Jataka Parijata 3.43 and Raman's Prasna Marga 5.27-28 notes. Its receipt
distinguishes that derivation from a direct classical D60 degree prescription.

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
``shashtiamsha``      — D60 Shashtiamsha (explicit full-position profile).
``D60Method``         — harmonic, Santhanam sign-only or PVR textbook/linear.
``D60SignResult``     — immutable sign-only result with source receipt.
``d60_sign``          — sign selection under the explicitly chosen method.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite, nextafter
from .constants import SIGNS, SIGN_SYMBOLS

SHASHTIAMSHA_DEITIES: tuple[str, ...] = (
    "Ghora", "Rakshasa", "Deva", "Kuber", "Yaksh", "Kinnara", "Bhrasht", "Kulaghna",
    "Garal", "Vahni", "Maya", "Purishak", "Apampathi", "Marutwan", "Kaal", "Sarpa",
    "Amrit", "Indu", "Mridu", "Komal", "Heramba", "Brahma", "Vishnu", "Maheshwara",
    "Deva", "Ardr", "Kalinas", "Kshitees", "Kamalakar", "Gulik", "Mrityu", "Kaal",
    "Davagni", "Ghora", "Yama", "Kantak", "Sudha", "Amrit", "PurnaCandr", "Vishadagdha",
    "Kulanas", "Vamshakshaya", "Utpat", "Kaal", "Saumya", "Komal", "Sheetal", "Karaladamshtr",
    "Candramukhi", "Praveen", "Kaalpavak", "Dandayudha", "Nirmal", "Saumya", "Krur",
    "Atisheetal", "Amrit", "Payodhi", "Bhramana", "CandraRekha"
)

__all__ = [
    # Core
    "VargaPoint",
    "D60Method", "D60SignResult", "d60_sign",
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
    # Vimshopaka Bala + vargottama
    "VIMSHOPAKA_GROUPS",
    "VARGA_VISHVA",
    "VimshopakaVargaEntry",
    "VimshopakaBala",
    "varga_sign_index",
    "vimshopaka_bala",
    "vimshopaka_all",
    "is_vargottama",
    "vargottama_planets",
]


class D60Method(str, Enum):
    """Bounded D60 profiles; no claim of a universally correct classical law."""

    HARMONIC = "harmonic"
    SANTHANAM_SIGN = "bphs_santhanam_sign"
    PVR_TEXTBOOK_LINEAR = "pvr_textbook_linear"
    CLASSICAL_DERIVED_LINEAR = "classical_derived_linear"


def _d60_source_references(method: D60Method | None) -> tuple[str, ...]:
    if method is None:
        return ()
    _d60_method(method)
    if method is D60Method.HARMONIC:
        return ("moira_generic_harmonic",)
    if method is D60Method.SANTHANAM_SIGN:
        return ("BPHS-Santhanam-Vol1:6.33:printed83:commentary",)
    if method is D60Method.CLASSICAL_DERIVED_LINEAR:
        # BPHS governs the sign; the other passages support fractional
        # progress. Their extension to D60 degrees is explicitly Moira's
        # derivation, not a continuous-D60 prescription in those texts.
        return (
            "BPHS-Santhanam-Vol1:6.33:printed83:commentary",
            "Saravali:3.18:subdivision-coordinate",
            "Jataka-Parijata-Sastri:3.43:printed139:fractional-correspondence",
            "Prasna-Marga-Raman:5.27-28:printed171-173:notes:navamsa-degrees",
            "Moira:D60:classical-derived-proportional:v1",
        )
    return (
        "PVR-Integrated-Approach:2000:6.2.20:printed60",
        "PVR-Two-Novel-Transit-Principles:2013-12-31:v1:pdf2:Calculation",
    )


def _d60_method(method: D60Method) -> None:
    if not isinstance(method, D60Method):
        raise TypeError("d60_method must be a D60Method")


def _require_d60_full_point(method: D60Method) -> None:
    """Fail before any chart/resource work for a sign-only requested method."""
    _d60_method(method)
    if method is D60Method.SANTHANAM_SIGN:
        raise ValueError("bphs_santhanam_sign supports sign-only results; use d60_sign")


@dataclass(frozen=True, slots=True)
class D60SignResult:
    """Sign-level D60 placement; deliberately has no varga longitude or degree."""

    longitude: float
    sign_index: int
    method: D60Method

    def __post_init__(self) -> None:
        _d60_method(self.method)
        if isinstance(self.longitude, bool) or not isinstance(self.longitude, (int, float)):
            raise ValueError("longitude must be a finite number")
        if not 0 <= self.longitude < 360 or not isfinite(self.longitude):
            raise ValueError("longitude must be normalized to [0, 360)")
        if type(self.sign_index) is not int or not 0 <= self.sign_index < 12:
            raise ValueError("sign_index must be an integer in [0, 11]")

    @property
    def sign(self) -> str:
        return SIGNS[self.sign_index]

    @property
    def sign_symbol(self) -> str:
        return SIGN_SYMBOLS[self.sign_index]

    @property
    def position_scope(self) -> str:
        return "sign_only"

    @property
    def source_reference(self) -> str:
        return _d60_source_references(self.method)[0]


def d60_sign(sidereal_longitude: float, *, method: D60Method = D60Method.HARMONIC) -> D60SignResult:
    """D60 sign by explicit convention; no astronomical/frame conversion.

    Santhanam Vol. I, ch. 6.33 commentary (printed p.83): discard the
    natal sign for the degree calculation, double degrees, take integer
    remainder modulo twelve, and count that remainder forward from the
    natal sign. Capricorn 13d25m -> the third sign, Pisces. Even-sign
    reversal governs deity names, not this commentary's sign calculation.
    No continuous-degree law is admitted from that sign-level passage.
    """
    _d60_method(method)
    if isinstance(sidereal_longitude, bool) or not isinstance(sidereal_longitude, (int, float)):
        raise ValueError("sidereal_longitude must be a finite number without coercion")
    try:
        lon = float(sidereal_longitude)
    except OverflowError as exc:
        raise ValueError("sidereal_longitude must be finite") from exc
    if not isfinite(lon):
        raise ValueError("sidereal_longitude must be finite")
    lon %= 360.0
    # Modulo can round a tiny negative angle to 360; preserve its left
    # circular limit at the nearest representable angle inside the domain.
    if lon == 360.0:
        lon = nextafter(360.0, 0.0)
    natal_sign = int(lon // 30.0)
    segment = int((lon % 30.0) // 0.5)
    sign = (segment + (0 if method is D60Method.HARMONIC else natal_sign)) % 12
    return D60SignResult(lon, sign, method)


@dataclass(frozen=True, slots=True)
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
                "varga_longitude", "sign", "sign_symbol", "sign_degree", "deity", "d60_method",
                "d60_source_references", "d60_degree_attribution"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "varga_name", "varga_number", "longitude",
                "varga_longitude", "sign", "sign_symbol", "sign_degree", "deity", "d60_method"
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
            "raises": ["TypeError", "ValueError"],
            "policy": "reject invalid or sign-only D60 receipt; caller ensures finite longitude"
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
    deity: str | None = None
    d60_method: D60Method | None = None

    def __post_init__(self) -> None:
        if self.d60_method is not None:
            _require_d60_full_point(self.d60_method)
            if self.varga_number != 60:
                raise ValueError("d60_method applies only to division 60")

    @property
    def d60_source_references(self) -> tuple[str, ...]:
        """Applied source chain; empty for non-D60 or unknown method."""
        return _d60_source_references(self.d60_method)

    @property
    def d60_degree_attribution(self) -> str | None:
        """Degree authority category; classical-derived is not direct text."""
        if self.d60_method is None:
            return None
        return {
            D60Method.HARMONIC: "generic_harmonic",
            D60Method.PVR_TEXTBOOK_LINEAR: "modern_composed",
            D60Method.CLASSICAL_DERIVED_LINEAR: "classical_derived",
        }[self.d60_method]

    def __repr__(self) -> str:
        d = int(self.sign_degree)
        m = int((self.sign_degree - d) * 60)
        s = (f"{self.varga_name} (D{self.varga_number}): "
             f"{d}°{m:02d}′ {self.sign} {self.sign_symbol}")
        if self.deity:
            s += f" [{self.deity}]"
        return s

def _navamsa_partition(longitude: float) -> tuple[float, int, float]:
    """Partition the exact supplied binary angle by rational 10/3 degrees.

    Rounded floor division by 30/9 misassigns exact multiples such as 10
    and 30 degrees. Integer ratios also preserve either nextafter neighbour.
    """
    if isinstance(longitude, bool) or not isinstance(longitude, (int, float)):
        raise TypeError("longitude must be a finite number")
    longitude = float(longitude)
    if not isfinite(longitude):
        raise ValueError("longitude must be finite")
    longitude %= 360.0
    if longitude == 360.0:
        longitude = nextafter(360.0, 0.0)
    numerator, denominator = longitude.as_integer_ratio()
    segment, remainder = divmod(numerator * 9, denominator * 30)
    degree = min(remainder / denominator, nextafter(30.0, 0.0))
    return longitude, segment, degree


def calculate_varga(longitude: float, n: int, name: str = "") -> VargaPoint:
    """
    Calculate the divisional (varga) position for a given longitude and division 'n'.
    
    Formula:
      SignIndex = floor(longitude / (30/n)) % 12
    
    Note: Standard Parasari vargas often have specific starting offsets 
    per sign (Fire/Earth/Air/Water). 
    """
    if n == 9:
        longitude, segment, degree = _navamsa_partition(longitude)
        sign = segment % 12
        mapped = min(sign * 30.0 + degree, nextafter((sign + 1) * 30.0, 0.0))
        return VargaPoint(name or "D9", n, longitude, mapped,
                          SIGNS[sign], SIGN_SYMBOLS[sign], degree)
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
        sign_degree=varga_deg,
        d60_method=D60Method.HARMONIC if n == 60 else None,
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


def shashtiamsha(sidereal_longitude: float, *, d60_method: D60Method = D60Method.HARMONIC) -> VargaPoint:
    """
    D60 Shashtiamsha under an explicitly selected full-position profile.

    The 60 Shashtiamsha divisions each span 0.5°. Sign assignment uses
    the generic formula by default. PVR_TEXTBOOK_LINEAR counts signs from
    the natal sign and scales progress through each half-degree by 60.
    CLASSICAL_DERIVED_LINEAR uses the same coordinates, with BPHS sign
    assignment and Moira's proportional-degree derivation supported by
    Saravali 3.18, Jataka Parijata 3.43 and Raman's Prasna Marga 5.27-28
    notes. None of these passages directly prescribes continuous D60
    degrees. The PVR profile retains its separate modern source chain.
    The traditional named Shashtiamsha deities (60
    names from BPHS Chapter 6) are mapped, reversing order for even signs.

    Parameters
    ----------
    sidereal_longitude : float
        Sidereal ecliptic longitude in degrees.

    Returns
    -------
    VargaPoint
        ``varga_number`` is 60. ``deity`` is populated.
    """
    _require_d60_full_point(d60_method)
    # Retain the original harmonic numeric path. The opt-in profile uses
    # the strict sign helper's finite circular normalization.
    placement = (d60_sign(sidereal_longitude, method=d60_method)
                 if d60_method is not D60Method.HARMONIC else None)
    lon = placement.longitude if placement is not None else sidereal_longitude % 360.0
    sign_idx = int(lon // 30)
    deg_in_sign = lon % 30.0
    
    segment_in_sign = int(deg_in_sign // 0.5)
    is_odd = (sign_idx % 2 == 0)  # 0-based Aries is 0 (odd sign)
    
    deity_idx = segment_in_sign if is_odd else (59 - segment_in_sign)
    deity = SHASHTIAMSHA_DEITIES[deity_idx]
    
    if placement is None:
        vp = calculate_varga(sidereal_longitude, 60, "Shashtiamsha")
    else:
        degree = (deg_in_sign - segment_in_sign * 0.5) * 60.0
        lower = placement.sign_index * 30.0
        upper = lower + 30.0
        mapped = lower + degree
        # Addition can round a left-limit point to the next sign. Preserve
        # the selected segment's half-open domain without an epsilon window.
        if mapped >= upper:
            mapped = nextafter(upper, lower)
        vp = VargaPoint(
            "Shashtiamsha", 60, lon, mapped, placement.sign,
            placement.sign_symbol, degree, d60_method=d60_method,
        )
    return VargaPoint(
        varga_name=vp.varga_name,
        varga_number=vp.varga_number,
        longitude=vp.longitude,
        varga_longitude=vp.varga_longitude,
        sign=vp.sign,
        sign_symbol=vp.sign_symbol,
        sign_degree=vp.sign_degree,
        deity=deity,
        d60_method=vp.d60_method,
    )


# ---------------------------------------------------------------------------
# Vimshopaka Bala — 20-point weighted varga-dignity strength (BPHS)
#
# Governing object: BPHS Shodashavarga Adhyaya, Vimshopaka section.  For a
# chosen varga group, each division carries a fixed weight (weights sum to
# 20 per group); within each division the planet earns a vargavishwa share
# of that weight from its dignity toward the division sign's lord:
#
#   own sign 20/20, adhi mitra 18/20, mitra 15/20, sama 10/20,
#   shatru 7/20, adhi shatru 5/20.
#
# Exaltation does not participate in this metric (it is Uchcha Bala's
# domain); the dignity is purely lordship-relational (Panchadha Maitri,
# with temporary friendships taken from the D1 chart per standard
# practice).  Varga signs are resolved by the same doctrine as the rest of
# this module: Parashari offsets for D2/D3/D4/D27/D40/D45, geometric
# formula elsewhere (D30 geometric per the module-declared alternative).
# ---------------------------------------------------------------------------

VIMSHOPAKA_GROUPS: dict[str, dict[int, float]] = {
    # division -> weight; each group's weights sum to 20.
    'shadvarga':     {1: 6.0, 2: 2.0, 3: 4.0, 9: 5.0, 12: 2.0, 30: 1.0},
    'saptavarga':    {1: 5.0, 2: 2.0, 3: 3.0, 7: 2.5, 9: 4.5, 12: 2.0, 30: 1.0},
    'dashavarga':    {1: 3.0, 2: 1.5, 3: 1.5, 7: 1.5, 9: 1.5, 10: 1.5,
                      12: 1.5, 16: 1.5, 30: 1.5, 60: 5.0},
    'shodashavarga': {1: 3.5, 2: 1.0, 3: 1.0, 4: 0.5, 7: 0.5, 9: 3.0,
                      10: 0.5, 12: 0.5, 16: 2.0, 20: 0.5, 24: 0.5, 27: 0.5,
                      30: 1.0, 40: 0.5, 45: 0.5, 60: 4.0},
}

# Vargavishwa: dignity -> share of the division weight, on the 20 scale.
VARGA_VISHVA: dict[str, float] = {
    'own_sign':    20.0,
    'adhi_mitra':  18.0,
    'mitra':       15.0,
    'sama':        10.0,
    'shatru':       7.0,
    'adhi_shatru':  5.0,
}


def varga_sign_index(sidereal_longitude: float, n: int, *, d60_method: D60Method = D60Method.HARMONIC) -> int:
    """
    Return the varga sign index (0-11) for any supported division.

    Dispatches to the Parashari sign-offset rules for D2/D3/D4/D27/D40/D45
    and the generic formula elsewhere; D1 is the plain sidereal sign.
    D3 uses the Parashari trine drekkana (decan 1 -> same sign, decan 2 ->
    5th, decan 3 -> 9th), matching the Saptavargaja doctrine in
    ``moira.shadbala``.
    """
    _d60_method(d60_method)
    if d60_method is not D60Method.HARMONIC:
        if n != 60:
            raise ValueError("nondefault d60_method applies only to division 60")
        return d60_sign(sidereal_longitude, method=d60_method).sign_index
    if n == 9:
        return _navamsa_partition(sidereal_longitude)[1] % 12
    lon = sidereal_longitude % 360.0
    sign_idx = int(lon // 30)
    deg = lon % 30.0
    if n == 1:
        return sign_idx
    if n == 2:
        return _hora_sign(sign_idx, deg)
    if n == 3:
        return (sign_idx + int(deg / 10.0) * 4) % 12
    if n == 4:
        return _d4_sign(sign_idx, deg)
    if n == 27:
        return _d27_sign(sign_idx, deg)
    if n == 40:
        return _d40_sign(sign_idx, deg)
    if n == 45:
        return _d45_sign(sign_idx, deg)
    return int(lon // (30.0 / n)) % 12


@dataclass(frozen=True, slots=True)
class VimshopakaVargaEntry:
    """
    One division's contribution to a planet's Vimshopaka Bala.

    Attributes
    ----------
    division : int
        Varga divisor (1 for D1 ... 60 for D60).
    varga_sign_index : int
        The planet's sign index (0-11) in this division.
    lord : str
        Classical lord of that varga sign.
    dignity : str
        ``'own_sign'`` or the Panchadha Maitri compound relationship of the
        planet toward the lord (``adhi_mitra`` ... ``adhi_shatru``).
    vishva : float
        Vargavishwa share on the 20 scale (see ``VARGA_VISHVA``).
    weight : float
        This division's weight within the chosen group.
    points : float
        ``weight * vishva / 20`` — the actual contribution.
    """

    division:         int
    varga_sign_index: int
    lord:             str
    dignity:          str
    vishva:           float
    weight:           float
    points:           float


@dataclass(frozen=True, slots=True)
class VimshopakaBala:
    """
    A planet's Vimshopaka Bala for one varga group.

    Attributes
    ----------
    planet : str
    group : str
        ``'shadvarga'`` | ``'saptavarga'`` | ``'dashavarga'`` |
        ``'shodashavarga'``.
    entries : tuple[VimshopakaVargaEntry, ...]
        Per-division breakdown, in ascending division order.
    total : float
        Sum of entry points; in [5, 20] by construction (a planet is at
        worst adhi shatru everywhere -> 5/20).
    """

    planet:  str
    group:   str
    entries: tuple[VimshopakaVargaEntry, ...]
    total:   float
    d60_method: D60Method | None = None

    def __post_init__(self) -> None:
        if self.d60_method is not None:
            _d60_method(self.d60_method)
            if 60 not in VIMSHOPAKA_GROUPS.get(self.group, {}):
                raise ValueError("d60_method is not applied in this group")
        if self.group not in VIMSHOPAKA_GROUPS:
            raise ValueError(
                f"VimshopakaBala.group must be one of "
                f"{sorted(VIMSHOPAKA_GROUPS)}, got {self.group!r}"
            )
        if not (0.0 <= self.total <= 20.0 + 1e-9):
            raise ValueError(
                f"VimshopakaBala.total must be in [0, 20], got {self.total}"
            )

    @property
    def d60_source_references(self) -> tuple[str, ...]:
        return _d60_source_references(self.d60_method)


def vimshopaka_bala(
    planet: str,
    sidereal_longitudes: dict[str, float],
    group: str = 'shodashavarga',
    *, d60_method: D60Method = D60Method.HARMONIC,
) -> VimshopakaBala:
    """
    Compute Vimshopaka Bala for one planet over the chosen varga group.

    Parameters
    ----------
    planet : str
        One of the seven classical planets.
    sidereal_longitudes : dict[str, float]
        Sidereal longitudes for all seven classical planets (all are needed
        because temporary friendships are computed from the D1 chart).
    group : str
        Varga group: ``'shadvarga'`` (6), ``'saptavarga'`` (7),
        ``'dashavarga'`` (10), or ``'shodashavarga'`` (16, default).

    Returns
    -------
    VimshopakaBala

    Source: BPHS Shodashavarga Adhyaya (Vimshopaka weights and vargavishwa).
    """
    from .vedic_dignities import OWN_SIGNS, planetary_relationships

    weights = VIMSHOPAKA_GROUPS.get(group)
    if weights is None:
        raise ValueError(
            f"group must be one of {sorted(VIMSHOPAKA_GROUPS)}, got {group!r}"
        )
    _d60_method(d60_method)
    if 60 not in weights and d60_method is not D60Method.HARMONIC:
        raise ValueError("nondefault d60_method requires a group containing D60")
    if planet not in sidereal_longitudes:
        raise KeyError(f"{planet!r} missing from sidereal_longitudes")

    if d60_method is not D60Method.HARMONIC:
        # All divisions and D1 relationships share the source profile's
        # normalized circular input; this does not alter their sign doctrines.
        sidereal_longitudes = {
            body: d60_sign(lon, method=d60_method).longitude
            for body, lon in sidereal_longitudes.items()
        }

    # Sign lords (classical, no nodes).
    lord_of_sign: dict[int, str] = {}
    for _p, _signs in OWN_SIGNS.items():
        for _s in _signs:
            lord_of_sign[_s] = _p

    # Compound (Panchadha Maitri) relationships from the D1 chart.
    compound: dict[str, str] = {
        rel.to_planet: rel.compound
        for rel in planetary_relationships(sidereal_longitudes)
        if rel.from_planet == planet
    }

    lon = sidereal_longitudes[planet]
    entries: list[VimshopakaVargaEntry] = []
    total = 0.0
    for division in sorted(weights):
        v_sign = varga_sign_index(lon, division, d60_method=d60_method if division == 60 else D60Method.HARMONIC)
        lord = lord_of_sign[v_sign]
        if lord == planet:
            dignity = 'own_sign'
        else:
            dignity = compound[lord]
        vishva = VARGA_VISHVA[dignity]
        weight = weights[division]
        points = weight * vishva / 20.0
        total += points
        entries.append(VimshopakaVargaEntry(
            division=division,
            varga_sign_index=v_sign,
            lord=lord,
            dignity=dignity,
            vishva=vishva,
            weight=weight,
            points=points,
        ))

    return VimshopakaBala(
        planet=planet,
        group=group,
        entries=tuple(entries),
        total=total,
        d60_method=d60_method if 60 in weights else None,
    )


def vimshopaka_all(
    sidereal_longitudes: dict[str, float],
    group: str = 'shodashavarga',
    *, d60_method: D60Method = D60Method.HARMONIC,
) -> dict[str, VimshopakaBala]:
    """Vimshopaka Bala for every planet present in *sidereal_longitudes*."""
    return {
        planet: vimshopaka_bala(planet, sidereal_longitudes, group, d60_method=d60_method)
        for planet in sidereal_longitudes
    }


# ---------------------------------------------------------------------------
# Vargottama — same sign in D1 and D9
# ---------------------------------------------------------------------------

def is_vargottama(sidereal_longitude: float) -> bool:
    """
    True when the longitude occupies the same sign in D1 and D9 (Navamsa).

    A vargottama placement strengthens the planet (classical doctrine:
    "like being in own sign").  Pure sign comparison; no orb concept.
    """
    return varga_sign_index(sidereal_longitude, 1) == varga_sign_index(
        sidereal_longitude, 9
    )


def vargottama_planets(sidereal_longitudes: dict[str, float]) -> frozenset[str]:
    """Return the set of planets in vargottama (same D1 and D9 sign)."""
    return frozenset(
        planet for planet, lon in sidereal_longitudes.items()
        if is_vargottama(lon)
    )
