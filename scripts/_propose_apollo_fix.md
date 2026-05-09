# Apollo (1862) Ephemeris Discontinuity - Root Cause and Fix

## Problem Summary
Apollo's ephemeris from Horizons shows a **43 million km discontinuity** at the chunk boundary (JD 2451547.5) when fetching 1600-2400 CE in 400-year chunks.

## Root Cause
Horizons solution JPL#578 for Apollo is fit around epoch 2018-Jul-30 with observational data from **1930-2026**. When requesting ephemeris far outside this observational window (e.g., 1600-2000 vs 2000-2400), Horizons' numerical integration produces **inconsistent trajectories** depending on the requested time span.

## Evidence
```
Chunk 1 (1600-2000): JD 2451547.5 → X = -212,077,803 km
Chunk 2 (2000-2400): JD 2451547.5 → X = -242,992,190 km
Discontinuity: 43 million km (0.29 AU)
```

## Proposed Solutions

### Option 1: Restrict to Observational Coverage (RECOMMENDED)
Only provide Apollo ephemeris for epochs with good observational data:
- **Time span**: 1930-2026 (JD 2426033.5 to JD 2461041.5)
- **Rationale**: This is the actual data arc for JPL#578
- **Impact**: Users requesting Apollo outside this range get an error
- **Benefit**: Guaranteed accuracy within observational constraints

### Option 2: Use Smaller Chunks with Validation
- Reduce chunk size from 400 years to 50 years
- Validate overlap at each boundary
- Abort if discontinuity > 1 km
- **Problem**: Will still fail for Apollo, just at different boundaries

### Option 3: Fetch Full Span Without Chunking
- Request entire 1600-2400 span in one Horizons call
- **Problem**: May timeout or exceed Horizons API limits
- **Risk**: Untested for 900-year spans

### Option 4: Use Different Data Source
- Switch to JPL's SBDB or direct SPK kernels
- **Problem**: Requires significant refactoring
- **Benefit**: More reliable for long time spans

## Recommended Implementation

**Implement Option 1** with a fallback:

```python
# In rebuild_shard_16.py
BODIES = [
    {"name": "Pandora",    "id": "55;",   "start": 2305447.5, "end": 2634157.5},
    {"name": "Persephone", "id": "399;",  "start": 2305447.5, "end": 2634157.5},
    {"name": "Amor",       "id": "1221;", "start": 2305447.5, "end": 2634157.5},
    {"name": "Icarus",     "id": "1566;", "start": 2305447.5, "end": 2634157.5},
    {"name": "Apollo",     "id": "1862;", "start": 2426033.5, "end": 2461041.5},  # 1930-2026 only
    {"name": "Karma",      "id": "3811;", "start": 2305447.5, "end": 2634157.5}
]
```

This ensures Apollo data is accurate within its observational arc, while other asteroids can use the full millennial span if their solutions support it.

## Next Steps
1. Test other asteroids in shard 16 for similar discontinuities
2. Document the observational coverage limits in the kernel metadata
3. Add runtime checks in Moira to warn users when querying outside coverage
