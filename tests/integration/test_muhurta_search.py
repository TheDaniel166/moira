"""Installed-DE441 composition and compatibility receipts; no predictive claim."""
from types import SimpleNamespace
from datetime import datetime, timezone

import pytest

import moira
import moira.facade as facade
import moira.vedic as vedic
import moira.muhurta_search as search
from moira._ephemeris_time import _bind_ephemeris_time
from moira.julian import julian_day, utc_to_ut1
from moira.muhurta import MuhurtaPolicy, personal_muhurta_score, find_best_muhurta_windows
from moira.electional import ElectionalPolicy
from moira.planets import planet_at
from moira.sidereal import Ayanamsa, _ayanamsa_at_tt
from moira.spk_reader import get_reader, use_reader_override

pytestmark = pytest.mark.requires_ephemeris


@pytest.mark.parametrize("system", Ayanamsa.ALL)
def test_reader_bound_positions_frames_and_canonical_personal_score(moira_engine, system):
    start = julian_day(2026, 10, 6)
    policy = search.MuhurtaSearchPolicy(ayanamsa_system=system, step_days=.25,
        min_score=-100, muhurta_policy=MuhurtaPolicy(weight_tara=2, weight_chandra=3))
    result = moira_engine.find_muhurta_windows(start, start+.25,
        janma_moon_sidereal_lon=100, policy=policy)
    assert len(result.samples) == 2
    for sample in result.samples:
        bound = _bind_ephemeris_time(sample.jd_ut1, moira_engine._reader)
        assert sample.jd_tt == bound.epoch_tt
        assert sample.jd_tdb == bound.epoch_tdb
        assert sample.clock_identity == bound.identity.summary_label
        assert sample.delta_t_source == bound.raw_delta_t.source_product
        for body, longitude in (("Sun", sample.sun_tropical_longitude),
                                 ("Moon", sample.moon_tropical_longitude)):
            assert longitude == pytest.approx(planet_at(body, sample.jd_ut1,
                reader=moira_engine._reader, jd_tt=bound.epoch_tt).longitude, abs=1e-10)
        with use_reader_override(moira_engine._reader):
            assert sample.ayanamsa_degrees == pytest.approx(
                _ayanamsa_at_tt(sample.jd_tt, system, "true"), abs=1e-10)
        direct = personal_muhurta_score(sample.panchanga, 100,
            (sample.moon_tropical_longitude-sample.ayanamsa_degrees) % 360, policy.muhurta_policy)
        assert sample.score == direct
    assert result.windows[0].qualifying_jds == (start, start+.25)


@pytest.mark.parametrize("year", [1600, 1900, 2000, 2100])
def test_historical_and_future_samples_preserve_the_serving_clock(moira_engine, year):
    jd = julian_day(year, 1, 1)
    result = moira_engine.find_muhurta_windows(jd, jd+.01,
        policy=search.MuhurtaSearchPolicy(step_days=.1))
    assert result.samples[0].jd_tt == _bind_ephemeris_time(jd, moira_engine._reader).epoch_tt
    assert result.samples[-1].jd_ut1 == jd+.01


def test_explicit_reader_restores_context_on_success_and_coverage_failure(moira_engine):
    ambient = object()
    with use_reader_override(ambient):
        result = moira_engine.find_muhurta_windows(2451545, 2451545.01)
        assert get_reader() is ambient
        assert len(result.samples) == 2
        with pytest.raises(search.MuhurtaCoverageError):
            moira_engine.find_muhurta_windows(-9500000, -9499999.99)
        assert get_reader() is ambient


def test_legacy_tuple_view_delegates_to_personal_search(moira_engine):
    policy = search.MuhurtaSearchPolicy(step_days=.25, min_score=-100, max_results=128)
    canonical = moira_engine.find_muhurta_windows(2451545, 2451545.5,
        janma_moon_sidereal_lon=100, policy=policy)
    legacy = find_best_muhurta_windows(2451545, 2451545.5, 51.5, -.1,
        janma_moon_sidereal_lon=100, electional_policy=ElectionalPolicy(step_days=.25),
        min_score=-100, reader=moira_engine._reader)
    assert [(w.qualifying_jds, score) for w, score in legacy] == [
        (w.qualifying_jds, w.peak.score.total) for w in canonical.windows]
    peak = canonical.windows[0].peak
    chart = SimpleNamespace(jd_ut=peak.jd_ut1, jd_tt=peak.jd_tt,
        planets={"Sun": SimpleNamespace(longitude=peak.sun_tropical_longitude),
                 "Moon": SimpleNamespace(longitude=peak.moon_tropical_longitude)})
    assert moira_engine.muhurta_score_for_chart(chart,
        janma_moon_sidereal_lon=100).score == peak.score


def test_search_exports_have_one_identity():
    for name in search.__all__:
        assert name in moira.__all__ and name in facade.__all__ and name in vedic.__all__
        assert getattr(moira, name) is getattr(facade, name) is getattr(vedic, name) is getattr(search, name)


def test_facade_chart_adaptation_does_not_mislabel_civil_utc_as_ut1(moira_engine):
    chart = moira_engine.chart(datetime(2000,1,1,12,tzinfo=timezone.utc),
                               bodies=["Sun","Moon"],include_nodes=False)
    moment = moira_engine.muhurta_score_for_chart(chart,janma_moon_sidereal_lon=100)
    assert moment.jd_ut1 == utc_to_ut1(chart.jd_ut)
    assert moment.jd_ut1 != chart.jd_ut
    assert moment.jd_tt == moment.jd_ut1 + chart.delta_t/86400
    assert moment.input_time_basis == "facade_civil_utc_delta_t"
    assert moment.clock_identity == "caller_supplied_chart"
    assert moment.jd_tdb is None
