import time
import numpy as np
from moira.eclipse import EclipseCalculator
from moira.solar_cartography import solar_eclipse_cartography
from moira.lunar_cartography import lunar_eclipse_cartography

from moira.spk_reader import use_reader_override, SpkReader
from moira._kernel_paths import find_planetary_kernel

def benchmark_cartography():
    path = find_planetary_kernel()
    with use_reader_override(SpkReader(path)):
        calc = EclipseCalculator()

        jd_2024 = 2460409.25  # April 8, 2024

        print("=== Cartography Benchmark ===")

        # 1. Solar Cartography
        print("\n[Solar Cartography Benchmark]")

        start = time.perf_counter()
        res_py = solar_eclipse_cartography(calc, jd_2024, backend="cpu")
        dur_py = time.perf_counter() - start
        print(f"NumPy (CPU) Duration:  {dur_py:.4f}s")

        start = time.perf_counter()
        res_native = solar_eclipse_cartography(calc, jd_2024, backend="moira-native")
        dur_native = time.perf_counter() - start
        print(f"Moira-Native Duration: {dur_native:.4f}s")
        print(f"Speedup: {dur_py / dur_native:.2f}x")

        # 2. Lunar Cartography
        print("\n[Lunar Cartography Benchmark]")
        jd_lunar = 2460750.0  # Lunar eclipse

        start = time.perf_counter()
        res_py_l = lunar_eclipse_cartography(calc, jd_lunar, backend="cpu")
        dur_py_l = time.perf_counter() - start
        print(f"NumPy (CPU) Duration:  {dur_py_l:.4f}s")

        start = time.perf_counter()
        res_native_l = lunar_eclipse_cartography(calc, jd_lunar, backend="moira-native")
        dur_native_l = time.perf_counter() - start
        print(f"Moira-Native Duration: {dur_native_l:.4f}s")
        print(f"Speedup: {dur_py_l / dur_native_l:.2f}x")

        print("\nBENCHMARK COMPLETE.")

if __name__ == "__main__":
    benchmark_cartography()
