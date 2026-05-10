from pathlib import Path

import pytest

from moira.coordinates import mat_vec_mul, vec_norm
from moira.corrections import (
    _observer_position_icrf,
    _observer_velocity_icrf,
    apply_diurnal_aberration,
    topocentric_correction,
)
from moira.polar_motion import PolarMotionRegistry, polar_motion_matrix


def _reset_registry(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(PolarMotionRegistry, "_path", path)
    monkeypatch.setattr(PolarMotionRegistry, "_data", None)
    monkeypatch.setattr(PolarMotionRegistry, "_mjds", None)


def test_polar_motion_registry_loads_bundled_data() -> None:
    x_p, y_p = PolarMotionRegistry.polar_motion_at(2451545.0)

    assert PolarMotionRegistry._data
    assert len(PolarMotionRegistry._data) > 1000
    assert abs(x_p) < 1.0
    assert abs(y_p) < 1.0


def test_polar_motion_registry_missing_file_returns_zero_and_warns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _reset_registry(monkeypatch, tmp_path / "missing.txt")

    with caplog.at_level("WARNING"):
        x_p, y_p = PolarMotionRegistry.polar_motion_at(2451545.0)

    assert (x_p, y_p) == (0.0, 0.0)
    assert "Polar motion data file is missing" in caplog.text


def test_polar_motion_registry_skips_malformed_lines_and_clamps(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = tmp_path / "iers_polar_motion.txt"
    path.write_text(
        "\n".join(
            [
                "# test data",
                "58000 0.100 0.200",
                "bad line",
                "58001 1.500 -2.000",
            ]
        ),
        encoding="utf-8",
    )
    _reset_registry(monkeypatch, path)

    with caplog.at_level("WARNING"):
        x0, y0 = PolarMotionRegistry.polar_motion_at(2400000.5 + 58000.0)
        x1, y1 = PolarMotionRegistry.polar_motion_at(2400000.5 + 58001.0)

    assert (x0, y0) == pytest.approx((0.1, 0.2))
    assert (x1, y1) == pytest.approx((1.0, -1.0))
    assert "Skipping malformed polar motion line" in caplog.text
    assert "Clamping out-of-bounds polar motion" in caplog.text


def test_polar_motion_registry_interpolates_and_clamps_edges(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "iers_polar_motion.txt"
    path.write_text(
        "\n".join(
            [
                "58000 0.100 0.200",
                "58010 0.300 0.600",
            ]
        ),
        encoding="utf-8",
    )
    _reset_registry(monkeypatch, path)

    before = PolarMotionRegistry.polar_motion_at(2400000.5 + 57999.0)
    exact = PolarMotionRegistry.polar_motion_at(2400000.5 + 58000.0)
    middle = PolarMotionRegistry.polar_motion_at(2400000.5 + 58005.0)
    after = PolarMotionRegistry.polar_motion_at(2400000.5 + 58011.0)

    assert before == pytest.approx((0.1, 0.2))
    assert exact == pytest.approx((0.1, 0.2))
    assert middle == pytest.approx((0.2, 0.4))
    assert after == pytest.approx((0.3, 0.6))


def test_polar_motion_matrix_zero_is_identity() -> None:
    assert polar_motion_matrix(0.0, 0.0) == (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )


def test_polar_motion_matrix_preserves_vector_norm() -> None:
    matrix = polar_motion_matrix(0.1, -0.2)
    vector = (6378.137, -1200.0, 4300.0)
    rotated = mat_vec_mul(matrix, vector)

    assert vec_norm(rotated) == pytest.approx(vec_norm(vector), rel=1e-14, abs=1e-14)


def test_observer_position_and_velocity_preserve_legacy_path_without_jd_ut(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(PolarMotionRegistry, "polar_motion_at", classmethod(lambda cls, jd_ut: (0.3, -0.2)))

    legacy = _observer_position_icrf(51.5, -0.1, 123.0, 45.0)
    explicit_none = _observer_position_icrf(51.5, -0.1, 123.0, 45.0, jd_ut=None)

    assert explicit_none == pytest.approx(legacy)


def test_topocentric_and_diurnal_apply_polar_motion_when_jd_ut_is_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(PolarMotionRegistry, "polar_motion_at", classmethod(lambda cls, jd_ut: (0.3, -0.2)))

    xyz = (149597870.7, 1.0e5, 2.0e5)
    topo_legacy = topocentric_correction(xyz, 51.5, -0.1, 123.0, 45.0)
    topo_polar = topocentric_correction(xyz, 51.5, -0.1, 123.0, 45.0, jd_ut=2451545.0)

    aberr_legacy = apply_diurnal_aberration(xyz, 51.5, -0.1, 123.0, 45.0)
    aberr_polar = apply_diurnal_aberration(xyz, 51.5, -0.1, 123.0, 45.0, jd_ut=2451545.0)

    topo_delta = max(abs(a - b) for a, b in zip(topo_polar, topo_legacy))
    aberr_delta = max(abs(a - b) for a, b in zip(aberr_polar, aberr_legacy))

    assert topo_delta > 1e-6
    assert aberr_delta > 1e-12


def test_observer_velocity_uses_polar_motion_corrected_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(PolarMotionRegistry, "polar_motion_at", classmethod(lambda cls, jd_ut: (0.3, -0.2)))

    legacy_position = _observer_position_icrf(12.0, 30.0, 80.0, 0.0)
    polar_position = _observer_position_icrf(12.0, 30.0, 80.0, 0.0, jd_ut=2451545.0)

    legacy_velocity = _observer_velocity_icrf(legacy_position)
    polar_velocity = _observer_velocity_icrf(polar_position)

    assert polar_position != pytest.approx(legacy_position)
    assert polar_velocity != pytest.approx(legacy_velocity)
    assert polar_velocity[2] == pytest.approx(0.0, abs=1e-15)
