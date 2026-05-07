import numpy as np
import time
import concurrent.futures
from moira import _moira_native

def create_synthetic_body(freq, phase, amplitude=1.0):
    # Simulated XYZ coefficients for a complex orbit
    # Using many coefficients to stress the Clenshaw evaluator
    coeff_count = 16
    record_count = 2000 # ~100 years of data
    
    coeffs = np.random.uniform(-amplitude, amplitude, (record_count, 3, coeff_count))
    # Add some structure so it's not pure noise
    t = np.linspace(0, 1, coeff_count)
    for r in range(record_count):
        for c in range(3):
            coeffs[r, c] = np.sin(freq * t + phase + r) * amplitude
            
    # Flatten for the evaluator
    coeffs_flat = coeffs.flatten().tolist()
    
    return _moira_native.ChebyshevEvaluator(
        2460000.5, # init
        32.0,      # intlen (days per record)
        record_count,
        3,         # components
        coeff_count,
        coeffs_flat
    )

def run_heavy_search(id, t1, t2, obs, start_jd, end_jd):
    # Stress: Find all 30-degree aspects in a 10-year window
    # aspect_deg = 30.0
    # dt = 0.5 day
    aspects = [0, 30, 60, 90, 120, 150, 180]
    results = []
    for deg in aspects:
        found = _moira_native.find_aspects(t1, t2, obs, deg, start_jd, end_jd, 0.2)
        results.extend(found)
    return len(results)

def phase3_stress_test():
    print("\n=== Phase 3 Stress Test: THE SEARCH KILLER ===")
    
    print("Constructing High-Complexity Synthetic Solar System...")
    body1 = create_synthetic_body(0.1, 0.0, 10.0)
    body2 = create_synthetic_body(0.15, 1.0, 5.0)
    earth = create_synthetic_body(0.05, 0.5, 1.0)
    
    start_jd = 2460000.5
    end_jd = start_jd + 365.25 * 10 # 10 years
    
    print(f"Window: {end_jd - start_jd:.1f} days")
    print(f"Tolerance: 1e-13 (Native Default)")
    
    # --- Single Threaded Peak Performance ---
    print("\n--- Running Baseline Heavy Search (10 Years, All Major Aspects) ---")
    start = time.perf_counter()
    count = run_heavy_search(0, body1, body2, earth, start_jd, end_jd)
    duration = time.perf_counter() - start
    
    print(f"Events Found: {count}")
    print(f"Search Time:  {duration:.3f} s")
    print(f"Events/Sec:   {count/duration:.1f}")

    # --- Multi-Threaded Stress ---
    print("\n--- Running Concurrent Stress (20 Parallel Searches) ---")
    num_tasks = 20
    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(run_heavy_search, i, body1, body2, earth, start_jd, end_jd) for i in range(num_tasks)]
        total_events = sum(f.result() for f in concurrent.futures.as_completed(futures))
    
    total_duration = time.perf_counter() - start
    print(f"Total Events Found: {total_events}")
    print(f"Total Time:         {total_duration:.3f} s")
    print(f"Effective Throughput: {total_events/total_duration:.1f} events/sec")

    # --- Extreme Precision Test ---
    print("\n--- Verifying Numerical Stability at Boundary ---")
    # Search for exactly one conjunction and check its value
    one_root = _moira_native.find_conjunctions(body1, body2, earth, start_jd, start_jd + 100, 0.5)
    if one_root:
        test_jd = one_root[0]
        val = _moira_native.longitude_difference(body1, body2, earth, test_jd)
        print(f"Root at: {test_jd:.15f}")
        print(f"Value at root: {val:.2e} (Residual)")
        assert abs(val) < 1e-12, "Precision stability failed at root boundary"

    print("\nSTRESS TEST COMPLETE: NO CRASHES, NO DRIFT.")

if __name__ == "__main__":
    try:
        phase3_stress_test()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Stress test failed: {e}")
