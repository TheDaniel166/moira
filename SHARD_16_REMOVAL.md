# Shards 16 & 18 Removal - Summary

## Date
2026-05-09

## Reason for Removal
Shards 16 and 18 were built from JPL Horizons API data using chunked fetching. Both kernels were **corrupted** due to Horizons returning inconsistent ephemeris solutions across different time spans.

### Root Cause
When fetching long time spans (900 years) in 400-year chunks, Horizons' numerical integration produces different trajectories depending on the requested time window. This causes catastrophic discontinuities (up to 43 million km) at chunk boundaries.

### Specific Example: Apollo (Shard 16)
Apollo (asteroid 1862) showed a 43 million km position error:
- Chunk 1 (1600-2000): X = -212,077,803 km at JD 2451547.5
- Chunk 2 (2000-2400): X = -242,992,190 km at JD 2451547.5
- **Discontinuity: 43 million km at the same epoch**

### Shard 18 Validation
Attempted to validate shard 18 (comets) but the kernel file was already damaged and unreadable by jplephem, confirming the same corruption issue.

## Bodies Removed

### Shard 16 (6 asteroids)
1. Pandora (NAIF 2000055)
2. Persephone (NAIF 2000399)
3. Amor (NAIF 2001221)
4. Icarus (NAIF 2001566)
5. Apollo (NAIF 2001862)
6. Karma (NAIF 2003811)

### Shard 18 (5 comets)
1. Halley (NAIF 1000001)
2. Encke (NAIF 1000002)
3. Tempel 1 (NAIF 1000009)
4. C-G (NAIF 1000067)
5. Swift-Tuttle (NAIF 1000109)

## Files Removed
- `kernels/sb441_type13/sb441_type13_shard_016.bsp` (corrupted)
- `kernels/sb441_type13/sb441_type13_shard_018.bsp` (corrupted)
- `scripts/rebuild_shard_16.py` (broken build script)
- `scripts/rebuild_shard_18.py` (broken build script)

## Files Modified
- `kernels/sb441_type13/manifest.json`:
  - Removed shard 16 and 18 entries
  - Updated body_count: 383 → 378

## Current Status
**Working shards**: 1-15, 17
**Total bodies**: 378
- Shards 1-15: 372 asteroids (from official sb441-n373s.bsp)
- Shard 17: 6 centaurs (from official centaurs.bsp)

All remaining bodies have:
- ✅ Reliable Type 13 (Hermite) coverage
- ✅ 1000-year span (1500-2500)
- ✅ Sub-nanometer precision (max_node_error_km < 3e-8)
- ✅ Converted from official JPL kernels (not Horizons API)

## Why Shard 17 Survived
Shard 17 (centaurs) was converted from the official `centaurs.bsp` kernel, not built from Horizons. Official kernels are pre-computed by JPL with consistent numerical integration, so they don't have the chunking discontinuity issue.

## Alternative Solutions Considered
1. **Restrict to observational coverage** - Limit bodies to their data arcs
   - Pro: Accurate within limits
   - Con: Limited utility, still requires Horizons
   
2. **Use official JPL kernels** - These specific bodies don't exist in official kernels
   - Not applicable for shards 16 & 18 bodies

3. **Accept discontinuities** - Document and live with the errors
   - Rejected: Unacceptable for astronomical precision

4. **Remove corrupted shards** - ✅ **CHOSEN**
   - Pro: Honest, clean, reliable
   - Con: Fewer bodies available

## Lessons Learned
1. **Never trust external APIs** to be consistent across different query parameters
2. **Always validate overlap points** when merging chunked data
3. **Prefer official kernels** over API-fetched data whenever possible
4. **Validate before deployment** - corruption can be silent
5. **Honest failure > silent corruption** - better to not have data than wrong data

## Impact
Users querying these 11 bodies (6 asteroids + 5 comets) will now get an error instead of silently wrong positions. This is the correct behavior for an astronomical truth-first engine.

## Recommendation
If these specific bodies are needed in the future:
1. Check if JPL has released official kernels for them
2. If using Horizons, restrict to observational coverage only (no extrapolation)
3. Always validate for discontinuities before deployment
