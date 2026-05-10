"""Oracle safety sweep for the explicit LOLA regional-query width policy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.lunar_limb import official_lunar_limb_profile_adjustment


_BASELINE_PATH = Path("tests/oracle_lunar_limb_baseline.json")
_CASE_INDICES = (0, 3, 7)
_QUERY_WIDTHS_KM = (250.0, 400.0)
_ORACLE_TOLERANCE_DEG = 1e-6


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.network
@pytest.mark.serial
def test_lola_query_width_policy_preserves_oracle_parity():
    if not _BASELINE_PATH.exists():
        pytest.skip("Oracle baseline not found. Run scripts/capture_lunar_limb_oracle.py first.")

    baseline = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))

    failures: list[str] = []
    for case_index in _CASE_INDICES:
        entry = baseline[case_index]
        inp = entry["input"]
        expected = entry["output"]

        for query_width_km in _QUERY_WIDTHS_KM:
            actual = official_lunar_limb_profile_adjustment(
                inp["jd_ut"],
                inp["observer_lat"],
                inp["observer_lon"],
                inp["observer_elev_m"],
                inp["position_angle_deg"],
                inp["moon_distance_km"],
                lola_query_half_width_km=query_width_km,
            )
            diff = abs(actual - expected)
            if diff > _ORACLE_TOLERANCE_DEG:
                failures.append(
                    f"case={case_index + 1} width={query_width_km}km expected={expected} actual={actual} diff={diff}"
                )

    assert not failures, "LOLA query width policy exceeded oracle tolerance:\n" + "\n".join(failures)
