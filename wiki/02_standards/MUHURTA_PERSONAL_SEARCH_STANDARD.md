# Personalized Muhurta policy and sampled search

Date: 6 October 2026. Scope: VED-004 and VED-006, with the directly affected
Panchanga/Muhurta numeric boundary from VED-005. Source presence, local
verification, Git publication, release and deployment are separate states.

## Governing object and source boundary

The product is the existing Moira Panchanga score, optionally overlaid with
Tara Bala and Chandra Bala from one supplied natal sidereal Moon longitude.
Search evaluates that product on a finite, closed UT1 grid and ranks consecutive
threshold-qualified sample runs. It does not solve continuous auspicious periods.

`MuhurtaPolicy.rule_profile` identifies
`moira.muhurta.existing_weighted_profile.v1`. The existing generic classification
tables and nine-Tara/basic Chandra rules in `moira/muhurta.py` are retained.
Seven numerical weights, the generic score coefficients and the doubled
Chandrashtama penalty are the existing Moira scoring policy. They are not
probabilities, independently source-validated measures of strength, or textual
authority for universally selecting a time.

This package repairs composition and transport. It adds no new classical rule,
source edition, activity profile, neutralization, Tara-cycle/paryaya doctrine or
paksha-dependent Chandra variant. The historical source leads in the Muhurta
module and paused tracker are not new edition-collation evidence. VED-007–011
retain their own source admission gates. Neither external-engine corroboration
nor predictive validity is established by the tests in this package.

## Policy and failures

The seven finite, nonnegative weights are `weight_tithi`, `weight_vara`,
`weight_nakshatra`, `weight_yoga`, `weight_karana`, `weight_tara`, and
`weight_chandra`. Defaults remain 1, 1, 1, 1.5, 0.8, 1, 1. Zero is lawful.
Engine and REST reject booleans, numeric strings, nonfinite values and weight
combinations whose worst component magnitudes could overflow aggregation.

`use_classical_ashubha_yoga` remains a reserved compatibility field, fixed to
`True`. The engine rejects other values; REST does not accept it as a selector.
There is no silently acknowledged alternate rule set. Receipts report the fixed
rule profile, all seven weights, configurable/exposed fields, fields actually
applied to this product, and reserved/omitted fields. Generic scores apply five
weights, personal scores seven, and classification labels apply no score weights.
`janma_nakshatra` and `activity` are not invented policy dataclass fields.

Public Tara indices are integers in [0, 26]. Natal/transit Moon longitudes are
finite numbers, normalized circularly by the existing evaluator. The direct
personal API continues to accept a supplied natal sidereal Moon; it does not
derive birth positions or verify the caller's natal ayanamsa. Its base and
overlays use the same effective transit ayanamsa, including nested Panchanga
policy precedence. The returned canonical transit longitude preserves the
existing whole-sign boundary semantics before Nakshatra's sector recovery.

Panchanga and Muhurta direct/chart numeric request fields now reject coercion.
Chart requests require aware civil datetime strings, rejecting numeric Unix
timestamps and naive datetimes. Existing finite numeric degrees remain circular
inputs; this does not add a new [0, 360) restriction to the supplied-position API.

## Engine and facade

`moira.muhurta_search` owns eight curated exports, shared by root, `facade` and
`vedic`: `MuhurtaSearchPolicy`, `MuhurtaMomentScore`, `MuhurtaSearchWindow`,
`MuhurtaSearchResult`, `MuhurtaResourceError`, `MuhurtaCoverageError`,
`muhurta_score_for_chart`, and `find_muhurta_windows`.

```python
from moira import Moira, MuhurtaPolicy, MuhurtaSearchPolicy

engine = Moira()  # requires a discovered planetary kernel
result = engine.find_muhurta_windows(
    2461319.5, 2461320.5,  # explicitly UT1 Julian days
    janma_moon_sidereal_lon=100.0,
    policy=MuhurtaSearchPolicy(
        ayanamsa_system="Raman", step_days=1 / 24, min_score=0.0,
        muhurta_policy=MuhurtaPolicy(weight_tara=2.0, weight_chandra=3.0),
    ),
)
for window in result.windows:
    print(window.qualifying_jds, window.peak.jd_ut1, window.peak.score.total)
```

Standalone search accepts `reader=`; `Moira.find_muhurta_windows` binds
`self._reader` across all samples and live anchor evaluation. UT1 is bound to
the serving reader's TT/TDB clock and DE/LE content identity at every sample.
Apparent geocentric Sun and Moon longitudes use true ecliptic of date with light
time, aberration, gravitational deflection and nutation. All 12 named ayanamsas
are admitted in true mode. A missing live anchor never becomes a polynomial
fallback. Moment receipts retain UT1, TT, TDB, Delta-T source, serving identity,
tropical longitudes, offset, Panchanga, policy and complete score components.

`muhurta_score_for_chart` requires actual Sun/Moon longitudes and a declared
chart clock. `ChartContext` supplies explicit UT1 `jd_ut` and `jd_tt`. The public
facade `Chart` is recognized by its owning type: its civil-UTC `jd_ut` is
converted once to UT1 and its retained Delta-T supplies TT. The receipt echoes
`input_time_basis`; a missing clock is never inferred from a default. Both chart
epochs must be within the admitted JD range. The caller owns the supplied
chart's position origin/frame and astronomical truth.
It also unwraps `ElectionalEvaluation.chart` instead of subtracting a sidereal
offset twice. No missing longitude/date becomes zero; no invalid chart becomes
`-999`. The facade binds its reader for live anchors. Supplied chart receipts
are labelled `caller_supplied_chart`; they do not invent TDB/kernel evidence.

`muhurta_scorer` is a scalar adapter over the same evaluator. A legacy natal
Nakshatra name can corroborate the supplied natal Moon, but cannot manufacture
a natal sign: name-only and contradictory inputs reject explicitly.

`find_best_muhurta_windows` preserves its list of `(ElectionalWindow, score)`
tuples by delegating to the typed search. Its legacy coordinates are validated,
but this geocentric/JD-weekday product uses no location, houses or Lagna factor.
ElectionalPolicy supplies cadence and an optional result cap. Nonconsecutive
merge gaps, boundary refinement, conflicting sidereal settings and body subsets
other than Sun/Moon reject. No Western electional judgment is imported. The
typed result should be used when peak, bracket or truncation evidence is needed.

## Sampling, limits and interpretation

- Search endpoints are closed samples. The start and end are retained exactly
  once; cadence is integer-indexed, with a final shorter step when needed.
- The JD interval must be ordered within [-10000000, 10000000] and span at most
  30 days. Cadence is between one minute and 30 days, with at most 4096 samples.
  These operational limits are validated before resource access.
- The default cadence is hourly, threshold 0, and result cap 32. The cap is a
  strict integer in [1, 128]. Every requested sample is evaluated before ranking
  and result truncation; a cap does not stop early and miss later peaks.
- Every retained sample in a run meets `total >= min_score`. Any rejected sample
  splits runs, regardless of a legacy merge-gap setting. A singleton is valid
  and has zero sampled span. No continuity between grid points is asserted.
- A window retains its qualifying moments, the earliest highest-scored moment,
  and adjacent rejected-sample JDs. Missing adjacent brackets indicate a request
  edge. Brackets are not refined transition times.
- Runs rank by descending peak score, then earlier peak time and earlier start.
  The result retains the complete sample grid, qualifying-sample count, total
  observed-run count, returned runs and an explicit truncation flag.
- Vara is `jd_weekday`. This product does not use the VED-015 local sunrise day.
  Sunrise-owned search needs a separate explicit date/zone/location composition;
  polar/missing-sunrise policy cannot be inferred from a geocentric scan.
- Named Muhurtas, purpose guidance, dosha/Parihara additions, Lagna/Navamsha
  strength, precise transitions and guarantees remain outside this admission.

Resource and coverage errors abort the entire scan. They do not become a low
score, a successful empty selection, or a partial result. Reader context is
restored on success and failure. A completed scan with no threshold-qualified
samples is an ordinary empty success.

## REST

The existing four direct/chart routes and `POST /v1/muhurta/personal/score`
remain. Personal-score responses preserve their previous top-level fields and
add actual policy, Panchanga, natal/transit Moon input evidence and provenance.
Direct Vara is JD weekday; existing chart-backed moment Vara is civil UTC
weekday. These distinct conventions are echoed, with local sunrise unadmitted.

`POST /v1/muhurta/search` accepts strict finite `start_jd_ut1`, `end_jd_ut1`,
optional `janma_moon_sidereal_lon`, and a bounded policy:

```json
{
  "start_jd_ut1": 2461319.5,
  "end_jd_ut1": 2461320.5,
  "janma_moon_sidereal_lon": 100.0,
  "policy": {
    "ayanamsa_system": "Raman",
    "step_minutes": 60,
    "min_score": 0,
    "max_results": 32,
    "muhurta_policy": {"weight_tara": 2, "weight_chandra": 3}
  }
}
```

The response preserves canonical engine window order, all qualifying JDs,
peak clock/position/Panchanga/score evidence, adjacent brackets, effective
policy and counts. Natal omission is explicit and generic peak Tara/Chandra
fields are null. The server does not recompute score, ranking or boundaries.
It reports all search limits and excluded products. GET is not admitted.

Invalid requests return the usual structured 422 validation envelope. Serving
coverage returns 422 `muhurta_date_outside_coverage`; required resources return
503 `muhurta_resource_unavailable`. Request IDs are preserved. The new route is
in the classical-vedic discovery family; OpenAPI exposes the 12 named systems,
numeric and cap bounds, extra-field rejection and typed result vessels.

See the [local validation receipt](../03_validation/MUHURTA_PERSONAL_SEARCH_VALIDATION_2026-10-06.md).
