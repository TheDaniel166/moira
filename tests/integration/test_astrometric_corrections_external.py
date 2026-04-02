from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.corrections import C_KM_PER_DAY, apply_aberration, apply_light_time
from moira.julian import ut_to_tt
from moira.planets import _barycentric, _earth_barycentric
from moira.spk_reader import get_reader
from tools.horizons import vector_state_corrected


ARCSEC = 3600.0
ABERRATION_THRESHOLD_ARCSEC = 1e-6
LIGHT_TIME_ANGLE_THRESHOLD_ARCSEC = 0.05
LIGHT_TIME_DISTANCE_THRESHOLD_KM = 200.0


def _norm(v: tuple[float, float, float]) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def _unit(v: tuple[float, float, float]) -> tuple[float, float, float]:
    mag = _norm(v)
    return (v[0] / mag, v[1] / mag, v[2] / mag)


def _angular_sep_arcsec(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    ua = _unit(a)
    ub = _unit(b)
    dot = max(-1.0, min(1.0, ua[0] * ub[0] + ua[1] * ub[1] + ua[2] * ub[2]))
    return math.degrees(math.acos(dot)) * ARCSEC


def _vector_diff_km(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


ABERRATION_CASES: list[tuple[str, tuple[float, float, float], tuple[float, float, float]]] = [
    (
        "forward-offset",
        (0.96, 0.24, 0.12),
        (-0.000021, 0.000087, 0.000004),
    ),
    (
        "quadrature",
        (-0.35, 0.91, 0.21),
        (0.000083, 0.000011, -0.000019),
    ),
    (
        "retrograde-like",
        (0.28, -0.52, 0.81),
        (-0.000062, -0.000054, 0.000008),
    ),
]


@pytest.mark.integration
@pytest.mark.parametrize("label,direction,beta", ABERRATION_CASES, ids=[case[0] for case in ABERRATION_CASES])
def test_apply_aberration_matches_erfa_ab(
    label: str,
    direction: tuple[float, float, float],
    beta: tuple[float, float, float],
) -> None:
    """
    Annual aberration must match the ERFA aberration routine at the vector level.
    """
    erfa = pytest.importorskip("erfa")
    pnat = _unit(direction)
    xyz = tuple(component * 1.0e8 for component in pnat)
    earth_velocity = tuple(component * C_KM_PER_DAY for component in beta)
    beta2 = sum(component * component for component in beta)
    bm1 = math.sqrt(1.0 - beta2)

    moira = apply_aberration(xyz, earth_velocity)
    erfa_vec = erfa.ab(pnat, beta, 1.0, bm1)

    error_arcsec = _angular_sep_arcsec(moira, tuple(float(x) for x in erfa_vec))
    assert error_arcsec <= ABERRATION_THRESHOLD_ARCSEC, (
        f"{label}: aberration angular error {error_arcsec:.9f}\" exceeds "
        f"{ABERRATION_THRESHOLD_ARCSEC:.9f}\""
    )


LIGHT_TIME_CASES: list[tuple[str, str, str, float]] = [
    ("moon-2024-04-08", Body.MOON, "301", 2460409.5),
    ("mars-2024-04-09", Body.MARS, "499", 2460409.5),
    ("jupiter-2024-04-09", Body.JUPITER, "599", 2460409.5),
]


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize("label,body,command,jd_ut", LIGHT_TIME_CASES, ids=[case[0] for case in LIGHT_TIME_CASES])
def test_apply_light_time_matches_horizons_lt_vectors(
    label: str,
    body: str,
    command: str,
    jd_ut: float,
) -> None:
    """
    The light-time correction stage must agree with Horizons VECTORS LT output.

    This isolates the Newtonian receive light-time step from aberration,
    deflection, and frame rotations.
    """
    reader = get_reader()
    jd_tt = ut_to_tt(jd_ut)
    earth_ssb = _earth_barycentric(jd_tt, reader)
    moira_xyz, light_time_days = apply_light_time(body, jd_tt, reader, earth_ssb, _barycentric)

    ref_lt = vector_state_corrected(command, jd_ut, center="500@399", vec_corr="LT")
    ref_none = vector_state_corrected(command, jd_ut, center="500@399", vec_corr="NONE")
    ref_xyz = (ref_lt.x, ref_lt.y, ref_lt.z)
    ref_none_xyz = (ref_none.x, ref_none.y, ref_none.z)

    angle_error_arcsec = _angular_sep_arcsec(moira_xyz, ref_xyz)
    distance_error_km = _vector_diff_km(moira_xyz, ref_xyz)
    lt_shift_km = _vector_diff_km(ref_none_xyz, ref_xyz)

    assert light_time_days > 0.0, f"{label}: expected positive light-time"
    assert lt_shift_km > 0.0, f"{label}: Horizons LT and NONE vectors unexpectedly identical"
    assert angle_error_arcsec <= LIGHT_TIME_ANGLE_THRESHOLD_ARCSEC, (
        f"{label}: light-time angular error {angle_error_arcsec:.6f}\" exceeds "
        f"{LIGHT_TIME_ANGLE_THRESHOLD_ARCSEC:.3f}\""
    )
    assert distance_error_km <= LIGHT_TIME_DISTANCE_THRESHOLD_KM, (
        f"{label}: light-time vector error {distance_error_km:.6f} km exceeds "
        f"{LIGHT_TIME_DISTANCE_THRESHOLD_KM:.3f} km"
    )
