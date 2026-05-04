# Categorical Boundary Validation Ledger

## 1. Audit Context
* **Target Subsystems:** `moira.constants`, `moira.planets`, `moira.houses`, `moira.aspects`
* **Objective:** Prove that astrological categories (signs, houses, aspects) are defined by absolute mathematical boundaries, and are immune to upstream float coercion, rounding errors, or fuzzy thresholding.
* **Core Threat:** Float-edge corruption, where a body at 29.9999999999° is prematurely coerced into the next sign/house due to loss of precision or silent rounding in the public interface.

## 2. Findings & Diagnostics
* **The Absolute Threshold:** Using 64-bit floating-point precision, a sequence of extreme limits was injected: `29.9999999999°` (10 nines), `29.99999999999°` (11 nines), and `29.999999999999°` (12 nines), followed by exactly `30.000000000000°`.
* **Data Vessel Integrity:** `PlanetData` inherently preserves the pure, unrounded longitude. Even the derived string-formatting helper `longitude_dms` correctly delegates to `math.trunc` style integer logic, avoiding the phenomenon where `.9999` coerces to the next degree prior to sign assignment.
* **Structural Purity:** Neither the engine layer nor the presentation layer implements artificial "fuzzy" boundaries. A body is in Aries until it mathematically equals or crosses `30.0`.

## 3. Validation Results
* **Test Regimen:** `tests/unit/test_categorical_boundary.py`
* **Outcome:** 
  1. **Sign Classification:** `moira.constants.sign_of` strictly retained "Aries" for all `29.9...` inputs.
  2. **House Classification:** `moira.houses.assign_house` placed `29.999999999999°` in House 1, and only flipped to House 2 when exactly `30.0` was reached. It correctly toggled the `exact_on_cusp` flag only on the exact boundary.
  3. **Aspect Engine:** `moira.aspects.aspects_between` retains the exact float difference for its `orb` calculation, refusing to artificially round an 89.999999999999° square to an exact orb of `0.0`.
  4. **Data Vessel:** `PlanetData` preserves the raw float.
* **Status:** Stable. The categorical layer is mathematically pure. No silent corruption exists at the threshold.
