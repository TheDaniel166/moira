from pathlib import Path

import pytest

from moira.asteroids import _AsteroidKernel
from moira.daf_writer import (
    _MAX_SUMMARIES,
    _RECORD_SIZE,
    _build_name_record,
    _build_summary_record,
    _build_type13_payload,
    write_spk_type13,
)


def _sample_states(n: int):
    return [[float(axis * 100 + idx) for idx in range(n)] for axis in range(6)]


def _sample_epochs(n: int):
    return [2451545.0 + idx for idx in range(n)]


def _linear_states(
    epochs_jd: list[float],
    position0_km: tuple[float, float, float],
    velocity_km_per_day: tuple[float, float, float],
):
    states = [[0.0] * len(epochs_jd) for _ in range(6)]
    jd0 = epochs_jd[0]
    for idx, jd in enumerate(epochs_jd):
        dt_days = jd - jd0
        for axis in range(3):
            states[axis][idx] = position0_km[axis] + velocity_km_per_day[axis] * dt_days
            states[axis + 3][idx] = velocity_km_per_day[axis] / 86400.0
    return states


def test_build_type13_payload_rejects_non_increasing_epochs() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        _build_type13_payload(
            _sample_states(3),
            [2451545.0, 2451546.0, 2451546.0],
            window_size=3,
        )


def test_build_type13_payload_rejects_even_or_oversized_window() -> None:
    with pytest.raises(ValueError, match="must be odd"):
        _build_type13_payload(_sample_states(3), _sample_epochs(3), window_size=2)

    with pytest.raises(ValueError, match="cannot exceed"):
        _build_type13_payload(_sample_states(3), _sample_epochs(3), window_size=5)


def test_single_record_builders_reject_overflow() -> None:
    summaries = [(0.0, 1.0, 10, 1, 1, 13, 385, 400)] * (_MAX_SUMMARIES + 1)
    names = ["X"] * (_MAX_SUMMARIES + 1)

    with pytest.raises(ValueError, match="at most"):
        _build_summary_record(summaries)

    with pytest.raises(ValueError, match="at most"):
        _build_name_record(names)


def test_write_spk_type13_rejects_too_many_bodies() -> None:
    bodies = [
        {
            "naif_id": 1000 + idx,
            "states": _sample_states(3),
            "epochs_jd": _sample_epochs(3),
            "window_size": 3,
        }
        for idx in range(_MAX_SUMMARIES + 1)
    ]

    with pytest.raises(ValueError, match="at most"):
        write_spk_type13("ignored.bsp", bodies)


def test_write_spk_type13_writes_record_aligned_file(tmp_path: Path) -> None:
    output = tmp_path / "sample.bsp"
    write_spk_type13(
        output,
        [
            {
                "naif_id": 2002060,
                "states": _sample_states(3),
                "epochs_jd": _sample_epochs(3),
                "window_size": 3,
                "name": "Chiron",
            }
        ],
    )

    assert output.exists()
    assert output.stat().st_size % _RECORD_SIZE == 0


def test_write_spk_type13_round_trips_interstellar_style_bodies(tmp_path: Path) -> None:
    output = tmp_path / "interstellar.bsp"
    epochs = [2460400.0, 2460401.0, 2460402.0, 2460403.0, 2460404.0]
    oumuamua_states = _linear_states(
        epochs,
        position0_km=(3.2e9, -7.5e8, 4.1e8),
        velocity_km_per_day=(5.7e7, 1.9e7, -8.0e6),
    )
    borisov_states = _linear_states(
        epochs,
        position0_km=(-2.8e9, 1.6e9, 9.0e8),
        velocity_km_per_day=(-4.4e7, 2.3e7, 1.1e7),
    )

    bodies = [
        {
            "naif_id": 20000001,
            "name": "1I Oumuamua",
            "center": 10,
            "states": oumuamua_states,
            "epochs_jd": epochs,
            "window_size": 5,
        },
        {
            "naif_id": 20000002,
            "name": "2I Borisov",
            "center": 10,
            "states": borisov_states,
            "epochs_jd": epochs,
            "window_size": 5,
        },
    ]
    write_spk_type13(output, bodies, locifn="MOIRA INTERSTELLAR TEST")

    kernel = _AsteroidKernel(output)
    try:
        assert kernel.has_body(20000001) is True
        assert kernel.has_body(20000002) is True
        assert kernel.segment_center(20000001) == 10
        assert kernel.segment_center(20000002) == 10

        # Written node epochs should round-trip exactly for linear trajectories.
        for idx, jd in enumerate(epochs):
            oumuamua = kernel.position(20000001, jd)
            borisov = kernel.position(20000002, jd)
            assert oumuamua == pytest.approx(
                tuple(axis[idx] for axis in oumuamua_states[:3]),
                abs=1e-6,
            )
            assert borisov == pytest.approx(
                tuple(axis[idx] for axis in borisov_states[:3]),
                abs=1e-6,
            )

        # Midpoint interpolation should also be exact for the linear test corpus.
        midpoint = 2460402.5
        assert kernel.position(20000001, midpoint) == pytest.approx(
            (
                oumuamua_states[0][0] + (midpoint - epochs[0]) * 5.7e7,
                oumuamua_states[1][0] + (midpoint - epochs[0]) * 1.9e7,
                oumuamua_states[2][0] + (midpoint - epochs[0]) * -8.0e6,
            ),
            abs=1e-3,
        )
        assert kernel.position(20000002, midpoint) == pytest.approx(
            (
                borisov_states[0][0] + (midpoint - epochs[0]) * -4.4e7,
                borisov_states[1][0] + (midpoint - epochs[0]) * 2.3e7,
                borisov_states[2][0] + (midpoint - epochs[0]) * 1.1e7,
            ),
            abs=1e-3,
        )
    finally:
        kernel.close()
