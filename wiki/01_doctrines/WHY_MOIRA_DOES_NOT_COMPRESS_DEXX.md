# Why Moira Does Not Compress DExx Files

**Date:** 2026-08-22
**Status:** Public technical note
**Context:** `wiki/01_doctrines/WHY_MOIRA_DOES_NOT_COMPRESS_DEXX.md`

A JPL Development Ephemeris is already a compressed product. A `.bsp` is
not the integrator’s state dump. It is Chebyshev segments over the
integration, addressed by body and epoch. DE441 is large because its
*span* is about thirty thousand years, not because the polynomials are
wasteful. DE440 covers the modern range in about 114 MiB. That is the
size reduction Moira already recommends for ordinary work.

Swiss Ephemeris `.se1` is a **second file**: another Chebyshev series,
fitted to a JPL kernel, packed into a private layout so the library can
stay small and fast. It can be accurate. It is not the kernel.

This note is about how the two engines *read*. Moira evaluates the
published SPK. Swiss evaluates the packed refit. Both interpolators are
Chebyshev. They do not interpolate the same object.

It is not an attack on Swiss Ephemeris. The compressed files are a
genuine engineering achievement. Official documentation states that they
reproduce JPL data at about 0.001 arcseconds when the reduction matches.
The issue is not that a second fit is impossible. The issue is what the
fit *replaces*: a public kernel, a public format, and a named origin.

---

## 1. Two interpolators, two files

Planetary position at a moment is not a table lookup of every second.
It is a polynomial on a time window. JPL already chose that
representation. Swiss chose it again, with different windows, a
different origin for the Moon, and integer packing.

| | Moira | Swiss Ephemeris |
| :--- | :--- | :--- |
| File | JPL SPK / DAF (`.bsp`) | private `.se1` |
| Whose series | JPL’s published Type 2/3 | a fit *to* a DExx kernel |
| Coefficients | IEEE doubles | variable-width packed integers |
| Address | NAIF `(center, target)` pair | body in `semo` / `sepl` / `seas` |
| After the read | ICRF km, relative to that center | equatorial J2000 3-vector, after `rot_back` |
| Reduction | later, named, in `planets.py` | later, in the same library (`app_pos_etc_*`) |

Reduction — light-time, aberration, nutation, ecliptic of date — is a
later layer in both engines. This paper stops at the file.

---

## 2. How Moira reads a DExx kernel

The runtime file is a JPL SPK. On the machine that produced the grid
below, `de441.bsp` identifies itself from the DAF summary label as
`DE-0441LE-0441`. That string is the kernel. Moira does not relabel it.

`SpkReader` is the only gateway. It opens the DAF catalog, groups
segments by NAIF pair, and, for a requested `(center, target, jd)`,
selects the segment whose epoch range covers the date. DE441 splits
each body across two long epochs at JD 2440432.5; the reader must take
the covering segment, not the last one in the catalog.

Bodies are **chains**, not a planet table:

| Product | NAIF path |
| :--- | :--- |
| Mercury…Pluto, barycentric | `(0, body)` |
| Sun, barycentric | `(0, 10)` |
| Earth-Moon barycenter | `(0, 3)` |
| Earth in EMB | `(3, 399)` |
| Moon in EMB | `(3, 301)` |

Geocentric Moon is therefore two interpolations added: Moon relative to
EMB, plus EMB relative to the solar-system barycenter, minus Earth in
EMB. The kernel never stores a geocentric Moon.

Each Type 2 record is:

1. `INIT` — start of the record, seconds from J2000 TDB
2. `INTLEN` — length of the record, seconds
3. three Chebyshev series (x, y, z) as IEEE doubles, kilometres, ICRF

Time inside the record is mapped to \(s \in [-1, 1]\):

\[
s = 2 \cdot \frac{t - t_0}{\Delta t} - 1
\]

and evaluated with a Clenshaw recurrence. Velocity, when asked for, is
the derivative of that same series, scaled by \(2 / \Delta t\). Type 3
records include velocity coefficients; Moira admits Type 2 and Type 3
and refuses anything else rather than falling back to a third-party
reader.

The independent variable of an SPK is TDB. Moira’s planetary path
converts civil time to TT before the reader; TDB−TT is milliseconds.
The reader returns barycentric (or center-relative) rectangular km in
ICRF. Ecliptic of date, apparent place, and topocentric parallax are
not in the file.

---

## 3. How Swiss reads `.se1`

A Swiss ephemeris file begins with three ASCII lines: a version stamp
`SWISSEPH`, the file name, and a copyright line that names the parent
JPL kernel. The 1800–2400 files used for the grid below still say
**DE431** on that line (2014 for `semo_18` / `sepl_18`; 2023 for
`seas_18`). Then binary:

- a byte-order test word
- declared file length
- DE number (`431`)
- start and end Julian day
- how many bodies, and which internal body numbers
- per body: file index origin, flags, coefficient count `ncoe`,
  scale `rmax`, epoch span, **segment length `dseg`**, and optional
  orbital elements

Three files do the work of one SPK:

- `semo_*.se1` — the Moon, stored **geocentric**
- `sepl_*.se1` — the planets; the Sun is reconstructed from
  heliocentric Earth / EMB in that file, because the file does not
  hold a barycentric Sun the way SPK `(0, 10)` does
- `seas_*.se1` — Ceres through Vesta, Chiron, Pholus

A read at time `tjd` (Swiss ET/TT) computes the segment index
`(tjd - tfstart) / dseg`, seeks a 3-byte file pointer, and unpacks
coefficients. Packing is the actual size trick. Each coordinate’s
series is split into size groups (four or six). Coefficients then
arrive as 4-byte, 3-byte, 2-byte, or 1-byte integers, then nibbles,
then two-bit fields, reconstituted as

\[
c = \pm \frac{\mathrm{int}/2}{10^9} \cdot \frac{r_{\max}}{2}
\]

Some bodies set `SEI_FLG_ELLIPSE`: the stored series is a residual
from a reference orbit, which is added back before use. Some set
`SEI_FLG_ROTATE`: the series lives in the orbital plane and
`rot_back()` rotates it to equatorial J2000 with the stored
equinoctial elements. Only then does `swi_echeb` evaluate the same
shape of Chebyshev polynomial Moira evaluates on the SPK, with

\[
t = 2 \cdot \frac{tjd - t_{\mathrm{seg}0}}{dseg} - 1
\]

The vector that comes out is Swiss’s ephemeris state, equatorial
J2000, already in the origin that file chose (geocentric Moon,
barycentric or heliocentric planets). Apparent place is a later
function in the same C library, behind `swe_calc`.

---

## 4. The two grids

JPL chose short windows and modest degree. Swiss chose windows on the
order of the orbit and high degree, then packed the extra
coefficients. Numbers below are from one DE441 SPK (`DE-0441LE-0441`)
and the matching 18xx `.se1` headers, read on 2026-08-22. Swiss
*order* is `ncoe − 1`. JPL *ncoe* is the coefficient count in the
Type 2 record.

| Body | JPL window | JPL ncoe | Swiss window | Swiss order |
| :--- | ---: | ---: | ---: | ---: |
| Moon | 4 d (EMB-relative) | 13 | 27.55 d (geocentric) | 28 |
| Mercury | 8 d | 14 | 87.97 d | 38 |
| Venus | 16 d | 10 | 224.70 d | 20 |
| Earth / EMB / Sun | 16 d EMB, 4 d Earth-in-EMB, 16 d Sun | 13 / 13 / 11 | 365.26 d | 25 |
| Mars | 32 d | 11 | 687 d | 25 |
| Jupiter | 32 d | 8 | 4000 d | 25 |
| Saturn | 32 d | 7 | 4000 d | 25 |
| Uranus | 32 d | 6 | 4000 d | 15 |
| Neptune | 32 d | 6 | 4000 d | 15 |
| Pluto | 32 d | 6 | 4000 d | 15 |

The Swiss intervals are not a secret law of nature. They are `dseg` in
the `.se1` header. Fast bodies still need more coefficients; Swiss
pays with degree instead of with shorter records. JPL pays with more
records of smaller degree, stored as doubles.

---

## 5. Why the Swiss file is tiny

The 18xx pack on disk (`semo_18` + `sepl_18` + `seas_18`) is **2.01
MiB** and covers roughly 1800–2400. The DE441 kernel next to it is
**3154.6 MiB** and covers 13201 BCE–17191 CE. Those two numbers are
not a verdict on polynomial waste.

Three decisions make `.se1` small:

1. **Span.** Six centuries, not thirty millennia.
2. **Long windows.** One lunar month of order-28 Chebyshev instead of
   a 4-day order-12 record, repeated.
3. **Integer packing.** High-order coefficients are almost zero; they
   collapse into nibbles. A DAF record does not do that. It stores the
   double JPL wrote.

DE440 already offers the first decision in public form: the modern
range, same Type 2 series, about 114 MiB. That is an install tier, not
a new astronomy. Whole-file `zstd` of a `.bsp` would shrink a download
and destroy random access, which both readers need.

---

## 6. What a second file does not carry

A competent refit at the Swiss grid can stay at milliarcseconds
against its parent kernel **when both sides interpolate the same
instant, in the same frame, from the same origin**. Accuracy is a
max-norm check per segment.

What the second file does not buy you, unless you publish it:

- **Which kernel.** The 18xx files still say DE431. A later rebuild
  from DE441 can keep the old sentence. The label lags the bytes.
- **Which origin.** SPK Moon is EMB-relative. `.se1` Moon is
  geocentric. Mixing those two interpolators without saying so is a
  geometry error, not a fit residual.
- **Which frame.** SPK is ICRF km. `.se1` after `rot_back` is
  equatorial J2000. Apparent ecliptic of date is neither file.
- **A residual ledger.** The budget lives in the fitter that produced
  `.se1`. It is not in the file a downstream author can re-run against
  Horizons.

Without that ledger, a disagreement between Swiss and JPL cannot be
assigned. It might be the Chebyshev residual. It might be DE431 versus
DE441. It might be geocentric versus barycentric. It might be a
reduction flag. The public SPK does not have that ambiguity: the file
*is* the series.

---

## 7. When both interpolators are asked the same question

On 2026-08-22 the two readers were given the same TT and the same
geometric-of-date reduction (no light-time, no aberration, no
nutation; ecliptic of date). Swiss 2.10.03 read the DE431 `.se1`
pack. Moira read `de441.bsp`.

| Instant | Moon | Sun | Mercury | Mars | Jupiter |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 1900-01-01 | 0.000″ | 0.000″ | 0.000″ | −0.006″ | −0.009″ |
| 2000-01-01 | 0.001″ | 0.000″ | 0.000″ | 0.000″ | 0.002″ |
| 2026-08-18 | −0.004″ | 0.000″ | 0.000″ | 0.000″ | 0.003″ |
| 2050-09-01 | −0.005″ | 0.000″ | −0.001″ | −0.005″ | 0.006″ |

That is DE431-pack versus DE441-kernel, plus the second fit. It is not
a different astronomy. Apparent of date on the same instants stays in
the same milliarcsecond band (largest residual in that pass: Mars in
1900 at 0.065″). Swiss’s 0.001″ claim against a matching reduction
and a matching parent kernel is compatible with this. The files still
disagree about **what the bytes are**.

---

## 8. Two products people confuse

**A smaller archive** is a distribution problem. You may ship DE440
for 1550–2650, leave DE441 as the long kernel, or someday publish a
second Chebyshev pack with a residual budget. The caller’s API can
stay whatever it was. The file is still an ephemeris.

**A drop-in Swiss replacement** is a surface problem. It owes
`calc_ut`, the flag bits, house letters, and body IDs. The packed
file then exists so that call stays fast without opening a
multi-gigabyte BSP. Libraries that take this path are keeping an old
door. They are not making a new astronomy.

Moira is an alternative, not a replacement. It does not implement
`swe_calc_ut`. Positions take a timezone-aware datetime or an
explicit Julian day. Time conversion is named before the reader
opens. A compressed DExx would only make sense here as an install
tier. The moment it has to answer Swiss flags, the file has been sold
with the door.

---

## 9. Why Moira leaves DExx as published

**The kernel is the evidence.** Moira’s planetary path is JPL DE430,
DE440, or DE441, read by a sovereign SPK/DAF reader. Type-2/3
Chebyshev evaluation is the interpolation JPL already published.
There is no Moira-owned `.se1`.

**The interpolation is inspectable.** Segment selection, Clenshaw
evaluation, and NAIF chaining live in `SpkReader` and `planets.py`.
The native path is a faster evaluation of the same Type 2 record, not
a different series.

**Validation needs a public original.** Horizons, ERFA, and
kernel-to-kernel checks are only honest if the runtime file is the
one those oracles speak. A private second fit can be validated — but
then *it* is the product, and it needs its own residual ledger. Moira
would rather spend that work on the reduction it already names.

**The small modern kernel already exists.** DE440 is the recommended
file for most users. DE441 is the long kernel. Compressing DE441 to
avoid a download is a different offer from hiding DE441 inside a
Swiss personality.

**An alternative should not owe the replacement surface.** Houses,
nodes, Lilith, and ΔT in Moira are admitted identities, not `SE_*`
aliases. See
[Migrating from Swiss Ephemeris](../02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md)
and
[Beyond Swiss Ephemeris](BEYOND_SWISS_EPHEMERIS.md).
A packed kernel that existed only to keep `FLG_TRUEPOS` cheap would
pull the engine back onto that surface.

---

## 10. What a second pack would have to be, if it ever existed

This is not a promise to ship one. It is the bar that made us keep the
kernel.

1. Fit **geometric barycentric ICRF** (or another stated SPK product),
   not apparent longitude. Reduce after interpolation.
2. Per-segment **max residual against the parent DExx**, same time
   scale, same origin, published with the archive.
3. Segment index that preserves **random access**. Whole-file `zstd`
   shrinks a download and kills seeks.
4. No Swiss flag personality. A Moira pack would be an install tier,
   addressed like a kernel, not like `swe_calc_ut`.

Until that bar is worth the file, Moira reads DExx as JPL published
it. DE440 when the century is enough. DE441 when the span is the
point. The interpolation is already in the kernel.

---

## 11. Related documents

- [The Light Box Doctrine](01_LIGHT_BOX_DOCTRINE.md)
- [Beyond Swiss Ephemeris](BEYOND_SWISS_EPHEMERIS.md)
- [Planetary Reduction Pipeline](../02_standards/PLANETARY_REDUCTION_PIPELINE.md)
- [Migrating from Swiss Ephemeris](../02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md)
- [Astronomy validation](../03_validation/VALIDATION_ASTRONOMY.md)

SPK format: NAIF SPK required reading (Type 2 Chebyshev). Kernel
identity: JPL DE440/DE441 technical comments. Swiss file layout and
`swi_echeb`: [Swiss Ephemeris Programmer’s Manual](https://www.astro.com/swisseph/swephprg.htm)
and the distributed `sweph.c` (`read_const`, `get_new_segment`,
`rot_back`). Official Swiss compression claim: [Swiss Ephemeris overview](https://www.astro.com/swisseph/sweph_e.htm).
