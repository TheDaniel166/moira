"""
Moira — phase_gamma_nodes_centaurs_test.py
Verifying True Osculating Lilith and the Centaur API.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path to allow moira imports
sys.path.append(str(Path(__file__).parent.parent))

from moira.nodes import mean_lilith, true_lilith
from moira.centaurs import chiron_at, available_centaurs, list_centaurs
from moira.julian import jd_from_datetime

def main():
    print("--- MOIRA PHASE Γ INTERMEDIATE TEST ---")
    
    dt = datetime(2026, 3, 16, 12, 0, 0, tzinfo=timezone.utc)
    jd_ut = jd_from_datetime(dt)
    
    # 1. Test Lilith
    print("\n[LUNAR APOGEE / LILITH]")
    ml = mean_lilith(jd_ut)
    tl = true_lilith(jd_ut)
    
    print(f"Mean Lilith : {ml.longitude:.6f}° ({ml.sign} {ml.sign_symbol})")
    print(f"True Lilith : {tl.longitude:.6f}° ({tl.sign} {tl.sign_symbol})")
    print(f"Difference  : {abs(tl.longitude - ml.longitude):.6f}°")
    
    # 2. Test Centaurs
    print("\n[CENTAURS]")
    print(f"Centaur API Catalog: {', '.join(list_centaurs())}")
    
    available = available_centaurs()
    print(f"Available Kernels  : {', '.join(available)}")
    
    if "Chiron" in available:
        chi = chiron_at(jd_ut)
        print(f"Chiron Position: {chi.longitude:.6f}° ({chi.sign} {chi.sign_symbol})")
        print(f"Retrograde     : {chi.retrograde}")
    else:
        print("[WARNING] Chiron not available in kernels.")

    print("\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    main()
