# Compatibility Notes - Moira 6.5.0

## Upgrade Boundary

Moira 6.5.0 is backward-compatible from 6.4.1. Existing Python signatures,
result vessels, defaults, and valid REST request bodies are unchanged. The
release adds new root exports and four new REST operations.

- The historical five-entry `POST /v1/galactic/reference-points` response is
  unchanged. The typed registry is a separate
  `POST /v1/galactic/cosmic-reference-points` operation.
- Planetary reduction, fixed-star reduction, Delta-T, house systems, transit
  searches, asteroid/comet catalogs, Hellenistic profiles, Track A/B, and
  physical visibility are unchanged.
- No database migration is required.

## New Python surface

The package root now exports deep-sky identity, search, and position functions,
plus the typed cosmic-reference definitions and position functions. These are
additive names; existing imports continue to resolve.

Deep-sky Python position functions accept a finite Julian Date in TT. They
return geocentric true-ecliptic-of-date directions. A returned longitude and
latitude are angular coordinates, not a distance or a claim that the catalog
center is a physical center of mass.

## New REST surface

```text
GET  /v1/deep-sky/list
POST /v1/deep-sky/position
POST /v1/deep-sky/bulk
POST /v1/galactic/cosmic-reference-points
```

The deep-sky position routes require a timezone-aware `dt`; the service
normalizes it to UTC and exposes the resulting TT epoch in provenance. The bulk
route accepts 1 to 60 names and defaults `skip_missing` to true. The cosmic
route accepts finite `jd_tt` and an optional `kind` of `physical_object`,
`coordinate_landmark`, or `proxy_reference`. Extra request keys remain 422.

Clients that pin or generate from the 6.4.1 OpenAPI document should regenerate
to discover the new paths, schemas, and `deep-sky` tag. No existing operation
schema was replaced.

## Catalog and identity semantics

- Deep-sky catalog version `2026.09.07.1` contains exactly 60 released
  coordinate anchors. Unknown names fail visibly; runtime lookup does not query
  SIMBAD or silently fill an unreviewed object.
- Cosmic-reference catalog version `2026.09.08.1` contains exactly 12 released
  references in three semantic classes.
- `star_registry_name`, `nasa_exoplanet_archive_hostname`, and
  `confirmed_planet_count` are host-star-specific fields. They are intentionally
  null for galaxies, nebulae, clusters, compact objects, and remnants.
- Aliases are exact normalized identities, not a fuzzy resolver. Use
  `find_deep_sky_objects()` or the list route's query parameter for substring
  discovery.
- Catalog contents are release-bound. A future catalog revision may add aliases
  or records under a new catalog version without changing the API vessel.

## Scope exclusions

Solar-System bodies are not admitted through the static deep-sky catalog.
Moons, asteroids, comets, and interstellar visitors require time-dependent
ephemerides and remain on their dedicated engine paths. The Local Group has no
released barycenter because no member and mass model has been selected.

## Recommended Migration Sequence

1. Install `moira-astro==6.5.0` in staging.
2. Replay existing 6.4.1 engine and REST requests; expect unchanged contracts.
3. Regenerate strict OpenAPI clients if the new routes are needed.
4. Exercise one catalog anchor and one typed reference, checking the returned
   provenance and catalog version.
5. Promote the exact staged artifact and restart processes that import Moira.

## Upgrade Pin

```text
moira-astro==6.5.0
moira-astro[server]==6.5.0
```

## Rollback

Pin back to `moira-astro==6.4.1`. Existing 6.4.1 calls remain valid; only the
new deep-sky and typed cosmic-reference names and routes become unavailable.
