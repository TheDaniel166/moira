import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import moira
from moira.julian import julian_day, ut_to_tt, delta_t_from_jd
from moira.asteroids import asteroid_at
from moira.spk_reader import use_reader_override

def main():
    # User's chart details
    # Date: 1987-08-03
    # Universal Time: 13:52:00
    
    # Calculate Julian Day UT
    jd_ut = julian_day(1987, 8, 3, 13.0 + 52.0 / 60.0)
    
    # Initialize Moira facade
    try:
        engine = moira.Moira()
        print("Moira initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Moira: {e}")
        return

    # Let's compute a full chart using the facade
    # The chart expects a datetime object. Let's construct a timezone-aware or naive datetime for 1987-08-03 13:52:00 UTC
    import datetime
    dt_utc = datetime.datetime(1987, 8, 3, 13, 52, 0, tzinfo=datetime.timezone.utc)
    chart = engine.chart(dt_utc)
    
    # Let's list the planets in order
    planets_order = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    
    # Let's list the asteroids
    asteroids_order = ["Ceres", "Pallas", "Juno", "Vesta", "Chiron", "Pholus", "Nessus", "Eros"]
    
    print("\n" + "=" * 110)
    print("MOIRA FULL ECLIPTIC POSITIONS (TROPICAL, APPARENT GEOCENTRIC OF DATE)")
    print("=" * 110)
    print(f"{'Body':12s} | {'Longitude':14s} | {'Sign Degree':24s} | {'Latitude':10s} | {'Distance (AU)':14s} | {'Speed (°/d)':12s} | {'Motion':6s}")
    print("-" * 110)
    
    # helper for DMS
    def fmt_dms(deg_val):
        d = int(deg_val)
        m = int((deg_val - d) * 60)
        s = ((deg_val - d) * 60 - m) * 60
        return f"{d:02d}°{m:02d}'{s:04.1f}\""

    # 1. Main Planets
    for name in planets_order:
        p = chart.planets.get(name)
        if p:
            dist_au = p.distance / 149597870.700
            motion = "Rx" if p.speed < 0 else "Dir"
            dms_str = fmt_dms(p.sign_degree)
            print(f"{name:<12s} | {p.longitude:11.6f}° | {p.sign:<12s} {dms_str} | {p.latitude:+9.6f}° | {dist_au:14.6f} | {p.speed:+12.6f} | {motion:<6s}")
            
    print("-" * 110)
    
    # 2. Nodes and Apogees
    for name in sorted(chart.nodes.keys()):
        n = chart.nodes[name]
        motion = "Rx" if n.speed < 0 else "Dir"
        dms_str = fmt_dms(n.sign_degree)
        print(f"{name:<12s} | {n.longitude:11.6f}° | {n.sign:<12s} {dms_str} | {'0.000000°':10s} | {'N/A':14s} | {n.speed:+12.6f} | {motion:<6s}")
        
    print("-" * 110)
    
    # 3. Asteroids
    with use_reader_override(engine._reader):
        for name in asteroids_order:
            try:
                pos = asteroid_at(name, jd_ut)
                dist_au = pos.distance / 149597870.700
                motion = "Rx" if pos.retrograde else "Dir"
                dms_str = fmt_dms(pos.sign_degree)
                print(f"{pos.name:<12s} | {pos.longitude:11.6f}° | {pos.sign:<12s} {dms_str} | {pos.latitude:+9.6f}° | {dist_au:14.6f} | {pos.speed:+12.6f} | {motion:<6s}")
            except Exception as e:
                print(f"{name:<12s} | Error: {e}")

if __name__ == "__main__":
    main()
