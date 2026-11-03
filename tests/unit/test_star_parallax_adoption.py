"""The adopted-parallax rules combine Gaia, Hipparcos and SIMBAD as the design record states.

Governing record: docs/architecture/STAR_PARALLAX_SIGNIFICANCE_POLICY_DESIGN.md, Section 4.2.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _ingest():
    path = ROOT / "scripts" / "data_ingestion" / "augment_star_registry_astrometry.py"
    spec = importlib.util.spec_from_file_location("augment_star_registry_astrometry", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ingest = _ingest()


def _gaia(parallax=10.0, error=0.1, ruwe=1.0, params=31, zero_point=-0.02):
    return {
        "parallax": parallax, "parallax_error": error, "ruwe": ruwe,
        "astrometric_params_solved": params, "zero_point": zero_point,
    }


def _hip(plx=10.0, error=0.5):
    return {"plx": plx, "e_plx": error}


def _adopt(gaia=None, hipparcos=None, simbad=None):
    return ingest.adopt_parallax({"gaia": gaia, "hipparcos": hipparcos, "simbad": simbad})


def test_gaia_alone_applies_the_zero_point_and_keeps_its_error() -> None:
    result = _adopt(gaia=_gaia(parallax=10.0, error=0.1, zero_point=-0.03))
    assert result["parallax_mas"] == pytest.approx(10.03)
    assert result["parallax_error_mas"] == pytest.approx(0.1)
    assert result["parallax_source"] == "gaia_dr3"
    assert result["flags"] == []


def test_gaia_error_is_inflated_by_ruwe_above_one() -> None:
    assert _adopt(gaia=_gaia(error=0.1, ruwe=3.0))["parallax_error_mas"] == pytest.approx(0.3)
    assert _adopt(gaia=_gaia(error=0.1, ruwe=0.8))["parallax_error_mas"] == pytest.approx(0.1)


def test_gaia_without_a_zero_point_is_used_uncorrected_and_flagged() -> None:
    result = _adopt(gaia=_gaia(parallax=10.0, zero_point=None))
    assert result["parallax_mas"] == 10.0
    assert result["parallax_source"] == "gaia_dr3_uncalibrated"
    assert result["flags"] == ["gaia_uncalibrated"]


@pytest.mark.parametrize("params", [3, 5, 33, 0])
def test_gaia_two_parameter_and_other_solutions_are_not_used(params: int) -> None:
    result = _adopt(gaia=_gaia(params=params), hipparcos=_hip(plx=7.0, error=0.4))
    assert result["parallax_source"] == "hipparcos_2007"
    assert result["parallax_mas"] == 7.0


def test_six_parameter_solution_is_admitted() -> None:
    assert _adopt(gaia=_gaia(params=95))["parallax_source"] == "gaia_dr3"


def test_agreeing_catalogs_combine_by_inverse_variance() -> None:
    result = _adopt(gaia=_gaia(parallax=10.0, error=0.1, zero_point=0.0), hipparcos=_hip(plx=10.2, error=0.4))
    weight_g, weight_h = 0.1 ** -2, 0.4 ** -2
    assert result["parallax_mas"] == pytest.approx((10.0 * weight_g + 10.2 * weight_h) / (weight_g + weight_h))
    assert result["parallax_error_mas"] == pytest.approx((weight_g + weight_h) ** -0.5)
    assert result["parallax_source"] == "gaia_hipparcos_combined"
    assert "discordant" not in result["flags"]
    assert result["parallax_error_mas"] < 0.1


def test_discordant_catalogs_take_the_midpoint_and_span_both() -> None:
    result = _adopt(gaia=_gaia(parallax=3.134, error=0.171, zero_point=0.0, ruwe=1.0),
                    hipparcos=_hip(plx=10.25, error=0.47))
    low, high = 3.134, 10.25
    assert result["parallax_source"] == "gaia_hipparcos_combined_discordant"
    assert "discordant" in result["flags"]
    assert result["discordance_z"] > 3.0
    assert result["parallax_mas"] == pytest.approx((low + high) / 2.0)
    assert result["parallax_error_mas"] == pytest.approx((high - low) / 2.0)
    assert abs(result["parallax_mas"] - low) <= result["parallax_error_mas"] * (1 + 1e-12)
    assert abs(result["parallax_mas"] - high) <= result["parallax_error_mas"] * (1 + 1e-12)


def test_discordant_result_does_not_depend_on_which_catalog_is_more_precise() -> None:
    narrow_gaia = _adopt(gaia=_gaia(parallax=5.0, error=0.01, zero_point=0.0),
                         hipparcos=_hip(plx=9.0, error=1.0))
    narrow_hip = _adopt(gaia=_gaia(parallax=5.0, error=1.0, zero_point=0.0),
                        hipparcos=_hip(plx=9.0, error=0.01))
    for result in (narrow_gaia, narrow_hip):
        assert result["parallax_source"] == "gaia_hipparcos_combined_discordant"
        assert result["parallax_mas"] == pytest.approx(7.0)
        assert result["parallax_error_mas"] == pytest.approx(2.0)


def test_discordance_boundary_is_three_combined_standard_errors() -> None:
    sigma_g, sigma_h = 0.3, 0.4
    combined = math.hypot(sigma_g, sigma_h)
    inside = _adopt(gaia=_gaia(parallax=10.0 + 2.999 * combined, error=sigma_g, zero_point=0.0),
                    hipparcos=_hip(plx=10.0, error=sigma_h))
    outside = _adopt(gaia=_gaia(parallax=10.0 + 3.001 * combined, error=sigma_g, zero_point=0.0),
                     hipparcos=_hip(plx=10.0, error=sigma_h))
    assert inside["parallax_source"] == "gaia_hipparcos_combined"
    assert outside["parallax_source"] == "gaia_hipparcos_combined_discordant"


def test_discordant_error_never_falls_below_the_combined_error() -> None:
    result = _adopt(gaia=_gaia(parallax=10.0, error=0.01, zero_point=0.0),
                    hipparcos=_hip(plx=10.5, error=0.01))
    weight = 0.01 ** -2
    assert result["parallax_error_mas"] >= (2 * weight) ** -0.5
    assert result["parallax_error_mas"] == pytest.approx(0.25)


def test_hipparcos_alone_is_adopted() -> None:
    result = _adopt(hipparcos=_hip(plx=6.55, error=0.83))
    assert (result["parallax_mas"], result["parallax_error_mas"]) == (6.55, 0.83)
    assert result["parallax_source"] == "hipparcos_2007"


def test_simbad_is_a_fallback_only_when_neither_primary_exists() -> None:
    simbad = {"plx_value": 68.3, "plx_err": 0.4, "plx_bibcode": "2020yCat.1350....0G"}
    result = _adopt(simbad=simbad)
    assert result["parallax_source"] == "simbad_fallback"
    assert result["parallax_bibcodes"] == ["2020yCat.1350....0G"]
    primary = _adopt(hipparcos=_hip(plx=7.0, error=0.4), simbad=simbad)
    assert primary["parallax_source"] == "hipparcos_2007"


@pytest.mark.parametrize("simbad", [None, {"plx_value": None, "plx_err": None, "plx_bibcode": None},
                                    {"plx_value": 5.0, "plx_err": None, "plx_bibcode": "x"},
                                    {"plx_value": 5.0, "plx_err": 0.0, "plx_bibcode": "x"}])
def test_no_usable_candidate_is_none(simbad) -> None:
    result = _adopt(simbad=simbad)
    assert result["parallax_source"] == "none"
    assert result["parallax_mas"] is None and result["parallax_error_mas"] is None


@pytest.mark.parametrize("error", [0.0, -0.1, None, math.nan, math.inf * 0.0])
def test_a_candidate_without_a_positive_error_is_not_used(error) -> None:
    assert _adopt(hipparcos=_hip(plx=5.0, error=error))["parallax_source"] == "none"
    assert _adopt(gaia=_gaia(error=error))["parallax_source"] == "none"


def test_a_negative_parallax_is_reported_not_hidden() -> None:
    result = _adopt(hipparcos=_hip(plx=-1.2, error=2.0))
    assert result["parallax_mas"] == -1.2
    assert result["parallax_source"] == "hipparcos_2007"


def test_candidate_order_does_not_change_the_result() -> None:
    first = _adopt(gaia=_gaia(parallax=12.0, error=0.2, zero_point=-0.02), hipparcos=_hip(plx=12.4, error=0.5))
    second = _adopt(hipparcos=_hip(plx=12.4, error=0.5), gaia=_gaia(parallax=12.0, error=0.2, zero_point=-0.02))
    assert first == second


def test_zero_point_is_undefined_outside_the_published_validity() -> None:
    base = {"phot_g_mean_mag": 12.0, "ecl_lat": 20.0, "astrometric_params_solved": 31,
            "nu_eff_used_in_astrometry": 1.5, "pseudocolour": None}
    assert ingest.gaia_zero_point({**base, "phot_g_mean_mag": 5.9}) is None
    assert ingest.gaia_zero_point({**base, "phot_g_mean_mag": 21.1}) is None
    assert ingest.gaia_zero_point({**base, "phot_g_mean_mag": None}) is None
    assert ingest.gaia_zero_point({**base, "nu_eff_used_in_astrometry": 1.0}) is None
    assert ingest.gaia_zero_point({**base, "astrometric_params_solved": 3}) is None
    six = {**base, "astrometric_params_solved": 95, "nu_eff_used_in_astrometry": None}
    assert ingest.gaia_zero_point({**six, "pseudocolour": 1.1}) is None
    assert ingest.gaia_zero_point({**six, "pseudocolour": None}) is None
