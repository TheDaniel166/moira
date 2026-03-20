#!/usr/bin/env python

import sys
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.asteroids import asteroid_at
from moira.constants import Body
from moira.planets import planet_at
from tests.tools.horizons import observer_ecliptic_position, signed_arcminutes


@dataclass(frozen=True)
class Case:
    name: str
    command: str
    jd_ut: float
    kind: str


CASES = [
    # --- Planets (Classical and Modern epochs) ---
    Case(Body.SUN, "10", 2305447.5, "planet"),       # 1600
    Case(Body.SUN, "10", 2396758.5, "planet"),       # 1850
    Case(Body.SUN, "10", 2436934.5, "planet"),       # 1960
    Case(Body.SUN, "10", 2451545.0, "planet"),       # 2000
    Case(Body.SUN, "10", 2460310.5, "planet"),       # 2024
    Case(Body.SUN, "10", 2488128.5, "planet"),       # 2100
    
    Case(Body.MOON, "301", 2396758.5, "planet"),
    Case(Body.MOON, "301", 2451545.0, "planet"),
    Case(Body.MOON, "301", 2488128.5, "planet"),

    Case(Body.MARS, "4",   2451545.0, "planet"),
    Case(Body.JUPITER, "5", 2451545.0, "planet"),
    Case(Body.NEPTUNE, "8", 2451545.0, "planet"),
    
    Case(Body.PLUTO, "999", 2305447.5, "planet"),
    Case(Body.PLUTO, "999", 2451545.0, "planet"),
    Case(Body.PLUTO, "999", 2488128.5, "planet"),

    # --- Asteroids / Centaurs ---
    Case("Ceres", "2000001", 2451545.0, "asteroid"),
    Case("Chiron", "2002060", 2396758.5, "asteroid"),
    Case("Chiron", "2002060", 2451545.0, "asteroid"),
    Case("Chiron", "2002060", 2488128.5, "asteroid"),
    Case("Pholus", "2005145", 2451545.0, "asteroid"),
    Case("Chariklo", "2010199", 2451545.0, "asteroid"),
]


def _position(case: Case):
    if case.kind == "planet":
        return planet_at(case.name, case.jd_ut)
    return asteroid_at(case.name, case.jd_ut)


def main() -> None:
    print("Moira vs JPL Horizons accuracy report")
    print("body       jd_ut       lon_err_arcmin   lat_err_arcmin")
    print("------------------------------------------------------")

    max_lon = ("", 0.0)
    max_lat = ("", 0.0)

    for case in CASES:
        moira = _position(case)
        ref = observer_ecliptic_position(case.command, case.jd_ut)
        lon_error = signed_arcminutes(moira.longitude, ref.longitude)
        lat_error = (moira.latitude - ref.latitude) * 60.0
        label = f"{case.name} {case.jd_ut:.1f}"
        print(f"{case.name:<10} {case.jd_ut:>10.1f} {lon_error:>16.4f} {lat_error:>17.4f}")

        if abs(lon_error) > max_lon[1]:
            max_lon = (label, abs(lon_error))
        if abs(lat_error) > max_lat[1]:
            max_lat = (label, abs(lat_error))

    print()
    print(f"max longitude error: {max_lon[1]:.4f} arcmin  ({max_lon[0]})")
    print(f"max latitude error:  {max_lat[1]:.4f} arcmin  ({max_lat[0]})")


if __name__ == "__main__":
    main()
