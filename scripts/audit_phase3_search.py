
import time
from moira import _moira_native

def audit_native_search():
    print("\n=== Phase 3: Native Search Engine Audit ===")
    
    # 1. Setup Native Evaluators
    # For a fair test, we'll use dummy Chebyshev evaluators
    # (In reality, these would be loaded from SPK segments)
    coeffs = [0.0] * 33 # 11 coeffs * 3 components
    coeffs[0] = 1.0 # Simple constant position
    
    sun_eval = _moira_native.ChebyshevEvaluator(2460000.5, 32.0, 100, 3, 11, coeffs)
    moon_eval = _moira_native.ChebyshevEvaluator(2460000.5, 32.0, 100, 3, 11, coeffs)
    earth_eval = _moira_native.ChebyshevEvaluator(2460000.5, 32.0, 100, 3, 11, coeffs)
    
    # 2. Performance Comparison: Longitude Difference
    jd = 2460000.5
    
    print("\n--- Scalar Evaluation Bottleneck ---")
    start = time.perf_counter()
    for _ in range(1000):
        _moira_native.longitude_difference(sun_eval, moon_eval, earth_eval, jd)
    native_eval_time = time.perf_counter() - start
    print(f"Native Eval Time (1000 calls): {native_eval_time*1e3:.2f} ms")
    
    # 3. Full Native Search Audit
    print("\n--- Full Native Search vs. Python-Callback Search ---")
    
    a, b = 2460000.5, 2460100.5 # 100 days
    dt = 0.5
    
    # Method A: Python Callback (Native solver calls Python function)
    def python_f(jd_val):
        return _moira_native.longitude_difference(sun_eval, moon_eval, earth_eval, jd_val)
        
    start = time.perf_counter()
    _moira_native.find_roots(python_f, a, b, dt)
    callback_search_time = time.perf_counter() - start
    
    # Method B: Full Native (Native solver calls Native evaluator)
    start = time.perf_counter()
    _moira_native.find_conjunctions(sun_eval, moon_eval, earth_eval, a, b, dt)
    full_native_search_time = time.perf_counter() - start
    
    print(f"Python-Callback Search: {callback_search_time*1e3:.2f} ms")
    print(f"Full-Native Search:     {full_native_search_time*1e3:.2f} ms")
    
    speedup = callback_search_time / full_native_search_time
    print(f"Performance Multiplier: {speedup:.1f}x Faster")

    # 4. Caching Audit
    print("\n--- Caching Efficiency ---")
    start = time.perf_counter()
    for _ in range(1000):
        sun_eval.evaluate(jd)
    cached_time = time.perf_counter() - start
    print(f"Cached Eval Time (1000 calls): {cached_time*1e3:.4f} ms")
    
    # 5. Batch Evaluation Audit
    print("\n--- Batched Evaluation Performance ---")
    jds = [a + i * (b - a) / 999 for i in range(1000)]
    start = time.perf_counter()
    res_batch = sun_eval.evaluate_batch(jds)
    batch_time = time.perf_counter() - start
    print(f"Batch Eval Time (1000 JDs):    {batch_time*1e3:.2f} ms")
    print(f"Batch Result Length:          {len(res_batch)}")

if __name__ == "__main__":
    audit_native_search()
