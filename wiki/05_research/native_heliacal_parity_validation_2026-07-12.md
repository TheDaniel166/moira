# Native Fixed-Star Heliacal Parity Validation

Date: 2026-07-12

Boundary hardening: 2026-07-14

Status: admitted native accelerator; Python remains the governing manuscript

## Governing Product

The product is the first observable morning appearance or last observable
morning appearance of a sovereign fixed star under the declared Arcus Visionis
and heliacal search policy. Python owns identity resolution, policy, public
vessels, metadata, and fallback semantics. Native code accelerates the repeated
astronomical observables and bounded daily search.

## Defect Repaired

The former native visibility path called a five-term routine labeled as
truncated IAU 2000B. It was neither the complete standard model nor equivalent
to Moira's authoritative Python path. Native setting also omitted
`setting_elongation_threshold` and `setting_visibility_factor`, rising metadata
reported the setting threshold, signed elongation omitted the Sun's annual
aberration/frame bias, fixed-star evaluators introduced a different geocentric
parallax convention, and one Delta-T value was held over the search.

The replacement:

1. Loads the packaged IERS Table 5.3a/5.3b 2000_R06 coefficients in Python.
2. Publishes one immutable native series snapshot with radians-native results.
3. Uses the shared series in both the public binding and visibility engine.
4. Applies the same fixed-star propagation and apparent solar correction
   semantics used by the Python elongation and altitude products.
5. Carries setting threshold/factor doctrine, rising metadata, and a bounded
   linear Delta-T drift through native search.
6. Keeps coefficient loading lazy and makes raw uninitialized native calls fail
   clearly.

No second coefficient table or new runtime dependency was introduced.

## Boundary Hardening

The admitted accelerator now enforces two additional invariants shared with
the Python manuscript:

1. A forward search never returns or remembers a twilight event earlier than
   `jd_start`. This applies to rising, setting, single-star, and catalog-batch
   searches while preserving the existing civil-day `day_offset` meaning.
2. A native SPK evaluator is bounded by the inclusive coverage in its own DAF
   descriptor. Exact descriptor endpoints remain valid; out-of-range requests
   raise instead of clamping to the first or last Chebyshev record or allowing
   Hermite extrapolation.

Native heliacal dispatch additionally requires one descriptor to cover the
complete TT interval evaluated by the daily search. If that admission test
fails, Python resumes epoch-by-epoch segment selection and raises on a real
coverage gap. The reproduced DE441-end setting search now fails explicitly in
both Python and native-enabled policy modes rather than returning a synthetic
post-coverage event.

`HeliacalSearchPolicy` now rejects non-finite or non-positive setting
thresholds and setting visibility factors outside `(0, 1]`. The historical
`visibility_tolerance` field has no source-owned computational meaning; it is
therefore retained only as a compatibility field fixed at `1.0`, rather than
silently accepting values that do not change the product.

## Differential Evidence

The independent event corpus uses Python with `use_native_heliacal=False` and
native with `use_native_heliacal=True`; it is not native-versus-native testing.

- Stars: Sirius, Regulus, Capella, Acrux, and Arcturus.
- Event kinds: heliacal rising and heliacal setting.
- Latitudes: -30, 0, 31.2, and 60 degrees; longitude 29.9 degrees east.
- Epoch/search: 2024-01-01, 400-day forward window.
- Event-set requirement: exact found, not-found, magnitude-skip, and
  latitude-skip equality.
- Event time tolerance: 0.05 seconds.
- Signed elongation tolerance: 0.00001 degree.
- Metadata requirements: exact day offset and doctrine-owned rising/setting
  threshold.
- Custom setting case: 20-degree eligibility threshold and 0.8 disappearance
  factor.

The named Sirius observable probe at Alexandria additionally measured native
versus Python residuals below 0.008 arcsecond in signed elongation, below
0.001 arcsecond in stellar altitude, and below 0.005 second in the solar
twilight root for the sampled 2024 epochs.

The core series is compared with the scalar Python table evaluator to
`1e-13` degree and with ERFA `nut06a` under the existing 0.001-arcsecond
integration tolerance. Cold initialization, invalid replacement, concurrent
readers, native argument rejection, single-star dispatch, adversarial native
runtime, and server packet paths are also exercised.

On 2026-07-14 the ERFA corpus's historical anchors were corrected to
proleptic-Gregorian 500 BCE (astronomical year `-499`, JD `1538803.5`) and
200 BCE (astronomical year `-199`, JD `1648376.5`). ERFA `cal2jd`, Moira
`julian_day`, and Moira's inverse calendar conversion now jointly guard those
identities. The corrected 12-epoch integration slice passed all 106 tests at
the unchanged 0.001-arcsecond threshold; the worst corrected precession-
nutation matrix residual was 0.000938 arcsecond.

The 2026-07-14 boundary corpus also exercises raw type-2 and type-13 evaluators
at both exact descriptor endpoints and one second outside them, the guarded
Python/native type-13 differential path, forward-start probes immediately
after known rising and setting events, and the DE441 terminal-coverage
reproduction. Its consolidated focused gate passed 153 tests; two optional
`jplephem` comparator tests skipped because that development-only comparator
was not installed.

## Performance Evidence

Local Windows project-`.venv` measurements after kernel warm-up:

| Product | Python oracle | Native default |
|---|---:|---:|
| Five-star setting batch, 400 days | 5.31 s | 0.97 s |
| Magnitude-3 setting batch, 175 searched stars | >120 s (timed out) | 20.69 s |

The native batch owns an explicit `native_heliacal_workers` policy. Its default
is eight workers, bounded to 1-64, and results retain deterministic input/event
ordering. Repeated noon nutation values live only in a request-scoped cache;
there is no process-global astronomical-result cache.

These timings are performance evidence, not astronomical validation.

## Verification Receipt

The final focused native/R06/ERFA/star/packet slice passed 170 tests under
strict known-issue expiry. A separate relevant visibility/server slice passed
140 tests. The broader historical visibility integration file was also run and
reported out-of-scope planet/Moon authority-corpus failures in Babylonian Venus and
Yallop lunar cases. Those branches do not dispatch through the fixed-star
native search; they remain an explicit repository validation gap and are not
counted as passing evidence for this work.

## Remaining Boundary

This admission covers sovereign fixed-star heliacal rising and setting only.
Planetary, lunar-crescent, acronychal, and other generalized visibility
products retain their existing Python-governed implementations and validation
status. Native availability never changes public result-vessel meaning.
