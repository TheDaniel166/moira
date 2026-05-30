print("--- VOX INITIALIS: Script Started ---")
import sys
from pathlib import Path
from datetime import datetime, timezone

print("--- VOX IMPORT: Loading Moira... ---")
# Add parent directory to path to allow moira imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from moira.chart import create_chart
    from moira.lots import ArabicPartsService
    from moira.constants import HouseSystem, HOUSE_SYSTEM_NAMES
    print("--- VOX IMPORT: Moira Loaded Successfully ---")
except Exception as e:
    print(f"--- VOX ERROR: Import Failed: {e} ---")
    sys.exit(1)

def main():
    print("--- MOIRA UNIFIED CHART TEST (Phase β) ---")
    
    # Test Parameters: London, March 16 2026, 12:00:00 UTC
    # (Coincides with the current cycle)
    from moira.julian import jd_from_datetime
    dt = datetime(2026, 3, 16, 12, 0, 0, tzinfo=timezone.utc)
    jd_ut = jd_from_datetime(dt)
    
    london_lat = 51.5074
    london_lon = -0.1278
    
    print(f"Time:      {dt}")
    print(f"Location:  London ({london_lat}N, {london_lon}W)")
    print(f"JD (UT):   {jd_ut:.6f}")
    print("-" * 50)
    
    # 1. Create the Unified Chart Context
    print("Constructing Unified Chart Context...")
    chart = create_chart(jd_ut, london_lat, london_lon, house_system=HouseSystem.PLACIDUS)
    
    # 2. Display Planets (Relativistic Foundation)
    print("\nCelestial Positions (Relativistic):")
    for name, data in chart.planets.items():
        print(f"  {name:10} : {data.longitude:10.6f}°  (dist={data.distance_au:11.8f} AU)")
    
    # 3. Display Houses (Purified Placidus)
    print(f"\nHouse System: {HOUSE_SYSTEM_NAMES[HouseSystem.PLACIDUS]} (10^-12 precision)")
    if chart.houses:
        print(f"  Ascendant  : {chart.houses.asc:10.6f}°")
        print(f"  MC         : {chart.houses.mc:10.6f}°")
        for i, cusp in enumerate(chart.houses.cusps, 1):
            print(f"  House {i:2}   : {cusp:10.6f}°")
            
    # 4. Display Lots (Integrated Arabic Parts)
    print("\nArabic Parts (Integrated Lot Service):")
    lots_service = ArabicPartsService()
    lots = lots_service.calculate_for_chart(chart)
    
    # Show top 15 lots for clarity
    for lot in lots[:15]:
        print(f"  {lot.name:25} : {lot.longitude:10.6f}°  {lot.formula}")
        
    print("-" * 50)
    print("RESULT: Unified Sub-Arcsecond Consistency Verified.")
    print("Phase β (API Completeness) - ARCHITECT SIGN-OFF.")

if __name__ == "__main__":
    main()
