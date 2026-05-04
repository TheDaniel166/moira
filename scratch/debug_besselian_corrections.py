import math
import numpy as _np
from moira.sky.eclipse import EclipseCalculator
from moira.solar_cartography import _compute_besselian_sample
from moira.planets import planet_at
from moira.constants import Body, EARTH_RADIUS_KM, SUN_RADIUS_KM, MOON_RADIUS_KM
from moira.spk_reader import get_reader
from moira.julian import local_sidereal_time

def debug_2017():
    # NASA Greatest Eclipse: 18:25:31.8 UT1 (18:26:40.4 TD)
    jd_ut = 2457987.267729 # 18:25:31.8 UT
    reader = get_reader()
    calc = EclipseCalculator(reader)
    
    print("--- APPARENT=TRUE (Default) ---")
    s_app = _compute_besselian_sample(calc, jd_ut)
    print(f"x: {s_app.x:.6f}, y: {s_app.y:.6f}, l1: {s_app.l1_earth_radii:.6f}, l2: {s_app.l2_earth_radii:.6f}")
    
    print("\n--- TRUE EQUATOR OF DATE (NASA Frame) ---")
    # Manually compute with apparent=False and true equator of date
    sun_geo = planet_at(Body.SUN, jd_ut, reader=reader, frame="cartesian", apparent=False)
    moon_geo = planet_at(Body.MOON, jd_ut, reader=reader, frame="cartesian", apparent=False)
    
    from moira.julian import ut_to_tt
    from moira.coordinates import precession_matrix_equatorial, nutation_matrix_equatorial, mat_vec_mul
    jd_tt = ut_to_tt(jd_ut)
    prec = precession_matrix_equatorial(jd_tt)
    nut = nutation_matrix_equatorial(jd_tt)
    # True North Pole of Date in ICRF
    def _transpose(mat):
        return tuple(zip(*mat))
    
    # North pole in date frame z_d = (0,0,1).
    # z_d = Nut @ Prec @ z_icrf  => z_icrf = Inv(Nut @ Prec) @ z_d = Transpose(Prec) @ Transpose(Nut) @ z_d
    nut_t = _transpose(nut)
    prec_t = _transpose(prec)
    z_icrf = mat_vec_mul(prec_t, mat_vec_mul(nut_t, (0,0,1)))
    north_pole = _np.array(z_icrf)
    
    sun_xyz = _np.array([sun_geo.x, sun_geo.y, sun_geo.z])
    moon_xyz = _np.array([moon_geo.x, moon_geo.y, moon_geo.z])
    axis = moon_xyz - sun_xyz
    axis /= _np.linalg.norm(axis)
    
    east = _np.cross(north_pole, axis)
    east /= _np.linalg.norm(east)
    north = _np.cross(axis, east)
    
    dist_to_plane = -float(_np.dot(moon_xyz, axis))
    plane_point = moon_xyz + (dist_to_plane * axis)
    x = float(_np.dot(plane_point, east) / EARTH_RADIUS_KM)
    y = float(_np.dot(plane_point, north) / EARTH_RADIUS_KM)
    
    # NASA Constants (Espenak)
    R_SUN = 696000.0
    R_MOON_P = 1737.97 # k = 0.2724880
    R_MOON_U = 1736.65 # k = 0.2722810
    R_EARTH = 6378.14
    
    sun_moon_dist = float(_np.linalg.norm(sun_xyz - moon_xyz))
    tan_f1 = (R_SUN + R_MOON_P) / sun_moon_dist
    tan_f2 = (R_SUN - R_MOON_U) / sun_moon_dist
    l1 = (R_MOON_P + (dist_to_plane * tan_f1)) / R_EARTH
    l2 = (R_MOON_U - (dist_to_plane * tan_f2)) / R_EARTH
    
    print(f"x: {x:.6f}, y: {y:.6f}, l1: {l1:.6f}, l2: {l2:.6f}")
    print(f"tan_f1: {tan_f1:.7f}, tan_f2: {tan_f2:.7f}")
    
    print("\nNASA GROUND TRUTH (2017-08-21 18:26:40 UT):")
    print("x: 0.000000, y: 0.000000 (roughly at greatest)")
    print("tan_f1: 0.0046115, tan_f2: 0.0045885, l1: 0.54209, l2: -0.00039")

if __name__ == "__main__":
    debug_2017()
