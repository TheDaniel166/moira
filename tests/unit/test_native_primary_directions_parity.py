from __future__ import annotations

import math
import random
import pytest

from moira import moira_native
from moira.primary_directions import SpeculumEntry
from moira.primary_directions.geometry import (
    compute_primary_direction_arcs,
    compute_primary_direction_arc,
    _shared_campanus_regio_sin_zenith_distance,
    _shared_campanus_regio_pole,
    _under_pole_w,
    _under_pole_arc,
    _topocentric_pole,
)
from moira.primary_directions.methods import PrimaryDirectionMethod
from moira.primary_directions.spaces import PrimaryDirectionSpace
from moira.primary_directions.latitudes import PrimaryDirectionLatitudeDoctrine
import moira.primary_directions.geometry as geom_module


def test_native_primary_directions_presence() -> None:
    """Verify that all native under-pole symbols are exported and callable."""
    assert hasattr(moira_native, "campanus_regio_sin_zenith_distance")
    assert hasattr(moira_native, "regiomontanus_pole_height")
    assert hasattr(moira_native, "topocentric_pole_height")
    assert hasattr(moira_native, "under_pole_w")
    assert hasattr(moira_native, "under_pole_arc_native")
    assert hasattr(moira_native, "regiomontanus_under_pole_arc")
    assert hasattr(moira_native, "topocentric_under_pole_arc")
    assert hasattr(moira_native, "compute_under_pole_pair_arcs")
    assert hasattr(moira_native, "compute_under_pole_arcs_matrix")
    assert hasattr(moira_native, "NativeSpeculumPoint")


def test_native_zenith_distance_and_pole_height_parity() -> None:
    """Sub-microarcsecond parity for Regiomontanus / Campanus pole height."""
    random.seed(1337)
    for _ in range(500):
        geo_lat = random.uniform(-65.0, 65.0)
        dec = random.uniform(-25.0, 25.0)
        ha = random.uniform(-170.0, 170.0)

        # Invariant: Speculum-like dummy point
        class DummyEntry:
            pass
        pt = DummyEntry()
        pt.dec = dec
        pt.ha = ha

        # Python calculation
        sin_zd_py = _shared_campanus_regio_sin_zenith_distance(pt, geo_lat=geo_lat)
        pole_py = _shared_campanus_regio_pole(pt, geo_lat=geo_lat)

        # Native calculation
        sin_zd_nat = moira_native.campanus_regio_sin_zenith_distance(dec, ha, geo_lat)
        pole_nat = moira_native.regiomontanus_pole_height(dec, ha, geo_lat)

        assert abs(sin_zd_py - sin_zd_nat) < 1e-13, f"sin(ZD) divergence: {abs(sin_zd_py - sin_zd_nat)}"
        assert abs(pole_py - pole_nat) < 1e-12, f"Pole height divergence: {abs(pole_py - pole_nat)}"


def test_native_topocentric_pole_height_parity() -> None:
    """Sub-microarcsecond parity for Topocentric pole height."""
    random.seed(2026)
    for _ in range(500):
        geo_lat = random.uniform(-60.0, 60.0)
        dsa = random.uniform(60.0, 120.0)
        nsa = 180.0 - dsa
        upper = random.choice([True, False])
        sa = dsa if upper else nsa
        ha = random.uniform(-sa * 0.95, sa * 0.95)

        class DummyEntry:
            pass
        pt = DummyEntry()
        pt.ha = ha
        pt.dsa = dsa
        pt.nsa = nsa
        pt.upper = upper

        # Force pure python by temporarily unsetting native in geom_module
        orig_native = geom_module._moira_native
        try:
            geom_module._moira_native = None
            pole_py = _topocentric_pole(pt, geo_lat=geo_lat)
        finally:
            geom_module._moira_native = orig_native

        pole_nat = moira_native.topocentric_pole_height(ha, dsa, nsa, upper, geo_lat)
        assert abs(pole_py - pole_nat) < 1e-12, f"Topocentric pole divergence: {abs(pole_py - pole_nat)}"


def test_native_under_pole_w_parity() -> None:
    """Sub-microarcsecond parity for under-pole oblique coordinate W."""
    random.seed(42)
    for _ in range(500):
        ra = random.uniform(0.0, 360.0)
        dec = random.uniform(-23.5, 23.5)
        pole = random.uniform(0.0, 55.0)
        eastern = random.choice([True, False])

        class DummyEntry:
            pass
        pt = DummyEntry()
        pt.ra = ra
        pt.dec = dec

        orig_native = geom_module._moira_native
        try:
            geom_module._moira_native = None
            w_py = _under_pole_w(pt, pole, eastern=eastern)
        finally:
            geom_module._moira_native = orig_native

        w_nat = moira_native.under_pole_w(ra, dec, pole, eastern)
        assert abs(w_py - w_nat) < 1e-12, f"W divergence: {abs(w_py - w_nat)}"


def test_native_under_pole_full_pair_arcs_parity() -> None:
    """Parity across full compute_primary_direction_arcs gauntlet between Python and native."""
    random.seed(777)
    obliquity = 23.44

    for _ in range(200):
        geo_lat = random.uniform(-55.0, 55.0)
        armc = random.uniform(0.0, 360.0)

        sig = SpeculumEntry.build(
            "Significator",
            random.uniform(0.0, 360.0),
            random.uniform(-5.0, 5.0),
            armc,
            obliquity,
            geo_lat,
        )
        prom = SpeculumEntry.build(
            "Promissor",
            random.uniform(0.0, 360.0),
            random.uniform(-5.0, 5.0),
            armc,
            obliquity,
            geo_lat,
        )

        for method in (
            PrimaryDirectionMethod.REGIOMONTANUS,
            PrimaryDirectionMethod.MORINUS,
            PrimaryDirectionMethod.CAMPANUS,
            PrimaryDirectionMethod.TOPOCENTRIC,
        ):
            # 1. Native execution
            nat_dir, nat_conv = compute_primary_direction_arcs(
                method,
                sig,
                prom,
                space=PrimaryDirectionSpace.IN_ZODIACO,
                latitude_doctrine=PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED,
                geo_lat=geo_lat,
                armc=armc,
                oa_asc=(armc + 90.0) % 360.0,
            )

            # 2. Pure Python fallback execution (monkeypatched)
            orig_native = geom_module._moira_native
            try:
                geom_module._moira_native = None
                py_dir, py_conv = compute_primary_direction_arcs(
                    method,
                    sig,
                    prom,
                    space=PrimaryDirectionSpace.IN_ZODIACO,
                    latitude_doctrine=PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED,
                    geo_lat=geo_lat,
                    armc=armc,
                    oa_asc=(armc + 90.0) % 360.0,
                )
            finally:
                geom_module._moira_native = orig_native

            diff_dir = abs(nat_dir - py_dir)
            diff_conv = abs(nat_conv - py_conv)
            assert diff_dir < 1e-12, f"Method {method.value} direct arc diff: {diff_dir}"
            assert diff_conv < 1e-12, f"Method {method.value} converse arc diff: {diff_conv}"


def test_morin_book_22_converse_role_exchange_asymmetry() -> None:
    """Morin Book 22 Chapter 7: converse is role-exchange, NOT simple negation."""
    geo_lat = 51.5
    armc = 45.0
    obliquity = 23.44

    mars = SpeculumEntry.build("Mars", 185.0, 1.5, armc, obliquity, geo_lat)
    jupiter = SpeculumEntry.build("Jupiter", 210.0, -1.0, armc, obliquity, geo_lat)

    # Compute Mars -> Jupiter and Jupiter -> Mars
    arcs_mars_jup = moira_native.compute_under_pole_pair_arcs(mars, jupiter, geo_lat, "R")
    arcs_jup_mars = moira_native.compute_under_pole_pair_arcs(jupiter, mars, geo_lat, "R")

    dir_mars_jup, conv_mars_jup = arcs_mars_jup
    dir_jup_mars, conv_jup_mars = arcs_jup_mars

    # 1. Asymmetry: converse is not -direct
    neg_dir_mod = (360.0 - dir_mars_jup) % 360.0
    assert abs(conv_mars_jup - neg_dir_mod) > 1e-4, "Under-pole direct and converse must not be symmetric negations"

    # 2. Morin's Theorem: converse(A -> B) == direct(B -> A)
    assert abs(conv_mars_jup - dir_jup_mars) < 1e-12, "Morin role-exchange law violated"
    assert abs(conv_jup_mars - dir_mars_jup) < 1e-12, "Morin role-exchange law violated"


def test_continuous_vector_zenith_distance_at_quadrature() -> None:
    """Meridian distance MD = 90 deg: vector/plane invariant remains smooth."""
    geo_lat = 45.0
    dec = 15.0
    ha = 90.0  # MD = 90 deg

    # Classical tan(MD) diverges to infinity, but native vector invariant is exact
    sin_zd = moira_native.campanus_regio_sin_zenith_distance(dec, ha, geo_lat)
    assert math.isfinite(sin_zd)
    assert 0.0 <= sin_zd <= 1.0

    pole = moira_native.regiomontanus_pole_height(dec, ha, geo_lat)
    assert math.isfinite(pole)
    assert 0.0 <= pole <= geo_lat + 1e-9


def test_culmination_and_horizon_pole_invariants() -> None:
    """Points at culmination have pole = 0; points on horizon have pole = geo_lat."""
    geo_lat = 52.0
    dec = 10.0

    # Culmination: HA = 0
    pole_culm = moira_native.regiomontanus_pole_height(dec, 0.0, geo_lat)
    assert abs(pole_culm) < 1e-12, f"Culmination pole must be 0, got {pole_culm}"

    # Topocentric at culmination: HA = 0
    pole_topo_culm = moira_native.topocentric_pole_height(0.0, 90.0, 90.0, True, geo_lat)
    assert abs(pole_topo_culm) < 1e-12, f"Topocentric culmination pole must be 0, got {pole_topo_culm}"


def test_batched_matrix_computation_and_parallelism() -> None:
    """compute_under_pole_arcs_matrix computes all pairs with complete reciprocity."""
    geo_lat = 48.85
    armc = 120.0
    obliquity = 23.44

    planets = [
        ("Sun", 30.0, 0.0),
        ("Moon", 65.0, 4.5),
        ("Mercury", 45.0, -1.2),
        ("Venus", 75.0, 2.1),
        ("Mars", 135.0, 1.1),
        ("Jupiter", 180.0, -0.5),
        ("Saturn", 220.0, 1.8),
    ]
    points = [SpeculumEntry.build(name, lon, lat, armc, obliquity, geo_lat) for name, lon, lat in planets]

    matrix = moira_native.compute_under_pole_arcs_matrix(points, geo_lat, "R")
    n = len(points)
    assert len(matrix) == n
    assert all(len(row) == n for row in matrix)

    for i in range(n):
        # Diagonal is identity (0, 0)
        assert matrix[i][i] == (0.0, 0.0)

        for j in range(n):
            if i == j:
                continue
            dir_ij, conv_ij = matrix[i][j]
            dir_ji, conv_ji = matrix[j][i]

            # Role reciprocity: converse of i->j equals direct of j->i
            assert abs(conv_ij - dir_ji) < 1e-12
            assert abs(conv_ji - dir_ij) < 1e-12

            # Single-pair parity
            single_dir, single_conv = moira_native.compute_under_pole_pair_arcs(points[i], points[j], geo_lat, "R")
            assert abs(dir_ij - single_dir) < 1e-12
            assert abs(conv_ij - single_conv) < 1e-12


def test_singularity_and_error_handling() -> None:
    """Circumpolar or invalid domain cases raise clean typed ValueError."""
    # 1. Geographic latitude out of bounds
    with pytest.raises(ValueError, match="Campanus-Regiomontanus geometry requires geographic latitude in"):
        moira_native.regiomontanus_pole_height(10.0, 30.0, 90.0)

    with pytest.raises(ValueError, match="Campanus-Regiomontanus geometry requires geographic latitude in"):
        moira_native.regiomontanus_pole_height(10.0, 30.0, -90.0)

    # 2. Non-finite equatorial coordinates
    with pytest.raises(ValueError):
        moira_native.regiomontanus_pole_height(float("nan"), 30.0, 45.0)

    with pytest.raises(ValueError):
        moira_native.under_pole_w(float("inf"), 10.0, 30.0, True)

    # 3. No real spherical solution (circumpolar body under high pole)
    # tan(dec) * tan(pole) > 1.0
    with pytest.raises(ValueError, match="no real spherical solution"):
        moira_native.under_pole_w(100.0, 70.0, 60.0, True)  # tan(70) * tan(60) = 2.747 * 1.732 = 4.758 > 1


def test_native_placidian_presence() -> None:
    """Verify that all native Placidian mundane symbols are exported and callable."""
    assert hasattr(moira_native, "placidian_required_ha")
    assert hasattr(moira_native, "placidian_mundane_arc")
    assert hasattr(moira_native, "compute_placidian_pair_arcs")
    assert hasattr(moira_native, "compute_placidian_arcs_matrix")


def test_native_placidian_parity_across_quadrants() -> None:
    """Verify sub-microarcsecond numerical parity between C++ and Python Placidian solvers."""
    from moira.primary_directions.geometry import _required_ha

    random.seed(42)
    for _ in range(500):
        f = random.uniform(-2.0, 2.0)
        dsa = random.uniform(40.0, 140.0)
        nsa = 180.0 - dsa
        prom_ha = random.uniform(-180.0, 180.0)

        # Python
        ha_py = _required_ha(f, dsa, nsa)
        arc_py = (ha_py - prom_ha) % 360.0

        # Native C++
        ha_nat = moira_native.placidian_required_ha(f, dsa, nsa)
        arc_nat = moira_native.placidian_mundane_arc(f, prom_ha, dsa, nsa)

        assert abs(ha_py - ha_nat) < 1e-12, f"required_ha parity failure: py={ha_py}, nat={ha_nat}"
        assert abs(arc_py - arc_nat) < 1e-12, f"mundane_arc parity failure: py={arc_py}, nat={arc_nat}"


def test_native_placidian_matrix_and_converse_modes() -> None:
    """Verify batched Placidian matrix, OpenMP parallelism, and converse doctrines."""
    pts = []
    for i in range(12):
        dsa = 70.0 + i * 3.0
        nsa = 180.0 - dsa
        ha = -150.0 + i * 25.0
        f = (ha / dsa) if abs(ha) <= dsa else (1.0 + (ha - dsa) / nsa if ha > 0 else -1.0 - (-ha - dsa) / nsa)
        pts.append(
            moira_native.NativeSpeculumPoint(
                f"Pt_{i}",
                i * 30.0, 0.0, i * 30.0, 0.0,
                ha, dsa, nsa,
                abs(ha) <= dsa,
                f,
                ha < 0.0,
            )
        )

    # 1. Traditional converse matrix
    mat_trad = moira_native.compute_placidian_arcs_matrix(pts, "T")
    n = len(pts)
    assert len(mat_trad) == n
    assert all(len(row) == n for row in mat_trad)

    for i in range(n):
        assert mat_trad[i][i] == (0.0, 0.0)
        for j in range(n):
            if i == j:
                continue
            dir_ij, conv_ij = mat_trad[i][j]
            dir_ji, conv_ji = mat_trad[j][i]
            # Role exchange reciprocity
            assert abs(conv_ij - dir_ji) < 1e-12

            # Single-pair parity
            single_dir, single_conv = moira_native.compute_placidian_pair_arcs(pts[i], pts[j], "T")
            assert abs(dir_ij - single_dir) < 1e-12
            assert abs(conv_ij - single_conv) < 1e-12

    # 2. Neo-converse matrix
    mat_neo = moira_native.compute_placidian_arcs_matrix(pts, "N")
    for i in range(n):
        assert mat_neo[i][i] == (0.0, 0.0)
        for j in range(n):
            if i == j:
                continue
            dir_ij, conv_ij = mat_neo[i][j]
            # Circle complement invariant: dir + neo_conv == 360
            assert math.isclose((dir_ij + conv_ij) % 360.0, 0.0, abs_tol=1e-12) or math.isclose((dir_ij + conv_ij) % 360.0, 360.0, abs_tol=1e-12)

            single_dir, single_conv = moira_native.compute_placidian_pair_arcs(pts[i], pts[j], "N")
            assert abs(dir_ij - single_dir) < 1e-12
            assert abs(conv_ij - single_conv) < 1e-12

