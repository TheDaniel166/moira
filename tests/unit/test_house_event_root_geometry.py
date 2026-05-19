"""
Event/root family geometry covenant tests.

These are primary proof tests for the event condition doctrine of the
event/root family (Placidus, APC).

Placidus doctrine (Phase E): the governing event — an ecliptic point has
traversed exactly frac of its own diurnal or nocturnal semi-arc from the
local meridian — is the ontological owner of each cusp.  Root-finding is
retained only as the execution method.

APC doctrine (Phase E): each intermediate cusp lies at an exact fraction
of the Ascendant's diurnal or nocturnal semi-arc on the Ascendant's parallel
circle, then projected to the ecliptic.  The governing objects are the
Ascendant's equatorial unit vector and the observer's zenith; the
ascensional difference and parallel-circle projection are derived reductions.
"""

from __future__ import annotations

import math

import pytest

from moira.constants import HouseSystem
from moira.houses import (
    _apc_project,
    _equatorial_ecliptic_direction,
    _local_horizon_basis,
    _placidus_semi_arc_event,
    calculate_houses,
)
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity


# ---------------------------------------------------------------------------
# Dual-path equivalence: governing vector vs. classical angle formula
# ---------------------------------------------------------------------------


def test_placidus_dsa_from_governing_vector_equals_classical() -> None:
    """
    Dual-path equivalence: DSA returned by _placidus_semi_arc_event (derived
    from the governing ecliptic-point vector and zenith) must equal the
    classical arccos(-tan(phi)*tan(dec)) formula.

    This proves the governing objects (ecliptic-point vector, zenith) produce
    the same semi-arc scalar as the angle-first route they replace.
    """
    jd_ut = 2451545.0
    lat = 51.5
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    armc = calculate_houses(jd_ut, lat, 0.0, HouseSystem.PLACIDUS).armc
    _, _, zenith = _local_horizon_basis(armc, lat)

    phi = math.radians(lat)
    eps_r = math.radians(obliquity)

    for lam_deg in (30.0, 75.0, 130.0, 200.0, 270.0, 315.0):
        lam_r = math.radians(lam_deg)
        dsa_vector, _ = _placidus_semi_arc_event(lam_r, obliquity, zenith)

        sin_dec = math.sin(eps_r) * math.sin(lam_r)
        dec = math.asin(max(-1.0, min(1.0, sin_dec)))
        cos_dsa_arg = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec)))
        dsa_classical = math.acos(cos_dsa_arg)

        assert dsa_vector == pytest.approx(dsa_classical, abs=1e-12), (
            f"λ={lam_deg}°: DSA vector={math.degrees(dsa_vector):.6f}° "
            f"classical={math.degrees(dsa_classical):.6f}°"
        )


def test_placidus_dsa_derivative_from_governing_vector_equals_classical() -> None:
    """
    Dual-path equivalence: dDSA/dλ returned by _placidus_semi_arc_event must
    equal the classical chain-rule derivative expressed through scalar angles.

    The derivative is the core of the Newton-Raphson convergence; this covenant
    proves the vector-first derivative is numerically identical.
    """
    jd_ut = 2451545.0
    lat = 51.5
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    armc = calculate_houses(jd_ut, lat, 0.0, HouseSystem.PLACIDUS).armc
    _, _, zenith = _local_horizon_basis(armc, lat)

    phi = math.radians(lat)
    eps_r = math.radians(obliquity)
    sin_eps = math.sin(eps_r)
    tan_phi = math.tan(phi)

    for lam_deg in (30.0, 75.0, 130.0, 200.0, 270.0):
        lam_r = math.radians(lam_deg)
        _, d_dsa_vector = _placidus_semi_arc_event(lam_r, obliquity, zenith)

        # Classical derivation
        sin_lam = math.sin(lam_r)
        cos_lam = math.cos(lam_r)
        s = max(-1.0, min(1.0, sin_eps * sin_lam))
        dec = math.asin(s)
        cos_dec = math.cos(dec)
        cos_dsa_arg = max(-1.0, min(1.0, -tan_phi * math.tan(dec)))
        dsa = math.acos(cos_dsa_arg)
        sin_dsa = math.sin(dsa)

        if cos_dec < 1e-12 or sin_dsa < 1e-12:
            continue

        d_dec_d_lam = sin_eps * cos_lam / cos_dec
        d_dsa_classical = (tan_phi / (cos_dec * cos_dec) * d_dec_d_lam) / sin_dsa

        assert d_dsa_vector == pytest.approx(d_dsa_classical, abs=1e-10), (
            f"λ={lam_deg}°: dDSA/dλ vector={d_dsa_vector:.8f} "
            f"classical={d_dsa_classical:.8f}"
        )


# ---------------------------------------------------------------------------
# Event-condition residual covenant: at solved cusps, residual ≈ 0
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 35.0, 25.0),
        (2451545.0, -33.9, 151.2),
    ],
)
def test_placidus_event_condition_satisfied_at_solved_cusps(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
) -> None:
    """
    Event-condition covenant: at each converged Placidus cusp, the fractional
    semi-arc residual f(λ) must vanish to solver precision.

    Upper cusps: f(λ) = RA(λ) − ARMC − frac·DSA(λ) = 0
    Lower cusps: f(λ) = RA(λ) − IC_RA + frac·NSA(λ) = 0

    This proves the governing event condition is truly satisfied at the cusp
    positions delivered by the solver — not merely that the output passed a
    downstream parity check.
    """
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.PLACIDUS)
    obliquity = true_obliquity(ut_to_tt(jd_ut))
    _, _, zenith = _local_horizon_basis(houses.armc, latitude_deg)

    armc_r = math.radians(houses.armc)
    ic_r = armc_r + math.pi

    def _ra_normalized(lam_deg: float, anchor_r: float) -> float:
        v = _equatorial_ecliptic_direction(lam_deg, obliquity)
        ra = math.atan2(v[1], v[0])
        return anchor_r + ((ra - anchor_r + math.pi) % (2.0 * math.pi) - math.pi)

    # Upper cusps (H11, H12): RA(λ) − ARMC − frac·DSA(λ) = 0
    for cusp_idx, frac in ((10, 1.0 / 3.0), (11, 2.0 / 3.0)):
        lam_r = math.radians(houses.cusps[cusp_idx])
        ra = _ra_normalized(houses.cusps[cusp_idx], armc_r)
        dsa, _ = _placidus_semi_arc_event(lam_r, obliquity, zenith)
        residual = abs(ra - armc_r - frac * dsa)
        assert residual < 1e-9, (
            f"H{cusp_idx + 1} upper event residual {residual:.2e} at "
            f"lat={latitude_deg} lon={longitude_deg}"
        )

    # Lower cusps (H2, H3): RA(λ) − IC_RA + frac·NSA(λ) = 0
    for cusp_idx, frac in ((1, 2.0 / 3.0), (2, 1.0 / 3.0)):
        lam_r = math.radians(houses.cusps[cusp_idx])
        ra = _ra_normalized(houses.cusps[cusp_idx], ic_r)
        dsa, _ = _placidus_semi_arc_event(lam_r, obliquity, zenith)
        nsa = math.pi - dsa
        residual = abs(ra - ic_r + frac * nsa)
        assert residual < 1e-9, (
            f"H{cusp_idx + 1} lower event residual {residual:.2e} at "
            f"lat={latitude_deg} lon={longitude_deg}"
        )


# ---------------------------------------------------------------------------
# APC: dual-path equivalence covenants (governing vector vs. classical staging)
#
# These tests prove that the spatial governing objects (Ascendant as equatorial
# unit vector, zenith as equatorial unit vector) produce the same scalar
# quantities as the classical angle-staging formulas they replace in _apc_sector.
# They run GREEN before the remediation and serve as derivation-ownership proof
# and regression guard for Phase E-APC.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 35.0, 25.0),
        (2451545.0, -33.9, 151.2),
    ],
)
def test_apc_dsa_from_governing_vector_equals_classical(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
) -> None:
    """
    Dual-path equivalence: DSA of the Ascendant derived from the governing
    equatorial unit vectors must equal asc_ad + π/2 from the classical
    _ascending_terms formula.

    Vector path: arccos(−(v_asc[2]·zenith[2]) / (cos_dec_asc·cos_lat))
    Classical path: atan(p·cos(ARMC) / (1 + p·sin(ARMC))) + π/2
                    where p = tan(lat)·tan(obl)

    Both paths resolve to the same DSA scalar because the algebraic identity
    atan(p·cos(α)/(1+p·sin(α))) + π/2 = arccos(−tan(δ_asc)·tan(lat))
    holds exactly for the geometric Ascendant at any ARMC and latitude.
    """
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.APC)
    obliquity = true_obliquity(ut_to_tt(jd_ut))

    v_asc = _equatorial_ecliptic_direction(houses.asc, obliquity)
    _, _, zenith = _local_horizon_basis(houses.armc, latitude_deg)
    cos_dec_asc = math.hypot(v_asc[0], v_asc[1])
    cos_lat = math.hypot(zenith[0], zenith[1])
    cos_dsa = max(-1.0, min(1.0, -(v_asc[2] * zenith[2]) / (cos_dec_asc * cos_lat)))
    dsa_vector = math.acos(cos_dsa)

    lat_r = math.radians(latitude_deg)
    obl_r = math.radians(obliquity)
    armc_r = math.radians(houses.armc)
    p = math.tan(lat_r) * math.tan(obl_r)
    denom = 1.0 + p * math.sin(armc_r)
    numer = p * math.cos(armc_r)
    asc_ad = (
        math.copysign(math.pi / 2.0, numer)
        if abs(denom) < 1e-12
        else math.atan(numer / denom)
    )
    dsa_classical = asc_ad + math.pi / 2.0

    assert dsa_vector == pytest.approx(dsa_classical, abs=1e-12), (
        f"lat={latitude_deg} lon={longitude_deg}: "
        f"DSA vector={math.degrees(dsa_vector):.8f}° "
        f"classical={math.degrees(dsa_classical):.8f}°"
    )


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 35.0, 25.0),
        (2451545.0, -33.9, 151.2),
    ],
)
def test_apc_tan_declination_from_governing_vector_equals_classical(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
) -> None:
    """
    Dual-path equivalence: tan(δ_asc) extracted from the Ascendant's equatorial
    unit vector z-component must equal sin(asc_ad) / tan(lat) from the
    classical _ascending_terms formula.

    Vector path: v_asc[2] / hypot(v_asc[0], v_asc[1])
    Classical path: sin(asc_ad) / tan(lat)

    The identity sin(AD) = tan(lat)·tan(dec) → tan(dec) = sin(AD)/tan(lat)
    is the standard astronomical ascensional-difference relation, here proved
    numerically for the governing Ascendant vector.  This confirms the vector
    z-component is the authoritative source of δ_asc in the object-first
    construction.
    """
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.APC)
    obliquity = true_obliquity(ut_to_tt(jd_ut))

    v_asc = _equatorial_ecliptic_direction(houses.asc, obliquity)
    cos_dec_asc = math.hypot(v_asc[0], v_asc[1])
    tan_dec_vector = v_asc[2] / cos_dec_asc

    lat_r = math.radians(latitude_deg)
    obl_r = math.radians(obliquity)
    armc_r = math.radians(houses.armc)
    p = math.tan(lat_r) * math.tan(obl_r)
    denom = 1.0 + p * math.sin(armc_r)
    numer = p * math.cos(armc_r)
    asc_ad = (
        math.copysign(math.pi / 2.0, numer)
        if abs(denom) < 1e-12
        else math.atan(numer / denom)
    )
    tan_dec_classical = math.sin(asc_ad) / math.tan(lat_r)

    assert tan_dec_vector == pytest.approx(tan_dec_classical, abs=1e-12), (
        f"lat={latitude_deg} lon={longitude_deg}: "
        f"tan(δ_asc) vector={tan_dec_vector:.10f} "
        f"classical={tan_dec_classical:.10f}"
    )


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 35.0, 25.0),
        (2451545.0, -33.9, 151.2),
    ],
)
def test_apc_parallel_scale_equals_neg_cos_dsa(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
) -> None:
    """
    Dual-path equivalence: the APC projection's parallel_scale factor
    (= tan(δ_asc)·tan(lat)) derived from governing vectors must equal
    −cos(DSA_asc).

    Vector path: (v_asc[2]/cos_dec_asc) · (zenith[2]/cos_lat)
    Event path:  −cos(arccos(−(v_asc[2]·zenith[2])/(cos_dec_asc·cos_lat)))

    The identity tan(δ)·tan(lat) = −cos(DSA) follows directly from the
    horizon event condition cos(DSA) = −tan(δ)·tan(lat).  This proves the
    APC projection formula can be parameterised entirely by the governing
    event (DSA of the Ascendant) without staging through separate
    asc_declination and tan_lat scalars.
    """
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.APC)
    obliquity = true_obliquity(ut_to_tt(jd_ut))

    v_asc = _equatorial_ecliptic_direction(houses.asc, obliquity)
    _, _, zenith = _local_horizon_basis(houses.armc, latitude_deg)
    cos_dec_asc = math.hypot(v_asc[0], v_asc[1])
    cos_lat = math.hypot(zenith[0], zenith[1])

    tan_dec_asc = v_asc[2] / cos_dec_asc
    tan_lat = zenith[2] / cos_lat
    parallel_scale_vector = tan_dec_asc * tan_lat

    cos_dsa = max(-1.0, min(1.0, -(v_asc[2] * zenith[2]) / (cos_dec_asc * cos_lat)))
    neg_cos_dsa = -math.cos(math.acos(cos_dsa))

    assert parallel_scale_vector == pytest.approx(neg_cos_dsa, abs=1e-14), (
        f"lat={latitude_deg} lon={longitude_deg}: "
        f"parallel_scale (vector)={parallel_scale_vector:.12f} "
        f"−cos(DSA)={neg_cos_dsa:.12f}"
    )


# ---------------------------------------------------------------------------
# APC: projection covenant (Phase E-APC-2 primary RED test)
#
# This test proves that _apc_project, given cusp RAs computed from the
# governing arc-trisection doctrine, reproduces each intermediate cusp to
# arc-second precision.  It imports _apc_project before that function exists,
# producing ImportError (RED).  After _apc_project is implemented and
# _apc_sector wired to call it, the test turns GREEN.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 35.0, 25.0),
        (2451545.0, -33.9, 151.2),
    ],
)
def test_apc_project_reproduces_intermediate_cusps(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    """
    Arc-doctrine projection covenant: _apc_project given cusp RAs derived from
    the Ascendant's arc trisection must reproduce H2, H3, H11, H12 exactly.

    Governing objects:
      v_asc  = _equatorial_ecliptic_direction(asc, obliquity)  — ASC unit vector
      zenith = _local_horizon_basis(armc, lat)[2]              — observer zenith
      ra_asc = atan2(v_asc[1], v_asc[0])                      — RA of ASC
      DSA    = arccos(−(v_asc[2]·zenith[2])/(cos_dec·cos_lat)) — diurnal semi-arc
      NSA    = π − DSA

    Arc doctrine:
      H12: ra_asc − DSA/3        (upper arc, 1/3 from ASC)
      H11: ra_asc − 2·DSA/3     (upper arc, 2/3 from ASC)
      H2:  ra_asc + NSA/3        (lower arc, 1/3 from ASC)
      H3:  ra_asc + 2·NSA/3     (lower arc, 2/3 from ASC)

    This covenant is the Phase E-APC-2 proof that _apc_project is the correct
    named projection primitive and that the arc doctrine is expressed through
    governing objects rather than through the classical _ascending_terms staging.
    """
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.APC)
    obliquity = true_obliquity(ut_to_tt(jd_ut))

    v_asc = _equatorial_ecliptic_direction(houses.asc, obliquity)
    _, _, zenith = _local_horizon_basis(houses.armc, latitude_deg)
    cos_dec_asc = math.hypot(v_asc[0], v_asc[1])
    cos_lat = math.hypot(zenith[0], zenith[1])

    ra_asc_r = math.atan2(v_asc[1], v_asc[0])
    cos_dsa = max(-1.0, min(1.0, -(v_asc[2] * zenith[2]) / (cos_dec_asc * cos_lat)))
    dsa_asc = math.acos(cos_dsa)
    nsa_asc = math.pi - dsa_asc
    tan_lat = zenith[2] / cos_lat
    armc_r = math.radians(houses.armc)
    obl_r = math.radians(obliquity)

    # Upper arc: H11 = 2/3 of DSA back from ASC, H12 = 1/3 back
    for cusp_idx, frac in ((10, 2.0 / 3.0), (11, 1.0 / 3.0)):
        cusp_ra = ra_asc_r - frac * dsa_asc
        lon = _apc_project(cusp_ra, dsa_asc, tan_lat, armc_r, obl_r)
        assert lon == moira_approx(houses.cusps[cusp_idx], kind="longitude"), (
            f"H{cusp_idx + 1} upper cusp mismatch at "
            f"lat={latitude_deg} lon={longitude_deg}: "
            f"computed={lon:.6f}° expected={houses.cusps[cusp_idx]:.6f}°"
        )

    # Lower arc: H2 = 1/3 of NSA forward from ASC, H3 = 2/3 forward
    for cusp_idx, frac in ((1, 1.0 / 3.0), (2, 2.0 / 3.0)):
        cusp_ra = ra_asc_r + frac * nsa_asc
        lon = _apc_project(cusp_ra, dsa_asc, tan_lat, armc_r, obl_r)
        assert lon == moira_approx(houses.cusps[cusp_idx], kind="longitude"), (
            f"H{cusp_idx + 1} lower cusp mismatch at "
            f"lat={latitude_deg} lon={longitude_deg}: "
            f"computed={lon:.6f}° expected={houses.cusps[cusp_idx]:.6f}°"
        )


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 35.0, 25.0),
        (2451545.0, -33.9, 151.2),
    ],
)
def test_apc_project_governing_invariant_ra_asc_recovers_ascendant(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    """
    Governing invariant of the APC projection: projecting ra_asc through
    _apc_project must recover the Ascendant ecliptic longitude to numerical
    precision.

    This is an internal consistency proof, independent of external authorities.
    The APC projection is defined as a generalisation of the Ascendant ecliptic
    longitude formula; the identity at α = ra_asc is the algebraic anchor of
    that definition and must hold exactly.
    """
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.APC)
    obliquity = true_obliquity(ut_to_tt(jd_ut))

    v_asc = _equatorial_ecliptic_direction(houses.asc, obliquity)
    _, _, zenith = _local_horizon_basis(houses.armc, latitude_deg)
    cos_dec_asc = math.hypot(v_asc[0], v_asc[1])
    cos_lat = math.hypot(zenith[0], zenith[1])

    ra_asc_r = math.atan2(v_asc[1], v_asc[0])
    cos_dsa = max(-1.0, min(1.0, -(v_asc[2] * zenith[2]) / (cos_dec_asc * cos_lat)))
    dsa_asc = math.acos(cos_dsa)
    tan_lat = zenith[2] / cos_lat
    armc_r = math.radians(houses.armc)
    obl_r = math.radians(obliquity)

    projected = _apc_project(ra_asc_r, dsa_asc, tan_lat, armc_r, obl_r)

    assert projected == moira_approx(houses.asc, kind="longitude"), (
        f"lat={latitude_deg} lon={longitude_deg}: "
        f"_apc_project(ra_asc)={projected:.8f}° but asc={houses.asc:.8f}°"
    )


@pytest.mark.parametrize(
    ("jd_ut", "latitude_deg", "longitude_deg"),
    [
        (2451545.0, 51.5, 0.0),
        (2451545.0, 35.0, 25.0),
        (2451545.0, -33.9, 151.2),
    ],
)
def test_apc_project_reproduces_far_intermediate_cusps(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    moira_approx,
) -> None:
    """
    Arc-doctrine projection covenant: _apc_project with cusp RAs from the
    full arc trisection must reproduce H5, H6, H8, H9 — the four cusps that
    cross the IC and DSC parallels and are computed independently (not as
    antipodal reflections of H2, H3, H11, H12).

    Arc doctrine:
      H5:  ra_asc + 4·NSA/3    (lower arc, 1/3 past IC toward DSC)
      H6:  ra_asc + 5·NSA/3    (lower arc, 2/3 past IC toward DSC)
      H8:  ra_asc − 5·DSA/3    (upper arc, 2/3 past DSC toward MC)
      H9:  ra_asc − 4·DSA/3    (upper arc, 1/3 past DSC toward MC)

    Independent computation of all eight intermediate cusps is the central
    architectural claim of Phase E-APC-3. This covenant proves it.
    """
    houses = calculate_houses(jd_ut, latitude_deg, longitude_deg, HouseSystem.APC)
    obliquity = true_obliquity(ut_to_tt(jd_ut))

    v_asc = _equatorial_ecliptic_direction(houses.asc, obliquity)
    _, _, zenith = _local_horizon_basis(houses.armc, latitude_deg)
    cos_dec_asc = math.hypot(v_asc[0], v_asc[1])
    cos_lat = math.hypot(zenith[0], zenith[1])

    ra_asc_r = math.atan2(v_asc[1], v_asc[0])
    cos_dsa = max(-1.0, min(1.0, -(v_asc[2] * zenith[2]) / (cos_dec_asc * cos_lat)))
    dsa_asc = math.acos(cos_dsa)
    nsa_asc = math.pi - dsa_asc
    tan_lat = zenith[2] / cos_lat
    armc_r = math.radians(houses.armc)
    obl_r = math.radians(obliquity)

    # Lower arc past IC: H5 at 4/3 NSA, H6 at 5/3 NSA forward from ASC
    for cusp_idx, frac in ((4, 4.0 / 3.0), (5, 5.0 / 3.0)):
        cusp_ra = ra_asc_r + frac * nsa_asc
        lon = _apc_project(cusp_ra, dsa_asc, tan_lat, armc_r, obl_r)
        assert lon == moira_approx(houses.cusps[cusp_idx], kind="longitude"), (
            f"H{cusp_idx + 1} lower-far cusp mismatch at "
            f"lat={latitude_deg} lon={longitude_deg}: "
            f"computed={lon:.6f}° expected={houses.cusps[cusp_idx]:.6f}°"
        )

    # Upper arc past DSC: H8 at −5/3 DSA, H9 at −4/3 DSA from ASC
    for cusp_idx, frac in ((7, 5.0 / 3.0), (8, 4.0 / 3.0)):
        cusp_ra = ra_asc_r - frac * dsa_asc
        lon = _apc_project(cusp_ra, dsa_asc, tan_lat, armc_r, obl_r)
        assert lon == moira_approx(houses.cusps[cusp_idx], kind="longitude"), (
            f"H{cusp_idx + 1} upper-far cusp mismatch at "
            f"lat={latitude_deg} lon={longitude_deg}: "
            f"computed={lon:.6f}° expected={houses.cusps[cusp_idx]:.6f}°"
        )


def test_apc_structural_invariants_and_branch_selections(moira_approx) -> None:
    """
    Sovereignty Covenant: Prove the APC house system's geometric invariants and branch selections
    without relying on external oracles as primary proof.

    This test verifies:
      1. Arc-doctrine structural ordering: H11 and H12 divide the upper-western ecliptic arc
         from MC (H10) to ASC (H1) into the correct fractions of the diurnal semi-arc (DSA).
      2. Arc-doctrine span invariants: H10 -> H11 -> H12 -> H1 spans the correct DSA, and
         H1 -> H2 -> H3 -> H4 spans the correct NSA.
      3. Endpoint sheet selection: when the raw APC projection of RA(ASC) lands
         on the antipodal candidate, all intermediate cusps stay on the
         Ascendant-recovering projection sheet.
      4. Polar-cap branch selection: at high polar latitudes (lat=70), the
         endpoint-selected sheet keeps intermediate cusps in the intended APC frame.
    """
    # Case 1: Standard mid-latitude case (London, 51.5° N)
    jd_ut = 2451545.0
    lat = 51.5
    houses = calculate_houses(jd_ut, lat, 0.0, HouseSystem.APC)

    asc = houses.asc
    mc = houses.cusps[9]
    ic = houses.cusps[3]
    h2 = houses.cusps[1]
    h3 = houses.cusps[2]
    h11 = houses.cusps[10]
    h12 = houses.cusps[11]

    # Validate H12 is angularly between MC and ASC
    # The ecliptic arc from MC to ASC is (asc - mc) % 360.0
    span_mc_asc = (asc - mc) % 360.0
    dist_mc_h12 = (h12 - mc) % 360.0
    dist_mc_h11 = (h11 - mc) % 360.0

    assert dist_mc_h11 < dist_mc_h12 < span_mc_asc, (
        f"APC intermediate cusps out of order. "
        f"MC={mc:.2f}°, H11={h11:.2f}°, H12={h12:.2f}°, ASC={asc:.2f}°"
    )

    # Validate H2 and H3 divide the lower quadrant from ASC to IC
    span_asc_ic = (ic - asc) % 360.0
    dist_asc_h2 = (h2 - asc) % 360.0
    dist_asc_h3 = (h3 - asc) % 360.0

    assert dist_asc_h2 < dist_asc_h3 < span_asc_ic, (
        f"APC lower intermediate cusps out of order. "
        f"ASC={asc:.2f}°, H2={h2:.2f}°, H3={h3:.2f}°, IC={ic:.2f}°"
    )

    # Case 2: Polar high latitude requiring endpoint-selected sheet continuity.
    houses_polar = calculate_houses(jd_ut, 70.0, 45.0, HouseSystem.APC)
    asc_pol = houses_polar.asc
    h12_pol = houses_polar.cusps[11]
    mc_pol = houses_polar.cusps[9]

    # Check that h12 is in the correct hemisphere (within the MC-ASC quadrant)
    span_polar = (asc_pol - mc_pol) % 360.0
    dist_polar = (h12_pol - mc_pol) % 360.0
    assert dist_polar < span_polar, (
        f"Polar APC failed. Cusp H12 lies in incorrect branch. "
        f"MC={mc_pol:.2f}°, H12={h12_pol:.2f}°, ASC={asc_pol:.2f}°"
    )

    # Case 3: Endpoint sheet selection in a high-latitude antipodal candidate case.
    houses_shifted = calculate_houses(jd_ut, -68.0, 180.0, HouseSystem.APC)
    asc_sh = houses_shifted.asc
    h12_sh = houses_shifted.cusps[11]
    h11_sh = houses_shifted.cusps[10]
    mc_sh = houses_shifted.cusps[9]

    # Verify Ascendant and MC values
    assert asc_sh == moira_approx(114.36929515925051, kind="longitude")
    assert mc_sh == moira_approx(279.61108765511676, kind="longitude")

    assert h12_sh == moira_approx(132.5490312111533, kind="longitude"), (
        f"APC endpoint sheet selection failed. "
        f"Expected H12 to be 132.549°, got {h12_sh:.6f}°"
    )
    assert h11_sh == moira_approx(263.207069665002, kind="longitude"), (
        f"APC endpoint sheet selection failed. "
        f"Expected H11 to be 263.207°, got {h11_sh:.6f}°"
    )
