from moira import moira_native
import math

def test_single_point(x, y, z):
    lon_bulk, lat_bulk, rad_bulk = moira_native.cartesian_to_spherical_bulk([x], [y], [z])
    
    r = math.sqrt(x*x + y*y + z*z)
    if r < 1e-15:
        lon, lat = 0.0, 0.0
    else:
        lat = math.degrees(math.asin(z/r))
        lon = math.degrees(math.atan2(y, x))
    
    print(f"Point: ({x}, {y}, {z})")
    print(f"Bulk:    lon={lon_bulk[0]}, lat={lat_bulk[0]}, rad={rad_bulk[0]}")
    print(f"Element: lon={lon}, lat={lat}, rad={r}")
    
    lon_diff = abs(lon_bulk[0] - lon)
    print(f"Lon diff: {lon_diff}")

test_single_point(0.0, 0.0, 0.0)
test_single_point(1.0, 1.0, 1.0)
test_single_point(-1.0, 0.0, 0.0)
