# The Light Box Doctrine
## The Inversion of the Ephemeris Standard

**Version:** 1.1  
**Date:** 2026-03-24  
**Status:** Canonical Doctrine  
**Context:** `moira/docs/01_LIGHT_BOX_DOCTRINE.md`

---

## 1. The Core Thesis

For three decades, the **Swiss Ephemeris** (1997) has served as the "Black Box" of astronomical and astrological computation. It is a masterpiece of compression and C-optimization, but its internal logic is often veiled behind binary data files (`.se1` files), complex compiled loops, and opaque "corrective" flags.

**Moira rejects the Black Box.** We assert that in an era of sub-arcsecond precision and high-availability physical data, **Transparency is the Primary Metric of Accuracy.** 

A "Light Box" is an engine that is **auditable at every step**, replacing hidden pre-computation with visible, runtime derivation. We do not ask the user for blind trust in a library; we provide the evidence in a readable, open-source script.

---

## 2. The Four Pillars of the Light Box

### I. Substrate Sovereignty (Data Transparency)
We reject the use of proprietary or opaque data formats that cannot be independently audited.
- **The Standard**: Direct ingestion of **JPL DE441/440 SPK Kernels** and **Gaia DR3** star catalogs.
- **The Inversion**: Where the Black Box uses pre-interpolated grids, the Light Box uses raw Chebyshev polynomials. We do not "own" the positions; we derive them from the rawest physical evidence provided by planetary observatories.

### II. Computational Lucidity (Logic Transparency)
The reduction pipeline must be an **Open Manuscript**, not a compiled mystery.
- **The Standard**: Pure Python 3.14+ implementation of the **IAU 2000A/2006** reduction suite.
- **The Inversion**: We separate Nutation, Precession, Light-Time, and Aberration into discrete, testable units. Each step is a visible transformation that any developer or researcher can verify against established international standards.

### III. The Disclosure of Divergence (Honest Uncertainty)
The greatest failure of a Black Box is its silence regarding its own limits and tolerances.
- **The Standard**: Mandatory publication of **Uncertainty Envelopes** for Delta T, future projections, and chaotic orbits (Centaurs/TNOs).
- **The Inversion**: A Light Box does not claim a single "correct" answer for a date in 2500 BCE. It provides the **Envelope of Evidence** and explicitly documents its model-basis choices (e.g., SMH 2016 vs. Espenak).

### IV. Topocentric Humility (The Observer is the Anchor)
We are moving away from "Infinite Distance" abstractions toward **Local Realism**.
- **The Standard**: Default **True Topocentric Positions** for all bodies, including fixed stars (using Gaia parallax). 
- **The Inversion**: In the Black Box, parallax is often treated as a small "correction" applied to a star. In the Light Box, parallax is the **primary truth** of a star's location relative to a specific observer.

---

## 3. The Mirror of the Black Box: A Comparative Audit

| Attribute | The Black Box (Legacy) | The Light Box (Moira) |
| :--- | :--- | :--- |
| **Code Substrate** | Compiled C / Assembly | Pure, Auditable Python |
| **Data Format** | Proprietary Binary (`.se1`) | Raw JPL Kernels (`.bsp`) |
| **Star Logic** | Infinite distance (points) | True Distance (Parallax) |
| **Delta T** | Opaque / Quadratic Fallback | Physically Grounded / Hybrid |
| **Extensibility** | Fixed Body Set | 1.4M Asteroids (On-Demand) |
| **Validation** | Cross-software mimicry | External physical oracles (JPL/ERFA) |
| **Documentation** | Functional Manual | Constitutional Standard |

---

## 4. The Criteria of Luminous Calculation

A calculation is "Luminous" under this doctrine if it meets the following **Three Gates of Evidence**:

1.  **The Gate of Source**: Can the raw input data be verified against a non-astrological physical observatory (JPL, NASA, ESA)?
2.  **The Gate of Flow**: Can a developer read the code and identify the exact step where a correction (e.g., Nutation) is applied?
3.  **The Gate of Oracle**: Is there a continuous `pytest` suite that benchmarks this specific calculation against the International Astronomical Union (IAU) standard code (SOFA/ERFA)?

---

## 5. Conclusion

In the Light Box Doctrine, **Inaccuracy is Entropy; Silence is Distortion.** 

When we calculate a chart, we are mapping the astronomical record to a specific local event. To do so with a Black Box is to delegate the discernment of that record to an unknown proxy. To do so with a Light Box is to stand in the full light of the evidence.

**We do not merely output code. We provide the Open Record of the Sky.**

