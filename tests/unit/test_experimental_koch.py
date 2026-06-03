from __future__ import annotations

import pytest

from moira.constants import HouseSystem
import moira.houses as houses_module
from moira.experimental_koch import (
    ExperimentalKochAdmissibilityMap,
    ExperimentalKochStatus,
    ExperimentalKochWindow,
    scan_experimental_koch_admissibility,
    search_experimental_koch,
)
from moira.houses import HousePolicy, calculate_houses, houses_from_armc
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity


_JD_J2000 = 2451545.0
_LAT_77 = 77.0
_OB_J2000 = true_obliquity(ut_to_tt(_JD_J2000))
_ARMC_VALID = 90.0
_LON_FOR_ARMC_VALID = 169.54292771060392


def test_search_experimental_koch_finds_unique_ordered_solution_at_77n_armc_90() -> None:
    result = search_experimental_koch(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalKochStatus.UNIQUE_ORDERED_SOLUTION
    assert result.has_solution is True
    assert result.cusps is not None
    assert result.cusps[1] == pytest.approx(201.65152274674918, abs=1e-9)
    assert result.cusps[2] == pytest.approx(214.4146746244032, abs=1e-9)
    assert result.cusps[10] == pytest.approx(145.5853253755968, abs=1e-9)
    assert result.cusps[11] == pytest.approx(158.34847725325082, abs=1e-9)


def test_houses_from_armc_experimental_policy_uses_koch_at_77n_valid_armc() -> None:
    houses = houses_from_armc(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        HouseSystem.KOCH,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.KOCH
    assert houses.effective_system == HouseSystem.KOCH
    assert houses.fallback is False
    assert houses.cusps[1] == pytest.approx(201.65152274674918, abs=1e-9)
    assert houses.cusps[10] == pytest.approx(145.5853253755968, abs=1e-9)


def test_calculate_houses_experimental_policy_uses_public_jd_path_for_koch() -> None:
    houses = calculate_houses(
        _JD_J2000,
        _LAT_77,
        _LON_FOR_ARMC_VALID,
        HouseSystem.KOCH,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.KOCH
    assert houses.effective_system == HouseSystem.KOCH
    assert houses.fallback is False
    assert houses.asc == pytest.approx(180.0, abs=1e-9)
    assert houses.mc == pytest.approx(90.0, abs=1e-9)
    assert houses.cusps[1] == pytest.approx(201.65152274674918, abs=1e-8)


def test_calculate_houses_default_policy_still_falls_back_for_koch_no_solution_high_lat() -> None:
    houses = calculate_houses(
        _JD_J2000,
        _LAT_77,
        0.0,
        HouseSystem.KOCH,
    )

    assert houses.effective_system == HouseSystem.PORPHYRY
    assert houses.fallback is True


def test_experimental_koch_policy_raises_when_no_ordered_solution_exists() -> None:
    with pytest.raises(ValueError, match="experimental search for 'K' did not return usable cusps or raised"):
        houses_from_armc(
            0.0,
            _OB_J2000,
            _LAT_77,
            HouseSystem.KOCH,
            policy=HousePolicy.experimental(),
        )


def test_search_experimental_koch_reports_no_valid_solution_at_armc_0() -> None:
    result = search_experimental_koch(
        0.0,
        _OB_J2000,
        _LAT_77,
        asc=0.0,
        mc=0.0,
    )

    assert result.status == ExperimentalKochStatus.UNORDERED_CUSP_CYCLE
    assert result.has_solution is False
    assert result.cusps is None
    assert "assembled cusps not strictly ordered" in result.diagnostic_summary


def test_search_experimental_koch_reports_branch_selection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_branch_failure(*args, **kwargs):
        raise RuntimeError("forced branch failure")

    monkeypatch.setattr(houses_module, "_select_horizon_branch", _raise_branch_failure)

    result = search_experimental_koch(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalKochStatus.HORIZON_BRANCH_SELECTION_FAILED
    assert result.has_solution is False
    assert result.cusps is None
    assert "horizon branch selection failed" in result.diagnostic_summary


def test_search_experimental_koch_reports_assembly_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_assembly_failure(*args, **kwargs):
        raise RuntimeError("forced assembly failure")

    monkeypatch.setattr(houses_module, "_assemble_antipodal_quadrant_cusps", _raise_assembly_failure)

    result = search_experimental_koch(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalKochStatus.ASSEMBLY_FAILED
    assert result.has_solution is False
    assert result.cusps is None
    assert "assembly failed" in result.diagnostic_summary


def test_scan_experimental_koch_admissibility_finds_77n_window_around_armc_90() -> None:
    admissibility = scan_experimental_koch_admissibility(
        _LAT_77,
        _OB_J2000,
        armc_start=60.0,
        armc_end=120.0,
        armc_step=5.0,
        sample_count=12000,
    )

    assert isinstance(admissibility, ExperimentalKochAdmissibilityMap)
    assert admissibility.has_any_window is True
    assert 90.0 in admissibility.valid_armcs
    assert admissibility.windows[0].start_armc <= 90.0 <= admissibility.windows[0].end_armc
    assert admissibility.valid_fraction > 0.0


def test_scan_experimental_koch_admissibility_recovers_measured_77n_window_bounds() -> None:
    admissibility = scan_experimental_koch_admissibility(
        _LAT_77,
        _OB_J2000,
        armc_start=60.0,
        armc_end=120.0,
        armc_step=5.0,
        sample_count=12000,
    )

    assert admissibility.windows == (
        ExperimentalKochWindow(start_armc=65.0, end_armc=115.0, sample_count=11),
    )


def test_scan_experimental_koch_admissibility_rejects_non_positive_step() -> None:
    with pytest.raises(ValueError, match="armc_step must be > 0"):
        scan_experimental_koch_admissibility(
            _LAT_77,
            _OB_J2000,
            armc_step=0.0,
        )
