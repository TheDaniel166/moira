from __future__ import annotations

import json
from pathlib import Path

import pytest


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "eclipse_nasa_reference.json"

GREATEST_LATITUDE_TOLERANCE_DEG = 0.25
GREATEST_LONGITUDE_TOLERANCE_DEG = 0.5
PATH_WIDTH_TOLERANCE_KM = 2.0
CENTRAL_DURATION_TOLERANCE_S = 5.0
MAGNITUDE_TOLERANCE = 0.005
CENTRAL_SEPARATION_TOLERANCE_DEG = 0.001


def _path_cases() -> tuple[dict[str, object], ...]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return tuple(payload["solar_path_products"])


@pytest.mark.slow
@pytest.mark.parametrize(
    "row",
    _path_cases(),
    ids=lambda row: str(row["label"]),
)
def test_native_solar_path_fields_match_named_nasa_product(
    eclipse_calculator,
    row: dict[str, object],
) -> None:
    """Validate selected scalar path products, not only event identity.

    The named NASA/GSFC Besselian products are external authority comparisons
    under their own VSOP87/ELP2000-82 and Delta-T policy. These are cross-model
    regression envelopes for Moira's DE441/TT native result, not an assertion
    that the two models are identical. Central-line sample arrays and complete
    ingress-to-egress track geography are outside this test's evidence scope.
    """

    seed = float(row["seed_jd"])
    path = eclipse_calculator.solar_eclipse_path(seed, kind=str(row["kind"]))
    event = eclipse_calculator.next_solar_eclipse(seed, kind=str(row["kind"]))

    assert abs(event.jd_ut - float(row["greatest_ut_jd"])) * 86400.0 <= float(
        row["timing_tolerance_s"]
    )
    assert str(path.eclipse_data.eclipse_type).lower() == str(row["kind"])
    assert path.max_eclipse_lat == pytest.approx(
        float(row["latitude_deg"]),
        abs=GREATEST_LATITUDE_TOLERANCE_DEG,
    )
    assert path.max_eclipse_lon == pytest.approx(
        float(row["longitude_deg"]),
        abs=float(
            row.get(
                "longitude_tolerance_deg",
                GREATEST_LONGITUDE_TOLERANCE_DEG,
            )
        ),
    )
    if str(row["kind"]) == "partial":
        assert row["path_width_km"] is None
        assert row["central_duration_s"] is None
        assert row["nasa_noncentral_width_display"] == "0.0 km"
        assert row["nasa_noncentral_duration_display"] == "00m00s"
        assert row["moira_noncentral_zero_sentinel"] is True
        assert path.umbral_width_km == 0.0
        assert path.duration_at_max_s == 0.0
    else:
        assert path.umbral_width_km == pytest.approx(
            float(row["path_width_km"]),
            abs=PATH_WIDTH_TOLERANCE_KM,
        )
        assert path.duration_at_max_s == pytest.approx(
            float(row["central_duration_s"]),
            abs=CENTRAL_DURATION_TOLERANCE_S,
        )
    assert path.eclipse_data.eclipse_magnitude == pytest.approx(
        float(row["magnitude"]),
        abs=MAGNITUDE_TOLERANCE,
    )
    if str(row["kind"]) == "partial":
        assert path.eclipse_data.solar_topocentric_separation < (
            path.eclipse_data.sun_apparent_radius
            + path.eclipse_data.moon_apparent_radius
        )
        assert path.eclipse_data.solar_topocentric_separation >= abs(
            path.eclipse_data.moon_apparent_radius
            - path.eclipse_data.sun_apparent_radius
        )
    else:
        assert (
            path.eclipse_data.solar_topocentric_separation
            < CENTRAL_SEPARATION_TOLERANCE_DEG
        )
