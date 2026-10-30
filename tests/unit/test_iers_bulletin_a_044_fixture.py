"""Frozen IERS Bulletin A 44 values: prediction-to-rapid residuals and broadcast-DUT1 segregation."""
import json
import math
from pathlib import Path

import pytest

_FX = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "iers_bulletin_a_044_2026_10_29.json").read_text("utf-8")
)
_ERA_ARCSEC_PER_S = 15.041067


def test_week_ahead_prediction_residuals() -> None:
    pred = _FX["bulletin_a_43_prediction_mjd_61336"]
    rapid = _FX["rapid_mjd_61336"]
    assert (rapid["x_arcsec"] - pred["x_arcsec"]) * 1000 == pytest.approx(0.22, abs=1e-9)
    assert (rapid["y_arcsec"] - pred["y_arcsec"]) * 1000 == pytest.approx(0.06, abs=1e-9)
    assert (rapid["ut1_utc_s"] - pred["ut1_utc_s"]) * 1e6 == pytest.approx(32.0, abs=1e-6)


def test_ut1_equals_utc_error_magnitudes() -> None:
    p = _FX["prediction_mjd_61343"]
    assert abs(p["ut1_utc_s"]) * _ERA_ARCSEC_PER_S == pytest.approx(0.8008, abs=5e-4)
    assert math.hypot(p["x_arcsec"], p["y_arcsec"]) == pytest.approx(0.3481, abs=5e-5)


def test_broadcast_dut1_step_is_not_physical() -> None:
    precise = _FX["rapid_mjd_61342"]["ut1_utc_s"]
    broadcast = _FX["broadcast_dut1_after_2026_10_29_s"]
    assert (broadcast - precise) * _ERA_ARCSEC_PER_S == pytest.approx(-0.713, abs=1e-3)
    # Treating the 0.0 -> -0.1 broadcast change as physical would invent this step.
    assert abs(broadcast) * _ERA_ARCSEC_PER_S == pytest.approx(1.504, abs=1e-3)
    # Precision UT1 moved smoothly across the same change.
    day_step = abs(precise - _FX["rapid_mjd_61336"]["ut1_utc_s"]) / 6
    assert day_step < 0.005
