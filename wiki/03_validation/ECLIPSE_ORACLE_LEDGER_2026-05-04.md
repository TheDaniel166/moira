# Eclipse Oracle Validation Ledger (In-Depth Audit)

## 1. Audit Context
* **Target Subsystems:** `moira.eclipse_geometry`, `moira.solar_cartography`, `moira.occultations`
* **Objective:** Conduct a deep-level adversarial audit of Moira's eclipse and occultation oracles to ensure absolute physical and mathematical sovereignty against professional astronomical standards (NASA Besselian Elements).
* **Audit Date:** 2026-05-04

## 2. In-Depth Audit Findings

### A. Besselian Alignment (NASA Parity)
Moira's shadow geometry was stress-tested against NASA's Besselian elements for the 2017-08-21 and 2024-04-08 total solar eclipses.

*   **Geometric Parity**: Moira matches NASA's $l_1$ and $\tan f_1/\tan f_2$ within $2 \times 10^{-4}$ Earth radii. 
*   **Residual Rationale**: Umbral residuals ($l_2$) of 20-60 km were identified. These are confirmed as being driven by the divergence in radius constants (Moira uses IAU-2015/WGS-84 while NASA/Espenak use IAU-1976/polynomial-fit constants) rather than geometric error.
*   **Sign Convention**: Moira's $l_2$ uses an internal positive-for-total convention (Moon closer to Sun than Apex), whereas NASA uses negative-for-total. This was verified as a consistent coordinate transform.

### B. Numerical Stability & Small-Angle Precision (FIXED)
*   **Regression Found**: Discovered that `_angular_separation_equatorial` was using the numerically unstable Spherical Law of Cosines. At asteroid distances (2.5 AU), a 1 km separation ($10^{-8}$ degrees) collapsed to zero due to precision loss in `acos(1.0)`.
*   **Resolution**: Upgraded the formula to the **Haversine** implementation.
*   **Proof**: A separation of $7.6 \times 10^{-8}$ deg is now resolved with a residual of only $7 \times 10^{-15}$ deg, recovering 7 orders of magnitude of precision.

### C. Geometric Invariants & Continuity
*   **Shadow-Cone Non-Collapse**: Verified. The umbral and penumbral sizes respond correctly to lunar distance variations (1/D perspective effect).
*   **Continuity**: Verified that shadow axis coordinates ($x, y$) move smoothly across time samples without micro-oscillations or solver jitter.
*   **Magnitude Monotonicity**: Verified. Magnitude strictly increases as the shadow axis offset reaches zero.

## 3. Validation Summary
*   **Test Suite**: 
    - `tests/unit/test_shadow_oracle.py` (Geometric invariants)
    - `tests/integration/test_eclipse_besselian_audit.py` (NASA Parity & Precision Audit)
*   **Outcome**: **PASSED**. 
*   **Conclusion**: Moira's shadow oracle is physically rigorous, numerically stable for small-angle grazing work, and aligned with NASA Besselian standards.

## 4. Unresolved Risks & Future Work
*   **Lunar Profile**: While the geometric "mean" shadow is validated, the engine currently lacks a bound lunar-limb topography dataset for "Baily's Bead" or profile-corrected graze work.
*   **Search Engine Triage**: The future-era eclipse search regression remains a blocker for fully automated canonical validation across millennium ranges. This is identified as a Delta T policy divergence (Stephens vs. Morrison/Stephenson) rather than a solver windowing failure.
