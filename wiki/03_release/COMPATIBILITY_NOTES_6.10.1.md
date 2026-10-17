# Compatibility Notes - Moira 6.10.1

## Upgrade boundary

Moira 6.10.1 follows 6.10.0. Python 3.10 through 3.14 remain supported, and all
6.10.0 Vedic, astronomical, and small-body (`2026.10.10.1`) contracts remain in
effect.

## Additive runtime truth and REST surfaces

- **Additive `*_with_truth` Python facade functions:**
  Existing functions (`jd_from_datetime`, `datetime_from_jd`, `delta_t_from_jd`,
  `utc_to_ut1`, `utc_to_tt`, `local_sidereal_time`, `ecliptic_to_equatorial`,
  `equatorial_to_horizontal`, `true_obliquity`, `planet_relative_to`,
  `true_lilith`, `ayanamsa`, `nakshatra_of`, `all_nakshatras_at`,
  `tropical_to_sidereal`, `sidereal_to_tropical`, `classify_chart_shape`)
  preserve their return types while paired `*_with_truth` functions return
  immutable `ComputationTruth`-bearing vessels.
- **Additive REST `computation_truth` fields:**
  Core chart, position, sky, house, sidereal, nakshatra, chart-wheel, phenomena,
  station, solar-condition, void-of-course, and relationship responses include
  additive `computation_truth` receipts. Strict clients that forbid unknown
  response keys should allow `computation_truth`.
- **Observer coordinate pairing on `POST /v1/chart` and `POST /v1/positions/planet`:**
  Supplying only one of `latitude` / `longitude` (or `observer_lat` /
  `observer_lon`) is rejected with HTTP 422 rather than silently dropping the
  partial observer coordinate.
- **Natal Discovery REST endpoints:**
  `POST /v1/natal-discovery/dispositor-chains`,
  `POST /v1/natal-discovery/jones-shape`, and
  `POST /v1/natal-discovery/lunar-context` are new additive `/v1` operations.

