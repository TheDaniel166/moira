# Why Moira Does Not Compress DExx Files

**Date:** 2026-08-18
**Status:** Public technical note
**Context:** `wiki/01_doctrines/WHY_MOIRA_DOES_NOT_COMPRESS_DEXX.md`

A JPL Development Ephemeris is already a compressed product. A `.bsp` is
not the integrator’s state dump. It is Chebyshev segments over the
integration, addressed by body and epoch. DE441 is large because its
*span* is about thirty thousand years, not because the polynomials are
wasteful. DE440 covers the modern range in about 114 MiB. That is the
size reduction Moira already recommends for ordinary work.

A second compression — Swiss Ephemeris `.se1`, or any later Chebyshev
pack derived from the same kernel — is a **new file**. It can be
accurate. It is not the kernel. Moira reads the published SPK and keeps
time, frame, and reduction in named code. This note says why, and what
goes wrong when the second file becomes the product.

It is not an attack on Swiss Ephemeris. The compressed files are a
genuine engineering achievement. Official documentation states that they
reproduce JPL data at about 0.001 arcseconds when the reduction matches.
The issue is not that a second fit is impossible. The issue is what the
fit *replaces*: a public kernel, a public format, and a clock that still
has to be declared.

---

## 1. What “compression” actually is

On each time window you choose a polynomial order, fit the JPL state (or
a derived coordinate) in a stated frame, and accept the window only if
the maximum residual against the original kernel stays under a budget.
Fast bodies need short windows. Swiss’s own grid is the confession:

| Body | Interval (days) | Order |
| :--- | ---: | ---: |
| Moon | 27.55 | 28 |
| Mercury | 87.97 | 38 |
| Sun | 365.26 | 25 |
| Venus | 224.70 | 20 |
| Mars | 687.00 | 25 |
| Jupiter–Saturn | 4000 | 25 |
| Uranus–Pluto | 4000 | 15 |

Those numbers come from the `.se1` header (`dseg`, `ncoe`), not from a
secret law of nature. A competent refit at that grid can stay at
milliarcseconds or better **if both sides use the same independent
variable**. Accuracy is a max-norm check per segment. It is not a vibe.

What the second file does not buy you, unless you publish it, is an
audit trail: which kernel, which origin, which frame, which time scale,
and the residual ledger that proves the budget. Without that ledger, a
downstream author cannot tell a fit residual from a clock mix, a frame
mix, or a bug in their own reader.

Moira already performs the first interpolation: Type-2/3 Chebyshev from
the SPK itself, in `SpkReader`. A second fit would duplicate that work
in a private layout.

---

## 2. Two products people confuse

**A smaller archive** is a distribution problem. You may ship DE440 for
1550–2650, leave DE441 as the long kernel, or someday publish a second
Chebyshev pack with a residual budget. The caller’s API can stay
whatever it was. The file is still an ephemeris.

**A drop-in Swiss replacement** is a surface problem. It owes
`calc_ut`, the flag bits, house letters, body IDs, and the convention
that a civil midnight Julian day is Universal Time. The compressed pack
then exists so that call stays fast without opening a multi-gigabyte
BSP. Contemporary libraries that take this path (for example
LibEphemeris’s LEB backend behind a `pyswisseph`-shaped API) are
solving *that* problem. They are not making a new astronomy. They are
keeping an old door.

Moira is an alternative, not a replacement. It does not implement
`swe_calc_ut`. Positions take a timezone-aware datetime or an explicit
Julian day, and the reduction names UT1, TT, and the correction stages.
Compressed DExx would only make sense here as an install tier. The
moment it has to answer Swiss flags, the clock has been sold with the
file.

---

## 3. What happens when you do compress — and then wrap

The second fit is the easy half. The wrapper is where numbers go
missing.

Swiss exposes two functions on purpose:

- `swe_calc_ut(tjd_ut, …)` — the Julian day is **UT**. Swiss adds ΔT
  and evaluates the ephemeris at TT.
- `swe_calc(tjd_et, …)` — the Julian day is already **TT**.

A JPL SPK’s independent variable is **TDB** (practically TT; TDB−TT is
milliseconds). A reader that takes a civil “0:00 UT” Julian day and
feeds it to the kernel as TDB evaluates the Moon at UT, not at TT.

That split is ΔT × lunar rate. It is not a Chebyshev residual.

On 2050-09-01 00:00 UT, Swiss Ephemeris 2.10.03 reports
`swe.deltat = 74.775` seconds. The Moon’s geometric longitude rate that
morning is about 15.313°/day (0.638″/s):

```text
74.775 s × 0.638 ″/s  =  47.709″
```

A Swiss-only check, no JPL involved:

```text
calc_ut(jd)  −  calc(jd + ΔT)     =  0.000″
calc_ut(jd)  −  calc(jd as TT)    =  +47.708″
```

The same mix at other civil midnights scales as ΔT × rate: about 32″ in
2000, 41″ in 2026, 1″ in 1900 when ΔT is near zero. The Sun shows the
same clock at the solar rate (a few arcseconds). When both sides are
locked to TT, Swiss `.se1` versus a DE441 SPK evaluation sits at
tenths of an arcsecond to a few arcseconds — not 47″. The large number
returns as soon as the kernel is given the UT day-number as TDB.

A published claim that Swiss “compression” leaves the Moon 47.7″ off
JPL, and that retargeting `.se1` from DE431 to DE441 “preserved” that
error, is exactly this pattern. Same-stack differences (Swiss after
minus Swiss before, DE441 minus DE431) stay at milliarcseconds and
track the real JPL version delta. Cross-stack Swiss minus JPL stays
near 47″ on both generations because both Swiss files still go through
`calc_ut`. The triangle inequality then looks like proof of a frozen
fit. It is the mix surviving a coefficient swap.

That is what compression-plus-wrapper costs: people measure the door,
not the file. Swiss’s own precision claim (0.001″ against JPL when the
reduction matches) is compatible with the locked-clock rows. It is not
compatible with treating ΔT × *n* as a re-approximation residual.

Other, quieter costs follow the same shape:

- The fit grid (`dseg` × `ncoe`) can stay unpublished except as bytes
  in a header. Downstream authors then cannot reproduce the budget.
- Documentation can still say “compression of DE431” after the
  coefficients have been rebuilt from DE441. The label lags the file.
- A drop-in API freezes silent defaults (midnight is UT, apparent of
  date unless flagged). A second pack built to feed that API inherits
  the defaults.

None of those require the second fit to be sloppy. They require the
product to be the *call*, not the kernel.

---

## 4. Why Moira leaves DExx as published

**The kernel is the evidence.** Moira’s planetary path is JPL DE430,
DE440, or DE441, read by a sovereign SPK/DAF reader. Type-2/3 Chebyshev
evaluation is the interpolation JPL already published. There is no
Moira-owned `.se1`.

**Time is a policy, not a side effect of `calc_ut`.** UT1, TT, and ΔT
are named. `DeltaTPolicy` selects IERS, polynomial, or a hybrid
physical branch. A civil datetime is timezone-aware and converted
explicitly. The engine does not treat a Julian day as UT in one
function and TT in another under similar names.

**The small modern kernel already exists.** DE440 is the recommended
file for most users. DE441 is the long kernel. Compressing DE441 to
avoid a download is a different offer from hiding DE441 inside a Swiss
personality.

**Validation needs a public original.** Horizons, ERFA, and kernel-to-
kernel checks are only honest if the runtime file is the one those
oracles speak. A private second fit can be validated — but then *it*
is the product, and it needs its own residual ledger. Moira would
rather spend that work on the reduction it already names.

**An alternative should not owe the replacement surface.** Houses,
nodes, Lilith, and ΔT in Moira are admitted identities, not
`SE_*` aliases. See
[Migrating from Swiss Ephemeris](../02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md)
and
[Beyond Swiss Ephemeris](BEYOND_SWISS_EPHEMERIS.md).
A compressed kernel that existed only to keep `FLG_TRUEPOS` cheap would
pull the engine back onto that surface.

---

## 5. What a second pack would have to be, if it ever existed

This is not a promise to ship one. It is the bar that made us keep the
kernel.

1. Fit **geometric barycentric ICRF** (or another stated SPK product),
   not apparent longitude. Reduce after interpolation.
2. Per-segment **max residual against the parent DExx**, same TT, same
   origin, published with the archive.
3. Segment index that preserves **random access**. Whole-file `zstd`
   shrinks a download and kills seeks.
4. No Swiss flag personality. A Moira pack would be an install tier,
   addressed like a kernel, not like `swe_calc_ut`.

Until that bar is worth the file, Moira reads DExx as JPL published it.
DE440 when the century is enough. DE441 when the span is the point.
The interpolation is already in the kernel. The clock stays in the
open.

---

## 6. Related documents

- [The Light Box Doctrine](01_LIGHT_BOX_DOCTRINE.md)
- [Beyond Swiss Ephemeris](BEYOND_SWISS_EPHEMERIS.md)
- [Planetary Reduction Pipeline](../02_standards/PLANETARY_REDUCTION_PIPELINE.md)
- [Migrating from Swiss Ephemeris](../02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md)
- [Astronomy validation](../03_validation/VALIDATION_ASTRONOMY.md)

Swiss function contracts: [Swiss Ephemeris Programmer’s Manual](https://www.astro.com/swisseph/swephprg.htm),
`swe_calc_ut` / `swe_calc`. Kernel identity: JPL DE440/DE441 technical
comments. Official Swiss compression claim: [Swiss Ephemeris overview](https://www.astro.com/swisseph/sweph_e.htm).
