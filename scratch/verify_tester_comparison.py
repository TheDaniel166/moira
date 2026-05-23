import sys
import os
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import moira
from moira.julian import julian_day, ut_to_tt, delta_t_from_jd
from moira.asteroids import asteroid_at
from moira.spk_reader import use_reader_override
from moira.coordinates import ecliptic_to_equatorial
from moira.obliquity import true_obliquity
from moira.houses import calculate_houses, body_house_position

def main():
    # User's chart details
    # Date: 1987-08-03
    # Universal Time: 13:52:00
    lat = -12.033333
    lon = -77.016667
    
    # Calculate Julian Day UT
    jd_ut = julian_day(1987, 8, 3, 13.0 + 52.0 / 60.0)
    dt_sec = delta_t_from_jd(jd_ut)
    dt_days = dt_sec / 86400.0
    
    # Let's load the tester's data from the image:
    swiss_data = {
        "Ceres":       {"lon": 261.8592022, "lat": -4.216989643, "decl": -27.40204287, "ra": 260.8470411, "house": 3.91559979, "speed": -0.04056405629},
        "Pallas":      {"lon": 225.5363799, "lat": 37.31449468,  "decl": 19.2887369,  "ra": 233.8274962, "house": 3.065329687, "speed": 0.1866660125},
        "Juno":        {"lon": 334.5314575, "lat": 9.083542613,  "decl": -1.380422627, "ra": 333.0950213, "house": 6.337459304, "speed": -0.1754366566},
        "Vesta":       {"lon": 94.9661582,  "lat": -2.097633169, "decl": 21.25396924, "ra": 95.32602581, "house": 10.42673257, "speed": 0.4065707448},
        "Astraea":     {"lon": 175.5687576, "lat": 3.359308766,  "decl": 4.844167984,  "ra": 177.2705037, "house": 1.168234198, "speed": 0.4860212085},
        "Hebe":        {"lon": 290.0707289, "lat": 8.965542597,  "decl": -13.06990453, "ra": 290.3651591, "house": 4.934953841, "speed": -0.2243539045},
        "Iris":        {"lon": 291.2302412, "lat": 5.912197879,  "decl": -15.92435715, "ra": 291.9973976, "house": 4.998582535, "speed": -0.2291331409},
        "Flora":       {"lon": 322.1638292, "lat": -4.920141357, "decl": -18.77346117, "ra": 326.2090307, "house": 6.201941698, "speed": -0.2379451942},
        "Metis":       {"lon": 141.9997497, "lat": 3.811015297,  "decl": 17.78075056,  "ra": 145.6603304, "house": 12.17680018, "speed": 0.4998962914},
        "Hygiea":      {"lon": 122.6243097, "lat": -0.8361062738, "decl": 18.76268834, "ra": 124.7031927, "house": 11.4503303,  "speed": 0.3472179254},
        "Parthenope":  {"lon": 141.2202545, "lat": 1.136188481,  "decl": 15.50504818,  "ra": 143.9829878, "house": 12.10538916, "speed": 0.4130431348},
        "Victoria":    {"lon": 121.7460078, "lat": -5.527544499, "decl": 14.38136144,  "ra": 122.7278883, "house": 11.36510144, "speed": 0.3856971174},
        "Egeria":      {"lon": 78.75243685, "lat": 4.010136149,  "decl": 26.96245217,  "ra": 77.39083352, "house": 9.791951985, "speed": 0.4056457699}
    }
    
    # Initialize Moira
    try:
        engine = moira.Moira()
    except Exception as e:
        print(f"Failed to initialize Moira: {e}")
        return

    out_lines = []

    # Let's perform comparisons for both cases
    for case_name, jd_input in [("Case A (13:52:00 UT)", jd_ut), ("Case B (Direct JD 2447011.078421 UT)", 2447011.078421)]:
        out_lines.append("\n" + "=" * 120)
        out_lines.append(f"RUNNING COMPARISON FOR {case_name}")
        out_lines.append("=" * 120)
        
        # Calculate house cusps for Placidus at this JD and location
        try:
            house_cusps = calculate_houses(jd_input, lat, lon, "P")
        except Exception as e:
            out_lines.append(f"Failed to compute houses: {e}")
            continue
            
        jd_tt_val = ut_to_tt(jd_input)
        obliquity = true_obliquity(jd_tt_val)
        
        out_lines.append(f"{'Body':12s} | {'Field':6s} | {'Swiss Value':15s} | {'Moira Value':15s} | {'Difference':15s}")
        out_lines.append("-" * 120)
        
        with use_reader_override(engine._reader):
            for name, swiss in swiss_data.items():
                try:
                    pos = asteroid_at(name, jd_input)
                    # Compute RA/Dec
                    ra, dec = ecliptic_to_equatorial(pos.longitude, pos.latitude, obliquity)
                    ra = ra % 360.0
                    
                    # Compute house position
                    h_pos = body_house_position(pos.longitude, house_cusps)
                    
                    # Compare each field
                    fields = [
                        ("lon", swiss["lon"], pos.longitude, "deg"),
                        ("lat", swiss["lat"], pos.latitude, "deg"),
                        ("decl", swiss["decl"], dec, "deg"),
                        ("ra", swiss["ra"], ra, "deg"),
                        ("house", swiss["house"], h_pos, "unit"),
                        ("speed", swiss["speed"], pos.speed, "deg/d")
                    ]
                    
                    for f_name, s_val, m_val, unit in fields:
                        diff = m_val - s_val
                        if unit == "deg":
                            if f_name in ("lon", "ra"):
                                diff = (diff + 180.0) % 360.0 - 180.0
                            diff_str = f"{diff * 3600.0:+.6f}\""
                        else:
                            diff_str = f"{diff:+.8f}"
                            
                        out_lines.append(f"{name:<12s} | {f_name:<6s} | {s_val:15.8f} | {m_val:15.8f} | {diff_str}")
                    out_lines.append("-" * 120)
                except Exception as e:
                    out_lines.append(f"{name:<12s} | Error: {e}")

    output_path = ROOT / "scratch" / "tester_comparison_output.txt"
    output_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Written comparison to {output_path}")

if __name__ == "__main__":
    main()
