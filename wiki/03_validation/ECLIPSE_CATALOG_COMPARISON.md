# Eclipse Catalog Comparison

This report summarizes the repository's selected eclipse catalog comparisons.
The NASA fixture identifies the Five Millennium solar and lunar catalog source
URLs in `tests/fixtures/eclipse_nasa_reference.json`. Cached Swiss rows in
`tests/fixtures/swe_t.exp` are a separate, secondary cross-engine corpus.

This is a readable evidence summary, not a replacement for the executable
tests and not a claim of full-catalog, Besselian-element, or atlas-grade path
validation.

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
- NASA catalog timing evidence does not imply runtime Besselian-element parity.
- Cached Swiss comparisons corroborate a bounded slice but do not govern
  Moira's native model.

## 2026-07 record note

This documentation correction removes stale raw-UT rankings, unfrozen timing
snapshots, and unsupported Besselian and small-angle claims. It records no new
passing test result; the active eclipse-remediation change must provide its own
exact command outcomes before stronger claims are added here.
