# Named Muhurta interval admission

**Date:** 8 October 2026. **Scope:** VED-007's seven named families, with
source-selected alternatives and scoped VED-021/022 evidence/documentation.
Abhijit/Brahma's published interfaces remain stable. The five additions are
owned by `moira.special_muhurta`; their contract follows below.

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
sampled search, natal overlays or activity guidance. VED-008–011 own their
other families. The original two-window
[execution receipt](../03_validation/NAMED_MUHURTA_VALIDATION_2026-10-08.md)
retains its exact evidence and publication state; the five-name extension has
its own [source packet](../06_roadmap/VEDIC_NAMED_MUHURTA_FIVE_SOURCE_AND_PLAN_2026-10-08.md)
and [execution receipt](../03_validation/SPECIAL_MUHURTA_VALIDATION_2026-10-08.md).

## Five-name extension

`SpecialMuhurtaPolicy` explicitly selects:

| Field | Admitted values and meaning |
| --- | --- |
| `amrita_basis` | Default `sadhana_amrita_siddhi`: seven weekday/nakshatra pairs from Muhurta Sadhana Samjna 78–79. Alternative `kalaprakasika_amirtha`: the larger Kalaprakasika XXXV weekday table. Outputs are distinctly named **Amrita Siddhi** and **Amirtha**. |
| `godhuli_weekday_rule` | Default `vrindavana_visibility`: Thursday requires the fully set Sun, Saturday requires it still visible. Other weekdays are not excluded by this selected rule. `geometry_only` declines this rule. |
| `godhuli_horizon` | Default `standard_refraction_34_arcmin`: centre crossing at −34/60 degrees, upper-limb sunset at −50/60 degrees. `geometric_disc`: centre at 0, upper-limb sunset at −16/60 degrees. Both use fixed 16 arcminute semidiameter, level horizon, zero elevation and no terrain. These are disclosed modern realizations of the textual event, not classical constants or observed atmospheric accuracy. |
| `ayanamsa_system` | Registered engine system, default Lahiri, true mode. Applied to dated geocentric apparent Sun/Moon positions; **not** applied again to supplied sidereal longitudes. |
| `solar_policy` | The full typed `NamedMuhurtaPolicy` above; governs included Abhijit/Brahma, daylight anchors and root tolerance. Its sunrise/sunset definition is independent of Godhuli's disc-event definition. |

The fixed source identities are inspectable in the policy and each result:

* **Vijaya:** eleventh of fifteen daylight parts, from sunrise +10/15 of
  daylight to sunrise +11/15. It is not a fixed 14:00 clock interval or a
  Vijaya Dashami festival calculation.
* **Godhuli:** Vivaha Vrindavana 9.6 with Vasantalakshmi commentary, half a
  ghati either side of the **half-set disc**, hence ±12 elapsed minutes.
  Godhuli's entire geometry remains present. On Thursday/Saturday, verse
  9.5's eligibility partitions it at the separate **upper-limb sunset**.
  A portion is `excluded`, `not_excluded_by_selected_rule`, or
  `not_evaluated`; lack of the visibility anchor yields partial status.
* **Amrita Siddhi / Amirtha:** presence while the Moon occupies a star in the
  selected source table for the sunrise-owned weekday. Kalaprakasika's
  reviewed Sunday table has no Amirtha entry; its Siddha rows are not renamed.
* **Ravi Yoga:** Chintamani Shubhashubha 27, inclusive Moon-star count from
  Sun-star in {4,6,9,10,13,20}. **Both** bodies' transitions can change it.
* **Sarvarthasiddhi:** Chintamani Shubhashubha 28–29's seven weekday tables.

The two Amrita tables, Anandadi Amrita, Choghadiya, Amrita Kalam and Nitya
Yoga are distinct objects. This package implements the first two, under
separate profile names. Source disagreement, especially Chintamani's
season-dependent Godhuli and Moon/Lagna restrictions versus Vrindavana's
reading, is documented rather than silently combined. No output claims
universal auspiciousness or complete marriage/travel/construction suitability;
`activity_suitability` is explicitly `not_evaluated`.

## New engine and REST surfaces

| Engine function / facade method | REST route | Contract |
| --- | --- | --- |
| `special_muhurta_from_solar_times` | `POST /v1/muhurta/special/solar` | Optional sunrise, sunset, half-set and upper-limb-set UT1 anchors; required Monday-first weekday; canonical Vijaya/Godhuli results. Supplied anchors retain caller ownership. Missing anchors yield per-result status. |
| `muhurta_yogas_from_longitudes` | `POST /v1/muhurta/special/yogas` | Required Sun and Moon **sidereal** longitudes in [0,360), plus sunrise weekday; returns all three named presence booleans, star indices/names, inclusive count and source evidence. No reader or coordinate conversion. |
| `special_muhurta_for_date` | `POST /v1/muhurta/special/day` | Civil date/location/timezone with the same admission as the existing named-day route. Returns all five new results plus `named`, the canonical Abhijit/Brahma day, without rebuilding it in transport. |

Eleven owning exports are shared by root, facade and `moira.vedic`. The three
facade methods delegate to the owner. Strict inputs reject booleans as numbers,
strings as numbers, non-finite/out-of-range coordinates, unsupported profiles,
unknown fields, malformed/skipped civil dates and contradictory supplied
anchors before astronomy. Partial/unavailable calculations remain HTTP 200;
resource/coverage errors use the existing named-Muhurta 503/422 envelopes.

### Date ownership, transition cells and uncertainty

The requested local sunrise date owns Vijaya, Godhuli, and the three yoga
families. The yoga interval runs from that sunrise to the following local
date's sunrise. Local midnight does not change its weekday. Discovery stays
within the existing previous/current/following civil dates, with no distant
seasonal substitute. Absence of the next sunrise makes yoga coverage
unavailable but preserves independently computable current-day solar windows.

For yogas, hourly forward-phase bracketing and root bisection find every Sun
and Moon nakshatra crossing in the sunrise day. Each phase step must be
positive and less than half a nakshatra; violations fail visibly. The
stopping tolerance is the policy's 0.01–1 second numerical bracket width,
not a claim about observational or ephemeris accuracy. The bounded day is at
most two elapsed days. No mean-speed interpolation or sampled-score interval
is substituted for a root.

Results contain constant-star **cells**, not merged maximal intervals. Each
cell has start/end nominal UT1, lower/upper brackets, civil displays and the
source evidence establishing presence. `status="available"` with no windows
means no match outside the separately reported numerical uncertainty bands.
It is distinct from unavailable astronomy.

`transition_bands` includes uncertain sunrise ownership and star crossings.
Overlapping Sun/Moon brackets are combined; possible very short occurrences
wholly inside such a band remain unresolved and are not falsely asserted
absent. `SpecialMuhurtaDay.contains_yoga(name, jd_ut1)` returns `None` inside
these bands or when required anchors are missing. Elsewhere it returns
membership in this day's selected yoga. Individual solar/yoga window
`contains` methods likewise retain half-open geometry and endpoint uncertainty;
they do not override a separate eligibility exclusion.

Every dated position and horizon evaluation borrows the same engine reader.
The embedded `named` result preserves the kernel and civil-midpoint clock
receipt; it is not presented as an independent clock measurement for every
transition. Exceptions restore the caller's active-reader context.
