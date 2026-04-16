# The Transparent Engine Doctrine
## Transparency as an Ephemeris Standard

**Version:** 1.3  
**Date:** 2026-04-07  
**Status:** Canonical Doctrine  
**Context:** `wiki/01_doctrines/01_LIGHT_BOX_DOCTRINE.md`

---

## 1. The Core Thesis

For three decades, the **Swiss Ephemeris** (1997) has served as a major standard in astronomical and astrological computation. It is a compact, accurate, carefully engineered library. Its design priorities, however, come from a different era: compiled internals, binary data products, and runtime behavior that is not always inspectable at the same level as a source-derived, fully spelled-out pipeline.

**Moira makes a different design choice.** In an era of sub-arcsecond precision and high-availability physical data, **transparency is itself part of accuracy** because it allows assumptions, authorities, and model choices to be audited directly.

A transparent engine is **auditable at every step**, replacing hidden pre-computation where practical with visible, runtime derivation. The point is not to denounce earlier engines, but to make Moira's own computational record readable, explicit, and reviewable.

---

## 2. The Four Pillars of Transparent Computation

### I. Substrate Sovereignty (Data Transparency)
We reject the use of proprietary or opaque data formats that cannot be independently audited.
- **The Standard (Planetary)**: Direct ingestion of **JPL DE441/440 SPK Kernels** via Moira's sovereign **`SpkReader`** (`moira/spk_reader.py`).
- **The Standard (Stars)**: Moira's **Sovereign Star Registry** — a curated catalog of 543+ IAU-sanctioned stars, minted from IAU modern star names and cross-resolved through SIMBAD (priority order: Hipparcos ID → Bayer designation → SIMBAD ID → proper name), optionally enriched with **Gaia DR3** astrometry and photometry. Source attribution, matching status, and resolution notes are preserved per star in a provenance sidecar (`star_provenance.json`). Gaia DR3 is an enrichment layer, not the primary authority — the registry is the sovereign foundation.
- **Moira's approach (Planetary)**: Moira uses raw Chebyshev polynomial coefficients from JPL SPK kernels. We do not "own" the positions; we derive them from the physical evidence provided by planetary observatories. `SpkReader` is the single authorised gateway between Moira and the binary kernel: it owns the file handle, resolves NAIF body ID pairs to the correct epoch-appropriate segment, and enforces the invariant that no other module holds a direct reference to the kernel object. `jplephem` is used solely as a binary SPK file reader; all segment selection, multi-epoch handling, and singleton lifecycle are Moira's own implementation, fully inspectable in source.
- **Moira's approach (Stars)**: Moira maintains explicit per-star source records, proper motion propagation to the requested epoch, and parallax-grounded distance. Every star in the registry can be traced to its originating authority. Gaia DR3 enrichment is policy-controlled and auditable; it is not silently applied.

### II. Computational Lucidity (Logic Transparency)
The reduction pipeline must be an **Open Manuscript**, not a compiled mystery.
- **The Standard**: Sovereign Python 3.10+ implementation of the full **IAU 2000A/2006** reduction suite — no external numerical library is used in the reduction pipeline. Nutation is evaluated directly from IERS table data (1358 lunisolar + 1056 planetary terms, per IERS Conventions 2010 Chapter 5). Precession uses the Fukushima-Williams four-angle parameterization (P03, Capitaine, Wallace & Chapront 2003). Time scale conversions (UT → TT → TDB, ΔT) are implemented in `julian.py` using stdlib only. SOFA/ERFA serves as a validation oracle, not a runtime dependency.
- **Moira's approach**: We separate Nutation, Precession, Light-Time, and Aberration into discrete, testable units. Each step is a visible transformation that any developer or researcher can verify against the source literature.
- **The Tradeoff**: The choice of Python is deliberate — auditability and sovereignty over raw speed. Performance in the nutation evaluator is managed through an optional NumPy vectorized fast path; the scalar fallback uses stdlib math only. We do not pretend this is free; we assert it is the correct tradeoff for an engine whose outputs must be traceable to first principles.

### III. The Disclosure of Divergence (Honest Uncertainty)
The greatest failure of any engine is silence regarding its own limits and tolerances.
- **The Standard**: Mandatory publication of **Uncertainty Envelopes** for Delta T, future projections, and chaotic orbits (Centaurs/TNOs).
- **Moira's approach**: Moira does not claim a single "correct" answer for a date in 2500 BCE. It provides the **Envelope of Evidence** and explicitly documents its model-basis choices — for example, the **Stephenson, Morrison & Hohenkerk (2016)** parabolic + observation hybrid model versus the **Espenak polynomial tables** (NASA/GSFC). These are not interchangeable; their disagreements at historical extremes must be surfaced, not hidden.

### IV. Topocentric Humility (The Observer is the Anchor)
We move away from "Infinite Distance" abstractions toward **Local Realism**.
- **The Standard**: Default **True Topocentric Positions** for all bodies, including fixed stars (using Gaia parallax). Earth orientation parameters (polar motion, UT1-UTC, length-of-day) are sourced from the **IERS** (International Earth Rotation and Reference Systems Service), not approximated internally.
- **Moira's approach**: Parallax is treated as the **primary truth** of a star's location relative to a specific observer. Similarly, the GCRS-to-TIRS frame rotation for topocentric conversion requires real EOP data — IERS bulletins, not polynomial fallbacks — wherever precision is claimed.

---

## 3. The Time Scale Chain

This doctrine extends to time itself. Positional astronomy is meaningless without an explicit, traceable answer to the question: *time in which scale, on which model, from which authority?* Moira answers that question in sovereign Python through `julian.py`, with no external time library and no hidden defaults.

### The Chain

**UT (user input) → TT** (for precession, nutation, coordinate transforms)  
**TT → TDB** (for JPL kernel access — SPK state vectors are in TDB)  
**TT → UT** (for sidereal time, topocentric hour angle, Earth rotation)

### ΔT — The Conversion Kernel

The central quantity is **ΔT = TT − UT1** (seconds). Moira implements a layered hybrid model in `delta_t()` that selects the highest-accuracy available source for each era:

| Era | Source | Accuracy |
| :--- | :--- | :--- |
| 2015–2026 | Annual IERS Bulletin B/A observed means | Sub-second |
| 1955–2015 | 5-year observed table, blended into annual at 2015 | ~0.1 s |
| Historical range | HPIERS table — Stephenson, Morrison & Hohenkerk (2016) | Few seconds |
| 1600–1900 | Telescopic anchor table, Espenak & Meeus / Morrison & Stephenson | ~10 s |
| 1900–1955 | Dense 5-year pre-modern table | ~1 s |
| All other eras | Morrison & Stephenson (2004) piecewise polynomials | Model-dependent |

All table-driven ranges use linear interpolation between anchor points. Polynomial branches activate only when no table covers the requested year. The far-past/far-future parabolic fallback (`−20 + 32u²`, u = (y − 1820)/100) is the same form used by SOFA and the standard literature.

A separate `delta_t_nasa_canon()` implements the Espenak/Meeus Five Millennium Canon polynomial set with its lunar secular-acceleration correction (`−0.000012932 × (year − 1955)²`). This is used exclusively when comparing against NASA eclipse contact times; it is never the default.

### DeltaTPolicy

The older global-flag approach (`Swiss Ephemeris set_delta_t_userdef`) is a mutable setting. Moira replaces it with an immutable **`DeltaTPolicy`** object passed per-call:

- `'hybrid'` — default multi-source model described above
- `'nasa_canon'` — NASA eclipse-canon polynomials for catalog parity
- `'fixed'` — explicit fixed ΔT in seconds, for controlled tests

Policy is explicit at every call site. There is no global state to corrupt.

### TT → TDB

JPL SPK kernels expect **Barycentric Dynamical Time (TDB)**. Moira converts via the standard low-amplitude periodic approximation:

> TDB − TT ≈ 0.001657 sin(g) + 0.00001385 sin(2g) seconds  
> g = 357.53° + 0.9856003° × (JD_TT − J2000)

This is sufficient for millisecond-level timing. The approximation's residual (< 2 ms over the modern era) is documented; it is not hidden.

### Sidereal Time and Earth Rotation

For topocentric positions, the Earth's rotation must be placed correctly. Moira implements:

- **ERA** (`earth_rotation_angle`) — IAU 2000 linear model (IERS Conventions 2010 §5.4.2), compatible with SOFA `iauEra00`
- **GMST** (`greenwich_mean_sidereal_time`) — IAU 2006 formula (Capitaine et al. 2003, A&A 412), ERA plus 5th-order polynomial correction for the CIO offset. Agreement with SOFA `iauGmst06` is better than 0.0001 arcsec for 1800–2200. This is explicitly not the older IAU 1982 polynomial, which diverges by up to ~0.55 arcsec two centuries from J2000.
- **GAST** (`apparent_sidereal_time`) — GMST plus equation of the equinoxes (nutation in right ascension).

### The Doctrine Consequence

This chain is not a correction appended after the fact. It is the substrate on which all position derivation rests. Every term — ΔT model, TDB approximation, sidereal time formula — is named, sourced, and testable. Opacity at this layer invalidates any transparency claim regardless of what happens downstream.

---

## 4. Comparative Audit

Swiss Ephemeris is named directly here because it is a longstanding reference implementation in this domain. Its design choices are historically coherent and technically clear: compact distribution, performance-optimized internals, a stable API maintained across decades, published source, pre-interpolated binary data for efficient shipping, and a global-flag policy model that was common in its era.

Swiss Ephemeris uses `.se1` binary data, a pre-interpolated format optimized for size and speed. Moira uses raw JPL SPK kernels directly, trading size and speed for source-level auditability.

Moira's positions are stated positively and explicitly:

- Moira uses raw JPL SPK kernels (`.bsp`) with explicit kernel path selection.
- Moira centralizes kernel access through `SpkReader` in `moira/spk_reader.py`.
- Moira evaluates reduction stages as named source functions (nutation, precession, aberration, topocentric transforms).
- Moira implements IAU 2000A nutation and IAU 2006 precession in sovereign Python modules.
- Moira exposes the full IAU 2000A term list at runtime from `iau2000a_ls.txt` and `iau2000a_pl.txt`.
- Moira supports an optional NumPy fast path and a scalar stdlib fallback.
- Moira passes computation policy as explicit immutable objects (for example `DeltaTPolicy`) rather than mutable process-wide flags.
- Moira documents time-scale expectations (TT vs UT) at the public function level.
- Moira keeps TT to TDB conversion explicit, including the periodic approximation and its documented residual.
- Moira keeps sidereal-time modeling explicit (ERA, GMST, GAST) with cited standards.
- Moira treats topocentric computation as first-class, including explicit parallax and refraction functions.
- Moira maintains star provenance explicitly (`star_provenance.json`) and supports policy-controlled Gaia enrichment.
- Moira uses primary external validation oracles (JPL Horizons, SOFA/ERFA, IERS references) and records divergence policy as doctrine.

This section is intentionally descriptive: it records design differences without ranking them.

## 5. The Four Gates of Luminous Calculation

A calculation is "Luminous" under this doctrine if it passes the following gates:

1. **The Gate of Source**: Can the raw input data be verified against a non-astrological physical observatory (JPL, NASA, ESA, IERS)?

2. **The Gate of Flow**: Can a developer read the code and identify the exact step where each correction (Nutation, Precession, Light-Time, Aberration) is applied?

3. **The Gate of Time**: Is the time scale chain (UTC → TT → TDB, UTC → UT1) explicit, sourced from IERS-current data, and tested against ERFA reference outputs?

4. **The Gate of Oracle**: Is there a continuous `pytest` suite that benchmarks this specific calculation against the IAU standard code (SOFA/ERFA) and JPL Horizons reference outputs?

---

## 6. Divergence Policy

When Moira's output disagrees with Swiss Ephemeris, JPL Horizons, or another derived tool, the doctrine does not treat disagreement as an error to be silenced. It treats it as a diagnostic event to be resolved by strata:

1. **Input and identity** — are the same bodies, epochs, and observer coordinates in use?
2. **Time scale** — is the disagreement traceable to a TT/TDB/UT1 difference?
3. **Reference frame** — is one result geocentric and the other topocentric?
4. **Apparent vs. geometric** — is light-time correction, aberration, or refraction applied differently?
5. **Model basis** — does the disagreement trace to a delta-T model choice, an EOP source, or a precession-nutation theory?
6. **Published product semantics** — do the two tools define the output quantity the same way (e.g., apparent vs. astrometric position)?

If Swiss Ephemeris disagrees with Moira and the strata audit cannot resolve it, the divergence is published — not suppressed. Moira does not correct toward Swiss Ephemeris unless Swiss Ephemeris can be shown to hold higher authority for that specific case. The default authority hierarchy remains: JPL / IERS / IAU / SOFA-ERFA above Swiss Ephemeris.

---

## 7. Conclusion

An engine that hides its assumptions does not merely fail to communicate — it actively distorts the record it claims to preserve. Every silent default, every opaque correction, every undocumented model choice is a substitution of the engine's judgment for the observer's evidence.

**We do not merely output code. We provide the Open Record of the Sky.**

