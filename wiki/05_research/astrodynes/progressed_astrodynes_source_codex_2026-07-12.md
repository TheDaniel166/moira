# Progressed Astrodynes Source Codex

Status: P0 primary-source capture for the progressed scalar doctrine

Date inspected: 2026-07-12

## 1. Authority and Inspection Method

Primary authority:

- Elbert Benjamine and W. M. A. Drake, *The Astrodyne Manual* (1946)
- local source: `C:\Users\nilad\Downloads\Astrodyne-Manual.pdf`
- progressed doctrine: printed pages 23-51, PDF pages 25-54

The pages were extracted with `pypdf` for discovery and rendered at 1.6x with
PyMuPDF for direct visual inspection. The rendered pages were checked for the
load-bearing ratios, examples, headings, terminal rules, and tables printed in
the manual body. Hyperlinked external inserts labelled `see pdf`, including the
standalone progressed-percentage and mutual-reception chart sheets, are not
embedded as separate local files. Their executable entries are nevertheless
defined in the manual prose and worked calculations captured below.

Evidence classes:

- formula and worked arithmetic below: primary authority validation
- computed Benjamine position geometry: printed witnesses are primary-source
  validation and modern JPL-kernel reconstruction is named corroboration
- no Swiss or other secondary engine is an authority for these formulas

## 2. Governing Products

The source distinguishes:

1. birth-chart power and harmony/discord
2. the normal progressed horoscope before progressed aspects
3. peak power and harmony/discord of a progressed aspect
4. power and harmony/discord of that aspect on a given date
5. relative power and harmony/discord of direct and indirect terminals
6. practical sign and house totals after accessory aspects
7. independent minor and transit aspects
8. minor reenforcement of major progressed aspects
9. total influence while an aspect remains within one effective degree

These are separate computational objects. The source does not authorize their
collapse into a single progressed score.

## 3. Normal Progressed Carry

Directly inspected on printed pages 25-27 (PDF pages 27-29):

| Tier | Carried birth power/harmony/discord | Dignity scale |
|---|---:|---:|
| Major planet | `1/2` | `1/2` |
| Major progressed Moon | `1/14` | `1/14` |
| Minor | `1/54.6` | `1/54.6` |
| Transit | `1/730.50` | `1/730.50` |

A progressing planet carries the same harmony or discord polarity it possessed
at birth. Essential dignity or debility in the progressed sign contributes the
same tier fraction of the natal dignity table value.

Mutual reception is conditional on the two planets forming a progressed aspect:

| Tier | Bonus to each planet |
|---|---:|
| Major | `2.50` harmodynes |
| Major Moon / sub-major | `0.36` harmodynes (`2.50 / 7`, printed) |
| Minor | `0.09` harmodynes (`2.50 / 27.3`, printed) |
| Transit | `0.01` harmodynes (`2.50 / 365.25`, printed) |

The independent source fixture captures Venus, Mercury, Mars, and Moon carry
examples from printed pages 29 and 31.

## 4. Progressed Aspect Percentage

Directly inspected on printed pages 33-34 (PDF pages 35-36):

```text
progressed percentage = applicable natal orb in degrees * 0.05
```

Source selection rules:

- use the most powerful house occupied by a governing radical or major
  progressed planet involved in the aspect
- treat parallel as having the same percentage as conjunction
- treat Mercury as Sun/Moon for the progressed percentage column
- select ordinary planet versus luminary column explicitly

Terminal assembly must decide which natal/major house governs. A minor or
transit angle does not silently replace that house; the minor progressed
Ascendant parallel progressed Venus example uses Venus in a succedent house and
therefore `10 * 0.05 = 0.50`.

Tier scaling of the major peak:

| Tier | Divisor |
|---|---:|
| Major planet | `1` |
| Major progressed Moon | `7` |
| Minor | `27.3` |
| Transit | `365.25` |

## 5. Peak Power and Manual Arithmetic

The source formula is:

```text
average birth power = (birth power A + birth power B) / 2
major peak = average birth power * progressed percentage
tier peak = major peak / tier divisor
```

The printed examples use commercial half-up rounding at staged intermediate
steps. Moira must retain exact values and a separate manual-facing staged path.

Examples captured in
`tests/fixtures/progressed_astrodynes_church_of_light.json`:

- major progressed Sun semi-square radical Moon: `16.51`
- minor progressed Ascendant parallel progressed Venus: major-equivalent
  `21.29`, minor peak `0.78`
- transiting Neptune sesqui-square progressed Sun: major-equivalent `17.34`,
  transit peak `0.05`

## 6. One-Effective-Degree Curve

Directly inspected on printed pages 33 and 37 (PDF pages 35 and 39):

- outside 60 arcminutes: no admitted progressed-aspect power
- at 60 arcminutes: one-half peak
- at perfection: full peak
- within the band: linear interpolation

Equivalent exact form for distance `d` in arcminutes:

```text
scale = 1 - d / 120, for 0 <= d <= 60
power = peak * scale
```

The manual-facing path rounds the decrement before subtracting it from the
rounded peak. Harmony/discord is then derived from the resulting current power;
it is not produced by independently scaling an already rounded peak harmony.

Worked checks:

- minor Ascendant parallel Venus, 20 minutes from perfect: `.78 - .13 = .65`
  astrodynes, then `.65 / 4 = .16` harmodynes
- transit Neptune sesqui-square Sun, 16 minutes from perfect: `.05 - .01 =
  .04` astrodynes/discordynes

## 7. Progressed Harmony and Discord

Directly inspected on printed pages 37-39 (PDF pages 39-41):

- harmonious, discordant, and neutral aspect families use the natal
  Church of Light translation
- Jupiter adds one-half harmony
- Venus adds one-quarter harmony
- Saturn adds one-half discord
- Mars adds one-quarter discord
- progressed essential dignity belongs to the normal progressed horoscope,
  not the accessory aspect calculation
- mutual reception is the separate in-orb per-planet bonus in Section 3

## 8. Terminal and Distribution Law

Directly inspected on printed pages 32-45 (PDF pages 34-48):

- a major progressed aspect normally has four terminals: radical and major
  progressed positions of both planets
- a major planet aspecting its own radical place has two terminals
- minor and transit aspects are made to radical or major progressed terminals
  and therefore have at least three terminals
- the two terminals actually forming the aspect are direct and receive full
  aspect power/harmony/discord
- the corresponding terminals not forming it are indirect and receive one-half
- a cusp-ruled sign/house receives one-half; an intercepted sign receives
  one-quarter
- practical totals add accessory influence to the normal progressed baseline

The full distribution examples for the seventh and ninth houses on August 29,
1949 remain P6/P10 fixtures, not P1 scalar fixtures.

## 9. Minor, Transit, and Reenforcement

Directly inspected on printed pages 47-50 (PDF pages 50-53):

- minor and transit aspects have independent power using their tier divisors
- transit aspects also carry trigger metadata, but the source does not justify
  deterministic event prediction language
- a minor aspect to a major aspect terminal separately reenforces the major
  aspect
- reenforcement changes major power only; harmony/discord remains unchanged
- direct-terminal reenforcement is full strength; an indirect terminal receives
  half
- multiple reenforcements may accumulate

Primary examples reserved for P8:

- June 16, 1949: Neptune minor sesqui-square radical Moon reenforces Sun major
  semi-square radical Moon
- September 5, 1949: Mercury minor inconjunct radical Jupiter reenforces major
  M.C. inconjunct radical Jupiter
- August 29, 1949: dated direct and indirect reenforcement examples

## 10. Total Influence

Directly inspected on printed pages 50-51 (PDF pages 53-54):

For a constant-rate aspect within one degree:

```text
average influence = peak influence * 0.75
total influence = average influence * duration
```

The output retains astrodyne/harmodyne/discordyne days, months, or years. The
worked compound conversion uses 30-day months. The analytic `0.75` rule is
explicitly conditioned on the planets not varying their rate during the orb
interval. Variable-rate numerical integration is not admitted by this capture.

The P1 fixture covers the 36-year component of progressed Saturn inconjunct
radical Sun: peak `14.37`, rounded average `10.78`, total `388.08`
astrodyne-years.

## 11. P0 Gate Result

Cleared for the scalar P1 core:

- carry ratios and dignity scaling
- explicit progressed percentage selection from the natal orb table
- tier peak divisors
- exact and manual-staged peak arithmetic
- the dated one-degree power curve
- shared aspect/nature harmony translation
- per-tier mutual-reception bonus
- constant-rate scalar total influence

Later implementation status (2026-07-12):

- complete terminal assembly and practical sign/house distribution are now
  implemented
- the full 27-row Benjamine dated table and seventh-/ninth-house witnesses are
  tracked in `tests/fixtures/progressed_astrodynes_benjamine_dated_1949.json`
- contradictions within the printed example are recorded separately in
  `progressed_astrodynes_manual_discrepancies_2026-07-12.md`; executable parity
  follows the declared formulas rather than reproducing publication errors
- `moira.progressed_astrodynes_chart` now implements the chart-backed geometry
  as a separate kernel-bound adapter; its derivation and tolerances are recorded
  in `church_of_light_progression_geometry_2026-07-12.md`

Still excluded from the primary-source doctrine:

- independent visual capture of the external standalone mutual-reception and
  progressed-percentage chart sheets, if available
- variable-rate integration as a Church of Light formula. Moira now offers a
  separately labeled numerical integral of the source-defined instantaneous
  curve with the manual's constant-rate product retained as a comparator.
