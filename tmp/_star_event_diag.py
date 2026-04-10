"""Diagnostic: what altitude does Moira compute for each star at its own predicted event JD?"""
from moira.julian import jd_from_datetime, format_jd_utc
from moira.stars import heliacal_rising_event, _star_altitude
import datetime

CASES = [
    ("Sirius",    datetime.datetime(2025,  7, 15, tzinfo=datetime.timezone.utc)),
    ("Aldebaran", datetime.datetime(2025,  6,  1, tzinfo=datetime.timezone.utc)),
    ("Regulus",   datetime.datetime(2025,  8, 15, tzinfo=datetime.timezone.utc)),
    ("Antares",   datetime.datetime(2025, 11, 25, tzinfo=datetime.timezone.utc)),
    ("Fomalhaut", datetime.datetime(2025,  4,  1, tzinfo=datetime.timezone.utc)),
]
LAT, LON = 32.55, 44.42

print(f"{'Star':<12}  {'Event date':>24}  {'Event JD':>15}  {'Moira star_alt':>14}  {'vs -0.5667':>10}")
print("-" * 85)
for name, start_dt in CASES:
    jd_start = jd_from_datetime(start_dt)
    result = heliacal_rising_event(name, jd_start, LAT, LON)
    event_jd = result.jd_ut
    event_date = format_jd_utc(event_jd)
    alt = _star_altitude(name, event_jd, LAT, LON)
    diff = alt - (-0.5667)
    sign = "ABOVE" if alt > -0.5667 else "BELOW"
    print(f"{name:<12}  {event_date:>24}  {event_jd:>15.6f}  {alt:>+14.6f}  {sign} by {abs(diff):.4f}")
