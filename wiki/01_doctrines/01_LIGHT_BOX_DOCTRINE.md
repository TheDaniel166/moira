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

The following audit is organized by computational domain. Each domain identifies the specific point of divergence between a traditional compact ephemeris-library model and Moira's sovereign, inspectable pipeline.

---

### Ephemeris Substrate

| Attribute | Established Library Model | Moira |
| :--- | :--- | :--- |
| **Data format** | Proprietary pre-interpolated binary (`.se1`) | Raw JPL SPK kernels (`.bsp`) — Chebyshev coefficients as distributed by JPL |
| **Kernel access layer** | Compiled C integration, not separately inspectable | Sovereign `SpkReader` (`moira/spk_reader.py`) — single gateway, explicit segment selection, inspectable in source |
| **Chebyshev evaluation** | Compiled, hidden | `jplephem` used as a binary file reader only; segment selection, epoch handling, and singleton lifecycle are Moira's own implementation |
| **Body coverage** | Fixed compiled body set | SPK-driven; extends to 1.4M+ minor planets on demand via separate kernel files |
| **Kernel version policy** | Bundled, opaque | Explicit — kernel path declared at engine init; version is the caller's declared choice |

---

### Reduction Pipeline

| Attribute | Established Library Model | Moira |
| :--- | :--- | :--- |
| **Nutation theory** | IAU 2000A (compiled, internal) | IAU 2000A — sovereign Python implementation, `nutation_2000a.py` |
| **Nutation series** | Opaque compiled evaluation | Full IERS table evaluation: 1358 lunisolar + 1056 planetary terms, read from `iau2000a_ls.txt` / `iau2000a_pl.txt` at runtime |
| **Nutation fast path** | Compiled C loop | Optional NumPy vectorized path; scalar stdlib fallback always available |
| **Precession theory** | IAU 2006 (compiled, internal) | IAU 2006 Fukushima-Williams four-angle parameterization (P03) — sovereign Python, `precession.py` |
| **Obliquity** | Opaque | Mean obliquity: IAU 2006 P03 polynomial (Capitaine, Wallace & Chapront 2003); True obliquity: mean + nutation-in-obliquity from full 2000A series |
| **Light-time correction** | Applied internally, not inspectable | Iterative correction applied explicitly in `planets.py`; each iteration is a readable function call |
| **Aberration** | Applied internally, not inspectable | Annual aberration applied as explicit vector correction in `coordinates.py` (`aberration_correction`) |
| **Pipeline visibility** | Single opaque function call | Each stage (nutation → precession → aberration → topocentric) is a discrete, named, testable function |

---

### Time System

| Attribute | Established Library Model | Moira |
| :--- | :--- | :--- |
| **ΔT model** | Internal polynomial / opaque fallback | Layered hybrid: IERS Bulletin A/B observed (2015–2026) → 5-year table (1955–2015) → SMH 2016 HPIERS table → telescopic anchors → Morrison & Stephenson (2004) polynomials |
| **ΔT policy mechanism** | Global mutable flag (`set_delta_t_userdef`) | Immutable `DeltaTPolicy` object passed per-call; models: `'hybrid'`, `'nasa_canon'`, `'fixed'` |
| **NASA eclipse parity** | Not distinguished | Separate `delta_t_nasa_canon()` with lunar secular-acceleration correction (`−0.000012932 × (year − 1955)²`); never the default |
| **TT → TDB** | Implicit | Explicit periodic approximation: `0.001657 sin(g) + 0.00001385 sin(2g)` seconds; residual < 2 ms, documented |
| **GMST formula** | IAU 1982 or 2006 (not declared) | Explicitly IAU 2006 (Capitaine et al. 2003) — ERA plus 5th-order polynomial; agreement with SOFA `iauGmst06` < 0.0001 arcsec for 1800–2200 |
| **ERA model** | Not separately exposed | IAU 2000 linear model (IERS Conventions 2010 §5.4.2), sovereign implementation compatible with SOFA `iauEra00` |
| **Time scale opacity** | Time scale in use is not declared to caller | Every public function that takes a JD documents whether it expects TT or UT in its signature and docstring |

---

### Star System

| Attribute | Established Library Model | Moira |
| :--- | :--- | :--- |
| **Catalog authority** | Internal fixed catalog, provenance undocumented | Sovereign Registry minted from IAU modern star names, resolved through SIMBAD (Hipparcos ID → Bayer → SIMBAD ID → proper name) |
| **Catalog size** | ~1000 stars (implementation-defined) | 543+ IAU-sanctioned stars, expandable |
| **Gaia DR3** | Not used | Optional enrichment layer — proper motion, parallax, photometry (G/BP/RP), Teff; policy-controlled, never silently applied |
| **Per-star provenance** | None | `star_provenance.json` — source attribution, matching status, resolution notes per star |
| **Parallax treatment** | Small additive correction | Primary geometric truth; Gaia parallax used to place the star at its true distance from the observer |
| **Proper motion** | Static epoch (often J2000) | Propagated to the requested JD; position reflects the star's actual location at the computation epoch |

---

### Observer / Topocentric

| Attribute | Established Library Model | Moira |
| :--- | :--- | :--- |
| **Default position type** | Geocentric (topocentric optional) | True topocentric by default for all bodies including fixed stars |
| **Parallax for stars** | Optional correction | Primary computation path — observer distance from Earth's center enters the unit vector directly |
| **Atmospheric refraction** | Applied via internal model | Explicit formula in `coordinates.py` (`atmospheric_refraction`, `atmospheric_refraction_extended`); model and parameters visible in source |
| **Horizontal coordinates** | Available | `equatorial_to_horizontal` / `horizontal_to_equatorial` — explicit rotation using GAST and observer latitude |

---

### Policy and Design

| Attribute | Established Library Model | Moira |
| :--- | :--- | :--- |
| **Computation policy** | Global flags and integer constants (opaque at call site) | Typed policy objects passed explicitly; policy is visible in any code that calls the engine |
| **Uncertainty disclosure** | Silent — no uncertainty envelope published | Mandatory for ΔT model range, historical projections, and chaotic orbits (Centaurs/TNOs) |
| **Model choice visibility** | Caller cannot inspect which model was used | Model name is part of the policy object; can be logged, tested, and audited |
| **External dependency count** | Implicitly many (compiled into binary) | `jplephem` (SPK binary reader), NumPy (optional nutation fast path), stdlib for everything else |

---

### Validation

| Attribute | Established Library Model | Moira |
| :--- | :--- | :--- |
| **Oracle strategy** | Cross-software agreement (circular) | Primary oracles: JPL Horizons, SOFA/ERFA reference implementations, IERS published values |
| **Test basis** | Unspecified | `pytest` suite with numerical benchmarks against external physical authorities |
| **Divergence handling** | Not documented | Explicit divergence policy (Section 6); disagreements are diagnostic events, not silenced |

---

### Documentation

| Attribute | Established Library Model | Moira |
| :--- | :--- | :--- |
| **Standard type** | API reference manual | Constitutional doctrinal standard — doctrine, policy, and machine contracts per module |
| **Docstring contract** | Optional / inconsistent | Machine contracts (`[MACHINE_CONTRACT]` blocks) on high-risk classes; frozen API surfaces declared explicitly |
| **What is documented** | Public function signatures | Public signatures + computation policy + authority source + known approximations + validation oracle |

---

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

