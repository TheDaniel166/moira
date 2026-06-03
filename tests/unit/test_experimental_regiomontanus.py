from __future__ import annotations

import pytest

from moira.constants import HouseSystem
from moira.experimental_regiomontanus import (
    ExperimentalRegiomontanusAdmissibilityMap,
    ExperimentalRegiomontanusStatus,
    ExperimentalRegiomontanusWindow,
    scan_experimental_regiomontanus_admissibility,
    search_experimental_regiomontanus,
)
from moira.houses import HousePolicy, calculate_houses, houses_from_armc
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity


_JD_J2000 = 2451545.0
_LAT_77 = 77.0
_OB_J2000 = true_obliquity(ut_to_tt(_JD_J2000))
_ARMC_VALID = 90.0
_LON_VALID = 170.0


def test_search_experimental_regiomontanus_finds_unique_ordered_solution_at_77n_armc_90() -> None:
    result = search_experimental_regiomontanus(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalRegiomontanusStatus.UNIQUE_ORDERED_SOLUTION
    assert result.has_solution is True
    assert result.cusps is not None
    assert result.cusps[1] == pytest.approx(192.33443049934604, abs=1e-9)
    assert result.cusps[2] == pytest.approx(213.2646547685577, abs=1e-9)
    assert result.cusps[10] == pytest.approx(146.73534523144227, abs=1e-9)
    assert result.cusps[11] == pytest.approx(167.66556950065396, abs=1e-9)


def test_houses_from_armc_experimental_policy_uses_regiomontanus_at_77n_valid_armc() -> None:
    houses = houses_from_armc(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        HouseSystem.REGIOMONTANUS,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.REGIOMONTANUS
    assert houses.effective_system == HouseSystem.REGIOMONTANUS
    assert houses.fallback is False
    assert houses.cusps[1] == pytest.approx(192.33443049934604, abs=1e-9)
    assert houses.cusps[10] == pytest.approx(146.73534523144227, abs=1e-9)


def test_calculate_houses_experimental_policy_uses_public_jd_path_for_regiomontanus() -> None:
    houses = calculate_houses(
        _JD_J2000,
        _LAT_77,
        _LON_VALID,
        HouseSystem.REGIOMONTANUS,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.REGIOMONTANUS
    assert houses.effective_system == HouseSystem.REGIOMONTANUS
    assert houses.fallback is False
    assert houses.asc == pytest.approx(180.17311047301007, abs=1e-9)
    assert houses.mc == pytest.approx(90.41936215629704, abs=1e-9)
    assert houses.cusps[1] == pytest.approx(192.5186950329331, abs=1e-8)


def test_calculate_houses_default_policy_still_falls_back_for_regiomontanus_no_solution_high_lat() -> None:
    houses = calculate_houses(
        _JD_J2000,
        _LAT_77,
        300.0,
        HouseSystem.REGIOMONTANUS,
    )

    assert houses.effective_system == HouseSystem.PORPHYRY
    assert houses.fallback is True


def test_experimental_regiomontanus_policy_raises_when_no_ordered_solution_exists() -> None:
    with pytest.raises(ValueError, match="experimental search for 'R' did not return usable cusps or raised"):
        houses_from_armc(
            250.0,
            _OB_J2000,
            _LAT_77,
            HouseSystem.REGIOMONTANUS,
            policy=HousePolicy.experimental(),
        )


def test_search_experimental_regiomontanus_reports_no_valid_solution_at_armc_250() -> None:
    result = search_experimental_regiomontanus(
        250.0,
        _OB_J2000,
        _LAT_77,
        asc=0.0,
        mc=0.0,
    )

    assert result.status == ExperimentalRegiomontanusStatus.NO_VALID_SOLUTION
    assert result.has_solution is False
    assert result.cusps is None
    assert "assembled cusps not strictly ordered" in result.diagnostic_summary


def test_scan_experimental_regiomontanus_admissibility_finds_77n_windows() -> None:
    admissibility = scan_experimental_regiomontanus_admissibility(
        _LAT_77,
        _OB_J2000,
        armc_start=0.0,
        armc_end=355.0,
        armc_step=5.0,
    )

    assert isinstance(admissibility, ExperimentalRegiomontanusAdmissibilityMap)
    assert admissibility.has_any_window is True
    assert 90.0 in admissibility.valid_armcs
    assert admissibility.valid_fraction > 0.0


def test_scan_experimental_regiomontanus_admissibility_recovers_measured_77n_window_bounds() -> None:
    admissibility = scan_experimental_regiomontanus_admissibility(
        _LAT_77,
        _OB_J2000,
        armc_start=0.0,
        armc_end=355.0,
        armc_step=5.0,
    )

    assert admissibility.windows == (
        ExperimentalRegiomontanusWindow(start_armc=0.0, end_armc=210.0, sample_count=43),
        ExperimentalRegiomontanusWindow(start_armc=330.0, end_armc=355.0, sample_count=6),
    )


def test_scan_experimental_regiomontanus_admissibility_rejects_non_positive_step() -> None:
    with pytest.raises(ValueError, match="armc_step must be > 0"):
        scan_experimental_regiomontanus_admissibility(
            _LAT_77,
            _OB_J2000,
            armc_step=0.0,
        )
