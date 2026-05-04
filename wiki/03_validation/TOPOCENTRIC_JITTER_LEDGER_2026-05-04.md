# Topocentric Jitter Validation Ledger

## 1. Audit Context
* **Target Subsystem:** `moira.stations` (Retrograde & Direct Event Solvers)
* **Objective:** Prove that planetary stations are defined purely by absolute barycentric/geocentric zero-crossings of ecliptic longitude velocity, and not corrupted by the rotational motion of a terrestrial observer.
* **Core Threat:** Earth's diurnal rotation introduces parallax oscillations. If a solver naively relies on topocentric apparent velocity, it risks generating spurious zero-crossings (micro-oscillations) when a planet's true geocentric speed is extremely low.

## 2. Findings & Diagnostics
* **The Physical Reality:** Using an adversarial numerical derivative model placed at the Earth's equator (maximal rotational speed), topocentric apparent velocity was sampled during the shallow Mars station of February 2025. 
* **The Jitter Margin:** As the true geocentric speed of Mars approached ~0.01 degrees per day, the diurnal topocentric parallax rate (~0.03 degrees per day) dominated the vector. This caused the apparent topocentric velocity to physically flip signs **four times** over a 24-hour period.
* **Architectural Safety:** Moira's design intrinsically protects against this. The underlying property `PlanetData.speed` strictly exposes the *astrometric geocentric velocity*. Even if an observer is defined for the target projection, the speed scalar used by event solvers remains absolute.

## 3. Validation Results
* **Test Regimen:** `tests/unit/test_topocentric_jitter.py`
* **Sweep Parameters:** Latitudes (−90° to +90°), Longitudes (0° to 360°), and Altitudes (0m to 5,000m).
* **Outcome:** 
  1. **Geocentric Stability:** Geocentric velocity crosses zero exactly *once*, and `moira.stations.find_stations()` returns exactly one stationary event.
  2. **Topocentric Volatility Confirmed:** The adversarial numerical method successfully demonstrates that micro-oscillations exist in the physical topocentric plane.
  3. **Universal Sign Agreement:** Outside the narrow margin where parallax exceeds planetary velocity, the topocentric velocity sign and the geocentric velocity sign match perfectly across all combinations of the latitude/longitude/elevation sweep.
* **Status:** Stable. The station engine is geometrically sovereign and immune to topocentric jitter. A station in Moira is an absolute astronomical event, not an artifact of the observer's spin.
