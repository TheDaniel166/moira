# Compatibility Notes - Moira 6.12.0

Python 3.10 through 3.15 are supported. REST routes are additive except where
stated below.

## Behaviour changes

- **Fixed stars default to the apparent place.** A star position without a
  named product now needs a planetary kernel and moves by up to about 20 arcsec.
  Pass `product="astrometric"` for the previous kernel-free result. REST maps a
  missing kernel to `503 kernel_not_ready`. Sirius and alpha Centauri positions
  also change (Sirius up to 3.9 arcsec).
- **Sidereal time** takes an optional `jd_tt`; without it, results move by
  0.1 mas in 2026 and up to 67 mas at -2000.
- **Native module signatures changed.** `greenwich_mean_sidereal_time` is
  `(jd_ut, jd_tt)`, `apparent_sidereal_time` is `(jd_ut, jd_tt,
  nutation_longitude)`, and `TopocentricEvaluator` and the five native
  visibility functions require `delta_t`. Callers of `moira._moira_native`
  directly must pass the new arguments.
- **Geodetic.** A direct sidereal geodetic chart requires an explicit
  `ayanamsa_deg`; a tropical request carrying an ayanamsa is refused (HTTP 422
  on `/v1/geodetic/*`); latitudes within 1e-6 degrees of a pole are refused.
- **`Moira.longevity`** uses Lilly 1647 and fails closed on missing planets or
  non-quadrant cusps.
- **Hellenistic inputs are validated:** a chart that does not match `natal_dt`,
  Spirit releasing without `fortune_longitude`, and unknown `/lots` house
  systems are rejected.
- **Strict schema clients** of the Enhanced ZR responses must accept the new
  `start_shift_truth` field.
- **Fixed-star truth fields:** `FixedStarTruth.true_position` is True only for
  the geometric product; `FixedStarClassification.observer_mode` is
  `"barycentric"` except for the apparent product.
- **Leap-second display:** a UT1 instant inside an inserted second shows as
  `23:59:60` rather than a repeated label.

## Packaging

Wheels now include `cp315`, which raises release size. DE441 is still
downloaded separately.
