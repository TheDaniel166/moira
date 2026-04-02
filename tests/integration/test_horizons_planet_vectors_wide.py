from __future__ import annotations

from math import asin, degrees, sqrt

import pytest

from moira.constants import Body
from moira.julian import julian_day, ut_to_tt
from moira.planets import _geocentric
from moira.spk_reader import get_reader
from tools.horizons import VectorState, vector_state


ANGULAR_THRESHOLD_ARCSEC = 1.0
VECTOR_DIFF_THRESHOLD_KM = 15_000.0

BODIES: list[tuple[str, str]] = [
    (Body.SUN, "10"),
    (Body.MOON, "301"),
    (Body.MERCURY, "199"),
    (Body.VENUS, "299"),
    (Body.MARS, "499"),
    (Body.JUPITER, "599"),
    (Body.SATURN, "699"),
    (Body.URANUS, "799"),
    (Body.NEPTUNE, "899"),
    (Body.PLUTO, "999"),
]

EPOCHS: list[tuple[str, float]] = [
    ("1800-06-24", julian_day(1800, 6, 24, 12)),
    ("1850-01-01", julian_day(1850, 1, 1, 12)),
    ("1900-01-01", julian_day(1900, 1, 1, 12)),
    ("1950-06-15", julian_day(1950, 6, 15, 12)),
    ("2000-01-01", julian_day(2000, 1, 1, 12)),
    ("2025-09-01", julian_day(2025, 9, 1, 12)),
    ("2100-01-01", julian_day(2100, 1, 1, 12)),
    ("2150-01-01", julian_day(2150, 1, 1, 12)),
]


def _vector_diff(moira_xyz: tuple[float, float, float], ref: VectorState) -> tuple[float, float]:
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
    ang_arcsec = degrees(asin(ratio)) * 3600.0
    return diff_km, ang_arcsec


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(("body", "command"), BODIES, ids=[body for body, _ in BODIES])
@pytest.mark.parametrize(("label", "jd_ut"), EPOCHS, ids=[label for label, _ in EPOCHS])
def test_planet_geocentric_vectors_match_horizons_across_wide_de441_range(
    body: str,
    command: str,
    label: str,
    jd_ut: float,
) -> None:
    reader = get_reader()
    moira_xyz = _geocentric(body, ut_to_tt(jd_ut), reader)
    ref = vector_state(command, jd_ut)
    diff_km, error_arcsec = _vector_diff(moira_xyz, ref)

    assert error_arcsec <= ANGULAR_THRESHOLD_ARCSEC, (
        f"{body} {label}: vector angular error {error_arcsec:.6f} arcsec "
        f"exceeds {ANGULAR_THRESHOLD_ARCSEC:.3f}"
    )
    assert diff_km <= VECTOR_DIFF_THRESHOLD_KM, (
        f"{body} {label}: vector difference {diff_km:.6f} km "
        f"exceeds {VECTOR_DIFF_THRESHOLD_KM:.3f}"
    )
