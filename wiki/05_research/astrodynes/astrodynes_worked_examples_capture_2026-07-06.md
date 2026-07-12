# Astrodynes Worked-Example Capture (2026-07-06)

Status: validation-oracle capture from the primary manual body

Purpose:
- close the "one or more fully worked examples reproduced term by term" gap that
  both the 2026-04-09 source assessment (Section 3) and the natal source capture
  (Section 8) listed as the key remaining blocker
- transcribe, directly from *The Astrodyne Manual* text, the discrete worked
  calculations (input to output) that a Phase 1 implementation must reproduce
- record the manual's full-chart output totals as a secondary end-to-end oracle
- report the cross-validation of the transcribed essential-dignity map (natal
  capture Section 5) against the manual's own worked chart and preserve the
  2026-07-12 resolution of the earlier Mercury transcription discrepancy

This note does not change any admission status. It is source capture and
validation-target definition only.

---

## 1. Provenance

Primary source: *The Astrodyne Manual* (Elbert Benjamine and W. M. A. Drake,
Church of Light, 1946). Text of manual pages 1-51 was supplied in-thread on
2026-07-06 and matches the `Astrodyne-Manual.pdf` already reviewed on
2026-04-09.

All numeric examples below are transcribed from that manual text. Where the
supplied text carries an internal inconsistency (an OCR hazard), it is flagged
explicitly and must be confirmed against the page image before it is trusted as
a fixture.

The worked chart used throughout the manual is the author's own nativity:
- Elbert Benjamine, December 12, 1882, 5:55:26 A.M., 94:00 W, 41:37 N
- Ascendant 2 Sagittarius 27

---

## 2. Discrete Natal Worked Examples (directly reproducible: input to output)

These carry both their inputs and their published outputs, so a Phase 1 engine
can reproduce them without reconstructing a whole chart. These are the primary
term-by-term validation fixtures.

### 2.1 House-position power

- Ascendant 2 Sagittarius 27 (9s 2.45); cusp of 12th 19 Scorpio 54; Venus in
  12th 29 Scorpio 07 (8s 29.12).
- Distance of Venus from nearest cusp (Ascendant): 32.45 - 29.12 = 3.33.
- Zodiacal size of the 12th house: 19.55.
- Weaker cusp (Ascendant) power 8.60; house variation 0.70.
- Variation for Venus = 3.33 * 0.70 / 19.55 = 0.12.
- **Venus house-position power = 8.60 + 0.12 = 8.72 astrodynes.**

OCR flag (must confirm against page image): the manual text renders the 12th
cusp both as `8s 19.90` (step 1) and as `12.90 Scorpio` (step 3). Only the
`12.90` value is arithmetically consistent with the stated house size 19.55 and
the final 8.72. Treat the 12th cusp longitude in this example as ~12.90 Scorpio
pending image confirmation; the load-bearing outputs (19.55, 0.12, 8.72) are
self-consistent.

### 2.2 Zodiacal aspect power

Rule under test: use the wider of the two bodies' effective orbs; astrodynes =
degrees-plus-decimal that the aspect lies inside the orb limit.

| # | Bodies | Aspect | Wider orb | Distance from perfect | Inside orb limit | Astrodynes |
|---|---|---|---:|---|---|---:|
| 1 | Sun 11th 12 Vir 42 / Jupiter 2nd 6 Cap 31 | trine | 10 (Sun succedent) | 6 deg 11 | 3 deg 49 -> 3.82 | **3.82** |
| 2 | Mars 1st 4 Sag 21 / Mercury 11th 7 Lib 44 | sextile | 7 (angle) | 3 deg 23 | 3 deg 37 -> 3.62 | **3.62** |
| 3 | Mercury 10th 15 Sco 15 / Saturn 5th 27 Tau 04 | opposition | 15 (Mercury takes Sun/Moon angular orb) | 11 deg 49 | 3 deg 11 -> 3.18 | **3.18** |

Example 3 also exercises the Mercury rule: Mercury keeps a planet's orb for
*presence* (here the aspect at 11 deg 49 is inside 12 for planets and inside 15
for Sun/Moon), but once within orb its power is scored as if Sun or Moon
occupied its place, so the 15 orb limit is used for the astrodyne count.

### 2.3 Parallel aspect power

Rule under test: orb limit 60 arcminutes; power linear from the perfect-parallel
value (the conjunction power in the more powerful house) to 0 at 60 arcminutes;
use the larger of the two bodies' class values.

| # | Bodies | Distance from perfect | Class values consulted | Astrodynes |
|---|---|---|---|---:|
| 1 | Sun 6th dec 20 N 23 / Saturn 1st dec 20 S 01 | 22 arcmin | Sun cadent 6.97 vs planet angle 7.60 | **7.60** |
| 2 | Mercury 1st dec 14 N 19 / Venus 2nd dec 15 N 18 | 59 arcmin | planet succedent 0.17 vs Mercury angle 0.25 | **0.25** |
| 3 | Uranus 2nd dec 3 S 38 / Jupiter 3rd dec 4 N 02 | 24 arcmin | planet succedent 6.00 vs planet cadent 4.80 | **6.00** |

Doctrine flag (must confirm): example 3 pairs a south declination (3 S 38) with
a north declination (4 N 02) and still scores it as a **parallel** at 24
arcminutes (the arithmetic difference of the magnitudes, 4 deg 02 - 3 deg 38).
In much of the tradition opposite-hemisphere declinations form a
*contra-parallel*, not a parallel. This example implies the manual scores the
declination aspect by magnitude difference irrespective of hemisphere for the
power calculation. Confirm whether Astrodynes distinguishes parallel from
contra-parallel at the power layer, or only at the harmony/discord layer.

### 2.4 Sign power roll-up

Given total planetary powers Venus 34.16, Mars 24.18, Jupiter 36.48,
Mercury 52.08, Saturn 28.22, Uranus 40.50:

- Taurus on 2nd cusp, Mars and Jupiter in Taurus: unoccupied = 34.16 / 2 = 17.08;
  total = 17.08 + 36.48 + 24.18 = **77.74**.
- Gemini intercepted in 2nd with Saturn: unoccupied = 52.08 / 4 = 13.02;
  total = 13.02 + 28.22 = **41.24**.
- Taurus on both 2nd and 3rd cusps: full ruler power, total =
  34.16 + 36.48 + 24.18 = **94.82**.
- Aquarius (double ruler Saturn + Uranus): average ruler = (28.22 + 40.50)/2 =
  34.36; one cusp unoccupied = 17.18; intercepted = 8.59; two cusps = 34.36.

### 2.5 House power roll-up

- 2nd house (Taurus on cusp, Mars in 2nd, Jupiter in 1st): 17.08 + 24.18 =
  **41.26** (Jupiter excluded, it is in the 1st).
- 2nd house additionally with Gemini intercepted and Saturn in Gemini:
  41.26 + 13.02 + 28.22 = **82.50**.

### 2.6 Sign harmony roll-up

- Sagittarius on 1st cusp; Jupiter 18.24 harmodynes; Saturn in Sagittarius 12.16
  discordynes; Ascendant 7.22 harmodynes. Unoccupied = 18.24 / 2 = 9.12 h;
  + 7.22 h - 12.16 d = **4.18 harmodynes**.
- Capricorn on 2nd cusp; Saturn 14.12 d; Moon in Capricorn 6.20 d.
  Unoccupied = 7.06 d; + 6.20 d = **13.26 discordynes**.

---

## 3. Full-Chart Output Totals (secondary end-to-end oracle)

The manual publishes the complete natal totals for the Benjamine chart (manual
page 28). These are **output only**: the chart's input positions are shown as a
wheel image ("see pdf") and are not fully transcribed in the manual text, so
these totals cannot yet be reproduced end-to-end without first capturing the
input positions. They remain a valuable final target once the input chart is
captured (birth data above is sufficient to reconstruct it, subject to matching
the Church of Light 1882 ephemeris and house system).

Later status (2026-07-12): this paragraph describes the Benjamine-chart evidence
boundary only. A separate three-chart corpus with captured official wheels and
all populated relation-grid cells is now executable; see
`astrodynes_three_chart_parity_validation_2026-07-12.md`.

Planets (astrodynes / net harmony):
Sun 103.64 / 21.65 d; Moon 28.39 / 11.09 h; Mercury 94.00 / 20.32 d;
Venus 47.63 / 11.27 h; Mars 91.33 / 35.65 d; Jupiter 64.04 / 00.01 h;
Saturn 40.03 / 06.14 h; Uranus 67.00 / 15.77 d; Neptune 35.04 / 18.71 h;
Pluto 25.49 / 08.17 d; M.C. 78.33 / 19.00 d; Asc. 37.51 / 06.20 d.

Signs (astrodynes / net harmony):
Aries 45.67 / 17.83 d; Taurus 124.38 / 22.32 h; Gemini 111.04 / 10.15 d;
Cancer 14.20 / 05.55 h; Leo 51.82 / 10.83 d; Virgo 192.33 / 44.93 d;
Libra 23.82 / 05.64 h; Scorpio 29.21 / 10.96 d; Sagittarius 406.13 / 72.54 d;
Capricorn 48.41 / 14.16 h; Aquarius 26.76 / 02.41 d; Pisces 24.77 / 04.68 h.

Houses (astrodynes / net harmony):
1: 406.13 / 72.54 d; 2: 48.41 / 14.16 h; 3: 26.76 / 02.41 d; 4: 24.77 / 04.68 h;
5: 45.67 / 17.83 d; 6: 124.38 / 22.32 h; 7: 111.04 / 10.15 d; 8: 14.20 / 05.55 h;
9: 51.82 / 10.83 d; 10: 192.33 / 44.93 d; 11: 23.82 / 05.64 h; 12: 29.21 / 10.96 d.

Internal checksum available from these totals: the manual states the sum of all
sign astrodynes equals the sum of all house astrodynes (and likewise for net
harmony). The published sign and house rows above satisfy this (each house row
equals a sign row), which is a useful invariant test even before the inputs are
captured.

---

## 4. Essential-Dignity Cross-Validation (natal capture Section 5)

The natal capture Section 5 dignity map was transcribed from imperfect-legibility
screenshots. The manual's worked chart applies specific dignities in its
progressed calculations (which reuse the natal dignity assignments), giving an
independent check on that map.

Confirmed by the worked chart:
- Sun detriment = Aquarius (progressed Sun in Aquarius scored "in its detriment").
- Mars inharmony = Aquarius (progressed Mars in Aquarius scored "its inharmony").
- Pluto detriment = Taurus (progressed Pluto in Taurus scored "in its detriment").
- Jupiter detriment = Gemini (progressed Jupiter in Gemini scored "in its detriment").
- Moon home = Cancer (progressed Moon in Cancer scored "in its home sign").

**Resolved source-table discrepancy (2026-07-12):**
- The worked chart scores progressed **Mercury in Aquarius** as **exaltation**
  ("due to its exaltation Mercury has 1/2 of 3.00, or 1.50 harmodynes"; manual
  page 29).
- Direct inspection of the Church of Light `Table of Essential Dignities`
  confirms that this is intentional Astrodyne doctrine: Mercury exaltation is
  **Aquarius 15**, fall is **Leo 15**, harmony is **Scorpio**, and inharmony is
  **Taurus**.
- The earlier natal capture had imported the conventional Western
  Virgo/Pisces axis. The worked calculation is therefore valid source evidence,
  not a hand-calculation error.
- The same table inspection corrected the Venus and Jupiter harmony axes and
  Neptune's exaltation, fall, harmony, and inharmony entries. The canonical
  corrected table is in the natal source capture, Section 5.

Not exercised by the worked chart (still unvalidated from examples):
- the degree-of-exaltation / degree-of-fall tier (+/-4), which fires only within
  1 degree of the exact exaltation/fall degree
- the non-classical outer-planet dignities for Uranus, Neptune, Pluto home and
  exaltation, which have no independent worked-example hit here

---

## 5. Mutual Reception Now Validatable From Source Examples

Both prior notes flagged that the standalone mutual-reception table is not
visible in the PDF scan. The manual text does not reproduce the table grid, but
it does state the rule (two planets in each other's home or exaltation) and it
names concrete mutual-reception pairs in the worked chart:
- "Uranus and Mercury are in mutual reception"
- "Jupiter and Mercury are in mutual reception"

The natal capture Section 6 derived mutual-reception rule can therefore be
validated against these named pairs using the corrected source table. The
standalone mutual-reception table is still desirable but is no longer the only
path to validating the rule.

---

## 6. Progressed Layer Is Also Fully Specified (future phase, not natal)

Both prior notes are natal-scoped. The manual body additionally specifies the
entire progressed layer, which a later phase would use:
- progressed carry-power ratios: major 1/2 of birth power; major Moon 1/14;
  minor 1/54.6; transit 1/730.50
- progressed-aspect peak power via the Table of Progressed Aspect Percentages,
  which the manual defines as orb-degrees * 0.05 (so it is reconstructable, not a
  separate opaque table); Moon aspect / 7; minor / 27.3; transit / 365.25
- a distinct progressed orb model: a progressed aspect carries 1/2 of its peak
  power and harmony at 1 degree from perfect, rising linearly to full at perfect
  (unlike the natal orb model, which falls to 0 at the orb limit)
- reenforcement of a major aspect by minor aspects, and total-influence integrals
  in astrodyne-years/months/days
- a fully worked progressed example for the Benjamine chart on August 29, 1949

This is recorded so the progressed source position is not re-chased later. It is
out of scope for Phase 1 natal work.

---

## 7. Reconciled Gap Status

Closed or downgraded by this capture:
- "enough worked examples to validate term by term": **closed for the discrete
  natal calculations** (Section 2); a full-chart end-to-end oracle also exists
  (Section 3). The separate three-chart corpus became executable on 2026-07-12
  after direct official-PDF wheel and grid capture.
- "standalone mutual-reception table": still not visually captured, but the rule
  is now **validatable against named source examples** (Section 5).

Resolved after this capture:
- the **Mercury exaltation discrepancy** was a transcription error in the natal
  capture; the table and worked chart both specify Aquarius 15 (Section 4)

Update (2026-07-06): three full worked charts with captured birth data (Trump,
Gandhi, Walters) were supplied and recorded in
`astrodynes_parity_oracle_charts_2026-07-06.md`. These give input-captured
end-to-end parity oracles (a secondary/software source), so the full-chart
oracle no longer depends solely on reconstructing the Benjamine inputs. Their
six-way power checksums all pass. None places Mercury in Aquarius or Virgo, but
the directly inspected table now settles the Section 4 Mercury question.

Still open (unchanged):
- a worked-example hit for the degree-of-exaltation tier remains desirable;
  the table and scoring rule are explicit, but this tier lacks an independent
  numeric example
- input positions of the Benjamine chart remain uncaptured, but are now optional
  given the three parity charts above

---

## 8. Verification Notes

Reviewed directly:
- the supplied manual text (pages 1-51)
- the natal source capture Section 5 dignity map and Section 6 mutual-reception
  derivation, checked term by term against the manual's worked calculations
- on 2026-07-12, the embedded and separately supplied images of the Church of
  Light `Table of Essential Dignities`

Not performed:
- this historical SCP Phase 1 capture itself validates only the discrete
  source-worked computational core; the later three-chart end-to-end parity run
  is documented in `astrodynes_three_chart_parity_validation_2026-07-12.md`
- no edit to the `moira.wiki` submodule copies of these notes (a separate mirror
  repo); only the canonical `wiki/05_research/astrodynes/` tree is updated
