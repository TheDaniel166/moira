"""
moira/huber.py -- Huber Astrological Psychology Engine

Implements the computational apparatus of the Huber method (Bruno and
Louise Huber, Astrological Psychology Institute, Adliswil):

    Age Point          the 72-year Life Clock progression through houses
    House Zones        golden-section division of each house into
                       Cardinal / Fixed / Mutable zones
    Dynamic Curve      intensity curve within each house (peak at cusp,
                       trough at Low Point)
    Planet Intensity   scoring natal planet positions against the curve

Authority
---------
    Age Point algorithm  -- Bruno & Louise Huber, *Life Clock* (API Press).
                            72-year cycle, 6 years per house, counterclockwise
                            from Ascendant, angular velocity proportional to
                            house size.
    Golden-section zones -- Bruno Huber, *Die astrologischen Hauser*
                            (*The Astrological Houses*).  Balance Point at
                            phi-complement (0.382) of house; Low Point at
                            phi (0.618) of house.
    Dynamic Curve        -- Described in *The Astrological Houses* as a
                            sinusoidal curve peaking at cusps and reaching
                            minimum at the Low Point.  The piecewise
                            half-cosine implemented here is a faithful
                            mathematical reconstruction of the published
                            shape; the explicit formula is not freely
                            available and should be verified against the
                            primary text if strict fidelity is required.
    Koch house system    -- Huber doctrine prescribes Koch houses.  The
                            implementation accepts any HouseCusps but notes
                            the doctrinal preference.

House system note
-----------------
    All functions accept any HouseCusps object.  The Huber school
    specifically mandates Koch houses; the caller is responsible for
    supplying Koch cusps when doctrinal fidelity is intended.
"""

import math
from dataclasses import dataclass
from enum import Enum

from .houses import HouseCusps


# ===========================================================================
# PUBLIC API
# ===========================================================================

__all__ = [
    # Enums
    "HouseZone",
    # Constants
    "PHI",
    "PHI_COMPLEMENT",
    "CYCLE_YEARS",
    "YEARS_PER_HOUSE",
    # Result vessels
    "HouseZoneProfile",
    "AgePointPosition",
    "DynamicIntensity",
    "PlanetIntensityScore",
    "ChartIntensityProfile",
    # Functions
    "house_zones",
    "age_point",
    "age_point_contacts",
    "dynamic_intensity",
    "intensity_at",
    "chart_intensity_profile",
]


# ===========================================================================
# CONSTANTS
# ===========================================================================

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0 - 1.0   # 0.6180339887...
"""The golden ratio fractional part (phi)."""

PHI_COMPLEMENT: float = 1.0 - PHI                    # 0.3819660113...
"""Complement of phi (1 - phi)."""

CYCLE_YEARS: float = 72.0
"""Full Age Point cycle in years."""

YEARS_PER_HOUSE: float = 6.0
"""Years the Age Point spends in each house."""


# ===========================================================================
# ENUMS
# ===========================================================================

class HouseZone(str, Enum):
    """
    Golden-section zone within a house.

    Each house is divided by the golden ratio into three developmental
    zones, following Huber's house-zone doctrine:

        CARDINAL   cusp to Balance Point (0.000 -- 0.382)
            Outward initiative, environmental engagement.
        FIXED      Balance Point to Low Point (0.382 -- 0.618)
            Consolidation, stable expression.
        MUTABLE    Low Point to next cusp (0.618 -- 1.000)
            Transition, preparation for the next house.
    """

    CARDINAL = "cardinal"
    FIXED    = "fixed"
    MUTABLE  = "mutable"


# ===========================================================================
# RESULT VESSELS
# ===========================================================================

@dataclass(frozen=True, slots=True)
class HouseZoneProfile:
    """
    Golden-section zone analysis for one house.

    Fields
    ------
    house : int
        House number (1--12).
    cusp_longitude : float
        Opening cusp longitude (degrees).
    next_cusp_longitude : float
        Next house cusp longitude (degrees).
    house_size : float
        Angular size of the house (degrees).
    balance_point_longitude : float
        Longitude of the Balance Point (cusp + 0.382 * house_size).
    low_point_longitude : float
        Longitude of the Low Point (cusp + 0.618 * house_size).
    balance_point_fraction : float
        Fraction through the house (always PHI_COMPLEMENT ~ 0.382).
    low_point_fraction : float
        Fraction through the house (always PHI ~ 0.618).
    """

    house:                    int
    cusp_longitude:           float
    next_cusp_longitude:      float
    house_size:               float
    balance_point_longitude:  float
    low_point_longitude:      float
    balance_point_fraction:   float
    low_point_fraction:       float


@dataclass(frozen=True, slots=True)
class AgePointPosition:
    """
    The Age Point at a specific age.

    Fields
    ------
    age_years : float
        Age in years from birth.
    cycle : int
        Which 72-year cycle (1 = first life, 2 = second, ...).
    house : int
        House number (1--12) the Age Point occupies.
    fraction_through_house : float
        0.0 at house cusp, 1.0 at next cusp.
    longitude : float
        Ecliptic longitude of the Age Point (degrees).
    zone : HouseZone
        Cardinal, Fixed, or Mutable zone.
    years_into_house : float
        Years elapsed since entering this house (0--6).
    intensity : float
        Dynamic Intensity Curve value at this position (0.0--1.0).
    """

    age_years:              float
    cycle:                  int
    house:                  int
    fraction_through_house: float
    longitude:              float
    zone:                   HouseZone
    years_into_house:       float
    intensity:              float


@dataclass(frozen=True, slots=True)
class DynamicIntensity:
    """
    Dynamic Intensity Curve value at a specific position within a house.

    Fields
    ------
    house : int
        House number (1--12).
    fraction : float
        Position within the house (0.0 = cusp, 1.0 = next cusp).
    intensity : float
        Curve value (0.0 at Low Point, 1.0 at cusps).
    zone : HouseZone
        Which zone this position falls in.
    """

    house:     int
    fraction:  float
    intensity: float
    zone:      HouseZone


@dataclass(frozen=True, slots=True)
class PlanetIntensityScore:
    """
    A planet's position scored against the Dynamic Intensity Curve.

    Fields
    ------
    name : str
        Planet or point name.
    longitude : float
        Ecliptic longitude (degrees).
    house : int
        House number (1--12).
    fraction : float
        Position within the house (0.0--1.0).
    intensity : float
        Dynamic Intensity Curve value (0.0--1.0).
    zone : HouseZone
        Zone within the house.
    near_cusp : bool
        True if intensity >= 0.8 (strong environmental engagement).
    near_low_point : bool
        True if intensity <= 0.2 (maximum introversion).
    """

    name:           str
    longitude:      float
    house:          int
    fraction:       float
    intensity:      float
    zone:           HouseZone
    near_cusp:      bool
    near_low_point: bool


@dataclass(frozen=True, slots=True)
class ChartIntensityProfile:
    """
    Dynamic Intensity scoring for all planets in a chart.

    Fields
    ------
    house_cusps : HouseCusps
        The house frame used.
    scores : tuple[PlanetIntensityScore, ...]
        One score per input point, preserving input order.
    high_intensity : tuple[PlanetIntensityScore, ...]
        Points with intensity >= 0.8 (near cusps).
    low_intensity : tuple[PlanetIntensityScore, ...]
        Points with intensity <= 0.2 (near Low Points).
    mean_intensity : float
        Average intensity across all scored points.
    """

    house_cusps:    HouseCusps
    scores:         tuple[PlanetIntensityScore, ...]
    high_intensity: tuple[PlanetIntensityScore, ...]
    low_intensity:  tuple[PlanetIntensityScore, ...]
    mean_intensity: float


# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

def _house_size(cusps: HouseCusps, house_index: int) -> float:
    """Angular size of house at 0-based index, handling 360 wrap."""
    c1 = cusps.cusps[house_index]
    c2 = cusps.cusps[(house_index + 1) % 12]
    size = (c2 - c1) % 360.0
    if size == 0.0:
        size = 360.0  # degenerate: shouldn't happen with real cusps
    return size


def _fraction_in_house(longitude: float, cusps: HouseCusps, house_index: int) -> float:
    """Fraction of the way through a house (0.0 at cusp, 1.0 at next cusp)."""
    c1 = cusps.cusps[house_index]
    size = _house_size(cusps, house_index)
    offset = (longitude - c1) % 360.0
    return offset / size


def _zone_of(fraction: float) -> HouseZone:
    """Classify a fraction (0--1) into a golden-section zone."""
    if fraction < PHI_COMPLEMENT:
        return HouseZone.CARDINAL
    if fraction < PHI:
        return HouseZone.FIXED
    return HouseZone.MUTABLE


def _intensity_at_fraction(fraction: float) -> float:
    """
    Dynamic Intensity Curve value at a given fraction through a house.

    Piecewise half-cosine, asymmetric around the golden-section Low Point:

        cusp to Low Point (0 <= f <= PHI):
            I(f) = (1 + cos(pi * f / PHI)) / 2

        Low Point to next cusp (PHI <= f <= 1):
            I(f) = (1 + cos(pi * (1 - f) / (1 - PHI))) / 2

    This yields:
        I(0)   = 1.0  (cusp: maximum environmental intensity)
        I(PHI) = 0.0  (Low Point: minimum intensity)
        I(1)   = 1.0  (next cusp: maximum again)

    The curve is smooth (C1-continuous) at all points and asymmetric
    because the Low Point sits at PHI (~0.618) rather than at 0.5.

    Reconstruction note
    -------------------
    This formula is a mathematical reconstruction of the curve described
    in Bruno Huber's *Die astrologischen Hauser* (The Astrological Houses).
    The published description specifies: sinusoidal shape, peak at cusps,
    minimum at the golden-section Low Point, asymmetric.  The piecewise
    half-cosine is the minimal smooth curve satisfying all constraints.
    The exact formula from the primary text has not been independently
    verified against this reconstruction.
    """
    f = max(0.0, min(1.0, fraction))

    if f <= PHI:
        # Cusp → Low Point: descending half-cosine
        return 0.5 * (1.0 + math.cos(math.pi * f / PHI))
    else:
        # Low Point → next cusp: ascending half-cosine
        return 0.5 * (1.0 + math.cos(math.pi * (1.0 - f) / (1.0 - PHI)))


# ===========================================================================
# SECTION 1 -- HOUSE ZONES
# ===========================================================================

def house_zones(house_cusps: HouseCusps) -> tuple[HouseZoneProfile, ...]:
    """
    Compute the golden-section zone boundaries for all 12 houses.

    Parameters
    ----------
    house_cusps : HouseCusps
        The house frame (Koch recommended by Huber doctrine).

    Returns
    -------
    Tuple of 12 HouseZoneProfile objects, houses 1--12.
    """
    profiles: list[HouseZoneProfile] = []
    for i in range(12):
        size = _house_size(house_cusps, i)
        cusp = house_cusps.cusps[i]
        next_cusp = house_cusps.cusps[(i + 1) % 12]
        bp_lon = (cusp + PHI_COMPLEMENT * size) % 360.0
        lp_lon = (cusp + PHI * size) % 360.0

        profiles.append(HouseZoneProfile(
            house=i + 1,
            cusp_longitude=cusp,
            next_cusp_longitude=next_cusp,
            house_size=size,
            balance_point_longitude=bp_lon,
            low_point_longitude=lp_lon,
            balance_point_fraction=PHI_COMPLEMENT,
            low_point_fraction=PHI,
        ))

    return tuple(profiles)


# ===========================================================================
# SECTION 2 -- AGE POINT
# ===========================================================================

def age_point(
    age_years: float,
    house_cusps: HouseCusps,
) -> AgePointPosition:
    """
    Compute the Age Point position for a given age.

    The Age Point begins at the Ascendant at birth and moves
    counterclockwise through the houses, spending exactly 6 years
    in each house.  Angular velocity within each house is proportional
    to house size, so the point accelerates through large houses and
    decelerates through small ones.

    Parameters
    ----------
    age_years   : age from birth in years (may be fractional, may exceed 72)
    house_cusps : house frame (Koch recommended)

    Returns
    -------
    AgePointPosition with longitude, house, zone, and intensity.

    Raises
    ------
    ValueError if age_years is negative.
    """
    if age_years < 0:
        raise ValueError(f"age must be non-negative, got {age_years}")

    cycle = int(age_years // CYCLE_YEARS) + 1
    age_in_cycle = age_years % CYCLE_YEARS

    house_index = int(age_in_cycle // YEARS_PER_HOUSE)  # 0-based
    if house_index >= 12:
        house_index = 11  # guard for age_in_cycle == 72.0 exactly
    years_into_house = age_in_cycle - house_index * YEARS_PER_HOUSE
    fraction = years_into_house / YEARS_PER_HOUSE

    size = _house_size(house_cusps, house_index)
    cusp = house_cusps.cusps[house_index]
    longitude = (cusp + fraction * size) % 360.0
    zone = _zone_of(fraction)
    intensity = _intensity_at_fraction(fraction)

    return AgePointPosition(
        age_years=age_years,
        cycle=cycle,
        house=house_index + 1,
        fraction_through_house=fraction,
        longitude=longitude,
        zone=zone,
        years_into_house=years_into_house,
        intensity=intensity,
    )


def age_point_contacts(
    house_cusps: HouseCusps,
    planet_longitudes: dict[str, float],
    orb: float = 2.0,
    start_age: float = 0.0,
    end_age: float = 72.0,
    step_years: float = 1.0 / 12.0,
) -> list[tuple[float, str, float]]:
    """
    Find approximate ages when the Age Point conjuncts natal planets.

    Scans the Age Point at regular intervals and reports when the
    separation to any natal planet falls within the orb.

    Parameters
    ----------
    house_cusps        : house frame
    planet_longitudes  : {name: longitude} of natal planets
    orb                : conjunction orb in degrees (default 2.0)
    start_age          : start of scan (years, default 0)
    end_age            : end of scan (years, default 72)
    step_years         : scan resolution (default 1 month)

    Returns
    -------
    List of (age, planet_name, separation_degrees) tuples,
    sorted by age.  Each entry represents one contact event.
    """
    contacts: list[tuple[float, str, float]] = []
    age = start_age

    while age <= end_age:
        ap = age_point(age, house_cusps)
        for name, pl_lon in planet_longitudes.items():
            sep = abs((ap.longitude - pl_lon + 180.0) % 360.0 - 180.0)
            if sep <= orb:
                contacts.append((age, name, sep))
        age += step_years

    # Deduplicate: keep the closest approach for each planet per passage.
    # A passage is a sequence of consecutive contacts with the same planet.
    if not contacts:
        return contacts

    deduped: list[tuple[float, str, float]] = []
    current_planet = contacts[0][1]
    best = contacts[0]

    for c in contacts[1:]:
        if c[1] == current_planet and c[0] - best[0] < 1.0:
            # Same passage — keep the tighter separation
            if c[2] < best[2]:
                best = c
        else:
            deduped.append(best)
            current_planet = c[1]
            best = c
    deduped.append(best)

    return sorted(deduped, key=lambda x: x[0])


# ===========================================================================
# SECTION 3 -- DYNAMIC INTENSITY CURVE
# ===========================================================================

def dynamic_intensity(
    house: int,
    fraction: float,
) -> DynamicIntensity:
    """
    Evaluate the Dynamic Intensity Curve at a specific house position.

    Parameters
    ----------
    house    : house number (1--12)
    fraction : position within the house (0.0 = cusp, 1.0 = next cusp)

    Returns
    -------
    DynamicIntensity with curve value and zone.
    """
    if house < 1 or house > 12:
        raise ValueError(f"house must be 1--12, got {house}")
    f = max(0.0, min(1.0, fraction))
    return DynamicIntensity(
        house=house,
        fraction=f,
        intensity=_intensity_at_fraction(f),
        zone=_zone_of(f),
    )


def intensity_at(
    longitude: float,
    house_cusps: HouseCusps,
) -> DynamicIntensity:
    """
    Evaluate the Dynamic Intensity Curve at an ecliptic longitude.

    Determines which house the longitude falls in, computes the
    fractional position, and returns the intensity.

    Parameters
    ----------
    longitude   : ecliptic longitude (degrees)
    house_cusps : house frame

    Returns
    -------
    DynamicIntensity
    """
    from .houses import assign_house

    placement = assign_house(longitude, house_cusps)
    house_index = placement.house - 1
    fraction = _fraction_in_house(longitude, house_cusps, house_index)

    return DynamicIntensity(
        house=placement.house,
        fraction=fraction,
        intensity=_intensity_at_fraction(fraction),
        zone=_zone_of(fraction),
    )


# ===========================================================================
# SECTION 4 -- CHART-WIDE INTENSITY PROFILE
# ===========================================================================

def chart_intensity_profile(
    points: dict[str, float],
    house_cusps: HouseCusps,
) -> ChartIntensityProfile:
    """
    Score all chart points against the Dynamic Intensity Curve.

    Parameters
    ----------
    points      : {name: longitude} for all chart bodies / points
    house_cusps : house frame (Koch recommended)

    Returns
    -------
    ChartIntensityProfile with per-planet scores, high/low intensity
    lists, and mean intensity.
    """
    scores: list[PlanetIntensityScore] = []

    for name, lon in points.items():
        di = intensity_at(lon, house_cusps)
        scores.append(PlanetIntensityScore(
            name=name,
            longitude=lon,
            house=di.house,
            fraction=di.fraction,
            intensity=di.intensity,
            zone=di.zone,
            near_cusp=(di.intensity >= 0.8),
            near_low_point=(di.intensity <= 0.2),
        ))

    scores_tuple = tuple(scores)
    high = tuple(s for s in scores_tuple if s.near_cusp)
    low = tuple(s for s in scores_tuple if s.near_low_point)
    mean = sum(s.intensity for s in scores_tuple) / len(scores_tuple) if scores_tuple else 0.0

    return ChartIntensityProfile(
        house_cusps=house_cusps,
        scores=scores_tuple,
        high_intensity=high,
        low_intensity=low,
        mean_intensity=mean,
    )
