# Compatibility Notes - Moira 6.2.2

## Upgrade Boundary

Moira 6.2.2 is API-compatible from 6.2.1, 6.2.0, 6.1.1, and 6.1.0.

- Public function signatures, REST paths, and response models remain.
- `mean_lilith(jd_ut, *, nutation=True)` and
  `true_node` / `true_lilith` call forms are unchanged.
- Planetary reduction, wheel catalog `2026.08.14.1`, Track A, Track B,
  and physical visibility are unchanged.
- Numerical products for two lunar-point fields change, as below.

## Mean Lilith series

`Body.LILITH` / `mean_lilith()` is now the IERS 2003 secular mean apogee
`F + Ω − l + 180°`, the same argument family as `mean_node()`.

- On 1955–2010 dates the longitude moves by **less than 0.2″** versus
  6.2.1 Meeus. At 1625 the shift is about **1.2″**.
- The 5.2.2 `nutation=` frame is unchanged. Default remains true equinox
  of date. Speed is the IERS combination rate, not Δψ.
- The **4–7′ residual versus Swiss `SE_MEAN_APOG` remains**. That is
  IERS secular mean versus Swiss ELP hybrid, not a frame error. Do not
  treat Swiss digits as a target. See
  [Why a Swiss number is not a Moira number](../02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md#why-a-swiss-number-is-not-a-moira-number).
- Regenerate cached Mean Lilith only if bit-level identity with 6.2.1
  Meeus values was frozen.

## True Node and True Lilith speed

Longitudes are unchanged. `NodeData.speed` is now the circular
finite-difference of the DE osculating true-of-date longitude
(0.002-day TT step).

- The previous True Node constant ≈ −0.05295°/day and the borrowed
  Mean Lilith rate ≈ +0.1114°/day are gone.
- Speeds may be several degrees per day, near zero, or retrograde.
  That is the geometry of the osculating axis, not a display defect.
- Chart-wheel retrograde glyphs and wheel aspect applying/separating
  that read `node.speed` will follow the geometric rate.
- `Chart.speeds()`, synastry motion, and transit searches do not use
  these fields (planets only, or longitude sampling).
- Mean Node / Mean Lilith speeds remain IERS series derivatives.

## Chart reduction

Lilith `stage_sequence` now includes `iers_2003_mean_apogee_solution`
instead of `analytical_apogee_solution`. `source_surface` remains
`moira.mean_lilith`. Strict response consumers must admit the new stage
name.

## Recommended Migration Sequence

1. Install `moira-astro==6.2.2` in staging.
2. Recompute a known Mean Lilith chart: longitude should match 6.2.1
   at chart precision; do not expect Swiss `MEAN_APOG` arcminute match.
3. If you display True Node / True Lilith daily motion or retrograde,
   accept that those speeds can now change sign.
4. If you freeze node `speed` in fixtures, regenerate them from 6.2.2.
5. Promote the exact staged artifact.

No database migration is required. Restart processes that import `moira`.

## Upgrade Pin

```text
moira-astro==6.2.2
moira-astro[server]==6.2.2
```

## Rollback

Pin back to `moira-astro==6.2.1` to restore Meeus Mean Lilith and the
mean-rate proxies on True Node / True Lilith speed. Signatures are the
same in both pins.
