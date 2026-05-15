
import time
from moira import Moira, julian_day, format_jd_utc, Body
import math

def test_mars_cazimi_decade():
    engine = Moira()
    
    # Range: 2026 to 2036 (10 years)
    jd_start = julian_day(2026, 1, 1)
    jd_end = julian_day(2037, 1, 1)
    
    print(f"Searching for Mars Cazimi (17') events from 2026 to 2036...")
    
    start_time = time.perf_counter()
    events = engine.solar_condition_events("Mars", jd_start, jd_end, condition="cazimi")
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    
    print(f"Search completed in {duration:.4f} seconds.\n")
    print(f"{'Date & Time (UTC)':20} | {'Angle':7} | {'Sun Lon':10} | {'Mars Lon':10} | {'Mars Lat':8}")
    print("-" * 65)
    
    for ev in events:
        utc = format_jd_utc(ev.jd_ut)
        # Format lon into degrees/minutes for easier oracle check
        def fmt_deg(d):
            d = d % 360
            deg = int(d)
            mnt = int(round((d - deg) * 60))
            if mnt == 60:
                deg += 1
                mnt = 0
            return f"{deg:3}{mnt:02}'"

        sun_fmt = fmt_deg(ev.body1_longitude)
        mars_fmt = fmt_deg(ev.body2_longitude)
        
        # In the table, Angle is reported as +/- 017'
        # ev.threshold_deg is the target separation sign-aware
        angle_fmt = f"{ev.threshold_deg:+.4f}"
        
        print(f"{utc:20} | {angle_fmt:7} | {sun_fmt:10} | {mars_fmt:10} | {ev.body2_latitude:+.4f}")

if __name__ == "__main__":
    test_mars_cazimi_decade()
