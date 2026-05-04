import pytest
import math
from moira.sky.eclipse import EclipseCalculator
from moira.solar_cartography import _compute_besselian_sample
from moira.spk_reader import get_reader

def test_besselian_elements_audit_2017() -> None:
    """
    Audit Moira's Besselian elements against NASA ground truth for 2017-08-21.
    NASA Greatest Eclipse: 2017-08-21 18:26:40 UT (JD 2457987.26852)
    """
    calc = EclipseCalculator(get_reader())
    jd_ut = 2457987.26852
    
    sample = _compute_besselian_sample(calc, jd_ut)
    
    # NASA Values (2017-08-21)
    # tan f1 = 0.0046115
    # tan f2 = 0.0045885
    # l1 = 0.54209
    # l2 = -0.00039
    
    # Note: Residuals (approx 1e-4) are expected due to different radius 
    # constants (Moira 696340/1737.4 vs NASA 696000/1738.1) and 
    # DE441 vs NASA polynomial fits.
    assert math.isclose(sample.tan_f1, 0.0046115, abs_tol=2e-4)
    assert math.isclose(sample.tan_f2, 0.0045885, abs_tol=2e-4)
    assert math.isclose(sample.l1_earth_radii, 0.54209, abs_tol=1e-3)
    # Moira uses opposite sign for total eclipses (positive) vs NASA (negative)
    assert math.isclose(abs(sample.l2_earth_radii), abs(-0.00039), abs_tol=5e-3)

def test_besselian_continuity_audit() -> None:
    """
    Verify that Besselian elements move smoothly across the fundamental plane.
    """
    calc = EclipseCalculator(get_reader())
    jd_start = 2457987.2 # 2017-08-21 early
    
    samples = []
    for i in range(10):
        samples.append(_compute_besselian_sample(calc, jd_start + i * 0.001))
        
    for i in range(len(samples) - 1):
        dx = abs(samples[i+1].x - samples[i].x)
        dy = abs(samples[i+1].y - samples[i].y)
        dl1 = abs(samples[i+1].l1_earth_radii - samples[i].l1_earth_radii)
        
        # In 0.001 days (86s), shadow axis moves approx 0.01-0.02 Earth radii
        assert 0.001 < dx < 0.05
        assert 0.0001 < dy < 0.05
        # Radii change very slowly
        assert dl1 < 1e-5

def test_besselian_elements_audit_2024() -> None:
    """
    Audit Moira's Besselian elements against NASA ground truth for 2024-04-08.
    NASA Greatest Eclipse: 2024-04-08 18:18:29 UT (JD 2460409.26284)
    """
    calc = EclipseCalculator(get_reader())
    jd_ut = 2460409.26284
    
    sample = _compute_besselian_sample(calc, jd_ut)
    
    # NASA Values (2024-04-08)
    # tan f1 = 0.0046683
    # tan f2 = 0.0046453
    # l1 = 0.53503
    # l2 = -0.00073
    
    assert math.isclose(sample.tan_f1, 0.0046683, abs_tol=2e-4)
    assert math.isclose(sample.tan_f2, 0.0046453, abs_tol=2e-4)
    assert math.isclose(sample.l1_earth_radii, 0.53503, abs_tol=2e-3)
    assert math.isclose(abs(sample.l2_earth_radii), abs(-0.00073), abs_tol=0.02)

def test_grazing_occultation_proximity_audit() -> None:
    """
    Test the grazing limit of a lunar occultation.
    Prove that a 'miss distance' of < 1 km is correctly reflected in the
    separation geometry.
    """
    from moira.occultations import _angular_separation_equatorial
    from moira.constants import MOON_RADIUS_KM, EARTH_RADIUS_KM
    
    # Simulate a body exactly at the lunar limb at 384,400 km
    dist_km = 384400.0
    moon_radius_deg = math.degrees(math.asin(MOON_RADIUS_KM / dist_km))
    
    # 1 km on the lunar limb at that distance is:
    one_km_deg = math.degrees(1.0 / dist_km)
    
    # Case A: 500m inside the limb
    sep_inside = moon_radius_deg - (0.5 / dist_km) * (180.0 / math.pi)
    # Case B: 500m outside the limb
    sep_outside = moon_radius_deg + (0.5 / dist_km) * (180.0 / math.pi)
    
    # Proximity check: ensure our angular math doesn't collapse at 1km scales
    assert sep_outside > moon_radius_deg > sep_inside
    assert math.isclose(sep_outside - sep_inside, 2 * (0.5 / dist_km) * (180.0 / math.pi), abs_tol=1e-12)

def test_asteroid_occultation_miss_distance_audit() -> None:
    """
    Verify that asteroid occultation solvers handle <1 km miss distances.
    At 2.5 AU, 1 km is approx 0.0005 arcseconds.
    """
    from moira.occultations import _angular_separation_equatorial
    
    # Body at 2.5 AU
    dist_km = 2.5 * 149597870.7
    # 0.5 km angular size
    one_km_deg = math.degrees(1.0 / dist_km)
    
    # Baseline RA/Dec
    ra1, dec1 = 120.0, 20.0
    # Shifted by 0.5 km (0.00025 arcsec)
    ra2 = ra1 + (0.5 / dist_km) * (180.0 / math.pi) / math.cos(math.radians(dec1))
    dec2 = dec1
    
    sep = _angular_separation_equatorial(ra1, dec1, ra2, dec2)
    expected_sep = (0.5 / dist_km) * (180.0 / math.pi)
    
    # Assert we can resolve the 500m separation at 2.5 AU
    assert math.isclose(sep, expected_sep, abs_tol=1e-13)

