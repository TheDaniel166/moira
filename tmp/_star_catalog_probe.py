from moira.stars import star_magnitude, star_at, _resolve_star_record, DEFAULT_FIXED_STAR_POLICY
from moira.julian import jd_from_datetime
import datetime
jd = jd_from_datetime(datetime.datetime(2025, 8, 3, tzinfo=datetime.timezone.utc))
for name in ["Sirius", "Aldebaran", "Regulus", "Antares", "Fomalhaut"]:
    mag = star_magnitude(name)
    r, _ = _resolve_star_record(name, DEFAULT_FIXED_STAR_POLICY.lookup)
    print(name, "mag=", round(mag, 2))
    print("  record attrs:", [a for a in dir(r) if not a.startswith("_")])
    print("  record:", r)
    print()
