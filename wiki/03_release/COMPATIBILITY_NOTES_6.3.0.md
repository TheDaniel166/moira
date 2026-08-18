# Compatibility Notes - Moira 6.3.0

## Upgrade Boundary

Moira 6.3.0 is backward-compatible from 6.2.2 for every *valid omitted*
Hellenistic profile request. New surfaces are additive. Extra request
keys still 422 (`extra=forbid`).

- Profile method stays `moira.hellenistic_chart_profile.v2`.
- `HELLENISTIC_PROFILE_LOTS` stays Fortune, Spirit, Eros (Valens),
  Necessity (Valens).
- Singular `zodiacal_releasing` is still the selected lot. Dual ZR is an
  optional companion, default off.
- `included_components` / `excluded_components` are bitwise identical to
  6.2.2.
- Planetary reduction, wheel catalog, Track A/B, and physical visibility
  are unchanged.

## Zodiacal Releasing default depth

Atomic, facade, and REST **omitted** `levels` changed from **4 to 2**.

- Callers that never passed `levels` now receive L1/L2 only.
- Explicit `levels=3` or `levels=4` still works. Maximum remains 4.
- This is the one implicit-behavior change in 6.3.0. If you displayed
  L3/L4 from an omitted argument, pass `levels=4` or set
  `policy.zr_levels = 4`.

`is_peak_period` is unchanged. `peak_grades` appears only when
`revival.zr_peak_grades` is on.

## Profile request and response shape

Omitted `policy.revival` and `policy.overlays` deserialize as all-off
6.2.2 composition.

When serialized, the profile now *echoes* those objects (defaults
false / depth 2) and may include null overlay fields:

- `supporting_lots`, `supporting_lots_not_evaluable`
- `twelfth_parts`
- `zodiacal_releasing_fortune`
- `sign_per_month_profection`
- `label_overlays`
- per-planet `assemble_condition` and `twelfth_part`
- ZR `peak_grades`

Strict response consumers that reject unknown keys must regenerate
clients. Request consumers that omit the new fields do not need to
change.

## New REST families

Regenerate OpenAPI clients to see:

```text
POST /v1/hellenistic/twelfth-parts
POST /v1/hellenistic/condition
POST /v1/hellenistic/circumambulations
POST /v1/hellenistic/transmissions
POST /v1/hellenistic/offices
```

These are not profile components. They do not alter
`POST /v1/hellenistic/chart-profile` unless overlays are explicitly
enabled.

## Offices and transmissions honesty

`POST /v1/hellenistic/offices` never selects a predominator or
house-master. `predominator` and `house_master` are null. It does not
import `find_hyleg` or `calculate_longevity`.

Transmission edges have no effect, prose, or polarity fields. The closed
Valens interpretive-table exclusion remains closed.

## Circumambulations

The releaser is caller-named. The engine will not pick a hyleg. Only
`time_key=bound_lord_minor_years` evaluates years. `rising_times` and
`equatorial` return `not_evaluable`. This is not a primary-direction
preset.

## Recommended Migration Sequence

1. Install `moira-astro==6.3.0` in staging.
2. Replay a 6.2.2 `POST /v1/hellenistic/chart-profile` body with no new
   keys. Expect `method_id` v2, four lots, and the same
   `included_components`.
3. If you relied on omitted ZR `levels=4`, pass `levels` explicitly.
4. Regenerate OpenAPI clients if you validate response models strictly.
5. Opt in to overlays only after reading the admission packets.
6. Promote the exact staged artifact.

No database migration is required. Restart processes that import `moira`.

## Upgrade Pin

```text
moira-astro==6.3.0
moira-astro[server]==6.3.0
```

## Rollback

Pin back to `moira-astro==6.2.2` to restore omitted ZR depth 4 and remove
the new Hellenistic atoms, overlays, and routes. 6.2.2 profile request
bodies remain valid on 6.3.0.
