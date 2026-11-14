"""Kernel-free unit tests for the out-of-bounds solver's doctrine.

These tests own the parts of ``moira.out_of_bounds`` that do not need an
ephemeris: input and policy validation, the clearance lemma, the
close-approach refinement trigger, conditioning classification, the scan's
bracketing behaviour against analytic bound functions, culmination solving
including the boundary-extremum case, and excursion assembly with clipped
window edges.

The analytic fields used here are synthetic declination/obliquity pairs
injected through a stub in place of the real apparent-place pipeline. They
establish that the solver's doctrine is correct on fields whose roots and
extrema are known in closed form. They are not astronomical evidence; the
ephemeris-backed proof lives in
``tests/integration/test_out_of_bounds_de441.py``.
"""

from __future__ import annotations

import math

import pytest

from moira.out_of_bounds import (
    UNAVAILABLE_REASONS,
    OutOfBoundsBudgetError,
    OutOfBoundsPolicy,
    OutOfBoundsUnavailableError,
    _assemble_excursions,
    _bisect_bound_root,
    _BoundField,
    _build_crossing,
    _classify_conditioning,
    _derive_coarse_step,
    _interval_is_clear,
    _measure_rates,
    _needs_close_approach_refinement,
    _scan_for_brackets,
    _solve_culmination,
    find_out_of_bounds,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Analytic stand-in for the apparent-place pipeline
# ---------------------------------------------------------------------------

class _AnalyticField(_BoundField):
    """A _BoundField whose declination and obliquity are closed-form.

    Substituting the field rather than the sampler keeps every tested code
    path — scan, clearance, bisection, culmination, assembly — exactly the
    production path, while making the expected roots and extrema exact.
    """

    def __init__(self, declination_fn, obliquity_fn=None, distance_fn=None):
        super().__init__(
            body="synthetic",
            reader=None,
            differentiation_step_days=1.0 / 480.0,
        )
        self._declination_fn = declination_fn
        self._obliquity_fn = obliquity_fn or (lambda jd: 23.4)
        self._distance_fn = distance_fn or (lambda jd: math.inf)

    def sample(self, jd):
        cached = self._cache.get(jd)
        if cached is not None:
            return cached
        # Share the production budget accounting, so a budget test exercises
        # the real guard rather than a stub that quietly ignores it.
        self._charge_evaluation()
        declination = self._declination_fn(jd)
        obliquity = self._obliquity_fn(jd)
        result = (
            declination,
            obliquity,
            abs(declination) - obliquity,
            self._distance_fn(jd),
        )
        self._cache[jd] = result
        self.evaluations += 1
        return result


def _sine_declination(amplitude: float, period: float, phase: float = 0.0):
    """Declination that sweeps sinusoidally, like a body on an inclined path."""

    return lambda jd: amplitude * math.sin(2.0 * math.pi * (jd - phase) / period)


# ---------------------------------------------------------------------------
# Policy validation
# ---------------------------------------------------------------------------

def test_default_policy_is_self_consistent():
    policy = OutOfBoundsPolicy()
    assert policy.min_step_days <= policy.max_step_days
    assert policy.rate_safety_factor >= 1.0
    assert policy.rate_probe_count >= 3
    assert policy.culmination_probe_count >= 3
    assert policy.solver_tolerance_days > 0.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"angular_resolution_deg": 0.0},
        {"angular_resolution_deg": -1.0},
        {"rate_safety_factor": 0.5},
        {"min_step_days": 10.0, "max_step_days": 1.0},
        {"rate_probe_count": 2},
        {"culmination_probe_count": 2},
        {"max_subdivision_depth": -1},
        {"solver_tolerance_days": 0.0},
        {"differentiation_step_days": -1.0},
        {"close_approach_distance_au": 0.0},
        {"distance_change_trigger": 0.0},
        {"angular_resolution_deg": float("nan")},
        {"angular_resolution_deg": float("inf")},
        {"max_declination_evaluations": 0},
        {"max_declination_evaluations": -5},
        {"max_declination_evaluations": 1.5},
        {"max_declination_evaluations": True},
    ],
)
def test_invalid_policy_fields_are_rejected(overrides):
    with pytest.raises(ValueError):
        OutOfBoundsPolicy(**overrides)


def test_policy_rejects_boolean_in_place_of_number():
    with pytest.raises(ValueError):
        OutOfBoundsPolicy(angular_resolution_deg=True)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("body", ["", "   ", None, 7])
def test_empty_or_non_string_body_is_rejected(body):
    with pytest.raises(ValueError):
        find_out_of_bounds(body, 2451545.0, 2451555.0)


@pytest.mark.parametrize(
    ("jd_start", "jd_end"),
    [
        (2451555.0, 2451545.0),
        (2451545.0, 2451545.0),
        (float("nan"), 2451555.0),
        (2451545.0, float("inf")),
    ],
)
def test_invalid_range_is_rejected(jd_start, jd_end):
    with pytest.raises(ValueError):
        find_out_of_bounds("Moon", jd_start, jd_end)


def test_wrong_policy_type_is_rejected():
    with pytest.raises(ValueError):
        find_out_of_bounds("Moon", 2451545.0, 2451555.0, policy=object())


def test_unavailable_error_carries_body_and_reason():
    error = OutOfBoundsUnavailableError(
        "Apophis", "ephemeris_coverage", "JD(UT1) 2461358.5"
    )
    assert error.body == "Apophis"
    assert error.reason == "ephemeris_coverage"
    assert error.detail == "JD(UT1) 2461358.5"
    assert "Apophis" in str(error)
    assert "ephemeris does not cover" in str(error)
    assert "2461358.5" in str(error)
    assert isinstance(error, ValueError)


def test_unavailable_error_reasons_are_a_closed_set():
    """The reason is a machine code a transport layer can branch on.

    It must not become free prose, or the REST layer would be reduced to
    pattern-matching messages to tell a bad request from an absent resource.
    """
    assert UNAVAILABLE_REASONS == frozenset(
        {"ephemeris_coverage", "body_unresolved"}
    )
    for reason in UNAVAILABLE_REASONS:
        assert OutOfBoundsUnavailableError("Eros", reason).reason == reason
    with pytest.raises(ValueError, match="reason must be one of"):
        OutOfBoundsUnavailableError("Eros", "no coverage")


def test_no_evaluation_budget_by_default():
    """A library caller may legitimately scan centuries."""
    assert OutOfBoundsPolicy().max_declination_evaluations is None


def test_an_explicit_budget_is_accepted():
    assert OutOfBoundsPolicy(
        max_declination_evaluations=1
    ).max_declination_evaluations == 1


def test_budget_error_carries_its_counts_and_stage():
    error = OutOfBoundsBudgetError("Moon", 2000, 2000, "scan")
    assert error.body == "Moon"
    assert error.budget == 2000
    assert error.evaluations == 2000
    assert error.stage == "scan"
    assert "2000" in str(error)
    assert "max_declination_evaluations" in str(error)
    assert isinstance(error, ValueError)


def test_budget_stops_the_scan_rather_than_truncating_it():
    """A truncated search must raise, not return a short list.

    "No further excursions" and "I stopped looking" are different statements,
    so a partial result is never returned.
    """
    field_ = _AnalyticField(_sine_declination(25.0, 27.3))
    field_.max_evaluations = 40
    field_.stage = "scan"
    policy = OutOfBoundsPolicy(max_declination_evaluations=40)
    with pytest.raises(OutOfBoundsBudgetError) as raised:
        _scan_for_brackets(field_, 2451545.0, 2451545.0 + 400.0, 0.5, policy)
    assert raised.value.budget == 40
    assert raised.value.stage == "scan"


def test_a_cached_instant_does_not_consume_budget():
    """Budget counts real evaluations, so re-reading an instant is free."""
    field_ = _AnalyticField(_sine_declination(25.0, 27.3))
    field_.max_evaluations = 2
    field_.bound(2451545.0)
    field_.bound(2451546.0)
    for _ in range(50):
        assert field_.bound(2451545.0) == field_.bound(2451545.0)
    assert field_.evaluations == 2
    with pytest.raises(OutOfBoundsBudgetError):
        field_.bound(2451547.0)


def test_unavailable_error_detail_is_optional():
    error = OutOfBoundsUnavailableError("Nibiru", "body_unresolved")
    assert error.detail == ""
    assert "Nibiru" in str(error)
    assert "could not be resolved" in str(error)


# ---------------------------------------------------------------------------
# The clearance lemma
# ---------------------------------------------------------------------------

def test_interval_with_both_ends_below_the_margin_is_clear():
    # |dB/dt| <= 10 deg/day over 1 day means B cannot rise more than 5 deg
    # from whichever end is nearer in time, so -6 at both ends is clear.
    assert _interval_is_clear(-6.0, -6.0, rate_bound=10.0, width=1.0)


def test_interval_with_both_ends_above_the_margin_is_clear():
    """The symmetric branch: deep inside an excursion nothing can happen.

    Without it the interior of every excursion subdivides to the recursion
    floor, which costs time and reports phantom unresolved intervals.
    """
    assert _interval_is_clear(6.0, 6.0, rate_bound=10.0, width=1.0)


def test_interval_with_an_end_inside_the_margin_is_not_clear():
    assert not _interval_is_clear(-4.0, -6.0, rate_bound=10.0, width=1.0)
    assert not _interval_is_clear(-6.0, -4.0, rate_bound=10.0, width=1.0)
    assert not _interval_is_clear(4.0, 6.0, rate_bound=10.0, width=1.0)


def test_interval_straddling_zero_is_not_clear():
    assert not _interval_is_clear(-6.0, 6.0, rate_bound=10.0, width=1.0)


def test_clearance_margin_scales_with_width():
    assert _interval_is_clear(-3.0, -3.0, rate_bound=10.0, width=0.5)
    assert not _interval_is_clear(-3.0, -3.0, rate_bound=10.0, width=1.0)


def test_clearance_lemma_holds_against_a_brute_force_sine_field():
    """A cleared interval must contain no root of the bound function.

    A sine declination sweeping past a fixed obliquity gives a bound function
    whose roots are known in closed form. For every interval the lemma clears,
    a dense subgrid is checked for any sample whose sign differs from the
    endpoints'. Such a sample would be a root the scan had been told to skip,
    which is a missed entry or a missed return.

    The property is stated on roots rather than on ``B > 0`` because the lemma
    is symmetric: an interval deep inside an excursion is correctly cleared
    while ``B > 0`` throughout it.
    """
    field_ = _AnalyticField(_sine_declination(25.0, 27.3))
    policy = OutOfBoundsPolicy(rate_safety_factor=3.0)
    width = 0.5
    false_clearances = 0
    cleared_negative = 0
    cleared_positive = 0
    jd = 2451545.0
    while jd < 2451545.0 + 60.0:
        bound_lo = field_.bound(jd)
        bound_hi = field_.bound(jd + width)
        secant = abs(bound_hi - bound_lo) / width
        rate_bound = max(secant * policy.rate_safety_factor, 1e-9)
        if _interval_is_clear(bound_lo, bound_hi, rate_bound, width):
            expected_sign = math.copysign(1.0, bound_lo)
            if expected_sign > 0.0:
                cleared_positive += 1
            else:
                cleared_negative += 1
            steps = 50
            for index in range(steps + 1):
                value = field_.bound(jd + width * index / steps)
                if value != 0.0 and math.copysign(1.0, value) != expected_sign:
                    false_clearances += 1
                    break
        jd += width
    # Both branches of the lemma must actually be exercised by this field.
    assert cleared_negative > 0
    assert cleared_positive > 0
    assert false_clearances == 0


# ---------------------------------------------------------------------------
# Close-approach refinement trigger
# ---------------------------------------------------------------------------

def test_near_distance_forces_refinement():
    policy = OutOfBoundsPolicy()
    assert _needs_close_approach_refinement(0.05, 0.06, policy)


def test_large_fractional_distance_change_forces_refinement():
    policy = OutOfBoundsPolicy(distance_change_trigger=0.10)
    assert _needs_close_approach_refinement(1.0, 2.0, policy)


def test_steady_far_distance_does_not_force_refinement():
    policy = OutOfBoundsPolicy()
    assert not _needs_close_approach_refinement(30.0, 30.1, policy)


def test_absent_distance_does_not_force_refinement():
    policy = OutOfBoundsPolicy()
    assert not _needs_close_approach_refinement(math.inf, math.inf, policy)


# ---------------------------------------------------------------------------
# Step derivation is measured, never a name lookup
# ---------------------------------------------------------------------------

def test_step_derivation_is_insensitive_to_the_body_name():
    """Two fields with identical motion must get an identical step.

    This is the guard against ``transits._auto_step``-style name lookup: the
    step comes from the measured bound-function rate and from nothing else.
    """
    policy = OutOfBoundsPolicy()
    jd_start, jd_end = 2451545.0, 2451545.0 + 60.0
    steps = []
    for name in ("Moon", "Zoozve", "comet:2P/Encke", "utterly-unknown-rock"):
        field_ = _AnalyticField(_sine_declination(25.0, 27.3))
        field_.body = name
        max_rate, median_rate = _measure_rates(field_, jd_start, jd_end, policy)
        steps.append(
            _derive_coarse_step(max_rate, median_rate, jd_start, jd_end, policy)
        )
    assert len(set(steps)) == 1


def test_faster_motion_yields_a_smaller_step():
    policy = OutOfBoundsPolicy()
    jd_start, jd_end = 2451545.0, 2451545.0 + 60.0
    derived = []
    for period in (27.3, 273.0):
        field_ = _AnalyticField(_sine_declination(25.0, period))
        max_rate, median_rate = _measure_rates(field_, jd_start, jd_end, policy)
        derived.append(
            _derive_coarse_step(max_rate, median_rate, jd_start, jd_end, policy)
        )
    assert derived[0] < derived[1]


def test_step_respects_declared_bounds():
    policy = OutOfBoundsPolicy(min_step_days=0.25, max_step_days=2.0)
    assert _derive_coarse_step(1e6, 1e6, 0.0, 100.0, policy) == 0.25
    assert _derive_coarse_step(0.0, 0.0, 0.0, 100.0, policy) == 2.0


def test_step_never_exceeds_the_requested_span():
    policy = OutOfBoundsPolicy(max_step_days=5.0)
    assert _derive_coarse_step(0.0, 0.0, 0.0, 0.5, policy) == 0.5


# ---------------------------------------------------------------------------
# Scan and root refinement
# ---------------------------------------------------------------------------

def test_scan_brackets_every_root_of_a_known_sine_field():
    """A 25 deg sine against a 23.4 deg bound has two roots per half period."""
    field_ = _AnalyticField(_sine_declination(25.0, 27.3))
    policy = OutOfBoundsPolicy()
    jd_start, jd_end = 2451545.0, 2451545.0 + 27.3
    outcome = _scan_for_brackets(field_, jd_start, jd_end, 0.5, policy)
    # One northern and one southern excursion per synodic period, two roots
    # each, and the phase at jd_start puts both fully inside the window.
    assert len(outcome.brackets) == 4
    assert outcome.unresolved_intervals == 0
    for bracket_lo, bracket_hi in outcome.brackets:
        assert field_.bound(bracket_lo) * field_.bound(bracket_hi) < 0.0


def test_scan_finds_a_shallow_excursion_a_coarse_grid_would_step_over():
    """A 0.01 deg excursion is captured although the coarse step is 2 days.

    The refinement guard, not the base cadence, is what finds it. This is the
    synthetic analogue of the measured 4.3-hour lunar excursion of
    2020-03-05 exercised in the ephemeris-backed tests.
    """
    amplitude = 23.41
    period = 27.3
    field_ = _AnalyticField(_sine_declination(amplitude, period))
    policy = OutOfBoundsPolicy(max_step_days=2.0)
    jd_start, jd_end = 2451545.0, 2451545.0 + period / 2.0
    outcome = _scan_for_brackets(field_, jd_start, jd_end, 2.0, policy)
    assert len(outcome.brackets) == 2
    assert outcome.refined_intervals > 0


def test_bisection_returns_a_root_inside_its_final_bracket():
    field_ = _AnalyticField(_sine_declination(25.0, 27.3))
    outcome = _scan_for_brackets(
        field_, 2451545.0, 2451545.0 + 14.0, 0.5, OutOfBoundsPolicy()
    )
    bracket_lo, bracket_hi = outcome.brackets[0]
    jd_root, final_lo, final_hi = _bisect_bound_root(
        field_, bracket_lo, bracket_hi, 1e-9
    )
    assert final_lo <= jd_root <= final_hi
    assert final_hi - final_lo <= 1e-9
    assert abs(field_.bound(jd_root)) < 1e-7


def test_bisection_matches_the_analytic_root():
    """asin(23.4/25) gives the exact crossing time for this sine field."""
    amplitude, period = 25.0, 27.3
    obliquity = 23.4
    epoch = 2451545.0
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: obliquity,
    )
    expected = epoch + period * math.asin(obliquity / amplitude) / (2.0 * math.pi)
    jd_root, _, _ = _bisect_bound_root(field_, epoch, epoch + period / 4.0, 1e-10)
    assert jd_root == pytest.approx(expected, abs=1e-8)


# ---------------------------------------------------------------------------
# Conditioning
# ---------------------------------------------------------------------------

def test_conditioning_classes_follow_the_declared_time_cost():
    # 2 deg/day is lunar-grade: an arcsecond costs about 12 seconds.
    assert _classify_conditioning(2.0) == "well_posed"
    # 0.1 deg/day costs about 4 minutes per arcsecond.
    assert _classify_conditioning(0.1) == "sensitive"
    # 0.004 deg/day is Pluto-grade: an arcsecond costs about 100 minutes.
    assert _classify_conditioning(0.004) == "ill_conditioned"
    assert _classify_conditioning(0.0) == "degenerate"


def test_conditioning_is_sign_independent():
    assert _classify_conditioning(0.5) == _classify_conditioning(-0.5)


def test_crossing_carries_rate_tolerance_and_sensitivity():
    """Every crossing must be judgeable without a second call."""
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    jd_root, low, high = _bisect_bound_root(
        field_, epoch, epoch + period / 4.0, 1e-9
    )
    crossing = _build_crossing(field_, "entry", jd_root, low, high)
    expected_rate = (
        amplitude
        * (2.0 * math.pi / period)
        * math.cos(2.0 * math.pi * (jd_root - epoch) / period)
    )
    assert crossing.declination_rate_deg_per_day == pytest.approx(
        expected_rate, rel=1e-5
    )
    assert crossing.obliquity_rate_deg_per_day == pytest.approx(0.0, abs=1e-12)
    assert crossing.bound_rate_deg_per_day == pytest.approx(expected_rate, rel=1e-5)
    assert crossing.achieved_tolerance_days <= 1e-9
    assert crossing.bracket_start_jd_ut <= crossing.jd_ut <= crossing.bracket_end_jd_ut
    # The sensitivity is the reciprocal of the rate in arcsec/day, exactly.
    assert crossing.time_sensitivity_days_per_arcsec == pytest.approx(
        1.0 / (abs(expected_rate) * 3600.0), rel=1e-5
    )
    assert crossing.time_sensitivity_seconds_per_arcsec == pytest.approx(
        crossing.time_sensitivity_days_per_arcsec * 86400.0
    )


def test_bound_rate_subtracts_a_moving_obliquity_in_the_north():
    """North of the equator a rising obliquity slows the bound crossing."""
    field_ = _AnalyticField(
        lambda jd: 23.4 + 0.5 * (jd - 2451545.0),
        obliquity_fn=lambda jd: 23.4 + 0.1 * (jd - 2451545.0),
    )
    crossing = _build_crossing(field_, "entry", 2451545.0, 2451545.0, 2451545.0)
    assert crossing.declination_rate_deg_per_day == pytest.approx(0.5, rel=1e-6)
    assert crossing.obliquity_rate_deg_per_day == pytest.approx(0.1, rel=1e-6)
    assert crossing.bound_rate_deg_per_day == pytest.approx(0.4, rel=1e-6)


def test_bound_rate_uses_the_southern_hemisphere_sign():
    """South of the equator a falling declination drives |delta| upward."""
    field_ = _AnalyticField(
        lambda jd: -(23.4 + 0.5 * (jd - 2451545.0)),
        obliquity_fn=lambda jd: 23.4 + 0.1 * (jd - 2451545.0),
    )
    crossing = _build_crossing(field_, "entry", 2451545.0, 2451545.0, 2451545.0)
    assert crossing.declination_rate_deg_per_day == pytest.approx(-0.5, rel=1e-6)
    # sign(delta) * ddelta/dt - deps/dt = (-1)(-0.5) - 0.1
    assert crossing.bound_rate_deg_per_day == pytest.approx(0.4, rel=1e-6)


# ---------------------------------------------------------------------------
# Culmination — the trap a ternary search falls into
# ---------------------------------------------------------------------------

def test_interior_culmination_matches_the_analytic_extremum():
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    entry = epoch + period * math.asin(23.4 / amplitude) / (2.0 * math.pi)
    departure = epoch + period / 2.0 - (entry - epoch)
    culmination = _solve_culmination(
        field_, entry, departure, 1.0, False, False, OutOfBoundsPolicy()
    )
    assert culmination.jd_ut == pytest.approx(epoch + period / 4.0, abs=1e-6)
    assert culmination.declination == pytest.approx(amplitude, abs=1e-8)
    assert culmination.at_boundary is False
    assert culmination.interior_critical_points == 1


def test_culmination_on_a_clipped_window_sits_on_the_boundary():
    """The case a ternary search gets wrong.

    The window is cut after the declination has already turned, so |delta| is
    monotonically falling across it and the maximum is the left edge. A
    hump-assuming search walks inward and returns a smaller peak than the
    window's own first sample. The solver must report the edge.
    """
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    peak = epoch + period / 4.0
    culmination = _solve_culmination(
        field_, peak + 0.2, peak + 1.5, 1.0, True, False, OutOfBoundsPolicy()
    )
    assert culmination.at_boundary is True
    assert culmination.boundary_edge == "range_start"
    assert culmination.interior_critical_points == 0
    assert culmination.jd_ut == pytest.approx(peak + 0.2, abs=1e-6)
    # The reported peak must be the true maximum over the clipped window,
    # which is its left edge, and must beat every interior sample.
    reported = abs(culmination.declination)
    for index in range(1, 40):
        jd = peak + 0.2 + (1.3 * index / 40.0)
        assert abs(field_.sample(jd)[0]) <= reported + 1e-9


def test_culmination_never_reports_below_the_window_maximum():
    """Property: the solved peak dominates a dense sweep of the window.

    This is the exact failure observed with a ternary search, which returned
    a peak below the grid maximum. It is asserted across many clipping
    offsets so a hump assumption cannot survive anywhere.
    """
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    peak = epoch + period / 4.0
    for offset in (-2.0, -1.0, -0.3, 0.0, 0.3, 1.0, 2.0):
        low = peak + offset
        high = low + 2.0
        culmination = _solve_culmination(
            field_, low, high, 1.0, True, True, OutOfBoundsPolicy()
        )
        reported = abs(culmination.declination)
        sweep = max(
            abs(field_.sample(low + (high - low) * index / 200.0)[0])
            for index in range(201)
        )
        assert reported >= sweep - 1e-9


def test_double_peaked_excursion_reports_its_global_maximum():
    """Two interior critical points, and the taller one must win."""

    def declination(jd):
        offset = jd - 2451545.0
        return 24.0 + 0.5 * math.sin(2.0 * math.pi * offset / 4.0) + 0.1 * offset

    field_ = _AnalyticField(declination, obliquity_fn=lambda jd: 23.4)
    culmination = _solve_culmination(
        field_, 2451545.0, 2451545.0 + 8.0, 1.0, True, True, OutOfBoundsPolicy()
    )
    assert culmination.interior_critical_points >= 2
    sweep = max(
        abs(field_.sample(2451545.0 + 8.0 * index / 400.0)[0])
        for index in range(401)
    )
    assert abs(culmination.declination) >= sweep - 1e-9


def test_southern_culmination_uses_the_hemisphere_sign():
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    trough = epoch + 3.0 * period / 4.0
    culmination = _solve_culmination(
        field_, trough - 2.0, trough + 2.0, -1.0, True, True, OutOfBoundsPolicy()
    )
    assert culmination.jd_ut == pytest.approx(trough, abs=1e-5)
    assert culmination.declination == pytest.approx(-amplitude, abs=1e-6)


# ---------------------------------------------------------------------------
# Excursion assembly and window-edge semantics
# ---------------------------------------------------------------------------

def _crossings(field_, brackets, policy):
    built = []
    for bracket_lo, bracket_hi in brackets:
        jd_root, low, high = _bisect_bound_root(
            field_, bracket_lo, bracket_hi, policy.solver_tolerance_days
        )
        kind = "departure" if field_.bound(bracket_lo) > 0.0 else "entry"
        built.append(_build_crossing(field_, kind, jd_root, low, high))
    built.sort(key=lambda crossing: crossing.jd_ut)
    return built


def test_fully_contained_excursion_has_both_edges_and_no_lower_bound():
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    policy = OutOfBoundsPolicy()
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    jd_start, jd_end = epoch, epoch + period / 2.0
    outcome = _scan_for_brackets(field_, jd_start, jd_end, 0.5, policy)
    roots = _crossings(field_, outcome.brackets, policy)
    excursions = _assemble_excursions(
        field_, "synthetic", jd_start, jd_end, roots, False, policy
    )
    assert len(excursions) == 1
    excursion = excursions[0]
    assert excursion.entry is not None and excursion.departure is not None
    assert excursion.entry.kind == "entry"
    assert excursion.departure.kind == "departure"
    assert excursion.entry_clipped is False
    assert excursion.departure_clipped is False
    assert excursion.duration_is_lower_bound is False
    assert excursion.is_complete is True
    assert excursion.hemisphere == "north"
    assert excursion.duration_hours == pytest.approx(
        (excursion.departure.jd_ut - excursion.entry.jd_ut) * 24.0
    )


def test_already_out_at_range_start_reports_a_clipped_entry():
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    policy = OutOfBoundsPolicy()
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    # Start at the peak: the body is already out of bounds.
    jd_start = epoch + period / 4.0
    jd_end = jd_start + 4.0
    assert field_.bound(jd_start) > 0.0
    outcome = _scan_for_brackets(field_, jd_start, jd_end, 0.5, policy)
    roots = _crossings(field_, outcome.brackets, policy)
    excursions = _assemble_excursions(
        field_, "synthetic", jd_start, jd_end, roots, True, policy
    )
    assert len(excursions) == 1
    excursion = excursions[0]
    assert excursion.entry is None
    assert excursion.entry_clipped is True
    assert excursion.departure is not None
    assert excursion.departure_clipped is False
    assert excursion.duration_is_lower_bound is True
    assert excursion.is_complete is False
    assert excursion.jd_start_observed == jd_start


def test_still_out_at_range_end_reports_a_clipped_departure():
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    policy = OutOfBoundsPolicy()
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    jd_start = epoch
    jd_end = epoch + period / 4.0
    outcome = _scan_for_brackets(field_, jd_start, jd_end, 0.5, policy)
    roots = _crossings(field_, outcome.brackets, policy)
    excursions = _assemble_excursions(
        field_, "synthetic", jd_start, jd_end, roots, False, policy
    )
    assert len(excursions) == 1
    excursion = excursions[0]
    assert excursion.entry is not None
    assert excursion.entry_clipped is False
    assert excursion.departure is None
    assert excursion.departure_clipped is True
    assert excursion.duration_is_lower_bound is True
    assert excursion.jd_end_observed == jd_end


def test_window_inside_one_excursion_is_clipped_at_both_edges():
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    policy = OutOfBoundsPolicy()
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    peak = epoch + period / 4.0
    excursions = _assemble_excursions(
        field_, "synthetic", peak - 0.5, peak + 0.5, [], True, policy
    )
    assert len(excursions) == 1
    excursion = excursions[0]
    assert excursion.entry is None and excursion.departure is None
    assert excursion.entry_clipped and excursion.departure_clipped
    assert excursion.duration_is_lower_bound is True
    assert excursion.duration_hours == pytest.approx(24.0)


def test_no_excursion_assembles_to_an_empty_tuple():
    field_ = _AnalyticField(lambda jd: 5.0, obliquity_fn=lambda jd: 23.4)
    excursions = _assemble_excursions(
        field_, "synthetic", 2451545.0, 2451555.0, [], False, OutOfBoundsPolicy()
    )
    assert excursions == ()


def test_southern_excursion_is_labelled_south():
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    policy = OutOfBoundsPolicy()
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    jd_start = epoch + period / 2.0
    jd_end = epoch + period
    outcome = _scan_for_brackets(field_, jd_start, jd_end, 0.5, policy)
    roots = _crossings(field_, outcome.brackets, policy)
    excursions = _assemble_excursions(
        field_, "synthetic", jd_start, jd_end, roots, False, policy
    )
    assert len(excursions) == 1
    assert excursions[0].hemisphere == "south"
    assert excursions[0].culmination.declination < 0.0


def test_hemisphere_sign_is_constant_through_every_excursion():
    """Invariant: |delta| > epsilon > 0 forbids a sign change while out.

    Asserted directly on the solved excursions rather than assumed.
    """
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    policy = OutOfBoundsPolicy()
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    jd_start, jd_end = epoch, epoch + 3.0 * period
    outcome = _scan_for_brackets(field_, jd_start, jd_end, 0.5, policy)
    roots = _crossings(field_, outcome.brackets, policy)
    excursions = _assemble_excursions(
        field_, "synthetic", jd_start, jd_end, roots, False, policy
    )
    assert len(excursions) == 6
    for excursion in excursions:
        expected = 1.0 if excursion.hemisphere == "north" else -1.0
        for index in range(21):
            jd = excursion.jd_start_observed + (
                excursion.jd_end_observed - excursion.jd_start_observed
            ) * index / 20.0
            declination = field_.sample(jd)[0]
            if abs(declination) > field_.sample(jd)[1]:
                assert math.copysign(1.0, declination) == expected


def test_excursions_are_ordered_and_disjoint():
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    policy = OutOfBoundsPolicy()
    field_ = _AnalyticField(
        _sine_declination(amplitude, period, phase=epoch),
        obliquity_fn=lambda jd: 23.4,
    )
    jd_start, jd_end = epoch, epoch + 3.0 * period
    outcome = _scan_for_brackets(field_, jd_start, jd_end, 0.5, policy)
    roots = _crossings(field_, outcome.brackets, policy)
    excursions = _assemble_excursions(
        field_, "synthetic", jd_start, jd_end, roots, False, policy
    )
    for earlier, later in zip(excursions, excursions[1:]):
        assert earlier.jd_end_observed <= later.jd_start_observed
        assert earlier.jd_start_observed < earlier.jd_end_observed


def test_a_moving_obliquity_moves_the_root():
    """Entries are roots of |delta| - epsilon(t), not of |delta| - 23.4."""
    amplitude, period, epoch = 25.0, 27.3, 2451545.0
    declination = _sine_declination(amplitude, period, phase=epoch)
    static = _AnalyticField(declination, obliquity_fn=lambda jd: 23.4)
    drifting = _AnalyticField(
        declination, obliquity_fn=lambda jd: 23.4 + 0.02 * (jd - epoch)
    )
    static_root, _, _ = _bisect_bound_root(static, epoch, epoch + period / 4.0, 1e-10)
    drifting_root, _, _ = _bisect_bound_root(
        drifting, epoch, epoch + period / 4.0, 1e-10
    )
    assert abs(static_root - drifting_root) > 1e-4
    # A rising bound delays the northern entry.
    assert drifting_root > static_root
