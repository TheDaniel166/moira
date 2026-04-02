#!/usr/bin/env python

import sys
from dataclasses import dataclass
from math import asin, degrees, sqrt
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from moira.asteroids import ASTEROID_NAIF, _asteroid_geocentric, _kernel_for
from moira.constants import Body
from moira.julian import ut_to_tt
from moira.planets import _geocentric
from moira.spk_reader import get_reader
from tools.horizons import VectorState, vector_state


@dataclass(frozen=True)
class Case:
    name: str
    command: str
    jd_ut: float
    kind: str


CASES = [
    Case(Body.SUN, "10", 2451545.0, "planet"),
    Case(Body.MOON, "301", 2451545.0, "planet"),
    Case(Body.PLUTO, "999", 2451545.0, "planet"),
    Case("Chiron", "2060", 2451545.0, "asteroid"),
    Case("Pholus", "5145", 2451545.0, "asteroid"),
]


def _angular_error_arcsec(moira_xyz: tuple[float, float, float], ref: VectorState) -> tuple[float, float]:
    dx = moira_xyz[0] - ref.x
    dy = moira_xyz[1] - ref.y
    dz = moira_xyz[2] - ref.z
    diff_km = sqrt(dx * dx + dy * dy + dz * dz)
    dist_km = sqrt(
        moira_xyz[0] * moira_xyz[0]
        + moira_xyz[1] * moira_xyz[1]
        + moira_xyz[2] * moira_xyz[2]
    )
    ratio = min(1.0, diff_km / dist_km) if dist_km > 1e-12 else 0.0
    return diff_km, degrees(asin(ratio)) * 3600.0


def _position(case: Case) -> tuple[float, float, float]:
    reader = get_reader()
    jd_tt = ut_to_tt(case.jd_ut)
    if case.kind == "planet":
        return _geocentric(case.name, jd_tt, reader)
    naif_id = ASTEROID_NAIF[case.name]
    return _asteroid_geocentric(naif_id, jd_tt, _kernel_for(naif_id), reader, apparent=False)


def main() -> None:
    print("Moira vs JPL Horizons vector report")
    print("body       jd_ut       diff_km        ang_err_arcsec")
    print("----------------------------------------------------")

    max_case = ("", 0.0)
    for case in CASES:
        moira_xyz = _position(case)
        ref = vector_state(case.command, case.jd_ut)
        diff_km, error_arcsec = _angular_error_arcsec(moira_xyz, ref)
        print(f"{case.name:<10} {case.jd_ut:>10.1f} {diff_km:>13.3f} {error_arcsec:>18.3f}")
        if error_arcsec > max_case[1]:
            max_case = (f"{case.name} {case.jd_ut:.1f}", error_arcsec)

    print()
    print(f"max angular vector error: {max_case[1]:.3f} arcsec  ({max_case[0]})")


if __name__ == "__main__":
    main()
