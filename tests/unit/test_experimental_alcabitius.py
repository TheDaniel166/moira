from __future__ import annotations

import pytest

from moira.constants import HouseSystem
import moira.houses as houses_module
from moira.experimental_alcabitius import (
    ExperimentalAlcabitiusAdmissibilityMap,
    ExperimentalAlcabitiusStatus,
    ExperimentalAlcabitiusWindow,
    scan_experimental_alcabitius_admissibility,
    search_experimental_alcabitius,
)
from moira.houses import HousePolicy, calculate_houses, houses_from_armc
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity


_JD_J2000 = 2451545.0
_LAT_77 = 77.0
_OB_J2000 = true_obliquity(ut_to_tt(_JD_J2000))
_ARMC_VALID = 90.0
_LON_VALID = 170.0


def test_search_experimental_alcabitius_finds_unique_ordered_solution_at_77n_armc_90() -> None:
    result = search_experimental_alcabitius(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalAlcabitiusStatus.UNIQUE_ORDERED_SOLUTION
    assert result.has_solution is True
    assert result.cusps is not None
    assert result.cusps[1] == pytest.approx(212.18094369462167, abs=1e-9)
    assert result.cusps[2] == pytest.approx(242.08916072445084, abs=1e-9)
    assert result.cusps[10] == pytest.approx(117.91083927554914, abs=1e-9)
    assert result.cusps[11] == pytest.approx(147.81905630537835, abs=1e-9)


def test_search_experimental_alcabitius_reports_quality_verdict_when_rho_ceiling_supplied() -> None:
    result = search_experimental_alcabitius(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        asc=180.0,
        mc=90.0,
        rho_max=10.0,
    )

    assert result.status == ExperimentalAlcabitiusStatus.UNIQUE_ORDERED_SOLUTION
    assert result.quality_verdict == "practically_admissible"
    assert result.distortion_profile is not None
    assert result.practical_rho_max == pytest.approx(10.0, abs=1e-12)


def test_houses_from_armc_experimental_policy_uses_alcabitius_at_77n_valid_armc() -> None:
    houses = houses_from_armc(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        HouseSystem.ALCABITIUS,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.ALCABITIUS
    assert houses.effective_system == HouseSystem.ALCABITIUS
    assert houses.fallback is False
    assert houses.cusps[1] == pytest.approx(212.18094369462167, abs=1e-9)
    assert houses.cusps[10] == pytest.approx(117.91083927554914, abs=1e-9)


def test_calculate_houses_experimental_policy_uses_public_jd_path_for_alcabitius() -> None:
    houses = calculate_houses(
        _JD_J2000,
        _LAT_77,
        _LON_VALID,
        HouseSystem.ALCABITIUS,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.ALCABITIUS
    assert houses.effective_system == HouseSystem.ALCABITIUS
    assert houses.fallback is False
    assert houses.asc == pytest.approx(180.17311047301007, abs=1e-9)
    assert houses.mc == pytest.approx(90.41936215629704, abs=1e-9)
    assert houses.cusps[1] == pytest.approx(212.44968366717276, abs=1e-8)


def test_calculate_houses_default_policy_uses_real_alcabitius_at_polar_latitude() -> None:
    houses = calculate_houses(
        _JD_J2000,
        _LAT_77,
        _LON_VALID,
        HouseSystem.ALCABITIUS,
    )

    assert houses.system == HouseSystem.ALCABITIUS
    assert houses.effective_system == HouseSystem.ALCABITIUS
    assert houses.fallback is False
    assert houses.cusps[1] == pytest.approx(212.44968366717276, abs=1e-8)


def test_houses_from_armc_experimental_policy_uses_real_alcabitius_at_armc_0() -> None:
    houses = houses_from_armc(
        0.0,
        _OB_J2000,
        _LAT_77,
        HouseSystem.ALCABITIUS,
        policy=HousePolicy.experimental(),
    )

    assert houses.effective_system == HouseSystem.ALCABITIUS
    assert houses.fallback is False
    assert houses.asc == pytest.approx(149.86768390035826, abs=1e-9)
    assert houses.cusps[1] == pytest.approx(159.75907243132656, abs=1e-9)


def test_search_experimental_alcabitius_reports_unordered_cycle_at_armc_0() -> None:
    result = search_experimental_alcabitius(
        0.0,
        _OB_J2000,
        _LAT_77,
        asc=0.0,
        mc=0.0,
    )

    assert result.status == ExperimentalAlcabitiusStatus.UNORDERED_CUSP_CYCLE
    assert result.has_solution is False
    assert result.cusps is None
    assert "assembled cusps not strictly ordered" in result.diagnostic_summary


def test_search_experimental_alcabitius_reports_assembly_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_assembly_failure(*args, **kwargs):
        raise RuntimeError("forced assembly failure")

    monkeypatch.setattr(houses_module, "_assemble_direct_zero_pole_quadrant_family", _raise_assembly_failure)

    result = search_experimental_alcabitius(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalAlcabitiusStatus.ASSEMBLY_FAILED
    assert result.has_solution is False
    assert result.cusps is None
    assert "assembly failed" in result.diagnostic_summary


def test_scan_experimental_alcabitius_admissibility_finds_full_77n_window() -> None:
    admissibility = scan_experimental_alcabitius_admissibility(
        _LAT_77,
        _OB_J2000,
        armc_start=0.0,
        armc_end=355.0,
        armc_step=5.0,
    )

    assert isinstance(admissibility, ExperimentalAlcabitiusAdmissibilityMap)
    assert admissibility.has_any_window is True
    assert 90.0 in admissibility.valid_armcs
    assert admissibility.valid_fraction == pytest.approx(1.0, abs=1e-12)


def test_scan_experimental_alcabitius_admissibility_recovers_measured_77n_window_bounds() -> None:
    admissibility = scan_experimental_alcabitius_admissibility(
        _LAT_77,
        _OB_J2000,
        armc_start=0.0,
        armc_end=355.0,
        armc_step=5.0,
    )

    assert admissibility.windows == (
        ExperimentalAlcabitiusWindow(start_armc=0.0, end_armc=355.0, sample_count=72),
    )


def test_scan_experimental_alcabitius_admissibility_tracks_practical_and_stable_windows() -> None:
    admissibility = scan_experimental_alcabitius_admissibility(
        _LAT_77,
        _OB_J2000,
        armc_start=0.0,
        armc_end=355.0,
        armc_step=5.0,
        rho_max=10.0,
        stability_radius=1,
    )

    assert admissibility.practical_rho_max == pytest.approx(10.0, abs=1e-12)
    assert len(admissibility.practically_valid_armcs) == 58
    assert admissibility.practical_windows == (
        ExperimentalAlcabitiusWindow(start_armc=0.0, end_armc=190.0, sample_count=39),
        ExperimentalAlcabitiusWindow(start_armc=230.0, end_armc=310.0, sample_count=17),
        ExperimentalAlcabitiusWindow(start_armc=350.0, end_armc=355.0, sample_count=2),
    )
    assert admissibility.stability_radius == 1
    assert len(admissibility.stable_practical_armcs) == 52
    assert admissibility.stable_practical_windows == (
        ExperimentalAlcabitiusWindow(start_armc=5.0, end_armc=185.0, sample_count=37),
        ExperimentalAlcabitiusWindow(start_armc=235.0, end_armc=305.0, sample_count=15),
    )


def test_scan_experimental_alcabitius_admissibility_rejects_non_positive_step() -> None:
    with pytest.raises(ValueError, match="armc_step must be > 0"):
        scan_experimental_alcabitius_admissibility(
            _LAT_77,
            _OB_J2000,
            armc_step=0.0,
        )


def test_scan_experimental_alcabitius_admissibility_rejects_negative_stability_radius() -> None:
    with pytest.raises(ValueError, match="stability_radius must be >= 0"):
        scan_experimental_alcabitius_admissibility(
            _LAT_77,
            _OB_J2000,
            stability_radius=-1,
        )
