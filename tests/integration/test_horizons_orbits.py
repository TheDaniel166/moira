from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.orbits import distance_extremes_at, orbital_elements_at
from moira.spk_reader import get_reader
from tools.horizons import orbital_elements, vector_series, vector_state


def _wrapped_angle_error_deg(a_deg: float, b_deg: float) -> float:
    return abs(((a_deg - b_deg + 180.0) % 360.0) - 180.0)


def _next_event_jd(base_jd: float, start_jd: float, period_days: float) -> float:
    if base_jd >= start_jd:
        return base_jd
    cycles = math.ceil((start_jd - base_jd) / period_days)
    return base_jd + cycles * period_days


def _helio_distance_au(command: str, jd_ut: float) -> float:
    state = vector_state(command, jd_ut, center="500@10")
    return math.sqrt(state.x * state.x + state.y * state.y + state.z * state.z) / 149_597_870.700


def _helio_distance_au_from_xyz(x: float, y: float, z: float) -> float:
    return math.sqrt(x * x + y * y + z * z) / 149_597_870.700


def _golden_section_extremum(
    func,
    left: float,
    right: float,
    *,
    maximise: bool,
    tol_days: float = 1e-3,
    max_iter: int = 32,
) -> tuple[float, float]:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    invphi = 1.0 / phi
    invphi2 = invphi * invphi

    a = left
    b = right
    h = b - a
    if h <= tol_days:
        x = 0.5 * (a + b)
        return x, func(x)

    c = a + invphi2 * h
    d = a + invphi * h
    fc = func(c)
    fd = func(d)

    for _ in range(max_iter):
        if h <= tol_days:
            break
        choose_left = fc > fd if maximise else fc < fd
        if choose_left:
            b = d
            d = c
            fd = fc
            h = invphi * h
            c = a + invphi2 * h
            fc = func(c)
        else:
            a = c
            c = d
            fc = fd
            h = invphi * h
            d = a + invphi * h
            fd = func(d)

    if (fc > fd) if maximise else (fc < fd):
        return c, fc
    return d, fd


def _first_local_extremum_bracket(
    command: str,
    start_jd_ut: float,
    *,
    maximise: bool,
) -> tuple[float, float, float]:
    elements = orbital_elements(command, start_jd_ut)
    step_days = max(0.5, elements.orbital_period_days / 100.0)
    samples = vector_series(
        command,
        start_jd_ut - step_days,
        start_jd_ut + elements.orbital_period_days * 1.5 + step_days,
        step_days,
        center="500@10",
    )
    distances = [
        _helio_distance_au_from_xyz(sample.state.x, sample.state.y, sample.state.z)
        for sample in samples
    ]
    for idx in range(1, len(samples) - 1):
        mid = distances[idx]
        lhs = distances[idx - 1]
        rhs = distances[idx + 1]
        if maximise:
            if mid >= lhs and mid >= rhs:
                return samples[idx - 1].jd_tdb, samples[idx].jd_tdb, samples[idx + 1].jd_tdb
        else:
            if mid <= lhs and mid <= rhs:
                return samples[idx - 1].jd_tdb, samples[idx].jd_tdb, samples[idx + 1].jd_tdb
    raise AssertionError(f"No {'maximum' if maximise else 'minimum'} bracket found for command {command}")


ORBIT_BODY_COMMANDS: list[tuple[str, str]] = [
    (Body.MERCURY, "199"),
    (Body.VENUS, "299"),
    (Body.EARTH, "399"),
    (Body.MARS, "499"),
    # DE441 exposes the giant-planet systems via barycenter routes; validate
    # against the corresponding Horizons barycenter commands.
    (Body.JUPITER, "5"),
    (Body.SATURN, "6"),
    (Body.URANUS, "7"),
    (Body.NEPTUNE, "8"),
    (Body.PLUTO, "9"),
]

ELEMENT_EPOCHS: list[tuple[str, float]] = [
    ("J2000", 2451545.0),
    ("2000-12-31", 2451910.5),
    ("2025-09-01", 2460919.5),
]

EXTREME_CASES: list[tuple[str, str, float]] = [
    (Body.VENUS, "299", 2451513.5),
    (Body.EARTH, "399", 2451513.5),
    (Body.MARS, "499", 2451513.5),
]

OUTER_EXTREME_CASES: list[tuple[str, str, float]] = [
    (Body.JUPITER, "5", 2451513.5),
    (Body.SATURN, "6", 2451513.5),
    (Body.URANUS, "7", 2451513.5),
    (Body.NEPTUNE, "8", 2451513.5),
    (Body.PLUTO, "9", 2451513.5),
]


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(("body", "command"), ORBIT_BODY_COMMANDS, ids=[body for body, _ in ORBIT_BODY_COMMANDS])
@pytest.mark.parametrize(("label", "jd_ut"), ELEMENT_EPOCHS, ids=[label for label, _ in ELEMENT_EPOCHS])
def test_orbital_elements_match_horizons(
    body: str,
    command: str,
    label: str,
    jd_ut: float,
) -> None:
    reader = get_reader()
    moira = orbital_elements_at(body, jd_ut, reader)
    ref = orbital_elements(command, jd_ut)

    assert abs(moira.semi_major_axis_au - ref.semi_major_axis_au) <= 1e-5, (
        f"{body} {label}: semi-major-axis error "
        f"{moira.semi_major_axis_au - ref.semi_major_axis_au:+.8f} AU exceeds 1e-5 AU"
    )
    assert abs(moira.eccentricity - ref.eccentricity) <= 1e-5, (
        f"{body} {label}: eccentricity error "
        f"{moira.eccentricity - ref.eccentricity:+.8f} exceeds 1e-5"
    )
    assert abs(moira.inclination_deg - ref.inclination_deg) <= 1e-3, (
        f"{body} {label}: inclination error "
        f"{moira.inclination_deg - ref.inclination_deg:+.8f} deg exceeds 1e-3 deg"
    )
    assert _wrapped_angle_error_deg(
        moira.lon_ascending_node_deg, ref.lon_ascending_node_deg
    ) <= 1e-3, (
        f"{body} {label}: ascending-node error "
        f"{_wrapped_angle_error_deg(moira.lon_ascending_node_deg, ref.lon_ascending_node_deg):.8f} deg "
        f"exceeds 1e-3 deg"
    )
    assert _wrapped_angle_error_deg(moira.arg_perihelion_deg, ref.arg_perihelion_deg) <= 0.05, (
        f"{body} {label}: argument-of-perihelion error "
        f"{_wrapped_angle_error_deg(moira.arg_perihelion_deg, ref.arg_perihelion_deg):.8f} deg "
        f"exceeds 0.05 deg"
    )
    assert _wrapped_angle_error_deg(moira.mean_anomaly_deg, ref.mean_anomaly_deg) <= 0.05, (
        f"{body} {label}: mean-anomaly error "
        f"{_wrapped_angle_error_deg(moira.mean_anomaly_deg, ref.mean_anomaly_deg):.8f} deg "
        f"exceeds 0.05 deg"
    )
    assert abs(moira.perihelion_distance_au - ref.perihelion_distance_au) <= 1e-5, (
        f"{body} {label}: perihelion-distance error "
        f"{moira.perihelion_distance_au - ref.perihelion_distance_au:+.8f} AU exceeds 1e-5 AU"
    )
    assert abs(moira.aphelion_distance_au - ref.aphelion_distance_au) <= 1e-5, (
        f"{body} {label}: aphelion-distance error "
        f"{moira.aphelion_distance_au - ref.aphelion_distance_au:+.8f} AU exceeds 1e-5 AU"
    )


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(("body", "command", "start_jd_ut"), EXTREME_CASES, ids=[body for body, _, _ in EXTREME_CASES])
def test_inner_distance_extremes_match_horizons_vector_extrema(
    body: str,
    command: str,
    start_jd_ut: float,
) -> None:
    reader = get_reader()
    moira = distance_extremes_at(body, start_jd_ut, reader)

    peri_left, _, peri_right = _first_local_extremum_bracket(command, start_jd_ut, maximise=False)
    aphe_left, _, aphe_right = _first_local_extremum_bracket(command, start_jd_ut, maximise=True)

    ref_peri_jd, ref_peri_dist = _golden_section_extremum(
        lambda jd: _helio_distance_au(command, jd),
        peri_left,
        peri_right,
        maximise=False,
    )
    ref_aphe_jd, ref_aphe_dist = _golden_section_extremum(
        lambda jd: _helio_distance_au(command, jd),
        aphe_left,
        aphe_right,
        maximise=True,
    )

    assert abs(moira.perihelion_jd - ref_peri_jd) <= 1.0, (
        f"{body}: perihelion date error "
        f"{moira.perihelion_jd - ref_peri_jd:+.6f} d exceeds 1.0 d"
    )
    assert abs(moira.aphelion_jd - ref_aphe_jd) <= 1.0, (
        f"{body}: aphelion date error "
        f"{moira.aphelion_jd - ref_aphe_jd:+.6f} d exceeds 1.0 d"
    )
    assert abs(moira.perihelion_distance_au - ref_peri_dist) <= 3e-4, (
        f"{body}: perihelion distance error "
        f"{moira.perihelion_distance_au - ref_peri_dist:+.8f} AU exceeds 3e-4 AU"
    )
    assert abs(moira.aphelion_distance_au - ref_aphe_dist) <= 3e-4, (
        f"{body}: aphelion distance error "
        f"{moira.aphelion_distance_au - ref_aphe_dist:+.8f} AU exceeds 3e-4 AU"
    )


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(("body", "command", "start_jd_ut"), OUTER_EXTREME_CASES, ids=[body for body, _, _ in OUTER_EXTREME_CASES])
def test_outer_distance_extremes_match_horizons_vector_extrema(
    body: str,
    command: str,
    start_jd_ut: float,
) -> None:
    reader = get_reader()
    moira = distance_extremes_at(body, start_jd_ut, reader)

    peri_left, _, peri_right = _first_local_extremum_bracket(command, start_jd_ut, maximise=False)
    aphe_left, _, aphe_right = _first_local_extremum_bracket(command, start_jd_ut, maximise=True)

    ref_peri_jd, ref_peri_dist = _golden_section_extremum(
        lambda jd: _helio_distance_au(command, jd),
        peri_left,
        peri_right,
        maximise=False,
    )
    ref_aphe_jd, ref_aphe_dist = _golden_section_extremum(
        lambda jd: _helio_distance_au(command, jd),
        aphe_left,
        aphe_right,
        maximise=True,
    )

    assert abs(moira.perihelion_jd - ref_peri_jd) <= 1.0, (
        f"{body}: perihelion date error "
        f"{moira.perihelion_jd - ref_peri_jd:+.6f} d exceeds 1.0 d"
    )
    assert abs(moira.aphelion_jd - ref_aphe_jd) <= 1.0, (
        f"{body}: aphelion date error "
        f"{moira.aphelion_jd - ref_aphe_jd:+.6f} d exceeds 1.0 d"
    )
    assert abs(moira.perihelion_distance_au - ref_peri_dist) <= 3e-4, (
        f"{body}: perihelion distance error "
        f"{moira.perihelion_distance_au - ref_peri_dist:+.8f} AU exceeds 3e-4 AU"
    )
    assert abs(moira.aphelion_distance_au - ref_aphe_dist) <= 3e-4, (
        f"{body}: aphelion distance error "
        f"{moira.aphelion_distance_au - ref_aphe_dist:+.8f} AU exceeds 3e-4 AU"
    )
