# Compatibility Notes - Moira 6.8.0

## Additive small-body orbital classification and nullable open-conic fields

Moira 6.8.0 preserves existing public Python function signatures and REST schemas
while adding SBDB osculating asteroid classification and admitting small bodies
to heliocentric orbital element routes.

## Python surface

- `orbit_class` and `orbit_classes_at` are added to the public API under
  `moira.orbits`, `moira.predictive`, and `moira.facade`.
- Asteroids and small bodies are admitted to `orbit_class`. Non-small bodies
  (major planets, the Sun, the Moon, and barycenters) explicitly raise
  `OrbitalBodyNotSupportedError`.
- `osculating_elements` continues to evaluate small bodies and planets identically.

## REST surface

- `POST /v1/orbits/elements`: Existing consumers of the 9 historical planets
  receive unchanged, non-null response payloads. When small bodies with parabolic
  or hyperbolic orbits ($e \ge 1.0$) are requested, the open-conic fields
  `semi_major_axis_au`, `aphelion_distance_au`, `orbital_period_days`,
  `mean_anomaly_deg`, and `mean_motion_deg_per_day` serialize as `null`.
- `POST /v1/orbits/distance-extremes`: Admits small bodies. If an open conic
  lacks an apocenter or an extremum lies outside the evaluated search interval,
  the route returns HTTP 422 with category `orbital_event_availability`.
- New endpoints `POST /v1/orbits/class` and `POST /v1/orbits/class/batch` are
  registered under the `orbits` OpenAPI tag.
