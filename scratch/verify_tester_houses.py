import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import moira
from moira.julian import julian_day
from moira.houses import calculate_houses, HouseSystem

def main():
    # User's chart details
    # Date: 1987-08-03
    # Universal Time: 13:52:00
    # Location: 77w01 -> -77.016667, 12s02 -> -12.033333
    
    # Calculate Julian Day UT
    jd_ut = julian_day(1987, 8, 3, 13.0 + 52.0 / 60.0)
    lat = -12.033333
    lon = -77.016667
    
    # Initialize Moira facade
    try:
        engine = moira.Moira()
    except Exception as e:
        print(f"Failed to initialize Moira: {e}")
        return

    # List of house systems we want to print
    systems = {
        HouseSystem.PLACIDUS: "Placidus",
        HouseSystem.KOCH: "Koch",
        HouseSystem.CAMPANUS: "Campanus",
        HouseSystem.REGIOMONTANUS: "Regiomontanus",
        HouseSystem.PORPHYRY: "Porphyry",
        HouseSystem.EQUAL: "Equal",
        HouseSystem.WHOLE_SIGN: "Whole Sign",
        HouseSystem.ALCABITIUS: "Alcabitius",
        HouseSystem.MORINUS: "Morinus",
        HouseSystem.TOPOCENTRIC: "Topocentric"
    }
    
    out_lines = []
    out_lines.append("=" * 110)
    out_lines.append("HOUSE CUSPS COMPARISON FOR 1987-08-03 13:52:00 UTC (77w01, 12s02)")
    out_lines.append("=" * 110)
    
    def fmt_dms(deg_val):
        sign_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                      "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        deg_val = deg_val % 360.0
        sign_idx = int(deg_val // 30)
        sign_name = sign_names[sign_idx]
        sign_deg = deg_val % 30
        d = int(sign_deg)
        m = int((sign_deg - d) * 60)
        s = ((sign_deg - d) * 60 - m) * 60
        return f"{sign_name:<12s} {d:02d}°{m:02d}'{s:04.1f}\""

    for sys_code, sys_name in systems.items():
        try:
            res = calculate_houses(jd_ut, lat, lon, sys_code)
            out_lines.append(f"\nHouse System: {sys_name}")
            out_lines.append("-" * 50)
            out_lines.append(f"  Ascendant  : {fmt_dms(res.asc)}")
            out_lines.append(f"  Midheaven  : {fmt_dms(res.mc)}")
            out_lines.append(f"  Vertex     : {fmt_dms(res.vertex)}")
            out_lines.append(f"  East Point : {fmt_dms(res.east_point)}")
            for i, cusp in enumerate(res.cusps):
                out_lines.append(f"  House {i+1:2d}   : {fmt_dms(cusp)} (longitude: {cusp:10.5f}°)")
        except Exception as e:
            out_lines.append(f"\nHouse System: {sys_name} - Error: {e}")

    output_path = ROOT / "scratch" / "house_cusps_output.txt"
    output_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Written house cusps to {output_path}")

if __name__ == "__main__":
    main()
