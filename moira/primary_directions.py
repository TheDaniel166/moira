"""
Moira — primary_directions.py
The Primary Direction Engine: governs Placidus mundane primary direction
arc computation for natal charts.

Boundary: owns speculum construction, mundane fraction arithmetic, direct and
converse arc computation, and symbolic time-key conversion. Delegates ecliptic-
to-equatorial coordinate transformation to constants (DEG2RAD/RAD2DEG). Does
NOT own natal chart construction, house computation, or ephemeris state.

Public surface:
    DIRECT, CONVERSE,
    SpeculumEntry, PrimaryArc,
    speculum, find_primary_arcs

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
    - Chart and HouseCusps instances must be fully constructed before calling
      speculum() or find_primary_arcs().
"""


import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .constants import Body, DEG2RAD, RAD2DEG

__all__ = [
    "DIRECT",
    "CONVERSE",
    "SpeculumEntry",
    "PrimaryArc",
    "speculum",
    "find_primary_arcs",
]

if TYPE_CHECKING:
    from .__init__ import Chart
    from .houses import HouseCusps


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NAIBOD_RATE  = 360.0 / 365.25   # ≈ 0.985647 °/yr
_PTOLEMY_RATE = 1.0               # 1.000000 °/yr

DIRECT   = "D"
CONVERSE = "C"


# ---------------------------------------------------------------------------
# SpeculumEntry
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpeculumEntry:
    """
    RITE: The Speculum Entry Vessel

    THEOREM: Governs the storage of one row of the Placidus mundane speculum for
    a single body at a given natal chart epoch.

    RITE OF PURPOSE:
        SpeculumEntry is the authoritative data vessel for a single body's mundane
        speculum row produced by the Primary Direction Engine. It captures the body
        name, ecliptic coordinates, equatorial coordinates, hour angle, diurnal and
        nocturnal semi-arcs, hemisphere flag, and mundane fraction. Without it,
        callers would receive unstructured tuples with no field-level guarantees. It
        exists to give find_primary_arcs() a single, named, mutable record of each
        body's mundane position.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single speculum row as named, typed fields
            - Construct itself from ecliptic coordinates via the build() classmethod
            - Serve as input to find_primary_arcs() and _mundane_arcs()
        Non-responsibilities:
            - Computing primary direction arcs (delegates to find_primary_arcs)
            - Resolving body positions from ephemeris (delegates to planets)
            - Converting Julian Days (delegates to julian)
        Dependencies:
            - build() requires obliquity, ARMC, and geographic latitude
        Structural invariants:
            - dsa is in [0, 180]
            - nsa = 180 - dsa
            - f is in [-2, 2]
        Behavioral invariants:
            - All consumers treat SpeculumEntry fields as read-only after construction

    Canon: Gansten, "Primary Directions" (Wessex Astrologer, 2009); Placidus de Titis, "Primum Mobile" (1657)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.primary_directions.SpeculumEntry",
      "risk": "high",
      "api": {
        "frozen": ["name", "lon", "lat", "ra", "dec", "ha", "dsa", "nsa", "upper", "f"],
        "internal": []
      },
      "state": {"mutable": true, "owners": ["speculum"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    name:  str
    lon:   float
    lat:   float
    ra:    float
    dec:   float
    ha:    float
    dsa:   float
    nsa:   float
    upper: bool
    f:     float

    @classmethod
    def build(
        cls,
        name:      str,
        lon:       float,
        lat:       float,
        armc:      float,
        obliquity: float,
        geo_lat:   float,
    ) -> "SpeculumEntry":
        """Construct a SpeculumEntry from ecliptic (lon, lat) coordinates."""
        eps = obliquity * DEG2RAD
        phi = geo_lat   * DEG2RAD
        l   = lon       * DEG2RAD
        b   = lat       * DEG2RAD

        # Ecliptic → equatorial
        sin_dec = math.sin(b) * math.cos(eps) + math.cos(b) * math.sin(eps) * math.sin(l)
        sin_dec = max(-1.0, min(1.0, sin_dec))
        dec_r   = math.asin(sin_dec)

        y  = math.sin(l) * math.cos(eps) - math.tan(b) * math.sin(eps)
        ra = math.degrees(math.atan2(y, math.cos(l))) % 360.0
        dec = math.degrees(dec_r)

        # Hour angle: negative = east of meridian, positive = west
        ha = (armc - ra + 180.0) % 360.0 - 180.0

        # Semi-arcs
        arg = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec_r)))
        dsa = math.degrees(math.acos(arg))  # 0° (never rises) – 180° (circumpolar)
        nsa = 180.0 - dsa

        upper = abs(ha) <= dsa + 1e-9

        # Mundane fraction f
        if upper:
            f = ha / dsa if dsa > 1e-9 else 0.0
        elif ha > 0:  # lower west: ha ∈ (dsa, 180)
            f =  1.0 + (ha  - dsa) / nsa if nsa > 1e-9 else  1.0
        else:         # lower east: ha ∈ (-180, -dsa)
            f = -1.0 - (-ha - dsa) / nsa if nsa > 1e-9 else -1.0

        return cls(
            name=name, lon=lon, lat=lat, ra=ra, dec=dec,
            ha=ha, dsa=dsa, nsa=nsa, upper=upper, f=f,
        )

    def __repr__(self) -> str:
        hem = "UH" if self.upper else "LH"
        return (
            f"Speculum({self.name:<12} "
            f"lon={self.lon:7.3f}° RA={self.ra:7.3f}° Dec={self.dec:+7.3f}° "
            f"HA={self.ha:+8.3f}° DSA={self.dsa:6.3f}° "
            f"f={self.f:+6.3f} {hem})"
        )


# ---------------------------------------------------------------------------
# PrimaryArc
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PrimaryArc:
    """
    RITE: The Primary Arc Vessel

    THEOREM: Governs the storage of a single primary direction arc between a
    promissor and a significator, with symbolic time-key conversion.

    RITE OF PURPOSE:
        PrimaryArc is the authoritative data vessel for a single primary direction
        arc produced by the Primary Direction Engine. It captures the significator
        name, promissor name, equatorial arc in degrees, direction type (direct or
        converse), and natal solar rate for the "solar" time key. Without it,
        callers would receive unstructured tuples with no field-level guarantees. It
        exists to give every higher-level consumer a single, named, mutable record
        of each primary direction arc and its symbolic year conversion.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single primary direction arc as named, typed fields
            - Convert arc to years of life via the years() method using ptolemy,
              naibod, or solar time keys
            - Serve as the return type of find_primary_arcs()
        Non-responsibilities:
            - Computing arcs (delegates to find_primary_arcs / _mundane_arcs)
            - Building the speculum (delegates to speculum())
        Dependencies:
            - Populated by find_primary_arcs()
            - solar_rate defaults to the Naibod rate if not supplied
        Structural invariants:
            - arc is always positive (forward arc only)
            - direction is DIRECT ("D") or CONVERSE ("C")
        Behavioral invariants:
            - years() is a pure function of arc and the chosen key

    Canon: Gansten, "Primary Directions" (Wessex Astrologer, 2009); Morin de Villefranche, "Astrologia Gallica" (1661)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.primary_directions.PrimaryArc",
      "risk": "high",
      "api": {
        "frozen": ["significator", "promissor", "arc", "direction", "solar_rate"],
        "internal": ["years"]
      },
      "state": {"mutable": true, "owners": ["find_primary_arcs"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    significator: str
    promissor:    str
    arc:          float
    direction:    str
    solar_rate:   float = field(default=_NAIBOD_RATE)

    def years(self, key: str = "naibod") -> float:
        """
        Convert arc to years of life via a symbolic time key.

        Parameters
        ----------
        key : "ptolemy" (1°/yr), "naibod" (0.9856°/yr), or "solar"
              For "solar", uses natal Sun speed in °/day as the yearly rate.
        """
        rate = {
            "ptolemy": _PTOLEMY_RATE,
            "naibod":  _NAIBOD_RATE,
            "solar":   self.solar_rate,
        }.get(key.lower(), _NAIBOD_RATE)
        return self.arc / rate if rate else float("inf")

    def __repr__(self) -> str:
        return (
            f"PrimaryArc({self.significator} <- {self.promissor}  "
            f"arc={self.arc:.4f}  {self.direction}  "
            f"{self.years():.2f} yr [Naibod])"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _required_ha(f: float, dsa: float, nsa: float) -> float:
    """
    Required hour angle for a body with (dsa, nsa) to occupy mundane position f.

    Parameters
    ----------
    f   : mundane fraction of the SIGNIFICATOR
    dsa : diurnal semi-arc of the PROMISSOR
    nsa : nocturnal semi-arc of the PROMISSOR

    Returns
    -------
    Required HA of the promissor (degrees, signed).
    """
    if abs(f) <= 1.0:     # target is in upper hemisphere
        return f * dsa
    elif f > 1.0:         # target is in lower west
        return dsa + (f - 1.0) * nsa
    else:                 # target is in lower east (f < -1)
        return -dsa - (-f - 1.0) * nsa


def _mundane_arcs(
    sig:  SpeculumEntry,
    prom: SpeculumEntry,
) -> tuple[float, float]:
    """
    Compute raw (direct_arc, converse_arc) in degrees.

    direct   > 0 : ARMC must advance by this amount  → future direct event
    converse > 0 : ARMC must retreat by this amount   → future converse event

    Use `% 360.0` on each to normalise to [0, 360).
    """
    req_ha   = _required_ha(sig.f, prom.dsa, prom.nsa)
    direct   =  req_ha - prom.ha
    converse = -direct
    return direct, converse


# ---------------------------------------------------------------------------
# Public: speculum
# ---------------------------------------------------------------------------

def speculum(
    chart:     "Chart",
    houses:    "HouseCusps",
    geo_lat:   float,
    obliquity: float | None = None,
    bodies:    list[str] | None = None,
) -> list[SpeculumEntry]:
    """
    Compute the Placidus mundane speculum for a natal chart.

    Parameters
    ----------
    chart      : natal Chart instance
    houses     : natal HouseCusps (provides ARMC)
    geo_lat    : geographic latitude in degrees (north positive)
    obliquity  : override true obliquity; defaults to chart.obliquity
    bodies     : planet names to include (default = all in chart.planets)

    Returns
    -------
    List of SpeculumEntry: planets + nodes + ASC/MC/DSC/IC.
    """
    obl  = obliquity if obliquity is not None else chart.obliquity
    armc = houses.armc

    entries: list[SpeculumEntry] = []

    # Planets
    planet_names = bodies if bodies is not None else list(chart.planets.keys())
    for name in planet_names:
        if name in chart.planets:
            p = chart.planets[name]
            entries.append(
                SpeculumEntry.build(name, p.longitude, p.latitude, armc, obl, geo_lat)
            )

    # Lunar nodes (ecliptic lat = 0 for mean node / Lilith)
    for name, nd in chart.nodes.items():
        entries.append(
            SpeculumEntry.build(name, nd.longitude, 0.0, armc, obl, geo_lat)
        )

    # Angles (ecliptic lat = 0 by definition — they are ecliptic points)
    for ang_name, ang_lon in [
        ("ASC", houses.asc),
        ("MC",  houses.mc),
        ("DSC", houses.dsc),
        ("IC",  houses.ic),
    ]:
        entries.append(
            SpeculumEntry.build(ang_name, ang_lon, 0.0, armc, obl, geo_lat)
        )

    return entries


# ---------------------------------------------------------------------------
# Public: find_primary_arcs
# ---------------------------------------------------------------------------

def find_primary_arcs(
    chart:            "Chart",
    houses:           "HouseCusps",
    geo_lat:          float,
    max_arc:          float = 90.0,
    include_converse: bool  = True,
    significators:    list[str] | None = None,
    promissors:       list[str] | None = None,
    solar_speed:      float | None = None,
    obliquity:        float | None = None,
) -> list[PrimaryArc]:
    """
    Find all Placidus mundane primary direction arcs up to *max_arc* degrees.

    Parameters
    ----------
    chart             : natal Chart instance
    houses            : natal HouseCusps (Placidus recommended for consistency)
    geo_lat           : geographic latitude (degrees, north positive)
    max_arc           : maximum arc in degrees; default 90 ≈ 90 years of life
    include_converse  : include converse directions (default True)
    significators     : body names for the fixed points; default = all in speculum
    promissors        : body names for the moving points; default = all in speculum
    solar_speed       : natal Sun speed in °/day (for key="solar");
                        if None, reads from chart; if unavailable uses Naibod rate
    obliquity         : override true obliquity; defaults to chart.obliquity

    Returns
    -------
    List of PrimaryArc, sorted by arc (ascending).
    """
    obl  = obliquity if obliquity is not None else chart.obliquity
    armc = houses.armc  # noqa: F841 (used implicitly via speculum())

    # Natal solar rate for "solar" key
    if solar_speed is not None:
        s_rate = abs(solar_speed)
    else:
        sun = chart.planets.get(Body.SUN)
        s_rate = abs(sun.speed) if sun else _NAIBOD_RATE

    # Build speculum
    spec    = speculum(chart, houses, geo_lat, obliquity=obl)
    sp_map  = {e.name: e for e in spec}

    all_names = list(sp_map.keys())
    sig_set   = set(significators) if significators is not None else set(all_names)
    prom_set  = set(promissors)    if promissors   is not None else set(all_names)

    results: list[PrimaryArc] = []

    for sig_e in spec:
        if sig_e.name not in sig_set:
            continue

        for prom_e in spec:
            if prom_e.name not in prom_set:
                continue
            if sig_e.name == prom_e.name:
                continue

            raw_dir, raw_conv = _mundane_arcs(sig_e, prom_e)

            # Normalise to [0, 360) — forward arc only
            arc_dir  = raw_dir  % 360.0
            arc_conv = raw_conv % 360.0

            if 0.0 < arc_dir <= max_arc:
                results.append(PrimaryArc(
                    significator=sig_e.name,
                    promissor=prom_e.name,
                    arc=arc_dir,
                    direction=DIRECT,
                    solar_rate=s_rate,
                ))

            if include_converse and 0.0 < arc_conv <= max_arc:
                results.append(PrimaryArc(
                    significator=sig_e.name,
                    promissor=prom_e.name,
                    arc=arc_conv,
                    direction=CONVERSE,
                    solar_rate=s_rate,
                ))

    results.sort(key=lambda a: a.arc)
    return results
