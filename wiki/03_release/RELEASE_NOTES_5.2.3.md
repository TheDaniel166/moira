# Moira 5.2.3 - Installed Small-Body Manifest Readiness

**Release date:** 2026-07-25  
**Public upgrade path:** 5.2.2 to 5.2.3

Moira 5.2.3 is an operational-correctness patch for asteroid and comet kernel
discovery. It does not change astronomical calculations, catalog membership,
public result vessels, or BSP data.

## What Changed

Published wheels retain asteroid and comet manifests as catalog and provenance
metadata, while their large BSP shards remain separately installed resources.
Earlier automatic discovery treated the presence of those metadata files as
proof that the corresponding ephemeris was installed. A wheel used alongside
an external small-body ephemeris could therefore report a missing packaged
shard in `Moira.kernel_status` and the server `/ready` receipt even though the
external ephemeris was loaded and functional.

Automatic discovery now admits a manifest only when at least one shard it
references is present:

- metadata-only wheel manifests remain available as packaged records but are
  not treated as installed ephemerides;
- complete external manifests load normally;
- partial installations remain discoverable so the shard loader rejects them
  rather than silently hiding corruption; and
- `MOIRA_SOVEREIGN_SMALL_BODY_MANIFEST` remains an explicit, strict operator
  instruction and is never suppressed by automatic discovery policy.

## Asteroid And Comet Data Boundary

No asteroid or comet manifest content, BSP shard, catalog identity, family
membership, coverage interval, or NAIF mapping changed in this release. Existing
external ephemerides remain the positional authority until a later shard set is
fully built, validated, and admitted as one coherent manifest-owned resource.

## Validation

The release exercises:

- metadata-only automatic discovery;
- complete installed-manifest discovery;
- partial-installation fail visibility;
- explicit-manifest fail visibility;
- facade kernel readiness; and
- REST server startup and `/ready` behavior.

A wheel-shaped isolated installation confirms that packaged manifests without
their large BSP shards are not admitted as installed ephemerides.
