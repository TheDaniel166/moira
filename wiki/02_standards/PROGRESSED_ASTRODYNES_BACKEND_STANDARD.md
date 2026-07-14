# Progressed Astrodynes Backend Standard

Status: public kernel-free doctrine plus kernel-backed Church of Light chart
adapter, facade, and REST surface admitted with explicit source provenance

## 1. Identity

`moira.progressed_astrodynes` implements the progressed power and
harmony/discord mathematics described by Benjamine and Drake in *The Astrodyne
Manual* (1946). It is not a generic progression score, not an alias for
`moira.progressions`, and not a predictive-event certainty engine.

The natal constitution remains in `moira.astrodynes`. The progressed module
uses natal source tables and harmony translation without altering natal output.

## 2. Current Admitted Products

The module currently admits:

- fixed progressed doctrine and policy rejection
- major, major-Moon, minor, and transit carry ratios
- exact and manual-staged commercial rounding truth
- normal progressed body, sign, and house totals from explicit placements
- explicit radical, major, minor, and transit terminal identity
- four-terminal and two-terminal major relation assembly
- progressed aspect percentage selection from the natal orb table
- major/Moon/minor/transit peak power
- the one-effective-degree dated power curve
- shared aspect/nature harmony and discord translation
- per-tier in-orb mutual-reception bonus
- independent minor and transit relations
- power-only direct and indirect minor reenforcement
- relative terminal harmony/discord
- complete practical sign and house distribution from terminal locations,
  cusp rulership, and interceptions
- constant-rate scalar and compound total influence
- bounded contact search with entry, perfection/closest approach, exit,
  clipping, and optional reenforcement-peak truth
- variable-rate numerical integration with the source constant-rate result
  retained as a comparator

Curated package-root exports, `Moira` facade delegates, and strict REST
contracts are public. Scalar and explicit-geometry products remain kernel-free.
The separate chart adapter is kernel-backed and derives its geometry from natal
and target datetimes under the fixed Church of Light progression policy.

## 3. Primary Authority

Primary authority:

- Elbert Benjamine and W. M. A. Drake, *The Astrodyne Manual* (1946), printed
  pages 23-51

Direct capture and derivation record:

- `wiki/05_research/astrodynes/progressed_astrodynes_source_codex_2026-07-12.md`
- `tests/fixtures/progressed_astrodynes_church_of_light.json`
- `tests/fixtures/progressed_astrodynes_benjamine_normal_1949.json`
- `tests/fixtures/progressed_astrodynes_benjamine_dated_1949.json`
- `wiki/05_research/astrodynes/progressed_astrodynes_manual_discrepancies_2026-07-12.md`

The manual pages were rendered and visually inspected. Text extraction was used
only to locate material, not as authority for layout-bearing numbers.

## 4. Fixed Doctrine

The only admitted policy fixes:

- major carry: `1/2`
- major Moon carry: `1/14`
- minor carry: `1/54.6`
- transit carry: `1/730.50`
- progressed percentage: applicable natal orb degrees times `0.05`
- major Moon aspect divisor: `7`
- minor aspect divisor: `27.3`
- transit aspect divisor: `365.25`
- progressed effective orb: 60 arcminutes
- power at the orb limit: one-half peak
- mutual reception per planet: major `2.50`, scaled by the tier divisor
- constant-rate average influence: `0.75` of peak
- manual-facing staged rounding: two decimals, half-up

Unsupported alternatives fail at construction.

## 5. Exact and Manual Arithmetic

Exact computation and manual-facing arithmetic are distinct preserved products.
The manual commonly rounds an average before applying a percentage, rounds the
major-equivalent peak before applying a tier divisor, and rounds the dated
decrement before subtraction. Moira retains both paths.

This distinction is load-bearing. For example, summing exact carried values
would give the progressed Aquarius power as `190.00`; summing the manual's
separately rounded components gives its published `190.01`.

## 6. Geometry Boundary

`moira.progressed_astrodynes` remains the kernel-free doctrine core.
`moira.progressed_astrodynes_chart` is the separately admitted astronomical
adapter. It does not reinterpret the generic `moira.progressions` API as Church
doctrine. It derives and discloses:

- the birth EGMT interval and 30-day symbolic Limiting Date
- the major ephemeris date at one ephemeris day per life year
- the Solar Constant and 27.3-day lunar-return Minor Ephemeris Date
- actual target time for transits
- progressed M.C. from the natal Sun-M.C. constant and solar arc
- progressed Ascendant from progressed M.C., natal latitude, and the selected
  house system
- radical, major, minor, and transit terminals in the natal house frame
- geocentric apparent planetary positions and requested/effective house-system
  truth

The adapter is kernel-backed. House fallback is rejected unless explicitly
enabled, then remains visible in the result. No chart input silently changes
the fixed progression policy.

## 7. Terminal Doctrine

A two-body major relation has four terminals: radical and major-progressed
positions for both bodies. The two aspect-forming terminals are direct; the
other two are indirect. A major body aspecting its own radical place has only
the two direct terminals.

An independent minor or transit relation has a minor/transit moving terminal, a
direct radical/major target, and the target's indirect counterpart.

Direct terminals receive full aspect influence. Indirect terminals receive
one-half. Minor reenforcement changes major power only; it does not change the
major relation's harmony or discord.

## 8. Total Influence and Search Boundary

The manual's constant-rate product remains unchanged. It preserves scalar units
and the worked compound normalization using a 365.25-day year and 30-day month.

The separate variable-rate product integrates the admitted instantaneous
one-degree curve over actual ephemeris motion. It is explicitly identified as
Moira composite-trapezoid quadrature, reports its maximum step, sample count,
coarse/fine error estimate, and retains the manual's constant-rate value as a
comparator. It is not represented as a primary-source formula.
The fine mesh has at least two intervals and is rounded upward to an even
interval count. The coarse mesh is exactly every second fine node, so its step
is twice the fine step and the reported Richardson error divisor of three is
mathematically admitted. `max_samples` is checked against the resulting fine
mesh before ephemeris evaluation, has a minimum of three, and `sample_count`
reports the actual number of unique cached chronology evaluations.
The comparator is absent for partial intervals because the manual's `0.75`
average governs the complete one-degree passage, not an arbitrary slice.

Bounded search finds entry and exit at the one-degree threshold and refines an
exact perfection or a named closest approach. Results preserve coarse step,
boundary/perfection tolerances, clipping, and `max_samples` rejection. A minor
query may name the major relation it reenforces; terminal membership is then
validated before the power-only reenforcement is returned.

## 9. Validation Evidence

The focused tests reproduce:

- Venus, Mercury, Mars, and Moon carry examples
- all twelve Benjamine normal-progressed sign totals
- all twelve Benjamine normal-progressed house totals
- major Sun semi-square Moon peak `16.51` and dated power `15.96`
- all four relative Sun/Moon terminal harmony/discord values
- minor Ascendant parallel Venus peak/date/harmony (`.78`, `.65`, `.16`)
- transit Neptune sesqui-square Sun peak/date/discord (`.05`, `.04`, `.04`)
- direct reenforcement `19.65` and indirect reenforcement `17.81`
- full Saturn inconjunct Sun compound influence (`390y 2m 25.38d` power and
  `195y 1m 12.69d` discord)
- exact/orb-limit/outside, finite, type, identity, counterpart, ordering, and
  checksum adversarial cases
- all 27 dated relation rows: 21 exact formula/print agreements and six named
  publication discrepancies
- complete 12-sign and 12-house practical distribution
- package-root/facade identity and strict REST/OpenAPI behavior
- the Benjamine worked chart's Limiting Date, major and minor ephemeris dates,
  and representative major/minor/transit positions against printed witnesses
- deterministic chart-backed assembly and strict datetime/location boundaries
- transit entry/perfection/exit chronology and the September 5, 1949 minor
  reenforcement perfection
- variable-rate quadrature convergence, units, comparator separation, and
  sample-limit failures

Natal regression tests must accompany every progressed verification receipt.

## 10. Publication Discrepancy Policy

The worked example contains formula, sign, and addition contradictions. Public
results follow the declared doctrine and staged arithmetic. Every conflicting
printed witness remains exposed in provenance; no compatibility switch makes a
publication error executable.

The chart adapter is a separate product from explicit-geometry doctrine. Modern
JPL-backed positions corroborate the printed historical geometry but do not
turn publication arithmetic errors into executable compatibility behavior.
