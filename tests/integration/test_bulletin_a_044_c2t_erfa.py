"""Moira's Earth-orientation chain against SOFA/ERFA at the Bulletin A 44 epoch (2026-10-30 0h UTC).

Bulletin A 44 values are frozen in iers_bulletin_a_044_2026_10_29.json.  The bundled table is
synced from the same IERS product, so later syncs may replace the 30 Oct *prediction* with a
rapid value; the bundled-data checks therefore allow prediction-sized tolerances, while the
fixture-driven checks are exact.
"""
import json
import math
from pathlib import Path

import pytest

from moira.julian import earth_rotation_angle, jd_from_datetime, utc_to_ut1
from moira.polar_motion import PolarMotionRegistry, polar_motion_matrix
from datetime import datetime, timezone

erfa = pytest.importorskip("erfa")

_FX = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "iers_bulletin_a_044_2026_10_29.json").read_text("utf-8")
)
_P = _FX["prediction_mjd_61343"]
_JD_UTC = 2400000.5 + _P["mjd"]
_ARCSEC_PER_S = 15.041067


def _max_diff(a, b) -> float:
    return max(abs(float(a[i][j]) - float(b[i][j])) for i in range(3) for j in range(3))


def test_epoch_matches_fixture_date() -> None:
    assert jd_from_datetime(datetime(2026, 10, 30, tzinfo=timezone.utc)) == _JD_UTC


def test_era_from_bulletin_dut1_matches_erfa_era00() -> None:
    jd_ut1 = _JD_UTC + _P["ut1_utc_s"] / 86400.0
    moira_era = math.radians(earth_rotation_angle(jd_ut1))
    # One-double JD input resolves ~4e-5 s of rotation; 1e-10 rad (~20 uas) is the honest bound.
    assert abs(moira_era - erfa.era00(jd_ut1, 0.0)) < 1e-10


def test_polar_motion_matrix_from_bulletin_matches_erfa_pom00() -> None:
    moira = polar_motion_matrix(_P["x_arcsec"], _P["y_arcsec"])
    ref = erfa.pom00(_P["x_arcsec"] * erfa.DAS2R, _P["y_arcsec"] * erfa.DAS2R, 0.0)
    assert _max_diff(moira, ref) < 1e-14


def test_full_c2t06a_chain_uses_moira_era_and_polar_motion() -> None:
    """SOFA C2T06A = POM * R3(ERA) * NPB; swap in Moira's ERA/POM and the matrix must agree."""
    jd_ut1 = _JD_UTC + _P["ut1_utc_s"] / 86400.0
    tta, ttb = 2400000.5, _P["mjd"] + (69.184 / 86400.0)  # TT = UTC + 69.184 s (TAI-UTC = 37 s)
    ref = erfa.c2t06a(tta, ttb, 2400000.5, _P["mjd"] + _P["ut1_utc_s"] / 86400.0,
                      _P["x_arcsec"] * erfa.DAS2R, _P["y_arcsec"] * erfa.DAS2R)
    rc2i = erfa.c2i06a(tta, ttb)
    sp = erfa.sp00(tta, ttb)
    era = math.radians(earth_rotation_angle(jd_ut1))
    pom = erfa.pom00(_P["x_arcsec"] * erfa.DAS2R, _P["y_arcsec"] * erfa.DAS2R, sp)
    chain = erfa.c2tcio(rc2i, era, pom)
    assert _max_diff(chain, ref) < 1e-9


def test_utc_as_ut1_error_is_the_documented_size() -> None:
    err = abs(erfa.era00(_JD_UTC, 0.0) - erfa.era00(_JD_UTC + _P["ut1_utc_s"] / 86400.0, 0.0))
    assert math.degrees(err) * 3600 == pytest.approx(0.8008, abs=5e-4)


def test_bundled_eop_agrees_with_bulletin_a_044_at_epoch() -> None:
    dut1 = (utc_to_ut1(_JD_UTC) - _JD_UTC) * 86400.0
    assert dut1 == pytest.approx(_P["ut1_utc_s"], abs=2e-3)
    x, y = PolarMotionRegistry.polar_motion_at(_JD_UTC + _P["ut1_utc_s"] / 86400.0)
    assert x == pytest.approx(_P["x_arcsec"], abs=2e-3)
    assert y == pytest.approx(_P["y_arcsec"], abs=2e-3)
