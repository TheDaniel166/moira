import math
from moira.spk_reader import get_reader
from moira.nodes import _TRUE_NODE_STEP, true_node
from moira.obliquity import mean_obliquity
from moira.obliquity import nutation as _nutation
from moira.precession import general_precession_in_longitude
from moira.julian import ut_to_tt
from moira.constants import DEG2RAD, RAD2DEG
from moira.coordinates import vec_sub

# Helper from test: approx year for UT->TT
def _node_approx_year(jd):
    T = (jd - 2451545.0) / 36525.0
    year = 2000.0 + T * 100.0
    return (year,)

reader = get_reader()

max_diff = 0.0
max_jd = 0
# Sample 200 points across the range 2400000-2600000
for i in range(201):
    jd = 2400000.0 + i * 1000.0
    year, *_ = _node_approx_year(jd)
    jd_tt = ut_to_tt(jd, year)
    dpsi_deg, deps_deg = _nutation(jd_tt)
    obliquity = mean_obliquity(jd_tt) + deps_deg
    eps = obliquity * DEG2RAD

    def moon_geo(t):
        emb_moon = reader.position(3, 301, t)
        emb_earth = reader.position(3, 399, t)
        return vec_sub(emb_moon, emb_earth)

    r1 = moon_geo(jd_tt - _TRUE_NODE_STEP)
    r2 = moon_geo(jd_tt + _TRUE_NODE_STEP)

    nx = r1[1]*r2[2] - r1[2]*r2[1]
    ny = r1[2]*r2[0] - r1[0]*r2[2]
    nz = r1[0]*r2[1] - r1[1]*r2[0]

    ex = 0.0
    ey = -math.sin(eps)
    ez = math.cos(eps)

    ix = ey*nz - ez*ny
    iy = ez*nx - ex*nz
    iz = ex*ny - ey*nx

    eps_j2000 = obliquity * DEG2RAD
    iye_j2000 = iy * math.cos(eps_j2000) + iz * math.sin(eps_j2000)
    ixe_j2000 = ix
    lon_j2000 = math.atan2(iye_j2000, ixe_j2000) * RAD2DEG % 360.0
    scalar_lon = (lon_j2000 + general_precession_in_longitude(jd_tt) + dpsi_deg) % 360.0

    matrix_lon = true_node(jd).longitude
    diff = abs(((matrix_lon - scalar_lon + 180.0) % 360.0 - 180.0) * 3600.0)
    if diff > max_diff:
        max_diff = diff
        max_jd = jd

print(f"Max divergence: {max_diff:.3f}\" at JD {max_jd}")
