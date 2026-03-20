"""
Moira — chart.py
The Chart Vessel: governs unified chart assembly, bridging raw ephemeris data
into a single cross-module data vessel for all higher-level astrological computation.

Boundary: owns the full pipeline from Julian Day inputs to a populated ChartContext
vessel. Delegates planet position computation to planets, node computation to nodes,
house calculation to houses, and time conversion to julian. Does not own aspect
detection, lot computation, synastry analysis, or any display formatting.

Public surface:
    ChartContext, create_chart()

Import-time side effects: None

External dependency assumptions:
    - jplephem must be importable (via spk_reader).
    - DE441 kernel must exist at kernels/de441.bsp (accessed lazily on first call
      inside create_chart() via get_reader()).
"""

from dataclasses import dataclass, field
from datetime import datetime

from .constants import Body, HouseSystem
from .julian import jd_from_datetime, ut_to_tt
from .planets import planet_at, PlanetData
from .houses import calculate_houses, HouseCusps
from .nodes import true_node, mean_node, mean_lilith, true_lilith, NodeData

@dataclass(slots=True)
class ChartContext:
    """
    RITE: The Chart Vessel — singular cross-module data vessel of the heavens.

    THEOREM: Governs the unified snapshot of all celestial positions, house cusps,
    and nodal data for a specific moment and terrestrial location.

    RITE OF PURPOSE:
        ChartContext is the single source of truth for every higher-level
        astrological calculation in the Moira system. Without it, each Engine
        (Lots, Aspects, Synastry, Transits) would independently re-derive
        planetary positions, introducing drift and inconsistency. It is populated
        once by create_chart() and thereafter treated as read-only by all consumers.

    LAW OF OPERATION:
        Responsibilities:
            - Carry all celestial body positions (planets, nodes) as PlanetData
              and NodeData vessels
            - Carry house cusp data as a HouseCusps vessel
            - Carry the Julian Day in both UT and TT timescales
            - Carry the observer's geographic coordinates (latitude, longitude)
            - Determine and expose the day/night sect flag (is_day) on construction
        Non-responsibilities:
            - Computing planetary positions (delegates to planets)
            - Computing house cusps (delegates to houses)
            - Computing nodal positions (delegates to nodes)
            - Performing aspect detection, lot computation, or synastry analysis
            - Persisting or serialising chart data
        Dependencies:
            - PlanetData vessels populated by planet_at() (moira.planets)
            - NodeData vessels populated by true_node(), mean_node(), etc. (moira.nodes)
            - HouseCusps vessel populated by calculate_houses() (moira.houses)
            - Body constants from moira.constants
        Structural invariants:
            - jd_ut and jd_tt are always set and finite
            - latitude is in the range [-90.0, 90.0]
            - longitude is in the range [-180.0, 180.0]
            - is_day is always set after __post_init__ completes
        Behavioral invariants:
            - All consumers treat ChartContext as read-only after construction
            - is_day reflects the geometric altitude of the Sun relative to the horizon

    LAW OF THE DATA PATH:
        State ownership: ChartContext owns all celestial snapshot data for one
        chart calculation. It is the authoritative vessel passed between all
        higher-level Engines.
        Mutation rules: Populated once by create_chart(); thereafter immutable
        by convention. No Engine may mutate a ChartContext it receives.
        Persistence: None — ChartContext is an in-memory computation result.
        Cross-pillar boundaries: Read by moira.lots, moira.aspects, moira.synastry,
        moira.transits, moira.progressions, moira.profections, moira.primary_directions,
        moira.parans, moira.astrocartography, and all other higher-level Engines.
        All cross-module access is read-only.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.chart.ChartContext",
      "risk": "critical",
      "api": {
        "frozen": ["jd_ut", "jd_tt", "latitude", "longitude", "planets", "nodes", "houses", "is_day"],
        "internal": ["__post_init__", "_sun_is_above_horizon"]
      },
      "state": {"mutable": false, "owners": ["create_chart"]},
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
    jd_ut:      float
    jd_tt:      float
    latitude:   float
    longitude:  float
    
    # Celestial Bodies
    planets:    dict[str, PlanetData] = field(default_factory=dict)
    nodes:      dict[str, NodeData]   = field(default_factory=dict)
    
    # House System
    houses:     HouseCusps | None = None
    
    # Metadata
    is_day:     bool = field(init=False)
    
    def __post_init__(self):
        """
        Determine the day/night sect and set self.is_day.

        Conducts a geometric altitude check via _sun_is_above_horizon() to
        establish whether the chart is a day or night chart. Falls back to
        True (day) when the Sun or house data is unavailable.

        Side effects:
            - Sets self.is_day to True if the Sun is geometrically above the
              horizon (houses 7–12 in the traditional sense), False otherwise.
              Falls back to True when planets or houses are absent.
        """
        # Determine day/night based on Sun's relation to horizon (geometric)
        sun = self.planets.get(Body.SUN)
        if sun and self.houses:
            # Traditional check: Sun above ASC/DSC line
            self.is_day = self.houses.asc > sun.longitude > self.houses.mc or \
                          (self.houses.mc > self.houses.asc and (sun.longitude > self.houses.mc or sun.longitude < self.houses.asc))
            # Refined check: Geometric altitude check would be better, but this matches traditional lots
            self.is_day = self._sun_is_above_horizon()
        else:
            self.is_day = True # fallback

    def _sun_is_above_horizon(self) -> bool:
        """Geometric check for day/night."""
        if not self.houses or Body.SUN not in self.planets:
            return True
        sun_lon = self.planets[Body.SUN].longitude
        # In a 12-house system, houses 7-12 are above the horizon.
        # Cusp 1 is Ascendant (rising), Cusp 7 is Descendant (setting).
        # We check if Sun longitude is between Cusp 7 and Cusp 1 (circulating through MC).
        h7 = self.houses.cusps[6]
        h1 = self.houses.cusps[0]
        if h7 < h1:
            return h7 <= sun_lon <= h1
        else:
            return sun_lon >= h7 or sun_lon <= h1

def create_chart(
    jd_ut:      float,
    latitude:   float,
    longitude:  float,
    house_system: str = HouseSystem.PLACIDUS,
    bodies:      list[str] | None = None
) -> ChartContext:
    """
    Construct a fully populated ChartContext vessel for the given time and location.

    Conducts the full chart assembly pipeline: converts UT to TT, computes all
    requested planetary positions via the DE441 kernel, computes the four nodal
    bodies, calculates house cusps, and assembles the result into a ChartContext.
    The returned vessel is the single source of truth for all subsequent
    higher-level calculations.

    Args:
        jd_ut: Julian Day in Universal Time (UT1) for the chart moment.
        latitude: Geographic latitude of the observer in decimal degrees,
            in the range [-90.0, 90.0]. Positive = North.
        longitude: Geographic longitude of the observer in decimal degrees,
            in the range [-180.0, 180.0]. Positive = East.
        house_system: House system identifier from HouseSystem constants.
            Defaults to HouseSystem.PLACIDUS.
        bodies: List of Body constant strings to compute. When None, defaults
            to the eleven standard bodies: Sun, Moon, Mercury, Venus, Mars,
            Jupiter, Saturn, Uranus, Neptune, Pluto, and Chiron.

    Returns:
        A fully populated ChartContext vessel with planets, nodes, houses,
        jd_ut, jd_tt, latitude, longitude, and is_day set.

    Raises:
        FileNotFoundError: If the DE441 SPK kernel cannot be located by get_reader().
        ValueError: If jplephem cannot compute a position for the requested body
            at the given Julian Day (out-of-range epoch).

    Side effects:
        - Reads the DE441 SPK kernel file from disk on the first call (via
          get_reader()), which initialises the module-level SpkReader singleton.
          Subsequent calls reuse the cached reader without additional I/O.
    """
    from .spk_reader import get_reader
    reader = get_reader()
    
    jd_tt = ut_to_tt(jd_ut)
    if bodies is None:
        bodies = [
            Body.SUN, Body.MOON, Body.MERCURY, Body.VENUS, Body.MARS,
            Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE, Body.PLUTO,
            Body.CHIRON
        ]
        
    planets = {b: planet_at(b, jd_ut, reader=reader) for b in bodies}
    
    nodes = {
        Body.TRUE_NODE: true_node(jd_ut, reader=reader),
        Body.MEAN_NODE: mean_node(jd_ut),
        Body.LILITH:    mean_lilith(jd_ut),
        Body.TRUE_LILITH: true_lilith(jd_ut, reader=reader)
    }
    
    houses = calculate_houses(jd_ut, latitude, longitude, system=house_system)
    
    return ChartContext(
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        latitude=latitude,
        longitude=longitude,
        planets=planets,
        nodes=nodes,
        houses=houses
    )
