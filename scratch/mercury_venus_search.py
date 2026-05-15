
import time
from moira import Moira, julian_day, format_jd_utc, Body
import math

def test_mercury_venus_proximity_sweep():
    engine = Moira()
    
    # Range: 2026 to 2030 (4 years covers the table provided)
    jd_start = julian_day(2026, 1, 1)
    jd_end = julian_day(2030, 1, 1)
    
    threshold = 0.2833333  # 17'
    
    print(f"Searching for Mercury-Venus Proximity (17') events from 2026 to 2029...")
    
    start_time = time.perf_counter()
    # Using the facade method I just added
    events = engine.proximity_events("Mercury", "Venus", jd_start, jd_end, threshold_deg=threshold)
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    
    print(f"Search completed in {duration:.4f} seconds.\n")
    print(f"{'Date & Time (UTC)':20} | {'Angle':7} | {'Merc Lon':10} | {'Venus Lon':10} | {'Venus Lat':8}")
    print("-" * 65)
    
    for ev in events:
        utc = format_jd_utc(ev.jd_ut)
        
        def fmt_deg(d):
            d = d % 360
            deg = int(d)
            mnt = int(round((d - deg) * 60))
            if mnt == 60:
                deg += 1
                mnt = 0
            return f"{deg:3}{mnt:02}'"

        merc_fmt = fmt_deg(ev.body1_longitude)
        venus_fmt = fmt_deg(ev.body2_longitude)
        
        # Determine the sign based on threshold in the event
        angle_fmt = f"{ev.threshold_deg:+.4f}"
        
        print(f"{utc:20} | {angle_fmt:7} | {merc_fmt:10} | {venus_fmt:10} | {ev.body2_latitude:+.4f}")

if __name__ == "__main__":
    test_mercury_venus_proximity_sweep()
