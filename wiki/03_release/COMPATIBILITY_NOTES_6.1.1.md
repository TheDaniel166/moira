# Compatibility Notes - Moira 6.1.1

## Upgrade Boundary

Moira 6.1.1 is a backward-compatible patch from 6.1.0. It adds 51 canonical
asteroid identities and binds the packaged manifest to catalog `2026.08.12.1`
without changing public function signatures, REST request/response models,
planetary computation, or kernel file formats.

Existing 9,974 names keep their canonical strings and NAIF IDs.

## Identity Is Not Ephemeris Availability

`list_asteroids()` returns 10,025 known canonical names. This does not mean
that every installation has all 401 external BSP shards.

Applications should distinguish:

- **known identity** — present in the bundled canonical registry;
- **loaded availability** — present in the active reader's covered-body set;
- **position capability** — the required nonempty BSP shard is installed and
  the requested time is inside the manifest-declared coverage.

For REST consumers, `GET /v1/asteroids/list` continues to intersect canonical
identities with the loaded small-body reader. An older `2026.07.27.1`
installation therefore returns only the bodies that catalog actually covers.

## Deployment Guidance

1. Upgrade the engine and optional server environment to
   `moira-astro==6.1.1`.
2. Point the host asteroid tree at the matching external release
   `2026.08.12.1`. On the Moira box that is the
   `/srv/moira-data/kernels/asteroids` symlink.
3. Restart processes that import `moira.asteroids`; the registry is loaded at
   module import time. Restart `moira-engine` and `moira-api` together.
4. Verify readiness and the resolved manifest before serving positions.
5. Search representative new names such as `'Aylo'chaxnim` and
   `Ka\`epaoka\`awela`, and a retained name such as `Mani`.
6. Perform at least one position call through the same service path used by
   the application.

No database migration is required.

## Rollback

The package can be rolled back to `moira-astro==6.1.0` without deleting the
`2026.08.12.1` files. On rollback, the 51 new canonical names are no longer
searchable by name. If the live symlink still points at `2026.08.12.1`, the
reused shards 000-397 continue to serve the 9,974 older identities. To restore
the previous pointer exactly, retarget
`/srv/moira-data/kernels/asteroids` to
`asteroid-catalog-releases/2026.07.27.1`.
