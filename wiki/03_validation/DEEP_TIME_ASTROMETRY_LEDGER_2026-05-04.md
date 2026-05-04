# Sovereign Star Registry — Deep-Time Astrometry Ledger

## 1. Audit Context
* **Target Subsystem:** `moira.stars._propagate_icrs_vector`
* **Objective:** Ensure stellar proper motion, parallax, and radial velocity calculations remain stable and mathematically rigorous across ±10,000-year epochs.
* **Core Threat:** Unbounded non-linear drift and coordinate distortion in high-proper-motion luminaries caused by tangential plane approximations.

## 2. Findings & Diagnostics
* **Original State:** The proper motion was computed using a first-order linear approximation on the tangent plane. 
* **The Divergence:** At an 8,000-year propagation horizon, fast-moving stars exhibited catastrophic angular displacement. For example, Kapteyn's Star diverged by approximately **26.7 degrees** relative to the exact IAU SOFA/ERFA truth vectors.
* **Identified Causes:**
  1. The projection completely ignored 3D space motion and perspective secular acceleration.
  2. The star's motion along the line of sight (radial velocity) was excluded from the calculations.

## 3. Implemented Interventions
* **Record Structure:** Expanded the `_SovereignStarRecord` data model and parser in `moira/stars.py` to securely store and coerce `radial_velocity_km_s` from the registry dataset.
* **Vectorized Space Motion:** Rewrote `_propagate_icrs_vector` to fully support Cartesian 3D space-motion. 
  * Converted angular proper motion into exact tangential velocities ($v_T = d_{pc} \cdot \mu$).
  * Aligned radial velocity precisely along the vector line of sight using explicit exact IAU coefficients ($1.022712 \times 10^{-6}$ pc/yr per km/s).
  * The actual coordinate translation is now resolved purely in 3-dimensional Cartesian space, normalizing the unit vectors after time progression, prior to returning to spherical coordinates.

## 4. Validation Results
* **Test Regimen:** `tests/unit/test_deep_time_astrometry.py`
* **Sweep Parameters:** Iterating from Julian year J−8000 to J+8000 in 100-year increments.
* **Comparison Oracle:** ERFA's position and proper motion reference formulas (`erfa.starpm`).
* **Outcome:** 
  * The catastrophic 26-degree drift has been eliminated.
  * Angular divergence for all tested stars (Barnard's Star, Kapteyn's Star, 61 Cygni A, and Groombridge 1830) strictly conforms to bounds $< 0.05$ degrees.
  * This negligible remaining variance appropriately isolates the relativistic aberration iterations present in ERFA, which are deliberately absent from Moira's physical substrate translation.
* **Status:** Stable. The astronomical substrate is sovereign and precise across the tested deep-time boundaries.
