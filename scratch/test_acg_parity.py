
import math
import numpy as np
from moira.astrocartography import acg_lines, _HAS_NUMPY
from moira.constants import Body

def test_vectorized_parity():
    if not _HAS_NUMPY:
        print("NumPy not available, skipping parity test.")
        return

    # Mock Mars RA/Dec
    planet_ra_dec = {"Mars": (45.0, 20.0)}
    gmst = 100.0
    
    # 1. Force Scalar path (temporarily disable numpy flag in module)
    import moira.astrocartography as acg
    original_has_numpy = acg._HAS_NUMPY
    acg._HAS_NUMPY = False
    lines_scalar = acg.acg_lines(planet_ra_dec, gmst, lat_step=1.0)
    
    # 2. Use Vectorized path
    acg._HAS_NUMPY = original_has_numpy
    lines_vec = acg.acg_lines(planet_ra_dec, gmst, lat_step=1.0)
    
    asc_scalar = next(l for l in lines_scalar if l.line_type == "ASC").points
    asc_vec = next(l for l in lines_vec if l.line_type == "ASC").points
    
    print(f"Comparing {len(asc_scalar)} points...")
    for p1, p2 in zip(asc_scalar, asc_vec):
        # Latitudes should be identical
        assert p1[0] == p2[0]
        # Longitudes should be very close (within float precision)
        diff = abs(p1[1] - p2[1])
        if diff > 1e-12:
            print(f"Discrepancy at Lat {p1[0]}: {p1[1]} vs {p2[1]} (diff {diff})")
            assert diff < 1e-10
            
    print("Parity test passed: Vectorized path matches Scalar path.")

if __name__ == "__main__":
    test_vectorized_parity()
