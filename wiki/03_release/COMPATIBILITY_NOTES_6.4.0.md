# Compatibility Notes - Moira 6.4.0

## Upgrade Boundary

Moira 6.4.0 is backward-compatible from 6.3.0 for every valid request
body. New surfaces are additive. Extra request keys still 422
(`extra=forbid`).

- Profile method stays `moira.hellenistic_chart_profile.v2`.
- `HELLENISTIC_PROFILE_LOTS`, ZR depth, planetary reduction, the wheel
  catalog, Track A/B, and physical visibility are unchanged.
- `find_aspect_transits()` keeps its signature and its `AspectTransitEvent`
  vessel. Numeric-target searches now pre-filter candidate windows from a
  native longitude scan; exact event times are still refined by the same
  bisection and tolerance.

## Delta-T future scenario

This is the one numeric change in 6.4.0 that can move an output without a
request change.

- Dates inside the observed Delta-T table are unchanged.
- Dates after the observed table follow
  `D0 + 29.09·((year − Y0)/100)²`. The previous linear handoff slope is no
  longer applied.
- `ΔT(2100)` moves from 83.29 s to about 85.00 s. The shift grows with
  distance from the table edge and is sub-second inside the next few
  decades.
- `chart.delta_t`, `ut_to_tt`, `tt_to_ut`, and every product derived from
  them reflect the new curve for future-dated epochs. Snapshots of
  future-dated charts taken on 6.3.0 will differ by that amount.
- `DeltaTPolicy` names, EOP handling, and source-era totals are unchanged.

## Natal aspect grid

New public surfaces, none of which alter existing ones:

- `moira.facade.find_aspect_transits_to_longitudes(body, targets, jd_start, jd_end, ...)`
  with `targets` as `(longitude_deg, aspect_angle_deg, orb_deg)` tuples.
- `Moira.natal_aspect_transits(body, natal_longitudes, aspect_angles, jd_start, jd_end, aspect_orbs=None, search_motion="forward")`.
- `POST /v1/transits/natal-aspects` (`predictive` tag).
- `POST /v1/batch/events` item kind `natal_aspect_transits` with
  `natal_longitudes`, `aspect_angles`, and `aspect_orbs`.

`EventBatchItemRequest` gained three optional list fields with
descriptions. `AspectTransitEventResponse` now lives in the transits model
module and is re-exported from the batch module; its schema name and shape
are unchanged. Strict OpenAPI clients should regenerate to see the new
route and fields.

## Native bindings

`moira._moira_native` gained `ecliptic_longitude_batch` and
`find_aspects_to_longitude`. Both release the GIL. Nothing was removed.

## Recommended Migration Sequence

1. Install `moira-astro==6.4.0` in staging.
2. Replay a 6.3.0 request body with no new keys. Expect identical output
   for epochs inside the observed Delta-T table.
3. If you keep future-dated golden charts, expect `delta_t` to move by the
   scenario difference and re-baseline deliberately.
4. Regenerate OpenAPI clients if you validate response models strictly.
5. Promote the exact staged artifact.

No database migration is required. Restart processes that import `moira`.

## Upgrade Pin

```text
moira-astro==6.4.0
moira-astro[server]==6.4.0
```

## Rollback

Pin back to `moira-astro==6.3.0` to restore the linear Delta-T handoff and
remove the natal aspect grid surfaces. 6.4.0 request bodies that do not use
the new route or batch kind remain valid on 6.3.0.
