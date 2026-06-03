from __future__ import annotations

import pytest

from moira.constants import HouseSystem
import moira.houses as houses_module
from moira.experimental_campanus import (
    ExperimentalCampanusAdmissibilityMap,
    ExperimentalCampanusStatus,
    ExperimentalCampanusWindow,
    scan_experimental_campanus_admissibility,
    search_experimental_campanus,
)
from moira.houses import HousePolicy, calculate_houses, houses_from_armc
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity


_JD_J2000 = 2451545.0
_LAT_80 = 80.0
_OB_J2000 = true_obliquity(ut_to_tt(_JD_J2000))
_ARMC_VALID = 90.0
_LON_VALID = 170.0


def test_search_experimental_campanus_finds_unique_ordered_solution_at_80n_armc_90() -> None:
    result = search_experimental_campanus(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_80,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalCampanusStatus.UNIQUE_ORDERED_SOLUTION
    assert result.has_solution is True
    assert result.cusps is not None
    assert result.cusps[1] == pytest.approx(226.33624289651013, abs=1e-9)
    assert result.cusps[2] == pytest.approx(252.35220293024855, abs=1e-9)
    assert result.cusps[10] == pytest.approx(107.64779706975143, abs=1e-9)
    assert result.cusps[11] == pytest.approx(133.66375710348987, abs=1e-9)


def test_houses_from_armc_experimental_policy_uses_campanus_at_80n_valid_armc() -> None:
    houses = houses_from_armc(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_80,
        HouseSystem.CAMPANUS,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.CAMPANUS
    assert houses.effective_system == HouseSystem.CAMPANUS
    assert houses.fallback is False
    assert houses.cusps[1] == pytest.approx(226.33624289651013, abs=1e-9)
    assert houses.cusps[10] == pytest.approx(107.64779706975143, abs=1e-9)


def test_calculate_houses_experimental_policy_uses_public_jd_path_for_campanus() -> None:
    houses = calculate_houses(
        _JD_J2000,
        _LAT_80,
        _LON_VALID,
        HouseSystem.CAMPANUS,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.CAMPANUS
    assert houses.effective_system == HouseSystem.CAMPANUS
    assert houses.fallback is False
    assert houses.asc == pytest.approx(180.14403852474203, abs=1e-9)
    assert houses.mc == pytest.approx(90.41936215629704, abs=1e-9)
    assert houses.cusps[1] == pytest.approx(226.62440634830227, abs=1e-8)


def test_houses_from_armc_experimental_policy_uses_campanus_at_80n_armc_0() -> None:
    houses = houses_from_armc(
        0.0,
        _OB_J2000,
        _LAT_80,
        HouseSystem.CAMPANUS,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.CAMPANUS
    assert houses.effective_system == HouseSystem.CAMPANUS
    assert houses.fallback is False
    assert houses.asc == pytest.approx(156.09182944261033, abs=1e-9)
    assert houses.mc == pytest.approx(0.0, abs=1e-12)
    assert houses.cusps[1] == pytest.approx(169.32741658957062, abs=1e-9)
    assert houses.cusps[11] == pytest.approx(51.52417416395844, abs=1e-9)


def test_search_experimental_campanus_reports_unordered_cycle_at_armc_0() -> None:
    result = search_experimental_campanus(
        0.0,
        _OB_J2000,
        _LAT_80,
        asc=0.0,
        mc=0.0,
    )

    assert result.status == ExperimentalCampanusStatus.UNORDERED_CUSP_CYCLE
    assert result.has_solution is False
    assert result.cusps is None
    assert "assembled cusps not strictly ordered" in result.diagnostic_summary


def test_search_experimental_campanus_reports_branch_selection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_branch_failure(*args, **kwargs):
        raise RuntimeError("forced branch failure")

    monkeypatch.setattr(houses_module, "_select_horizon_branch", _raise_branch_failure)

    result = search_experimental_campanus(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_80,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalCampanusStatus.HORIZON_BRANCH_SELECTION_FAILED
    assert result.has_solution is False
    assert result.cusps is None
    assert "horizon branch selection failed" in result.diagnostic_summary


def test_search_experimental_campanus_reports_assembly_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_assembly_failure(*args, **kwargs):
        raise RuntimeError("forced assembly failure")

    monkeypatch.setattr(houses_module, "_assemble_antipodal_quadrant_cusps", _raise_assembly_failure)

    result = search_experimental_campanus(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_80,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalCampanusStatus.ASSEMBLY_FAILED
    assert result.has_solution is False
    assert result.cusps is None
    assert "assembly failed" in result.diagnostic_summary


def test_scan_experimental_campanus_admissibility_finds_80n_windows() -> None:
    admissibility = scan_experimental_campanus_admissibility(
        _LAT_80,
        _OB_J2000,
        armc_start=0.0,
        armc_end=355.0,
        armc_step=5.0,
    )

    assert isinstance(admissibility, ExperimentalCampanusAdmissibilityMap)
    assert admissibility.has_any_window is True
    assert 90.0 in admissibility.valid_armcs
    assert admissibility.valid_fraction == pytest.approx(0.625, abs=1e-12)


def test_scan_experimental_campanus_admissibility_recovers_measured_80n_window_bounds() -> None:
    admissibility = scan_experimental_campanus_admissibility(
        _LAT_80,
        _OB_J2000,
        armc_start=0.0,
        armc_end=355.0,
        armc_step=5.0,
    )

    assert admissibility.windows == (
        ExperimentalCampanusWindow(start_armc=0.0, end_armc=200.0, sample_count=41),
        ExperimentalCampanusWindow(start_armc=340.0, end_armc=355.0, sample_count=4),
    )


def test_scan_experimental_campanus_admissibility_rejects_non_positive_step() -> None:
    with pytest.raises(ValueError, match="armc_step must be > 0"):
        scan_experimental_campanus_admissibility(
            _LAT_80,
            _OB_J2000,
            armc_step=0.0,
        )
