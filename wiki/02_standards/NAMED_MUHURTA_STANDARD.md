# Named Muhurta interval admission

**Date:** 8 October 2026. **Scope:** VED-007 Abhijit and Brahma, with scoped
VED-021/022 evidence and documentation. The existing-helper integration is
complete locally. Additional named windows retain individual source gates.

## Governing object and sources

`moira.named_muhurta` computes two time intervals, their solar anchors,
numerical endpoint bounds and selected-rule eligibility. It supplies no
generic score or complete activity judgement. Source identity, inspected
pages, hashes, competing readings and the local-library search limits are
in the [source decision](../06_roadmap/VEDIC_NAMED_MUHURTA_SOURCE_AND_PLAN_2026-10-08.md).

| Policy | Executing reading and attribution |
| --- | --- |
| `chintamani_eighth_daylight_part` | Fixed Abhijit geometry. Daivajna Rama, *Muhurta Chintamani*, Avasthi commentary, tenth edition 2004, Vivaha 52, printed p.126: the eighth of fifteen equal divisions of actual daylight. |
| `chintamani_wednesday_exclusion` | Default eligibility rule, from Vivaha 54, printed p.127. Wednesday is `excluded`; the other six weekdays are `not_excluded_by_selected_rule`. This ritual/marriage-context rule is not a full marriage judgement or universal auspiciousness claim. |
| `geometry_only` | Caller explicitly declines weekday-rule evaluation. Eligibility is `not_evaluated`, while Abhijit geometry is identical. |
| `arunadatta_fixed_ghati` | Default Brahma reading: Arunadatta's *Sarvangasundara* on *Ashtanga Hridaya*, Sutrasthana 2.1. Four ghatis remaining in all seasons supplies the beginning; one muhurta is two ghatis. Compute 96 to 48 minutes before sunrise. The exact timing is commentarial, not a formula quoted from the base verse. |
| `legacy_proportional_night_14` | Explicit compatibility with Moira's existing Brahma predicate: the fourteenth of fifteen equal divisions of the preceding night. It equals 96-to-48 minutes only for a twelve-hour night. Hemadri's shorter penultimate-muhurta gloss does not independently settle seasonal scaling; this profile is not attributed to Arunadatta. |

Brahma eligibility is always `not_evaluated`. The product does not evaluate
health effects, meditative outcomes, doshas, cancellations or purpose rules.
The reported daylight midpoint is not identified with actual solar meridian
transit. Abhijit Muhurta and Abhijit Nakshatra are distinct objects.

## Arithmetic and endpoint ownership

Let `R` be sunrise, `S` the following sunset and `P` the previous sunset,
all UT1 Julian days. Intervals are half-open `[start,end)`:

| Window | Start | End |
| --- | --- | --- |
| Abhijit | `R + 7*(S-R)/15` | `R + 8*(S-R)/15` |
| Fixed-ghati Brahma | `R - 4/60` | `R - 2/60` |
| Proportional-night Brahma | `P + 13*(R-P)/15` | `P + 14*(R-P)/15` |

The engine evaluates the rational affine expressions on the exact supplied
binary64 values and rounds each endpoint once. Direct anchors are treated as
exact caller inputs; their astronomical accuracy is caller-owned. Dated
anchors retain root brackets. Their lower/upper bounds propagate monotonically
through each expression, with outward floating-point rounding.

`interval.contains(jd_ut1)` reports geometric membership: `True` in the
resolved interior, `False` outside all possible endpoints, and `None` when
the interval is unavailable or the query falls within endpoint uncertainty.
Wednesday exclusion remains a separate field and does not erase geometry.
Root brackets measure numerical resolution, not uncertainty in refraction,
terrain, atmospheric conditions, Earth orientation or the source tradition.

## Python ownership and strict inputs

Root `moira`, `moira.facade` and `moira.vedic` share the seven objects owned
by `moira.named_muhurta`: `NamedMuhurtaPolicy`, `NamedMuhurtaAnchor`,
`NamedMuhurtaInterval`, `NamedMuhurtaResult`, `NamedMuhurtaDay`,
`named_muhurta_from_solar_times` and `named_muhurta_for_date`. The `Moira`
facade supplies both functions as methods.

The supplied-anchor API requires finite representable `sunrise_jd_ut1` and
an explicit integer `weekday` from Monday=0 to Sunday=6. This is **not** the
Sunday-first Vara index used elsewhere. Optional `sunset_jd_ut1` must follow
sunrise; optional `previous_sunset_jd_ut1` must precede it. No numeric strings,
booleans, nonfinite numbers or silently reordered anchors are admitted.
`solar_policy_applied=False` records that no horizon/solver policy was used.

The dated API requires a Gregorian `date` (year 2 through 9998), latitude
strictly between -90 and +90 degrees, east-positive longitude in [-180,180],
and an explicit IANA timezone, `UTC` or `UTC+/-HH:MM`. It does not infer a
timezone from coordinates. It evaluates the previous, requested and following
civil dates using the existing daily-Panchanga solar discovery. Skipped
dates within the required civil-boundary scope reject before reader access.
There is no search for a distant seasonal sunrise.

The requested local sunrise date owns both intervals and the weekday rule.
Brahma can start on the preceding civil date; its display is not clipped at
midnight. DST changes affect civil displays and civil-date durations, while
interval arithmetic remains UT1. Multiple requested-date sunrises are
ambiguous. A refined sunrise bracket must lie wholly inside that civil date.

## Horizon, clock and resource policy

The three existing `PanchangaSunriseDefinition` choices are admitted:
`rashtriya_upper_limb` (default, -47/60 degrees), `usno_upper_limb`
(-50/60 degrees), and `geometric_center` (0 degrees).
The same selected altitude threshold defines sunrise and sunset. This uses
the existing level-horizon, zero-elevation solar signal, without terrain or
caller-adjustable atmospheric inputs. Local bisection refines discovered
crossings; `solver_tolerance_seconds` is finite in [0.01,1], default 0.1.
Refinement searches at most sixty seconds either side of each coarse witness.
It never silently substitutes a different sunrise model.

The facade borrows its reader. The standalone dated function borrows an
explicit `reader=`, or uses the active reader context when omitted. It does
not discover/open a fresh reader outside a context. Every path restores the
previous override and leaves reader closure to its owner.

`NamedMuhurtaDay` retains the three civil-date solar witnesses, refined
anchors and endpoint civil moments. Its `clock_*`, Delta-T and kernel-label
receipt is sampled at the requested civil date's midpoint; it is not a
separate clock receipt for every root. Underlying solar evaluations use the
existing reader-bound time machinery. Endpoint `utc` and `local` displays
are converted from UT1 through the established civil-time conversion.

Availability is per window: Abhijit needs sunrise and following sunset;
fixed Brahma needs only sunrise; legacy Brahma also needs previous sunset.
Absent, multiple, unresolved or ambiguously owned events produce explicit
reasons and null endpoints. The aggregate is `available`, `partial` or
`unavailable`. Missing resources and coverage failures remain exceptions,
not invented polar outcomes.

## REST contract

| Route | Canonical product |
| --- | --- |
| `POST /v1/muhurta/named/direct` | Supplied UT1 anchors and Monday-first weekday -> `NamedMuhurtaResult` |
| `POST /v1/muhurta/named/day` | Civil date, location, timezone and startup engine reader -> `NamedMuhurtaDay` |

Both accept a typed `policy` object with the two selectable Brahma readings,
two weekday modes, three sunrise definitions and bounded solver tolerance.
Unknown fields and values reject. Date strings must be canonical
`YYYY-MM-DD`; Unix timestamps, compact dates and datetime strings reject.
Preflight runs before astronomy. Responses project canonical dataclasses;
the server contains no interval or eligibility arithmetic.

Unavailable astronomy returns HTTP 200 with typed status, reasons and nulls.
Invalid requests use the existing 422 `validation_error` envelope. Existing
`MuhurtaCoverageError` maps to 422 `muhurta_date_outside_coverage` and
`MuhurtaResourceError` to 503 `muhurta_resource_unavailable`. Request IDs are
preserved. The operation is synchronous and bounded to three civil dates.

## Compatibility and completion boundary

The legacy `is_abhijit_muhurta` and `is_brahma_muhurta` boolean arithmetic
remains unchanged. Their documentation now distinguishes source-owned
intervals and the proportional-night compatibility reading. The new default
fixed-ghati Brahma policy does not silently change legacy callers.
The compatibility profile retains the legacy proportional-night formula;
its rational single-round endpoints are the canonical new-product boundary,
not a promise of bitwise equality with the legacy chained-float predicate.

This admission does not integrate named windows into generic scoring,
sampled search, natal overlays or activity guidance. Godhuli, Vijaya, Amrita,
Ravi Yoga and Sarvarthasiddhi remain separately sourced additions in VED-007;
VED-008–011 own their other families. See the
[execution receipt](../03_validation/NAMED_MUHURTA_VALIDATION_2026-10-08.md)
for exact test evidence, limits and publication state.
