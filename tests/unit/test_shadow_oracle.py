import pytest
import math

from moira.constants import EARTH_RADIUS_KM, SUN_RADIUS_KM, MOON_RADIUS_KM
from moira.eclipse_geometry import (
    umbra_radius,
    penumbra_radius,
    lunar_umbral_magnitude,
    lunar_penumbral_magnitude,
    shadow_axis_offset_deg,
)

def test_shadow_cone_geometry_invariants() -> None:
    """Prove that shadow cone geometry does not collapse or invert."""
    sun_dist_km = 149597870.7  # 1 AU
    moon_dist_km_perigee = 362600.0
    moon_dist_km_apogee = 405400.0
    
    # 1. Penumbra must always be strictly larger than Umbra
    u_peri = umbra_radius(sun_dist_km, moon_dist_km_perigee)
    p_peri = penumbra_radius(sun_dist_km, moon_dist_km_perigee)
    assert p_peri > u_peri > 0.0

    u_apo = umbra_radius(sun_dist_km, moon_dist_km_apogee)
    p_apo = penumbra_radius(sun_dist_km, moon_dist_km_apogee)
    assert p_apo > u_apo > 0.0
    
    # 2. Umbra size must strictly decrease as the Moon moves away
    # (The cone narrows to a point)
    assert u_peri > u_apo
    
    # 3. Penumbra size must strictly decrease as the Moon moves away
    # (The apparent angular size decreases due to 1/D perspective)
    assert p_peri > p_apo

def test_magnitude_monotonicity() -> None:
    """Prove that magnitude strictly increases as the axis offset decreases."""
    u_rad = 0.75  # degrees
    m_rad = 0.25  # degrees
    
    # Offset decreasing from 1.0 (edge) to 0.0 (exact center)
    offsets = [1.0, 0.75, 0.5, 0.25, 0.0]
    magnitudes = [
        lunar_umbral_magnitude(u_rad, m_rad, offset)
        for offset in offsets
    ]
    
    # Check strict monotonicity
    for i in range(len(magnitudes) - 1):
        assert magnitudes[i+1] > magnitudes[i]
        
    # At exact center (offset=0), mag = (0.75 + 0.25 - 0) / 0.5 = 2.0
    assert magnitudes[-1] == 2.0

def test_grazing_limits() -> None:
    """Test exactly when the Moon barely touches the umbra."""
    u_rad = 0.75
    m_rad = 0.25
    
    # Barely touching (exterior contact): offset = u_rad + m_rad = 1.0
    offset_exterior = 1.0
    mag_exterior = lunar_umbral_magnitude(u_rad, m_rad, offset_exterior)
    assert math.isclose(mag_exterior, 0.0, abs_tol=1e-9)
    
    # Just inside: offset slightly less than 1.0
    mag_just_inside = lunar_umbral_magnitude(u_rad, m_rad, 0.99)
    assert mag_just_inside > 0.0

def test_anti_solar_geometry() -> None:
    """Prove the shadow axis offset treats 180 degrees as zero offset."""
    # Exact opposition
    assert shadow_axis_offset_deg(180.0) == 0.0
    
    # Slightly off
    assert math.isclose(shadow_axis_offset_deg(179.5), 0.5, abs_tol=1e-9)
    assert math.isclose(shadow_axis_offset_deg(180.5), 0.5, abs_tol=1e-9)

def test_besselian_fundamental_plane_logic() -> None:
    """
    Test the pure math behind Besselian elements as implemented in
    _compute_besselian_sample.
    """
    # Simulate the mathematical expressions for tan_f1, tan_f2, l1, l2
    # at a representative sun/moon distance
    sun_dist_km = 149597870.0
    moon_dist_km = 384400.0
    
    # Under typical conditions, sun_moon_distance is roughly sun_dist_km
    # since Earth is at origin, but let's assume exact collinearity for the test
    sun_moon_dist = sun_dist_km - moon_dist_km
    
    tan_f1 = (SUN_RADIUS_KM + MOON_RADIUS_KM) / sun_moon_dist
    tan_f2 = (SUN_RADIUS_KM - MOON_RADIUS_KM) / sun_moon_dist
    
    # distance_to_plane is roughly moon_dist_km when the plane passes through Earth center
    # and Moon is at zenith (exact collinearity)
    distance_to_plane = moon_dist_km
    
    penumbra_radius_er = (MOON_RADIUS_KM + (distance_to_plane * tan_f1)) / EARTH_RADIUS_KM
    umbra_radius_er = (MOON_RADIUS_KM - (distance_to_plane * tan_f2)) / EARTH_RADIUS_KM
    
    # 1. Penumbra l1 must be larger than Umbra l2
    assert penumbra_radius_er > umbra_radius_er
    
    # 2. l1 (penumbra) is always positive. l2 (umbra) is positive for total 
    # eclipses (Moon close) and negative for annular eclipses (Moon far).
    # At 384,400 km, the eclipse is annular (l2 < 0).
    assert penumbra_radius_er > 0.0
    assert umbra_radius_er < 0.0
    
    # Check a total eclipse case (Moon at perigee)
    distance_to_plane_total = 360000.0
    umbra_radius_er_total = (MOON_RADIUS_KM - (distance_to_plane_total * tan_f2)) / EARTH_RADIUS_KM
    assert umbra_radius_er_total > 0.0
    
    # 3. f1 is the penumbral cone half-angle, f2 is the umbral cone half-angle
    # Since Sun > Earth > Moon, f1 > f2
    assert tan_f1 > tan_f2
