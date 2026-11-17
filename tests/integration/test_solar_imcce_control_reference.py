"""Independent IMCCE global control; bounded comparisons across models."""
import json
from pathlib import Path

import pytest

from moira.julian import julian_day


pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.slow]
REFERENCE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "imcce_solar_1999_control.json")
    .read_text(encoding="utf-8")
)


def test_imcce_1999_total_global_control(eclipse_calculator):
    reference = REFERENCE["greatest"]
    tolerance = REFERENCE["comparison_tolerances"]
    result = eclipse_calculator.solar_global_circumstances(julian_day(1999, 8, 10))
    assert str(result.event.data.eclipse_type) == "Total"
    # IERS Bulletin C confirms TAI-UTC=32 s; TT=TAI+32.184 s.
    utc_jd = julian_day(1999, 8, 11, 11 + 3 / 60 + 6 / 3600)
    ref_tt = utc_jd + (REFERENCE["tai_minus_utc_seconds"] + 32.184) / 86400
    assert abs(result.greatest.epoch.jd_tt - ref_tt) * 86400 < tolerance["tt_seconds"]
    assert result.greatest.latitude_deg == pytest.approx(reference["latitude_deg"], abs=tolerance["location_deg"])
    assert result.greatest.longitude_deg == pytest.approx(reference["longitude_deg"], abs=tolerance["location_deg"])
    assert result.greatest.sun_altitude_deg == pytest.approx(reference["sun_elevation_deg"], abs=tolerance["sun_elevation_deg"])
    assert result.greatest.magnitude == pytest.approx(reference["magnitude"], abs=tolerance["magnitude"])
    assert result.greatest.path_width_status == "available"
    assert result.greatest.path_width_km > 0
