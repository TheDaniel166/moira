import math
from moira.spk_reader import get_reader
from moira.planets import _earth_barycentric
from moira.nutation_2000a import nutation_2000a
from moira.precession import general_precession_in_longitude
from moira.obliquity import mean_obliquity
from moira.nodes import true_node
from moira.coordinates import mat_vec_mul
from moira.constants import DEG2RAD, RAD2DEG

max_diff = 0.0
max_jd = 0
for i in range(400):
    jd = 2400000 + i * 500
    jd_tt = float(jd)
    obliquity = mean_obliquity(jd_tt)
    eps = obliquity * DEG2RAD
    r = get_reader()
    earth = _earth_barycentric(jd_tt)
    moon = r.get_position(301, jd_tt)
    rel = [moon[k] - earth[k] for k in range(3)]
    rot = [
        [1.0, 0.0, 0.0],
        [0.0, math.cos(eps), -math.sin(eps)],
        [0.0, math.sin(eps),  math.cos(eps)],
    ]
    ecl = mat_vec_mul(rot, rel)
    x, y, z = ecl
    # orbit normal via cross product of rel and ecl (approx node direction)
    ix, iy, iz = x, y, z
    dpsi_arcsec, _ = nutation_2000a(jd_tt)
    dpsi_deg = dpsi_arcsec / 3600.0
    eps_j2000 = obliquity * DEG2RAD
    iye_j2000 = iy * math.cos(eps_j2000) + iz * math.sin(eps_j2000)
    lon_j2000 = math.atan2(iye_j2000, ix) * RAD2DEG % 360.0
    scalar_lon = (lon_j2000 + general_precession_in_longitude(jd_tt) + dpsi_deg) % 360.0
    matrix_lon = true_node(jd).longitude
    diff = abs(((matrix_lon - scalar_lon + 180.0) % 360.0 - 180.0) * 3600.0)
    if diff > max_diff:
        max_diff = diff
        max_jd = jd

print(f"Max divergence: {max_diff:.3f}\" at JD {max_jd}")
