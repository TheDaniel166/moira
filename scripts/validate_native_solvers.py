import math
import time
from scipy import optimize
from moira import _moira_native

def test_brent_root():
    print("\n--- Testing Brent's Root-Finding ---")
    
    # Test case: f(x) = x^3 - x - 2 (Root near 1.521)
    def f(x):
        return x**3 - x - 2

    a, b = 1.0, 2.0
    
    # SciPy reference
    start = time.perf_counter()
    ref_root = optimize.brentq(f, a, b, xtol=1e-12)
    scipy_time = time.perf_counter() - start
    
    # Native implementation
    start = time.perf_counter()
    native_root = _moira_native.brent_root(f, a, b, tol=1e-12)
    native_time = time.perf_counter() - start
    
    print(f"SciPy Root:  {ref_root:.15f} ({scipy_time*1e6:.1f} us)")
    print(f"Native Root: {native_root:.15f} ({native_time*1e6:.1f} us)")
    
    diff = abs(native_root - ref_root)
    print(f"Difference:  {diff:.15e}")
    assert diff < 1e-12, "Brent root parity failed"

def test_brent_minimize():
    print("\n--- Testing Brent's Minimization ---")
    
    # Test case: f(x) = (x - 0.5)^2 + 3 (Minimum at 0.5)
    def f(x):
        return (x - 0.5)**2 + 3

    a, b = -1.0, 1.0
    
    # SciPy reference
    start = time.perf_counter()
    res = optimize.minimize_scalar(f, bracket=(a, b), method='brent', tol=1e-12)
    ref_min = res.x
    scipy_time = time.perf_counter() - start
    
    # Native implementation
    start = time.perf_counter()
    native_min = _moira_native.brent_minimize(f, a, b, tol=1e-12)
    native_time = time.perf_counter() - start
    
    print(f"SciPy Min:   {ref_min:.15f} ({scipy_time*1e6:.1f} us)")
    print(f"Native Min:  {native_min:.15f} ({native_time*1e6:.1f} us)")
    
    diff = abs(native_min - ref_min)
    print(f"Difference:  {diff:.15e}")
    assert diff < 1e-10, "Brent minimize parity failed" # Minimization tolerance is often coarser

def test_newton_safe():
    print("\n--- Testing Safe Newton ---")
    
    # Test case: f(x) = cos(x) - x (Root near 0.739)
    def f(x):
        return math.cos(x) - x
    def df(x):
        return -math.sin(x) - 1

    a, b = 0.0, 1.0
    
    # SciPy reference (Newton)
    start = time.perf_counter()
    ref_root = optimize.newton(f, 0.5, fprime=df, tol=1e-12)
    scipy_time = time.perf_counter() - start
    
    # Native implementation
    start = time.perf_counter()
    native_root = _moira_native.newton_safe(f, df, a, b, tol=1e-12)
    native_time = time.perf_counter() - start
    
    print(f"SciPy Root:  {ref_root:.15f} ({scipy_time*1e6:.1f} us)")
    print(f"Native Root: {native_root:.15f} ({native_time*1e6:.1f} us)")
    
    diff = abs(native_root - ref_root)
    print(f"Difference:  {diff:.15e}")
    assert diff < 1e-12, "Newton safe parity failed"

def test_find_roots():
    print("\n--- Testing Interval Root Scanning ---")
    
    # Test case: f(x) = sin(x) in [0, 10]
    # Roots at 0, PI, 2*PI, 3*PI
    def f(x):
        return math.sin(x)

    a, b = 0.1, 10.0 # Start slightly above 0 to avoid exactly matching it
    dt = 0.5
    
    native_roots = _moira_native.find_roots(f, a, b, dt, tol=1e-12)
    print(f"Native Roots: {[r for r in native_roots]}")
    
    expected = [math.pi, 2*math.pi, 3*math.pi]
    assert len(native_roots) == len(expected), f"Expected {len(expected)} roots, got {len(native_roots)}"
    for got, want in zip(native_roots, expected):
        diff = abs(got - want)
        print(f"Root: {got:.15f}, Diff: {diff:.15e}")
        assert diff < 1e-12

def test_light_time():
    print("\n--- Testing Light-Time Iteration ---")
    
    # Simple model: target moving at v = 10 AU/day, observer at origin
    # r_target(t) = [10*t, 0, 0]
    # Observer at [0, 0, 0]
    # tau = |r_target(t - tau)| / c = 10 * (t - tau) / c
    # tau = 10t / c - 10tau / c => tau(1 + 10/c) = 10t/c => tau = 10t / (c + 10)
    
    c = 173.1446326742403 # AU / day (approx)
    v = 10.0
    t_obs = 1.0
    
    def target_ephem(t):
        return _moira_native.Vec3(v * t, 0.0, 0.0)
    
    obs_pos = _moira_native.Vec3(0.0, 0.0, 0.0)
    
    expected_tau = (v * t_obs) / (c + v)
    native_tau = _moira_native.solve_light_time(target_ephem, obs_pos, t_obs)
    
    print(f"Expected Tau: {expected_tau:.15f}")
    print(f"Native Tau:   {native_tau:.15f}")
    
    diff = abs(native_tau - expected_tau)
    print(f"Difference:   {diff:.15e}")
    assert diff < 1e-12

def test_spk_type13():
    print("\n--- Testing SPK Type 13 (Small Body) Evaluation ---")
    
    # Test case: f(t) = t^2 for each component
    # Epochs: [0, 1, 2, 3, 4]
    # States: [[0, 1, 4, 9, 16], ...]
    epochs = [0.0, 1.0, 2.0, 3.0, 4.0]
    states = [[t*t for t in epochs] for _ in range(6)]
    
    jd = 1.5
    window_size = 4
    
    # Expected result: 1.5^2 = 2.25
    native_res = _moira_native.spk_type13_record(epochs, states, window_size, jd)
    print(f"Native Result at {jd}: {native_res}")
    
    for val in native_res:
        diff = abs(val - 2.25)
        assert diff < 1e-12

if __name__ == "__main__":
    try:
        test_brent_root()
        test_brent_minimize()
        test_newton_safe()
        test_find_roots()
        test_light_time()
        test_spk_type13()
        print("\nAll Phase 3 foundation and solver parity checks passed.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nValidation failed: {e}")
        exit(1)
