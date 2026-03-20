"""
Moira — house_system_test.py
Verifying the complete catalog of purified house systems.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path to allow moira imports
sys.path.append(str(Path(__file__).parent.parent))

from moira.houses import calculate_houses
from moira.constants import HouseSystem, HOUSE_SYSTEM_NAMES
from moira.julian import jd_from_datetime

def main():
    print("--- MOIRA HOUSE SYSTEM TEST (Phase β completeness) ---")
    
    dt = datetime(2026, 3, 16, 12, 0, 0, tzinfo=timezone.utc)
    jd_ut = jd_from_datetime(dt)
    lat, lon = 51.5074, -0.1278 # London
    
    systems = [
        HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.TOPOCENTRIC,
        HouseSystem.ALCABITIUS, HouseSystem.CAMPANUS, HouseSystem.REGIOMONTANUS,
        HouseSystem.MORINUS, HouseSystem.MERIDIAN, HouseSystem.EQUAL, HouseSystem.WHOLE_SIGN
    ]
    
    for sys_code in systems:
        name = HOUSE_SYSTEM_NAMES.get(sys_code, sys_code)
        print(f"\n{name} ({sys_code}):")
        try:
            h = calculate_houses(jd_ut, lat, lon, system=sys_code)
            print(f"  Ascendant : {h.asc:.6f}°")
            print(f"  MC        : {h.mc:.6f}°")
            print(f"  Cusp 2    : {h.cusps[1]:.6f}°")
            print(f"  Cusp 11   : {h.cusps[10]:.6f}°")
        except Exception as e:
            print(f"  [ERROR] {e}")

    print("\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    main()
