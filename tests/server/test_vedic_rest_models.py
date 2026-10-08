"""Valid compatibility and period-interval witnesses for VED-005 models."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from moira.dasha_systems import AshtottariPolicy, YoginiPolicy, ashtottari, yogini_dasha
from moira.sidereal import list_ayanamsa_systems
from moira_server.models.alternate_dashas import AlternateDashaPeriodRequest
from moira_server.models.dasha import DashaNatalRequest
from moira_server.models.shadbala import ShadbalaChartRequest
from moira_server.models.vedic_dignities import VedicDignityChartRequest
from moira_server.models._vedic_inputs import resolve_vedic_house_system


@pytest.mark.parametrize("text", ["2000-01-01T12:00:00Z", "2000-01-01T07:00:00-05:00", "2000-01-01 17:30:00+05:30"])
def test_aware_civil_timestamp_normalization(text):
    parsed = DashaNatalRequest(dt=text)
    assert parsed.dt.astimezone(timezone.utc) == datetime(2000, 1, 1, 12, tzinfo=timezone.utc)


def test_engine_ayanamsa_registry_and_house_aliases_remain_admitted():
    for name in list_ayanamsa_systems():
        assert DashaNatalRequest(dt="2000-01-01T12:00:00Z", ayanamsa=name).ayanamsa == name
    for alias, code in (("P", "P"), ("placidus", "P"), ("whole_sign", "W"), ("whole-sign", "W"), (" Whole Sign ", "W")):
        request = ShadbalaChartRequest(dt="2000-01-01T12:00:00Z", observer_lat=40, observer_lon=-74, house_system=alias)
        assert request.house_system == alias
        assert resolve_vedic_house_system(alias) == code


def test_partial_classical_maps_are_preserved_without_filling_missing_planets():
    request = VedicDignityChartRequest(sidereal_longitudes={"Sun": -350})
    assert request.sidereal_longitudes == {"Sun": -350.0}
    with pytest.raises(ValidationError):
        VedicDignityChartRequest(sidereal_longitudes={"Sun": 10, "Pluto": 50})


def _period_input(period):
    return {"system": period.system, "level": period.level, "lord": period.lord,
            "start_jd": period.start_jd, "end_jd": period.end_jd,
            "sub": [_period_input(child) for child in period.sub]}


@pytest.mark.parametrize("system", ["ashtottari", "yogini"])
@pytest.mark.parametrize("year_basis", ["julian_365.25", "savana_360"])
@pytest.mark.parametrize("longitude", [0.0, 10.0, 179.0, 359.999])
def test_generated_periods_remain_admissible(system, year_basis, longitude):
    # Engine-generated nested intervals expose floating-point endpoint behavior.
    # This is compatibility evidence, not independent historical authority.
    if system == "ashtottari":
        periods = ashtottari(longitude, 2451545.0, levels=3,
                            policy=AshtottariPolicy(year_basis=year_basis, bypass_eligibility=True))
    else:
        periods = yogini_dasha(longitude, 2451545.0, levels=3,
                              policy=YoginiPolicy(year_basis=year_basis))
    for period in periods:
        parsed = AlternateDashaPeriodRequest.model_validate(_period_input(period))
        assert parsed.start_jd == period.start_jd
        assert parsed.end_jd == period.end_jd


def test_partial_children_are_admitted_but_overlap_is_rejected():
    parent = {"system": "ashtottari", "level": 1, "lord": "Sun", "start_jd": 10.0, "end_jd": 20.0}
    child = {**parent, "level": 2, "start_jd": 12.0, "end_jd": 13.0}
    assert AlternateDashaPeriodRequest(**parent, sub=[child]).sub[0].start_jd == 12.0
    with pytest.raises(ValidationError):
        AlternateDashaPeriodRequest(**parent, sub=[child, {**child, "start_jd": 12.5, "end_jd": 14.0}])


def test_period_tolerance_is_bounded_and_duration_cannot_overflow():
    parent = {"system": "ashtottari", "level": 1, "lord": "Sun", "start_jd": 10.0, "end_jd": 20.0}
    child = {**parent, "level": 2, "start_jd": 19.0, "end_jd": 20.0 + 0.5e-6}
    parsed = AlternateDashaPeriodRequest(**parent, sub=[child])
    assert parsed.sub[0].end_jd == child["end_jd"]  # Never repair/snap input.
    with pytest.raises(ValidationError):
        AlternateDashaPeriodRequest(**parent, sub=[{**child, "end_jd": 20.0 + 2e-6}])
    with pytest.raises(ValidationError):
        AlternateDashaPeriodRequest(**{**parent, "start_jd": -1e308, "end_jd": 1e308})


def test_profile_year_receipt_uses_the_engine_default_policy(monkeypatch):
    import moira.dasha as doctrine
    from moira_server.models.vedic_profile import VedicChartProfileRequest
    from moira_server.services import vedic_profile
    monkeypatch.setattr(doctrine, "DEFAULT_VIMSHOTTARI_POLICY", doctrine.VimshottariComputationPolicy(
        year=doctrine.VimshottariYearPolicy(year_basis="savana_360"),
    ))
    def supplied_moon(_engine, request):
        # Only chart acquisition is substituted. The selected year doctrine
        # and actual chain reduction run through the existing engine.
        return doctrine.dasha_active_line(doctrine.current_dasha(
            10.0, 2451545.0, 2451600.0,
            levels=request.levels, year_basis=request.natal.year_basis,
        ))
    monkeypatch.setattr(vedic_profile, "compute_dasha_active_line", supplied_moon)
    request = VedicChartProfileRequest(
        dt="2000-01-01T12:00:00Z", current_dt="2000-02-25T12:00:00Z",
        observer_lat=40.0, observer_lon=-74.0, dasha_levels=1,
        include={"chart": False, "panchanga": False, "panchanga_profile": False,
                 "shadbala": False, "shadbala_profile": False, "dasha_current": True},
    )
    response = vedic_profile.compute_vedic_chart_profile(object(), request)
    assert response.request.dasha_year_basis is None
    assert response.policy_receipt.applied_dasha_year_basis == response.dasha_current.mahadasha.year_basis == "savana_360"
