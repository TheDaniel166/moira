"""Composition and bounded-search contracts; fixtures are synthetic, not source proof."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from moira.muhurta import MuhurtaPolicy, personal_muhurta_score, muhurta_scorer
import moira.muhurta_search as search
from moira.sidereal import _ayanamsa_at_tt
from moira.spk_reader import OutOfRangeError, MissingKernelError


def _chart(moon=70.0):
    return SimpleNamespace(jd_ut=2451545.0, jd_tt=2451545.001,
        planets={"Sun": SimpleNamespace(longitude=280.0),
                 "Moon": SimpleNamespace(longitude=moon)})


@pytest.mark.parametrize("name", ["weight_tithi", "weight_vara", "weight_nakshatra",
    "weight_yoga", "weight_karana", "weight_tara", "weight_chandra"])
@pytest.mark.parametrize("value", [True, "1", float("nan"), float("inf"), -1])
def test_policy_rejects_invalid_weights(name, value):
    with pytest.raises(ValueError):
        MuhurtaPolicy(**{name: value})


def test_policy_overflow_and_reserved_flag():
    with pytest.raises(ValueError, match="overflow"):
        MuhurtaPolicy(weight_chandra=1e308)
    with pytest.raises(ValueError, match="reserved"):
        MuhurtaPolicy(use_classical_ashubha_yoga=False)


def test_chart_personalization_uses_natal_moon_and_explicit_frame():
    chart = _chart()
    policy = MuhurtaPolicy(weight_tara=2, weight_chandra=3)
    moment = search.muhurta_score_for_chart(chart, janma_moon_sidereal_lon=100,
                                           ayanamsa_system="Raman", policy=policy)
    offset = _ayanamsa_at_tt(chart.jd_tt, "Raman", "true")
    direct = personal_muhurta_score(moment.panchanga, 100, (70 - offset) % 360, policy)
    assert moment.score == direct
    assert moment.natal_mode == "tara_chandra"
    assert moment.ayanamsa_degrees == offset
    assert moment.panchanga.jd == chart.jd_ut
    assert muhurta_scorer(chart, janma_moon_sidereal_lon=100,
                         ayanamsa_system="Raman", policy=policy) == direct.total
    different = search.muhurta_score_for_chart(chart, janma_moon_sidereal_lon=220,
                                              ayanamsa_system="Raman", policy=policy)
    assert moment.score.chandra != different.score.chandra
    assert moment.score.tara != different.score.tara


@pytest.mark.parametrize("missing", ["jd_ut", "jd_tt", "Sun", "Moon", "longitude"])
def test_chart_failures_have_no_sentinel_or_defaults(missing):
    chart = _chart()
    if missing in ("Sun", "Moon"):
        del chart.planets[missing]
    elif missing == "longitude":
        del chart.planets["Sun"].longitude
    else:
        delattr(chart, missing)
    with pytest.raises(ValueError):
        muhurta_scorer(chart)


def test_nakshatra_alone_is_not_a_natal_sign():
    with pytest.raises(ValueError, match="alone is insufficient"):
        muhurta_scorer(_chart(), janma_nakshatra="Ashwini")
    with pytest.raises(ValueError, match="disagrees"):
        muhurta_scorer(_chart(), janma_nakshatra="Ashwini", janma_moon_sidereal_lon=100)


@pytest.mark.parametrize("field",["jd_ut","jd_tt"])
def test_chart_epochs_are_bounded_before_ayanamsa_work(monkeypatch,field):
    chart = _chart()
    setattr(chart,field,1e300)
    monkeypatch.setattr(search,"_offset",lambda *args:pytest.fail("unexpected astronomy"))
    with pytest.raises(ValueError,match="chart epochs"):
        search.muhurta_score_for_chart(chart)


@pytest.mark.parametrize("method",["find_muhurta_windows","muhurta_score_for_chart"])
def test_readerless_facade_cannot_borrow_an_ambient_kernel(monkeypatch,method):
    from moira import Moira
    engine = object.__new__(Moira)
    engine._reader_obj = None
    engine._kernel_path = None
    engine._kernel_init_error = None
    engine._try_initialize_reader = lambda: None
    monkeypatch.setattr(search,"get_reader",lambda:pytest.fail("unexpected ambient reader"))
    with pytest.raises(search.MuhurtaResourceError,match="this Moira instance"):
        if method == "find_muhurta_windows":
            engine.find_muhurta_windows(2451545,2451546)
        else:
            engine.muhurta_score_for_chart(_chart())
    if method == "find_muhurta_windows":
        with pytest.raises(ValueError,match="ordered"):
            engine.find_muhurta_windows(2451545,2451545)


def test_supplied_electional_evaluation_does_not_double_subtract_frame():
    chart = _chart()
    payload = SimpleNamespace(chart=chart, planet_longitudes={"Sun": 0, "Moon": 0})
    assert muhurta_scorer(payload) == muhurta_scorer(chart)


def test_moment_receipt_cannot_be_rewritten_or_describe_other_inputs():
    moment = search.muhurta_score_for_chart(_chart())
    with pytest.raises(TypeError):
        moment.score.breakdown["tithi"] = 999
    with pytest.raises(ValueError, match="Panchanga does not describe"):
        replace(moment, moon_tropical_longitude=100)
    with pytest.raises(ValueError, match="score does not describe"):
        replace(moment, score=replace(moment.score, total=999))
    with pytest.raises(ValueError, match="finite"):
        search.MuhurtaSearchWindow((moment,), moment, float("nan"), None)


def test_grid_closed_endpoints_and_non_dividing_step():
    assert search._sample_grid(2451545.0, 2451545.5, .2) == (
        2451545.0, 2451545.2, 2451545.4, 2451545.5)
    assert search._sample_grid(2451545.0, 2451545.5, .25) == (
        2451545.0, 2451545.25, 2451545.5)


@pytest.mark.parametrize("kwargs", [
    {"start_jd_ut1": True, "end_jd_ut1": 2451546},
    {"start_jd_ut1": 2451545, "end_jd_ut1": 2451545},
    {"start_jd_ut1": 2451545, "end_jd_ut1": 2451580},
    {"start_jd_ut1": 2451545, "end_jd_ut1": 2451550,
     "policy": search.MuhurtaSearchPolicy(step_days=1/1440)},
    {"start_jd_ut1": 2451545, "end_jd_ut1": 2451546, "janma_moon_sidereal_lon": "1"},
])
def test_search_rejects_invalid_scope_before_reader_access(monkeypatch, kwargs):
    monkeypatch.setattr(search, "get_reader", lambda: pytest.fail("unexpected reader access"))
    with pytest.raises(ValueError):
        search.find_muhurta_windows(**kwargs)


def _synthetic_samples(monkeypatch, phases=None):
    # Isolate scan/selection from ephemeris. Every actual score is still computed
    # by the real Panchanga and personal evaluator from these explicit phases.
    monkeypatch.setattr(search, "_offset", lambda tt, system: 0)
    identity = SimpleNamespace(planetary_ephemeris=441, lunar_ephemeris=441,
                               summary_label="synthetic_clock")
    monkeypatch.setattr(search, "_bind_ephemeris_time", lambda jd, reader: SimpleNamespace(
        epoch_tt=jd+.001, epoch_tdb=jd+.0011, identity=identity,
        raw_delta_t=SimpleNamespace(source_product="synthetic")))
    # Favorable Sampat/H1 = +2, Janma/H1 = +1, Vipat/H2 = -1,
    # Kshema/H2 = +1. The middle rejected sample must split qualifying runs.
    phases = [15, 15, 1, 30, 41, 41] if phases is None else phases
    calls = []
    def planet(body, jd, **kwargs):
        calls.append((body, jd, kwargs))
        index = round((jd-2451545.0)*4)
        return SimpleNamespace(longitude=280 if body == "Sun" else phases[index])
    monkeypatch.setattr(search, "planet_at", planet)
    return calls


def test_threshold_splits_runs_and_full_range_precedes_top_cap(monkeypatch):
    calls = _synthetic_samples(monkeypatch)
    weights = MuhurtaPolicy(weight_tithi=0, weight_vara=0, weight_nakshatra=0,
                            weight_yoga=0, weight_karana=0)
    result = search.find_muhurta_windows(2451545, 2451546.25, reader=object(),
        janma_moon_sidereal_lon=1, policy=search.MuhurtaSearchPolicy(
            step_days=.25, min_score=1, max_results=1, muhurta_policy=weights))
    assert len(calls) == 12  # Sun and Moon once per grid point, no rescoring.
    assert [s.score.total for s in result.samples] == [2, 2, 1, -1, 1, 1]
    assert result.qualifying_sample_count == 5
    assert result.observed_window_count == 2
    assert result.truncated
    window = result.windows[0]
    assert window.qualifying_jds == (2451545, 2451545.25, 2451545.5)
    assert window.peak.jd_ut1 == 2451545  # earliest tie
    assert window.left_unqualified_jd is None
    assert window.right_unqualified_jd == 2451545.75
    assert all(c[2]["jd_tt"] == c[1]+.001 for c in calls)
    with pytest.raises(ValueError, match="complete requested grid"):
        replace(result, samples=result.samples[:-1])


def test_empty_selection_is_a_successful_completed_scan(monkeypatch):
    _synthetic_samples(monkeypatch)
    result = search.find_muhurta_windows(2451545, 2451545.5, reader=object(),
        policy=search.MuhurtaSearchPolicy(step_days=.25, min_score=1e6))
    assert len(result.samples) == 3
    assert result.windows == ()
    assert result.qualifying_sample_count == result.observed_window_count == 0
    assert not result.truncated


def test_later_stronger_run_is_selected_after_full_scan(monkeypatch):
    _synthetic_samples(monkeypatch, phases=[1, 1, 30, 15, 15])
    weights = MuhurtaPolicy(weight_tithi=0, weight_vara=0, weight_nakshatra=0,
                            weight_yoga=0, weight_karana=0)
    result = search.find_muhurta_windows(2451545,2451546,reader=object(),
        janma_moon_sidereal_lon=1,policy=search.MuhurtaSearchPolicy(
            step_days=.25,min_score=1,max_results=1,muhurta_policy=weights))
    assert result.windows[0].peak.jd_ut1 == 2451545.75
    assert result.windows[0].left_unqualified_jd == 2451545.5
    assert result.windows[0].right_unqualified_jd is None
    assert result.observed_window_count == 2


def test_sample_budget_includes_final_clipped_endpoint():
    assert len(search._sample_grid(2451545,2451545+4095/1440,1/1440)) == 4096
    with pytest.raises(ValueError,match="4096"):
        search._sample_grid(2451545,2451545+4095.5/1440,1/1440)


@pytest.mark.parametrize("policy",[
    {"merge_gap_days":.1}, {"boundary_refine_steps":1},
    {"bodies":("Sun",)}, {"bodies":("Sun","Moon","Moon")},
    {"zodiac_frame":"sidereal","ayanamsa_system":"Raman"},
])
def test_legacy_scanner_settings_cannot_silently_change_product(monkeypatch,policy):
    from moira.electional import ElectionalPolicy
    from moira.muhurta import find_best_muhurta_windows
    monkeypatch.setattr(search,"get_reader",lambda:pytest.fail("unexpected reader access"))
    with pytest.raises(ValueError):
        find_best_muhurta_windows(2451545,2451546,51.5,-.1,
            electional_policy=ElectionalPolicy(**policy))


@pytest.mark.parametrize("error,expected", [
    (OutOfRangeError("outside", [2451545]), search.MuhurtaCoverageError),
    (MissingKernelError("missing"), search.MuhurtaResourceError),
])
def test_reader_failure_does_not_return_partial_selection(monkeypatch, error, expected):
    def fail(*args):
        raise error
    monkeypatch.setattr(search, "_bind_ephemeris_time", fail)
    with pytest.raises(expected):
        search.find_muhurta_windows(2451545, 2451545.1, reader=object())


def test_live_anchor_never_uses_polynomial_fallback(monkeypatch):
    def fail(*args):
        raise FileNotFoundError("anchor absent")
    monkeypatch.setattr(search, "star_at", fail)
    with pytest.raises(search.MuhurtaResourceError):
        search.muhurta_score_for_chart(_chart(), ayanamsa_system="True Chitrapaksha")
