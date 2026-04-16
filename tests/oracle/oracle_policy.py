"""
Oracle Validation Policy — Moira Swiss-Lineage Remediation Campaign

This module defines the tolerance matrices, test cases, and oracle comparison
methodology for validating the 12 rewritten-pending-oracle functions against
independent external authorities (JPL Horizons, SOFA, NASA Ephemeris).

Authority ranking for oracle comparisons:
  1. JPL HORIZONS API (primary ephemeris authority; ICRF, light-time corrected)
  2. SOFA/ERFA (reference implementations for coordinate transforms)
  3. NASA Ephemeris (eclipse/event data; secondary validation)
  4. Internal cross-checks (consistency within Moira's own stack)

Tolerance policy:
  - All tolerances are 3-sigma budgets (i.e., rare events are OK).
  - Positions: arcseconds (angular) or km (distance).
  - Times: seconds (absolute) or milliseconds (relative phase crossing).
  - Magnitudes: 0.01 mag (photometric scatter).
  - Rates: arcsec/day (angular velocity); km/day (linear velocity).

Test-case matrix strategy:
  - Historical epochs (pre-2000, post-2000) to cover secular terms.
  - Edge cases (perihelion, aphelion, node crossing, ecliptic alignment).
  - Geocentric, heliocentric, and topocentric positions where relevant.
"""

import math
from dataclasses import dataclass
from typing import NamedTuple

# ============================================================================
# TOLERANCE MATRICES (3-sigma budgets)
# ============================================================================

@dataclass
class PositionTolerance:
    """Angular and distance position tolerance."""
    arcsec: float         # Angular separation (arcseconds)
    km: float             # Distance tolerance (km)
    
    def check_angular(self, diff_arcsec: float) -> bool:
        return abs(diff_arcsec) <= self.arcsec
    
    def check_distance(self, diff_km: float) -> bool:
        return abs(diff_km) <= self.km


@dataclass
class TimeTolerance:
    """Event time tolerance."""
    seconds: float        # Absolute time tolerance (seconds)
    
    def check(self, diff_sec: float) -> bool:
        return abs(diff_sec) <= self.seconds


@dataclass
class SpeedTolerance:
    """Angular and linear speed tolerance."""
    arcsec_per_day: float  # Angular rate (arcsec/day)
    km_per_day: float      # Linear rate (km/day)
    
    def check_angular(self, diff_arcsec_per_day: float) -> bool:
        return abs(diff_arcsec_per_day) <= self.arcsec_per_day
    
    def check_linear(self, diff_km_per_day: float) -> bool:
        return abs(diff_km_per_day) <= self.km_per_day


# ============================================================================
# TOLERANCE MATRICES PER FUNCTION
# ============================================================================

# coordinates.py tranch
HORIZONTAL_TO_EQUATORIAL_POSITION = PositionTolerance(
    arcsec=0.1,    # 0.1 arcsec: accurate to naked-eye precision
    km=1.0,        # N/A for topocentric transform
)

COTRANS_SP_POSITION = PositionTolerance(
    arcsec=0.05,   # 0.05 arcsec: ~parsec-level at 1 AU
    km=0.01,       # Sub-km ecliptic-equatorial fidelity
)

ATMOSPHERIC_REFRACTION_ALTITUDE = 30.0  # arcseconds (Bennett 1982 formula accuracy)

ATMOSPHERIC_REFRACTION_EXTENDED_ALTITUDE = 60.0  # arcseconds (humidity+wavelength spread)

EQUATION_OF_TIME = 60.0  # seconds (Meeus low-precision formula spread)

# nodes.py tranche
NEXT_MOON_NODE_CROSSING_TIME = TimeTolerance(
    seconds=1.0,   # 1 second: sub-Saros precision
)

NODES_AND_APSIDES_AT_LONGITUDE = PositionTolerance(
    arcsec=10.0,   # 10 arcsec: practical ecliptic accuracy
    km=1.0,        # N/A
)

# eclipse.py tranche
NEXT_SOLAR_ECLIPSE_AT_LOCATION_TIME = TimeTolerance(
    seconds=5.0,   # 5 seconds: visibility window tolerance
)

NEXT_SOLAR_ECLIPSE_AT_LOCATION_SEPARATION = PositionTolerance(
    arcsec=30.0,   # 30 arcsec: topocentric Sun-Moon separation at local max
    km=1.0,        # N/A
)

# planets.py tranche
PLANET_RELATIVE_TO_POSITION = PositionTolerance(
    arcsec=0.05,   # 0.05 arcsec: ICRF-to-ecliptic transform fidelity
    km=1.0,        # Relative position uncertainty (depends on distance)
)

PLANET_RELATIVE_TO_SPEED = SpeedTolerance(
    arcsec_per_day=0.1,  # 0.1 arcsec/day: finite-difference noise floor
    km_per_day=0.1,      # N/A
)

NEXT_HELIOCENTRIC_TRANSIT_TIME = TimeTolerance(
    seconds=1.0,   # 1 second: crossing refinement tolerance
)

# phenomena.py tranche
PLANET_PHENOMENA_PHASE_ANGLE = 0.01  # degrees (3-degree typical spread per source)

PLANET_PHENOMENA_ILLUMINATION = 0.001  # fraction (0.1% spread)

PLANET_PHENOMENA_ELONGATION = 0.1  # degrees (topocentric vs geocentric spread)

PLANET_PHENOMENA_ANGULAR_DIAMETER = 0.01  # arcseconds (physical radius uncertainty)

PLANET_PHENOMENA_MAGNITUDE = 0.01  # magnitude units (photometric model scatter)


# ============================================================================
# TEST-CASE MATRICES
# ============================================================================

class TestEpoch(NamedTuple):
    """A single test epoch with context."""
    jd_ut: float
    label: str
    body: str = "Moon"
    reason: str = ""


# Coordinates tranche: common epochs
COORDINATE_TEST_EPOCHS = [
    TestEpoch(2400000.5, "J2000 epoch J2000.0", reason="IAU reference epoch"),
    TestEpoch(2440000.5, "Early epoch (1968-05-23)", reason="Pre-modern era"),
    TestEpoch(2451545.0, "Standard J2000.0", reason="Canonical reference"),
    TestEpoch(2460000.5, "Recent epoch (2023-11-15)", reason="Modern secular terms"),
    TestEpoch(2465442.5, "Far future (2040-01-01)", reason="Extrapolation test"),
]

# Nodes tranche: lunar node crossing epochs
# (Historical node crossing dates from Meeus)
NODES_TEST_EPOCHS = [
    TestEpoch(2451545.0, "Node crossing example 1", "Moon", "Ascending node"),
    TestEpoch(2451560.0, "Node crossing example 2", "Moon", "Descending node"),
    TestEpoch(2460000.0, "Recent node epoch", "Moon", "Modern secular"),
]

# Eclipse tranche: solar eclipse maxima (historical)
ECLIPSE_TEST_EPOCHS = [
    TestEpoch(2451711.414, "Total Solar Eclipse 1999-08-11", reason="Iconic modern eclipse"),
    TestEpoch(2460151.646, "Annular Solar Eclipse 2023-10-14", reason="Recent eclipse"),
]

# Planets tranche: planetary positions at various epochs
PLANET_TEST_EPOCHS = [
    TestEpoch(2451545.0, "Mars at J2000", "Mars", "Reference epoch"),
    TestEpoch(2451545.0, "Venus at J2000", "Venus", "Inner planet"),
    TestEpoch(2451545.0, "Jupiter at J2000", "Jupiter", "Outer planet"),
    TestEpoch(2460000.0, "Saturn recent", "Saturn", "Modern epoch"),
]

# Phenomena tranche: planetary phenomena epochs
PHENOMENA_TEST_EPOCHS = [
    TestEpoch(2451545.0, "Venus phenomenon J2000", "Venus", "Inner planet phase"),
    TestEpoch(2460000.0, "Mars phenomenon recent", "Mars", "Outer planet phase"),
    TestEpoch(2459580.0, "Mercury phenomenon 2022", "Mercury", "Superior planet"),
]


# ============================================================================
# ORACLE COMPARISON CONFIGURATION
# ============================================================================

HORIZONS_API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
HORIZONS_TIMEOUT_SEC = 30

# SOFA library path (optional; used if available)
SOFA_REF_AVAILABILITY = "sofa_c" # or None if unavailable


# ============================================================================
# VALIDATION RESULT VESSEL
# ============================================================================

class ValidationResult(NamedTuple):
    """Result of a single oracle comparison."""
    function_name: str
    epoch: TestEpoch
    quantity: str               # e.g., "position_arcsec", "time_seconds"
    moira_value: float
    oracle_value: float
    diff: float
    tolerance: float
    passed: bool
    error_msg: str = ""


def format_result(result: ValidationResult) -> str:
    """Human-readable validation result."""
    status = "✓ PASS" if result.passed else "✗ FAIL"
    return (
        f"{status} | {result.function_name} | {result.epoch.label} | "
        f"{result.quantity} | Δ={result.diff:.6f} (tol={result.tolerance:.6f})"
    )
