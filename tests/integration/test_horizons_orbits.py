from __future__ import annotations

import json
import math
from pathlib import Path
import re

import pytest

from moira.constants import Body
from moira.orbits import (
    ApsidalDirection,
    OrbitalCenter,
    apsidal_passages,
    orbital_elements_at,
)
from tools.horizons import (
    orbital_elements,
    orbital_elements_response_tdb,
    orbital_elements_tdb,
    vector_series_tdb,
    vector_state_tdb,
)


_FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures"
_STAGE1_AUTHORITY_RECORDS = tuple(
    record
    for filename in (
        "horizons_orbital_elements_calibration.json",
        "horizons_orbital_elements_holdout.json",
        "horizons_orbital_elements_catalog_holdout.json",
    )
    for record in json.loads(
        (_FIXTURE_ROOT / filename).read_text(encoding="utf-8")
    )["records"]
)


def _wrapped_angle_error_deg(a_deg: float, b_deg: float) -> float:
    return abs(((a_deg - b_deg + 180.0) % 360.0) - 180.0)


def _response_value(pattern: str, text: str) -> str | None:
    found = re.search(pattern, text, re.MULTILINE)
    return None if found is None else found.group(1).strip()


@pytest.mark.integration
@pytest.mark.external_network
@pytest.mark.slow
@pytest.mark.parametrize(
    "record",
    _STAGE1_AUTHORITY_RECORDS,
    ids=[record["case_key"] for record in _STAGE1_AUTHORITY_RECORDS],
)
def test_stage1_exact_tdb_horizons_authority_has_not_drifted(record) -> None:
    command = record["requests"]["elements"]["COMMAND"].strip("'")
    center = record["requests"]["elements"]["CENTER"].strip("'")
    epoch_tdb = record["jd_tdb"]
    text = orbital_elements_response_tdb(command, epoch_tdb, center)
    live_elements = orbital_elements_tdb(command, epoch_tdb, center)
    live_vector = vector_state_tdb(command, epoch_tdb, center)
    authority = record["authority"]

    assert _response_value(r"^API VERSION:\s*(.+)$", text) == authority[
        "api_version"
    ]
    assert _response_value(r"^API SOURCE:\s*(.+)$", text) == authority[
        "api_source"
    ]
    assert _response_value(
        r"^Target body name:.*?\{source:\s*([^}]+)\}", text
    ) == authority["target_solution"]
    gm = _response_value(
        r"^Keplerian GM\s*:\s*([+\-0-9.Ee]+)\s+au\^3/d\^2", text
    )
    assert gm is not None
    assert float(gm) == pytest.approx(
        authority["keplerian_gm_au3_day2"], rel=0.0, abs=5.0e-19
    )

    expected_elements = record["elements_j2000_ecliptic_au_day"]
    for field, expected in expected_elements.items():
        actual = getattr(live_elements, field)
        tolerance = 5.0e-10 if "deg" in field else 2.0e-10
        if "deg" in field:
            assert _wrapped_angle_error_deg(actual, expected) < tolerance
        else:
            assert actual == pytest.approx(expected, abs=tolerance)

    expected_vector = record["vector_icrf_km_km_s"]
    for field, expected in expected_vector.items():
        assert getattr(live_vector, field) == pytest.approx(expected, abs=1.0e-7)


def _next_event_jd(base_jd: float, start_jd: float, period_days: float) -> float:
    if base_jd >= start_jd:
        return base_jd
    cycles = math.ceil((start_jd - base_jd) / period_days)
    return base_jd + cycles * period_days


def _helio_distance_au_tdb(command: str, jd_tdb: float) -> float:
    state = vector_state_tdb(command, jd_tdb, center="500@10")
    return math.sqrt(state.x * state.x + state.y * state.y + state.z * state.z) / 149_597_870.700


def _radial_velocity_km_s(state) -> float:
    distance_km = math.sqrt(
        state.x * state.x + state.y * state.y + state.z * state.z
    )
    return (
        state.x * state.vx + state.y * state.vy + state.z * state.vz
    ) / distance_km


def _horizons_step_size(step_days: float) -> str:
    """Return a deterministic integer-minute Horizons step no wider than requested."""

    return f"{max(1, math.floor(step_days * 1440.0))} m"


def _refine_horizons_radial_root(
    command: str,
    left_tdb: float,
    right_tdb: float,
    *,
    maximise: bool,
    tol_days: float = 2.0e-7,
    max_iter: int = 48,
) -> tuple[float, float]:
    """Refine one official-Horizons radial-velocity crossing in exact TDB."""

    left_state = vector_state_tdb(command, left_tdb, center="500@10")
    right_state = vector_state_tdb(command, right_tdb, center="500@10")
    left_g = _radial_velocity_km_s(left_state)
    right_g = _radial_velocity_km_s(right_state)
    if maximise:
        assert left_g >= 0.0 >= right_g
    else:
        assert left_g <= 0.0 <= right_g

    for _ in range(max_iter):
        if right_tdb - left_tdb <= tol_days:
            break
        middle_tdb = (left_tdb + right_tdb) / 2.0
        middle_state = vector_state_tdb(
            command, middle_tdb, center="500@10"
        )
        middle_g = _radial_velocity_km_s(middle_state)
        if middle_g == 0.0:
            left_tdb = right_tdb = middle_tdb
            break
        if left_g * middle_g <= 0.0:
            right_tdb = middle_tdb
            right_g = middle_g
        else:
            left_tdb = middle_tdb
            left_g = middle_g

    epoch_tdb = (left_tdb + right_tdb) / 2.0
    return epoch_tdb, _helio_distance_au_tdb(command, epoch_tdb)


def _first_local_extremum_bracket(
    command: str,
    start_jd_tdb: float,
    *,
    maximise: bool,
) -> tuple[float, float]:
    elements = orbital_elements_tdb(command, start_jd_tdb)
    step_days = max(
        0.05,
        min(32.0, elements.orbital_period_days / 256.0),
    )
    samples = vector_series_tdb(
        command,
        start_jd_tdb - step_days,
        start_jd_tdb + elements.orbital_period_days * 1.5 + step_days,
        _horizons_step_size(step_days),
        center="500@10",
    )
    for left, right in zip(samples, samples[1:]):
        if right.jd_tdb < start_jd_tdb:
            continue
        left_g = _radial_velocity_km_s(left.state)
        right_g = _radial_velocity_km_s(right.state)
        if maximise:
            crossed = left_g >= 0.0 >= right_g
        else:
            crossed = left_g <= 0.0 <= right_g
        if crossed:
            return left.jd_tdb, right.jd_tdb
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
@pytest.mark.external_network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(("body", "command"), ORBIT_BODY_COMMANDS, ids=[body for body, _ in ORBIT_BODY_COMMANDS])
@pytest.mark.parametrize(("label", "jd_ut"), ELEMENT_EPOCHS, ids=[label for label, _ in ELEMENT_EPOCHS])
def test_orbital_elements_match_horizons(
    body: str,
    command: str,
    label: str,
    jd_ut: float,
    planetary_reader,
) -> None:
    moira = orbital_elements_at(body, jd_ut, planetary_reader)
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
@pytest.mark.external_network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(("body", "command", "start_jd_ut"), EXTREME_CASES, ids=[body for body, _, _ in EXTREME_CASES])
def test_inner_distance_extremes_match_horizons_vector_extrema(
    body: str,
    command: str,
    start_jd_ut: float,
    planetary_reader,
) -> None:
    moira = apsidal_passages(
        body,
        start_jd_ut,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        reader=planetary_reader,
    )
    assert moira.pericenter.epoch_tdb is not None
    assert moira.pericenter.distance_au is not None
    assert moira.apocenter.epoch_tdb is not None
    assert moira.apocenter.distance_au is not None

    peri_left, peri_right = _first_local_extremum_bracket(
        command, moira.start_epoch_tdb, maximise=False
    )
    aphe_left, aphe_right = _first_local_extremum_bracket(
        command, moira.start_epoch_tdb, maximise=True
    )

    ref_peri_jd, ref_peri_dist = _refine_horizons_radial_root(
        command,
        peri_left,
        peri_right,
        maximise=False,
    )
    ref_aphe_jd, ref_aphe_dist = _refine_horizons_radial_root(
        command,
        aphe_left,
        aphe_right,
        maximise=True,
    )

    assert abs(moira.pericenter.epoch_tdb - ref_peri_jd) <= 1.0e-4, (
        f"{body}: perihelion date error "
        f"{moira.pericenter.epoch_tdb - ref_peri_jd:+.9f} d exceeds 1e-4 d"
    )
    assert abs(moira.apocenter.epoch_tdb - ref_aphe_jd) <= 1.0e-4, (
        f"{body}: aphelion date error "
        f"{moira.apocenter.epoch_tdb - ref_aphe_jd:+.9f} d exceeds 1e-4 d"
    )
    assert abs(moira.pericenter.distance_au - ref_peri_dist) <= 1.0e-9, (
        f"{body}: perihelion distance error "
        f"{moira.pericenter.distance_au - ref_peri_dist:+.12f} AU exceeds 1e-9 AU"
    )
    assert abs(moira.apocenter.distance_au - ref_aphe_dist) <= 1.0e-9, (
        f"{body}: aphelion distance error "
        f"{moira.apocenter.distance_au - ref_aphe_dist:+.12f} AU exceeds 1e-9 AU"
    )


@pytest.mark.integration
@pytest.mark.external_network
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize(("body", "command", "start_jd_ut"), OUTER_EXTREME_CASES, ids=[body for body, _, _ in OUTER_EXTREME_CASES])
def test_outer_distance_extremes_match_horizons_vector_extrema(
    body: str,
    command: str,
    start_jd_ut: float,
    planetary_reader,
) -> None:
    moira = apsidal_passages(
        body,
        start_jd_ut,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        reader=planetary_reader,
    )
    assert moira.pericenter.epoch_tdb is not None
    assert moira.pericenter.distance_au is not None
    assert moira.apocenter.epoch_tdb is not None
    assert moira.apocenter.distance_au is not None

    peri_left, peri_right = _first_local_extremum_bracket(
        command, moira.start_epoch_tdb, maximise=False
    )
    aphe_left, aphe_right = _first_local_extremum_bracket(
        command, moira.start_epoch_tdb, maximise=True
    )

    ref_peri_jd, ref_peri_dist = _refine_horizons_radial_root(
        command,
        peri_left,
        peri_right,
        maximise=False,
    )
    ref_aphe_jd, ref_aphe_dist = _refine_horizons_radial_root(
        command,
        aphe_left,
        aphe_right,
        maximise=True,
    )

    assert abs(moira.pericenter.epoch_tdb - ref_peri_jd) <= 1.0e-4, (
        f"{body}: perihelion date error "
        f"{moira.pericenter.epoch_tdb - ref_peri_jd:+.9f} d exceeds 1e-4 d"
    )
    assert abs(moira.apocenter.epoch_tdb - ref_aphe_jd) <= 1.0e-4, (
        f"{body}: aphelion date error "
        f"{moira.apocenter.epoch_tdb - ref_aphe_jd:+.9f} d exceeds 1e-4 d"
    )
    assert abs(moira.pericenter.distance_au - ref_peri_dist) <= 1.0e-9, (
        f"{body}: perihelion distance error "
        f"{moira.pericenter.distance_au - ref_peri_dist:+.12f} AU exceeds 1e-9 AU"
    )
    assert abs(moira.apocenter.distance_au - ref_aphe_dist) <= 1.0e-9, (
        f"{body}: aphelion distance error "
        f"{moira.apocenter.distance_au - ref_aphe_dist:+.12f} AU exceeds 1e-9 AU"
    )
