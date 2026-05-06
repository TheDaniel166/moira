# Moira Architecture and Philosophy Summary

## 1. Core Philosophy & Doctrine

Moira is an "astronomy-first" astrology engine built in pure Python. It prioritizes **transparent, inspectable, and reproducible calculations**, challenging the opacity of traditional ephemeris tools (like Swiss Ephemeris).

Its guiding principles are codified in the **"Light Box Doctrine"**:
- **Transparency & Derivation**: Computations are explicit. Core astronomical corrections (Nutation, Precession, Aberration, Light-Time) are applied sequentially in inspectable Python stages.
- **Topocentric Humility**: It prioritizes true topocentric positions (Local Realism) incorporating WGS-84 observer elevation and Gaia proper motions/parallaxes instead of infinite distance abstractions.
- **Honest Uncertainty**: It documents model-basis choices explicitly (e.g., Delta T historical curves, orbital chaos envelopes) and surfaces uncertainty rather than hiding it behind single assumed values.
- **Explicit Policy**: There is no global, hidden state. Options for time scales, reference frames, and calculation methods are injected as explicit, immutable policy objects.

## 2. Core Architecture

The system is structured as a pipeline translating astronomical substrate into astrological artifacts.

### The Pipeline
1. **Raw Input**: Reads Chebyshev state vectors and Hermite interpolated data (SPK Type 13) directly from JPL DE-series `.bsp` kernels using `jplephem`.
2. **Positional Reductions**: Geocentric/topocentric positions are calculated using iterative light-time correction, gravitational deflection, relativistic annual aberration, frame bias, IAU 2006 precession, and IAU 2000A nutation.
3. **Data Vessels**: Output is encapsulated in frozen dataclasses, the primary one being `Chart`. A `Chart` is an immutable snapshot of all body positions, node states, and computational variables (like ΔT) for a given Julian Day.

### Major Modules
- **`moira/julian.py`**: Manages the crucial time scale chain (UTC → TT → TDB, UTC → UT1). It handles complex Delta-T modeling (hybridizing modern IERS data, historical tables, and polynomial fallbacks).
- **`moira/spk_reader.py` & `moira/_spk_body_kernel.py`**: Interacts with the raw kernel files, executing geometric and kinematic queries without opaque C extensions.
- **Astrological "Pillars" (`aspects.py`, `houses.py`, `dignities.py`, `lots.py`)**: Dedicated domain implementations acting upon the immutable `Chart` vessels.
- **The Facade (`moira/facade.py` & mixins)**: A unified public API (`Moira` class). It is decomposed internally via mixins (`_facade_core.py`, `_facade_astronomy.py`, `_facade_kernel.py`) that strictly delegate computations back to the isolated domain modules.

## 3. The Constitutional Process

Moira’s evolution is strictly governed by a 12-phase **Constitutional Process** which dictates that every subsystem must prove its invariants and semantic stability before becoming public API:
1. **Truth Preservation** -> **Classification** -> **Inspectability** -> **Policy Surface**
2. **Relational Formalization** -> **Hardening**
3. **Integrated Local Condition** -> **Aggregate/Network Intelligence**
4. **Full-Subsystem Hardening** -> **Architecture Freeze (Validation Codex)** -> **Public API Curation**

This ensures that any component is epistemically solid, reproducible, and verifiable against authoritative astronomical standards (SOFA/ERFA, JPL Horizons) and astrological canons before developers rely on it.
