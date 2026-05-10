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
    x_p_arcsec, y_p_arcsec = PolarMotionRegistry.polar_motion_at(jd_ut)
    legacy_position = _observer_position_icrf(
        latitude_deg,
        longitude_deg,
        lst_deg,
        elevation_m,
    )
    erfa_matrix = erfa.pom00(
        x_p_arcsec * erfa.DAS2R,
        y_p_arcsec * erfa.DAS2R,
        0.0,
    )
    erfa_position = mat_vec_mul(
        tuple(tuple(float(value) for value in row) for row in erfa_matrix),
        legacy_position,
    )
    moira_position = _observer_position_icrf(
        latitude_deg,
        longitude_deg,
        lst_deg,
        elevation_m,
        jd_ut=jd_ut,
    )

    for moira_value, erfa_value in zip(moira_position, erfa_position):
        assert moira_value == pytest.approx(erfa_value, abs=1e-12)
