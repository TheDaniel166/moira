# Moira 6.2.2 - Lunar Node And Lilith Honesty

**Release date:** 2026-08-15

**Public upgrade path:** 6.2.1 to 6.2.2. Callers still on 6.2.0 inherit the
wheel catalog plus this node/Lilith honesty patch.

Moira 6.2.2 is a lunar-point honesty release. It binds Mean Lilith to the
same IERS conventional arguments as the mean node, and it stops reporting
a mean-rate proxy as the speed of True Node and True Lilith. Public
function signatures and REST paths do not change.

## In this release

- **IERS Mean Lilith** — `Body.LILITH` / `mean_lilith()` is the IERS 2003
  secular mean apogee `F + Ω − l + 180°` from `_fundamental_args`, with
  the 5.2.2 `nutation=` frame unchanged. ERFA `faf03 + faom03 − fal03 +
  180°` is the authority. Modern longitudes move by less than 0.2″ versus
  the previous Meeus polynomial.
- **True Node and True Lilith speed** — `NodeData.speed` is the circular
  finite-difference of the DE osculating true-of-date longitude (0.002-day
  TT step, same span as planetary longitude rates). The previous constant
  mean-node rate and borrowed mean-Lilith rate are removed. Speeds may be
  large or retrograde; that is the geometry.
- **Receipts** — Lilith reduction stages name
  `iers_2003_mean_apogee_solution`.
- **Swiss comparison doctrine** — a shared astrological name is not a
  shared number. Swiss digits are not a target. The 4–7′ residual versus
  `SE_MEAN_APOG` is expected (IERS secular mean vs ELP hybrid). True
  Lilith versus `SE_OSCU_APOG` remains the close numerical match.

See
[`MIGRATING_FROM_SWISS_EPHEMERIS.md`](../02_services/MIGRATING_FROM_SWISS_EPHEMERIS.md#why-a-swiss-number-is-not-a-moira-number).

## Not in 6.2.2

- `smoothed_lilith()` and `Body.SMOOTHED_LILITH` are not implemented.
- Kernel presence does not change which product `Body.LILITH` is.
- Swiss `SE_MEAN_APOG` digits are not a parity target.
- No Track B, visibility, Track C, or website entitlement change.

## Install

```text
pip install moira-astro==6.2.2
```

```python
from moira.nodes import mean_lilith, true_lilith, true_node

# Mean Lilith: IERS secular mean. Do not assert arcminute parity with swe.MEAN_APOG.
mean_lilith(jd_ut)

# True Lilith / True Node: longitude unchanged; speed is dλ/dt of that point.
true_lilith(jd_ut, reader=reader)
true_node(jd_ut, reader=reader)
```

## Addresses

[TheDaniel166/moira#18](https://github.com/TheDaniel166/moira/issues/18)
is answered by this release: the Mean Lilith residual versus Swiss
`SE_MEAN_APOG` is a series difference, not a defect. The issue is not
closed as a Swiss-parity bug.
