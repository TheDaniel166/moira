"""Probe: get Moira's heliacal rising predictions for Sirius + 4 Royal Stars at Babylon."""
from moira.stars import heliacal_rising_event, _default_arcus_for_star
from moira.julian import jd_from_datetime, format_jd_utc
import datetime

STARS = ["Sirius", "Aldebaran", "Regulus", "Antares", "Fomalhaut"]
LAT, LON = 32.55, 44.42  # Babylon

# Two search windows: one starting Jan 2025, one starting Jul 2025
# (catches stars whose heliacal rising falls mid-year)
for start_label, start_dt in [
    ("2025-Jan-01", datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)),
    ("2025-Jul-01", datetime.datetime(2025, 7, 1, tzinfo=datetime.timezone.utc)),
]:
    jd_start = jd_from_datetime(start_dt)
    print(f"\nSearch from {start_label}:")
    print(f"{'Star':<12}  {'av':>5}  {'Date/UT':>24}  {'star_alt':>9}  {'sun_alt':>8}  {'elong':>8}")
    print("-" * 75)
    for name in STARS:
        av = _default_arcus_for_star(name)
        result = heliacal_rising_event(name, jd_start, LAT, LON)
        jd = result.jd_ut
        date_str = format_jd_utc(jd) if jd else "None"
        star_alt = getattr(result, "star_altitude_deg", "?")
        sun_alt  = getattr(result, "sun_altitude_deg", "?")
        elong    = getattr(result, "elongation_deg", "?")
        print(f"{name:<12}  {av:>4.1f}  {date_str:>24}  {star_alt!s:>9}  {sun_alt!s:>8}  {elong!s:>8}")
