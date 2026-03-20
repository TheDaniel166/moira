from __future__ import annotations

from math import asin, degrees, sqrt

import pytest

from moira.asteroids import ASTEROID_NAIF, _asteroid_geocentric, _kernel_for
from moira.julian import ut_to_tt
from moira.planets import _geocentric
from moira.spk_reader import get_reader
from tests.tools.benchmark_matrix import (
    VECTOR_ASTEROID_CASES,
    VECTOR_PLANET_CASES,
    VectorCase,
)
from tests.tools.horizons import VectorState, vector_state


def _angular_error_arcsec(moira_xyz: tuple[float, float, float], ref: VectorState) -> float:
    dx = moira_xyz[0] - ref.x
    dy = moira_xyz[1] - ref.y
    dz = moira_xyz[2] - ref.z
    diff_km = sqrt(dx * dx + dy * dy + dz * dz)
    dist_km = sqrt(
        moira_xyz[0] * moira_xyz[0]
        + moira_xyz[1] * moira_xyz[1]
        + moira_xyz[2] * moira_xyz[2]
    )
    if dist_km <= 1e-12:
        return 0.0
    ratio = min(1.0, diff_km / dist_km)
    return degrees(asin(ratio)) * 3600.0


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(
    ("body", "case"),
    [(body, case) for body, cases in VECTOR_PLANET_CASES.items() for case in cases],
    ids=[f"{body}-{case.label}" for body, cases in VECTOR_PLANET_CASES.items() for case in cases],
)
def test_planet_geocentric_vectors_match_horizons(body: str, case: VectorCase) -> None:
    reader = get_reader()
    moira_xyz = _geocentric(body, ut_to_tt(case.jd_ut), reader)
    ref = vector_state(case.command, case.jd_ut)
    error_arcsec = _angular_error_arcsec(moira_xyz, ref)

    assert error_arcsec <= case.tolerance_arcsec, (
        f"{body} {case.label}: vector error {error_arcsec:.3f} arcsec "
        f"exceeds {case.tolerance_arcsec:.3f}"
    )


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(
    ("name", "case"),
    [(name, case) for name, cases in VECTOR_ASTEROID_CASES.items() for case in cases],
    ids=[f"{name}-{case.label}" for name, cases in VECTOR_ASTEROID_CASES.items() for case in cases],
)
def test_asteroid_geocentric_vectors_match_horizons(name: str, case: VectorCase) -> None:
    reader = get_reader()
    naif_id = ASTEROID_NAIF[name]
    moira_xyz = _asteroid_geocentric(
        naif_id, ut_to_tt(case.jd_ut), _kernel_for(naif_id), reader, apparent=False
    )
    ref = vector_state(case.command, case.jd_ut)
    error_arcsec = _angular_error_arcsec(moira_xyz, ref)

    assert error_arcsec <= case.tolerance_arcsec, (
        f"{name} {case.label}: vector error {error_arcsec:.3f} arcsec "
        f"exceeds {case.tolerance_arcsec:.3f}"
    )
