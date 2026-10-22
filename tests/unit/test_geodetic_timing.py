"""Controlled analytic movers verify root, branch, window and failure semantics.

These are numerical invariant tests, not ephemeris accuracy certification.
JD tolerance is 2e-6 days; angular residual acceptance is 1e-6 degrees.
"""

from types import SimpleNamespace

import math
import pytest

from moira.geodetic import geodetic_chart
from moira.geodetic_timing import GeodeticFixedReference, GeodeticTimingPolicy, find_geodetic_transits
from moira.transits_aspects import _require_natal_aspect_mover

JD = 2451545.


def synthetic(monkeypatch, function, *, intervals=None):
    clock = SimpleNamespace(identity="synthetic_clock")
    monkeypatch.setattr("moira.geodetic_timing._coverage_schedule",
                        lambda body, identity, reader, low, high, policy: (tuple((JD + a, JD + b) for a, b in intervals) if intervals else ((low, high),), (), clock))
    monkeypatch.setattr("moira._ephemeris_time._bind_ephemeris_time", lambda *a, **k: clock)
    monkeypatch.setattr("moira.planets.planet_at", lambda body, jd, **k: SimpleNamespace(longitude=function(jd - JD) % 360, distance=1e8))
    return GeodeticFixedReference(geodetic_chart(0, 35, 23.44), JD, angles=("MC",))


def run(reference, end=100, *, start=0, aspects=((0, 3),), policy=None, mover="comet:Halley"):
    return find_geodetic_transits(reference, mover, JD + start, JD + end, aspects=aspects,
                                 policy=policy or GeodeticTimingPolicy(step_days=1), reader=object())


def test_slow_orb_window_longer_than_two_days_and_reference_alias(monkeypatch):
    reference = synthetic(monkeypatch, lambda t: .1 * (t - 50))
    result = run(reference)
    assert result.complete
    assert result.body_id == "comet:1P/Halley"
    assert result.identity.naif_id == 1000001
    assert len(result.events) == len(result.windows) == 1
    assert result.events[0].jd_ut1 == pytest.approx(JD + 50, abs=2e-6)
    window = result.windows[0]
    assert window.entry_jd_ut1 == pytest.approx(JD + 20, abs=2e-6)
    assert window.exit_jd_ut1 == pytest.approx(JD + 80, abs=2e-6)
    assert window.pass_indices == (0,)
    assert result.timescale == "JD_UT1"


def test_repeated_retrograde_passes_share_one_connected_window(monkeypatch):
    reference = synthetic(monkeypatch, lambda t: 10 * math.sin((t - 15) * math.pi / 10))
    result = run(reference, end=30, aspects=((0, 15),))
    assert result.complete
    assert [e.jd_ut1 - JD for e in result.events] == pytest.approx([5, 15, 25], abs=2e-6)
    assert [e.motion for e in result.events] == ["retrograde", "direct", "retrograde"]
    assert len(result.windows) == 1
    assert result.windows[0].pass_indices == (0, 1, 2)
    assert result.windows[0].entry_status == result.windows[0].exit_status == "outside_study_span"
    assert result.windows[0].entry_jd_ut1 is None


def test_stationary_touch_requires_refined_velocity_zero(monkeypatch):
    reference = synthetic(monkeypatch, lambda t: .01 * (t - 10.3) ** 2)
    result = run(reference, end=20, aspects=((0, .1),))
    assert result.complete
    assert len(result.events) == 1
    assert result.events[0].jd_ut1 == pytest.approx(JD + 10.3, abs=2e-6)
    assert result.events[0].motion == "stationary"
    assert result.events[0].residual_deg <= 1e-6


def test_endpoint_wrap_and_directed_branch_deduplication(monkeypatch):
    reference = synthetic(monkeypatch, lambda t: 18 * t)
    result = run(reference, end=20, aspects=((0, 1), (90, 1), (180, 1)))
    assert result.complete
    assert [(e.aspect_angle_deg, e.directed_angle_deg) for e in result.events] == [(0, 0), (90, 90), (180, 180), (90, -90), (0, 0)]
    assert [e.jd_ut1 - JD for e in result.events] == pytest.approx([0, 5, 10, 15, 20], abs=2e-6)


def test_gaps_are_not_bridged_and_partial_policy_is_explicit(monkeypatch):
    reference = synthetic(monkeypatch, lambda t: .1 * (t - 10), intervals=((0, 8), (12, 20)))
    with pytest.raises(ValueError, match="not fully covered"):
        run(reference, end=20)
    result = run(reference, end=20, policy=GeodeticTimingPolicy(step_days=1, coverage_policy="allow_partial"))
    assert not result.complete and "partial_coverage" in result.reasons
    assert result.gaps_jd_ut1 == ((JD + 8, JD + 12),)
    assert not result.events
    assert len(result.windows) == 2
    assert result.windows[0].exit_status == result.windows[1].entry_status == "coverage_gap"


def test_budget_exhaustion_is_not_successful_empty_result(monkeypatch):
    reference = synthetic(monkeypatch, lambda t: t - 50)
    result = run(reference, policy=GeodeticTimingPolicy(step_days=1, max_evaluations=3))
    assert not result.complete
    assert "search_budget_exhausted" in result.reasons
    assert result.evaluations <= 3
    assert not result.scanned_intervals_jd_ut1
    extreme = run(reference, policy=GeodeticTimingPolicy(step_days=1e-310, velocity_step_days=1e-312, max_evaluations=3))
    assert not extreme.complete and "search_budget_exhausted" in extreme.reasons


def test_continuous_exact_degeneracy_is_not_fabricated_passes(monkeypatch):
    reference = synthetic(monkeypatch, lambda t: 0)
    result = run(reference, end=5)
    assert not result.complete
    assert "unresolved_near_continuous_contact" in result.reasons
    assert not result.events
    assert len(result.windows) == 1


def test_sidereal_view_freezes_reference_offset(monkeypatch):
    reference = synthetic(monkeypatch, lambda t: .1 * (t - 50))
    sidereal = GeodeticFixedReference(geodetic_chart(0, 35, 23.44, 24, "sidereal"), JD, angles=("MC",))
    assert sidereal.selected_targets == (("MC", 336),)
    assert sidereal.tropical_targets == reference.tropical_targets
    assert run(reference).events == run(sidereal).events


def test_fixed_reference_preserves_known_chart_epoch():
    from dataclasses import replace
    from moira.geodetic import GeodeticChartProvenance
    provenance = GeodeticChartProvenance(calculation_source="chart_context", chart_jd_ut=JD, chart_jd_tt=JD + .001,
                                         obliquity_timescale="TT", mean_obliquity_model="controlled_test", nutation_model="controlled_test")
    chart = replace(geodetic_chart(0, 35, 23.44), provenance=provenance)
    reference = GeodeticFixedReference(chart, JD)
    assert reference.reference_jd_tt == JD + .001
    with pytest.raises(ValueError, match="epoch"):
        GeodeticFixedReference(chart, JD + 1)


@pytest.mark.parametrize("mover", ["Halley", "Not a body", "1000001"])
def test_unresolved_or_ambiguous_mover_refused_before_scan(monkeypatch, mover):
    reference = synthetic(monkeypatch, lambda t: t)
    with pytest.raises(ValueError):
        run(reference, mover=mover)


def test_rest_bulk_admission_does_not_expand():
    for name in ("comet:1P/Halley", "comet:Halley", "asteroid:Ceres"):
        with pytest.raises(ValueError, match="unsupported natal-aspect mover"):
            _require_natal_aspect_mover(name)
    _require_natal_aspect_mover("Ceres")


def test_contiguous_descriptor_seam_merges_windows_and_deduplicates_touch(monkeypatch):
    reference = synthetic(monkeypatch, lambda t: .01 * (t - 10) ** 2, intervals=((0, 10), (10, 20)))
    result = run(reference, end=20, aspects=((0, .1),))
    assert result.complete
    assert len(result.events) == len(result.windows) == 1
    assert result.events[0].motion == "stationary"
    assert result.windows[0].entry_status == result.windows[0].exit_status == "found"


def test_slow_near_zero_sample_is_refined_without_duplicate_pass_or_window(monkeypatch):
    reference = synthetic(monkeypatch, lambda t: .00001 * (t - 10.03))
    result = run(reference, end=20, aspects=((0, .00001),))
    assert result.complete
    assert len(result.events) == len(result.windows) == 1
    assert result.events[0].jd_ut1 == pytest.approx(JD + 10.03, abs=2e-6)
    assert result.windows[0].entry_jd_ut1 == pytest.approx(JD + 9.03, abs=2e-6)
    assert result.windows[0].exit_jd_ut1 == pytest.approx(JD + 11.03, abs=2e-6)


def test_shallow_double_crossing_is_not_a_third_stationary_contact(monkeypatch):
    reference = synthetic(monkeypatch, lambda t: .01 * (t - 10.3) ** 2 - 1e-7)
    result = run(reference, end=20, aspects=((0, .1),))
    assert result.complete
    assert len(result.events) == 2
    assert [e.jd_ut1 - JD for e in result.events] == pytest.approx([10.3 - math.sqrt(1e-5), 10.3 + math.sqrt(1e-5)], abs=2e-6)


@pytest.mark.requires_ephemeris
def test_coverage_admission_uses_disjoint_descriptors_and_reduction_padding(tmp_path, planetary_reader, jd_j2000):
    """Controlled Type13 gaps test coverage routing, not orbit accuracy."""
    from moira.daf_writer import write_spk_type13
    from moira._spk_body_kernel import SmallBodyKernel
    from moira._ephemeris_time import _bind_ephemeris_time
    from moira.geodetic_inputs import _body_identity
    from moira.geodetic_timing import _coverage_schedule, _gaps
    from moira.spk_reader import KernelPool
    path = tmp_path / "controlled_coverage.bsp"
    bodies = []
    for start, end in ((-20, -10), (-10, -3), (3, 20)):
        bodies.append({"naif_id": 2000001, "center": 10, "frame": 1,
                       "name": "CONTROLLED CERES COVERAGE", "window_size": 3,
                       "epochs_jd": [jd_j2000 + start, jd_j2000 + (start + end) / 2, jd_j2000 + end],
                       "states": [[4e8] * 3, [1e8] * 3, [0.] * 3, [0.] * 3, [0.] * 3, [0.] * 3]})
    write_spk_type13(path, bodies=bodies, locifn="GEODETIC COVERAGE TEST ONLY")
    kernel = SmallBodyKernel(path)
    try:
        pool = KernelPool((planetary_reader, kernel))
        policy = GeodeticTimingPolicy(step_days=.5, coverage_policy="allow_partial")
        body_id, identity = _body_identity("asteroid:Ceres")
        covered, resources, _ = _coverage_schedule(body_id, identity, pool, jd_j2000 - 15, jd_j2000 + 15, policy)
        gaps = _gaps(jd_j2000 - 15, jd_j2000 + 15, covered)
        assert len(gaps) == 1
        assert gaps[0][1] - gaps[0][0] > 6 + 2 * policy.resource_padding_days - 1e-4
        assert len(covered) == 3  # includes the continuous -10-day descriptor seam
        assert {(r.center, r.target) for r in resources} >= {(0, 3), (3, 399), (0, 10), (0, 5), (0, 6), (10, 2000001)}
        for start, end in covered:
            a = _bind_ephemeris_time(start, pool).epoch_tdb - policy.resource_padding_days
            b = _bind_ephemeris_time(end, pool).epoch_tdb + policy.resource_padding_days
            assert any(x - 1e-8 <= a <= b <= y + 1e-8 for x, y in kernel.coverage_intervals_tdb(10, 2000001))
    finally:
        kernel.close()
