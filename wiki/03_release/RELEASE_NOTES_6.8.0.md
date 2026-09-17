# Moira 6.8.0 - SBDB Osculating Asteroid Orbit Classification and Small Body REST Surface

Release date: 2026-09-17. Upgrade path: 6.7.0 to 6.8.0.

This release delivers official NASA JPL Small-Body Database (SBDB) osculating
asteroid orbit classification, diagnostic predicate boundary margins, and full
small-body admission across the FastAPI `/v1/orbits/*` REST surface.

## SBDB-style osculating asteroid orbit classification

- Implemented `moira.orbits.orbit_class(body, jd_ut, *, reader=None)` and batch
  helper `orbit_classes_at(bodies, jd_ut, *, reader=None)`.
- Classifies small bodies into all 14 official dynamical groups:
  `IEO` (Atira), `ATE` (Aten), `APO` (Apollo), `AMO` (Amor),
  `MCA` (Mars-crossing Asteroid), `IMB` (Inner Main-belt Asteroid),
  `MBA` (Main-belt Asteroid), `OMB` (Outer Main-belt Asteroid),
  `TJN` (Jupiter Trojan), `CEN` (Centaur), `TNO` (TransNeptunian Object),
  `PAA` (Parabolic Asteroid), `HYA` (Hyperbolic Asteroid), and fallback `AST` (Asteroid).
- Evaluates strict inequality conditions with zero signed margins on exact boundaries.
- Provides structured diagnostic predicate margins (`OrbitClassBoundaryMargin`,
  `OrbitClassPredicate`) documenting exact signed distances to qualifying cutoffs
  ($a$, $q$, $Q$, and Jupiter Tisserand parameter $T_J$).
- Re-exported 9 public symbols in `moira`, `moira.facade`, and `moira.predictive`:
  `OrbitClassCode`, `OrbitClassBoundaryMargin`, `OrbitClassPredicate`,
  `OrbitClassResult`, `OrbitalErrorReceipt`, `OrbitClassBatchItem`,
  `OrbitClassBatchResult`, `orbit_class`, and `orbit_classes_at`.

## Small bodies admission to `/v1/orbits/*` REST surface

- `POST /v1/orbits/elements`: Admits catalog small bodies (asteroids and comets).
  For open conics ($e \ge 1.0$), non-applicable elliptic fields (`semi_major_axis_au`,
  `aphelion_distance_au`, `orbital_period_days`, `mean_anomaly_deg`,
  `mean_motion_deg_per_day`) serialize truthfully as `null`, while maintaining
  backward compatibility for elliptic orbits.
- `POST /v1/orbits/distance-extremes`: Admits catalog small bodies. Unreachable
  passages (e.g., hyperbolic orbits without an apocenter) raise
  `OrbitalPassageUnavailableError`, mapped to HTTP 422 (`orbital_event_availability`).
- `POST /v1/orbits/class`: Dedicated single asteroid classification endpoint
  returning classification code, title, description, and diagnostic boundary
  margins with allowlisted SPK provenance.
- `POST /v1/orbits/class/batch`: Batch evaluation for up to 128 small bodies at
  one epoch, featuring per-item error isolation and strict local path redaction.

## Verification scope

- Unit test suite (`tests/unit/test_orbit_classes.py`): 45 tests verifying all
  14 classes, boundary edge conditions, non-asteroid rejections, and batch errors.
- Integration test suite (`tests/integration/test_sbdb_orbit_classes.py`): verified
  against authentic SPK kernels from `receipted_small_body_reader_pool`.
- Server test suite (`tests/server/test_server_orbits_routes.py`): 14 tests
  covering transport models, small bodies, open conics, and classification endpoints.
- Total combined orbit verification: 65 passed, 1 skipped (external network policy).

## Migration

- Read [ORBITAL_ELEMENTS_BACKEND_STANDARD.md](../02_standards/ORBITAL_ELEMENTS_BACKEND_STANDARD.md),
  [REST_API_REFERENCE.md](../02_services/REST_API_REFERENCE.md),
  and [COMPATIBILITY_NOTES_6.8.0.md](COMPATIBILITY_NOTES_6.8.0.md).
- Install `moira-astro==6.8.0`; server consumers use `moira-astro[server]==6.8.0`.
