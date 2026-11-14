# Release Notes - Moira 6.14.0

**Release date:** 14 November 2026.

This release adds an out-of-bounds declination solver and Sothic drift fitting,
and corrects comet topocentric apparent places. Read the
[compatibility notes](COMPATIBILITY_NOTES_6.14.0.md) before upgrading: one
existing product changes value, which is the comet topocentric position.

## Out of bounds, solved rather than interpolated

A body is **out of bounds** when the magnitude of its geocentric apparent
declination exceeds the true obliquity of the ecliptic of date. Both terms
move: the declination with the body's own motion, the obliquity with precession
and nutation in obliquity. Entries and returns are therefore roots of
`|declination(t)| - obliquity(t)`, not of `|declination(t)| - 23.4`.

`moira.out_of_bounds` owns that bound function, the excursion object assembled
from its roots, and the extremal declination inside each excursion. The new
surfaces are `Moira.out_of_bounds(body, jd_start, jd_end, *, policy=None)` and
`POST /v1/out-of-bounds/search`.

The extremal declination is solved as a root of the declination rate, not read
off the scan grid. A search that assumes a single hump — a ternary search, for
instance — is wrong here: when a window is clipped the body may already be past
its turn, the maximum then sits on the window edge, and such a search walks
away from it and returns a peak below the grid's own samples. Every interior
critical point and both endpoints are evaluated, so a double-peaked excursion
reports its true maximum, and `culmination.at_boundary` says when the extremum
is on an edge.

## Every crossing says how much it is worth

The time error at a crossing is the declination error divided by the crossing
rate, and that rate varies enormously between bodies. Measured on this engine:

| crossing | bound rate | cost of one arcsecond |
|---|---|---|
| Moon, steep | 4.08 deg/day | 5.9 seconds |
| Mercury | 0.43 deg/day | 55 seconds |
| Eros | 0.22 deg/day | 109 seconds |
| Ceres | 0.023 deg/day | 17 minutes |
| Pluto | 0.0059 deg/day | 68 minutes |

Every crossing therefore carries `declination_rate_deg_per_day`,
`obliquity_rate_deg_per_day`, `bound_rate_deg_per_day` (the rate of the
quantity actually driven to zero), `time_sensitivity_days_per_arcsec`, the
solver's `achieved_tolerance_days`, its bracket, and a `conditioning` class of
`well_posed`, `sensitive`, `ill_conditioned` or `degenerate`. A printed instant
cannot be judged without them, and a caller cannot cheaply derive them.

## Window edges are stated, not truncated

A body already out of bounds at the range start reports `entry: null` with
`entry_clipped: true`; one still out at the range end reports `departure: null`
with `departure_clipped: true`. Either case sets `duration_is_lower_bound`, so
the duration means "at least this long". `out_of_bounds_at_start` and
`out_of_bounds_at_end` give the state at the requested bounds.

## Any body, at a cadence matched to its motion

`moira.transits._auto_step` returns 1.0 day for any body outside its table,
which is every asteroid and comet, and a fast near-Earth object can cross the
bound well inside a day. This solver measures the bound function's own secant
rates across the requested window and derives its coarse step from them, then
refines recursively any interval that is not provably clear of a root, with
bounded extra refinement across a close approach. No body name enters the
decision.

How much that matters is now an acceptance test, and the example is lunar
rather than exotic. On **2020-03-05** the Moon is out of bounds for **4.32
hours**, clearing the obliquity by only **20.6 arcseconds**, because its
monthly declination maximum is passing through the obliquity near a quarter
point of the 18.6-year nodal cycle. Sweeping ten grid phasings on this engine, a
1-day cadence misses it in **8 of 10**, and the 0.25-day cadence
`_auto_step` assigns the Moon — its best table entry — misses it in **2 of 10**.

Planets, asteroids and comets are all admitted, including the family-qualified
`asteroid:Name` and `comet:Name` forms. The lunar nodes and apogees are not:
Moira models them as longitude-only points, so no declination exists to compare
against the obliquity, and a node lies on the ecliptic by construction in any
case. A body whose ephemeris
does not cover the requested range raises `OutOfBoundsUnavailableError`, or
returns HTTP 422 with `out_of_bounds_date_outside_ephemeris_coverage`. It never
degrades to an empty excursion list, because "this body went nowhere out of
bounds" and "this body cannot be computed here" are different statements.

## Comet declinations now resolve at all

`transits_equatorial._declination` routed small bodies through `asteroid_at`
only, so a comet name fell through to the star resolver and raised. Small
bodies now route through `planets.planet_at`, the engine's unified front door,
which admits asteroids and comets alike and delegates to the same pipelines
those surfaces own. Declination parallels and contra-parallels for comets work
as a consequence. Asteroid results are unchanged and bit-identical.

## Comet topocentric places are now observer-centred

`sky_position_at()` built a *geocentric* apparent vector for a comet and then
shifted it to the observer. The observer's own position was therefore absent
from the light-time solution: no parallax, and diurnal aberration applied about
the wrong origin. For a comet near Earth that is a large error, and it is
exactly the regime in which anyone asks for a topocentric comet position.

Comets now take an observer-centred light-time solve through
`_comet_topocentric_equatorial_vector()`, built on `_observer_position_icrf`
and `_observer_velocity_icrf`. **Topocentric comet right ascension and
declination change value.** Geocentric comet positions are untouched:
`comet_at()` and `planet_at()` return exactly what they returned before, and
the kernel-selection refactor behind them is behaviour-preserving.

The asteroid arm of the same branch is deliberately unchanged and still uses
the geocentric-apparent vector with a topocentric shift. That approximation is
negligible for a main-belt body and is not for a near-Earth one, so the
asteroid path is now the weaker of the two. It is recorded as a known
limitation rather than quietly equalised.

Astrocartography follows from this: comet lines now project right ascension
from the selected observer rather than the geocentre, and require a loaded
comet kernel instead of assuming one. Comets are excluded from chart assembly
in line context, which wants an ecliptic position they do not supply there.

## Sothic drift, fitted rather than asserted

`SothicRisingSeries.fit_drift()` returns a `SothicDriftFit` carrying
`rate_days_per_year` — calendar days per astronomical year, positive for a
later rising date — together with the `SothicDriftSample` series it was fitted
from, each sample showing the civil-day offset both before and after calendar
unwrapping. `POST /v1/sothic/drift-rate` transports it.

The fit declines to guess. Below five found years the status is
`insufficient_found_years` and the rate is null rather than extrapolated from
too little. Unwrapping shifts a step that exceeds half an Egyptian year, and an
exact half-year step keeps its sign rather than being silently resolved one
way. The response states all of this in its own fields — method, missing-year
policy, wrap policy, half-cycle tie policy and engine entrypoint — so a caller
reads the doctrine rather than inferring it.

## Performance

Python only; no native port was made. Measured with Python 3.14.8 against DE441
and the installed small-body releases:

- 60-day scan across the Sun, Moon and eight planets: **1.58 s** total,
  2,804 declination evaluations.
- 10-year scans: Zoozve 5.09 s, Eros 4.58 s, Hathor 4.26 s, Orpheus 3.61 s,
  Ceres 3.44 s, 2P/Encke 2.73 s, 1P/Halley 1.37 s.

Time is dominated by apparent-place evaluation, so the solver's own arithmetic
is not the cost. The scan doctrine is what keeps the evaluation count low.

## A bounded search behind the route

Search cost is linear in the requested span: measured at roughly 3,800
declination evaluations and 2.4 seconds per year of lunar scan, so a
century-long request is minutes of work and a millennium is most of an hour.
`OutOfBoundsPolicy.max_declination_evaluations` bounds it. The engine defaults
to no ceiling, because a library caller may legitimately scan centuries;
`POST /v1/out-of-bounds/search` always imposes one of 100,000 evaluations and
accepts a smaller request but not a larger one.

An exhausted budget raises `OutOfBoundsBudgetError`, or returns HTTP 422 with
`out_of_bounds_search_budget` and category `search_budget`. It never returns
the excursions the search happened to reach first: a truncated list cannot be
told apart from a genuinely quiet interval.

## Validation

The solver is checked against independently derived witnesses, not against
itself:

- Every solved crossing is a root of a declination built by a separate route —
  the equatorial Cartesian product for planets and points, an explicit vector
  rotation of the apparent ecliptic place for small bodies — to within
  0.05 arcseconds on the bound function.
- Reported declination rates match finite differences of that witness to 1 per
  cent.
- Thirteen brute-force comparisons against a fine grid (0.002 to 0.05 day)
  agree on every excursion count and edge, across the Moon, Mercury, Venus,
  Pluto, Ceres, Eros, 2P/Encke, Zoozve, Orpheus and Hathor.
- Structural invariants are asserted directly: hemisphere constancy within an
  excursion, bracket containment, ordering and disjointness, and that an
  unclipped excursion culminates strictly inside itself.

Comet topocentric places are validated differently, because an authority does
govern that product: an independent ERFA reduction agrees to better than
**2e-5 arcsecond** of separation for 1P/Halley at a topocentric site, with an
analytic linear-comet light-time check alongside it. The Sothic drift rate is
checked against the DE441 annual rising series and the engine slope. Because
`_sky_position_at_impl` is a shared service, its dependent suites were run too
— astrocartography, physical horizon, local space, rise/set, frame positions
and the rendering adapter.

For the out-of-bounds solver, no agreement with an external engine or published
out-of-bounds table is claimed. No external authority publishes this product — apparent geocentric
declination of date against the true obliquity of date — under matching
semantics, so the evidence here is invariant testing and independent-scan
corroboration, and the tests say so.

The capture guarantee is relative to a measured, declared rate bound, not a
proven Lipschitz constant. `scan_truth.unresolved_intervals` discloses any
interval that reached the subdivision limit without clearing. A tangential
contact, where the bound function touches zero without changing sign, is
deliberately not reported as an entry or return.
