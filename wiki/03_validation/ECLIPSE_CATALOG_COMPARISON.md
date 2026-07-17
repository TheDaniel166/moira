# Eclipse Catalog Comparison

This report summarizes the repository's selected eclipse catalog comparisons.
The NASA fixtures identify the Five Millennium solar and lunar catalog source
URLs in `tests/fixtures/eclipse_nasa_reference.json` and the published
Besselian-element rows in
`tests/fixtures/nasa_solar_besselian_reference.json`, plus the paired 2015
polar path/Besselian product in
`tests/fixtures/nasa_solar_polar_path_reference.json`. Cached Swiss rows in
`tests/fixtures/swe_t.exp` are a separate, secondary cross-engine corpus.

This is a readable evidence summary, not a replacement for the executable
tests and not a claim of full-catalog, exact-model, or atlas-grade path
validation. The bounded Besselian per-field evidence admitted below applies
only to its named events, fields, epochs, models, and tolerances. The polar
path evidence is likewise limited to the named 2015 product and its explicit
geographic gates.

## Classification at catalog maxima

The following rows record native classification at the NASA catalog's
published maximum. They establish selected at-instant classification only;
they do not validate Moira's searched maximum or every field of the event.
The displayed NASA timestamps are catalog TD; the Moira column is evaluated at
the fixture's corresponding derived UT1 Julian Day.

### Solar

| NASA catalog TD of greatest | NASA type | Moira native type at derived UT1 maximum | Evidence |
|---|---|---|---|
| -1797-02-01T21:25:34 | H | hybrid | selected catalog-maximum classification |
| 0500-02-15T11:06:27 | H | hybrid | selected catalog-maximum classification |
| 0500-08-11T00:35:02 | A | annular | selected catalog-maximum classification |
| 2005-04-08T20:36:51 | H | hybrid | selected catalog-maximum classification |
| 2809-02-05T21:20:58 | H | hybrid | selected catalog-maximum classification |

### Lunar

| NASA catalog TD of greatest | NASA type | Moira native type at derived UT1 maximum | Evidence |
|---|---|---|---|
| -1801-04-30T07:38:52 | T | total | selected catalog-maximum classification |
| -1801-10-23T22:49:56 | P | partial | selected catalog-maximum classification |
| 0499-03-13T12:12:02 | T | total | selected catalog-maximum classification |
| 2000-01-21T04:44:34 | T | total | selected catalog-maximum classification |
| 2800-02-01T23:47:11 | T | total | selected catalog-maximum classification |

`tests/integration/test_eclipse_nasa_reference.py` contains a broader selected
fixture slice than the representative rows displayed above.

## Search timing on a common TT scale

Raw UT1 differences cannot rank the native and NASA products because their
UT1-to-TT mappings are different. For each row below:

- NASA reference TT is catalog UT1 plus the catalog's published Delta T; and
- Moira TT is searched event UT1 transformed with Moira's active,
  kernel-coherent Delta-T policy.

`tests/integration/test_eclipse_nasa_reference.py` computes the residuals at
runtime and enforces the following policy. Exact residual snapshots are not
frozen in prose because they change when an admitted search or time-policy
implementation changes.

| Case class | Representative products | Executable TT envelope |
|---|---|---:|
| Ancient | solar hybrid (~1797 BCE) and lunar total (~1801 BCE) | 360 s |
| Post-2150 | solar total (~2799) and lunar penumbral (~2801) | 60 s |

The ancient 360-second envelope is cross-authority regression evidence for the
combined search and model-basis difference. It is not an accuracy bound or an
uncertainty estimate for ancient Earth rotation. The post-2150 60-second TT
gate checks search geometry on a common dynamical scale; it does not validate
Moira's future UT1 scenario as a forecast.

## Runtime Besselian per-field comparison

`tests/integration/test_eclipse_besselian_nasa_reference.py` compares the
instantaneous `EclipseCalculator.solar_besselian_elements(jd_ut1)` result with
four published NASA/GSFC Besselian products: the 2000 partial, 2024 total, 2031
hybrid, and 2032 annular solar eclipses. Each polynomial is evaluated at five
TT/TDT epochs spanning `t0 - 3 h` through `t0 + 3 h`, for 20 element sets in
total.

Every admitted numerical field is checked. The exact absolute envelopes are
`1.0e-4` Earth equatorial radii for `x`, `y`, `l1`, and `l2`; `0.003` degrees
for `d`; `0.007` degrees circular for `mu`; and `3.0e-6` for each dimensionless
cone tangent. The test pins this tolerance map independently of the fixture so
a data-only edit cannot silently weaken the gate.

This is primary-authority cross-model evidence, not exact-model parity. NASA's
published elements use VSOP87/ELP2000-82 and the stated `k1`/`k2` lunar-radius
convention. Moira independently evaluates a content-identified DE441/LE441
Earth-reception shadow axis with physical mean-limb radii; NASA coefficients
are never used by the runtime method.

## Polar central-path comparison

`tests/integration/test_eclipse_polar_path_nasa_reference.py` compares the
DE441-native path with the official NASA/GSFC 2015-03-20 total-eclipse product.
The NASA fixture keeps its paired path and Besselian pages under the same
declared model: JPL DE405, `Delta T = 67.6 s`, WGS 84 coordinates at the
published 120-second cadence, published `k1`/`k2` lunar-radius constants, and
mean-limb center-of-mass geometry.

The independent gates are `1 s` for searched greatest time, `3 km` for the
greatest point, five named central-line rows, and both axis/ellipsoid tangency
endpoints, `3 km` for greatest path width, `3 s` for local central duration,
`0.005` for greatest magnitude, and `3 km` of physical cone clearance at each
available published north/south limit. Five TT epochs also exercise the paired
Besselian polynomial under the existing per-field envelopes.

This is one authoritative polar central-path fixture, not an atlas-wide claim.
It does not assert per-row path-width parity away from greatest and does not
reinterpret NASA's missing north limits at 10:16 and 10:18. At those epochs
the ordinary closed-footprint solver is required to fail explicitly. A path
whose other boundary closes on the terminator remains a distinct, unsolved
public width product.

## Native and NASA-compatible products

The native model is Moira's DE441-backed physical geometry in TT. The
`nasa_compat` path is a translation for catalog comparison and does not replace
native truth.

For the focused ancient lunar total case, the native result is transformed
with Moira's active Delta-T policy and the `nasa_compat` result is transformed
through `ut_to_tt_nasa_canon()`. Both are required to remain inside the same
360-second cross-authority regression envelope. Their exact residuals are
runtime evidence rather than frozen documentation, and their raw UT1 residuals
are intentionally not used to declare one model more accurate because that
would compare unlike Earth-rotation policies.

`tests/integration/test_eclipse_ancient_residual_diagnosis.py` separately
checks that the Delta-T branch change is a larger contributor than the sampled
retarded/geometric Moon change and that aligned objectives identify the same
physical TT minimum to within one second. It does not establish historical
event time to one-second accuracy.

## Swiss corroboration boundary

`tests/integration/test_eclipse_external_reference.py` compares selected
classification and searched maxima with cached Swiss rows. This is secondary
cross-engine corroboration, not primary authority validation.

`tests/integration/test_eclipse_occultation_where_reference.py` checks one
cached Swiss solar `where` row at a one-degree latitude/longitude tolerance.
That row does not validate magnitude, path width, central duration, or the
sampled track against NASA Besselian data.

## Interpretation

- Selected NASA catalog maxima support classification evidence across ancient,
  modern, and future rows.
- Search timing must be compared in TT while retaining each product's declared
  Delta-T basis.
- Native and compatibility modes are distinct products and must remain
  explicitly labeled at public boundaries.
- The separate runtime Besselian test establishes bounded per-field cross-model
  evidence for four modern event classes; it does not establish exact NASA
  model parity or atlas-wide coverage.
- The paired 2015 fixture establishes bounded DE441-versus-DE405 evidence for
  one polar central line, its ellipsoid tangencies, greatest width, local
  durations, and available published limit coordinates as cone-boundary
  points; it does not establish one-limit or full-atlas path-width parity.
- Cached Swiss comparisons corroborate a bounded slice but do not govern
  Moira's native model.

## 2026-07 record note

This record retains the earlier removal of stale raw-UT rankings and unsupported
small-angle claims. It now also records the independently derived runtime
Besselian surface, its executable pinned per-field NASA/GSFC comparison, and
the bounded 2015 polar central-path authority fixture.
Exact test-command outcomes belong in the change's completion receipt; this
document states only the durable evidence scope and acceptance envelopes.
