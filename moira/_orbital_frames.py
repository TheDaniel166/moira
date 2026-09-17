"""Primary-source frame routing for Stage 1 osculating elements.

The matrix constructions are independently named Python adaptations of IAU
SOFA Issue 2023-10-11 Ecm06, Ltecm, and the documented
``Rx(epsa+deps) * Pnm06a`` composition.  This derived module is not SOFA
software and is not endorsed by the IAU SOFA Board.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._orbital_errors import OrbitalFrameUnavailableError, OrbitalInputError
from .constants import ARCSEC2RAD
from .coordinates import Mat3, Vec3, mat_mul, mat_vec_mul, rot_x_axis
from .julian import J2000
from .obliquity import nutation
from .precession import (
    _cross3,
    _norm3,
    _vondrak_ltpecl,
    _vondrak_ltpequ,
    mean_obliquity_p03,
    precession_matrix,
)


J2000_ECLIPTIC = "J2000_ECLIPTIC"
MEAN_ECLIPTIC_OF_DATE = "MEAN_ECLIPTIC_OF_DATE"
TRUE_ECLIPTIC_OF_DATE = "TRUE_ECLIPTIC_OF_DATE"

MODERN_FRAME_INTERVAL_TT = (2415020.0, 2488070.0)
LONG_TERM_JULIAN_EPOCH_INTERVAL = (-200000.0, 200000.0)
LONG_TERM_FRAME_INTERVAL_TT = (
    J2000 + (LONG_TERM_JULIAN_EPOCH_INTERVAL[0] - 2000.0) * 365.25,
    J2000 + (LONG_TERM_JULIAN_EPOCH_INTERVAL[1] - 2000.0) * 365.25,
)
_J2000_HORIZONS_OBLIQUITY_RAD = 84381.448 * ARCSEC2RAD


@dataclass(frozen=True, slots=True)
class _OrbitalFrameTransform:
    """One selected ICRS-to-ecliptic matrix and its model receipt."""

    frame_key: str
    matrix: Mat3
    routine: str
    router_branch: str
    admitted_interval_tt: tuple[float, float] | None
    precession_model: str | None
    obliquity_model: str
    nutation_model: str | None


def _require_epoch_tt(epoch_tt: float) -> float:
    if isinstance(epoch_tt, bool) or not isinstance(epoch_tt, (int, float)):
        raise OrbitalInputError("epoch_tt", epoch_tt, ("finite real",))
    result = float(epoch_tt)
    if not math.isfinite(result) or math.ulp(result) >= 1.0:
        raise OrbitalInputError("epoch_tt", epoch_tt, ("finite representable JD",))
    return result


def _normalize_frame_key(frame: object) -> str:
    value = getattr(frame, "value", frame)
    if not isinstance(value, str):
        raise OrbitalInputError(
            "frame",
            frame,
            (J2000_ECLIPTIC, MEAN_ECLIPTIC_OF_DATE, TRUE_ECLIPTIC_OF_DATE),
        )
    key = value.upper()
    if key not in {
        J2000_ECLIPTIC,
        MEAN_ECLIPTIC_OF_DATE,
        TRUE_ECLIPTIC_OF_DATE,
    }:
        raise OrbitalInputError(
            "frame",
            value,
            (J2000_ECLIPTIC, MEAN_ECLIPTIC_OF_DATE, TRUE_ECLIPTIC_OF_DATE),
        )
    return key


def _apply_first_order_icrs_bias(rows: Mat3) -> Mat3:
    """Apply the IERS 2010 first-order bias used by SOFA Ltecm/Ltpb."""

    dx = -0.016617 * ARCSEC2RAD
    de = -0.0068192 * ARCSEC2RAD
    dr = -0.0146 * ARCSEC2RAD
    return tuple(
        (
            row[0] - row[1] * dr + row[2] * dx,
            row[0] * dr + row[1] + row[2] * de,
            -row[0] * dx - row[1] * de + row[2],
        )
        for row in rows
    )


def _long_term_ecliptic_matrix(epoch_tt: float) -> Mat3:
    """Return the long-term ICRS-to-ecliptic matrix (SOFA Ltecm semantics)."""

    centuries = (epoch_tt - J2000) / 36525.0
    equator_pole = _vondrak_ltpequ(centuries)
    ecliptic_pole = _vondrak_ltpecl(centuries)
    equinox = _norm3(_cross3(equator_pole, ecliptic_pole))
    middle = _cross3(ecliptic_pole, equinox)
    return _apply_first_order_icrs_bias((equinox, middle, ecliptic_pole))


def orbital_frame_transform(frame: object, epoch_tt: float) -> _OrbitalFrameTransform:
    """Select an admitted Stage 1 ICRS-to-ecliptic frame matrix."""

    key = _normalize_frame_key(frame)
    epoch = _require_epoch_tt(epoch_tt)
    if key == J2000_ECLIPTIC:
        return _OrbitalFrameTransform(
            frame_key=key,
            matrix=rot_x_axis(_J2000_HORIZONS_OBLIQUITY_RAD),
            routine="HORIZONS_IAU76_80_J2000_OBLIQUITY_ROTATION",
            router_branch="fixed_j2000",
            admitted_interval_tt=None,
            precession_model=None,
            obliquity_model="IAU76_80_J2000_84381.448_ARCSEC",
            nutation_model=None,
        )

    if key == TRUE_ECLIPTIC_OF_DATE:
        if not MODERN_FRAME_INTERVAL_TT[0] <= epoch <= MODERN_FRAME_INTERVAL_TT[1]:
            raise OrbitalFrameUnavailableError(
                key,
                epoch,
                (MODERN_FRAME_INTERVAL_TT,),
            )
        epsa_deg = mean_obliquity_p03(epoch)
        _dpsi_deg, deps_deg = nutation(epoch)
        from .coordinates import nutation_matrix_equatorial

        rnpb = mat_mul(
            nutation_matrix_equatorial(epoch),
            precession_matrix(epoch),
        )
        return _OrbitalFrameTransform(
            frame_key=key,
            matrix=mat_mul(
                rot_x_axis(math.radians(epsa_deg + deps_deg)),
                rnpb,
            ),
            routine="OBL06_NUT06A_PNM06A_RX",
            router_branch="modern_true",
            admitted_interval_tt=MODERN_FRAME_INTERVAL_TT,
            precession_model="IAU_2006_PMAT06",
            obliquity_model="IAU_2006_OBL06",
            nutation_model="IAU_2006_2000A_NUT06A",
        )

    if MODERN_FRAME_INTERVAL_TT[0] <= epoch <= MODERN_FRAME_INTERVAL_TT[1]:
        return _OrbitalFrameTransform(
            frame_key=key,
            matrix=mat_mul(
                rot_x_axis(math.radians(mean_obliquity_p03(epoch))),
                precession_matrix(epoch),
            ),
            routine="ECM06",
            router_branch="modern_mean",
            admitted_interval_tt=MODERN_FRAME_INTERVAL_TT,
            precession_model="IAU_2006_PMAT06",
            obliquity_model="IAU_2006_OBL06",
            nutation_model=None,
        )

    if not LONG_TERM_FRAME_INTERVAL_TT[0] <= epoch <= LONG_TERM_FRAME_INTERVAL_TT[1]:
        raise OrbitalFrameUnavailableError(
            key,
            epoch,
            (LONG_TERM_FRAME_INTERVAL_TT,),
        )
    return _OrbitalFrameTransform(
        frame_key=key,
        matrix=_long_term_ecliptic_matrix(epoch),
        routine="LTECM",
        router_branch="long_term_mean",
        admitted_interval_tt=LONG_TERM_FRAME_INTERVAL_TT,
        precession_model="VONDRAK_2011_2012_LTECM",
        obliquity_model="VONDRAK_LONG_TERM_ECLIPTIC_POLE",
        nutation_model=None,
    )


def rotate_orbital_state(
    transform: _OrbitalFrameTransform,
    position_icrf_km: Vec3,
    velocity_icrf_km_per_day: Vec3,
) -> tuple[Vec3, Vec3]:
    """Rotate position and velocity by the same instantaneous matrix."""

    return (
        mat_vec_mul(transform.matrix, position_icrf_km),
        mat_vec_mul(transform.matrix, velocity_icrf_km_per_day),
    )
