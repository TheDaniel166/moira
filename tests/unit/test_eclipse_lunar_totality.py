"""Conditional point-TT route obligations do not overclaim totality."""
from fractions import Fraction
import math
from types import SimpleNamespace

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_lunar_totality import (
    _check_guarded_norm,
    assess_conditional_lunar_interval_totality,
    assess_conditional_lunar_point_totality,
)
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_serving_astro import evaluate_lunar_frozen_snapshot
from moira.eclipse import _eclipse_body_pair
import moira.corrections as corrections
import moira._eclipse_lunar_cone_bounds as cone_bounds
import moira._eclipse_serving_astro as serving_astro
import moira.lunar_shadow_events as lunar_shadow_events
import moira.lunar_shadow_models as lunar_shadow_models
import moira.planets as planets
from moira.lunar_shadow_models import spherical_cone_shadow


def _point_vector(*values):
    return tuple(I.point(v) for v in values)


def test_norm_obligations_prove_regular_box_and_refuse_wide_or_extreme_boxes():
    normal = _check_guarded_norm(_point_vector(3.0, 4.0, 0.0))
    assert normal.status == "proved"
    assert normal.norm_km.contains(5)
    assert _check_guarded_norm((I(-10, 10),) * 3).status == "unresolved"
    assert _check_guarded_norm(_point_vector(1.7e308, 0.0, 0.0)).status == "unresolved"


def test_missing_route_is_unresolved_without_fabricated_checks(monkeypatch):
    def missing(*args, **kwargs):
        raise EnclosureUnavailable("no supported reader")
    monkeypatch.setattr("moira._eclipse_lunar_totality.bound_conditional_lunar_serving_vectors", missing)
    result = assess_conditional_lunar_point_totality(None, 2459891.9582497696)
    assert result.status == "unresolved" and "no supported reader" in result.reasons[0]
    assert result.vectors is None and result.clock_checks == result.norm_checks == ()
    assert not result.eclipse_absence_certified


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt,expect_clocks", [(2459891.9582497696, True), (1248813.457560655, False)])
def test_real_point_retains_exact_reception_and_emission_obligations(planetary_reader, tt, expect_clocks):
    result = assess_conditional_lunar_point_totality(planetary_reader, tt)
    assert result.status == "unresolved"
    assert not result.route_totality_established and not result.native_build_attested
    assert not result.live_kernel_attested and not result.eclipse_absence_certified
    assert len(result.clock_checks) == len(result.norm_checks) == 11
    assert all(check.status == "proved" for check in result.norm_checks)
    assert all(check.tt_anchor_jd == tt for check in result.clock_checks)
    assert result.clock_checks[0].tt_offset_days == I.point(0)
    assert tuple(check.tt_offset_days for check in result.clock_checks[1:]) == tuple(
        step.emission_tt_offset_days for step in result.vectors.iterations
    )
    assert all(check.status == "proved" for check in result.clock_checks) is expect_clocks


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 10**400])
def test_nonfinite_point_is_rejected(value):
    with pytest.raises(ValueError):
        assess_conditional_lunar_point_totality(None, value)


@pytest.mark.requires_ephemeris
def test_real_interval_preserves_separate_reception_and_emission_parts(planetary_reader):
    """All ten emission clocks use independent TT and delay enclosures."""
    tt = 2459891.9582497696
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    result = assess_conditional_lunar_interval_totality(planetary_reader, tt, offsets)
    assert result.status == "unresolved"
    assert not result.represented_point_tt_only
    assert result.tt_reception_offsets == offsets
    assert len(result.clock_checks) == len(result.norm_checks) == 11
    assert all(check.tt_anchor_jd == tt for check in result.clock_checks)
    assert all(check.tt_first_part_offsets == offsets for check in result.clock_checks)
    assert result.clock_checks[0].tt_offset_days == I.point(0)
    expected_delays = (result.vectors.initial_delay_days,
                       *(step.next_delay_days for step in result.vectors.iterations[:-1]))
    assert tuple(check.tt_offset_days for check in result.clock_checks[1:]) == tuple(
        -delay for delay in expected_delays
    )
    assert tuple(check.tt_combined_offset_days for check in result.clock_checks[1:]) == tuple(
        step.emission_tt_offset_days for step in result.vectors.iterations
    )
    assert all(check.status == "proved" for check in result.clock_checks)
    assert all(check.status == "proved" for check in result.norm_checks)
    assert not result.route_totality_established
    assert not result.native_build_attested and not result.live_kernel_attested
    assert not result.eclipse_absence_certified


def test_interval_requires_explicit_rational_domain():
    with pytest.raises(TypeError):
        assess_conditional_lunar_interval_totality(None, 2459891.0, (0, 1))


@pytest.mark.parametrize("budget", [-1, True, 1.5])
def test_exhaustive_clock_budget_must_be_a_nonnegative_integer(budget):
    with pytest.raises(ValueError):
        assess_conditional_lunar_interval_totality(
            None, 2459891.0, I.point(0), max_exhaustive_clock_states=budget,
        )


@pytest.mark.requires_ephemeris
def test_exhaustive_clock_budget_is_shared_and_identical_boxes_are_cached(planetary_reader, monkeypatch):
    """Every state count is charged once, including when a box is unresolved."""
    import moira._eclipse_lunar_totality as totality

    calls = []
    def limited(_anchor, second, *, first_part_offsets, max_states):
        assert first_part_offsets == I.point(0)
        used = min(2, max_states)
        calls.append((second, max_states, used))
        return SimpleNamespace(status="unresolved", exhaustive_states_checked=used)

    monkeypatch.setattr(totality, "prove_split_time_convergence_exhaustively", limited)
    result = assess_conditional_lunar_interval_totality(
        planetary_reader, 1248813.457560655, I.point(0), max_exhaustive_clock_states=6,
    )
    assert result.status == "unresolved" and not result.eclipse_absence_certified
    assert len(result.clock_checks) == 11
    assert len({second for second, _, _ in calls}) == len(calls)
    assert result.exhaustive_clock_cache_hits == 11 - len(calls)
    assert result.exhaustive_clock_states_checked == sum(used for _, _, used in calls)
    assert result.exhaustive_clock_states_checked <= result.max_exhaustive_clock_states == 6
    remaining = 6
    for _, budget, used in calls:
        assert budget == remaining
        remaining -= used


@pytest.mark.requires_ephemeris
def test_exhausted_shared_budget_still_rejects_changed_clock_source(planetary_reader, monkeypatch):
    """An exhausted positive budget must not bypass the opt-in source guard."""
    from moira import julian
    import moira._eclipse_lunar_totality as totality

    original = julian._require_finite

    def exhaust_then_change_source(_anchor, _second, *, first_part_offsets, max_states):
        assert first_part_offsets == I.point(0)
        monkeypatch.setattr(julian, "_require_finite", lambda *args, **kwargs: original(*args, **kwargs))
        return SimpleNamespace(status="unresolved", exhaustive_states_checked=max_states)

    monkeypatch.setattr(totality, "prove_split_time_convergence_exhaustively", exhaust_then_change_source)
    result = assess_conditional_lunar_interval_totality(
        planetary_reader, 1248813.457560655, I.point(0), max_exhaustive_clock_states=2,
    )
    assert result.status == "unresolved"
    assert "source or math function changed" in result.reasons[0]
    assert result.exhaustive_clock_states_checked == 2
    assert result.exhaustive_clock_cache_hits == 0
    assert not result.eclipse_absence_certified


@pytest.mark.requires_ephemeris
def test_real_interval_obligations_cover_production_split_calls_and_norms(planetary_reader, monkeypatch):
    """Observe the actual split-clock and norm calls at represented TT samples."""
    tt = 2459891.9582497696
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    result = assess_conditional_lunar_interval_totality(planetary_reader, tt, offsets)
    assert all(check.status == "proved" for check in (*result.clock_checks, *result.norm_checks))

    clock_inputs = []
    norm_inputs = []
    real_split = planets._tt_to_tdb_split
    real_norm = corrections.vec_norm

    def capture_split(first, second):
        clock_inputs.append((first, second))
        return real_split(first, second)

    def capture_norm(vector):
        value = real_norm(vector)
        norm_inputs.append((vector, value))
        return value

    monkeypatch.setattr(planets, "_tt_to_tdb_split", capture_split)
    monkeypatch.setattr(corrections, "vec_norm", capture_norm)
    lo = math.nextafter(tt - 5 / 86400, math.inf)
    hi = math.nextafter(tt + 5 / 86400, -math.inf)
    samples = (lo, math.nextafter(lo, math.inf), tt, math.nextafter(hi, -math.inf), hi)
    for sample in samples:
        clock_inputs.clear()
        norm_inputs.clear()
        assert offsets.contains(Fraction.from_float(sample) - Fraction.from_float(tt))
        _eclipse_body_pair(sample, planetary_reader, sun_retarded=True, moon_retarded=False)
        # Reception calls supply Earth, the geometric Sun, and the Moon.
        assert len(clock_inputs) >= 4
        assert clock_inputs[0] == clock_inputs[1] == clock_inputs[-1] == (sample, 0.0)
        emission_calls = clock_inputs[2:-1]
        assert len(norm_inputs) == 1 + len(emission_calls)
        for (first, second), check in zip(emission_calls, result.clock_checks[1:]):
            assert check.tt_first_part_offsets.contains(Fraction.from_float(first) - Fraction.from_float(tt))
            assert check.tt_offset_days.contains(Fraction.from_float(second))
        for (vector, norm), check in zip(norm_inputs, result.norm_checks):
            assert check.norm_km.contains(norm)
            assert check.max_component_km.contains(max(abs(value) for value in vector))
    assert result.status == "unresolved" and not result.eclipse_absence_certified


@pytest.mark.requires_ephemeris
def test_fresh_snapshot_composes_same_bounded_route_clocks_norms_and_cone(planetary_reader):
    """Snapshot numeric totality is conditional and does not prove an event."""
    tt = 2459891.9582497696
    offsets = I(Fraction(-5, 86400), Fraction(5, 86400))
    result = assess_conditional_lunar_interval_totality(
        planetary_reader, tt, offsets, include_frozen_snapshot=True,
    )
    assert result.frozen_snapshot_status == "conditionally_proved"
    assert result.frozen_snapshot_scope.bounds is result.vectors
    assert result.frozen_snapshot_cone.geometry_total_for_vector_box_under_premises
    assert all(check.status == "proved" for check in (*result.clock_checks, *result.norm_checks))
    assert result.status == "unresolved"
    assert not result.route_totality_established and not result.live_kernel_attested
    assert not result.native_build_attested and not result.eclipse_absence_certified
    assert not result.frozen_snapshot_scope.source_and_kernel_attested
    assert not result.frozen_snapshot_scope.totality_certified
    for seconds in (-4, 0, 4):
        sample_tt = tt + seconds / 86400
        assert offsets.contains(Fraction.from_float(sample_tt) - Fraction.from_float(tt))
        sample = evaluate_lunar_frozen_snapshot(result.frozen_snapshot_scope, sample_tt)
        geometry = spherical_cone_shadow(sample.sun_retarded_km, sample.moon_geometric_km)
        assert result.frozen_snapshot_cone.penumbral_margin_km.contains(geometry.penumbral_margin)
        assert result.frozen_snapshot_cone.umbral_margin_km.contains(geometry.umbral_margin)
        assert result.frozen_snapshot_cone.total_margin_km.contains(geometry.total_margin)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("changed", [
    "serving_speed", "corrections_speed", "cone_earth", "cone_sun", "cone_moon", "model_default", "model_alias",
])
def test_fresh_snapshot_rejects_mismatched_route_or_model_constants(planetary_reader, monkeypatch, changed):
    tt = 2459891.9582497696
    if changed == "serving_speed":
        monkeypatch.setattr(serving_astro, "C_KM_PER_DAY", serving_astro.C_KM_PER_DAY + 1)
    elif changed == "corrections_speed":
        monkeypatch.setattr(corrections, "C_KM_PER_DAY", corrections.C_KM_PER_DAY + 1)
    elif changed.startswith("cone_"):
        name = {"cone_earth": "EARTH_RADIUS_KM", "cone_sun": "SUN_RADIUS_KM", "cone_moon": "MOON_RADIUS_KM"}[changed]
        monkeypatch.setattr(cone_bounds, name, getattr(cone_bounds, name) + 1)
    elif changed == "model_default":
        defaults = dict(lunar_shadow_models.spherical_cone_shadow.__kwdefaults__)
        defaults["earth_radius_km"] += 1
        monkeypatch.setattr(lunar_shadow_models.spherical_cone_shadow, "__kwdefaults__", defaults)
    else:
        monkeypatch.setattr(lunar_shadow_events, "spherical_cone_shadow", lambda *args, **kwargs: None)
    result = assess_conditional_lunar_interval_totality(
        planetary_reader, tt, I.point(0), include_frozen_snapshot=True,
    )
    assert result.frozen_snapshot_status == "unresolved"
    assert result.frozen_snapshot_scope is None and result.frozen_snapshot_cone is None
    assert any("differs" in reason or "differ" in reason for reason in result.reasons)
    assert not result.eclipse_absence_certified


@pytest.mark.requires_ephemeris
def test_fresh_snapshot_retains_unknown_clock_and_unsupported_cone(planetary_reader):
    historical = assess_conditional_lunar_interval_totality(
        planetary_reader, 1248813.457560655, I.point(0), include_frozen_snapshot=True,
    )
    assert historical.frozen_snapshot_status == "unresolved"
    assert any("clock totality" in reason for reason in historical.reasons)
    assert historical.frozen_snapshot_scope is None
    # A new moon is on the sunward side: the finite-cone shadow model is not
    # defined there, so no snapshot proof can be returned.
    sunward = assess_conditional_lunar_interval_totality(
        planetary_reader, 2459907.46, I.point(0), include_frozen_snapshot=True,
    )
    assert sunward.frozen_snapshot_status == "unresolved"
    assert any("cone" in reason for reason in sunward.reasons)
    assert not sunward.eclipse_absence_certified
