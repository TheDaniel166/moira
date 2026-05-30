"""
Test of Topocentric Jitter in Event Solvers
Target: moira.stations
Threat: False station events caused by observer rotation (parallax-driven micro-oscillations).
"""

import math
import pytest

from moira.constants import Body
from moira.planets import planet_at
from moira.julian import julian_day, local_sidereal_time
from moira.stations import find_stations

def _compute_numerical_velocity(body: str, jd: float, lat: float, lon: float, elev: float, dt_days: float = 1.0/1440.0) -> float:
    """Compute apparent topocentric velocity in degrees per day using finite difference."""
    lst_1 = local_sidereal_time(jd - dt_days, lon)
    topo_1 = planet_at(body, jd - dt_days, observer_lat=lat, observer_lon=lon, observer_elev_m=elev, lst_deg=lst_1).longitude
    
    lst_2 = local_sidereal_time(jd + dt_days, lon)
    topo_2 = planet_at(body, jd + dt_days, observer_lat=lat, observer_lon=lon, observer_elev_m=elev, lst_deg=lst_2).longitude
    
    diff = topo_2 - topo_1
    if diff > 180: diff -= 360
    if diff < -180: diff += 360
    
    return diff / (2 * dt_days)


def test_station_solver_is_immune_to_topocentric_micro_oscillations() -> None:
    """
    Prove that Earth's rotation creates physical parallax micro-oscillations
    (multiple sign flips in topocentric velocity) near a shallow station, but
    the engine's station solver uses true geocentric astrometric velocity to
    return exactly one clean event, averting false solver convergence.
    """
    # Mars retrograde station around Jan/Feb 2025
    jd_start = julian_day(2025, 2, 20, 0.0)
    jd_end = julian_day(2025, 3, 1, 0.0)

    # Find the station via the engine
    events = find_stations(Body.MARS, jd_start, jd_end)
    assert len(events) == 1, "Engine should find exactly one station event"
    station = events[0]
    
    assert station.station_type == "direct"
    
    # Analyze the velocity over a 4-day window centered on the station
    jd_center = station.jd_ut
    
    geo_sign_flips = 0
    topo_sign_flips = 0
    
    prev_geo_sign = None
    prev_topo_sign = None
    
    lat = 0.0 # Equator maximizes rotational velocity
    lon = 0.0
    elev = 0.0
    
    # Sweep across 4 days in 1-hour increments
    for i in range(-48, 48):
        jd_eval = jd_center + i / 24.0
        
        # 1. Geocentric velocity
        geo_speed = planet_at(Body.MARS, jd_eval).speed
        geo_sign = 1 if geo_speed > 0 else -1
        
        if prev_geo_sign is not None and geo_sign != prev_geo_sign:
            geo_sign_flips += 1
            
        # 2. Topocentric numerical velocity
        topo_speed = _compute_numerical_velocity(Body.MARS, jd_eval, lat, lon, elev)
        topo_sign = 1 if topo_speed > 0 else -1
        
        if prev_topo_sign is not None and topo_sign != prev_topo_sign:
            topo_sign_flips += 1
            
        prev_geo_sign = geo_sign
        prev_topo_sign = topo_sign

    # The geocentric velocity must cross zero exactly once
    assert geo_sign_flips == 1, "Geocentric velocity must have exactly one clean zero-crossing."
    
    # The topocentric velocity MUST exhibit jitter (multiple zero crossings) due to Earth's rotation
    # For Mars at the equator, diurnal parallax introduces ~0.03 deg/day oscillations,
    # causing it to flip signs several times when true speed is near zero.
    assert topo_sign_flips > 1, f"Topocentric velocity must exhibit micro-oscillations, found {topo_sign_flips} flips."
    
    # Assert that despite the topocentric jitter, the engine's solver is completely stable
    assert len(find_stations(Body.MARS, jd_center - 2, jd_center + 2)) == 1

def test_observer_sweeps_preserve_velocity_sign_outside_parallax_margin() -> None:
    """
    Sweep across extreme observer locations to verify that topocentric velocity
    agrees with barycentric/geocentric velocity outside of the narrow temporal
    margin where parallax exceeds planetary speed (the micro-oscillation zone).
    """
    # Evaluate at a time where Mars is moving slowly but definitely direct
    # (e.g. 10 days after the station)
    jd_eval = julian_day(2025, 3, 6, 0.0)
    
    geo_speed = planet_at(Body.MARS, jd_eval).speed
    geo_sign = 1 if geo_speed > 0 else -1
    
    # Assert it's away from the immediate zero-crossing
    assert abs(geo_speed) > 0.05
    
    latitudes = [-90.0, -45.0, 0.0, 45.0, 90.0]
    longitudes = [0.0, 90.0, 180.0, 270.0]
    altitudes = [0.0, 2500.0, 5000.0]
    
    for lat in latitudes:
        for lon in longitudes:
            for elev in altitudes:
                topo_speed = _compute_numerical_velocity(Body.MARS, jd_eval, lat, lon, elev)
                topo_sign = 1 if topo_speed > 0 else -1
                
                # Assert sign(geocentric_vel) == sign(topocentric_vel) 
                # away from the shallow parallax-driven margin
                assert topo_sign == geo_sign, (
                    f"Sign mismatch at lat={lat}, lon={lon}, elev={elev}. "
                    f"Geo={geo_speed:+.4f}, Topo={topo_speed:+.4f}"
                )


