import os
import random

from moira.dispatch import MoiraBackend, settings
from moira.julian import (
    apparent_sidereal_time as py_apparent_sidereal_time,
    earth_rotation_angle as py_earth_rotation_angle,
    greenwich_mean_sidereal_time as py_greenwich_mean_sidereal_time,
)
from moira.moira_native import (
    apparent_sidereal_time as native_apparent_sidereal_time,
    earth_rotation_angle as native_earth_rotation_angle,
    greenwich_mean_sidereal_time as native_greenwich_mean_sidereal_time,
)


def test_sidereal_phase1_parity():
    random.seed(314159)

    for _ in range(1000):
        jd_ut = random.uniform(0.0, 5_000_000.0)
        # Distinct TT coordinate: Delta-T up to ~1 day exposes any use of UT where TT belongs.
        jd_tt = jd_ut + random.uniform(-1.0, 1.0)
        dpsi = random.uniform(-1.0, 1.0)
        obliquity = random.uniform(20.0, 25.0)

        py_era = py_earth_rotation_angle(jd_ut)
        native_era = native_earth_rotation_angle(jd_ut)
        assert abs(py_era - native_era) < 1e-12

        py_gmst = py_greenwich_mean_sidereal_time(jd_ut, jd_tt)
        native_gmst = native_greenwich_mean_sidereal_time(jd_ut, jd_tt)
        assert abs(py_gmst - native_gmst) < 1e-12

        # The native twin has no obliquity argument: the equation of the equinoxes
        # uses the IAU 2006 mean obliquity (SOFA iauEe00), so the Python argument is inert.
        py_gast = py_apparent_sidereal_time(jd_ut, dpsi, obliquity, jd_tt)
        native_gast = native_apparent_sidereal_time(jd_ut, jd_tt, dpsi)
        assert abs(py_gast - native_gast) < 1e-12


def test_sidereal_phase1_edge_audit():
    samples = [
        (2451545.0, 2451545.0 + 64.184 / 86400.0, 0.0, 23.4392911),
        (0.0, 0.0 + 0.2, -0.25, 23.0),
        (2299160.0, 2299160.0 + 0.0005, 0.5, 24.5),
        (1721058.0, 1721058.0 + 0.12, -0.5, 22.0),
    ]

    for jd_ut, jd_tt, dpsi, obliquity in samples:
        assert abs(py_earth_rotation_angle(jd_ut) - native_earth_rotation_angle(jd_ut)) < 1e-12
        assert abs(py_greenwich_mean_sidereal_time(jd_ut, jd_tt) - native_greenwich_mean_sidereal_time(jd_ut, jd_tt)) < 1e-12
        assert abs(py_apparent_sidereal_time(jd_ut, dpsi, obliquity, jd_tt) - native_apparent_sidereal_time(jd_ut, jd_tt, dpsi)) < 1e-12


def test_sidereal_accelerated_two_scale_core_matches_python_core():
    from moira import julian

    jd_ut, jd_tt, dpsi = 2461041.5, 2461041.5 + 69.184 / 86400.0, 0.0031
    python_gmst = julian._greenwich_mean_sidereal_time_at_tt(jd_ut, jd_tt)
    python_gast = julian._apparent_sidereal_time_at_tt(jd_ut, jd_tt, dpsi)
    os.environ["MOIRA_ACCELERATE"] = "1"
    settings.__init__()
    try:
        assert settings.current_backend() == MoiraBackend.NATIVE
        assert abs(julian._greenwich_mean_sidereal_time_at_tt(jd_ut, jd_tt) - python_gmst) < 1e-12
        assert abs(julian._apparent_sidereal_time_at_tt(jd_ut, jd_tt, dpsi) - python_gast) < 1e-12
        # The public wrappers resolve TT once and then take the same accelerated core.
        assert abs(py_apparent_sidereal_time(jd_ut, dpsi, 0.0, jd_tt) - python_gast) < 1e-12
    finally:
        os.environ["MOIRA_ACCELERATE"] = "0"
        settings.__init__()
        assert settings.current_backend() == MoiraBackend.PYTHON


def test_sidereal_dispatcher_integration():
    from moira import moira_native

    original = moira_native.earth_rotation_angle
    os.environ["MOIRA_ACCELERATE"] = "1"
    settings.__init__()

    try:
        moira_native.earth_rotation_angle = lambda jd_ut: 123.456789
        assert py_earth_rotation_angle(2451545.0) == 123.456789
    finally:
        moira_native.earth_rotation_angle = original
        os.environ["MOIRA_ACCELERATE"] = "0"
        settings.__init__()
        assert settings.current_backend() == MoiraBackend.PYTHON
