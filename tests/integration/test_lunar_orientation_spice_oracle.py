from __future__ import annotations

import pytest

from moira._lunar_orientation_resources import (
    _resolve_resource,
    lunar_me_rotation,
    lunar_orientation_resources,
)


spice = pytest.importorskip("spiceypy")


def _max_matrix_residual(left, right) -> float:
    return max(
        abs(float(left[row][column]) - float(right[row][column]))
        for row in range(3)
        for column in range(3)
    )


def test_native_pck_and_fixed_frame_match_spice_pxform() -> None:
    resources = lunar_orientation_resources()
    spice.kclear()
    spice.furnsh(str(_resolve_resource("moon_pa_de440_200625.bpc")))
    spice.furnsh(str(_resolve_resource("moon_de440_250416.tf")))
    boundary = float(resources.handle.catalog()["summaries"][1]["descriptor"][0]) / 86400.0 + 2451545.0
    epochs = (
        resources.coverage_start_jd_tdb,
        2451545.0,
        2461309.5,
        boundary,
        resources.coverage_end_jd_tdb,
    )
    try:
        for jd_tdb in epochs:
            et = (jd_tdb - 2451545.0) * 86400.0
            native_pa = resources.handle.rotation_matrix(jd_tdb)
            spice_pa = spice.pxform("J2000", "MOON_PA_DE440", et)
            assert _max_matrix_residual(native_pa, spice_pa) <= 3.0e-12

            native_me = lunar_me_rotation(jd_tdb)
            spice_me = spice.pxform("J2000", "MOON_ME_DE440_ME421", et)
            assert _max_matrix_residual(native_me, spice_me) <= 3.0e-12
    finally:
        spice.kclear()
