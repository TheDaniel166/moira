# True Node And True Lilith Speed — Sky Rate

**Date:** 2026-08-15
**Status:** Approved
**Ships in:** `moira-astro` 6.2.2 (with the IERS mean-Lilith series)
**Depends on:** `docs/superpowers/specs/2026-08-15-mean-lilith-iers-and-de-smoothed-design.md` (already on this branch)

## Problem

`true_node()` and `true_lilith()` already compute DE-geometric longitudes.
`NodeData.speed` does not. True Node ships a constant mean-node rate
(`−1934.136261/36525`). True Lilith ships `mean_lilith(..., nutation=False).speed`.
Both comments say the true point “oscillates wildly.” That is the geometry.
Substituting the secular rate is a social convention, not the sky.

Planets already differentiate the declared longitude product
(`_geocentric_longitude_rate`, 0.002-day TT step). Progressions already
drop node/Lilith speeds. Transits time these points from longitude.
The fake rate is unused where it matters and dishonest where it is shown.

## Decision

`NodeData.speed` for an osculating point is the circular finite-difference
of **that point’s published true-of-date longitude**, in TT days, using
the same 0.002-day half-span planets use.

Mean Node and Mean Lilith keep IERS series derivatives. Those rates
already belong to the objects they name.

Loyalty is to the sky: a violent or sign-changing True Lilith/Node
speed is correct. Do not clamp, smooth, or fall back to the mean rate.

## Formula

```
step = 0.002   # TT days; same value as planets._LONGITUDE_RATE_STEP_DAYS
λ₋ = longitude(t_TT − step)
λ₊ = longitude(t_TT + step)
speed = ((λ₊ − λ₋ + 180) % 360 − 180) / (2 × step)   # deg/day
```

Do not import `moira.planets` from `moira.nodes` (cycle). Duplicate the
step constant in `nodes.py` with a comment pointing at the planetary one.

When `true_node(..., jd_tt=...)` is passed, differentiate that TT. When
only `jd_ut` is passed, convert with the existing
`_ut1_to_ephemeris_tt` path, then step TT.

Extract longitude-only helpers so rate evaluation cannot recurse through
the public functions.

Do not use two-body `a = −μr/r³`. Do not copy Swiss OSCU speeds.

## Signatures

Unchanged:

```python
true_node(jd_ut, reader=None, jd_tt=None) -> NodeData
true_lilith(jd_ut, reader=None) -> NodeData
```

`NodeData.name` stays `"True Node"` / `"True Lilith"`. Longitude, μ,
frame, and eccentricity-vector math stay as they are.

## Expected behaviour

- Speed is finite on covered DE epochs.
- Speed matches an independent circular difference of the public
  `.longitude` at `±0.002` TT days, within `2e-9` °/day (same tightness
  as the mean-node speed test).
- Speed is **not** the old constants. On ordinary modern dates it will
  differ from the mean rate, sometimes by degrees/day, and may be
  retrograde.
- Mean Node / Mean Lilith speeds are unchanged.

## Non-goals

- `smoothed_lilith()`, `Body.SMOOTHED_LILITH`, kernel auto-promotion.
- Changing true longitudes, μ, or frames.
- Changing mean series rates.
- Matching Swiss `OSCU_APOG` / true-node speed digits.
- Clamping, median filters, or “display speeds.”
- Bumping `pyproject` / `__version__` in this patch (release task names
  6.2.2 when both 6.2.2 fixes ship).

## Docs

- `true_node` / `true_lilith` docstrings: speed is `dλ/dt` of the
  osculating longitude. Remove “approximation” / “use finite difference
  yourself.”
- `moira/sky/bodies.py` blurbs: one line each that speed is the
  geometric rate and can change sign.
- API tables: True Node / True Lilith speed is the differentiated
  osculating longitude, not the mean rate.
- `CHANGELOG.md` `[Unreleased]`: add this change next to the IERS
  mean-Lilith note. Both ship as 6.2.2.
- Compatibility notes for 6.2.2 (written at release): True Node/Lilith
  `speed` is no longer a mean proxy; regenerate anything that froze
  those fields.

## Tests

Add `@pytest.mark.requires_ephemeris` tests beside
`tests/integration/test_true_node_frame_consistency.py` (True Node)
and a sibling or the same file (True Lilith), using the existing
`reader` fixture:

- J2000 and 2026-08-15 (jd_tt `2451545.0` and `2461199.9375`):
  `speed` equals the circular FD of `.longitude` at `±0.002` TT days.
- Those speeds are not equal to `-1934.136261/36525` (True Node) or
  `mean_lilith(jd, nutation=False).speed` (True Lilith) within
  `1e-6` °/day — at least at 2026-08-15, where the osculating rate
  is not the secular rate.
- Existing true-node longitude invariants stay green.

## Key Decisions

1. **Differentiate the published longitude.** Same object, honest rate.
2. **0.002-day TT step.** Match planets. No new differentiator.
3. **No smoothing.** Wild rates are the sky.
4. **Same 6.2.2 train as IERS mean Lilith.** One node/Lilith honesty
   release.

## Open Questions

None. Framing approved: math fix, loyal to the sky.
