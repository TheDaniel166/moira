import math
from moira.constants import Body
from moira.planets import planet_at
from moira.julian import julian_day, local_sidereal_time
from moira.stations import find_stations

# Let's find a Mars station. Mars retrograde around 2025-01-16.
jd_start = julian_day(2024, 12, 1, 0.0)
jd_end = julian_day(2025, 3, 1, 0.0)

events = find_stations(Body.MARS, jd_start, jd_end)
for ev in events:
    print(ev)

# Pick the first station (which is a Retrograde station)
if not events:
    print("No events found.")
    exit()

jd_station = events[0].jd_ut
print(f"Mars station exactly at JD: {jd_station}")

# Now, let's sample the topocentric velocity over the 4 days surrounding the station
# using a specific observer on the equator (max rotational velocity)
lat = 0.0
lon = 0.0
elev = 0.0

print("\nJD, Geo Speed, Topo Num Speed")
for i in range(-48, 48):
    jd_eval = jd_station + i/24.0
    
    # Geocentric speed is directly provided by the engine
    geo_speed = planet_at(Body.MARS, jd_eval).speed
    
    # Topocentric numerical speed
    dt = 1.0 / 24.0 / 60.0 # 1 minute
    
    lst_1 = local_sidereal_time(jd_eval - dt, lon)
    topo_1 = planet_at(Body.MARS, jd_eval - dt, observer_lat=lat, observer_lon=lon, observer_elev_m=elev, lst_deg=lst_1).longitude
    
    lst_2 = local_sidereal_time(jd_eval + dt, lon)
    topo_2 = planet_at(Body.MARS, jd_eval + dt, observer_lat=lat, observer_lon=lon, observer_elev_m=elev, lst_deg=lst_2).longitude
    
    # Handle wrap-around
    diff = topo_2 - topo_1
    if diff > 180: diff -= 360
    if diff < -180: diff += 360
    
    topo_speed = diff / (2 * dt)
    
    print(f"{jd_eval:.3f}, {geo_speed:+.6f}, {topo_speed:+.6f}")
