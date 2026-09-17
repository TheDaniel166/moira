# Moira 6.7.0 - Strict Orbital Core, Ephemeris Apsides, and Doctrinal Chesta Bala

Release date: 2026-09-17. Upgrade path: 6.6.0 to 6.7.0.

This release introduces a strict SOFA/Horizons-anchored orbital core foundation,
live numerical radial-velocity apsidal passage detection, geometric nodes
migration with sealed catalog holdouts, and source-correct Vedic Chesta Bala.

## Strict orbital core foundation

- Pinned NAIF-LSK `naif0012` TT↔TDB time reduction and JPL Horizons
  `gm_Horizons.pck` gravitational parameters across body systems.
- Complete coordinate frame transformations between ICRF, fixed J2000 ecliptic
  (`ECLIPJ2000_BOP`), and SOFA-derived mean/true ecliptic of date, owning frame
  bias once in precession without double-bias leakage.
- Direct SPK reader velocity state evaluation and center chaining.
- Strict `osculating_elements` calculation and `POST /v1/orbits/elements` REST
  endpoint with allowlisted provenance and singularity receipts.

## Live ephemeris radial-velocity apsides

- Replaced legacy fixed-period / mean-motion approximations with exact live
  ephemeris radial-velocity root searches ($\dot{r}(t) = 0$).
- Two-sided local distance extrema confirmation with cubic Hermite root
  polishing over TDB time, returning explicit `FOUND`, `BEYOND_COVERAGE`, or
  `NOT_IN_WINDOW` outcomes.
- Disjoint calibration and holdout test fixtures derived directly from JPL
  Horizons geometric ICRF VECTORS at exact JDTDB.

## Geometric nodes migration and catalog sealing

- `planetary_nodes.geometric_node` delegates to the Sun-centered true ecliptic of
  date orbital core for planets and all 10,025 catalog asteroids.
- Validated holdout test fixtures sealed across all 401 asteroid shards, with
  complete small-body catalog manifest synchronization.
- True-date model validity bounded to [1900.0, 2100.0], with explicit failure
  receipts outside coverage.
- Updated `POST /v1/nodes/geometric` schema and service.

## Doctrinal Chesta Bala redesign

- Doctrinally compliant Chesta Kendra calculation for non-luminary planets
  adhering strictly to B.V. Raman (*Graha and Bhava Balas*, Ch. VI, §§84–97).
- Removed unverified `_sun_mandoccha_lon` and `_moon_mandoccha_lon`; Sun and
  Moon Chesta Bala are derived directly from Ayana Bala according to Raman
  Ch. X (§§136–137), eliminating arbitrary planetary mandoccha offsets.
- Formula yields $0 \le \text{Chesta Bala} \le 60$ Virupas with piecewise linear
  transformation `chesta_kendra / 3` for $\le 180^\circ$ and
  `(360 - chesta_kendra) / 3` for $> 180^\circ$.

## Verification scope

- Full regression suites across all 4 stages pass with zero test failures:
  reader clock and frame shifts, Horizons holdout element verification,
  live apsidal passage tests, 401-shard node seals, and Shadbala unit/server
  test suites.
- Formal release validation receipts sealed under `tests/artifacts/release/`.

## Migration

- Read [ORBITAL_ELEMENTS_BACKEND_STANDARD.md](../02_standards/ORBITAL_ELEMENTS_BACKEND_STANDARD.md),
  [PLANETARY_NODES_BACKEND_STANDARD.md](../02_standards/PLANETARY_NODES_BACKEND_STANDARD.md),
  [SHADBALA_BACKEND_STANDARD.md](../02_standards/SHADBALA_BACKEND_STANDARD.md),
  and [COMPATIBILITY_NOTES_6.7.0.md](COMPATIBILITY_NOTES_6.7.0.md).
- Install `moira-astro==6.7.0`; server consumers use `moira-astro[server]==6.7.0`.
