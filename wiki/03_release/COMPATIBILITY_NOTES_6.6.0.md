# Compatibility Notes - Moira 6.6.0

## Additive API, bounded numerical correction

Existing Python signatures and REST request bodies remain accepted. New
exports and `POST /v1/stelliums/analyze` introduce `moira.stellium.v1`.
This release also intentionally changes nonzero-offset Whole Sign/Solar Sign
cusp values to the selected zodiac's sign boundaries. Clients depending on
the previous rotated-tropical-sign result must refresh affected chart caches.
Polar policy, requested/effective system identity and fallback receipts stay
intact. Tropical, zero-offset and physical quadrant results are unchanged.

## Old and new stelliums are different products

`moira.aspects.find_patterns`, `moira.patterns.find_stelliums`,
`find_all_patterns`, `Moira.patterns` and `/v1/patterns/*` retain existing
clique/centroid, arbitrary supplied-object and condition semantics.

The new analyzer counts only the canonical ten planets under Strict four or
Broad three. Associated factors never count. Default eight degrees is a
**maximum total arc**, not the old centroid radius; old orb settings must not
be silently migrated into this field. New evidence is separate from
`AspectPattern` and does not supply invented contributions or strength scores.

## Snapshot migration

Preserve full-precision computed longitudes, explicit selection and source,
coordinate regime, zodiac/offset and same-frame house geometry. House input
reuses the full house response plus `longitude_frame`; no per-body house
integer map replaces engine geometry. Missing/unknown time must withhold
unreliable houses and angles rather than treating nominal noon as known.

An old server or unsupported schema is a visible error/unavailable state,
not permission to fall back to local strings or legacy detection. Cache and
late-response guards must include schema, engine generation, complete
positions, selection, policy and house/frame context. Associated visibility
must not alter the source/group identity. Historical saved reports remain
unchanged; newly generated packets must identify their evidence version.

## Rollout boundary

Install and test the same published package in staging before production.
Only then admit new consumer contracts and invalidate affected chart caches.
No database migration, new notification admission, paid-report regeneration,
kernel rebuild or native algorithm change is required by this engine release.
