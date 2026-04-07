from __future__ import annotations

import pytest

from moira.constants import HouseSystem
from moira.experimental_placidus import (
    ExperimentalPlacidusStatus,
    scan_experimental_placidus_admissibility,
    search_experimental_placidus,
)
from moira.houses import HousePolicy, calculate_houses, houses_from_armc
from moira.julian import ut_to_tt
from moira.obliquity import true_obliquity


_JD_J2000 = 2451545.0
_LAT_77 = 77.0
_OB_J2000 = true_obliquity(ut_to_tt(_JD_J2000))
_ARMC_VALID = 90.0
_LON_FOR_ARMC_VALID = 169.54292771060392


def test_search_experimental_placidus_finds_unique_ordered_solution_at_77n_armc_90() -> None:
    result = search_experimental_placidus(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        asc=180.0,
        mc=90.0,
    )

    assert result.status == ExperimentalPlacidusStatus.UNIQUE_ORDERED_SOLUTION
    assert result.ordered_solution_count == 1
    assert result.cusps is not None
    assert result.cusps[1] == pytest.approx(194.28146317340529, abs=1e-9)
    assert result.cusps[2] == pytest.approx(214.2401525041282, abs=1e-9)
    assert result.cusps[10] == pytest.approx(145.75984749587178, abs=1e-9)
    assert result.cusps[11] == pytest.approx(165.7185368265947, abs=1e-9)


def test_houses_from_armc_experimental_policy_uses_placidus_at_77n_valid_armc() -> None:
    houses = houses_from_armc(
        _ARMC_VALID,
        _OB_J2000,
        _LAT_77,
        HouseSystem.PLACIDUS,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.PLACIDUS
    assert houses.effective_system == HouseSystem.PLACIDUS
    assert houses.fallback is False
    assert houses.cusps[1] == pytest.approx(194.28146317340529, abs=1e-9)
    assert houses.cusps[10] == pytest.approx(145.75984749587178, abs=1e-9)


def test_calculate_houses_experimental_policy_uses_public_jd_path() -> None:
    houses = calculate_houses(
        _JD_J2000,
        _LAT_77,
        _LON_FOR_ARMC_VALID,
        HouseSystem.PLACIDUS,
        policy=HousePolicy.experimental(),
    )

    assert houses.system == HouseSystem.PLACIDUS
    assert houses.effective_system == HouseSystem.PLACIDUS
    assert houses.fallback is False
    assert houses.asc == pytest.approx(180.0, abs=1e-9)
    assert houses.mc == pytest.approx(90.0, abs=1e-9)
    assert houses.cusps[1] == pytest.approx(194.28146317340529, abs=1e-8)


def test_calculate_houses_default_policy_still_falls_back_at_same_case() -> None:
    houses = calculate_houses(
        _JD_J2000,
        _LAT_77,
        _LON_FOR_ARMC_VALID,
        HouseSystem.PLACIDUS,
    )

    assert houses.effective_system == HouseSystem.PORPHYRY
    assert houses.fallback is True


def test_experimental_policy_raises_when_no_ordered_solution_exists() -> None:
    with pytest.raises(ValueError, match="experimental Placidus search failed: status="):
        houses_from_armc(
            0.0,
            _OB_J2000,
            _LAT_77,
            HouseSystem.PLACIDUS,
            policy=HousePolicy.experimental(),
        )


def test_search_experimental_placidus_reports_missing_root_diagnostics_at_armc_0() -> None:
    result = search_experimental_placidus(
        0.0,
        _OB_J2000,
        _LAT_77,
        asc=0.0,
        mc=0.0,
    )

    assert result.status == ExperimentalPlacidusStatus.NO_REQUIRED_ROOTS
    assert result.has_solution is False
    assert len(result.h11_roots) == 0
    assert "root_counts=" in result.diagnostic_summary


def test_scan_experimental_placidus_admissibility_finds_77n_window_around_armc_90() -> None:
    admissibility = scan_experimental_placidus_admissibility(
        _LAT_77,
        _OB_J2000,
        armc_start=88.0,
        armc_end=92.0,
        armc_step=0.5,
        sample_count=8000,
    )

    assert admissibility.has_any_window is True
    assert 90.0 in admissibility.valid_armcs
    assert admissibility.windows[0].start_armc <= 90.0 <= admissibility.windows[0].end_armc


def test_experimental_policy_is_placidus_only_for_now() -> None:
    with pytest.raises(ValueError, match="only implemented for 'P'"):
        houses_from_armc(
            _ARMC_VALID,
            _OB_J2000,
            _LAT_77,
            HouseSystem.KOCH,
            policy=HousePolicy.experimental(),
        )