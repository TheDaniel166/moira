# Moira 6.8.1 - KernelPool Native Planetary Evaluator & Ephemeris Graph Routing

Release date: 2026-09-20. Upgrade path: 6.8.0 to 6.8.1.

Moira 6.8.1 delivers critical engine performance and architectural optimizations
when operating with large sharded small-body catalogs. It restores high-speed compiled
C++ planetary reduction under pooled kernels and optimizes SPK graph traversal from
linear search to $O(1)$ indexed lookup.

## Key Changes

### Native Planetary Evaluator Admission (`planets.py`)
- Admitted `KernelPool` into `NativePlanetaryEvaluator` reduction planning.
- Added `_resolve_primary_spk_reader()` to extract the authoritative planetary
  JPL ephemeris (`de441.bsp`) from a heterogeneous reader pool.
- Restores 0.53 ms 10-planet chart reduction speed in pooled environments (a 50,000× speedup
  over pure-Python fallback under large shard sets).

### Indexed Graph Routing & Candidate Pruning (`spk_reader.py`)
- Implemented $O(1)$ direct edge lookup (`_find_direct_edge_tdb`) using pre-indexed
  pair mappings (`_pair_readers`).
- Added candidate-pruned BFS routing (`_find_candidate_route_tdb`) with strict hub
  pruning against the planetary clock spine `((0, 3), (3, 399), (0, 10), (3, 301))`,
  preventing minor planet shards from acting as graph hubs.
- Added bounded LRU route caching (`_route_cache`) with exact epoch validity intervals,
  reducing repeated small-body lookups to 0.07 ms.
- Optimized clock route evaluation in `_ephemeris_kernel_identity_at_tdb` to query only
  planetary spine readers, reducing segment checks from 2,355 down to 5 per epoch conversion.

### Small-Body Catalog Expansion & Release Memoization
- Includes official sealed 449-shard `2026.09.18.1` minor planet catalog expansion
  (11,223 numbered bodies, 214 Centaurs, 1,048 TNOs) with 100% outer solar system coverage.
- Added thread-safe memoization (`_VERIFIED_RELEASE_CACHE`) in `small_body_catalog_release.py`.

## Verification Scope

- Planetary architecture invariants (`tests/unit/test_planets_architecture_invariants.py`):
  20 passed in 54.3s, confirming C++ native evaluator admission under `KernelPool`
  and parity with pure-Python reference reductions to within $10^{-12}$ degrees.
- Live production benchmark: chart reduction HTTP 200 in 1.50 ms, liveCards figure
  tRPC query in 14.12 ms, calculator compute mutation in 21.35 ms.

## Install

```text
pip install moira-astro==6.8.1
```
