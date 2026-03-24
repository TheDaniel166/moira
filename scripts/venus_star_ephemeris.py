"""
Venus Star High-Fidelity Ephemeris — scripts/venus_star_ephemeris.py

Purpose: Generates a complete astronomical manifest of the Venus Star points,
         including Longitude, Latitude, Distance, Speed, and Rx status, 
         mirroring professional conjunction tables.
"""

from datetime import datetime, timezone
from moira import Moira, Body

def generate_venus_star_table(start_date: datetime, count: int = 10):
    m = Moira()
    jd = m.jd(start_date.year, start_date.month, start_date.day, start_date.hour)
    jd_end = jd + (365.25 * 8.5)
    
    # Header scansion
    header = (
        f"{'DATE (UTC)':<20} | {'TYPE':<10} | {'ZODIAC DEGREE':<18} | "
        f"{'LAT':>8} | {'DIST':>8} | {'SPEED':>8} | {'Rx'}"
    )
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    
    # Use native conjunction engine
    events = m.conjunctions(Body.VENUS, Body.SUN, jd, jd_end)
    
    for ev in events[:count]:
        chart = m.chart(ev.datetime_utc)
        v_data = chart.planets[Body.VENUS]
        
        # Conjunction Type
        is_inferior = v_data.distance_au < 1.0 
        ctype = "Inferior" if is_inferior else "Superior"
        
        # Sign information (e.g. 0°45' Scorpio)
        sign_deg, m_part, s_part = v_data.longitude_dms
        sign_ext = f"{sign_deg:02d}°{m_part:02d}' {v_data.sign}"
        
        # Rx marker
        rx_label = "Rx" if v_data.retrograde else "  "
        
        # Manifest the row
        print(
            f"{ev.datetime_utc.strftime('%Y-%m-%d %H:%M:%S'):<20} | "
            f"{ctype:<10} | "
            f"{sign_ext:<18} | "
            f"{v_data.latitude:>8.4f}° | "
            f"{v_data.distance_au:>8.4f} | "
            f"{v_data.speed:>8.4f} | "
            f"{rx_label}"
        )

    print("-" * len(header))

if __name__ == "__main__":
    start = datetime.now(timezone.utc)
    print(f"Moira Luminous Ephemeris: The Rose of Venus (from {start.date()})")
    generate_venus_star_table(start, count=10)
