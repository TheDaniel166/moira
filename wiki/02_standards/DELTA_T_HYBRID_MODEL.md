# Moira — Delta T Source-Priority and Scenario Policy

**Version:** 3.2

**Date:** 2026-07-17

**Status:** Implemented bounded policy; validation scope stated below

**Surfaces:** `moira.julian.delta_t` · `moira.delta_t_physical.delta_t_hybrid`

---

## 1. Governing product

Delta T is the total time-scale difference

```text
Delta T = TT - UT1
```

in seconds. The public product is a total. A total Earth-rotation observation
does not identify how much arose from the core, atmosphere, oceans,
cryosphere, mantle, tides, or any other cause.

Moira therefore applies two rules:

1. **Source totals govern where an admitted source exists.**
2. **Forecast policy remains visibly separate from source-backed history.**

The model is deterministic and file-backed. It performs no network access and
does not silently replace a missing admitted source with a weaker causal
proxy.

## 2. Domain and source priority

The explicit physical-policy surface is admitted from decimal year `-2000.0`.
Requests below that HPIERS table domain raise `ValueError`; they are not
silently clamped to the first table row. The generic `moira.julian.delta_t()`
surface is broader and keeps its earlier-era extrapolation visible.

| Era | Mean policy | Evidence class |
|---|---|---|
| Earlier than `-2100` on generic `delta_t()` only | Morrison-Stephenson/NASA-lineage polynomial and historical anchors on their declared source basis | Explicit extrapolation outside the physical surface |
| `-2100` to `-2000` on generic `delta_t()` only | One explicit linear 100-year C0 bridge from the earlier polynomial value to the first HPIERS row | Declared source-floor reconciliation; not an observation |
| `-2000` through the final distinct HPIERS knot before the aggregate table | Stephenson-Morrison-Hohenkerk/HPIERS mean through `moira.julian.delta_t()` | Published historical reconstruction on its raw DE430/LE430 source basis |
| Final HPIERS knot to first aggregate representative epoch (currently `2015.0` to about `2015.456`) | One explicit linear C0 source bridge | Declared source-reconciliation policy |
| Modern aggregate entries through their final representative epoch (currently about `2026.123`) | Higher-priority `moira.julian.delta_t()` aggregate totals | Full-year and Jan–Apr means are materialized at the mean epoch of their first-of-month USNO samples, not at integer product labels |
| After the final aggregate epoch through `2150` | Boundary-anchored scenario defined in section 3 | Explicit extrapolation policy |
| After `2150` | Same mathematical scenario continued | Scenario extrapolation only; not an authority-validated forecast |

HPIERS states that its 1950–2016 values are half-yearly, while the authority's
HTML DATE display rounds those epochs to integers. The packaged artifact
restores the declared `0.5`-year ordinal cadence before interpolation and
loader parity is tested against it. HPIERS states that those values belong with DE430/LE430 and its
lunar tidal acceleration of `-25.85 arcsec/cy²`. Generic Delta T is a clock
product and cannot infer which ephemeris a downstream caller will use.
Consequently, `delta_t()` preserves the HPIERS source basis and performs no
ambient retargeting to DE441.

Moira retains the published source-to-target arithmetic as an explicit private
helper:

```text
c = -0.91072 * (n_DE441 - n_source) * ((year - 1955) / 100)^2
Delta T_target = Delta T_source + c
```

That helper is not called by generic `delta_t()`. A target-aware computation
may use it only after establishing both the source product and target ephemeris
identity. Moira's reader-backed SPK paths now establish that identity from the
opened kernel's coherent DAF summary labels, never from its filename. The
admitted mappings are DE430/LE430 at `-25.85 arcsec/cy^2` and DE441/LE441 at
`-25.936 arcsec/cy^2`. Historical declared-basis composition fails closed for
an unmapped or conflicting kernel identity; direct EOP and aggregate-era clock
products remain numerically unchanged. NASA-canon comparison remains separately owned by
`delta_t_nasa_canon()`, including NASA's published month-midpoint decimal-year
convention and its own limited lunar-correction regime.

`DeltaTPolicy(model="hybrid")` remains the default layered time policy.
`DeltaTPolicy(model="physical")` exposes this bounded source-priority/scenario
surface explicitly. The word *physical* in the compatibility name does not
claim that historical totals have been causally decomposed.

## 3. Future mean scenario

Let the final two aggregate representative epochs define a boundary vessel

```text
Y0 = final aggregate representative epoch # currently about 2026.123
D0 = final aggregate Delta T
m0 = slope of the final two epochs         # provisional seconds per year
h  = year - Y0                           # years after the handoff
```

The post-handoff mean is

```text
Delta T scenario(year) = D0 + m0*h + 28*(h/100)^2
```

The construction preserves both the admitted value and the provisional
aggregate-epoch slope at the handoff. The current final product is a Jan–Apr
2026 partial mean, so `m0` is explicit scenario policy rather than an observed instantaneous
derivative. The `28 s/cy²` curvature is the declared sum of a
`+31 s/cy²` tidal term and a `-3 s/cy²` GIA term. It is forecast doctrine, not
an observation and not a fitted decomposition of the historical source total.

The scenario is useful for deterministic future computation, but Earth
rotation remains unpredictable. No value after the current final aggregate epoch is
described as observed merely because it is produced by the scenario.
No value after 2150 is described as a validated forecast.

## 4. Compatibility breakdown

`DeltaTBreakdown` remains a stable public vessel:

```text
year, total, secular, core, cryo, fluid, bridge, residual, era
```

Its fields obey

```text
secular + core + cryo + fluid + bridge + residual == total
```

The historical field names do not override source truth:

- `total` is the admitted source total or future scenario mean.
- `secular` is the declared curvature baseline. It must not be read as a
  measured causal tidal/GIA component during the source-backed eras.
- `core`, `cryo`, `fluid`, and `residual` are preserved for compatibility and
  are zero while their candidate datasets are quarantined.
- `bridge` is the explicit reconciliation between the declared curvature
  baseline and the admitted total. In the future it carries the boundary value
  and slope terms. It is arithmetic accounting, not a fitted physical cause.
- `era` retains the compatibility categories `pre-1840`, `historical`,
  `measured`, and `future`. These labels are not source-row provenance; in
  particular, the legacy word `measured` does not certify every admitted row
  as a definitive observation.

The helper functions `core_delta_t()`, `cryo_delta_t()`, and
`fluid_lowfreq()` likewise remain callable but return zero. This is deliberate
quarantine, not missing-data fallback.

## 5. Why the proxy components are quarantined

### IERS C04 annual LOD

`moira/data/core_angular_momentum.txt` contains annual means of **total** IERS
EOP C04 LOD. It is not a published core-angular-momentum inversion and cannot
lawfully be labelled as a core-only contribution. It remains packaged for
research reproducibility but is not consumed by the admitted mean.

### GRACE/GRACE-FO derivative

`moira/data/grace_lod_contribution.txt` is a historical derived artifact. Its
generator divided integrated milliseconds by `86400` instead of `1000`, an
exact factor-of-86.4 unit defect. Correcting that divisor would still not prove
the candidate C20-to-inertia-to-LOD derivation or a cryosphere-only
attribution. The artifact is therefore retained unchanged except for its
quarantine header and is not consumed at runtime.

### AAM and OAM proxies

The packaged AAM and OAM series use different source quantities and units.
Regression coefficients cannot turn them into independently identified causal
Delta-T components. They remain diagnostic research data only.

Admission of any future component requires all of the following together:

- a named governing physical object and primary source;
- compatible units and an explicit derivation into Delta-T seconds;
- a declared integration constant and boundary policy;
- provenance, coverage, uncertainty, and transformation metadata;
- tests against source-owned fixtures and independently derived invariants.

## 6. Uncertainty

`delta_t_hybrid_uncertainty(year)` returns a scale in seconds:

- while HPIERS owns the mean it uses the table's quoted error column;
- from the explicit source bridge through the final aggregate epoch it uses a
  `0.06 s` modern policy scale, covering the verified `0.052808 s` maximum
  daily residual against the bundled EOP snapshot; the aggregate table carries
  no row-level errors;
- after the final aggregate epoch it uses the arithmetic policy sum below, not
  quadrature.

For `h = year - Y0 > 0`, `q = h / 100`, and `theta = 0.1 / year`:

```text
sigma(year) = 0.06 s
            + abs(31 s/cy²) * (0.003 / 25.858) * q²
            + 0.5 s/cy² * q²
            + sigma_OU(h)

z = theta*h
u = 1 - exp(-z)
B = 2*z - 2*u - u²

sigma_OU(h) = (365.25 days/year / 1000 ms/s)
              * (0.2379 ms/day/sqrt(year))
              * sqrt(B / (2*theta³))
```

The implementation evaluates the small-`z` limit with a series expansion to
avoid cancellation. The O-U term is conditional on the declared
`theta = 0.1/year` and diffusion scale. Those future coefficients do not have
a complete traceable calibration record in the module. The handoff value's
source error and the uncertainty of the final-row slope are not propagated.
Accordingly, the result is explicitly an **uncalibrated policy scale**: it has
no asserted 68-percent or other coverage probability and is not a proof of
independent causal errors. The stable field name `sigma` is compatibility
vocabulary, not a calibration claim.

These values are not assembled by treating the quarantined causal proxies as
independent random variables. `DeltaTDistribution` exposes a normal
approximation (`year`, `mean`, `sigma`) as a convenient computational vessel,
but normal tails are not claimed as observed Earth-rotation statistics. Its
`pdf()` and `interval()` methods are mathematical conveniences around the
caller-visible scale, not validated probability products.

## 7. Time-scale coherence

For a UTC instant with admitted EOP data, chart and transport metadata satisfy

```text
delta_t_seconds = (jd_tt - jd_ut1) * 86400
```

The same TT/UT1 relation governs the planetary calculation for that chart.
`jd_tt`, `jd_ut1`, chart `delta_t`, and REST reduction metadata must therefore
describe one clock path rather than mixing an atomic UTC-to-TT conversion with
a separate annual forecast.

The bundled EOP record owns its admitted rows' UTC days. The packaged
transformation did not retain the source observed/predicted flag, so those rows
must not all be called measured or definitive observations. At each outer
coverage boundary, the difference between the EOP value and the year model is
fully applied for C0 continuity, then smoothly tapers to zero over one Julian
year. It is never propagated as a constant correction into remote epochs.
Across an internal EOP gap, only the two admitted boundary corrections are
interpolated; the gap is not relabelled as observed. TT-to-UT1 conversion in an
EOP segment is inverted directly in TT coordinates; outside coverage it solves
the same continuous model surface iteratively.

Hybrid and physical JD transforms evaluate that year model on a private exact
proleptic-Gregorian coordinate: the elapsed fraction between consecutive
January 1 boundaries. This avoids the monthly steps and possible
non-injectivity that would result from using the public NASA-compatible
month-midpoint helper. `decimal_year()` and `decimal_year_from_jd()` retain the
NASA convention deliberately. No-hint NASA-canon TT/UT1 transforms use the
same continuous coordinate as the other JD transforms, while catalog
compatibility paths pass the published month-midpoint coordinate explicitly.
The raw NASA polynomial has small piecewise boundary jumps; the no-hint inverse
fails closed for their ambiguous or absent TT intervals rather than selecting
a silent branch.

The packaged leap-second authority begins on `1972-01-01`. The lower-level
`tai_minus_utc()` and `utc_to_tai()` helpers separately implement the IAU SOFA
`iauDat` offset-and-drift segments from `1960-01-01` through `1971-12-31`, then
the IERS Bulletin C steps. They reject earlier atomic conversion instead of
inventing a flat `TAI-UTC = 10 s` history.

That atomic-helper authority does not silently redefine the engine's
historical civil-input convention. Before the final civil day of 1971, a
timezone-normalized civil JD retains the established UT1-proxy interpretation,
and TT is obtained from that same UT1 coordinate with the admitted Delta-T
model. Over that final civil day, a monotonic smoothstep joins the proxy rule
to the first atomic result. This removes the overlap that a hard switch would
create; the private inverse solves the same handoff by bisection. This is
explicit clock policy, not a reconstruction of pre-1960 UTC.

Private UT1-to-UTC display/serialization plumbing is also leap-safe inside EOP
coverage. It inverts the within-day UT1-TAI affine relation and then applies
the TAI-UTC offset effective at the civil instant. It does not map a full
86401-second UT1 segment onto a 86400-second UTC-coded day and therefore does
not smear a positive leap across the preceding day. This helper changes no
facade signature or REST schema.

No facade method name, chart request model, chart response field, or `/v1`
route path is changed by this coherence rule.

## 8. Data integrity and provenance

`moira/data/delta_t_manifest.json` records, for each packaged Delta-T or
Earth-rotation artifact:

- source URL and computational product;
- units and transformation lineage;
- retrieval timestamp when known;
- row count and coverage;
- SHA-256 checksum;
- admitted or quarantined runtime status;
- known semantic caveats.

Loaders reject non-finite, malformed, unordered, or otherwise invalid admitted
data. The required HPIERS authority table fails closed when absent. For clock
conversion, a wholly absent EOP file retains the documented year-model
fallback; a present but malformed EOP file raises before any partial rows are
cached. Quarantined artifacts are never activated merely because their files
are present.

Generic Delta-T computation accepts finite years only in
`[-100000, +100000]`; the source-bounded physical surface additionally rejects
years below `-2000`. JD-aware time transforms accept finite JDs only in
`[-40000000, +40000000]`. These limits are computational representability
guards chosen for binary64 behavior, not scientific-validity, source-coverage,
or forecast-confidence claims.

The human-readable source and licensing account is in `PROVENANCE.md`.

## 9. Validation posture

The relevant evidence classes remain separate:

- source-table tests prove exact selection and interpolation of admitted rows;
- time-scale invariants prove TT/UT1/Delta-T coherence;
- boundary tests prove value and slope continuity at the source-owned final
  aggregate representative epoch, including synthetic source extension and contraction;
- EOP tests prove C0 first/last/gap handoffs, one-Julian-year outer tapers,
  direct TT-to-UT1 inversion, and leap-day-safe private UTC formatting;
- historical civil-clock tests prove the pre-1972 UT1-proxy policy and the
  monotonic final-day atomic UTC handoff at 1972-01-01, including its inverse;
- domain and non-finite tests prove explicit failure behavior;
- component-zero tests prove quarantined artifacts cannot affect the mean;
- future tests prove the declared scenario formula, not future astronomical
  truth.

Python/native agreement is not external Delta-T validation. Regression against
Moira's own `delta_t()` is not an independent IERS oracle. Forecast values are
not promoted to observations by passing deterministic tests.

## 10. Maintenance rule

When a new source total becomes admissible:

1. preserve the source product, status, epoch, units, and uncertainty;
2. update the packaged artifact and manifest together;
3. extend the source-priority boundary only through admitted coverage;
4. let the boundary vessel derive `Y0`, `D0`, and `m0` directly from the final
   two rows; do not add a second literal handoff year;
5. rerun source, seam, time-scale, facade, and REST tests;
6. update numerical validation artifacts whose baseline Delta-T changed.

Do not tune the scenario curvature to hide a source discrepancy. Diagnose
inputs, time scales, source status, and boundary semantics first.

## 11. Primary references

- Stephenson, F. R., Morrison, L. V., and Hohenkerk, C. Y. (2016),
  *Measurement of the Earth's rotation: 720 BC to AD 2015*.
- IERS/HPIERS, *TT-UT and Earth rotation rate from 2000 BC to 2016 AD*,
  including the DE430/LE430 `-25.85 arcsec/cy²` product basis.
- NASA GSFC, *Secular Acceleration of the Moon*, for the sign and scale of an
  explicitly requested source-to-lunar-ephemeris Delta-T correction and for
  the separate NASA-canon policy.
- JPL Horizons release history, version 4.80, for the DE441
  `-25.936 arcsec/cy²` lunar tidal deceleration basis. This identifies a
  possible explicit target; it is not ambiently applied to generic Delta T.
- IAU SOFA `iauDat`, for the 1960-1971 UTC offset-and-drift segments used by
  the bounded UTC-to-TAI helper before the IERS leap-second era.
- IERS Earth Orientation Parameters C04 and `finals2000A` products.
- NASA/JPL PO.DAAC GRACE-FO documentation for TN-14 C20/C30 replacement data.
- Caron et al. (2018), DOI `10.1002/2017GL076644`, for GIA model context.

These references govern their named products only. None independently proves
the quarantined causal decomposition.
