from __future__ import annotations

from math import asin, degrees, sqrt

import pytest

from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.constants import Body, NAIF_ROUTES
from moira.julian import julian_day
from moira.planets import _geocentric
from tools.horizons import VectorState, vector_state_tdb


ANGULAR_THRESHOLD_ARCSEC = 0.001
VECTOR_DIFF_THRESHOLD_KM = 0.01

HORIZONS_TARGETS: list[tuple[str, str, str]] = [
    (Body.SUN, "10", "Sun center"),
    (Body.MOON, "301", "Moon center"),
    (Body.MERCURY, "199", "Mercury center"),
    (Body.VENUS, "299", "Venus center"),
    (Body.MARS, "4", "Mars system barycenter"),
    (Body.JUPITER, "5", "Jupiter system barycenter"),
    (Body.SATURN, "6", "Saturn system barycenter"),
    (Body.URANUS, "7", "Uranus system barycenter"),
    (Body.NEPTUNE, "8", "Neptune system barycenter"),
    (Body.PLUTO, "9", "Pluto system barycenter"),
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


def test_wide_vector_targets_match_moira_route_identities() -> None:
    """Keep the vector oracle on the same DE441 target as Moira."""
    assert [body for body, _command, _identity in HORIZONS_TARGETS] == list(
        Body.ALL_PLANETS
    )
    for body, command, identity in HORIZONS_TARGETS:
        assert int(command) == NAIF_ROUTES[body][-1][1], (
            f"{body}: Horizons target {command} ({identity}) does not match "
            f"Moira's final SPK target {NAIF_ROUTES[body][-1][1]}"
        )


@pytest.mark.integration
@pytest.mark.external_network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(
    ("body", "command", "target_identity"),
    HORIZONS_TARGETS,
    ids=[body for body, _command, _identity in HORIZONS_TARGETS],
)
@pytest.mark.parametrize(("label", "jd_ut"), EPOCHS, ids=[label for label, _ in EPOCHS])
def test_planet_geocentric_vectors_match_horizons_across_wide_de441_range(
    body: str,
    command: str,
    target_identity: str,
    label: str,
    jd_ut: float,
    planetary_reader,
) -> None:
    # Moira currently passes its reader-bound ephemeris JD directly to the SPK
    # evaluator. Horizons receives that same numeric JD explicitly as TDB, so
    # this fixture isolates target/vector geometry rather than independently
    # validating a TT-to-TDB conversion.
    jd_ephemeris = _ut1_to_ephemeris_tt(jd_ut, planetary_reader)
    moira_xyz = _geocentric(body, jd_ephemeris, planetary_reader)
    ref = vector_state_tdb(command, jd_ephemeris)
    diff_km, error_arcsec = _vector_diff(moira_xyz, ref)

    assert error_arcsec <= ANGULAR_THRESHOLD_ARCSEC, (
        f"{body} ({target_identity}) {label}: vector angular error "
        f"{error_arcsec:.6f} arcsec "
        f"exceeds {ANGULAR_THRESHOLD_ARCSEC:.3f}"
    )
    assert diff_km <= VECTOR_DIFF_THRESHOLD_KM, (
        f"{body} ({target_identity}) {label}: vector difference "
        f"{diff_km:.6f} km "
        f"exceeds {VECTOR_DIFF_THRESHOLD_KM:.3f}"
    )
