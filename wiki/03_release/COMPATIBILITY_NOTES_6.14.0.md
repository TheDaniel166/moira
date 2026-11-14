# Compatibility Notes - Moira 6.14.0

Python 3.10 through 3.15 are supported. One existing product changes value:
the topocentric apparent place of a comet. Everything else in this release is
additive, and no new dependency is introduced — the base runtime remains the
standard library plus the required compiled `moira._moira_native` extension.

## Topocentric comet positions change value

`sky_position_at()` previously built a geocentric apparent vector for a comet
and shifted it to the observer, leaving the observer's position out of the
light-time solution entirely. Comets now take an observer-centred solve.

- **Recalculate any stored topocentric comet right ascension or declination.**
  The old values carried no parallax, and their diurnal aberration was applied
  about the wrong origin. The error grows as the comet comes nearer, so stored
  close-approach positions are the most affected.
- **Geocentric comet positions are unchanged.** `comet_at()` and
  `planet_at()` return exactly their previous values; the `_comet_kernel()`
  extraction behind them preserves the same kernel search and the same
  `KeyError`.
- **Asteroids are unchanged**, including through `sky_position_at()`. They
  still use the geocentric-apparent vector with a topocentric shift. The
  asteroid path is now the weaker of the two; see the known limitation in the
  release notes.
- **Astrocartography comet lines change** accordingly: right ascension is now
  projected from the selected observer. A comet line request also now requires
  a loaded comet kernel and fails explicitly without one, where it previously
  assumed one was present.

## Nothing else to recalculate

The out-of-bounds solver and Sothic drift fitting are new surfaces and change
no existing result.

## One previously raising path now works

`transits_equatorial._declination` routed small bodies through `asteroid_at`
only, so a comet name fell through to the star resolver and raised
`ValueError`. Small bodies now route through `planets.planet_at`.

- Code that called `find_declination_transits()` or
  `Moira.declination_transits()` with a comet name received an exception. It now
  receives results. Callers that relied on the exception to detect "not an
  asteroid" need a different check; use
  `moira.small_body_identity.resolve_small_body_identity()`, whose
  `identity.family` is `"asteroid"` or `"comet"`.
- Asteroid and planet declinations are unchanged. `planet_at` and `asteroid_at`
  were verified to agree bit-for-bit for the asteroid path, so existing
  declination parallels and contra-parallels keep their values exactly.
- An unqualified small-body name that occurs in both the asteroid and comet
  catalogs now raises `AmbiguousSmallBodyNameError` from the shared identity
  registry on this path, rather than silently resolving to the asteroid. Pass
  `asteroid:Name` or `comet:Name` to be explicit.

## Lunar nodes and apogees are not admitted

`Moira.out_of_bounds()` and `POST /v1/out-of-bounds/search` refuse True Node,
Mean Node, Lilith and True Lilith with an explicit reason. Moira models these as
longitude-only points — `nodes.NodeData` carries no ecliptic latitude — so no
declination exists to compare against the obliquity. A node also lies on the
ecliptic by construction, so its declination magnitude could never exceed the
obliquity, and nothing astrological is lost.

The same four names are now refused by `_declination`, and therefore by
`find_declination_transits()` and `Moira.declination_transits()`, with a named
`ValueError` instead of the previous vague "could not be resolved" message.
They were never computable on that path.

## New public surface

Exported from `moira.facade`:

- `find_out_of_bounds`, and `Moira.out_of_bounds()`
- `OutOfBoundsReport`, `OutOfBoundsExcursion`, `OutOfBoundsCrossing`,
  `OutOfBoundsCulmination`, `OutOfBoundsScanTruth`, `OutOfBoundsPolicy`
- `OutOfBoundsUnavailableError` and `OutOfBoundsBudgetError`, both of which
  subclass `ValueError`

Exported from `moira.sothic`:

- `SothicDriftSample`, `SothicDriftFit`, and `SothicRisingSeries.fit_drift()`

`POST /v1/out-of-bounds/search` is added under the `predictive` tag and
`POST /v1/sothic/drift-rate` under the `sothic` tag, whose tag description
text also changes. `drift-rate` accepts the same request body as
`/v1/sothic/rising`. Three new REST error codes are introduced:
`out_of_bounds_date_outside_ephemeris_coverage` (category
`ephemeris_coverage`), `out_of_bounds_unknown_body` (category
`input_validation`), and `out_of_bounds_search_budget` (category
`search_budget`). All three return HTTP 422. Clients that matched on
`validation_error` for every 422 should treat an unrecognised `error_code` as a
validation failure rather than enumerate the set.

## Semantics worth knowing before you print a result

- A crossing's `achieved_tolerance_days` is the solver's final bracket width,
  not the requested tolerance. Read it rather than assuming the request was met.
- `duration_hours` is a lower bound whenever `duration_is_lower_bound` is true,
  which happens for any excursion clipped by the requested window.
- `time_sensitivity_seconds_per_arcsec` is `-1.0` over REST when the bound rate
  is exactly zero, because the true value is unbounded and JSON cannot carry
  it. `conditioning` is `"degenerate"` in that case. In Python the field is
  `math.inf`.
- A tangential contact, where the bound function touches zero without changing
  sign, is not reported as an entry or return.
- The route caps one search at 100,000 declination evaluations. Cost is linear
  in the span, at roughly 3,800 evaluations per year of lunar scan, so a window
  beyond about 25 years of Moon needs splitting. An exhausted budget raises
  rather than truncating.
- A Sothic drift fit over fewer than five found years returns
  `status: "insufficient_found_years"` with `rate_days_per_year: null`. Treat
  null as "not determinable from this window", not as zero drift.
- `scan_truth.unresolved_intervals` is normally zero. A nonzero value discloses
  intervals that reached the subdivision limit without clearing; it is a stated
  gap in capture, not an error.
