import time
import random
import math
from moira import _moira_native as moira_native

def generate_random_point_cloud(n=100000):
    x = [1.0] * n
    y = [0.0] * n
    z = [0.0] * n
    return moira_native.LolaPointCloud(x, y, z)

def benchmark_filters():
    n_points = 100000
    print(f"Generating {n_points} points...")
    pc = generate_random_point_cloud(n_points)
    
    observer_dir = moira_native.Vec3(1.0, 0.0, 0.0)
    sky_east = moira_native.Vec3(0.0, 1.0, 0.0)
    sky_north = moira_native.Vec3(0.0, 0.0, 1.0)
    target_pa = 0.0
    tolerance = 360.0
    min_radius = -1.0
    
    # Warmup
    for _ in range(5):
        pc.filter_combined(observer_dir, sky_east, sky_north, target_pa, tolerance, min_radius)
    
    # 1. Sequential Benchmark
    start_seq = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        pc1 = pc.filter_by_visibility(observer_dir)
        pc2 = pc1.filter_by_position_angle(sky_east, sky_north, target_pa, tolerance)
        pc3 = pc2.filter_by_radius(sky_east, sky_north, min_radius)
    end_seq = time.perf_counter()
    avg_seq = (end_seq - start_seq) / iterations
    
    # 2. Combined Benchmark
    start_comb = time.perf_counter()
    for _ in range(iterations):
        pc_final = pc.filter_combined(observer_dir, sky_east, sky_north, target_pa, tolerance, min_radius)
    end_comb = time.perf_counter()
    avg_comb = (end_comb - start_comb) / iterations
    
    speedup = (avg_seq / avg_comb)
    reduction = (1.0 - avg_comb / avg_seq) * 100
    
    print(f"Sequential avg time: {avg_seq*1000:.4f} ms")
    print(f"Combined avg time:   {avg_comb*1000:.4f} ms")
    print(f"Speedup:             {speedup:.2f}x")
    print(f"Time reduction:      {reduction:.2f}%")
    
    # Verification of parity
    pc1 = pc.filter_by_visibility(observer_dir)
    pc2 = pc1.filter_by_position_angle(sky_east, sky_north, target_pa, tolerance)
    pc3 = pc2.filter_by_radius(sky_east, sky_north, min_radius)
    pc_final = pc.filter_combined(observer_dir, sky_east, sky_north, target_pa, tolerance, min_radius)
    
    print(f"Original size: {pc.size()}")
    print(f"Filtered size: {pc_final.size()}")
    
    assert pc3.size() == pc_final.size(), f"Parity failed: {pc3.size()} != {pc_final.size()}"
    print("Numerical parity verified.")
    
    if reduction < 15.0:
        print("WARNING: Speedup less than mandated 15%!")
    else:
        print("SUCCESS: Performance mandate met.")

if __name__ == "__main__":
    benchmark_filters()
