# Apollo (1862) Ephemeris Corruption - Investigation and Fix

## Executive Summary
Apollo's position in shard 16 was off by **~27-43 million km** due to Horizons returning **inconsistent ephemeris solutions** when fetching different time spans. The chunked fetch logic blindly merged incompatible data arcs, creating a catastrophic discontinuity.

## Investigation Timeline

### Initial Symptom
- Apollo apparent position at JD 2451545.0 (J2000.0) showed **~41 million km error** vs Horizons
- Shard data: X = -221M km
- Horizons: X = -250M km

### Root Cause Discovery
1. **CSV parsing was correct** - `parts[2]` correctly extracts X coordinate
2. **Chunk boundary analysis** revealed the smoking gun:
   - Chunk 1 (1600-2000): JD 2451547.5 → X = **-212,077,803 km**
   - Chunk 2 (2000-2400): JD 2451547.5 → X = **-242,992,190 km**
   - **Discontinuity: 43 million km** at the same epoch!

3. **Horizons behavior**: Different time span requests return different numerical integrations
   - Apollo solution JPL#578 is fit around epoch 2018-Jul-30
   - Observational data: 1930-2026 only
   - Extrapolation to 1600-2400 produces inconsistent trajectories

### Why the Old Code Failed
```python
# OLD CODE (BROKEN)
if all_states:
    all_states.extend(states[1:])  # Blindly skip first state, assuming it's a duplicate
else:
    all_states.extend(states)
```

This assumed chunk boundaries would align perfectly, but Horizons returns **different solutions** for different time spans, so the "overlap" point doesn't actually match.

## The Fix

### 1. Validated Chunking
Added overlap validation to detect discontinuities:

```python
if all_states:
    last_prev = all_states[-1]
    first_curr = states[0]
    sep = sqrt((dx)^2 + (dy)^2 + (dz)^2)
    
    if sep > 1.0 km:  # Discontinuity detected!
        raise RuntimeError(f"Chunk boundary discontinuity: {sep:.3f} km")
    
    all_states.extend(states[1:])  # Only skip if validated
```

### 2. Restricted Apollo to Observational Coverage
```python
{"name": "Apollo", "id": "1862;", "start_jd": 2426033.5, "end_jd": 2461041.5}
# 1930-2026 only (JPL#578 observational arc)
```

This ensures Apollo data is accurate within the time span where Horizons has actual observational constraints.

## Files Modified
- `scripts/rebuild_shard_16.py` - Added validation + restricted Apollo coverage
- `scripts/rebuild_shard_18.py` - Added validation (comets)

## Testing
Created diagnostic scripts:
- `scripts/_check_horizons_csv_format.py` - Verified CSV column layout
- `scripts/_trace_chunk_boundary.py` - Demonstrated the discontinuity
- `scripts/_check_apollo_solutions.py` - Confirmed JPL#578 solution metadata
- `scripts/_test_validated_chunking.py` - Verified the fix detects discontinuities

## Lessons Learned
1. **Never trust external APIs to be consistent** across different query parameters
2. **Always validate overlap points** when merging chunked data
3. **Respect observational coverage limits** - extrapolation is unreliable
4. **The ~29M km offset** was actually the Sun-Earth distance, suggesting a reference frame issue, but the real problem was deeper: completely different solution arcs

## Next Steps
1. ✅ Rebuild shard 16 with the fix
2. Test other asteroids in shard 16 for similar issues
3. Document coverage limits in kernel metadata
4. Add runtime warnings in Moira when querying outside coverage

## Impact
- **Apollo**: Now accurate within 1930-2026 (96-year span)
- **Other asteroids**: Protected by validation - will abort if discontinuities detected
- **Users**: Will get clear error messages instead of silently wrong data
