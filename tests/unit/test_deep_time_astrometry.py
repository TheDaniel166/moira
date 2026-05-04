import math
import pytest
import erfa

from moira.stars import _SovereignStarRecord, _propagate_icrs_vector
from moira.julian import julian_day

_J2000 = 2451545.0

# (ra, dec, pmra_mas_yr, pmdec_mas_yr, parallax_mas, rv_km_s)
# High proper motion stars
_TEST_STARS = {
    "Barnard's Star": (269.4520752, +4.6933909, -798.58, 10328.12, 546.98, -110.51),
    "Kapteyn's Star": (77.9190989, -45.0184083, 6505.74, -5731.39, 255.27, +245.5),
    "Groombridge 1830": (178.2435773, +37.7186835, 4003.54, -5814.73, 109.22, -98.0),
    "61 Cygni A": (316.7335607, +38.7494481, 4165.41, 3270.81, 285.89, -65.6),
}

def _erfa_pmpx_vector(ra_deg, dec_deg, pmra_mas_yr, pmdec_mas_yr, parallax_mas, rv_km_s, dt_years):
    """
    Use ERFA to propagate the star's position.
    Since Moira currently ignores radial velocity, we set rv=0 for comparison.
    """
    ra_rad = math.radians(ra_deg)
    dec_rad = math.radians(dec_deg)
    
    # ERFA starpm takes pmr, pmd in radians/year
    # But pmra_mas_yr in Gaia is pm_ra * cos(dec).
    # ERFA expects pmr = d(ra)/dt without the cos(dec) factor.
    # Actually, let's just use erfa.starpv or erfa.pmsafe.
    
    # pmra_mas_yr is already mu_alpha * cos(dec)
    # So d(ra)/dt = pmra_mas_yr / cos(dec)
    pmra_rad_yr = (pmra_mas_yr / 1000.0 / 3600.0) * (math.pi / 180.0) / math.cos(dec_rad)
    pmdec_rad_yr = (pmdec_mas_yr / 1000.0 / 3600.0) * (math.pi / 180.0)
    px_arcsec = parallax_mas / 1000.0
    
    # erfa.starpm(ra, dec, pmr, pmd, px, rv, ep1a, ep1b, ep2a, ep2b)
    # returns ra, dec, pmr, pmd, px, rv
    try:
        ra_out, dec_out, _, _, _, _ = erfa.starpm(
            ra_rad, dec_rad, pmra_rad_yr, pmdec_rad_yr, px_arcsec, rv_km_s,
            _J2000, 0.0, _J2000 + (dt_years * 365.25), 0.0
        )
    except erfa.core.ErfaWarning:
        pass
        
    return math.cos(dec_out) * math.cos(ra_out), math.cos(dec_out) * math.sin(ra_out), math.sin(dec_out)


@pytest.mark.parametrize("star_name", _TEST_STARS.keys())
def test_deep_time_astrometry_stability(star_name: str):
    ra, dec, pmra, pmdec, px, rv = _TEST_STARS[star_name]
    record = _SovereignStarRecord(
        name=star_name,
        nomenclature="test",
        gaia_dr3_id=None,
        ra_deg=ra,
        dec_deg=dec,
        pmra_mas_yr=pmra,
        pmdec_mas_yr=pmdec,
        parallax_mas=px,
        radial_velocity_km_s=rv,
        magnitude_v=1.0,
        color_index=1.0,
        ecl_lon_deg=0.0,
        ecl_lat_deg=0.0,
        arc_vis_deg=10.0,
        lat_limit_deg=90.0,
        lore={},
        provenance={},
    )
    
    # Epoch sweep: J-8000 to J+8000 in 100-year increments
    # JD span is roughly J2000 +/- 10000 years
    years = range(-8000, 8001, 100)
    
    max_divergence_deg = 0.0
    
    for year in years:
        jd_tt = julian_day(year, 1, 1, 12.0)
        dt_years = (jd_tt - _J2000) / 365.25
        
        # Moira propagation
        m_x, m_y, m_z = _propagate_icrs_vector(record, jd_tt)
        
        # Invariants: Normalization error < 1e-12
        norm = math.sqrt(m_x**2 + m_y**2 + m_z**2)
        assert abs(norm - 1.0) < 1e-12, f"Normalization error at year {year} for {star_name}: {norm}"
        
        # ERFA propagation
        e_x, e_y, e_z = _erfa_pmpx_vector(ra, dec, pmra, pmdec, px, rv, dt_years)
        
        # Angle difference between Moira and ERFA vectors
        dot = m_x * e_x + m_y * e_y + m_z * e_z
        # Clamping dot product to valid domain
        dot = max(-1.0, min(1.0, dot))
        diff_deg = math.degrees(math.acos(dot))
        
        if diff_deg > max_divergence_deg:
            max_divergence_deg = diff_deg

        # We assert no NaN or Inf
        assert math.isfinite(m_x) and math.isfinite(m_y) and math.isfinite(m_z)
        
    # How well does the current linear proper motion hold up against ERFA over 10000 years?
    # This assertion is designed to fail if the linear approximation breaks down (e.g. > 10 degrees).
    # We allow a small divergence (e.g. < 0.05 degrees) since Moira does not perform ERFA's iterative relativistic adjustment.
    assert max_divergence_deg < 0.05, f"Divergence from ERFA reached {max_divergence_deg} degrees for {star_name}"
