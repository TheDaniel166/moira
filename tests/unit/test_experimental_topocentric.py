from __future__ import annotations

import pytest

from moira.constants import HouseSystem
import moira.houses as houses_module
from moira.experimental_topocentric import (
    ExperimentalTopocentricAdmissibilityMap,
    ExperimentalTopocentricStatus,
    ExperimentalTopocentricWindow,
    scan_experimental_topocentric_admissibility,
    search_experimental_topocentric,
)
from moira.houses import HousePolicy, calculate_houses, houses_from_armc
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity


_JD_J2000 = 2451545.0
_LAT_77 = 77.0
_OB_J2000 = true_obliquity(ut_to_tt(_JD_J2000))
_ARMC_VALID = 90.0
_LON_VALID = -100.0


def test_search_experimental_topocentric_finds_unique_ordered_solution_at_77n_armc_90() -> None:
    result = search_experimental_topocentric(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalTopocentricStatus.UNIQUE_ORDERED_SOLUTION
    assert result.has_solution is True
    assert result.cusps is not None
    assert result.cusps[1] == pytest.approx(194.4300550225039, abs=1e-9)
    assert result.cusps[2] == pytest.approx(219.97428712854238, abs=1e-9)
    assert result.cusps[10] == pytest.approx(140.02571287145759, abs=1e-9)
    assert result.cusps[11] == pytest.approx(165.56994497749608, abs=1e-9)


def test_houses_from_armc_experimental_policy_uses_topocentric_at_77n_valid_armc() -> None:
    houses = houses_from_armc(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        HouseSystem.TOPOCENTRIC,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.TOPOCENTRIC
    assert houses.effective_system == HouseSystem.TOPOCENTRIC
    assert houses.fallback is False
    assert houses.cusps[1] == pytest.approx(194.4300550225039, abs=1e-9)
    assert houses.cusps[10] == pytest.approx(140.02571287145759, abs=1e-9)


def test_calculate_houses_experimental_policy_uses_public_jd_path_for_topocentric() -> None:
    houses = calculate_houses(
        _JD_J2000,
        _LAT_77,
        _LON_VALID,
        HouseSystem.TOPOCENTRIC,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.TOPOCENTRIC
    assert houses.effective_system == HouseSystem.TOPOCENTRIC
    assert houses.fallback is False
    assert houses.asc == pytest.approx(210.23753854604496, abs=1e-9)
    assert houses.mc == pytest.approx(180.49817310130808, abs=1e-9)
    assert houses.cusps[1] == pytest.approx(231.58872947023573, abs=1e-8)


def test_calculate_houses_default_policy_still_falls_back_for_topocentric_no_solution_high_lat() -> None:
    houses = calculate_houses(
        _JD_J2000,
        _LAT_77,
        0.0,
        HouseSystem.TOPOCENTRIC,
    )

    assert houses.effective_system == HouseSystem.PORPHYRY
    assert houses.fallback is True


def test_experimental_topocentric_policy_raises_when_no_ordered_solution_exists() -> None:
    with pytest.raises(ValueError, match="experimental search for 'T' did not return usable cusps or raised"):
        houses_from_armc(
            250.0,
            _OB_J2000,
            _LAT_77,
            HouseSystem.TOPOCENTRIC,
            policy=HousePolicy.experimental(),
        )


def test_search_experimental_topocentric_reports_unordered_cycle_at_armc_250() -> None:
    result = search_experimental_topocentric(
        250.0,
        _OB_J2000,
        _LAT_77,
        asc=21.67186798514654,
        mc=251.5337610049483,
    )

    assert result.status == ExperimentalTopocentricStatus.UNORDERED_CUSP_CYCLE
    assert result.has_solution is False
    assert result.cusps is None
    assert "assembled cusps not strictly ordered" in result.diagnostic_summary


def test_search_experimental_topocentric_reports_assembly_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_assembly_failure(*args, **kwargs):
        raise RuntimeError("forced assembly failure")

    monkeypatch.setattr(houses_module, "_assemble_pole_height_quadrant_family", _raise_assembly_failure)

    result = search_experimental_topocentric(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalTopocentricStatus.ASSEMBLY_FAILED
    assert result.has_solution is False
    assert result.cusps is None
    assert "assembly failed" in result.diagnostic_summary


def test_scan_experimental_topocentric_admissibility_finds_77n_windows() -> None:
    admissibility = scan_experimental_topocentric_admissibility(
        _LAT_77,
        _OB_J2000,
        armc_start=0.0,
        armc_end=355.0,
        armc_step=5.0,
    )

    assert isinstance(admissibility, ExperimentalTopocentricAdmissibilityMap)
    assert admissibility.has_any_window is True
    assert 90.0 in admissibility.valid_armcs
    assert admissibility.valid_fraction == pytest.approx(39.0 / 72.0, abs=1e-12)


def test_scan_experimental_topocentric_admissibility_recovers_measured_77n_window_bounds() -> None:
    admissibility = scan_experimental_topocentric_admissibility(
        _LAT_77,
        _OB_J2000,
        armc_start=0.0,
        armc_end=355.0,
        armc_step=5.0,
    )

    assert admissibility.windows == (
        ExperimentalTopocentricWindow(start_armc=0.0, end_armc=185.0, sample_count=38),
        ExperimentalTopocentricWindow(start_armc=355.0, end_armc=355.0, sample_count=1),
    )


def test_scan_experimental_topocentric_admissibility_rejects_non_positive_step() -> None:
    with pytest.raises(ValueError, match="armc_step must be > 0"):
        scan_experimental_topocentric_admissibility(
            _LAT_77,
            _OB_J2000,
            armc_step=0.0,
        )
