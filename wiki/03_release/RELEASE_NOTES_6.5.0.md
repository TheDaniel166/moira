# Moira 6.5.0 - Source-Bound Cosmic Catalogs

**Release date:** 2026-09-09

**Public upgrade path:** 6.4.1 to 6.5.0.

Moira 6.5.0 is an additive catalog and coordinate-surface release. It admits a
curated 60-object deep-sky catalog and a typed 12-entry cosmic-reference
registry without treating every astronomical "center" as the same kind of
object. Existing Python signatures and REST request bodies remain valid.

## In this release

- **Sixty source-bound deep-sky anchors** - 15 galaxies, 15 nebulae, 15 star
  clusters, 5 compact objects, 5 stellar remnants, and 5 confirmed exoplanet
  host stars. Every record carries its released SIMBAD identity and coordinate
  receipt; host status is separately confirmed against the NASA Exoplanet
  Archive.
- **Honest position semantics** - extended objects are represented by their
  catalog centers, not by claims of a unique physical point or mass center.
  Eligible cluster and compact-system records use only explicitly admitted
  SIMBAD proper motion, while host-star positions delegate to Moira's sovereign
  star registry. Results are geocentric directions in the true ecliptic of
  date.
- **Twelve typed cosmic references** - seven coordinate landmarks, two
  physical catalog objects, and three declared proxies. The formal
  supergalactic longitude origin remains distinct from the Virgo/M87
  astrological SGC convention. Norma/ACO 3627 and Shapley/ACO 3558 are exposed
  as named proxies for broad structures rather than universal point centers.
- **Python package surface** - `DeepSkyClass`, `DeepSkyObject`,
  `DeepSkyPosition`, catalog lookup/search functions, position functions,
  `CosmicReferenceKind`, reference definition/position vessels, and reference
  lookup/position functions are exported from `moira`.
- **REST surface** - `GET /v1/deep-sky/list`,
  `POST /v1/deep-sky/position`, `POST /v1/deep-sky/bulk`, and
  `POST /v1/galactic/cosmic-reference-points`. The cosmic route accepts an
  optional semantic-kind filter. Responses preserve catalog version, source,
  frame, epoch, meaning, and coordinate receipts.
- **Release-bound provenance** - the deep-sky JSON is checked against its
  committed SHA-256 receipt at load time. Catalog class counts, identities,
  aliases, coordinate ranges, semantic classes, and citation fields fail
  visibly if the packaged artifacts drift.

## Compatibility boundary

The historical five-entry `POST /v1/galactic/reference-points` contract is
unchanged. No existing route, Python function signature, result vessel, default
policy, planetary reduction, or kernel requirement changed. The newly added
catalogs do not turn galaxies, nebulae, satellites, comets, or other moving
objects into interchangeable bodies.

## Validation

- Catalog integrity checks bind the 60 records to their metadata receipt and
  enforce the declared 15/15/15/5/5/5 class partition.
- Registry covenants enforce the 2/7/3 semantic partition, unique normalized
  labels, finite ICRS/J2000 directions, antipodal frame landmarks, and complete
  source receipts.
- Unit and server tests cover lookup, filtering, alias resolution, proper-motion
  policy, projection to true ecliptic of date, strict request validation, bulk
  missing-object policy, OpenAPI registration, and preservation of the legacy
  galactic route.

## Not in 6.5.0

- Planetary moons, additional comets, or interstellar visitors; those require
  time-dependent JPL ephemerides rather than a static coordinate catalog
- A Local Group barycenter without a declared member set and mass model
- Distances, physical sizes, topocentric parallax, or atmospheric refraction
  for deep-sky anchors
- Interpretive doctrine, scoring, Workspace UI, or public-website UI

## Install

```text
pip install moira-astro==6.5.0
```

```python
from moira import deep_sky_at, all_cosmic_references_at

m31 = deep_sky_at("M31", 2451545.0)
references = all_cosmic_references_at(2451545.0)
```

Read `COMPATIBILITY_NOTES_6.5.0.md` for the catalog-version, coordinate, and
REST migration boundaries.
