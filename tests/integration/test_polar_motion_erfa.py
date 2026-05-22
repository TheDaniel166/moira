import math
import pytest

from moira.coordinates import mat_vec_mul
from moira.corrections import _observer_position_icrf
from moira.polar_motion import PolarMotionRegistry, polar_motion_matrix

erfa = pytest.importorskip("erfa")


_SAMPLE_JD_UTS = (
    2441317.5,  # 1972-01-01
    2451545.0,  # J2000
    2460805.5,  # 2025-05-01
)

_SAMPLE_OBSERVERS = (
    (0.0, 0.0, 0.0, 0.0),
    (51.5, -0.1, 123.0, 45.0),
    (-33.9, 151.2, 280.0, 250.0),
)


def _matrix_max_abs_diff(a, b) -> float:
    return max(abs(float(a[i][j]) - float(b[i][j])) for i in range(3) for j in range(3))


@pytest.mark.integration
@pytest.mark.parametrize("jd_ut", _SAMPLE_JD_UTS)
def test_polar_motion_matrix_matches_erfa_pom00(jd_ut: float) -> None:
    x_p_arcsec, y_p_arcsec = PolarMotionRegistry.polar_motion_at(jd_ut)
    moira_matrix = polar_motion_matrix(x_p_arcsec, y_p_arcsec)
    erfa_matrix = erfa.pom00(
        x_p_arcsec * erfa.DAS2R,
        y_p_arcsec * erfa.DAS2R,
        0.0,
    )

    assert _matrix_max_abs_diff(moira_matrix, erfa_matrix) < 1e-14


@pytest.mark.integration
@pytest.mark.parametrize("jd_ut", _SAMPLE_JD_UTS)
@pytest.mark.parametrize("latitude_deg,longitude_deg,lst_deg,elevation_m", _SAMPLE_OBSERVERS)
def test_observer_position_matches_erfa_polar_motion_rotation(
    jd_ut: float,
    latitude_deg: float,
    longitude_deg: float,
    lst_deg: float,
    elevation_m: float,
) -> None:
    # 1. Compute ITRF coordinates (terrestrial frame) using WGS-84:
    DEG2RAD = 0.017453292519943295
    lat = latitude_deg * DEG2RAD
    lon = longitude_deg * DEG2RAD
    f = 1.0 / 298.257223563
    a = 6378.137  # EARTH_RADIUS_KM
    h = elevation_m / 1000.0
    cos_lat = math.cos(lat)
    sin_lat = math.sin(lat)
    C = 1.0 / math.sqrt(cos_lat**2 + (1.0 - f)**2 * sin_lat**2)
    S = (1.0 - f)**2 * C
    itrf = (
        (a * C + h) * cos_lat * math.cos(lon),
        (a * C + h) * cos_lat * math.sin(lon),
        (a * S + h) * sin_lat,
    )

    # 2. Get polar motion from Registry
    x_p_arcsec, y_p_arcsec = PolarMotionRegistry.polar_motion_at(jd_ut)

    # 3. Rotate by Polar Motion W(t) using ERFA pom00
    erfa_pom = erfa.pom00(
        x_p_arcsec * erfa.DAS2R,
        y_p_arcsec * erfa.DAS2R,
        0.0,
    )
    tirs = mat_vec_mul(
        tuple(tuple(float(value) for value in row) for row in erfa_pom),
        itrf,
    )

    # 4. Rotate by -GST around Z-axis to get TETE
    gast_deg = lst_deg - longitude_deg
    gast_rad = gast_deg * DEG2RAD
    cos_gst = math.cos(gast_rad)
    sin_gst = math.sin(gast_rad)
    tete = (
        tirs[0] * cos_gst - tirs[1] * sin_gst,
        tirs[0] * sin_gst + tirs[1] * cos_gst,
        tirs[2],
    )

    # 5. Rotate from TETE to ICRF/GCRS using transpose of ERFA pnm06a
    from moira.julian import ut_to_tt
    jd_tt = ut_to_tt(jd_ut)
    erfa_pnm = erfa.pnm06a(2400000.5, jd_tt - 2400000.5)

    def _transpose(m):
        return (
            (m[0][0], m[1][0], m[2][0]),
            (m[0][1], m[1][1], m[2][1]),
            (m[0][2], m[1][2], m[2][2]),
        )

    erfa_position = mat_vec_mul(
        _transpose(erfa_pnm),
        tete,
    )

    # 6. Get Moira's observer position (which should perform the same chain)
    moira_position = _observer_position_icrf(
        latitude_deg,
        longitude_deg,
        lst_deg,
        elevation_m,
        jd_ut=jd_ut,
    )

    for moira_value, erfa_value in zip(moira_position, erfa_position):
        assert moira_value == pytest.approx(erfa_value, abs=1e-5)

