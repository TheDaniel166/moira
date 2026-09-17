"""Stage 1 orbital frame ownership and matrix contracts."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira._orbital_errors import OrbitalFrameUnavailableError
from moira._orbital_frames import (
    J2000_ECLIPTIC,
    LONG_TERM_FRAME_INTERVAL_TT,
    MEAN_ECLIPTIC_OF_DATE,
    MODERN_FRAME_INTERVAL_TT,
    TRUE_ECLIPTIC_OF_DATE,
    orbital_frame_transform,
    rotate_orbital_state,
)
from moira.constants import ARCSEC2RAD
from moira.precession import precession_matrix


FRAME_AUTHORITY = json.loads(
    (
        Path(__file__).parents[1]
        / "fixtures"
        / "orbital_frames_sofa_20231011_reference.json"
    ).read_text(encoding="utf-8")
)


def _max_matrix_delta(left, right) -> float:
    return max(
        abs(float(left[row][column]) - float(right[row][column]))
        for row in range(3)
        for column in range(3)
    )


def _determinant(matrix) -> float:
    a, b, c = matrix
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


@pytest.mark.parametrize("case", FRAME_AUTHORITY["cases"])
def test_orbital_frame_router_matches_official_sofa_c_fixture(case) -> None:
    actual = orbital_frame_transform(case["frame"], case["epoch_tt"])
    tolerance = 5.0e-15 if case["routine"] == "LTECM" else 4.0e-10

    assert actual.routine == case["routine"]
    assert _max_matrix_delta(actual.matrix, case["matrix"]) < tolerance


def test_fixed_j2000_frame_is_only_the_horizons_obliquity_rotation() -> None:
    matrix = orbital_frame_transform(J2000_ECLIPTIC, 1000000.0).matrix
    epsilon = 84381.448 * ARCSEC2RAD

    assert matrix == (
        (1.0, 0.0, 0.0),
        (0.0, math.cos(epsilon), math.sin(epsilon)),
        (0.0, -math.sin(epsilon), math.cos(epsilon)),
    )


@pytest.mark.parametrize("epoch_tt", (2415020.0, 2451545.0, 2461298.5, 2488070.0))
def test_modern_mean_matrix_matches_official_algorithm_secondary_erfa_parity(
    epoch_tt: float,
) -> None:
    erfa = pytest.importorskip("erfa")
    expected = erfa.ecm06(2451545.0, epoch_tt - 2451545.0)
    actual = orbital_frame_transform(MEAN_ECLIPTIC_OF_DATE, epoch_tt)

    assert actual.routine == "ECM06"
    assert actual.router_branch == "modern_mean"
    assert _max_matrix_delta(actual.matrix, expected) < 3.0e-10


@pytest.mark.parametrize("julian_epoch", (-10000.0, 0.0, 5000.0, 12000.0))
def test_long_term_mean_matrix_matches_official_algorithm_secondary_erfa_parity(
    julian_epoch: float,
) -> None:
    erfa = pytest.importorskip("erfa")
    epoch_tt = 2451545.0 + (julian_epoch - 2000.0) * 365.25
    expected = erfa.ltecm(julian_epoch)
    actual = orbital_frame_transform(MEAN_ECLIPTIC_OF_DATE, epoch_tt)

    assert actual.routine == "LTECM"
    assert actual.router_branch == "long_term_mean"
    assert _max_matrix_delta(actual.matrix, expected) < 5.0e-15


@pytest.mark.parametrize("epoch_tt", MODERN_FRAME_INTERVAL_TT)
def test_true_frame_includes_both_closed_modern_endpoints(epoch_tt: float) -> None:
    erfa = pytest.importorskip("erfa")
    epsa = erfa.obl06(2451545.0, epoch_tt - 2451545.0)
    _dpsi, deps = erfa.nut06a(2451545.0, epoch_tt - 2451545.0)
    expected = erfa.rx(
        epsa + deps,
        erfa.pnm06a(2451545.0, epoch_tt - 2451545.0).copy(),
    )
    actual = orbital_frame_transform(TRUE_ECLIPTIC_OF_DATE, epoch_tt)

    assert actual.router_branch == "modern_true"
    assert _max_matrix_delta(actual.matrix, expected) < 4.0e-10


@pytest.mark.parametrize(
    "epoch_tt",
    (
        math.nextafter(MODERN_FRAME_INTERVAL_TT[0], -math.inf),
        math.nextafter(MODERN_FRAME_INTERVAL_TT[1], math.inf),
    ),
)
def test_true_frame_fails_immediately_outside_admitted_interval(epoch_tt: float) -> None:
    with pytest.raises(OrbitalFrameUnavailableError) as caught:
        orbital_frame_transform(TRUE_ECLIPTIC_OF_DATE, epoch_tt)

    assert caught.value.epoch_tt == epoch_tt
    assert caught.value.supported_intervals_tt == (MODERN_FRAME_INTERVAL_TT,)


def test_mean_frame_fails_outside_long_term_authority_interval() -> None:
    with pytest.raises(OrbitalFrameUnavailableError):
        orbital_frame_transform(
            MEAN_ECLIPTIC_OF_DATE,
            math.nextafter(LONG_TERM_FRAME_INTERVAL_TT[0], -math.inf),
        )


@pytest.mark.parametrize(
    ("frame", "epoch_tt"),
    (
        (J2000_ECLIPTIC, 2451545.0),
        (MEAN_ECLIPTIC_OF_DATE, 2451545.0),
        (MEAN_ECLIPTIC_OF_DATE, 1000000.0),
        (TRUE_ECLIPTIC_OF_DATE, 2451545.0),
    ),
)
def test_frame_matrices_are_right_handed_orthogonal(frame: str, epoch_tt: float) -> None:
    matrix = orbital_frame_transform(frame, epoch_tt).matrix
    for left in range(3):
        for right in range(3):
            dot = sum(matrix[left][i] * matrix[right][i] for i in range(3))
            assert dot == pytest.approx(1.0 if left == right else 0.0, abs=2.0e-14)
    assert _determinant(matrix) == pytest.approx(1.0, abs=2.0e-14)


def test_position_and_velocity_receive_the_identical_instantaneous_matrix() -> None:
    transform = orbital_frame_transform(MEAN_ECLIPTIC_OF_DATE, 2461298.5)
    position = (1.0, 2.0, 3.0)
    velocity = tuple(value * 7.0 for value in position)
    rotated_position, rotated_velocity = rotate_orbital_state(
        transform, position, velocity
    )

    assert rotated_velocity == pytest.approx(
        tuple(value * 7.0 for value in rotated_position), abs=2.0e-15
    )


def test_mean_and_fixed_j2000_axes_are_intentionally_distinct() -> None:
    fixed = orbital_frame_transform(J2000_ECLIPTIC, 2451545.0).matrix
    mean = orbital_frame_transform(MEAN_ECLIPTIC_OF_DATE, 2451545.0).matrix
    delta = tuple(
        tuple(sum(mean[i][k] * fixed[j][k] for k in range(3)) for j in range(3))
        for i in range(3)
    )
    angle_arcsec = math.acos(
        max(-1.0, min(1.0, (sum(delta[i][i] for i in range(3)) - 1.0) / 2.0))
    ) / ARCSEC2RAD

    assert angle_arcsec == pytest.approx(0.042, abs=0.002)


@pytest.mark.parametrize("julian_epoch", (-10000.0, 12000.0))
def test_public_precession_long_branch_is_bias_inclusive(julian_epoch: float) -> None:
    erfa = pytest.importorskip("erfa")
    epoch_tt = 2451545.0 + (julian_epoch - 2000.0) * 365.25
    assert _max_matrix_delta(
        precession_matrix(epoch_tt), erfa.ltpb(julian_epoch)
    ) < 5.0e-15
