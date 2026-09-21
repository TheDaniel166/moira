from __future__ import annotations

import random
import pytest

from moira.houses import (
    _mc_from_armc as py_mc,
    _asc_from_armc as py_asc,
    _vertex_from_armc as py_vertex,
    _project_ra_morinus as py_morinus,
    _placidus as py_placidus,
    _koch as py_koch,
    _regiomontanus as py_regiomontanus,
    _campanus as py_campanus,
    _porphyry as py_porphyry,
    _equal_house as py_equal,
    _whole_sign as py_whole_sign,
    _local_angles_at as py_local_angles_at,
    ut_to_tt,
    nutation,
    true_obliquity,
    _armc,
)
from moira.obliquity import mean_obliquity
from moira import moira_native


def test_native_local_angles_parity_reference() -> None:
    """Validate native angle reduction against Python reference across random epochs and coordinates."""
    random.seed(42)

    for _ in range(1000):
        # Sample JD from -3000 to +3000 CE (JD 625674.5 to 2816912.5)
        jd_ut = random.uniform(625674.5, 2816912.5)
        lat = random.uniform(-65.0, 65.0)
        lon = random.uniform(-180.0, 180.0)

        jd_tt = ut_to_tt(jd_ut)
        dpsi, deps = nutation(jd_tt)
        obl = mean_obliquity(jd_tt) + deps
        armc = _armc(jd_ut, lon, jd_tt, dpsi, obl)
        mc = py_mc(armc, obl, lat)
        asc = py_asc(armc, obl, lat)
        vtx = py_vertex(armc, obl, lat)
        ep = py_morinus((armc + 90.0) % 360.0, obl)

        # Native reduction
        n_armc, n_obl, n_dpsi, n_mc, n_asc, n_vtx, n_ep = moira_native.reduce_local_angles(jd_ut, jd_tt, lat, lon)

        assert abs(armc - n_armc) < 1e-12, f"ARMC divergence: {abs(armc - n_armc)}"
        assert abs(obl - n_obl) < 1e-12, f"Obliquity divergence: {abs(obl - n_obl)}"
        assert abs(dpsi - n_dpsi) < 1e-12, f"dpsi divergence: {abs(dpsi - n_dpsi)}"
        assert abs(mc - n_mc) < 1e-12, f"MC divergence: {abs(mc - n_mc)}"
        assert abs(asc - n_asc) < 1e-12, f"ASC divergence: {abs(asc - n_asc)}"
        assert abs(vtx - n_vtx) < 1e-12, f"Vertex divergence: {abs(vtx - n_vtx)}"
        assert abs(ep - n_ep) < 1e-12, f"East Point divergence: {abs(ep - n_ep)}"


def test_native_placidus_parity_gauntlet() -> None:
    """Validate native Placidus cusps against Python Placidus across 2,000 global configurations."""
    random.seed(1337)

    for _ in range(2000):
        armc = random.uniform(0.0, 360.0)
        obl = random.uniform(21.5, 24.5)
        # Stay within normal Placidus convergence zone (< ~65 degrees)
        lat = random.uniform(-62.0, 62.0)

        mc = py_mc(armc, obl, lat)
        asc = py_asc(armc, obl, lat)

        try:
            py_cusps = py_placidus(armc, obl, lat)
        except (ValueError, ZeroDivisionError):
            continue

        native_cusps = moira_native.calculate_houses_cusps(armc, obl, lat, asc, mc, "P")

        for cusp_idx in range(12):
            diff = abs(py_cusps[cusp_idx] - native_cusps[cusp_idx])
            # Handle 0/360 wrap
            if diff > 180.0:
                diff = abs(diff - 360.0)
            assert diff < 1e-11, f"Placidus Cusp {cusp_idx + 1} divergence at ARMC={armc}, lat={lat}: {diff} deg"


def test_native_porphyry_parity_gauntlet() -> None:
    """Validate native Porphyry cusps against Python Porphyry across 1,000 configurations."""
    random.seed(2026)

    for _ in range(1000):
        asc = random.uniform(0.0, 360.0)
        mc = random.uniform(0.0, 360.0)

        py_cusps = py_porphyry(asc, mc)
        native_cusps = moira_native.calculate_houses_cusps(0.0, 23.44, 0.0, asc, mc, "O")

        for cusp_idx in range(12):
            diff = abs(py_cusps[cusp_idx] - native_cusps[cusp_idx])
            if diff > 180.0:
                diff = abs(diff - 360.0)
            assert diff < 1e-12, f"Porphyry Cusp {cusp_idx + 1} divergence: {diff} deg"


def test_native_equal_and_whole_sign_parity() -> None:
    """Validate native Equal and Whole Sign cusps against Python reference."""
    random.seed(777)

    for _ in range(1000):
        asc = random.uniform(0.0, 360.0)

        py_eq = py_equal(asc)
        native_eq = moira_native.calculate_houses_cusps(0.0, 23.44, 0.0, asc, 0.0, "E")
        for cusp_idx in range(12):
            diff = abs(py_eq[cusp_idx] - native_eq[cusp_idx])
            if diff > 180.0:
                diff = abs(diff - 360.0)
            assert diff < 1e-12, f"Equal Cusp {cusp_idx + 1} divergence: {diff} deg"

        py_ws = py_whole_sign(asc)
        native_ws = moira_native.calculate_houses_cusps(0.0, 23.44, 0.0, asc, 0.0, "W")
        for cusp_idx in range(12):
            diff = abs(py_ws[cusp_idx] - native_ws[cusp_idx])
            if diff > 180.0:
                diff = abs(diff - 360.0)
            assert diff < 1e-12, f"Whole Sign Cusp {cusp_idx + 1} divergence: {diff} deg"


def test_native_koch_parity_gauntlet() -> None:
    """Validate native Koch cusps against Python Koch across 1,000 configurations."""
    random.seed(1001)

    for _ in range(1000):
        armc = random.uniform(0.0, 360.0)
        obl = random.uniform(22.0, 24.5)
        lat = random.uniform(-62.0, 62.0)

        mc = py_mc(armc, obl, lat)
        asc = py_asc(armc, obl, lat)

        try:
            py_cusps = py_koch(armc, obl, lat)
        except (ValueError, ZeroDivisionError):
            continue

        native_cusps = moira_native.calculate_houses_cusps(armc, obl, lat, asc, mc, "K")

        for cusp_idx in range(12):
            diff = abs(py_cusps[cusp_idx] - native_cusps[cusp_idx])
            if diff > 180.0:
                diff = abs(diff - 360.0)
            assert diff < 1e-11, f"Koch Cusp {cusp_idx + 1} divergence at ARMC={armc}, lat={lat}: {diff} deg"


def test_native_regiomontanus_parity_gauntlet() -> None:
    """Validate native Regiomontanus cusps against Python Regiomontanus across 1,000 configurations."""
    random.seed(1002)

    for _ in range(1000):
        armc = random.uniform(0.0, 360.0)
        obl = random.uniform(22.0, 24.5)
        lat = random.uniform(-62.0, 62.0)

        mc = py_mc(armc, obl, lat)
        asc = py_asc(armc, obl, lat)

        try:
            py_cusps = py_regiomontanus(armc, obl, lat)
        except (ValueError, ZeroDivisionError):
            continue

        native_cusps = moira_native.calculate_houses_cusps(armc, obl, lat, asc, mc, "R")

        for cusp_idx in range(12):
            diff = abs(py_cusps[cusp_idx] - native_cusps[cusp_idx])
            if diff > 180.0:
                diff = abs(diff - 360.0)
            assert diff < 1e-11, f"Regiomontanus Cusp {cusp_idx + 1} divergence at ARMC={armc}, lat={lat}: {diff} deg"


def test_native_campanus_parity_gauntlet() -> None:
    """Validate native Campanus cusps against Python Campanus across 1,000 configurations."""
    random.seed(1003)

    for _ in range(1000):
        armc = random.uniform(0.0, 360.0)
        obl = random.uniform(22.0, 24.5)
        lat = random.uniform(-62.0, 62.0)

        mc = py_mc(armc, obl, lat)
        asc = py_asc(armc, obl, lat)

        try:
            py_cusps = py_campanus(armc, obl, lat)
        except (ValueError, ZeroDivisionError):
            continue

        native_cusps = moira_native.calculate_houses_cusps(armc, obl, lat, asc, mc, "C")

        for cusp_idx in range(12):
            diff = abs(py_cusps[cusp_idx] - native_cusps[cusp_idx])
            if diff > 180.0:
                diff = abs(diff - 360.0)
            assert diff < 1e-11, f"Campanus Cusp {cusp_idx + 1} divergence at ARMC={armc}, lat={lat}: {diff} deg"


def test_nutation_caching_parity_and_speed() -> None:
    """Validate that repeated evaluations of nutation hit the cache and produce identical values."""
    from moira.nutation_2000a import nutation_2000a

    jd_tt = 2451545.0
    nutation_2000a.cache_clear()

    res1 = nutation_2000a(jd_tt)
    res2 = nutation_2000a(jd_tt)

    assert res1 == res2
    info = nutation_2000a.cache_info()
    assert info.hits >= 1, f"Expected cache hit, got {info}"

