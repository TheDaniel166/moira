from pathlib import Path

import pytest

from moira.asteroids import (
    ASTEROID_NAIF,
    _AsteroidKernel,
    _ensure_quaternary_kernel,
    _ensure_tertiary_kernel,
)
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


def _quadratic_states(
    epochs_jd: list[float],
    position0_km: tuple[float, float, float],
    velocity_km_per_day: tuple[float, float, float],
    acceleration_km_per_day2: tuple[float, float, float],
):
    states = [[0.0] * len(epochs_jd) for _ in range(6)]
    jd0 = epochs_jd[0]
    for idx, jd in enumerate(epochs_jd):
        dt_days = jd - jd0
        for axis in range(3):
            position = (
                position0_km[axis]
                + velocity_km_per_day[axis] * dt_days
                + 0.5 * acceleration_km_per_day2[axis] * dt_days * dt_days
            )
            velocity_day = velocity_km_per_day[axis] + acceleration_km_per_day2[axis] * dt_days
            states[axis][idx] = position
            states[axis + 3][idx] = velocity_day / 86400.0
    return states


def _quadratic_position(
    jd: float,
    jd0: float,
    position0_km: tuple[float, float, float],
    velocity_km_per_day: tuple[float, float, float],
    acceleration_km_per_day2: tuple[float, float, float],
) -> tuple[float, float, float]:
    dt_days = jd - jd0
    return tuple(
        position0_km[axis]
        + velocity_km_per_day[axis] * dt_days
        + 0.5 * acceleration_km_per_day2[axis] * dt_days * dt_days
        for axis in range(3)
    )


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


@pytest.mark.parametrize("window_size", [3, 5, 7])
def test_write_spk_type13_preserves_quadratic_trajectory_with_irregular_epochs(
    tmp_path: Path,
    window_size: int,
) -> None:
    epochs = [
        2460400.00,
        2460400.50,
        2460401.25,
        2460402.75,
        2460405.00,
        2460408.50,
        2460413.00,
    ]
    position0 = (1.7e9, -2.1e9, 6.0e8)
    velocity = (2.4e7, -1.3e7, 5.5e6)
    acceleration = (1.1e6, 4.0e5, -2.5e5)
    states = _quadratic_states(epochs, position0, velocity, acceleration)

    output = tmp_path / f"quadratic_ws{window_size}.bsp"
    write_spk_type13(
        output,
        [
            {
                "naif_id": 29999990 + window_size,
                "name": f"Quadratic-{window_size}",
                "center": 10,
                "states": states,
                "epochs_jd": epochs,
                "window_size": window_size,
            }
        ],
        locifn=f"MOIRA QUADRATIC WS{window_size}",
    )

    kernel = _AsteroidKernel(output)
    naif_id = 29999990 + window_size
    try:
        off_node_samples = [2460400.25, 2460401.75, 2460406.25, 2460410.50]
        for jd in epochs + off_node_samples:
            expected = _quadratic_position(jd, epochs[0], position0, velocity, acceleration)
            result = kernel.position(naif_id, jd)
            assert result == pytest.approx(expected, abs=1e-3), (window_size, jd)
    finally:
        kernel.close()


def test_write_spk_type13_preserves_multiple_distinct_regimes_in_one_kernel(tmp_path: Path) -> None:
    epochs_linear = [2460300.0, 2460301.0, 2460302.0, 2460303.0, 2460304.0]
    epochs_quadratic = [2460500.0, 2460500.4, 2460501.1, 2460502.6, 2460504.8]

    bodies = [
        {
            "naif_id": 21000001,
            "name": "Hyperbolic-A",
            "center": 10,
            "states": _linear_states(
                epochs_linear,
                position0_km=(4.5e9, -1.2e9, 7.0e8),
                velocity_km_per_day=(6.2e7, 2.8e7, -1.3e7),
            ),
            "epochs_jd": epochs_linear,
            "window_size": 5,
        },
        {
            "naif_id": 21000002,
            "name": "Curved-B",
            "center": 10,
            "states": _quadratic_states(
                epochs_quadratic,
                position0_km=(-3.0e9, 2.4e9, -9.0e8),
                velocity_km_per_day=(-3.8e7, 1.1e7, 9.0e6),
                acceleration_km_per_day2=(7.5e5, -2.0e5, 1.0e5),
            ),
            "epochs_jd": epochs_quadratic,
            "window_size": 5,
        },
    ]

    output = tmp_path / "multi_regime.bsp"
    write_spk_type13(output, bodies, locifn="MOIRA MULTI REGIME TEST")
    kernel = _AsteroidKernel(output)
    try:
        assert kernel.list_naif_ids() == [21000001, 21000002]
        assert kernel.position(21000001, 2460302.5) == pytest.approx(
            (
                4.5e9 + 2.5 * 6.2e7,
                -1.2e9 + 2.5 * 2.8e7,
                7.0e8 + 2.5 * -1.3e7,
            ),
            abs=1e-3,
        )
        assert kernel.position(21000002, 2460503.3) == pytest.approx(
            _quadratic_position(
                2460503.3,
                epochs_quadratic[0],
                (-3.0e9, 2.4e9, -9.0e8),
                (-3.8e7, 1.1e7, 9.0e6),
                (7.5e5, -2.0e5, 1.0e5),
            ),
            abs=1e-3,
        )
    finally:
        kernel.close()


@pytest.mark.requires_ephemeris
def test_write_spk_type13_reproduces_centaurs_kernel_segments(tmp_path: Path) -> None:
    source_kernel = _ensure_tertiary_kernel()
    if source_kernel is None:
        pytest.skip("centaurs.bsp not available")

    names = ("Chiron", "Pholus", "Nessus")
    bodies = []
    source_segments = {}
    for segment in source_kernel._kernel.segments:
        if segment.target in {ASTEROID_NAIF[name] for name in names}:
            source_segments[segment.target] = segment

    for name in names:
        naif_id = ASTEROID_NAIF[name]
        segment = source_segments[naif_id]
        states, epochs_jd, window_size = segment._data
        bodies.append(
            {
                "naif_id": naif_id,
                "name": name,
                "center": segment.center,
                "frame": segment.frame,
                "states": states,
                "epochs_jd": epochs_jd,
                "window_size": window_size,
            }
        )

    rebuilt_path = tmp_path / "centaurs_rebuilt.bsp"
    write_spk_type13(rebuilt_path, bodies, locifn="MOIRA CENTAURS REBUILD")
    rebuilt_kernel = _AsteroidKernel(rebuilt_path)

    try:
        for name in names:
            naif_id = ASTEROID_NAIF[name]
            segment = source_segments[naif_id]
            states, epochs_jd, _window_size = segment._data

            assert rebuilt_kernel.has_body(naif_id) is True
            assert rebuilt_kernel.segment_center(naif_id) == segment.center

            sample_jds = [epochs_jd[0], epochs_jd[len(epochs_jd) // 2], epochs_jd[-1]]
            if len(epochs_jd) >= 2:
                midpoint_index = min(len(epochs_jd) // 2, len(epochs_jd) - 2)
                sample_jds.append((epochs_jd[midpoint_index] + epochs_jd[midpoint_index + 1]) / 2.0)

            for jd in sample_jds:
                original = source_kernel.position(naif_id, jd)
                rebuilt = rebuilt_kernel.position(naif_id, jd)
                assert rebuilt == pytest.approx(original, abs=1e-6), (name, jd)

            # Node epochs should also reproduce the original embedded state vectors exactly.
            for idx in (0, len(epochs_jd) // 2, len(epochs_jd) - 1):
                rebuilt = rebuilt_kernel.position(naif_id, epochs_jd[idx])
                expected = tuple(axis[idx] for axis in states[:3])
                assert rebuilt == pytest.approx(expected, abs=1e-6), (name, idx)
    finally:
        rebuilt_kernel.close()


@pytest.mark.requires_ephemeris
def test_write_spk_type13_reproduces_minor_bodies_kernel_segments(tmp_path: Path) -> None:
    source_kernel = _ensure_quaternary_kernel()
    if source_kernel is None:
        pytest.skip("minor_bodies.bsp not available")

    names = ("Pandora", "Amor", "Icarus")
    target_ids = {ASTEROID_NAIF[name] for name in names}
    bodies = []
    source_segments = {}
    for segment in source_kernel._kernel.segments:
        if segment.target in target_ids:
            source_segments[segment.target] = segment

    for name in names:
        naif_id = ASTEROID_NAIF[name]
        segment = source_segments[naif_id]
        states, epochs_jd, window_size = segment._data
        bodies.append(
            {
                "naif_id": naif_id,
                "name": name,
                "center": segment.center,
                "frame": segment.frame,
                "states": states,
                "epochs_jd": epochs_jd,
                "window_size": window_size,
            }
        )

    rebuilt_path = tmp_path / "minor_bodies_rebuilt.bsp"
    write_spk_type13(rebuilt_path, bodies, locifn="MOIRA MINOR BODIES REBUILD")
    rebuilt_kernel = _AsteroidKernel(rebuilt_path)

    try:
        for name in names:
            naif_id = ASTEROID_NAIF[name]
            segment = source_segments[naif_id]
            states, epochs_jd, _window_size = segment._data

            assert rebuilt_kernel.has_body(naif_id) is True
            assert rebuilt_kernel.segment_center(naif_id) == segment.center

            sample_jds = [epochs_jd[0], epochs_jd[len(epochs_jd) // 2], epochs_jd[-1]]
            if len(epochs_jd) >= 2:
                midpoint_index = min(len(epochs_jd) // 2, len(epochs_jd) - 2)
                sample_jds.append((epochs_jd[midpoint_index] + epochs_jd[midpoint_index + 1]) / 2.0)

            for jd in sample_jds:
                original = source_kernel.position(naif_id, jd)
                rebuilt = rebuilt_kernel.position(naif_id, jd)
                assert rebuilt == pytest.approx(original, abs=1e-6), (name, jd)

            for idx in (0, len(epochs_jd) // 2, len(epochs_jd) - 1):
                rebuilt = rebuilt_kernel.position(naif_id, epochs_jd[idx])
                expected = tuple(axis[idx] for axis in states[:3])
                assert rebuilt == pytest.approx(expected, abs=1e-6), (name, idx)
    finally:
        rebuilt_kernel.close()
