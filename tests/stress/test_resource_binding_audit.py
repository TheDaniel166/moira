import threading
import random
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from moira.planets import planet_at
from moira.constants import Body
from moira.spk_reader import get_reader, SpkReader

def stress_test_resource_binding():
    print("Starting Resource Binding Stress Test (10,000 queries)...")
    
    # 1. Setup
    tracemalloc.start()
    bodies = [Body.SUN, Body.MOON, Body.MERCURY, Body.VENUS, Body.MARS, 
              Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE, Body.PLUTO]
    
    # Ensure reader is initialized
    reader = get_reader()
    print(f"Active Reader: {reader}")
    
    num_queries = 10000
    num_threads = 20
    queries_per_thread = num_queries // num_threads
    
    # Capture initial memory
    current, peak = tracemalloc.get_traced_memory()
    initial_mem = current
    print(f"Initial Memory: {initial_mem / 1024 / 1024:.2f} MB")
    
    results_lock = threading.Lock()
    all_results = {} # (body, jd) -> result_vec
    contamination_detected = False
    
    def worker(worker_id):
        nonlocal contamination_detected
        for _ in range(queries_per_thread):
            body = random.choice(bodies)
            jd = random.uniform(2400000.0, 2500000.0)
            
            # Execute query and discard result
            planet_at(body, jd, reader=reader, frame='cartesian', apparent=False)
            
        return None

    # 2. Parallel Execution
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, i) for i in range(num_threads)]
        for future in as_completed(futures):
            future.result() # wait for completion

    duration = time.time() - start_time
    print(f"Completed {num_queries} queries in {duration:.2f}s ({num_queries/duration:.0f} q/s)")

    # 3. Explicit Parity Check (Threaded)
    print("Running Explicit Parity Check (Identical inputs across threads)...")
    fixed_queries = [(random.choice(bodies), random.uniform(2400000.0, 2500000.0)) for _ in range(100)]
    
    def parity_worker(query_idx):
        body, jd = fixed_queries[query_idx]
        p1 = planet_at(body, jd, reader=reader, frame='cartesian', apparent=False)
        return (body, jd, (p1.x, p1.y, p1.z))

    parity_results = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Each query executed 10 times in parallel
        for i in range(len(fixed_queries)):
            tasks = [executor.submit(parity_worker, i) for _ in range(10)]
            outputs = [t.result()[2] for t in tasks]
            
            # Assert all 10 parallel outputs are bit-for-bit identical
            first = outputs[0]
            for out in outputs[1:]:
                if out != first:
                    print(f"PARITY FAILURE: Body {fixed_queries[i][0]} at JD {fixed_queries[i][1]}")
                    print(f"  Result 1: {first}")
                    print(f"  Result N: {out}")
                    return False
    print("Parity Check: PASSED (No cross-thread contamination detected)")

    # 5. Handle Isolation Check
    print("Running Handle Isolation Check (Multiple Readers)...")
    reader2 = SpkReader(reader.path)
    body, jd = random.choice(bodies), random.uniform(2400000.0, 2500000.0)
    
    # Query both readers
    p1 = planet_at(body, jd, reader=reader, frame='cartesian', apparent=False)
    p2 = planet_at(body, jd, reader=reader2, frame='cartesian', apparent=False)
    
    assert (p1.x, p1.y, p1.z) == (p2.x, p2.y, p2.z)
    
    # Close one, ensure other still works
    reader2.close()
    p3 = planet_at(body, jd, reader=reader, frame='cartesian', apparent=False)
    assert (p1.x, p1.y, p1.z) == (p3.x, p3.y, p3.z)
    print("Handle Isolation: PASSED")

    tracemalloc.stop()
    return True

if __name__ == "__main__":
    if stress_test_resource_binding():
        print("\nRESOURCE BINDING AUDIT: SUCCESSFUL")
    else:
        print("\nRESOURCE BINDING AUDIT: FAILED")
        exit(1)
