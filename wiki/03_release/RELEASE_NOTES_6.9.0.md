# Moira 6.9.0 - Lunar Orientation and Source-Aligned Astrology

Release date: 2026-09-26. Upgrade path: 6.8.2 to 6.9.0.

Moira 6.9.0 adds a sovereign lunar-orientation product, expands primary
directions and house dynamics, and tightens eclipse and chart-pattern
semantics against their governing sources. It also extends native acceleration
for the new astronomical and directional workloads.

## Key Changes

### Lunar Orientation and Libration

- Added `lunar_orientation_at()` and `Moira.lunar_orientation()` for
  geocentric or WGS-84 topocentric total apparent libration, subsolar
  coordinates, lunar-axis and bright-limb position angles, and solar
  colongitude.
- Added a native DAF/PCK type-2 reader for the pinned JPL DE440 lunar
  principal-axis model and the admitted `MOON_ME_DE440_ME421` frame transform.
- Added fail-closed resource identity, coverage, timescale, light-cone, and
  convention provenance.
- Validated the product with frozen JPL Horizons and NASA SVS comparisons and
  native-versus-SPICE matrix checks.

### Eclipse Saros Identity

- `saros_series` now reports the conventional van den Bergh/NASA catalog
  series for actual solar and lunar eclipses.
- `saros_index` remains as a compatibility field name for that catalog series.
- The former continuous mean-month value is preserved explicitly as
  `saros_cycle_position`; `saros_lunation_number` exposes the corresponding
  NASA/GSFC `Luna Num`.

### Jones Chart Shapes and Aspect-Pattern Coherence

- Reworked the seven Jones chart shapes from Marc Edmund Jones's primary text,
  including the canonical Sun-through-Pluto input set and source-specific
  Bucket, Locomotive, Seesaw, Splay, and Splash rules.
- Added auditable qualitative coherence bands and motion qualifiers for
  T-Square, Grand Trine, Grand Cross, Yod, Mystic Rectangle, and Kite patterns.
- Added typed REST contracts for pattern discovery and coherence assessment.

### Primary Directions and House Dynamics

- Added bound distributions, dynamic solar-arc keys, chronological life
  timelines, neo-converse motion, mundane aspects and parallels, and zodiacal
  midpoint targets.
- Added native under-pole and Placidian mundane solvers with Python/native
  parity coverage.
- Added analytical house-angle and cusp-speed products, high-latitude
  Campanus, Regiomontanus, and Topocentric integration, and REST endpoints for
  house dynamics and polar admissibility.

### Native Performance and Maintenance

- Added a single-pass native apparent planetary evaluator with cached SPK
  segment resolution and GIL-released batch evaluation.
- Added thread-local nutation caching while preserving numerical parity.
- Removed the unused export-governance subsystem and its obsolete reports and
  scripts.

## Compatibility Highlights

- The lunar-orientation product requires the pinned
  `moon_pa_de440_200625.bpc` and `moon_de440_250416.tf` resources in addition
  to the applicable DE441/LE441 translation kernels.
- Eclipse `saros_index` is now `int | None`, not the former floating cycle
  phase. Consumers that need the former value must read
  `saros_cycle_position`.
- Jones classification now requires exactly the canonical ten planetary
  bodies; REST requests containing nodes or custom body sets are rejected with
  HTTP 422.

## Install

```text
pip install --upgrade moira-astro==6.9.0
```

For the optional REST service:

```text
pip install --upgrade "moira-astro[server]==6.9.0"
```
