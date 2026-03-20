from __future__ import annotations

from dataclasses import dataclass

from moira.constants import Body


@dataclass(frozen=True)
class PositionCase:
    label: str
    command: str
    jd_ut: float
    lon_tolerance_arcmin: float
    lat_tolerance_arcmin: float


@dataclass(frozen=True)
class VectorCase:
    label: str
    command: str
    jd_ut: float
    tolerance_arcsec: float


@dataclass(frozen=True)
class SkyCase:
    label: str
    command: str
    jd_ut: float
    latitude_deg: float
    longitude_deg: float
    elevation_km: float
    ra_tolerance_arcsec: float
    dec_tolerance_arcsec: float
    az_tolerance_arcsec: float
    alt_tolerance_arcsec: float


STRICT_POSITION_PLANET_CASES: dict[str, list[PositionCase]] = {
    Body.SUN: [
        PositionCase("1960-01-01", "10", 2436934.5, 0.10, 0.50),
        PositionCase("2000-01-01", "10", 2451545.0, 0.10, 0.50),
        PositionCase("2024-01-01", "10", 2460310.5, 0.10, 0.50),
    ],
    Body.MOON: [
        PositionCase("1960-01-01", "301", 2436934.5, 0.15, 0.50),
        PositionCase("2000-01-01", "301", 2451545.0, 0.15, 0.50),
        PositionCase("2024-01-01", "301", 2460310.5, 0.15, 0.50),
    ],
    Body.MERCURY: [
        PositionCase("2000-01-01", "199", 2451545.0, 0.10, 0.20),
    ],
    Body.MARS: [
        PositionCase("2000-01-01", "499", 2451545.0, 0.10, 0.40),
    ],
    Body.JUPITER: [
        PositionCase("2000-01-01", "599", 2451545.0, 0.10, 0.30),
    ],
    Body.SATURN: [
        PositionCase("2000-01-01", "699", 2451545.0, 0.10, 0.20),
    ],
    Body.PLUTO: [
        PositionCase("1960-01-01", "999", 2436934.5, 0.10, 0.50),
        PositionCase("2000-01-01", "999", 2451545.0, 0.10, 0.20),
        PositionCase("2024-01-01", "999", 2460310.5, 0.10, 0.50),
    ],
}

STRICT_POSITION_ASTEROID_CASES: dict[str, list[PositionCase]] = {
    "Chiron": [
        PositionCase("1960-01-01", "2060", 2436934.5, 0.10, 0.15),
        PositionCase("2000-01-01", "2060", 2451545.0, 0.10, 0.15),
        PositionCase("2024-01-01", "2060", 2460310.5, 0.10, 0.15),
    ],
    "Pholus": [
        PositionCase("2000-01-01", "5145", 2451545.0, 0.10, 0.15),
    ],
    "Chariklo": [
        PositionCase("2000-01-01", "10199", 2451545.0, 0.10, 0.15),
    ],
}


EXPLORATORY_POSITION_PLANET_CASES: dict[str, list[PositionCase]] = {
    Body.SUN: [
        PositionCase("1800-06-24", "10", 2378670.5, 0.10, 0.50),
        PositionCase("1850-01-01", "10", 2396758.5, 0.10, 0.50),
        PositionCase("2100-01-01", "10", 2488069.5, 0.15, 0.50),
        PositionCase("2150-01-01", "10", 2506331.5, 0.20, 0.50),
    ],
    Body.MOON: [
        PositionCase("1800-06-24", "301", 2378670.5, 0.15, 0.50),
        PositionCase("1850-01-01", "301", 2396758.5, 0.15, 0.50),
        PositionCase("2100-01-01", "301", 2488069.5, 1.50, 0.50),
        PositionCase("2150-01-01", "301", 2506331.5, 2.50, 0.50),
    ],
    Body.MERCURY: [
        PositionCase("1850-01-01", "199", 2396758.5, 0.10, 0.20),
        PositionCase("2150-01-01", "199", 2506331.5, 0.25, 0.20),
    ],
    Body.MARS: [
        PositionCase("1850-01-01", "499", 2396758.5, 0.10, 0.40),
        PositionCase("2150-01-01", "499", 2506331.5, 0.15, 0.40),
    ],
    Body.JUPITER: [
        PositionCase("1850-01-01", "599", 2396758.5, 0.10, 0.30),
        PositionCase("2150-01-01", "599", 2506331.5, 0.10, 0.30),
    ],
    Body.SATURN: [
        PositionCase("1850-01-01", "699", 2396758.5, 0.10, 0.20),
        PositionCase("2150-01-01", "699", 2506331.5, 0.10, 0.20),
    ],
    Body.PLUTO: [
        PositionCase("1800-06-24", "999", 2378670.5, 0.10, 0.50),
        PositionCase("1850-01-01", "999", 2396758.5, 0.10, 0.50),
        PositionCase("2100-01-01", "999", 2488069.5, 0.15, 0.50),
        PositionCase("2150-01-01", "999", 2506331.5, 0.10, 0.50),
    ],
}

EXPLORATORY_POSITION_ASTEROID_CASES: dict[str, list[PositionCase]] = {
    "Chiron": [
        PositionCase("1800-06-24", "2060", 2378670.5, 0.10, 0.15),
        PositionCase("1850-01-01", "2060", 2396758.5, 0.10, 0.15),
        PositionCase("2100-01-01", "2060", 2488069.5, 0.10, 0.15),
        PositionCase("2150-01-01", "2060", 2506331.5, 0.10, 0.15),
    ],
    "Pholus": [
        PositionCase("1800-06-24", "5145", 2378670.5, 0.10, 0.15),
        PositionCase("1850-01-01", "5145", 2396758.5, 0.10, 0.15),
        PositionCase("2100-01-01", "5145", 2488069.5, 0.10, 0.15),
        PositionCase("2150-01-01", "5145", 2506331.5, 0.10, 0.15),
    ],
    "Chariklo": [
        PositionCase("1800-06-24", "10199", 2378670.5, 0.10, 0.15),
        PositionCase("1850-01-01", "10199", 2396758.5, 0.10, 0.15),
        PositionCase("2100-01-01", "10199", 2488069.5, 0.10, 0.15),
        PositionCase("2150-01-01", "10199", 2506331.5, 0.10, 0.15),
    ],
}


POSITION_PLANET_CASES = STRICT_POSITION_PLANET_CASES | {
    body: STRICT_POSITION_PLANET_CASES.get(body, []) + EXPLORATORY_POSITION_PLANET_CASES.get(body, [])
    for body in set(STRICT_POSITION_PLANET_CASES) | set(EXPLORATORY_POSITION_PLANET_CASES)
}

POSITION_ASTEROID_CASES = STRICT_POSITION_ASTEROID_CASES | {
    body: STRICT_POSITION_ASTEROID_CASES.get(body, []) + EXPLORATORY_POSITION_ASTEROID_CASES.get(body, [])
    for body in set(STRICT_POSITION_ASTEROID_CASES) | set(EXPLORATORY_POSITION_ASTEROID_CASES)
}

VECTOR_PLANET_CASES: dict[str, list[VectorCase]] = {
    Body.SUN: [
        VectorCase("1800-06-24", "10", 2378670.5, 5.0),
        VectorCase("2000-01-01", "10", 2451545.0, 5.0),
        VectorCase("2150-01-01", "10", 2506331.5, 5.0),
    ],
    Body.MOON: [
        VectorCase("1800-06-24", "301", 2378670.5, 5.0),
        VectorCase("2000-01-01", "301", 2451545.0, 5.0),
        VectorCase("2150-01-01", "301", 2506331.5, 5.0),
    ],
    Body.PLUTO: [
        VectorCase("1800-06-24", "999", 2378670.5, 1.0),
        VectorCase("2000-01-01", "999", 2451545.0, 1.0),
        VectorCase("2150-01-01", "999", 2506331.5, 1.0),
    ],
}

VECTOR_ASTEROID_CASES: dict[str, list[VectorCase]] = {
    "Chiron": [
        VectorCase("1800-06-24", "2060", 2378670.5, 1.0),
        VectorCase("2000-01-01", "2060", 2451545.0, 1.0),
        VectorCase("2150-01-01", "2060", 2506331.5, 1.0),
    ],
    "Pholus": [
        VectorCase("1800-06-24", "5145", 2378670.5, 1.0),
        VectorCase("2000-01-01", "5145", 2451545.0, 1.0),
        VectorCase("2150-01-01", "5145", 2506331.5, 1.0),
    ],
}


STRICT_SKY_PLANET_CASES: dict[str, list[SkyCase]] = {
    Body.SUN: [
        SkyCase("Greenwich-2000-01-01", "10", 2451545.0, 51.4769, 0.0, 0.0, 30.0, 5.0, 1500.0, 900.0),
        SkyCase("Greenwich-2024-01-01", "10", 2460311.0, 51.4769, 0.0, 0.0, 30.0, 5.0, 1500.0, 900.0),
        SkyCase("NewYork-2024-01-01", "10", 2460311.0, 40.7128, -74.0060, 0.0, 30.0, 5.0, 1500.0, 900.0),
    ],
    Body.MOON: [
        SkyCase("Greenwich-2000-01-01", "301", 2451545.0, 51.4769, 0.0, 0.0, 25.0, 12.0, 1600.0, 500.0),
        SkyCase("Greenwich-2024-01-01", "301", 2460311.0, 51.4769, 0.0, 0.0, 25.0, 12.0, 1600.0, 500.0),
        SkyCase("NewYork-2024-01-01", "301", 2460311.0, 40.7128, -74.0060, 0.0, 25.0, 12.0, 1600.0, 500.0),
    ],
    Body.MERCURY: [
        SkyCase("Greenwich-2000-01-01", "199", 2451545.0, 51.4769, 0.0, 0.0, 30.0, 6.0, 1600.0, 900.0),
        SkyCase("Greenwich-2024-01-01", "199", 2460311.0, 51.4769, 0.0, 0.0, 30.0, 6.0, 1600.0, 900.0),
    ],
    Body.MARS: [
        SkyCase("Greenwich-2000-01-01", "499", 2451545.0, 51.4769, 0.0, 0.0, 30.0, 8.0, 1600.0, 900.0),
        SkyCase("Greenwich-2024-01-01", "499", 2460311.0, 51.4769, 0.0, 0.0, 30.0, 8.0, 1600.0, 900.0),
    ],
    Body.JUPITER: [
        SkyCase("Greenwich-2000-01-01", "599", 2451545.0, 51.4769, 0.0, 0.0, 15.0, 4.0, 1600.0, 900.0),
        SkyCase("Greenwich-2024-01-01", "599", 2460311.0, 51.4769, 0.0, 0.0, 15.0, 4.0, 1600.0, 900.0),
    ],
    Body.SATURN: [
        SkyCase("Greenwich-2000-01-01", "699", 2451545.0, 51.4769, 0.0, 0.0, 15.0, 6.0, 1600.0, 900.0),
        SkyCase("Greenwich-2024-01-01", "699", 2460311.0, 51.4769, 0.0, 0.0, 15.0, 6.0, 1600.0, 900.0),
    ],
    Body.PLUTO: [
        SkyCase("Greenwich-2000-01-01", "999", 2451545.0, 51.4769, 0.0, 0.0, 25.0, 6.0, 1600.0, 900.0),
        SkyCase("Greenwich-2024-01-01", "999", 2460311.0, 51.4769, 0.0, 0.0, 25.0, 6.0, 1600.0, 900.0),
    ],
    Body.VENUS: [
        SkyCase("Greenwich-2000-01-01", "299", 2451545.0, 51.4779, 0.0, 0.0, 30.0, 6.0, 1600.0, 900.0),
        SkyCase("Greenwich-2024-01-01", "299", 2460310.5, 51.4779, 0.0, 0.0, 30.0, 6.0, 1600.0, 900.0),
    ],
}
