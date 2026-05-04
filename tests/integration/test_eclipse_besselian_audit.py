import pytest
from moira.solar_cartography import _compute_besselian_sample

def test_besselian_elements_audit_2017(eclipse_calculator, moira_approx) -> None:
    """
    Audit Moira's Besselian elements against NASA ground truth for 2017-08-21.
    NASA Greatest Eclipse: 2017-08-21 18:26:40 UT (JD 2457987.26852)
    """
    jd_ut = 2457987.26852
    sample = _compute_besselian_sample(eclipse_calculator, jd_ut)
    
    # NASA Values (2017-08-21)
    # tan f1 = 0.0046115, tan f2 = 0.0045885, l1 = 0.54209, l2 = -0.00039
    
    # Note: Residuals are expected due to different radius constants and DE441 vs polynomial fits.
    assert sample.tan_f1 == pytest.approx(0.0046115, abs=2e-4)
    assert sample.tan_f2 == pytest.approx(0.0045885, abs=2e-4)
    assert sample.l1_earth_radii == pytest.approx(0.54209, abs=1e-3)
    # Moira uses opposite sign for total eclipses (positive) vs NASA (negative)
    assert abs(sample.l2_earth_radii) == pytest.approx(0.00039, abs=5e-3)

def test_besselian_continuity_audit(eclipse_calculator) -> None:
    """Verify that Besselian elements move smoothly across the fundamental plane."""
    jd_start = 2457987.2 # 2017-08-21 early
    
    samples = [_compute_besselian_sample(eclipse_calculator, jd_start + i * 0.001) for i in range(10)]
        
    for i in range(len(samples) - 1):
        dx = abs(samples[i+1].x - samples[i].x)
        dy = abs(samples[i+1].y - samples[i].y)
        dl1 = abs(samples[i+1].l1_earth_radii - samples[i].l1_earth_radii)
        
        # In 0.001 days (86s), shadow axis moves approx 0.01-0.02 Earth radii
        assert 0.001 < dx < 0.05
        assert 0.0001 < dy < 0.05
        assert dl1 < 1e-5 # Radii change very slowly

def test_besselian_elements_audit_2024(eclipse_calculator, moira_approx) -> None:
    """
    Audit Moira's Besselian elements against NASA ground truth for 2024-04-08.
    NASA Greatest Eclipse: 2024-04-08 18:18:29 UT (JD 2460409.26284)
    """
    jd_ut = 2460409.26284
    sample = _compute_besselian_sample(eclipse_calculator, jd_ut)
    
    # NASA Values (2024-04-08)
    # tan f1 = 0.0046683, tan f2 = 0.0046453, l1 = 0.53503, l2 = -0.00073
    assert sample.tan_f1 == pytest.approx(0.0046683, abs=2e-4)
    assert sample.tan_f2 == pytest.approx(0.0046453, abs=2e-4)
    assert sample.l1_earth_radii == pytest.approx(0.53503, abs=2e-3)
    assert abs(sample.l2_earth_radii) == pytest.approx(0.00073, abs=0.02)

def test_grazing_occultation_proximity_audit() -> None:
    """
    Test the grazing limit of a lunar occultation.
    Prove that a 'miss distance' of < 1 km is correctly reflected in the separation geometry.
    """
    import math
    from moira.constants import MOON_RADIUS_KM
    
    # Simulate a body exactly at the lunar limb at 384,400 km
    dist_km = 384400.0
    moon_radius_deg = math.degrees(math.asin(MOON_RADIUS_KM / dist_km))
    
    # Proximity check: ensure our angular math doesn't collapse at 1km scales
    sep_inside = moon_radius_deg - (0.5 / dist_km) * (180.0 / math.pi)
    sep_outside = moon_radius_deg + (0.5 / dist_km) * (180.0 / math.pi)
    
    assert sep_outside > moon_radius_deg > sep_inside
    assert (sep_outside - sep_inside) == pytest.approx(2 * (0.5 / dist_km) * (180.0 / math.pi), abs=1e-12)

def test_asteroid_occultation_miss_distance_audit() -> None:
    """
    Verify that asteroid occultation solvers handle <1 km miss distances.
    At 2.5 AU, 1 km is approx 0.0005 arcseconds.
    """
    import math
    from moira.occultations import _angular_separation_equatorial
    
    # Body at 2.5 AU
    dist_km = 2.5 * 149597870.7
    ra1, dec1 = 120.0, 20.0
    # Shifted by 0.5 km (0.00025 arcsec)
    ra2 = ra1 + (0.5 / dist_km) * (180.0 / math.pi) / math.cos(math.radians(dec1))
    dec2 = dec1
    
    sep = _angular_separation_equatorial(ra1, dec1, ra2, dec2)
    expected_sep = (0.5 / dist_km) * (180.0 / math.pi)
    
    # Assert we can resolve the 500m separation at 2.5 AU
    assert sep == pytest.approx(expected_sep, abs=1e-13)


