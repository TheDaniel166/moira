"""Bias-inclusive IAU 2006 angles, with independent SOFA/ERFA references."""

import json
import math
from pathlib import Path

import pytest

from moira import moira_native
from moira._event_search.frames import Differential, FrameEnclosures
from moira._orbital_frames import orbital_frame_transform
from moira.precession import _fw_angles, precession_matrix


@pytest.mark.parametrize("centuries", [-50.0, -25.0, -1.5, 0.0, 1.5, 25.0, 50.0])
def test_bias_inclusive_fw06_angles_and_matrix_match_erfa(centuries):
    erfa = pytest.importorskip("erfa")
    jd_tt = 2451545.0 + centuries * 36525.0
    expected = erfa.pfw06(2451545.0, jd_tt - 2451545.0)
    # Radians and dimensionless matrix entries: only floating point evaluation
    # of the same IAU 2006 polynomials is permitted, including the FW endpoints.
    assert _fw_angles(centuries) == pytest.approx(expected, rel=0.0, abs=3e-14)
    actual = precession_matrix(jd_tt)
    oracle = erfa.pmat06(2451545.0, jd_tt - 2451545.0)
    assert max(abs(actual[i][j] - oracle[i, j]) for i in range(3) for j in range(3)) < 5e-15

    # The interval event-search owner must enclose the same bias-inclusive
    # angles. Its polynomial method has no dependency on initialized caches.
    enclosure = FrameEnclosures.__new__(FrameEnclosures)
    angles, _ = enclosure._polynomials(Differential.point(jd_tt))
    for angle, reference in zip(angles, expected):
        assert angle.value.lo <= reference <= angle.value.hi


def test_mean_ecliptic_matches_existing_official_sofa_fixture_at_roundoff():
    path = Path(__file__).parents[1] / "fixtures/orbital_frames_sofa_20231011_reference.json"
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        if case["routine"] != "ECM06":
            continue
        actual = orbital_frame_transform(case["frame"], case["epoch_tt"]).matrix
        assert max(
            abs(actual[i][j] - case["matrix"][i][j])
            for i in range(3) for j in range(3)
        ) < 5e-15


@pytest.mark.parametrize("centuries", [-50.0, -1.5, 1.5, 50.0])
def test_rebuilt_native_frame_matches_erfa_precession(centuries):
    erfa = pytest.importorskip("erfa")
    jd_tt = 2451545.0 + centuries * 36525.0
    # Constant ICRS vectors isolate the native frame from SPK and time models.
    target = moira_native.ChebyshevEvaluator(-2e11, 4e11, 1, 3, 1, [1.0, 0.5, 0.25])
    observer = moira_native.ChebyshevEvaluator(-2e11, 4e11, 1, 3, 1, [0.0, 0.0, 0.0])
    dpsi_deg, _ = moira_native.nutation_2000a(jd_tt)
    mean = erfa.ecm06(2451545.0, jd_tt - 2451545.0) @ [1.0, 0.5, 0.25]
    # True ecliptic longitude is mean longitude plus native dpsi. Holding
    # nutation fixed makes this an independent test of native precession alone.
    expected = (math.degrees(math.atan2(mean[1], mean[0])) + dpsi_deg) % 360.0
    actual = moira_native.ecliptic_longitude_batch(target, observer, [jd_tt])[0]
    error_deg = (actual - expected + 180.0) % 360.0 - 180.0
    assert abs(error_deg) < 2e-12
