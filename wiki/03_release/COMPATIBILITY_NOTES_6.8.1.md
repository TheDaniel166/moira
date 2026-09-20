# Compatibility Notes - Moira 6.8.1

## Upgrade Boundary

Moira 6.8.1 is fully backward-compatible from 6.8.0 for all public Python APIs,
REST routes, and transport schemas. No public signatures, parameters, or response
structures were altered.

## Performance and Evaluation Behavior

- **Planetary Reduction Speed**: Calling `all_planets_at` or `planet_at` on an instance
  of `Moira` that holds an active `KernelPool` (such as when small-body catalogs are discovered)
  now seamlessly invokes the C++ `NativePlanetaryEvaluator`. Planetary positions match
  reference DE441 reductions to $10^{-12}$ degrees while completing in under 1 millisecond.
- **Graph Routing**: `KernelPool` route discovery no longer scales linearly with reader count.
  Direct edge queries and candidate routes execute in $O(1)$ amortized time.
- **Route Cache**: `KernelPool` maintains an internal, thread-safe LRU route cache bounded
  at 512 entries. No user intervention or cache maintenance is required.

## Recommended Migration Sequence

Direct drop-in upgrade from 6.8.0:
```text
pip install --upgrade moira-astro==6.8.1
```
For services running `moira_server`:
```text
pip install --upgrade "moira-astro[server]==6.8.1"
```
Restart server processes (`moira-engine`, `moira-api`) following upgrade.
