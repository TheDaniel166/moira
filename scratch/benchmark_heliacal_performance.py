import time
import moira
from moira.stars import heliacal_catalog_batch

def benchmark_heliacal():
    # Observer at Alexandria
    lat = 31.2
    lon = 29.9
    jd_start = 2451545.0  # J2000
    
    from moira._kernel_paths import find_planetary_kernel
    from moira.spk_reader import set_kernel_path
    
    kernel_path = find_planetary_kernel()
    set_kernel_path(kernel_path)
    engine = moira.Moira()
    
    print(f"Benchmarking heliacal_catalog_batch...")
    print(f"Location: {lat}N, {lon}E")
    print(f"Start JD: {jd_start}")
    
    # 1. Benchmark small batch (10 stars)
    names = ["Sirius", "Canopus", "Arcturus", "Vega", "Capella", "Rigel", "Procyon", "Achernar", "Betelgeuse", "Hadar"]
    start_time = time.perf_counter()
    # Use engine's context or just having it initialized might be enough if it sets a global context
    # but usually we should use engine.stars.heliacal_catalog_batch if it exists
    # or just use the facade methods.
    result = heliacal_catalog_batch("heliacal_rising", jd_start, lat, lon, names=names, search_days=400)
    end_time = time.perf_counter()
    print(f"Small batch (10 named stars): {end_time - start_time:.4f} seconds")
    print(f"Found: {len(result.found)}, Searched: {result.total_searched}")
    
    # 2. Benchmark catalog batch by magnitude (e.g. brighter than 2.0)
    max_mag = 2.0
    start_time = time.perf_counter()
    result = heliacal_catalog_batch("heliacal_rising", jd_start, lat, lon, max_magnitude=max_mag, search_days=400)
    end_time = time.perf_counter()
    print(f"Catalog batch (mag < {max_mag}): {end_time - start_time:.4f} seconds")
    print(f"Found: {len(result.found)}, Searched: {result.total_searched}, Skipped (lat): {len(result.skipped_latitude)}")

    # 3. Benchmark catalog batch by magnitude (brighter than 4.0)
    max_mag = 4.0
    start_time = time.perf_counter()
    result = heliacal_catalog_batch("heliacal_rising", jd_start, lat, lon, max_magnitude=max_mag, search_days=400)
    end_time = time.perf_counter()
    print(f"Catalog batch (mag < {max_mag}): {end_time - start_time:.4f} seconds")
    print(f"Found: {len(result.found)}, Searched: {result.total_searched}, Skiched (lat): {len(result.skipped_latitude)}")

if __name__ == "__main__":
    benchmark_heliacal()
