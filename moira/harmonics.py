"""
Harmonic Engine — moira/harmonics.py

Archetype: Engine
Purpose: Computes harmonic chart positions by multiplying natal ecliptic
         longitudes by a harmonic number and reducing modulo 360°, with
         a preset catalogue of astrologically named harmonics.

Boundary declaration:
    Owns: the harmonic formula (lon × H mod 360°), the HARMONIC_PRESETS
          catalogue, and the HarmonicPosition and HarmonicsService types.
    Delegates: sign derivation to moira.constants.sign_of.

Import-time side effects: None

External dependency assumptions:
    - moira.constants.sign_of(longitude) returns (sign_name, symbol, degree).

Public surface / exports:
    HarmonicPosition      — result dataclass for one body's harmonic position
    HarmonicsService      — service class for computing harmonic charts
    HARMONIC_PRESETS      — dict of harmonic number → (name, description)
    calculate_harmonic()  — module-level convenience wrapper
"""

from dataclasses import dataclass, field

from .constants import sign_of

__all__ = [
    "HarmonicPosition",
    "HarmonicsService",
    "HARMONIC_PRESETS",
    "calculate_harmonic",
]

# ---------------------------------------------------------------------------
# Preset harmonics with astrological meanings
# ---------------------------------------------------------------------------

HARMONIC_PRESETS: dict[int, tuple[str, str]] = {
    1:  ("Natal",        "Base chart — no transformation"),
    2:  ("Opposition",   "Polarity, opposition, awareness"),
    3:  ("Trine",        "Ease, flow, integration"),
    4:  ("Square",       "Tension, challenges, action"),
    5:  ("Quintile",     "Creativity, talent, gifts"),
    7:  ("Septile",      "Destiny, fate, karma"),
    8:  ("Octile",       "Stress, power, material"),
    9:  ("Novile",       "Spiritual gifts, gestation"),
    11: ("Undecile",     "Rhythm, pattern, timing"),
    12: ("Semi-sextile", "Integration, adjustment"),
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class HarmonicPosition:
    """
    RITE: The Resonant Echo — a planet's natal longitude transformed into
          the frequency of a chosen harmonic, revealing hidden patterns
          that are invisible on the natal wheel.

    THEOREM: Immutable record of a single body's harmonic chart position,
             storing the natal longitude, the harmonic number, the computed
             harmonic longitude, and the derived sign/degree fields.

    RITE OF PURPOSE:
        HarmonicPosition is the result vessel of HarmonicsService.  It
        pairs the natal longitude with its harmonic transformation so that
        callers can compare both values and read the sign position of the
        harmonic point without performing the multiplication themselves.
        Without this vessel, harmonic results would be bare floats with no
        association to the originating planet or harmonic number.

    LAW OF OPERATION:
        Responsibilities:
            - Store planet, natal_longitude, harmonic_longitude, and harmonic.
            - Derive sign, sign_symbol, and sign_degree via __post_init__.
            - Render a compact repr showing both natal and harmonic positions.
        Non-responsibilities:
            - Does not compute the harmonic; that is HarmonicsService's role.
            - Does not validate that harmonic >= 1.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.constants.sign_of for sign derivation.
        Structural invariants:
            - harmonic_longitude == (natal_longitude * harmonic) % 360.
            - sign, sign_symbol, sign_degree are consistent with
              harmonic_longitude.

    Canon: John Addey, Harmonics in Astrology (1976)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.harmonics.HarmonicPosition",
        "risk": "low",
        "api": {"frozen": ["planet", "natal_longitude", "harmonic_longitude", "harmonic"], "internal": ["sign", "sign_symbol", "sign_degree"]},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    planet:              str
    natal_longitude:     float
    harmonic_longitude:  float
    harmonic:            int
    sign:                str   = field(init=False)
    sign_symbol:         str   = field(init=False)
    sign_degree:         float = field(init=False)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.harmonic_longitude)

    def __repr__(self) -> str:
        return (f"H{self.harmonic} {self.planet:<10}: "
                f"natal={self.natal_longitude:>8.4f}  "
                f"H{self.harmonic}={self.harmonic_longitude:>8.4f}  "
                f"{self.sign} {self.sign_degree:.2f}")


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class HarmonicsService:
    """
    RITE: The Frequency Tuner — the Engine that multiplies every natal
          longitude by the chosen harmonic number and returns the full
          transformed chart.

    THEOREM: Governs the computation of harmonic chart positions for all
             supplied bodies by applying the formula (lon × H) mod 360°
             and returning a sorted list of HarmonicPosition records.

    RITE OF PURPOSE:
        HarmonicsService is the computational core of the Harmonic Engine.
        It accepts a dict of natal longitudes and a harmonic number, applies
        the transformation uniformly, and returns results sorted by harmonic
        longitude for easy pattern inspection.  Without this Engine, the
        harmonic formula would need to be re-implemented at every call site.

    LAW OF OPERATION:
        Responsibilities:
            - Accept planet_longitudes dict and harmonic integer.
            - Clamp harmonic to >= 1.
            - Compute (lon × H) mod 360° for every body.
            - Return a list of HarmonicPosition sorted by harmonic_longitude.
            - Provide get_preset_info() for harmonic name/description lookup.
        Non-responsibilities:
            - Does not validate that planet names are known bodies.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.constants.sign_of for sign derivation in HarmonicPosition.
        Failure behavior:
            - Non-numeric longitude values will raise ValueError at float
              conversion; callers are responsible for clean input.

    Canon: John Addey, Harmonics in Astrology (1976)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.harmonics.HarmonicsService",
        "risk": "low",
        "api": {"frozen": ["calculate_harmonic", "get_preset_info"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "raise"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    @staticmethod
    def calculate_harmonic(
        planet_longitudes: dict[str, float],
        harmonic: int,
    ) -> list[HarmonicPosition]:
        """
        Calculate harmonic positions for all bodies.

        Parameters
        ----------
        planet_longitudes : dict of body name → natal longitude (degrees)
        harmonic          : harmonic number (1 = natal, 4 = square harmonic, etc.)

        Returns
        -------
        List of HarmonicPosition sorted by harmonic longitude
        """
        harmonic = max(1, int(harmonic))
        results = [
            HarmonicPosition(
                planet=name.strip().title(),
                natal_longitude=lon,
                harmonic_longitude=(lon * harmonic) % 360.0,
                harmonic=harmonic,
            )
            for name, lon in planet_longitudes.items()
        ]
        results.sort(key=lambda p: p.harmonic_longitude)
        return results

    @staticmethod
    def get_preset_info(harmonic: int) -> tuple[str, str]:
        """Return (name, description) for a harmonic number."""
        return HARMONIC_PRESETS.get(harmonic, (f"H{harmonic}", "Custom harmonic"))


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_service = HarmonicsService()


def calculate_harmonic(
    planet_longitudes: dict[str, float],
    harmonic: int,
) -> list[HarmonicPosition]:
    """
    Compute harmonic chart positions.

    Parameters
    ----------
    planet_longitudes : dict of body name → longitude (degrees)
    harmonic          : harmonic number
    """
    return _service.calculate_harmonic(planet_longitudes, harmonic)
