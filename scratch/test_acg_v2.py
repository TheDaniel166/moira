
import math
from moira.astrocartography import acg_lines, ACGLine
from moira.constants import Body

def test_acg_features():
    # Mock RA/Dec for one planet
    # RA=0, Dec=10. GMST=0.
    planet_ra_dec = {"Mars": (0.0, 10.0)}
    gmst = 0.0
    
    lines = acg_lines(planet_ra_dec, gmst, lat_step=10.0)
    
    print(f"Computed {len(lines)} features for Mars.")
    for line in lines:
        if line.line_type in ("MC", "IC"):
            print(f"  {line.line_type}: lon={line.longitude}")
        elif line.line_type in ("ZEN", "NAD"):
            print(f"  {line.line_type}: at {line.points[0]}")
        else:
            print(f"  {line.line_type}: {len(line.points)} points")
            
    # Verify 6 features
    assert len(lines) == 6
    # Verify MC/IC
    assert lines[0].longitude == 0.0
    assert lines[1].longitude == 180.0
    # Verify Zenith/Nadir
    assert lines[2].points[0] == (10.0, 0.0) # Zen: (dec, mc_lon)
    assert lines[3].points[0] == (-10.0, 180.0) # Nad: (-dec, ic_lon)
    
def test_lunar_topo():
    # JD for a recent date
    jd_ut = 2460310.5
    # Geocentric RA/Dec at this moment
    # RA: 159.11843, Dec: 12.62749
    planet_ra_dec = {Body.MOON: (159.11843, 12.62749)}
    gmst = 215.22739 # Approx GAST
    
    # 1. Without JD (Geocentric fallback)
    lines_geo = acg_lines(planet_ra_dec, gmst, lat_step=10.0)
    # 2. With JD (Topocentric)
    lines_topo = acg_lines(planet_ra_dec, gmst, lat_step=10.0, jd_ut=jd_ut)
    
    asc_geo = next(l for l in lines_geo if l.line_type == "ASC")
    asc_topo = next(l for l in lines_topo if l.line_type == "ASC")
    
    # Compare longitude at Latitude 40N
    lon_geo = next(p[1] for p in asc_geo.points if p[0] == 41.0) # Sampled at -89 + i*10: -89, -79... -9, 1, 11, 21, 31, 41
    lon_topo = next(p[1] for p in asc_topo.points if p[0] == 41.0)
    
    diff = (lon_topo - lon_geo + 180) % 360 - 180
    print(f"Lunar ASC Longitude Diff at Lat 41N: {diff:.5f}°")
    assert abs(diff) > 0.5 # Should be around 1.1°

if __name__ == "__main__":
    test_acg_features()
    test_lunar_topo()
    print("All tests passed.")
