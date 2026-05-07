import math
import random
from moira.julian import julian_day as py_julian_day, calendar_from_jd as py_calendar_from_jd
from moira.moira_native import (
    Vec3, Mat3, julian_day, calendar_from_jd,
    deg_to_rad, rad_to_deg, normalize_deg_360, normalize_deg_180,
    mod_floor, safe_acos, safe_asin, almost_equal,
    horner, lagrange_interpolate,
    bisect, newton_safe, minimize_bracketed,
    radec_to_vec3, vec3_to_radec, ecliptic_to_equatorial, equatorial_to_ecliptic
)

# --- The Adversarial Audit of the Forge ---

def test_numerical_guardrails():
    """Stress test the safe trig and hygiene functions."""
    print("  - Testing out-of-bounds safe_acos/asin...")
    # These should NOT return NaN, but clamp to 1.0/-1.0
    assert almost_equal(safe_acos(1.0000000001), 0.0)
    assert almost_equal(safe_acos(-1.0000000001), math.pi)
    assert almost_equal(safe_asin(1.0000000001), math.pi / 2.0)
    assert almost_equal(safe_asin(-1.0000000001), -math.pi / 2.0)
    
    # NaN and Infinity checks
    from moira.moira_native import is_finite, has_nan
    assert is_finite(1.0)
    assert not is_finite(float('inf'))
    assert has_nan(float('nan'))

def test_round_trips():
    """Audit the reversibility of transformations."""
    print("  - Testing transformation round-trips...")
    random.seed(123)
    
    # 1. JD <-> Calendar
    for _ in range(100):
        jd = random.uniform(0, 5000000)
        y_native, m_native, d_native, h_native = calendar_from_jd(jd)
        y_py, m_py, d_py, h_py = py_calendar_from_jd(jd)
        assert (y_native, m_native, d_native) == (y_py, m_py, d_py), f"Native calendar parity failed at {jd}"
        assert almost_equal(h_native, h_py, abs_eps=1e-12), f"Native calendar hour parity failed at {jd}"

        jd_native = julian_day(y_native, m_native, d_native, h_native)
        jd_py = py_julian_day(y_py, m_py, d_py, h_py)
        assert almost_equal(jd_native, jd_py, abs_eps=1e-8), f"JD parity failed after inverse conversion at {jd}"
        
    # 2. Cartesian <-> Spherical
    for _ in range(100):
        v_orig = Vec3([random.uniform(-100, 100) for _ in range(3)])
        ra, dec, dist = vec3_to_radec(v_orig)
        v_back = radec_to_vec3(ra, dec, dist)
        for i in range(3):
            assert almost_equal(v_orig[i], v_back[i]), f"Cartesian Round-trip failed"

    # 3. Ecliptic <-> Equatorial
    obliq = 23.43929
    for _ in range(100):
        lon = random.uniform(0, 360)
        lat = random.uniform(-90, 90)
        ra, dec = ecliptic_to_equatorial(lon, lat, obliq)
        lon_back, lat_back = equatorial_to_ecliptic(ra, dec, obliq)
        assert almost_equal(lon, lon_back) and almost_equal(lat, lat_back)

def test_adversarial_solvers():
    """Stress test solvers with pathological inputs."""
    print("  - Testing adversarial solver conditions...")
    
    # 1. Invalid Bracket
    try:
        bisect(lambda x: x**2 - 4, 3.0, 4.0)
        assert False, "Bisect should have failed for un-bracketed root"
    except RuntimeError as e:
        assert "not bracketed" in str(e)
        
    # 2. Vanishing Derivative in Newton
    # f(x) = x^2, root at 0, derivative 2x is 0 at x=0
    # Safe Newton should handle this via bisection fallback
    res = newton_safe(lambda x: x**2, lambda x: 2*x, -1.0, 1.0)
    assert almost_equal(res, 0.0, abs_eps=1e-7)

def test_julian_extreme_audit():
    """Stress test Julian conversions at time-scale edges."""
    print("  - Testing extreme temporal points...")
    # Deep past (DE441 limit is roughly -13000)
    jd_past = julian_day(-15000, 1, 1, 0.0)
    y, m, d, h = calendar_from_jd(jd_past)
    assert y == -15000
    
    # Far future
    jd_future = julian_day(25000, 12, 31, 23.99)
    y, m, d, h = calendar_from_jd(jd_future)
    assert y == 25000 and m == 12 and d == 31

def test_matrix_adversarial():
    """Test singular matrices and near-singular cases."""
    print("  - Testing singular matrix handling...")
    # Singular matrix (all zeros)
    m_zero = Mat3([[0,0,0], [0,0,0], [0,0,0]])
    try:
        m_zero.inverse()
        assert False, "Should have failed to invert singular matrix"
    except RuntimeError as e:
        assert "singular" in str(e)

if __name__ == "__main__":
    tests = [
        test_numerical_guardrails,
        test_round_trips,
        test_adversarial_solvers,
        test_julian_extreme_audit,
        test_matrix_adversarial
    ]
    
    passed = 0
    print("Initiating Adversarial Audit of the Forge Substrate...")
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            
    if passed == len(tests):
        print("\nThe Forge has withstood the Adversarial Audit. Its integrity is absolute.")
    else:
        print(f"\nThe Audit exposed {len(tests) - passed} vulnerabilities.")
