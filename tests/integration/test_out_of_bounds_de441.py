"""Out-of-bounds solver invariants under DE441 and the released small-body kernels.

What this proves, in the vocabulary of AGENTS.md Part VI:

* **Physical and geometric invariants.** Every solved entry and return is
  checked against an independently projected declination built from the
  equatorial Cartesian product and the true obliquity of date, not from the
  ecliptic longitude/latitude pair the solver itself consumes. Hemisphere
  constancy, bracket containment, ordering and disjointness are asserted
  directly.
* **Independent-scan corroboration.** Excursion counts and edges are compared
  with a brute-force fine grid over the same window, built in the test from
  the same independent projection. The fine grid is a second, dumber search,
  not an external authority.
* **Conditioning.** The declination rate and achieved tolerance carried on
  every crossing are checked against finite differences of the independent
  projection, and the lunar-versus-Plutonian conditioning spread that
  motivates reporting them at all is asserted as a measured fact.

What it does not prove: agreement with any external engine or published
out-of-bounds table. No authority validation against a primary source is
claimed here, because Moira owns the definition of the product (apparent
geocentric declination of date against the true obliquity of date) and no
external authority publishes that product under matching semantics.

Tolerances are owned by the product under test and stated at each assertion.
"""

from __future__ import annotations

import math

import pytest

from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira._kernel_paths import find_planetary_kernel
from moira.julian import julian_day
from moira.obliquity import true_obliquity
from moira.out_of_bounds import (
    OutOfBoundsBudgetError,
    OutOfBoundsPolicy,
    OutOfBoundsUnavailableError,
    find_out_of_bounds,
)
from moira.planets import planet_at
from moira.spk_reader import use_reader_override

pytestmark = pytest.mark.requires_ephemeris


# ---------------------------------------------------------------------------
# Independent witness: declination from the equatorial Cartesian product
# ---------------------------------------------------------------------------

def _witness_is_cartesian(body: str) -> bool:
    """True where ``planet_at`` admits the equatorial Cartesian frame.

    Small bodies are restricted to the default apparent geocentric ecliptic
    path through ``planet_at``, so the strongest witness is available for
    planets and points only. The weaker small-body witness is described in
    ``_independent_declination``.
    """

    from moira.constants import Body
    from moira.small_body_identity import resolve_small_body_identity

    name = body.strip()
    if name in Body.ALL_PLANETS or name in getattr(Body, "ALL_POINTS", ()):
        return True
    return resolve_small_body_identity(name) is None


def _independent_declination(body: str, jd_ut: float, reader) -> float:
    """Declination by a route the solver does not take.

    Two strengths of witness, and the difference is stated rather than
    glossed:

    * **Planets and points** use ``frame="cartesian"``: the declination is
      read straight off the equatorial Cartesian vector, so the solver's
      ecliptic longitude/latitude pair and its frame rotation are both
      bypassed. A sign, quadrant, units or rotation defect anywhere in the
      solver's path cannot hide behind agreement with itself.
    * **Small bodies** cannot use that frame — ``planet_at`` admits only the
      default apparent geocentric ecliptic path for them. The witness instead
      builds a unit vector from the apparent ecliptic place and rotates it
      about the x-axis by the true obliquity, taking the declination from the
      rotated z component. That is an algebraically distinct route from the
      closed-form ``sin(dec) = sin(lat)cos(eps) + cos(lat)sin(eps)sin(lon)``
      identity in ``coordinates.ecliptic_to_equatorial``, so it still catches
      sign, quadrant and units defects in the transform. It does share the
      apparent-place pipeline with the solver, so for small bodies this is a
      transform-and-assembly witness, not a full independent position.
    """

    if _witness_is_cartesian(body):
        position = planet_at(body, jd_ut, reader=reader, frame="cartesian")
        return math.degrees(
            math.atan2(position.z, math.hypot(position.x, position.y))
        )

    place = planet_at(body, jd_ut, reader=reader)
    longitude = math.radians(place.longitude)
    latitude = math.radians(place.latitude)
    obliquity = math.radians(
        true_obliquity(_ut1_to_ephemeris_tt(jd_ut, reader))
    )
    # Unit vector in the ecliptic frame, then an explicit x-axis rotation
    # into the equatorial frame.
    x = math.cos(latitude) * math.cos(longitude)
    y = math.cos(latitude) * math.sin(longitude)
    z = math.sin(latitude)
    y_eq = y * math.cos(obliquity) - z * math.sin(obliquity)
    z_eq = y * math.sin(obliquity) + z * math.cos(obliquity)
    return math.degrees(math.atan2(z_eq, math.hypot(x, y_eq)))


def _independent_bound(body: str, jd_ut: float, reader) -> float:
    """|declination| - obliquity from the independent witness."""

    declination = _independent_declination(body, jd_ut, reader)
    obliquity = true_obliquity(_ut1_to_ephemeris_tt(jd_ut, reader))
    return abs(declination) - obliquity


def _brute_force_excursions(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float,
    reader,
) -> list[tuple[float, float]]:
    """A second, dumber search: fine grid with linear root interpolation.

    Returns observed (start, end) pairs, clipped to the window exactly as the
    solver clips them. Its own accuracy is limited by ``step_days``, so it
    corroborates counts and edges, never the solver's precision.
    """

    samples: list[tuple[float, float]] = []
    jd = jd_start
    while jd <= jd_end + 1e-12:
        samples.append((jd, _independent_bound(body, jd, reader)))
        jd += step_days
    if samples[-1][0] < jd_end:
        samples.append((jd_end, _independent_bound(body, jd_end, reader)))

    excursions: list[tuple[float, float]] = []
    inside = samples[0][1] > 0.0
    start = jd_start if inside else None
    for (jd_low, value_low), (jd_high, value_high) in zip(samples, samples[1:]):
        if value_low <= 0.0 < value_high:
            start = jd_low + (jd_high - jd_low) * (-value_low) / (
                value_high - value_low
            )
            inside = True
        elif value_low > 0.0 >= value_high:
            end = jd_low + (jd_high - jd_low) * value_low / (value_low - value_high)
            excursions.append((start, end))
            inside = False
    if inside:
        excursions.append((start, jd_end))
    return excursions


@pytest.fixture(scope="module")
def reader():
    """Planetary-only reader for the planet and point cases.

    Kept separate from the small-body pool so the planetary cases still run on
    a checkout that has DE441 but no small-body release installed.
    """
    from moira.spk_reader import SpkReader

    kernel = find_planetary_kernel()
    assert kernel is not None, "DE441 is required for this module"
    with SpkReader(kernel) as active:
        with use_reader_override(active):
            yield active


@pytest.fixture
def small_body_reader(small_body_reader_context):
    """Planetary plus separately admitted small-body readers.

    Asteroid and comet cases need the catalog kernels, which the plain
    planetary reader does not carry. This routes the repository's own admitted
    small-body pool, so these cases skip rather than fail where no small-body
    release is installed.
    """

    return small_body_reader_context


# ---------------------------------------------------------------------------
# The measured lunar case that defeats a name-derived scan step
# ---------------------------------------------------------------------------

# 2020-03-05: the Moon's monthly declination maximum is passing through the
# obliquity near a quarter point of the 18.6-year nodal cycle, so it clears
# the bound by only about 21 arcseconds and stays out for roughly 4.3 hours.
# Measured against this engine, a 1-day scan step misses it for 8 of 10 grid
# phasings, and even the 0.25-day step that moira.transits._auto_step assigns
# the Moon misses it for 2 of 10. Every asteroid and comet gets 1.0 day from
# that table, which is why this solver derives its step from measured motion.
_SHALLOW_LUNAR_WINDOW = (julian_day(2020, 3, 1, 0.0), julian_day(2020, 3, 10, 0.0))
_SHALLOW_LUNAR_PEAK_JD = 2458913.5654
_SHALLOW_LUNAR_PEAK_EXCESS_DEG = 0.005733
_SHALLOW_LUNAR_DURATION_HOURS = 4.37


def test_shallow_lunar_excursion_is_found_at_all(reader):
    """The 4.3-hour excursion of 2020-03-05 must be reported."""
    jd_start, jd_end = _SHALLOW_LUNAR_WINDOW
    report = find_out_of_bounds("Moon", jd_start, jd_end, reader=reader)
    assert report.excursion_count == 1
    excursion = report.excursions[0]
    assert excursion.hemisphere == "north"
    assert excursion.is_complete is True
    # Duration to better than a minute against the measured 4.37 hours.
    assert excursion.duration_hours == pytest.approx(
        _SHALLOW_LUNAR_DURATION_HOURS, abs=0.02
    )


def test_shallow_lunar_culmination_matches_the_measured_peak(reader):
    """The peak clears the bound by about 21 arcseconds, and it is solved.

    The tolerance is 0.1 arcsecond on the excess, which is far finer than the
    excursion's own 21-arcsecond amplitude; a grid-read peak could not meet it.
    """
    jd_start, jd_end = _SHALLOW_LUNAR_WINDOW
    report = find_out_of_bounds("Moon", jd_start, jd_end, reader=reader)
    culmination = report.excursions[0].culmination
    assert culmination.jd_ut == pytest.approx(_SHALLOW_LUNAR_PEAK_JD, abs=1e-3)
    assert culmination.excess_deg == pytest.approx(
        _SHALLOW_LUNAR_PEAK_EXCESS_DEG, abs=0.1 / 3600.0
    )
    assert culmination.at_boundary is False
    assert culmination.interior_critical_points == 1


def test_a_one_day_step_misses_the_shallow_lunar_excursion_in_most_phasings(
    reader,
):
    """The guard is proven by showing the naive cadence usually fails.

    This is the exact failure mode ``moira.transits._auto_step`` would hand
    every asteroid and comet, which it gives 1.0 day. Whether a fixed grid
    catches a 4.3-hour excursion is pure luck of phase: a node has to land
    inside it. Sweeping the start offset across one full day measures that
    luck instead of relying on a single lucky or unlucky alignment.

    The measured result on this engine is that a 1-day cadence misses it for
    8 of 10 offsets, while the default measured-rate policy finds it at every
    offset. The assertions below are deliberately looser than the measurement
    so that an unrelated ephemeris refinement cannot make them brittle.
    """
    jd_start, jd_end = _SHALLOW_LUNAR_WINDOW
    naive = OutOfBoundsPolicy(
        min_step_days=1.0,
        max_step_days=1.0,
        angular_resolution_deg=1e6,
        max_subdivision_depth=0,
        close_approach_refinement_depth=0,
    )
    offsets = [index / 10.0 for index in range(10)]
    naive_found = 0
    default_found = 0
    for offset in offsets:
        naive_found += find_out_of_bounds(
            "Moon", jd_start + offset, jd_end + offset, reader=reader, policy=naive
        ).excursion_count
        default_found += find_out_of_bounds(
            "Moon", jd_start + offset, jd_end + offset, reader=reader
        ).excursion_count
    # The naive cadence is mostly blind to it.
    assert naive_found <= 4, (
        f"a 1-day cadence found the excursion in {naive_found}/10 phasings; "
        "it should be mostly blind to a 4.3-hour excursion"
    )
    # The measured-rate policy with refinement finds it every time.
    assert default_found == len(offsets)


def test_shallow_lunar_excursion_is_witnessed_by_the_independent_projection(reader):
    """The excursion exists in the Cartesian witness too, not only the solver."""
    jd_start, jd_end = _SHALLOW_LUNAR_WINDOW
    report = find_out_of_bounds("Moon", jd_start, jd_end, reader=reader)
    excursion = report.excursions[0]
    # Inside, the witness agrees the body is out; just outside, it agrees it
    # is not. One second of margin keeps the test off the root itself.
    second = 1.0 / 86400.0
    assert _independent_bound("Moon", excursion.culmination.jd_ut, reader) > 0.0
    assert _independent_bound("Moon", excursion.entry.jd_ut - 60 * second, reader) < 0.0
    assert (
        _independent_bound("Moon", excursion.departure.jd_ut + 60 * second, reader)
        < 0.0
    )


# ---------------------------------------------------------------------------
# Crossings are roots, and are witnessed independently
# ---------------------------------------------------------------------------

# Each case names the reader fixture it needs. Planets run on the plain
# planetary reader; asteroids and comets need the separately admitted
# small-body pool and skip without it.
_WITNESS_CASES = (
    ("Moon", julian_day(2026, 1, 1, 0.0), julian_day(2026, 3, 1, 0.0), "reader"),
    ("Mercury", julian_day(2026, 1, 1, 0.0), julian_day(2027, 1, 1, 0.0), "reader"),
    ("Venus", julian_day(2026, 1, 1, 0.0), julian_day(2027, 6, 1, 0.0), "reader"),
    ("Pluto", julian_day(2026, 1, 1, 0.0), julian_day(2027, 1, 1, 0.0), "reader"),
    (
        "Ceres",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2027, 6, 1, 0.0),
        "small_body_reader",
    ),
    (
        "Eros",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2027, 1, 1, 0.0),
        "small_body_reader",
    ),
)


@pytest.mark.parametrize(
    ("body", "jd_start", "jd_end", "reader_fixture"), _WITNESS_CASES
)
def test_every_crossing_is_a_root_of_the_independent_bound(
    body, jd_start, jd_end, reader_fixture, request
):
    """At each solved crossing the independent witness is within tolerance of 0.

    The tolerance is 0.05 arcsecond on the bound function. It is a declination
    residual, not a time residual: at a crossing the two independent paths to
    |declination| - obliquity must agree on being at the root.
    """
    reader = request.getfixturevalue(reader_fixture)
    report = find_out_of_bounds(body, jd_start, jd_end, reader=reader)
    checked = 0
    for excursion in report.excursions:
        for crossing in (excursion.entry, excursion.departure):
            if crossing is None:
                continue
            residual = _independent_bound(body, crossing.jd_ut, reader)
            assert abs(residual) < 0.05 / 3600.0, (
                f"{body} {crossing.kind} at {crossing.jd_ut} has bound "
                f"residual {residual * 3600.0} arcsec"
            )
            checked += 1
    assert checked > 0


@pytest.mark.parametrize(
    ("body", "jd_start", "jd_end", "reader_fixture"), _WITNESS_CASES
)
def test_crossing_sits_inside_its_reported_bracket(body, jd_start, jd_end, reader_fixture, request):
    """The achieved tolerance must describe the bracket it came from."""
    reader = request.getfixturevalue(reader_fixture)
    report = find_out_of_bounds(body, jd_start, jd_end, reader=reader)
    for excursion in report.excursions:
        for crossing in (excursion.entry, excursion.departure):
            if crossing is None:
                continue
            assert (
                crossing.bracket_start_jd_ut
                <= crossing.jd_ut
                <= crossing.bracket_end_jd_ut
            )
            assert crossing.achieved_tolerance_days == pytest.approx(
                crossing.bracket_end_jd_ut - crossing.bracket_start_jd_ut,
                abs=1e-12,
            )
            assert crossing.achieved_tolerance_days <= (
                report.scan_truth.policy.solver_tolerance_days
            )


@pytest.mark.parametrize(
    ("body", "jd_start", "jd_end", "reader_fixture"), _WITNESS_CASES
)
def test_declination_rate_matches_an_independent_finite_difference(
    body, jd_start, jd_end, reader_fixture, request
):
    """The reported rate must be the real rate of the independent witness.

    Tolerance: 1 percent relative, plus an absolute floor of 1e-4 deg/day for
    a crossing whose rate is near zero. The witness difference uses a
    half-step of 0.002 day, so its own truncation error is the binding term
    for a fast body, not the solver's.
    """
    reader = request.getfixturevalue(reader_fixture)
    report = find_out_of_bounds(body, jd_start, jd_end, reader=reader)
    half_step = 0.002
    for excursion in report.excursions:
        for crossing in (excursion.entry, excursion.departure):
            if crossing is None:
                continue
            witness_rate = (
                _independent_declination(body, crossing.jd_ut + half_step, reader)
                - _independent_declination(body, crossing.jd_ut - half_step, reader)
            ) / (2.0 * half_step)
            assert crossing.declination_rate_deg_per_day == pytest.approx(
                witness_rate, rel=0.01, abs=1e-4
            )


@pytest.mark.parametrize(
    ("body", "jd_start", "jd_end", "reader_fixture"), _WITNESS_CASES
)
def test_bound_rate_is_the_hemisphere_signed_rate_less_the_obliquity_rate(
    body, jd_start, jd_end, reader_fixture, request
):
    """The conditioning quantity must be assembled as declared."""
    reader = request.getfixturevalue(reader_fixture)
    report = find_out_of_bounds(body, jd_start, jd_end, reader=reader)
    for excursion in report.excursions:
        for crossing in (excursion.entry, excursion.departure):
            if crossing is None:
                continue
            sign = 1.0 if crossing.declination >= 0.0 else -1.0
            expected = (
                sign * crossing.declination_rate_deg_per_day
                - crossing.obliquity_rate_deg_per_day
            )
            assert crossing.bound_rate_deg_per_day == pytest.approx(
                expected, rel=1e-9, abs=1e-12
            )
            # An entry drives the bound upward, a return downward.
            if crossing.kind == "entry":
                assert crossing.bound_rate_deg_per_day > 0.0
            else:
                assert crossing.bound_rate_deg_per_day < 0.0


def test_obliquity_rate_is_small_but_not_zero(reader):
    """The bound moves. A solver that froze the obliquity would report zero."""
    report = find_out_of_bounds(
        "Moon",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2026, 3, 1, 0.0),
        reader=reader,
    )
    rates = [
        crossing.obliquity_rate_deg_per_day
        for excursion in report.excursions
        for crossing in (excursion.entry, excursion.departure)
        if crossing is not None
    ]
    assert rates
    # Nutation in obliquity moves the bound by order 1e-5 deg/day; precession
    # alone would be some 1e-7. Neither is zero.
    assert all(rate != 0.0 for rate in rates)
    assert max(abs(rate) for rate in rates) < 1e-3


# ---------------------------------------------------------------------------
# Independent-scan corroboration of counts and edges
# ---------------------------------------------------------------------------

_CORROBORATION_CASES = (
    ("Moon", julian_day(2020, 3, 1, 0.0), julian_day(2020, 3, 20, 0.0), 0.002, "reader"),
    ("Moon", julian_day(2026, 1, 1, 0.0), julian_day(2026, 3, 1, 0.0), 0.005, "reader"),
    ("Mercury", julian_day(2026, 1, 1, 0.0), julian_day(2027, 1, 1, 0.0), 0.02, "reader"),
    ("Pluto", julian_day(2026, 1, 1, 0.0), julian_day(2027, 1, 1, 0.0), 0.05, "reader"),
    (
        "Ceres",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2027, 6, 1, 0.0),
        0.05,
        "small_body_reader",
    ),
    (
        "Eros",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2027, 1, 1, 0.0),
        0.05,
        "small_body_reader",
    ),
)


@pytest.mark.slow
@pytest.mark.parametrize(
    ("body", "jd_start", "jd_end", "grid_step", "reader_fixture"),
    _CORROBORATION_CASES,
)
def test_excursion_count_and_edges_agree_with_a_brute_force_grid(
    body, jd_start, jd_end, grid_step, reader_fixture, request
):
    """A second, dumber search must find the same excursions.

    Edge agreement is asserted to 120 seconds, which is the brute-force
    grid's own linear-interpolation error at these step sizes, not the
    solver's accuracy. The solver's accuracy is established by the root
    residual test above.
    """
    reader = request.getfixturevalue(reader_fixture)
    report = find_out_of_bounds(body, jd_start, jd_end, reader=reader)
    brute = _brute_force_excursions(body, jd_start, jd_end, grid_step, reader)
    assert report.excursion_count == len(brute), (
        f"{body}: solver found {report.excursion_count}, grid found {len(brute)}"
    )
    for excursion, (grid_start, grid_end) in zip(report.excursions, brute):
        if not excursion.entry_clipped:
            assert excursion.jd_start_observed == pytest.approx(
                grid_start, abs=120.0 / 86400.0
            )
        if not excursion.departure_clipped:
            assert excursion.jd_end_observed == pytest.approx(
                grid_end, abs=120.0 / 86400.0
            )


@pytest.mark.slow
@pytest.mark.parametrize(
    ("body", "jd_start", "jd_end", "grid_step"),
    [
        ("Zoozve", julian_day(2026, 9, 1, 0.0), julian_day(2027, 1, 1, 0.0), 0.01),
        ("Hathor", julian_day(2026, 2, 1, 0.0), julian_day(2026, 6, 1, 0.0), 0.01),
    ],
)
def test_fast_minor_body_excursions_agree_with_a_brute_force_grid(
    body, jd_start, jd_end, grid_step, small_body_reader
):
    """The asteroid case the 1-day table step exists to break.

    These are near-Earth bodies whose declination can sweep several degrees a
    day during a close approach. The brute-force grid here is 0.01 day, fine
    enough that the comparison is meaningful.
    """
    reader = small_body_reader
    report = find_out_of_bounds(body, jd_start, jd_end, reader=reader)
    brute = _brute_force_excursions(body, jd_start, jd_end, grid_step, reader)
    assert report.excursion_count == len(brute)


@pytest.mark.slow
def test_culminated_peak_is_never_below_the_grid_maximum(small_body_reader):
    """The solved extremum must dominate a dense sweep of its own excursion.

    This is the ternary-search failure stated as an invariant: a hump-assuming
    search returned a peak *below* the grid maximum on a clipped window. The
    solved peak must never do that, for any body or clipping.
    """
    reader = small_body_reader
    cases = (
        ("Moon", julian_day(2020, 3, 1, 0.0), julian_day(2020, 3, 20, 0.0)),
        ("Moon", julian_day(2026, 1, 15, 0.0), julian_day(2026, 2, 5, 0.0)),
        ("Eros", julian_day(2026, 1, 1, 0.0), julian_day(2027, 1, 1, 0.0)),
        ("Ceres", julian_day(2026, 6, 1, 0.0), julian_day(2027, 6, 1, 0.0)),
    )
    checked = 0
    for body, jd_start, jd_end in cases:
        report = find_out_of_bounds(body, jd_start, jd_end, reader=reader)
        for excursion in report.excursions:
            reported = abs(excursion.culmination.declination)
            span = excursion.jd_end_observed - excursion.jd_start_observed
            sweep = max(
                abs(
                    _independent_declination(
                        body,
                        excursion.jd_start_observed + span * index / 60.0,
                        reader,
                    )
                )
                for index in range(61)
            )
            # 0.5 arcsecond covers the difference between the two declination
            # paths; the point is that the solved peak is not materially lower.
            assert reported >= sweep - 0.5 / 3600.0, (
                f"{body}: solved peak {reported} below grid sweep {sweep}"
            )
            checked += 1
    assert checked > 0


# ---------------------------------------------------------------------------
# Conditioning: the measured fact that motivates the whole receipt
# ---------------------------------------------------------------------------

def test_lunar_and_plutonian_crossings_differ_by_orders_of_magnitude(reader):
    """Why every crossing must carry its rate.

    Measured against this engine, a lunar crossing costs a few seconds of time
    per arcsecond of declination error while a Plutonian one costs over an
    hour. The same printed minute is meaningful for one and meaningless for
    the other, so the rate is not optional metadata.
    """
    lunar = find_out_of_bounds(
        "Moon",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2026, 3, 1, 0.0),
        reader=reader,
    )
    plutonian = find_out_of_bounds(
        "Pluto",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2027, 1, 1, 0.0),
        reader=reader,
    )
    lunar_crossings = [
        crossing
        for excursion in lunar.excursions
        for crossing in (excursion.entry, excursion.departure)
        if crossing is not None
    ]
    plutonian_crossings = [
        crossing
        for excursion in plutonian.excursions
        for crossing in (excursion.entry, excursion.departure)
        if crossing is not None
    ]
    assert lunar_crossings and plutonian_crossings

    best_lunar = min(
        crossing.time_sensitivity_seconds_per_arcsec for crossing in lunar_crossings
    )
    worst_plutonian = max(
        crossing.time_sensitivity_seconds_per_arcsec
        for crossing in plutonian_crossings
    )
    # A lunar crossing stays inside a minute per arcsecond.
    assert best_lunar < 60.0
    # A Plutonian crossing exceeds half an hour per arcsecond.
    assert worst_plutonian > 1800.0
    # And the spread is at least two orders of magnitude.
    assert worst_plutonian / best_lunar > 100.0
    assert all(
        crossing.conditioning == "well_posed" for crossing in lunar_crossings
    )
    assert all(
        crossing.conditioning == "ill_conditioned"
        for crossing in plutonian_crossings
    )


def test_sensitivity_is_the_reciprocal_of_the_bound_rate(reader):
    """The receipt must be internally consistent, not decorative."""
    report = find_out_of_bounds(
        "Moon",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2026, 3, 1, 0.0),
        reader=reader,
    )
    for excursion in report.excursions:
        for crossing in (excursion.entry, excursion.departure):
            if crossing is None:
                continue
            arcsec_per_day = abs(crossing.bound_rate_deg_per_day) * 3600.0
            assert crossing.time_sensitivity_days_per_arcsec == pytest.approx(
                1.0 / arcsec_per_day, rel=1e-12
            )
            assert crossing.time_sensitivity_seconds_per_arcsec == pytest.approx(
                crossing.time_sensitivity_days_per_arcsec * 86400.0, rel=1e-12
            )


# ---------------------------------------------------------------------------
# Window-edge semantics
# ---------------------------------------------------------------------------

def test_window_starting_inside_an_excursion_reports_a_clipped_entry(reader):
    """A clipped duration is 'at least this long', never the full length."""
    full = find_out_of_bounds(
        "Pluto",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2027, 1, 1, 0.0),
        reader=reader,
    )
    assert full.excursion_count == 1
    assert full.excursions[0].is_complete

    # Re-ask starting after the entry: the entry must now be unknown.
    entry_jd = full.excursions[0].entry.jd_ut
    clipped = find_out_of_bounds(
        "Pluto", entry_jd + 5.0, julian_day(2027, 1, 1, 0.0), reader=reader
    )
    assert clipped.excursion_count == 1
    excursion = clipped.excursions[0]
    assert clipped.out_of_bounds_at_start is True
    assert excursion.entry is None
    assert excursion.entry_clipped is True
    assert excursion.duration_is_lower_bound is True
    assert excursion.is_complete is False
    # The clipped duration must be strictly shorter than the true one.
    assert excursion.duration_hours < full.excursions[0].duration_hours


def test_window_ending_inside_an_excursion_reports_a_clipped_departure(reader):
    full = find_out_of_bounds(
        "Pluto",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2027, 1, 1, 0.0),
        reader=reader,
    )
    departure_jd = full.excursions[0].departure.jd_ut
    clipped = find_out_of_bounds(
        "Pluto", julian_day(2026, 1, 1, 0.0), departure_jd - 5.0, reader=reader
    )
    assert clipped.excursion_count == 1
    excursion = clipped.excursions[0]
    assert clipped.out_of_bounds_at_end is True
    assert excursion.departure is None
    assert excursion.departure_clipped is True
    assert excursion.duration_is_lower_bound is True


def test_window_wholly_inside_an_excursion_is_clipped_at_both_edges(reader):
    full = find_out_of_bounds(
        "Pluto",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2027, 1, 1, 0.0),
        reader=reader,
    )
    entry_jd = full.excursions[0].entry.jd_ut
    departure_jd = full.excursions[0].departure.jd_ut
    clipped = find_out_of_bounds(
        "Pluto", entry_jd + 5.0, departure_jd - 5.0, reader=reader
    )
    assert clipped.excursion_count == 1
    excursion = clipped.excursions[0]
    assert excursion.entry is None and excursion.departure is None
    assert excursion.entry_clipped and excursion.departure_clipped
    assert excursion.duration_is_lower_bound is True
    assert clipped.out_of_bounds_at_start and clipped.out_of_bounds_at_end
    # Clipped at both ends, the extremum may well sit on an edge; whichever
    # it is, it must be reported honestly.
    if excursion.culmination.at_boundary:
        assert excursion.culmination.boundary_edge in {"range_start", "range_end"}


def test_clipped_culmination_at_a_boundary_is_labelled_as_such(reader):
    """A window cut just after the peak must say the extremum is on the edge."""
    full = find_out_of_bounds(
        "Pluto",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2027, 1, 1, 0.0),
        reader=reader,
    )
    peak_jd = full.excursions[0].culmination.jd_ut
    after = find_out_of_bounds(
        "Pluto",
        peak_jd + 1.0,
        full.excursions[0].departure.jd_ut - 1.0,
        reader=reader,
    )
    assert after.excursion_count == 1
    culmination = after.excursions[0].culmination
    assert culmination.at_boundary is True
    assert culmination.boundary_edge == "range_start"
    assert culmination.interior_critical_points == 0


def test_a_complete_excursion_culminates_strictly_inside_itself(small_body_reader):
    """Theorem: an unclipped excursion has its bound maximum in the interior.

    B vanishes at both solved edges and is strictly positive between them, so
    the maximum of B cannot sit on an edge. Asserted on real excursions.
    """
    reader = small_body_reader
    for body, jd_start, jd_end in (
        ("Moon", julian_day(2026, 1, 1, 0.0), julian_day(2026, 3, 1, 0.0)),
        ("Mercury", julian_day(2026, 1, 1, 0.0), julian_day(2027, 1, 1, 0.0)),
        ("Eros", julian_day(2026, 1, 1, 0.0), julian_day(2027, 1, 1, 0.0)),
    ):
        report = find_out_of_bounds(body, jd_start, jd_end, reader=reader)
        for excursion in report.excursions:
            if not excursion.is_complete:
                continue
            assert excursion.culmination.at_boundary is False
            assert excursion.culmination.interior_critical_points >= 1
            assert (
                excursion.jd_start_observed
                < excursion.culmination.jd_ut
                < excursion.jd_end_observed
            )
            assert excursion.culmination.excess_deg > 0.0


# ---------------------------------------------------------------------------
# Structural invariants over real excursions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("body", "jd_start", "jd_end", "reader_fixture"),
    [
        ("Moon", julian_day(2026, 1, 1, 0.0), julian_day(2026, 6, 1, 0.0), "reader"),
        (
            "Eros",
            julian_day(2026, 1, 1, 0.0),
            julian_day(2028, 1, 1, 0.0),
            "small_body_reader",
        ),
        (
            "Ceres",
            julian_day(2026, 1, 1, 0.0),
            julian_day(2028, 1, 1, 0.0),
            "small_body_reader",
        ),
    ],
)
def test_hemisphere_is_constant_across_each_excursion(
    body, jd_start, jd_end, reader_fixture, request
):
    """|delta| > epsilon > 0 forbids a sign change while the body is out."""
    reader = request.getfixturevalue(reader_fixture)
    report = find_out_of_bounds(body, jd_start, jd_end, reader=reader)
    assert report.excursion_count > 0
    for excursion in report.excursions:
        expected = 1.0 if excursion.hemisphere == "north" else -1.0
        span = excursion.jd_end_observed - excursion.jd_start_observed
        for index in range(1, 20):
            jd = excursion.jd_start_observed + span * index / 20.0
            declination = _independent_declination(body, jd, reader)
            assert math.copysign(1.0, declination) == expected
        assert math.copysign(1.0, excursion.culmination.declination) == expected


@pytest.mark.parametrize(
    ("body", "jd_start", "jd_end", "reader_fixture"),
    [
        ("Moon", julian_day(2026, 1, 1, 0.0), julian_day(2026, 6, 1, 0.0), "reader"),
        (
            "Eros",
            julian_day(2026, 1, 1, 0.0),
            julian_day(2028, 1, 1, 0.0),
            "small_body_reader",
        ),
    ],
)
def test_excursions_are_ordered_disjoint_and_inside_the_range(
    body, jd_start, jd_end, reader_fixture, request
):
    reader = request.getfixturevalue(reader_fixture)
    report = find_out_of_bounds(body, jd_start, jd_end, reader=reader)
    for excursion in report.excursions:
        assert jd_start <= excursion.jd_start_observed
        assert excursion.jd_end_observed <= jd_end
        assert excursion.jd_start_observed < excursion.jd_end_observed
    for earlier, later in zip(report.excursions, report.excursions[1:]):
        assert earlier.jd_end_observed < later.jd_start_observed


def test_report_edge_states_match_the_independent_witness(reader):
    for body, jd_start, jd_end in (
        ("Moon", julian_day(2026, 1, 1, 0.0), julian_day(2026, 3, 1, 0.0)),
        ("Pluto", julian_day(2026, 6, 1, 0.0), julian_day(2027, 1, 1, 0.0)),
    ):
        report = find_out_of_bounds(body, jd_start, jd_end, reader=reader)
        assert report.out_of_bounds_at_start == (
            _independent_bound(body, jd_start, reader) > 0.0
        )
        assert report.out_of_bounds_at_end == (
            _independent_bound(body, jd_end, reader) > 0.0
        )
        assert report.obliquity_at_start == pytest.approx(
            true_obliquity(_ut1_to_ephemeris_tt(jd_start, reader)), abs=1e-12
        )


# ---------------------------------------------------------------------------
# Body classes: planets, asteroids, comets
# ---------------------------------------------------------------------------

def test_comets_resolve_and_are_scanned(small_body_reader):
    """The comet path must reach the solver at all.

    Before this work the shared declination primitive routed small bodies
    through ``asteroid_at`` only, so a comet name fell through to the star
    resolver and raised. A comet now resolves, is classified as a comet, and
    produces a scan with a measured step.
    """
    reader = small_body_reader
    jd_start = julian_day(2026, 1, 1, 0.0)
    jd_end = julian_day(2027, 1, 1, 0.0)
    for name in ("2P/Encke", "comet:2P/Encke", "1P/Halley"):
        report = find_out_of_bounds(name, jd_start, jd_end, reader=reader)
        assert report.resolved_kind == "comet"
        assert report.scan_truth.declination_evaluations > 0
        assert report.scan_truth.coarse_step_days > 0.0
        assert report.obliquity_at_start > 23.0


def test_asteroid_and_qualified_asteroid_agree(small_body_reader):
    reader = small_body_reader
    jd_start = julian_day(2026, 1, 1, 0.0)
    jd_end = julian_day(2027, 6, 1, 0.0)
    bare = find_out_of_bounds("Ceres", jd_start, jd_end, reader=reader)
    qualified = find_out_of_bounds(
        "asteroid:Ceres", jd_start, jd_end, reader=reader
    )
    assert bare.resolved_kind == "asteroid"
    assert qualified.resolved_kind == "asteroid"
    assert bare.excursion_count == qualified.excursion_count
    for left, right in zip(bare.excursions, qualified.excursions):
        assert left.jd_start_observed == pytest.approx(
            right.jd_start_observed, abs=1e-9
        )


def test_resolved_kind_distinguishes_the_body_classes(small_body_reader):
    reader = small_body_reader
    jd_start = julian_day(2026, 1, 1, 0.0)
    jd_end = julian_day(2026, 4, 1, 0.0)
    for name, expected in (
        ("Moon", "planet"),
        ("Pluto", "planet"),
        ("Ceres", "asteroid"),
        ("2P/Encke", "comet"),
    ):
        report = find_out_of_bounds(name, jd_start, jd_end, reader=reader)
        assert report.resolved_kind == expected


def test_scan_step_is_not_a_per_body_table_lookup(small_body_reader):
    """A fast minor body must get a finer cadence than a slow one.

    ``moira.transits._auto_step`` returns 1.0 day for every body outside its
    table, which is every asteroid and comet. Here the step must follow
    measured motion, so bodies of very different speed must not share a step
    by accident.
    """
    reader = small_body_reader
    jd_start = julian_day(2026, 1, 1, 0.0)
    jd_end = julian_day(2026, 4, 1, 0.0)
    steps = {}
    for name in ("Moon", "Neptune", "Hathor"):
        report = find_out_of_bounds(name, jd_start, jd_end, reader=reader)
        steps[name] = report.scan_truth.coarse_step_days
        assert report.scan_truth.measured_max_rate_deg_per_day > 0.0
    # The Moon's measured rate is far above Neptune's, so its step must be
    # strictly finer. Nothing about the names enters this.
    assert steps["Moon"] < steps["Neptune"]


# ---------------------------------------------------------------------------
# Explicit unavailable, never a silent empty result
# ---------------------------------------------------------------------------

def test_uncovered_small_body_range_raises_explicit_unavailable(small_body_reader):
    """A body outside its kernel's arc must not report 'no excursions'.

    Apophis is released in the small-body catalog with an observed-arc
    coverage that does not extend to this window, which makes it the natural
    witness for the distinction between 'went nowhere' and 'cannot be said'.
    """
    reader = small_body_reader
    with pytest.raises(OutOfBoundsUnavailableError) as raised:
        find_out_of_bounds(
            "Apophis",
            julian_day(2026, 1, 1, 0.0),
            julian_day(2026, 2, 1, 0.0),
            reader=reader,
        )
    assert raised.value.reason == "ephemeris_coverage"
    assert raised.value.body == "Apophis"


@pytest.mark.parametrize(
    "body", ["True Node", "Mean Node", "Lilith", "True Lilith"]
)
def test_longitude_only_points_are_unavailable_not_empty(body, reader):
    """Moira models these as longitude-only, so they have no declination.

    ``nodes.NodeData`` carries no ecliptic latitude, so no declination can be
    formed. They must raise rather than be routed into a position API that
    answers with an opaque ``KeyError`` for three of them and, for Lilith, with
    a different object's position. A node also lies on the ecliptic by
    construction, so its declination magnitude could never exceed the
    obliquity, which is why the refusal costs nothing astrologically.
    """
    with pytest.raises(OutOfBoundsUnavailableError) as raised:
        find_out_of_bounds(
            body,
            julian_day(2026, 1, 1, 0.0),
            julian_day(2026, 7, 1, 0.0),
            reader=reader,
        )
    assert raised.value.reason == "body_unresolved"
    assert "longitude-only" in raised.value.detail


def test_unknown_body_raises_explicit_unavailable(reader):
    with pytest.raises(OutOfBoundsUnavailableError) as raised:
        find_out_of_bounds(
            "Nibiru",
            julian_day(2026, 1, 1, 0.0),
            julian_day(2026, 2, 1, 0.0),
            reader=reader,
        )
    assert raised.value.reason == "body_unresolved"


def test_a_genuinely_empty_range_is_an_empty_list_not_an_error(reader):
    """The other side of the distinction: Saturn really does stay in bounds."""
    report = find_out_of_bounds(
        "Saturn",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2026, 4, 1, 0.0),
        reader=reader,
    )
    assert report.excursion_count == 0
    assert report.excursions == ()
    assert report.out_of_bounds_at_start is False
    assert report.out_of_bounds_at_end is False
    assert report.scan_truth.declination_evaluations > 0


# ---------------------------------------------------------------------------
# Scan truth is honest about itself
# ---------------------------------------------------------------------------

def test_scan_truth_reports_its_own_cost_and_cadence(reader):
    report = find_out_of_bounds(
        "Moon",
        julian_day(2026, 1, 1, 0.0),
        julian_day(2026, 3, 1, 0.0),
        reader=reader,
    )
    truth = report.scan_truth
    assert truth.coarse_step_days > 0.0
    assert truth.coarse_node_count > 0
    assert truth.declination_evaluations > truth.coarse_node_count
    assert truth.measured_max_rate_deg_per_day >= (
        truth.measured_median_rate_deg_per_day
    )
    assert truth.rate_bound_deg_per_day > 0.0
    assert truth.resolved_amplitude_floor_deg > 0.0
    assert truth.policy.solver_tolerance_days > 0.0


def test_an_exhausted_budget_raises_instead_of_truncating(reader):
    """Measured cost is linear in the span, so a long span needs a ceiling.

    On this engine a lunar scan runs about 3,800 declination evaluations and
    2.4 seconds per year, so a century-long request is minutes of work. A
    search that runs out of budget must raise rather than hand back the
    excursions it happened to reach, which would be indistinguishable from a
    genuinely quiet century.
    """
    jd_start = julian_day(2020, 1, 1, 0.0)
    with pytest.raises(OutOfBoundsBudgetError) as raised:
        find_out_of_bounds(
            "Moon",
            jd_start,
            jd_start + 3652.5,
            reader=reader,
            policy=OutOfBoundsPolicy(max_declination_evaluations=2_000),
        )
    assert raised.value.budget == 2_000
    assert raised.value.evaluations >= 2_000
    assert raised.value.body == "Moon"


def test_a_generous_budget_does_not_disturb_the_result(reader):
    """A ceiling that is never reached must change nothing."""
    jd_start = julian_day(2020, 3, 1, 0.0)
    jd_end = julian_day(2020, 3, 20, 0.0)
    unbounded = find_out_of_bounds("Moon", jd_start, jd_end, reader=reader)
    bounded = find_out_of_bounds(
        "Moon",
        jd_start,
        jd_end,
        reader=reader,
        policy=OutOfBoundsPolicy(max_declination_evaluations=1_000_000),
    )
    assert bounded.excursion_count == unbounded.excursion_count
    for left, right in zip(bounded.excursions, unbounded.excursions):
        assert left.jd_start_observed == pytest.approx(
            right.jd_start_observed, abs=1e-12
        )
        assert left.culmination.jd_ut == pytest.approx(
            right.culmination.jd_ut, abs=1e-12
        )


def test_a_finer_requested_resolution_costs_more_and_finds_no_less(reader):
    """Tightening the declared resolution must not lose an excursion."""
    jd_start = julian_day(2020, 3, 1, 0.0)
    jd_end = julian_day(2020, 3, 20, 0.0)
    coarse = find_out_of_bounds("Moon", jd_start, jd_end, reader=reader)
    fine = find_out_of_bounds(
        "Moon",
        jd_start,
        jd_end,
        reader=reader,
        policy=OutOfBoundsPolicy(angular_resolution_deg=0.25),
    )
    assert fine.scan_truth.coarse_step_days < coarse.scan_truth.coarse_step_days
    assert fine.excursion_count >= coarse.excursion_count
